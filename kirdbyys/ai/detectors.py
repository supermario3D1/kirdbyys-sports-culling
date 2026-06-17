"""Object detection and subject classification for sports imagery."""
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple, Optional
from kirdbyys.ai.models import get_model_manager, preprocess_yolo
from kirdbyys.config import settings
import os

# YOLOv8 COCO class names (80 classes)
YOLO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

# Map common COCO-like indices to sports classes
SPORTS_BALL_NAMES = {"sports ball", "ball", "football", "soccer ball"}
PERSON_NAMES = {"person", "athlete", "man", "woman", "human"}
GOALPOST_NAMES = {"goal", "net", "goalpost"}

class YOLODetector:
    """YOLOv8 object detection using ONNX."""
    
    def __init__(self, model_name: str = "yolov8n", input_size: int = 640):
        self.model_name = model_name
        self.input_size = input_size
        self.session = None
        self._ensure_model()
    
    def _ensure_model(self):
        # Use Ultralytics YOLOv8n-oiv7 ONNX if available
        mgr = get_model_manager()
        model_path = settings.MODELS_DIR / f"{self.model_name}.onnx"
        if not model_path.exists():
            try:
                mgr.download_model(
                    settings.YOLOV8N_ONNX_URL,
                    f"{self.model_name}.onnx"
                )
            except Exception as e:
                print(f"[Kirdbyys] Could not download YOLO model: {e}")
                raise
        self.session = mgr.load(self.model_name, model_path)
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.25) -> Dict[str, Any]:
        if self.session is None:
            return {"objects": [], "has_ball": False, "has_person": False, "has_goalpost": False}
        
        orig_h, orig_w = image.shape[:2]
        tensor, scale, pad = preprocess_yolo(image, self.input_size)
        outputs = model_manager.run(self.model_name, {self.session.get_inputs()[0].name: tensor})
        
        detections = []
        # YOLOv8 ONNX outputs shape [1, 84, 8400] (xywh + conf + 80 classes) or similar
        predictions = outputs[0]
        if predictions.shape[0] == 1:
            predictions = predictions[0]
        if predictions.shape[0] > predictions.shape[1]:
            predictions = predictions.T
        
        # predictions now [8400, 84]
        boxes = predictions[:, :4]
        scores = predictions[:, 4:5]
        classes = predictions[:, 5:]
        
        # Convert to xyxy and scale back
        for i in range(len(boxes)):
            conf = float(scores[i])
            if conf < conf_threshold:
                continue
            cls_idx = int(np.argmax(classes[i]))
            cls_conf = float(classes[i][cls_idx])
            if cls_conf < conf_threshold:
                continue
            
            x, y, w, h = boxes[i]
            # Undo letterbox
            x1 = (x - w/2 - pad[1]) / scale[0]
            y1 = (y - h/2 - pad[0]) / scale[0]
            x2 = (x + w/2 - pad[1]) / scale[0]
            y2 = (y + h/2 - pad[0]) / scale[0]
            
            # Clamp
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            
            class_name = YOLO_CLASSES[cls_idx] if cls_idx < len(YOLO_CLASSES) else f"class_{cls_idx}"
            detections.append({
                "class": class_name,
                "confidence": round(conf, 4),
                "class_conf": round(cls_conf, 4),
                "bbox": [float(x1), float(y1), float(x2), float(y2)],
                "area": float((x2-x1)*(y2-y1))
            })
        
        has_ball = any(d["class"].lower() in SPORTS_BALL_NAMES for d in detections)
        has_person = any(d["class"].lower() in PERSON_NAMES for d in detections)
        has_goalpost = any(d["class"].lower() in GOALPOST_NAMES for d in detections)
        
        return {
            "objects": detections,
            "has_ball": has_ball,
            "has_person": has_person,
            "has_goalpost": has_goalpost,
            "person_count": sum(1 for d in detections if d["class"].lower() in PERSON_NAMES),
            "ball_count": sum(1 for d in detections if d["class"].lower() in SPORTS_BALL_NAMES),
            "dominant_class": detections[0]["class"] if detections else "none"
        }

class SoccerMomentClassifier:
    """Heuristic + learned soccer moment classifier."""
    
    def __init__(self):
        self.moment_rules = [
            ("goal_celebration", lambda d: d.get("person_count", 0) >= 3 and d.get("has_ball", False) is False and (d.get("emotional_density", 0) > 0.35 or d.get("action_intensity", 0) > 0.5)),
            ("goal", lambda d: d.get("ball_count", 0) > 0 and d.get("has_goalpost", False) and d.get("action_intensity", 0) > 0.8),
            ("goalkeeper_save", lambda d: d.get("has_ball", False) and d.get("goalkeeper_present", False) and d.get("action_intensity", 0) > 0.7),
            ("penalty_save", lambda d: d.get("goalkeeper_present", False) and d.get("ball_near_goal", False) and d.get("action_intensity", 0) > 0.75),
            ("slide_tackle", lambda d: d.get("ground_contact_ratio", 0) > 0.15 and d.get("person_count", 0) >= 2 and d.get("action_intensity", 0) > 0.65),
            ("tackle", lambda d: d.get("person_count", 0) >= 2 and d.get("players_close", False) and d.get("action_intensity", 0) > 0.6),
            ("header", lambda d: d.get("ball_airborne", False) and d.get("players_leaping", 0) > 0 and d.get("action_intensity", 0) > 0.6),
            ("shot_on_goal", lambda d: d.get("has_ball", False) and d.get("has_goalpost", False) and d.get("action_intensity", 0) > 0.65),
            ("dribble", lambda d: d.get("has_ball", False) and d.get("person_count", 0) == 1 and d.get("action_intensity", 0) > 0.45),
            ("player_posession", lambda d: d.get("has_ball", False) and d.get("person_count", 0) >= 1),
            ("ball_in_play", lambda d: d.get("has_ball", False)),
        ]
    
    def classify(self, detection_data: Dict[str, Any], action_features: Dict[str, Any]) -> List[str]:
        """Return list of moment labels for an image."""
        merged = {**detection_data, **action_features}
        moments = []
        for label, rule in self.moment_rules:
            try:
                if rule(merged):
                    moments.append(label)
                    break  # take highest-priority match
            except Exception:
                continue
        if not moments:
            moments.append("static_scene")
        return moments

def detect_subjects(image: np.ndarray, detector: Optional[YOLODetector] = None) -> Dict[str, Any]:
    """High-level subject detection wrapper."""
    if detector is None:
        detector = YOLODetector()
    return detector.detect(image)