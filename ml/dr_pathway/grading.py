"""ICDR grading and ICO / AAO clinical recommendations.

Grading follows the International Clinical Diabetic Retinopathy (ICDR) scale
developed via AAO-led international consensus and adopted by ICO guidelines.
"""

from __future__ import annotations

from ml.dr_pathway.macular_atrophy import MacularAtrophyResult
from ml.dr_pathway.schemas import (
    AAORecommendation,
    ICDR_LABELS,
    ICDRGrade,
    ICORecommendation,
    LesionMetrics,
)


def _lesion_map(lesions: list[LesionMetrics]) -> dict[str, LesionMetrics]:
    return {l.lesion_type: l for l in lesions}


def grade_icdr(lesions: list[LesionMetrics]) -> tuple[int, str, float, list[str]]:
    """Rule-based ICDR grade from detected lesion burden."""
    lm = _lesion_map(lesions)
    ma = lm.get("microaneurysms")
    he = lm.get("hemorrhages")
    ex = lm.get("hard_exudates")
    cws = lm.get("cotton_wool_spots")

    ma_c = ma.count if ma else 0
    he_c = he.count if he else 0
    ex_c = ex.count if ex else 0
    cws_c = cws.count if cws else 0
    he_pct = he.total_area_pct if he else 0.0

    rationale: list[str] = []
    total_lesions = ma_c + he_c + ex_c + cws_c

    if total_lesions == 0:
        rationale.append("No DR lesions detected.")
        return ICDRGrade.NO_DR, ICDR_LABELS[0], 0.85, rationale

    # Severe NPDR proxy: 4-2-1 rule approximation from global lesion density
    severe_signals = 0
    if he_c >= 20:
        severe_signals += 1
        rationale.append(f"Hemorrhage count ({he_c}) suggests severe NPDR 4-2-1 criterion.")
    if he_pct >= 0.5:
        severe_signals += 1
        rationale.append(f"Hemorrhage area ({he_pct:.2f}%) elevated.")
    if cws_c >= 3:
        severe_signals += 1
        rationale.append(f"Multiple cotton wool spots ({cws_c}) — ischemic signs.")

    if severe_signals >= 2:
        confidence = min(0.75, 0.5 + severe_signals * 0.1)
        rationale.append("Meets proxy criteria for severe NPDR (IRMA/NV not assessed).")
        return ICDRGrade.SEVERE_NPDR, ICDR_LABELS[3], confidence, rationale

    if he_c >= 8 or ex_c >= 5 or cws_c >= 2 or (ma_c >= 3 and (he_c >= 2 or ex_c >= 1)):
        rationale.append(
            f"Multiple lesion types: MA={ma_c}, HE={he_c}, EX={ex_c}, CWS={cws_c}."
        )
        return ICDRGrade.MODERATE_NPDR, ICDR_LABELS[2], 0.65, rationale

    if ma_c >= 1 and he_c == 0 and ex_c == 0 and cws_c == 0:
        rationale.append(f"Microaneurysms only ({ma_c}) — mild NPDR.")
        return ICDRGrade.MILD_NPDR, ICDR_LABELS[1], 0.7, rationale

    if ma_c >= 1:
        rationale.append(
            f"Predominantly microaneurysms with minor additional findings (MA={ma_c})."
        )
        return ICDRGrade.MILD_NPDR, ICDR_LABELS[1], 0.6, rationale

    rationale.append("Lesion pattern does not match standard ICDR categories clearly.")
    return ICDRGrade.MODERATE_NPDR, ICDR_LABELS[2], 0.45, rationale


def atrophy_likely_explains_dr_findings(
    atrophy: MacularAtrophyResult,
    lesions: list[LesionMetrics],
) -> bool:
    """True when central findings are probably atrophy mimic, not true DR.

    Macular exudates and edema are still detected — this only revises ICDR when
    hemorrhages / microaneurysms are absent and central exudate/CWS pattern fits
    a large homogeneous atrophic zone.
    """
    if not atrophy.detected or atrophy.confidence < 0.55:
        return False

    lm = _lesion_map(lesions)
    ma = lm.get("microaneurysms")
    he = lm.get("hemorrhages")
    ex = lm.get("hard_exudates")
    cws = lm.get("cotton_wool_spots")

    ma_c = ma.count if ma else 0
    he_c = he.count if he else 0
    ex_c = ex.count if ex else 0
    cws_c = cws.count if cws else 0

    if he_c >= 1 or ma_c >= 1:
        return False

    central_mimic = 0
    if ex and ex_c > 0:
        large_central = (
            ex.macula_proximity_score >= 0.65
            and ex.count <= 4
            and ex.max_component_area_px >= 500
        )
        if large_central:
            central_mimic += 1

    if cws and cws_c > 0:
        if cws.macula_proximity_score >= 0.65 and cws.count <= 3:
            central_mimic += 1

    return central_mimic >= 1


