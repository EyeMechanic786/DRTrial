"""Study management routes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from apps.api.config import settings
from apps.api.db.database import get_db
from apps.api.db.models import AnalysisRecord, JobRecord, Study, StudyImage
from apps.api.schemas import StudyCreate, StudyResponse
from apps.api.services.audit import log_action
from apps.api.worker.celery_app import analyze_study_task

router = APIRouter(prefix="/studies", tags=["studies"])

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("", response_model=StudyResponse)
def create_study(payload: StudyCreate, db: Session = Depends(get_db)):
    study = Study(
        patient_ref=payload.patient_ref,
        eye=payload.eye,
        resource_setting=payload.resource_setting,
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    log_action(db, "study_created", study_id=study.id, detail={"patient_ref": payload.patient_ref})
    return study


@router.get("/{study_id}", response_model=StudyResponse)
def get_study(study_id: str, db: Session = Depends(get_db)):
    study = db.query(Study).filter(Study.id == study_id).first()
    if not study:
        raise HTTPException(404, "Study not found")
    return study


@router.post("/{study_id}/images")
async def upload_image(
    study_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    study = db.query(Study).filter(Study.id == study_id).first()
    if not study:
        raise HTTPException(404, "Study not found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Upload JPEG or PNG colour fundus image.")

    image_id = str(uuid.uuid4())
    ext = Path(file.filename or "fundus.jpg").suffix or ".jpg"
    storage_path = UPLOAD_DIR / f"{study_id}_{image_id}{ext}"
    content = await file.read()
    if len(content) < 1000:
        raise HTTPException(400, "Image file too small.")
    storage_path.write_bytes(content)

    image = StudyImage(
        id=image_id,
        study_id=study_id,
        filename=file.filename or f"fundus{ext}",
        storage_path=str(storage_path),
        content_type=file.content_type,
    )
    study.status = "uploaded"
    db.add(image)
    db.commit()
    log_action(db, "image_uploaded", study_id=study_id, detail={"image_id": image_id})
    return {"image_id": image_id, "filename": image.filename}


@router.post("/{study_id}/analyze", response_model=dict)
def analyze_study(study_id: str, db: Session = Depends(get_db)):
    study = db.query(Study).filter(Study.id == study_id).first()
    if not study:
        raise HTTPException(404, "Study not found")

    image = (
        db.query(StudyImage)
        .filter(StudyImage.study_id == study_id)
        .order_by(StudyImage.uploaded_at.desc())
        .first()
    )
    if not image:
        raise HTTPException(400, "No image uploaded for this study.")

    job = JobRecord(study_id=study_id, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    task = analyze_study_task.delay(study_id, image.storage_path, study.resource_setting)
    job.celery_task_id = task.id
    study.status = "analyzing"
    db.commit()
    log_action(db, "analysis_queued", study_id=study_id, detail={"job_id": job.id, "task_id": task.id})
    return {"job_id": job.id, "celery_task_id": task.id, "status": "queued"}


@router.get("/{study_id}/results")
def get_results(study_id: str, db: Session = Depends(get_db)):
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.study_id == study_id)
        .order_by(AnalysisRecord.created_at.desc())
        .first()
    )
    if not record:
        raise HTTPException(404, "No analysis results yet.")
    return record.result_json
