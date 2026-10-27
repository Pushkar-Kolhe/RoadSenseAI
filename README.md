# RoadSense AI

Detects road damage (potholes), stores each defect with location, severity, time and photo evidence, and shows them on a map so repairs can be prioritised.

## Folder guide
| Folder | What goes in it |
|---|---|
| `dataset/` | Downloaded datasets (Kaggle folders, Roboflow YOLO set). Never commit; large. |
| `models/` | Trained weights, e.g. `best.pt` |
| `test_images/` | Road photos you want to test the model on |
| `outputs/detections/` | Images with boxes drawn (from `detect.py` on files) |
| `outputs/evidence/` | Photo evidence saved by the backend for each defect |
| `backend/` | Flask server, database code, severity rules |
| `database/` | `schema.sql` and the SQLite file `roadsense.db` (auto-created) |
| `vision/` | `detect.py` (YOLO + OpenCV) and the client that talks to Flask |
| `simulate/` | Fake-data demo (no hardware, no model needed) |
| `hardware/` | Pico 2 MicroPython code + PC serial bridge |
| `frontend/` | Dashboard (HTML, CSS, JS, Leaflet) |
| `scripts/` | check_env, inspect_kaggle, download_roboflow, train |

## Setup (Windows, PowerShell, inside the RoadSense_AI folder)
Use Python 3.12 or 3.13 (Python 3.15 is too new for PyTorch/Ultralytics).
```
py --list
py -3.13 -m venv .venv          # or -3.12
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install flask requests opencv-python numpy plyer
python scripts/check_env.py
```
If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry.
Install YOLO later (big download): `pip install ultralytics`

## Run the demo (works with no hardware and no model)
Terminal 1: `python backend/app.py`  -> open http://127.0.0.1:5000
Terminal 2: `python simulate/simulate_detections.py`
Dashboard shows 12 markers tagged SIMULATED, with filters, sorting and status changes.

## Real detection pipeline
1. `python scripts/inspect_kaggle.py dataset/kaggle_pothole` - your Kaggle set has no boxes, so it cannot train YOLO; use it as test images.
2. `pip install roboflow`, fill in the key/version in `scripts/download_roboflow.py`, run it. Check the dataset license and `data.yaml`.
3. `python scripts/train.py 30` (try 3 epochs first to test). Copy `outputs/training/pothole/weights/best.pt` to `models/best.pt`.
4. `python vision/detect.py --source test_images` then `--source 0 --send --lat 18.515 --lon 73.78` for webcam.

## How the parts talk
Camera -> `detect.py` (laptop, OpenCV + YOLO) -> HTTP POST JSON -> Flask -> SQLite -> dashboard (browser calls Flask API every 5 s).
Pico 2 (GPS+IMU) -> USB serial -> `pc_bridge.py` -> HTTP POST -> Flask. The Pico cannot run YOLOv8; it only collects sensor data.
Flask matches a detection to an IMU spike within +/-3 s and 50 m. If matched: `vision+sensor`, otherwise `vision_only`.
Vibration alone is never enough: speed bumps, braking and rough tarmac also cause spikes, and GPS error / clock offset limit matching.

## SQLite vs MySQL
SQLite: no install, one file, matches your PPT, enough for a single-laptop demo. MySQL: needs a server, but supports many users and remote access. Recommendation for the prototype: SQLite. All SQL is in `backend/db.py` and `database/schema.sql`, so switching to MySQL later means changing the connection and a few column types.

## Honest status (update as you test)
| Module | Status |
|---|---|
| Flask API, validation, duplicate merge, SQLite | Built and tested with simulated data |
| Dashboard (Leaflet map, filters, sorting, status) | Built; API and static serving verified, map view needs your browser check |
| Simulation | Built and tested |
| YOLO training and detection (`train.py`, `detect.py`) | Written, NOT yet run |
| Pico GPS+IMU code, PC bridge | Written, NOT tested on hardware |
| Notifications | Dashboard title/browser notification and plyer in `detect.py`; untested on your PC |

Do not claim "100% complete". Present tested modules as working, the rest as in development.
