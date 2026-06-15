"""Inference service tests."""

import cv2
import numpy as np

from ml.inference.service import run_inference


def test_run_inference_cv_backend():
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[:, :] = (20, 60, 20)
    cv2.circle(img, (200, 200), 5, (0, 0, 180), -1)
    result = run_inference(img)
    assert result.backend == "cv"
    assert len(result.metrics) == 4
    assert result.model_version
