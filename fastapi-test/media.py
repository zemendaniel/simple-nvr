import asyncio
from aiortc import RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCPeerConnection
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole
from parse_config import conf


class MediaCapture:
    def __init__(self, cam_url, fps, width, height):
        self.cam_url = cam_url
        self.fps = fps
        self.width = width
        self.height = height

        self.pcs = set()
        self.cam_relay = None
        self.cam = None

    def _create_tracks(self):
        if self.cam_relay is None:
            self.cam = MediaPlayer(self.cam_url,
                                   format="v4l2",
                                   options={'framerate': str(self.fps), 'video_size': f"{self.width}x{self.height}"})
            self.cam_relay = MediaRelay()
        return self.cam_relay.subscribe(self.cam.video)
    
    async def handle_offer(self, params):
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        config = RTCConfiguration(iceServers=[
            RTCIceServer(urls=[conf['turn']['url']], username=conf['turn']['username'],
                         credential=conf['turn']['password'])
        ])
        pc = RTCPeerConnection(configuration=config)
        self.pcs.add(pc)

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print("Connection state is", pc.connectionState)
            if pc.connectionState == "failed":
                await pc.close()
                self.pcs.discard(pc)

        video = self._create_tracks()
        if video:
            pc.addTrack(video)

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