def apply_atrophy_grading_context(
    icdr_grade: int,
    icdr_label: str,
    confidence: float,
    grade_rationale: list[str],
    atrophy: MacularAtrophyResult,
    lesions: list[LesionMetrics],
) -> tuple[int, str, float, list[str]]:
    """Adjust ICDR confidence when macular atrophy likely explains false DR calls."""
    rationale = list(grade_rationale)
    if not atrophy.detected:
        return icdr_grade, icdr_label, confidence, rationale

    rationale = atrophy.rationale + rationale

    if atrophy_likely_explains_dr_findings(atrophy, lesions):
        rationale.append(
            "Central exudate/CWS signal likely reflects macular atrophy rather than DR — "
            "ICDR downgraded to no apparent DR. DME assessment unchanged."
        )
        return ICDRGrade.NO_DR, ICDR_LABELS[0], min(confidence, 0.45), rationale

    if icdr_grade > ICDRGrade.NO_DR:
        rationale.append(
            "Macular atrophy suspected — interpret central findings with caution; "
            "true DR and DME may coexist with atrophy."
        )
        confidence = max(0.35, confidence - 0.15)

    return icdr_grade, icdr_label, confidence, rationale


def ico_recommendation(
    icdr_grade: int,
    icdr_label: str,
    dme_grade: int,
    dme_label: str,
    resource_setting: str = "high",
) -> ICORecommendation:
    """ICO Guidelines for Diabetic Eye Care — Table 2a (high resource)."""
    notes: list[str] = []
    referral = False
    follow_up = "12 months"

    if dme_grade == 2:
        referral = True
        follow_up = "< 1 month"
        notes.append("Center-involving DME suspect — urgent ophthalmology referral.")
    elif dme_grade == 1:
        referral = True
        follow_up = "3 months"
        notes.append("Non-center-involving DME suspect — ophthalmology referral.")

    if icdr_grade == ICDRGrade.NO_DR:
        if dme_grade == 0:
            referral = False
            follow_up = "12 months"
    elif icdr_grade == ICDRGrade.MILD_NPDR:
        if dme_grade == 0:
            referral = False
            follow_up = "12 months"
    elif icdr_grade == ICDRGrade.MODERATE_NPDR:
        referral = True
        follow_up = "3–6 months"
        notes.append("Moderate NPDR — referral to ophthalmologist required (ICO high-resource).")
    elif icdr_grade == ICDRGrade.SEVERE_NPDR:
        referral = True
        follow_up = "< 3 months"
        notes.append("Severe NPDR — urgent referral; consider PRP evaluation.")
    elif icdr_grade == ICDRGrade.PDR:
        referral = True
        follow_up = "< 1 month"
        notes.append("Proliferative DR — urgent referral for panretinal photocoagulation / anti-VEGF.")

    if resource_setting == "low_intermediate" and icdr_grade >= ICDRGrade.MODERATE_NPDR:
        notes.append("Low/intermediate setting: refer at moderate NPDR or worse per ICO Table 2b.")

    return ICORecommendation(
        icdr_grade=icdr_grade,
        icdr_label=icdr_label,
        dme_grade=dme_grade,
        dme_label=dme_label,
        referral_required=referral,
        follow_up_months=follow_up,
        resource_setting=resource_setting,  # type: ignore[arg-type]
        notes=notes,
    )


def aao_recommendation(
    icdr_grade: int,
    icdr_label: str,
    dme_grade: int,
    dme_label: str,
) -> AAORecommendation:
    """AAO DR Preferred Practice Pattern aligned screening intervals."""
    pearls: list[str] = []
    referral = False
    interval = "12 months"

    if dme_grade == 2:
        referral = True
        interval = "1 month"
        pearls.append("Suspected center-involving DME — OCT and ophthalmology evaluation.")
    elif dme_grade == 1:
        referral = True
        interval = "3 months"
        pearls.append("Suspected non-center-involving DME — ophthalmology referral.")

    grade_intervals = {
        ICDRGrade.NO_DR: ("12 months", False),
        ICDRGrade.MILD_NPDR: ("12 months", False),
        ICDRGrade.MODERATE_NPDR: ("3–6 months", True),
        ICDRGrade.SEVERE_NPDR: ("2–4 months", True),
        ICDRGrade.PDR: ("1 month", True),
    }
    dr_interval, dr_referral = grade_intervals.get(icdr_grade, ("6 months", True))
    if dme_grade == 0:
        interval = dr_interval
    referral = referral or dr_referral

    if icdr_grade >= ICDRGrade.MODERATE_NPDR:
        pearls.append("Consider fluorescein angiography if treatment planning required.")
    if icdr_grade == ICDRGrade.SEVERE_NPDR:
        pearls.append("Evaluate for panretinal photocoagulation per ETDRS criteria.")

    pearls.append("Pregnant patients with diabetes require more frequent monitoring.")

    return AAORecommendation(
        icdr_grade=icdr_grade,
        icdr_label=icdr_label,
        dme_grade=dme_grade,
        dme_label=dme_label,
        referral_to_ophthalmologist=referral,
        re_examination_interval=interval,
        clinical_pearls=pearls,
    )
