"""Build Optos UWF reference statistics from ingested open datasets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from ml.dr_pathway.macular_atrophy import detect_macular_atrophy
from ml.dr_pathway.pipeline import analyze_fundus_image
from ml.dr_pathway.preprocessing import preprocess_fundus


def build_reference(manifest_path: Path, output_path: Path, max_images: int = 200) -> dict:
    records = json.loads(manifest_path.read_text())
    all_optos = [
        r
        for r in records
        if r.get("metadata", {}).get("camera_vendor") == "optos_uwf"
        or r.get("source") in ("uwf4dr", "uwf_iqa", "prime_fp20")
    ]
    by_folder: dict[str, list[dict]] = {}
    for rec in all_optos:
        folder = rec.get("metadata", {}).get("diagnosis_folder", "unknown")
        by_folder.setdefault(folder, []).append(rec)

    per_folder = max(1, max_images // max(len(by_folder), 1))
    optos_records: list[dict] = []
    for items in by_folder.values():
        optos_records.extend(items[:per_folder])
    optos_records = optos_records[:max_images]

    focus_scores: list[float] = []
    brightness_vals: list[float] = []
    atrophy_on_amd_healthy = 0
    false_dr_on_non_dr = 0
    non_dr_count = 0
    datasets_used: set[str] = set()

    for rec in optos_records:
        img_path = Path(rec["image_path"])
        if not img_path.exists():
            continue
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        meta = rec.get("metadata", {})
        diagnosis_folder = meta.get("diagnosis_folder") or meta.get("diagnosis", "")

        datasets_used.add(meta.get("dataset", rec.get("source", "unknown")))
        preprocess = preprocess_fundus(img, camera_hint="optos_uwf")
        gray = cv2.cvtColor(preprocess.analysis_bgr, cv2.COLOR_BGR2GRAY)
        focus_scores.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        brightness_vals.append(float(np.mean(gray) / 255.0))

        if meta.get("non_dr_pathology") or diagnosis_folder in (
            "AMD",
            "Healthy",
            "healthy",
            "PM",
        ):
            non_dr_count += 1
            atrophy = detect_macular_atrophy(preprocess.analysis_bgr, preprocess.fovea_xy)
            if atrophy.detected:
                atrophy_on_amd_healthy += 1
            result = analyze_fundus_image(img_path.read_bytes(), rec["image_id"], camera_hint="optos_uwf")
            if result.icdr_grade > 0:
                false_dr_on_non_dr += 1

    stats = {
        "n_images": len(focus_scores),
        "datasets": sorted(datasets_used),
        "focus_score_median": round(float(np.median(focus_scores)), 2) if focus_scores else None,
        "focus_score_p10": round(float(np.percentile(focus_scores, 10)), 2) if focus_scores else None,
        "brightness_median": round(float(np.median(brightness_vals)), 3) if brightness_vals else None,
        "non_dr_cohort_size": non_dr_count,
        "atrophy_detection_rate_non_dr": round(atrophy_on_amd_healthy / non_dr_count, 3)
        if non_dr_count
        else None,
        "false_dr_rate_before_calibration": round(false_dr_on_non_dr / non_dr_count, 3)
        if non_dr_count
        else None,
        "recommended_focus_min": 35,
        "notes": [
            "Built from open Optos UWF datasets (UWF4DR, UWF IQA, PRIME-FP20).",
            "Use for QC threshold cross-check and validation reporting.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    return stats


def main():
    parser = argparse.ArgumentParser(description="Build Optos reference stats from manifests")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/optos_reference/stats.json"),
    )
    parser.add_argument("--max-images", type=int, default=200)
    args = parser.parse_args()
    build_reference(args.manifest, args.output, args.max_images)


if __name__ == "__main__":
    main()
