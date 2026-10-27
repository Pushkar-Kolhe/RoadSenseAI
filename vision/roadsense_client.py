"""Small helper that sends detections / sensor events to the Flask backend."""
import base64
from datetime import datetime, timezone

import cv2
import requests

BACKEND = "http://127.0.0.1:5000"


def utc_now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def encode_jpg(image_bgr, quality=85):
    ok, buf = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("could not encode image")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def send_detection(image_bgr, confidence, area_ratio, lat=None, lon=None,
                   source="real", timestamp=None, backend=BACKEND):
    payload = {
        "defect_type": "pothole",
        "confidence": round(float(confidence), 3),
        "area_ratio": round(float(area_ratio), 4),
        "timestamp": timestamp or utc_now_iso(),
        "source": source,
        "image_base64": encode_jpg(image_bgr),
    }
    if lat is not None and lon is not None:
        payload["latitude"], payload["longitude"] = lat, lon
    r = requests.post(f"{backend}/api/detections", json=payload, timeout=10)
    return r.status_code, r.json()


def send_sensor_event(peak_g, lat=None, lon=None, source="real", timestamp=None, backend=BACKEND):
    payload = {"peak_g": peak_g, "source": source, "timestamp": timestamp or utc_now_iso()}
    if lat is not None and lon is not None:
        payload["latitude"], payload["longitude"] = lat, lon
    r = requests.post(f"{backend}/api/sensor-events", json=payload, timeout=10)
    return r.status_code, r.json()
