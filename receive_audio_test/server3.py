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
import numpy as np
import atexit

ROOT = os.path.dirname(__file__)


class AudioPlaybackTrack:
    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue(maxsize=100)

        self.stream = sd.OutputStream(
            samplerate=48000,
            channels=1,
            dtype='int16',
            blocksize=256,
        )
        self.stream.start()

    def start(self):
        if not self.stream.active:
            asyncio.create_task(self.playback_loop())
            print('[AudioPlaybackTrack] Audio thread started.')

    def receive_audio(self, frame):
        try:
            self.queue.put_nowait(frame)
        except asyncio.QueueFull:
            print("Audio queue full — dropping frame")

    async def playback_loop(self):
        while True:
            frame = await self.queue.get()
            # Convert to ndarray with signed 16-bit PCM format (common for sounddevice)
            data = frame.to_ndarray()
            # Flatten the array (mono)
            sd_data = np.asarray(data, dtype=np.int16).flatten()
            # Use a thread to avoid blocking the event loop during output write
            await asyncio.to_thread(self.stream.write, sd_data)


class MediaCapture:
    def __init__(self):
        self.pcs = set()
        self.playback = AudioPlaybackTrack()

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
                self.playback.start()
                print("Client audio track received")

                async def receive_audio():
                    while True:
                        frame = await track.recv()
                        self.playback.receive_audio(frame)
                        print(f"Received audio frame: {frame.samples} samples")

                # Start the frame receiving loop
                asyncio.create_task(receive_audio())

        # @pc.on("datachannel")
        # def on_datachannel(channel):
        #     print(f"Data channel created: {channel.label}")
        #
        #     @channel.on("message")
        #     def on_message(message):
        #         print(f"Received message: {message}")

        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return pc.localDescription.sdp, pc.localDescription.type

    async def shutdown(self):
        coros = [pc.close() for pc in self.pcs]
        await asyncio.gather(*coros)
        self.pcs.clear()


media = MediaCapture()


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
