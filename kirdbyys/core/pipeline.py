"""Main image analysis pipeline."""
import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ExifTags
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import base64
import pickle
import io
import traceback

from kirdbyys.config import settings
from kirdbyys.ai.detectors import YOLODetector, SoccerMomentClassifier, detect_subjects
from kirdbyys.ai.analyzers import TechnicalAnalyzer, CompositionAnalyzer, ActionAnalyzer, estimate_emotional_density, estimate_goalkeeper_present
from kirdbyys.ai.ranking import RankingEngine
from kirdbyys.ai.duplicate import DuplicateDetector

class ImagePipeline:
    """End-to-end analysis pipeline for a single image."""
    
    def __init__(self, detector: Optional[YOLODetector] = None):
        self.detector = detector or YOLODetector()
        self.moment_classifier = SoccerMomentClassifier()
        self.tech = TechnicalAnalyzer()
        self.comp = CompositionAnalyzer()
        self.action = ActionAnalyzer()
        self.dup = DuplicateDetector()
    
    def load_image(self, path: str) -> Optional[np.ndarray]:
        """Load image, supporting RAW via rawpy if available."""
        ext = Path(path).suffix.lower()
        try:
            if ext in settings.SUPPORTED_RAW_FORMATS:
                try:
                    import rawpy
                    with rawpy.imread(path) as raw:
                        rgb = raw.postprocess(no_auto_bright=True, use_camera_wb=True, output_color=rawpy.ColorSpace.sRGB)
                    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    print(f"[Kirdbyys] RAW fallback to OpenCV for {path}: {e}")
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                return None
            return img
        except Exception as e:
            print(f"[Kirdbyys] Failed to load {path}: {e}")
            return None
    
    def extract_exif(self, path: str) -> Dict[str, Any]:
        metadata = {}
        try:
            img = Image.open(path)
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag in {"DateTimeOriginal", "DateTime", "Make", "Model", "LensModel", "ISOSpeedRatings", 
                               "FNumber", "ExposureTime", "FocalLength", "ImageWidth", "ImageLength"}:
                        metadata[tag] = value
            metadata["width"] = img.width
            metadata["height"] = img.height
            img.close()
        except Exception as e:
            metadata["error"] = str(e)
        return metadata
    
    def parse_datetime(self, s: str) -> Optional[datetime]:
        try:
            return datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
        except Exception:
            return None
    
    def create_thumbnails(self, image: np.ndarray, image_id: int, filename: str) -> Tuple[str, str]:
        cache_dir = settings.CACHE_DIR / "thumbnails"
        preview_dir = settings.CACHE_DIR / "previews"
        cache_dir.mkdir(parents=True, exist_ok=True)
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        thumb_path = cache_dir / f"{image_id}_{filename}.jpg"
        preview_path = preview_dir / f"{image_id}_{filename}.jpg"
        
        # Thumbnail
        h, w = image.shape[:2]
        scale = settings.THUMBNAIL_SIZE / max(h, w)
        thumb = cv2.resize(image, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(thumb_path), thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        
        # Preview
        scale = min(1.0, settings.PREVIEW_SIZE / max(h, w))
        preview = cv2.resize(image, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(preview_path), preview, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        
        return str(thumb_path), str(preview_path)
    
    def analyze_image(self, path: str, image_id: int, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        result = {
            "id": image_id,
            "original_path": path,
            "filename": Path(path).name,
            "processed": False,
            "processing_error": None
        }
        
        try:
            # Metadata
            exif = self.extract_exif(path)
            result["width"] = exif.get("width")
            result["height"] = exif.get("height")
            result["capture_time"] = self.parse_datetime(exif.get("DateTimeOriginal", exif.get("DateTime", ""))) if exif.get("DateTimeOriginal") or exif.get("DateTime") else None
            result["camera_make"] = exif.get("Make")
            result["camera_model"] = exif.get("Model")
            result["lens"] = exif.get("LensModel")
            result["iso"] = exif.get("ISOSpeedRatings")
            result["aperture"] = str(exif.get("FNumber")) if exif.get("FNumber") else None
            result["shutter_speed"] = str(exif.get("ExposureTime")) if exif.get("ExposureTime") else None
            result["focal_length"] = str(exif.get("FocalLength")) if exif.get("FocalLength") else None
            
            # Load image
            image_bgr = self.load_image(path)
            if image_bgr is None:
                raise ValueError("Could not load image")
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            
            # Resize for analysis if needed
            h, w = image_rgb.shape[:2]
            if max(h, w) > settings.IMAGE_RESIZE_LONG_EDGE:
                scale = settings.IMAGE_RESIZE_LONG_EDGE / max(h, w)
                image_rgb = cv2.resize(image_rgb, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
            
            # Create thumbnails
            thumb_path, preview_path = self.create_thumbnails(image_bgr, image_id, Path(path).stem[:40])
            result["thumbnail_path"] = thumb_path
            result["preview_path"] = preview_path
            
            # Perceptual hash + feature vector
            result["perceptual_hash"] = self.dup.compute_hash(image_rgb)
            feat = self.dup.compute_feature_vector(image_rgb)
            result["feature_vector"] = base64.b64encode(pickle.dumps(feat)).decode("utf-8")
            
            # Detection
            detection_data = detect_subjects(image_rgb, self.detector)
            result["detected_labels"] = [d["class"] for d in detection_data.get("objects", [])]
            result["has_ball"] = detection_data.get("has_ball", False)
            result["person_count"] = detection_data.get("person_count", 0)
            
            # Action features for moment classification
            action_features = self.action.analyze(image_rgb, detection_data.get("objects", []))
            emotional_density = estimate_emotional_density(image_rgb, detection_data.get("objects", []))
            goalkeeper_present = estimate_goalkeeper_present(image_rgb, detection_data.get("objects", []))
            
            # Compute heuristic features for moment rules
            moment_input = {
                "person_count": detection_data.get("person_count", 0),
                "has_ball": detection_data.get("has_ball", False),
                "has_goalpost": detection_data.get("has_goalpost", False),
                "ball_count": detection_data.get("ball_count", 0),
                "action_intensity": action_features["score"] / 100.0,
                "emotional_density": emotional_density,
                "goalkeeper_present": goalkeeper_present,
                "ball_near_goal": detection_data.get("has_goalpost", False) and detection_data.get("has_ball", False),
                "ground_contact_ratio": self._estimate_ground_contact(detection_data.get("objects", [])),
                "players_close": action_features["breakdown"].get("player_interaction", 0) > 60,
                "ball_airborne": False,  # placeholder; could be estimated with pose
                "players_leaping": 0
            }
            moments = self.moment_classifier.classify(detection_data, moment_input)
            result["moments"] = moments
            
            # Technical analysis
            tech = self.tech.analyze(image_rgb)
            result["technical_score"] = tech["score"]
            result["quality_breakdown"] = tech["breakdown"]
            
            # Composition analysis
            comp = self.comp.analyze(image_rgb, detection_data.get("objects", []))
            result["composition_score"] = comp["score"]
            result["composition_breakdown"] = comp["breakdown"]
            
            # Action / storytelling analysis
            # Override action features with moments
            action_features = self.action.analyze(image_rgb, detection_data.get("objects", []), moments=moments)
            result["action_score"] = action_features["score"]
            result["action_breakdown"] = action_features["breakdown"]
            
            # Storytelling score derived from moments + emotional density + action
            story = 0
            for m in moments:
                story = max(story, settings.MOMENT_PRIORITY.get(m, 0.3) * 100)
            story = story * 0.6 + emotional_density * 30 + action_features["score"] * 0.1
            result["storytelling_score"] = round(min(100, story), 3)
            
            result["processed"] = True
            if progress_callback:
                progress_callback()
        except Exception as e:
            result["processed"] = False
            result["processing_error"] = f"{str(e)}\n{traceback.format_exc()}"
            print(f"[Kirdbyys] Error analyzing image {path}: {e}")
        
        return result
    
    def _estimate_ground_contact(self, detections: List[Dict[str, Any]]) -> float:
        """Estimate fraction of people whose bottom edge is near frame bottom."""
        if not detections:
            return 0.0
        people = [d for d in detections if any(x in d.get("class", "").lower() for x in ["person", "athlete", "man", "woman"])]
        if not people:
            return 0.0
        # Need original dimensions; use bbox normalized
        ground = 0
        for p in people:
            _, y2, _, _ = p.get("bbox", [0,0,0,0])
            # approximate: if y2 is near 1.0 -> ground contact
            if y2 > 0.8:
                ground += 1
        return ground / len(people)
    
    def rank_project(self, images: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None, top_n: int = 20) -> Dict[str, Any]:
        engine = RankingEngine(weights)
        ranked = engine.rank([dict(img) for img in images])
        # Duplicate suppression
        ranked = self.dup.suppress_duplicates(ranked)
        # Select top N only from representatives
        representatives = [img for img in ranked if img.get("is_representative", True)]
        selected = engine.select_top_n(representatives, top_n)
        for img in ranked:
            img["selected"] = img in selected
        return {
            "ranked_images": ranked,
            "selected_images": selected,
            "weights": engine.weights
        }

def build_explanation(image: Dict[str, Any]) -> str:
    """Convenience wrapper for explanation."""
    engine = RankingEngine(image.get("weights"))
    scores = {
        "technical_quality": image.get("technical_score", 0) / 100.0,
        "action_value": image.get("action_score", 0) / 100.0,
        "storytelling": image.get("storytelling_score", 0) / 100.0,
        "composition": image.get("composition_score", 0) / 100.0
    }
    return engine._explain(image, scores)