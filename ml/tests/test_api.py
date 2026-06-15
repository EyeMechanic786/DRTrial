"""API integration tests."""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

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


def test_study_workflow():
    create = client.post("/studies", json={"patient_ref": "P001", "eye": "OD"})
    assert create.status_code == 200
    study_id = create.json()["id"]

    upload = client.post(
        f"/studies/{study_id}/images",
        files={"file": ("fundus.jpg", _synthetic_fundus_jpeg(), "image/jpeg")},
    )
    assert upload.status_code == 200

    # Sync analyze via legacy endpoint for test without celery
    analyze = client.post(
        "/analyze",
        files={"file": ("fundus.jpg", _synthetic_fundus_jpeg(), "image/jpeg")},
    )
    assert analyze.status_code == 200


def test_review_endpoint():
    create = client.post("/studies", json={})
    study_id = create.json()["id"]

    review = client.patch(
        f"/studies/{study_id}/review",
        json={
            "reviewer": "Dr Test",
            "icdr_override": 2,
            "dismissed_lesions": [],
            "signed_off": True,
        },
    )
    assert review.status_code == 200
    assert review.json()["signed_off"] is True
