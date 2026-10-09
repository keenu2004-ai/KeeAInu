import { InspectionSession, MediaItem, ThumbnailItem, Finding, BoundingBox } from "../types/inspection";

const API_BASE = "/api/v1";

export async function fetchSessions(): Promise<InspectionSession[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch inspection sessions.");
  return res.json();
}

export async function fetchSession(sessionId: string): Promise<InspectionSession> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch inspection session details.");
  return res.json();
}

export async function createSession(data: {
  title: string;
  inspector_name: string;
  asset_tag?: string;
}): Promise<InspectionSession> {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create session.");
  return res.json();
}

export async function updateSessionStatus(sessionId: string, status: string): Promise<InspectionSession> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update session status.");
  }
  return res.json();
}

export async function uploadMedia(sessionId: string, file: File): Promise<MediaItem> {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/media/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Media upload failed.");
  }
  return res.json();
}

export async function fetchMediaThumbnails(mediaId: string): Promise<ThumbnailItem[]> {
  const res = await fetch(`${API_BASE}/media/${mediaId}/thumbnails`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchInferenceEngines(): Promise<{
  engines: {
    engine_name: string;
    model_version: string;
    is_simulated: boolean;
    auth_configured: boolean;
  }[];
  cloud_inference_globally_allowed: boolean;
  cache_enabled: boolean;
}> {
  const res = await fetch(`${API_BASE}/inference/engines`);
  if (!res.ok) throw new Error("Failed to fetch inference engines.");
  return res.json();
}

export async function analyzeFrame(data: {
  session_id: string;
  media_id: string;
  frame_index: number;
  confidence_threshold?: number;
  engine?: string;
  prompts?: string[];
  allow_cloud_inference?: boolean;
  use_cache?: boolean;
}): Promise<{
  inference_record_id: string;
  media_id: string;
  frame_index: number;
  timestamp_ms: number;
  engine_name: string;
  model_version: string;
  is_simulated: boolean;
  evidence_sha256: string;
  processing_duration_ms: number;
  cache_hit: boolean;
  findings_count: number;
  findings: Finding[];
}> {
  const res = await fetch(`${API_BASE}/inference/analyze-frame`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Analysis request failed.");
  }
  return res.json();
}

export async function fetchInferenceRecords(params?: {
  session_id?: string;
  media_id?: string;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (params?.session_id) query.append("session_id", params.session_id);
  if (params?.media_id) query.append("media_id", params.media_id);

  const res = await fetch(`${API_BASE}/inference/records?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch inference records.");
  return res.json();
}

export async function fetchInferenceRecord(recordId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/inference/records/${recordId}`);
  if (!res.ok) throw new Error("Failed to fetch inference record details.");
  return res.json();
}

export async function fetchSessionFindings(sessionId: string): Promise<Finding[]> {
  const res = await fetch(`${API_BASE}/inference/sessions/${sessionId}/findings`);
  if (!res.ok) return [];
  return res.json();
}

export async function submitReviewDecision(data: {
  finding_id: string;
  decision_status: "CONFIRMED" | "ADJUSTED" | "REJECTED";
  severity: "CRITICAL" | "MAJOR" | "MINOR" | "INFORMATIONAL";
  reviewed_by: string;
  inspector_notes?: string;
  adjusted_bbox?: BoundingBox;
}): Promise<Finding> {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit review.");
  }
  return res.json();
}

export function getMediaContentUrl(mediaId: string): string {
  return `${API_BASE}/media/${mediaId}/content`;
}

export function getThumbnailContentUrl(mediaId: string, thumbId: string): string {
  return `${API_BASE}/media/${mediaId}/thumbnails/${thumbId}/content`;
}

export function getFrameContentUrl(mediaId: string, frameIndex: number): string {
  return `${API_BASE}/media/${mediaId}/frames/${frameIndex}`;
}

// --- Discovery & Profiling API (Phase 4A) ---

export async function triggerDiscoveryScan(data: {
  source_directory?: string;
  sample_count_per_video?: number;
  force_rescan?: boolean;
}): Promise<{ status: string; scanned_count: number; summary: any }> {
  const res = await fetch(`${API_BASE}/discovery/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Discovery scan failed.");
  }
  return res.json();
}

export async function fetchDiscoveredAssets(params?: {
  domain?: string;
  is_synthetic?: boolean;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (params?.domain) query.append("domain", params.domain);
  if (params?.is_synthetic !== undefined) query.append("is_synthetic", String(params.is_synthetic));

  const res = await fetch(`${API_BASE}/discovery/assets?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch discovered assets.");
  return res.json();
}

export async function fetchDiscoveredAsset(assetId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/discovery/assets/${assetId}`);
  if (!res.ok) throw new Error("Failed to fetch asset details.");
  return res.json();
}

export async function updateAssetDomain(
  assetId: string,
  data: {
    domain_assignment: string;
    domain_confidence: string;
    domain_notes?: string;
    reviewed_by: string;
  }
): Promise<any> {
  const res = await fetch(`${API_BASE}/discovery/assets/${assetId}/domain`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update domain assignment.");
  }
  return res.json();
}

export async function updateSampleReview(
  sampleId: string,
  data: {
    review_status: string;
    suspected_category?: string;
    reviewer_notes?: string;
    reviewed_by: string;
  }
): Promise<any> {
  const res = await fetch(`${API_BASE}/discovery/samples/${sampleId}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update sample review.");
  }
  return res.json();
}

export async function fetchDiscoveryReport(): Promise<any> {
  const res = await fetch(`${API_BASE}/discovery/report`);
  if (!res.ok) throw new Error("Failed to fetch discovery report.");
  return res.json();
}

export function getContactSheetUrl(assetId: string): string {
  return `${API_BASE}/discovery/assets/${assetId}/contact-sheet`;
}

export function getSampleImageUrl(sampleId: string): string {
  return `${API_BASE}/discovery/samples/${sampleId}/content`;
}

export function getManifestUrl(): string {
  return `${API_BASE}/discovery/manifest`;
}

// Multi-Source Dataset Discovery & Controlled Acquisition API

export async function fetchSourceProviders(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/acquisition/providers`);
  if (!res.ok) throw new Error("Failed to fetch discovery providers.");
  return res.json();
}

export async function searchDatasetCandidates(query: any): Promise<any[]> {
  const res = await fetch(`${API_BASE}/acquisition/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(query),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Search failed.");
  }
  return res.json();
}

export async function fetchDatasetCandidates(filters?: {
  source_id?: string;
  domain_tag?: string;
  license_status?: string;
  acquisition_status?: string;
  direct_videoscope_only?: boolean;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (filters?.source_id) query.append("source_id", filters.source_id);
  if (filters?.domain_tag) query.append("domain_tag", filters.domain_tag);
  if (filters?.license_status) query.append("license_status", filters.license_status);
  if (filters?.acquisition_status) query.append("acquisition_status", filters.acquisition_status);
  if (filters?.direct_videoscope_only) query.append("direct_videoscope_only", "true");

  const res = await fetch(`${API_BASE}/acquisition/candidates?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch dataset candidates.");
  return res.json();
}

export async function submitLicenseReview(candidateId: string, data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/acquisition/candidates/${candidateId}/license-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "License review submission failed.");
  }
  return res.json();
}

export async function acquireDatasetCandidate(candidateId: string, data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/acquisition/candidates/${candidateId}/acquire`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Dataset acquisition failed.");
  }
  return res.json();
}

export async function generateSyntheticMedia(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/acquisition/synthetic/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Synthetic generation failed.");
  }
  return res.json();
}

export async function fetchAcquisitionAuditTrail(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/acquisition/audit-trail`);
  if (!res.ok) throw new Error("Failed to fetch acquisition audit trail.");
  return res.json();
}

// --- Equipment Taxonomy & Decoupled Annotations API ---

export async function fetchTaxonomyStructure(): Promise<any> {
  const res = await fetch(`${API_BASE}/taxonomy/structure`);
  if (!res.ok) throw new Error("Failed to fetch taxonomy structure.");
  return res.json();
}

export async function translateSourceLabel(rawLabel: string, targetFamily?: string): Promise<any> {
  const query = new URLSearchParams({ raw_label: rawLabel });
  if (targetFamily) query.append("target_family", targetFamily);
  const res = await fetch(`${API_BASE}/taxonomy/translate?${query.toString()}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to translate label.");
  return res.json();
}

export async function createDecoupledAnnotation(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/taxonomy/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create decoupled annotation.");
  }
  return res.json();
}

