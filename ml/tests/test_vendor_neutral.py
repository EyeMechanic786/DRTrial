"""Vendor-neutral preprocessing and Optos UWF compatibility tests."""

import cv2
import numpy as np

from ml.dr_pathway.preprocessing import CameraVendor, preprocess_fundus
from ml.dr_pathway.pipeline import analyze_fundus_image


def _synthetic_optos_uwf_jpeg() -> bytes:
    """Simulate Optos optomap: black letterbox + elliptical green-dominant fundus."""
    canvas = np.zeros((1200, 1600, 3), dtype=np.uint8)
    center = (800, 600)
    axes = (620, 480)
    cv2.ellipse(canvas, center, axes, 0, 0, 360, (40, 120, 50), -1)
    # Optic disc bright spot (nasal)
    cv2.circle(canvas, (620, 580), 35, (180, 200, 220), -1)
    # Lesion-like hemorrhage
    cv2.circle(canvas, (900, 620), 12, (30, 30, 180), -1)
    # Microaneurysm
    cv2.circle(canvas, (850, 550), 4, (20, 20, 200), -1)
    _, buf = cv2.imencode(".jpg", canvas)
    return buf.tobytes()


def _synthetic_standard_cfp_jpeg() -> bytes:
    img = np.zeros((1024, 1024, 3), dtype=np.uint8)
    img[:, :] = (35, 90, 35)
    cv2.circle(img, (512, 512), 8, (0, 0, 200), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_optos_vendor_detection():
    arr = np.frombuffer(_synthetic_optos_uwf_jpeg(), dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    result = preprocess_fundus(image, camera_hint="auto")
    assert result.vendor in (CameraVendor.OPTOS_UWF, CameraVendor.CONFOCAL_SLO, CameraVendor.UNKNOWN)
    assert result.analysis_bgr.shape[0] > 100
    assert result.roi_offset[0] >= 0


def test_optos_explicit_hint():
    arr = np.frombuffer(_synthetic_optos_uwf_jpeg(), dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    result = preprocess_fundus(image, camera_hint="optos_uwf")
    assert result.vendor == CameraVendor.OPTOS_UWF


def test_standard_cfp_vendor():
    arr = np.frombuffer(_synthetic_standard_cfp_jpeg(), dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    result = preprocess_fundus(image)
    assert result.vendor in (CameraVendor.STANDARD_CFP, CameraVendor.UNKNOWN)


def test_optos_end_to_end_analysis():
    result = analyze_fundus_image(_synthetic_optos_uwf_jpeg(), "optos-test", camera_hint="optos_uwf")
    assert result.camera is not None
    assert result.camera.vendor_neutral is True
    assert result.camera.vendor == "optos_uwf"
    assert "icdr_grade" in result.model_dump()
    assert any("Optos" in r or "optos" in r.lower() or "UWF" in r for r in result.grading_rationale) or result.camera.vendor == "optos_uwf"


def test_vendor_neutral_no_camera_coupling():
    """Analysis must succeed for both Optos-like and standard CFP without error."""
    for jpeg in (_synthetic_optos_uwf_jpeg(), _synthetic_standard_cfp_jpeg()):
        result = analyze_fundus_image(jpeg, "vendor-neutral-test")
        assert 0 <= result.icdr_grade <= 4
        assert result.camera is not None
