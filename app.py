import eventlet
eventlet.monkey_patch()
from flask import Flask
import atexit
from cameras.manager import CameraManager
from config import Config
import persistence
import security
from flask_wtf.csrf import CSRFProtect
from flask_minify import Minify
import blueprints.cams
import blueprints.pages
import blueprints.security
import blueprints.clips
import blueprints.audio
import os
from extensions import sio


csrf = CSRFProtect()
minify = Minify(html=True, js=True, cssless=True)


def create_app(config_class=Config):
    app = Flask(__name__)
    sio.init_app(app)
    app.config.from_object(config_class)
    persistence.init_app(app)
    security.init_app(app)
    csrf.init_app(app)
    minify.init_app(app)
    camera_manager = CameraManager()
    atexit.register(camera_manager.stop_all)

    if os.path.exists("INSTALLED"):
        camera_manager.start_all_from_db()

    app.register_blueprint(blueprints.cams.bp, url_prefix='/cams')
    app.register_blueprint(blueprints.pages.bp, url_prefix='/')
    app.register_blueprint(blueprints.security.bp, url_prefix='/')
    app.register_blueprint(blueprints.clips.bp, url_prefix='/clips')

    return app


app = create_app()


if __name__ == '__main__':
    sio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
