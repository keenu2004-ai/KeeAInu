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
  const [selectedEngine, setSelectedEngine] = useState<string>("roboflow");
  const [allowCloudInference, setAllowCloudInference] = useState<boolean>(true);
  const [customPrompts, setCustomPrompts] = useState<string>("defect, crack, pitting, corrosion");
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.5);
  const [useCache, setUseCache] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [lastInferenceMeta, setLastInferenceMeta] = useState<{
    engine_name?: string;
    model_version?: string;
    is_simulated?: boolean;
    processing_duration_ms?: number;
    evidence_sha256?: string;
    cache_hit?: boolean;
    record_id?: string;
  } | null>(null);

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
      const promptList = customPrompts
        ? customPrompts.split(",").map((p) => p.trim()).filter((p) => p.length > 0)
        : undefined;

      const res = await analyzeFrame({
        session_id: session.id,
        media_id: activeMedia.id,
        frame_index: currentFrame,
        confidence_threshold: confidenceThreshold,
        engine: selectedEngine,
        prompts: promptList,
        allow_cloud_inference: allowCloudInference,
        use_cache: useCache,
      });

      setLastInferenceMeta({
        engine_name: res.engine_name,
        model_version: res.model_version,
        is_simulated: res.is_simulated,
        processing_duration_ms: res.processing_duration_ms,
        evidence_sha256: res.evidence_sha256,
        cache_hit: res.cache_hit,
        record_id: res.inference_record_id,
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
      alert(`Inference failed: ${err.message}`);
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
              <div className="playback-controls-row" style={{ flexWrap: "wrap", gap: "10px", alignItems: "center" }}>
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

                {/* AI Vision Engine Selection & Privacy Controls */}
                <div style={{ display: "flex", gap: "8px", alignItems: "center", flex: 1 }}>
                  <select
                    className="form-select"
                    style={{ fontSize: "0.8rem", padding: "4px 8px", background: "var(--bg-surface)", color: "#e2e8f0" }}
                    value={selectedEngine}
                    onChange={(e) => setSelectedEngine(e.target.value)}
                  >
                    <option value="roboflow">Roboflow SAM 3 (Segmentation)</option>
                    <option value="mock">Mock Baseline (Simulated)</option>
                  </select>

                  <input
                    type="text"
                    className="form-input"
                    style={{ fontSize: "0.8rem", padding: "4px 8px", flex: 1, minWidth: "180px" }}
                    value={customPrompts}
                    onChange={(e) => setCustomPrompts(e.target.value)}
                    placeholder="Prompts: defect, crack, pitting..."
                    title="Defect segmentation prompt labels"
                  />

                  <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", color: "#94a3b8" }}>
                    <span>Conf:</span>
                    <input
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="1.0"
                      className="form-input"
                      style={{ width: "55px", fontSize: "0.75rem", padding: "2px 4px" }}
                      value={confidenceThreshold}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value) || 0.5)}
                      title="Confidence threshold"
                    />
                  </div>

                  <label style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", color: "#94a3b8", cursor: "pointer" }} title="Cache inference results deterministically">
                    <input
                      type="checkbox"
                      checked={useCache}
                      onChange={(e) => setUseCache(e.target.checked)}
                    />
                    Cache
                  </label>

                  <label style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", color: "#94a3b8", cursor: "pointer" }} title="Allow transmitting frame to cloud vision service">
                    <input
                      type="checkbox"
                      checked={allowCloudInference}
                      onChange={(e) => setAllowCloudInference(e.target.checked)}
                    />
                    Cloud Consent
                  </label>
                </div>

                <button
                  className="btn btn-primary btn-sm"
                  style={{ background: selectedEngine === "roboflow" ? "linear-gradient(135deg, #06b6d4, #8b5cf6)" : "var(--bg-surface)" }}
                  onClick={handleAnalyzeFrame}
                  disabled={analyzing}
                >
                  <Sparkles size={15} />
                  {analyzing ? "Running Segmentation..." : selectedEngine === "roboflow" ? "SAM 3 Segment Frame" : "Run Mock Detection"}
                </button>
              </div>

              {/* Provenance and Inference Metadata Banner */}
              {lastInferenceMeta && (
                <div style={{
                  display: "flex",
                  gap: "12px",
                  alignItems: "center",
                  padding: "6px 12px",
                  background: "rgba(15, 23, 42, 0.6)",
                  borderRadius: "8px",
                  fontSize: "0.75rem",
                  fontFamily: "var(--font-mono)",
                  border: "1px solid rgba(6, 182, 212, 0.2)",
                  color: "#cbd5e1"
                }}>
                  <span style={{ color: lastInferenceMeta.is_simulated ? "#fbbf24" : "#10b981", fontWeight: 700 }}>
                    {lastInferenceMeta.is_simulated ? "[SIMULATED BASELINE]" : "[REAL SAM 3 INFERENCE]"}
                  </span>
                  <span>Engine: <strong>{lastInferenceMeta.engine_name}</strong> ({lastInferenceMeta.model_version})</span>
                  <span>Latency: <strong>{lastInferenceMeta.processing_duration_ms}ms</strong></span>
                  {lastInferenceMeta.cache_hit && <span style={{ color: "#38bdf8" }}>(Cache Hit)</span>}
                  <span>SHA-256: {lastInferenceMeta.evidence_sha256?.substring(0, 10)}...</span>
                </div>
              )}

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
