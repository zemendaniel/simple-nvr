import sounddevice as sd
import threading
from extensions import sio
from flask_socketio import join_room, leave_room


class AudioStreamer:
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.thread = None
        self.room = 'audio_listeners'
        self.is_running = False
        self.clients = set()

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._stream_audio, daemon=True)
        self.thread.start()
        print('[AudioStreamer] Audio thread started.')

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.thread.join(timeout=1)
        print('[AudioStreamer] Audio thread stopped.')

    def add_client(self, sid):
        if sid in self.clients:
            return
        join_room(self.room, sid=sid)
        self.clients.add(sid)
        if not self.is_running:
            self.start()

    def remove_client(self, sid):
        if sid not in self.clients:
            return
        leave_room(self.room, sid=sid)
        self.clients.remove(sid)
        if len(self.clients) == 0:
            self.stop()

    def _stream_audio(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16', latency='low') as stream:
                while self.is_running:
                    data, _ = stream.read(self.chunk_size)
                    sio.emit('audio_chunk', data.tobytes(), room=self.room)
                    sio.sleep(0)
        except Exception as e:
            print(f'[AudioStreamer] Error: {e}')

