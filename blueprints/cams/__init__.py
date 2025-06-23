from flask import Blueprint

bp = Blueprint('cams', __name__)

from blueprints.cams import routes
