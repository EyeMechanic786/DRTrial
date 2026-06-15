# DRTrial

**DRTrial** is a clinical decision support platform for automated diabetic retinopathy (DR) lesion detection from colour fundus photographs, with **ICO** and **AAO**-aligned severity classification and referral guidance.

> **Disclaimer:** Investigational CDS — not for autonomous diagnosis.

**Repository:** https://github.com/EyeMechanic786/DRTrial

## Architecture

```
Browser (React) → FastAPI → Celery Worker → ML Pipeline → PostgreSQL + Redis
```

| Component | Technology |
|-----------|------------|
| Frontend | React + TypeScript + Vite |
| API | FastAPI + SQLAlchemy |
| Jobs | Celery + Redis |
| Database | PostgreSQL |
| ML | OpenCV CV + optional fundus-lesions-toolkit + sklearn ICDR classifier |

## Features

- Multi-lesion detection (MA, hemorrhages, hard exudates, cotton wool spots)
- ICDR grading (ICO international scale, grades 0–4)
- DME suspect flag from macula proximity heuristic
- ICO referral/follow-up and AAO PPP intervals
- Explainable overlays with layer toggles and false-positive dismiss
- Clinician grade override and PDF report export
- Async study workflow with audit trail

## Quick start

### Docker (full stack)

```bash
docker compose up --build
```

- API: http://localhost:8000
- Web UI: http://localhost:5173

### Local development

```bash
# Terminal 1 — API
pip install -r requirements.txt
set PYTHONPATH=.
python -m apps.api.db.init_db
uvicorn apps.api.main:app --reload --port 8000

# Terminal 2 — Celery worker
celery -A apps.api.worker.celery_app worker --loglevel=info

# Terminal 3 — React frontend
cd apps/web && npm install && npm run dev
```

Train ICDR classifier (bootstrap):
```bash
python -m ml.training.train_icdr
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/studies` | Create study |
| POST | `/studies/{id}/images` | Upload fundus image |
| POST | `/studies/{id}/analyze` | Queue async analysis |
| GET | `/jobs/{id}` | Poll job status |
| GET | `/studies/{id}/results` | Get analysis JSON |
| PATCH | `/studies/{id}/review` | Clinician override + sign-off |
| GET | `/studies/{id}/audit` | Audit log |
| GET | `/studies/{id}/report` | Export JSON report |
| POST | `/analyze` | Sync analyze (dev/testing) |

## Data pipelines

```bash
python -m data.pipelines.idrid --raw-dir /path/to/idrid --output-dir data/processed/idrid
python -m data.pipelines.ddr --raw-dir /path/to/ddr --output-dir data/processed/ddr
python -m ml.training.train_icdr --manifest data/processed/ddr/manifest.json
python -m ml.evaluation.benchmark --manifest data/processed/idrid/manifest.json
```

## Documentation

- [Classification standards](docs/classifications.md)
- [Model card](docs/validation/model_card.md)
- [Pilot guide](docs/clinical/pilot_guide.md)

## License

MIT
