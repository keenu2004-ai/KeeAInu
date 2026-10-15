import React, { useState, useEffect, useRef } from "react";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Sparkles,
  Upload,
  Layers,
  Video as VideoIcon,
  ShieldCheck,
  PlusCircle,
  CheckCircle2
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
  createManualFinding,
  verifyMediaDefectFree
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
  const [selectedEngine, setSelectedEngine] = useState<string>("mock");
  const [allowCloudInference, setAllowCloudInference] = useState<boolean>(true);
  const [customPrompts, setCustomPrompts] = useState<string>("defect, crack, pitting, corrosion");
  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(0.5);
  const [useCache, setUseCache] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isManualModalOpen, setIsManualModalOpen] = useState<boolean>(false);
  const [manualDefectClass, setManualDefectClass] = useState<string>("CRACK");
  const [manualBbox, setManualBbox] = useState({ x_min: 0.2, y_min: 0.2, x_max: 0.6, y_max: 0.6 });
  const [manualNotes, setManualNotes] = useState<string>("");
  const [savingManual, setSavingManual] = useState<boolean>(false);
  const [certifyingDefectFree, setCertifyingDefectFree] = useState<boolean>(false);
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

  const handleSelectFinding = (findingId: string) => {
    setActiveFindingId(findingId);
    const target = findings.find((f) => f.id === findingId);
    if (!target) return;

    // Switch media item if finding belongs to another media
    if (session.media && target.media_id && target.media_id !== activeMedia?.id) {
      const mediaIdx = session.media.findIndex((m) => m.id === target.media_id);
      if (mediaIdx !== -1) {
        setActiveMediaIndex(mediaIdx);
      }
    }

    // Seek to finding frame
    if (target.frame_index !== undefined && target.frame_index >= 0) {
      handleSeekFrame(target.frame_index);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!newStatus || newStatus === session.status) return;
    try {
      const updated = await updateSessionStatus(session.id, newStatus);
      onSessionUpdated(updated);
    } catch (err: any) {
      alert(`Status transition failed: ${err.message}`);
    }
  };

  const handleCertifyDefectFree = async () => {
    if (!activeMedia) return;
    const confirmCert = window.confirm(
      `Explicitly certify "${activeMedia.filename}" as Defect-Free Negative Ground Truth?\n\nThis records immutable SHA-256 evidence under inspector: ${session.inspector_name}.`
    );
    if (!confirmCert) return;

    try {
      setCertifyingDefectFree(true);
      await verifyMediaDefectFree(activeMedia.id, {
        inspector_name: session.inspector_name,
        notes: "Human inspector verified zero defects on this media asset."
      });
      const updatedMediaList = (session.media || []).map((m) =>
        m.id === activeMedia.id
          ? {
              ...m,
              is_verified_defect_free: true,
              verified_defect_free_by: session.inspector_name,
              verified_defect_free_at: new Date().toISOString()
            }
          : m
      );
      onSessionUpdated({ ...session, media: updatedMediaList });
      alert(`Media "${activeMedia.filename}" successfully certified defect-free.`);
    } catch (err: any) {
      alert(`Defect-free certification failed: ${err.message}`);
    } finally {
      setCertifyingDefectFree(false);
    }
  };

  const handleSaveManualFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMedia) return;
    try {
      setSavingManual(true);
      const newFinding = await createManualFinding(activeMedia.id, {
        defect_class: manualDefectClass,
        bbox: manualBbox,
        frame_index: currentFrame,
        timestamp_ms: activeMedia.fps > 0 ? (currentFrame / activeMedia.fps) * 1000 : 0,
        inspector_name: session.inspector_name,
        notes: manualNotes || "Human expert annotated defect.",
      });
      setFindings((prev) => [...prev, newFinding]);
      setActiveFindingId(newFinding.id);
      setIsManualModalOpen(false);
      setManualNotes("");
    } catch (err: any) {
      alert(`Manual annotation failed: ${err.message}`);
    } finally {
      setSavingManual(false);
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
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "0.95rem", fontWeight: "700" }}>
                  {activeMedia ? activeMedia.filename : "No Media Uploaded"}
                </span>
                {activeMedia?.is_verified_defect_free && (
                  <span style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#10b981",
                    border: "1px solid rgba(16, 185, 129, 0.4)",
                    borderRadius: "6px",
                    padding: "2px 8px",
                    fontSize: "0.75rem",
                    fontWeight: 700
                  }}>
                    <CheckCircle2 size={13} />
                    VERIFIED NEGATIVE
                  </span>
                )}
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
              disabled={session.status === "ARCHIVED"}
              onChange={(e) => handleStatusChange(e.target.value)}
            >
              <option value={session.status}>{session.status} (Current)</option>
              {session.status === "DRAFT" && (
                <>
                  <option value="IN_REVIEW">Move to IN_REVIEW</option>
                  <option value="ARCHIVED">Archive Session</option>
                </>
              )}
              {session.status === "IN_REVIEW" && (
                <>
                  <option value="DRAFT">Return to DRAFT</option>
                  <option value="COMPLETED">Complete Inspection</option>
                  <option value="ARCHIVED">Archive Session</option>
                </>
              )}
              {session.status === "COMPLETED" && (
                <option value="ARCHIVED">Archive Inspection</option>
              )}
            </select>

            <button
              className="btn btn-secondary btn-sm"
              style={{
                borderColor: activeMedia?.is_verified_defect_free ? "#10b981" : "var(--border-subtle)",
                color: activeMedia?.is_verified_defect_free ? "#10b981" : undefined
              }}
              onClick={handleCertifyDefectFree}
              disabled={certifyingDefectFree || !activeMedia}
              title="Certify active image/video as verified defect-free negative ground truth"
            >
              <ShieldCheck size={14} color={activeMedia?.is_verified_defect_free ? "#10b981" : undefined} />
              {certifyingDefectFree ? "Certifying..." : activeMedia?.is_verified_defect_free ? "Certified Defect-Free" : "Certify Defect-Free"}
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setIsManualModalOpen(true)}
              disabled={!activeMedia}
              title="Add genuine human ground-truth defect finding"
            >
              <PlusCircle size={14} color="#06b6d4" />
              Add Human Defect
            </button>

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
                    onSelectFinding={handleSelectFinding}
                    width={displaySize.width}
                    height={displaySize.height}
                    activeMediaId={activeMedia.id}
                    isStillImage={false}
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
                    onSelectFinding={handleSelectFinding}
                    width={displaySize.width}
                    height={displaySize.height}
                    activeMediaId={activeMedia.id}
                    isStillImage={true}
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
                    <option value="mock">Mock Baseline (Simulated)</option>
                    <option value="onnx_local">Local ONNX (In-House Offline)</option>
                    <option value="roboflow">Roboflow SAM 3 (Cloud API Key Required)</option>
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
        onSelectFinding={handleSelectFinding}
        onReviewSubmitted={handleReviewSubmitted}
        inspectorName={session.inspector_name}
        mediaList={session.media}
      />

      <MediaUploadModal
        isOpen={isUploadOpen}
        sessionId={session.id}
        onClose={() => setIsUploadOpen(false)}
        onMediaUploaded={(newMedia) => {
          const updatedMediaList = [...(session.media || []), newMedia];
          onSessionUpdated({ ...session, media: updatedMediaList, media_count: updatedMediaList.length });
          setActiveMediaIndex(updatedMediaList.length - 1);
        }}
      />

      {/* Human Ground-Truth Defect Annotation Modal */}
      {isManualModalOpen && activeMedia && (
        <div className="modal-backdrop">
          <div className="modal-card" style={{ maxWidth: "500px", width: "100%" }}>
            <div className="modal-header">
              <h3 style={{ fontSize: "1.1rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "8px" }}>
                <PlusCircle size={18} color="#06b6d4" />
                Add Human Verified Defect
              </h3>
              <button
                className="btn-icon"
                onClick={() => setIsManualModalOpen(false)}
                style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "1.2rem" }}
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleSaveManualFinding} style={{ padding: "16px 20px" }}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "6px" }}>
                  Defect Category (Taxonomy)
                </label>
                <select
                  className="form-select"
                  value={manualDefectClass}
                  onChange={(e) => setManualDefectClass(e.target.value)}
                  style={{ width: "100%" }}
                  required
                >
                  <option value="CRACK">CRACK (Structural / Fatigue Crack)</option>
                  <option value="THERMAL_CRACKING">THERMAL_CRACKING (Thermal Fatigue Crazing)</option>
                  <option value="CHIPPING">CHIPPING (Coating / Edge Flake)</option>
                  <option value="CORROSION">CORROSION (Oxidation / Chemical Attack)</option>
                  <option value="RUSTING">RUSTING (Surface Ferrous Rust)</option>
                  <option value="PITTING">PITTING (Cavity / Localized Pit)</option>
                  <option value="DIRT">DIRT (Surface Particulate / Soot)</option>
                  <option value="SCORING_SCRATCH">SCORING_SCRATCH (Mechanical Abrasive Gouge)</option>
                  <option value="DEPOSIT_FOULING">DEPOSIT_FOULING (Caked Deposit)</option>
                  <option value="FOREIGN_OBJECT_DAMAGE">FOREIGN_OBJECT_DAMAGE (Impact / Dent)</option>
                  <option value="SURFACE_SPALLING">SURFACE_SPALLING (Spall)</option>
                  <option value="OTHER_DEFECT">OTHER_DEFECT (Non-standard Defect)</option>
                </select>
              </div>

              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "6px" }}>
                  Normalized Bounding Box [x_min, y_min, x_max, y_max] (0.0 to 1.0)
                </label>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                  <div>
                    <span style={{ fontSize: "0.7rem", color: "#64748b" }}>x_min:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.0"
                      max="0.99"
                      className="form-input"
                      value={manualBbox.x_min}
                      onChange={(e) => setManualBbox({ ...manualBbox, x_min: parseFloat(e.target.value) || 0 })}
                      required
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: "0.7rem", color: "#64748b" }}>y_min:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.0"
                      max="0.99"
                      className="form-input"
                      value={manualBbox.y_min}
                      onChange={(e) => setManualBbox({ ...manualBbox, y_min: parseFloat(e.target.value) || 0 })}
                      required
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: "0.7rem", color: "#64748b" }}>x_max:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="1.0"
                      className="form-input"
                      value={manualBbox.x_max}
                      onChange={(e) => setManualBbox({ ...manualBbox, x_max: parseFloat(e.target.value) || 1 })}
                      required
                    />
                  </div>
                  <div>
                    <span style={{ fontSize: "0.7rem", color: "#64748b" }}>y_max:</span>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      max="1.0"
                      className="form-input"
                      value={manualBbox.y_max}
                      onChange={(e) => setManualBbox({ ...manualBbox, y_max: parseFloat(e.target.value) || 1 })}
                      required
                    />
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "6px" }}>
                  Inspector Notes / Verification Rationale
                </label>
                <textarea
                  className="form-input"
                  style={{ width: "100%", height: "60px", resize: "none" }}
                  placeholder="Inspector observations, defect extent..."
                  value={manualNotes}
                  onChange={(e) => setManualNotes(e.target.value)}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setIsManualModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={savingManual}
                >
                  {savingManual ? "Saving..." : "Save Verified Finding"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
