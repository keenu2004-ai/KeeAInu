import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Sparkles,
  Upload,
  Layers,
  Video as VideoIcon
} from "lucide-react";
import {
  InspectionSession,
  MediaItem,
  ThumbnailItem,
  Finding,
} from "../types/inspection";
import {
  fetchMediaThumbnails,
  fetchSessionFindings,
  analyzeFrame,
  getMediaContentUrl,
  updateSessionStatus,
} from "../services/api";
import { CanvasOverlay } from "./CanvasOverlay";
import { TimelineScrubber } from "./TimelineScrubber";
import { ReviewPanel } from "./ReviewPanel";
import { MediaUploadModal } from "./MediaUploadModal";

interface InspectionWorkspaceProps {
  session: InspectionSession;
  onSessionUpdated: (updated: InspectionSession) => void;
}

export const InspectionWorkspace: React.FC<InspectionWorkspaceProps> = ({
  session,
  onSessionUpdated,
}) => {
  const [activeMediaIndex, setActiveMediaIndex] = useState(0);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [thumbnails, setThumbnails] = useState<ThumbnailItem[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [displaySize, setDisplaySize] = useState({ width: 640, height: 480 });

  const activeMedia: MediaItem | undefined = session.media?.[activeMediaIndex];

  // Load thumbnails and findings on media change
  useEffect(() => {
    if (!activeMedia) return;

    setCurrentFrame(0);
    setIsPlaying(false);

    // Fetch thumbnails
    if (activeMedia.media_type.startsWith("video/")) {
      fetchMediaThumbnails(activeMedia.id).then(setThumbnails).catch(console.error);
    } else {
      setThumbnails([]);
    }

    // Fetch existing session findings
    fetchSessionFindings(session.id).then(setFindings).catch(console.error);
  }, [activeMedia?.id, session.id]);

  // Sync video element time with current frame
  const handleTimeUpdate = () => {
    if (!videoRef.current || !activeMedia || activeMedia.fps <= 0) return;
    const frame = Math.floor(videoRef.current.currentTime * activeMedia.fps);
    setCurrentFrame(Math.min(frame, (activeMedia.total_frames || 1) - 1));
  };

  const handleSeekFrame = (targetFrame: number) => {
    if (!activeMedia) return;
    const clamped = Math.max(0, Math.min(targetFrame, (activeMedia.total_frames || 1) - 1));
    setCurrentFrame(clamped);

    if (videoRef.current && activeMedia.fps > 0) {
      videoRef.current.currentTime = clamped / activeMedia.fps;
    }
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const stepFrame = (delta: number) => {
    if (isPlaying && videoRef.current) {
      videoRef.current.pause();
      setIsPlaying(false);
    }
    handleSeekFrame(currentFrame + delta);
  };

  const handleAnalyzeFrame = async () => {
    if (!activeMedia) return;
    try {
      setAnalyzing(true);
      const res = await analyzeFrame({
        session_id: session.id,
        media_id: activeMedia.id,
        frame_index: currentFrame,
        confidence_threshold: 0.5,
      });

      // Append new findings
      setFindings((prev) => {
        const existingIds = new Set(prev.map((f) => f.id));
        const added = res.findings.filter((f) => !existingIds.has(f.id));
        return [...prev, ...added];
      });

      if (res.findings.length > 0) {
        setActiveFindingId(res.findings[0].id);
      }
    } catch (err: any) {
      alert(`Analysis failed: ${err.message}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReviewSubmitted = (updatedFinding: Finding) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === updatedFinding.id ? updatedFinding : f))
    );
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      const updated = await updateSessionStatus(session.id, newStatus);
      onSessionUpdated(updated);
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="workspace-layout">
      {/* Viewport & Controls */}
      <div className="viewport-section">
        {/* Media Selector / Status Bar */}
        <div className="session-card-header" style={{ background: "var(--bg-card)", padding: "12px 18px", borderRadius: "12px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <VideoIcon size={20} color="#06b6d4" />
            <div>
              <div style={{ fontSize: "0.95rem", fontWeight: "700" }}>
                {activeMedia ? activeMedia.filename : "No Media Uploaded"}
              </div>
              {activeMedia && (
                <div style={{ fontSize: "0.75rem", color: "#94a3b8", display: "flex", gap: "12px", fontFamily: "var(--font-mono)" }}>
                  <span>{activeMedia.width}x{activeMedia.height}</span>
                  <span>{activeMedia.fps && activeMedia.fps > 0 ? `${activeMedia.fps} FPS` : "FPS: N/A"}</span>
                  <span>SHA-256: {activeMedia.sha256_hash.substring(0, 10)}...</span>
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <select
              className="form-select"
              style={{ fontSize: "0.8rem", padding: "4px 10px" }}
              value={session.status}
              onChange={(e) => handleStatusChange(e.target.value)}
            >
              <option value="DRAFT">DRAFT</option>
              <option value="IN_REVIEW">IN_REVIEW</option>
              <option value="COMPLETED">COMPLETED</option>
            </select>

            <button className="btn btn-secondary btn-sm" onClick={() => setIsUploadOpen(true)}>
              <Upload size={14} />
              Add Media
            </button>
          </div>
        </div>

        {/* Viewport Frame Container */}
        <div className="viewport-card">
          <div className="viewport-header">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={16} color="#06b6d4" />
              <span style={{ fontSize: "0.85rem", fontWeight: "700" }}>INSPECTION VIEWPORT</span>
            </div>
            {activeMedia && (
              <span className="time-display">
                Frame {currentFrame}
                {activeMedia.fps && activeMedia.fps > 0 ? (
                  <> | TS: ~{((currentFrame / activeMedia.fps) * 1000).toFixed(1)}ms <span style={{ fontSize: "0.75em", opacity: 0.8 }}>(Nominal)</span></>
                ) : (
                  <> | TS: N/A</>
                )}
              </span>
            )}
          </div>

          <div className="media-display-area" ref={containerRef}>
            {activeMedia ? (
              activeMedia.media_type.startsWith("video/") ? (
                <>
                  <video
                    ref={videoRef}
                    src={getMediaContentUrl(activeMedia.id)}
                    className="video-element"
                    onTimeUpdate={handleTimeUpdate}
                    onEnded={() => setIsPlaying(false)}
                    onLoadedMetadata={(e) => {
                      const v = e.currentTarget;
                      setDisplaySize({ width: v.clientWidth || 640, height: v.clientHeight || 480 });
                    }}
                  />
                  <CanvasOverlay
                    findings={findings}
                    currentFrameIndex={currentFrame}
                    activeFindingId={activeFindingId}
                    onSelectFinding={setActiveFindingId}
                    width={displaySize.width}
                    height={displaySize.height}
                  />
                </>
              ) : (
                <>
                  <img
                    src={getMediaContentUrl(activeMedia.id)}
                    alt="Inspection Frame"
                    className="image-element"
                    onLoad={(e) => {
                      const img = e.currentTarget;
                      setDisplaySize({ width: img.clientWidth || 640, height: img.clientHeight || 480 });
                    }}
                  />
                  <CanvasOverlay
                    findings={findings}
                    currentFrameIndex={0}
                    activeFindingId={activeFindingId}
                    onSelectFinding={setActiveFindingId}
                    width={displaySize.width}
                    height={displaySize.height}
                  />
                </>
              )
            ) : (
              <div className="empty-state">
                <Upload size={40} color="#64748b" />
                <p>No inspection media attached.</p>
                <button className="btn btn-primary btn-sm" onClick={() => setIsUploadOpen(true)}>
                  Upload Footage Now
                </button>
              </div>
            )}
          </div>

          {/* Viewport Playback and Action Controls */}
          {activeMedia && (
            <div className="viewport-controls">
              <div className="playback-controls-row">
                <div className="playback-buttons">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => stepFrame(-1)}
                    title="Previous Frame (Left Arrow)"
                  >
                    <SkipBack size={15} />
                  </button>

                  {activeMedia.media_type.startsWith("video/") && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={togglePlay}
                      title="Play/Pause (Space)"
                    >
                      {isPlaying ? <Pause size={15} /> : <Play size={15} />}
                      {isPlaying ? "Pause" : "Play"}
                    </button>
                  )}

                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => stepFrame(1)}
                    title="Next Frame (Right Arrow)"
                  >
                    <SkipForward size={15} />
                  </button>
                </div>

                <button
                  className="btn btn-primary btn-sm"
                  style={{ background: "linear-gradient(135deg, #06b6d4, #8b5cf6)" }}
                  onClick={handleAnalyzeFrame}
                  disabled={analyzing}
                >
                  <Sparkles size={15} />
                  {analyzing ? "Analyzing Frame..." : "Run AI Defect Detection"}
                </button>
              </div>

              {/* Timeline scrubber with thumbnails */}
              {activeMedia.media_type.startsWith("video/") && (
                <TimelineScrubber
                  mediaId={activeMedia.id}
                  totalFrames={activeMedia.total_frames}
                  currentFrame={currentFrame}
                  fps={activeMedia.fps}
                  durationSeconds={activeMedia.duration_seconds}
                  thumbnails={thumbnails}
                  findings={findings}
                  onSeekFrame={handleSeekFrame}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Review Panel Sidebar */}
      <ReviewPanel
        findings={findings}
        activeFindingId={activeFindingId}
        onSelectFinding={setActiveFindingId}
        onReviewSubmitted={handleReviewSubmitted}
        inspectorName={session.inspector_name}
      />

      <MediaUploadModal
        isOpen={isUploadOpen}
        sessionId={session.id}
        onClose={() => setIsUploadOpen(false)}
        onMediaUploaded={(newMedia) => {
          const updatedMediaList = [...(session.media || []), newMedia];
          onSessionUpdated({ ...session, media: updatedMediaList });
          setActiveMediaIndex(updatedMediaList.length - 1);
        }}
      />
    </div>
  );
};
