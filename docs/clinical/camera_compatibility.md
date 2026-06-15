# Camera compatibility — vendor-neutral DR analysis

DRTrial is **vendor-neutral**: it does not require a specific fundus camera. Images from any manufacturer can be uploaded as JPEG or PNG colour fundus photographs.

## Supported camera types

| Camera class | Examples | DRTrial handling |
|--------------|----------|------------------|
| Standard CFP | Topcon, Canon, Zeiss, Kowa | Direct analysis; macula at image center |
| Optos UWF | Daytona, California, Silverstone | ROI extraction removes letterbox; fovea estimated from optic disc |
| Confocal SLO | Heidelberg Spectralis, Eidon | Green-channel CLAHE normalization |
| Unknown | Any other JPEG/PNG fundus | Generic normalization applied |

## Optos ultra-widefield (UWF)

Optos **opto map** images are supported. Key differences from standard CFP:

- **200° field of view** — peripheral DR lesions are visible (advantage for screening)
- **Black letterbox borders** — automatically cropped before analysis
- **cSLO pseudocolour** — colour normalization applied; no Optos-specific SDK required
- **Macula position** — estimated relative to optic disc, not image center
- **Projection distortion** — peripheral lesion sizing is approximate; clinician review recommended

DRTrial does **not** replicate Optos's proprietary CE-marked AI product. It provides independent CDS analysis on exported Optos JPEG/PNG images.

### Optos compatibility checklist

| Requirement | Status |
|-------------|--------|
| Accept Optos JPEG/PNG export | Yes |
| Remove black letterbox / ROI crop | Yes |
| Wide aspect ratio QC (no false reject) | Yes |
| Peripheral lesion detection | Yes (with UWF caveat in report) |
| Explicit `camera_hint=optos_uwf` | Yes |
| Auto-detect Optos profile | Yes (heuristic) |
| DICOM from Optos PACS | Phase 2 |

## API usage

```http
POST /analyze?camera_hint=auto
POST /analyze?camera_hint=optos_uwf
POST /analyze?camera_hint=standard_cfp
```

When creating a study:

```json
POST /studies
{
  "patient_ref": "P001",
  "camera_hint": "optos_uwf"
}
```

## Camera hint values

| Value | Description |
|-------|-------------|
| `auto` | Detect camera profile from image (default) |
| `optos_uwf` | Force Optos / UWF preprocessing |
| `standard_cfp` | Force standard colour fundus pipeline |
| `confocal_slo` | Force confocal SLO normalization |

## Limitations

- Models are primarily validated on central-field CFP datasets (IDRiD, DDR). Optos UWF peripheral sensitivity may be lower until UWF-specific fine-tuning (e.g. UWF4DR dataset).
- No camera serial number or DICOM metadata coupling — intentionally vendor-neutral.
- For production Optos integration, export images as high-quality JPEG from **optomap** review software.

## References

- Optos UWF clinical validation literature (peripheral DR lesions)
- UWF4DR Challenge (MICCAI 2024) — Optos-acquired images
- ICO Guidelines — camera-agnostic DR grading standards
