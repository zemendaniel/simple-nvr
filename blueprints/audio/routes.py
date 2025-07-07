from extensions import sio
from audio.streamer import AudioStreamer
from flask import request

streamer = AudioStreamer()


@sio.on('start_audio')
def start_audio_stream():
    sid = request.sid
    print(f'[AudioStreamer] Start requested by: {sid}')
    streamer.add_client(sid)


@sio.on('stop_audio')
def stop_audio_stream():
    sid = request.sid
    print(f'[AudioStreamer] Stop requested by: {sid}')
    streamer.remove_client(sid)
