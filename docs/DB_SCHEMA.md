# Database Schema

Kirdbyys uses **SQLite** with the following tables. The schema is defined in `kirdbyys/core/database.py` using SQLAlchemy.

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────────┐
│  projects   │ 1---* │   images    │ *---0..1│ duplicate_groups│
├─────────────┤       ├─────────────┤       ├─────────────────┤
│ id PK       │       │ id PK       │       │ id PK           │
│ name        │       │ project_id FK│      │ project_id FK   │
│ sport       │       │ filename    │       │ representative  │
│ source_folder│      │ original_path│       │ frame_count     │
│ weights     │       │ rel_path    │       └─────────────────┘
│ status      │       │ file_size   │
│ target_count│      │ ... scores  │
└─────────────┘       │ detected    │
                      │ moments     │
                      │ breakdowns  │
                      │ feature_hash│
                      └─────────────┘
                             │
                             │ 1---*
                      ┌─────────────┐
                      │    jobs     │
                      ├─────────────┤
                      │ id PK       │
                      │ project_id  │
                      │ job_type    │
                      │ status      │
                      │ progress    │
                      │ message     │
                      └─────────────┘
```

## Table Definitions

### `projects`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Project ID |
| name | VARCHAR(255) | Display name |
| sport | VARCHAR(64) | Sport type (soccer, afl, etc.) |
| source_folder | TEXT | Original folder path |
| created_at | DATETIME | Creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| status | VARCHAR(32) | idle / importing / analyzing / complete / error |
| weights | JSON | Scoring weights JSON |
| target_selection_count | INTEGER | Default top N selection |

### `images`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Image ID |
| project_id | INTEGER FK | Parent project |
| filename | VARCHAR(512) | File name |
| original_path | TEXT | Source file path |
| rel_path | TEXT | Path relative to data dir |
| file_size | INTEGER | Bytes |
| width, height | INTEGER | Dimensions |
| capture_time | DATETIME | EXIF capture time |
| camera_make / model | VARCHAR(128) | Camera metadata |
| lens | VARCHAR(128) | Lens model |
| iso | INTEGER | ISO |
| aperture / shutter_speed / focal_length | VARCHAR(32) | EXIF exposure |
| technical_score | FLOAT | 0–100 technical quality |
| action_score | FLOAT | 0–100 action value |
| storytelling_score | FLOAT | 0–100 storytelling |
| composition_score | FLOAT | 0–100 composition |
| final_score | FLOAT | 0–100 weighted final |
| rank | INTEGER | Final rank |
| detected_labels | JSON | List of detected classes |
| moments | JSON | List of moment labels |
| quality_breakdown | JSON | Technical sub-scores |
| composition_breakdown | JSON | Composition sub-scores |
| action_breakdown | JSON | Action sub-scores |
| explanation | TEXT | Human-readable explanation |
| selected | BOOLEAN | In final selection |
| rejected | BOOLEAN | User rejected |
| duplicate_group_id | INTEGER FK | Group membership |
| is_best_in_group | BOOLEAN | Representative frame |
| thumbnail_path | TEXT | Cached thumbnail path |
| preview_path | TEXT | Cached preview path |
| perceptual_hash | VARCHAR(64) | pHash string |
| feature_vector | TEXT | Base64 pickle of feature vector |
| processed | BOOLEAN | Analysis complete |
| processing_error | TEXT | Error message if failed |

### `duplicate_groups`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Group ID |
| project_id | INTEGER FK | Parent project |
| representative_image_id | INTEGER | Best frame ID |
| similarity_score | FLOAT | Group similarity |
| frame_count | INTEGER | Number of frames |

### `jobs`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | UUID string |
| project_id | INTEGER FK | Project |
| job_type | VARCHAR(32) | analyze / import / export |
| status | VARCHAR(32) | queued / running / complete / error / cancelled |
| progress | FLOAT | 0.0–1.0 |
| total_items | INTEGER | Total work units |
| processed_items | INTEGER | Completed units |
| message | TEXT | Current status message |
| created_at / updated_at | DATETIME | Timestamps |
| error_log | TEXT | Stack trace on failure |

### `export_presets`

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Preset ID |
| name | VARCHAR(128) | Preset name |
| top_n | INTEGER | Top N count |
| mode | VARCHAR(32) | copy / move / csv / xlsx / xmp / pdf |
| include_rejected | BOOLEAN | Include rejected images |
| include_duplicates | BOOLEAN | Include duplicate frames |
| destination | TEXT | Export path |
| created_at | DATETIME | Timestamp |
