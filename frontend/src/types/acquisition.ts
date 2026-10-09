/**
 * KeeAInu Multi-Source Dataset Discovery & Controlled Acquisition Frontend Types.
 */

export type SourceProviderCategory =
  | 'PUBLIC_CATALOG'
  | 'RESEARCH_INSTITUTION'
  | 'GOVERNMENT_CATALOG'
  | 'CLOUD_REGISTRY'
  | 'INTERNAL_STORAGE'
  | 'SYNTHETIC_GENERATOR';

export type LicensePermissionStatus =
  | 'LICENSE_UNKNOWN'
  | 'APPROVED_FOR_EVALUATION'
  | 'APPROVED_FOR_NONCOMMERCIAL_RESEARCH'
  | 'COMMERCIAL_USE_REVIEW_REQUIRED'
  | 'ACCESS_RESTRICTED'
  | 'DOWNLOAD_NOT_AUTHORIZED'
  | 'REJECTED';

export type CandidateAcquisitionStatus =
  | 'DISCOVERED'
  | 'LICENSE_REVIEWED'
  | 'ACQUISITION_APPROVED'
  | 'DOWNLOADING'
  | 'INGESTED'
  | 'REJECTED';

export type JobStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface SourceProviderInfo {
  id: string;
  name: string;
  category: SourceProviderCategory;
  base_url?: string;
  is_enabled: boolean;
  auth_configured: boolean;
  rate_limit_per_min: number;
  description: string;
}

export interface RelevanceScoreBreakdown {
  videoscope_similarity: number;
  domain_match: number;
  modality_match: number;
  defect_utility: number;
  annotation_quality: number;
  provenance_completeness: number;
  total_score: number;
  is_direct_videoscope: boolean;
  relevance_explanations: string[];
}

export interface DatasetCandidateRecord {
  id: string;
  source_id: string;
  provider_name: string;
  title: string;
  publisher: string;
  external_id?: string;
  canonical_url: string;
  landing_page_url?: string;
  domain_tag: string;
  is_direct_videoscope: boolean;
  modalities: string[];
  approximate_size_bytes?: number;
  file_count?: number;
  annotation_types: string[];
  license_identifier: string;
  license_url?: string;
  license_status: LicensePermissionStatus;
  commercial_use_allowed: boolean;
  attribution_required: boolean;
  relevance_score: number;
  relevance_breakdown?: RelevanceScoreBreakdown;
  description?: string;
  limitations_notes?: string;
  acquisition_status: CandidateAcquisitionStatus;
  created_at: string;
  updated_at: string;
}

export interface SearchCandidateQuery {
  query: string;
  target_domain?: string;
  provider_ids?: string[];
  direct_videoscope_only?: boolean;
  max_results_per_provider?: number;
}

export interface LicenseReviewRequest {
  license_status: LicensePermissionStatus;
  commercial_rights_status: 'ALLOWED' | 'FORBIDDEN' | 'REVIEW_REQUIRED';
  license_notes?: string;
  terms_url?: string;
  reviewed_by: string;
}

export interface AcquireCandidateRequest {
  candidate_id: string;
  max_files_limit: number;
  max_megabytes_limit: number;
  requested_by: string;
}

export interface SyntheticGenerationRequest {
  generation_type: 'PROCEDURAL_SURFACE' | 'DEFECT_OVERLAY' | 'NOISE_VARIATION';
  target_domain: 'MECHANICAL' | 'PIPES_CHANNELS' | 'MOULD_CAVITIES';
  defect_type: 'CRACK' | 'CORROSION_PIT' | 'EROSION' | 'DEPOSIT';
  count: number;
  parent_asset_id?: string;
  lighting_variation: number;
  blur_level: number;
  noise_level: number;
  random_seed?: number;
  requested_by: string;
}

export interface AcquisitionJobRecord {
  id: string;
  candidate_id?: string;
  job_type: string;
  status: JobStatus;
  target_directory: string;
  bytes_downloaded: number;
  files_acquired: number;
  error_message?: string;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface AcquisitionAuditEvent {
  id: string;
  job_id?: string;
  candidate_id?: string;
  event_type: string;
  details: Record<string, any>;
  created_at: string;
}
