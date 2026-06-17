"""Job manager for async background processing."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from kirdbyys.config import settings
from kirdbyys.core.pipeline import ImagePipeline

class JobManager:
    """Manages running, queued, and completed analysis jobs."""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or settings.MAX_WORKERS
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.running = {}
    
    def create_job(self, job_type: str, project_id: int, total_items: int) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "id": job_id,
            "job_type": job_type,
            "project_id": project_id,
            "status": "queued",
            "progress": 0.0,
            "total_items": total_items,
            "processed_items": 0,
            "message": "Queued",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "error_log": None
        }
        return job_id
    
    def update_job(self, job_id: str, progress: Optional[float] = None, status: Optional[str] = None, message: Optional[str] = None, error: Optional[str] = None):
        if job_id not in self.jobs:
            return
        now = datetime.utcnow().isoformat()
        if progress is not None:
            self.jobs[job_id]["progress"] = progress
            self.jobs[job_id]["processed_items"] = int(progress * self.jobs[job_id]["total_items"])
        if status:
            self.jobs[job_id]["status"] = status
        if message:
            self.jobs[job_id]["message"] = message
        if error:
            self.jobs[job_id]["error_log"] = error
        self.jobs[job_id]["updated_at"] = now
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)
    
    def list_jobs(self, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        jobs = list(self.jobs.values())
        if project_id is not None:
            jobs = [j for j in jobs if j["project_id"] == project_id]
        return sorted(jobs, key=lambda x: x["created_at"], reverse=True)
    
    async def run_analysis(self, job_id: str, image_paths: List[str], db_images: List[Dict[str, Any]], pipeline: ImagePipeline, on_item_complete: Optional[Callable] = None):
        """Run analysis in thread pool with progress updates."""
        self.update_job(job_id, status="running", message="Starting analysis...")
        total = len(image_paths)
        self.jobs[job_id]["total_items"] = total
        
        loop = asyncio.get_event_loop()
        results = []
        
        def progress_step(idx):
            p = (idx + 1) / total
            self.update_job(job_id, progress=p, message=f"Analyzed {idx+1}/{total} images")
        
        # Process in batches to avoid memory explosion
        batch_size = settings.BATCH_SIZE
        for i in range(0, total, batch_size):
            batch_paths = image_paths[i:i+batch_size]
            batch_db = db_images[i:i+batch_size]
            futures = []
            for path, db_img in zip(batch_paths, batch_db):
                future = loop.run_in_executor(
                    self.executor,
                    pipeline.analyze_image,
                    path,
                    db_img["id"],
                    None
                )
                futures.append(future)
            batch_results = await asyncio.gather(*futures, return_exceptions=True)
            for idx, res in enumerate(batch_results):
                if isinstance(res, Exception):
                    results.append({
                        "id": batch_db[idx]["id"],
                        "original_path": batch_paths[idx],
                        "processed": False,
                        "processing_error": str(res)
                    })
                else:
                    results.append(res)
                if on_item_complete:
                    await on_item_complete(batch_db[idx]["id"], res)
                progress_step(i + idx)
        
        self.update_job(job_id, progress=1.0, status="complete", message=f"Analysis complete: {total} images")
        return results
    
    def cancel_job(self, job_id: str) -> bool:
        if job_id in self.jobs and self.jobs[job_id]["status"] in ("queued", "running"):
            self.update_job(job_id, status="cancelled", message="Cancelled by user")
            return True
        return False

# Global job manager instance
job_manager = JobManager()