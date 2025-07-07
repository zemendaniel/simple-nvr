from flask import Blueprint
from audio.streamer import AudioStreamer

bp = Blueprint('audio', __name__)
streamer = AudioStreamer()

from blueprints.audio import routes
