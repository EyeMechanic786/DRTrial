"""ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Study(Base):
    __tablename__ = "studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eye: Mapped[str | None] = mapped_column(String(8), nullable=True)
    resource_setting: Mapped[str] = mapped_column(String(32), default="high")
    camera_hint: Mapped[str] = mapped_column(String(32), default="auto")
    status: Mapped[str] = mapped_column(String(32), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images: Mapped[list[StudyImage]] = relationship(back_populates="study", cascade="all, delete-orphan")
    results: Mapped[list[AnalysisRecord]] = relationship(back_populates="study", cascade="all, delete-orphan")
    reviews: Mapped[list[ClinicianReview]] = relationship(back_populates="study", cascade="all, delete-orphan")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="study", cascade="all, delete-orphan")


class StudyImage(Base):
    __tablename__ = "study_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"))
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    study: Mapped[Study] = relationship(back_populates="images")


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"))
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64))
    result_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    study: Mapped[Study] = relationship(back_populates="results")


class ClinicianReview(Base):
    __tablename__ = "clinician_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"))
    reviewer: Mapped[str] = mapped_column(String(128))
    icdr_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dme_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dismissed_lesions: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_off: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    study: Mapped[Study] = relationship(back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("studies.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    study: Mapped[Study | None] = relationship(back_populates="audit_logs")


class JobRecord(Base):
    __tablename__ = "job_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    study_id: Mapped[str] = mapped_column(String(36), ForeignKey("studies.id"))
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
