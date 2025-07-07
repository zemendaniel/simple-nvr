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
        self.stop_event = threading.Event()
        self.room = 'audio_listeners'  # Room name for clients

    def add_client(self, sid):
        # Add client to room
        join_room(self.room, sid=sid)
        # Start audio thread if not running
        if not self.thread or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._stream_audio, daemon=True)
            self.thread.start()
            print('[AudioStreamer] Audio thread started.')

    def remove_client(self, sid):
        # Remove client from room
        leave_room(self.room, sid=sid)
        # Check if room is empty, stop thread if no clients remain
        # Unfortunately, Flask-SocketIO does not provide a direct API
        # to check room size server-side, so you might want to
        # keep track of number of clients separately or ignore stopping.
        # For safety, you can just stop if you want to:
        # self.stop_event.set()
        pass

    def _stream_audio(self):
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=self.channels, dtype='int16') as stream:
                while not self.stop_event.is_set():
                    data, _ = stream.read(self.chunk_size)
                    # Emit audio chunk to the room
                    sio.emit('audio_chunk', data.tobytes(), room=self.room)
                    sio.sleep(0)
        except Exception as e:
            print(f'[AudioStreamer] Error: {e}')
