"""Tests for Optos open dataset pipelines."""

import csv
import json
import tempfile
from pathlib import Path

from data.pipelines.optos_catalog import OPTOS_DATASETS, get_dataset
from data.pipelines.uwf4dr import _read_labels_csv, ingest_uwf4dr


def test_optos_catalog_has_uwf4dr():
    ds = get_dataset("uwf4dr")
    assert ds.camera.startswith("Optos")
    assert "uwf4dr" in ds.ingest_module
    assert len(OPTOS_DATASETS) >= 4


def test_uwf4dr_label_parser():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["image", "rdr", "dme", "quality"])
        writer.writeheader()
        writer.writerow({"image": "case001.jpg", "rdr": "1", "dme": "0", "quality": "1"})
        writer.writerow({"image": "case002.jpg", "rdr": "0", "dme": "0", "quality": "1"})
        path = Path(f.name)

    labels = _read_labels_csv(path)
    assert labels["case001"]["referable_dr"] == 1
    assert labels["case001"]["icdr_grade"] == 2
    assert labels["case002"]["icdr_grade"] == 0
    path.unlink()


def test_uwf4dr_ingest_minimal(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    import cv2
    import numpy as np

    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.imwrite(str(raw / "optos001.jpg"), img)

    labels = raw / "labels.csv"
    labels.write_text("image,rdr,dme\noptos001.jpg,0,0\n")

    out = tmp_path / "processed"
    records = ingest_uwf4dr(raw, out, labels)
    assert len(records) == 1
    assert records[0].metadata["camera_vendor"] == "optos_uwf"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest[0]["source"] == "uwf4dr"
