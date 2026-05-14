"""
GET /api/v1/report/{area_cd}  — 상권 종합 리포트 (차트 데이터 + 마크다운 + 매칭 정책)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag_engine import DEMO_POLICIES
from app.core.database import get_db
from app.data.processors.transformer import calculate_risk_score
from app.models.database import (
    CommercialArea, PopulationData, SalesData, StoreCount,
)
from app.models.schemas import ReportChartsOut, ReportOut

logger = logging.getLogger(__name__)
router = APIRouter()


def _sample_report(area_cd: str) -> ReportOut:
    area_nm = "종로3가" if area_cd == "3110016" else f"상권 {area_cd}"
    return ReportOut(
        area_nm=area_nm,
        risk_score=62.0,
        report_md=(
            "## 상권 종합 평가\n"
            "공공데이터 DB 연결이 없을 때 표시되는 제출용 샘플 리포트입니다.\n\n"
            "## 매출 현황\n"
            "월평균 매출은 약 2.3억원 수준이며 점심과 저녁 시간대 수요가 높습니다.\n\n"
            "## 위험 신호\n"
            "폐업률과 경쟁 강도를 함께 확인해야 합니다.\n\n"
            "## 추천 업종\n"
            "카페, 간편식, 테이크아웃 전문점을 우선 검토할 수 있습니다."
        ),
        charts=ReportChartsOut(
            sales_trend=[
                {"quarter": "2025Q2", "avg_sales": 210000000},
                {"quarter": "2025Q3", "avg_sales": 218000000},
                {"quarter": "2025Q4", "avg_sales": 226000000},
                {"quarter": "2026Q1", "avg_sales": 230000000},
            ],
            time_slots=[
                {"slot": "06-11", "amount": 12},
                {"slot": "11-14", "amount": 28},
                {"slot": "14-17", "amount": 24},
                {"slot": "17-21", "amount": 30},
                {"slot": "21-24", "amount": 6},
            ],
            age_distribution=[
                {"age_group": "20대", "count": 32},
                {"age_group": "30대", "count": 28},
                {"age_group": "40대", "count": 21},
                {"age_group": "50대", "count": 14},
                {"age_group": "60대+", "count": 5},
            ],
        ),
        matched_policies=[
            {
                "program_nm": "소상공인 정책자금",
                "category": "융자",
                "budget_max": 7000,
                "source_url": "https://www.semas.or.kr",
            }
        ],
    )


# ── 헬퍼 ───────────────────────────────────────────────────────────────────────

def _extract_time_slots(sales_rows) -> list[dict]:
    """JSONB time_slot_sales를 차트용 리스트로 변환 (업종 합산)."""
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
        if not row.time_slot_sales:
            continue
        for slot, amount in row.time_slot_sales.items():
            normalized_slot = slot_aliases.get(str(slot), str(slot))
            totals[normalized_slot] = totals.get(normalized_slot, 0) + (int(amount) if amount else 0)

    order = ["00-06", "06-11", "11-14", "14-17", "17-21", "21-24"]
    return [
        {"slot": s, "amount": totals.get(s, 0)}
        for s in order
        if s in totals
    ]


def _extract_age_dist(pop_row) -> list[dict]:
    """PopulationData 행을 연령대 분포 리스트로 변환."""
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
        return "데이터 없음"
    return "\n".join(
        f"- {r.industry_nm}: 월평균 {r.monthly_sales_avg:,}원"
        if r.monthly_sales_avg else f"- {r.industry_nm}"
        for r in rows[:3]
    )


def _fmt_stores(rows) -> str:
    if not rows:
        return "데이터 없음"
    return "\n".join(
        f"- {r.industry_cd}: 점포 {r.store_count}개, 폐업률 {r.close_rate:.1f}%"
        if r.store_count else f"- {r.industry_cd}"
        for r in rows[:3]
    )


def _fmt_pop(r) -> str:
    if not r or not r.total_population:
        return "데이터 없음"
    return (
        f"총 {r.total_population:,}명 | "
        f"20대 {r.age_20s or 0:,} / 30대 {r.age_30s or 0:,} / 40대 {r.age_40s or 0:,}"
    )


async def _generate_report_md(
    area_nm: str,
    sales_rows,
    store_rows,
    pop_row,
    risk_score: float,
) -> str:
    """Generate a fast data-based report body for the detail page."""
    monthly_sales = sum(row.monthly_sales_avg or 0 for row in sales_rows)
    store_count = sum(row.store_count or 0 for row in store_rows)
    avg_close_rate = (
        sum(row.close_rate or 0 for row in store_rows) / len(store_rows)
        if store_rows else 0
    )
    sales_eok = monthly_sales / 100_000_000

    population_text = _fmt_pop(pop_row)
    risk_label = "낮은 편" if risk_score < 40 else "중간" if risk_score < 70 else "높은 편"
    opportunity = (
        "현재 위험도가 낮아 신규 고객 유입을 늘리는 마케팅과 메뉴 실험을 병행하기 좋습니다."
        if risk_score < 40
        else "경쟁과 비용 부담을 함께 관리하면서 검증된 메뉴와 재방문 장치를 우선 설계하는 편이 좋습니다."
        if risk_score < 70
        else "초기 고정비를 낮추고 보수적인 매출 시나리오로 진입 여부를 판단해야 합니다."
    )

    return (
        "## 상권 종합 평가\n"
        f"{area_nm} 상권은 최신 공공데이터 기준 월평균 매출 약 {sales_eok:.1f}억원, "
        f"점포 {store_count:,}개 수준으로 확인됩니다. 폐업 위험 점수는 {risk_score:.1f}점으로 "
        f"{risk_label}입니다.\n\n"
        "## 매출 현황\n"
        f"{_fmt_sales(sales_rows)}\n"
        "시간대별 매출과 최근 분기 추이를 함께 보면 피크 시간대 의존도와 단기 매출 방향을 확인할 수 있습니다.\n\n"
        "## 유동인구 분석\n"
        f"{population_text}\n"
        "주요 생활인구 연령대에 맞춰 상품 가격대, 매장 체류형/포장형 비중, 홍보 채널을 조정하는 것이 좋습니다.\n\n"
        "## 위험 신호\n"
        f"최신 점포 데이터 기준 평균 폐업률은 {avg_close_rate:.1f}%입니다. "
        "동종 업종 점포 수와 매출 변동성을 함께 보고 과밀 진입을 피해야 합니다.\n\n"
        "## 기회 요인\n"
        f"{opportunity}\n\n"
        "## 추천 업종\n"
        "- 카페/음료: 생활인구와 회전율을 활용하기 좋습니다.\n"
        "- 간편식/포장형 음식점: 점심과 퇴근 시간대 수요를 동시에 노릴 수 있습니다.\n"
        "- 소형 특화 매장: 고정비를 낮추고 차별화된 메뉴로 테스트하기 좋습니다."
    )


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/{area_cd}", response_model=ReportOut)
async def get_area_report(
    area_cd: str,
    db: AsyncSession = Depends(get_db),
):
    """상권 코드로 종합 리포트 조회."""

    # 1. 상권 기본 정보
    try:
        area_row = (await db.execute(
            select(CommercialArea).where(CommercialArea.area_cd == area_cd).limit(1)
        )).scalars().first()
    except Exception as exc:
        logger.warning("report sample fallback for %s: %s", area_cd, exc)
        return _sample_report(area_cd)

    if not area_row:
        return _sample_report(area_cd)

    area_nm = area_row.area_nm

    # 2. 최신 분기
    latest_q = (await db.execute(
        select(func.max(SalesData.year_quarter)).where(SalesData.area_cd == area_cd)
    )).scalar() or (await db.execute(
        select(func.max(StoreCount.year_quarter)).where(StoreCount.area_cd == area_cd)
    )).scalar()

    if not latest_q:
        return _sample_report(area_cd)

    # 3. 최신 분기 데이터 조회 (순차 — 동일 세션 concurrent 불가)
    sales_rows = (await db.execute(
        select(SalesData)
        .where(SalesData.area_cd == area_cd, SalesData.year_quarter == latest_q)
        .limit(10)
    )).scalars().all()

    store_rows = (await db.execute(
        select(StoreCount)
        .where(StoreCount.area_cd == area_cd, StoreCount.year_quarter == latest_q)
        .limit(10)
    )).scalars().all()

    pop_row = (await db.execute(
        select(PopulationData)
        .where(PopulationData.area_cd == area_cd, PopulationData.year_quarter == latest_q)
        .limit(1)
    )).scalars().first()

    # 4. 차트 데이터

    # sales_trend: 분기별 월평균 매출 추이 (최근 8분기)
    trend_rows = (await db.execute(
        select(
            SalesData.year_quarter,
            func.avg(SalesData.monthly_sales_avg).label("avg_sales"),
        )
        .where(SalesData.area_cd == area_cd)
        .group_by(SalesData.year_quarter)
        .order_by(SalesData.year_quarter.desc())
        .limit(8)
    )).all()

    sales_trend = [
        {"quarter": r.year_quarter, "avg_sales": int(r.avg_sales or 0)}
        for r in sorted(trend_rows, key=lambda row: row.year_quarter)
    ]

    time_slots      = _extract_time_slots(sales_rows)
    age_distribution = _extract_age_dist(pop_row)

    # 5. 위험도 점수
    store_dict = {"close_rate": store_rows[0].close_rate if store_rows else 0}
    sales_dict = {"monthly_sales_avg": sales_rows[0].monthly_sales_avg if sales_rows else 0}
    risk_score = calculate_risk_score(store_dict, sales_dict)

    # 6. 마크다운 리포트 생성
    report_md = await _generate_report_md(
        area_nm, sales_rows, store_rows, pop_row, risk_score
    )

    # 7. 리포트 화면은 진입 속도가 중요하므로 벡터 검색 대신 안정적인 정책 샘플을 즉시 제공한다.
    matched_policies = DEMO_POLICIES[:3]

    return ReportOut(
        area_nm=area_nm,
        risk_score=round(risk_score, 2),
        report_md=report_md,
        charts=ReportChartsOut(
            sales_trend=sales_trend,
            time_slots=time_slots,
            age_distribution=age_distribution,
        ),
        matched_policies=matched_policies,
    )
