import React, { useState, useEffect } from "react";
import {
  Search,
  RefreshCw,
  FileVideo,
  FileImage,
  Layers,
  Sparkles,
  Sliders,
  Download,
  Info,
  FolderOpen
} from "lucide-react";
import {
  AssetRecord,
  DomainCategory,
  DomainConfidence,
  SampleReviewStatus,
  DiscoveryReport
} from "../types/discovery";
import {
  fetchDiscoveredAssets,
  triggerDiscoveryScan,
  updateAssetDomain,
  updateSampleReview,
  fetchDiscoveryReport,
  getContactSheetUrl,
  getSampleImageUrl,
  getManifestUrl
} from "../services/api";

export const DatasetDiscoveryView: React.FC = () => {
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null);
  const [report, setReport] = useState<DiscoveryReport | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);

  // Filter states
  const [domainFilter, setDomainFilter] = useState<string>("ALL");
  const [provenanceFilter, setProvenanceFilter] = useState<string>("ALL");
  const [customDir, setCustomDir] = useState<string>("");
  const [sampleCount, setSampleCount] = useState<number>(5);
  const [reviewerName, setReviewerName] = useState<string>("Inspector (NDT)");

  const loadAssets = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (domainFilter !== "ALL") params.domain = domainFilter;
      if (provenanceFilter === "REAL") params.is_synthetic = false;
      if (provenanceFilter === "SYNTHETIC") params.is_synthetic = true;

      const data = await fetchDiscoveredAssets(params);
      setAssets(data);

      const rep = await fetchDiscoveryReport();
      setReport(rep);
    } catch (err: any) {
      console.error("Failed to load discovery assets:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAssets();
  }, [domainFilter, provenanceFilter]);

  const handleRunScan = async (force: boolean = false) => {
    try {
      setScanning(true);
      await triggerDiscoveryScan({
        source_directory: customDir.trim() || undefined,
        sample_count_per_video: sampleCount,
        force_rescan: force,
      });
      await loadAssets();
    } catch (err: any) {
      alert(`Scan failed: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  const handleDomainChange = async (
    assetId: string,
    domain: DomainCategory,
    confidence: DomainConfidence = "PROVISIONAL",
    notes: string = ""
  ) => {
    try {
      const updated = await updateAssetDomain(assetId, {
        domain_assignment: domain,
        domain_confidence: confidence,
        domain_notes: notes,
        reviewed_by: reviewerName,
      });
      setAssets((prev) => prev.map((a) => (a.id === assetId ? updated : a)));
      if (selectedAsset?.id === assetId) {
        setSelectedAsset(updated);
      }
      const rep = await fetchDiscoveryReport();
      setReport(rep);
    } catch (err: any) {
      alert(`Failed to update domain: ${err.message}`);
    }
  };

  const handleSampleReviewChange = async (
    sampleId: string,
    status: SampleReviewStatus,
    category?: string,
    notes?: string
  ) => {
    try {
      const updatedSample = await updateSampleReview(sampleId, {
        review_status: status,
        suspected_category: category,
        reviewer_notes: notes,
        reviewed_by: reviewerName,
      });

      if (selectedAsset) {
        const updatedSamples = selectedAsset.samples.map((s) =>
          s.id === sampleId ? updatedSample : s
        );
        setSelectedAsset({ ...selectedAsset, samples: updatedSamples });
      }

      setAssets((prev) =>
        prev.map((a) => {
          if (a.id === selectedAsset?.id) {
            return {
              ...a,
              samples: a.samples.map((s) => (s.id === sampleId ? updatedSample : s)),
            };
          }
          return a;
        })
      );

      const rep = await fetchDiscoveryReport();
      setReport(rep);
    } catch (err: any) {
      alert(`Failed to update sample review: ${err.message}`);
    }
  };

  const getDomainBadgeColor = (dom: string) => {
    switch (dom) {
      case "MECHANICAL":
        return "#3b82f6";
      case "PIPES_CHANNELS":
        return "#10b981";
      case "MOULD_CAVITIES":
        return "#8b5cf6";
      case "OTHER":
        return "#f59e0b";
      default:
        return "#64748b";
    }
  };

  const getReviewBadgeStyle = (status: SampleReviewStatus) => {
    switch (status) {
      case "CONFIRMED_DEFECT":
        return { background: "rgba(239, 68, 68, 0.2)", color: "#ef4444", border: "1px solid #ef4444" };
      case "SUSPECTED_ANOMALY":
        return { background: "rgba(245, 158, 11, 0.2)", color: "#f59e0b", border: "1px solid #f59e0b" };
      case "NO_VISIBLE_DEFECT":
        return { background: "rgba(16, 185, 129, 0.2)", color: "#10b981", border: "1px solid #10b981" };
      case "UNCERTAIN_NEEDS_EXPERT":
        return { background: "rgba(139, 92, 246, 0.2)", color: "#8b5cf6", border: "1px solid #8b5cf6" };
      case "UNUSABLE":
        return { background: "rgba(100, 116, 139, 0.2)", color: "#94a3b8", border: "1px solid #64748b" };
      default:
        return { background: "rgba(51, 65, 85, 0.4)", color: "#cbd5e1", border: "1px solid #475569" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Banner & Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px" }}>
        <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>Discovered Assets</span>
          <span style={{ fontSize: "1.8rem", fontWeight: "800", color: "#06b6d4" }}>{report?.total_assets ?? 0}</span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
            {report?.real_assets_count ?? 0} Real Vault | {report?.synthetic_assets_count ?? 0} Synthetic
          </span>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>Metadata Integrity</span>
          <span style={{ fontSize: "1.8rem", fontWeight: "800", color: "#10b981" }}>
            {report?.metadata_completeness_percent ?? 0}%
          </span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
            {report?.readable_assets_count ?? 0} Readable | {report?.unreadable_assets_count ?? 0} Unreadable
          </span>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>Samples Profiled</span>
          <span style={{ fontSize: "1.8rem", fontWeight: "800", color: "#8b5cf6" }}>
            {report?.total_samples_extracted ?? 0}
          </span>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
            Avg Sharpness: {report?.average_sharpness ?? 0}
          </span>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", textTransform: "uppercase" }}>Domain Triage</span>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
            {report && Object.entries(report.domain_breakdown).map(([dom, count]) => (
              <span
                key={dom}
                style={{
                  fontSize: "0.7rem",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: "var(--bg-card-hover)",
                  color: getDomainBadgeColor(dom),
                  fontWeight: "600"
                }}
              >
                {dom}: {count}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Action Controls & Scanner Toolbar */}
      <div className="card" style={{ padding: "16px", display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <FolderOpen size={16} color="#06b6d4" />
            <input
              type="text"
              placeholder="Source dir (e.g. data/source_footage)"
              value={customDir}
              onChange={(e) => setCustomDir(e.target.value)}
              className="form-control"
              style={{ fontSize: "0.8rem", width: "240px", padding: "6px 10px" }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <Sliders size={14} color="#94a3b8" />
            <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Samples/Video:</span>
            <select
              value={sampleCount}
              onChange={(e) => setSampleCount(parseInt(e.target.value, 10))}
              className="form-select"
              style={{ fontSize: "0.8rem", padding: "6px 10px" }}
            >
              <option value={3}>3 Samples</option>
              <option value={5}>5 Samples</option>
              <option value={8}>8 Samples</option>
              <option value={10}>10 Samples</option>
            </select>
          </div>

          <button
            className="btn btn-primary btn-sm"
            onClick={() => handleRunScan(false)}
            disabled={scanning}
          >
            <Search size={14} />
            {scanning ? "Scanning..." : "Run Discovery Scan"}
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => handleRunScan(true)}
            disabled={scanning}
            title="Force re-sampling & re-profiling of all files"
          >
            <RefreshCw size={14} />
            Force Re-Scan
          </button>
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setIsReportOpen(true)}>
            <Info size={14} />
            Discovery Report
          </button>

          <a
            href={getManifestUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary btn-sm"
            download="keeainu_discovery_manifest.json"
          >
            <Download size={14} />
            Export Manifest
          </a>
        </div>
      </div>

      {/* Filters Toolbar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Domain:</span>
          <select
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="form-select"
            style={{ fontSize: "0.8rem", padding: "4px 8px" }}
          >
            <option value="ALL">All Domains</option>
            <option value="MECHANICAL">Mechanical (Engines/Turbines)</option>
            <option value="PIPES_CHANNELS">Pipes & Channels</option>
            <option value="MOULD_CAVITIES">Mould Cavities</option>
            <option value="OTHER">Other / Different</option>
            <option value="UNKNOWN">Unknown / Insufficient Evidence</option>
          </select>

          <span style={{ fontSize: "0.8rem", color: "#94a3b8", marginLeft: "10px" }}>Provenance:</span>
          <select
            value={provenanceFilter}
            onChange={(e) => setProvenanceFilter(e.target.value)}
            className="form-select"
            style={{ fontSize: "0.8rem", padding: "4px 8px" }}
          >
            <option value="ALL">All Assets</option>
            <option value="REAL">Real Footage Only</option>
            <option value="SYNTHETIC">Synthetic Fixtures Only</option>
          </select>
        </div>

        <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
          Showing {assets.length} assets
        </span>
      </div>

      {/* Asset Grid & Gallery */}
      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px" }} />
          Loading asset inventory...
        </div>
      ) : assets.length === 0 ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>
          <FileVideo size={40} color="#64748b" style={{ margin: "0 auto 16px" }} />
          <h3 style={{ color: "#f8fafc", marginBottom: "8px" }}>No Discovered Assets Found</h3>
          <p style={{ fontSize: "0.85rem", maxWidth: "500px", margin: "0 auto 16px" }}>
            Place raw inspection footage into <code style={{ color: "#06b6d4" }}>data/source_footage/</code> or click
            "Run Discovery Scan" to profile existing vaults and synthetic test fixtures.
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => handleRunScan(false)} style={{ margin: "0 auto" }}>
            Scan Default Vaults
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "16px" }}>
          {assets.map((asset) => {
            const hasContact = Boolean(asset.contact_sheet_path);
            const domColor = getDomainBadgeColor(asset.domain_assignment);

            return (
              <div
                key={asset.id}
                className="card"
                style={{
                  padding: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  cursor: "pointer",
                  border: selectedAsset?.id === asset.id ? "1px solid #06b6d4" : "1px solid var(--border-subtle)",
                }}
                onClick={() => setSelectedAsset(asset)}
              >
                {/* Header & Badges */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {asset.asset_type === "video" ? (
                      <FileVideo size={18} color="#06b6d4" />
                    ) : (
                      <FileImage size={18} color="#10b981" />
                    )}
                    <div style={{ fontWeight: "700", fontSize: "0.9rem", color: "#f8fafc", wordBreak: "break-all" }}>
                      {asset.filename}
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: "0.65rem",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontWeight: "700",
                      background: asset.is_synthetic ? "rgba(148, 163, 184, 0.2)" : "rgba(6, 182, 212, 0.2)",
                      color: asset.is_synthetic ? "#94a3b8" : "#06b6d4",
                      border: asset.is_synthetic ? "1px solid #64748b" : "1px solid #06b6d4",
                      whiteSpace: "nowrap"
                    }}
                  >
                    {asset.is_synthetic ? "SYNTHETIC" : "REAL EVIDENCE"}
                  </span>
                </div>

                {/* Preview Image / Contact Sheet Thumbnail */}
                <div
                  style={{
                    width: "100%",
                    height: "160px",
                    background: "#070a13",
                    borderRadius: "8px",
                    overflow: "hidden",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "1px solid var(--border-subtle)",
                    position: "relative"
                  }}
                >
                  {hasContact ? (
                    <img
                      src={getContactSheetUrl(asset.id)}
                      alt={asset.filename}
                      style={{ width: "100%", height: "100%", objectFit: "contain" }}
                      loading="lazy"
                    />
                  ) : asset.samples.length > 0 ? (
                    <img
                      src={getSampleImageUrl(asset.samples[0].id)}
                      alt={asset.filename}
                      style={{ width: "100%", height: "100%", objectFit: "contain" }}
                      loading="lazy"
                    />
                  ) : (
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>No Preview Available</span>
                  )}

                  <span
                    style={{
                      position: "absolute",
                      bottom: "6px",
                      right: "6px",
                      fontSize: "0.65rem",
                      background: "rgba(0,0,0,0.75)",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      fontFamily: "var(--font-mono)",
                      color: "#cbd5e1"
                    }}
                  >
                    {asset.samples_count} Samples
                  </span>
                </div>

                {/* Metadata details */}
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8", fontFamily: "var(--font-mono)" }}>
                  <span>{asset.width}x{asset.height}</span>
                  <span>{asset.fps > 0 ? `${asset.fps} FPS` : "FPS: N/A"}</span>
                  <span>{(asset.file_size_bytes / 1024).toFixed(1)} KB</span>
                </div>

                {/* Quality & Domain Indicators */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span
                      style={{
                        fontSize: "0.7rem",
                        fontWeight: "700",
                        padding: "2px 8px",
                        borderRadius: "12px",
                        background: `${domColor}22`,
                        color: domColor,
                        border: `1px solid ${domColor}`
                      }}
                    >
                      {asset.domain_assignment}
                    </span>
                  </div>

                  {asset.quality_profile && (
                    <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.7rem", color: asset.quality_profile.blur_detected ? "#f59e0b" : "#10b981" }}>
                      <Sparkles size={12} />
                      <span>Sharpness: {asset.quality_profile.sharpness_score}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Asset Detail & Sample Review Drawer */}
      {selectedAsset && (
        <div
          style={{
            position: "fixed",
            top: 0,
            right: 0,
            bottom: 0,
            width: "600px",
            maxWidth: "90vw",
            background: "var(--bg-card)",
            borderLeft: "1px solid var(--border-subtle)",
            zIndex: 1000,
            padding: "24px",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
            overflowY: "auto",
            boxShadow: "-10px 0 30px rgba(0,0,0,0.5)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Layers size={18} color="#06b6d4" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: "#f8fafc" }}>{selectedAsset.filename}</h3>
              </div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", fontFamily: "var(--font-mono)", marginTop: "4px" }}>
                SHA-256: {selectedAsset.sha256_hash}
              </div>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedAsset(null)}
              style={{ padding: "4px 8px" }}
            >
              ✕
            </button>
          </div>

          {/* Contact Sheet Preview */}
          {selectedAsset.contact_sheet_path && (
            <div>
              <div style={{ fontSize: "0.8rem", fontWeight: "700", color: "#94a3b8", marginBottom: "8px" }}>
                REPRESENTATIVE CONTACT SHEET MOSAIC
              </div>
              <div style={{ background: "#070a13", borderRadius: "8px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
                <img
                  src={getContactSheetUrl(selectedAsset.id)}
                  alt="Contact Sheet"
                  style={{ width: "100%", height: "auto", display: "block" }}
                />
              </div>
            </div>
          )}

          {/* Explainable Quality Heuristics */}
          {selectedAsset.quality_profile && (
            <div className="card" style={{ padding: "14px", background: "var(--bg-dark)" }}>
              <div style={{ fontSize: "0.8rem", fontWeight: "700", color: "#06b6d4", marginBottom: "8px", display: "flex", alignItems: "center", gap: "6px" }}>
                <Sparkles size={14} />
                EXPLAINABLE QUALITY PROFILE (HEURISTICS)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                <div>Sharpness: <strong>{selectedAsset.quality_profile.sharpness_score}</strong></div>
                <div>Brightness: <strong>{selectedAsset.quality_profile.brightness_mean}/255</strong></div>
                <div>Contrast Std: <strong>{selectedAsset.quality_profile.contrast_std}</strong></div>
                <div>Overexposure: <strong>{(selectedAsset.quality_profile.overexposure_ratio * 100).toFixed(1)}%</strong></div>
                <div>Static Frame Ratio: <strong>{(selectedAsset.quality_profile.near_duplicate_ratio * 100).toFixed(1)}%</strong></div>
                <div>Meta Reliability: <strong>{selectedAsset.quality_profile.metadata_reliability}</strong></div>
              </div>

              {selectedAsset.quality_profile.explanations.length > 0 && (
                <div style={{ marginTop: "10px", borderTop: "1px solid var(--border-subtle)", paddingTop: "8px" }}>
                  {selectedAsset.quality_profile.explanations.map((exp, idx) => (
                    <div key={idx} style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>
                      • {exp}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Domain Review Assignment Form */}
          <div className="card" style={{ padding: "14px" }}>
            <div style={{ fontSize: "0.8rem", fontWeight: "700", color: "#f8fafc", marginBottom: "10px" }}>
              INSPECTION DOMAIN REVIEW
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Candidate Domain:</label>
                <select
                  value={selectedAsset.domain_assignment}
                  onChange={(e) =>
                    handleDomainChange(
                      selectedAsset.id,
                      e.target.value as DomainCategory,
                      selectedAsset.domain_confidence,
                      selectedAsset.domain_notes || ""
                    )
                  }
                  className="form-select"
                  style={{ width: "100%", marginTop: "4px" }}
                >
                  <option value="UNKNOWN">UNKNOWN (Insufficient / Indeterminate Evidence)</option>
                  <option value="MECHANICAL">MECHANICAL (Engines, Turbines, Gearboxes)</option>
                  <option value="PIPES_CHANNELS">PIPES & CHANNELS (Tubes, Boiler Internal Surfaces)</option>
                  <option value="MOULD_CAVITIES">MOULD CAVITIES (Casting Dies, Cavities)</option>
                  <option value="OTHER">OTHER (Different Domain)</option>
                </select>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Confidence Level:</label>
                  <select
                    value={selectedAsset.domain_confidence}
                    onChange={(e) =>
                      handleDomainChange(
                        selectedAsset.id,
                        selectedAsset.domain_assignment,
                        e.target.value as DomainConfidence,
                        selectedAsset.domain_notes || ""
                      )
                    }
                    className="form-select"
                    style={{ width: "100%", marginTop: "4px" }}
                  >
                    <option value="PROVISIONAL">PROVISIONAL</option>
                    <option value="CERTAIN">CERTAIN</option>
                    <option value="UNCERTAIN">UNCERTAIN</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Reviewer Name:</label>
                  <input
                    type="text"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    className="form-control"
                    style={{ width: "100%", marginTop: "4px" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Reviewer Domain Notes:</label>
                <textarea
                  placeholder="Record observations regarding component structure, surface finish, scale..."
                  value={selectedAsset.domain_notes || ""}
                  onChange={(e) =>
                    setSelectedAsset({ ...selectedAsset, domain_notes: e.target.value })
                  }
                  onBlur={(e) =>
                    handleDomainChange(
                      selectedAsset.id,
                      selectedAsset.domain_assignment,
                      selectedAsset.domain_confidence,
                      e.target.value
                    )
                  }
                  className="form-control"
                  rows={2}
                  style={{ width: "100%", marginTop: "4px" }}
                />
              </div>
            </div>
          </div>

          {/* Sample Frames Gallery & Defect Triage */}
          <div>
            <div style={{ fontSize: "0.8rem", fontWeight: "700", color: "#f8fafc", marginBottom: "10px" }}>
              SAMPLE FRAMES & DEFECT TRIAGE ({selectedAsset.samples.length})
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {selectedAsset.samples.map((sample) => {
                const badgeStyle = getReviewBadgeStyle(sample.review_status);

                return (
                  <div
                    key={sample.id}
                    className="card"
                    style={{ padding: "12px", display: "flex", gap: "12px", background: "var(--bg-dark)" }}
                  >
                    <img
                      src={getSampleImageUrl(sample.id)}
                      alt={`Frame ${sample.frame_index}`}
                      style={{
                        width: "120px",
                        height: "90px",
                        objectFit: "cover",
                        borderRadius: "6px",
                        border: "1px solid var(--border-subtle)"
                      }}
                      loading="lazy"
                    />

                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "0.8rem", fontWeight: "700" }}>Frame #{sample.frame_index}</span>
                        <span style={{ fontSize: "0.7rem", fontFamily: "var(--font-mono)", color: "#94a3b8" }}>
                          TS: {sample.timestamp_ms.toFixed(1)}ms ({sample.timestamp_provenance})
                        </span>
                      </div>

                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                        <button
                          className="btn btn-sm"
                          style={{ fontSize: "0.7rem", padding: "2px 6px", ...badgeStyle }}
                        >
                          {sample.review_status}
                        </button>

                        <select
                          value={sample.review_status}
                          onChange={(e) =>
                            handleSampleReviewChange(
                              sample.id,
                              e.target.value as SampleReviewStatus,
                              sample.suspected_category,
                              sample.reviewer_notes
                            )
                          }
                          className="form-select"
                          style={{ fontSize: "0.75rem", padding: "2px 6px" }}
                        >
                          <option value="UNREVIEWED">Unreviewed</option>
                          <option value="NO_VISIBLE_DEFECT">No Visible Defect</option>
                          <option value="SUSPECTED_ANOMALY">Suspected Anomaly</option>
                          <option value="CONFIRMED_DEFECT">Confirmed Defect</option>
                          <option value="UNCERTAIN_NEEDS_EXPERT">Uncertain (Needs Expert)</option>
                          <option value="UNUSABLE">Unusable (Low Quality)</option>
                        </select>
                      </div>

                      {sample.reviewer_notes && (
                        <div style={{ fontSize: "0.75rem", color: "#94a3b8", fontStyle: "italic" }}>
                          "{sample.reviewer_notes}"
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Discovery Report Modal */}
      {isReportOpen && report && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "20px"
          }}
          onClick={() => setIsReportOpen(false)}
        >
          <div
            className="card"
            style={{
              width: "700px",
              maxWidth: "100%",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px"
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Info size={20} color="#06b6d4" />
                <h3 style={{ fontSize: "1.2rem", fontWeight: "800" }}>Dataset Discovery & Profiling Report</h3>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsReportOpen(false)}>✕</button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.85rem" }}>
              <div className="card" style={{ padding: "12px", background: "var(--bg-dark)" }}>
                <div style={{ color: "#94a3b8", fontSize: "0.75rem" }}>TOTAL ASSETS</div>
                <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>{report.total_assets}</div>
                <div style={{ color: "#64748b", fontSize: "0.75rem" }}>Real: {report.real_assets_count} | Synthetic: {report.synthetic_assets_count}</div>
              </div>

              <div className="card" style={{ padding: "12px", background: "var(--bg-dark)" }}>
                <div style={{ color: "#94a3b8", fontSize: "0.75rem" }}>SAMPLES EXTRACTED</div>
                <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#06b6d4" }}>{report.total_samples_extracted}</div>
                <div style={{ color: "#64748b", fontSize: "0.75rem" }}>Avg Sharpness: {report.average_sharpness}</div>
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: "0.9rem", color: "#f8fafc", marginBottom: "8px" }}>Evaluation Split Policy (Strict)</h4>
              <div style={{ fontSize: "0.8rem", color: "#94a3b8", background: "var(--bg-dark)", padding: "10px", borderRadius: "6px", border: "1px solid var(--border-subtle)" }}>
                {report.evaluation_split_recommendation}
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: "0.9rem", color: "#f8fafc", marginBottom: "8px" }}>Unresolved Questions & Next Steps</h4>
              <ul style={{ paddingLeft: "20px", fontSize: "0.8rem", color: "#94a3b8", lineHeight: "1.6" }}>
                {report.unresolved_questions.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsReportOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
