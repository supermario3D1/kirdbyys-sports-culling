# Kirdbyys System Architecture

## Overview

Kirdbyys is a **local, self-contained desktop-class web application** for AI-driven sports photography culling. It combines a **FastAPI backend**, an **ONNX-based AI inference pipeline**, and a **modern single-page web UI**.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web UI (Browser / Desktop)               │
│            Dark/Light Mode · Dashboards · Gallery           │
└─────────────────────────────────────────────────────────────┘
                              │ REST + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  Projects API · Import API · Analysis API · Export API · XMP  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
  ┌──────────┐        ┌──────────────┐       ┌──────────┐
  │  SQLite  │        │  Job Manager │       │  Cache   │
  │  (metadata)│      │ (async tasks)│      │ (thumbnails)│
  └──────────┘        └──────────────┘       └──────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │          Kirdbyys AI Pipeline             │
        │  ┌─────────┐ ┌──────────┐ ┌──────────┐   │
        │  │ YOLOv8  │ │ Technical│ │Composition│   │
        │  │ Detection│ │ Analyzer │ │ Analyzer │   │
        │  └─────────┘ └──────────┘ └──────────┘   │
        │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
        │  │  Action  │ │ Storytelling│ │ Duplicate│  │
        │  │ Analyzer │ │  Scoring    │ │ Detector │  │
        │  └──────────┘ └──────────┘ └──────────┘   │
        └──────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │        ONNX Runtime Execution             │
        │  TensorRT → CUDA → ROCm → MIGraphX       │
        │  → CoreML → OpenVINO → DirectML → CPU     │
        └──────────────────────────────────────────┘
```

## Components

### 1. Frontend
- **Technology**: Vanilla HTML5, CSS3, JavaScript
- **No build step required** for the core application
- **Features**: drag-and-drop, dark/light mode, dashboards, galleries, image detail modal, duplicate review, export panel
- **Why vanilla**: faster iteration, easier debugging, no dependency lock-in, lighter install footprint

### 2. Backend API (FastAPI)
- **Technology**: FastAPI + Uvicorn + SQLAlchemy Async
- **State**: RESTful endpoints for projects, images, analysis, jobs, export
- **Concurrency**: Async task queue with ThreadPoolExecutor for CPU/ONNX inference
- **Files**: static file serving for thumbnails, previews, logos, and app icons

### 3. Database (SQLite)
- Stores project metadata, per-image scores, EXIF, duplicate groups, and job status
- Async `aiosqlite` driver for non-blocking API
- Sync engine for batch operations and model creation

### 4. AI Pipeline
- **YOLOv8n ONNX** for object detection (players, ball, etc.)
- **Classical CV + custom heuristics** for technical quality, composition, and action
- **Soccer Moment Classifier** for high-value moments (goal, save, tackle, celebration, etc.)
- **Ranking Engine** with configurable weights
- **Duplicate Detector** using perceptual hashing and feature vectors

### 5. Caching & Performance
- Thumbnails and previews cached on disk
- Analysis results persisted in DB
- Incremental / resumable jobs: already-processed images are skipped
- Batch inference with configurable batch size

### 6. Execution Providers
The `kirdbyys.ai.hardware` module detects the CPU/GPU vendor and builds a provider priority list:

| Hardware | Priority Providers |
|----------|--------------------|
| NVIDIA GPU | TensorRT → CUDA → DirectML → CPU |
| AMD GPU (Linux) | ROCm → MIGraphX → OpenVINO → CPU |
| AMD GPU (Windows) | DirectML → OpenVINO → CPU |
| Intel GPU/CPU | OpenVINO → CPU |
| Apple Silicon | CoreML → CPU |
| Generic CPU | OpenVINO (if Intel/AMD) → CPU |

All providers are configurable via `.env` toggles.

## Data Flow

1. User creates a project and imports a folder
2. `ImportService` copies supported files into project workspace
3. Images are registered in SQLite with `processed = False`
4. User starts analysis (or auto-starts on import)
5. `JobManager` spawns a background job
6. Images are processed in batches through the `ImagePipeline`
7. Each image receives technical, composition, action, and storytelling scores
8. `RankingEngine` ranks all images and selects top N
9. `DuplicateDetector` suppresses duplicates/bursts
10. Results are written back to DB and displayed in UI
11. User exports selection via CSV, Excel, XMP, copy/move, or PDF

## Scalability on Target Hardware

- **AMD Ryzen 7 7840U**: 8 cores / 16 threads ideal for parallel batch processing
- **Radeon 780M iGPU**: optional ROCm inference; CPU fallback is highly optimized
- **32 GB RAM**: allows large batches without swapping
- **Fedora Linux**: supports ROCm and OpenVINO packages natively

## Design Principles

- **Local-first**: no cloud, no API keys, no subscriptions
- **Modular**: each analyzer is independent; future sports can be added without rewrites
- **Explainable**: every image gets a human-readable explanation
- **Configurable**: weights, batch sizes, thresholds, and export presets are user-configurable
- **Professional**: dark/light UI, fast feedback, responsive during processing
