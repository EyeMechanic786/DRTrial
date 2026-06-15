const form = document.getElementById("upload-form");
const fileInput = document.getElementById("fundus-file");
const resourceSelect = document.getElementById("resource-setting");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const analyzeBtn = document.getElementById("analyze-btn");
const canvas = document.getElementById("overlay-canvas");
const ctx = canvas.getContext("2d");

const LESION_COLORS = {
  microaneurysms: "rgba(255, 0, 0, 0.7)",
  hemorrhages: "rgba(200, 0, 50, 0.7)",
  hard_exudates: "rgba(255, 255, 0, 0.7)",
  cotton_wool_spots: "rgba(180, 180, 255, 0.7)",
};

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = fileInput.files?.[0];
  if (!file) return;

  analyzeBtn.disabled = true;
  statusEl.textContent = "Analyzing fundus image…";
  statusEl.classList.remove("error");
  resultsEl.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(
      `/analyze?resource_setting=${encodeURIComponent(resourceSelect.value)}`,
      { method: "POST", body: formData }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Analysis failed (${res.status})`);
    }
    const data = await res.json();
    renderResults(data, file);
    statusEl.textContent = `Analysis complete — study ${data.study_id.slice(0, 8)}…`;
  } catch (err) {
    statusEl.textContent = err.message;
    statusEl.classList.add("error");
  } finally {
    analyzeBtn.disabled = false;
  }
});

function renderResults(data, file) {
  resultsEl.classList.remove("hidden");

  document.getElementById("icdr-grade").textContent = `Grade ${data.icdr_grade}`;
  document.getElementById("icdr-label").textContent = data.icdr_label;
  document.getElementById("icdr-confidence").textContent =
    `Confidence: ${(data.icdr_confidence * 100).toFixed(0)}%`;
  document.getElementById("dme-label").textContent = data.dme_label;

  document.getElementById("ico-details").innerHTML = [
    `<li><strong>Referral:</strong> ${data.ico.referral_required ? "Required" : "Not required"}</li>`,
    `<li><strong>Follow-up:</strong> ${data.ico.follow_up_months}</li>`,
    ...data.ico.notes.map((n) => `<li>${n}</li>`),
  ].join("");

  document.getElementById("aao-details").innerHTML = [
    `<li><strong>Referral:</strong> ${data.aao.referral_to_ophthalmologist ? "Required" : "Not required"}</li>`,
    `<li><strong>Re-examination:</strong> ${data.aao.re_examination_interval}</li>`,
    ...data.aao.clinical_pearls.map((p) => `<li>${p}</li>`),
  ].join("");

  const tbody = document.querySelector("#lesion-table tbody");
  tbody.innerHTML = data.lesions
    .map(
      (l) => `<tr>
        <td>${formatLesion(l.lesion_type)}</td>
        <td>${l.count}</td>
        <td>${l.total_area_pct.toFixed(3)}%</td>
        <td>${l.macula_proximity_score.toFixed(2)}</td>
      </tr>`
    )
    .join("");

  document.getElementById("rationale").innerHTML = data.grading_rationale
    .map((r) => `<li>${r}</li>`)
    .join("");

  document.getElementById("qc-details").innerHTML = [
    `<li>Focus score: ${data.qc.focus_score}</li>`,
    `<li>Brightness: ${data.qc.brightness}</li>`,
    `<li>QC passed: ${data.qc.passed ? "Yes" : "No"}</li>`,
    ...data.qc.warnings.map((w) => `<li class="warning">${w}</li>`),
  ].join("");

  drawOverlay(file, data);
}

function formatLesion(type) {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function drawOverlay(file, data) {
  const img = new Image();
  const composite = data.overlays.find((o) => o.lesion_type === "composite_overlay");

  img.onload = () => {
    const maxW = 520;
    const scale = Math.min(1, maxW / img.width);
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;

    if (composite?.mask_png_base64) {
      const overlayImg = new Image();
      overlayImg.onload = () => {
        ctx.drawImage(overlayImg, 0, 0, canvas.width, canvas.height);
        drawBoundingBoxes(data, scale);
      };
      overlayImg.src = `data:image/png;base64,${composite.mask_png_base64}`;
    } else {
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      drawBoundingBoxes(data, scale);
    }
  };
  img.src = URL.createObjectURL(file);
}

function drawBoundingBoxes(data, scale) {
  for (const layer of data.overlays) {
    if (layer.lesion_type === "composite_overlay") continue;
    ctx.strokeStyle = LESION_COLORS[layer.lesion_type] || "rgba(255,255,255,0.8)";
    ctx.lineWidth = 2;
    for (const box of layer.bounding_boxes) {
      ctx.strokeRect(
        box.x * scale,
        box.y * scale,
        box.w * scale,
        box.h * scale
      );
    }
  }
}
