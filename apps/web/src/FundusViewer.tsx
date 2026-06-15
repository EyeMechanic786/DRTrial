import { useRef, useEffect, useCallback } from "react";
import type { AnalysisResult, OverlayLayer } from "./api";

const LESION_COLORS: Record<string, string> = {
  microaneurysms: "rgba(255,0,0,0.7)",
  hemorrhages: "rgba(200,0,50,0.7)",
  hard_exudates: "rgba(255,255,0,0.7)",
  cotton_wool_spots: "rgba(180,180,255,0.7)",
};

interface Props {
  imageUrl: string;
  result: AnalysisResult;
  visibleLayers: Set<string>;
  opacity: number;
  dismissed: Set<string>;
  onDismiss: (key: string) => void;
}

export function FundusViewer({
  imageUrl,
  result,
  visibleLayers,
  opacity,
  dismissed,
  onDismiss,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      const maxW = 560;
      const scale = Math.min(1, maxW / img.width);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const composite = result.overlays.find((o) => o.lesion_type === "composite_overlay");
      if (composite?.mask_png_base64 && visibleLayers.size > 0) {
        const overlayImg = new Image();
        overlayImg.onload = () => {
          ctx.globalAlpha = opacity;
          ctx.drawImage(overlayImg, 0, 0, canvas.width, canvas.height);
          ctx.globalAlpha = 1;
          drawBoxes(ctx, result.overlays, scale, visibleLayers, dismissed, onDismiss);
        };
        overlayImg.src = `data:image/png;base64,${composite.mask_png_base64}`;
      } else {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        drawBoxes(ctx, result.overlays, scale, visibleLayers, dismissed, onDismiss);
      }
    };
    img.src = imageUrl;
  }, [imageUrl, result, visibleLayers, opacity, dismissed, onDismiss]);

  useEffect(() => {
    draw();
  }, [draw]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);
    const scale = canvas.width / (result.overlays[0]?.bounding_boxes[0] ? 1 : 1);

    for (const layer of result.overlays) {
      if (layer.lesion_type === "composite_overlay" || !visibleLayers.has(layer.lesion_type))
        continue;
      for (const box of layer.bounding_boxes) {
        const bx = box.x * (canvas.width / (canvas.width || 1));
        const by = box.y * (canvas.height / (canvas.height || 1));
        if (x >= bx && x <= bx + box.w * scale && y >= by && y <= by + box.h * scale) {
          onDismiss(`${layer.lesion_type}-${box.x}-${box.y}`);
          return;
        }
      }
    }
  };

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      style={{ maxWidth: "100%", cursor: "crosshair", border: "1px solid #2d3a4f", borderRadius: 6 }}
      title="Click a lesion box to dismiss as false positive"
    />
  );
}

function drawBoxes(
  ctx: CanvasRenderingContext2D,
  overlays: OverlayLayer[],
  scale: number,
  visible: Set<string>,
  dismissed: Set<string>,
  _onDismiss: (k: string) => void
) {
  for (const layer of overlays) {
    if (layer.lesion_type === "composite_overlay" || !visible.has(layer.lesion_type)) continue;
    ctx.strokeStyle = LESION_COLORS[layer.lesion_type] || "white";
    ctx.lineWidth = 2;
    for (const box of layer.bounding_boxes) {
      const key = `${layer.lesion_type}-${box.x}-${box.y}`;
      if (dismissed.has(key)) continue;
      ctx.strokeRect(box.x * scale, box.y * scale, box.w * scale, box.h * scale);
    }
  }
}
