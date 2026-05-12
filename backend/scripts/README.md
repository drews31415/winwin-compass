# Backend Scripts

Operational scripts for demo setup and backend smoke tests.

## Scripts

- `seed_demo_data.py`: inserts stable 2026Q1 demo data for 종로3가, 홍대입구, and 불광동 plus sample policies.
- `smoke_test.sh`: checks health, area detail, ML risk, ML forecast, policy match, and simple chat endpoints.

## Usage

```bash
cd backend
python scripts/seed_demo_data.py
bash scripts/smoke_test.sh http://localhost:8000
bash scripts/smoke_test.sh https://winwin-compass-production.up.railway.app
```

The smoke script uses URL-encoded or escaped Korean strings to avoid terminal encoding issues on Windows.
