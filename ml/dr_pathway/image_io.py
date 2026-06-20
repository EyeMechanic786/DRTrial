"""Decode colour fundus uploads — JPEG, PNG, TIFF, WebP, BMP."""

from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"})
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/x-tiff",
        "image/webp",
        "image/bmp",
    }
)


def is_allowed_upload(filename: str | None, content_type: str | None) -> bool:
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_EXTENSIONS:
            return True
    if content_type:
        if content_type in ALLOWED_CONTENT_TYPES:
            return True
        if content_type.startswith("image/"):
            return True
    return False


def decode_fundus_image(image_bytes: bytes) -> np.ndarray | None:
    """Return BGR image array or None if decode fails."""
    if not image_bytes:
        return None

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is not None:
        return bgr

    try:
        with Image.open(io.BytesIO(image_bytes)) as pil:
            rgb = pil.convert("RGB")
            return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    except Exception:
        return None
