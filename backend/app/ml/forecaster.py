"""Prophet-based sales forecasting."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from prophet import Prophet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.model_store import ModelStore
from app.models.database import PopulationData, SalesData, StoreCount


REGRESSORS = ["store_count", "population", "close_rate"]
MIN_INTERVAL_HALF_WIDTH_RATIO = 0.12
FORECAST_MODEL_VERSION = "1.2.0"
MIN_YEARLY_SEASONALITY_SAMPLES = 16
MAX_FIRST_FORECAST_CHANGE = 0.18


def _quarter_to_date(year_quarter: str) -> pd.Timestamp:
    year = int(year_quarter[:4])
    quarter = int(year_quarter[-1])
    month = (quarter - 1) * 3 + 1
    return pd.Timestamp(year=year, month=month, day=1)


def _date_to_quarter(value: pd.Timestamp) -> str:
    date = pd.Timestamp(value)
    quarter = ((date.month - 1) // 3) + 1
    return f"{date.year}Q{quarter}"


def _safe_mean(values: list[float]) -> float:
    clean = [value for value in values if not pd.isna(value)]
    return float(np.mean(clean)) if clean else 0.0


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


class SalesForecaster:
    """Train, cache, persist, and run Prophet sales forecasts by area."""

    def __init__(self) -> None:
        self.model_cache: dict[str, Prophet] = {}
        self.model_store = ModelStore()
        self.training_data_cache: dict[str, pd.DataFrame] = {}
        self.trained_at_cache: dict[str, datetime] = {}

    async def prepare_prophet_data(self, area_cd: str, db: AsyncSession) -> pd.DataFrame:
        """Convert DB rows into Prophet input format."""
        sales_rows = (
            await db.execute(select(SalesData).where(SalesData.area_cd == area_cd))
        ).scalars().all()
        store_rows = (
            await db.execute(select(StoreCount).where(StoreCount.area_cd == area_cd))
        ).scalars().all()
        population_rows = (
            await db.execute(select(PopulationData).where(PopulationData.area_cd == area_cd))
        ).scalars().all()

        quarters = sorted(
            {
                row.year_quarter
                for rows in (sales_rows, store_rows, population_rows)
                for row in rows
                if row.year_quarter
            },
            key=_quarter_to_date,
        )

        records: list[dict[str, Any]] = []
        for quarter in quarters:
            sales_q = [row for row in sales_rows if row.year_quarter == quarter]
            stores_q = [row for row in store_rows if row.year_quarter == quarter]
            populations_q = [row for row in population_rows if row.year_quarter == quarter]

            monthly_sales = _safe_mean(
                [float(row.monthly_sales_avg or 0) for row in sales_q]
            )
            store_count = sum(row.store_count or 0 for row in stores_q)
            close_rate = _safe_mean([row.close_rate for row in stores_q if row.close_rate is not None])
            population = float(populations_q[0].total_population or 0) if populations_q else 0.0

            records.append(
                {
                    "ds": _quarter_to_date(quarter),
                    "y": np.log1p(monthly_sales),
                    "store_count": float(store_count),
                    "population": population,
                    "close_rate": close_rate,
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            return pd.DataFrame(columns=["ds", "y", *REGRESSORS])

        df = df.sort_values("ds").reset_index(drop=True)
        for column in REGRESSORS:
            df[column] = pd.to_numeric(df[column], errors="coerce")
            df[column] = df[column].ffill().bfill().fillna(0)
        return df

    def train(self, df: pd.DataFrame, area_cd: str) -> Prophet:
        """Train and persist a Prophet model for one area."""
        if len(df) < 2:
            raise ValueError(f"At least 2 quarters are required to train Prophet for {area_cd}")

        # Quarterly demo/public data is often short. Yearly multiplicative seasonality
        # needs several full cycles; with fewer points it can create a spurious drop
        # on the first forecast quarter.
        use_yearly_seasonality = len(df) >= MIN_YEARLY_SEASONALITY_SAMPLES
        model = Prophet(
            yearly_seasonality=use_yearly_seasonality,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="additive",
            changepoint_prior_scale=0.03,
            interval_width=0.8,
        )
        for regressor in REGRESSORS:
            model.add_regressor(regressor)

        model.fit(df[["ds", "y", *REGRESSORS]])
        self.model_cache[area_cd] = model
        self.training_data_cache[area_cd] = df.copy()
        self.trained_at_cache[area_cd] = datetime.utcnow()
        self.model_store.save(
            model,
            self._model_name(area_cd),
            n_samples=len(df),
            metrics={"yearly_seasonality": use_yearly_seasonality},
            version=FORECAST_MODEL_VERSION,
        )
        return model

    async def predict(self, area_cd: str, periods: int = 4, db: AsyncSession | None = None) -> dict:
        """Forecast sales for the next N quarters."""
        model = await self._get_or_train_model(area_cd, db)
        history = await self._get_history(area_cd, db)
        future = model.make_future_dataframe(periods=periods, freq="QS")
        future = self._attach_future_regressors(future, history)

        forecast = model.predict(future)
        future_forecast = forecast.tail(periods).copy()
        current_sales = float(np.expm1(history["y"].iloc[-1])) if not history.empty else 0.0

        items = []
        for _, row in future_forecast.iterrows():
            predicted = max(0.0, float(np.expm1(row["yhat"])))
            lower = max(0.0, float(np.expm1(row["yhat_lower"])))
            upper = max(0.0, float(np.expm1(row["yhat_upper"])))
            lower, upper = self._calibrate_interval(predicted, lower, upper)
            items.append(
                {
                    "quarter": _date_to_quarter(row["ds"]),
                    "date": pd.Timestamp(row["ds"]).date().isoformat(),
                    "predicted_sales": int(round(predicted)),
                    "lower_bound": int(round(lower)),
                    "upper_bound": int(round(upper)),
                    "trend": self.get_trend_label(current_sales, predicted),
                }
            )
        items = self._calibrate_forecast(history, items)

        return {
            "area_cd": area_cd,
            "forecast": items,
            "trend_summary": self._trend_summary(history),
            "confidence": self._confidence_score_from_items(items),
            "model_trained_at": self.trained_at_cache.get(area_cd, datetime.utcnow()),
        }

    async def batch_predict(self, area_cds: list[str], db: AsyncSession) -> dict:
        """Run forecasts for many areas in batches of 10."""
        results: dict[str, Any] = {}
        for index in range(0, len(area_cds), 10):
            batch = area_cds[index : index + 10]
            forecasts = await asyncio.gather(
                *(self.predict(area_cd, db=db) for area_cd in batch),
                return_exceptions=True,
            )
            for area_cd, forecast in zip(batch, forecasts):
                if isinstance(forecast, Exception):
                    results[area_cd] = {"error": str(forecast)}
                else:
                    results[area_cd] = forecast
        return results

    def get_trend_label(self, current: float, predicted: float) -> str:
        """Return trend label using a 3% threshold."""
        if current <= 0:
            return "보합"
        change = (predicted - current) / current
        if change >= 0.03:
            return "상승"
        if change <= -0.03:
            return "하락"
        return "보합"

    def _calibrate_interval(self, predicted: float, lower: float, upper: float) -> tuple[float, float]:
        """Keep Prophet intervals visible and realistic for short quarterly demo series."""
        if predicted <= 0:
            return lower, upper
        min_half_width = predicted * MIN_INTERVAL_HALF_WIDTH_RATIO
        return max(0.0, min(lower, predicted - min_half_width)), max(upper, predicted + min_half_width)

    async def _get_or_train_model(self, area_cd: str, db: AsyncSession | None) -> Prophet:
        if area_cd in self.model_cache:
            return self.model_cache[area_cd]

        model_name = self._model_name(area_cd)
        if db is None and self.model_store.exists(model_name):
            model = self.model_store.load(model_name)
            self.model_cache[area_cd] = model
            return model

        if db is None:
            raise ValueError("db is required when no stored Prophet model exists")

        df = await self.prepare_prophet_data(area_cd, db)
        if self.model_store.exists(model_name) and self._stored_model_matches(model_name, len(df)):
            model = self.model_store.load(model_name)
            self.model_cache[area_cd] = model
            self.training_data_cache[area_cd] = df.copy()
            return model

        return self.train(df, area_cd)

    async def _get_history(self, area_cd: str, db: AsyncSession | None) -> pd.DataFrame:
        if area_cd in self.training_data_cache:
            return self.training_data_cache[area_cd]
        if db is None:
            raise ValueError("db is required to estimate future regressors")
        history = await self.prepare_prophet_data(area_cd, db)
        self.training_data_cache[area_cd] = history
        return history

    def _attach_future_regressors(self, future: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
        future = future.copy()
        merged = future.merge(history[["ds", *REGRESSORS]], on="ds", how="left")

        recent_store = history["store_count"].tail(3).to_numpy(dtype=float)
        if len(recent_store) >= 2:
            store_step = recent_store[-1] - recent_store[-2]
        else:
            store_step = 0.0

        population_avg = float(history["population"].tail(3).mean()) if not history.empty else 0.0
        close_rate_avg = float(history["close_rate"].tail(2).mean()) if not history.empty else 0.0
        last_store = float(history["store_count"].iloc[-1]) if not history.empty else 0.0

        missing_mask = merged["store_count"].isna()
        future_index = 0
        for idx in merged.index[missing_mask]:
            future_index += 1
            merged.loc[idx, "store_count"] = max(0.0, last_store + store_step * future_index)
            merged.loc[idx, "population"] = population_avg
            merged.loc[idx, "close_rate"] = close_rate_avg

        for column in REGRESSORS:
            merged[column] = pd.to_numeric(merged[column], errors="coerce").ffill().bfill().fillna(0)
        return merged

    def _trend_summary(self, history: pd.DataFrame) -> str:
        if len(history) < 2:
            return "매출 추세를 판단하기에는 데이터가 부족합니다"

        sales = np.expm1(history["y"].tail(4))
        growth = pd.Series(sales).pct_change().dropna()
        recent_growth = growth.tail(3)
        if recent_growth.empty:
            return "최근 매출 변동률을 계산할 수 없습니다"

        avg_growth = float(recent_growth.mean() * 100)
        direction = "증가" if avg_growth > 0.5 else "감소" if avg_growth < -0.5 else "보합"
        return f"최근 3분기 매출이 월평균 {abs(avg_growth):.1f}% {direction} 추세"

    def _confidence_score(self, forecast: pd.DataFrame) -> float:
        if forecast.empty:
            return 0.0
        yhat = np.expm1(forecast["yhat"]).replace(0, np.nan)
        lower = np.expm1(forecast["yhat_lower"])
        upper = np.expm1(forecast["yhat_upper"])
        interval_ratio = ((upper - lower) / yhat).replace([np.inf, -np.inf], np.nan).dropna()
        if interval_ratio.empty:
            return 0.5
        confidence = 1 - min(float(interval_ratio.mean()), 1.0)
        return round(max(0.0, min(confidence, 1.0)), 2)

    def _confidence_score_from_items(self, items: list[dict[str, Any]]) -> float:
        ratios = []
        for item in items:
            predicted = item.get("predicted_sales") or 0
            if predicted <= 0:
                continue
            ratios.append((item.get("upper_bound", 0) - item.get("lower_bound", 0)) / predicted)
        if not ratios:
            return 0.5
        confidence = 1 - min(float(np.mean(ratios)), 1.0)
        return round(max(0.0, min(confidence, 1.0)), 2)

    def _stored_model_matches(self, name: str, n_samples: int) -> bool:
        meta = self.model_store._read_meta(self.model_store._stem(name))
        return (
            meta.get("version") == FORECAST_MODEL_VERSION
            and meta.get("n_samples") == n_samples
        )

    def _recent_growth_rate(self, history: pd.DataFrame) -> float:
        if len(history) < 2:
            return 0.0
        sales = pd.Series(np.expm1(history["y"]).to_numpy(dtype=float))
        growth = sales.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        if growth.empty:
            return 0.0
        return _clamp(float(growth.tail(3).mean()), -0.04, 0.06)

    def _calibrate_forecast(self, history: pd.DataFrame, items: list[dict]) -> list[dict]:
        """Keep short-history forecasts continuous with the latest observed quarter."""
        if history.empty or not items:
            return items

        current_sales = float(np.expm1(history["y"].iloc[-1]))
        first_predicted = float(items[0]["predicted_sales"])
        if current_sales <= 0:
            return items

        first_change = (first_predicted - current_sales) / current_sales
        if abs(first_change) <= MAX_FIRST_FORECAST_CHANGE:
            return items

        growth = self._recent_growth_rate(history)
        calibrated = []
        for index, item in enumerate(items):
            seasonal_adjustment = -0.025 if index == 3 else 0.0
            predicted = max(0.0, current_sales * (1 + growth * (index + 1) + seasonal_adjustment))
            spread = 0.14 if index == 0 else 0.16
            calibrated.append({
                **item,
                "predicted_sales": int(round(predicted)),
                "lower_bound": int(round(predicted * (1 - spread))),
                "upper_bound": int(round(predicted * (1 + spread))),
                "trend": self.get_trend_label(current_sales, predicted),
            })
        return calibrated

    def _model_name(self, area_cd: str) -> str:
        return f"prophet_{area_cd}.pkl"
