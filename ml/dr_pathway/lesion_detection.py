"""Lesion detection from colour fundus photographs.

Phase 1 uses classical colour/morphology CV heuristics tuned for DR lesions.
Designed for plug-in replacement with deep learning (e.g. fundus-lesions-toolkit).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy import ndimage

from ml.dr_pathway.schemas import LesionMetrics, OverlayLayer

LESION_COLORS: dict[str, list[int]] = {
    "microaneurysms": [255, 0, 0],
    "hemorrhages": [200, 0, 50],
    "hard_exudates": [255, 255, 0],
    "cotton_wool_spots": [180, 180, 255],
}

MIN_AREA_PX = {
    "microaneurysms": 3,
    "hemorrhages": 15,
    "hard_exudates": 20,
    "cotton_wool_spots": 40,
}
MAX_AREA_PCT = {
    "microaneurysms": 0.05,
    "hemorrhages": 5.0,
    "hard_exudates": 8.0,
    "cotton_wool_spots": 6.0,
}


@dataclass
class DetectionOutput:
    metrics: list[LesionMetrics]
    overlays: list[OverlayLayer]
    masks: dict[str, np.ndarray]


def _green_channel_enhanced(gray: np.ndarray, green: np.ndarray) -> np.ndarray:
    enhanced = cv2.addWeighted(green, 0.75, gray, 0.25, 0)
    return cv2.equalizeHist(enhanced)


def _macula_distance_score(
    cy: float, cx: float, h: int, w: int, fovea_xy: tuple[float, float] | None = None
) -> float:
    """Proximity to estimated fovea (0=far, 1=at fovea)."""
    if fovea_xy is not None:
        fx, fy = fovea_xy
        ref_y, ref_x = fy, fx
    else:
        ref_y, ref_x = h / 2, w / 2
    dy = (cy - ref_y) / (h / 2)
    dx = (cx - ref_x) / (w / 2)
    dist = min(1.0, float(np.sqrt(dx * dx + dy * dy)))
    return round(1.0 - dist, 3)


def _connected_components(
    mask: np.ndarray,
    lesion_type: str,
    h: int,
    w: int,
    fovea_xy: tuple[float, float] | None = None,
) -> LesionMetrics:
    total_px = h * w
    labeled, n = ndimage.label(mask)
    if n == 0:
        return LesionMetrics(lesion_type=lesion_type, count=0)

    areas = ndimage.sum(mask, labeled, range(1, n + 1))
    min_a = MIN_AREA_PX.get(lesion_type, 5)
    max_pct = MAX_AREA_PCT.get(lesion_type, 10.0)
    valid = [int(a) for a in areas if a >= min_a and (a / total_px * 100) <= max_pct]

    proximities: list[float] = []
    for i in range(1, n + 1):
        area = int(areas[i - 1])
        if area < min_a:
            continue
        ys, xs = np.where(labeled == i)
        if len(ys) == 0:
            continue
        cy, cx = float(np.mean(ys)), float(np.mean(xs))
        proximities.append(_macula_distance_score(cy, cx, h, w, fovea_xy))

    total_area = sum(valid)
    macula_score = float(np.mean(proximities)) if proximities else 0.0

    return LesionMetrics(
        lesion_type=lesion_type,
        count=len(valid),
        total_area_px=total_area,
        total_area_pct=round(total_area / total_px * 100, 4),
        max_component_area_px=max(valid) if valid else 0,
        macula_proximity_score=round(macula_score, 3),
    )


def _mask_to_overlay(mask: np.ndarray, lesion_type: str) -> OverlayLayer:
    boxes: list[dict] = []
    labeled, n = ndimage.label(mask)
    for i in range(1, n + 1):
        ys, xs = np.where(labeled == i)
        if len(xs) < MIN_AREA_PX.get(lesion_type, 5):
            continue
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        boxes.append({"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0})

    return OverlayLayer(
        lesion_type=lesion_type,
        color_rgb=LESION_COLORS[lesion_type],
        bounding_boxes=boxes,
    )


def _detect_microaneurysms(green_enh: np.ndarray, h: int, w: int) -> np.ndarray:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    tophat = cv2.morphologyEx(green_enh, cv2.MORPH_TOPHAT, kernel)
    _, binary = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary.astype(np.uint8)


def _detect_hemorrhages(image_bgr: np.ndarray, h: int, w: int) -> np.ndarray:
    b, g, r = cv2.split(image_bgr)
    rg = cv2.subtract(r, g)
    rg = cv2.GaussianBlur(rg, (5, 5), 0)
    _, binary = cv2.threshold(rg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary.astype(np.uint8)


def _detect_hard_exudates(image_bgr: np.ndarray, h: int, w: int) -> np.ndarray:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([15, 40, 120])
    upper = np.array([45, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask.astype(np.uint8)


def _detect_cotton_wool_spots(gray: np.ndarray, h: int, w: int) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    diff = cv2.subtract(blur, gray)
    _, binary = cv2.threshold(diff, 12, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary.astype(np.uint8)


def detect_lesions(
    image_bgr: np.ndarray,
    fovea_xy: tuple[float, float] | None = None,
) -> DetectionOutput:
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    green = image_bgr[:, :, 1]
    green_enh = _green_channel_enhanced(gray, green)

    detectors = {
        "microaneurysms": _detect_microaneurysms(green_enh, h, w),
        "hemorrhages": _detect_hemorrhages(image_bgr, h, w),
        "hard_exudates": _detect_hard_exudates(image_bgr, h, w),
        "cotton_wool_spots": _detect_cotton_wool_spots(gray, h, w),
    }

    metrics = [
        _connected_components(m, name, h, w, fovea_xy) for name, m in detectors.items()
    ]
    overlays = [_mask_to_overlay(m, name) for name, m in detectors.items()]

    return DetectionOutput(metrics=metrics, overlays=overlays, masks=detectors)
