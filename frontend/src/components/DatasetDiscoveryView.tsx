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
  FolderOpen,
  Globe,
  ShieldCheck,
  History,
  Database,
  Tag,
  BarChart3,
  UserCheck
} from "lucide-react";
import {
  AssetRecord,
  DomainCategory,
  DomainConfidence,
  SampleReviewStatus,
  DiscoveryReport
} from "../types/discovery";
import {
  SourceProviderInfo,
  DatasetCandidateRecord,
  LicensePermissionStatus,
  AcquisitionAuditEvent
} from "../types/acquisition";
import { EquipmentTaxonomyView } from "./EquipmentTaxonomyView";
import { EvaluationBenchmarkView } from "./EvaluationBenchmarkView";
import { HumanFindingsReviewView } from "./HumanFindingsReviewView";
import {
  fetchDiscoveredAssets,
  triggerDiscoveryScan,
  updateAssetDomain,
  updateSampleReview,
  fetchDiscoveryReport,
  getContactSheetUrl,
  getSampleImageUrl,
  getManifestUrl,
  fetchSourceProviders,
  searchDatasetCandidates,
  fetchDatasetCandidates,
  submitLicenseReview,
  acquireDatasetCandidate,
  generateSyntheticMedia,
  fetchAcquisitionAuditTrail
} from "../services/api";

