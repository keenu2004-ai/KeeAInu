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

export async function analyzeFrame(data: {
  session_id: string;
  media_id: string;
  frame_index: number;
  confidence_threshold?: number;
}): Promise<{ findings: Finding[]; is_simulated: boolean }> {
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

