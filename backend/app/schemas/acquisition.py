"""Pydantic schemas for Multi-Source Dataset Discovery and Controlled Acquisition (Phase 4A.1 / Multi-Source Expansion)."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourceProviderCategory(str, Enum):
    """Categorization of dataset source providers."""
    PUBLIC_CATALOG = "PUBLIC_CATALOG"
    RESEARCH_INSTITUTION = "RESEARCH_INSTITUTION"
    GOVERNMENT_CATALOG = "GOVERNMENT_CATALOG"
    CLOUD_REGISTRY = "CLOUD_REGISTRY"
    INTERNAL_STORAGE = "INTERNAL_STORAGE"
    SYNTHETIC_GENERATOR = "SYNTHETIC_GENERATOR"


class LicensePermissionStatus(str, Enum):
    """Explicit license and permission gating states."""
    LICENSE_UNKNOWN = "LICENSE_UNKNOWN"
    APPROVED_FOR_EVALUATION = "APPROVED_FOR_EVALUATION"
    APPROVED_FOR_NONCOMMERCIAL_RESEARCH = "APPROVED_FOR_NONCOMMERCIAL_RESEARCH"
    COMMERCIAL_USE_REVIEW_REQUIRED = "COMMERCIAL_USE_REVIEW_REQUIRED"
    ACCESS_RESTRICTED = "ACCESS_RESTRICTED"
    DOWNLOAD_NOT_AUTHORIZED = "DOWNLOAD_NOT_AUTHORIZED"
    REJECTED = "REJECTED"


class CandidateAcquisitionStatus(str, Enum):
    """State progression of discovered candidate datasets."""
    DISCOVERED = "DISCOVERED"
    LICENSE_REVIEWED = "LICENSE_REVIEWED"
    ACQUISITION_APPROVED = "ACQUISITION_APPROVED"
    DOWNLOADING = "DOWNLOADING"
    INGESTED = "INGESTED"
    REJECTED = "REJECTED"


class DiscoveryVerificationStatus(str, Enum):
    """Honest verification state of dataset candidate metadata."""
    LIVE_METADATA_VERIFIED = "LIVE_METADATA_VERIFIED"
    CURATED_LEAD_AWAITING_VERIFICATION = "CURATED_LEAD_AWAITING_VERIFICATION"
    PUBLISHER_LINK_VERIFIED_DATA_UNAVAILABLE = "PUBLISHER_LINK_VERIFIED_DATA_UNAVAILABLE"
    SOURCE_UNREACHABLE = "SOURCE_UNREACHABLE"
    LICENSE_OR_ACCESS_UNKNOWN = "LICENSE_OR_ACCESS_UNKNOWN"


class DownloadSupportStatus(str, Enum):
    """Operational status for direct automated acquisition."""
    DIRECT_DOWNLOAD_SUPPORTED = "DIRECT_DOWNLOAD_SUPPORTED"
    INTERNAL_SANDBOX_IMPORT = "INTERNAL_SANDBOX_IMPORT"
    SYNTHETIC_GENERATION_SUPPORTED = "SYNTHETIC_GENERATION_SUPPORTED"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"


class JobStatus(str, Enum):
    """Acquisition and generation job execution statuses."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    MANUAL_ACTION_REQUIRED = "MANUAL_ACTION_REQUIRED"


class ProvenanceType(str, Enum):
    """Classification of asset origin and lineage."""
    DIRECT_ACQUISITION = "DIRECT_ACQUISITION"
    INTERNAL_IMPORT = "INTERNAL_IMPORT"
    SYNTHETIC_PROCEDURAL = "SYNTHETIC_PROCEDURAL"
    SYNTHETIC_AUGMENTED = "SYNTHETIC_AUGMENTED"


class RelevanceScoreBreakdown(BaseModel):
    """Transparent explainable relevance sub-scores (0-100 total)."""
    videoscope_similarity: float = Field(..., description="Borescope/probe visual characteristics (0-30)")
    domain_match: float = Field(..., description="Mechanical / Pipes / Moulds domain affinity (0-25)")
    modality_match: float = Field(..., description="Video stream vs high-res still vs other (0-15)")
    defect_utility: float = Field(..., description="Presence of genuine flaw/crack/corrosion labels (0-15)")
    annotation_quality: float = Field(..., description="Masks / BBoxes / Tags / Unlabeled (0-10)")
    provenance_completeness: float = Field(..., description="Source integrity, sensor documentation (0-5)")
    total_score: float = Field(..., description="Sum of weighted criteria (0-100)")
    is_direct_videoscope: bool = Field(..., description="Whether dataset is verified borescope/endoscope footage")
    relevance_explanations: List[str] = Field(default_factory=list, description="Reasoning and caveats")