export const DatasetDiscoveryView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    "inventory" | "catalog" | "licenses" | "synthetic" | "taxonomy" | "evaluation" | "findings" | "audit"
  >("inventory");

  // Local Footage Inventory states
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<AssetRecord | null>(null);
  const [report, setReport] = useState<DiscoveryReport | null>(null);
  const [isReportOpen, setIsReportOpen] = useState(false);

  // Filter states for inventory
  const [domainFilter, setDomainFilter] = useState<string>("ALL");
  const [provenanceFilter, setProvenanceFilter] = useState<string>("ALL");
  const [customDir, setCustomDir] = useState<string>("");
  const sampleCount = 5;
  const reviewerName = "Inspector (NDT)";

  // Catalog Discovery states
  const [providers, setProviders] = useState<SourceProviderInfo[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("borescope pipe turbine crack");
  const [targetSearchDomain, setTargetSearchDomain] = useState<string>("PIPES_CHANNELS");
  const [directVideoscopeOnly, setDirectVideoscopeOnly] = useState<boolean>(false);
  const [candidates, setCandidates] = useState<DatasetCandidateRecord[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState<DatasetCandidateRecord | null>(null);
  const [isRelevanceModalOpen, setIsRelevanceModalOpen] = useState(false);

  // License Review modal state
  const [licenseModalCandidate, setLicenseModalCandidate] = useState<DatasetCandidateRecord | null>(null);
  const [targetLicenseStatus, setTargetLicenseStatus] = useState<LicensePermissionStatus>("APPROVED_FOR_EVALUATION");
  const [targetCommRights, setTargetCommRights] = useState<"ALLOWED" | "FORBIDDEN" | "REVIEW_REQUIRED">("ALLOWED");
  const [licenseNotes, setLicenseNotes] = useState<string>("");
  const [complianceReviewer, setComplianceReviewer] = useState<string>("Compliance Officer");

  // Synthetic Studio states
  const [synthDomain, setSynthDomain] = useState<"MECHANICAL" | "PIPES_CHANNELS" | "MOULD_CAVITIES">("PIPES_CHANNELS");
  const [synthDefect, setSynthDefect] = useState<"CRACK" | "CORROSION_PIT" | "EROSION" | "DEPOSIT">("CRACK");
  const [synthCount, setSynthCount] = useState<number>(3);
  const [lightingVar, setLightingVar] = useState<number>(0.2);
  const [noiseVar, setNoiseVar] = useState<number>(0.1);
  const [blurVar, setBlurVar] = useState<number>(0.0);
  const [synthSeed, setSynthSeed] = useState<number>(42);
  const [generatingSynth, setGeneratingSynth] = useState(false);

  // Audit trail state
  const [auditEvents, setAuditEvents] = useState<AcquisitionAuditEvent[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const loadAssets = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (domainFilter !== "ALL") params.domain = domainFilter;
      if (provenanceFilter === "SYNTHETIC") params.is_synthetic = true;
      if (provenanceFilter === "REAL") params.is_synthetic = false;

      const data = await fetchDiscoveredAssets(params);
      setAssets(data);
      if (data.length > 0 && !selectedAsset) {
        setSelectedAsset(data[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadProvidersAndCandidates = async () => {
    try {
      const provs = await fetchSourceProviders();
      setProviders(provs);
      const cands = await fetchDatasetCandidates();
      setCandidates(cands);
    } catch (err) {
      console.error(err);
    }
  };

  const loadAuditTrail = async () => {
    try {
      setLoadingAudit(true);
      const events = await fetchAcquisitionAuditTrail();
      setAuditEvents(events);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    loadAssets();
    loadProvidersAndCandidates();
  }, [domainFilter, provenanceFilter]);

  useEffect(() => {
    if (activeTab === "audit") {
      loadAuditTrail();
    }
  }, [activeTab]);

  const handleScan = async (forceRescan: boolean = false) => {
    try {
      setScanning(true);
      await triggerDiscoveryScan({
        source_directory: customDir ? customDir : undefined,
        sample_count_per_video: sampleCount,
        force_rescan: forceRescan
      });
      await loadAssets();
    } catch (err) {
      alert(`Scan failed: ${err}`);
    } finally {
      setScanning(false);
    }
  };

  const handleCatalogSearch = async () => {
    try {
      setSearching(true);
      const results = await searchDatasetCandidates({
        query: searchQuery,
        target_domain: targetSearchDomain,
        provider_ids: selectedProviders.length > 0 ? selectedProviders : undefined,
        direct_videoscope_only: directVideoscopeOnly,
        max_results_per_provider: 10
      });
      setCandidates(results);
    } catch (err) {
      alert(`Search error: ${err}`);
    } finally {
      setSearching(false);
    }
  };

  const handleOpenLicenseModal = (candidate: DatasetCandidateRecord) => {
    setLicenseModalCandidate(candidate);
    setTargetLicenseStatus(candidate.license_status);
    setTargetCommRights(candidate.commercial_use_allowed ? "ALLOWED" : "FORBIDDEN");
    setLicenseNotes(candidate.limitations_notes || "");
  };

  const handleSaveLicenseReview = async () => {
    if (!licenseModalCandidate) return;
    try {
      const updated = await submitLicenseReview(licenseModalCandidate.id, {
        license_status: targetLicenseStatus,
        commercial_rights_status: targetCommRights,
        license_notes: licenseNotes,
        reviewed_by: complianceReviewer
      });
      setCandidates(candidates.map(c => (c.id === updated.id ? updated : c)));
      setLicenseModalCandidate(null);
      alert(`License review recorded. Updated permission state: ${updated.license_status}`);
    } catch (err) {
      alert(`License review failed: ${err}`);
    }
  };

  const handleAcquireCandidate = async (candidate: DatasetCandidateRecord) => {
    try {
      const res = await acquireDatasetCandidate(candidate.id, {
        candidate_id: candidate.id,
        max_files_limit: 10,
        max_megabytes_limit: 150,
        requested_by: reviewerName
      });
      if (res.job_status === "MANUAL_ACTION_REQUIRED") {
        alert(`Direct automated download is not supported for public catalog '${candidate.provider_name}'.\n\nInstructions: Download manually from canonical source (${candidate.canonical_url}) into data/internal_imports/ to ingest under verified provenance.`);
      } else {
        alert(`Acquisition complete! Acquired ${res.acquired_assets_count} assets into KeeAInu repository.`);
      }
      await loadAssets();
      await loadProvidersAndCandidates();
    } catch (err) {
      alert(`Acquisition blocked: ${err}`);
    }
  };

  const handleGenerateSynthetic = async () => {
    try {
      setGeneratingSynth(true);
      const res = await generateSyntheticMedia({
        generation_type: "PROCEDURAL_SURFACE",
        target_domain: synthDomain,
        defect_type: synthDefect,
        count: synthCount,
        lighting_variation: lightingVar,
        noise_level: noiseVar,
        blur_level: blurVar,
        random_seed: synthSeed,
        requested_by: reviewerName
      });
      alert(`Generated ${res.generated_count} synthetic assets with verifiable provenance links!`);
      await loadAssets();
      setActiveTab("inventory");
    } catch (err) {
      alert(`Synthetic generation failed: ${err}`);
    } finally {
      setGeneratingSynth(false);
    }
  };

  const handleUpdateDomain = async (domain: DomainCategory, confidence: DomainConfidence) => {
    if (!selectedAsset) return;
    try {
      const updated = await updateAssetDomain(selectedAsset.id, {
        domain_assignment: domain,
        domain_confidence: confidence,
        domain_notes: `Assigned via Discovery Workspace by ${reviewerName}`,
        reviewed_by: reviewerName
      });
      setSelectedAsset(updated);
      setAssets(assets.map(a => (a.id === updated.id ? updated : a)));
    } catch (err) {
      alert(`Failed to update domain: ${err}`);
    }
  };

  const handleUpdateSampleReview = async (sampleId: string, status: SampleReviewStatus, category?: string) => {
    try {
      const updatedSample = await updateSampleReview(sampleId, {
        review_status: status,
        suspected_category: category,
        reviewed_by: reviewerName
      });
      if (selectedAsset) {
        const updatedSamples = selectedAsset.samples.map(s => (s.id === updatedSample.id ? updatedSample : s));
        setSelectedAsset({ ...selectedAsset, samples: updatedSamples });
      }
    } catch (err) {
      alert(`Failed to update sample review: ${err}`);
    }
  };

  const openReport = async () => {
    try {
      const data = await fetchDiscoveryReport();
      setReport(data);
      setIsReportOpen(true);
    } catch (err) {
      alert(`Failed to fetch report: ${err}`);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px)", backgroundColor: "#0b0f19", color: "#f3f4f6" }}>
      {/* Top Discovery & Acquisition Navigation Bar */}
      <div style={{ padding: "12px 24px", borderBottom: "1px solid #1f293d", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "#0e1424" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Database size={22} color="#38bdf8" />
            <h2 style={{ fontSize: "1.2rem", fontWeight: "700", letterSpacing: "0.5px", margin: 0 }}>
              KeeAInu Discovery & Acquisition Hub
            </h2>
          </div>

          <div style={{ display: "flex", gap: "4px", backgroundColor: "#161f36", padding: "4px", borderRadius: "8px" }}>
            <button
              onClick={() => setActiveTab("inventory")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "inventory" ? "#2563eb" : "transparent",
                color: activeTab === "inventory" ? "#ffffff" : "#94a3b8"
              }}
            >
              <FolderOpen size={16} /> Local Inventory ({assets.length})
            </button>
            <button
              onClick={() => setActiveTab("catalog")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "catalog" ? "#2563eb" : "transparent",
                color: activeTab === "catalog" ? "#ffffff" : "#94a3b8"
              }}
            >
              <Globe size={16} /> Multi-Source Catalog Search ({candidates.length})
            </button>
            <button
              onClick={() => setActiveTab("licenses")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "licenses" ? "#2563eb" : "transparent",
                color: activeTab === "licenses" ? "#ffffff" : "#94a3b8"
              }}
            >
              <ShieldCheck size={16} /> License & Permission Gates
            </button>
            <button
              onClick={() => setActiveTab("synthetic")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "synthetic" ? "#2563eb" : "transparent",
                color: activeTab === "synthetic" ? "#ffffff" : "#94a3b8"
              }}
            >
              <Sparkles size={16} /> Synthetic Studio
            </button>
            <button
              onClick={() => setActiveTab("taxonomy")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "taxonomy" ? "#2563eb" : "transparent",
                color: activeTab === "taxonomy" ? "#ffffff" : "#94a3b8"
              }}
            >
              <Tag size={16} /> Equipment Taxonomy & Labels
            </button>
            <button
              onClick={() => setActiveTab("evaluation")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "evaluation" ? "#2563eb" : "transparent",
                color: activeTab === "evaluation" ? "#ffffff" : "#94a3b8"
              }}
            >
              <BarChart3 size={16} /> Evaluation & Benchmarks
            </button>
            <button
              onClick={() => setActiveTab("findings")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "findings" ? "#2563eb" : "transparent",
                color: activeTab === "findings" ? "#ffffff" : "#94a3b8"
              }}
            >
              <UserCheck size={16} /> Human Review Findings
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              style={{
                padding: "6px 14px",
                borderRadius: "6px",
                border: "none",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "0.85rem",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: activeTab === "audit" ? "#2563eb" : "transparent",
                color: activeTab === "audit" ? "#ffffff" : "#94a3b8"
              }}
            >
              <History size={16} /> Audit Trail & Manifest
            </button>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            onClick={openReport}
            style={{
              padding: "7px 14px",
              backgroundColor: "#1e293b",
              color: "#38bdf8",
              border: "1px solid #334155",
              borderRadius: "6px",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontWeight: "600",
              fontSize: "0.85rem"
            }}
          >
            <Info size={16} /> Readiness Report
          </button>
          <a
            href={getManifestUrl()}
            target="_blank"
            rel="noreferrer"
            style={{
              padding: "7px 14px",
              backgroundColor: "#1e293b",
              color: "#a855f7",
              border: "1px solid #334155",
              borderRadius: "6px",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontWeight: "600",
              fontSize: "0.85rem"
            }}
          >
            <Download size={16} /> Export Manifest
          </a>
        </div>
      </div>

      {/* Main Tab Views */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex" }}>
        {activeTab === "inventory" && (
          <div style={{ display: "flex", width: "100%", height: "100%" }}>
            {/* Left Sidebar: Controls & Asset List */}
            <div style={{ width: "380px", borderRight: "1px solid #1f293d", display: "flex", flexDirection: "column", backgroundColor: "#0e1424" }}>
              {/* Scan Trigger & Directory Box */}
              <div style={{ padding: "16px", borderBottom: "1px solid #1f293d" }}>
                <div style={{ display: "flex", gap: "8px", marginBottom: "10px" }}>
                  <input
                    type="text"
                    placeholder="Custom sub-dir (e.g. data/source_footage)"
                    value={customDir}
                    onChange={(e) => setCustomDir(e.target.value)}
                    style={{
                      flex: 1,
                      backgroundColor: "#161f36",
                      border: "1px solid #2e3d60",
                      borderRadius: "6px",
                      padding: "7px 10px",
                      color: "#fff",
                      fontSize: "0.85rem"
                    }}
                  />
                  <button
                    onClick={() => handleScan(false)}
                    disabled={scanning}
                    style={{
                      padding: "7px 14px",
                      backgroundColor: "#2563eb",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      cursor: scanning ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      fontWeight: "600",
                      fontSize: "0.85rem"
                    }}
                  >
                    <RefreshCw size={15} className={scanning ? "animate-spin" : ""} />
                    {scanning ? "Scanning..." : "Scan"}
                  </button>
                </div>

                <div style={{ display: "flex", gap: "8px" }}>
                  <select
                    value={domainFilter}
                    onChange={(e) => setDomainFilter(e.target.value)}
                    style={{
                      flex: 1,
                      backgroundColor: "#161f36",
                      border: "1px solid #2e3d60",
                      borderRadius: "6px",
                      padding: "6px 8px",
                      color: "#cbd5e1",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="ALL">All Domains</option>
                    <option value="MECHANICAL">Mechanical</option>
                    <option value="PIPES_CHANNELS">Pipes & Channels</option>
                    <option value="MOULD_CAVITIES">Mould Cavities</option>
                    <option value="OTHER">Other</option>
                    <option value="UNKNOWN">Unknown</option>
                  </select>

                  <select
                    value={provenanceFilter}
                    onChange={(e) => setProvenanceFilter(e.target.value)}
                    style={{
                      flex: 1,
                      backgroundColor: "#161f36",
                      border: "1px solid #2e3d60",
                      borderRadius: "6px",
                      padding: "6px 8px",
                      color: "#cbd5e1",
                      fontSize: "0.8rem"
                    }}
                  >
                    <option value="ALL">All Provenance</option>
                    <option value="REAL">Genuine Footage</option>
                    <option value="SYNTHETIC">Synthetic Fixtures</option>
                  </select>
                </div>
              </div>

              {/* Asset List */}
              <div style={{ flex: 1, overflowY: "auto", padding: "12px" }}>
                {loading ? (
                  <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>Loading assets...</div>
                ) : assets.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b" }}>
                    No media assets discovered. Run a scan or acquire datasets from the Catalog tab.
                  </div>
                ) : (
                  assets.map((asset) => (
                    <div
                      key={asset.id}
                      onClick={() => setSelectedAsset(asset)}
                      style={{
                        padding: "12px",
                        borderRadius: "8px",
                        backgroundColor: selectedAsset?.id === asset.id ? "#1e293b" : "#131a2c",
                        border: `1px solid ${selectedAsset?.id === asset.id ? "#38bdf8" : "#1f293d"}`,
                        marginBottom: "8px",
                        cursor: "pointer",
                        transition: "all 0.15s ease"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px", maxWidth: "220px" }}>
                          {asset.asset_type === "video" ? <FileVideo size={16} color="#38bdf8" /> : <FileImage size={16} color="#4ade80" />}
                          <span style={{ fontSize: "0.85rem", fontWeight: "600", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {asset.filename}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: "0.7rem",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            backgroundColor: asset.is_synthetic ? "#4c1d95" : "#065f46",
                            color: asset.is_synthetic ? "#d8b4fe" : "#a7f3d0",
                            fontWeight: "600"
                          }}
                        >
                          {asset.is_synthetic ? "SYNTHETIC" : "REAL"}
                        </span>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8" }}>
                        <span>Domain: <strong style={{ color: "#e2e8f0" }}>{asset.domain_assignment || "UNKNOWN"}</strong></span>
                        <span>{asset.samples_count || 0} samples</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Main Pane: Asset Detail, Domain Review & Gallery */}
            <div style={{ flex: 1, overflowY: "auto", padding: "24px", backgroundColor: "#0b0f19" }}>
              {selectedAsset ? (
                <div>
                  {/* Header & Quality Summary */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "20px" }}>
                    <div>
                      <h1 style={{ fontSize: "1.4rem", fontWeight: "700", marginBottom: "4px" }}>{selectedAsset.filename}</h1>
                      <div style={{ display: "flex", gap: "12px", fontSize: "0.8rem", color: "#94a3b8" }}>
                        <span>SHA-256: <code style={{ color: "#38bdf8" }}>{selectedAsset.sha256_hash.slice(0, 16)}...</code></span>
                        <span>Dimensions: <strong>{selectedAsset.width}x{selectedAsset.height}</strong></span>
                        {selectedAsset.asset_type === "video" && <span>Duration: <strong>{selectedAsset.duration_seconds.toFixed(1)}s</strong></span>}
                      </div>
                    </div>

                    {/* Domain Assignment Control */}
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", backgroundColor: "#161f36", padding: "8px 12px", borderRadius: "8px", border: "1px solid #2e3d60" }}>
                      <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Domain:</span>
                      <select
                        value={selectedAsset.domain_assignment || "UNKNOWN"}
                        onChange={(e) => handleUpdateDomain(e.target.value as DomainCategory, "CERTAIN")}
                        style={{
                          backgroundColor: "#0e1424",
                          color: "#38bdf8",
                          border: "1px solid #38bdf8",
                          borderRadius: "4px",
                          padding: "4px 8px",
                          fontWeight: "700",
                          fontSize: "0.85rem"
                        }}
                      >
                        <option value="MECHANICAL">Mechanical (Engines/Turbines)</option>
                        <option value="PIPES_CHANNELS">Pipes & Channels</option>
                        <option value="MOULD_CAVITIES">Mould Cavities</option>
                        <option value="OTHER">Other Domain</option>
                        <option value="UNKNOWN">Unknown / Indeterminate</option>
                      </select>
                    </div>
                  </div>

                  {/* Contact Sheet & Quality Heuristics */}
                  <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "20px", marginBottom: "24px" }}>
                    <div style={{ backgroundColor: "#0e1424", padding: "16px", borderRadius: "8px", border: "1px solid #1f293d" }}>
                      <h3 style={{ fontSize: "0.95rem", fontWeight: "600", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Layers size={16} color="#38bdf8" /> Continuous Contact Sheet Gallery
                      </h3>
                      {selectedAsset.contact_sheet_path ? (
                        <img
                          src={getContactSheetUrl(selectedAsset.id)}
                          alt="Contact Sheet"
                          style={{ width: "100%", borderRadius: "6px", border: "1px solid #334155" }}
                        />
                      ) : (
                        <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>Contact sheet not generated</div>
                      )}
                    </div>

                    <div style={{ backgroundColor: "#0e1424", padding: "16px", borderRadius: "8px", border: "1px solid #1f293d" }}>
                      <h3 style={{ fontSize: "0.95rem", fontWeight: "600", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
                        <Sliders size={16} color="#a855f7" /> Automated Visual Quality Profiling
                      </h3>
                      {selectedAsset.quality_profile ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem" }}>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#94a3b8" }}>Sharpness (Laplacian Var):</span>
                            <strong>{selectedAsset.quality_profile.sharpness_score.toFixed(1)}</strong>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#94a3b8" }}>Mean Brightness:</span>
                            <strong>{selectedAsset.quality_profile.brightness_mean.toFixed(1)} / 255</strong>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#94a3b8" }}>Contrast (Std Dev):</span>
                            <strong>{selectedAsset.quality_profile.contrast_std.toFixed(1)}</strong>
                          </div>
                          <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#94a3b8" }}>Blur Heuristic Flag:</span>
                            <span style={{ color: selectedAsset.quality_profile.blur_detected ? "#ef4444" : "#4ade80", fontWeight: "700" }}>
                              {selectedAsset.quality_profile.blur_detected ? "BLUR FLAGGED" : "NOMINAL FOCUS"}
                            </span>
                          </div>
                          <div style={{ borderTop: "1px solid #1f293d", paddingTop: "8px", marginTop: "4px" }}>
                            <span style={{ color: "#94a3b8", fontSize: "0.75rem", display: "block", marginBottom: "4px" }}>Heuristic Explanations:</span>
                            {selectedAsset.quality_profile.explanations.map((exp, i) => (
                              <div key={i} style={{ fontSize: "0.75rem", color: "#cbd5e1", marginBottom: "2px" }}>• {exp}</div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>Quality metrics unavailable</div>
                      )}
                    </div>
                  </div>

                  {/* Representative Sample Frames Grid & Human Review */}
                  <div style={{ backgroundColor: "#0e1424", padding: "20px", borderRadius: "8px", border: "1px solid #1f293d" }}>
                    <h3 style={{ fontSize: "1rem", fontWeight: "600", marginBottom: "16px" }}>
                      Representative Extracted Sample Frames ({selectedAsset.samples.length})
                    </h3>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "16px" }}>
                      {selectedAsset.samples.map((sample) => (
                        <div key={sample.id} style={{ backgroundColor: "#161f36", borderRadius: "8px", overflow: "hidden", border: "1px solid #2e3d60" }}>
                          <img
                            src={getSampleImageUrl(sample.id)}
                            alt={`Frame ${sample.frame_index}`}
                            style={{ width: "100%", height: "140px", objectFit: "cover" }}
                          />
                          <div style={{ padding: "12px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#94a3b8", marginBottom: "8px" }}>
                              <span>Frame #{sample.frame_index}</span>
                              <span>{sample.timestamp_ms.toFixed(0)} ms</span>
                            </div>

                            <select
                              value={sample.review_status}
                              onChange={(e) => handleUpdateSampleReview(sample.id, e.target.value as SampleReviewStatus)}
                              style={{
                                width: "100%",
                                backgroundColor: "#0b0f19",
                                color: sample.review_status === "CONFIRMED_DEFECT" ? "#ef4444" : "#f1f5f9",
                                border: "1px solid #334155",
                                borderRadius: "4px",
                                padding: "6px",
                                fontSize: "0.8rem",
                                fontWeight: "600"
                              }}
                            >
                              <option value="UNREVIEWED">Unreviewed</option>
                              <option value="NO_VISIBLE_DEFECT">No Visible Defect</option>
                              <option value="SUSPECTED_ANOMALY">Suspected Anomaly</option>
                              <option value="CONFIRMED_DEFECT">Confirmed Defect</option>
                              <option value="UNCERTAIN_NEEDS_EXPERT">Needs Expert Review</option>
                              <option value="UNUSABLE">Unusable / Corrupt</option>
                            </select>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: "center", padding: "100px 0", color: "#64748b" }}>
                  Select an asset from the left panel to inspect details and quality metrics.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Multi-Source Catalog Search */}
        {activeTab === "catalog" && (
          <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", padding: "24px", overflowY: "auto" }}>
            {/* Search Header Controls */}
            <div style={{ backgroundColor: "#0e1424", padding: "20px", borderRadius: "10px", border: "1px solid #1f293d", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Globe size={20} color="#38bdf8" /> Discover External & Internal Datasets
              </h2>

              <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter keywords (e.g. borescope, sewer pipe fracture, turbine blade erosion...)"
                  style={{
                    flex: 1,
                    backgroundColor: "#161f36",
                    border: "1px solid #2e3d60",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    color: "#fff",
                    fontSize: "0.95rem"
                  }}
                />
                <select
                  value={targetSearchDomain}
                  onChange={(e) => setTargetSearchDomain(e.target.value)}
                  style={{
                    backgroundColor: "#161f36",
                    border: "1px solid #2e3d60",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    color: "#38bdf8",
                    fontWeight: "600"
                  }}
                >
                  <option value="MECHANICAL">Mechanical (Engines/Turbines)</option>
                  <option value="PIPES_CHANNELS">Pipes & Channels</option>
                  <option value="MOULD_CAVITIES">Mould Cavities</option>
                  <option value="UNKNOWN">All / Cross-Domain</option>
                </select>
                <button
                  onClick={handleCatalogSearch}
                  disabled={searching}
                  style={{
                    padding: "10px 20px",
                    backgroundColor: "#2563eb",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    fontWeight: "700",
                    cursor: searching ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px"
                  }}
                >
                  <Search size={18} /> {searching ? "Searching..." : "Search Catalogs"}
                </button>
              </div>

              {/* Provider checkboxes */}
              <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap", fontSize: "0.8rem", color: "#94a3b8" }}>
                <span>Search Providers:</span>
                {providers.map((p) => (
                  <label key={p.id} style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer" }}>
                    <input
                      type="checkbox"
                      checked={selectedProviders.length === 0 || selectedProviders.includes(p.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedProviders([...selectedProviders, p.id]);
                        } else {
                          setSelectedProviders(selectedProviders.filter(id => id !== p.id));
                        }
                      }}
                    />
                    {p.name}
                  </label>
                ))}
                <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", marginLeft: "auto", color: "#38bdf8" }}>
                  <input
                    type="checkbox"
                    checked={directVideoscopeOnly}
                    onChange={(e) => setDirectVideoscopeOnly(e.target.checked)}
                  />
                  Direct Borescope Only
                </label>
              </div>
            </div>

            {/* Candidates Results Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: "20px" }}>
              {candidates.map((cand) => (
                <div
                  key={cand.id}
                  style={{
                    backgroundColor: "#0e1424",
                    borderRadius: "10px",
                    border: "1px solid #1f293d",
                    padding: "20px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between"
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                      <span style={{ fontSize: "0.75rem", color: "#38bdf8", fontWeight: "700" }}>{cand.provider_name}</span>
                      <div style={{ display: "flex", gap: "6px" }}>
                        {cand.verification_status && (
                          <span
                            style={{
                              fontSize: "0.65rem",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontWeight: "700",
                              backgroundColor:
                                cand.verification_status === "LIVE_METADATA_VERIFIED"
                                  ? "#065f46"
                                  : cand.verification_status === "CURATED_LEAD_AWAITING_VERIFICATION"
                                  ? "#1e3a8a"
                                  : "#475569",
                              color: "#fff"
                            }}
                          >
                            {cand.verification_status === "LIVE_METADATA_VERIFIED"
                              ? "LIVE VERIFIED"
                              : cand.verification_status === "CURATED_LEAD_AWAITING_VERIFICATION"
                              ? "CURATED LEAD"
                              : cand.verification_status}
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: "0.65rem",
                            padding: "2px 6px",
                            borderRadius: "4px",
                            fontWeight: "700",
                            backgroundColor:
                              cand.license_status === "APPROVED_FOR_EVALUATION"
                                ? "#065f46"
                                : cand.license_status === "APPROVED_FOR_NONCOMMERCIAL_RESEARCH"
                                ? "#0369a1"
                                : cand.license_status === "REJECTED"
                                ? "#7f1d1d"
                                : "#854d0e",
                            color: "#fff"
                          }}
                        >
                          {cand.license_status}
                        </span>
                      </div>
                    </div>

                    <h3 style={{ fontSize: "1.05rem", fontWeight: "700", marginBottom: "6px", lineHeight: "1.3" }}>
                      {cand.title}
                    </h3>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginBottom: "8px" }}>
                      Publisher: <strong>{cand.publisher}</strong> | Domain: <strong>{cand.domain_tag}</strong>
                    </div>
                    {cand.download_support && (
                      <div style={{ fontSize: "0.75rem", color: cand.download_support === "DIRECT_DOWNLOAD_SUPPORTED" ? "#34d399" : "#fbbf24", marginBottom: "8px" }}>
                        Acquisition: <strong>{cand.download_support === "DIRECT_DOWNLOAD_SUPPORTED" ? "Automated Pipeline" : "Manual Download Required"}</strong>
                      </div>
                    )}

                    <p style={{ fontSize: "0.85rem", color: "#cbd5e1", marginBottom: "14px", lineHeight: "1.4" }}>
                      {cand.description}
                    </p>

                    {/* Relevance Score Bar */}
                    <div
                      onClick={() => {
                        setSelectedCandidate(cand);
                        setIsRelevanceModalOpen(true);
                      }}
                      style={{
                        backgroundColor: "#161f36",
                        padding: "8px 12px",
                        borderRadius: "6px",
                        cursor: "pointer",
                        marginBottom: "14px",
                        border: "1px solid #2e3d60"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: "4px" }}>
                        <span>Explainable Relevance Score:</span>
                        <strong style={{ color: "#38bdf8" }}>{cand.relevance_score} / 100</strong>
                      </div>
                      <div style={{ width: "100%", height: "6px", backgroundColor: "#0b0f19", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ width: `${cand.relevance_score}%`, height: "100%", backgroundColor: "#38bdf8" }} />
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "10px", borderTop: "1px solid #1f293d", paddingTop: "14px" }}>
                    <button
                      onClick={() => handleOpenLicenseModal(cand)}
                      style={{
                        flex: 1,
                        padding: "8px",
                        backgroundColor: "#1e293b",
                        color: "#f8fafc",
                        border: "1px solid #334155",
                        borderRadius: "6px",
                        fontSize: "0.8rem",
                        fontWeight: "600",
                        cursor: "pointer"
                      }}
                    >
                      Audit License
                    </button>
                    <button
                      onClick={() => handleAcquireCandidate(cand)}
                      style={{
                        flex: 1,
                        padding: "8px",
                        backgroundColor:
                          cand.license_status === "APPROVED_FOR_EVALUATION" || cand.license_status === "APPROVED_FOR_NONCOMMERCIAL_RESEARCH"
                            ? "#2563eb"
                            : "#334155",
                        color: "#fff",
                        border: "none",
                        borderRadius: "6px",
                        fontSize: "0.8rem",
                        fontWeight: "700",
                        cursor:
                          cand.license_status === "APPROVED_FOR_EVALUATION" || cand.license_status === "APPROVED_FOR_NONCOMMERCIAL_RESEARCH"
                            ? "pointer"
                            : "not-allowed"
                      }}
                    >
                      Acquire Data
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: License Review & Permission Gates */}
        {activeTab === "licenses" && (
          <div style={{ width: "100%", padding: "24px", overflowY: "auto" }}>
            <div style={{ backgroundColor: "#0e1424", padding: "20px", borderRadius: "10px", border: "1px solid #1f293d", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldCheck size={22} color="#10b981" /> Formal License & Rights Gating Registry
              </h2>
              <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                Strict compliance gates prevent unauthorized, non-commercial, or unverified dataset assets from entering AI model evaluation or commercial pipelines.
              </p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "12px" }}>
              {candidates.map((cand) => (
                <div
                  key={cand.id}
                  style={{
                    backgroundColor: "#0e1424",
                    padding: "16px 20px",
                    borderRadius: "8px",
                    border: "1px solid #1f293d",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center"
                  }}
                >
                  <div>
                    <h4 style={{ fontSize: "1rem", fontWeight: "700", marginBottom: "4px" }}>{cand.title}</h4>
                    <div style={{ fontSize: "0.8rem", color: "#94a3b8", display: "flex", gap: "14px" }}>
                      <span>Publisher: <strong>{cand.publisher}</strong></span>
                      <span>Declared License: <strong style={{ color: "#38bdf8" }}>{cand.license_identifier}</strong></span>
                      <span>Commercial Allowed: <strong>{cand.commercial_use_allowed ? "YES" : "NO"}</strong></span>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <span
                      style={{
                        fontSize: "0.75rem",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontWeight: "700",
                        backgroundColor:
                          cand.license_status === "APPROVED_FOR_EVALUATION"
                            ? "#065f46"
                            : cand.license_status === "APPROVED_FOR_NONCOMMERCIAL_RESEARCH"
                            ? "#0369a1"
                            : cand.license_status === "REJECTED"
                            ? "#7f1d1d"
                            : "#854d0e",
                        color: "#fff"
                      }}
                    >
                      {cand.license_status}
                    </span>
                    <button
                      onClick={() => handleOpenLicenseModal(cand)}
                      style={{
                        padding: "6px 14px",
                        backgroundColor: "#2563eb",
                        color: "#fff",
                        border: "none",
                        borderRadius: "6px",
                        fontWeight: "600",
                        fontSize: "0.8rem",
                        cursor: "pointer"
                      }}
                    >
                      Edit Review
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Synthetic Defect Studio */}
        {activeTab === "synthetic" && (
          <div style={{ width: "100%", padding: "24px", overflowY: "auto", display: "flex", justifyContent: "center" }}>
            <div style={{ width: "680px", backgroundColor: "#0e1424", padding: "28px", borderRadius: "12px", border: "1px solid #1f293d" }}>
              <h2 style={{ fontSize: "1.3rem", fontWeight: "700", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Sparkles size={22} color="#a855f7" /> Controlled Procedural Synthetic Defect Studio
              </h2>
              <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "24px" }}>
                Generate parameterized procedural defect media with immutable provenance tracking (<code>is_synthetic=True</code>) and deterministic random seeds.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ fontSize: "0.85rem", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                    Target Industrial Domain:
                  </label>
                  <select
                    value={synthDomain}
                    onChange={(e) => setSynthDomain(e.target.value as any)}
                    style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px 12px", color: "#fff" }}
                  >
                    <option value="PIPES_CHANNELS">Pipes & Channels (Tubular Perspective)</option>
                    <option value="MECHANICAL">Mechanical (Turbine Blades / Compressors)</option>
                    <option value="MOULD_CAVITIES">Mould Cavities (Specular Die Surfaces)</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.85rem", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                    Defect Flaw Pattern:
                  </label>
                  <select
                    value={synthDefect}
                    onChange={(e) => setSynthDefect(e.target.value as any)}
                    style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px 12px", color: "#fff" }}
                  >
                    <option value="CRACK">Fracture / Stress Corrosion Crack</option>
                    <option value="CORROSION_PIT">Localized Pitting Corrosion</option>
                    <option value="EROSION">Leading Edge Surface Erosion</option>
                    <option value="DEPOSIT">Internal Scale / Foreign Object Debris</option>
                  </select>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  <div>
                    <label style={{ fontSize: "0.85rem", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                      Batch Item Count:
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={synthCount}
                      onChange={(e) => setSynthCount(parseInt(e.target.value) || 1)}
                      style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px 12px", color: "#fff" }}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: "0.85rem", fontWeight: "600", color: "#cbd5e1", display: "block", marginBottom: "6px" }}>
                      Random Seed (Reproducibility):
                    </label>
                    <input
                      type="number"
                      value={synthSeed}
                      onChange={(e) => setSynthSeed(parseInt(e.target.value) || 42)}
                      style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px 12px", color: "#fff" }}
                    />
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                    <span>Lighting Variation:</span>
                    <span>{(lightingVar * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={lightingVar}
                    onChange={(e) => setLightingVar(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                    <span>Sensor Noise Level:</span>
                    <span>{(noiseVar * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={0.5}
                    step={0.02}
                    value={noiseVar}
                    onChange={(e) => setNoiseVar(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                    <span>Optical Blur Level:</span>
                    <span>{(blurVar * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={blurVar}
                    onChange={(e) => setBlurVar(parseFloat(e.target.value))}
                    style={{ width: "100%" }}
                  />
                </div>

                <button
                  onClick={handleGenerateSynthetic}
                  disabled={generatingSynth}
                  style={{
                    marginTop: "12px",
                    padding: "12px",
                    backgroundColor: "#9333ea",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    fontWeight: "700",
                    fontSize: "0.95rem",
                    cursor: generatingSynth ? "not-allowed" : "pointer",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    gap: "8px"
                  }}
                >
                  <Sparkles size={18} />
                  {generatingSynth ? "Generating Procedural Media..." : "Generate Synthetic Media Batch"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Audit Trail & Manifest */}
        {activeTab === "audit" && (
          <div style={{ width: "100%", padding: "24px", overflowY: "auto" }}>
            <div style={{ backgroundColor: "#0e1424", padding: "20px", borderRadius: "10px", border: "1px solid #1f293d", marginBottom: "20px" }}>
              <h2 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
                <History size={22} color="#38bdf8" /> Immutable Acquisition & Provenance Audit Trail
              </h2>
              <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                Complete event log tracing catalog searches, compliance license gate approvals, controlled downloads, and procedural generations.
              </p>
            </div>

            {loadingAudit ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>Loading audit log...</div>
            ) : auditEvents.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>No audit events recorded yet.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {auditEvents.map((evt) => (
                  <div
                    key={evt.id}
                    style={{
                      backgroundColor: "#0e1424",
                      padding: "14px 18px",
                      borderRadius: "8px",
                      border: "1px solid #1f293d",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8" }}>{evt.event_type}</span>
                        <code style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{evt.id}</code>
                      </div>
                      <div style={{ fontSize: "0.8rem", color: "#cbd5e1" }}>
                        {JSON.stringify(evt.details)}
                      </div>
                    </div>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                      {new Date(evt.created_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "taxonomy" && (
          <div style={{ width: "100%", height: "100%", overflowY: "auto" }}>
            <EquipmentTaxonomyView />
          </div>
        )}

        {activeTab === "evaluation" && (
          <div style={{ width: "100%", height: "100%", overflowY: "auto" }}>
            <EvaluationBenchmarkView />
          </div>
        )}

        {activeTab === "findings" && (
          <div style={{ width: "100%", height: "100%", overflowY: "auto" }}>
            <HumanFindingsReviewView />
          </div>
        )}
      </div>

      {/* License Audit Modal */}
      {licenseModalCandidate && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ width: "520px", backgroundColor: "#0e1424", padding: "24px", borderRadius: "10px", border: "1px solid #2e3d60", color: "#fff" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "12px" }}>
              Formal License Review: {licenseModalCandidate.title}
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px", fontSize: "0.85rem", marginBottom: "20px" }}>
              <div>
                <label style={{ display: "block", color: "#94a3b8", marginBottom: "4px" }}>License Permission State:</label>
                <select
                  value={targetLicenseStatus}
                  onChange={(e) => setTargetLicenseStatus(e.target.value as LicensePermissionStatus)}
                  style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px", color: "#fff" }}
                >
                  <option value="APPROVED_FOR_EVALUATION">APPROVED_FOR_EVALUATION (Permissive / Safe)</option>
                  <option value="APPROVED_FOR_NONCOMMERCIAL_RESEARCH">APPROVED_FOR_NONCOMMERCIAL_RESEARCH</option>
                  <option value="COMMERCIAL_USE_REVIEW_REQUIRED">COMMERCIAL_USE_REVIEW_REQUIRED</option>
                  <option value="LICENSE_UNKNOWN">LICENSE_UNKNOWN</option>
                  <option value="ACCESS_RESTRICTED">ACCESS_RESTRICTED</option>
                  <option value="DOWNLOAD_NOT_AUTHORIZED">DOWNLOAD_NOT_AUTHORIZED</option>
                  <option value="REJECTED">REJECTED (Prohibited)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", marginBottom: "4px" }}>Commercial Rights Clearance:</label>
                <select
                  value={targetCommRights}
                  onChange={(e) => setTargetCommRights(e.target.value as any)}
                  style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px", color: "#fff" }}
                >
                  <option value="ALLOWED">ALLOWED (Commercial & Evaluation Rights Verified)</option>
                  <option value="FORBIDDEN">FORBIDDEN (Non-Commercial / Gated Only)</option>
                  <option value="REVIEW_REQUIRED">REVIEW_REQUIRED (Pending Legal Audit)</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", marginBottom: "4px" }}>Compliance Reviewer Name:</label>
                <input
                  type="text"
                  value={complianceReviewer}
                  onChange={(e) => setComplianceReviewer(e.target.value)}
                  style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px", color: "#fff" }}
                />
              </div>

              <div>
                <label style={{ display: "block", color: "#94a3b8", marginBottom: "4px" }}>Audit Notes & Rationale:</label>
                <textarea
                  rows={3}
                  value={licenseNotes}
                  onChange={(e) => setLicenseNotes(e.target.value)}
                  style={{ width: "100%", backgroundColor: "#161f36", border: "1px solid #2e3d60", borderRadius: "6px", padding: "8px", color: "#fff" }}
                />
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                onClick={() => setLicenseModalCandidate(null)}
                style={{ padding: "8px 16px", backgroundColor: "#1e293b", color: "#fff", border: "1px solid #334155", borderRadius: "6px", cursor: "pointer" }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveLicenseReview}
                style={{ padding: "8px 16px", backgroundColor: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontWeight: "700", cursor: "pointer" }}
              >
                Save Compliance Audit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Relevance Breakdown Modal */}
      {isRelevanceModalOpen && selectedCandidate && selectedCandidate.relevance_breakdown && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ width: "540px", backgroundColor: "#0e1424", padding: "24px", borderRadius: "10px", border: "1px solid #2e3d60", color: "#fff" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", marginBottom: "8px" }}>
              Relevance Scoring Breakdown
            </h3>
            <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "16px" }}>
              {selectedCandidate.title}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", marginBottom: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Videoscope Visual Similarity:</span>
                <strong>{selectedCandidate.relevance_breakdown.videoscope_similarity} / 30</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Domain Match:</span>
                <strong>{selectedCandidate.relevance_breakdown.domain_match} / 25</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Modality Match:</span>
                <strong>{selectedCandidate.relevance_breakdown.modality_match} / 15</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Defect Flaw Utility:</span>
                <strong>{selectedCandidate.relevance_breakdown.defect_utility} / 15</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Annotation Quality:</span>
                <strong>{selectedCandidate.relevance_breakdown.annotation_quality} / 10</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", borderTop: "1px solid #1f293d", paddingTop: "8px" }}>
                <span>Total Explainable Relevance:</span>
                <strong style={{ color: "#38bdf8", fontSize: "1rem" }}>{selectedCandidate.relevance_breakdown.total_score} / 100</strong>
              </div>

              <div style={{ marginTop: "10px" }}>
                <span style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>Score Rationale:</span>
                {selectedCandidate.relevance_breakdown.relevance_explanations.map((exp, i) => (
                  <div key={i} style={{ fontSize: "0.8rem", color: "#cbd5e1", marginBottom: "3px" }}>• {exp}</div>
                ))}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setIsRelevanceModalOpen(false)}
                style={{ padding: "8px 18px", backgroundColor: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontWeight: "700", cursor: "pointer" }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Discovery Readiness Report Modal */}
      {isReportOpen && report && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ width: "640px", maxHeight: "80vh", overflowY: "auto", backgroundColor: "#0e1424", padding: "28px", borderRadius: "12px", border: "1px solid #2e3d60", color: "#fff" }}>
            <h2 style={{ fontSize: "1.3rem", fontWeight: "700", marginBottom: "8px" }}>KeeAInu Discovery Corpus Readiness Report</h2>
            <p style={{ fontSize: "0.8rem", color: "#94a3b8", marginBottom: "20px" }}>Generated at: {new Date(report.generated_at).toLocaleString()}</p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "20px", fontSize: "0.85rem" }}>
              <div style={{ backgroundColor: "#161f36", padding: "12px", borderRadius: "6px" }}>
                <span style={{ color: "#94a3b8" }}>Total Discovered Assets:</span>
                <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#38bdf8" }}>{report.total_assets}</div>
              </div>
              <div style={{ backgroundColor: "#161f36", padding: "12px", borderRadius: "6px" }}>
                <span style={{ color: "#94a3b8" }}>Real vs Synthetic:</span>
                <div style={{ fontSize: "1rem", fontWeight: "700", color: "#4ade80" }}>
                  {report.real_assets_count} Real / {report.synthetic_assets_count} Synth
                </div>
              </div>
              <div style={{ backgroundColor: "#161f36", padding: "12px", borderRadius: "6px" }}>
                <span style={{ color: "#94a3b8" }}>Samples Extracted:</span>
                <div style={{ fontSize: "1.2rem", fontWeight: "700", color: "#a855f7" }}>{report.total_samples_extracted}</div>
              </div>
              <div style={{ backgroundColor: "#161f36", padding: "12px", borderRadius: "6px" }}>
                <span style={{ color: "#94a3b8" }}>Avg Sharpness Score:</span>
                <div style={{ fontSize: "1.2rem", fontWeight: "700", color: "#facc15" }}>{report.average_sharpness}</div>
              </div>
            </div>

            <div style={{ marginBottom: "20px" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "600", marginBottom: "6px" }}>Evaluation Split Policy:</h4>
              <p style={{ fontSize: "0.85rem", color: "#cbd5e1", backgroundColor: "#161f36", padding: "10px", borderRadius: "6px" }}>
                {report.evaluation_split_recommendation}
              </p>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setIsReportOpen(false)}
                style={{ padding: "8px 20px", backgroundColor: "#2563eb", color: "#fff", border: "none", borderRadius: "6px", fontWeight: "700", cursor: "pointer" }}
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
