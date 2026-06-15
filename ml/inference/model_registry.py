"""Model version registry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "weights" / "registry.json"


def get_active_version() -> str:
    if REGISTRY_PATH.exists():
        data = json.loads(REGISTRY_PATH.read_text())
        return data.get("active_version", "drtrial-cv-1.0.0")
    return "drtrial-cv-1.0.0"


def register_model(version: str, metadata: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry = {"active_version": version, "models": {}}
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
    registry["active_version"] = version
    registry["models"][version] = {
        **metadata,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))
