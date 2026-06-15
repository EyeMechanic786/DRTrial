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


def evaluate_grading(manifest_path: Path) -> dict:
    records = json.loads(manifest_path.read_text())
    y_true, y_pred = [], []
    latencies = []

    for rec in records:
        if rec.get("icdr_grade") is None:
            continue
        img_path = Path(rec["image_path"])
        if not img_path.exists():
            continue
        image_bytes = img_path.read_bytes()
        t0 = time.perf_counter()
        result = analyze_fundus_image(image_bytes, rec["image_id"])
        latencies.append(time.perf_counter() - t0)
        y_true.append(int(rec["icdr_grade"]))
        y_pred.append(int(result.icdr_grade))

    if not y_true:
        return {"kappa": None, "n": 0, "latency_p95_ms": None}

    kappa = cohen_kappa_score(y_true, y_pred, weights="quadratic")
    p95 = float(np.percentile(latencies, 95)) * 1000
    return {
        "kappa": round(kappa, 4),
        "n": len(y_true),
        "latency_mean_ms": round(float(np.mean(latencies)) * 1000, 1),
        "latency_p95_ms": round(p95, 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/validation/benchmark_report.json"))
    parser.add_argument("--max-seg", type=int, default=30)
    args = parser.parse_args()

    report = {
        "manifest": str(args.manifest),
        "segmentation": evaluate_segmentation(args.manifest, args.max_seg),
        "grading": evaluate_grading(args.manifest),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
