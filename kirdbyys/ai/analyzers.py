"""Image quality, composition, and action analyzers."""
import numpy as np
import cv2
from scipy import ndimage, stats
from scipy.signal import convolve2d
from scipy.ndimage import sobel
from skimage import feature, measure, filters
from typing import Dict, Any, List, Tuple
from kirdbyys.config import settings
import warnings
warnings.filterwarnings("ignore")

class TechnicalAnalyzer:
    """Evaluate technical image quality with classical CV metrics."""
    
    def analyze(self, image: np.ndarray) -> Dict[str, Any]:
        if len(image.shape) == 2:
            gray = image.astype(np.float32)
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            rgb = image.astype(np.float32)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
        
        h, w = gray.shape
        
        # Sharpness via Laplacian variance and gradient magnitude
        lap = cv2.Laplacian(gray, cv2.CV_32F)
        lap_var = float(np.var(lap))
        gx = sobel(gray, axis=1)
        gy = sobel(gray, axis=0)
        grad_mag = np.sqrt(gx**2 + gy**2)
        gradient_score = self._scale(float(np.mean(grad_mag)), 0, 80, 0, 100)
        
        # MTF-like acutance: local standard deviation over 5x5 windows
        local_std = cv2.blur(gray**2, (5,5)) - cv2.blur(gray, (5,5))**2
        local_std = np.sqrt(np.maximum(local_std, 0))
        acutance = float(np.mean(local_std))
        
        # Focus via center-weighted sharpness (subject likely in center)
        cx, cy = w // 2, h // 2
        center_crop = gray[max(0, cy-h//4):min(h, cy+h//4), max(0, cx-w//4):min(w, cx+w//4)]
        center_sharp = float(np.var(cv2.Laplacian(center_crop, cv2.CV_32F))) if center_crop.size > 0 else 0
        
        # Motion blur via directional blur detection
        motion_blur = self._detect_motion_blur(gray)
        
        # Exposure / histogram
        hist = cv2.calcHist([gray.astype(np.uint8)], [0], None, [256], [0,256])
        hist = hist.flatten() / (h*w)
        mean_luma = float(np.mean(gray))
        std_luma = float(np.std(gray))
        
        # Clipping
        highlight_clip = float(np.sum(hist[-10:]))  # top 10 bins
        shadow_clip = float(np.sum(hist[:10]))       # bottom 10 bins
        
        # Dynamic range (percentile-based)
        dr = float(np.percentile(gray, 99) - np.percentile(gray, 1))
        
        # Noise estimate via median absolute deviation of Laplacian (high-pass residual)
        noise_est = float(np.median(np.abs(lap - np.median(lap))) / 0.6745)
        
        # Color quality
        if len(rgb.shape) == 3:
            hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV)
            saturation = float(np.mean(hsv[:,:,1]))
            color_balance = self._color_balance_score(rgb)
        else:
            saturation = 0
            color_balance = 50
        
        # Compression artifacts via blockiness (DCT grid 8x8 energy)
        artifacts = self._detect_artifacts(gray)
        
        # Overall technical score
        breakdown = {
            "sharpness": self._scale_log(lap_var, 50, 5000, 0, 100),
            "focus": self._scale_log(center_sharp, 20, 3000, 0, 100),
            "motion_blur": 100 - self._scale_log(motion_blur, 1, 50, 0, 100),
            "exposure": 100 - abs(mean_luma - 128) / 1.28,
            "dynamic_range": self._scale_log(dr, 20, 220, 0, 100),
            "highlight_clipping": 100 - self._scale_log(highlight_clip * 100, 0.5, 15, 0, 100),
            "shadow_clipping": 100 - self._scale_log(shadow_clip * 100, 0.5, 15, 0, 100),
            "noise": self._scale_log(noise_est, 1, 30, 100, 0),
            "color_quality": self._scale(saturation, 20, 180, 0, 100) * 0.5 + color_balance * 0.5,
            "white_balance": color_balance,
            "clarity": gradient_score,
            "compression_artifacts": 100 - artifacts
        }
        
        # Clamp
        breakdown = {k: max(0.0, min(100.0, v)) for k, v in breakdown.items()}
        weights = {
            "sharpness": 0.18, "focus": 0.14, "motion_blur": 0.12, "exposure": 0.12,
            "dynamic_range": 0.08, "highlight_clipping": 0.06, "shadow_clipping": 0.06,
            "noise": 0.10, "color_quality": 0.06, "white_balance": 0.04, "clarity": 0.04
        }
        overall = sum(breakdown.get(k, 0) * weights.get(k, 0) for k in weights) * (1.0 / sum(weights.values()))
        
        return {
            "score": round(max(0, min(100, overall)), 3),
            "breakdown": breakdown,
            "metadata": {
                "mean_luma": round(mean_luma, 2),
                "std_luma": round(std_luma, 2),
                "gradient_mean": round(float(np.mean(grad_mag)), 2),
                "noise_estimate": round(noise_est, 2)
            }
        }
    
    def _scale_log(self, val: float, low: float, high: float, out_min: float, out_max: float) -> float:
        val = max(1e-6, val)
        low = max(1e-6, low)
        high = max(low * 1.01, high)
        log_val = np.log(val)
        log_low = np.log(low)
        log_high = np.log(high)
        t = (log_val - log_low) / (log_high - log_low)
        return out_min + t * (out_max - out_min)
    
    def _scale(self, val: float, low: float, high: float, out_min: float, out_max: float) -> float:
        t = (val - low) / (high - low)
        return out_min + t * (out_max - out_min)
    
    def _detect_motion_blur(self, gray: np.ndarray) -> float:
        # Use Radon-like directional variance: compare horizontal vs vertical gradients
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        ratio = float(np.mean(gx**2) / (np.mean(gy**2) + 1e-6))
        # Ratio far from 1 suggests directional blur
        return abs(np.log(ratio + 1e-6))
    
    def _color_balance_score(self, rgb: np.ndarray) -> float:
        # Gray world assumption: avg of R/G/B should be equal
        means = np.mean(rgb, axis=(0,1))
        if len(means) < 3:
            return 50
        rg, gg, bg = means[0], means[1], means[2]
        avg = (rg + gg + bg) / 3.0
        if avg == 0:
            return 50
        deviations = [abs(rg-avg)/avg, abs(gg-avg)/avg, abs(bg-avg)/avg]
        return max(0, 100 - np.mean(deviations) * 200)
    
    def _detect_artifacts(self, gray: np.ndarray) -> float:
        # DCT blockiness: measure 8x8 grid discontinuities
        h, w = gray.shape
        if h < 16 or w < 16:
            return 0
        # Horizontal block boundary differences
        rows = np.arange(7, h-1, 8)
        cols = np.arange(7, w-1, 8)
        if len(rows) < 2 or len(cols) < 2:
            return 0
        h_diff = np.abs(gray[rows, 1:-1] - gray[rows+1, 1:-1])
        v_diff = np.abs(gray[1:-1, cols] - gray[1:-1, cols+1])
        return float(np.mean(h_diff) + np.mean(v_diff)) / 2.0

class CompositionAnalyzer:
    """Evaluate composition heuristics."""
    
    def analyze(self, image: np.ndarray, detections: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if len(image.shape) == 2:
            gray = image.astype(np.float32)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape
        
        # Rule of thirds: detect subjects near intersections
        thirds_score = 0
        if detections:
            for det in detections:
                x1, y1, x2, y2 = det.get("bbox", [0,0,w,h])
                cx, cy = (x1+x2)/2, (y1+y2)/2
                nx, ny = cx/w, cy/h
                # Distance to nearest third line
                dx = min(abs(nx-0.333), abs(nx-0.666))
                dy = min(abs(ny-0.333), abs(ny-0.666))
                dist = np.sqrt(dx**2 + dy**2)
                thirds_score += max(0, 100 - dist * 200)
            if detections:
                thirds_score /= len(detections)
        else:
            thirds_score = 50
        
        # Framing: subject coverage (not too small, not too cropped)
        subject_area_ratio = 0
        if detections:
            total_area = sum(d.get("area", 0) for d in detections)
            subject_area_ratio = total_area / (w*h)
        framing_score = 100 - abs(subject_area_ratio - 0.25) * 300
        framing_score = max(0, min(100, framing_score))
        
        # Background distractions: measure high-frequency clutter outside subjects
        # Heuristic: variance of edges in non-subject regions
        mask = np.ones((h, w), dtype=np.uint8) * 255
        if detections:
            for det in detections:
                x1, y1, x2, y2 = map(int, det.get("bbox", [0,0,w,h]))
                cv2.rectangle(mask, (x1, y1), (x2, y2), 0, -1)
        bg_edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
        bg_edge_density = float(np.sum(bg_edges & mask)) / (np.sum(mask) + 1e-6)
        distraction_score = 100 - self._scale(bg_edge_density, 0.01, 0.15, 0, 100)
        
        # Horizon alignment: detect dominant horizontal lines with Hough
        horizon_score = 100
        edges = cv2.Canny(gray.astype(np.uint8), 80, 160)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=w//4, maxLineGap=20)
        if lines is not None and len(lines) > 0:
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = abs(np.degrees(np.arctan2(y2-y1, x2-x1)))
                if angle < 20 or angle > 160:
                    angles.append(angle)
            if angles:
                mean_angle = np.mean(angles)
                horizon_score = 100 - min(100, mean_angle * 5)
        
        # Leading lines (line convergence toward center)
        leading_score = 50
        if lines is not None and len(lines) > 0:
            converging = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                mid = ((x1+x2)/2/w, (y1+y2)/2/h)
                dist_to_center = np.sqrt((mid[0]-0.5)**2 + (mid[1]-0.5)**2)
                if dist_to_center < 0.3:
                    converging += 1
            leading_score = min(100, 40 + converging * 2)
        
        # Subject isolation via saliency (OpenCV static saliency)
        isolation_score = 60
        try:
            saliency = cv2.saliency.StaticSaliencyFineGrained_create()
            success, sal_map = saliency.computeSaliency(gray.astype(np.uint8))
            if success and sal_map is not None:
                sal_map = (sal_map * 255).astype(np.uint8)
                _, thresh = cv2.threshold(sal_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                isolation_score = 100 - (float(np.sum(thresh)) / (w*h)) * 100
                isolation_score = max(0, min(100, isolation_score))
        except Exception:
            pass
        
        # Depth / visual impact via contrast range
        contrast = float(np.std(gray))
        depth_score = self._scale(contrast, 20, 80, 0, 100)
        
        breakdown = {
            "rule_of_thirds": max(0, min(100, thirds_score)),
            "framing": max(0, min(100, framing_score)),
            "background_distractions": max(0, min(100, distraction_score)),
            "horizon_alignment": max(0, min(100, horizon_score)),
            "leading_lines": max(0, min(100, leading_score)),
            "subject_isolation": max(0, min(100, isolation_score)),
            "depth": max(0, min(100, depth_score)),
            "visual_impact": max(0, min(100, depth_score * 0.7 + thirds_score * 0.3))
        }
        weights = {
            "rule_of_thirds": 0.20, "framing": 0.15, "background_distractions": 0.15,
            "horizon_alignment": 0.10, "leading_lines": 0.10, "subject_isolation": 0.15,
            "depth": 0.10, "visual_impact": 0.05
        }
        overall = sum(breakdown[k] * weights[k] for k in weights) / sum(weights.values())
        return {
            "score": round(max(0, min(100, overall)), 3),
            "breakdown": breakdown
        }
    
    def _scale(self, val, low, high, out_min, out_max):
        t = (val - low) / (high - low)
        return out_min + t * (out_max - out_min)

class ActionAnalyzer:
    """Analyze action, movement, and storytelling intensity."""
    
    def __init__(self):
        self.technical = TechnicalAnalyzer()
    
    def analyze(self, image: np.ndarray, detections: List[Dict[str, Any]] = None,
                moments: List[str] = None, optical_flow: np.ndarray = None) -> Dict[str, Any]:
        if len(image.shape) == 2:
            gray = image.astype(np.float32)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape
        
        # Motion energy via optical flow or gradient variance
        if optical_flow is not None:
            flow_mag = np.sqrt(optical_flow[...,0]**2 + optical_flow[...,1]**2)
            motion_energy = float(np.mean(flow_mag))
        else:
            # Use single-image motion blur / sharpness as proxy
            gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
            motion_energy = float(np.mean(gx**2 + gy**2))
        
        # Ball presence and position value
        ball_value = 0
        ball_pos_score = 0
        if detections:
            for det in detections:
                cls = det.get("class", "").lower()
                if "ball" in cls or cls == "football":
                    ball_value = 1.0
                    x1, y1, x2, y2 = det.get("bbox", [0,0,w,h])
                    cx, cy = (x1+x2)/2/w, (y1+y2)/2/h
                    # Ball in central/action zone is more valuable
                    ball_pos_score = 100 - (abs(cx-0.5) + abs(cy-0.5)) * 80
                    break
        
        # Interaction / proximity between players
        interaction_score = 0
        player_boxes = []
        if detections:
            for det in detections:
                cls = det.get("class", "").lower()
                if "person" in cls or cls in {"athlete", "man", "woman", "human"}:
                    player_boxes.append(det.get("bbox", [0,0,w,h]))
        if len(player_boxes) >= 2:
            min_dist = float('inf')
            for i in range(len(player_boxes)):
                for j in range(i+1, len(player_boxes)):
                    c1 = ((player_boxes[i][0]+player_boxes[i][2])/2, (player_boxes[i][1]+player_boxes[i][3])/2)
                    c2 = ((player_boxes[j][0]+player_boxes[j][2])/2, (player_boxes[j][1]+player_boxes[j][3])/2)
                    dist = np.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)
                    min_dist = min(min_dist, dist)
            max_diag = np.sqrt(w**2 + h**2)
            interaction_score = 100 - (min_dist / max_diag) * 100
        elif len(player_boxes) == 1:
            interaction_score = 30
        else:
            interaction_score = 10
        
        # Energy / intensity
        energy = self._scale_log(motion_energy, 50, 5000, 0, 100)
        
        # Storytelling based on moments and emotional density
        story_score = 0
        if moments:
            from kirdbyys.config import settings as cfg
            priorities = cfg.MOMENT_PRIORITY
            for m in moments:
                story_score = max(story_score, priorities.get(m, 0.3) * 100)
        
        # Peak action timing: high energy + ball in frame + interaction
        peak_action = (energy + ball_value * 100 + interaction_score) / 3.0
        if "goal" in (moments or []) or "goal_celebration" in (moments or []):
            peak_action = min(100, peak_action * 1.2)
        
        # Newsworthiness / editorial value
        editorial = story_score * 0.6 + ball_value * 100 * 0.2 + interaction_score * 0.2
        
        breakdown = {
            "peak_action_timing": round(max(0, min(100, peak_action)), 3),
            "athletic_movement": round(max(0, min(100, energy)), 3),
            "ball_position": round(max(0, min(100, ball_pos_score if ball_value else 20)), 3),
            "player_interaction": round(max(0, min(100, interaction_score)), 3),
            "energy": round(max(0, min(100, energy)), 3),
            "intensity": round(max(0, min(100, energy * 0.7 + interaction_score * 0.3)), 3),
            "storytelling_strength": round(max(0, min(100, story_score)), 3),
            "newsworthiness": round(max(0, min(100, editorial)), 3),
            "editorial_value": round(max(0, min(100, editorial)), 3)
        }
        weights = {
            "peak_action_timing": 0.25, "athletic_movement": 0.15, "ball_position": 0.15,
            "player_interaction": 0.15, "energy": 0.10, "intensity": 0.05,
            "storytelling_strength": 0.10, "newsworthiness": 0.05
        }
        overall = sum(breakdown[k] * weights[k] for k in weights) / sum(weights.values())
        return {
            "score": round(max(0, min(100, overall)), 3),
            "breakdown": breakdown,
            "features": {
                "motion_energy": round(motion_energy, 2),
                "ball_visible": bool(ball_value),
                "player_count": len(player_boxes)
            }
        }
    
    def _scale_log(self, val, low, high, out_min, out_max):
        val = max(1e-6, val)
        low = max(1e-6, low)
        high = max(low*1.01, high)
        t = (np.log(val) - np.log(low)) / (np.log(high) - np.log(low))
        return out_min + t * (out_max - out_min)

def estimate_emotional_density(image: np.ndarray, detections: List[Dict[str, Any]]) -> float:
    """Heuristic emotional density from face density and gesture poses."""
    if not detections:
        return 0.0
    faces = [d for d in detections if any(x in d.get("class", "").lower() for x in ["face", "head"])]
    people = [d for d in detections if any(x in d.get("class", "").lower() for x in ["person", "athlete", "man", "woman"])]
    if not people:
        return 0.0
    face_ratio = min(1.0, len(faces) / max(1, len(people)))
    density = min(1.0, len(people) / 6.0)
    return min(1.0, face_ratio * 0.5 + density * 0.5)

def estimate_goalkeeper_present(image: np.ndarray, detections: List[Dict[str, Any]]) -> bool:
    """Heuristic: if a person is near the goal line / large box, assume goalkeeper."""
    if not detections:
        return False
    h, w = image.shape[:2]
    for det in detections:
        cls = det.get("class", "").lower()
        if "person" in cls or cls in {"athlete", "man", "woman"}:
            x1, y1, x2, y2 = det.get("bbox", [0,0,w,h])
            cy = (y1 + y2) / 2
            # Near top or bottom center of frame (goal line area)
            if (cy < h * 0.2 or cy > h * 0.8) and abs((x1+x2)/2 - w/2) < w * 0.3:
                return True
    return False