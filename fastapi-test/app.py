from flask import Flask, render_template, request, jsonify
from media import MediaCapture


app = Flask(__name__)

capture = MediaCapture('/dev/video0', 30, 1280, 720, 'hw:3,0')


@app.route("/")
def root():
    return render_template("index.html")


@app.post("/offer")
async def offer():
    params = request.json
    sdp, type_ = await capture.handle_offer(params)

    return jsonify({
        "sdp": sdp,
        "type": type_
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)
