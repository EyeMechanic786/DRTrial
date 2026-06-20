# DRTrial dataset status

Last updated: 2026-06-20

## Downloaded locally

| Dataset | Location | Status |
|---------|----------|--------|
| Open UWF IQA (Optos 200Tx, 700 images) | `data/raw/uwf_iqa/` | Zip (8.4 GB) + extracted |
| UWF4DR-Benchmark splits | `data/raw/UWF4DR-Benchmark/` | CSV splits only (no images) |

## Processed

| Artifact | Path | Status |
|----------|------|--------|
| UWF IQA manifest | `data/processed/uwf_iqa/manifest.json` | **700 records ingested** |
| Combined manifest | `data/processed/combined/manifest.json` | Ready |
| Optos reference stats | `data/processed/optos_reference/stats.json` | **Done** — 77 images, 33 non-DR, ~30% false-DR pre-calibration |
| Benchmark report | `docs/validation/optos_benchmark_report.json` | **Done** (10 grading + 3/cohort, 2026-06-20) |

## Image formats accepted (after rebuild)

JPEG, PNG, TIFF, WebP, BMP — via `ml/dr_pathway/image_io.py`

## Batched UWF IQA validation (10 images per run)

Each batch takes ~8–12 minutes on Docker worker:

```powershell
# Batch 1 (images 1–10)
docker compose exec worker python -m ml.evaluation.benchmark `
  --manifest /app/data/processed/uwf_iqa/manifest.json `
  --output /app/docs/validation/optos_benchmark_batch01.json `
  --max-seg 0 --max-grading 10 --grading-offset 0

# Batch 2 (images 11–20): use --grading-offset 10, batch02.json, etc.
```

Reports accumulate under `docs/validation/optos_benchmark_batch*.json`.

```powershell
# Ensure Docker Desktop is running, then:
powershell -ExecutionPolicy Bypass -File scripts\finalize-optos.ps1
```

App: http://localhost:5173 · API: http://localhost:8000

## Still manual

- UWF4DR images: https://codalab.lisn.upsaclay.fr/competitions/18605
- IDRiD / DDR for deep-learning fine-tuning
- PRIME-FP20: IEEE DataPort (free account)
