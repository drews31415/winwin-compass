"""Commercial-area report endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import REPORT_PROMPT, SYSTEM_PROMPT
from app.ai.rag_engine import PolicyRAGEngine
from app.core.config import settings
from app.core.database import get_db
from app.data.processors.transformer import calculate_risk_score
from app.models.database import CommercialArea, PopulationData, SalesData, StoreCount
from app.models.schemas import ReportChartsOut, ReportOut

logger = logging.getLogger(__name__)
router = APIRouter()
_rag = PolicyRAGEngine()
_llm: Any = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI

        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )
    return _llm


def _industry_label(industry_cd: str, industry_names: dict[str, str]) -> str:
    return industry_names.get(industry_cd) or "기타 업종"


def _extract_time_slots(sales_rows) -> list[dict]:
    slot_aliases = {
        "00": "00-06",
        "00-06": "00-06",
        "06": "06-11",
        "09": "06-11",
        "06-11": "06-11",
        "11": "11-14",
        "12": "11-14",
        "11-14": "11-14",
        "14": "14-17",
        "15": "14-17",
        "14-17": "14-17",
        "17": "17-21",
        "18": "17-21",
        "20": "17-21",
        "17-21": "17-21",
        "21": "21-24",
        "21-24": "21-24",
    }
    totals: dict[str, int] = {}
    for row in sales_rows:
        for slot, amount in (row.time_slot_sales or {}).items():
            normalized = slot_aliases.get(str(slot), str(slot))
            totals[normalized] = totals.get(normalized, 0) + int(amount or 0)

    order = ["00-06", "06-11", "11-14", "14-17", "17-21", "21-24"]
    return [{"slot": slot, "amount": totals.get(slot, 0)} for slot in order if slot in totals]


def _extract_age_dist(pop_row) -> list[dict]:
    if not pop_row:
        return []
    mapping = [
        ("10대", pop_row.age_10s),
        ("20대", pop_row.age_20s),
        ("30대", pop_row.age_30s),
        ("40대", pop_row.age_40s),
        ("50대", pop_row.age_50s),
        ("60대+", pop_row.age_60s),
    ]
    return [
        {"age_group": label, "count": count or 0}
        for label, count in mapping
        if count is not None
    ]


def _fmt_sales(rows) -> str:
    if not rows:
        return "수집된 매출 데이터가 없습니다."
    return "\n".join(
        f"- {row.industry_nm or row.industry_cd}: 월평균 {row.monthly_sales_avg:,}원"
        if row.monthly_sales_avg
        else f"- {row.industry_nm or row.industry_cd}"
        for row in rows[:3]
    )


def _fmt_stores(rows, industry_names: dict[str, str]) -> str:
    if not rows:
        return "수집된 점포 데이터가 없습니다."
    return "\n".join(
        f"- {_industry_label(row.industry_cd, industry_names)}: 점포 {row.store_count}개, 폐업률 {row.close_rate:.1f}%"
        if row.store_count
        else f"- {_industry_label(row.industry_cd, industry_names)}"
        for row in rows[:3]
    )


def _fmt_pop(row) -> str:
    if not row or not row.total_population:
        return "수집된 유동인구 데이터가 없습니다."
    return (
        f"총 {row.total_population:,}명 | "
        f"20대 {row.age_20s or 0:,} / 30대 {row.age_30s or 0:,} / 40대 {row.age_40s or 0:,}"
    )


def _fallback_report_md(
    area_nm: str,
    sales_rows,
    store_rows,
    pop_row,
    risk_score: float,
    industry_names: dict[str, str],
) -> str:
    industry_names = {
        **industry_names,
        **{
            row.industry_cd: row.industry_nm
            for row in sales_rows
            if row.industry_cd and row.industry_nm
        },
    }
    top_sales = sales_rows[0] if sales_rows else None
    lowest_close = min(store_rows, key=lambda row: row.close_rate or 0) if store_rows else None
    high_close = max(store_rows, key=lambda row: row.close_rate or 0) if store_rows else None

    opportunity = "매출과 점포 수가 함께 확인되는 업종을 우선 검토하세요."
    if top_sales:
        opportunity = (
            f"{top_sales.industry_nm or top_sales.industry_cd} 업종은 현재 수집 데이터에서 매출 규모가 가장 크게 나타납니다."
        )

    recommendation = "폐업률과 경쟁 밀도를 함께 확인한 뒤 진입 업종을 좁히세요."
    if lowest_close:
        recommendation = (
            f"{_industry_label(lowest_close.industry_cd, industry_names)}처럼 폐업률이 낮게 잡힌 업종은 "
            "후보군으로 검토할 수 있습니다."
        )

    caution = "점포 데이터가 더 쌓이면 위험 신호를 더 구체화할 수 있습니다."
    if high_close:
        caution = (
            f"{_industry_label(high_close.industry_cd, industry_names)}은 폐업률이 "
            f"{high_close.close_rate:.1f}%로 상대적으로 높아 비용 구조와 경쟁 상황을 먼저 확인해야 합니다."
        )

    return (
        "## 상권 종합 평가\n"
        f"{area_nm} 상권은 서울시 공공데이터에서 수집한 매출, 점포, 유동인구 데이터를 기준으로 분석했습니다. "
        f"현재 폐업 위험 점수는 {round(risk_score, 1)}점입니다.\n\n"
        "## 매출 현황\n"
        f"{_fmt_sales(sales_rows)}\n\n"
        "## 유동인구 분석\n"
        f"{_fmt_pop(pop_row)}\n\n"
        "## 위험 신호\n"
        f"{_fmt_stores(store_rows, industry_names)}\n\n"
        "## 기회 요인\n"
        f"{opportunity}\n\n"
        "## 추천 업종\n"
        f"- {recommendation}\n"
        f"- {caution}"
    )


async def _generate_report_md(
    area_nm: str,
    sales_rows,
    store_rows,
    pop_row,
    risk_score: float,
    industry_names: dict[str, str],
) -> str:
    if not settings.OPENAI_API_KEY:
        return _fallback_report_md(
            area_nm,
            sales_rows,
            store_rows,
            pop_row,
            risk_score,
            industry_names,
        )

    context = REPORT_PROMPT.format(
        area_nm=area_nm,
        sales_data=_fmt_sales(sales_rows),
        store_data=_fmt_stores(store_rows, industry_names),
        population_data=_fmt_pop(pop_row),
        risk_score=round(risk_score, 1),
    )

    from langchain_core.messages import HumanMessage, SystemMessage

    response = await _get_llm().ainvoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=context)]
    )
    return response.content


async def _industry_names_for_store_rows(
    db: AsyncSession,
    area_cd: str,
    latest_q: str,
    store_rows,
) -> dict[str, str]:
    store_industry_codes = [row.industry_cd for row in store_rows if row.industry_cd]
    if not store_industry_codes:
        return {}

    name_rows = (
        await db.execute(
            select(SalesData.industry_cd, SalesData.industry_nm)
            .where(
                SalesData.area_cd == area_cd,
                SalesData.year_quarter == latest_q,
                SalesData.industry_cd.in_(store_industry_codes),
            )
            .distinct()
        )
    ).all()
    names = {
        row.industry_cd: row.industry_nm
        for row in name_rows
        if row.industry_cd and row.industry_nm
    }

    missing_codes = [code for code in store_industry_codes if code not in names]
    if missing_codes:
        fallback_name_rows = (
            await db.execute(
                select(SalesData.industry_cd, SalesData.industry_nm)
                .where(SalesData.industry_cd.in_(missing_codes))
                .distinct()
            )
        ).all()
        names.update(
            {
                row.industry_cd: row.industry_nm
                for row in fallback_name_rows
                if row.industry_cd and row.industry_nm
            }
        )

    return names


@router.get("/{area_cd}", response_model=ReportOut)
async def get_area_report(
    area_cd: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        area = (
            await db.execute(
                select(CommercialArea).where(CommercialArea.area_cd == area_cd).limit(1)
            )
        ).scalars().first()
    except Exception as exc:
        logger.exception("report area lookup failed for %s", area_cd)
        raise HTTPException(status_code=503, detail="상권 데이터를 조회할 수 없습니다.") from exc

    if not area:
        raise HTTPException(status_code=404, detail="수집된 상권 정보가 없습니다.")

    latest_q = (
        await db.execute(
            select(func.max(SalesData.year_quarter)).where(SalesData.area_cd == area_cd)
        )
    ).scalar() or (
        await db.execute(
            select(func.max(StoreCount.year_quarter)).where(StoreCount.area_cd == area_cd)
        )
    ).scalar()

    if not latest_q:
        raise HTTPException(
            status_code=404,
            detail="이 상권의 매출/점포 데이터가 아직 수집되지 않았습니다.",
        )

    sales_rows = (
        await db.execute(
            select(SalesData)
            .where(SalesData.area_cd == area_cd, SalesData.year_quarter == latest_q)
            .order_by(desc(SalesData.monthly_sales_avg))
            .limit(10)
        )
    ).scalars().all()

    store_rows = (
        await db.execute(
            select(StoreCount)
            .where(StoreCount.area_cd == area_cd, StoreCount.year_quarter == latest_q)
            .order_by(desc(StoreCount.close_rate), desc(StoreCount.store_count))
            .limit(10)
        )
    ).scalars().all()

    industry_names = await _industry_names_for_store_rows(
        db,
        area_cd,
        latest_q,
        store_rows,
    )

    pop_row = (
        await db.execute(
            select(PopulationData)
            .where(PopulationData.area_cd == area_cd, PopulationData.year_quarter == latest_q)
            .limit(1)
        )
    ).scalars().first()

    trend_rows = (
        await db.execute(
            select(
                SalesData.year_quarter,
                func.avg(SalesData.monthly_sales_avg).label("avg_sales"),
            )
            .where(SalesData.area_cd == area_cd)
            .group_by(SalesData.year_quarter)
            .order_by(desc(SalesData.year_quarter))
            .limit(8)
        )
    ).all()

    sales_trend = [
        {"quarter": row.year_quarter, "avg_sales": int(row.avg_sales or 0)}
        for row in sorted(trend_rows, key=lambda item: item.year_quarter)
    ]

    store_input = {"close_rate": store_rows[0].close_rate if store_rows else 0}
    sales_input = {"monthly_sales_avg": sales_rows[0].monthly_sales_avg if sales_rows else 0}
    risk_score = calculate_risk_score(store_input, sales_input)

    report_md = await _generate_report_md(
        area.area_nm,
        sales_rows,
        store_rows,
        pop_row,
        risk_score,
        industry_names,
    )

    try:
        matched_policies = await _rag.search_policies(area.area_nm, k=3)
        if not matched_policies:
            matched_policies = await _rag.search_policies("소상공인 지원", k=3)
    except Exception as exc:
        logger.warning("policy search failed: %s", exc)
        matched_policies = []

    return ReportOut(
        area_nm=area.area_nm,
        risk_score=round(risk_score, 2),
        report_md=report_md,
        charts=ReportChartsOut(
            sales_trend=sales_trend,
            time_slots=_extract_time_slots(sales_rows),
            age_distribution=_extract_age_dist(pop_row),
        ),
        matched_policies=matched_policies,
    )
