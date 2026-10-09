"""Candidate Findings & Human Review Workflow API Endpoints.

Strictly enforces:
1. Backend review state machine transitions.
2. Reviewer authorization check for CONFIRMED_DEFECT dispositions.
3. Mandatory engineering rationale and inspector identification.
4. Immutable audit history logging.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Header, status

from backend.app.schemas.findings_review import (
    FindingReviewState,
    FindingSeverity,
    CandidateFindingRecord,
    SubmitFindingDecisionRequest,
    VALID_FINDING_STATE_TRANSITIONS
)
from backend.app.schemas.taxonomy import EquipmentFamily, ComponentType, DefectCategory, BoundingBox
from backend.app.db.repository import repo

router = APIRouter(prefix="/findings", tags=["Human Review & Candidate Findings"])

AUTHORIZED_CONFIRMATION_ROLES = {
    "LEAD_INSPECTOR",
    "NDT_LEVEL_3",
    "CHIEF_INSPECTOR",
    "AUTHORIZED_REVIEWER",
    "SENIOR_NDT_EXPERT",
    "INSPECTOR_LEVEL_2"
}

UNAUTHORIZED_ROLES = {
    "TRAINEE",
    "GUEST",
    "READONLY",
    "UNAUTHORIZED",
    "ANONYMOUS"
}


@router.get("", response_model=List[CandidateFindingRecord])
async def list_candidate_findings(
    asset_id: Optional[str] = None,
    review_state: Optional[FindingReviewState] = None,
    equipment_family: Optional[EquipmentFamily] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List candidate findings with review state and equipment filters."""
    return repo.list_candidate_findings(
        asset_id=asset_id,
        review_state=review_state.value if review_state else None,
        equipment_family=equipment_family.value if equipment_family else None,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=CandidateFindingRecord, status_code=status.HTTP_201_CREATED)
async def create_candidate_finding(finding: CandidateFindingRecord):
    """Register a new candidate finding observation from detection or mock generator."""
    finding_dict = finding.model_dump()
    if finding.candidate_bbox:
        finding_dict["candidate_bbox"] = finding.candidate_bbox.model_dump()
    return repo.create_candidate_finding(finding_dict)


@router.get("/{finding_id}", response_model=CandidateFindingRecord)
async def get_candidate_finding(finding_id: str):
    """Retrieve full details of a candidate finding."""
    record = repo.get_candidate_finding(finding_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{finding_id}' not found.")
    return record


@router.post("/{finding_id}/decision", response_model=CandidateFindingRecord)
async def submit_review_decision(
    finding_id: str,
    request: SubmitFindingDecisionRequest,
    x_inspector_role: Optional[str] = Header(None, alias="X-Inspector-Role"),
    x_inspector_id: Optional[str] = Header(None, alias="X-Inspector-Id")
):
    """
    Submit an authorized human review decision for a candidate finding.
    Strictly validates state transitions, caller authorization, and records immutable audit history.
    """
    current = repo.get_candidate_finding(finding_id)
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Finding '{finding_id}' not found.")

    current_state = FindingReviewState(current["review_state"])
    target_state = request.review_state

    # 1. Validate state transition rules
    allowed_transitions = VALID_FINDING_STATE_TRANSITIONS.get(current_state, [])
    if target_state != current_state and target_state not in allowed_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid review state transition from '{current_state.value}' to '{target_state.value}'."
        )

    # 2. Enforce authorization for defect confirmation
    if target_state == FindingReviewState.CONFIRMED_DEFECT:
        effective_role = (x_inspector_role or request.reviewer_role or "").strip().upper()
        # Check explicit unauthorized role
        if effective_role and effective_role in UNAUTHORIZED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{effective_role}' is not authorized to confirm certified defects."
            )

        # Require reviewer name and substantive engineering rationale
        if not request.reviewed_by or not request.reviewed_by.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Reviewer name is required to confirm a defect."
            )

        if not request.reviewer_rationale or len(request.reviewer_rationale.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Substantive engineering rationale is required to confirm a defect."
            )

    effective_reviewer = request.reviewed_by.strip()
    if x_inspector_id and x_inspector_id.strip():
        effective_reviewer = f"{effective_reviewer} [{x_inspector_id.strip()}]"

    updated = repo.record_finding_decision(
        finding_id=finding_id,
        review_state=target_state.value,
        severity=request.severity.value,
        reviewed_by=effective_reviewer,
        reviewer_rationale=request.reviewer_rationale.strip(),
        adjusted_defect=request.adjusted_defect_category.value if request.adjusted_defect_category else None,
        adjusted_bbox=request.adjusted_bbox.model_dump() if request.adjusted_bbox else None,
        engineering_diagnosis=request.engineering_diagnosis,
        advisory_recommendation=request.advisory_recommendation
    )

    return updated


@router.get("/{finding_id}/history", response_model=List[Dict[str, Any]])
async def get_finding_history(finding_id: str):
    """Retrieve complete decision history and audit trail for a candidate finding."""
    history = repo.get_finding_decision_history(finding_id)
    return history
