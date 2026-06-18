# Kirdbyys Installation Guide

Kirdbyys runs on **Fedora Linux**, **Ubuntu/Debian**, **Windows 10/11**, and **macOS**. All AI processing is local. No cloud account or API key is required.

## Quick Decision Table

| Your Hardware | OS | Install This ONNX Runtime |
|-------------|----|---------------------------|
| NVIDIA GPU (RTX/GTX/Quadro) | Linux or Windows | `onnxruntime-gpu` |
| AMD GPU (dGPU) | Linux | `onnxruntime-rocm` |
| AMD 780M iGPU | Linux | `onnxruntime` or `onnxruntime-openvino` (ROCm may not support iGPU) |
| AMD GPU | Windows | `onnxruntime-directml` |
| Intel Arc / iGPU / CPU | Any | `onnxruntime-openvino` |
| Apple Silicon (M1/M2/M3) | macOS | `onnxruntime` (CoreML included) |
| No discrete GPU | Any | `onnxruntime` |

> **Note:** The base `onnxruntime` package is CPU-only and works everywhere. Install a GPU package only if you want faster inference.

---

## 1. Prerequisites (All Platforms)

- **Python 3.10, 3.11, or 3.12**
- **8 GB RAM** minimum (16–32 GB recommended for 2,000+ images)
- A folder of photos to test with

---

## 2. Fedora Linux

### Install system packages

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-venv python3-devel
sudo dnf install -y opencv opencv-devel
```

### Download Kirdbyys

```bash
cd ~/Software
git clone https://github.com/supermario3D1/kirdbyys-sports-culling.git
cd kirdbyys-sports-culling
```

### Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Choose your hardware acceleration

#### AMD GPU (ROCm)

```bash
sudo dnf install -y rocm-opencl rocm-hip rocm-runtime
pip uninstall -y onnxruntime
pip install onnxruntime-rocm
```

> If you have a 780M iGPU, ROCm may not work. Use CPU or OpenVINO instead.

#### NVIDIA GPU (CUDA)

```bash
sudo dnf install -y akmod-nvidia
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu
```

#### Intel CPU/GPU (OpenVINO)

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-openvino
```

#### CPU-only (always works)

```bash
pip install onnxruntime
```

### Download AI models

```bash
python scripts/setup_models.py
```

### Run

```bash
python -m kirdbyys
```

Open **http://127.0.0.1:7840**.

---

## 3. Ubuntu / Debian

### Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv python3-dev
sudo apt install -y libopencv-dev
```

### Download Kirdbyys

```bash
cd ~/Software
git clone https://github.com/supermario3D1/kirdbyys-sports-culling.git
cd kirdbyys-sports-culling
```

### Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Choose your hardware acceleration

#### AMD GPU (ROCm)

```bash
sudo apt install -y rocm-opencl rocm-hip-runtime
pip uninstall -y onnxruntime
pip install onnxruntime-rocm
```

#### NVIDIA GPU (CUDA)

```bash
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu
```

#### Intel CPU/GPU (OpenVINO)

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-openvino
```

#### CPU-only

```bash
pip install onnxruntime
```

### Download AI models and run

```bash
python scripts/setup_models.py
python -m kirdbyys
```

---

## 4. Windows 10 / 11

### Install Python

Download and install Python 3.11 or 3.12 from https://www.python.org/downloads/

During installation, check **"Add Python to PATH"**.

### Download Kirdbyys

Use PowerShell or Command Prompt:

```powershell
cd C:\Users\YOURNAME\Software
git clone https://github.com/supermario3D1/kirdbyys-sports-culling.git
cd kirdbyys-sports-culling
```

If you don't have `git`, download the ZIP from GitHub and extract it.

### Create virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### Install Python dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Choose your hardware acceleration

#### NVIDIA GPU (CUDA)

Install NVIDIA drivers first, then:

```powershell
pip uninstall -y onnxruntime onnxruntime-gpu
pip install onnxruntime-gpu
```

#### AMD GPU (DirectML)

```powershell
pip uninstall -y onnxruntime
pip install onnxruntime-directml
```

#### Intel CPU/GPU (OpenVINO)

```powershell
pip uninstall -y onnxruntime
pip install onnxruntime-openvino
```

#### CPU-only

```powershell
pip install onnxruntime
```

### Download AI models and run

```powershell
python scripts\setup_models.py
python -m kirdbyys
```

Open **http://127.0.0.1:7840** in your browser.

---

## 5. macOS (Apple Silicon or Intel)

### Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Install Python

```bash
brew install python@3.11
```

### Download Kirdbyys

```bash
cd ~/Software
git clone https://github.com/supermario3D1/kirdbyys-sports-culling.git
cd kirdbyys-sports-culling
```

### Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Hardware acceleration on macOS

- **Apple Silicon (M1/M2/M3)**: CoreML is included in the standard `onnxruntime` package. No extra package needed.
- **Intel Mac**: Use the standard `onnxruntime` for CPU inference.

```bash
pip install onnxruntime
```

### Download AI models and run

```bash
python scripts/setup_models.py
python -m kirdbyys
```

Open **http://127.0.0.1:7840**.

---

## 6. Optional Extras

For RAW file support and PDF reports:

```bash
pip install rawpy reportlab
```

---

## 7. Verify Your Installation

Run the verification script:

```bash
python verify_setup.py
```

You should see a green checkmark and the detected hardware provider.

---

## 8. Which ONNX Runtime Should I Use?

| Package | When to use |
|--------|-------------|
| `onnxruntime` | CPU-only, works everywhere, default |
| `onnxruntime-gpu` | NVIDIA CUDA on Linux/Windows |
| `onnxruntime-rocm` | AMD ROCm on Linux |
| `onnxruntime-directml` | Windows with any GPU/CPU |
| `onnxruntime-openvino` | Intel CPU/GPU, also good on AMD CPUs |
| `onnxruntime-coreml` | macOS CoreML (usually included in base) |

Always uninstall the old `onnxruntime` before installing a GPU-specific one:

```bash
pip uninstall -y onnxruntime
pip install onnxruntime-gpu   # or onnxruntime-rocm, etc.
```

---

## 9. Common Issues

### `ImportError: libGL.so.1`

Use the headless OpenCV package:

```bash
pip uninstall -y opencv-python opencv-python-headless
pip install opencv-python-headless
```

### ONNX GPU provider fails at runtime

Kirdbyys automatically falls back to CPU. To check what providers are available:

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

If your GPU provider is missing, your GPU drivers or the wrong ONNX package are installed.

### Out of memory with 2,000+ images

Edit `kirdbyys/config.py` or create a `.env` file:

```bash
BATCH_SIZE=4
IMAGE_RESIZE_LONG_EDGE=960
```

### Port 7840 is already in use

Create a `.env` file:

```bash
echo "PORT=7841" > .env
```

---

## 10. First Run Checklist

- [ ] Application starts without errors
- [ ] UI loads at http://127.0.0.1:7840
- [ ] Create a test project with a small folder of photos
- [ ] Verify analysis completes and rankings appear
- [ ] Export a CSV and confirm the file is created
