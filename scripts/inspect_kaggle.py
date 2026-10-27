"""Count images in your Kaggle Normal/Pothole folders.
Run:  python scripts/inspect_kaggle.py dataset/kaggle_pothole
"""
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "dataset/kaggle_pothole")
ext = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
if not root.exists():
    sys.exit(f"Folder not found: {root}")
for folder in sorted(p for p in root.rglob("*") if p.is_dir()):
    n = sum(1 for f in folder.iterdir() if f.suffix.lower() in ext)
    if n:
        print(f"{folder.relative_to(root)}: {n} images")
labels = list(root.rglob("*.txt")) + list(root.rglob("*.xml")) + list(root.rglob("*.json"))
print("Label files found:", len(labels))
print("-> If 0, this is a CLASSIFICATION set (no boxes): usable as test images, not for YOLO detection training.")
