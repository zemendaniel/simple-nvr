import socket
import sounddevice as sd

HOST = '0.0.0.0'
PORT = 12345
sample_rate = 44100
channels = 2
chunk_size = 1024  # frames per chunk

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print("Waiting for connection...")
    conn, addr = s.accept()
    print(f"Connected by {addr}")

    with conn:
        with sd.InputStream(samplerate=sample_rate, channels=channels, dtype='int16') as stream:
            while True:
                data, _ = stream.read(chunk_size)
                conn.sendall(data.tobytes())
