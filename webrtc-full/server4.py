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
    RTCSessionDescription, RTCIceServer, RTCConfiguration, MediaStreamError,
)
from aiortc.contrib.media import MediaPlayer, MediaRelay
import numpy as np
import atexit

ROOT = os.path.dirname(__file__)


class AudioPlaybackTrack:
    def __init__(self, track, device=1):
        self.track = track
        self.queue = asyncio.Queue(maxsize=20)
        self.device = device
        self.buffer = np.empty((0, 2), dtype=np.int16)

        print(f"[AudioPlaybackTrack] Starting output stream on device {self.device}")
        try:
            self.stream = sd.OutputStream(
                samplerate=48000,
                channels=2,
                dtype='int16',
                blocksize=256,
                device=self.device,
                callback=self._callback,
            )
            self.stream.start()
        except sd.PortAudioError as e:
            pass
            print(f"PortAudio error opening output stream: {e}")

        self._task_receive = asyncio.create_task(self._receive_audio())

    async def _receive_audio(self):
        print("[AudioPlaybackTrack] Audio receive task started")
        while True:
            try:
                frame = await self.track.recv()
                # print("[AudioPlaybackTrack] Received audio frame")
            except MediaStreamError:
                # print("[AudioPlaybackTrack] Track ended or closed")
                break

            try:
                self.queue.put_nowait(frame)
                # print(f"[AudioPlaybackTrack] Frame put in queue (size={self.queue.qsize()})")
            except asyncio.QueueFull:
                pass
                # print("[AudioPlaybackTrack] Queue full, dropping frame")

    def _callback(self, outdata, frames, time, status):
        if status:
            pass
            # print(f"[AudioPlaybackTrack] Output stream status: {status}")

        try:
            while self.buffer.shape[0] < frames:
                frame = self.queue.get_nowait()
                raw = frame.to_ndarray()
                data = raw.reshape(-1, 2)  # reshape to (samples, 2 channels)
                if data.dtype != np.int16:
                    data = (data * 32767).astype(np.int16)
                self.buffer = np.vstack([self.buffer, data])
                # print(f"[AudioPlaybackTrack] Added {data.shape[0]} samples to buffer (buffer size={self.buffer.shape[0]})")

        except asyncio.QueueEmpty:
            pass
            # print("[AudioPlaybackTrack] Queue empty, no new data to add")

        if self.buffer.shape[0] >= frames:
            outdata[:] = self.buffer[:frames]
            self.buffer = self.buffer[frames:]
            # print(f"[AudioPlaybackTrack] Outputting {frames} frames, buffer left {self.buffer.shape[0]}")
        else:
            outdata.fill(0)  # not enough data, output silence
            self.buffer = np.empty((0, 2), dtype=np.int16)
            # print(f"[AudioPlaybackTrack] Not enough data, outputting silence")

    async def close(self):
        if self.stream:
            print("[AudioPlaybackTrack] Stopping output stream")
            self.stream.stop()
            self.stream.close()


class AudioRecordTrack(MediaStreamTrack):
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

    async def close(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class MediaCapture:
    def __init__(self, cam_url, fps, width, height, mic_url, playback_url):
        self.cam_url = cam_url
        self.fps = fps
        self.width = width
        self.height = height
        self.mic_url = mic_url
        self.playback_url = playback_url
        self.pcs = set()
        self.playback_track = None

        self.cam_relay = None
        self.cam = None
        self.mic_relay = None
        self.mic = None

    def _create_tracks(self):
        if self.cam_relay is None:
            self.cam = MediaPlayer(
                self.cam_url,
                format="v4l2",
                options={"framerate": str(self.fps), "video_size": f"{self.width}x{self.height}"}
            )
            self.cam_relay = MediaRelay()

        if self.mic_relay is None:
            self.mic = AudioRecordTrack(self.mic_url)
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

        @pc.on("track")
        def on_track(track):
            if track.kind == "audio":
                print("Client audio track received")
                if not self.playback_track:
                    self.playback_track = AudioPlaybackTrack(track, self.playback_url)
                # pc._track = self.playback_track  # Instantly starts receiving & playing

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

        if self.playback_track:
            await self.playback_track.close()
            self.playback_track = None

        if self.cam:
            self.cam.video.stop()

        if self.mic:
            await self.mic.close()


media = MediaCapture('/dev/video0', 30, 1280, 720, 2, 3)


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


async def stop(request):
    await media.shutdown()
    return web.Response()


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
    app.router.add_post("/stop", stop)
    web.run_app(app, host="0.0.0.0", port=8080, ssl_context=ssl_context)
