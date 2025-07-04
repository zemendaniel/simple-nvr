import sounddevice as sd
import queue
import threading
import time


class LiveAudioStream:
    def __init__(self,
                 rate=44100,
                 channels=2,
                 bits_per_sample=16,
                 chunk=1024,
                 max_queue_size=10):
        self.rate = rate
        self.channels = channels
        self.bits_per_sample = bits_per_sample
        self.chunk = chunk
        self.max_queue_size = max_queue_size

        self.q = queue.Queue(maxsize=max_queue_size)
        self.running = False
        self.stream = None

        self.wav_header = self._generate_wav_header()

    def _generate_wav_header(self):
        datasize = 2000 * 10**6  # large dummy size for streaming
        o = bytes("RIFF", 'ascii')
        o += (datasize + 36).to_bytes(4, 'little')
        o += bytes("WAVE", 'ascii')
        o += bytes("fmt ", 'ascii')
        o += (16).to_bytes(4, 'little')  # fmt chunk size
        o += (1).to_bytes(2, 'little')  # PCM format
        o += self.channels.to_bytes(2, 'little')
        o += self.rate.to_bytes(4, 'little')
        byte_rate = self.rate * self.channels * self.bits_per_sample // 8
        o += byte_rate.to_bytes(4, 'little')
        block_align = self.channels * self.bits_per_sample // 8
        o += block_align.to_bytes(2, 'little')
        o += self.bits_per_sample.to_bytes(2, 'little')
        o += bytes("data", 'ascii')
        o += datasize.to_bytes(4, 'little')
        return o

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"Sounddevice status: {status}")
        try:
            self.q.put(indata.copy(), block=False)
        except queue.Full:
            try:
                self.q.get_nowait()  # discard oldest
                self.q.put(indata.copy())
            except queue.Empty:
                pass

    def start(self):
        if self.running:
            return
        self.running = True
        self.stream = sd.InputStream(
            samplerate=self.rate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.chunk,
            callback=self._callback
        )
        self.stream.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def generate_audio_stream(self):
        """Generator for streaming in Flask response."""
        yield self.wav_header
        while self.running or not self.q.empty():
            try:
                data = self.q.get(timeout=1)
                yield data.tobytes()
            except queue.Empty:
                continue
