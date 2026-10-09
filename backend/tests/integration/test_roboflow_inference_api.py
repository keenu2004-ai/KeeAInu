"""Integration tests for Roboflow SAM 3 Inference API, Caching, Provenance, and Privacy Gate."""

import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.db.repository import repo
from backend.app.core.config import settings

client = TestClient(app)


@pytest.fixture
def test_session_and_image(tmp_path):
    """Setup a valid session with an attached still image."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    session = repo.create_session(f"sess_rf_test_{uid}", "Roboflow Integration Test Session", "Lead Inspector")

    # Create dummy image in raw media dir
    img = Image.new("RGB", (320, 240), color=(73, 109, 137))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    file_path = settings.RAW_MEDIA_DIR / f"rf_test_sample_{uid}.png"
    file_path.write_bytes(img_bytes)

    import hashlib
    sha256_hash = hashlib.sha256(img_bytes).hexdigest()

    media = repo.create_media(
        media_id=f"med_rf_test_{uid}",
        session_id=session["id"],
        filename=f"rf_test_sample_{uid}.png",
        file_path=str(file_path),
        media_type="image/png",
        sha256_hash=sha256_hash,
        width=320,
        height=240,
        duration_seconds=0.0,
        fps=0.0,
        total_frames=1,
        is_readable=True
    )

    yield session, media


def test_list_inference_engines():
    """Verify registered vision engines and global privacy settings."""
    resp = client.get("/api/v1/inference/engines")
    assert resp.status_code == 200
    data = resp.json()
    assert "engines" in data
    engine_names = [e["engine_name"] for e in data["engines"]]
    assert "mock" in engine_names
    assert "roboflow" in engine_names


def test_analyze_frame_privacy_gate_blocking(test_session_and_image):
    """Verify privacy gate blocks cloud inference when allow_cloud_inference=False."""
    session, media = test_session_and_image

    resp = client.post(
        "/api/v1/inference/analyze-frame",
        json={
            "session_id": session["id"],
            "media_id": media["id"],
            "frame_index": 0,
            "confidence_threshold": 0.5,
            "engine": "roboflow",
            "allow_cloud_inference": False
        }
    )
    assert resp.status_code == 403
    assert "Privacy Gate Restriction" in resp.json()["detail"]


def test_analyze_frame_roboflow_end_to_end(test_session_and_image):
    """Verify full Roboflow inference lifecycle: request, parsing, polygon persistence, and caching."""
    session, media = test_session_and_image

    mock_rf_response = {
        "time": 0.08,
        "image": {"width": 320, "height": 240},
        "predictions": [
            {
                "x": 160.0,
                "y": 120.0,
                "width": 80.0,
                "height": 60.0,
                "confidence": 0.94,
                "class": "crack",
                "points": [
                    {"x": 120.0, "y": 90.0},
                    {"x": 200.0, "y": 90.0},
                    {"x": 200.0, "y": 150.0},
                    {"x": 120.0, "y": 150.0}
                ]
            }
        ]
    }

    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json = MagicMock(return_value=mock_rf_response)

    with patch("httpx.AsyncClient.post", return_value=mock_http_resp):
        with patch.object(settings, "ROBOFLOW_API_KEY", "rf_valid_test_key"):
            # First execution -> Cache miss, calls client
            resp = client.post(
                "/api/v1/inference/analyze-frame",
                json={
                    "session_id": session["id"],
                    "media_id": media["id"],
                    "frame_index": 0,
                    "confidence_threshold": 0.5,
                    "engine": "roboflow",
                    "allow_cloud_inference": True,
                    "use_cache": True
                }
            )

            assert resp.status_code == 200
            data = resp.json()
            assert data["engine_name"] == "roboflow"
            assert data["is_simulated"] is False
            assert data["cache_hit"] is False
            assert len(data["findings"]) == 1

            finding = data["findings"][0]
            assert finding["defect_class"] == "crack"
            assert finding["polygon_mask"] is not None
            assert len(finding["polygon_mask"]) == 4
            assert finding["evidence_sha256"] == data["evidence_sha256"]

            # Second execution with identical payload -> Cache hit
            resp2 = client.post(
                "/api/v1/inference/analyze-frame",
                json={
                    "session_id": session["id"],
                    "media_id": media["id"],
                    "frame_index": 0,
                    "confidence_threshold": 0.5,
                    "engine": "roboflow",
                    "allow_cloud_inference": True,
                    "use_cache": True
                }
            )

            assert resp2.status_code == 200
            data2 = resp2.json()
            assert data2["cache_hit"] is True

            # Verify inference records endpoint
            rec_resp = client.get(f"/api/v1/inference/records/{data['inference_record_id']}")
            assert rec_resp.status_code == 200
            rec = rec_resp.json()
            assert rec["id"] == data["inference_record_id"]
            assert rec["engine_name"] == "roboflow"
            assert rec["evidence_sha256"] == data["evidence_sha256"]
