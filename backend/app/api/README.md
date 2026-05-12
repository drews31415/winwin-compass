# API Routers

API modules expose 상생나침반 backend features.

## Layout

- `v1/chat.py`: streaming and simple chat endpoints.
- `v1/report.py`: area report payloads.
- `v1/policy.py`: policy match and search endpoints.
- `v1/ml.py`: forecast, risk, training, and model inventory endpoints.
- `v1/marketing.py`: text-based marketing content generation.
- `routes/data.py`: area listing/map/detail compatibility routes.
- `routes/health.py`: health check.

## Conventions

Use `APIRouter` per feature and register it from `app/main.py`. Keep database access async and inject sessions through `get_db` where possible. Demo-critical endpoints should return deterministic sample data when the DB is unavailable.

## Common Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/areas/3110016
curl http://localhost:8000/api/v1/ml/forecast/3110016?periods=4
curl -X POST http://localhost:8000/api/v1/marketing/generate -H "Content-Type: application/json" -d '{"business_type":"카페","area":"종로구","purpose":"sns","tone":"friendly"}'
```
