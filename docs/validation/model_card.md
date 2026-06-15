# DRTrial Model Card

**Version:** drtrial-1.1.0  
**Date:** 2026-06-15  
**Type:** Clinical decision support (not autonomous diagnostic)

## Model description

DRTrial performs multi-lesion detection and ICDR severity grading from colour fundus photographs, with ICO and AAO-aligned referral recommendations.

| Component | Backend | Description |
|-----------|---------|-------------|
| Lesion segmentation | OpenCV CV (default) / fundus-lesions-toolkit (optional) | MA, HE, EX, CWS |
| ICDR grading | Rule-based + GradientBoosting on lesion features | ICO/AAO 5-level scale |
| DME flag | Heuristic | Hard exudate macula proximity |

## Intended use

- **Users:** Ophthalmologists, retinal specialists
- **Input:** Macula-centered colour fundus JPEG/PNG
- **Output:** Lesion overlays, counts, ICDR grade, DME suspect flag, ICO/AAO referral guidance
- **Not for:** Autonomous screening without clinician review

## Training data

| Dataset | Purpose | License |
|---------|---------|---------|
| IDRiD | Segmentation benchmark, grading | CC BY 4.0 |
| DDR | Fine-tuning, grading | CC BY 4.0 |
| Synthetic bootstrap | ICDR classifier cold-start | Internal |

Ingest with:
```bash
python -m data.pipelines.idrid --raw-dir /path/to/idrid --output-dir data/processed/idrid
python -m data.pipelines.ddr --raw-dir /path/to/ddr --output-dir data/processed/ddr
```

## Performance targets (internal)

| Metric | Target | Notes |
|--------|--------|-------|
| MA Dice | > 0.30 | Inherently difficult |
| HE/EX Dice | > 0.50 | CV baseline lower than DL |
| ICDR κ | > 0.80 | vs ophthalmologist labels |
| P95 latency | < 30s | CPU acceptable for CDS |

Run benchmark:
```bash
python -m ml.evaluation.benchmark --manifest data/processed/idrid/manifest.json
```

## Limitations

- PDR detection limited without neovascularization model
- DME is suspect-only; OCT required for confirmation
- Domain shift across camera types not fully characterized
- IRMA and venous beading not assessed in v1.1

## Ethical considerations

Clinician sign-off required. Audit trail logs all analyses and overrides.

## Version history

| Version | Changes |
|---------|---------|
| drtrial-cv-1.0.0 | Initial CV pipeline |
| drtrial-1.1.0 | Inference service, ICDR classifier, async API, React UI |
