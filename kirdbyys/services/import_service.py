"""Import service for folders and drag-and-drop images."""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from kirdbyys.config import settings

class ImportService:
    """Import images from source folders into a project workspace."""
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.project_dir = settings.DATA_DIR / f"project_{project_id}"
        self.project_dir.mkdir(parents=True, exist_ok=True)
    
    def is_supported(self, path: str) -> bool:
        ext = Path(path).suffix.lower()
        return ext in settings.SUPPORTED_IMAGE_FORMATS or ext in settings.SUPPORTED_RAW_FORMATS
    
    def scan_folder(self, folder: str) -> List[str]:
        folder_path = Path(folder)
        paths = []
        for ext in settings.SUPPORTED_IMAGE_FORMATS + settings.SUPPORTED_RAW_FORMATS:
            paths.extend(folder_path.rglob(f"*{ext}"))
            paths.extend(folder_path.rglob(f"*{ext.upper()}"))
        # Deduplicate and sort
        paths = sorted(set(str(p) for p in paths if p.is_file()))
        return paths
    
    def import_paths(self, paths: List[str], copy: bool = False) -> List[Dict[str, Any]]:
        imported = []
        for src in paths:
            if not self.is_supported(src):
                continue
            try:
                src_path = Path(src)
                dest = self.project_dir / src_path.name
                # Handle duplicate filenames
                counter = 1
                stem = dest.stem
                while dest.exists():
                    dest = self.project_dir / f"{stem}_{counter}{dest.suffix}"
                    counter += 1
                if copy:
                    shutil.copy2(src, dest)
                else:
                    # For safety, default to copy to not modify originals
                    shutil.copy2(src, dest)
                imported.append({
                    "original_path": str(src),
                    "project_path": str(dest),
                    "filename": dest.name,
                    "file_size": dest.stat().st_size
                })
            except Exception as e:
                print(f"[Kirdbyys] Import failed for {src}: {e}")
        return imported
    
    def import_folder(self, folder: str, copy: bool = False) -> List[Dict[str, Any]]:
        paths = self.scan_folder(folder)
        return self.import_paths(paths, copy=copy)
    
    async def import_async(self, folder: str, progress_callback: Optional[callable] = None, copy: bool = False) -> List[Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        paths = await loop.run_in_executor(None, self.scan_folder, folder)
        imported = await loop.run_in_executor(None, self.import_paths, paths, copy)
        if progress_callback:
            for _ in imported:
                await progress_callback()
        return imported