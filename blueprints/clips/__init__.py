from flask import Blueprint

bp = Blueprint('clips', __name__)

from blueprints.clips import routes
