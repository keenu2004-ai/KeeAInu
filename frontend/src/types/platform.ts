export type EquipmentFamily = 
  | "ENGINES_TURBINES"
  | "GEARBOXES_TRANSMISSIONS"
  | "OTHER_MECHANICAL_ASSEMBLIES"
  | "UNKNOWN_EQUIPMENT";

export type ComponentType = string;
export type DefectCategory = string;
export type MappingConfidence = "EXACT_MATCH" | "SEMANTIC_EQUIVALENT" | "PROVISIONAL_INFERRED" | "UNCERTAIN";

export interface DecoupledAnnotation {
  id: string;
  asset_id: string;
  sample_id?: string;
  frame_index: number;
  equipment_family: EquipmentFamily;
  component_type: ComponentType;
  defect_category: DefectCategory;
  observed_visual_condition?: string;
  bbox?: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  source_raw_label?: string;
  mapping_confidence: MappingConfidence;
  annotator_type: string;
  annotator_id: string;
  taxonomy_version: string;
  is_synthetic: boolean;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export type FindingReviewState = 
  | "UNREVIEWED"
  | "UNDER_REVIEW"
  | "CONFIRMED_DEFECT"
  | "NO_VISIBLE_DEFECT"
  | "UNCERTAIN_NEEDS_EXPERT"
  | "UNUSABLE_EVIDENCE"
  | "REJECTED_FALSE_POSITIVE";

export type FindingSeverity = "CRITICAL" | "MAJOR" | "MINOR" | "INFORMATIONAL" | "UNSPECIFIED";

export interface CandidateFinding {
  id: string;
  asset_id: string;
  sample_id?: string;
  frame_index: number;
  timestamp_ms: number;
  timestamp_provenance: string;
  equipment_family: EquipmentFamily;
  component_type: ComponentType;
  candidate_defect: DefectCategory;
  candidate_bbox?: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  model_prediction_confidence?: number;
  is_simulated: boolean;
  review_state: FindingReviewState;
  severity: FindingSeverity;
  reviewed_by?: string;
  reviewer_rationale?: string;
  engineering_diagnosis?: string;
  advisory_recommendation?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ClassificationMetric {
  precision?: number;
  recall?: number;
  f1_score?: number;
  support: number;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
  status: "VALID" | "UNDEFINED_ZERO_SUPPORT" | "INSUFFICIENT_SAMPLES";
}

export interface LocalizationMetric {
  mean_iou?: number;
  pixel_precision?: number;
  pixel_recall?: number;
  pixel_f1?: number;
  evaluated_objects_count: number;
  status: "VALID" | "UNDEFINED_ZERO_SUPPORT" | "INSUFFICIENT_SAMPLES";
}

export interface EquipmentSliceResult {
  equipment_family: EquipmentFamily;
  component_type?: ComponentType;
  defect_category?: DefectCategory;
  sample_count: number;
  is_synthetic: boolean;
  classification: ClassificationMetric;
  localization?: LocalizationMetric;
}

export interface EvaluationReport {
  run_id: string;
  run_name: string;
  dataset_manifest_hash: string;
  total_assets_evaluated: number;
  total_samples_evaluated: number;
  real_samples_count: number;
  synthetic_samples_count: number;
  split_strategy: string;
  overall_classification: ClassificationMetric;
  equipment_slices: EquipmentSliceResult[];
  confusion_matrix_labels: string[];
  confusion_matrix: number[][];
  is_simulated_baseline: boolean;
  limitations: string[];
  created_at: string;
}
