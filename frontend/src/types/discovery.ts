export type DomainCategory =
  | "MECHANICAL"
  | "PIPES_CHANNELS"
  | "MOULD_CAVITIES"
  | "OTHER"
  | "UNKNOWN";

export type DomainConfidence = "CERTAIN" | "PROVISIONAL" | "UNCERTAIN";

export type SampleReviewStatus =
  | "UNREVIEWED"
  | "NO_VISIBLE_DEFECT"
  | "SUSPECTED_ANOMALY"
  | "CONFIRMED_DEFECT"
  | "UNCERTAIN_NEEDS_EXPERT"
  | "UNUSABLE";

export interface QualityProfile {
  resolution: string;
  sharpness_score: number;
  blur_detected: boolean;
  brightness_mean: number;
  contrast_std: number;
  overexposure_ratio: number;
  underexposure_ratio: number;
  near_duplicate_ratio: number;
  metadata_reliability: string;
  explanations: string[];
}

export interface SampleItem {
  id: string;
  asset_id: string;
  frame_index: number;
  timestamp_ms: number;
  timestamp_provenance: "EXACT" | "NOMINAL_APPROXIMATE" | "UNAVAILABLE";
  file_path: string;
  sha256_hash: string;
  width: number;
  height: number;
  sharpness_score: number;
  brightness_score: number;
  contrast_score: number;
  review_status: SampleReviewStatus;
  suspected_category?: string;
  reviewer_notes?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface AssetRecord {
  id: string;
  source_path: string;
  filename: string;
  asset_type: "video" | "image";
  extension: string;
  file_size_bytes: number;
  sha256_hash: string;
  is_readable: boolean;
  width: number;
  height: number;
  duration_seconds: number;
  fps: number;
  total_frames: number;
  is_synthetic: boolean;
  validation_status: "VALID" | "MALFORMED" | "UNREADABLE" | "CORRUPT";
  error_details?: string;
  contact_sheet_path?: string;
  quality_profile?: QualityProfile;
  domain_assignment: DomainCategory;
  domain_confidence: DomainConfidence;
  domain_notes?: string;
  domain_reviewed_by?: string;
  domain_reviewed_at?: string;
  samples_count: number;
  samples: SampleItem[];
  created_at: string;
  updated_at: string;
}

export interface DiscoveryReport {
  total_assets: number;
  real_assets_count: number;
  synthetic_assets_count: number;
  readable_assets_count: number;
  unreadable_assets_count: number;
  total_samples_extracted: number;
  metadata_completeness_percent: number;
  domain_breakdown: Record<string, number>;
  defect_review_breakdown: Record<string, number>;
  average_sharpness: number;
  blur_flagged_assets_count: number;
  evaluation_split_recommendation: string;
  unresolved_questions: string[];
  generated_at: string;
}
