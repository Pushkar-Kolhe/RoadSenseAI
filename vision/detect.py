"""Run the YOLOv8 pothole model on an image, a folder, a video, or the webcam.

Run from the RoadSense_AI folder with (.venv) active. Examples:
  python vision/detect.py --source test_images                  # just detect, save pictures
  python vision/detect.py --source test_images --send --spread  # also send to dashboard (fake GPS spread)
  python vision/detect.py --source 0 --send --lat 18.515 --lon 73.78   # webcam, fixed manual location
  python vision/detect.py --source road.mp4 --send --lat 18.515 --lon 73.78

Needs models/best.pt (your trained weights).
No GPS hardware yet: --lat/--lon is a MANUAL location. --spread makes a FAKE route, and such
data is tagged "simulated" on the dashboard.
"""
import argparse
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from roadsense_client import send_detection  # noqa: E402

OUT_DIR = ROOT / "outputs" / "detections"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ROUTE_START = (18.5120, 73.7790)   # sample points near Bavdhan, Pune (not real defect locations)
ROUTE_END = (18.5200, 73.7900)


def notify(msg):
    try:
        from plyer import notification
        notification.notify(title="RoadSense AI", message=msg, timeout=4)
    except Exception:
        pass
    print("NOTIFY:", msg)


def process_frame(model, frame, args, last_sent, lat=None, lon=None, source="real"):
    """Detect, draw boxes, optionally send the best detection (with cooldown)."""
    result = model.predict(frame, conf=args.conf, verbose=False)[0]
    annotated = result.plot()          # image with boxes + confidence drawn
    h, w = frame.shape[:2]
    best = None
    for box in result.boxes:
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        area_ratio = (x2 - x1) * (y2 - y1) / (w * h)
        if best is None or conf > best[0]:
            best = (conf, area_ratio)
    if best and args.send and time.time() - last_sent[0] >= args.cooldown:
        try:
            status, body = send_detection(annotated, best[0], best[1], lat, lon,
                                          source=source, backend=args.backend)
            print(f"  sent -> HTTP {status} {body}")
            last_sent[0] = time.time()
            if status == 201:
                notify(f"New {body.get('severity')} pothole recorded (id {body.get('id')})")
        except Exception as e:
            print("  could not reach backend (is backend/app.py running?):", e)
    return annotated, len(result.boxes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="image, folder, video file, or webcam index like 0")
    ap.add_argument("--weights", default=str(ROOT / "models" / "best.pt"))
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--send", action="store_true", help="send detections to the Flask backend")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--spread", action="store_true",
                    help="folder mode: give each image a different FAKE location (tagged simulated)")
    ap.add_argument("--cooldown", type=float, default=5.0,
                    help="webcam/video: min seconds between sends (stops duplicate records)")
    ap.add_argument("--backend", default="http://127.0.0.1:5000")
    args = ap.parse_args()

    from ultralytics import YOLO
    if not Path(args.weights).exists():
        sys.exit(f"Weights not found: {args.weights}\nTrain first, then copy best.pt into the models folder.")
    model = YOLO(args.weights)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    src = Path(args.source)
    if src.is_dir() or src.suffix.lower() in IMG_EXT:
        files = sorted(p for p in ([src] if src.is_file() else src.iterdir()) if p.suffix.lower() in IMG_EXT)
        found = 0
        for i, p in enumerate(files):
            frame = cv2.imread(str(p))
            if frame is None:
                continue
            lat, lon, source = args.lat, args.lon, "real"
            if args.spread:
                t = i / max(len(files) - 1, 1)
                lat = ROUTE_START[0] + (ROUTE_END[0] - ROUTE_START[0]) * t
                lon = ROUTE_START[1] + (ROUTE_END[1] - ROUTE_START[1]) * t
                source = "simulated"
            annotated, n = process_frame(model, frame, args, [0.0], lat, lon, source)
            cv2.imwrite(str(OUT_DIR / f"det_{p.name}"), annotated)
            found += n > 0
            print(f"{p.name}: {n} pothole(s) -> outputs/detections/det_{p.name}")
        print(f"Done. Potholes found in {found} of {len(files)} images.")
        return

    cap = cv2.VideoCapture(int(args.source) if args.source.isdigit() else args.source)
    if not cap.isOpened():
        sys.exit("Could not open video/webcam source.")
    print("Press q in the video window to quit.")
    last_sent = [0.0]
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        annotated, _ = process_frame(model, frame, args, last_sent, args.lat, args.lon, "real")
        cv2.imshow("RoadSense AI", annotated)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()