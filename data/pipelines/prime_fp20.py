"""PRIME-FP20 Optos 200Tx ingestion — validity masks for ROI calibration."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from data.pipelines.schema import DatasetSource, FundusRecord, Split


def ingest_prime_fp20(raw_dir: Path, output_dir: Path) -> list[FundusRecord]:
    """
    Expect IEEE DataPort zip contents with paired:
      *UWF*FP*.tif / *.tiff  — fundus
      *validity* / *mask*     — valid region mask
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_out = output_dir / "images"
    masks_out = output_dir / "validity_masks"
    images_out.mkdir(exist_ok=True)
    masks_out.mkdir(exist_ok=True)

    fundus_files = sorted(
        p for p in raw_dir.rglob("*") if p.suffix.lower() in (".tif", ".tiff") and p.is_file()
    )

    records: list[FundusRecord] = []
    for img_path in fundus_files:
        name_lower = img_path.name.lower()
        if any(k in name_lower for k in ("vessel", "validity", "mask", "fa", "angiography")):
            continue

        image_id = img_path.stem
        dest_img = images_out / f"{image_id}.tif"
        if not dest_img.exists():
            shutil.copy2(img_path, dest_img)

        validity_mask: Path | None = None
        for candidate in raw_dir.rglob("*"):
            if candidate.suffix.lower() not in (".tif", ".tiff"):
                continue
            cl = candidate.name.lower()
            if image_id.lower() in cl and any(k in cl for k in ("valid", "mask", "roi")):
                dest_mask = masks_out / f"{image_id}_validity.tif"
                if not dest_mask.exists():
                    shutil.copy2(candidate, dest_mask)
                validity_mask = dest_mask
                break

        meta = {"camera_vendor": "optos_uwf", "dataset": "prime_fp20", "resolution": "4000x4000"}
        if validity_mask:
            meta["validity_mask"] = str(validity_mask)

        records.append(
            FundusRecord(
                image_id=image_id,
                image_path=dest_img,
                source=DatasetSource.PRIME_FP20,
                split=Split.TEST,
                metadata=meta,
            )
        )

    manifest = [
        {
            "image_id": r.image_id,
            "image_path": str(r.image_path),
            "source": r.source,
            "split": r.split,
            "metadata": r.metadata,
        }
        for r in records
    ]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"PRIME-FP20: ingested {len(records)} Optos records → {output_dir}")
    return records


def main():
    parser = argparse.ArgumentParser(description="Ingest PRIME-FP20 Optos UWF dataset")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/prime_fp20"))
    args = parser.parse_args()
    ingest_prime_fp20(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
