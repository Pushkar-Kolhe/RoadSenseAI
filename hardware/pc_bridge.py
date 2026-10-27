"""Runs on the laptop: reads JSON lines from the Pico over USB and forwards them to Flask.
Run:  python hardware/pc_bridge.py COM5        (find the port in Thonny or Device Manager)
"""
import json
import sys
from pathlib import Path

import serial  # pip install pyserial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vision"))
from roadsense_client import send_sensor_event  # noqa: E402

port = sys.argv[1] if len(sys.argv) > 1 else "COM5"
with serial.Serial(port, 115200, timeout=1) as ser:
    print("Listening on", port)
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line.startswith("{"):
            continue
        try:
            e = json.loads(line)
            print(send_sensor_event(e["peak_g"], e.get("latitude"), e.get("longitude"), source="real"))
        except Exception as ex:
            print("bad line:", line, ex)
