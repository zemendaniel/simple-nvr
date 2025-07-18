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


def custom_host_addresses(**kwargs):
    print("Custom get_host_addresses called with:", kwargs)
    return ["0.0.0.0"]  # ← IP as string, not ip_address()


#ice.get_host_addresses = custom_host_addresses

pcs = set()
video_relay = None
audio_relay = None
webcam = None
mic = None


class SoundDeviceAudioTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, samplerate=48000, channels=1, blocksize=1024):
        super().__init__()
        self.samplerate = samplerate
        self.channels = channels
        self.blocksize = blocksize
        self.queue = asyncio.Queue()
        self.frame_count = 0  # Add this

        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            blocksize=self.blocksize,
            dtype='int16',
            callback=self.audio_callback
        )
        self.stream.start()

    def audio_callback(self, indata, frames, time, status):
        if status:
            if status.input_overflow:
                # silently ignore input overflow
                return
            else:
                print("Sounddevice status:", status)
        self.queue.put_nowait(indata.copy())

    async def recv(self):
        data = await self.queue.get()

        frame = AudioFrame(format="s16", layout="mono", samples=data.shape[0])
        for i in range(self.channels):
            frame.planes[i].update(data[:, i].tobytes() if self.channels > 1 else data.tobytes())

        frame.sample_rate = self.samplerate
        frame.time_base = Fraction(1, self.samplerate)

        # Set pts to frame count
        frame.pts = self.frame_count
        self.frame_count += frame.samples

        return frame


def create_local_tracks():
    global video_relay, audio_relay, webcam, mic

    options = {"framerate": "30", "video_size": "1280x720"}

    if video_relay is None:
        webcam = MediaPlayer("/dev/video0", format="v4l2", options=options)
        video_relay = MediaRelay()

    if audio_relay is None:
        mic = SoundDeviceAudioTrack(samplerate=48000, channels=1) # todo ez csere alsa
        audio_relay = MediaRelay()

    return audio_relay.subscribe(mic), video_relay.subscribe(webcam.video)


async def index(request):
    content = open(os.path.join(ROOT, "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def javascript(request):
    content = open(os.path.join(ROOT, "client.js"), "r").read()
    return web.Response(content_type="application/javascript", text=content)


async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    turn_server = RTCIceServer(
        urls=["turn:10.21.40.25:3478"],  # your TURN server IP and port
        username="turnuser",  # replace with your TURN username
        credential="turnpassword"  # replace with your TURN password
    )

    configuration = RTCConfiguration(iceServers=[turn_server])
    pc = RTCPeerConnection(configuration=configuration)

    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("Connection state is %s" % pc.connectionState)
        if pc.connectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    # Get tracks
    audio, video = create_local_tracks()

    if audio:
        pc.addTrack(audio)
    if video:
        pc.addTrack(video)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps(
            {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
        ),
    )


async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

    if webcam is not None:
        webcam.video.stop()


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
