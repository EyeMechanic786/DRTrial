@echo off
REM Ingest open Optos UWF datasets (place downloads under data\raw\)
echo DRTrial Optos dataset ingestion
echo See docs\clinical\optos_datasets.md for download links.

if exist data\raw\uwf4dr (
  python -m data.pipelines.uwf4dr --raw-dir data\raw\uwf4dr --output-dir data\processed\uwf4dr
) else (
  echo Skip UWF4DR - place data in data\raw\uwf4dr
)

if exist data\raw\uwf_iqa (
  python -m data.pipelines.uwf_iqa --raw-dir data\raw\uwf_iqa --output-dir data\processed\uwf_iqa
) else (
  echo Skip UWF IQA - place Figshare extract in data\raw\uwf_iqa
)

if exist data\raw\prime_fp20 (
  python -m data.pipelines.prime_fp20 --raw-dir data\raw\prime_fp20 --output-dir data\processed\prime_fp20
) else (
  echo Skip PRIME-FP20 - place IEEE DataPort extract in data\raw\prime_fp20
)

python -m data.pipelines.merge_manifests data/processed/uwf4dr/manifest.json data/processed/uwf_iqa/manifest.json --output data/processed/combined/manifest.json 2>nul
python -m data.pipelines.build_optos_reference --manifest data/processed/combined/manifest.json 2>nul
echo Done. Rebuild Docker to pick up reference stats: docker compose up --build -d api worker
