"""Inference service wrapping lesion detection with optional DL backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np

from ml.dr_pathway.lesion_detection import DetectionOutput, detect_lesions
from ml.dr_pathway.schemas import LesionMetrics, OverlayLayer
from ml.inference.model_registry import get_active_version

USE_DL = os.environ.get("USE_DL_MODELS", "false").lower() == "true"

LESION_INDEX_TO_TYPE = {
    0: "cotton_wool_spots",
    1: "hard_exudates",
    2: "hemorrhages",
    3: "microaneurysms",
}


@dataclass
class InferenceResult:
    metrics: list[LesionMetrics]
    overlays: list[OverlayLayer]
    masks: dict[str, np.ndarray]
    model_version: str
    backend: str


_dl_segment = None


def _load_dl_model():
    global _dl_segment
    if _dl_segment is not None:
        return _dl_segment
    try:
        from fundus_lesions_toolkit.models import segment as dl_segment

        _dl_segment = dl_segment
        return _dl_segment
    except ImportError:
        return None


def _dl_detect(image_bgr: np.ndarray) -> DetectionOutput | None:
    segment_fn = _load_dl_model()
    if segment_fn is None:
        return None

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pred = segment_fn(image_rgb, device="cpu", weights="ALL")

    h, w = image_bgr.shape[:2]
    masks: dict[str, np.ndarray] = {}
    metrics: list[LesionMetrics] = []
    overlays: list[OverlayLayer] = []

    from ml.dr_pathway.lesion_detection import (
        LESION_COLORS,
        _connected_components,
        _mask_to_overlay,
    )

    for idx, lesion_type in LESION_INDEX_TO_TYPE.items():
        if hasattr(pred, "shape") and len(pred.shape) == 3:
            mask = (pred[:, :, idx] > 0).astype(np.uint8) * 255
        else:
            continue
        masks[lesion_type] = mask
        metrics.append(_connected_components(mask, lesion_type, h, w))
        overlays.append(_mask_to_overlay(mask, lesion_type))

    return DetectionOutput(metrics=metrics, overlays=overlays, masks=masks)


def run_inference(image_bgr: np.ndarray) -> InferenceResult:
    version = get_active_version()
    backend = "cv"

    if USE_DL:
        dl_result = _dl_detect(image_bgr)
        if dl_result is not None:
            backend = "fundus-lesions-toolkit"
            return InferenceResult(
                metrics=dl_result.metrics,
                overlays=dl_result.overlays,
                masks=dl_result.masks,
                model_version=f"{version}-dl",
                backend=backend,
            )

    cv_result = detect_lesions(image_bgr)
    return InferenceResult(
        metrics=cv_result.metrics,
        overlays=cv_result.overlays,
        masks=cv_result.masks,
        model_version=version,
        backend=backend,
    )
