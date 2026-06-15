"""DME grading heuristic aligned with ICO / AAO guidelines."""

from __future__ import annotations

from ml.dr_pathway.schemas import DME_LABELS, DMEGrade, LesionMetrics


def grade_dme(lesions: list[LesionMetrics]) -> tuple[int, str, list[str]]:
    """Grade DME from hard exudate macula proximity (OCT confirmation required clinically)."""
    rationale: list[str] = []
    exudates = next((l for l in lesions if l.lesion_type == "hard_exudates"), None)

    if exudates is None or exudates.count == 0:
        rationale.append("No hard exudates detected; no DME signal from fundus photo.")
        return DMEGrade.NONE, DME_LABELS[0], rationale

    if exudates.macula_proximity_score >= 0.75:
        rationale.append(
            f"Hard exudates near presumed macula (proximity={exudates.macula_proximity_score})."
        )
        rationale.append("Center-involving DME cannot be confirmed without OCT.")
        return DMEGrade.CENTER_INVOLVING_SUSPECT, DME_LABELS[2], rationale

    if exudates.macula_proximity_score >= 0.45 or exudates.total_area_pct > 0.1:
        rationale.append(
            f"Hard exudates in macular region (proximity={exudates.macula_proximity_score})."
        )
        return DMEGrade.NON_CENTER_INVOLVING, DME_LABELS[1], rationale

    rationale.append("Hard exudates present but distant from macula center.")
    return DMEGrade.NONE, DME_LABELS[0], rationale
