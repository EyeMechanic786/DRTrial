"""Tests for fundus image decode and upload validation."""

import cv2
import numpy as np

from ml.dr_pathway.image_io import decode_fundus_image, is_allowed_upload


def test_is_allowed_upload_extensions():
    assert is_allowed_upload("fundus.tif", None) is True
    assert is_allowed_upload("fundus.tiff", "application/octet-stream") is True
    assert is_allowed_upload("fundus.jpg", "image/jpeg") is True
    assert is_allowed_upload("report.pdf", "application/pdf") is False


def test_decode_jpeg():
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    img[:, :] = (40, 120, 50)
    _, buf = cv2.imencode(".jpg", img)
    decoded = decode_fundus_image(buf.tobytes())
    assert decoded is not None
    assert decoded.shape[0] == 64


def test_decode_png():
    img = np.zeros((32, 32, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    decoded = decode_fundus_image(buf.tobytes())
    assert decoded is not None
