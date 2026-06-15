"""Clinical schemas for DR lesion detection and grading."""

from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, Field


class ICDRGrade(IntEnum):
    """International Clinical Diabetic Retinopathy (ICDR) / ICO scale."""

    NO_DR = 0
    MILD_NPDR = 1
    MODERATE_NPDR = 2
    SEVERE_NPDR = 3
    PDR = 4


ICDR_LABELS: dict[int, str] = {
    0: "No apparent DR",
    1: "Mild nonproliferative DR",
    2: "Moderate nonproliferative DR",
    3: "Severe nonproliferative DR",
    4: "Proliferative DR",
}


class DMEGrade(IntEnum):
    """Diabetic macular edema severity (ICO / AAO aligned)."""

    NONE = 0
    NON_CENTER_INVOLVING = 1
    CENTER_INVOLVING_SUSPECT = 2


DME_LABELS: dict[int, str] = {
    0: "No apparent DME",
    1: "Non-center-involving DME (suspect)",
    2: "Center-involving DME (suspect)",
}


class LesionMetrics(BaseModel):
    lesion_type: str
    count: int = 0
    total_area_px: int = 0
    total_area_pct: float = Field(0.0, description="Percentage of fundus image area")
    max_component_area_px: int = 0
    macula_proximity_score: float = Field(
        0.0, description="0=far from center, 1=at presumed fovea"
    )


class ImageQC(BaseModel):
    passed: bool
    focus_score: float
    brightness: float
    warnings: list[str] = Field(default_factory=list)


class ICORecommendation(BaseModel):
    """ICO Guidelines for Diabetic Eye Care — referral and follow-up."""

    icdr_grade: int
    icdr_label: str
    dme_grade: int
    dme_label: str
    referral_required: bool
    follow_up_months: str
    resource_setting: Literal["high", "low_intermediate"] = "high"
    notes: list[str] = Field(default_factory=list)


class AAORecommendation(BaseModel):
    """AAO Diabetic Retinopathy Preferred Practice Pattern aligned guidance."""

    icdr_grade: int
    icdr_label: str
    dme_grade: int
    dme_label: str
    referral_to_ophthalmologist: bool
    re_examination_interval: str
    ppp_reference: str = "AAO DR Preferred Practice Pattern (2024)"
    clinical_pearls: list[str] = Field(default_factory=list)


class OverlayLayer(BaseModel):
    lesion_type: str
    color_rgb: list[int]
    mask_png_base64: str | None = None
    bounding_boxes: list[dict] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    study_id: str
    model_version: str
    qc: ImageQC
    lesions: list[LesionMetrics]
    icdr_grade: int
    icdr_label: str
    icdr_confidence: float
    dme_grade: int
    dme_label: str
    ico: ICORecommendation
    aao: AAORecommendation
    overlays: list[OverlayLayer] = Field(default_factory=list)
    grading_rationale: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "AI-assisted clinical decision support only. "
        "Final diagnosis and management by a licensed ophthalmologist."
    )
