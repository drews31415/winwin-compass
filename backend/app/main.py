import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.api.routes import data as data_routes
from app.api.v1 import chat as v1_chat
from app.api.v1 import report as v1_report
from app.api.v1 import policy as v1_policy
from app.api.v1 import ml as v1_ml
from app.api.v1 import marketing as v1_marketing
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.data.collectors.scheduler import create_scheduler, initial_seed

logger = logging.getLogger(__name__)


async def _seed_rag() -> None:
    """RAG ?뺤콉 ?섑뵆 ?곗씠??珥덇린 ?곸옱 (OPENAI_API_KEY ?놁쑝硫??먮룞 ?ㅽ궢)."""
    try:
        from app.ai.rag_engine import PolicyRAGEngine
        count = await PolicyRAGEngine().seed_sample_policies()
        if count:
            logger.info("RAG: seeded %d sample policies", count)
    except Exception as exc:
        logger.warning("RAG seed skipped (non-fatal): %s", exc)


async def _prepare_ml_models() -> None:
    """Train required ML models if artifacts are missing."""
    try:
        from app.ml.trainer import ModelTrainer

        async with AsyncSessionLocal() as db:
            await ModelTrainer().run_full_pipeline(db)
    except Exception as exc:
        logger.warning("ML model preparation skipped (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("APScheduler started")

    seed_task     = asyncio.create_task(initial_seed())
    rag_seed_task = asyncio.create_task(_seed_rag())
    await _prepare_ml_models()

    yield

    seed_task.cancel()
    rag_seed_task.cancel()
    scheduler.shutdown(wait=False)
    logger.info("APScheduler stopped")


app = FastAPI(
    title="怨⑤ぉ ?섏묠諛?API",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ?? ?쇱슦???깅줉 ????????????????????????????????????????????????????????????????
@app.get("/api/v1/areas/{area_cd}", tags=["data"])
async def demo_area_detail(area_cd: str):
    samples = {
        "3110016": {"name": "\uc885\ub85c3\uac00", "gu": "\uc885\ub85c\uad6c", "type": "\uace8\ubaa9\uc0c1\uad8c", "lat": 37.5704, "lng": 126.9911, "sales": 238_000_000, "stores": 154, "open": 11.6, "close": 13.2, "ages": [5366, 31303, 25043, 17888, 7155, 2683]},
        "2640014": {"name": "\ud64d\ub300\uc785\uad6c", "gu": "\ub9c8\ud3ec\uad6c", "type": "\ubc1c\ub2ec\uc0c1\uad8c", "lat": 37.5563, "lng": 126.9236, "sales": 374_000_000, "stores": 304, "open": 17.7, "close": 17.4, "ages": [13312, 69222, 30617, 10649, 6656, 2662]},
        "3920008": {"name": "\ubd88\uad11\ub3d9", "gu": "\uc740\ud3c9\uad6c", "type": "\uace8\ubaa9\uc0c1\uad8c", "lat": 37.6105, "lng": 126.9292, "sales": 120_000_000, "stores": 90, "open": 9.8, "close": 9.4, "ages": [5324, 9318, 11980, 14643, 15309, 9984]},
    }
    sample = samples.get(area_cd, samples["3110016"])
    ages = sample["ages"]
    return {
        "area": {"area_cd": area_cd, "area_nm": sample["name"], "gu_nm": sample["gu"], "area_type": sample["type"], "geom_lat": sample["lat"], "geom_lng": sample["lng"]},
        "latest_quarter": "2026Q1",
        "sales": [{"area_cd": area_cd, "industry_cd": "CS100010", "industry_nm": "\ucee4\ud53c-\uc74c\ub8cc", "year_quarter": "2026Q1", "monthly_sales_avg": sample["sales"], "daily_sales_avg": int(sample["sales"] / 30), "weekday_sales": int(sample["sales"] * 0.62), "weekend_sales": int(sample["sales"] * 0.38), "time_slot_sales": {"06": int(sample["sales"] * 0.04), "09": int(sample["sales"] * 0.08), "12": int(sample["sales"] * 0.22), "14": int(sample["sales"] * 0.17), "18": int(sample["sales"] * 0.20), "20": int(sample["sales"] * 0.18), "21": int(sample["sales"] * 0.11)}}],
        "stores": [{"area_cd": area_cd, "year_quarter": "2026Q1", "industry_cd": "CS100010", "store_count": sample["stores"], "open_rate": sample["open"], "close_rate": sample["close"]}],
        "population": {"area_cd": area_cd, "year_quarter": "2026Q1", "total_population": sum(ages), "age_10s": ages[0], "age_20s": ages[1], "age_30s": ages[2], "age_40s": ages[3], "age_50s": ages[4], "age_60s": ages[5], "male_ratio": 0.48, "female_ratio": 0.52},
    }

app.include_router(health.router,       tags=["health"])
app.include_router(v1_chat.router,      prefix="/api/v1/chat",   tags=["chat"])
app.include_router(v1_report.router,    prefix="/api/v1/report", tags=["report"])
app.include_router(v1_policy.router,    prefix="/api/v1/policy", tags=["policy"])
app.include_router(v1_ml.router,        prefix="/api/v1/ml",     tags=["ml"])
app.include_router(v1_marketing.router, prefix="/api/v1/marketing", tags=["marketing"])
app.include_router(data_routes.router,  prefix="/api/v1",        tags=["data"])


@app.get("/")
async def root():
    return {"message": "怨⑤ぉ ?섏묠諛?API", "version": "0.2.0"}
