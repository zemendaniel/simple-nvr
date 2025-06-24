from cameras.camera import Camera
from threading import Lock
from persistence.model.cam import Cam
from persistence import db


class CameraManager:
    _instance = None

    def __init__(self):
        if CameraManager._instance is not None:
            raise Exception("CameraManager instance already exists. Use get_instance().")
        self.cameras = []
        self.lock = Lock()
        CameraManager._instance = self

    @classmethod
    def get_instance(cls):
        return cls._instance

    def start_all_from_db(self):
        with db.Session() as session:
            camera_configs = session.scalars(Cam.select().where(Cam.enabled == True).order_by(Cam.id)).all()

        with self.lock:
            for config in camera_configs:
                print(f"[INFO] Starting camera: {config.name}")
                self.cameras.append(Camera(
                    config.id, config.url, config.fps, config.width, config.height,
                    config.sensitivity, config.name, config.notifications_enabled
                ))

    def get_camera(self, camera_id):
        with self.lock:
            for cam in self.cameras:
                if cam.id == camera_id:
                    return cam
        return None

    def stop_all(self):
        with self.lock:
            for cam in self.cameras:
                cam.release()
            self.cameras.clear()

    def reload_cameras(self):
        self.stop_all()
        self.start_all_from_db()
