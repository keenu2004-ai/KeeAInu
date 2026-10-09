"""AI Inference, Roboflow SAM 3 Vision Integration and Findings API Router."""

import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
import cv2
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.security import is_path_safe, verify_and_resolve_media_file, calculate_sha256
from backend.app.db.repository import repo
from backend.app.modules.inference.registry import engine_registry
from backend.app.modules.inference.cache import inference_cache, should_sample_frame
from backend.app.modules.inference.roboflow_client import (
    RoboflowError,
    RoboflowAuthError,
    RoboflowTimeoutError,
    RoboflowApiError,
    RoboflowPrivacyError
)
from backend.app.modules.video.extractor import VideoFrameExtractor

router = APIRouter(prefix="/inference", tags=["Inference & Defect Analysis"])


class AnalyzeFrameRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    media_id: str = Field(..., min_length=1)
    frame_index: int = Field(0, ge=0)
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)
    engine: str = Field("mock", description="Inference engine: 'mock' or 'roboflow'")
    prompts: Optional[List[str]] = Field(None, description="Custom prompt labels for SAM 3 segmentation")
    allow_cloud_inference: Optional[bool] = Field(None, description="Explicit operator privacy consent for cloud inference")
    use_cache: bool = Field(True, description="Enable deterministic result caching")


@router.get("/engines", status_code=status.HTTP_200_OK)
async def list_available_engines():
    """List all registered vision inference engines and their runtime configuration."""
    return {
        "engines": engine_registry.list_engines(),
        "cloud_inference_globally_allowed": settings.ROBOFLOW_ALLOW_CLOUD_INFERENCE,
        "cache_enabled": settings.ROBOFLOW_CACHE_ENABLED
    }


@router.post("/analyze-frame", status_code=status.HTTP_200_OK)
async def analyze_frame(req: AnalyzeFrameRequest):
    """
    Run defect candidate analysis / segmentation on a selected media frame.
    Supports Roboflow SAM 3 vision engine and Mock baseline.
    Enforces privacy gating, evidence hashing, caching, provenance recording, and reviewer isolation.
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

    # Check payload size constraint
    if len(frame_bytes) > settings.ROBOFLOW_MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Frame size ({len(frame_bytes)} bytes) exceeds maximum limit of {settings.ROBOFLOW_MAX_IMAGE_SIZE_BYTES} bytes."
        )

    evidence_sha256 = calculate_sha256(frame_bytes)

    # Resolve target engine
    engine = engine_registry.get_engine(req.engine)
    if not engine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown inference engine '{req.engine}'. Available: {[e['engine_name'] for e in engine_registry.list_engines()]}"
        )

    # Deterministic Cache Lookup
    cache_key = inference_cache.generate_key(
        evidence_sha256=evidence_sha256,
        engine_name=engine.engine_name,
        model_version=engine.model_version,
        confidence_threshold=req.confidence_threshold,
        prompts=req.prompts
    )

    inference_res = None
    if req.use_cache and settings.ROBOFLOW_CACHE_ENABLED:
        inference_res = inference_cache.get(cache_key)

    if inference_res is None:
        try:
            if hasattr(engine, "infer_frame"):
                # Call engine with custom prompts and privacy override if supported
                if req.engine.lower() == "roboflow":
                    inference_res = await engine.infer_frame(
                        frame_bytes=frame_bytes,
                        frame_index=req.frame_index,
                        timestamp_ms=timestamp_ms,
                        confidence_threshold=req.confidence_threshold,
                        prompts=req.prompts,
                        allow_cloud_override=req.allow_cloud_inference
                    )
                else:
                    inference_res = await engine.infer_frame(
                        frame_bytes=frame_bytes,
                        frame_index=req.frame_index,
                        timestamp_ms=timestamp_ms,
                        confidence_threshold=req.confidence_threshold
                    )
        except RoboflowPrivacyError as pe:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
        except RoboflowAuthError as ae:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ae))
        except RoboflowTimeoutError as te:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(te))
        except RoboflowApiError as ape:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(ape))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Inference execution failed: {str(e)}")

        # Store in cache
        if req.use_cache and settings.ROBOFLOW_CACHE_ENABLED and inference_res:
            inference_cache.set(cache_key, inference_res)

    # Persist inference provenance record
    record_id = f"inf_{uuid.uuid4().hex[:12]}"
    repo.create_inference_record(
        record_id=record_id,
        session_id=req.session_id,
        media_id=req.media_id,
        frame_index=req.frame_index,
        timestamp_ms=timestamp_ms,
        evidence_sha256=evidence_sha256,
        engine_name=inference_res.engine_name,
        model_id=engine.engine_name,
        model_version=inference_res.model_version,
        is_simulated=inference_res.is_simulated,
        processing_duration_ms=inference_res.processing_duration_ms or 0.0,
        prompt_config_dict={"prompts": inference_res.prompts_used or []},
        cache_hit=inference_res.cache_hit,
        raw_response_dict=inference_res.raw_response,
        normalized_result_dict=inference_res.model_dump(exclude={"raw_response"})
    )

    # Persist findings with polygon masks and provenance links
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
            model_version=inference_res.model_version,
            polygon_mask=candidate.polygon_mask,
            evidence_sha256=evidence_sha256,
            inference_record_id=record_id
        )
        persisted_findings.append(record)

    return {
        "inference_record_id": record_id,
        "media_id": req.media_id,
        "frame_index": req.frame_index,
        "timestamp_ms": timestamp_ms,
        "engine_name": inference_res.engine_name,
        "model_version": inference_res.model_version,
        "is_simulated": inference_res.is_simulated,
        "evidence_sha256": evidence_sha256,
        "processing_duration_ms": inference_res.processing_duration_ms,
        "cache_hit": inference_res.cache_hit,
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


@router.get("/records", status_code=status.HTTP_200_OK)
async def list_inference_records(
    session_id: Optional[str] = Query(None),
    media_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """List inference execution and provenance records."""
    return repo.list_inference_records(session_id=session_id, media_id=media_id, skip=skip, limit=limit)


@router.get("/records/{record_id}", status_code=status.HTTP_200_OK)
async def get_inference_record(record_id: str):
    """Retrieve full inference record including raw response."""
    rec = repo.get_inference_record(record_id)
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inference record '{record_id}' not found."
        )
    return rec


@router.post("/cache/clear", status_code=status.HTTP_200_OK)
async def clear_inference_cache():
    """Clear in-memory inference cache."""
    inference_cache.clear()
    return {"message": "Inference cache cleared."}

