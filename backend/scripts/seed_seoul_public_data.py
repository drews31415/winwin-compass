"""Seed Seoul commercial-area public data into the local database.

Examples:
    python scripts/seed_seoul_public_data.py --areas-only
    python scripts/seed_seoul_public_data.py --quarter auto
    python scripts/seed_seoul_public_data.py --quarter 2025Q4 --services sales stores
    python scripts/seed_seoul_public_data.py --quarter 2025Q4 --recent-quarters 8 --services sales
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal
from app.data.collectors.seoul_api import (
    SERVICE_AREAS,
    SERVICE_FLOATING_POPULATION,
    SERVICE_SALES,
    SERVICE_STORES,
    SERVICE_WORKER_POPULATION,
    SeoulOpenAPI,
    _map_population,
    _map_sales,
    _map_store,
    _map_worker,
    map_area,
    quarter_to_seoul_code,
)
from app.models.database import (
    CommercialArea,
    PopulationData,
    SalesData,
    StoreCount,
    WorkerPopulation,
)

logger = logging.getLogger("seed_seoul_public_data")

Mapper = Callable[[dict], object]


def recent_quarters(latest_quarter: str, count: int) -> list[str]:
    year = int(latest_quarter[:4])
    quarter = int(latest_quarter[-1])
    values: list[str] = []
    for _ in range(count):
        values.append(f"{year}Q{quarter}")
        quarter -= 1
        if quarter == 0:
            year -= 1
            quarter = 4
    return list(reversed(values))


async def upsert_areas(api: SeoulOpenAPI) -> int:
    rows = await api.get_all_commercial_areas()
    values = [
        {
            "area_cd": area.area_cd,
            "area_nm": area.area_nm,
            "gu_nm": area.gu_nm,
            "area_type": area.area_type,
            "geom_lng": area.geom_lng,
            "geom_lat": area.geom_lat,
        }
        for area in (map_area(row) for row in rows)
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


async def replace_quarter_rows(
    api: SeoulOpenAPI,
    *,
    service: str,
    model: type,
    mapper: Mapper,
    quarter: str,
    limit_pages: int | None,
    early_stop_after_target: bool = False,
) -> int:
    target = quarter_to_seoul_code(quarter)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(model).where(model.year_quarter == quarter))
        await session.commit()

    saved = 0
    page_count = 0
    seen_target_quarter = False
    async for page_rows, total in api.iter_pages(service):
        page_count += 1
        objects = [
            mapper(row)
            for row in page_rows
            if str(row.get("STDR_YYQU_CD") or "") == target
        ]
        if objects:
            seen_target_quarter = True

        if objects:
            async with AsyncSessionLocal() as session:
                session.add_all(objects)
                await session.commit()
            saved += len(objects)

        if page_count == 1 or page_count % 25 == 0:
            logger.info(
                "%s: page=%d total_api_rows=%d saved=%d",
                service,
                page_count,
                total,
                saved,
            )

        if limit_pages is not None and page_count >= limit_pages:
            break

        if early_stop_after_target and seen_target_quarter and not objects:
            logger.info(
                "%s: stopped after latest quarter block ended at page=%d",
                service,
                page_count,
            )
            break

    logger.info("%s complete: saved=%d quarter=%s", service, saved, quarter)
    return saved


async def replace_quarters_rows(
    api: SeoulOpenAPI,
    *,
    service: str,
    model: type,
    mapper: Mapper,
    quarters: list[str],
    limit_pages: int | None,
    early_stop_after_target: bool = False,
) -> int:
    targets = {quarter_to_seoul_code(quarter) for quarter in quarters}
    async with AsyncSessionLocal() as session:
        await session.execute(delete(model).where(model.year_quarter.in_(quarters)))
        await session.commit()

    saved = 0
    page_count = 0
    seen_target_quarter = False
    async for page_rows, total in api.iter_pages(service):
        page_count += 1
        objects = [
            mapper(row)
            for row in page_rows
            if str(row.get("STDR_YYQU_CD") or "") in targets
        ]
        if objects:
            seen_target_quarter = True

        if objects:
            async with AsyncSessionLocal() as session:
                session.add_all(objects)
                await session.commit()
            saved += len(objects)

        if page_count == 1 or page_count % 25 == 0:
            logger.info(
                "%s: page=%d total_api_rows=%d saved=%d quarters=%s",
                service,
                page_count,
                total,
                saved,
                ",".join(quarters),
            )

        if limit_pages is not None and page_count >= limit_pages:
            break

        if early_stop_after_target and seen_target_quarter and not objects:
            logger.info(
                "%s: stopped after target quarter block ended at page=%d",
                service,
                page_count,
            )
            break

    logger.info("%s complete: saved=%d quarters=%s", service, saved, ",".join(quarters))
    return saved


async def print_counts() -> None:
    async with AsyncSessionLocal() as session:
        for model in (
            CommercialArea,
            SalesData,
            StoreCount,
            PopulationData,
            WorkerPopulation,
        ):
            count = (
                await session.execute(select(func.count()).select_from(model))
            ).scalar_one()
            logger.info("%s rows=%d", model.__tablename__, count)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quarter", default="auto")
    parser.add_argument("--areas-only", action="store_true")
    parser.add_argument(
        "--services",
        nargs="+",
        choices=["sales", "stores", "population", "workers"],
        default=["sales", "stores", "population", "workers"],
    )
    parser.add_argument(
        "--limit-pages",
        type=int,
        default=None,
        help="Debug option. Limits pages per service; omit for full collection.",
    )
    parser.add_argument(
        "--recent-quarters",
        type=int,
        default=1,
        help="Collect this many recent quarters ending at --quarter.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    async with SeoulOpenAPI() as api:
        area_count = await upsert_areas(api)
        logger.info("%s upserted rows=%d", SERVICE_AREAS, area_count)

        if args.areas_only:
            await print_counts()
            return

        quarter = args.quarter
        if quarter == "auto":
            quarter = await api.get_latest_quarter()
        quarters = recent_quarters(quarter, args.recent_quarters)
        logger.info("Collecting Seoul public data quarters=%s", ",".join(quarters))

        service_specs = {
            "sales": (SERVICE_SALES, SalesData, _map_sales, False),
            "stores": (SERVICE_STORES, StoreCount, _map_store, True),
            "population": (
                SERVICE_FLOATING_POPULATION,
                PopulationData,
                _map_population,
                False,
            ),
            "workers": (
                SERVICE_WORKER_POPULATION,
                WorkerPopulation,
                _map_worker,
                False,
            ),
        }

        for name in args.services:
            service, model, mapper, early_stop_after_target = service_specs[name]
            if len(quarters) == 1:
                await replace_quarter_rows(
                    api,
                    service=service,
                    model=model,
                    mapper=mapper,
                    quarter=quarters[0],
                    limit_pages=args.limit_pages,
                    early_stop_after_target=early_stop_after_target,
                )
            else:
                await replace_quarters_rows(
                    api,
                    service=service,
                    model=model,
                    mapper=mapper,
                    quarters=quarters,
                    limit_pages=args.limit_pages,
                    early_stop_after_target=False,
                )

    await print_counts()


if __name__ == "__main__":
    asyncio.run(main())
