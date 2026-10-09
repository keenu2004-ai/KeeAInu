"""Unit tests for Roboflow SAM 3 Vision Integration Adapter, Privacy Gate & Cache."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.modules.inference.roboflow_client import (
    RoboflowInferenceEngine,
    RoboflowAuthError,
    RoboflowTimeoutError,
    RoboflowApiError,
    RoboflowPrivacyError
)
from backend.app.modules.inference.cache import (
    InferenceCache,
    should_sample_frame
)
from backend.app.modules.inference.base import FrameInferenceResult, FindingCandidate, BoundingBox


SAMPLE_ROBOFLOW_RESPONSE = {
    "time": 0.12,
    "image": {"width": 1280, "height": 720},
    "predictions": [
        {
            "x": 640.0,
            "y": 360.0,
            "width": 200.0,
            "height": 100.0,
            "confidence": 0.88,
            "class": "crack",
            "class_id": 1,
            "detection_id": "det_01",
            "points": [
                {"x": 540.0, "y": 310.0},
                {"x": 740.0, "y": 310.0},
                {"x": 740.0, "y": 410.0},
                {"x": 540.0, "y": 410.0}
            ]
        }
    ]
}


def test_roboflow_privacy_gate():
    """Verify that cloud inference fails closed when privacy consent is not granted."""
    engine = RoboflowInferenceEngine(
        api_key="rf_test_key_12345",
        allow_cloud_inference=False
    )
    with pytest.raises(RoboflowPrivacyError) as exc_info:
        import asyncio
        asyncio.run(engine.infer_frame(
            frame_bytes=b"fake_frame_bytes",
            frame_index=0,
            timestamp_ms=0.0
        ))
    assert "Privacy Gate Restriction" in str(exc_info.value)


def test_roboflow_auth_missing_key():
    """Verify that missing API key raises RoboflowAuthError before making network calls."""
    engine = RoboflowInferenceEngine(
        api_key="",
        allow_cloud_inference=True
    )
    with pytest.raises(RoboflowAuthError) as exc_info:
        import asyncio
        asyncio.run(engine.infer_frame(
            frame_bytes=b"fake_frame_bytes",
            frame_index=0,
            timestamp_ms=0.0
        ))
    assert "API key is not configured" in str(exc_info.value)


def test_roboflow_parse_response_with_polygons():
    """Verify normalization of center coordinates and polygon points from real response schema."""
    engine = RoboflowInferenceEngine(
        api_key="rf_test_key_12345",
        allow_cloud_inference=True
    )

    res = engine.parse_roboflow_response(
        raw_data=SAMPLE_ROBOFLOW_RESPONSE,
        frame_index=5,
        timestamp_ms=166.7,
        evidence_hash="sha256:abc123test",
        duration_ms=120.0,
        confidence_threshold=0.50,
        prompts_used=["crack", "pitting"]
    )

    assert res.is_simulated is False
    assert res.engine_name == "roboflow"
    assert res.processing_duration_ms == 120.0
    assert res.evidence_sha256 == "sha256:abc123test"
    assert len(res.findings) == 1

    finding = res.findings[0]
    assert finding.defect_class == "crack"
    assert finding.confidence_score == 0.88

    # Normalized BBox: center (640, 360), size (200, 100) on 1280x720 image
    # x_min = (640 - 100) / 1280 = 540 / 1280 = 0.421875 -> 0.4219
    # x_max = (640 + 100) / 1280 = 740 / 1280 = 0.578125 -> 0.5781
    # y_min = (360 - 50) / 720 = 310 / 720 = 0.43055... -> 0.4306
    # y_max = (360 + 50) / 720 = 410 / 720 = 0.56944... -> 0.5694
    assert round(finding.bbox.x_min, 2) == 0.42
    assert round(finding.bbox.x_max, 2) == 0.58
    assert round(finding.bbox.y_min, 2) == 0.43
    assert round(finding.bbox.y_max, 2) == 0.57

    # Normalized Polygon mask
    assert finding.polygon_mask is not None
    assert len(finding.polygon_mask) == 4
    assert finding.polygon_mask[0] == [0.4219, 0.4306]


@pytest.mark.asyncio
async def test_roboflow_timeout_handling():
    """Verify that network timeouts raise RoboflowTimeoutError and do not fabricate predictions."""
    engine = RoboflowInferenceEngine(
        api_key="rf_test_key_12345",
        allow_cloud_inference=True,
        timeout_seconds=0.01
    )

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Network timeout")):
        with pytest.raises(RoboflowTimeoutError) as exc_info:
            await engine.infer_frame(
                frame_bytes=b"sample_frame_bytes",
                frame_index=0,
                timestamp_ms=0.0
            )
        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_roboflow_api_error_handling():
    """Verify HTTP 500/502 errors raise RoboflowApiError without generating synthetic findings."""
    engine = RoboflowInferenceEngine(
        api_key="rf_test_key_12345",
        allow_cloud_inference=True
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(RoboflowApiError) as exc_info:
            await engine.infer_frame(
                frame_bytes=b"sample_frame_bytes",
                frame_index=0,
                timestamp_ms=0.0
            )
        assert "502" in str(exc_info.value)


def test_inference_cache_determinism():
    """Verify cache keys incorporate all parameters and prevent prompt cross-contamination."""
    cache = InferenceCache()

    key1 = cache.generate_key(
        evidence_sha256="hash_001",
        engine_name="roboflow",
        model_version="videoscope-sam3/1",
        confidence_threshold=0.5,
        prompts=["crack", "pitting"]
    )

    key2 = cache.generate_key(
        evidence_sha256="hash_001",
        engine_name="roboflow",
        model_version="videoscope-sam3/1",
        confidence_threshold=0.5,
        prompts=["crack", "pitting"]
    )

    # Different prompt must produce different key
    key_diff_prompt = cache.generate_key(
        evidence_sha256="hash_001",
        engine_name="roboflow",
        model_version="videoscope-sam3/1",
        confidence_threshold=0.5,
        prompts=["corrosion"]
    )

    assert key1 == key2
    assert key1 != key_diff_prompt

    result = FrameInferenceResult(
        frame_index=0,
        timestamp_ms=0.0,
        engine_name="roboflow",
        model_version="videoscope-sam3/1",
        is_simulated=False,
        findings=[]
    )

    cache.set(key1, result)
    cached = cache.get(key1)
    assert cached is not None
    assert cached.cache_hit is True
    assert cache.get(key_diff_prompt) is None


def test_frame_sampling_utility():
    """Verify frame sampling skips intermediate video frames when appropriate."""
    # First frame always sampled
    assert should_sample_frame(frame_index=0, total_frames=100, sample_rate=5) is True
    # Frame 1 skipped (not keyframe, sample_rate=5)
    assert should_sample_frame(frame_index=1, total_frames=100, sample_rate=5) is False
    # Frame 5 sampled
    assert should_sample_frame(frame_index=5, total_frames=100, sample_rate=5) is True
    # Explicit keyframe sampled
    assert should_sample_frame(frame_index=3, total_frames=100, sample_rate=5, is_keyframe=True) is True
