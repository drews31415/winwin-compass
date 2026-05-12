# Backend App Modules

This directory contains the runtime FastAPI application.

## Module Map

- `main.py`: app creation, CORS, lifespan startup tasks, and router registration.
- `api/`: versioned and compatibility API routers.
- `core/`: `Settings`, async SQLAlchemy engine, and DB session dependency.
- `models/`: ORM table definitions and API schemas.
- `ai/`: prompt templates, Text-to-SQL, policy RAG, and chat orchestration.
- `data/`: Seoul Open API clients, cache/rate limiting, scheduler, and data transformers.
- `ml/`: feature engineering, Prophet forecasting, XGBoost/rule-based risk scoring, and model persistence.

## Startup Behavior

The FastAPI lifespan starts the APScheduler, seeds policy RAG samples, and prepares ML models when artifacts are missing. These tasks are non-fatal so demos can still run if DB, Redis, or model training fails.

## Adding Features

Add new user-facing endpoints under `api/v1/`. Put reusable domain logic in `ai/`, `data/`, or `ml/` rather than directly in routers. Keep router responses JSON-serializable and provide fallbacks for demo-critical flows.
