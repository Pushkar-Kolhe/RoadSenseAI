"""Demo without any hardware or model: sends FAKE potholes along a Pune road.
Everything it sends is tagged source="simulated" and the dashboard shows a SIMULATED badge.

Run (backend must be running):  python simulate/simulate_detections.py
"""
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vision"))
from roadsense_client import send_detection, send_sensor_event  # noqa: E402

# Straight-ish route near Bavdhan, Pune (sample coordinates, not real defect locations)
START = (18.5120, 73.7790)
END = (18.5200, 73.7900)


def fake_road_image(w=640, h=360):
    img = np.full((h, w, 3), 90, np.uint8)
    cv2.rectangle(img, (0, h // 2), (w, h), (60, 60, 60), -1)
    cx, cy = random.randint(200, 440), random.randint(220, 300)
    ax, ay = random.randint(15, 110), random.randint(8, 55)
    cv2.ellipse(img, (cx, cy), (ax, ay), 0, 0, 360, (25, 25, 25), -1)
    box = (cx - ax, cy - ay, cx + ax, cy + ay)
    cv2.rectangle(img, box[:2], box[2:], (0, 255, 0), 2)
    cv2.putText(img, "SIMULATED IMAGE", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    area_ratio = (box[2] - box[0]) * (box[3] - box[1]) / (w * h)
    return img, area_ratio


def main(n=12):
    random.seed(7)
    for i in range(n):
        t = i / (n - 1)
        lat = START[0] + (END[0] - START[0]) * t + random.uniform(-0.0002, 0.0002)
        lon = START[1] + (END[1] - START[1]) * t + random.uniform(-0.0002, 0.0002)
        img, area = fake_road_image()
        conf = random.uniform(0.45, 0.95)
        # every other pothole also has a (simulated) IMU spike at the same moment
        if i % 2 == 0:
            send_sensor_event(random.uniform(0.8, 2.0), lat, lon, source="simulated")
        status, body = send_detection(img, conf, area, lat, lon, source="simulated")
        print(f"[{i+1}/{n}] HTTP {status} {body}")
        time.sleep(0.3)
    # send one near-duplicate to demonstrate duplicate merging
    img, area = fake_road_image()
    status, body = send_detection(img, 0.9, area, lat, lon, source="simulated")
    print("duplicate test:", status, body)


if __name__ == "__main__":
    main()
