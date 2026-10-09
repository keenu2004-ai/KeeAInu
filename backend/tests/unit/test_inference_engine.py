"""Unit tests for pluggable AI inference engine and mock detector."""

import pytest
from backend.app.modules.inference.mock_engine import MockInferenceEngine


@pytest.mark.asyncio
async def test_mock_inference_engine_contract():
    engine = MockInferenceEngine()
    
    # Engine metadata checks
    assert engine.engine_name == "DeterministicMockEngine"
    assert engine.model_version == "v1.0.0-mock"
    assert engine.is_simulated is True  # Non-negotiable requirement: simulated results marked clearly
    
    # Even frame index -> 0 findings
    even_res = await engine.infer_frame(
        frame_bytes=b"dummy_frame_bytes",
        frame_index=0,
        timestamp_ms=0.0,
        confidence_threshold=0.5
    )
    assert even_res.frame_index == 0
    assert len(even_res.findings) == 0
    assert even_res.is_simulated is True
    
    # Odd frame index -> 1 candidate finding (CRACK)
    odd_res = await engine.infer_frame(
        frame_bytes=b"dummy_frame_bytes",
        frame_index=1,
        timestamp_ms=33.33,
        confidence_threshold=0.5
    )
    assert odd_res.frame_index == 1
    assert len(odd_res.findings) == 1
    finding = odd_res.findings[0]
    assert finding.defect_class == "CRACK"
    assert finding.confidence_score == 0.88
    assert finding.bbox.x_min == 0.25
    assert finding.bbox.x_max == 0.65
    assert finding.metadata.get("synthetic_flag") is True
