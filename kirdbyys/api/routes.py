"""FastAPI routes for Kirdbyys."""
import os
import json
import base64
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import joinedload

from kirdbyys.config import settings
from kirdbyys.core.database import (
    init_db, AsyncSessionLocal, Project, Image, Job, DuplicateGroup, ExportPreset, Base, sync_engine
)
from kirdbyys.core.pipeline import ImagePipeline, build_explanation
from kirdbyys.core.job_manager import job_manager
from kirdbyys.ai.hardware import get_hardware_info, summarize_hardware
from kirdbyys.ai.ranking import RankingEngine
from kirdbyys.ai.duplicate import DuplicateDetector
from kirdbyys.ai.hardware import get_hardware_info
from kirdbyys.services.import_service import ImportService
from kirdbyys.services.export_service import ExportService
from kirdbyys.services.lightroom import LightroomService

router = APIRouter()
pipeline = ImagePipeline()

# --- Pydantic schemas ---
class ProjectCreate(BaseModel):
    name: str
    sport: str = "soccer"
    source_folder: str
    weights: Optional[Dict[str, float]] = None
    target_selection_count: int = 20

class WeightsUpdate(BaseModel):
    weights: Dict[str, float]
    target_selection_count: Optional[int] = None

class ExportRequest(BaseModel):
    mode: str = "copy"  # copy, move, csv, xlsx, xmp, pdf
    top_n: int = 20
    destination: Optional[str] = None
    include_rejected: bool = False

class AnalyzeRequest(BaseModel):
    project_id: int
    weights: Optional[Dict[str, float]] = None
    top_n: Optional[int] = None

# --- Helpers ---
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def image_to_dict(img: Image) -> Dict[str, Any]:
    capture_time = img.capture_time.isoformat() if img.capture_time else None
    return {
        "id": img.id,
        "project_id": img.project_id,
        "filename": img.filename,
        "original_path": img.original_path,
        "rel_path": img.rel_path,
        "file_size": img.file_size,
        "width": img.width,
        "height": img.height,
        "capture_time": capture_time,
        "camera_make": img.camera_make,
        "camera_model": img.camera_model,
        "lens": img.lens,
        "iso": img.iso,
        "aperture": img.aperture,
        "shutter_speed": img.shutter_speed,
        "focal_length": img.focal_length,
        "technical_score": img.technical_score,
        "action_score": img.action_score,
        "storytelling_score": img.storytelling_score,
        "composition_score": img.composition_score,
        "final_score": img.final_score,
        "rank": img.rank,
        "detected_labels": img.detected_labels or [],
        "moments": img.moments or [],
        "quality_breakdown": img.quality_breakdown or {},
        "composition_breakdown": img.composition_breakdown or {},
        "action_breakdown": img.action_breakdown or {},
        "explanation": img.explanation,
        "selected": img.selected,
        "rejected": img.rejected,
        "duplicate_group_id": img.duplicate_group_id,
        "is_best_in_group": img.is_best_in_group,
        "thumbnail_path": img.thumbnail_path,
        "preview_path": img.preview_path,
        "perceptual_hash": img.perceptual_hash,
        "processed": img.processed,
        "processing_error": img.processing_error
    }

# --- Project routes ---
@router.post("/projects")
async def create_project(data: ProjectCreate):
    async with AsyncSessionLocal() as session:
        weights = data.weights or dict(settings.DEFAULT_WEIGHTS)
        project = Project(
            name=data.name,
            sport=data.sport,
            source_folder=data.source_folder,
            weights=json.dumps(weights),
            target_selection_count=data.target_selection_count,
            status="idle"
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        return {"id": project.id, "name": project.name, "status": project.status}

@router.get("/projects")
async def list_projects():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project))
        projects = result.scalars().all()
        return [
            {
                "id": p.id, "name": p.name, "sport": p.sport,
                "source_folder": p.source_folder, "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "target_selection_count": p.target_selection_count,
                "weights": json.loads(p.weights) if p.weights else {}
            }
            for p in projects
        ]

@router.get("/projects/{project_id}")
async def get_project(project_id: int):
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return {
            "id": project.id, "name": project.name, "sport": project.sport,
            "source_folder": project.source_folder, "status": project.status,
            "weights": json.loads(project.weights) if project.weights else {},
            "target_selection_count": project.target_selection_count
        }

@router.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Image).where(Image.project_id == project_id))
        await session.execute(delete(Project).where(Project.id == project_id))
        await session.commit()
        return {"deleted": project_id}

