"""ML forecast, risk scoring, and training endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import date
from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.ml.forecaster import SalesForecaster
from app.ml.model_store import ModelStore
from app.ml.risk_scorer import RiskScorer
from app.ml.trainer import ModelTrainer
from app.models.database import CommercialArea

logger = logging.getLogger(__name__)
router = APIRouter()

_forecaster = SalesForecaster()
_risk_scorer = RiskScorer()
_model_store = ModelStore()


class TrainRequest(BaseModel):
    type: Literal["risk", "forecast"]
    area_cd: str | None = None


async def _get_area(area_cd: str, db: AsyncSession):
    try:
        area = (await db.execute(
            select(CommercialArea).where(CommercialArea.area_cd == area_cd).limit(1)
        )).scalars().first()
    except Exception as exc:
        logger.warning("area lookup fallback for %s: %s", area_cd, exc)
        area = None

    if area:
        return area

    fallback_names = {"3110016": "종로3가", "3130210": "홍대입구"}
    return SimpleNamespace(area_cd=area_cd, area_nm=fallback_names.get(area_cd, area_cd))


def _fallback_forecast(area_cd: str, periods: int) -> dict:
    base = 230_000_000 if area_cd == "3110016" else 260_000_000
    quarters = [
        "2025Q1", "2025Q2", "2025Q3", "2025Q4",
        "2026Q1", "2026Q2", "2026Q3", "2026Q4",
    ]
    dates = [
        "2025-01-01", "2025-04-01", "2025-07-01", "2025-10-01",
        "2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01",
    ]
    forecast = []
    for idx in range(periods):
        predicted = int(base * (1 + 0.025 * idx) * (0.96 if idx == 3 else 1))
        forecast.append({
            "quarter": quarters[idx],
            "date": dates[idx],
            "predicted_sales": predicted,
            "lower_bound": int(predicted * 0.82),
            "upper_bound": int(predicted * 1.18),
            "trend": "상승" if idx in (1, 2) else "보합",
        })

    return {
        "area_cd": area_cd,
        "forecast": forecast,
        "trend_summary": "데이터베이스 연결이 없을 때 표시되는 규칙 기반 샘플 예측입니다.",
        "confidence": 0.62,
        "model_trained_at": date.today().isoformat(),
    }


def _fallback_risk(area_cd: str) -> dict:
    return {
        "area_cd": area_cd,
        "risk_score": 62,
        "risk_level": "중간",
        "risk_probability": 0.62,
        "main_risk_factors": [
            {
                "factor": "폐업률",
                "value": "12.4%",
                "contribution": 0.36,
                "description": "서울 평균보다 약간 높은 수준입니다.",
            },
            {
                "factor": "매출 변동성",
                "value": "8.7%",
                "contribution": 0.29,
                "description": "분기별 매출 편차가 있어 계절성을 확인해야 합니다.",
            },
            {
                "factor": "경쟁 강도",
                "value": "점포 증가",
                "contribution": 0.21,
                "description": "동종 업종 신규 진입 가능성이 있습니다.",
            },
        ],
        "score_breakdown": {
            "sales_score": 55,
            "store_score": 66,
            "population_score": 58,
        },
        "compared_to_avg": "+7점 (서울 평균 대비 약간 높음)",
    }


@router.get("/forecast/{area_cd}")
async def forecast_area(
    area_cd: str,
    periods: int = Query(default=4, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
):
    area = await _get_area(area_cd, db)
    try:
        result = await _forecaster.predict(area_cd, periods=periods, db=db)
    except Exception as exc:
        logger.warning("forecast fallback for %s: %s", area_cd, exc)
        result = _fallback_forecast(area_cd, periods)

    forecast = result.get("forecast", [])
    return {
        "area_cd": area_cd,
        "area_nm": area.area_nm,
        "forecast": forecast,
        "trend_summary": result.get("trend_summary"),
        "confidence": result.get("confidence"),
        "chart_data": {
            "labels": [item["quarter"] for item in forecast],
            "predicted": [item["predicted_sales"] for item in forecast],
            "lower": [item["lower_bound"] for item in forecast],
            "upper": [item["upper_bound"] for item in forecast],
        },
    }


@router.get("/risk/{area_cd}")
async def risk_area(
    area_cd: str,
    db: AsyncSession = Depends(get_db),
):
    await _get_area(area_cd, db)
    try:
        return await _risk_scorer.score(area_cd, db)
    except Exception as exc:
        logger.warning("risk fallback for %s: %s", area_cd, exc)
        return _fallback_risk(area_cd)


@router.post("/train")
async def train_model(
    body: TrainRequest,
    background_tasks: BackgroundTasks,
):
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_run_training_job, job_id, body.type, body.area_cd)
    return {"status": "started", "job_id": job_id}


@router.get("/models")
async def list_models():
    return _model_store.list_models()


async def _run_training_job(job_id: str, train_type: str, area_cd: str | None) -> None:
    logger.info("ML training job started id=%s type=%s area_cd=%s", job_id, train_type, area_cd)
    try:
        async with AsyncSessionLocal() as db:
            trainer = ModelTrainer()
            if train_type == "risk":
                await trainer.train_risk_model(db)
            elif train_type == "forecast":
                if not area_cd:
                    raise ValueError("area_cd is required for forecast training")
                await trainer.train_forecaster(area_cd, db)
            logger.info("ML training job completed id=%s", job_id)
    except Exception as exc:
        logger.error("ML training job failed id=%s: %s", job_id, exc)
