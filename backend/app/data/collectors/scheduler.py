import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.data.collectors.seoul_api import SeoulOpenAPI
from app.models.database import CommercialArea

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_CURRENT_QUARTER = "2024Q3"

# 서울 주요 상권 코드 — 실제 운영 시 API로 확인 후 갱신
_TOP_50_AREA_CODES: list[str] = [
    "1000001", "1000002", "1000003", "1000004", "1000005",
    "1000006", "1000007", "1000008", "1000009", "1000010",
    "2000001", "2000002", "2000003", "2000004", "2000005",
    "2000006", "2000007", "2000008", "2000009", "2000010",
    "3000001", "3000002", "3000003", "3000004", "3000005",
    "3000006", "3000007", "3000008", "3000009", "3000010",
    "4000001", "4000002", "4000003", "4000004", "4000005",
    "4000006", "4000007", "4000008", "4000009", "4000010",
    "5000001", "5000002", "5000003", "5000004", "5000005",
    "5000006", "5000007", "5000008", "5000009", "5000010",
]


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

async def _save_area_list(areas: list[dict]) -> int:
    """get_all_commercial_areas() 응답을 commercial_areas 테이블에 upsert."""
    objects = [
        CommercialArea(
            area_cd=r["TRDAR_CD"],
            area_nm=r.get("TRDAR_CD_NM", ""),
            gu_nm=r.get("SIGNGU_CD_NM", ""),
            area_type=r.get("TRDAR_SE_CD_NM", ""),
            geom_lng=float(r["X_COORDINATE"]) if r.get("X_COORDINATE") else None,
            geom_lat=float(r["Y_COORDINATE"]) if r.get("Y_COORDINATE") else None,
        )
        for r in areas
    ]
    async with AsyncSessionLocal() as session:
        session.add_all(objects)
        await session.commit()
    return len(objects)


async def _collect_one(api: SeoulOpenAPI, area_cd: str) -> int:
    """단일 상권 수집 — 전용 세션 사용."""
    async with AsyncSessionLocal() as session:
        return await api.fetch_and_save(session, area_cd, _CURRENT_QUARTER)


async def _run_batch(api: SeoulOpenAPI, area_codes: list[str]) -> int:
    """배치 단위 병렬 수집 — 항목별 독립 세션으로 concurrent commit 충돌 방지."""
    results = await asyncio.gather(
        *[_collect_one(api, cd) for cd in area_codes],
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            logger.warning("배치 항목 실패: %s", r)
    return sum(1 for r in results if not isinstance(r, Exception))


# ── 수집 작업 ─────────────────────────────────────────────────────────────────

async def fetch_all_areas() -> None:
    """전체 서울 상권 순회 수집 — 매일 새벽 3시."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CommercialArea.area_cd))
        area_codes = [row[0] for row in result.all()]

    if not area_codes:
        logger.warning("fetch_all_areas: DB에 상권 없음 — initial_seed 먼저 실행 필요")
        return

    total = len(area_codes)
    logger.info("fetch_all_areas 시작 — 총 %d개 상권", total)
    completed = 0

    async with SeoulOpenAPI() as api:
        for i in range(0, total, _BATCH_SIZE):
            batch = area_codes[i : i + _BATCH_SIZE]
            completed += await _run_batch(api, batch)
            done = i + len(batch)
            logger.info("진행률: %d/%d (%.1f%%)", done, total, done / total * 100)

    logger.info("fetch_all_areas 완료 — %d/%d 성공", completed, total)


async def fetch_top50_areas() -> None:
    """인기 상권 TOP 50 우선 업데이트 — 매 6시간."""
    logger.info("fetch_top50_areas 시작")
    completed = 0

    async with SeoulOpenAPI() as api:
        for i in range(0, len(_TOP_50_AREA_CODES), _BATCH_SIZE):
            batch = _TOP_50_AREA_CODES[i : i + _BATCH_SIZE]
            completed += await _run_batch(api, batch)

    logger.info("fetch_top50_areas 완료 — %d개 상권 업데이트", completed)


async def initial_seed() -> None:
    """앱 최초 실행 시 기초 데이터 적재 — commercial_areas 0건일 때만."""
    async with AsyncSessionLocal() as session:
        count = (
            await session.execute(select(func.count()).select_from(CommercialArea))
        ).scalar_one()

    if count > 0:
        logger.info("initial_seed 스킵 — 이미 %d개 상권 존재", count)
        return

    logger.info("initial_seed 시작")
    api = SeoulOpenAPI()

    # 1) 전체 상권 목록 → commercial_areas 적재
    areas = await api.get_all_commercial_areas()
    seeded = await _save_area_list(areas)
    logger.info("상권 목록 적재 완료: %d건", seeded)

    # 2) dev mode(더미 2건)면 전체, 아니면 TOP 50만 우선 수집
    priority_codes = (
        [a["TRDAR_CD"] for a in areas]
        if len(areas) <= len(_TOP_50_AREA_CODES)
        else _TOP_50_AREA_CODES
    )

    completed = 0
    async with api:
        for i in range(0, len(priority_codes), _BATCH_SIZE):
            batch = priority_codes[i : i + _BATCH_SIZE]
            completed += await _run_batch(api, batch)

    logger.info("initial_seed 완료 — %d개 상권 데이터 수집", completed)


# ── FastAPI 연동 ──────────────────────────────────────────────────────────────

def create_scheduler() -> AsyncIOScheduler:
    """
    설정된 AsyncIOScheduler를 반환한다 (시작은 하지 않음).
    main.py의 lifespan context manager에서 scheduler.start() / shutdown() 호출.
    """
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    scheduler.add_job(
        fetch_all_areas,
        trigger=CronTrigger(hour=3, minute=0, timezone="Asia/Seoul"),
        id="fetch_all_areas",
        replace_existing=True,
    )
    scheduler.add_job(
        fetch_top50_areas,
        trigger=IntervalTrigger(hours=6),
        id="fetch_top50_areas",
        replace_existing=True,
    )
    return scheduler
