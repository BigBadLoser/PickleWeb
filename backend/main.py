from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from vision import detect_ball, get_stats, sample_pixel
import cv2
import asyncio
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, sdp
from aiortc.contrib.media import MediaBlackhole, MediaPlayer
import json
import numpy as np
import subprocess
from av import VideoFrame
import time
import io


import pigpio

app = FastAPI()
pi = pigpio.pi()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⬅️ allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def safe_and_direction(a, b):
    if a not in sdp.DIRECTIONS or b not in sdp.DIRECTIONS:
        print(f"[WARN] Invalid direction values: a={a}, b={b} — defaulting to 'inactive'")
        return "inactive"  # or choose "recvonly" or "sendonly" as fallback
    return sdp.DIRECTIONS[sdp.DIRECTIONS.index(a) & sdp.DIRECTIONS.index(b)]

RTCPeerConnection.and_direction = safe_and_direction
class OpenCVStreamTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.proc = subprocess.Popen(
            [
                "libcamera-vid",
                "--codec", "mjpeg",
                "--width", "640",
                "--height", "480",
                "--framerate", "30",
                "-t", "0",
                "-o", "-"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        self.reader = io.BufferedReader(self.proc.stdout)
        self.buffer = b""

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        while True:
            chunk = self.reader.read1(4096)
            if not chunk:
                continue
            self.buffer += chunk
            start = self.buffer.find(b'\xff\xd8')  # JPEG start
            end = self.buffer.find(b'\xff\xd9')    # JPEG end

            if start != -1 and end != -1 and end > start:
                jpg = self.buffer[start:end + 2]
                self.buffer = self.buffer[end + 2:]

                frame_np = np.frombuffer(jpg, dtype=np.uint8)
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                frame = detect_ball(frame)

                cv2.putText(frame, time.strftime("%H:%M:%S"), (460, 470),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                app.state.last_frame = frame.copy()
                frame = VideoFrame.from_ndarray(frame, format="bgr24")
                frame.pts = pts
                frame.time_base = time_base
                return frame

    def close(self):
        if self.proc:
            print("[CLEANUP] Killing libcamera-vid subprocess")
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1)
            except Exception:
                self.proc.kill()
            self.proc = None
        if hasattr(self, "reader"):
            try:
                self.reader.close()
            except:
                pass




@app.post("/offer")
async def offer(request: Request):
    offer_json = await request.json()

    print("\n======= SDP OFFER RECEIVED =======")
    print(offer_json["sdp"])
    print("==================================\n")

    desc = RTCSessionDescription(sdp=offer_json["sdp"], type=offer_json["type"])

    pc = RTCPeerConnection()

    # Close old stream if needed
    if hasattr(app.state, "track") and app.state.track:
        print("🧹 Cleaning up previous stream...")
        app.state.track.close()
        app.state.track = None

    # Must match client's recvonly → so we sendonly
    track = OpenCVStreamTrack()
    app.state.track = track
    pc.addTransceiver(track, direction="sendonly")

    await pc.setRemoteDescription(desc)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            print("🔌 WebRTC disconnected — tearing down track")
            track.close()
            await pc.close()

    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


@app.get("/api/sample_pixel")
def sample_pixel_api(x: int = Query(...), y: int = Query(...)):
    if hasattr(app.state, "last_frame"):
        hsv = sample_pixel(app.state.last_frame, x, y)
        return {"h": hsv[0], "s": hsv[1], "v": hsv[2]}
    return {"error": "No frame available"}



    
@app.get("/api/ball_stats")
def stats():
    return get_stats()










ESC1_GPIO = 16
ESC2_GPIO = 12

@app.post("/set_throttle/")
def set_throttle(esc: int = Query(..., ge=1, le=2), value: int = Query(..., ge=0, le=2000)):
    gpio = ESC1_GPIO if esc == 1 else ESC2_GPIO
    print(f"Setting ESC {esc} to {value}µs on GPIO {gpio}")
    pi.set_servo_pulsewidth(gpio, value)
    return {"esc": esc, "pulse": value}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)