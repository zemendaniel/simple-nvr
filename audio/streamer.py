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

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._stream_audio, daemon=True).start()
        print('[AudioStreamer] Audio thread started.')

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.thread.join(timeout=1)
        print('[AudioStreamer] Audio thread stopped.')

    def add_client(self, sid):
        join_room(self.room, sid=sid)
        if not self.is_running:
            self.start()

    def remove_client(self, sid):
        leave_room(self.room, sid=sid)
        # todo stop if empty

    def _stream_audio(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16') as stream:
                while self.is_running:
                    data, _ = stream.read(self.chunk_size)
                    threading.Thread(
                        target=AudioStreamer.send_audio, args=(self.room, data)
                    ).start()
        except Exception as e:
            print(f'[AudioStreamer] Error: {e}')

    @staticmethod
    def send_audio(room, data):
        sio.emit('audio_chunk', data.tobytes(), room=room)
        sio.sleep(0)
