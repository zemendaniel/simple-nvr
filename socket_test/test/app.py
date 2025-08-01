import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import sounddevice as sd
import threading


app = Flask(__name__)
socketio = SocketIO(app)

sample_rate = 44100
channels = 2
chunk_size = 1024


def audio_stream_thread():
    with sd.InputStream(samplerate=sample_rate, channels=channels, dtype='int16') as stream:
        while True:
            data, _ = stream.read(chunk_size)
            # send raw PCM bytes to all connected clients
            socketio.emit('audio_chunk', data.tobytes())
            socketio.sleep(0)

# @socketio.on('connect')
# def on_connect():
#     print('Client connected')
#
# @socketio.on('disconnect')
# def on_disconnect():
#     print('Client disconnected')


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    threading.Thread(target=audio_stream_thread, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
