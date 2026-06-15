"""Runtime Optos UWF reference stats loaded from open dataset cross-validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_STATS_PATH = Path("data/processed/optos_reference/stats.json")

_stats_cache: dict | None = None


@dataclass
class OptosReference:
    available: bool
    n_images: int
    datasets: list[str]
    focus_score_median: float | None
    focus_score_p10: float | None
    recommended_focus_min: float
    notes: list[str]

    def qc_notes(self) -> list[str]:
        if not self.available:
            return [
                "Optos reference stats not built yet — run data/pipelines/build_optos_reference.py "
                "after ingesting UWF4DR or UWF IQA manifests."
            ]
        return [
            f"Optos QC calibrated against {self.n_images} open UWF images "
            f"({', '.join(self.datasets)}).",
            f"Reference focus median: {self.focus_score_median}, p10: {self.focus_score_p10}.",
        ]


def load_optos_reference(stats_path: Path | None = None) -> OptosReference:
    global _stats_cache
    path = stats_path or DEFAULT_STATS_PATH
    if _stats_cache is None and path.exists():
        _stats_cache = json.loads(path.read_text())

    if not _stats_cache:
        return OptosReference(
            available=False,
            n_images=0,
            datasets=[],
            focus_score_median=None,
            focus_score_p10=None,
            recommended_focus_min=35.0,
            notes=[],
        )

    return OptosReference(
        available=True,
        n_images=int(_stats_cache.get("n_images", 0)),
        datasets=list(_stats_cache.get("datasets", [])),
        focus_score_median=_stats_cache.get("focus_score_median"),
        focus_score_p10=_stats_cache.get("focus_score_p10"),
        recommended_focus_min=float(_stats_cache.get("recommended_focus_min", 35)),
        notes=list(_stats_cache.get("notes", [])),
    )
