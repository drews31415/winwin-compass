# Backend Models

Database and schema definitions for 상생나침반.

## Files

- `database.py`: SQLAlchemy ORM tables such as commercial areas, sales data, store counts, population data, workers, and policy programs.
- `schemas.py`: Pydantic request/response models used by API routes.

## Guidelines

Keep persistent database shape in ORM models and HTTP payload validation in schemas. When adding a table, also add or update an Alembic migration under `backend/alembic/`.

## Naming

Use snake_case table and column names. Keep public API field names stable because frontend charts and cards depend on them.
