# Download open Optos UWF datasets into data/raw/
# UWF4DR and PRIME-FP20 require manual registration (see docs/clinical/optos_datasets.md)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

New-Item -ItemType Directory -Force -Path data/raw/uwf_iqa, data/raw/uwf_tumors, data/raw/prime_fp20 | Out-Null

Write-Host "=== UWF IQA (Optos 200Tx, 700 images, ~9 GB) ==="
$iqaZip = "data/raw/uwf_iqa/Dataset.zip"
if (-not (Test-Path $iqaZip) -or (Get-Item $iqaZip).Length -lt 8GB) {
    curl.exe -L -C - -o $iqaZip "https://ndownloader.figshare.com/files/49014559"
} else {
    Write-Host "UWF IQA zip already present."
}

Write-Host "=== UWF tumors (Optomap Daytona, ~2 GB, optional) ==="
$tumorRar = "data/raw/uwf_tumors/UWF_Fundus_Tumors.rar"
if (-not (Test-Path $tumorRar)) {
    Write-Host "Downloading tumors dataset (optional)..."
    curl.exe -L -C - -o $tumorRar "https://ndownloader.figshare.com/files/51055511"
}

Write-Host "=== UWF4DR-Benchmark splits (no images) ==="
if (-not (Test-Path data/raw/UWF4DR-Benchmark)) {
    git clone --depth 1 https://github.com/BiDAlab/UWF4DR-Benchmark.git data/raw/UWF4DR-Benchmark
}

Write-Host "Done. Run scripts/finalize-optos.ps1 after extraction."
