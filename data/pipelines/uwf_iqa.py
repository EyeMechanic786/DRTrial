"""Open UWF IQA dataset (Optos 200Tx, 700 images) ingestion.

Figshare: https://doi.org/10.6084/m9.figshare.26936446
Folders: DR, AMD, RVO, PM, uveitis, RD, healthy
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from data.pipelines.schema import DatasetSource, FundusRecord, Split

DIAGNOSIS_FOLDERS = {
    "DR": {"diagnosis": "diabetic_retinopathy", "icdr_grade": 2},
    "AMD": {"diagnosis": "age_related_macular_degeneration"},
    "RVO": {"diagnosis": "retinal_vein_occlusion"},
    "PM": {"diagnosis": "pathological_myopia"},
    "uveitis": {"diagnosis": "uveitis"},
    "Uveitis": {"diagnosis": "uveitis"},
    "RD": {"diagnosis": "retinal_detachment"},
    "healthy": {"diagnosis": "healthy", "icdr_grade": 0},
    "Healthy": {"diagnosis": "healthy", "icdr_grade": 0},
}

NON_DR_FOLDERS = {"AMD", "healthy", "Healthy", "PM"}


def _load_ground_truth_xlsx(xlsx_path: Path) -> dict[str, dict]:
    try:
        import openpyxl
    except ImportError:
        print("openpyxl not installed; skipping Ground Truth.xlsx (pip install openpyxl)")
        return {}

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {}
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    id_idx = next((i for i, h in enumerate(header) if "id" in h or h == "image"), 0)
    overall_idx = next((i for i, h in enumerate(header) if "overall" in h), None)

    out: dict[str, dict] = {}
    for row in rows[1:]:
        if not row or row[id_idx] is None:
            continue
        image_id = str(row[id_idx]).strip().replace(".jpg", "")
        meta: dict = {}
        if overall_idx is not None and row[overall_idx] is not None:
            meta["image_quality"] = int(row[overall_idx])
        out[image_id] = meta
    return out


def ingest_uwf_iqa(
    raw_dir: Path,
    output_dir: Path,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    in_place: bool = False,
) -> list[FundusRecord]:
    """
    Expect extracted Figshare zip:
      raw_dir/Original UWF Images/{DR,AMD,...,healthy}/*.jpg
      raw_dir/Ground Truth.xlsx (optional)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    images_out = output_dir / "images"
    if not in_place:
        images_out.mkdir(exist_ok=True)

    images_root = raw_dir / "Original UWF Images"
    if not images_root.exists():
        images_root = raw_dir / "Original UWF Image"
    if not images_root.exists():
        images_root = raw_dir

    gt_path = raw_dir / "Ground Truth.xlsx"
    if not gt_path.exists():
        gt_path = raw_dir.parent / "Ground Truth.xlsx" if (raw_dir / "Original UWF Image").exists() else gt_path
    quality_map = _load_ground_truth_xlsx(gt_path) if gt_path.exists() else {}

    records: list[FundusRecord] = []
    all_images: list[tuple[Path, str, dict]] = []
    for folder_name, diag_meta in DIAGNOSIS_FOLDERS.items():
        folder = images_root / folder_name
        if not folder.exists():
            continue
        for img_path in sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png")):
            all_images.append((img_path, folder_name, diag_meta))

    n = len(all_images)
    for idx, (img_path, folder_name, diag_meta) in enumerate(all_images):
        image_id = img_path.stem
        dest = img_path if in_place else images_out / img_path.name
        if not in_place and not dest.exists():
            shutil.copy2(img_path, dest)

        if idx < int(n * test_ratio):
            split = Split.TEST
        elif idx < int(n * (test_ratio + val_ratio)):
            split = Split.VAL
        else:
            split = Split.TRAIN

        q_meta = quality_map.get(image_id, {})
        records.append(
            FundusRecord(
                image_id=image_id,
                image_path=dest,
                source=DatasetSource.UWF_IQA,
                split=split,
                icdr_grade=diag_meta.get("icdr_grade"),
                metadata={
                    "camera_vendor": "optos_uwf",
                    "diagnosis": diag_meta["diagnosis"],
                    "diagnosis_folder": folder_name,
                    "image_quality": q_meta.get("image_quality"),
                    "dataset": "uwf_iqa",
                    "non_dr_pathology": folder_name in NON_DR_FOLDERS,
                },
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
            "metadata": r.metadata,
        }
        for r in records
    ]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"UWF IQA: ingested {len(records)} Optos 200Tx records → {output_dir}")
    return records


def main():
    parser = argparse.ArgumentParser(description="Ingest Open UWF IQA Optos dataset")
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/uwf_iqa"))
    parser.add_argument("--in-place", action="store_true", help="Reference raw images without copying")
    args = parser.parse_args()
    ingest_uwf_iqa(args.raw_dir, args.output_dir, in_place=args.in_place)


if __name__ == "__main__":
    main()
