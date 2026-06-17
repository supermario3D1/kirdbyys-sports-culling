"""Ranking engine for sports photography selection."""
import numpy as np
from typing import List, Dict, Any, Optional
from kirdbyys.config import settings

class RankingEngine:
    """Configurable weighted ranking with explainability."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or dict(settings.DEFAULT_WEIGHTS)
        self._normalize_weights()
    
    def _normalize_weights(self):
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v/total for k, v in self.weights.items()}
    
    def rank(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score and rank images, return sorted list with explanations."""
        for img in images:
            scores = {
                "technical_quality": img.get("technical_score", 0) / 100.0,
                "action_value": img.get("action_score", 0) / 100.0,
                "storytelling": img.get("storytelling_score", 0) / 100.0,
                "composition": img.get("composition_score", 0) / 100.0
            }
            # Final weighted score
            final = sum(scores[k] * self.weights[k] for k in self.weights) * 100.0
            img["final_score"] = round(final, 3)
            img["score_breakdown"] = {k: round(scores[k]*100, 2) for k in scores}
            img["weight_breakdown"] = dict(self.weights)
            img["explanation"] = self._explain(img, scores)
        
        sorted_images = sorted(images, key=lambda x: (x["final_score"], x.get("action_score", 0)), reverse=True)
        for i, img in enumerate(sorted_images):
            img["rank"] = i + 1
        return sorted_images
    
    def _explain(self, img: Dict[str, Any], scores: Dict[str, float]) -> str:
        """Generate human-readable ranking explanation."""
        # Find top strengths
        breakdowns = {
            "technical_quality": img.get("quality_breakdown", {}),
            "action_value": img.get("action_breakdown", {}),
            "storytelling": {"moments": img.get("moments", [])},
            "composition": img.get("composition_breakdown", {})
        }
        
        strengths = []
        if scores["action_value"] >= 0.75:
            moments = img.get("moments", [])
            if moments and moments[0] != "static_scene":
                strengths.append(f"strong action moment: {moments[0].replace('_', ' ')}")
            else:
                strengths.append("strong athletic action")
        if scores["storytelling"] >= 0.70:
            strengths.append("high storytelling / editorial value")
        if scores["technical_quality"] >= 0.80:
            q = breakdowns["technical_quality"]
            top_tech = max(q, key=q.get) if q else "technical quality"
            strengths.append(f"excellent {top_tech.replace('_', ' ')}")
        if scores["composition"] >= 0.75:
            c = breakdowns["composition"]
            top_comp = max(c, key=c.get) if c else "composition"
            strengths.append(f"strong {top_comp.replace('_', ' ')}")
        
        weaknesses = []
        if scores["technical_quality"] < 0.45:
            q = breakdowns["technical_quality"]
            worst = min(q, key=q.get) if q else "technical quality"
            weaknesses.append(f"low {worst.replace('_', ' ')}")
        if scores["action_value"] < 0.35:
            weaknesses.append("minimal action or ball not prominent")
        if scores["storytelling"] < 0.30:
            weaknesses.append("limited narrative moment")
        if scores["composition"] < 0.40:
            weaknesses.append("composition could be improved")
        
        if not strengths:
            strengths.append("acceptable general image")
        
        explanation = "Ranked highly because of " + ", ".join(strengths) + "."
        if weaknesses:
            explanation += " Watch out: " + "; ".join(weaknesses) + "."
        return explanation
    
    def select_top_n(self, images: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
        return images[:n]