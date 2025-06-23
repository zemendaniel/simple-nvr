import shutil

import cv2
import threading
import time
from collections import deque
import os
import subprocess


class Camera:
    def __init__(self, url):
        Camera.kill_video_processes(url)

        self.cap = cv2.VideoCapture(url)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 10)

        self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure mode
        self.cap.set(cv2.CAP_PROP_EXPOSURE, -6)  # Try -6, -5, or -4
        self.cap.set(cv2.CAP_PROP_GAIN, 50)
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, 200)

        self.lock = threading.Lock()
        self.prev_gray = None
        self.latest_frame = b''  # Holds latest JPEG frame bytes
        self.running = True

        self.motion_detected = False

        self.frame_buffer = deque()
        self.buffer_duration = 5  # seconds
        self.is_recording = False  # Are we currently in a recording session?
        self.record_start_time = None
        self.record_end_time = None
        self.post_motion_end_time = None  # When should we stop recording (if no new motion)?
        self.recording_frames = []  # Temp buffer to hold the full recording (pre + during motion)

        # Start background thread for motion detection and frame grabbing
        self.thread = threading.Thread(target=self._capture_loop)
        self.thread.daemon = True
        self.thread.start()

    def _capture_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            current_time = time.time()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if self.prev_gray is not None:
                diff = cv2.absdiff(self.prev_gray, gray)
                thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
                motion_level = cv2.countNonZero(thresh)
                self.motion_detected = motion_level > 1000  # adjust this if needed

            self.prev_gray = gray

            if self.motion_detected:
                print("Motion detected!")
                if not self.is_recording:
                    with self.lock:
                        self.recording_frames = list(self.frame_buffer)
                    self.is_recording = True
                    self.record_start_time = time.time()
                    print("[DEBUG] Started recording due to motion")

                self.post_motion_end_time = current_time + 5

            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                frame_time = current_time  # reuse from earlier in loop

                with self.lock:
                    self.latest_frame = jpeg.tobytes()
                    self.frame_buffer.append((frame_time, frame.copy()))

                    # Prune old frames if not recording
                    if not self.is_recording:
                        while self.frame_buffer and (frame_time - self.frame_buffer[0][0] > self.buffer_duration):
                            self.frame_buffer.popleft()

                    # If recording, append frame
                    if self.is_recording:
                        self.recording_frames.append((frame_time, frame.copy()))

                        if self.post_motion_end_time and frame_time >= self.post_motion_end_time:
                            self.record_end_time = current_time  # <-- record end time here
                            print("[DEBUG] Motion ended. Saving clip...")
                            self._save_clip(self.recording_frames, self.record_start_time, self.record_end_time)
                            self.recording_frames = []
                            self.is_recording = False
                            self.post_motion_end_time = None

            print(f"[DEBUG] Buffer size: {len(self.frame_buffer)} frames")
            if self.frame_buffer:
                oldest = time.strftime('%H:%M:%S', time.localtime(self.frame_buffer[0][0]))
                newest = time.strftime('%H:%M:%S', time.localtime(self.frame_buffer[-1][0]))
                print(f"[DEBUG] Frame timestamps: oldest={oldest}, newest={newest}")

            time.sleep(0.1)  # approx 10 FPS

    def get_frame(self):
        # with self.lock:
        #     return self.latest_frame
        return self.latest_frame

    def release(self):
        self.running = False
        self.thread.join(timeout=1)
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()

    def generate_frames(self):
        try:
            while True:
                frame = self.get_frame()
                if frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    time.sleep(0.1)
        except GeneratorExit:
            print("Video stream stopped.")
        finally:
            print("Frame generator exited.")

    @staticmethod
    def _save_clip(frames, start_time, end_time):
        if not frames:
            return

        duration = end_time - start_time
        if duration <= 0:
            duration = 1 / 10  # fallback to 10 FPS if duration zero or negative

        fps = len(frames) / duration
        print(f"[DEBUG] Saving clip at {fps:.2f} FPS")

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        folder = "clips"
        filename = f"{folder}/motion_clip_{timestamp}.mp4"

        height, width = frames[0][1].shape[:2]
        out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

        for _, frame in frames:
            out.write(frame)

        out.release()
        print(f"[DEBUG] Saved clip as {filename}")

    @staticmethod
    def kill_video_processes(url):
        if not shutil.which("fuser"):
            print("'fuser' command not found. Install it using your package manager (e.g., apt install psmisc).")
            return

        try:
            result = subprocess.run(
                ["fuser", url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0 or not result.stdout.strip():
                print(f"No process is using {url}.")
                return

            pids = result.stdout.strip().split()
            for pid in pids:
                try:
                    subprocess.run(["kill", "-9", pid], check=True)
                    print(f"Killed process using {url}: PID {pid}")
                except subprocess.CalledProcessError:
                    print(f"Failed to kill PID {pid}")

        except Exception as e:
            print(f"Exception while trying to kill processes using {url}: {e}")
