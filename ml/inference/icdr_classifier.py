"""ICDR classifier — sklearn model on lesion feature vectors."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np

from ml.dr_pathway.schemas import LesionMetrics

WEIGHTS_PATH = Path(__file__).resolve().parents[1] / "weights" / "icdr_classifier.joblib"


def lesion_features(lesions: list[LesionMetrics]) -> np.ndarray:
    lm = {l.lesion_type: l for l in lesions}
    return np.array(
        [
            lm.get("microaneurysms", LesionMetrics(lesion_type="ma")).count,
            lm.get("hemorrhages", LesionMetrics(lesion_type="he")).count,
            lm.get("hard_exudates", LesionMetrics(lesion_type="ex")).count,
            lm.get("cotton_wool_spots", LesionMetrics(lesion_type="cws")).count,
            lm.get("microaneurysms", LesionMetrics(lesion_type="ma")).total_area_pct,
            lm.get("hemorrhages", LesionMetrics(lesion_type="he")).total_area_pct,
            lm.get("hard_exudates", LesionMetrics(lesion_type="ex")).total_area_pct,
            lm.get("cotton_wool_spots", LesionMetrics(lesion_type="cws")).total_area_pct,
            lm.get("hard_exudates", LesionMetrics(lesion_type="ex")).macula_proximity_score,
        ],
        dtype=np.float32,
    ).reshape(1, -1)


class ICDRClassifier:
    def __init__(self):
        self.model = None
        if WEIGHTS_PATH.exists():
            self.model = joblib.load(WEIGHTS_PATH)

    @property
    def available(self) -> bool:
        return self.model is not None

    def predict(self, lesions: list[LesionMetrics]) -> tuple[int, float] | None:
        if not self.model:
            return None
        features = lesion_features(lesions)
        grade = int(self.model.predict(features)[0])
        proba = self.model.predict_proba(features)[0]
        confidence = float(max(proba))
        return grade, confidence


_classifier: ICDRClassifier | None = None


def get_icdr_classifier() -> ICDRClassifier:
    global _classifier
    if _classifier is None:
        _classifier = ICDRClassifier()
    return _classifier
