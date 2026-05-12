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
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.data.collectors.scheduler import create_scheduler, initial_seed

logger = logging.getLogger(__name__)


async def _seed_rag() -> None:
    """RAG 정책 샘플 데이터 초기 적재 (OPENAI_API_KEY 없으면 자동 스킵)."""
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
    title="골목 나침반 API",
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

# ── 라우터 등록 ────────────────────────────────────────────────────────────────
app.include_router(health.router,       tags=["health"])
app.include_router(v1_chat.router,      prefix="/api/v1/chat",   tags=["chat"])
app.include_router(v1_report.router,    prefix="/api/v1/report", tags=["report"])
app.include_router(v1_policy.router,    prefix="/api/v1/policy", tags=["policy"])
app.include_router(v1_ml.router,        prefix="/api/v1/ml",     tags=["ml"])
app.include_router(data_routes.router,  prefix="/api/v1",        tags=["data"])


@app.get("/")
async def root():
    return {"message": "골목 나침반 API", "version": "0.2.0"}
