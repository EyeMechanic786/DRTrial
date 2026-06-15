# Extract, ingest, build Optos reference stats, train classifier, benchmark
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$iqaZip = "data/raw/uwf_iqa/Dataset.zip"
$iqaDir = "data/raw/uwf_iqa/extracted"
if (Test-Path $iqaZip) {
    if (-not (Test-Path "$iqaDir/Original UWF Images")) {
        Write-Host "Extracting UWF IQA dataset..."
        New-Item -ItemType Directory -Force -Path $iqaDir | Out-Null
        Expand-Archive -Path $iqaZip -DestinationPath $iqaDir -Force
    }
    docker compose exec api python -m data.pipelines.uwf_iqa --raw-dir /app/data/raw/uwf_iqa/extracted --output-dir /app/data/processed/uwf_iqa
}

docker compose exec api python -m data.pipelines.merge_manifests /app/data/processed/uwf_iqa/manifest.json --output /app/data/processed/combined/manifest.json
docker compose exec api python -m data.pipelines.build_optos_reference --manifest /app/data/processed/combined/manifest.json --max-images 100
docker compose exec api python -m ml.training.train_icdr --manifest /app/data/processed/combined/manifest.json
docker compose exec api python -m ml.evaluation.benchmark --manifest /app/data/processed/uwf_iqa/manifest.json --output /app/docs/validation/optos_benchmark_report.json --max-seg 0

Write-Host "Optos finalization complete. Restart: docker compose up -d api worker"
