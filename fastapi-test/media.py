import asyncio
from aiortc import RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCPeerConnection
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole


class MediaCapture:
    def __init__(self, cam_url, fps, width, height, mic_url):
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
            self.cam = MediaPlayer(self.cam_url,
                                   format="v4l2",
                                   options={'framerate': str(self.fps), 'video_size': f"{self.width}x{self.height}"})
            self.cam_relay = MediaRelay()

        if self.mic_relay is None:
            self.mic = MediaPlayer("hw:3,0", format="pulseaudio", options={"channels": "1", "sample_rate": "44100"})
            self.mic_relay = MediaRelay()

        return self.cam_relay.subscribe(self.cam.video), self.mic_relay.subscribe(self.mic.audio)
    
    async def handle_offer(self, params):
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls=['10.21.40.25:3478'], username='turnuser',
                         credential='turnpassword')
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
