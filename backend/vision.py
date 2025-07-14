import cv2
import numpy as np
import time
from collections import deque

BALL_DIAMETER_M = 0.074  # 74mm
FOCAL_LENGTH_PX = 700    # Adjust via calibration

positions = deque(maxlen=10)
last_speed = 0
last_angle = 0

def detect_ball(frame):
    global last_speed, last_angle

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = (35, 100, 50)
    upper = (50, 255, 150)
    mask = cv2.inRange(hsv, lower, upper)  # Orange ball HSV range
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center = None

    if contours:
        c = max(contours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)

        if radius > 5:
            center = (int(x), int(y))
            positions.append((time.time(), x, y))

            # Draw overlay
            cv2.circle(frame, center, int(radius), (0, 255, 0), 2)
            cv2.putText(frame, f"{last_speed:.1f} m/s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(frame, f"{last_angle:.1f} deg", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

    if len(positions) >= 2:
        t0, x0, y0 = positions[0]
        t1, x1, y1 = positions[-1]
        dt = t1 - t0
        dx, dy = x1 - x0, y0 - y1  # screen y is inverted
        dist_px = np.sqrt(dx**2 + dy**2)
        speed = dist_px / dt if dt > 0 else 0
        angle = np.degrees(np.arctan2(dy, dx))
        last_speed = pixel_to_meters(speed)
        last_angle = angle

    return frame

def pixel_to_meters(px_speed):
    px_ball = np.mean([np.linalg.norm([x2 - x1, y2 - y1]) for (_, x1, y1), (_, x2, y2) in zip(positions, list(positions)[1:])])
    if px_ball == 0: return 0
    px_per_meter = px_ball / BALL_DIAMETER_M
    return px_speed / px_per_meter

def get_stats():
    return {'speed_mps': round(last_speed, 2), 'angle_deg': round(last_angle, 2)}

last_sampled_hsv = (0, 0, 0)

def sample_pixel(frame, x, y):
    global last_sampled_hsv
    pixel = frame[y, x]  # BGR
    hsv_pixel = cv2.cvtColor(np.uint8([[pixel]]), cv2.COLOR_BGR2HSV)[0][0]
    last_sampled_hsv = tuple(int(v) for v in hsv_pixel)
    print("[HSV] Sampled:", last_sampled_hsv)
    return last_sampled_hsv

def get_last_sampled_hsv():
    return last_sampled_hsv
