import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.data.collectors.seoul_api import SeoulOpenAPI, map_area
from app.models.database import CommercialArea

logger = logging.getLogger(__name__)

_BATCH_SIZE = 10
_CURRENT_QUARTER = "2025Q4"


async def _save_area_list(areas: list[dict]) -> int:
    """Upsert Seoul commercial-area master rows into commercial_areas."""
    values = [
        {
            "area_cd": area.area_cd,
            "area_nm": area.area_nm,
            "gu_nm": area.gu_nm,
            "area_type": area.area_type,
            "geom_lng": area.geom_lng,
            "geom_lat": area.geom_lat,
        }
        for area in (map_area(row) for row in areas)
    ]
    if not values:
        return 0

    stmt = insert(CommercialArea).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[CommercialArea.area_cd],
        set_={
            "area_nm": stmt.excluded.area_nm,
            "gu_nm": stmt.excluded.gu_nm,
            "area_type": stmt.excluded.area_type,
            "geom_lng": stmt.excluded.geom_lng,
            "geom_lat": stmt.excluded.geom_lat,
        },
    )

    async with AsyncSessionLocal() as session:
        await session.execute(stmt)
        await session.commit()
    return len(values)


async def _collect_one(api: SeoulOpenAPI, area_cd: str) -> int:
    async with AsyncSessionLocal() as session:
        return await api.fetch_and_save(session, area_cd, _CURRENT_QUARTER)


async def _run_batch(api: SeoulOpenAPI, area_codes: list[str]) -> int:
    results = await asyncio.gather(
        *[_collect_one(api, area_cd) for area_cd in area_codes],
        return_exceptions=True,
    )
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Collection failed for one area: %s", result)
    return sum(1 for result in results if not isinstance(result, Exception))


async def fetch_all_areas() -> None:
    """Collect all commercial areas already present in the local DB."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(CommercialArea.area_cd))
        area_codes = [row[0] for row in result.all()]

    if not area_codes:
        logger.warning("fetch_all_areas: no commercial areas; run initial_seed first")
        return

    total = len(area_codes)
    logger.info("fetch_all_areas started: total=%d", total)
    completed = 0

    async with SeoulOpenAPI() as api:
        for index in range(0, total, _BATCH_SIZE):
            batch = area_codes[index : index + _BATCH_SIZE]
            completed += await _run_batch(api, batch)
            done = index + len(batch)
            logger.info("Progress: %d/%d (%.1f%%)", done, total, done / total * 100)

    logger.info("fetch_all_areas complete: %d/%d succeeded", completed, total)


async def fetch_top50_areas() -> None:
    """Refresh the first 50 local DB areas on a shorter interval."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(CommercialArea.area_cd).order_by(CommercialArea.area_cd).limit(50)
        )
        area_codes = [row[0] for row in result.all()]

    if not area_codes:
        logger.warning("fetch_top50_areas: no commercial areas; run initial_seed first")
        return

    logger.info("fetch_top50_areas started")
    completed = 0

    async with SeoulOpenAPI() as api:
        for index in range(0, len(area_codes), _BATCH_SIZE):
            completed += await _run_batch(api, area_codes[index : index + _BATCH_SIZE])

    logger.info("fetch_top50_areas complete: %d areas updated", completed)


async def initial_seed() -> None:
    """Seed commercial-area master data and a priority batch on first boot."""
    async with AsyncSessionLocal() as session:
        count = (
            await session.execute(select(func.count()).select_from(CommercialArea))
        ).scalar_one()

    if count > 0:
        logger.info("initial_seed skipped: %d commercial areas already exist", count)
        return

    logger.info("initial_seed started")
    async with SeoulOpenAPI() as api:
        areas = await api.get_all_commercial_areas()
        seeded = await _save_area_list(areas)
        logger.info("Commercial-area master seed complete: %d rows", seeded)

        priority_codes = [row["TRDAR_CD"] for row in areas[:50]]
        completed = 0
        for index in range(0, len(priority_codes), _BATCH_SIZE):
            completed += await _run_batch(api, priority_codes[index : index + _BATCH_SIZE])

    logger.info("initial_seed complete: %d priority areas collected", completed)


def create_scheduler() -> AsyncIOScheduler:
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
