import secrets
import cv2
import threading
import time
import subprocess
import shutil
from collections import deque
from discord.discord import send_message
from persistence import db
from persistence.model.app_config import AppConfig
import os


class Camera:
    def __init__(self, cam_id, url, fps, width, height, sensitivity, name, notifications_enabled):
        if "/dev/video" in url:
            Camera.kill_video_processes(url)
            subprocess.run(["v4l2-ctl", "-d", url, "-c", "auto_exposure=3"])

        self.url = url
        self.fps = fps
        self.sensitivity = sensitivity
        self.id = cam_id
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
        self.recording_lock = threading.Lock()
        self.post_motion_end_time = None
        self.ffmpeg_process = None

        self.startup_time = time.time()

        with db.Session() as s:
            self.app_conf = s.get(AppConfig, 1)

        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            current_time = time.time()

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(self.fps_sleep)
                continue

            # Update latest JPEG-encoded frame
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                with self.lock:
                    self.latest_frame = jpeg.tobytes()

            if self.sensitivity != 0:
                if current_time - self.startup_time > 10:
                    self.motion_detected = self._detect_motion(frame)
                else:
                    self.motion_detected = False

                # Save recent frames for pre-motion buffer
                with self.lock:
                    self.frame_buffer.append(frame.copy())

                if self.motion_detected:
                    print("[INFO] Motion detected.")
                    if not self.is_recording:
                        self.recording_start_timestamp = time.strftime("%H_%M_%S")
                        self._start_recording(frame)
                    self.post_motion_end_time = current_time + 5

                if self.is_recording:
                    with self.recording_lock:
                        if self.ffmpeg_process and self.ffmpeg_process.stdin:
                            try:
                                self.ffmpeg_process.stdin.write(frame.tobytes())
                            except BrokenPipeError:
                                print("[ERROR] FFmpeg pipe closed unexpectedly.")
                    if current_time >= self.post_motion_end_time:
                        self._stop_recording()
                        if self.notifications_enabled and self.app_conf.notifications_enabled and self.app_conf.discord_webhook:
                            send_message(f"Motion detected on camera **{self.name}** at {self.recording_start_timestamp}. Recording saved.",
                                         self.app_conf.discord_webhook)

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
        recording_filename = f"{self.app_conf.root_folder}/cams/{self.id}/{self.recording_start_timestamp}_{secrets.token_hex(4)}.mp4"
        height, width = frame.shape[:2]

        # Start FFmpeg process
        self.ffmpeg_process = subprocess.Popen([
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(self.fps),
            '-i', '-',  # Input from stdin
            '-an',  # No audio
            '-vcodec', 'libx264',
            '-preset', 'veryfast',
            '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p',
            recording_filename
        ], stdin=subprocess.PIPE)

        self.is_recording = True

        # Write pre-buffered frames
        with self.lock:
            for buffered_frame in self.frame_buffer:
                self.ffmpeg_process.stdin.write(buffered_frame.tobytes())

        print(f"[INFO] Recording started: {recording_filename}")

    def _stop_recording(self):
        with self.recording_lock:
            if self.ffmpeg_process:
                try:
                    self.ffmpeg_process.stdin.close()
                    self.ffmpeg_process.wait()
                except Exception as e:
                    print(f"[ERROR] Error closing FFmpeg: {e}")
                self.ffmpeg_process = None

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
                    time.sleep(self.fps_sleep)
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
