# Dataset Recommendations

## Primary Goal

Obtain or build a dataset of soccer match photographs with labels that reflect **professional publishing decisions**, not just image quality.

## Recommended Public Datasets

1. **SoccerNet** (https://www.soccer-net.org/)
   - Broadcast video frames with event annotations (goals, cards, substitutions)
   - Can be used to train moment classifiers by extracting key frames around events

2. **Football Object Detection Datasets (Hugging Face)**
   - Search: `football detection`, `soccer ball detection`, `player detection`
   - Use to fine-tune YOLOv8 for pitch-specific objects

3. **AVA Dataset (Generic action recognition)**
   - Can provide action/intensity labels for general sports movement

4. **Piqsels / Wikimedia Commons Soccer Galleries**
   - Published sports photos under free licenses
   - Use as positive examples for "publishable" images

## Building a Custom Dataset

### Label Taxonomy (Soccer)

| Label | Definition | Priority |
|-------|------------|----------|
| goal | Ball crossing the goal line, goal-scoring action | 1.00 |
| goal_celebration | Players celebrating a goal | 1.00 |
| game_winning_moment | Decisive late match moment | 0.98 |
| penalty_save | Goalkeeper saving a penalty | 0.95 |
| goalkeeper_save | Goalkeeper making a save | 0.92 |
| shot_on_goal | Player shooting at goal | 0.90 |
| slide_tackle | Sliding challenge | 0.88 |
| header | Aerial challenge / header | 0.86 |
| tackle | Standing tackle / challenge | 0.85 |
| coach_reaction | Coach responding to match | 0.80 |
| crowd_reaction | Crowd celebrating / reacting | 0.78 |
| team_huddle | Players grouped together | 0.72 |
| player_posession | Player with ball | 0.70 |
| ball_in_play | Ball visible but no clear action | 0.60 |
| pass | Passing action | 0.55 |
| substitution | Player entering/leaving | 0.50 |
| warmup | Pre-match warm-up | 0.30 |
| static_portrait | Player standing still | 0.25 |
| empty_field | No people / no story | 0.10 |

### Annotation Workflow

1. Import a match into Kirdbyys
2. Run initial rule-based analysis
3. Photographer reviews and corrects labels for 50–100 representative matches
4. Export labels to a training dataset (CSV/JSON)
5. Train the moment classifier
6. Repeat with retrained model for active learning

## Negative Examples

Include many images that are technically good but not publishable:

- Players standing still with no story
- Backs of players
- Empty field / crowd shots with no action
- Out-of-focus or poorly framed images (as technical-negative examples)

## Data Augmentation

- Random crop / resize
- Brightness / contrast / saturation jitter
- Horizontal flip (only if sport-agnostic)
- Add synthetic noise and blur for technical robustness
- JPEG compression artifacts

## Storage Format

```json
{
  "image_path": "/path/to/img.jpg",
  "moments": ["goal_celebration"],
  "technical_score": 82.5,
  "action_score": 91.2,
  "storytelling_score": 96.0,
  "composition_score": 74.3,
  "published": true,
  "duplicate_group": null
}
```
