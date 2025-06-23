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
import os


# camera = Camera(1, "/dev/video0", 5, 1280, 720, 1000, "clips")
csrf = CSRFProtect()
minify = Minify(html=True, js=True, cssless=True)


def create_app(config_class=Config):
    app = Flask(__name__)
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

    return app


if __name__ == '__main__':
    create_app().run(host="0.0.0.0", port=5001, debug=False, threaded=True)
