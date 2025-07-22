import asyncio
import json
import logging
import os
import ssl
from av.audio.frame import AudioFrame
import sounddevice as sd
from fractions import Fraction
from aiohttp import web
from aiortc import (
    MediaStreamTrack,
    RTCPeerConnection,
    RTCSessionDescription, RTCIceServer, RTCConfiguration,
)
from aiortc.contrib.media import MediaPlayer, MediaRelay

ROOT = os.path.dirname(__file__)


class AsyncSoundDeviceAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, mic_url, samplerate=48000, channels=1, blocksize=256):
        super().__init__()
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.queue = asyncio.Queue(maxsize=10)
        self.frame_count = 0
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            blocksize=self.blocksize,
            dtype='int16',
            device=mic_url,
        )
        self.stream.start()
        asyncio.create_task(self._produce_audio())

    async def _produce_audio(self):
        while True:
            data, overflow = await asyncio.to_thread(self.stream.read, self.blocksize)
            if overflow:
                continue
            try:
                await self.queue.put(data.copy())
            except asyncio.QueueFull:
                try:
                    _ = self.queue.get_nowait()
                    await self.queue.put(data.copy())
                except asyncio.QueueEmpty:
                    pass

    async def recv(self):
        data = await self.queue.get()
        frame = AudioFrame(format="s16", layout="mono", samples=data.shape[0])
        frame.planes[0].update(data.tobytes())
        frame.sample_rate = self.samplerate
        frame.time_base = Fraction(1, self.samplerate)
        frame.pts = self.frame_count
        self.frame_count += frame.samples
        return frame


class MediaCapture:
    def __init__(self, cam_url, mic_url, fps=30, width=1280, height=720):
        self.cam_url = cam_url
        self.fps = fps
        self.width = width
        self.height = height
        self.mic_url = mic_url

        self.pcs = set()
        self.cam_relay = None
        self.cam = None
        self.mic = None
        self.mic_relay = None

    def _create_tracks(self):
        if self.cam_relay is None:
            self.cam = MediaPlayer(
                self.cam_url,
                format="v4l2",
                options={"framerate": str(self.fps), "video_size": f"{self.width}x{self.height}"}
            )
            self.cam_relay = MediaRelay()

        if self.mic_relay is None:
            self.mic = AsyncSoundDeviceAudioTrack(self.mic_url)
            self.mic_relay = MediaRelay()

        audio_track = self.mic_relay.subscribe(self.mic)
        video_track = self.cam_relay.subscribe(self.cam.video)

        return video_track, audio_track

    async def handle_offer(self, params):
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls=["turn:10.21.40.25:3478"], username="turnuser", credential="turnpassword")
        ])
        pc = RTCPeerConnection(configuration=config)
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is", pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        video, audio = self._create_tracks()
        if video:
            pc.addTrack(video)
        if audio:
            pc.addTrack(audio)

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return pc.localDescription.sdp, pc.localDescription.type

    async def shutdown(self):
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()

        if self.cam:
            self.cam.video.stop()

        if isinstance(self.mic, MediaPlayer) and hasattr(self.mic, "audio"):
            self.mic.audio.stop()


media = MediaCapture('/dev/video0', 0, 30, 1280, 720)


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    sdp, typ = await media.handle_offer(params)

    return web.Response(
        content_type="application/json",
        text=json.dumps({"sdp": sdp, "type": typ}),
    )


async def on_shutdown(app):
    await media.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain("cert.pem", "key.pem")

    app = web.Application()
    app.on_shutdown.append(on_shutdown)
    app.router.add_get("/", index)
    app.router.add_get("/client.js", javascript)
    app.router.add_post("/offer", offer)
    web.run_app(app, host="0.0.0.0", port=8080, ssl_context=ssl_context)
