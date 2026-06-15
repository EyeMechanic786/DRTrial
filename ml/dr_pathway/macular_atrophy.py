"""Detect central macular atrophy as non-DR pathology (parallel to DR analysis).

The macular region is never excluded from lesion or DME assessment — hard exudates
and edema can coexist with atrophy. This module flags atrophy so grading can
account for common false-positive DR patterns.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy import ndimage


@dataclass
class MacularAtrophyResult:
    detected: bool
    confidence: float
    central_area_pct: float
    region_mask: np.ndarray
    rationale: list[str]


def detect_macular_atrophy(
    image_bgr: np.ndarray,
    fovea_xy: tuple[float, float] | None = None,
) -> MacularAtrophyResult:
    """Identify suspected central macular atrophy; does not mask out analysis."""
    h, w = image_bgr.shape[:2]
    fx, fy = (w / 2, h / 2) if fovea_xy is None else fovea_xy
    fx_i, fy_i = int(np.clip(fx, 0, w - 1)), int(np.clip(fy, 0, h - 1))

    ys, xs = np.ogrid[:h, :w]
    dist2 = (xs - fx) ** 2 + (ys - fy) ** 2
    search_r = min(h, w) * 0.22
    central = dist2 <= search_r**2

    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l_ch = lab[:, :, 0]
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]

    empty = np.zeros((h, w), dtype=np.uint8)
    if not np.any(central):
        return MacularAtrophyResult(False, 0.0, 0.0, empty, [])

    l_thresh = float(np.percentile(l_ch[central], 58))
    pale = (l_ch >= l_thresh) & central & (saturation < 130)
    pale = pale.astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    pale = cv2.morphologyEx(pale, cv2.MORPH_CLOSE, kernel)
    pale = cv2.morphologyEx(pale, cv2.MORPH_OPEN, kernel)

    labeled, n = ndimage.label(pale)
    if n == 0:
        return MacularAtrophyResult(False, 0.0, 0.0, empty, [])

    fovea_label = int(labeled[fy_i, fx_i])
    if fovea_label == 0:
        areas = ndimage.sum(pale > 0, labeled, range(1, n + 1))
        fovea_label = int(np.argmax(areas)) + 1

    region_mask = (labeled == fovea_label).astype(np.uint8) * 255
    area_px = int(np.sum(region_mask > 0))
    area_pct = area_px / (h * w) * 100

    ring = (dist2 > search_r**2) & (dist2 <= (min(h, w) * 0.34) ** 2)
    zone_l = float(np.mean(l_ch[region_mask > 0]))
    ring_l = float(np.mean(l_ch[ring])) if np.any(ring) else zone_l
    delta_l = zone_l - ring_l
    zone_std = float(np.std(l_ch[region_mask > 0]))

    rationale: list[str] = []
    score = 0.0

    if area_pct >= 0.6:
        score += 0.3
        rationale.append(f"Central pale zone covers {area_pct:.1f}% of image.")
    if delta_l >= 5:
        score += 0.25
        rationale.append(
            f"Macular zone brighter than perimacular ring (ΔL={delta_l:.0f}/255)."
        )
    if zone_std < 30:
        score += 0.2
        rationale.append(
            "Central zone is relatively homogeneous — pattern consistent with atrophy."
        )
    if area_pct >= 1.5 and delta_l >= 7:
        score += 0.15

    detected = score >= 0.55 and area_pct >= 0.6
    confidence = min(0.92, score)

    if detected:
        rationale.insert(
            0,
            "Suspected macular atrophy (non-DR pathology). "
            "Macula remains fully analysed for exudates and edema.",
        )
        rationale.append(
            "Consider OCT / FAF for atrophy confirmation; "
            "coexistent DR and DME may still be present."
        )
    else:
        region_mask = empty

    return MacularAtrophyResult(
        detected=detected,
        confidence=round(confidence, 3),
        central_area_pct=round(area_pct, 3),
        region_mask=region_mask,
        rationale=rationale,
    )
