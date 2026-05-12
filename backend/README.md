# Backend

FastAPI backend for 상생나침반. It serves chat, report, policy, data, and ML endpoints, while keeping demo-safe fallbacks for competition presentations.

## Structure

```text
app/main.py          FastAPI app, lifespan, router registration
app/api/             HTTP endpoints
app/core/            settings, database engine, shared configuration
app/models/          SQLAlchemy ORM models and Pydantic schemas
app/ai/              LangChain chat, RAG, Text-to-SQL
app/data/            Seoul API collectors and transformers
app/ml/              forecasting, risk scoring, model storage
scripts/             seed and smoke-test scripts
alembic/             database migrations
models/              local model artifacts, ignored by Git
```

## Local Run

```bash
pip install -r requirements.txt --prefer-binary
uvicorn app.main:app --reload --port 8000
```

The app expects PostgreSQL and Redis from root `docker-compose.yml`, but key demo endpoints include fallback responses when external services are unavailable.

## Useful Commands

```bash
python scripts/seed_demo_data.py
bash scripts/smoke_test.sh http://localhost:8000
alembic upgrade head
```

## Environment

Main variables are `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `SEOUL_API_KEY`, `CORS_ORIGINS`, and `PORT`. Railway may inject `postgresql://`; `app/core/config.py` normalizes it to `postgresql+asyncpg://`.

## Deployment

```bash
railway up backend --path-as-root --service winwin-compass --detach
```
