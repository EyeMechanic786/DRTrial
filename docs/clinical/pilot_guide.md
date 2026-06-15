# Ophthalmologist Pilot Guide

## Purpose

Validate DRTrial clinical decision support usability with 2–3 ophthalmologists over ~50 fundus images.

## Participants

- 2–3 licensed ophthalmologists or retinal specialists
- Optional: 1 grader for reference ICDR labels

## Image set

- 50 colour fundus images stratified by ICDR grade (10 per grade 0–4)
- Sources: IDRiD test split, DDR test split, or de-identified clinic images (with consent)
- Include 10 poor-quality images to test QC warnings

## Protocol

1. **Upload** — Create study, upload image, run analysis
2. **Review overlays** — Toggle MA, HE, EX, CWS layers; dismiss false positives
3. **Override grade** — Set ICDR/DME if AI disagrees; add notes
4. **Sign off** — Export JSON report
5. **Feedback** — Complete short survey (5 min)

## Success criteria

| Criterion | Target |
|-----------|--------|
| Workflow time (upload → sign-off) | < 3 minutes |
| Overlay interpretability (subjective ≥4/5) | ≥ 80% of images |
| ICDR within ±1 of clinician final grade | ≥ 85% |
| False positive dismiss UX rated usable | ≥ 4/5 |

## Survey questions

1. Were lesion overlays clinically interpretable? (1–5)
2. Was the grade override workflow intuitive? (1–5)
3. Were ICO/AAO recommendations appropriate? (1–5)
4. Would you use this in clinic with current accuracy? (Y/N + comments)
5. Top 3 improvements needed?

## UX features for pilot

- Toggleable lesion layers with opacity slider
- Click-to-dismiss false positive bounding boxes
- Mandatory grade confirmation before sign-off
- Prominent investigational CDS disclaimer

## Reporting

Aggregate results in `docs/validation/pilot_results_template.md` after pilot completion.
