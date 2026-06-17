# Kirdbyys Optimization Guide

## Target Hardware

Kirdbyys is tested and optimized for:

- **AMD**: Ryzen 7 7840U + Radeon 780M iGPU (Fedora Linux)
- **NVIDIA**: RTX 3060/4060/4090 and GTX/Quadro series (Windows/Linux)
- **Intel**: Core i7/i9 with Arc/integrated graphics (Windows/Linux/macOS)
- **Apple**: M1/M2/M3 Macs (macOS)
- **CPU-only**: any modern x86_64 or ARM64 CPU

## Recommended Software Stack

1. **Python 3.11** from OS repos or pyenv
2. **ONNX Runtime** with execution provider for your hardware
3. **OpenCV** built with `opencv-python-headless` for server use
4. Vendor GPU drivers (ROCm, CUDA, Intel OpenVINO, Apple CoreML)

## Hardware Detection

Kirdbyys automatically detects the CPU/GPU vendor and selects the best ONNX execution provider. Check the detected provider at startup or via the API:

```bash
curl http://127.0.0.1:7840/api/system/info
```

## ROCm Setup (AMD GPU on Linux)

```bash
# Fedora ROCm installation (check AMD documentation for latest)
sudo dnf install rocm-opencl rocm-hip rocm-runtime
# Verify
cat /opt/rocm/.info/version
# Install onnxruntime-rocm if available
pip install onnxruntime-rocm
```

If ROCm does not support the 780M iGPU, the CPU fallback is still fast thanks to batch processing.

## NVIDIA Setup (CUDA/TensorRT)

```bash
pip install onnxruntime-gpu
```

Ensure NVIDIA drivers and CUDA are installed. Kirdbyys will automatically prefer `CUDAExecutionProvider` and `TensorrtExecutionProvider` when available.

## Intel Setup (OpenVINO)

```bash
pip install onnxruntime-openvino
```

OpenVINO works on Intel CPUs, integrated GPUs, and Arc discrete GPUs. It also provides good acceleration on AMD CPUs.

## Apple Silicon (CoreML)

On macOS with Apple Silicon, install `onnxruntime-silicon` or the standard package with CoreML support. Kirdbyys will use `CoreMLExecutionProvider` automatically.

## CPU Optimization

ONNX Runtime CPU provider is already optimized:

- `intra_op_num_threads` set to half of CPU cores
- `inter_op_num_threads` set to 1
- `graph_optimization_level = ORT_ALL`

Additional tuning:

```python
# In kirdbyys/config.py
BATCH_SIZE = 16  # increase if RAM allows
MAX_WORKERS = 12  # leave threads for UI and OS
```

## Processing 2,000+ Images

1. **Use batch processing**: default batch size is 8; raise to 16 with 32 GB RAM
2. **Lower resize size**: `IMAGE_RESIZE_LONG_EDGE` can be reduced to 960 for faster detection if you only need web-sized ranking
3. **Enable thumbnails once**: previews are cached on disk, not recomputed
4. **Process on SSD**: reading thousands of RAW files from HDD is slow
5. **Avoid RAW for ranking pass**: convert to JPG proxy first, then map selections back to RAW masters

## Memory Management

- The pipeline resizes images to a max long edge of 1280 px before analysis
- Thumbnails are small (320 px on long edge)
- Feature vectors are ~60 floats stored as compressed base64
- For 2,000 images, total DB size is typically < 50 MB

## Benchmarking

Run a quick benchmark on a subset:

```bash
python -c "
import time
from kirdbyys.core.pipeline import ImagePipeline
from pathlib import Path
p = ImagePipeline()
files = list(Path('/photos/match').glob('*.jpg'))[:100]
t0 = time.time()
for f in files:
    p.analyze_image(str(f), 0)
print(f'{len(files)/(time.time()-t0):.2f} images/sec')
"
```

Target: **1–3 images/sec on CPU**, **3–8 images/sec on ROCm** for the target hardware.

## Export Performance

- CSV/Excel/XMP: fast, metadata-only
- Copy/move: limited by disk I/O; use SSD-to-SSD copies
- For 2,000 images, copying 25 MB each = ~50 GB; plan destination space

## Caching Strategy

- `CACHE_DIR/thumbnails/`: 320 px thumbnails
- `CACHE_DIR/previews/`: 1280 px previews
- `DATA_DIR/project_{id}/`: imported master copies (or proxies)
- `kirdbyys/data/kirdbyys.db`: SQLite metadata and scores

Delete cache if needed; it is rebuilt automatically.

## Future Optimizations

- Compile ONNX models to INT8 for OpenVINO
- Use ROCm MIOpen for any GPU-accelerated models
- Add shared memory for batch feature extraction
- Use `ray` or `dask` for multi-machine scaling (optional, still local cluster)