# --- Import routes ---
@router.post("/projects/{project_id}/import")
async def import_folder(project_id: int, folder: str = Form(...), copy: bool = Form(True)):
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        project.status = "importing"
        await session.commit()
    
    service = ImportService(project_id)
    imported = service.import_folder(folder, copy=copy)
    
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        db_images = []
        for item in imported:
            img = Image(
                project_id=project_id,
                filename=item["filename"],
                original_path=item["original_path"],
                rel_path=str(Path(item["project_path"]).relative_to(settings.DATA_DIR)),
                file_size=item["file_size"],
                processed=False
            )
            db_images.append(img)
        session.add_all(db_images)
        project.status = "idle"
        await session.commit()
        for img in db_images:
            await session.refresh(img)
        return {"imported": len(db_images), "images": [image_to_dict(img) for img in db_images]}

@router.post("/projects/{project_id}/import-files")
async def import_files(project_id: int, files: List[UploadFile] = File(...)):
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
    
    service = ImportService(project_id)
    temp_paths = []
    for file in files:
        temp_path = settings.TEMP_DIR / file.filename
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        temp_paths.append(str(temp_path))
    
    imported = service.import_paths(temp_paths, copy=True)
    
    async with AsyncSessionLocal() as session:
        db_images = []
        for item in imported:
            img = Image(
                project_id=project_id,
                filename=item["filename"],
                original_path=item["original_path"],
                rel_path=str(Path(item["project_path"]).relative_to(settings.DATA_DIR)),
                file_size=item["file_size"],
                processed=False
            )
            db_images.append(img)
        session.add_all(db_images)
        await session.commit()
        for img in db_images:
            await session.refresh(img)
        return {"imported": len(db_images), "images": [image_to_dict(img) for img in db_images]}

# --- Analysis routes ---
@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: int, data: Optional[AnalyzeRequest] = None, background_tasks: BackgroundTasks = None):
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        result = await session.execute(select(Image).where(Image.project_id == project_id))
        images = result.scalars().all()
        if not images:
            raise HTTPException(400, "No images to analyze")
        project.status = "analyzing"
        await session.commit()
    
    job_id = job_manager.create_job("analyze", project_id, len(images))
    paths = [img.original_path for img in images]
    db_images = [{"id": img.id, "original_path": img.original_path} for img in images]
    
    async def on_item_complete(img_id: int, res: Dict[str, Any]):
        async with AsyncSessionLocal() as session:
            stmt = select(Image).where(Image.id == img_id)
            result = await session.execute(stmt)
            img = result.scalar_one_or_none()
            if not img:
                return
            img.technical_score = res.get("technical_score", 0) or 0
            img.action_score = res.get("action_score", 0) or 0
            img.storytelling_score = res.get("storytelling_score", 0) or 0
            img.composition_score = res.get("composition_score", 0) or 0
            img.detected_labels = res.get("detected_labels", [])
            img.moments = res.get("moments", [])
            img.quality_breakdown = res.get("quality_breakdown", {})
            img.composition_breakdown = res.get("composition_breakdown", {})
            img.action_breakdown = res.get("action_breakdown", {})
            img.thumbnail_path = res.get("thumbnail_path")
            img.preview_path = res.get("preview_path")
            img.perceptual_hash = res.get("perceptual_hash")
            img.feature_vector = res.get("feature_vector")
            img.processed = res.get("processed", False)
            img.processing_error = res.get("processing_error")
            img.width = res.get("width")
            img.height = res.get("height")
            if res.get("capture_time"):
                img.capture_time = res.get("capture_time")
            img.camera_make = res.get("camera_make")
            img.camera_model = res.get("camera_model")
            img.lens = res.get("lens")
            img.iso = res.get("iso")
            img.aperture = res.get("aperture")
            img.shutter_speed = res.get("shutter_speed")
            img.focal_length = res.get("focal_length")
            await session.commit()
    
    async def run_job():
        try:
            await job_manager.run_analysis(job_id, paths, db_images, pipeline, on_item_complete)
            # Now rank
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Image).where(Image.project_id == project_id))
                all_images = result.scalars().all()
                weights = json.loads(project.weights) if project.weights else dict(settings.DEFAULT_WEIGHTS)
                if data and data.weights:
                    weights = data.weights
                top_n = data.top_n if data and data.top_n else project.target_selection_count
                # Rank
                dicts = [image_to_dict(img) for img in all_images]
                ranked = pipeline.rank_project(dicts, weights=weights, top_n=top_n)
                # Save ranks and duplicate groups
                for r_img in ranked["ranked_images"]:
                    stmt = select(Image).where(Image.id == r_img["id"])
                    res2 = await session.execute(stmt)
                    db_img = res2.scalar_one_or_none()
                    if db_img:
                        db_img.final_score = r_img.get("final_score", 0)
                        db_img.rank = r_img.get("rank", 0)
                        db_img.selected = r_img.get("selected", False)
                        db_img.explanation = build_explanation(r_img)
                        db_img.duplicate_group_id = r_img.get("duplicate_group_id")
                        db_img.is_best_in_group = r_img.get("is_representative", True)
                project = await session.get(Project, project_id)
                project.status = "complete"
                await session.commit()
        except Exception as e:
            job_manager.update_job(job_id, status="error", error=str(e))
            async with AsyncSessionLocal() as session:
                project = await session.get(Project, project_id)
                project.status = "error"
                await session.commit()
    
    asyncio.create_task(run_job())
    return {"job_id": job_id, "status": "queued", "total_images": len(images)}

