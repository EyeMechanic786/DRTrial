"""End-to-end DR analysis pathway."""

from __future__ import annotations

import base64
import io

import cv2
import numpy as np
from PIL import Image

from ml.dr_pathway.dme import grade_dme
from ml.dr_pathway.image_io import decode_fundus_image
from ml.dr_pathway.grading import (
    aao_recommendation,
    apply_atrophy_grading_context,
    atrophy_likely_explains_dr_findings,
    grade_icdr,
    ico_recommendation,
)
from ml.dr_pathway.lesion_detection import LESION_COLORS
from ml.dr_pathway.macular_atrophy import detect_macular_atrophy
from ml.dr_pathway.preprocessing import CameraVendor, preprocess_fundus
from ml.dr_pathway.qc import assess_image_quality
from ml.dr_pathway.schemas import (
    AnalysisResult,
    CameraInfo,
    NonDRPathologyFinding,
    OverlayLayer,
    ICDR_LABELS,
)
from ml.inference.icdr_classifier import get_icdr_classifier
from ml.inference.service import run_inference


def _fov_label(vendor: CameraVendor) -> str:
    if vendor == CameraVendor.OPTOS_UWF:
        return "ultra-widefield (~200°)"
    if vendor == CameraVendor.STANDARD_CFP:
        return "standard field (~30–50°)"
    return "variable"


def _draw_overlays(image_bgr: np.ndarray, masks: dict[str, np.ndarray]) -> str:
    h, w = image_bgr.shape[:2]
    overlay = image_bgr.copy()
    for lesion_type, mask in masks.items():
        if mask.shape[0] != h or mask.shape[1] != w:
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        color = LESION_COLORS.get(lesion_type, [255, 255, 255])
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
    camera_hint: str = "auto",
) -> AnalysisResult:
    """Full pathway: preprocess → QC → lesion detection → ICDR grade → DME → ICO/AAO."""
    image_bgr = decode_fundus_image(image_bytes)
    if image_bgr is None:
        raise ValueError(
            "Could not decode image. Upload a colour fundus photo "
            "(JPEG, PNG, TIFF, WebP, or BMP)."
        )

    preprocess = preprocess_fundus(image_bgr, camera_hint=camera_hint)
    qc = assess_image_quality(image_bgr, preprocess)
    atrophy = detect_macular_atrophy(preprocess.analysis_bgr, preprocess.fovea_xy)
    inference = run_inference(image_bgr, preprocess)

    icdr_grade, icdr_label, confidence, grade_rationale = grade_icdr(inference.metrics)
    classifier = get_icdr_classifier()
    clf_result = classifier.predict(inference.metrics)
    if clf_result is not None:
        clf_grade, clf_conf = clf_result
        grade_rationale.append(
            f"ML classifier suggests grade {clf_grade} (confidence {clf_conf:.2f})."
        )
        if clf_conf >= 0.55 and not atrophy_likely_explains_dr_findings(atrophy, inference.metrics):
            icdr_grade = clf_grade
            icdr_label = ICDR_LABELS.get(clf_grade, icdr_label)
            confidence = clf_conf

    icdr_grade, icdr_label, confidence, grade_rationale = apply_atrophy_grading_context(
        icdr_grade, icdr_label, confidence, grade_rationale, atrophy, inference.metrics
    )

    dme_grade, dme_label, dme_rationale = grade_dme(inference.metrics)

    rationale = list(preprocess.notes) + grade_rationale + dme_rationale
    rationale.append(f"Inference backend: {inference.backend}")
    if not qc.passed:
        rationale.extend([f"QC warning: {w}" for w in qc.warnings])
        confidence = max(0.3, confidence - 0.15)

    display_bgr = preprocess.original_bgr
    overlay_b64 = _draw_overlays(display_bgr, inference.masks)
    composite = OverlayLayer(
        lesion_type="composite_overlay",
        color_rgb=[255, 255, 255],
        mask_png_base64=overlay_b64,
    )

    ico = ico_recommendation(
        icdr_grade, icdr_label, dme_grade, dme_label, resource_setting
    )
    aao = aao_recommendation(icdr_grade, icdr_label, dme_grade, dme_label)

    non_dr: NonDRPathologyFinding | None = None
    if atrophy.detected:
        non_dr = NonDRPathologyFinding(
            pathology_type="macular_atrophy",
            label="Suspected macular atrophy",
            detected=True,
            confidence=atrophy.confidence,
            central_area_pct=atrophy.central_area_pct,
            notes=atrophy.rationale,
        )
        macular_note = (
            "Suspected macular atrophy — evaluate with OCT/FAF. "
            "Macular exudates and DME assessment retained."
        )
        ico.notes.insert(0, macular_note)
        aao.clinical_pearls.insert(0, macular_note)

    camera_info = CameraInfo(
        vendor=preprocess.vendor.value,
        vendor_label=preprocess.vendor_label,
        field_of_view=_fov_label(preprocess.vendor),
        vendor_neutral=True,
        preprocessing_notes=preprocess.notes,
    )

    return AnalysisResult(
        study_id=study_id,
        model_version=inference.model_version,
        qc=qc,
        camera=camera_info,
        lesions=inference.metrics,
        icdr_grade=icdr_grade,
        icdr_label=icdr_label,
        icdr_confidence=round(confidence, 3),
        dme_grade=dme_grade,
        dme_label=dme_label,
        ico=ico,
        aao=aao,
        overlays=inference.overlays + [composite],
        grading_rationale=rationale,
        non_dr_pathology=non_dr,
    )
