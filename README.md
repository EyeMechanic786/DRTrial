# DRTrial

**DRTrial** is a clinical decision support web application for automated diabetic retinopathy (DR) lesion detection from colour fundus photographs, with severity classification aligned to **ICO Guidelines for Diabetic Eye Care** and **AAO Diabetic Retinopathy Preferred Practice Pattern**.

> **Disclaimer:** Investigational CDS tool. Not for autonomous diagnosis. Final clinical decisions must be made by a licensed ophthalmologist.

## Features

- Upload colour fundus images (JPEG/PNG)
- Multi-lesion detection: microaneurysms, hemorrhages, hard exudates, cotton wool spots
- **ICDR** severity grading (ICO international classification, 0–4)
- **DME** suspect grading from hard exudate macula proximity
- **ICO** referral and follow-up recommendations (high / low-intermediate resource settings)
- **AAO** re-examination intervals and clinical pearls
- Explainable overlays with lesion bounding boxes

## Quick start

### Local development

```bash
cd DRTrial
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn apps.api.main:app --reload --port 8000
```

Open http://localhost:8000

### Docker

```bash
docker compose up --build
```

### Run tests

```bash
pip install -r requirements.txt
pytest
```

## Architecture

```
Upload → QC → Lesion detection → ICDR grade → DME grade → ICO + AAO recommendations
```

| Module | Path | Role |
|--------|------|------|
| Pipeline | `ml/dr_pathway/pipeline.py` | End-to-end analysis |
| Lesion detection | `ml/dr_pathway/lesion_detection.py` | CV-based lesion segmentation |
| Grading | `ml/dr_pathway/grading.py` | ICDR + ICO + AAO logic |
| DME | `ml/dr_pathway/dme.py` | Macular edema heuristic |
| API | `apps/api/main.py` | FastAPI REST + static UI |
| Web UI | `apps/web/` | Upload and results viewer |

## API

`POST /analyze` — multipart form with `file` (fundus image)

Query param: `resource_setting=high|low_intermediate`

Returns JSON with `icdr_grade`, `ico`, `aao`, `lesions`, `overlays`, `grading_rationale`.

## Classification standards

Both ICO and AAO adopt the **International Clinical Diabetic Retinopathy (ICDR)** five-level scale:

| Grade | Label |
|-------|-------|
| 0 | No apparent DR |
| 1 | Mild nonproliferative DR |
| 2 | Moderate nonproliferative DR |
| 3 | Severe nonproliferative DR |
| 4 | Proliferative DR |

See [docs/classifications.md](docs/classifications.md) for referral tables.

## Roadmap

- [ ] Deep learning integration (`fundus-lesions-toolkit`, DDR/IDRiD fine-tuning)
- [ ] Vessel segmentation for IRMA / venous beading
- [ ] DICOM / PACS integration
- [ ] Clinician review and sign-off workflow
- [ ] Regulatory pathway (FDA 21 CFR 886.1100)

## License

MIT — see [LICENSE](LICENSE).

## References

- ICO Guidelines for Diabetic Eye Care (2017/2018)
- AAO Diabetic Retinopathy Preferred Practice Pattern
- Porwal P. et al., IDRiD dataset, IEEE Dataport 2018
