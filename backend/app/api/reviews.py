"""Inspector Review Decisions API Router."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.db.repository import repo
from backend.app.schemas.annotation import NormalizedBoundingBox

router = APIRouter(prefix="/reviews", tags=["Inspector Reviews"])


class SubmitReviewRequest(BaseModel):
    finding_id: str = Field(..., min_length=1)
    decision_status: str = Field(..., description="CONFIRMED, ADJUSTED, or REJECTED")
    severity: str = Field("INFORMATIONAL", description="CRITICAL, MAJOR, MINOR, or INFORMATIONAL")
    reviewed_by: str = Field(..., min_length=1, max_length=100)
    inspector_notes: Optional[str] = Field(None, max_length=1000)
    adjusted_bbox: Optional[NormalizedBoundingBox] = None


@router.post("", status_code=status.HTTP_200_OK)
@router.put("/{finding_id}", status_code=status.HTTP_200_OK)
async def submit_review(req: SubmitReviewRequest):
    """
    Record an inspector's verification decision for a candidate finding.
    Enforces status and severity validation.
    """
    try:
        adj_dict = req.adjusted_bbox.model_dump() if req.adjusted_bbox else None
        updated = repo.update_review(
            finding_id=req.finding_id,
            decision_status=req.decision_status,
            severity=req.severity,
            reviewed_by=req.reviewed_by,
            inspector_notes=req.inspector_notes,
            adjusted_bbox_dict=adj_dict
        )
        return updated
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
