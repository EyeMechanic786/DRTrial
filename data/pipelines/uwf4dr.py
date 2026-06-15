"""UWF4DR (MICCAI 2024) Optos UWF dataset ingestion.

Download from https://codalab.lisn.upsaclay.fr/competitions/18605 after registration.
Optional split CSVs from https://github.com/BiDAlab/UWF4DR-Benchmark (data/splits/).
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path

from data.pipelines.schema import DatasetSource, FundusRecord, Split


def _read_labels_csv(csv_path: Path) -> dict[str, dict]:
    """Parse label CSV; supports common UWF4DR column names."""
    labels: dict[str, dict] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return labels
        fields = {c.lower().strip(): c for c in reader.fieldnames}

        def col(*names: str) -> str | None:
            for n in names:
                if n in fields:
                    return fields[n]
            return None

        id_col = col("image", "image_id", "filename", "file", "id", "name")
        iq_col = col("quality", "image_quality", "iqa", "gradable", "task1")
        rdr_col = col("rdr", "referable_dr", "referable", "task2", "dr")
        dme_col = col("dme", "task3", "macular_edema")

        for row in reader:
            raw_id = row.get(id_col or "", "").strip()
            if not raw_id:
                continue
            image_id = Path(raw_id).stem
            entry: dict = {}
            if iq_col and row.get(iq_col, "") != "":
                entry["image_quality"] = int(float(row[iq_col]))
            if rdr_col and row.get(rdr_col, "") != "":
                entry["referable_dr"] = int(float(row[rdr_col]))
                entry["icdr_grade"] = 2 if entry["referable_dr"] else 0
            if dme_col and row.get(dme_col, "") != "":
                entry["dme_grade"] = int(float(row[dme_col]))
            labels[image_id] = entry
    return labels


def _resolve_split(image_id: str, split_map: dict[str, str] | None, default: str) -> str:
    if split_map and image_id in split_map:
        return split_map[image_id]
    return default


def ingest_uwf4dr(
    raw_dir: Path,
    output_dir: Path,
    labels_csv: Path | None = None,
    split_csv: Path | None = None,
    default_split: str = Split.TRAIN,
) -> list[FundusRecord]:
    """
    Ingest UWF4DR images. Supports layouts:
      raw_dir/images/*.jpg|png|tif
      raw_dir/train/*.jpg
      raw_dir/<split>/*.jpg
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_out = output_dir / "images"
    images_out.mkdir(exist_ok=True)

    if labels_csv is None:
        for candidate in (
            raw_dir / "labels.csv",
            raw_dir / "train_labels.csv",
            raw_dir / "GroundTruth.csv",
        ):
            if candidate.exists():
                labels_csv = candidate
                break

    label_map = _read_labels_csv(labels_csv) if labels_csv and labels_csv.exists() else {}

    split_map: dict[str, str] | None = None
    if split_csv and split_csv.exists():
        split_map = {}
        with split_csv.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            id_col = next(
                (c for c in (reader.fieldnames or []) if c.lower() in ("image", "image_id", "filename", "id")),
                None,
            )
            split_col = next(
                (c for c in (reader.fieldnames or []) if c.lower() in ("split", "partition", "set")),
                None,
            )
            for row in reader:
                if id_col and split_col:
                    split_map[Path(row[id_col]).stem] = row[split_col].lower()

    image_files: list[Path] = []
    for pattern in ("**/*.jpg", "**/*.jpeg", "**/*.png", "**/*.tif", "**/*.tiff"):
        image_files.extend(raw_dir.glob(pattern))
    image_files = sorted({p.resolve() for p in image_files if "mask" not in p.name.lower()})

    records: list[FundusRecord] = []
    for img_path in image_files:
        image_id = img_path.stem
        dest = images_out / f"{image_id}{img_path.suffix.lower()}"
        if not dest.exists():
            shutil.copy2(img_path, dest)

        meta = label_map.get(image_id, {})
        split = _resolve_split(image_id, split_map, default_split)
        if split not in (Split.TRAIN, Split.VAL, Split.TEST):
            split = Split.TRAIN

        records.append(
            FundusRecord(
                image_id=image_id,
                image_path=dest,
                source=DatasetSource.UWF4DR,
                split=split,
                icdr_grade=meta.get("icdr_grade"),
                dme_grade=meta.get("dme_grade"),
                metadata={
                    "camera_vendor": "optos_uwf",
                    "referable_dr": meta.get("referable_dr"),
                    "image_quality": meta.get("image_quality"),
                    "dataset": "uwf4dr",
                },
            )
        )

    manifest = [_record_to_dict(r) for r in records]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"UWF4DR: ingested {len(records)} Optos UWF records → {output_dir}")
    return records


def _record_to_dict(r: FundusRecord) -> dict:
    return {
        "image_id": r.image_id,
        "image_path": str(r.image_path),
        "source": r.source,
        "split": r.split,
        "icdr_grade": r.icdr_grade,
        "dme_grade": r.dme_grade,
        "metadata": r.metadata,
    }


def main():
    parser = argparse.ArgumentParser(description="Ingest UWF4DR Optos UWF dataset")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/uwf4dr"))
    parser.add_argument("--labels-csv", type=Path, default=None)
    parser.add_argument("--split-csv", type=Path, default=None, help="BiDA UWF4DR-Benchmark split CSV")
    parser.add_argument("--default-split", default=Split.TRAIN)
    args = parser.parse_args()
    ingest_uwf4dr(args.raw_dir, args.output_dir, args.labels_csv, args.split_csv, args.default_split)


if __name__ == "__main__":
    main()
