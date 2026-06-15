# Open Optos / UWF datasets

DRTrial cross-references publicly available **Optos ultra-widefield (UWF)** datasets to validate preprocessing, reduce false positives (e.g. macular atrophy mimicking DR), and benchmark DR/DME performance on real Optos hardware.

The macular region is **never excluded** from lesion or DME analysis — open datasets help calibrate grading when atrophy and DR coexist.

## Catalog

| Dataset | Camera | Access | Images | DRTrial role |
|---------|--------|--------|--------|--------------|
| [UWF4DR](https://codalab.lisn.upsaclay.fr/competitions/18605) | Optos UWF | CodaLab registration | ~495 | DR, DME, image quality (MICCAI 2024) |
| [Open UWF IQA](https://doi.org/10.6084/m9.figshare.26936446) | Optos 200Tx | Figshare (open) | 700 | AMD/healthy negatives, QC, non-DR pathology |
| [PRIME-FP20](https://ieee-dataport.org/open-access/prime-fp20-ultra-widefield-fundus-photography-vessel-segmentation-dataset) | Optos 200Tx | IEEE DataPort (open) | 15 | Validity masks, letterbox ROI calibration |
| [UWF tumors](https://doi.org/10.6084/m9.figshare.27986258) | Optomap Daytona | Figshare (open) | 2,031 | Normal controls, non-DR stress tests |

Split definitions for UWF4DR reproducibility: [BiDAlab/UWF4DR-Benchmark](https://github.com/BiDAlab/UWF4DR-Benchmark).

## Ingestion workflow

1. Download datasets to `data/raw/` (see links above).

2. Ingest each source:

```bash
# UWF4DR (after CodaLab download)
python -m data.pipelines.uwf4dr --raw-dir data/raw/uwf4dr --output-dir data/processed/uwf4dr

# Optional: BiDA benchmark split CSVs
python -m data.pipelines.uwf4dr --raw-dir data/raw/uwf4dr --split-csv data/raw/UWF4DR-Benchmark/data/splits/task2_train.csv

# Open UWF IQA (Figshare 10.6084/m9.figshare.26936446)
python -m data.pipelines.uwf_iqa --raw-dir data/raw/uwf_iqa --output-dir data/processed/uwf_iqa

# PRIME-FP20 (IEEE DataPort)
python -m data.pipelines.prime_fp20 --raw-dir data/raw/prime_fp20 --output-dir data/processed/prime_fp20
```

3. Merge with existing CFP manifests:

```bash
python -m data.pipelines.merge_manifests \
  data/processed/idrid/manifest.json \
  data/processed/uwf4dr/manifest.json \
  data/processed/uwf_iqa/manifest.json \
  --output data/processed/combined/manifest.json
```

4. Build Optos reference statistics (QC calibration, validation report):

```bash
python -m data.pipelines.build_optos_reference \
  --manifest data/processed/combined/manifest.json \
  --output data/processed/optos_reference/stats.json
```

5. Train and benchmark with Optos-aware preprocessing:

```bash
python -m ml.training.train_icdr --manifest data/processed/combined/manifest.json
python -m ml.evaluation.benchmark --manifest data/processed/uwf4dr/manifest.json
```

## Runtime cross-reference

When `data/processed/optos_reference/stats.json` exists, Optos uploads include QC notes citing the open validation cohort (focus score medians from UWF4DR / UWF IQA).

## Clinical notes

- **UWF IQA `AMD` folder** — useful for macular atrophy / geographic atrophy patterns (non-DR) without masking the macula from exudate or DME detection.
- **UWF4DR** — binary referable DR and DME labels; map to ICDR grade 0 vs 2 for screening benchmarks.
- **PRIME-FP20** — small but high-quality validity masks; improves letterbox removal on Optos 200Tx exports.

## Licensing

Respect each dataset's terms. UWF4DR images cannot be redistributed; ingest locally only. UWF IQA is CC BY 4.0. UWF tumors dataset is CC BY-NC-ND 4.0.
