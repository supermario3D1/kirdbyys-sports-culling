"""Configuration for Kirdbyys Sports Culling Tool."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Dict, Any

class Settings(BaseSettings):
    APP_NAME: str = "Kirdbyys Sports Culling Tool"
    APP_VERSION: str = "1.0.0"
    APP_TAGLINE: str = "AI-Powered Sports Photography Culling"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent
    MODELS_DIR: Path = BASE_DIR / "models"
    CACHE_DIR: Path = BASE_DIR / "cache"
    DATA_DIR: Path = BASE_DIR / "data"
    TEMP_DIR: Path = BASE_DIR / "temp"
    EXPORT_DIR: Path = BASE_DIR / "exports"
    UI_STATIC_DIR: Path = BASE_DIR / "ui" / "static"
    UI_TEMPLATES_DIR: Path = BASE_DIR / "ui" / "templates"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./kirdbyys/data/kirdbyys.db"
    SYNC_DATABASE_URL: str = "sqlite:///./kirdbyys/data/kirdbyys.db"
    
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 7840
    
    # Processing
    BATCH_SIZE: int = 8
    MAX_WORKERS: int = os.cpu_count() or 4
    GPU_ENABLED: bool = True
    CPU_FALLBACK: bool = True
    # ONNX execution provider toggles (auto-detect if not forced)
    ENABLE_CUDA: bool = True          # NVIDIA GPUs
    ENABLE_TENSORRT: bool = False     # NVIDIA TensorRT (optional, requires setup)
    ENABLE_ROCM: bool = True          # AMD GPUs on Linux
    ENABLE_OPENVINO: bool = True      # Intel CPUs/GPUs and cross-platform optimization
    ENABLE_DIRECTML: bool = True      # Windows GPU/CPU via DirectML
    ENABLE_COREML: bool = True        # Apple Silicon Neural Engine
    ENABLE_MIGRAPHX: bool = False     # AMD MIGraphX (optional)
    ENABLE_VITISAI: bool = False      # Xilinx/AMD Vitis AI (optional)
    ENABLE_OPENCL: bool = True        # Generic OpenCL fallback
    IMAGE_RESIZE_LONG_EDGE: int = 1280
    THUMBNAIL_SIZE: int = 320
    PREVIEW_SIZE: int = 1280
    
    # Supported formats
    SUPPORTED_RAW_FORMATS: List[str] = [".cr2", ".cr3", ".nef", ".arw", ".orf", ".raf", ".dng", ".rw2"]
    SUPPORTED_IMAGE_FORMATS: List[str] = [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp"]
    
    # Model URLs (open-source, local-only)
    YOLOV8N_ONNX_URL: str = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.onnx"
    MEGAASSETS_AESTHETIC_URL: str = "https://github.com/youthjoey/aesthetic_prediction/releases/download/v1.0/aesthetic_model_mobilenetv2.onnx"
    
    # Default scoring weights (configurable per-job)
    DEFAULT_WEIGHTS: Dict[str, float] = {
        "technical_quality": 0.25,
        "action_value": 0.35,
        "storytelling": 0.25,
        "composition": 0.15
    }
    
    # Soccer moment priorities (higher = more publishable)
    MOMENT_PRIORITY: Dict[str, float] = {
        "goal": 1.00,
        "goal_celebration": 1.00,
        "game_winning_moment": 0.98,
        "penalty_save": 0.95,
        "goalkeeper_save": 0.92,
        "tackle": 0.85,
        "slide_tackle": 0.88,
        "header": 0.86,
        "shot_on_goal": 0.90,
        "dribble": 0.75,
        "pass": 0.55,
        "player_posession": 0.70,
        "ball_in_play": 0.60,
        "coach_reaction": 0.80,
        "crowd_reaction": 0.78,
        "team_huddle": 0.72,
        "substitution": 0.50,
        "warmup": 0.30,
        "static_portrait": 0.25,
        "empty_field": 0.10
    }
    
    # Subject class mapping from YOLOv8 COCO model
    RELEVANT_CLASSES: List[str] = [
        "person", "sports ball", "baseball bat", "baseball glove", "tennis racket",
        "skateboard", "surfboard", "skis", "snowboard"
    ]
    
    # Duplicate detection
    DUPLICATE_HASH_SIZE: int = 16
    DUPLICATE_THRESHOLD: float = 0.92
    BURST_SIMILARITY_THRESHOLD: float = 0.85
    BURST_TIME_DELTA_SECONDS: float = 2.0
    
    # Lightroom
    XMP_RATING_NAMESPACE: str = "http://ns.adobe.com/xap/1.0/"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Ensure directories exist
for d in [settings.MODELS_DIR, settings.CACHE_DIR, settings.DATA_DIR, 
          settings.TEMP_DIR, settings.EXPORT_DIR]:
    d.mkdir(parents=True, exist_ok=True)