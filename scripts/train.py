"""Fine-tune YOLOv8n on the pothole dataset.
Test run (about 1 epoch):  python scripts/train.py 1
Real run:                  python scripts/train.py 30
"""
import sys
from pathlib import Path


def main():
    from ultralytics import YOLO

    root = Path(__file__).resolve().parent.parent
    data_yaml = root / "dataset" / "roboflow_pothole" / "data.yaml"
    if not data_yaml.exists():
        sys.exit("data.yaml not found. Check dataset/roboflow_pothole/")

    epochs = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    model = YOLO("yolov8n.pt")   # small pretrained model, downloaded automatically (~6 MB)
    model.train(data=str(data_yaml), epochs=epochs, imgsz=640, batch=8,
                project=str(root / "outputs" / "training"), name="pothole", exist_ok=True)
    print("Done. Best weights: outputs/training/pothole/weights/best.pt")
    print("Copy that file to models/best.pt")


if __name__ == "__main__":      # required on Windows so training workers start correctly
    main()