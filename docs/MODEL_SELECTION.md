# Model Selection & Justification

## Principle

Kirdbyys must run entirely on local, open-source models with no paid API. All inference is done via **ONNX Runtime** so it can be optimized for AMD, Intel, NVIDIA, and Apple hardware.

## Selected Models

### 1. Object Detection: YOLOv8n (COCO)
- **Model**: `yolov8n.onnx`
- **Role**: Detect players, ball, goalkeeper, goalposts, crowd, coaches, faces
- **Why**: extremely fast, small (6 MB), high accuracy, broad class coverage
- **Speed**: ~5-10 ms per image on CPU; faster on GPU
- **License**: AGPL-3.0 (Ultralytics), model weights are open for personal/professional use
- **Classes**: 80 COCO classes including person, sports ball, baseball bat, tennis racket
- **Future**: can be replaced with a custom soccer-tuned YOLOv8 model trained on pitch-level annotations

### 2. Technical Quality: Classical CV + Optional Aesthetic Classifier
- **Primary**: handcrafted metrics (Laplacian variance, gradient magnitude, histogram analysis, noise estimation, color balance, compression artifact detection)
- **Optional**: MobileNetV2 aesthetic classifier ONNX for second opinion
- **Why classical first**: deterministic, interpretable, no training data needed, fast on CPU, covers all requested technical metrics (sharpness, exposure, noise, clipping, dynamic range, white balance, artifacts)
- **Why optional aesthetic**: adds a learned "photo quality" signal when dataset is available

### 3. Duplicate Detection: Perceptual Hash + Feature Vector
- **Perceptual hash**: `imagehash.phash` (16-bit)
- **Feature vector**: HSV histogram + edge histogram
- **Why**: robust to small JPEG/recompression changes, fast to compute, low memory footprint, excellent for burst detection

### 4. Soccer Moment Classifier: Heuristic Rule Engine
- **Approach**: rule-based classifier using YOLO detections + classical CV features
- **Why**: rules are transparent, editable, and require no training data to start working
- **Future**: rules will be replaced/augmented by a small trained classifier (e.g., EfficientNet-B0 ONNX) once a labeled dataset is built

### 5. Face / Emotion Detection (Optional Future)
- **Candidate**: YOLOv8-face ONNX or MediaPipe face detection
- **Use**: emotional density scoring, coach/player reactions
- **Status**: placeholder logic exists; can be plugged in without backend changes

## Execution Providers (Cross-Platform)

Kirdbyys auto-detects the available hardware and selects the best provider. The priority order is:

| Provider | Platform | Hardware | Notes |
|----------|----------|----------|-------|
| TensorrtExecutionProvider | Linux/Windows | NVIDIA | Fastest, requires setup |
| CUDAExecutionProvider | Linux/Windows | NVIDIA | General NVIDIA GPU |
| ROCMExecutionProvider | Linux | AMD | Primary target for AMD dGPU/iGPU |
| MIGraphXExecutionProvider | Linux | AMD | Optional AMD graph compiler |
| OpenVINOExecutionProvider | Linux/Windows/macOS | Intel/AMD CPU, Intel GPU | Excellent CPU acceleration |
| DmlExecutionProvider | Windows | Any GPU/CPU | DirectML fallback |
| CoreMLExecutionProvider | macOS | Apple Silicon | Neural Engine / GPU |
| OpenCLExecutionProvider | Variable | Generic | Rarely used |
| CPUExecutionProvider | All | Any CPU | Reliable universal fallback |

## Why ONNX?

ONNX Runtime is the only inference framework that supports NVIDIA, AMD, Intel, and Apple hardware from the same model file. This allows Kirdbyys to run optimally on any machine without vendor lock-in.

## Model Roadmap

| Phase | Model | Purpose |
|-------|-------|---------|
| Now | YOLOv8n + classical CV | Full pipeline working immediately |
| Phase 2 | Custom YOLOv8 soccer | Better player/ball/goalpost detection on field |
| Phase 3 | EfficientNet-B0 moment classifier | Learned soccer moment classification |
| Phase 4 | Facial expression ONNX | Emotional impact scoring |
| Phase 5 | Sport-specific adapters | AFL, basketball, rugby, cricket, etc. |
