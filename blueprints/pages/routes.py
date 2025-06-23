from flask import redirect, url_for
from blueprints.pages import bp


@bp.route('/')
def home():
    return redirect(url_for('cams.list_all'))
