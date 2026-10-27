CREATE TABLE IF NOT EXISTS defects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_type     TEXT    NOT NULL DEFAULT 'pothole',
    latitude        REAL,                       -- NULL if no GPS (e.g. webcam only)
    longitude       REAL,
    severity        TEXT    NOT NULL CHECK (severity IN ('Low','Medium','High')),
    severity_score  REAL,
    confidence      REAL    NOT NULL,
    detected_at     TEXT    NOT NULL,           -- ISO 8601 UTC, first seen
    last_seen_at    TEXT    NOT NULL,           -- ISO 8601 UTC, most recent sighting
    evidence_path   TEXT,                       -- file name inside outputs/evidence
    vibration_g     REAL,                       -- peak vibration if a sensor event matched
    verification    TEXT    NOT NULL DEFAULT 'vision_only'
                    CHECK (verification IN ('vision_only','vision+sensor')),
    status          TEXT    NOT NULL DEFAULT 'Reported'
                    CHECK (status IN ('Reported','In Progress','Repaired')),
    source          TEXT    NOT NULL DEFAULT 'real' CHECK (source IN ('real','simulated')),
    detection_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sensor_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time  TEXT NOT NULL,                  -- ISO 8601 UTC
    latitude    REAL,
    longitude   REAL,
    peak_g      REAL NOT NULL,
    source      TEXT NOT NULL DEFAULT 'real' CHECK (source IN ('real','simulated'))
);

CREATE INDEX IF NOT EXISTS idx_defects_status   ON defects(status);
CREATE INDEX IF NOT EXISTS idx_defects_severity ON defects(severity);
CREATE INDEX IF NOT EXISTS idx_sensor_time      ON sensor_events(event_time);
