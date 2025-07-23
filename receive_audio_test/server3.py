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
    def __init__(self, track, device='hw:1,0'):
        self.track = track
        self.queue = asyncio.Queue(maxsize=20)
        self.device = device
        self.buffer = np.empty((0, 2), dtype=np.int16)

        print(f"[AudioPlaybackTrack] Starting output stream on device {self.device}")
        self.stream = sd.OutputStream(
            samplerate=48000,
            channels=2,
            dtype='int16',
            blocksize=256,
            device=self.device,
            callback=self._callback,
        )
        self.stream.start()
        print("[AudioPlaybackTrack] Output stream started")

        self._task_receive = asyncio.create_task(self._receive_audio())

    async def _receive_audio(self):
        print("[AudioPlaybackTrack] Audio receive task started")
        while True:
            try:
                frame = await self.track.recv()
                print("[AudioPlaybackTrack] Received audio frame")
            except MediaStreamError:
                print("[AudioPlaybackTrack] Track ended or closed")
                break

            try:
                self.queue.put_nowait(frame)
                print(f"[AudioPlaybackTrack] Frame put in queue (size={self.queue.qsize()})")
            except asyncio.QueueFull:
                print("[AudioPlaybackTrack] Queue full, dropping frame")

    def _callback(self, outdata, frames, time, status):
        if status:
            print(f"[AudioPlaybackTrack] Output stream status: {status}")

        try:
            while self.buffer.shape[0] < frames:
                frame = self.queue.get_nowait()
                raw = frame.to_ndarray()
                data = raw.reshape(-1, 2)  # reshape to (samples, 2 channels)
                if data.dtype != np.int16:
                    data = (data * 32767).astype(np.int16)
                self.buffer = np.vstack([self.buffer, data])
                print(f"[AudioPlaybackTrack] Added {data.shape[0]} samples to buffer (buffer size={self.buffer.shape[0]})")

        except asyncio.QueueEmpty:
            print("[AudioPlaybackTrack] Queue empty, no new data to add")

        if self.buffer.shape[0] >= frames:
            outdata[:] = self.buffer[:frames]
            self.buffer = self.buffer[frames:]
            print(f"[AudioPlaybackTrack] Outputting {frames} frames, buffer left {self.buffer.shape[0]}")
        else:
            outdata.fill(0)  # not enough data, output silence
            self.buffer = np.empty((0, 2), dtype=np.int16)
            print(f"[AudioPlaybackTrack] Not enough data, outputting silence")

class MediaCapture:
    def __init__(self):
        self.pcs = set()

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
                pc._track = AudioPlaybackTrack(track)  # Instantly starts receiving & playing

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
