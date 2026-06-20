# DRTrial dataset status

Last updated: 2026-06-20

**Agent handoff:** read `AGENTS.md` and `docs/validation/batch_index.json` first.

## Downloaded locally

| Dataset | Location | Status |
|---------|----------|--------|
| Open UWF IQA (Optos 200Tx, 700 JPG) | `data/raw/uwf_iqa/` | Zip (8.4 GB) + extracted |
| UWF4DR-Benchmark splits | `data/raw/UWF4DR-Benchmark/` | CSV splits only (no images) |

## Validation strategy

| Source | Status |
|--------|--------|
| **UWF IQA (Figshare)** | **Primary** — ingested, batched benchmark in progress |
| UWF4DR images (CodaLab) | **Optional / blocked** — skip unless user regains access |

## Processed

| Artifact | Path | Status |
|----------|------|--------|
| UWF IQA manifest | `data/processed/uwf_iqa/manifest.json` | **700 records** |
| Combined manifest | `data/processed/combined/manifest.json` | Ready |
| Optos reference stats | `data/processed/optos_reference/stats.json` | Done — 77 images, 33 non-DR |
| Full cohort report | `docs/validation/optos_benchmark_report.json` | Done (small sample, 2026-06-20) |
| Batched reports | `docs/validation/optos_benchmark_batch*.json` | **Batches 1–3 done** (30 images) |

## Batched UWF IQA validation (10 images per run)

Progress: **`docs/validation/batch_index.json`** → next batch **4**, offset **30**.

Each batch ~7–10 minutes on Docker worker:

```powershell
docker compose exec worker python -m ml.evaluation.benchmark `
  --manifest /app/data/processed/uwf_iqa/manifest.json `
  --output /app/docs/validation/optos_benchmark_batch04.json `
  --max-seg 0 --max-grading 10 --grading-offset 30
```

After each batch: update `batch_index.json` (and commit reports if requested).

## Image formats

JPEG, PNG, TIFF, WebP, BMP — `ml/dr_pathway/image_io.py`

## App

http://localhost:5173 · http://localhost:8000

```powershell
docker compose up -d
docker compose up -d --build api worker   # after code changes
```

## Still manual (later phase)

- IDRiD / DDR for deep-learning fine-tuning
- PRIME-FP20: IEEE DataPort
- UWF4DR images: https://codalab.lisn.upsaclay.fr/competitions/18605 (optional)
- Clinical pilot: `docs/clinical/pilot_guide.md`
