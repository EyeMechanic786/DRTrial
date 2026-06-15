"""Vendor-neutral fundus image preprocessing.

Supports standard colour fundus photography (CFP), Optos ultra-widefield (UWF),
and other confocal/SLO devices without camera-specific coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np


class CameraVendor(str, Enum):
    AUTO = "auto"
    STANDARD_CFP = "standard_cfp"
    OPTOS_UWF = "optos_uwf"
    CONFOCAL_SLO = "confocal_slo"
    UNKNOWN = "unknown"


VENDOR_LABELS: dict[str, str] = {
    CameraVendor.STANDARD_CFP: "Standard colour fundus (CFP)",
    CameraVendor.OPTOS_UWF: "Optos / ultra-widefield (UWF)",
    CameraVendor.CONFOCAL_SLO: "Confocal scanning laser ophthalmoscope",
    CameraVendor.UNKNOWN: "Unknown camera — generic normalization applied",
}


@dataclass
class PreprocessResult:
    original_bgr: np.ndarray
    analysis_bgr: np.ndarray
    vendor: CameraVendor
    vendor_label: str
    fovea_xy: tuple[float, float]
    fovea_xy_original: tuple[float, float]
    roi_offset: tuple[int, int]
    roi_size: tuple[int, int]
    scale: float
    notes: list[str]


def _fundus_mask(gray: np.ndarray) -> np.ndarray:
    """Segment fundus tissue vs black letterbox background."""
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    _, mask = cv2.threshold(blurred, 18, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    return mask


def _fundus_bbox(mask: np.ndarray, padding: float = 0.02) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        h, w = mask.shape[:2]
        return 0, 0, w, h
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    h, w = mask.shape[:2]
    pad_x = int((x1 - x0) * padding)
    pad_y = int((y1 - y0) * padding)
    x0 = max(0, x0 - pad_x)
    y0 = max(0, y0 - pad_y)
    x1 = min(w, x1 + pad_x)
    y1 = min(h, y1 + pad_y)
    return x0, y0, x1, y1


def _detect_vendor(
    image_bgr: np.ndarray,
    mask: np.ndarray,
    bbox: tuple[int, int, int, int],
    hint: CameraVendor | None,
) -> CameraVendor:
    if hint and hint != CameraVendor.AUTO:
        return hint

    h, w = image_bgr.shape[:2]
    x0, y0, x1, y1 = bbox
    roi_w, roi_h = x1 - x0, y1 - y0
    aspect = roi_w / roi_h if roi_h else 1.0
    background_ratio = 1.0 - (mask > 0).sum() / mask.size

    b, g, r = cv2.split(image_bgr)
    green_dom = float(g.mean()) / (float(r.mean()) + 1e-6)

    # Optos UWF: large black border, elliptical fundus, often green-dominant cSLO
    if background_ratio > 0.25 and 0.85 <= aspect <= 1.35 and min(roi_w, roi_h) > 800:
        return CameraVendor.OPTOS_UWF
    if background_ratio > 0.15 and aspect > 1.4:
        return CameraVendor.OPTOS_UWF
    if green_dom > 1.15 and background_ratio > 0.1:
        return CameraVendor.CONFOCAL_SLO

    if 0.9 <= aspect <= 1.8 and background_ratio < 0.15:
        return CameraVendor.STANDARD_CFP

    return CameraVendor.UNKNOWN


def _estimate_optic_disc(gray: np.ndarray, mask: np.ndarray) -> tuple[float, float] | None:
    """Bright circular region heuristic for optic disc center."""
    masked = cv2.bitwise_and(gray, gray, mask=mask)
    blurred = cv2.GaussianBlur(masked, (31, 31), 0)
    _, bright = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = cv2.bitwise_and(bright, mask)
    contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    h, w = gray.shape[:2]
    best = None
    best_score = 0.0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < (h * w * 0.001) or area > (h * w * 0.08):
            continue
        perimeter = cv2.arcLength(cnt, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        if circularity < 0.4:
            continue
        M = cv2.moments(cnt)
        if M["m00"] == 0:
            continue
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        score = circularity * area
        if score > best_score:
            best_score = score
            best = (cx, cy)
    return best


def _estimate_fovea(
    gray: np.ndarray,
    mask: np.ndarray,
    vendor: CameraVendor,
    roi_w: int,
    roi_h: int,
) -> tuple[float, float]:
    """Estimate fovea location — vendor-aware, not always image center."""
    disc = _estimate_optic_disc(gray, mask)
    if disc is not None:
        cx, cy = disc
        # Fovea is temporal to optic disc (typically right on standard fundus orientation)
        offset = 0.22 * min(roi_w, roi_h)
        fx = min(roi_w - 1, cx + offset)
        fy = cy
        return fx, fy

    if vendor == CameraVendor.OPTOS_UWF:
        # Macula often slightly temporal-inferior in Optos orientation
        return roi_w * 0.55, roi_h * 0.48

    # Standard CFP: macula near center
    return roi_w * 0.5, roi_h * 0.5


def _normalize_colors(image_bgr: np.ndarray, vendor: CameraVendor) -> np.ndarray:
    """Vendor-neutral contrast normalization via CLAHE on green channel."""
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    result = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    if vendor in (CameraVendor.OPTOS_UWF, CameraVendor.CONFOCAL_SLO):
        # cSLO pseudocolour: boost green channel slightly for lesion contrast
        b_ch, g_ch, r_ch = cv2.split(result)
        g_ch = cv2.addWeighted(g_ch, 1.1, b_ch, 0.0, 0)
        result = cv2.merge([b_ch, np.clip(g_ch, 0, 255).astype(np.uint8), r_ch])
    return result


def _resize_for_analysis(image_bgr: np.ndarray, max_dim: int = 2048) -> tuple[np.ndarray, float]:
    h, w = image_bgr.shape[:2]
    if max(h, w) <= max_dim:
        return image_bgr, 1.0
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def preprocess_fundus(
    image_bgr: np.ndarray,
    camera_hint: str = "auto",
) -> PreprocessResult:
    """
    Vendor-neutral preprocessing pipeline:
    1. Detect fundus ROI (removes Optos letterbox / black borders)
    2. Infer camera vendor
    3. Normalize colour/contrast
    4. Estimate fovea for macula-centric grading
    5. Resize for consistent lesion detector scale
    """
    notes: list[str] = []
    hint = CameraVendor(camera_hint) if camera_hint in CameraVendor._value2member_map_ else CameraVendor.AUTO

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    mask = _fundus_mask(gray)
    x0, y0, x1, y1 = _fundus_bbox(mask)
    roi = image_bgr[y0:y1, x0:x1].copy()
    roi_mask = mask[y0:y1, x0:x1]
    roi_gray = gray[y0:y1, x0:x1]

    vendor = _detect_vendor(image_bgr, mask, (x0, y0, x1, y1), hint if hint != CameraVendor.AUTO else None)
    notes.append(f"Detected camera profile: {VENDOR_LABELS.get(vendor, vendor.value)}")

    if vendor == CameraVendor.OPTOS_UWF:
        notes.append(
            "Optos UWF: peripheral lesions included; macula localized relative to optic disc."
        )
    elif vendor == CameraVendor.STANDARD_CFP:
        notes.append("Standard CFP: ETDRS-style central field assumed.")

    normalized = _normalize_colors(roi, vendor)
    analysis_bgr, scale = _resize_for_analysis(normalized)

    roi_h, roi_w = roi.shape[:2]
    fx, fy = _estimate_fovea(roi_gray, roi_mask, vendor, roi_w, roi_h)
    fx_scaled, fy_scaled = fx * scale, fy * scale
    fx_orig, fy_orig = fx + x0, fy + y0

    if (x0, y0) != (0, 0) or (x1, y1) != (image_bgr.shape[1], image_bgr.shape[0]):
        notes.append(f"Fundus ROI extracted ({roi_w}x{roi_h}px); letterbox/crop removed.")
    if scale < 1.0:
        notes.append(f"Downscaled to max 2048px (scale={scale:.3f}) for analysis.")

    return PreprocessResult(
        original_bgr=image_bgr,
        analysis_bgr=analysis_bgr,
        vendor=vendor,
        vendor_label=VENDOR_LABELS.get(vendor, vendor.value),
        fovea_xy=(fx_scaled, fy_scaled),
        fovea_xy_original=(fx_orig, fy_orig),
        roi_offset=(x0, y0),
        roi_size=(roi_w, roi_h),
        scale=scale,
        notes=notes,
    )


def map_bbox_to_original(
    box: dict,
    preprocess: PreprocessResult,
) -> dict:
    """Map detection bbox from analysis image coords back to original upload."""
    inv_scale = 1.0 / preprocess.scale if preprocess.scale else 1.0
    ox, oy = preprocess.roi_offset
    return {
        "x": int(box["x"] * inv_scale + ox),
        "y": int(box["y"] * inv_scale + oy),
        "w": int(box["w"] * inv_scale),
        "h": int(box["h"] * inv_scale),
    }


def map_mask_to_original(mask: np.ndarray, preprocess: PreprocessResult) -> np.ndarray:
    """Resize mask and place into original image coordinates."""
    h_orig, w_orig = preprocess.original_bgr.shape[:2]
    inv_scale = 1.0 / preprocess.scale if preprocess.scale else 1.0
    roi_h, roi_w = preprocess.roi_size
    restored_roi = cv2.resize(
        mask,
        (roi_w, roi_h),
        interpolation=cv2.INTER_NEAREST,
    )
    full = np.zeros((h_orig, w_orig), dtype=np.uint8)
    ox, oy = preprocess.roi_offset
    full[oy : oy + roi_h, ox : ox + roi_w] = restored_roi
    return full
