from flask import Blueprint

bp = Blueprint('security', __name__)

from blueprints.security import routes
