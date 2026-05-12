"""Training pipeline orchestration for ML models."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.ml.features import FEATURE_COLUMNS, FeatureEngineer
from app.ml.forecaster import SalesForecaster
from app.ml.model_store import ModelStore
from app.ml.risk_scorer import RiskScorer

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Coordinates feature extraction, training, and model persistence."""

    def __init__(self) -> None:
        self.feature_engineer = FeatureEngineer()
        self.risk_scorer = RiskScorer()
        self.sales_forecaster = SalesForecaster()
        self.model_store = ModelStore()

    async def train_risk_model(self, db) -> dict:
        """Run the full risk-model training pipeline."""
        X, y = await self.feature_engineer.get_training_dataset(db)
        used_sample_data = False

        if len(X) < 30 or y.nunique() < 2:
            logger.warning(
                "Insufficient risk training data (%d rows, %d classes); using synthetic samples",
                len(X),
                y.nunique(),
            )
            X, y = self.generate_sample_training_data(n_areas=100)
            used_sample_data = True

        metrics = self.risk_scorer.train(X, y)
        logger.info("Risk model trained: %s", metrics)
        return {
            "model": "risk_scorer",
            "status": "trained",
            "n_samples": int(len(X)),
            "used_sample_data": used_sample_data,
            "metrics": metrics,
        }

    async def train_forecaster(self, area_cd: str, db) -> dict:
        """Train a Prophet sales forecaster for one area."""
        df = await self.sales_forecaster.prepare_prophet_data(area_cd, db)
        used_sample_data = False

        if len(df) < 6:
            logger.warning("Insufficient forecast data for %s (%d rows); using sample series", area_cd, len(df))
            df = self._generate_sample_forecast_data()
            used_sample_data = True

        self.sales_forecaster.train(df, area_cd)
        return {
            "model": f"prophet_{area_cd}",
            "area_cd": area_cd,
            "status": "trained",
            "n_samples": int(len(df)),
            "used_sample_data": used_sample_data,
        }

    def generate_sample_training_data(self, n_areas: int = 100) -> tuple[pd.DataFrame, pd.Series]:
        """Generate reproducible synthetic training data for sparse DB states."""
        np.random.seed(42)

        monthly_sales = np.clip(np.random.normal(220_000_000, 90_000_000, n_areas), 50_000_000, 500_000_000)
        close_rate = np.clip(np.random.exponential(scale=6, size=n_areas) + 3, 3, 25)
        store_count = np.random.uniform(20, 500, n_areas)
        sales_growth_yoy = np.random.normal(-0.03, 0.14, n_areas)
        sales_growth_qoq = sales_growth_yoy / 4 + np.random.normal(0, 0.03, n_areas)
        store_growth_qoq = np.random.normal(0.05, 0.12, n_areas)
        population_growth_qoq = np.random.normal(0.0, 0.04, n_areas)
        total_population = np.random.uniform(5_000, 150_000, n_areas)
        worker_ratio = np.random.uniform(0.1, 1.8, n_areas)
        young_ratio = np.random.uniform(0.15, 0.55, n_areas)
        open_rate = np.random.uniform(2, 20, n_areas)

        data = pd.DataFrame(
            {
                "monthly_sales_avg": monthly_sales,
                "sales_growth_qoq": sales_growth_qoq,
                "sales_growth_yoy": sales_growth_yoy,
                "sales_volatility": np.random.uniform(0.02, 0.35, n_areas),
                "weekday_weekend_ratio": np.random.uniform(0.7, 2.2, n_areas),
                "peak_hour_concentration": np.random.uniform(0.18, 0.55, n_areas),
                "store_count": store_count,
                "store_growth_qoq": store_growth_qoq,
                "open_rate": open_rate,
                "close_rate": close_rate,
                "open_close_ratio": open_rate / np.maximum(close_rate, 0.1),
                "competition_index": np.clip(np.maximum(store_growth_qoq, 0) + np.maximum(-sales_growth_qoq, 0), 0, 1),
                "total_population": total_population,
                "population_growth_qoq": population_growth_qoq,
                "young_ratio": young_ratio,
                "worker_ratio": worker_ratio,
                "age_diversity_index": np.random.uniform(0.45, 0.82, n_areas),
                "sales_per_store": monthly_sales / np.maximum(store_count, 1),
                "sales_per_population": monthly_sales / np.maximum(total_population, 1),
                "risk_trend_3q": np.random.normal(0, 3, n_areas),
                "quarters_since_peak": np.random.randint(0, 10, n_areas),
            }
        )

        y = ((data["close_rate"] > 15) & (data["sales_growth_yoy"] < -0.05)).astype(int)
        if y.mean() < 0.18:
            risky = data.sort_values(["close_rate", "sales_growth_yoy"], ascending=[False, True]).head(max(1, n_areas // 4)).index
            y.loc[risky] = 1
        elif y.mean() > 0.32:
            safe = y[y == 1].sample(frac=(y.mean() - 0.25) / y.mean(), random_state=42).index
            y.loc[safe] = 0

        return data[FEATURE_COLUMNS], pd.Series(y, name="label")

    async def run_full_pipeline(self, db) -> None:
        """Ensure required ML models are available."""
        if not self.model_store.exists("risk_scorer"):
            await self.train_risk_model(db)
        logger.warning("ML 모델 준비 완료")

    def _generate_sample_forecast_data(self, periods: int = 8) -> pd.DataFrame:
        dates = pd.date_range("2023-01-01", periods=periods, freq="QS")
        sales = np.linspace(180_000_000, 230_000_000, periods) * np.random.normal(1, 0.05, periods)
        return pd.DataFrame(
            {
                "ds": dates,
                "y": np.log1p(sales),
                "store_count": np.linspace(80, 110, periods),
                "population": np.linspace(35_000, 39_000, periods),
                "close_rate": np.linspace(7.0, 9.0, periods),
            }
        )


def train_risk_model(frame: pd.DataFrame, label_column: str = "is_closed") -> str:
    """Backward-compatible sync helper for older scripts."""
    if label_column not in frame:
        raise ValueError(f"Missing label column: {label_column}")
    X = frame[FEATURE_COLUMNS].copy()
    y = frame[label_column].astype(int)
    scorer = RiskScorer()
    scorer.train(X, y)
    return str(ModelStore().path_for("risk_scorer"))
