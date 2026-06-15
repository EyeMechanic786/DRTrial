export interface LesionMetrics {
  lesion_type: string;
  count: number;
  total_area_pct: number;
  macula_proximity_score: number;
}

export interface OverlayLayer {
  lesion_type: string;
  color_rgb: number[];
  mask_png_base64?: string;
  bounding_boxes: { x: number; y: number; w: number; h: number }[];
}

export interface ICORecommendation {
  referral_required: boolean;
  follow_up_months: string;
  notes: string[];
}

export interface AAORecommendation {
  referral_to_ophthalmologist: boolean;
  re_examination_interval: string;
  clinical_pearls: string[];
}

export interface AnalysisResult {
  study_id: string;
  model_version: string;
  qc: {
    passed: boolean;
    focus_score: number;
    brightness: number;
    warnings: string[];
    camera_vendor?: string;
    camera_label?: string;
    field_of_view?: string;
  };
  camera?: {
    vendor: string;
    vendor_label: string;
    field_of_view: string;
    vendor_neutral: boolean;
    preprocessing_notes: string[];
  };
  lesions: LesionMetrics[];
  icdr_grade: number;
  icdr_label: string;
  icdr_confidence: number;
  dme_grade: number;
  dme_label: string;
  ico: ICORecommendation;
  aao: AAORecommendation;
  overlays: OverlayLayer[];
  grading_rationale: string[];
  disclaimer: string;
}

export interface Study {
  id: string;
  patient_ref: string | null;
  eye: string | null;
  resource_setting: string;
  status: string;
  created_at: string;
}

export interface Job {
  id: string;
  study_id: string;
  status: string;
  error: string | null;
}

const API = import.meta.env.DEV ? "/api" : "/api";

export async function createStudy(patientRef?: string, eye?: string): Promise<Study> {
  const res = await fetch(`${API}/studies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ patient_ref: patientRef, eye, resource_setting: "high" }),
  });
  if (!res.ok) throw new Error("Failed to create study");
  return res.json();
}

export async function uploadImage(studyId: string, file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API}/studies/${studyId}/images`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
}

export async function startAnalysis(studyId: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/studies/${studyId}/analyze`, { method: "POST" });
  if (!res.ok) throw new Error("Analysis queue failed");
  return res.json();
}

export async function pollJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Job not found");
  return res.json();
}

export async function getResults(studyId: string): Promise<AnalysisResult> {
  const res = await fetch(`${API}/studies/${studyId}/results`);
  if (!res.ok) throw new Error("Results not ready");
  return res.json();
}

export async function submitReview(
  studyId: string,
  data: {
    reviewer: string;
    icdr_override?: number;
    dme_override?: number;
    dismissed_lesions: { lesion_type: string; x: number; y: number; w: number; h: number }[];
    notes?: string;
    signed_off: boolean;
  }
): Promise<void> {
  const res = await fetch(`${API}/studies/${studyId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Review submit failed");
}

export async function analyzeSync(
  file: File,
  resourceSetting: string,
  cameraHint: string = "auto"
): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(
    `${API}/analyze?resource_setting=${resourceSetting}&camera_hint=${cameraHint}`,
    { method: "POST", body: form }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}
