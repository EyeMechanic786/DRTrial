"""Fundus image quality control — vendor-neutral, ROI-aware."""

from __future__ import annotations

import cv2
import numpy as np

from ml.dr_pathway.preprocessing import CameraVendor, PreprocessResult, VENDOR_LABELS
from ml.dr_pathway.schemas import ImageQC


def _fov_label(vendor: CameraVendor) -> str:
    if vendor == CameraVendor.OPTOS_UWF:
        return "ultra-widefield (~200°)"
    if vendor == CameraVendor.STANDARD_CFP:
        return "standard field (~30–50°)"
    if vendor == CameraVendor.CONFOCAL_SLO:
        return "confocal widefield"
    return "unknown"


def assess_image_quality(
    image_bgr: np.ndarray,
    preprocess: PreprocessResult | None = None,
) -> ImageQC:
    """QC on fundus ROI — does not penalize Optos letterbox aspect ratios."""
    if preprocess is not None:
        gray = cv2.cvtColor(preprocess.analysis_bgr, cv2.COLOR_BGR2GRAY)
        vendor = preprocess.vendor
    else:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        vendor = CameraVendor.UNKNOWN

    h, w = gray.shape[:2]
    focus_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray) / 255.0)

    warnings: list[str] = []
    passed = True

    # Optos and UWF images often have lower Laplacian on downscaled ROI — relaxed threshold
    focus_min = 35 if vendor == CameraVendor.OPTOS_UWF else 50
    if focus_score < focus_min:
        warnings.append("Image may be out of focus (low sharpness).")
        passed = False
    elif focus_score < 80:
        warnings.append("Borderline focus quality.")

    if brightness < 0.12:
        warnings.append("Image appears under-exposed.")
        passed = False
    elif brightness > 0.88:
        warnings.append("Image appears over-exposed.")
        passed = False

    min_dim = min(h, w)
    if min_dim < 300:
        warnings.append("Low resolution after ROI extraction; lesion detection may be unreliable.")
        passed = False

    if vendor == CameraVendor.OPTOS_UWF:
        warnings.append(
            "Optos UWF: peripheral lesion sensitivity may differ from central CFP training data."
        )
    elif vendor == CameraVendor.UNKNOWN:
        warnings.append("Camera type not recognized; results use generic normalization.")

    return ImageQC(
        passed=passed,
        focus_score=round(focus_score, 2),
        brightness=round(brightness, 3),
        warnings=warnings,
        camera_vendor=vendor.value,
        camera_label=VENDOR_LABELS.get(vendor, vendor.value),
        field_of_view=_fov_label(vendor),
    )