export async function fetchDecoupledAnnotations(filters?: {
  asset_id?: string;
  equipment_family?: string;
  component_type?: string;
  defect_category?: string;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (filters?.asset_id) query.append("asset_id", filters.asset_id);
  if (filters?.equipment_family) query.append("equipment_family", filters.equipment_family);
  if (filters?.component_type) query.append("component_type", filters.component_type);
  if (filters?.defect_category) query.append("defect_category", filters.defect_category);

  const res = await fetch(`${API_BASE}/taxonomy/annotations?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch annotations.");
  return res.json();
}

// --- Equipment-Aware Evaluation & Benchmarking API ---

export async function runEvaluationBenchmark(config: any): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Evaluation benchmark failed.");
  }
  return res.json();
}

export async function fetchEvaluationRuns(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/evaluation/runs`);
  if (!res.ok) throw new Error("Failed to fetch evaluation runs.");
  return res.json();
}

export async function fetchEvaluationReport(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/evaluation/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch evaluation report.");
  return res.json();
}

// --- Candidate Findings & Human Review Workflow API ---

export async function fetchCandidateFindings(filters?: {
  asset_id?: string;
  review_state?: string;
  equipment_family?: string;
}): Promise<any[]> {
  const query = new URLSearchParams();
  if (filters?.asset_id) query.append("asset_id", filters.asset_id);
  if (filters?.review_state) query.append("review_state", filters.review_state);
  if (filters?.equipment_family) query.append("equipment_family", filters.equipment_family);

  const res = await fetch(`${API_BASE}/findings?${query.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch candidate findings.");
  return res.json();
}

export async function createCandidateFinding(data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/findings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create candidate finding.");
  }
  return res.json();
}

export async function submitFindingReviewDecision(findingId: string, data: any): Promise<any> {
  const res = await fetch(`${API_BASE}/findings/${findingId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to submit finding review decision.");
  }
  return res.json();
}

export async function fetchFindingDecisionHistory(findingId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/findings/${findingId}/history`);
  if (!res.ok) throw new Error("Failed to fetch finding decision history.");
  return res.json();
}



