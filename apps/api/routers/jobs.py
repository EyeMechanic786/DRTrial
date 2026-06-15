"""Job polling and review routes."""

from __future__ import annotations

import json
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.api.db.database import get_db
from apps.api.db.models import AnalysisRecord, AuditLog, ClinicianReview, JobRecord, Study
from apps.api.schemas import AuditResponse, JobResponse, ReviewCreate, ReviewResponse
from apps.api.services.audit import log_action
from apps.api.worker.celery_app import celery_app

router = APIRouter(tags=["jobs", "review", "audit"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobRecord).filter(JobRecord.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.celery_task_id and job.status in ("pending", "running"):
        async_result = celery_app.AsyncResult(job.celery_task_id)
        if async_result.state == "SUCCESS" and job.status != "completed":
            job.status = "completed"
            db.commit()
        elif async_result.state == "FAILURE" and job.status != "failed":
            job.status = "failed"
            job.error = str(async_result.result)
            db.commit()
    return job


@router.patch("/studies/{study_id}/review", response_model=ReviewResponse)
def submit_review(study_id: str, payload: ReviewCreate, db: Session = Depends(get_db)):
    study = db.query(Study).filter(Study.id == study_id).first()
    if not study:
        raise HTTPException(404, "Study not found")

    review = ClinicianReview(
        study_id=study_id,
        reviewer=payload.reviewer,
        icdr_override=payload.icdr_override,
        dme_override=payload.dme_override,
        dismissed_lesions=payload.dismissed_lesions,
        notes=payload.notes,
        signed_off=payload.signed_off,
    )
    if payload.signed_off:
        study.status = "signed_off"
    else:
        study.status = "reviewed"
    db.add(review)
    db.commit()
    db.refresh(review)
    log_action(
        db,
        "clinician_review",
        study_id=study_id,
        actor=payload.reviewer,
        detail={
            "icdr_override": payload.icdr_override,
            "signed_off": payload.signed_off,
            "dismissed_count": len(payload.dismissed_lesions),
        },
    )
    return review


@router.get("/studies/{study_id}/audit", response_model=list[AuditResponse])
def get_audit(study_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.study_id == study_id)
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    return logs


@router.get("/studies/{study_id}/report")
def export_report(study_id: str, db: Session = Depends(get_db)):
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.study_id == study_id)
        .order_by(AnalysisRecord.created_at.desc())
        .first()
    )
    review = (
        db.query(ClinicianReview)
        .filter(ClinicianReview.study_id == study_id)
        .order_by(ClinicianReview.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(404, "No analysis to report.")

    report = {
        "study_id": study_id,
        "model_version": record.model_version,
        "analysis": record.result_json,
        "clinician_review": None,
        "disclaimer": record.result_json.get("disclaimer", ""),
    }
    if review:
        report["clinician_review"] = {
            "reviewer": review.reviewer,
            "icdr_override": review.icdr_override,
            "dme_override": review.dme_override,
            "notes": review.notes,
            "signed_off": review.signed_off,
            "dismissed_lesions": review.dismissed_lesions,
        }

    content = json.dumps(report, indent=2).encode()
    return StreamingResponse(
        BytesIO(content),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="drtrial-report-{study_id[:8]}.json"'},
    )
