# DRTrial dataset status

Last updated: 2026-06-15

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
| Optos reference stats | `data/processed/optos_reference/stats.json` | Initial run (rebuild after code update) |
| Benchmark report | `docs/validation/optos_benchmark_report.json` | Run `scripts/finalize-optos.ps1` |

## Image formats accepted (after rebuild)

JPEG, PNG, TIFF, WebP, BMP — via `ml/dr_pathway/image_io.py`

## Finish setup

```powershell
# Ensure Docker Desktop is running, then:
powershell -ExecutionPolicy Bypass -File scripts\finalize-optos.ps1
```

App: http://localhost:5173 · API: http://localhost:8000

## Still manual

- UWF4DR images: https://codalab.lisn.upsaclay.fr/competitions/18605
- IDRiD / DDR for deep-learning fine-tuning
- PRIME-FP20: IEEE DataPort (free account)
