import pyaudio
import threading
import queue


class LiveAudioStream:
    def __init__(self,
                 rate=44100,
                 channels=1,
                 bits_per_sample=16,
                 chunk=256,
                 input_device_index=None,
                 max_queue_size=5):
        self.rate = rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.chunk = chunk
        self.input_device_index = input_device_index
        self.format = pyaudio.paInt16

        self.audio_interface = pyaudio.PyAudio()
        self.stream = None

        self.running = False
        self.thread = None

        self.buffer = queue.Queue(maxsize=max_queue_size)  # thread-safe queue for audio chunks

        self.wav_header = self._generate_wav_header()

    def _generate_wav_header(self):
        datasize = 2000 * 10 ** 6  # large dummy size for live stream
        o = bytes("RIFF", 'ascii')
        o += (datasize + 36).to_bytes(4, 'little')
        o += bytes("WAVE", 'ascii')
        o += bytes("fmt ", 'ascii')
        o += (16).to_bytes(4, 'little')
        o += (1).to_bytes(2, 'little')
        o += self.channels.to_bytes(2, 'little')
        o += self.rate.to_bytes(4, 'little')
        o += (self.rate * self.channels * self.bits_per_sample // 8).to_bytes(4, 'little')
        o += (self.channels * self.bits_per_sample // 8).to_bytes(2, 'little')
        o += self.bits_per_sample.to_bytes(2, 'little')
        o += bytes("data", 'ascii')
        o += datasize.to_bytes(4, 'little')
        return o

    def _start_stream(self):
        if not self.stream:
            self.stream = self.audio_interface.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.input_device_index,
                frames_per_buffer=self.chunk
            )

    def _capture_loop(self):
        """Background thread: reads audio and pushes to queue."""
        self._start_stream()
        while self.running:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                # If buffer is full, discard oldest to keep latency low
                if self.buffer.full():
                    try:
                        self.buffer.get_nowait()
                    except queue.Empty:
                        pass
                self.buffer.put(data)
            except Exception as e:
                print("Audio capture error:", e)
                break
        self._stop_stream()

    def start(self):
        """Start background audio capturing thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop background capturing thread."""
        self.running = False
        if self.thread:
            self.thread.join()
            self.thread = None

    def _stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def terminate(self):
        """Stop thread, close stream and terminate PyAudio."""
        self.stop()
        self._stop_stream()
        self.audio_interface.terminate()

    def generate_audio_stream(self):
        """Generator used in Flask response — yields WAV header once, then audio from queue."""
        yield self.wav_header
        while self.running or not self.buffer.empty():
            try:
                chunk = self.buffer.get(timeout=1)  # wait max 1 second for chunk
                yield chunk
            except queue.Empty:
                # If no data available, just continue and wait
                continue

