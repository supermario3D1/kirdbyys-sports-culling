# Training Strategy

## Goal

Build a robust, sport-specific ranking system that thinks like a professional sports photographer. The strategy starts with **rule-based heuristics** and evolves toward **learned models** as labeled data is collected.

## Phase 1: Rule-Based Foundation (Current)

No training data is required to start. The system uses:

- YOLOv8 object detection outputs
- Classical computer vision metrics
- Handcrafted soccer moment rules
- Configurable scoring weights

This phase delivers immediate value and is fully explainable.

## Phase 2: Weakly Supervised Moment Labels

Collect pseudo-labels from existing soccer photo datasets and video frames:

- Use video event detection (goal detection, whistle detection) to tag frames
- Use web-scraped professional sports photo galleries as "positive" examples
- Use heuristics from the rule engine as initial noisy labels

Train a small **EfficientNet-B0 / MobileNetV2** classifier to predict moment class from image features.

## Phase 3: Human-in-the-Loop Labeling

Build a labeling tool inside Kirdbyys where the photographer can:

- Mark which images they would actually publish
- Adjust moment labels
- Rank pairs of images (A vs B)

Collect these labels in a local SQLite dataset and periodically retrain the moment classifier and ranking model.

## Phase 4: Learned Aesthetic + Story Ranking

Train a multi-task model with two heads:

1. **Technical quality head**: regression to perceived technical score
2. **Story/action head**: classification + regression to publishability

Use a **contrastive learning** approach: published photos should score higher than non-published photos from the same match.

## Phase 5: Sport-Specific Fine-Tuning

For each new sport (AFL, basketball, rugby, cricket, baseball, tennis, motorsport), fine-tune the detection and moment classifier on sport-specific data. The architecture remains the same; only the label taxonomy and heuristics change.

## Training Pipeline

```python
# 1. Collect labeled dataset from user feedback and web sources
# 2. Preprocess images (resize, normalize, augment)
# 3. Fine-tune YOLOv8 on sport-specific detections (player, ball, goalpost, umpire)
# 4. Train moment classifier (EfficientNet-B0 ONNX)
# 5. Train technical/aesthetic scorer (MobileNetV2 ONNX)
# 6. Export all models to ONNX INT8/FP16 for AMD inference
# 7. Evaluate on held-out test set; update default weights per sport
```

## Evaluation Metrics

- **Top-20 precision**: how many of the AI-selected top 20 match the photographer's picks
- **Normalized Discounted Cumulative Gain (NDCG)**: ranking quality
- **Duplicate suppression recall**: percentage of true burst frames grouped correctly
- **Inference time per image**: target < 500 ms on target CPU; < 150 ms on GPU
