"""ONNX model loading and inference optimized for AMD/Intel/NVIDIA/Apple hardware."""
import os
import onnxruntime as ort
import numpy as np
from pathlib import Path
from PIL import Image
import cv2
import urllib.request
import hashlib
from kirdbyys.config import settings
from kirdbyys.ai.hardware import get_hardware_info, build_provider_priority, configure_onnx_session_options
from typing import List, Tuple, Optional, Dict, Any

class ONNXModelManager:
    """Manages ONNX models with automatic hardware detection and provider priority."""
    
    def __init__(self):
        self.models: Dict[str, ort.InferenceSession] = {}
        self.hw = get_hardware_info()
        self.providers = self._get_providers()
        print(f"[Kirdbyys] Hardware: {self.hw.cpu_name} / {self.hw.gpu_name}")
        print(f"[Kirdbyys] Available ONNX execution providers: {ort.get_available_providers()}")
        print(f"[Kirdbyys] Active provider priority: {self.providers}")
    
    def _get_providers(self) -> List[str]:
        available = ort.get_available_providers()
        if not settings.GPU_ENABLED:
            available = [p for p in available if p == "CPUExecutionProvider"]
        priority = build_provider_priority(self.hw, available)
        if not priority:
            priority = ["CPUExecutionProvider"] if "CPUExecutionProvider" in available else available[:1]
        return priority
    
    def download_model(self, url: str, filename: str, expected_hash: Optional[str] = None) -> Path:
        path = settings.MODELS_DIR / filename
        if path.exists():
            return path
        print(f"[Kirdbyys] Downloading model {filename} from {url}...")
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        urllib.request.urlretrieve(url, path)
        if expected_hash:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_hash:
                raise ValueError(f"Model hash mismatch for {filename}")
        return path
    
    def load(self, name: str, path: Path) -> ort.InferenceSession:
        if name in self.models:
            return self.models[name]
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ALL
        # CPU threads: leave cores for UI and OS; use fewer threads on GPU
        if self.providers and self.providers[0] != "CPUExecutionProvider":
            opts.intra_op_num_threads = 1
            opts.inter_op_num_threads = 1
        else:
            opts.intra_op_num_threads = max(1, min(4, settings.MAX_WORKERS // 2))
            opts.inter_op_num_threads = 1
        opts.enable_cpu_mem_arena = True
        # Build provider-specific options
        provider_options = [configure_onnx_session_options(p) for p in self.providers]
        session = ort.InferenceSession(
            str(path),
            sess_options=opts,
            providers=self.providers,
            provider_options=provider_options
        )
        self.models[name] = session
        return session
    
    def get_input_shape(self, session: ort.InferenceSession) -> Tuple[int, ...]:
        inp = session.get_inputs()[0]
        shape = inp.shape
        # Resolve dynamic dims
        return tuple(1 if isinstance(s, str) else s for s in shape)
    
    def run(self, name: str, inputs: Dict[str, np.ndarray]) -> List[np.ndarray]:
        session = self.models[name]
        return session.run(None, inputs)

# Global model manager (lazy singleton)
_model_manager: Optional[ONNXModelManager] = None

def get_model_manager() -> ONNXModelManager:
    global _model_manager
    if _model_manager is None:
        _model_manager = ONNXModelManager()
    return _model_manager

# Keep legacy alias for compatibility
model_manager = get_model_manager

def letterbox_resize(img: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, Tuple[float, float], Tuple[int, int]]:
    """Resize image with padding preserving aspect ratio."""
    h, w = img.shape[:2]
    scale = min(target_size / h, target_size / w)
    new_h, new_w = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_top = (target_size - new_h) // 2
    pad_bottom = target_size - new_h - pad_top
    pad_left = (target_size - new_w) // 2
    pad_right = target_size - new_w - pad_left
    padded = cv2.copyMakeBorder(resized, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return padded, (scale, scale), (pad_top, pad_left)

def preprocess_cls(image: np.ndarray, input_size: int = 224) -> np.ndarray:
    """Preprocess for classification model (ImageNet stats)."""
    img = cv2.resize(image, (input_size, input_size))
    img = img.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    img = np.transpose(img, (2, 0, 1))
    return np.expand_dims(img, axis=0)

def preprocess_yolo(image: np.ndarray, input_size: int = 640) -> Tuple[np.ndarray, Tuple[float, float], Tuple[int, int]]:
    img, scale, pad = letterbox_resize(image, input_size)
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return img, scale, pad
