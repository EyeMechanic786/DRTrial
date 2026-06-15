"""DRTrial API — colour fundus upload and DR analysis."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ml.dr_pathway.pipeline import analyze_fundus_image
from ml.dr_pathway.schemas import AnalysisResult

APP_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = APP_ROOT / "data" / "uploads"
WEB_DIR = APP_ROOT / "apps" / "web"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="DRTrial",
    description="Clinical decision support for diabetic retinopathy lesion detection and ICO/AAO grading",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "DRTrial"}


@app.get("/")
def index():
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "DRTrial API running. POST /analyze with fundus image."}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(
    file: UploadFile = File(...),
    resource_setting: str = "high",
) -> AnalysisResult:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload a JPEG or PNG colour fundus image.")

    study_id = str(uuid.uuid4())
    image_bytes = await file.read()
    if len(image_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Image file too small.")

    ext = Path(file.filename or "upload.jpg").suffix or ".jpg"
    (UPLOAD_DIR / f"{study_id}{ext}").write_bytes(image_bytes)

    try:
        return analyze_fundus_image(image_bytes, study_id, resource_setting)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
