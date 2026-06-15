# DR Classification Standards — ICO & AAO

## ICDR / ICO Scale

The **International Clinical Diabetic Retinopathy (ICDR)** scale was developed through an international consensus workshop (AAO-led, 2001–2002) and is the standard used in **ICO Guidelines for Diabetic Eye Care**.

| ICDR Grade | Clinical definition |
|------------|---------------------|
| 0 | No apparent DR — no abnormalities |
| 1 | Mild NPDR — microaneurysms only |
| 2 | Moderate NPDR — more than mild but less than severe |
| 3 | Severe NPDR — 4-2-1 rule (≥20 HE/quadrant, venous beading in 2 quadrants, IRMA in 1 quadrant) |
| 4 | PDR — neovascularization or vitreous/preretinal hemorrhage |

## ICO Referral — High Resource (Table 2a)

| DR severity | Re-examination | Referral |
|-------------|----------------|----------|
| No DR / mild, no DME | 12 months | Not required |
| Moderate NPDR | 3–6 months | Required |
| Severe NPDR | < 3 months | Required |
| PDR | < 1 month | Required |
| Non-center DME | 3 months | Required |
| Center-involving DME | 1 month | Required |

## AAO Preferred Practice Pattern

AAO DR PPP aligns with ICO intervals for screening and referral. DRTrial outputs:

- `referral_to_ophthalmologist` — boolean
- `re_examination_interval` — recommended months
- `clinical_pearls` — contextual guidance

## DME

True DME diagnosis requires OCT. DRTrial uses hard exudate proximity to the presumed fovea (image center) as a **suspect** flag only.

## DRTrial implementation

Phase 1 uses rule-based ICDR grading from CV-detected lesion counts and areas. Deep learning models (IDRiD/DDR-trained) are planned for improved sensitivity.
