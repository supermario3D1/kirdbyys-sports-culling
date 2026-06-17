import numpy as np
import cv2
import pytest
from kirdbyys.ai.analyzers import TechnicalAnalyzer, CompositionAnalyzer, ActionAnalyzer
from kirdbyys.ai.ranking import RankingEngine
from kirdbyys.ai.duplicate import DuplicateDetector

def test_technical_analyzer_scores_blurred_image_low():
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    blurred = cv2.GaussianBlur(img, (21, 21), 0)
    tech = TechnicalAnalyzer()
    result = tech.analyze(blurred)
    assert "score" in result
    assert result["score"] < 60  # blurred image should not score high

def test_technical_analyzer_scores_sharp_image_high():
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    tech = TechnicalAnalyzer()
    result = tech.analyze(img)
    assert result["score"] > 30  # random but sharp edges should be decent

def test_composition_rule_of_thirds():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = [{"class": "person", "bbox": [180.0, 120.0, 260.0, 200.0], "area": 6400.0}]
    comp = CompositionAnalyzer()
    result = comp.analyze(img, detections)
    assert result["score"] > 0
    assert result["breakdown"]["rule_of_thirds"] > 70

def test_action_analyzer_with_goal_moment():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = [
        {"class": "person", "bbox": [100.0, 200.0, 200.0, 400.0], "area": 20000.0},
        {"class": "sports ball", "bbox": [300.0, 220.0, 340.0, 260.0], "area": 1600.0}
    ]
    action = ActionAnalyzer()
    result = action.analyze(img, detections, moments=["goal"])
    assert result["score"] > 50
    assert result["breakdown"]["ball_position"] > 50

def test_ranking_engine_orders_images():
    images = [
        {"technical_score": 80, "action_score": 90, "storytelling_score": 85, "composition_score": 70},
        {"technical_score": 95, "action_score": 30, "storytelling_score": 20, "composition_score": 90},
    ]
    engine = RankingEngine()
    ranked = engine.rank(images)
    # Action/story weighted default should prefer first image
    assert ranked[0] == images[0]

def test_duplicate_detector_groups_similar_images():
    img1 = np.random.randint(0, 255, (200, 300, 3), dtype=np.uint8)
    img2 = img1 + np.random.randint(-5, 5, (200, 300, 3), dtype=np.int16).astype(np.uint8)
    detector = DuplicateDetector()
    h1 = detector.compute_hash(img1)
    h2 = detector.compute_hash(img2)
    sim = detector.similarity(h1, h2)
    assert sim > 0.85