@router.get("/jobs")
async def list_jobs(project_id: Optional[int] = Query(None)):
    return job_manager.list_jobs(project_id)

@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    if job_manager.cancel_job(job_id):
        return {"cancelled": True}
    raise HTTPException(400, "Job not running")

# --- Images routes ---
@router.get("/projects/{project_id}/images")
async def get_images(
    project_id: int,
    sort_by: str = "final_score",
    order: str = "desc",
    limit: int = 100,
    offset: int = 0,
    selected_only: bool = False,
    duplicates_only: bool = False,
    moments: Optional[str] = None
):
    async with AsyncSessionLocal() as session:
        stmt = select(Image).where(Image.project_id == project_id)
        if selected_only:
            stmt = stmt.where(Image.selected == True)
        if duplicates_only:
            stmt = stmt.where(Image.duplicate_group_id != None)
        if moments:
            moment_list = [m.strip() for m in moments.split(",")]
            for m in moment_list:
                stmt = stmt.where(Image.moments.contains(m))
        
        if sort_by == "final_score":
            stmt = stmt.order_by(Image.final_score.desc() if order == "desc" else Image.final_score.asc())
        elif sort_by == "rank":
            stmt = stmt.order_by(Image.rank.asc() if order == "asc" else Image.rank.desc())
        elif sort_by == "action_score":
            stmt = stmt.order_by(Image.action_score.desc() if order == "desc" else Image.action_score.asc())
        elif sort_by == "storytelling_score":
            stmt = stmt.order_by(Image.storytelling_score.desc() if order == "desc" else Image.storytelling_score.asc())
        elif sort_by == "technical_score":
            stmt = stmt.order_by(Image.technical_score.desc() if order == "desc" else Image.technical_score.asc())
        elif sort_by == "composition_score":
            stmt = stmt.order_by(Image.composition_score.desc() if order == "desc" else Image.composition_score.asc())
        elif sort_by == "capture_time":
            stmt = stmt.order_by(Image.capture_time.desc() if order == "desc" else Image.capture_time.asc())
        else:
            stmt = stmt.order_by(Image.final_score.desc())
        
        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        images = result.scalars().all()
        return [image_to_dict(img) for img in images]

@router.get("/images/{image_id}")
async def get_image(image_id: int):
    async with AsyncSessionLocal() as session:
        img = await session.get(Image, image_id)
        if not img:
            raise HTTPException(404, "Image not found")
        return image_to_dict(img)

@router.get("/images/{image_id}/thumbnail")
async def get_thumbnail(image_id: int):
    async with AsyncSessionLocal() as session:
        img = await session.get(Image, image_id)
        if not img or not img.thumbnail_path or not Path(img.thumbnail_path).exists():
            raise HTTPException(404, "Thumbnail not found")
        return FileResponse(img.thumbnail_path)

@router.get("/images/{image_id}/preview")
async def get_preview(image_id: int):
    async with AsyncSessionLocal() as session:
        img = await session.get(Image, image_id)
        if not img or not img.preview_path or not Path(img.preview_path).exists():
            raise HTTPException(404, "Preview not found")
        return FileResponse(img.preview_path)

@router.post("/images/{image_id}/select")
async def toggle_selection(image_id: int, selected: bool = Form(True)):
    async with AsyncSessionLocal() as session:
        img = await session.get(Image, image_id)
        if not img:
            raise HTTPException(404, "Image not found")
        img.selected = selected
        img.rejected = not selected
        await session.commit()
        return image_to_dict(img)

