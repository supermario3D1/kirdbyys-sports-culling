# Kirdbyys API Design

All API endpoints are local-only and served by FastAPI. Base path: `/api`.

## Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create a new project |
| GET | `/projects` | List all projects |
| GET | `/projects/{id}` | Get project details |
| DELETE | `/projects/{id}` | Delete a project |

## Import

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/import` | Import folder (form: `folder`, `copy`) |
| POST | `/projects/{id}/import-files` | Upload files (multipart) |

## Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/analyze` | Start analysis job (weights, top_n) |
| GET | `/jobs` | List jobs |
| GET | `/jobs/{id}` | Job status |
| POST | `/jobs/{id}/cancel` | Cancel job |

## Images

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/{id}/images` | List images with sorting/filtering |
| GET | `/images/{id}` | Get image details |
| GET | `/images/{id}/thumbnail` | Get thumbnail |
| GET | `/images/{id}/preview` | Get preview |
| POST | `/images/{id}/select` | Toggle selected/rejected |
| GET | `/projects/{id}/search` | Search images |
| GET | `/projects/{id}/duplicates` | Duplicate groups |
| GET | `/projects/{id}/stats` | Project statistics |

## Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| PUT | `/projects/{id}/weights` | Update scoring weights |
| GET | `/system/info` | System and provider info |

## Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/export` | Export selection (copy/move/csv/xlsx/xmp/pdf) |
| POST | `/projects/{id}/export-xmp` | Write XMP sidecars |

## Example: Create and Analyze

```bash
# Create project
curl -X POST http://127.0.0.1:7840/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Grand Final","sport":"soccer","source_folder":"/photos/grandfinal"}'

# Import folder
curl -X POST http://127.0.0.1:7840/api/projects/1/import \
  -F "folder=/photos/grandfinal" -F "copy=true"

# Analyze
curl -X POST http://127.0.0.1:7840/api/projects/1/analyze \
  -H "Content-Type: application/json" \
  -d '{"weights":{"technical_quality":0.25,"action_value":0.35,"storytelling":0.25,"composition":0.15},"top_n":20}'

# Get top 20
curl "http://127.0.0.1:7840/api/projects/1/images?sort_by=final_score&limit=20"

# Export CSV
curl -X POST http://127.0.0.1:7840/api/projects/1/export \
  -H "Content-Type: application/json" \
  -d '{"mode":"csv","top_n":20}'
```

## WebSocket / Real-Time (Future)

The current UI polls `/jobs/{id}` every second. A future WebSocket endpoint `/ws/jobs` can push progress updates to reduce latency.
