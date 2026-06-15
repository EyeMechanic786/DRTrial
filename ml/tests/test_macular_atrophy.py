"""Tests for macular atrophy detection and grading context."""

import cv2
import numpy as np

from ml.dr_pathway.grading import (
    apply_atrophy_grading_context,
    atrophy_likely_explains_dr_findings,
    grade_icdr,
)
from ml.dr_pathway.macular_atrophy import detect_macular_atrophy
from ml.dr_pathway.pipeline import analyze_fundus_image
from ml.dr_pathway.schemas import ICDR_LABELS, LesionMetrics


def _synthetic_optos_macular_atrophy_jpeg() -> bytes:
  """Optos-like image with central pale atrophy, no true DR lesions."""
  canvas = np.zeros((1200, 1600, 3), dtype=np.uint8)
  cv2.ellipse(canvas, (800, 600), (620, 480), 0, 0, 360, (40, 120, 50), -1)
  cv2.circle(canvas, (620, 580), 35, (180, 200, 220), -1)
  cv2.ellipse(canvas, (820, 590), (190, 155), 0, 0, 360, (210, 225, 235), -1)
  cv2.ellipse(canvas, (820, 590), (165, 135), 0, 0, 360, (245, 248, 252), -1)
  _, buf = cv2.imencode(".jpg", canvas)
  return buf.tobytes()


def test_detect_macular_atrophy_on_synthetic():
  arr = np.frombuffer(_synthetic_optos_macular_atrophy_jpeg(), dtype=np.uint8)
  image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
  result = detect_macular_atrophy(image, (820, 590))
  assert result.detected is True
  assert result.confidence >= 0.55
  assert result.central_area_pct >= 0.6


def test_atrophy_mimic_downgrades_icdr_not_dme():
  atrophy = detect_macular_atrophy(
    cv2.imdecode(
      np.frombuffer(_synthetic_optos_macular_atrophy_jpeg(), dtype=np.uint8),
      cv2.IMREAD_COLOR,
    ),
    (820, 590),
  )
  lesions = [
    LesionMetrics(
      lesion_type="hard_exudates",
      count=2,
      max_component_area_px=12000,
      macula_proximity_score=0.9,
      total_area_pct=2.5,
    ),
    LesionMetrics(lesion_type="hemorrhages", count=0),
    LesionMetrics(lesion_type="microaneurysms", count=0),
    LesionMetrics(lesion_type="cotton_wool_spots", count=0),
  ]
  assert atrophy_likely_explains_dr_findings(atrophy, lesions) is True

  grade, label, conf, _ = grade_icdr(lesions)
  assert grade >= 1

  adj_grade, adj_label, adj_conf, rationale = apply_atrophy_grading_context(
    grade, label, conf, [], atrophy, lesions
  )
  assert adj_grade == 0
  assert adj_label == ICDR_LABELS[0]
  assert adj_conf <= 0.5
  assert any("DME assessment unchanged" in r for r in rationale)


def test_atrophy_with_hemorrhages_does_not_suppress_dr():
  atrophy = detect_macular_atrophy(
    cv2.imdecode(
      np.frombuffer(_synthetic_optos_macular_atrophy_jpeg(), dtype=np.uint8),
      cv2.IMREAD_COLOR,
    ),
    (820, 590),
  )
  lesions = [
    LesionMetrics(
      lesion_type="hard_exudates",
      count=2,
      max_component_area_px=12000,
      macula_proximity_score=0.9,
    ),
    LesionMetrics(lesion_type="hemorrhages", count=3),
    LesionMetrics(lesion_type="microaneurysms", count=0),
    LesionMetrics(lesion_type="cotton_wool_spots", count=0),
  ]
  assert atrophy_likely_explains_dr_findings(atrophy, lesions) is False


def test_optos_atrophy_end_to_end():
  result = analyze_fundus_image(
    _synthetic_optos_macular_atrophy_jpeg(),
    "atrophy-test",
    camera_hint="optos_uwf",
  )
  assert result.non_dr_pathology is not None
  assert result.non_dr_pathology.detected is True
  assert result.icdr_grade == 0
