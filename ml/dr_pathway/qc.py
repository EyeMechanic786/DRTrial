"""Fundus image quality control heuristics."""

from __future__ import annotations

import cv2
import numpy as np

from ml.dr_pathway.schemas import ImageQC


def assess_image_quality(image_bgr: np.ndarray) -> ImageQC:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]

    focus_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray) / 255.0)

    warnings: list[str] = []
    passed = True

    if focus_score < 50:
        warnings.append("Image may be out of focus (low sharpness).")
        passed = False
    elif focus_score < 100:
        warnings.append("Borderline focus quality.")

    if brightness < 0.15:
        warnings.append("Image appears under-exposed.")
        passed = False
    elif brightness > 0.85:
        warnings.append("Image appears over-exposed.")
        passed = False

    min_dim = min(h, w)
    if min_dim < 400:
        warnings.append("Low resolution; lesion detection may be unreliable.")
        passed = False

    aspect = w / h if h else 1.0
    if aspect < 0.8 or aspect > 2.0:
        warnings.append("Unusual aspect ratio; verify field of view.")

    return ImageQC(
        passed=passed,
        focus_score=round(focus_score, 2),
        brightness=round(brightness, 3),
        warnings=warnings,
    )
