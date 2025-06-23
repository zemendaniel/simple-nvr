import cv2
import threading
import time
import os
import subprocess
import shutil
from collections import deque
from discord.discord import send_message
from datetime import datetime


class Camera:
    def __init__(self, cam_id, url, fps, width, height, sensitivity, folder, name, notifications_enabled):
        if "/dev/video" in url:
            Camera.kill_video_processes(url)
            subprocess.run(["v4l2-ctl", "-d", url, "-c", "auto_exposure=3"])

        self.url = url
        self.fps = fps
        self.sensitivity = sensitivity
        self.id = cam_id
        self.folder = folder
        self.width = width
        self.height = height
        self.name = name
        self.notifications_enabled = notifications_enabled

        self.fps_sleep = 1 / self.fps
        self.cap = cv2.VideoCapture(url)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        self.lock = threading.Lock()
        self.latest_frame = b''

        self.running = True
        self.prev_gray = None

        self.motion_detected = False
        self.buffer_duration = 5
        self.frame_buffer = deque(maxlen=self.fps * 5)  # 5 sec at most
        self.recording_start_timestamp = None

        self.is_recording = False
        self.video_writer = None
        self.recording_lock = threading.Lock()
        self.post_motion_end_time = None

        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(self.fps_sleep)
                continue

            # frame = cv2.resize(frame, (640, 360))
            self.motion_detected = self._detect_motion(frame)

            current_time = time.time()

            # Save recent frames for pre-motion buffer
            with self.lock:
                self.frame_buffer.append(frame.copy())

            # Update latest JPEG-encoded frame
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                with self.lock:
                    self.latest_frame = jpeg.tobytes()

            if self.motion_detected:
                print("[INFO] Motion detected.")
                if not self.is_recording:
                    self.recording_start_timestamp = time.strftime("%H:%M:%S")
                    self._start_recording(frame)
                self.post_motion_end_time = current_time + 5

            if self.is_recording:
                with self.recording_lock:
                    if self.video_writer:
                        self.video_writer.write(frame)
                if current_time >= self.post_motion_end_time:
                    self._stop_recording()
                    if self.notifications_enabled:
                        send_message(f"Motion detected on camera **{self.name}** at {self.recording_start_timestamp}. Recording saved.")

            time.sleep(self.fps_sleep)

    def _detect_motion(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_gray is None:
            self.prev_gray = gray
            return False

        diff = cv2.absdiff(self.prev_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        motion_level = cv2.countNonZero(thresh)

        self.prev_gray = gray
        return motion_level > self.sensitivity

    def _start_recording(self, frame):
        filename = f"{self.folder}/cam_{self.id}_clip{self.recording_start_timestamp}.mp4"
        height, width = frame.shape[:2]
        self.video_writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), self.fps, (width, height))
        self.is_recording = True

        # Write pre-motion buffer to file
        with self.lock:
            for frame in self.frame_buffer:
                self.video_writer.write(frame)

        print(f"[INFO] Recording started: {filename}")

    def _stop_recording(self):
        with self.recording_lock:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
        self.is_recording = False
        print("[INFO] Recording stopped.")

    def get_frame(self):
        with self.lock:
            return self.latest_frame

    def generate_frames(self):
        try:
            while self.running:
                frame = self.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    time.sleep(0.1)
        except GeneratorExit:
            print("Video watch stream stopped.")
        finally:
            print("Frame generator exited.")

    def release(self):
        self.running = False
        self.thread.join(timeout=1)
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()
        with self.recording_lock:
            if self.video_writer:
                self.video_writer.release()

    @staticmethod
    def kill_video_processes(url):
        if not shutil.which("fuser"):
            print("'fuser' command not found. Install it (e.g., `sudo apt install psmisc`).")
            return

        try:
            result = subprocess.run(["fuser", url],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True)
            if result.returncode != 0 or not result.stdout.strip():
                return

            for pid in result.stdout.strip().split():
                try:
                    subprocess.run(["kill", "-9", pid], check=True)
                    print(f"Killed process using {url}: PID {pid}")
                except subprocess.CalledProcessError:
                    print(f"Failed to kill PID {pid}")

        except Exception as e:
            print(f"Error killing video processes: {e}")
