from flask import Blueprint

bp = Blueprint('audio', __name__)

from blueprints.audio import routes
