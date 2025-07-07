import sounddevice as sd
import threading
from extensions import sio
from flask_socketio import join_room, leave_room


class AudioStreamer:
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.clients = set()  # Track connected SIDs
        self.lock = threading.Lock()
        self.thread = None
        self.stop_event = threading.Event()

    def add_client(self, sid):
        with self.lock:
            self.clients.add(sid)
            if not self.thread or not self.thread.is_alive():
                self.stop_event.clear()
                self.thread = threading.Thread(target=self._stream_audio, daemon=True)
                self.thread.start()
                print('[AudioStreamer] Audio thread started.')

    def remove_client(self, sid):
        with self.lock:
            self.clients.discard(sid)
            if not self.clients:
                self.stop_event.set()
                print('[AudioStreamer] No more clients. Stopping thread.')

    def _stream_audio(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16') as stream:
                while not self.stop_event.is_set():
                    data, _ = stream.read(self.chunk_size)
                    with self.lock:
                        for sid in list(self.clients):
                            sio.emit('audio_chunk', data.tobytes(), to=sid)
                    sio.sleep(0)
        except Exception as e:
            print(f'[AudioStreamer] Error: {e}')