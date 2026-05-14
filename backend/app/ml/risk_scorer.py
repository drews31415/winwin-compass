"""XGBoost-based commercial-area closure-risk scoring."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.ml.features import FEATURE_COLUMNS, FeatureEngineer
from app.ml.model_store import ModelStore


SALES_COLUMNS = ["sales_growth_qoq", "sales_growth_yoy", "sales_volatility", "sales_per_store"]
STORE_COLUMNS = ["close_rate", "open_close_ratio", "competition_index", "store_growth_qoq"]
POPULATION_COLUMNS = ["population_growth_qoq", "worker_ratio", "young_ratio", "sales_per_population"]


class RiskScorer:
    """Train and serve XGBoost closure-risk scores."""

    def __init__(self) -> None:
        self.model: XGBClassifier | None = None
        self.scaler: StandardScaler | None = None
        self.feature_engineer = FeatureEngineer()
        self.feature_columns: list[str] = FEATURE_COLUMNS.copy()
        self.model_store = ModelStore()
        self._load_if_available()

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """Train an XGBoost classifier and persist model/scaler artifacts."""
        X = X[self.feature_columns].replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median(numeric_only=True)).fillna(0)
        y = y.astype(int)

        stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
        X_train, X_valid, y_train, y_valid = train_test_split(
            X,
            y,
            test_size=0.2,
            stratify=stratify,
            random_state=42,
        )

        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_valid_scaled = self.scaler.transform(X_valid)

        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=3,
            random_state=42,
            eval_metric="auc",
            early_stopping_rounds=20,
        )

        try:
            self.model.fit(
                X_train_scaled,
                y_train,
                eval_set=[(X_valid_scaled, y_valid)],
                verbose=False,
            )
        except TypeError:
            self.model.set_params(early_stopping_rounds=None)
            self.model.fit(
                X_train_scaled,
                y_train,
                eval_set=[(X_valid_scaled, y_valid)],
                verbose=False,
            )

        probabilities = self.model.predict_proba(X_valid_scaled)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)

        metrics = {
            "accuracy": round(float(accuracy_score(y_valid, predictions)), 4),
            "auc_roc": round(float(roc_auc_score(y_valid, probabilities)), 4) if y_valid.nunique() > 1 else 0.0,
            "precision": round(float(precision_score(y_valid, predictions, zero_division=0)), 4),
            "recall": round(float(recall_score(y_valid, predictions, zero_division=0)), 4),
            "f1": round(float(f1_score(y_valid, predictions, zero_division=0)), 4),
            "feature_importance": self._feature_importance(),
        }

        self.model_store.save(self.model, "risk_scorer", n_samples=len(X), metrics=metrics)
        self.model_store.save(self.scaler, "risk_scaler", n_samples=len(X), metrics={"source": "risk_scorer"})
        return metrics

    async def score(self, area_cd: str, db: Any) -> dict:
        """Calculate ML-based risk score for a single commercial area."""
        if self.model is None or self.scaler is None:
            return await self.score_without_model(area_cd, db)

        frame = await self.feature_engineer.get_area_features(area_cd, db)
        if frame.empty:
            return await self.score_without_model(area_cd, db)

        latest = frame.tail(1).copy()
        X = latest[self.feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
        X_scaled = self.scaler.transform(X)
        probability = float(self.model.predict_proba(X_scaled)[0, 1])
        score = int(round(probability * 100))

        return {
            "area_cd": area_cd,
            "risk_score": score,
            "risk_level": self.get_risk_level(score),
            "risk_probability": round(probability, 4),
            "main_risk_factors": self._main_risk_factors(latest, X_scaled),
            "score_breakdown": self._score_breakdown(latest),
            "compared_to_avg": self._compared_to_avg(score),
        }

    async def score_without_model(self, area_cd: str, db: Any) -> dict:
        """Rule-based fallback when trained artifacts are unavailable."""
        frame = await self.feature_engineer.get_area_features(area_cd, db)
        if frame.empty:
            score = 30
            latest = pd.DataFrame([{column: 0 for column in self.feature_columns}])
        else:
            latest = frame.tail(1)
            row = latest.iloc[0]
            score = 30
            close_rate = float(row.get("close_rate") or 0)
            sales_growth = float(row.get("sales_growth_qoq") or 0)
            store_growth = float(row.get("store_growth_qoq") or 0)
            population_growth = float(row.get("population_growth_qoq") or 0)

            if close_rate > 15:
                score += 30
            elif close_rate > 10:
                score += 15
            if sales_growth < -0.10:
                score += 25
            elif sales_growth < -0.05:
                score += 12
            if store_growth > 0.20:
                score += 20
            if population_growth < -0.05:
                score += 15
            score = min(100, score)

        probability = round(score / 100, 4)
        return {
            "area_cd": area_cd,
            "risk_score": score,
            "risk_level": self.get_risk_level(score),
            "risk_probability": probability,
            "main_risk_factors": self._rule_based_factors(latest),
            "score_breakdown": self._score_breakdown(latest),
            "compared_to_avg": self._compared_to_avg(score),
        }

    def get_risk_level(self, score: int) -> str:
        if score <= 39:
            return "낮음"
        if score <= 69:
            return "중간"
        return "높음"

    def _load_if_available(self) -> None:
        if self.model_store.exists("risk_scorer"):
            self.model = self.model_store.load("risk_scorer")
        if self.model_store.exists("risk_scaler"):
            self.scaler = self.model_store.load("risk_scaler")

    def _feature_importance(self) -> dict[str, float]:
        if self.model is None:
            return {}
        values = self.model.feature_importances_
        return {
            column: round(float(value), 6)
            for column, value in sorted(
                zip(self.feature_columns, values),
                key=lambda item: item[1],
                reverse=True,
            )
        }

    def _main_risk_factors(self, latest: pd.DataFrame, X_scaled: np.ndarray) -> list[dict]:
        try:
            import shap

            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(X_scaled)
            if isinstance(shap_values, list):
                shap_row = shap_values[-1][0]
            else:
                shap_row = shap_values[0]
            top_indexes = np.argsort(np.abs(shap_row))[-3:][::-1]
            factors = []
            for index in top_indexes:
                column = self.feature_columns[int(index)]
                factors.append(self._factor_payload(column, latest.iloc[0], float(abs(shap_row[index]))))
            return factors
        except Exception:
            return self._rule_based_factors(latest)

    def _rule_based_factors(self, latest: pd.DataFrame) -> list[dict]:
        row = latest.iloc[0]
        sales_growth_qoq = float(row.get("sales_growth_qoq") or 0)
        sales_growth_yoy = float(row.get("sales_growth_yoy") or 0)
        store_growth_qoq = float(row.get("store_growth_qoq") or 0)
        population_growth_qoq = float(row.get("population_growth_qoq") or 0)

        candidates = [
            (
                float(row.get("close_rate") or 0) / 100,
                self._factor_payload("close_rate", row, float(row.get("close_rate") or 0) / 100),
            ),
            (
                max(0.0, -sales_growth_qoq, -sales_growth_yoy),
                self._factor_payload(
                    "sales_growth_qoq" if sales_growth_qoq <= sales_growth_yoy else "sales_growth_yoy",
                    row,
                    max(0.0, -sales_growth_qoq, -sales_growth_yoy),
                ),
            ),
            (
                max(0.0, store_growth_qoq),
                self._factor_payload("store_growth_qoq", row, max(0.0, store_growth_qoq)),
            ),
            (
                max(0.0, -population_growth_qoq),
                self._factor_payload("population_growth_qoq", row, max(0.0, -population_growth_qoq)),
            ),
        ]
        sorted_candidates = sorted(candidates, key=lambda item: item[0], reverse=True)
        meaningful = [payload for score, payload in sorted_candidates if score > 0.005]
        if len(meaningful) < 3:
            meaningful.extend([
                self._factor_payload("young_ratio", row, 0.08),
                self._factor_payload("worker_ratio", row, 0.06),
            ])
        return meaningful[:3]

    def _factor_payload(self, column: str, row: pd.Series, contribution: float) -> dict:
        value = float(row.get(column) or 0)
        if pd.isna(value):
            value = 0.0
        if column == "close_rate":
            return {
                "factor": "폐업률",
                "value": f"{value:.1f}%",
                "contribution": round(contribution, 4),
                "description": "최근 폐업률 수준이 위험 점수에 반영되었습니다.",
            }
        if column in {"sales_growth_qoq", "sales_growth_yoy"}:
            period = "전분기" if column == "sales_growth_qoq" else "전년"
            direction = "감소" if value < 0 else "증가"
            return {
                "factor": "매출 감소" if value < 0 else "매출 변동",
                "value": f"{period} 대비 {value * 100:+.1f}%",
                "contribution": round(contribution, 4),
                "description": f"{period} 대비 매출 {direction} 흐름이 위험 점수에 반영되었습니다.",
            }
        if column == "competition_index":
            return {
                "factor": "경쟁 강도",
                "value": f"{value:.2f}",
                "contribution": round(contribution, 4),
                "description": "상권 내 점포 밀집도와 매출 대비 경쟁 수준이 반영되었습니다.",
            }
        if column == "store_growth_qoq":
            direction = "증가" if value >= 0 else "감소"
            return {
                "factor": "경쟁 심화" if value >= 0 else "점포 감소",
                "value": f"점포 {value * 100:+.1f}% {direction}",
                "contribution": round(contribution, 4),
                "description": "전분기 대비 점포 수 변화가 위험 점수에 반영되었습니다.",
            }
        if column in {"population_growth_qoq", "worker_ratio", "young_ratio"}:
            if column == "population_growth_qoq":
                direction = "감소" if value < 0 else "증가"
                value_label = f"전분기 대비 {value * 100:+.1f}%"
                description = f"생활인구 {direction} 흐름이 상권 수요 위험에 반영되었습니다."
            elif column == "worker_ratio":
                value_label = f"직장인구 비중 {value * 100:.1f}%"
                description = "직장인구 비중이 상권 수요 안정성 판단에 반영되었습니다."
            else:
                value_label = f"20~30대 비중 {value * 100:.1f}%"
                description = "주요 소비 연령대 비중이 상권 수요 판단에 반영되었습니다."
            return {
                "factor": "인구 변화",
                "value": value_label,
                "contribution": round(contribution, 4),
                "description": description,
            }
        if column == "close_rate":
            return {
                "factor": "폐업률",
                "value": f"{value:.1f}%",
                "contribution": round(contribution, 4),
                "description": "최근 폐업률 수준이 위험 점수에 반영되었습니다",
            }
        if column in {"sales_growth_qoq", "sales_growth_yoy"}:
            return {
                "factor": "매출 감소",
                "value": f"{value * 100:.1f}%",
                "contribution": round(contribution, 4),
                "description": "분기 또는 전년 대비 매출 변화가 반영되었습니다",
            }
        if column in {"store_growth_qoq", "competition_index"}:
            return {
                "factor": "경쟁 심화",
                "value": f"점포 {value * 100:.1f}% 증가",
                "contribution": round(contribution, 4),
                "description": "점포 증가와 매출 감소가 함께 반영되었습니다",
            }
        if column in {"population_growth_qoq", "worker_ratio", "young_ratio"}:
            return {
                "factor": "인구 변화",
                "value": f"{value * 100:.1f}%",
                "contribution": round(contribution, 4),
                "description": "생활인구와 직장인구 변화가 반영되었습니다",
            }
        return {
            "factor": column,
            "value": f"{value:.4f}",
            "contribution": round(contribution, 4),
            "description": "모델이 주요 위험 변수로 판단했습니다",
        }

    def _score_breakdown(self, latest: pd.DataFrame) -> dict[str, int]:
        row = latest.iloc[0]
        sales_penalty = max(0, -float(row.get("sales_growth_qoq") or 0)) * 500
        store_penalty = float(row.get("close_rate") or 0) * 3 + max(0, float(row.get("store_growth_qoq") or 0)) * 100
        population_penalty = max(0, -float(row.get("population_growth_qoq") or 0)) * 600
        return {
            "sales_score": int(min(100, round(30 + sales_penalty))),
            "store_score": int(min(100, round(30 + store_penalty))),
            "population_score": int(min(100, round(30 + population_penalty))),
        }

    def _compared_to_avg(self, score: int) -> str:
        diff = score - 57
        if diff > 0:
            return f"+{diff}점 (서울 평균 대비 높음)"
        if diff < 0:
            return f"{diff}점 (서울 평균 대비 낮음)"
        return "0점 (서울 평균과 유사)"


class ClosureRiskScorer:
    """Backward-compatible wrapper used by earlier trainer code."""

    def __init__(self) -> None:
        self.model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
        )

    def fit(self, features: pd.DataFrame, labels: pd.Series) -> None:
        self.model.fit(features, labels)

    def predict_risk(self, features: pd.DataFrame) -> list[float]:
        return self.model.predict_proba(features)[:, 1].tolist()
