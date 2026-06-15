"""API integration tests."""

from fastapi.testclient import TestClient
import cv2
import numpy as np

from apps.api.main import app

client = TestClient(app)


def _synthetic_fundus_jpeg() -> bytes:
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    img[:, :] = (30, 80, 30)
    cv2.circle(img, (256, 256), 8, (0, 0, 200), -1)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "DRTrial"


def test_analyze_fundus():
    res = client.post(
        "/analyze",
        files={"file": ("fundus.jpg", _synthetic_fundus_jpeg(), "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert "icdr_grade" in data
    assert "ico" in data
    assert "aao" in data
    assert data["model_version"].startswith("drtrial")
