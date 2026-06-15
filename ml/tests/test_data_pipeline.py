"""Data pipeline tests."""

import json
import tempfile
from pathlib import Path

from data.pipelines.schema import FundusRecord
from ml.dr_pathway.schemas import ICDR_LABELS


def test_fundus_record_schema():
    rec = FundusRecord(
        image_id="test_01",
        image_path=Path("data/test.jpg"),
        source="idrid",
        split="train",
        icdr_grade=1,
    )
    assert rec.icdr_grade == 1
    assert rec.source == "idrid"


def test_idrid_grading_parser():
    from data.pipelines.idrid import parse_idrid_grading

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("Image name;Retinopathy grade;Risk of macular edema\n")
        f.write("IDRiD_001.jpg;2;1\n")
        path = Path(f.name)

    grades = parse_idrid_grading(path)
    assert grades["IDRiD_001"]["icdr_grade"] == 2
    path.unlink()


def test_icdr_labels_complete():
    assert len(ICDR_LABELS) == 5
