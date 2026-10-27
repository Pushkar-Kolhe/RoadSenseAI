"""Convert polygon/oriented labels to plain YOLO boxes and make two check images.

Run once:  python scripts/prepare_labels.py

What it does
 1. Backs up your original labels to dataset/roboflow_pothole_labels_backup (never overwritten).
 2. Rewrites every label line as:  class x_center y_center width height   (the standard YOLO box).
 3. Prints how many images have boxes / have no boxes in each split.
 4. Saves two pictures to outputs/ so YOU can check the data by eye:
      outputs/check_labeled.jpg  - 12 random images with the converted boxes drawn
      outputs/check_empty.jpg    - 12 random images that have NO label (do any show a pothole?)
"""
import random
import shutil
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DS = ROOT / "dataset" / "roboflow_pothole"
BACKUP = ROOT / "dataset" / "roboflow_pothole_labels_backup"
OUT = ROOT / "outputs"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
random.seed(1)


def read_img(path):
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def write_img(path, img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    buf.tofile(str(path))


def convert_line(line):
    p = line.split()
    if len(p) == 5:                       # already a normal box
        return line.strip()
    cls, vals = p[0], [float(v) for v in p[1:]]
    if len(vals) < 6 or len(vals) % 2:
        return None
    xs, ys = vals[0::2], vals[1::2]
    x1, x2 = max(min(xs), 0.0), min(max(xs), 1.0)
    y1, y2 = max(min(ys), 0.0), min(max(ys), 1.0)
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    return f"{cls} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {w:.6f} {h:.6f}"


def draw_boxes(img, label_file):
    h, w = img.shape[:2]
    for line in label_file.read_text().splitlines():
        p = line.split()
        if len(p) != 5:
            continue
        _, cx, cy, bw, bh = map(float, p)
        x1, y1 = int((cx - bw / 2) * w), int((cy - bh / 2) * h)
        x2, y2 = int((cx + bw / 2) * w), int((cy + bh / 2) * h)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 3)
    return img


def contact_sheet(paths, label_dir, out_file, draw):
    tiles = []
    for ip in paths:
        img = read_img(ip)
        if img is None:
            continue
        if draw:
            img = draw_boxes(img, label_dir / (ip.stem + ".txt"))
        tiles.append(cv2.resize(img, (320, 320)))
    if not tiles:
        print("  (no images for", out_file.name + ")")
        return
    while len(tiles) % 4:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
    write_img(out_file, np.vstack(rows))
    print("  saved", out_file)


if not DS.exists():
    raise SystemExit(f"Not found: {DS}")
OUT.mkdir(exist_ok=True)

for split in ("train", "valid", "test"):
    lbl_dir, img_dir = DS / split / "labels", DS / split / "images"
    if not lbl_dir.exists():
        print(split, ": labels folder missing, skipped")
        continue
    if not (BACKUP / split).exists():
        shutil.copytree(lbl_dir, BACKUP / split)
    n_empty = n_boxes = n_with = n_bad = 0
    for lf in lbl_dir.glob("*.txt"):
        out = []
        for line in lf.read_text().splitlines():
            if not line.strip():
                continue
            c = convert_line(line)
            if c is None:
                n_bad += 1
            else:
                out.append(c)
        lf.write_text("\n".join(out) + ("\n" if out else ""))
        if out:
            n_with += 1
            n_boxes += len(out)
        else:
            n_empty += 1
    print(f"{split}: {n_with} images with potholes ({n_boxes} boxes), {n_empty} with no label, {n_bad} bad lines dropped")

train_imgs = [p for p in (DS / "train" / "images").iterdir() if p.suffix.lower() in IMG_EXT]
lbl = DS / "train" / "labels"
labeled = [p for p in train_imgs if (lbl / (p.stem + ".txt")).exists() and (lbl / (p.stem + ".txt")).stat().st_size > 0]
empty = [p for p in train_imgs if not (lbl / (p.stem + ".txt")).exists() or (lbl / (p.stem + ".txt")).stat().st_size == 0]
contact_sheet(random.sample(labeled, min(12, len(labeled))), lbl, OUT / "check_labeled.jpg", True)
contact_sheet(random.sample(empty, min(12, len(empty))), lbl, OUT / "check_empty.jpg", False)
print("Done. Open the two pictures in the outputs folder.")