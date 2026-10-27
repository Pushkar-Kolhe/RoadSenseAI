"""All database code lives here (SQLite)."""
import math
import sqlite3
from datetime import datetime, timedelta

from config import DB_PATH, SCHEMA_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_duplicate(conn, lat, lon, radius_m):
    """Nearest not-yet-repaired defect within radius_m, or None."""
    if lat is None or lon is None:
        return None
    rows = conn.execute("SELECT * FROM defects WHERE status != 'Repaired' AND latitude IS NOT NULL").fetchall()
    best, best_d = None, radius_m
    for r in rows:
        d = haversine_m(lat, lon, r["latitude"], r["longitude"])
        if d <= best_d:
            best, best_d = r, d
    return best


def find_sensor_event(conn, when_iso, window_s, lat=None, lon=None, max_dist_m=50):
    """Strongest IMU spike within +/- window_s seconds (and within max_dist_m if both have GPS)."""
    t = datetime.fromisoformat(when_iso)
    lo = (t - timedelta(seconds=window_s)).isoformat()
    hi = (t + timedelta(seconds=window_s)).isoformat()
    rows = conn.execute(
        "SELECT * FROM sensor_events WHERE event_time BETWEEN ? AND ? ORDER BY peak_g DESC",
        (lo, hi),
    ).fetchall()
    for r in rows:
        if lat is not None and r["latitude"] is not None:
            if haversine_m(lat, lon, r["latitude"], r["longitude"]) > max_dist_m:
                continue
        return r
    return None


def insert_defect(conn, d):
    cur = conn.execute(
        """INSERT INTO defects (defect_type, latitude, longitude, severity, severity_score,
           confidence, detected_at, last_seen_at, evidence_path, vibration_g, verification, source)
           VALUES (:defect_type,:latitude,:longitude,:severity,:severity_score,
           :confidence,:detected_at,:last_seen_at,:evidence_path,:vibration_g,:verification,:source)""",
        d,
    )
    return cur.lastrowid


def insert_sensor_event(conn, e):
    cur = conn.execute(
        "INSERT INTO sensor_events (event_time, latitude, longitude, peak_g, source) VALUES (?,?,?,?,?)",
        (e["event_time"], e["latitude"], e["longitude"], e["peak_g"], e["source"]),
    )
    return cur.lastrowid


def list_defects(conn, severity=None, status=None, source=None, sort="newest"):
    sql, args = "SELECT * FROM defects WHERE 1=1", []
    for col, val in (("severity", severity), ("status", status), ("source", source)):
        if val:
            sql += f" AND {col} = ?"
            args.append(val)
    order = {
        "newest": "detected_at DESC",
        "oldest": "detected_at ASC",
        "severity": "severity_score DESC",
        "seen": "detection_count DESC",
    }.get(sort, "detected_at DESC")
    return [dict(r) for r in conn.execute(sql + " ORDER BY " + order, args).fetchall()]


def stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM defects").fetchone()[0]
    by_sev = {r[0]: r[1] for r in conn.execute("SELECT severity, COUNT(*) FROM defects GROUP BY severity")}
    by_status = {r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM defects GROUP BY status")}
    return {"total": total, "by_severity": by_sev, "by_status": by_status}
