"""Hardware/architecture detection and ONNX provider selection.

Detects CPU/GPU vendor and chooses the best available ONNX execution provider.
Works on AMD, Intel, NVIDIA, Apple Silicon, and generic CPU.
"""
import os
import platform
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import onnxruntime as ort
from kirdbyys.config import settings

@dataclass
class HardwareInfo:
    platform: str = ""
    cpu_name: str = ""
    cpu_count: int = 0
    gpu_vendor: str = "unknown"
    gpu_name: str = "none"
    gpu_memory_mb: int = 0
    has_cuda: bool = False
    has_rocm: bool = False
    has_openvino: bool = False
    has_directml: bool = False
    has_coreml: bool = False
    has_tensorrt: bool = False
    has_migraphx: bool = False
    has_vitisai: bool = False
    has_opencl: bool = False


def _run_command(cmd: List[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def get_cpu_name() -> str:
    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif system == "Windows":
        out = _run_command(["wmic", "cpu", "get", "name"])
        lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
        if lines:
            return lines[0]
    elif system == "Darwin":
        out = _run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        if out:
            return out
    return platform.processor() or "Unknown CPU"


def get_gpu_info() -> Dict[str, Any]:
    """Detect GPU vendor and basic info."""
    info = {"vendor": "unknown", "name": "none", "memory_mb": 0}
    system = platform.system()

    # NVIDIA: try nvidia-smi
    if system in ("Linux", "Windows"):
        out = _run_command(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])
        if out and "," in out:
            parts = [p.strip() for p in out.split(",")]
            if parts:
                info["vendor"] = "nvidia"
                info["name"] = parts[0]
                if len(parts) > 1:
                    mem_str = parts[1].replace("MiB", "").replace("MB", "").strip()
                    try:
                        info["memory_mb"] = int(mem_str)
                    except ValueError:
                        pass
                return info

    # Linux: lspci for GPU vendors
    if system == "Linux":
        out = _run_command(["lspci"])
        if out:
            out_lower = out.lower()
            if "amd" in out_lower or "ati" in out_lower or "radeon" in out_lower:
                info["vendor"] = "amd"
                # Try to extract name
                for line in out.splitlines():
                    if "amd" in line.lower() or "radeon" in line.lower():
                        if "vga" in line.lower() or "3d" in line.lower() or "display" in line.lower():
                            info["name"] = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
                            break
            elif "intel" in out_lower and "arc" in out_lower:
                info["vendor"] = "intel"
            elif "apple" in out_lower:
                info["vendor"] = "apple"

    # Windows: wmic path win32_VideoController
    if system == "Windows":
        out = _run_command(["wmic", "path", "win32_VideoController", "get", "name"])
        lines = [l.strip() for l in out.splitlines() if l.strip() and "Name" not in l]
        if lines:
            name = lines[0]
            info["name"] = name
            name_lower = name.lower()
            if "nvidia" in name_lower or "geforce" in name_lower or "rtx" in name_lower:
                info["vendor"] = "nvidia"
            elif "amd" in name_lower or "radeon" in name_lower:
                info["vendor"] = "amd"
            elif "intel" in name_lower:
                info["vendor"] = "intel"

    # macOS: system_profiler
    if system == "Darwin":
        out = _run_command(["system_profiler", "SPDisplaysDataType"])
        if out:
            if "apple" in out.lower() or "m1" in out.lower() or "m2" in out.lower() or "m3" in out.lower():
                info["vendor"] = "apple"
                info["name"] = "Apple Silicon"
            elif "intel" in out.lower():
                info["vendor"] = "intel"

    return info


def get_hardware_info() -> HardwareInfo:
    available = ort.get_available_providers()
    gpu = get_gpu_info()
    hw = HardwareInfo(
        platform=platform.system(),
        cpu_name=get_cpu_name(),
        cpu_count=os.cpu_count() or 4,
        gpu_vendor=gpu["vendor"],
        gpu_name=gpu["name"],
        gpu_memory_mb=gpu["memory_mb"],
        has_cuda="CUDAExecutionProvider" in available,
        has_rocm="ROCMExecutionProvider" in available,
        has_openvino="OpenVINOExecutionProvider" in available,
        has_directml="DmlExecutionProvider" in available,
        has_coreml="CoreMLExecutionProvider" in available,
        has_tensorrt="TensorrtExecutionProvider" in available,
        has_migraphx="MIGraphXExecutionProvider" in available,
        has_vitisai="VitisAIExecutionProvider" in available,
        has_opencl="OpenCLExecutionProvider" in available,
    )
    return hw


def _provider_score(provider: str, hw: HardwareInfo) -> int:
    """Lower score = higher priority."""
    scores = {
        "TensorrtExecutionProvider": 10,
        "CUDAExecutionProvider": 20,
        "MIGraphXExecutionProvider": 25,
        "ROCMExecutionProvider": 30,
        "CoreMLExecutionProvider": 35,
        "OpenVINOExecutionProvider": 40,
        "DmlExecutionProvider": 50,
        "VitisAIExecutionProvider": 55,
        "OpenCLExecutionProvider": 90,
        "CPUExecutionProvider": 100,
    }
    return scores.get(provider, 99)


def build_provider_priority(hw: HardwareInfo, available: List[str]) -> List[str]:
    """Build a provider priority list based on detected hardware and available providers."""
    # Start with all available providers
    candidates = list(available)

    # If a specific GPU vendor is detected, deprioritize mismatched GPU providers to avoid crashes
    if hw.gpu_vendor == "nvidia":
        if hw.has_tensorrt and settings.ENABLE_TENSORRT:
            pass
        elif hw.has_cuda and settings.ENABLE_CUDA:
            pass
        # Remove AMD/Intel/Apple specific providers if they somehow appear
        candidates = [p for p in candidates if p not in ("ROCMExecutionProvider", "MIGraphXExecutionProvider", "CoreMLExecutionProvider")]
    elif hw.gpu_vendor == "amd":
        if hw.has_rocm and settings.ENABLE_ROCM:
            pass
        # Remove NVIDIA/Apple specific providers
        candidates = [p for p in candidates if p not in ("CUDAExecutionProvider", "TensorrtExecutionProvider", "CoreMLExecutionProvider")]
    elif hw.gpu_vendor == "intel":
        # Prefer OpenVINO on Intel
        candidates = [p for p in candidates if p not in ("CUDAExecutionProvider", "TensorrtExecutionProvider", "ROCMExecutionProvider", "MIGraphXExecutionProvider", "CoreMLExecutionProvider")]
    elif hw.gpu_vendor == "apple":
        # Prefer CoreML on Apple Silicon
        candidates = [p for p in candidates if p not in ("CUDAExecutionProvider", "TensorrtExecutionProvider", "ROCMExecutionProvider", "MIGraphXExecutionProvider")]

    # Respect user toggles
    if not settings.ENABLE_CUDA:
        candidates = [p for p in candidates if p != "CUDAExecutionProvider"]
    if not settings.ENABLE_TENSORRT:
        candidates = [p for p in candidates if p != "TensorrtExecutionProvider"]
    if not settings.ENABLE_ROCM:
        candidates = [p for p in candidates if p != "ROCMExecutionProvider"]
    if not settings.ENABLE_MIGRAPHX:
        candidates = [p for p in candidates if p != "MIGraphXExecutionProvider"]
    if not settings.ENABLE_OPENVINO:
        candidates = [p for p in candidates if p != "OpenVINOExecutionProvider"]
    if not settings.ENABLE_DIRECTML:
        candidates = [p for p in candidates if p != "DmlExecutionProvider"]
    if not settings.ENABLE_COREML:
        candidates = [p for p in candidates if p != "CoreMLExecutionProvider"]
    if not settings.ENABLE_VITISAI:
        candidates = [p for p in candidates if p != "VitisAIExecutionProvider"]
    if not settings.ENABLE_OPENCL:
        candidates = [p for p in candidates if p != "OpenCLExecutionProvider"]
    if not settings.CPU_FALLBACK:
        candidates = [p for p in candidates if p != "CPUExecutionProvider"]

    # Sort by priority score
    candidates = sorted(candidates, key=lambda p: _provider_score(p, hw))

    # Always ensure CPU fallback if enabled and available
    if not candidates and settings.CPU_FALLBACK and "CPUExecutionProvider" in available:
        candidates = ["CPUExecutionProvider"]
    if not candidates:
        candidates = available

    return candidates


def configure_onnx_session_options(provider: str) -> Dict[str, Any]:
    """Provider-specific session options."""
    opts: Dict[str, Any] = {}
    if provider == "OpenVINOExecutionProvider":
        opts = {
            "device_type": "GPU" if settings.GPU_ENABLED else "CPU",
            "precision": "FP16" if settings.GPU_ENABLED else "FP32",
        }
    elif provider == "CUDAExecutionProvider":
        opts = {
            "device_id": 0,
            "arena_extend_strategy": "kNextPowerOfTwo",
            "cuda_mem_limit": 2 * 1024 * 1024 * 1024,  # 2 GB
        }
    elif provider == "ROCMExecutionProvider":
        opts = {
            "device_id": 0,
            "miopen_conv_exhaustive_search": False,
        }
    elif provider == "TensorrtExecutionProvider":
        opts = {
            "device_id": 0,
            "trt_max_workspace_size": 2 * 1024 * 1024 * 1024,
            "trt_fp16_enable": True,
        }
    elif provider == "DmlExecutionProvider":
        opts = {
            "device_id": 0,
        }
    elif provider == "CoreMLExecutionProvider":
        opts = {
            "model_format": "MLProgram",
            "use_cpu_only": False,
        }
    return opts


def summarize_hardware(hw: Optional[HardwareInfo] = None) -> Dict[str, Any]:
    if hw is None:
        hw = get_hardware_info()
    return {
        "platform": hw.platform,
        "cpu": hw.cpu_name,
        "cpu_count": hw.cpu_count,
        "gpu_vendor": hw.gpu_vendor,
        "gpu_name": hw.gpu_name,
        "gpu_memory_mb": hw.gpu_memory_mb,
        "onnx_providers": ort.get_available_providers(),
        "selected_providers": build_provider_priority(hw, ort.get_available_providers()),
    }
