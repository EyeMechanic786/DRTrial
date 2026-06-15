"""API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StudyCreate(BaseModel):
    patient_ref: str | None = None
    eye: str | None = Field(None, pattern="^(OD|OS|OU)?$")
    resource_setting: str = "high"
    camera_hint: str = Field(
        default="auto",
        description="Camera profile: auto, standard_cfp, optos_uwf, confocal_slo",
    )


class StudyResponse(BaseModel):
    id: str
    patient_ref: str | None
    eye: str | None
    resource_setting: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: str
    study_id: str
    celery_task_id: str | None
    status: str
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    reviewer: str
    icdr_override: int | None = Field(None, ge=0, le=4)
    dme_override: int | None = Field(None, ge=0, le=2)
    dismissed_lesions: list[dict] = Field(default_factory=list)
    notes: str | None = None
    signed_off: bool = False


class ReviewResponse(BaseModel):
    id: str
    study_id: str
    reviewer: str
    icdr_override: int | None
    dme_override: int | None
    dismissed_lesions: list
    notes: str | None
    signed_off: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    id: str
    study_id: str | None
    actor: str
    action: str
    detail: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
