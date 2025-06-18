from flask import Flask, Response, stream_with_context, render_template
from camera.camera import Camera
import atexit
import time

app = Flask(__name__)
camera = Camera("/dev/video0")

# Ensure the camera is released on app exit
atexit.register(camera.release)


@app.route('/video')
def video_feed():
    """
    Video streaming route.
    """
    return Response(
        stream_with_context(camera.generate_frames()),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/snapshot')
def snapshot():
    """
    Snapshot route to get a single frame.
    """
    frame = camera.get_frame()
    if frame:
        return Response(response=frame, mimetype='image/jpeg')
    else:
        return Response("Camera frame not available.", status=404)


@app.route('/')
def index():
    """
        Home page with live video and snapshot viewer.
        """
    return render_template("index.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