# --- Weights and config ---
@router.put("/projects/{project_id}/weights")
async def update_weights(project_id: int, data: WeightsUpdate):
    async with AsyncSessionLocal() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        project.weights = json.dumps(data.weights)
        if data.target_selection_count is not None:
            project.target_selection_count = data.target_selection_count
        await session.commit()
        return {"weights": data.weights, "target_selection_count": project.target_selection_count}

# --- Export routes ---
@router.post("/projects/{project_id}/export")
async def export_project(project_id: int, data: ExportRequest):
    async with AsyncSessionLocal() as session:
        stmt = select(Image).where(Image.project_id == project_id)
        if not data.include_rejected:
            stmt = stmt.where(Image.rejected == False)
        if data.mode in ("copy", "move"):
            # Only selected for copy/move
            stmt = stmt.where(Image.selected == True)
        stmt = stmt.order_by(Image.final_score.desc())
        result = await session.execute(stmt)
        images = result.scalars().all()
        if data.top_n:
            images = images[:data.top_n]
        dicts = [image_to_dict(img) for img in images]
    
    service = ExportService(project_id)
    out_path = service.export(dicts, data.mode, data.destination)
    return {"path": out_path, "mode": data.mode, "count": len(dicts)}

@router.post("/projects/{project_id}/export-xmp")
async def export_xmp(project_id: int, sidecar_dir: Optional[str] = Form(None)):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Image).where(Image.project_id == project_id))
        images = result.scalars().all()
        dicts = [image_to_dict(img) for img in images]
    
    lr = LightroomService(settings.DATA_DIR / f"project_{project_id}")
    written = lr.write_sidecars(dicts, sidecar_dir)
    return {"written": len(written), "paths": written[:10]}

# --- Duplicate groups ---
@router.get("/projects/{project_id}/duplicates")
async def get_duplicates(project_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Image).where(Image.project_id == project_id).where(Image.duplicate_group_id != None))
        images = result.scalars().all()
        # Group by duplicate_group_id (which is the representative image id)
        groups = {}
        for img in images:
            gid = img.duplicate_group_id
            if gid not in groups:
                groups[gid] = {
                    "id": gid,
                    "representative_image_id": gid,
                    "similarity_score": img.final_score,
                    "frame_count": 0,
                    "image_ids": []
                }
            groups[gid]["frame_count"] += 1
            groups[gid]["image_ids"].append(img.id)
        # Mark best representative
        for g in groups.values():
            g["best_image_id"] = g["representative_image_id"]
        return list(groups.values())

# --- Stats ---
@router.get("/projects/{project_id}/stats")
async def project_stats(project_id: int):
    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count(Image.id)).where(Image.project_id == project_id))
        processed = await session.scalar(select(func.count(Image.id)).where(Image.project_id == project_id, Image.processed == True))
        selected = await session.scalar(select(func.count(Image.id)).where(Image.project_id == project_id, Image.selected == True))
        duplicates = await session.scalar(select(func.count(func.distinct(Image.duplicate_group_id))).where(Image.project_id == project_id).where(Image.duplicate_group_id != None))
        avg_score = await session.scalar(select(func.avg(Image.final_score)).where(Image.project_id == project_id))
        return {
            "total_images": total,
            "processed": processed,
            "selected": selected,
            "duplicate_groups": duplicates,
            "average_final_score": round(avg_score or 0, 2)
        }

# --- Search ---
@router.get("/projects/{project_id}/search")
async def search_images(project_id: int, q: str = Query(...), limit: int = 50):
    async with AsyncSessionLocal() as session:
        stmt = select(Image).where(Image.project_id == project_id).where(
            (Image.filename.ilike(f"%{q}%")) | (Image.moments.contains(q)) | (Image.explanation.ilike(f"%{q}%"))
        ).order_by(Image.final_score.desc()).limit(limit)
        result = await session.execute(stmt)
        images = result.scalars().all()
        return [image_to_dict(img) for img in images]

# --- System info ---
@router.get("/system/info")
async def system_info():
    summary = summarize_hardware()
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "max_workers": settings.MAX_WORKERS,
        "onnx_providers": summary["onnx_providers"],
        "recommended_providers": summary["selected_providers"],
        "gpu_enabled": settings.GPU_ENABLED,
        "cpu_fallback": settings.CPU_FALLBACK,
        "hardware": summary
    }
