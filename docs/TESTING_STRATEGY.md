# Kirdbyys Testing Strategy

## Unit Tests

Test each analyzer independently with synthetic and real images.

```python
# tests/test_analyzers.py
import numpy as np
from kirdbyys.ai.analyzers import TechnicalAnalyzer, CompositionAnalyzer, ActionAnalyzer

def test_technical_scores_blur_low():
    # Create a blurred image
    img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    img = cv2.GaussianBlur(img, (21, 21), 0)
    tech = TechnicalAnalyzer()
    result = tech.analyze(img)
    assert result["score"] < 50

def test_composition_rule_of_thirds():
    # Place subject at intersection
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = [{"class": "person", "bbox": [180, 120, 260, 200], "area": 6400}]
    comp = CompositionAnalyzer()
    result = comp.analyze(img, detections)
    assert result["breakdown"]["rule_of_thirds"] > 70
```

## Integration Tests

- Import a folder of test images
- Run analysis end-to-end
- Verify DB entries have scores and ranks
- Verify export files are created
- Verify duplicate groups are detected on a burst sequence

## Regression Tests

- Maintain a small set of "known-good" soccer images
- After every model or code change, verify top-10 rankings do not change unexpectedly
- Track scores for each image in a golden JSON file

## Performance Tests

- Process 100 images and measure throughput
- Ensure UI remains responsive (job polling returns quickly)
- Memory usage should not exceed 4 GB for 1,000 images

## Acceptance Criteria

Given 1,000 soccer photographs, the system must:

1. Import all images without errors
2. Analyze all images within a reasonable time (< 30 min on target hardware)
3. Rank images with a clear final score
4. Provide explanations for top selections
5. Detect and suppress burst sequences
6. Allow user to select Top 10/20/50/100 or custom
7. Export selected images in a usable format
8. Write XMP sidecars compatible with Lightroom

## Test Commands

```bash
cd kirdbyys-sports-culling
python -m pytest tests/ -v
```

## Manual QA Checklist

- [ ] UI loads in dark and light mode
- [ ] Drag-and-drop import works
- [ ] Folder import works
- [ ] Analysis progress bar updates
- [ ] Rankings sort correctly by all columns
- [ ] Image detail modal shows scores and explanation
- [ ] Duplicates view shows burst groups
- [ ] Export produces expected files
- [ ] XMP sidecars open correctly in Lightroom
- [ ] App works without internet after setup
