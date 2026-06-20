# DRTrial — agent briefing

Investigational CDS for diabetic retinopathy from colour fundus photos (ICO/AAO-aligned).  
**Repo:** https://github.com/EyeMechanic786/DRTrial · **Branch:** `master`

## Open this project as the workspace root

Path: `C:\Users\docra\Projects\DRTrial` (not glaucoma-drop-calendar).

## URLs (Docker)

- Web: http://localhost:5173
- API: http://localhost:8000

```powershell
docker compose up -d
docker compose up -d --build api worker   # after ML / API code changes
```

## Architecture

`React (apps/web)` → `FastAPI (apps/api)` → `Celery worker` → `ml/dr_pathway/` → PostgreSQL + Redis

Key ML entry: `ml/dr_pathway/pipeline.py` · Upload decode: `ml/dr_pathway/image_io.py`

## Docker volumes (host paths)

| Mount | Purpose |
|-------|---------|
| `data/raw/` | Downloaded datasets (gitignored, large) |
| `data/processed/` | Manifests, reference stats |
| `ml/weights/` | ICDR classifier |
| `docs/` | Validation reports (mounted — persist on host) |

**Source code is baked into images**, not bind-mounted. Rebuild `api`/`worker` after Python changes.

## Validation strategy (current)

- **Primary:** Open UWF IQA (Figshare, 700 JPG Optos images) — ingested.
- **UWF4DR (CodaLab):** optional / blocked — do not spend time on CodaLab download unless user regains access.
- **Batched grading:** 10 images per run (~7–10 min on worker). Progress: `docs/validation/batch_index.json`.

```powershell
docker compose exec worker python -m ml.evaluation.benchmark `
  --manifest /app/data/processed/uwf_iqa/manifest.json `
  --output /app/docs/validation/optos_benchmark_batch04.json `
  --max-seg 0 --max-grading 10 --grading-offset 30
```

Run long benchmarks on **worker**, not api (api startup retrains ICDR).

## Clinical constraints (do not regress)

1. **Macula stays in analysis** for exudates and DME — never exclude macula from lesion detection.
2. **Macular atrophy** (`ml/dr_pathway/macular_atrophy.py`) may downgrade false DR; it is not a macula mask.
3. Default pipeline is **classical CV** (`USE_DL_MODELS=false`).

## Handoff files (read these first)

| File | Use |
|------|-----|
| `data/DATASETS_STATUS.md` | Datasets, ingest state, batch commands |
| `docs/validation/batch_index.json` | Next batch number and offset |
| `docs/clinical/optos_datasets.md` | Optos dataset catalog and ingest |
| `docs/validation/model_card.md` | Model limitations |
| `data/processed/optos_reference/stats.json` | QC reference stats |

## Do not load into context

- `data/raw/**` (multi-GB zips/images)
- Full `manifest.json` files (700+ records) — use counts from `DATASETS_STATUS.md`
- Long Docker TIFF warning logs

## Git

- Never commit `data/raw/` or `data/processed/` (gitignored).
- Commit small validation JSON under `docs/validation/`.
- Only commit when the user asks.

## Common tasks

| Task | Command / file |
|------|----------------|
| Ingest UWF IQA | `python -m data.pipelines.uwf_iqa --raw-dir data/raw/uwf_iqa ...` |
| Merge manifests | `python -m data.pipelines.merge_manifests ...` |
| Optos reference stats | `python -m data.pipelines.build_optos_reference` |
| Train ICDR (stratified) | `python -m ml.training.train_icdr --manifest ... --max-samples N` |
| Tests | `pytest ml/tests/test_image_io.py ml/tests/test_macular_atrophy.py ml/tests/test_vendor_neutral.py ml/tests/test_optos_pipelines.py` |

## Known gaps

- PDR / severe NPDR 4-2-1 incomplete (no IRMA/NV)
- DME is heuristic; OCT required clinically
- Pilot not run (`docs/clinical/pilot_guide.md`)
- IDRiD/DDR ingest and `USE_DL_MODELS=true` not done
