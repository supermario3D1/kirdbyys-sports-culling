"""Duplicate, near-duplicate, and burst-sequence detection."""
import numpy as np
import cv2
import imagehash
from PIL import Image
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from kirdbyys.config import settings

class DuplicateDetector:
    """Detect duplicates using perceptual hashing and feature vectors."""
    
    def __init__(self, hash_size: int = 16, threshold: float = 0.92, burst_time_delta: float = 2.0):
        self.hash_size = hash_size
        self.threshold = threshold
        self.burst_time_delta = burst_time_delta
    
    def compute_hash(self, image: np.ndarray) -> str:
        if len(image.shape) == 3:
            pil_img = Image.fromarray(image.astype(np.uint8))
        else:
            pil_img = Image.fromarray(image.astype(np.uint8))
        phash = imagehash.phash(pil_img, hash_size=self.hash_size)
        return str(phash)
    
    def compute_feature_vector(self, image: np.ndarray, bins: int = 16) -> np.ndarray:
        """Compact color histogram + edge histogram feature vector."""
        if len(image.shape) == 2:
            rgb = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        else:
            rgb = image.astype(np.uint8)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [bins], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [bins], [0, 256]).flatten()
        hist_v = cv2.calcHist([hsv], [2], None, [bins], [0, 256]).flatten()
        hist = np.concatenate([hist_h, hist_s, hist_v])
        hist = hist / (np.sum(hist) + 1e-9)
        
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_hist = np.zeros(4)
        h, w = edges.shape
        edge_hist[0] = np.sum(edges[:h//2, :w//2])
        edge_hist[1] = np.sum(edges[:h//2, w//2:])
        edge_hist[2] = np.sum(edges[h//2:, :w//2])
        edge_hist[3] = np.sum(edges[h//2:, w//2:])
        edge_hist = edge_hist / (np.sum(edge_hist) + 1e-9)
        
        return np.concatenate([hist, edge_hist])
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
    
    def similarity(self, hash1: str, hash2: str) -> float:
        max_dist = self.hash_size ** 2
        dist = self.hamming_distance(hash1, hash2)
        return 1.0 - (dist / max_dist)
    
    def find_duplicates(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group images into duplicate/burst sets."""
        n = len(images)
        if n < 2:
            return []
        
        # Sort by capture time if available
        for img in images:
            if not img.get("capture_time"):
                img["capture_time"] = datetime.min
        images_sorted = sorted(images, key=lambda x: x.get("capture_time", datetime.min))
        
        parent = list(range(n))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
        
        for i in range(n):
            for j in range(i+1, n):
                t1 = images_sorted[i].get("capture_time", datetime.min)
                t2 = images_sorted[j].get("capture_time", datetime.min)
                time_diff = abs((t2 - t1).total_seconds()) if t2 and t1 else float('inf')
                
                h1 = images_sorted[i].get("perceptual_hash")
                h2 = images_sorted[j].get("perceptual_hash")
                if not h1 or not h2:
                    continue
                sim = self.similarity(h1, h2)
                
                # Duplicate: very high similarity regardless of time
                if sim >= self.threshold:
                    union(i, j)
                # Burst: high similarity + close in time
                elif sim >= settings.BURST_SIMILARITY_THRESHOLD and time_diff <= self.burst_time_delta:
                    union(i, j)
        
        groups = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)
        
        duplicate_groups = []
        for root, members in groups.items():
            if len(members) > 1:
                group_images = [images_sorted[m] for m in members]
                # Pick best representative by final score
                best = max(group_images, key=lambda x: x.get("final_score", 0) or x.get("technical_score", 0))
                duplicate_groups.append({
                    "representative_id": best.get("id"),
                    "image_ids": [img.get("id") for img in group_images],
                    "count": len(group_images),
                    "best_score": best.get("final_score", 0)
                })
        return duplicate_groups
    
    def suppress_duplicates(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mark duplicates and return list with suppression flags."""
        groups = self.find_duplicates(images)
        group_by_id = {}
        for g in groups:
            for img_id in g["image_ids"]:
                group_by_id[img_id] = g
        
        for img in images:
            g = group_by_id.get(img.get("id"))
            if g:
                img["duplicate_group_id"] = g["representative_id"]
                img["is_representative"] = img.get("id") == g["representative_id"]
            else:
                img["duplicate_group_id"] = None
                img["is_representative"] = True
        return images