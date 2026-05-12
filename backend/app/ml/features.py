"""Feature engineering for forecasting and closure-risk models."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    CommercialArea,
    PopulationData,
    SalesData,
    StoreCount,
    WorkerPopulation,
)


FEATURE_COLUMNS = [
    "monthly_sales_avg",
    "sales_growth_qoq",
    "sales_growth_yoy",
    "sales_volatility",
    "weekday_weekend_ratio",
    "peak_hour_concentration",
    "store_count",
    "store_growth_qoq",
    "open_rate",
    "close_rate",
    "open_close_ratio",
    "competition_index",
    "total_population",
    "population_growth_qoq",
    "young_ratio",
    "worker_ratio",
    "age_diversity_index",
    "sales_per_store",
    "sales_per_population",
    "risk_trend_3q",
    "quarters_since_peak",
]


def _safe_divide(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if denominator in (None, 0) or pd.isna(denominator):
        return None
    if numerator is None or pd.isna(numerator):
        return None
    return float(numerator) / float(denominator)


def _quarter_key(year_quarter: str) -> tuple[int, int]:
    try:
        return int(year_quarter[:4]), int(year_quarter[-1])
    except (TypeError, ValueError):
        return 0, 0


def _sum_values(values: Iterable[int | float | None]) -> float:
    return float(sum(value or 0 for value in values))


class FeatureEngineer:
    """Build ML-ready features from commercial-area database tables."""

    async def get_area_features(self, area_cd: str, db: AsyncSession) -> pd.DataFrame:
        """Extract quarterly features for one commercial area."""
        sales_rows = (
            await db.execute(select(SalesData).where(SalesData.area_cd == area_cd))
        ).scalars().all()
        store_rows = (
            await db.execute(select(StoreCount).where(StoreCount.area_cd == area_cd))
        ).scalars().all()
        population_rows = (
            await db.execute(select(PopulationData).where(PopulationData.area_cd == area_cd))
        ).scalars().all()
        worker_rows = (
            await db.execute(select(WorkerPopulation).where(WorkerPopulation.area_cd == area_cd))
        ).scalars().all()

        quarters = sorted(
            {
                row.year_quarter
                for rows in (sales_rows, store_rows, population_rows, worker_rows)
                for row in rows
                if row.year_quarter
            },
            key=_quarter_key,
        )

        records: list[dict] = []
        for quarter in quarters:
            sales_q = [row for row in sales_rows if row.year_quarter == quarter]
            stores_q = [row for row in store_rows if row.year_quarter == quarter]
            population_q = [row for row in population_rows if row.year_quarter == quarter]
            workers_q = [row for row in worker_rows if row.year_quarter == quarter]

            monthly_sales = _sum_values(row.monthly_sales_avg for row in sales_q)
            weekday_sales = _sum_values(row.weekday_sales for row in sales_q)
            weekend_sales = _sum_values(row.weekend_sales for row in sales_q)

            time_slots: dict[str, float] = {}
            for row in sales_q:
                for slot, amount in (row.time_slot_sales or {}).items():
                    time_slots[str(slot)] = time_slots.get(str(slot), 0.0) + float(amount or 0)

            total_time_sales = sum(time_slots.values())
            peak_hour_concentration = (
                max(time_slots.values()) / total_time_sales if total_time_sales else None
            )

            store_count = _sum_values(row.store_count for row in stores_q)
            open_rates = [row.open_rate for row in stores_q if row.open_rate is not None]
            close_rates = [row.close_rate for row in stores_q if row.close_rate is not None]
            open_rate = float(np.mean(open_rates)) if open_rates else None
            close_rate = float(np.mean(close_rates)) if close_rates else None

            population = population_q[0] if population_q else None
            worker = workers_q[0] if workers_q else None
            total_population = float(population.total_population or 0) if population else 0.0
            total_workers = float(worker.total_workers or 0) if worker else 0.0

            age_counts = []
            if population:
                age_counts = [
                    population.age_10s or 0,
                    population.age_20s or 0,
                    population.age_30s or 0,
                    population.age_40s or 0,
                    population.age_50s or 0,
                    population.age_60s or 0,
                ]
            age_total = sum(age_counts)
            age_shares = [count / age_total for count in age_counts if age_total]
            age_diversity_index = 1 - sum(share**2 for share in age_shares) if age_shares else None

            records.append(
                {
                    "area_cd": area_cd,
                    "year_quarter": quarter,
                    "monthly_sales_avg": monthly_sales,
                    "weekday_weekend_ratio": _safe_divide(weekday_sales, weekend_sales),
                    "peak_hour_concentration": peak_hour_concentration,
                    "store_count": store_count,
                    "open_rate": open_rate,
                    "close_rate": close_rate,
                    "open_close_ratio": _safe_divide(open_rate, close_rate),
                    "total_population": total_population,
                    "young_ratio": _safe_divide(
                        (population.age_20s or 0) + (population.age_30s or 0) if population else 0,
                        total_population,
                    ),
                    "worker_ratio": _safe_divide(total_workers, total_population),
                    "age_diversity_index": age_diversity_index,
                    "sales_per_store": _safe_divide(monthly_sales, store_count),
                    "sales_per_population": _safe_divide(monthly_sales, total_population),
                }
            )

        if not records:
            return pd.DataFrame(columns=["area_cd", "year_quarter", *FEATURE_COLUMNS])

        frame = pd.DataFrame(records).sort_values("year_quarter").reset_index(drop=True)
        sales = frame["monthly_sales_avg"]
        stores = frame["store_count"]
        population = frame["total_population"]

        frame["sales_growth_qoq"] = sales.pct_change().replace([np.inf, -np.inf], np.nan).round(4)
        frame["sales_growth_yoy"] = sales.pct_change(periods=4).replace([np.inf, -np.inf], np.nan).round(4)
        frame["sales_volatility"] = sales.expanding(min_periods=2).std() / sales.expanding().mean()
        frame["store_growth_qoq"] = stores.pct_change().replace([np.inf, -np.inf], np.nan).round(4)
        frame["population_growth_qoq"] = population.pct_change().replace([np.inf, -np.inf], np.nan).round(4)

        sales_decline = (-frame["sales_growth_qoq"]).clip(lower=0).fillna(0)
        store_growth = frame["store_growth_qoq"].clip(lower=0).fillna(0)
        frame["competition_index"] = (store_growth * 0.5 + sales_decline * 0.5).round(4)

        frame["risk_trend_3q"] = (frame["close_rate"] - frame["close_rate"].shift(2)).round(4)

        peak_idx = int(sales.idxmax()) if not sales.empty else 0
        frame["quarters_since_peak"] = [max(0, idx - peak_idx) for idx in range(len(frame))]

        return frame[["area_cd", "year_quarter", *FEATURE_COLUMNS]]

    def calculate_growth_rate(self, series: pd.Series) -> float | None:
        """Calculate the latest growth rate against the previous value."""
        clean = pd.to_numeric(series, errors="coerce").dropna()
        if len(clean) < 2:
            return None
        previous = clean.iloc[-2]
        current = clean.iloc[-1]
        if previous == 0:
            return None
        return round(float((current - previous) / previous), 4)

    def calculate_volatility(self, series: pd.Series) -> float | None:
        """Calculate volatility as standard deviation divided by mean."""
        clean = pd.to_numeric(series, errors="coerce").dropna()
        if clean.empty or clean.mean() == 0:
            return None
        return round(float(clean.std() / clean.mean()), 4)

    async def get_training_dataset(self, db: AsyncSession) -> tuple[pd.DataFrame, pd.Series]:
        """Build the full training dataset from all commercial areas."""
        area_codes = (
            await db.execute(select(CommercialArea.area_cd).order_by(CommercialArea.area_cd))
        ).scalars().all()

        frames = []
        for area_cd in area_codes:
            features = await self.get_area_features(area_cd, db)
            if not features.empty:
                frames.append(features)

        if not frames:
            return pd.DataFrame(columns=FEATURE_COLUMNS), pd.Series(dtype="int64", name="label")

        dataset = pd.concat(frames, ignore_index=True)
        labels = (pd.to_numeric(dataset["close_rate"], errors="coerce").fillna(0) > 15).astype(int)
        features = dataset[FEATURE_COLUMNS].copy()
        features = features.replace([np.inf, -np.inf], np.nan)
        features = features.fillna(features.median(numeric_only=True)).fillna(0)
        labels.name = "label"
        return features, labels


def build_sales_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with common sales trend features."""
    data = frame.copy()
    if "monthly_sales_avg" in data:
        data["sales_lag_1"] = data["monthly_sales_avg"].shift(1)
        data["sales_pct_change"] = data["monthly_sales_avg"].pct_change()
    return data


def build_risk_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize baseline columns used by the risk scorer."""
    data = frame.copy()
    for column in FEATURE_COLUMNS:
        if column in data:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    return data.replace([np.inf, -np.inf], np.nan).fillna(0)
