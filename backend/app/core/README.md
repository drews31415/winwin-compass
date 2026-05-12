# Core Backend Services

Shared infrastructure code for the FastAPI backend.

## Files

- `config.py`: Pydantic settings, environment loading, CORS origins, Railway database URL normalization.
- `database.py`: async SQLAlchemy engine, session factory, `get_db` dependency, and pgvector initialization.

## Guidelines

Keep environment parsing and cross-cutting backend configuration here. Feature modules should import `settings` or `get_db` rather than reading environment variables directly.

## Important Variables

- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `SEOUL_API_KEY`
- `CORS_ORIGINS`
- `PORT`
