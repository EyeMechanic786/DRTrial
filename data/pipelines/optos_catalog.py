"""Registry of open-access Optos / UWF fundus datasets for DRTrial."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OptosDataset:
    key: str
    name: str
    camera: str
    access: str
    url: str
    doi: str | None
    images: int | None
    labels: list[str]
    drtrial_use: str
    ingest_module: str
    license_note: str


OPTOS_DATASETS: dict[str, OptosDataset] = {
    "uwf4dr": OptosDataset(
        key="uwf4dr",
        name="UWF4DR Challenge (MICCAI 2024)",
        camera="Optos (UWF)",
        access="Registration required (CodaLab)",
        url="https://codalab.lisn.upsaclay.fr/competitions/18605",
        doi="10.5281/zenodo.10992021",
        images=495,
        labels=["image_quality", "referable_dr", "dme"],
        drtrial_use="Primary Optos DR/DME validation and fine-tuning",
        ingest_module="data.pipelines.uwf4dr",
        license_note="Challenge terms; images not redistributable",
    ),
    "uwf_iqa": OptosDataset(
        key="uwf_iqa",
        name="Open UWF IQA (Zhejiang, Optos 200Tx)",
        camera="Optos 200Tx",
        access="Open (Figshare)",
        url="https://doi.org/10.6084/m9.figshare.26936446",
        doi="10.6084/m9.figshare.26936446",
        images=700,
        labels=["diagnosis", "image_quality", "demographics"],
        drtrial_use="AMD/atrophy negatives, QC thresholds, non-DR pathology",
        ingest_module="data.pipelines.uwf_iqa",
        license_note="CC BY 4.0 (Scientific Data 2024)",
    ),
    "prime_fp20": OptosDataset(
        key="prime_fp20",
        name="PRIME-FP20 vessel segmentation",
        camera="Optos 200Tx",
        access="Open (IEEE DataPort)",
        url="https://ieee-dataport.org/open-access/prime-fp20-ultra-widefield-fundus-photography-vessel-segmentation-dataset",
        doi=None,
        images=15,
        labels=["vessel_map", "validity_mask"],
        drtrial_use="Letterbox/ROI mask calibration for Optos preprocessing",
        ingest_module="data.pipelines.prime_fp20",
        license_note="Open access IEEE DataPort",
    ),
    "uwf_tumors": OptosDataset(
        key="uwf_tumors",
        name="UWF intraocular tumors (Optomap Daytona)",
        camera="Optos Daytona",
        access="Open (Figshare)",
        url="https://doi.org/10.6084/m9.figshare.27986258",
        doi="10.6084/m9.figshare.27986258",
        images=2031,
        labels=["tumor_category"],
        drtrial_use="Normal controls and non-DR pathology stress testing",
        ingest_module="data.pipelines.uwf_tumors",
        license_note="CC BY-NC-ND 4.0",
    ),
}


def list_datasets() -> list[OptosDataset]:
    return list(OPTOS_DATASETS.values())


def get_dataset(key: str) -> OptosDataset:
    if key not in OPTOS_DATASETS:
        raise KeyError(f"Unknown Optos dataset: {key}. Known: {list(OPTOS_DATASETS)}")
    return OPTOS_DATASETS[key]
