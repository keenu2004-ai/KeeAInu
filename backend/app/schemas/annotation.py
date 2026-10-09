"""KeeAInu Versioned Annotation Data Schema and Validators."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class ProvenanceType(str, Enum):
    """Provenance category for ground truth data."""
    SYNTHETIC_GENERATED = "SYNTHETIC_GENERATED"
    HUMAN_VERIFIED = "HUMAN_VERIFIED"
    EXPERT_AUDITED = "EXPERT_AUDITED"


class NormalizedBoundingBox(BaseModel):
    """Normalized bounding box coordinates (0.0 <= min < max <= 1.0)."""
    x_min: float = Field(..., description="Left bound [0.0, 1.0]")
    y_min: float = Field(..., description="Top bound [0.0, 1.0]")
    x_max: float = Field(..., description="Right bound [0.0, 1.0]")
    y_max: float = Field(..., description="Bottom bound [0.0, 1.0]")

    @field_validator("x_min", "y_min", "x_max", "y_max")
    @classmethod
    def validate_range(cls, v: float, info) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"{info.field_name} must be between 0.0 and 1.0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_box_invariants(self) -> "NormalizedBoundingBox":
        if self.x_min >= self.x_max:
            raise ValueError(f"x_min ({self.x_min}) must be strictly less than x_max ({self.x_max})")
        if self.y_min >= self.y_max:
            raise ValueError(f"y_min ({self.y_min}) must be strictly less than y_max ({self.y_max})")
        return self


class GroundTruthAnnotationItem(BaseModel):
    """Single ground-truth annotation for a specific frame."""
    annotation_id: str = Field(..., min_length=1)
    frame_index: int = Field(..., ge=0)
    timestamp_ms: float = Field(..., ge=0.0)
    defect_class: str = Field(..., min_length=1)
    bbox: NormalizedBoundingBox
    polygon_mask: Optional[List[List[float]]] = None
    inspector_notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GroundTruthDatasetRecord(BaseModel):
    """Machine-readable versioned ground truth dataset record."""
    schema_version: str = Field("1.0.0", description="Schema version identifier")
    dataset_id: str = Field(..., min_length=1)
    media_id: str = Field(..., min_length=1)
    media_sha256: str = Field(..., pattern=r"^[a-f0-9]{64}$")
    media_filename: str = Field(..., min_length=1)
    image_width: int = Field(..., gt=0)
    image_height: int = Field(..., gt=0)
    provenance: ProvenanceType
    is_synthetic: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    annotations: List[GroundTruthAnnotationItem] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v != "1.0.0":
            raise ValueError(f"Unsupported schema version: {v}. Expected '1.0.0'")
        return v

    @model_validator(mode="after")
    def validate_synthetic_flag(self) -> "GroundTruthDatasetRecord":
        if self.provenance == ProvenanceType.SYNTHETIC_GENERATED and not self.is_synthetic:
            raise ValueError("is_synthetic must be True when provenance is SYNTHETIC_GENERATED")
        return self
