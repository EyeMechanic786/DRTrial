@echo off
cd /d %~dp0..
pip install -r requirements.txt -q
set PYTHONPATH=.
python -m ml.training.train_icdr
python -m ml.evaluation.benchmark --manifest data/processed/synthetic/manifest.json --output docs/validation/benchmark_report.json 2>nul || echo Benchmark skipped - no sample images
pytest -q
echo Done.
