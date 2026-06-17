"""Sport adapter base classes for future expansion.

Architecture: each sport can define its own moment taxonomy, weights, and heuristics
while reusing the same technical/composition/action analyzers and ranking engine.
"""
from typing import Dict, List, Any, Callable
from abc import ABC, abstractmethod

class SportAdapter(ABC):
    """Base class for sport-specific culling logic."""
    
    name: str = "generic"
    default_weights: Dict[str, float] = {
        "technical_quality": 0.25,
        "action_value": 0.35,
        "storytelling": 0.25,
        "composition": 0.15
    }
    moment_priority: Dict[str, float] = {}
    relevant_object_classes: List[str] = []
    
    @abstractmethod
    def classify_moments(self, detection_data: Dict[str, Any], action_features: Dict[str, Any]) -> List[str]:
        """Return moment labels for the image."""
        pass
    
    def adjust_scores(self, technical: float, action: float, story: float, composition: float,
                      moments: List[str]) -> Dict[str, float]:
        """Optionally adjust analyzer scores before final ranking."""
        return {
            "technical_score": technical,
            "action_score": action,
            "storytelling_score": story,
            "composition_score": composition
        }
    
    def get_explanation_template(self, top_strengths: List[str], weaknesses: List[str]) -> str:
        if not top_strengths:
            top_strengths.append("acceptable general image")
        explanation = "Ranked highly because of " + ", ".join(top_strengths) + "."
        if weaknesses:
            explanation += " Watch out: " + "; ".join(weaknesses) + "."
        return explanation

class SoccerAdapter(SportAdapter):
    name = "soccer"
    default_weights = {
        "technical_quality": 0.25,
        "action_value": 0.35,
        "storytelling": 0.25,
        "composition": 0.15
    }
    moment_priority = {
        "goal": 1.00,
        "goal_celebration": 1.00,
        "game_winning_moment": 0.98,
        "penalty_save": 0.95,
        "goalkeeper_save": 0.92,
        "shot_on_goal": 0.90,
        "slide_tackle": 0.88,
        "header": 0.86,
        "tackle": 0.85,
        "coach_reaction": 0.80,
        "crowd_reaction": 0.78,
        "dribble": 0.75,
        "team_huddle": 0.72,
        "player_posession": 0.70,
        "ball_in_play": 0.60,
        "pass": 0.55,
        "substitution": 0.50,
        "warmup": 0.30,
        "static_portrait": 0.25,
        "empty_field": 0.10
    }
    relevant_object_classes = ["person", "sports ball", "baseball bat", "tennis racket"]
    
    def classify_moments(self, detection_data: Dict[str, Any], action_features: Dict[str, Any]) -> List[str]:
        from kirdbyys.ai.detectors import SoccerMomentClassifier
        return SoccerMomentClassifier().classify(detection_data, action_features)

class AFLAdapter(SportAdapter):
    name = "afl"
    default_weights = {
        "technical_quality": 0.25,
        "action_value": 0.40,
        "storytelling": 0.25,
        "composition": 0.10
    }
    moment_priority = {
        "goal": 1.00,
        "mark": 0.95,
        "tackle": 0.88,
        "goal_celebration": 1.00,
        "coach_reaction": 0.80,
        "crowd_reaction": 0.78,
        "ball_in_play": 0.55,
        "static_portrait": 0.25
    }
    
    def classify_moments(self, detection_data: Dict[str, Any], action_features: Dict[str, Any]) -> List[str]:
        # Placeholder for AFL-specific rules
        return ["afl_action"]

class BasketballAdapter(SportAdapter):
    name = "basketball"
    default_weights = {
        "technical_quality": 0.25,
        "action_value": 0.40,
        "storytelling": 0.20,
        "composition": 0.15
    }
    moment_priority = {
        "dunk": 1.00,
        "three_pointer": 0.95,
        "block": 0.92,
        "steal": 0.88,
        "fast_break": 0.85,
        "celebration": 0.90,
        "coach_reaction": 0.78,
        "crowd_reaction": 0.75,
        "static_portrait": 0.25
    }
    
    def classify_moments(self, detection_data: Dict[str, Any], action_features: Dict[str, Any]) -> List[str]:
        return ["basketball_action"]

# Registry for future expansion
SPORT_ADAPTERS: Dict[str, SportAdapter] = {
    "soccer": SoccerAdapter(),
    "afl": AFLAdapter(),
    "basketball": BasketballAdapter(),
    # "rugby": RugbyAdapter(),
    # "cricket": CricketAdapter(),
    # "baseball": BaseballAdapter(),
    # "tennis": TennisAdapter(),
    # "motorsport": MotorsportAdapter(),
}

def get_sport_adapter(sport: str) -> SportAdapter:
    return SPORT_ADAPTERS.get(sport.lower(), SoccerAdapter())