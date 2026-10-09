"""Simulated AI Inference and Findings API Router (Hardened)."""

import uuid
from pathlib import Path
from typing import List, Optional
import cv2
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.security import is_path_safe, verify_and_resolve_media_file
from backend.app.db.repository import repo
from backend.app.modules.inference.mock_engine import MockInferenceEngine
from backend.app.modules.video.extractor import VideoFrameExtractor

router = APIRouter(prefix="/inference", tags=["Inference & Defect Analysis"])

# Instantiate pluggable engine
mock_engine = MockInferenceEngine()


class AnalyzeFrameRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    media_id: str = Field(..., min_length=1)
    frame_index: int = Field(0, ge=0)
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)


@router.post("/analyze-frame", status_code=status.HTTP_200_OK)
async def analyze_frame(req: AnalyzeFrameRequest):
    """
    Run simulated defect candidate analysis on a selected media frame.
    Enforces session/media association integrity, evidence hash verification, and explicit simulation labeling.
    """
    session = repo.get_session(req.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{req.session_id}' not found."
        )

    media = repo.get_media(req.media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media '{req.media_id}' not found."
        )

    # Gate 3: Enforce session/media consistency
    if media["session_id"] != req.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error: Media '{req.media_id}' does not belong to session '{req.session_id}'."
        )

    file_path = verify_and_resolve_media_file(media, settings.RAW_MEDIA_DIR)

    frame_bytes = b""
    timestamp_ms = 0.0

    if media["media_type"].startswith("video/"):
        try:
            with VideoFrameExtractor(file_path) as extractor:
                frame_bgr, frame_meta = extractor.extract_frame(req.frame_index)
                timestamp_ms = frame_meta.timestamp_ms
                success, encoded = cv2.imencode(".jpg", frame_bgr)
                if not success or encoded is None:
                    raise RuntimeError(f"Failed to encode frame {req.frame_index} for inference.")
                frame_bytes = encoded.tobytes()
        except IndexError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    else:
        frame_bytes = file_path.read_bytes()

    if not frame_bytes or len(frame_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Frame buffer is empty; cannot run inference."
        )

    # Execute inference engine
    inference_res = await mock_engine.infer_frame(
        frame_bytes=frame_bytes,
        frame_index=req.frame_index,
        timestamp_ms=timestamp_ms,
        confidence_threshold=req.confidence_threshold
    )

    persisted_findings = []
    for candidate in inference_res.findings:
        finding_id = f"fnd_{uuid.uuid4().hex[:12]}"
        record = repo.add_finding(
            finding_id=finding_id,
            session_id=req.session_id,
            media_id=req.media_id,
            frame_index=req.frame_index,
            timestamp_ms=timestamp_ms,
            defect_class=candidate.defect_class,
            confidence_score=candidate.confidence_score,
            bbox_dict=candidate.bbox.model_dump(),
            is_simulated=inference_res.is_simulated,
            model_name=inference_res.engine_name,
            model_version=inference_res.model_version
        )
        persisted_findings.append(record)

    return {
        "media_id": req.media_id,
        "frame_index": req.frame_index,
        "timestamp_ms": timestamp_ms,
        "engine_name": inference_res.engine_name,
        "model_version": inference_res.model_version,
        "is_simulated": inference_res.is_simulated,
        "findings_count": len(persisted_findings),
        "findings": persisted_findings
    }


@router.get("/sessions/{session_id}/findings")
async def list_session_findings(session_id: str):
    """List all findings and review states for an inspection session."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found."
        )
    return repo.list_findings(session_id)
