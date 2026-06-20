import { useState } from "react";
import { analyzeSync } from "./api";
import type { AnalysisResult } from "./api";
import { FundusViewer } from "./FundusViewer";
import { exportPdf } from "./exportPdf";
import "./App.css";

const LAYER_OPTIONS = [
  "microaneurysms",
  "hemorrhages",
  "hard_exudates",
  "cotton_wool_spots",
];

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string>("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [visibleLayers, setVisibleLayers] = useState<Set<string>>(new Set(LAYER_OPTIONS));
  const [opacity, setOpacity] = useState(0.7);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [reviewer, setReviewer] = useState("");
  const [icdrOverride, setIcdrOverride] = useState<number | "">("");
  const [notes, setNotes] = useState("");
  const [resourceSetting, setResourceSetting] = useState("high");
  const [cameraHint, setCameraHint] = useState("auto");

  const handleFile = (f: File) => {
    setFile(f);
    setImageUrl(URL.createObjectURL(f));
    setResult(null);
    setDismissed(new Set());
    setError("");
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const data = await analyzeSync(file, resourceSetting, cameraHint);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const toggleLayer = (layer: string) => {
    setVisibleLayers((prev) => {
      const next = new Set(prev);
      if (next.has(layer)) next.delete(layer);
      else next.add(layer);
      return next;
    });
  };

  const handleDismiss = (key: string) => {
    setDismissed((prev) => new Set(prev).add(key));
  };

  const handleExportPdf = () => {
    if (!result) return;
    exportPdf(result, reviewer || "Clinician", icdrOverride, notes);
  };

  return (
    <div className="app">
      <header>
        <h1>DRTrial</h1>
        <p className="tagline">DR Lesion Detection — ICO / AAO Clinical Decision Support</p>
        <p className="disclaimer">Investigational CDS — not for autonomous diagnosis.</p>
      </header>

      <section className="panel">
        <h2>Upload colour fundus photograph</h2>
        <div className="controls">
          <input
            type="file"
            accept="image/jpeg,image/png,image/tiff,image/webp,image/bmp,.tif,.tiff"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <select value={resourceSetting} onChange={(e) => setResourceSetting(e.target.value)}>
            <option value="high">ICO high resource</option>
            <option value="low_intermediate">ICO low/intermediate</option>
          </select>
          <select value={cameraHint} onChange={(e) => setCameraHint(e.target.value)} title="Camera type">
            <option value="auto">Camera: auto-detect</option>
            <option value="standard_cfp">Standard fundus (CFP)</option>
            <option value="optos_uwf">Optos / ultra-widefield</option>
            <option value="confocal_slo">Confocal SLO</option>
          </select>
          <button onClick={handleAnalyze} disabled={!file || loading}>
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {result && imageUrl && (
        <section className="panel results">
          {result.non_dr_pathology?.detected && (
            <div className="pathology-banner">
              <strong>{result.non_dr_pathology.label}</strong>
              <span>
                Confidence {(result.non_dr_pathology.confidence * 100).toFixed(0)}% —
                central area {result.non_dr_pathology.central_area_pct.toFixed(1)}%.
                Macula is still fully analysed for exudates and edema; consider OCT/FAF.
              </span>
            </div>
          )}
          <div className="grid">
            <div>
              <h3>Fundus viewer</h3>
              <div className="layer-toggles">
                {LAYER_OPTIONS.map((l) => (
                  <label key={l}>
                    <input
                      type="checkbox"
                      checked={visibleLayers.has(l)}
                      onChange={() => toggleLayer(l)}
                    />
                    {l.replace(/_/g, " ")}
                  </label>
                ))}
              </div>
              <label className="opacity">
                Overlay opacity:{" "}
                <input
                  type="range"
                  min={0.2}
                  max={1}
                  step={0.05}
                  value={opacity}
                  onChange={(e) => setOpacity(parseFloat(e.target.value))}
                />
              </label>
              <p className="hint">Click lesion boxes to dismiss false positives</p>
              <FundusViewer
                imageUrl={imageUrl}
                result={result}
                visibleLayers={visibleLayers}
                opacity={opacity}
                dismissed={dismissed}
                onDismiss={handleDismiss}
              />
            </div>

            <div>
              <h3>ICDR / ICO severity</h3>
              <div className="grade-card">
                <span className="grade-num">Grade {icdrOverride !== "" ? icdrOverride : result.icdr_grade}</span>
                <span>{result.icdr_label}</span>
                <span className="muted">Confidence {(result.icdr_confidence * 100).toFixed(0)}%</span>
              </div>
              <p><strong>DME:</strong> {result.dme_label}</p>
              {result.camera && (
                <>
                  <h4>Camera (vendor-neutral)</h4>
                  <ul>
                    <li>{result.camera.vendor_label}</li>
                    <li>Field of view: {result.camera.field_of_view}</li>
                  </ul>
                </>
              )}
              <h4>ICO</h4>
              <ul>
                <li>Referral: {result.ico.referral_required ? "Required" : "Not required"}</li>
                <li>Follow-up: {result.ico.follow_up_months}</li>
                {result.ico.notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
              <h4>AAO</h4>
              <ul>
                <li>Referral: {result.aao.referral_to_ophthalmologist ? "Required" : "Not required"}</li>
                <li>Re-exam: {result.aao.re_examination_interval}</li>
              </ul>
            </div>
          </div>

          <h3>Lesion quantification</h3>
          <table>
            <thead>
              <tr><th>Lesion</th><th>Count</th><th>Area %</th><th>Macula proximity</th></tr>
            </thead>
            <tbody>
              {result.lesions.map((l) => (
                <tr key={l.lesion_type}>
                  <td>{l.lesion_type.replace(/_/g, " ")}</td>
                  <td>{l.count}</td>
                  <td>{l.total_area_pct.toFixed(3)}</td>
                  <td>{l.macula_proximity_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Clinician review</h3>
          <div className="review-form">
            <input
              placeholder="Reviewer name"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
            />
            <select
              value={icdrOverride}
              onChange={(e) => setIcdrOverride(e.target.value === "" ? "" : parseInt(e.target.value))}
            >
              <option value="">AI grade (no override)</option>
              {[0, 1, 2, 3, 4].map((g) => (
                <option key={g} value={g}>Override ICDR grade {g}</option>
              ))}
            </select>
            <textarea
              placeholder="Clinical notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
            <button onClick={handleExportPdf}>Export PDF report</button>
          </div>

          <h3>Grading rationale</h3>
          <ul>{result.grading_rationale.map((r, i) => <li key={i}>{r}</li>)}</ul>
        </section>
      )}

      <footer>
        <p>DRTrial v1.1 — ICO Guidelines &amp; AAO DR Preferred Practice Pattern</p>
      </footer>
    </div>
  );
}
