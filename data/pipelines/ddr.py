"""DDR dataset ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from data.pipelines.schema import DDR_MASK_MAP, DatasetSource, FundusRecord, Split


def ingest_ddr(raw_dir: Path, output_dir: Path) -> list[FundusRecord]:
    """
    Expect DDR layout:
      raw_dir/train/DR_grading.csv + images/
      raw_dir/train/lesion_seg/{microaneurysms,hemorrhages,hard_exudates,soft_exudates}/
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[FundusRecord] = []

    for split_name in ("train", "valid", "test"):
        split_dir = raw_dir / split_name
        if not split_dir.exists():
            continue

        split = Split.TRAIN if split_name == "train" else Split.VAL if split_name == "valid" else Split.TEST
        images_src = split_dir / "images"
        if not images_src.exists():
            images_src = split_dir

        images_out = output_dir / split / "images"
        masks_out = output_dir / split / "masks"
        images_out.mkdir(parents=True, exist_ok=True)
        masks_out.mkdir(parents=True, exist_ok=True)

        grading_file = split_dir / "DR_grading.csv"
        grades: dict[str, int] = {}
        if grading_file.exists():
            for line in grading_file.read_text().strip().splitlines()[1:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    grades[parts[0].replace(".jpg", "").replace(".png", "")] = int(parts[1])

        for img_path in sorted(images_src.glob("*.jpg")) + sorted(images_src.glob("*.png")):
            image_id = img_path.stem
            dest_img = images_out / img_path.name
            if not dest_img.exists():
                shutil.copy2(img_path, dest_img)

            lesion_masks: dict[str, Path] = {}
            lesion_dir = split_dir / "lesion_seg"
            if lesion_dir.exists():
                for folder, canonical in DDR_MASK_MAP.items():
                    mask_src = lesion_dir / folder / f"{image_id}.png"
                    if not mask_src.exists():
                        mask_src = lesion_dir / folder / f"{image_id}.tif"
                    if mask_src.exists():
                        dest_mask = masks_out / f"{image_id}_{canonical}.png"
                        if not dest_mask.exists():
                            shutil.copy2(mask_src, dest_mask)
                        lesion_masks[canonical] = dest_mask

            records.append(
                FundusRecord(
                    image_id=image_id,
                    image_path=dest_img,
                    source=DatasetSource.DDR,
                    split=split,
                    icdr_grade=grades.get(image_id),
                    lesion_mask_paths=lesion_masks,
                    metadata={"split_folder": split_name},
                )
            )

    manifest = [
        {
            "image_id": r.image_id,
            "image_path": str(r.image_path),
            "source": r.source,
            "split": r.split,
            "icdr_grade": r.icdr_grade,
            "lesion_masks": {k: str(v) for k, v in r.lesion_mask_paths.items()},
        }
        for r in records
    ]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"DDR: ingested {len(records)} records → {output_dir}")
    return records


def main():
    parser = argparse.ArgumentParser(description="Ingest DDR dataset")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/ddr"))
    args = parser.parse_args()
    ingest_ddr(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
