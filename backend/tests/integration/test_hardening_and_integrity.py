"""Hardening and Evidence Integrity Regression Tests for Phase 3.1."""

from pathlib import Path
import tempfile
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.modules.ingestion.validator import validate_media_file


def test_strict_magic_signature_validation():
    # Valid signatures
    assert validate_media_file("video.mp4", b"\x00\x00\x00\x20ftypmp42", 100)[0] is True
    assert validate_media_file("video.avi", b"RIFF\x00\x00\x00\x00AVI LIST", 100)[0] is True
    assert validate_media_file("image.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ", 100)[0] is True
    assert validate_media_file("image.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00", 100)[0] is True
    assert validate_media_file("image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\r", 100)[0] is True
    assert validate_media_file("image.bmp", b"BM\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 100)[0] is True
    assert validate_media_file("video.mkv", b"\x1A\x45\xDF\xA3\x93\x42\x86\x81\x01\x42\xF7\x81\x01", 100)[0] is True

    # Invalid signatures
    assert validate_media_file("video.mp4", b"not_a_valid_mp4_header", 100)[0] is False
    assert validate_media_file("video.avi", b"RIFF\x00\x00\x00\x00NOTAVI ", 100)[0] is False
    assert validate_media_file("image.webp", b"RIFF\x00\x00\x00\x00NOTWEBP", 100)[0] is False
    assert validate_media_file("image.jpg", b"\x00\x00\x00\x00JFIF\x00\x01\x01", 100)[0] is False
    assert validate_media_file("image.png", b"GIF89a\x00\x00\x00\x00\x00\x00", 100)[0] is False
    assert validate_media_file("video.mkv", b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00", 100)[0] is False


@pytest.mark.asyncio
async def test_evidence_integrity_hash_mismatch_detection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session and upload image
        s_res = await client.post("/api/v1/sessions", json={"title": "Hash Integrity Test", "inspector_name": "Auditor"})
        session_id = s_res.json()["id"]

        image_path = Path("data/sample_fixtures/synthetic_still_grid.png")
        files = {"file": ("probe_grid.png", image_path.read_bytes(), "image/png")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        assert up_res.status_code == 201
        media = up_res.json()
        media_id = media["id"]
        stored_path = Path(media["file_path"])

        # 1. Normal access: hash matches -> 200 OK
        ok_res = await client.get(f"/api/v1/media/{media_id}/content")
        assert ok_res.status_code == 200

        # 2. Simulate evidence tampering on disk
        original_bytes = stored_path.read_bytes()
        try:
            tampered_bytes = original_bytes + b"tampered_bit"
            stored_path.write_bytes(tampered_bytes)

            # Requesting tampered media MUST trigger 409 Conflict integrity failure
            tampered_res = await client.get(f"/api/v1/media/{media_id}/content")
            assert tampered_res.status_code == 409
            assert "integrity failure" in tampered_res.json()["detail"].lower()
        finally:
            # Restore original bytes
            stored_path.write_bytes(original_bytes)


@pytest.mark.asyncio
async def test_cross_session_inference_rejection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Session A & upload video
        s_res_a = await client.post("/api/v1/sessions", json={"title": "Session A", "inspector_name": "Tester A"})
        session_a_id = s_res_a.json()["id"]

        video_path = Path("data/sample_fixtures/synthetic_test_video.mp4")
        files = {"file": ("feed_a.mp4", video_path.read_bytes(), "video/mp4")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_a_id}, files=files)
        media_a_id = up_res.json()["id"]

        # Create Session B
        s_res_b = await client.post("/api/v1/sessions", json={"title": "Session B", "inspector_name": "Tester B"})
        session_b_id = s_res_b.json()["id"]

        # Attempt to run inference on Media A using Session B ID -> MUST fail with 400 Bad Request
        bad_inf_res = await client.post(
            "/api/v1/inference/analyze-frame",
            json={
                "session_id": session_b_id,
                "media_id": media_a_id,
                "frame_index": 0,
                "confidence_threshold": 0.5
            }
        )
        assert bad_inf_res.status_code == 400
        assert "does not belong to session" in bad_inf_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_atomic_cleanup_on_corrupted_container():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Cleanup Test", "inspector_name": "Tester"})
        session_id = s_res.json()["id"]

        # Valid JPEG magic bytes but completely truncated/corrupt payload
        corrupt_jpeg = b"\xFF\xD8\xFF\xE0" + b"\x00" * 20
        files = {"file": ("corrupt.jpg", corrupt_jpeg, "image/jpeg")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        assert up_res.status_code == 400
        assert "decoding failed" in up_res.json()["detail"].lower()
