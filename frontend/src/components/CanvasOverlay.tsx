
import React, { useEffect, useRef } from "react";
import { Finding } from "../types/inspection";

interface CanvasOverlayProps {
  findings: Finding[];
  currentFrameIndex: number;
  activeFindingId: string | null;
  onSelectFinding: (findingId: string) => void;
  width: number;
  height: number;
  activeMediaId?: string;
  isStillImage?: boolean;
}

export const CanvasOverlay: React.FC<CanvasOverlayProps> = ({
  findings,
  currentFrameIndex,
  activeFindingId,
  onSelectFinding,
  width,
  height,
  activeMediaId,
  isStillImage,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const currentFindings = findings.filter((finding) => {
    if (
      activeMediaId &&
      finding.media_id &&
      finding.media_id !== activeMediaId
    ) {
      return false;
    }

    if (isStillImage) {
      return (
        finding.frame_index === 0 ||
        finding.frame_index === undefined
      );
    }

    return finding.frame_index === currentFrameIndex;
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, width, height);

    currentFindings.forEach((finding) => {
      const bbox = finding.adjusted_bbox || finding.bbox;
      if (!bbox) return;

      const x = bbox.x_min * width;
      const y = bbox.y_min * height;
      const w = (bbox.x_max - bbox.x_min) * width;
      const h = (bbox.y_max - bbox.y_min) * height;
      const isActive = finding.id === activeFindingId;

      // Temporary review-status colors.
      let strokeColor = "#06b6d4";

      if (finding.decision_status === "CONFIRMED") {
        strokeColor = "#10b981";
      } else if (finding.decision_status === "REJECTED") {
        strokeColor = "#ef4444";
      } else if (finding.decision_status === "ADJUSTED") {
        strokeColor = "#3b82f6";
      }

      // Polygon mask: draw only the defect outline.
      const polygon = finding.polygon_mask;

      if (polygon && polygon.length >= 3) {
        ctx.save();
        ctx.beginPath();

        polygon.forEach((point, index) => {
          const px = point[0] * width;
          const py = point[1] * height;

          if (index === 0) {
            ctx.moveTo(px, py);
          } else {
            ctx.lineTo(px, py);
          }
        });

        ctx.closePath();
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = isActive ? 2.5 : 1.5;
        ctx.stroke();
        ctx.restore();

        return;
      }

      // Legacy box-only findings remain visible until
      // actual segmentation masks are available.
      ctx.save();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = isActive ? 3 : 2;
      ctx.strokeRect(x, y, w, h);

      const label = `${finding.defect_class} (${(
        finding.confidence_score * 100
      ).toFixed(0)}%)`;

      ctx.font = "bold 11px 'JetBrains Mono', monospace";

      const textWidth = ctx.measureText(label).width;
      const labelY = Math.max(0, y - 18);
      const textY = Math.max(12, y - 4);

      ctx.fillStyle = strokeColor;
      ctx.fillRect(x, labelY, textWidth + 8, 18);

      ctx.fillStyle = "#070a13";
      ctx.fillText(label, x + 4, textY);
      ctx.restore();
    });
  }, [currentFindings, activeFindingId, width, height]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="canvas-overlay"
      onClick={(event) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        if (!rect.width || !rect.height) return;

        const clickX = (event.clientX - rect.left) / rect.width;
        const clickY = (event.clientY - rect.top) / rect.height;

        // Select the finding whose bounding box contains the click.
        for (const finding of currentFindings) {
          const box = finding.adjusted_bbox || finding.bbox;

          if (
            clickX >= box.x_min &&
            clickX <= box.x_max &&
            clickY >= box.y_min &&
            clickY <= box.y_max
          ) {
            onSelectFinding(finding.id);
            break;
          }
        }
      }}
    />
  );
};
