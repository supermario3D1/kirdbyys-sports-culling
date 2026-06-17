#!/usr/bin/env python3
"""Download required ONNX models for Kirdbyys."""
import urllib.request
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "kirdbyys" / "models"
BASE.mkdir(parents=True, exist_ok=True)

MODELS = {
    "yolov8n.onnx": "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n-oiv7.onnx",
    # Aesthetic scoring model — optional, will fall back to classical CV if unavailable
    # "aesthetic_mobilenetv2.onnx": "https://github.com/youthjoey/aesthetic_prediction/releases/download/v1.0/aesthetic_model_mobilenetv2.onnx",
}

def download(name, url):
    path = BASE / name
    if path.exists():
        print(f"[setup] {name} already exists at {path}")
        return
    print(f"[setup] Downloading {name}...")
    urllib.request.urlretrieve(url, path)
    print(f"[setup] Saved {name} ({os.path.getsize(path) / 1e6:.1f} MB)")

if __name__ == "__main__":
    for name, url in MODELS.items():
        try:
            download(name, url)
        except Exception as e:
            print(f"[setup] Failed to download {name}: {e}")
    print("[setup] Done. You can now run Kirdbyys.")