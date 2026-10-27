"""Download an annotated pothole dataset in YOLOv8 format from Roboflow Universe.

1. Make a free Roboflow account, open the dataset page, click Download Dataset -> YOLOv8 -> "show download code".
2. Copy the workspace, project, version number and your API key into the variables below
   (or pass the key as an environment variable ROBOFLOW_API_KEY).
3. Check the dataset's LICENSE on its page and note it in your report.
Run:  pip install roboflow    then    python scripts/download_roboflow.py
"""
import os
from pathlib import Path

WORKSPACE = "yeeun-kim-fyvoj"      # from the URL you were given
PROJECT = "pothole-vhmow"
VERSION = 1                        # CHECK on the page which versions exist
API_KEY = os.environ.get("ROBOFLOW_API_KEY", "PASTE_YOUR_KEY_HERE")

from roboflow import Roboflow  # noqa: E402

dest = Path(__file__).resolve().parent.parent / "dataset" / "roboflow_pothole"
rf = Roboflow(api_key=API_KEY)
ds = rf.workspace(WORKSPACE).project(PROJECT).version(VERSION).download("yolov8", location=str(dest))
print("Downloaded to:", ds.location)
print("Now open", dest / "data.yaml", "and check train/val/test paths and class names.")
