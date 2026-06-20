# Finalize Optos UWF validation pipeline
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== Rebuild API/worker with data volume mounts ==="
docker compose build api worker web
docker compose up -d api worker web

$extracted = "data/raw/uwf_iqa/extracted"
if (-not (Test-Path $extracted)) {
    Write-Host "Extracting UWF IQA..."
    Expand-Archive -Path data/raw/uwf_iqa/Dataset.zip -DestinationPath $extracted -Force
}

Write-Host "=== Ingest UWF IQA (in-place, no copy) ==="
docker compose exec api python -m data.pipelines.uwf_iqa `
  --raw-dir /app/data/raw/uwf_iqa/extracted `
  --output-dir /app/data/processed/uwf_iqa `
  --in-place

Write-Host "=== Merge manifest ==="
docker compose exec api python -m data.pipelines.merge_manifests `
  /app/data/processed/uwf_iqa/manifest.json `
  --output /app/data/processed/combined/manifest.json

Write-Host "=== Build Optos reference stats (sample 80 images) ==="
docker compose exec api python -m data.pipelines.build_optos_reference `
  --manifest /app/data/processed/combined/manifest.json `
  --max-images 80

Write-Host "=== Train ICDR classifier (120 samples) ==="
docker compose exec api python -m ml.training.train_icdr `
  --manifest /app/data/processed/combined/manifest.json `
  --max-samples 120

Write-Host "=== Benchmark: grading (100 images) + UWF cohorts (30 per folder) ==="
docker compose exec api python -m ml.evaluation.benchmark `
  --manifest /app/data/processed/uwf_iqa/manifest.json `
  --output /app/docs/validation/optos_benchmark_report.json `
  --max-seg 0 `
  --max-grading 100 `
  --uwf-cohorts `
  --max-per-cohort 30

Write-Host "=== Run tests ==="
docker compose exec api python -m pytest ml/tests/test_image_io.py ml/tests/test_macular_atrophy.py ml/tests/test_optos_pipelines.py ml/tests/test_vendor_neutral.py -v --tb=short

Write-Host "Done. Open http://localhost:5173 and upload Optos TIFF/JPG images."
