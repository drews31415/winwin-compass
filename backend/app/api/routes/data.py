import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.data.collectors.seoul_api import SeoulOpenAPI
from app.data.processors.transformer import calculate_risk_score
from app.models.database import CommercialArea, PopulationData, SalesData, StoreCount
from app.models.schemas import (
    AreaDetailOut,
    AreaMapFeature,
    AreaOut,
    CollectOut,
    PopulationOut,
    RiskOut,
    SalesOut,
    StoreOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _prev_quarter(yq: str) -> str:
    """'2024Q3' → '2024Q2', '2024Q1' → '2023Q4'"""
    year, q = int(yq[:4]), int(yq[-1])
    return f"{year - 1}Q4" if q == 1 else f"{year}Q{q - 1}"


async def _ensure_area(db: AsyncSession, area_cd: str) -> CommercialArea:
    """
    CommercialArea가 없으면 stub 레코드를 즉시 생성.
    API 호출 없이 빠르게 처리 — 상세 정보는 initial_seed 또는 수집 후 채워진다.
    """
    result = await db.execute(select(CommercialArea).where(CommercialArea.area_cd == area_cd))
    area = result.scalar_one_or_none()
    if area is not None:
        return area

    area = CommercialArea(
        area_cd=area_cd,
        area_nm=area_cd,   # initial_seed 이후 갱신 예정
        gu_nm="",
        area_type="기타",
    )
    db.add(area)
    await db.commit()
    await db.refresh(area)
    logger.info("_ensure_area: stub created for %s", area_cd)
    return area


async def _bg_collect(area_cd: str, year_quarter: str) -> None:
    """BackgroundTask — 별도 세션으로 수집 후 저장."""
    try:
        async with AsyncSessionLocal() as session:
            async with SeoulOpenAPI() as api:
                count = await api.fetch_and_save(session, area_cd, year_quarter)
        logger.info("bg_collect done: area=%s quarter=%s count=%d", area_cd, year_quarter, count)
    except Exception as exc:
        logger.error("bg_collect failed: area=%s: %s", area_cd, exc)


# ── GET /areas ────────────────────────────────────────────────────────────────

@router.get("/areas", response_model=list[AreaOut], summary="전체 상권 목록")
async def list_areas(
    gu_nm: str | None = None,
    area_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CommercialArea)
    if gu_nm:
        stmt = stmt.where(CommercialArea.gu_nm.ilike(f"%{gu_nm}%"))
    if area_type:
        stmt = stmt.where(CommercialArea.area_type == area_type)
    stmt = stmt.order_by(CommercialArea.area_nm).offset(offset).limit(limit)

    rows = (await db.execute(stmt)).scalars().all()
    return [AreaOut.model_validate(r) for r in rows]


# ── GET /areas/map ────────────────────────────────────────────────────────────

_SAMPLE_MAP_AREAS: list[dict] = [
    {"area_cd": "3110016", "area_nm": "홍대입구역", "gu_nm": "마포구", "area_type": "발달상권", "lat": 37.5563, "lng": 126.9237, "monthly_sales_avg": 230_000_000, "store_count": 147, "risk_score": 0.38, "main_industry": "카페"},
    {"area_cd": "3220005", "area_nm": "강남역", "gu_nm": "강남구", "area_type": "발달상권", "lat": 37.4979, "lng": 127.0276, "monthly_sales_avg": 410_000_000, "store_count": 312, "risk_score": 0.22, "main_industry": "음식점"},
    {"area_cd": "3010007", "area_nm": "명동", "gu_nm": "중구", "area_type": "관광특구", "lat": 37.5636, "lng": 126.9822, "monthly_sales_avg": 180_000_000, "store_count": 98, "risk_score": 0.71, "main_industry": "의류"},
    {"area_cd": "3140011", "area_nm": "이태원", "gu_nm": "용산구", "area_type": "관광특구", "lat": 37.5345, "lng": 126.9943, "monthly_sales_avg": 125_000_000, "store_count": 76, "risk_score": 0.68, "main_industry": "음식점"},
    {"area_cd": "3110008", "area_nm": "신촌·연세로", "gu_nm": "서대문구", "area_type": "발달상권", "lat": 37.5559, "lng": 126.9367, "monthly_sales_avg": 150_000_000, "store_count": 203, "risk_score": 0.45, "main_industry": "음식점"},
    {"area_cd": "3010012", "area_nm": "동대문", "gu_nm": "중구", "area_type": "발달상권", "lat": 37.5710, "lng": 127.0097, "monthly_sales_avg": 95_000_000, "store_count": 184, "risk_score": 0.63, "main_industry": "의류"},
    {"area_cd": "3110015", "area_nm": "합정역", "gu_nm": "마포구", "area_type": "지역상권", "lat": 37.5498, "lng": 126.9147, "monthly_sales_avg": 88_000_000, "store_count": 64, "risk_score": 0.28, "main_industry": "카페"},
    {"area_cd": "3270003", "area_nm": "건대입구역", "gu_nm": "광진구", "area_type": "발달상권", "lat": 37.5403, "lng": 127.0695, "monthly_sales_avg": 172_000_000, "store_count": 137, "risk_score": 0.41, "main_industry": "음식점"},
    {"area_cd": "3230010", "area_nm": "잠실역", "gu_nm": "송파구", "area_type": "발달상권", "lat": 37.5133, "lng": 127.1000, "monthly_sales_avg": 310_000_000, "store_count": 228, "risk_score": 0.19, "main_industry": "음식점"},
    {"area_cd": "3050004", "area_nm": "광장시장", "gu_nm": "종로구", "area_type": "전통시장", "lat": 37.5703, "lng": 126.9978, "monthly_sales_avg": 83_000_000, "store_count": 214, "risk_score": 0.48, "main_industry": "음식점"},
    {"area_cd": "3200008", "area_nm": "신림역", "gu_nm": "관악구", "area_type": "지역상권", "lat": 37.4843, "lng": 126.9290, "monthly_sales_avg": 61_000_000, "store_count": 95, "risk_score": 0.52, "main_industry": "편의점"},
    {"area_cd": "3220012", "area_nm": "청담동", "gu_nm": "강남구", "area_type": "발달상권", "lat": 37.5231, "lng": 127.0472, "monthly_sales_avg": 290_000_000, "store_count": 118, "risk_score": 0.24, "main_industry": "의류"},
    {"area_cd": "3110020", "area_nm": "망원동", "gu_nm": "마포구", "area_type": "지역상권", "lat": 37.5563, "lng": 126.9036, "monthly_sales_avg": 55_000_000, "store_count": 78, "risk_score": 0.31, "main_industry": "카페"},
    {"area_cd": "3250006", "area_nm": "성수동", "gu_nm": "성동구", "area_type": "지역상권", "lat": 37.5443, "lng": 127.0566, "monthly_sales_avg": 110_000_000, "store_count": 92, "risk_score": 0.29, "main_industry": "카페"},
    {"area_cd": "3110022", "area_nm": "연남동", "gu_nm": "마포구", "area_type": "지역상권", "lat": 37.5617, "lng": 126.9269, "monthly_sales_avg": 78_000_000, "store_count": 67, "risk_score": 0.32, "main_industry": "카페"},
    {"area_cd": "3190004", "area_nm": "노량진", "gu_nm": "동작구", "area_type": "발달상권", "lat": 37.5129, "lng": 126.9426, "monthly_sales_avg": 52_000_000, "store_count": 83, "risk_score": 0.56, "main_industry": "음식점"},
    {"area_cd": "3200012", "area_nm": "서울대입구역", "gu_nm": "관악구", "area_type": "발달상권", "lat": 37.4811, "lng": 126.9527, "monthly_sales_avg": 98_000_000, "store_count": 126, "risk_score": 0.47, "main_industry": "음식점"},
    {"area_cd": "3220009", "area_nm": "압구정", "gu_nm": "강남구", "area_type": "발달상권", "lat": 37.5270, "lng": 127.0282, "monthly_sales_avg": 260_000_000, "store_count": 156, "risk_score": 0.21, "main_industry": "의류"},
    {"area_cd": "3110014", "area_nm": "상암·월드컵", "gu_nm": "마포구", "area_type": "지역상권", "lat": 37.5716, "lng": 126.8981, "monthly_sales_avg": 45_000_000, "store_count": 52, "risk_score": 0.39, "main_industry": "편의점"},
    {"area_cd": "3050016", "area_nm": "종로", "gu_nm": "종로구", "area_type": "전통시장", "lat": 37.5725, "lng": 126.9791, "monthly_sales_avg": 72_000_000, "store_count": 289, "risk_score": 0.58, "main_industry": "의류"},
]


@router.get("/areas/map", response_model=list[AreaMapFeature], summary="지도용 상권 집약 데이터")
async def list_areas_map(
    gu_nm: str | None = None,
    area_type: str | None = None,
    risk_max: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    지도 마커 렌더링용. 각 상권의 좌표·매출·위험도를 하나의 응답으로 반환.
    DB에 데이터가 5개 미만이면 개발용 샘플 데이터를 반환한다.
    """
    try:
        count_result = await db.execute(
            select(func.count()).select_from(CommercialArea).where(CommercialArea.geom_lat.isnot(None))
        )
        total = count_result.scalar_one()
    except Exception as exc:
        logger.warning("map sample fallback: %s", exc)
        total = 0

    if total < 5:
        data = _SAMPLE_MAP_AREAS
        if gu_nm:
            data = [a for a in data if gu_nm in a["gu_nm"]]
        if area_type:
            data = [a for a in data if a["area_type"] == area_type]
        if risk_max is not None:
            data = [a for a in data if a["risk_score"] <= risk_max]
        return [AreaMapFeature(**a) for a in data]

    # DB 데이터: CommercialArea LEFT JOIN 최신 SalesData + StoreCount
    from sqlalchemy import case, literal_column
    stmt = (
        select(
            CommercialArea.area_cd,
            CommercialArea.area_nm,
            CommercialArea.gu_nm,
            CommercialArea.area_type,
            CommercialArea.geom_lat.label("lat"),
            CommercialArea.geom_lng.label("lng"),
            func.coalesce(func.max(SalesData.monthly_sales_avg), 0).label("monthly_sales_avg"),
            func.coalesce(func.sum(StoreCount.store_count), 0).label("store_count"),
            func.coalesce(func.avg(StoreCount.close_rate), 0.5).label("risk_score"),
        )
        .outerjoin(SalesData, CommercialArea.area_cd == SalesData.area_cd)
        .outerjoin(StoreCount, CommercialArea.area_cd == StoreCount.area_cd)
        .where(CommercialArea.geom_lat.isnot(None))
    )
    if gu_nm:
        stmt = stmt.where(CommercialArea.gu_nm.ilike(f"%{gu_nm}%"))
    if area_type:
        stmt = stmt.where(CommercialArea.area_type == area_type)
    stmt = stmt.group_by(
        CommercialArea.area_cd,
        CommercialArea.area_nm,
        CommercialArea.gu_nm,
        CommercialArea.area_type,
        CommercialArea.geom_lat,
        CommercialArea.geom_lng,
    ).order_by(CommercialArea.area_nm).limit(500)

    rows = (await db.execute(stmt)).mappings().all()
    features = []
    for r in rows:
        score = float(r["risk_score"])
        if risk_max is not None and score > risk_max:
            continue
        features.append(AreaMapFeature(
            area_cd=r["area_cd"],
            area_nm=r["area_nm"],
            gu_nm=r["gu_nm"],
            area_type=r["area_type"],
            lat=float(r["lat"]),
            lng=float(r["lng"]),
            monthly_sales_avg=int(r["monthly_sales_avg"]),
            store_count=int(r["store_count"]),
            risk_score=min(max(score, 0.0), 1.0),
        ))
    return features


# ── GET /areas/{area_cd} ──────────────────────────────────────────────────────

@router.get("/areas/{area_cd}", response_model=AreaDetailOut, summary="상권 상세 (매출+인구+점포)")
async def get_area(area_cd: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommercialArea).where(CommercialArea.area_cd == area_cd))
    area = result.scalar_one_or_none()
    if area is None:
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    latest_q = (
        await db.execute(
            select(func.max(SalesData.year_quarter)).where(SalesData.area_cd == area_cd)
        )
    ).scalar_one_or_none()

    sales, stores, population = [], [], None
    if latest_q:
        sales = (
            await db.execute(
                select(SalesData).where(
                    SalesData.area_cd == area_cd,
                    SalesData.year_quarter == latest_q,
                ).order_by(SalesData.industry_nm)
            )
        ).scalars().all()

        stores = (
            await db.execute(
                select(StoreCount).where(
                    StoreCount.area_cd == area_cd,
                    StoreCount.year_quarter == latest_q,
                )
            )
        ).scalars().all()

        population = (
            await db.execute(
                select(PopulationData).where(
                    PopulationData.area_cd == area_cd,
                    PopulationData.year_quarter == latest_q,
                )
            )
        ).scalar_one_or_none()

    return AreaDetailOut(
        area=AreaOut.model_validate(area),
        latest_quarter=latest_q,
        sales=[SalesOut.model_validate(s) for s in sales],
        stores=[StoreOut.model_validate(s) for s in stores],
        population=PopulationOut.model_validate(population) if population else None,
    )


# ── GET /areas/{area_cd}/sales ────────────────────────────────────────────────

@router.get("/areas/{area_cd}/sales", response_model=list[SalesOut], summary="매출 시계열")
async def get_area_sales(
    area_cd: str,
    year_quarter: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if not (
        await db.execute(select(CommercialArea).where(CommercialArea.area_cd == area_cd))
    ).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    stmt = select(SalesData).where(SalesData.area_cd == area_cd)
    if year_quarter:
        stmt = stmt.where(SalesData.year_quarter == year_quarter)
    stmt = stmt.order_by(SalesData.year_quarter.desc(), SalesData.industry_nm)

    rows = (await db.execute(stmt)).scalars().all()
    return [SalesOut.model_validate(r) for r in rows]


# ── GET /areas/{area_cd}/risk ─────────────────────────────────────────────────

@router.get("/areas/{area_cd}/risk", response_model=RiskOut, summary="폐업 위험 점수")
async def get_area_risk(area_cd: str, db: AsyncSession = Depends(get_db)):
    if not (
        await db.execute(select(CommercialArea).where(CommercialArea.area_cd == area_cd))
    ).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    latest_q = (
        await db.execute(
            select(func.max(StoreCount.year_quarter)).where(StoreCount.area_cd == area_cd)
        )
    ).scalar_one_or_none()

    if latest_q is None:
        raise HTTPException(status_code=404, detail="수집된 점포 데이터가 없습니다")

    prev_q = _prev_quarter(latest_q)

    async def _agg_stores(yq: str) -> dict:
        rows = (
            await db.execute(
                select(StoreCount).where(
                    StoreCount.area_cd == area_cd,
                    StoreCount.year_quarter == yq,
                )
            )
        ).scalars().all()
        if not rows:
            return {}
        return {
            "store_count": sum(r.store_count or 0 for r in rows),
            "close_rate":  sum(r.close_rate  or 0.0 for r in rows) / len(rows),
        }

    async def _agg_sales(yq: str) -> dict:
        rows = (
            await db.execute(
                select(SalesData).where(
                    SalesData.area_cd == area_cd,
                    SalesData.year_quarter == yq,
                )
            )
        ).scalars().all()
        if not rows:
            return {}
        return {"monthly_sales_avg": sum(r.monthly_sales_avg or 0 for r in rows)}

    cur_stores  = await _agg_stores(latest_q)
    prev_stores = await _agg_stores(prev_q)
    cur_sales   = await _agg_sales(latest_q)
    prev_sales  = await _agg_sales(prev_q)

    store_input = {**cur_stores,  "prev_store_count":       prev_stores.get("store_count", 0)}
    sales_input = {**cur_sales,   "prev_monthly_sales_avg": prev_sales.get("monthly_sales_avg", 0)}
    score = calculate_risk_score(store_input, sales_input)

    return RiskOut(
        area_cd=area_cd,
        year_quarter=latest_q,
        risk_score=score,
        breakdown={
            "close_rate":             cur_stores.get("close_rate", 0.0),
            "store_count":            cur_stores.get("store_count", 0),
            "prev_store_count":       prev_stores.get("store_count", 0),
            "monthly_sales_avg":      cur_sales.get("monthly_sales_avg", 0),
            "prev_monthly_sales_avg": prev_sales.get("monthly_sales_avg", 0),
        },
    )


# ── POST /admin/collect/{area_cd} ─────────────────────────────────────────────

@router.post(
    "/admin/collect/{area_cd}",
    response_model=CollectOut,
    status_code=202,
    summary="특정 상권 즉시 수집 트리거",
)
async def trigger_collect(
    area_cd: str,
    background_tasks: BackgroundTasks,
    year_quarter: str = "2026Q1",
    db: AsyncSession = Depends(get_db),
):
    """
    수집을 백그라운드에서 시작하고 즉시 202를 반환한다.
    완료 여부는 GET /api/v1/areas/{area_cd} 로 확인.
    SEOUL_API_KEY 없는 dev 모드에서도 더미 데이터로 동작.
    """
    await _ensure_area(db, area_cd)
    background_tasks.add_task(_bg_collect, area_cd, year_quarter)

    return CollectOut(
        area_cd=area_cd,
        year_quarter=year_quarter,
        records_saved=-1,
        message="수집 작업이 백그라운드에서 시작됐습니다. GET /api/v1/areas/{area_cd} 로 결과 확인.",
    )
