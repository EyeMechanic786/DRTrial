"""DRTrial API — clinical decision support for DR lesion detection."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from apps.api.routers import jobs, studies
from ml.dr_pathway.image_io import is_allowed_upload
from ml.dr_pathway.pipeline import analyze_fundus_image
from ml.dr_pathway.schemas import AnalysisResult

app = FastAPI(
    title="DRTrial",
    description="Clinical decision support for diabetic retinopathy lesion detection and ICO/AAO grading",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(studies.router)
app.include_router(jobs.router)

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def startup():
    try:
        from apps.api.db.init_db import init_db

        init_db()
    except Exception:
        pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "DRTrial", "version": "1.1.0"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_legacy(
    file: UploadFile = File(...),
    resource_setting: str = "high",
    camera_hint: str = "auto",
) -> AnalysisResult:
    """Legacy synchronous analyze endpoint for quick testing."""
    import uuid

    if not is_allowed_upload(file.filename, file.content_type):
        raise HTTPException(
            400,
            detail="Upload a colour fundus image (JPEG, PNG, TIFF, WebP, or BMP).",
        )

    study_id = str(uuid.uuid4())
    image_bytes = await file.read()
    if len(image_bytes) < 1000:
        raise HTTPException(400, detail="Image file too small.")

    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    (UPLOAD_DIR / f"{study_id}{ext}").write_bytes(image_bytes)

    try:
        return analyze_fundus_image(image_bytes, study_id, resource_setting, camera_hint)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
