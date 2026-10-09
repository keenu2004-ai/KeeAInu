"""Inspection Sessions API Router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from backend.app.db.repository import repo

router = APIRouter(prefix="/sessions", tags=["Inspection Sessions"])


class CreateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    inspector_name: str = Field(..., min_length=1, max_length=100)
    asset_tag: Optional[str] = Field(None, max_length=100)


class UpdateSessionStatusRequest(BaseModel):
    status: str = Field(..., description="Target status (IN_REVIEW, COMPLETED, ARCHIVED)")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(req: CreateSessionRequest):
    """Create a new inspection session."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session = repo.create_session(
        session_id=session_id,
        title=req.title,
        inspector_name=req.inspector_name,
        asset_tag=req.asset_tag
    )
    return session


@router.get("")
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List inspection sessions with bounded pagination."""
    return repo.list_sessions(skip=skip, limit=limit)


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Retrieve an inspection session and its attached media metadata."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found."
        )
    return session


@router.patch("/{session_id}/status")
async def update_session_status(session_id: str, req: UpdateSessionStatusRequest):
    """Update inspection session status with state transition validation."""
    try:
        updated = repo.update_session_status(session_id, req.status)
        return updated
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
