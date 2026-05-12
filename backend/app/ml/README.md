# ML Pipeline

ML modules provide forecast and risk analysis for 상생나침반 reports and chat answers.

## Files

- `features.py`: builds per-area feature frames and training datasets.
- `forecaster.py`: Prophet-based quarterly sales forecasting with model cache.
- `risk_scorer.py`: XGBoost classifier and rule-based fallback risk score.
- `model_store.py`: joblib model and metadata persistence under `backend/models/`.
- `trainer.py`: training pipeline and synthetic fallback dataset generation.

## Runtime Behavior

If trained artifacts are unavailable, the app attempts to train during startup. If dependencies or data are insufficient, risk scoring falls back to deterministic rules so demo endpoints remain usable.

## Commands

```bash
python -c "
import asyncio
from app.ml.trainer import ModelTrainer
from app.core.database import get_db

async def main():
    async for db in get_db():
        await ModelTrainer().run_full_pipeline(db)
        break

asyncio.run(main())
"
```

Generated `*.pkl` files should stay out of Git.
