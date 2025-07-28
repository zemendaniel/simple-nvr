let pc = null;


function negotiate() {
    pc.addTransceiver('video', { direction: 'recvonly' });
    // pc.addTransceiver('audio', { direction: 'sendrecv' });
    console.log("Creating offer...");
    return pc.createOffer().then((offer) => {
        console.log("Setting local description...");
        return pc.setLocalDescription(offer);
    }).then(() => {
        console.log("Waiting for ICE gathering to complete...");
        return new Promise((resolve) => {
            if (pc.iceGatheringState === 'complete') {
                resolve();
            } else {
                const checkState = () => {
                    if (pc.iceGatheringState === 'complete') {
                        pc.removeEventListener('icegatheringstatechange', checkState);
                        resolve();
                    }
                };
                pc.addEventListener('icegatheringstatechange', checkState);
            }
        });
    }).then(() => {
        console.log("Sending offer to server...");
        var offer = pc.localDescription;
        return fetch('/offer', {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then((response) => {
        console.log("Received answer from server");
        return response.json();
    }).then((answer) => {
        console.log("Setting remote description...");
        return pc.setRemoteDescription(answer);
    }).catch((e) => {
        console.error("Negotiation failed:", e);
        alert(e);
    });
}

function start() {
    var config = {
        sdpSemantics: 'unified-plan',
        iceServers: [{
            urls: ['turn:10.21.40.25:3478'],  // Your TURN server IP and port
            username: 'turnuser',             // Your TURN username
            credential: 'turnpassword'        // Your TURN password
        }]
    };

    pc = new RTCPeerConnection(config);

    // connect audio / video
    pc.addEventListener('track', (evt) => {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0];
        } else {
            document.getElementById('audio').srcObject = evt.streams[0];
        }
    });

    navigator.mediaDevices.getUserMedia({ audio: true, video: false }).then((stream) => {
        stream.getTracks().forEach((track) => {
            pc.addTrack(track, stream);
        });

        negotiate();
    }).catch((err) => {
        console.error("getUserMedia error:", err);
    });
}

function stop() {

    // close peer connection
    setTimeout(() => {
        pc.close();
    }, 500);

    fetch("/stop", {
          method: "POST"
        }).then(response => {
          if (response.ok) {
            console.log("Server shutdown requested");
          } else {
            console.error("Shutdown request failed");
          }
        });
}
