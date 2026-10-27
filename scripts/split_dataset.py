"""Split dataset/roboflow_pothole/train into train / valid / test (80/10/10).
Run once:  python scripts/split_dataset.py
Safe to run twice: it stops if valid/ already has images.
"""
import random
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "dataset" / "roboflow_pothole"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
random.seed(42)

img_dir, lbl_dir = ROOT / "train" / "images", ROOT / "train" / "labels"
if not img_dir.exists():
    raise SystemExit(f"Not found: {img_dir}")
if (ROOT / "valid" / "images").exists() and any((ROOT / "valid" / "images").iterdir()):
    raise SystemExit("valid/ already has images - split was already done.")

images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXT)
random.shuffle(images)
n = len(images)
n_val, n_test = round(n * 0.10), round(n * 0.10)
parts = {"valid": images[:n_val], "test": images[n_val:n_val + n_test]}

# What do the label lines look like? 5 numbers = boxes; more = polygons (YOLO converts them)
cols = Counter()
for p in images[:200]:
    lf = lbl_dir / (p.stem + ".txt")
    if lf.exists():
        for line in lf.read_text().splitlines():
            if line.strip():
                cols[len(line.split())] += 1
print("Numbers per label line (count of lines):", dict(cols))

for name, files in parts.items():
    (ROOT / name / "images").mkdir(parents=True, exist_ok=True)
    (ROOT / name / "labels").mkdir(parents=True, exist_ok=True)
    for p in files:
        shutil.move(str(p), ROOT / name / "images" / p.name)
        lf = lbl_dir / (p.stem + ".txt")
        if lf.exists():
            shutil.move(str(lf), ROOT / name / "labels" / lf.name)

for name in ("train", "valid", "test"):
    c_img = len(list((ROOT / name / "images").iterdir()))
    c_lbl = len(list((ROOT / name / "labels").iterdir()))
    print(f"{name}: {c_img} images, {c_lbl} labels")