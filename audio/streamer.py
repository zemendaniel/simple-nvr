import queue

import sounddevice as sd
import threading
from extensions import sio
from flask_socketio import join_room, leave_room


class AudioStreamer:
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.capture_thread = None
        self.room = 'audio_listeners'
        self.is_running = False
        self.q = queue.Queue(maxsize=100)

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.capture_thread = threading.Thread(target=self._capture_audio, daemon=True).start()
        sio.start_background_task(self._stream_audio)
        print('[AudioStreamer] Audio thread started.')

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        self.capture_thread.join(timeout=1)
        print('[AudioStreamer] Audio thread stopped.')

    def add_client(self, sid):
        join_room(self.room, sid=sid)
        if not self.is_running:
            self.start()

    def remove_client(self, sid):
        leave_room(self.room, sid=sid)
        # todo stop if empty

    def _capture_audio(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16') as stream:
                while self.is_running:
                    data, _ = stream.read(self.chunk_size)
                    try:
                        self.q.put(data.tobytes())
                    except queue.Full:
                        pass
        except Exception as e:
            print(f'[AudioStreamer] Error: {e}')

    def _stream_audio(self):
        while self.is_running:
            try:
                data = self.q.get(timeout=0.1)
                sio.emit('audio_chunk', data, to=self.room)
            except queue.Empty:
                continue  # check self.is_running again
            except Exception as e:
                print(f"[SocketIO Emit Error] {e}")
            sio.sleep(0)