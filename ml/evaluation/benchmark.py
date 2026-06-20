"""Benchmark evaluation: Dice, kappa, latency."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
from sklearn.metrics import cohen_kappa_score

from ml.dr_pathway.pipeline import analyze_fundus_image
from ml.inference.service import run_inference


def dice_score(pred: np.ndarray, gt: np.ndarray) -> float:
    pred_b = pred > 0
    gt_b = gt > 0
    intersection = np.logical_and(pred_b, gt_b).sum()
    total = pred_b.sum() + gt_b.sum()
    if total == 0:
        return 1.0
    return float(2.0 * intersection / total)


def evaluate_segmentation(manifest_path: Path, max_images: int = 50) -> dict:
    records = json.loads(manifest_path.read_text())
    results: dict[str, list[float]] = {
        "microaneurysms": [],
        "hemorrhages": [],
        "hard_exudates": [],
        "soft_exudates": [],
    }

    count = 0
    for rec in records:
        if count >= max_images:
            break
        masks = rec.get("lesion_masks", {})
        if not masks:
            continue
        img = cv2.imread(rec["image_path"])
        if img is None:
            continue
        meta = rec.get("metadata", {})
        if meta.get("camera_vendor") == "optos_uwf":
            from ml.dr_pathway.preprocessing import preprocess_fundus

            preprocess = preprocess_fundus(img, camera_hint="optos_uwf")
            inference = run_inference(img, preprocess)
        else:
            inference = run_inference(img)
        for lesion_type, mask_path in masks.items():
            gt = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if gt is None:
                continue
            gt = cv2.resize(gt, (img.shape[1], img.shape[0]))
            pred = inference.masks.get(lesion_type)
            if pred is None:
                pred = inference.masks.get(
                    lesion_type.replace("soft_exudates", "cotton_wool_spots")
                )
            if pred is None:
                continue
            key = lesion_type if lesion_type in results else "soft_exudates"
            results[key].append(dice_score(pred, gt))
        count += 1

    summary = {
        k: {"mean_dice": round(float(np.mean(v)), 4), "n": len(v)} if v else {"mean_dice": None, "n": 0}
        for k, v in results.items()
    }
    return summary


def evaluate_grading(
    manifest_path: Path,
    max_images: int | None = None,
    offset: int = 0,
) -> dict:
    records = json.loads(manifest_path.read_text())
    y_true, y_pred = [], []
    latencies = []
    skipped = 0

    for rec in records:
        if rec.get("icdr_grade") is None:
            continue
        img_path = Path(rec["image_path"])
        if not img_path.exists():
            continue
        if skipped < offset:
            skipped += 1
            continue
        if max_images is not None and len(y_true) >= max_images:
            break
        image_bytes = img_path.read_bytes()
        camera_hint = rec.get("metadata", {}).get("camera_vendor", "auto")
        t0 = time.perf_counter()
        result = analyze_fundus_image(image_bytes, rec["image_id"], camera_hint=camera_hint)
        latencies.append(time.perf_counter() - t0)
        y_true.append(int(rec["icdr_grade"]))
        y_pred.append(int(result.icdr_grade))

    if not y_true:
        return {
            "kappa": None,
            "n": 0,
            "offset": offset,
            "latency_mean_ms": None,
            "latency_p95_ms": None,
        }

    kappa = cohen_kappa_score(y_true, y_pred, weights="quadratic")
    p95 = float(np.percentile(latencies, 95)) * 1000
    return {
        "kappa": round(kappa, 4),
        "n": len(y_true),
        "offset": offset,
        "latency_mean_ms": round(float(np.mean(latencies)) * 1000, 1),
        "latency_p95_ms": round(p95, 1),
    }


def evaluate_uwf_cohorts(manifest_path: Path, max_per_cohort: int = 50) -> dict:
    """Benchmark DR grading on UWF IQA diagnosis folders (AMD vs DR vs Healthy)."""
    records = json.loads(manifest_path.read_text())
    cohorts: dict[str, list[dict]] = {}

    for rec in records:
        meta = rec.get("metadata", {})
        folder = meta.get("diagnosis_folder") or meta.get("diagnosis", "unknown")
        cohorts.setdefault(folder, []).append(rec)

    summary: dict[str, dict] = {}
    for folder, items in sorted(cohorts.items()):
        analyzed = 0
        false_dr = 0
        atrophy_detected = 0
        icdr_grades: list[int] = []

        for rec in items[:max_per_cohort]:
            img_path = Path(rec["image_path"])
            if not img_path.exists():
                continue
            result = analyze_fundus_image(
                img_path.read_bytes(),
                rec["image_id"],
                camera_hint="optos_uwf",
            )
            analyzed += 1
            icdr_grades.append(result.icdr_grade)
            if result.icdr_grade > 0:
                false_dr += 1
            if result.non_dr_pathology and result.non_dr_pathology.detected:
                atrophy_detected += 1

        expected_no_dr = folder in ("AMD", "Healthy", "healthy")
        summary[folder] = {
            "n_analyzed": analyzed,
            "mean_icdr_grade": round(float(np.mean(icdr_grades)), 2) if icdr_grades else None,
            "pct_icdr_gt0": round(100 * false_dr / analyzed, 1) if analyzed else None,
            "pct_atrophy_flagged": round(100 * atrophy_detected / analyzed, 1) if analyzed else None,
            "expected_no_dr_cohort": expected_no_dr,
        }

    non_dr_folders = [f for f, s in summary.items() if s.get("expected_no_dr_cohort")]
    non_dr_false = [
        summary[f]["pct_icdr_gt0"]
        for f in non_dr_folders
        if summary[f].get("pct_icdr_gt0") is not None
    ]
    return {
        "cohorts": summary,
        "non_dr_cohorts_mean_false_dr_pct": round(float(np.mean(non_dr_false)), 1)
        if non_dr_false
        else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/validation/benchmark_report.json"))
    parser.add_argument("--max-seg", type=int, default=30)
    parser.add_argument("--max-grading", type=int, default=None)
    parser.add_argument("--grading-offset", type=int, default=0, help="Skip N graded records before batch")
    parser.add_argument("--uwf-cohorts", action="store_true", help="Run UWF IQA cohort analysis")
    parser.add_argument("--max-per-cohort", type=int, default=50)
    args = parser.parse_args()

    report = {
        "manifest": str(args.manifest),
        "segmentation": evaluate_segmentation(args.manifest, args.max_seg),
        "grading": evaluate_grading(args.manifest, args.max_grading, args.grading_offset),
    }
    if args.uwf_cohorts:
        report["uwf_cohorts"] = evaluate_uwf_cohorts(args.manifest, args.max_per_cohort)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
