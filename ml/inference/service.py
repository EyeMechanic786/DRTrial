"""Inference service wrapping lesion detection with optional DL backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np

from ml.dr_pathway.lesion_detection import DetectionOutput, detect_lesions
from ml.dr_pathway.preprocessing import PreprocessResult, map_bbox_to_original, map_mask_to_original
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
    preprocess: PreprocessResult | None = None


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


def _remap_overlays_to_original(
    overlays: list[OverlayLayer],
    masks: dict[str, np.ndarray],
    preprocess: PreprocessResult,
) -> tuple[list[OverlayLayer], dict[str, np.ndarray]]:
    remapped_overlays: list[OverlayLayer] = []
    remapped_masks: dict[str, np.ndarray] = {}

    for layer in overlays:
        remapped_overlays.append(
            OverlayLayer(
                lesion_type=layer.lesion_type,
                color_rgb=layer.color_rgb,
                bounding_boxes=[map_bbox_to_original(b, preprocess) for b in layer.bounding_boxes],
            )
        )

    for name, mask in masks.items():
        remapped_masks[name] = map_mask_to_original(mask, preprocess)

    return remapped_overlays, remapped_masks


def _dl_detect(
    image_bgr: np.ndarray,
    fovea_xy: tuple[float, float] | None,
) -> DetectionOutput | None:
    segment_fn = _load_dl_model()
    if segment_fn is None:
        return None

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pred = segment_fn(image_rgb, device="cpu", weights="ALL")

    h, w = image_bgr.shape[:2]
    masks: dict[str, np.ndarray] = {}
    metrics: list[LesionMetrics] = []
    overlays: list[OverlayLayer] = []

    from ml.dr_pathway.lesion_detection import _connected_components, _mask_to_overlay

    for idx, lesion_type in LESION_INDEX_TO_TYPE.items():
        if hasattr(pred, "shape") and len(pred.shape) == 3:
            mask = (pred[:, :, idx] > 0).astype(np.uint8) * 255
        else:
            continue
        masks[lesion_type] = mask
        metrics.append(_connected_components(mask, lesion_type, h, w, fovea_xy))
        overlays.append(_mask_to_overlay(mask, lesion_type))

    return DetectionOutput(metrics=metrics, overlays=overlays, masks=masks)


def run_inference(
    image_bgr: np.ndarray,
    preprocess: PreprocessResult | None = None,
) -> InferenceResult:
    version = get_active_version()
    backend = "cv"

    analysis_img = preprocess.analysis_bgr if preprocess else image_bgr
    fovea_xy = preprocess.fovea_xy if preprocess else None

    if USE_DL:
        dl_result = _dl_detect(analysis_img, fovea_xy)
        if dl_result is not None:
            backend = "fundus-lesions-toolkit"
            overlays, masks = dl_result.overlays, dl_result.masks
            if preprocess:
                overlays, masks = _remap_overlays_to_original(overlays, masks, preprocess)
            return InferenceResult(
                metrics=dl_result.metrics,
                overlays=overlays,
                masks=masks,
                model_version=f"{version}-dl",
                backend=backend,
                preprocess=preprocess,
            )

    cv_result = detect_lesions(analysis_img, fovea_xy)
    overlays, masks = cv_result.overlays, cv_result.masks
    if preprocess:
        overlays, masks = _remap_overlays_to_original(overlays, masks, preprocess)

    return InferenceResult(
        metrics=cv_result.metrics,
        overlays=overlays,
        masks=masks,
        model_version=version,
        backend=backend,
        preprocess=preprocess,
    )
