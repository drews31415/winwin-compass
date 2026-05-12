# Repository Guidelines

## Project Structure & Module Organization

This repository is a monorepo for Golmok Compass.

- `frontend/`: Next.js App Router frontend. Pages live in `app/`, shared UI in `components/`, API helpers and hooks in `lib/`, static assets in `public/`.
- `backend/`: FastAPI backend. Main app entry is `app/main.py`; API routes are under `app/api/`; settings and database setup are in `app/core/`; SQLAlchemy models and schemas are in `app/models/`; AI logic is in `app/ai/`; data collectors/processors are in `app/data/`.
- `backend/alembic/`: database migrations.
- `docker-compose.yml` and `docker/`: local PostgreSQL with pgvector and Redis.
- `.env.example`: required environment variable template.

## Build, Test, and Development Commands

Run infrastructure from the repository root:

```bash
docker-compose up -d
```

Backend:

```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt --prefer-binary
uvicorn app.main:app --reload --port 8000
python test_endpoints.py
```

Database migrations:

```bash
cd backend
alembic check
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

`npm run dev` starts the Next.js app, `npm run build` validates production compilation, and `npm run lint` runs Next ESLint checks.

## Coding Style & Naming Conventions

Use TypeScript for frontend code and Python 3.11+ for backend code. Prefer 2-space indentation in TSX/TS and 4-space indentation in Python. Name React components in `PascalCase`, hooks as `useSomething`, backend modules in `snake_case`, and API route files by feature, e.g. `report.py`.

Use Tailwind utility classes and existing shadcn-style components in `frontend/components/ui/`. Keep API response types explicit in frontend files when consuming backend endpoints.

Follow the existing Golmok design tokens in `tailwind.config.ts`: primary `#2D6A4F`, accent `#F4A261`, surface `#F8F7F2`, and risk colors `risk-low`, `risk-mid`, `risk-high`.

## Testing Guidelines

Current backend smoke coverage is `backend/test_endpoints.py`; run it with the FastAPI server already listening on `localhost:8000`. Add future backend tests as `test_*.py`. For frontend changes, run `npm run build` at minimum; add component or route tests when introducing non-trivial UI state.

## Architecture Notes

External services should degrade gracefully in development. Empty `SEOUL_API_KEY` should use Seoul API dummy data, empty `OPENAI_API_KEY` should return sample AI context, and sparse map data may fall back to hardcoded Seoul samples.

Chat streaming uses `POST /api/v1/chat` with `StreamingResponse` and SSE lines like `data: {"chunk": "..."}` followed by `data: [DONE]`. The frontend should read the `fetch` response stream with `ReadableStream`/`TextDecoder`; do not use `EventSource` for this POST flow.

Map rendering chooses Mapbox only when `NEXT_PUBLIC_MAPBOX_TOKEN` is present and starts with `pk.`; otherwise use the Leaflet/OpenStreetMap fallback. Keep `mapbox-gl/dist/mapbox-gl.css` imported globally.

## Commit & Pull Request Guidelines

No Git history is available in this checkout, so use clear conventional-style commits such as `feat: add report dashboard` or `fix: handle missing Seoul API key`.

Pull requests should include a short summary, verification commands run, linked issues if any, and screenshots or screen recordings for UI changes. Mention any required environment variables or migration steps.

## Security & Configuration Tips

Never commit real secrets. Copy `.env.example` to local `.env` files and set `OPENAI_API_KEY`, `SEOUL_API_KEY`, `DATABASE_URL`, `REDIS_URL`, and frontend `NEXT_PUBLIC_*` values as needed. Keep generated caches such as `.next/`, `node_modules/`, `__pycache__/`, and virtual environments out of commits.

On Windows, keep config files such as `alembic.ini` ASCII-only to avoid `cp949` decode issues. Keep `next.config.mjs` as `.mjs`; avoid adding a webpack alias for `mapbox-gl`, which breaks CSS subpath resolution.
