"""Seed deterministic demo data for competition presentations.

Run from backend/:
    python scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete

from app.ai.rag_engine import DEMO_POLICIES
from app.core.database import AsyncSessionLocal
from app.models.database import (
    CommercialArea,
    PolicyProgram,
    PopulationData,
    SalesData,
    StoreCount,
    WorkerPopulation,
    init_db,
)


QUARTERS = [
    "2023Q3",
    "2023Q4",
    "2024Q1",
    "2024Q2",
    "2024Q3",
    "2024Q4",
    "2025Q1",
    "2025Q2",
    "2025Q3",
    "2025Q4",
    "2026Q1",
]


AREAS = [
    {
        "area_cd": "3110016",
        "area_nm": "종로3가",
        "gu_nm": "종로구",
        "area_type": "골목상권",
        "geom_lat": 37.5704,
        "geom_lng": 126.9911,
        "sales": [180, 188, 196, 205, 212, 225, 236, 242, 250, 244, 238],
        "stores": [130, 132, 134, 136, 139, 142, 146, 150, 153, 155, 154],
        "open_rates": [10.2, 10.7, 11.1, 11.5, 12.0, 12.4, 12.8, 13.1, 12.7, 12.0, 11.6],
        "close_rates": [8.0, 8.4, 8.9, 9.5, 10.2, 10.8, 11.6, 12.5, 13.4, 14.0, 13.2],
        "population_total": 86_000,
        "age_ratio": {"10s": 0.06, "20s": 0.35, "30s": 0.28, "40s": 0.20, "50s": 0.08, "60s": 0.03},
        "workers": 45_000,
    },
    {
        "area_cd": "2640014",
        "area_nm": "홍대입구",
        "gu_nm": "마포구",
        "area_type": "발달상권",
        "geom_lat": 37.5563,
        "geom_lng": 126.9236,
        "sales": [320, 333, 348, 366, 381, 397, 410, 405, 392, 382, 374],
        "stores": [210, 218, 226, 235, 244, 253, 263, 274, 286, 297, 304],
        "open_rates": [14.0, 14.7, 15.3, 16.0, 16.8, 17.5, 18.1, 18.8, 19.0, 18.4, 17.7],
        "close_rates": [11.0, 11.6, 12.1, 12.8, 13.5, 14.4, 15.2, 16.1, 17.0, 18.0, 17.4],
        "population_total": 128_000,
        "age_ratio": {"10s": 0.10, "20s": 0.52, "30s": 0.23, "40s": 0.08, "50s": 0.05, "60s": 0.02},
        "workers": 52_000,
    },
    {
        "area_cd": "3920008",
        "area_nm": "불광동",
        "gu_nm": "은평구",
        "area_type": "골목상권",
        "geom_lat": 37.6105,
        "geom_lng": 126.9292,
        "sales": [80, 84, 86, 89, 93, 97, 101, 106, 110, 116, 120],
        "stores": [78, 79, 80, 82, 83, 84, 85, 86, 88, 89, 90],
        "open_rates": [7.2, 7.5, 7.8, 8.0, 8.3, 8.6, 8.9, 9.1, 9.4, 9.6, 9.8],
        "close_rates": [6.0, 6.3, 6.7, 7.0, 7.2, 7.5, 7.9, 8.2, 8.6, 9.0, 9.4],
        "population_total": 64_000,
        "age_ratio": {"10s": 0.08, "20s": 0.14, "30s": 0.18, "40s": 0.22, "50s": 0.23, "60s": 0.15},
        "workers": 21_000,
    },
]


def quarter_index(quarter: str) -> int:
    year = int(quarter[:4])
    q = int(quarter[-1])
    return (year - 2023) * 4 + q - 1


def clear_demo_forecast_models() -> None:
    """Remove cached Prophet models so forecasts are trained from fresh 2026 demo data."""
    model_dir = ROOT / "models"
    for area in AREAS:
        stem = f"prophet_{area['area_cd']}"
        for suffix in (".pkl", "_meta.json"):
            path = model_dir / f"{stem}{suffix}"
            if path.exists():
                path.unlink()


def time_slot_sales(monthly_sales: int) -> dict[str, int]:
    slots = {
        "06": 0.04,
        "09": 0.08,
        "12": 0.22,
        "14": 0.17,
        "18": 0.20,
        "20": 0.18,
        "21": 0.11,
    }
    return {slot: int(monthly_sales * ratio) for slot, ratio in slots.items()}


def population_counts(total: int, ratios: dict[str, float], trend: float) -> dict[str, int]:
    adjusted_total = int(total * trend)
    return {
        "age_10s": int(adjusted_total * ratios["10s"]),
        "age_20s": int(adjusted_total * ratios["20s"]),
        "age_30s": int(adjusted_total * ratios["30s"]),
        "age_40s": int(adjusted_total * ratios["40s"]),
        "age_50s": int(adjusted_total * ratios["50s"]),
        "age_60s": int(adjusted_total * ratios["60s"]),
        "total_population": adjusted_total,
    }


async def seed_area(session, area: dict) -> None:
    area_cd = area["area_cd"]
    for model in (SalesData, StoreCount, PopulationData, WorkerPopulation):
        await session.execute(delete(model).where(model.area_cd == area_cd))
    await session.execute(delete(CommercialArea).where(CommercialArea.area_cd == area_cd))

    session.add(
        CommercialArea(
            area_cd=area_cd,
            area_nm=area["area_nm"],
            gu_nm=area["gu_nm"],
            area_type=area["area_type"],
            geom_lat=area["geom_lat"],
            geom_lng=area["geom_lng"],
        )
    )
    await session.flush()

    for idx, quarter in enumerate(QUARTERS):
        sales_amount = area["sales"][idx] * 1_000_000
        weekday_sales = int(sales_amount * 0.62)
        weekend_sales = int(sales_amount * 0.38)
        session.add(
            SalesData(
                area_cd=area_cd,
                industry_cd="CS100010",
                industry_nm="커피-음료",
                year_quarter=quarter,
                monthly_sales_avg=sales_amount,
                daily_sales_avg=int(sales_amount / 30),
                weekday_sales=weekday_sales,
                weekend_sales=weekend_sales,
                time_slot_sales=time_slot_sales(sales_amount),
            )
        )
        session.add(
            StoreCount(
                area_cd=area_cd,
                year_quarter=quarter,
                industry_cd="CS100010",
                store_count=area["stores"][idx],
                open_rate=area["open_rates"][idx],
                close_rate=area["close_rates"][idx],
            )
        )
        trend = 1 + (idx - 5) * 0.008
        counts = population_counts(area["population_total"], area["age_ratio"], trend)
        session.add(
            PopulationData(
                area_cd=area_cd,
                year_quarter=quarter,
                male_ratio=0.48,
                female_ratio=0.52,
                **counts,
            )
        )
        workers = int(area["workers"] * (1 + (idx - 5) * 0.006))
        session.add(
            WorkerPopulation(
                area_cd=area_cd,
                year_quarter=quarter,
                total_workers=workers,
                age_20s=int(workers * 0.24),
                age_30s=int(workers * 0.34),
                age_40s=int(workers * 0.26),
                age_50s=int(workers * 0.16),
            )
        )


async def seed_policies(session) -> None:
    await session.execute(delete(PolicyProgram))
    for policy in DEMO_POLICIES:
        session.add(
            PolicyProgram(
                program_nm=policy["program_nm"],
                category=policy["category"],
                target=f"{policy['target']} / {policy['description']}",
                budget_min=policy["budget_min"],
                budget_max=policy["budget_max"],
                apply_start=date.fromisoformat(policy["apply_start"]),
                apply_end=date.fromisoformat(policy["apply_end"]),
                source_url=policy["source_url"],
            )
        )


async def main() -> None:
    await init_db()
    clear_demo_forecast_models()
    async with AsyncSessionLocal() as session:
        for area in AREAS:
            await seed_area(session, area)
        await seed_policies(session)
        await session.commit()
    print("Demo data seeded: 3 areas, 2023Q3~2026Q1, 5 policies")


if __name__ == "__main__":
    asyncio.run(main())
