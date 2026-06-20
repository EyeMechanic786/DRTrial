"""Train ICDR classifier from dataset manifest lesion features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, cohen_kappa_score
from sklearn.model_selection import train_test_split

from ml.dr_pathway.lesion_detection import detect_lesions
from ml.dr_pathway.preprocessing import preprocess_fundus
from ml.inference.icdr_classifier import lesion_features
from ml.inference.model_registry import register_model


def load_manifest_records(manifest_path: Path) -> list[dict]:
    return json.loads(manifest_path.read_text())


def extract_training_data(manifest_path: Path, max_samples: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    records = load_manifest_records(manifest_path)
    X, y = [], []
    for rec in records:
        if max_samples is not None and len(y) >= max_samples:
            break
        if rec.get("icdr_grade") is None:
            continue
        img_path = Path(rec["image_path"])
        if not img_path.exists():
            continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        meta = rec.get("metadata", {})
        camera_hint = meta.get("camera_vendor", "auto")
        if camera_hint == "optos_uwf":
            preprocess = preprocess_fundus(img, camera_hint="optos_uwf")
            detection = detect_lesions(preprocess.analysis_bgr, preprocess.fovea_xy)
        else:
            detection = detect_lesions(img)
        features = lesion_features(detection.metrics).flatten()
        X.append(features)
        y.append(int(rec["icdr_grade"]))
    return np.array(X), np.array(y)


def train_synthetic_fallback() -> None:
    """Bootstrap classifier from rule-based synthetic feature vectors."""
    from ml.dr_pathway.schemas import LesionMetrics

    X, y = [], []
    patterns = [
        ([0, 0, 0, 0, 0, 0, 0, 0, 0], 0),
        ([5, 0, 0, 0, 0.01, 0, 0, 0, 0], 1),
        ([3, 4, 2, 1, 0.02, 0.1, 0.05, 0.02, 0.3], 2),
        ([2, 25, 3, 4, 0.01, 0.8, 0.1, 0.15, 0.5], 3),
        ([1, 30, 8, 6, 0.01, 1.2, 0.5, 0.3, 0.8], 4),
    ]
    for base, grade in patterns:
        for _ in range(20):
            noise = np.random.randn(9) * 0.1
            X.append(np.array(base, dtype=np.float32) + noise)
            y.append(grade)
    return np.array(X), np.array(y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, help="Path to dataset manifest.json")
    parser.add_argument("--max-samples", type=int, default=None, help="Limit training records")
    parser.add_argument("--output", type=Path, default=Path("ml/weights/icdr_classifier.joblib"))
    args = parser.parse_args()

    if args.manifest and args.manifest.exists():
        X, y = extract_training_data(args.manifest, args.max_samples)
        print(f"Training on {len(y)} real samples from {args.manifest}")
    else:
        X, y = train_synthetic_fallback()
        print(f"Training on {len(y)} synthetic bootstrap samples")

    if len(y) < 10:
        print("Insufficient data; using synthetic bootstrap.")
        X, y = train_synthetic_fallback()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = GradientBoostingClassifier(n_estimators=100, max_depth=4, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    kappa = cohen_kappa_score(y_test, y_pred, weights="quadratic")
    print(f"Quadratic weighted kappa: {kappa:.3f}")
    print(classification_report(y_test, y_pred))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, args.output)
    register_model("drtrial-gb-1.1.0", {"type": "gradient_boosting", "kappa": kappa, "n_samples": len(y)})
    print(f"Model saved → {args.output}")


if __name__ == "__main__":
    main()
