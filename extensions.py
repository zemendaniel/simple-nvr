from flask_socketio import SocketIO
from flask import request

sio = SocketIO()


@sio.on('disconnect')
def disconnect():
    from blueprints.audio import streamer
    streamer.remove_client(request.sid)
