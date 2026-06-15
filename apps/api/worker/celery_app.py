"""Celery application and inference tasks."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from celery import Celery

from apps.api.config import settings

celery_app = Celery(
    "drtrial",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)


@celery_app.task(bind=True, name="analyze_study")
def analyze_study_task(
    self,
    study_id: str,
    image_path: str,
    resource_setting: str = "high",
    camera_hint: str = "auto",
):
    """Run ML pipeline asynchronously and persist results."""
    from apps.api.db.database import SessionLocal
    from apps.api.db.models import AnalysisRecord, JobRecord
    from apps.api.services.audit import log_action
    from ml.dr_pathway.pipeline import analyze_fundus_image

    db = SessionLocal()
    job = db.query(JobRecord).filter(JobRecord.celery_task_id == self.request.id).first()

    try:
        if job:
            job.status = "running"
            db.commit()

        image_bytes = Path(image_path).read_bytes()
        result = analyze_fundus_image(image_bytes, study_id, resource_setting, camera_hint)
        result_dict = result.model_dump()

        record = AnalysisRecord(
            study_id=study_id,
            job_id=job.id if job else None,
            model_version=result.model_version,
            result_json=result_dict,
        )
        db.add(record)

        from apps.api.db.models import Study

        study = db.query(Study).filter(Study.id == study_id).first()
        if study:
            study.status = "analyzed"
            study.updated_at = datetime.utcnow()

        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()

        log_action(
            db,
            action="analysis_completed",
            study_id=study_id,
            detail={"model_version": result.model_version, "icdr_grade": result.icdr_grade},
        )
        db.commit()
        return result_dict
    except Exception as exc:
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.completed_at = datetime.utcnow()
            db.commit()
        log_action(db, action="analysis_failed", study_id=study_id, detail={"error": str(exc)})
        raise
    finally:
        db.close()
