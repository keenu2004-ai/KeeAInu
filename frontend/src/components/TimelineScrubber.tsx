import React from "react";
import { ThumbnailItem, Finding } from "../types/inspection";
import { getThumbnailContentUrl } from "../services/api";

interface TimelineScrubberProps {
  mediaId: string;
  totalFrames: number;
  currentFrame: number;
  fps: number;
  durationSeconds: number;
  thumbnails: ThumbnailItem[];
  findings: Finding[];
  onSeekFrame: (frameIndex: number) => void;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  mediaId,
  totalFrames,
  currentFrame,
  fps,
  durationSeconds,
  thumbnails,
  findings,
  onSeekFrame,
}) => {
  if (totalFrames <= 1) return null;

  return (
    <div className="timeline-container">
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8" }}>
        <span>Frame {currentFrame} / {totalFrames - 1}</span>
        <span>Duration: {durationSeconds.toFixed(2)}s ({fps.toFixed(1)} FPS)</span>
      </div>

      <input
        type="range"
        min={0}
        max={totalFrames - 1}
        value={currentFrame}
        onChange={(e) => onSeekFrame(parseInt(e.target.value, 10))}
        className="timeline-scrubber"
      />

      {thumbnails.length > 0 && (
        <div className="thumbnail-strip">
          {thumbnails.map((thumb) => {
            const isActive = Math.abs(thumb.frame_index - currentFrame) <= (totalFrames / thumbnails.length);
            const hasFinding = findings.some((f) => f.frame_index === thumb.frame_index);

            return (
              <div
                key={thumb.id}
                className={`thumbnail-item ${isActive ? "active" : ""}`}
                onClick={() => onSeekFrame(thumb.frame_index)}
                title={`Jump to frame ${thumb.frame_index} (${(thumb.timestamp_ms / 1000).toFixed(2)}s)`}
              >
                <img
                  src={getThumbnailContentUrl(mediaId, thumb.id)}
                  alt={`Frame ${thumb.frame_index}`}
                  loading="lazy"
                />
                <span className="thumbnail-label">F{thumb.frame_index}</span>
                {hasFinding && (
                  <div
                    style={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#ef4444",
                      boxShadow: "0 0 6px #ef4444",
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
