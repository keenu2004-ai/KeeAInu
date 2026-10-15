"""Unit tests for LocalOnnxInferenceEngine and Offline Inference Contracts."""

from pathlib import Path
import pytest
import numpy as np
import cv2

from backend.app.modules.inference.onnx_engine import (
    LocalOnnxInferenceEngine,
    LocalModelNotFoundError,
    LocalInferenceRuntimeError
)
from backend.app.modules.inference.registry import engine_registry


def test_onnx_engine_properties_and_registry():
    """Verifies that onnx_local is registered with is_simulated=False."""
    engine = engine_registry.get_engine("onnx_local")
    assert engine is not None
    assert engine.engine_name == "onnx_local"
    assert engine.model_version == "1.0.0-offline"
    assert engine.is_simulated is False  # Real detection engine, never simulated!
    assert engine.is_auth_configured() is True  # No SaaS / cloud API key needed!

    # Test alias resolution
    alias_engine = engine_registry.get_engine("local_onnx")
    assert alias_engine is engine


@pytest.mark.asyncio
async def test_missing_model_file_raises_actionable_error(tmp_path: Path):
    """When the local model file does not exist, infer_frame must raise LocalModelNotFoundError."""
    missing_path = tmp_path / "models" / "non_existent_detector.onnx"
    engine = LocalOnnxInferenceEngine(model_path=missing_path)

    assert engine.is_model_present() is False

    # Create dummy image bytes
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", dummy_img)
    frame_bytes = encoded.tobytes()

    with pytest.raises(LocalModelNotFoundError) as exc_info:
        await engine.infer_frame(
            frame_bytes=frame_bytes,
            frame_index=0,
            timestamp_ms=0.0
        )

    err_msg = str(exc_info.value)
    assert "Local defect detector model weights not found" in err_msg
    assert str(missing_path) in err_msg
    assert "/api/v1/evaluation/datasets/export" in err_msg


def test_preprocessing_letterbox_and_tensor_contract():
    """Verifies image letterboxing, aspect ratio retention, and NCHW normalization contract."""
    engine = LocalOnnxInferenceEngine(input_size=(640, 640))

    # Create a non-square test image: 300 height x 600 width
    test_img = np.full((300, 600, 3), 128, dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", test_img)
    frame_bytes = encoded.tobytes()

    tensor, meta = engine.preprocess(frame_bytes, target_size=(640, 640))

    # Assert shape is (1, 3, 640, 640)
    assert tensor.shape == (1, 3, 640, 640)
    assert tensor.dtype == np.float32

    # Assert normalized values [0.0, 1.0]
    assert np.min(tensor) >= 0.0
    assert np.max(tensor) <= 1.0

    # Assert metadata tracks letterboxing accurately
    assert meta["orig_w"] == 600
    assert meta["orig_h"] == 300
    assert meta["target_w"] == 640
    assert meta["target_h"] == 640
    # Scale: 640 / 600 = 1.0667
    assert pytest.approx(meta["scale"], 0.01) == 640 / 600
    # Vertical padding must be non-zero since original aspect ratio 2:1 is wider than 1:1
    assert meta["pad_h"] > 0
    assert meta["pad_w"] == 0


def test_postprocessing_box_unletterboxing_and_nms():
    """Verifies that postprocessing reverses letterbox padding, applies thresholding and NMS."""
    engine = LocalOnnxInferenceEngine(
        input_size=(640, 640),
        class_names=["CRACK", "CORROSION", "PITTING", "WEAR"]
    )

    meta = {
        "orig_w": 1280,
        "orig_h": 720,
        "target_w": 640,
        "target_h": 640,
        "scale": 0.5,  # 640 / 1280
        "pad_w": 0,
        "pad_h": 140   # (640 - 720*0.5) / 2 = 140
    }

    # Simulate detector raw output for 3 anchor boxes:
    # Box 1: high confidence CRACK at center
    # Box 2: overlapping duplicate box of Box 1 (should be suppressed by NMS)
    # Box 3: low confidence CORROSION (should be filtered out by confidence_threshold)
    num_anchors = 3
    num_classes = 4  # CRACK, CORROSION, PITTING, WEAR
    # Shape: (num_anchors, 4 + 4) = (3, 8)
    raw = np.zeros((num_anchors, 8), dtype=np.float32)

    # Box 1: cx=320, cy=320, w=100, h=80, CRACK score=0.92
    raw[0, :4] = [320.0, 320.0, 100.0, 80.0]
    raw[0, 4] = 0.92  # CRACK

    # Box 2: cx=322, cy=321, w=98, h=82, CRACK score=0.88 (overlapping Box 1)
    raw[1, :4] = [322.0, 321.0, 98.0, 82.0]
    raw[1, 4] = 0.88  # CRACK

    # Box 3: cx=100, cy=200, w=50, h=50, CORROSION score=0.25 (below threshold 0.5)
    raw[2, :4] = [100.0, 200.0, 50.0, 50.0]
    raw[2, 5] = 0.25  # CORROSION

    findings = engine.postprocess(
        raw,
        meta=meta,
        confidence_threshold=0.5,
        iou_threshold=0.45
    )

    # Box 2 suppressed by NMS; Box 3 filtered by threshold -> only 1 candidate remains!
    assert len(findings) == 1
    cand = findings[0]
    assert cand.defect_class == "CRACK"
    assert cand.confidence_score == 0.92

    # Check normalized coordinate bounds
    assert 0.0 <= cand.bbox.x_min < cand.bbox.x_max <= 1.0
    assert 0.0 <= cand.bbox.y_min < cand.bbox.y_max <= 1.0
