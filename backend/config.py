"""Central settings. Edit values here, not all over the code."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "database" / "roadsense.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
EVIDENCE_DIR = ROOT / "outputs" / "evidence"
FRONTEND_DIR = ROOT / "frontend"

DUPLICATE_RADIUS_M = 15      # detections closer than this = same pothole
SENSOR_MATCH_SECONDS = 3     # sensor spike within +/- this many seconds supports a detection
MIN_CONFIDENCE = 0.25        # server rejects anything below this
