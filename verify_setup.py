#!/usr/bin/env python3
"""Verify Kirdbyys installation and environment."""
import sys
import os
from pathlib import Path

print("=" * 60)
print("Kirdbyys Sports Culling Tool — Setup Verification")
print("=" * 60)

errors = []
warnings = []

# Python version
print(f"\nPython version: {sys.version}")
if sys.version_info < (3, 10):
    errors.append("Python 3.10 or newer is required")

# Core dependencies
print("\nChecking core dependencies...")
core_deps = [
    "fastapi", "uvicorn", "pillow", "numpy", "scipy", "sklearn",
    "skimage", "pandas", "onnxruntime", "cv2", "imagehash", "sqlalchemy"
]
for dep in core_deps:
    try:
        __import__(dep)
        print(f"  ✓ {dep}")
    except ImportError as e:
        errors.append(f"Missing dependency: {dep} ({e})")
        print(f"  ✗ {dep}")

# Hardware detection
print("\nChecking hardware and execution providers...")
try:
    from kirdbyys.ai.hardware import get_hardware_info, print_hardware_summary
    hw = get_hardware_info()
    print_hardware_summary()
    if hw.recommended_provider == "CPUExecutionProvider" and hw.gpu_vendor != "none":
        warnings.append(f"GPU detected ({hw.gpu_vendor}) but only CPU provider is available. Install a GPU-specific onnxruntime package.")
except Exception as e:
    warnings.append(f"Hardware detection failed: {e}")

# Models
print("\nChecking model files...")
models_dir = Path(__file__).resolve().parent / "kirdbyys" / "models"
required_models = ["yolov8n.onnx"]
for m in required_models:
    path = models_dir / m
    if path.exists():
        print(f"  ✓ {m} ({path.stat().st_size / 1e6:.1f} MB)")
    else:
        warnings.append(f"Model not found: {path}. Run 'python scripts/setup_models.py'")
        print(f"  ! {m} not found")

# Directories
print("\nChecking directories...")
for sub in ["data", "cache", "temp", "exports"]:
    d = Path(__file__).resolve().parent / "kirdbyys" / sub
    d.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {sub}")

# Disk space
print("\nChecking disk space...")
try:
    import shutil
    total, used, free = shutil.disk_usage("/")
    print(f"  Free disk space: {free / 1e9:.1f} GB")
    if free < 10 * 1e9:
        warnings.append("Less than 10 GB free disk space")
except Exception as e:
    warnings.append(f"Could not check disk space: {e}")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)} error(s) found:")
    for e in errors:
        print(f"   - {e}")
if warnings:
    print(f"⚠️  {len(warnings)} warning(s):")
    for w in warnings:
        print(f"   - {w}")
if not errors and not warnings:
    print("✅ Kirdbyys is ready to run!")
print("=" * 60)

sys.exit(1 if errors else 0)
