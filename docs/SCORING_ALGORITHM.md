# Scoring Algorithm

## Final Score Formula

```
Final Score = 100 × (
    w_tech × (Technical / 100) +
    w_action × (Action / 100) +
    w_story × (Storytelling / 100) +
    w_comp × (Composition / 100)
)
```

Weights are normalized so they sum to 1.0.

## Default Weights (Soccer)

| Dimension | Weight | Justification |
|-----------|--------|---------------|
| Technical Quality | 25% | Must be usable, but not the only factor |
| Action Value | 35% | Sports photos are about peak moments |
| Storytelling | 25% | Emotion, significance, publishability |
| Composition | 15% | Framing supports the story |

These weights are configurable per project and per sport.

## Technical Quality (0–100)

Calculated from:

| Metric | Sub-score | Weight within Technical |
|--------|-----------|------------------------|
| Sharpness | Laplacian variance | 18% |
| Focus | Center-weighted sharpness | 14% |
| Motion blur | Directional gradient ratio | 12% |
| Exposure | Mean luma deviation from 128 | 12% |
| Dynamic range | 1st–99th percentile luma spread | 8% |
| Highlight clipping | Top 10 histogram bins | 6% |
| Shadow clipping | Bottom 10 histogram bins | 6% |
| Noise | MAD of high-pass residual | 10% |
| Color quality | Saturation + balance | 6% |
| White balance | Gray-world deviation | 4% |
| Clarity | Gradient magnitude | 4% |

Each sub-score is normalized to 0–100 and weighted.

## Action Value (0–100)

| Metric | How Measured | Weight |
|--------|--------------|--------|
| Peak action timing | Motion energy + ball + interaction | 25% |
| Athletic movement | Gradient / edge energy | 15% |
| Ball position | Ball detected + centrality | 15% |
| Player interaction | Proximity between detected players | 15% |
| Energy | Motion intensity | 10% |
| Intensity | Energy + interaction | 5% |
| Storytelling strength | Moment priority | 10% |
| Newsworthiness | Goal/celebration/save moments | 5% |

## Storytelling Score (0–100)

```
Storytelling = 0.6 × Highest_Moment_Priority × 100
             + 0.3 × Emotional_Density × 100
             + 0.1 × Action_Score
```

Moment priorities are defined in `config.MOMENT_PRIORITY`. Highest-priority moment wins.

## Composition Score (0–100)

| Metric | Weight |
|--------|--------|
| Rule of thirds | 20% |
| Framing (subject coverage) | 15% |
| Background distractions | 15% |
| Horizon alignment | 10% |
| Leading lines | 10% |
| Subject isolation | 15% |
| Depth / contrast | 10% |
| Visual impact | 5% |

## Explainability

For every image, Kirdbyys generates a sentence like:

> "Ranked highly because of strong action moment: goal celebration, excellent sharpness, and strong subject isolation. Watch out: low background distractions."

The explanation is built from the highest sub-scores and any weak areas.

## Re-ranking

When the user changes weights, only the weighted sum is recomputed. Full re-analysis is optional. This allows instant experimentation with different creative priorities.

## Selection

After ranking, the top N images are selected. The default is 20. Images inside duplicate/burst groups are suppressed unless they are the representative frame.
