# Duplicate Detection Algorithm

## Goal

Automatically detect and suppress:

- Exact duplicate images (re-imported files)
- Near-duplicate images (small JPEG recompressions, minor crops)
- Burst sequences (20+ frames of the same celebration or action)

The strongest frame from each group is kept in the final selection.

## Algorithm Overview

### 1. Perceptual Hashing

Each image is converted to a pHash (perceptual hash) using `imagehash.phash` with hash size 16.

- pHash is robust to small brightness, contrast, and compression changes
- It detects near-duplicates that are visually identical to a human

### 2. Feature Vector

A compact feature vector is also computed from:

- HSV color histogram (48 bins)
- Edge histogram in 4 quadrants

This helps distinguish similar-looking frames within a burst (e.g., goal celebration where poses change slightly).

### 3. Similarity Score

```
similarity = 1 - (hamming_distance / max_distance)
```

where `max_distance = hash_size²` (256 for 16-bit hash).

### 4. Grouping Rules

Two images are grouped if either:

- **Duplicate**: `similarity >= 0.92` (very high, even across time)
- **Burst**: `similarity >= 0.85` AND time difference `<= 2 seconds`

Images are sorted by capture time, then a union-find algorithm groups connected frames.

### 5. Representative Selection

For each group, the frame with the highest **final score** is chosen as the representative. This means the AI selects the best technical + action + storytelling frame from the burst, not just the first or middle frame.

### 6. Suppression in Ranking

Non-representative frames retain their scores but are marked as duplicates. The default Top N selection excludes them unless the user explicitly includes duplicates.

## Tuning Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| hash_size | 16 | Larger = more precise but stricter |
| duplicate_threshold | 0.92 | Near-exact duplicates |
| burst_similarity_threshold | 0.85 | Burst frame grouping |
| burst_time_delta_seconds | 2.0 | Time window for burst grouping |

These can be changed in `kirdbyys/config.py` or via the future settings UI.

## Performance

Pairwise comparison is O(n²), but the hash itself is tiny (16-bit) and computed once. For 2,000 images, grouping takes less than 1 second on the target CPU. For larger galleries, locality-sensitive hashing (LSH) can be added later.

## Future Improvements

- Use deep features (e.g., CLIP/ResNet embeddings) for semantic similarity
- Add optical flow to better group bursts and pick the peak action frame
- Learned duplicate detector trained on photographer-labeled burst groups
