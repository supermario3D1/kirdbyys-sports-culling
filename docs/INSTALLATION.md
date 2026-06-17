# Installation Guide

## Supported Platforms

- Fedora Linux (primary target)
- Ubuntu / Debian
- Windows 10/11
- macOS 13+ (Apple Silicon or Intel)

## Prerequisites

- Python 3.10, 3.11, or 3.12
- pip
- 8 GB RAM minimum (16–32 GB recommended)
- Optional: ROCm (AMD GPU on Linux) or OpenVINO

## Step-by-Step Installation

### 1. Clone or Extract

```bash
cd ~/Software
git clone https://github.com/kirdbyys/kirdbyys-sports-culling.git
cd kirdbyys-sports-culling
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:
```cmd
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

Install the base package first:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Choose the right ONNX Runtime for your hardware

The default `onnxruntime` is CPU-only. For GPU acceleration, install the matching package for your hardware **before** running Kirdbyys:

```bash
# NVIDIA GPU (CUDA / TensorRT)
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu

# AMD GPU on Linux (ROCm)
pip uninstall -y onnxruntime
pip install onnxruntime-rocm

# Intel CPU/GPU (OpenVINO)
pip uninstall -y onnxruntime
pip install onnxruntime-openvino

# Apple Silicon (CoreML is included in the standard onnxruntime package)
# No extra package needed on macOS
```

You can verify the correct provider is detected by running:

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

For RAW support and PDF reports:

```bash
pip install rawpy reportlab
```

#### GPU Acceleration (optional, but recommended)

The base `onnxruntime` package is CPU-only. Install the package matching your GPU for the best performance:

- **NVIDIA GPU**: `pip install onnxruntime-gpu`
- **AMD GPU on Linux**: `pip install onnxruntime-rocm` (requires ROCm drivers)
- **AMD GPU on Windows**: `pip install onnxruntime-directml`
- **Intel GPU/CPU**: `pip install onnxruntime-openvino`
- **Apple Silicon**: `pip install onnxruntime` (CoreML support is often included)

Kirdbyys will auto-detect the available provider and use it.


### 4. Download ONNX Models

```bash
python scripts/setup_models.py
```

This downloads YOLOv8n into `kirdbyys/models/`.

### 5. Run the Application

```bash
python -m kirdbyys
```

Open **http://127.0.0.1:7840** in your browser.

### 6. Optional: Install as System Package

```bash
pip install -e .
```

Then run from anywhere:

```bash
kirdbyys
```

## Fedora-Specific Notes

```bash
sudo dnf install python3-pip python3-venv python3-devel
sudo dnf install opencv opencv-devel
```

For ROCm:

```bash
sudo dnf install rocm-opencl rocm-hip rocm-runtime
pip install onnxruntime-rocm
```

## Ubuntu / Debian

```bash
sudo apt update
sudo apt install python3-pip python3-venv python3-dev libopencv-dev
```

## Windows

Use PowerShell or Command Prompt. No ROCm support; use DirectML or CPU.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m kirdbyys
```

## Troubleshooting

### ImportError: libGL.so.1

Install OpenCV system libraries or use the headless version:

```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python-headless
```

### ONNX Runtime cannot load GPU provider

The app automatically falls back to CPU. To verify:

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

### Out of memory during large import

Reduce batch size and resize size in `kirdbyys/config.py`:

```python
BATCH_SIZE = 4
IMAGE_RESIZE_LONG_EDGE = 960
```

## First Run Checklist

- [ ] Application starts without errors
- [ ] UI loads at http://127.0.0.1:7840
- [ ] Create a test project with a small folder
- [ ] Verify analysis completes and rankings appear
- [ ] Export a CSV and confirm file is created
