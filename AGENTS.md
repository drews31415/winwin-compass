# Repository Guidelines

## Project Structure & Module Organization

This repository is a monorepo for 상생나침반.

- `frontend/`: Next.js App Router frontend. Pages live in `app/`, shared UI in `components/`, API helpers and hooks in `lib/`, and Playwright smoke tests in `tests/`.
- `backend/`: FastAPI backend. Entry point is `app/main.py`; API routers are under `app/api/`; settings/database setup are in `app/core/`; AI orchestration is in `app/ai/`; public data collectors are in `app/data/`; ML code is in `app/ml/`; ORM models are in `app/models/`.
- `backend/scripts/`: demo data seeding and API smoke tests.
- `scripts/`: repository-level demo automation, including Playwright recording.
- `.github/workflows/`: CI/CD workflows for Railway and Vercel.

## Build, Test, and Development Commands

Infrastructure:

```bash
docker-compose up -d
```

Backend:

```bash
cd backend
pip install -r requirements.txt --prefer-binary
uvicorn app.main:app --reload --port 8000
python scripts/seed_demo_data.py
bash scripts/smoke_test.sh http://localhost:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
```

Deployment:

```bash
vercel --prod --yes
railway up backend --path-as-root --service winwin-compass --detach
```

## Coding Style & Naming Conventions

Use TypeScript for frontend code and Python 3.11+ for backend code. Prefer 2-space indentation in TSX/TS and 4-space indentation in Python. Name React components in `PascalCase`, hooks as `useSomething`, backend modules in `snake_case`, and route files by feature, e.g. `report.py`.

Use Tailwind utilities and existing UI components in `frontend/components/ui/`. Keep API response shapes explicit when consuming backend endpoints. Keep the existing `brand-*` Tailwind token names unless doing a dedicated design-token migration.

## Testing Guidelines

For frontend changes, run `npm run build` at minimum. Use `frontend/tests/deploy-smoke.spec.ts` for deployed page smoke checks. For backend changes, run the FastAPI server and `bash backend/scripts/smoke_test.sh`. Add focused `test_*.py` files for non-trivial backend logic.

## Architecture Notes

External services should degrade gracefully. Missing Seoul/OpenAI/DB dependencies should fall back to sample or demo-safe data where possible. Chat streaming uses `POST /api/v1/chat` with SSE-formatted response chunks. Map rendering uses Mapbox only when `NEXT_PUBLIC_MAPBOX_TOKEN` starts with `pk.`; otherwise it falls back to Leaflet/OpenStreetMap.

## Commit & Pull Request Guidelines

Use conventional-style commits such as `feat: add report chart` or `fix: handle missing API key`. Pull requests should include a summary, verification commands, linked issues if any, screenshots for UI changes, and any required environment or migration notes.

## Security & Configuration Tips

Never commit real secrets. Use `.env.example` as the template and set production values in Railway, Vercel, and GitHub Secrets. Keep generated artifacts such as `.next/`, `node_modules/`, `__pycache__/`, `.venv/`, `demo_videos/`, and model `*.pkl` files out of commits.
