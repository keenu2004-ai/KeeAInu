import React, { useEffect, useRef } from "react";
import { Finding } from "../types/inspection";

interface CanvasOverlayProps {
  findings: Finding[];
  currentFrameIndex: number;
  activeFindingId: string | null;
  onSelectFinding: (findingId: string) => void;
  width: number;
  height: number;
}

export const CanvasOverlay: React.FC<CanvasOverlayProps> = ({
  findings,
  currentFrameIndex,
  activeFindingId,
  onSelectFinding,
  width,
  height,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Filter findings for the current frame index (or all if image)
  const currentFindings = findings.filter(
    (f) => f.frame_index === currentFrameIndex
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    if (currentFindings.length === 0) return;

    currentFindings.forEach((finding) => {
      const bbox = finding.adjusted_bbox || finding.bbox;
      if (!bbox) return;

      const x = bbox.x_min * width;
      const y = bbox.y_min * height;
      const w = (bbox.x_max - bbox.x_min) * width;
      const h = (bbox.y_max - bbox.y_min) * height;

      const isActive = finding.id === activeFindingId;

      // Color coding by review status
      let strokeColor = "#06b6d4"; // Default cyan
      let fillColor = "rgba(6, 182, 212, 0.15)";

      if (finding.decision_status === "CONFIRMED") {
        strokeColor = "#10b981";
        fillColor = "rgba(16, 185, 129, 0.2)";
      } else if (finding.decision_status === "REJECTED") {
        strokeColor = "#ef4444";
        fillColor = "rgba(239, 68, 68, 0.15)";
      } else if (finding.decision_status === "ADJUSTED") {
        strokeColor = "#3b82f6";
        fillColor = "rgba(59, 130, 246, 0.2)";
      }

      // Draw bounding box
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = isActive ? 3 : 2;
      ctx.fillStyle = fillColor;

      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);

      // Draw corner brackets
      const cornerLength = Math.min(12, w / 4, h / 4);
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      // Top-Left
      ctx.beginPath();
      ctx.moveTo(x, y + cornerLength);
      ctx.lineTo(x, y);
      ctx.lineTo(x + cornerLength, y);
      ctx.stroke();
      // Top-Right
      ctx.beginPath();
      ctx.moveTo(x + w - cornerLength, y);
      ctx.lineTo(x + w, y);
      ctx.lineTo(x + w, y + cornerLength);
      ctx.stroke();

      // Label background
      const label = `${finding.defect_class} (${(finding.confidence_score * 100).toFixed(0)}%) ${finding.is_simulated ? '[SIM]' : ''}`;
      ctx.font = "bold 11px 'JetBrains Mono', monospace";
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const textHeight = 16;

      ctx.fillStyle = strokeColor;
      ctx.fillRect(x, Math.max(0, y - textHeight - 2), textWidth + 8, textHeight + 2);

      // Label text
      ctx.fillStyle = "#070a13";
      ctx.fillText(label, x + 4, Math.max(12, y - 4));
    });
  }, [currentFindings, activeFindingId, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="canvas-overlay"
      onClick={(e) => {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (!rect) return;
        const clickX = (e.clientX - rect.left) / rect.width;
        const clickY = (e.clientY - rect.top) / rect.height;

        // Check if click hit a finding box
        for (const f of currentFindings) {
          const b = f.adjusted_bbox || f.bbox;
          if (
            clickX >= b.x_min &&
            clickX <= b.x_max &&
            clickY >= b.y_min &&
            clickY <= b.y_max
          ) {
            onSelectFinding(f.id);
            break;
          }
        }
      }}
    />
  );
};
