"""Human-Reviewed Findings and Decision Workflow Schemas."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.schemas.taxonomy import EquipmentFamily, ComponentType, DefectCategory, BoundingBox


class FindingReviewState(str, Enum):
    """Enforced state machine for candidate finding review and confirmation."""
    UNREVIEWED = "UNREVIEWED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CONFIRMED_DEFECT = "CONFIRMED_DEFECT"
    NO_VISIBLE_DEFECT = "NO_VISIBLE_DEFECT"
    UNCERTAIN_NEEDS_EXPERT = "UNCERTAIN_NEEDS_EXPERT"
    UNUSABLE_EVIDENCE = "UNUSABLE_EVIDENCE"
    REJECTED_FALSE_POSITIVE = "REJECTED_FALSE_POSITIVE"


class FindingSeverity(str, Enum):
    """Human-assessed flaw severity."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFORMATIONAL = "INFORMATIONAL"
    UNSPECIFIED = "UNSPECIFIED"


VALID_FINDING_STATE_TRANSITIONS: Dict[FindingReviewState, List[FindingReviewState]] = {
    FindingReviewState.UNREVIEWED: [
        FindingReviewState.UNDER_REVIEW,
        FindingReviewState.CONFIRMED_DEFECT,
        FindingReviewState.NO_VISIBLE_DEFECT,
        FindingReviewState.UNCERTAIN_NEEDS_EXPERT,
        FindingReviewState.UNUSABLE_EVIDENCE,
        FindingReviewState.REJECTED_FALSE_POSITIVE
    ],
    FindingReviewState.UNDER_REVIEW: [
        FindingReviewState.CONFIRMED_DEFECT,
        FindingReviewState.NO_VISIBLE_DEFECT,
        FindingReviewState.UNCERTAIN_NEEDS_EXPERT,
        FindingReviewState.UNUSABLE_EVIDENCE,
        FindingReviewState.REJECTED_FALSE_POSITIVE,
        FindingReviewState.UNREVIEWED
    ],
    FindingReviewState.CONFIRMED_DEFECT: [
        FindingReviewState.UNDER_REVIEW,
        FindingReviewState.UNCERTAIN_NEEDS_EXPERT,
        FindingReviewState.REJECTED_FALSE_POSITIVE
    ],
    FindingReviewState.NO_VISIBLE_DEFECT: [
        FindingReviewState.UNDER_REVIEW,
        FindingReviewState.CONFIRMED_DEFECT
    ],
    FindingReviewState.UNCERTAIN_NEEDS_EXPERT: [
        FindingReviewState.CONFIRMED_DEFECT,
        FindingReviewState.NO_VISIBLE_DEFECT,
        FindingReviewState.UNUSABLE_EVIDENCE,
        FindingReviewState.REJECTED_FALSE_POSITIVE
    ],
    FindingReviewState.UNUSABLE_EVIDENCE: [
        FindingReviewState.UNDER_REVIEW
    ],
    FindingReviewState.REJECTED_FALSE_POSITIVE: [
        FindingReviewState.UNDER_REVIEW,
        FindingReviewState.CONFIRMED_DEFECT
    ]
}


class CandidateFindingRecord(BaseModel):
    """An observation or candidate finding with equipment context and review state."""
    id: str
    asset_id: str
    sample_id: Optional[str] = None
    frame_index: int = 0
    timestamp_ms: float = 0.0
    timestamp_provenance: str = "NOMINAL_APPROXIMATE"
    equipment_family: EquipmentFamily
    component_type: ComponentType
    candidate_defect: DefectCategory
    candidate_bbox: Optional[BoundingBox] = None
    model_prediction_confidence: Optional[float] = None
    is_simulated: bool = True
    review_state: FindingReviewState = FindingReviewState.UNREVIEWED
    severity: FindingSeverity = FindingSeverity.UNSPECIFIED
    reviewed_by: Optional[str] = None
    reviewer_rationale: Optional[str] = None
    engineering_diagnosis: Optional[str] = None
    advisory_recommendation: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str
    updated_at: str


class SubmitFindingDecisionRequest(BaseModel):
    """Payload to record or transition a human review decision."""
    review_state: FindingReviewState
    severity: FindingSeverity = FindingSeverity.UNSPECIFIED
    reviewed_by: str = Field(..., min_length=1, description="Authorized inspector / reviewer name")
    reviewer_rationale: str = Field(..., min_length=1, description="Reasoning and engineering evidence for the disposition")
    adjusted_defect_category: Optional[DefectCategory] = None
    adjusted_bbox: Optional[BoundingBox] = None
    engineering_diagnosis: Optional[str] = None
    advisory_recommendation: Optional[str] = None
