"""End-to-end DR analysis pathway."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image

from ml.dr_pathway.dme import grade_dme
from ml.dr_pathway.grading import aao_recommendation, grade_icdr, ico_recommendation
from ml.dr_pathway.lesion_detection import LESION_COLORS, detect_lesions
from ml.dr_pathway.qc import assess_image_quality
from ml.dr_pathway.schemas import AnalysisResult, OverlayLayer

MODEL_VERSION = "drtrial-cv-1.0.0"


def _draw_overlays(image_bgr: np.ndarray, masks: dict[str, np.ndarray]) -> str:
    """Render lesion overlays and return base64 PNG."""
    overlay = image_bgr.copy()
    for lesion_type, mask in masks.items():
        color = LESION_COLORS[lesion_type]
        colored = np.zeros_like(image_bgr)
        colored[mask > 0] = color
        overlay = cv2.addWeighted(overlay, 1.0, colored, 0.45, 0)

    rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def analyze_fundus_image(
    image_bytes: bytes,
    study_id: str,
    resource_setting: str = "high",
) -> AnalysisResult:
    """Full pathway: QC → lesion detection → ICDR grade → DME → ICO/AAO recommendations."""
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError("Could not decode image. Upload JPEG or PNG colour fundus photo.")

    qc = assess_image_quality(image_bgr)
    detection = detect_lesions(image_bgr)

    icdr_grade, icdr_label, confidence, grade_rationale = grade_icdr(detection.metrics)
    dme_grade, dme_label, dme_rationale = grade_dme(detection.metrics)

    rationale = grade_rationale + dme_rationale
    if not qc.passed:
        rationale.extend([f"QC warning: {w}" for w in qc.warnings])
        confidence = max(0.3, confidence - 0.15)

    overlay_b64 = _draw_overlays(image_bgr, detection.masks)
    composite = OverlayLayer(
        lesion_type="composite_overlay",
        color_rgb=[255, 255, 255],
        mask_png_base64=overlay_b64,
    )

    ico = ico_recommendation(
        icdr_grade, icdr_label, dme_grade, dme_label, resource_setting
    )
    aao = aao_recommendation(icdr_grade, icdr_label, dme_grade, dme_label)

    return AnalysisResult(
        study_id=study_id,
        model_version=MODEL_VERSION,
        qc=qc,
        lesions=detection.metrics,
        icdr_grade=icdr_grade,
        icdr_label=icdr_label,
        icdr_confidence=round(confidence, 3),
        dme_grade=dme_grade,
        dme_label=dme_label,
        ico=ico,
        aao=aao,
        overlays=detection.overlays + [composite],
        grading_rationale=rationale,
    )
