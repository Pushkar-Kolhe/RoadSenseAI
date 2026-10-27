"""RoadSense AI - Flask backend.

Run:  python backend/app.py      then open http://127.0.0.1:5000
"""
import base64
import binascii
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

import db
from config import (DUPLICATE_RADIUS_M, EVIDENCE_DIR, FRONTEND_DIR, ROOT,
                    MIN_CONFIDENCE, SENSOR_MATCH_SECONDS)
from severity import estimate_severity

app = Flask(__name__, static_folder=None)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
db.init_db()

STATUSES = {"Reported", "In Progress", "Repaired"}


def now_iso():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def parse_time(value):
    """Accept ISO 8601 text; store as naive UTC. Missing value = now."""
    if not value:
        return now_iso()
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds")


def parse_coords(data):
    lat, lon = data.get("latitude"), data.get("longitude")
    if lat is None and lon is None:
        return None, None
    lat, lon = float(lat), float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("latitude/longitude out of range")
    return lat, lon


def save_evidence(b64):
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64.split(",")[-1], validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("image_base64 is not valid base64")
    if len(raw) > 5_000_000:
        raise ValueError("image too large (max 5 MB)")
    name = f"defect_{uuid.uuid4().hex[:12]}.jpg"
    (EVIDENCE_DIR / name).write_bytes(raw)
    return name


# ---------- pages & files ----------
@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/static/<path:name>")
def frontend_files(name):
    static_dir = ROOT / "static"
    if (static_dir / name).is_file():
        return send_from_directory(static_dir, name)
    return send_from_directory(FRONTEND_DIR, name)


@app.get("/evidence/<path:name>")
def evidence(name):
    return send_from_directory(EVIDENCE_DIR, name)


# ---------- API ----------
@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/detections")
def post_detection():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send JSON body"), 400
    try:
        confidence = float(data["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if confidence < MIN_CONFIDENCE:
            return jsonify(error=f"confidence below {MIN_CONFIDENCE}, ignored"), 422
        area_ratio = float(data.get("area_ratio", 0.02))
        lat, lon = parse_coords(data)
        detected_at = parse_time(data.get("timestamp"))
        source = data.get("source", "real")
        if source not in ("real", "simulated"):
            raise ValueError("source must be 'real' or 'simulated'")
        defect_type = str(data.get("defect_type", "pothole"))[:40]
        evidence_name = save_evidence(data.get("image_base64"))
    except KeyError as e:
        return jsonify(error=f"missing field: {e.args[0]}"), 400
    except (ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400

    with db.get_conn() as conn:
        # Sensor support: IMU spike close in time?
        ev = db.find_sensor_event(conn, detected_at, SENSOR_MATCH_SECONDS, lat, lon)
        vib = ev["peak_g"] if ev else None
        verification = "vision+sensor" if ev else "vision_only"
        label, score = estimate_severity(confidence, area_ratio, vib)

        dup = db.find_duplicate(conn, lat, lon, DUPLICATE_RADIUS_M)
        if dup:
            better = score > (dup["severity_score"] or 0)
            conn.execute(
                """UPDATE defects SET last_seen_at=?, detection_count=detection_count+1,
                   confidence=MAX(confidence,?),
                   severity=CASE WHEN ? THEN ? ELSE severity END,
                   severity_score=CASE WHEN ? THEN ? ELSE severity_score END,
                   evidence_path=CASE WHEN ? THEN COALESCE(?, evidence_path) ELSE evidence_path END,
                   vibration_g=COALESCE(MAX(vibration_g,?), vibration_g, ?),
                   verification=CASE WHEN ? THEN 'vision+sensor' ELSE verification END
                   WHERE id=?""",
                (detected_at, confidence, better, label, better, score, better, evidence_name,
                 vib, vib, ev is not None, dup["id"]),
            )
            return jsonify(id=dup["id"], merged=True, message="Duplicate of existing defect"), 200

        new_id = db.insert_defect(conn, dict(
            defect_type=defect_type, latitude=lat, longitude=lon, severity=label,
            severity_score=score, confidence=confidence, detected_at=detected_at,
            last_seen_at=detected_at, evidence_path=evidence_name, vibration_g=vib,
            verification=verification, source=source))
    return jsonify(id=new_id, merged=False, severity=label, verification=verification), 201


@app.post("/api/sensor-events")
def post_sensor_event():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Send JSON body"), 400
    try:
        peak_g = float(data["peak_g"])
        if peak_g < 0 or peak_g > 50:
            raise ValueError("peak_g out of range")
        lat, lon = parse_coords(data)
        source = data.get("source", "real")
        if source not in ("real", "simulated"):
            raise ValueError("source must be 'real' or 'simulated'")
        event = dict(event_time=parse_time(data.get("timestamp")), latitude=lat,
                     longitude=lon, peak_g=peak_g, source=source)
    except KeyError as e:
        return jsonify(error=f"missing field: {e.args[0]}"), 400
    except (ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400
    with db.get_conn() as conn:
        new_id = db.insert_sensor_event(conn, event)
    return jsonify(id=new_id), 201


@app.get("/api/defects")
def get_defects():
    with db.get_conn() as conn:
        rows = db.list_defects(
            conn,
            severity=request.args.get("severity"),
            status=request.args.get("status"),
            source=request.args.get("source"),
            sort=request.args.get("sort", "newest"),
        )
    for r in rows:
        r["evidence_url"] = f"/evidence/{r['evidence_path']}" if r["evidence_path"] else None
    return jsonify(rows)


@app.patch("/api/defects/<int:defect_id>")
def update_defect(defect_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in STATUSES:
        return jsonify(error=f"status must be one of {sorted(STATUSES)}"), 400
    with db.get_conn() as conn:
        cur = conn.execute("UPDATE defects SET status=? WHERE id=?", (status, defect_id))
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return jsonify(id=defect_id, status=status)


@app.get("/api/stats")
def get_stats():
    with db.get_conn() as conn:
        return jsonify(db.stats(conn))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
