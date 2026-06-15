"""Tests for DR grading pathway."""

import numpy as np
import pytest

from ml.dr_pathway.grading import aao_recommendation, grade_icdr, ico_recommendation
from ml.dr_pathway.schemas import ICDR_LABELS, LesionMetrics


def test_grade_no_dr():
    lesions = [
        LesionMetrics(lesion_type="microaneurysms", count=0),
        LesionMetrics(lesion_type="hemorrhages", count=0),
        LesionMetrics(lesion_type="hard_exudates", count=0),
        LesionMetrics(lesion_type="cotton_wool_spots", count=0),
    ]
    grade, label, conf, _ = grade_icdr(lesions)
    assert grade == 0
    assert label == ICDR_LABELS[0]
    assert conf > 0.5


def test_grade_mild_npdr():
    lesions = [
        LesionMetrics(lesion_type="microaneurysms", count=5),
        LesionMetrics(lesion_type="hemorrhages", count=0),
        LesionMetrics(lesion_type="hard_exudates", count=0),
        LesionMetrics(lesion_type="cotton_wool_spots", count=0),
    ]
    grade, label, _, _ = grade_icdr(lesions)
    assert grade == 1
    assert "Mild" in label


def test_ico_referral_moderate():
    ico = ico_recommendation(2, ICDR_LABELS[2], 0, "No apparent DME")
    assert ico.referral_required is True
    assert "3" in ico.follow_up_months


def test_aao_referral_severe():
    aao = aao_recommendation(3, ICDR_LABELS[3], 0, "No apparent DME")
    assert aao.referral_to_ophthalmologist is True