class SourceProviderInfo(BaseModel):
    """Registered discovery provider information."""
    id: str
    name: str
    category: SourceProviderCategory
    base_url: Optional[str] = None
    is_enabled: bool = True
    auth_configured: bool = False
    rate_limit_per_min: int = 60
    description: str
    supports_live_search: bool = False
    default_download_support: DownloadSupportStatus = DownloadSupportStatus.MANUAL_ACTION_REQUIRED


class SearchCandidateQuery(BaseModel):
    """Multi-source search parameters."""
    query: str = Field(..., min_length=1, description="Search term or topic")
    target_domain: Optional[str] = Field(None, description="Candidate domain e.g. MECHANICAL, PIPES_CHANNELS, MOULD_CAVITIES")
    provider_ids: Optional[List[str]] = Field(None, description="Limit search to specific providers")
    direct_videoscope_only: bool = Field(False, description="Filter for direct borescope/endoscope media only")
    max_results_per_provider: int = Field(10, ge=1, le=50)


class DatasetCandidateRecord(BaseModel):
    """A discovered candidate dataset or collection."""
    id: str
    source_id: str
    provider_name: str
    title: str
    publisher: str
    external_id: Optional[str] = None
    canonical_url: str
    landing_page_url: Optional[str] = None
    domain_tag: str
    is_direct_videoscope: bool
    modalities: List[str]
    approximate_size_bytes: Optional[int] = None
    file_count: Optional[int] = None
    annotation_types: List[str]
    license_identifier: str
    license_url: Optional[str] = None
    license_status: LicensePermissionStatus
    commercial_use_allowed: bool
    attribution_required: bool
    relevance_score: float
    relevance_breakdown: Optional[RelevanceScoreBreakdown] = None
    description: Optional[str] = None
    limitations_notes: Optional[str] = None
    acquisition_status: CandidateAcquisitionStatus
    verification_status: DiscoveryVerificationStatus = DiscoveryVerificationStatus.CURATED_LEAD_AWAITING_VERIFICATION
    download_support: DownloadSupportStatus = DownloadSupportStatus.MANUAL_ACTION_REQUIRED
    created_at: str
    updated_at: str


class LicenseReviewRequest(BaseModel):
    """Payload for human license audit and decision."""
    license_status: LicensePermissionStatus
    commercial_rights_status: str = Field(..., description="'ALLOWED', 'FORBIDDEN', or 'REVIEW_REQUIRED'")
    license_notes: Optional[str] = None
    terms_url: Optional[str] = None
    reviewed_by: str = Field("Compliance Officer", min_length=1)


class AcquireCandidateRequest(BaseModel):
    """Request to initiate controlled download or import."""
    candidate_id: str
    max_files_limit: int = Field(20, ge=1, le=100, description="Bounding safety limit on imported assets")
    max_megabytes_limit: int = Field(200, ge=1, le=1000, description="Bounding size limit in MB")
    requested_by: str = Field("Inspector", min_length=1)


class SyntheticGenerationRequest(BaseModel):
    """Request to generate controlled synthetic defect media."""
    generation_type: str = Field("PROCEDURAL_SURFACE", description="'PROCEDURAL_SURFACE', 'DEFECT_OVERLAY', 'NOISE_VARIATION'")
    target_domain: str = Field("PIPES_CHANNELS", description="'MECHANICAL', 'PIPES_CHANNELS', 'MOULD_CAVITIES'")
    defect_type: str = Field("CRACK", description="'CRACK', 'CORROSION_PIT', 'EROSION', 'DEPOSIT'")
    count: int = Field(3, ge=1, le=20, description="Number of synthetic items to generate")
    parent_asset_id: Optional[str] = Field(None, description="Optional parent source asset ID for augmentation")
    lighting_variation: float = Field(0.2, ge=0.0, le=1.0)
    blur_level: float = Field(0.0, ge=0.0, le=1.0)
    noise_level: float = Field(0.1, ge=0.0, le=1.0)
    random_seed: Optional[int] = Field(42)
    requested_by: str = Field("ML Engineer", min_length=1)


class AcquisitionJobRecord(BaseModel):
    """Execution status of an acquisition or synthetic generation job."""
    id: str
    candidate_id: Optional[str] = None
    job_type: str
    status: JobStatus
    target_directory: str
    bytes_downloaded: int = 0
    files_acquired: int = 0
    error_message: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str


class AcquisitionAuditEvent(BaseModel):
    """Audit log entry for compliance and provenance tracing."""
    id: str
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None
    event_type: str
    details: Dict[str, Any]
    created_at: str
