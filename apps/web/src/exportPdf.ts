import { jsPDF } from "jspdf";
import type { AnalysisResult } from "./api";

export function exportPdf(
  result: AnalysisResult,
  reviewer: string,
  icdrOverride: number | "",
  notes: string
) {
  const doc = new jsPDF();
  let y = 20;

  doc.setFontSize(16);
  doc.text("DRTrial — DR Analysis Report", 20, y);
  y += 10;
  doc.setFontSize(10);
  doc.text(result.disclaimer, 20, y, { maxWidth: 170 });
  y += 15;

  doc.text(`Study ID: ${result.study_id}`, 20, y);
  y += 6;
  doc.text(`Model: ${result.model_version}`, 20, y);
  y += 6;
  doc.text(`ICDR Grade: ${icdrOverride !== "" ? icdrOverride : result.icdr_grade} — ${result.icdr_label}`, 20, y);
  y += 6;
  doc.text(`DME: ${result.dme_label}`, 20, y);
  y += 6;
  doc.text(`Confidence: ${(result.icdr_confidence * 100).toFixed(0)}%`, 20, y);
  y += 10;

  doc.text("ICO: Referral " + (result.ico.referral_required ? "required" : "not required"), 20, y);
  y += 6;
  doc.text(`ICO follow-up: ${result.ico.follow_up_months}`, 20, y);
  y += 6;
  doc.text("AAO: Referral " + (result.aao.referral_to_ophthalmologist ? "required" : "not required"), 20, y);
  y += 6;
  doc.text(`AAO re-exam: ${result.aao.re_examination_interval}`, 20, y);
  y += 10;

  doc.text("Lesions:", 20, y);
  y += 6;
  for (const l of result.lesions) {
    doc.text(`  ${l.lesion_type}: count=${l.count}, area=${l.total_area_pct.toFixed(3)}%`, 20, y);
    y += 5;
  }
  y += 5;

  if (notes) {
    doc.text(`Clinician notes (${reviewer}):`, 20, y);
    y += 6;
    doc.text(notes, 20, y, { maxWidth: 170 });
  }

  doc.save(`drtrial-report-${result.study_id.slice(0, 8)}.pdf`);
}
