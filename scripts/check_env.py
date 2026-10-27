"""Run:  python scripts/check_env.py   -> shows Python version and which libraries work."""
import importlib
import sys

print("Python:", sys.version.split()[0])
if sys.version_info >= (3, 14):
    print("WARNING: Python 3.14+ may not be supported by PyTorch/Ultralytics yet. Use 3.12 or 3.13.")
for mod in ["flask", "requests", "cv2", "numpy", "ultralytics", "plyer", "serial"]:
    try:
        m = importlib.import_module(mod)
        print(f"OK       {mod} {getattr(m, '__version__', '')}")
    except Exception as e:
        print(f"MISSING  {mod}  ({type(e).__name__})")
