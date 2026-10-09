export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Finding {
  id: string;
  session_id: string;
  media_id: string;
  frame_index: number;
  timestamp_ms: number;
  defect_class: string;
  confidence_score: number;
  bbox: BoundingBox;
  polygon_mask?: [number, number][];
  evidence_sha256?: string;
  inference_record_id?: string;
  is_simulated: boolean;
  model_name: string;
  model_version: string;
  created_at: string;
  review_id?: string;
  decision_status?: "PENDING_REVIEW" | "CONFIRMED" | "ADJUSTED" | "REJECTED";
  severity?: "CRITICAL" | "MAJOR" | "MINOR" | "INFORMATIONAL";
  inspector_notes?: string;
  adjusted_bbox?: BoundingBox;
  reviewed_by?: string;
  reviewed_at?: string;
}

export interface InferenceEngineInfo {
  engine_name: string;
  model_version: string;
  is_simulated: boolean;
  auth_configured: boolean;
}

export interface InferenceRecord {
  id: string;
  session_id: string;
  media_id: string;
  frame_index: number;
  timestamp_ms: number;
  evidence_sha256: string;
  engine_name: string;
  model_id: string;
  model_version: string;
  prompt_config?: { prompts?: string[] };
  is_simulated: boolean;
  processing_duration_ms: number;
  cache_hit: boolean;
  created_at: string;
}

export interface MediaItem {
  id: string;
  session_id: string;
  filename: string;
  file_path: string;
  media_type: string;
  sha256_hash: string;
  width: number;
  height: number;
  duration_seconds: number;
  fps: number;
  total_frames: number;
  is_readable: boolean;
  created_at: string;
}

export interface ThumbnailItem {
  id: string;
  media_id: string;
  frame_index: number;
  timestamp_ms: number;
  file_path: string;
  sha256_hash: string;
  created_at: string;
}

export interface InspectionSession {
  id: string;
  title: string;
  inspector_name: string;
  status: "DRAFT" | "IN_REVIEW" | "COMPLETED" | "ARCHIVED";
  asset_tag?: string;
  created_at: string;
  updated_at: string;
  media?: MediaItem[];
}
