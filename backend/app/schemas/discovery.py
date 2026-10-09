"""KeeAInu Phase 4A — Discovery, Profiling, and Domain Review Schemas."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DomainCategory(str, Enum):
    """Supported candidate inspection domains and fallback categories."""
    MECHANICAL = "MECHANICAL"  # Engines, turbines, machinery, rotating equipment
    PIPES_CHANNELS = "PIPES_CHANNELS"  # Internal tube/pipe surfaces, corrosion, cracks, deposits
    MOULD_CAVITIES = "MOULD_CAVITIES"  # Mould cooling channels, dies, internal casting cavities
    OTHER = "OTHER"  # Valid videoscope footage belonging to a distinct/different domain
    UNKNOWN = "UNKNOWN"  # Insufficient visual evidence or indeterminate domain


class DomainConfidence(str, Enum):
    """Reviewer confidence level in domain assignment."""
    CERTAIN = "CERTAIN"
    PROVISIONAL = "PROVISIONAL"
    UNCERTAIN = "UNCERTAIN"


class SampleReviewStatus(str, Enum):
    """Sampled representative frame review and defect triage states."""
    UNREVIEWED = "UNREVIEWED"
    NO_VISIBLE_DEFECT = "NO_VISIBLE_DEFECT"
    SUSPECTED_ANOMALY = "SUSPECTED_ANOMALY"
    CONFIRMED_DEFECT = "CONFIRMED_DEFECT"
    UNCERTAIN_NEEDS_EXPERT = "UNCERTAIN_NEEDS_EXPERT"
    UNUSABLE = "UNUSABLE"


class ValidationStatus(str, Enum):
    """Decoder & container integrity validation status."""
    VALID = "VALID"
    MALFORMED = "MALFORMED"
    UNREADABLE = "UNREADABLE"
    CORRUPT = "CORRUPT"


class TimestampProvenance(str, Enum):
    """Origin and precision classification of frame timestamps."""
    EXACT = "EXACT"
    NOMINAL_APPROXIMATE = "NOMINAL_APPROXIMATE"
    UNAVAILABLE = "UNAVAILABLE"


class QualityProfile(BaseModel):
    """Explainable heuristic indicators of visual media quality."""
    resolution: str = Field(..., description="e.g. '1280x720'")
    sharpness_score: float = Field(..., description="Laplacian variance indicative of edge focus")
    blur_detected: bool = Field(..., description="Heuristic flag if sharpness falls below focus threshold")
    brightness_mean: float = Field(..., description="Average intensity across all pixels (0-255)")
    contrast_std: float = Field(..., description="Standard deviation of intensity indicative of contrast")
    overexposure_ratio: float = Field(..., description="Fraction of pixels saturated at highlights (>250)")
    underexposure_ratio: float = Field(..., description="Fraction of pixels crushed in shadows (<10)")
    near_duplicate_ratio: float = Field(0.0, description="Estimated fraction of redundant/static frames")
    metadata_reliability: str = Field("NOMINAL", description="'HIGH', 'NOMINAL', or 'LOW'")
    explanations: List[str] = Field(default_factory=list, description="Human-readable heuristic explanations")


class SampleItem(BaseModel):
    """An individual representative visual frame extracted from an asset."""
    id: str
    asset_id: str
    frame_index: int
    timestamp_ms: float
    timestamp_provenance: TimestampProvenance
    file_path: str
    sha256_hash: str
    width: int
    height: int
    sharpness_score: float
    brightness_score: float
    contrast_score: float
    review_status: SampleReviewStatus = SampleReviewStatus.UNREVIEWED
    suspected_category: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str


class AssetRecord(BaseModel):
    """Inventory item representing an inspected video or still asset."""
    id: str
    source_path: str
    filename: str
    asset_type: str  # 'video' or 'image'
    extension: str
    file_size_bytes: int
    sha256_hash: str
    is_readable: bool
    width: int
    height: int
    duration_seconds: float
    fps: float
    total_frames: int
    is_synthetic: bool = False
    validation_status: ValidationStatus = ValidationStatus.VALID
    error_details: Optional[str] = None
    contact_sheet_path: Optional[str] = None
    quality_profile: Optional[QualityProfile] = None
    domain_assignment: Optional[DomainCategory] = DomainCategory.UNKNOWN
    domain_confidence: Optional[DomainConfidence] = DomainConfidence.UNCERTAIN
    domain_notes: Optional[str] = None
    domain_reviewed_by: Optional[str] = None
    domain_reviewed_at: Optional[str] = None
    samples_count: int = 0
    samples: List[SampleItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ScanDirectoryRequest(BaseModel):
    """Request payload to initiate or refresh a dataset discovery scan."""
    source_directory: Optional[str] = Field(None, description="Optional relative directory path inside project data root")
    sample_count_per_video: int = Field(5, ge=1, le=20, description="Number of representative frames to sample")
    force_rescan: bool = Field(False, description="Whether to re-profile previously ingested assets")


class UpdateDomainRequest(BaseModel):
    """Human reviewer assignment of candidate inspection domain."""
    domain_assignment: DomainCategory
    domain_confidence: DomainConfidence = DomainConfidence.PROVISIONAL
    domain_notes: Optional[str] = None
    reviewed_by: str = Field("Inspector", min_length=1)


class UpdateSampleReviewRequest(BaseModel):
    """Human reviewer defect classification for an individual sample frame."""
    review_status: SampleReviewStatus
    suspected_category: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_by: str = Field("Inspector", min_length=1)


class DiscoveryReport(BaseModel):
    """Comprehensive discovery and profiling summary report."""
    total_assets: int
    real_assets_count: int
    synthetic_assets_count: int
    readable_assets_count: int
    unreadable_assets_count: int
    total_samples_extracted: int
    metadata_completeness_percent: float
    domain_breakdown: Dict[str, int]
    defect_review_breakdown: Dict[str, int]
    average_sharpness: float
    blur_flagged_assets_count: int
    evaluation_split_recommendation: str
    unresolved_questions: List[str]
    generated_at: str


class DatasetManifest(BaseModel):
    """Machine-readable versioned discovery dataset manifest."""
    schema_version: str = "1.0.0"
    dataset_name: str = "KeeAInu Discovery Corpus"
    generated_at: str
    total_assets: int
    items: List[Dict[str, Any]]
