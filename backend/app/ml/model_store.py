"""Model persistence utilities with metadata support."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib


MODEL_DIR = Path(__file__).resolve().parents[2] / "models"


class ModelStore:
    """Store and load ML model artifacts under backend/models."""

    base_path = "models/"

    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = model_dir or MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model: Any,
        name: str,
        *,
        n_samples: int = 0,
        metrics: dict | None = None,
        version: str = "1.0.0",
    ) -> Path:
        """Save a model with joblib and write a sidecar metadata file."""
        stem = self._stem(name)
        model_path = self.model_dir / f"{stem}.pkl"
        meta_path = self.model_dir / f"{stem}_meta.json"

        joblib.dump(model, model_path)
        metadata = {
            "trained_at": datetime.utcnow().isoformat(),
            "n_samples": n_samples,
            "metrics": metrics or {},
            "version": version,
        }
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return model_path

    def load(self, name: str) -> Any | None:
        """Load a model, returning None if it does not exist."""
        path = self.path_for(name)
        if not path.exists():
            return None
        return joblib.load(path)

    def exists(self, name: str) -> bool:
        return self.path_for(name).exists()

    def list_models(self) -> list[dict]:
        """Return stored model files with metadata when available."""
        models = []
        for model_path in sorted(self.model_dir.glob("*.pkl")):
            stem = model_path.stem
            meta = self._read_meta(stem)
            models.append(
                {
                    "name": stem,
                    "path": str(model_path),
                    "size_bytes": model_path.stat().st_size,
                    **meta,
                }
            )
        return sorted(models, key=lambda item: item.get("trained_at", ""), reverse=True)

    def delete_old_models(self, keep_latest: int = 3) -> None:
        """Delete older model artifacts, keeping the latest N by metadata time."""
        models = self.list_models()
        for item in models[keep_latest:]:
            stem = item["name"]
            for path in (self.model_dir / f"{stem}.pkl", self.model_dir / f"{stem}_meta.json"):
                if path.exists():
                    path.unlink()

    def path_for(self, name: str) -> Path:
        return self.model_dir / f"{self._stem(name)}.pkl"

    def meta_path_for(self, name: str) -> Path:
        return self.model_dir / f"{self._stem(name)}_meta.json"

    def _read_meta(self, stem: str) -> dict:
        path = self.meta_path_for(stem)
        if not path.exists():
            return {"trained_at": None, "n_samples": None, "metrics": {}, "version": None}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"trained_at": None, "n_samples": None, "metrics": {}, "version": None}

    def _stem(self, name: str) -> str:
        return name[:-4] if name.endswith(".pkl") else name


def save_model(model: Any, name: str) -> Path:
    """Backward-compatible helper."""
    return ModelStore().save(model, name)


def load_model(name: str) -> Any | None:
    """Backward-compatible helper."""
    return ModelStore().load(name)


def model_exists(name: str) -> bool:
    """Backward-compatible helper."""
    return ModelStore().exists(name)
