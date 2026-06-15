"""Standardized label schema for IDRiD and DDR datasets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


class DatasetSource(str):
    IDRID = "idrid"
    DDR = "ddr"
    EYEPACS = "eyepacs"


class Split(str):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"


@dataclass
class FundusRecord:
    image_id: str
    image_path: Path
    source: str
    split: str
    icdr_grade: int | None = None
    dme_grade: int | None = None
    lesion_mask_paths: dict[str, Path] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


LESION_CLASSES = ["microaneurysms", "hemorrhages", "hard_exudates", "soft_exudates"]

# IDRiD mask folder → canonical class name
IDRID_MASK_MAP = {
    "MA": "microaneurysms",
    "HE": "hemorrhages",
    "EX": "hard_exudates",
    "SE": "soft_exudates",
}

# DDR lesion folder names
DDR_MASK_MAP = {
    "microaneurysms": "microaneurysms",
    "hemorrhages": "hemorrhages",
    "hard_exudates": "hard_exudates",
    "soft_exudates": "soft_exudates",
}
