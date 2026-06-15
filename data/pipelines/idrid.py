"""IDRiD dataset ingestion pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from data.pipelines.schema import IDRID_MASK_MAP, DatasetSource, FundusRecord, Split

IDRID_GRADING_COLUMNS = {
    "Retinopathy grade": "icdr_grade",
    "Risk of macular edema": "dme_grade",
}


def parse_idrid_grading(csv_path: Path) -> dict[str, dict]:
    grades: dict[str, dict] = {}
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            image_id = row.get("Image name", "").replace(".jpg", "")
            grades[image_id] = {
                "icdr_grade": int(row.get("Retinopathy grade", 0)),
                "dme_grade": int(row.get("Risk of macular edema", 0)),
            }
    return grades


def ingest_idrid(
    raw_dir: Path,
    output_dir: Path,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> list[FundusRecord]:
    """
    Expect raw_dir layout from IEEE Dataport IDRiD:
      raw_dir/A. Segmentation/Original Images/...
      raw_dir/A. Segmentation/Ground truth/...
      raw_dir/B. Disease Grading/GroundTruth.csv
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    masks_dir = output_dir / "masks"
    images_dir.mkdir(exist_ok=True)
    masks_dir.mkdir(exist_ok=True)

    grading_csv = raw_dir / "B. Disease Grading" / "GroundTruth.csv"
    if not grading_csv.exists():
        grading_csv = raw_dir / "GroundTruth.csv"
    grades = parse_idrid_grading(grading_csv) if grading_csv.exists() else {}

    seg_img_dir = raw_dir / "A. Segmentation" / "Original Images"
    seg_mask_dir = raw_dir / "A. Segmentation" / "Ground truth"
    if not seg_img_dir.exists():
        seg_img_dir = raw_dir / "Original Images"
        seg_mask_dir = raw_dir / "Ground truth"

    records: list[FundusRecord] = []
    image_files = sorted(seg_img_dir.glob("*.jpg")) if seg_img_dir.exists() else []

    for i, img_path in enumerate(image_files):
        image_id = img_path.stem
        if i < int(len(image_files) * test_ratio):
            split = Split.TEST
        elif i < int(len(image_files) * (test_ratio + val_ratio)):
            split = Split.VAL
        else:
            split = Split.TRAIN

        dest_img = images_dir / f"{image_id}.jpg"
        if not dest_img.exists():
            shutil.copy2(img_path, dest_img)

        lesion_masks: dict[str, Path] = {}
        if seg_mask_dir.exists():
            for abbr, canonical in IDRID_MASK_MAP.items():
                mask_path = seg_mask_dir / f"{image_id}_{abbr}.tif"
                if mask_path.exists():
                    dest_mask = masks_dir / f"{image_id}_{canonical}.tif"
                    if not dest_mask.exists():
                        shutil.copy2(mask_path, dest_mask)
                    lesion_masks[canonical] = dest_mask

        g = grades.get(image_id, {})
        records.append(
            FundusRecord(
                image_id=image_id,
                image_path=dest_img,
                source=DatasetSource.IDRID,
                split=split,
                icdr_grade=g.get("icdr_grade"),
                dme_grade=g.get("dme_grade"),
                lesion_mask_paths=lesion_masks,
                metadata={"has_masks": bool(lesion_masks)},
            )
        )

    manifest = [
        {
            "image_id": r.image_id,
            "image_path": str(r.image_path),
            "source": r.source,
            "split": r.split,
            "icdr_grade": r.icdr_grade,
            "dme_grade": r.dme_grade,
            "lesion_masks": {k: str(v) for k, v in r.lesion_mask_paths.items()},
        }
        for r in records
    ]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"IDRiD: ingested {len(records)} records → {output_dir}")
    return records


def main():
    parser = argparse.ArgumentParser(description="Ingest IDRiD dataset")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/idrid"))
    args = parser.parse_args()
    ingest_idrid(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
