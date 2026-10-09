"""Comprehensive Evidence Integrity, Tampering Detection, and Format Validation Suite (Phase 3.2)."""

import io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.modules.ingestion.validator import validate_media_file


def _create_minimal_image_bytes(format_name: str, ext: str) -> bytes:
    """Generate genuine minimal valid image bytes using Pillow."""
    img = Image.new("RGB", (32, 32), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def _create_minimal_video_bytes(ext: str) -> bytes:
    """Generate genuine minimal valid video bytes using OpenCV."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        fourcc = cv2.VideoWriter_fourcc(*"MJPG") if ext == ".avi" else cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(tmp_path), fourcc, 10.0, (64, 64))
        for _ in range(5):
            writer.write(np.zeros((64, 64, 3), dtype=np.uint8))
        writer.release()
        return tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.mark.asyncio
async def test_all_supported_image_formats_ingest_and_validate():
    """Verify that all advertised image formats (.png, .jpg, .jpeg, .bmp, .webp) upload and validate."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Image Formats Session", "inspector_name": "Auditor"})
        session_id = s_res.json()["id"]

        formats = [
            ("PNG", "test.png", "image/png"),
            ("JPEG", "test.jpg", "image/jpeg"),
            ("JPEG", "test.jpeg", "image/jpeg"),
            ("BMP", "test.bmp", "image/bmp"),
            ("WEBP", "test.webp", "image/webp"),
        ]

        for fmt_name, filename, mime in formats:
            img_bytes = _create_minimal_image_bytes(fmt_name, filename)
            files = {"file": (filename, img_bytes, mime)}
            res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
            assert res.status_code == 201, f"Failed to upload {filename}: {res.text}"
            media_data = res.json()
            assert media_data["width"] == 32
            assert media_data["height"] == 32
            assert media_data["is_readable"] is True

            # Verify content retrieval and frame 0 retrieval
            content_res = await client.get(f"/api/v1/media/{media_data['id']}/content")
            assert content_res.status_code == 200

            frame_res = await client.get(f"/api/v1/media/{media_data['id']}/frames/0")
            assert frame_res.status_code == 200


@pytest.mark.asyncio
async def test_all_supported_video_formats_ingest_and_validate():
    """Verify that advertised video formats (.mp4, .avi) upload, validate metadata, and extract frames."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Video Formats Session", "inspector_name": "Auditor"})
        session_id = s_res.json()["id"]

        formats = [
            (".mp4", "test_feed.mp4", "video/mp4"),
            (".avi", "test_feed.avi", "video/avi"),
        ]

        for ext, filename, mime in formats:
            vid_bytes = _create_minimal_video_bytes(ext)
            files = {"file": (filename, vid_bytes, mime)}
            res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
            assert res.status_code == 201, f"Failed to upload {filename}: {res.text}"
            media_data = res.json()
            assert media_data["width"] == 64
            assert media_data["height"] == 64
            assert media_data["is_readable"] is True
            assert media_data["total_frames"] >= 1

            # Verify content retrieval and frame extraction
            content_res = await client.get(f"/api/v1/media/{media_data['id']}/content")
            assert content_res.status_code == 200

            frame_res = await client.get(f"/api/v1/media/{media_data['id']}/frames/0")
            assert frame_res.status_code == 200



@pytest.mark.asyncio
async def test_tampered_image_rejected_at_all_consumption_points():
    """
    If an image file is altered on disk after upload:
    - GET /content MUST return 409
    - GET /frames/0 MUST return 409
    - POST /inference/analyze-frame MUST return 409
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Tamper Test", "inspector_name": "Integrity Gate"})
        session_id = s_res.json()["id"]

        img_bytes = _create_minimal_image_bytes("PNG", "test.png")
        files = {"file": ("test.png", img_bytes, "image/png")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        assert up_res.status_code == 201
        media = up_res.json()
        media_id = media["id"]
        stored_path = Path(media["file_path"])

        # 1. Verify all 3 consumption points work before tampering
        res_content = await client.get(f"/api/v1/media/{media_id}/content")
        assert res_content.status_code == 200

        res_frame = await client.get(f"/api/v1/media/{media_id}/frames/0")
        assert res_frame.status_code == 200

        res_inf = await client.post(
            "/api/v1/inference/analyze-frame",
            json={"session_id": session_id, "media_id": media_id, "frame_index": 0, "confidence_threshold": 0.5}
        )
        assert res_inf.status_code == 200

        # 2. Tamper with the image file on disk
        original_bytes = stored_path.read_bytes()
        try:
            stored_path.write_bytes(original_bytes + b"_tampered_data")

            # GET /content -> 409
            tampered_content = await client.get(f"/api/v1/media/{media_id}/content")
            assert tampered_content.status_code == 409
            assert "evidence integrity failure" in tampered_content.json()["detail"].lower()

            # GET /frames/0 -> 409
            tampered_frame = await client.get(f"/api/v1/media/{media_id}/frames/0")
            assert tampered_frame.status_code == 409
            assert "evidence integrity failure" in tampered_frame.json()["detail"].lower()

            # POST /inference/analyze-frame -> 409
            tampered_inf = await client.post(
                "/api/v1/inference/analyze-frame",
                json={"session_id": session_id, "media_id": media_id, "frame_index": 0, "confidence_threshold": 0.5}
            )
            assert tampered_inf.status_code == 409
            assert "evidence integrity failure" in tampered_inf.json()["detail"].lower()

        finally:
            stored_path.write_bytes(original_bytes)


@pytest.mark.asyncio
async def test_tampered_video_rejected_at_all_consumption_points():
    """
    If a video file is altered on disk after upload:
    - GET /content MUST return 409
    - GET /frames/{idx} MUST return 409
    - POST /inference/analyze-frame MUST return 409
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Video Tamper Test", "inspector_name": "Integrity Gate"})
        session_id = s_res.json()["id"]

        video_path = settings.DATA_DIR / "sample_fixtures" / "synthetic_test_video.mp4"
        files = {"file": ("inspection_feed.mp4", video_path.read_bytes(), "video/mp4")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        assert up_res.status_code == 201
        media = up_res.json()
        media_id = media["id"]
        stored_path = Path(media["file_path"])

        # 1. Verify normal access before tampering
        res_content = await client.get(f"/api/v1/media/{media_id}/content")
        assert res_content.status_code == 200

        res_frame = await client.get(f"/api/v1/media/{media_id}/frames/1")
        assert res_frame.status_code == 200

        res_inf = await client.post(
            "/api/v1/inference/analyze-frame",
            json={"session_id": session_id, "media_id": media_id, "frame_index": 1, "confidence_threshold": 0.5}
        )
        assert res_inf.status_code == 200

        # 2. Tamper with the video file on disk
        original_bytes = stored_path.read_bytes()
        try:
            # Modify a non-fatal bit inside the video container
            tampered_bytes = bytearray(original_bytes)
            tampered_bytes[-10] ^= 0xFF
            stored_path.write_bytes(bytes(tampered_bytes))

            # GET /content -> 409
            tampered_content = await client.get(f"/api/v1/media/{media_id}/content")
            assert tampered_content.status_code == 409
            assert "evidence integrity failure" in tampered_content.json()["detail"].lower()

            # GET /frames/1 -> 409
            tampered_frame = await client.get(f"/api/v1/media/{media_id}/frames/1")
            assert tampered_frame.status_code == 409
            assert "evidence integrity failure" in tampered_frame.json()["detail"].lower()

            # POST /inference/analyze-frame -> 409
            tampered_inf = await client.post(
                "/api/v1/inference/analyze-frame",
                json={"session_id": session_id, "media_id": media_id, "frame_index": 1, "confidence_threshold": 0.5}
            )
            assert tampered_inf.status_code == 409
            assert "evidence integrity failure" in tampered_inf.json()["detail"].lower()

        finally:
            stored_path.write_bytes(original_bytes)


@pytest.mark.asyncio
async def test_missing_media_file_rejected_at_all_consumption_points():
    """
    If a media file is missing from the vault on disk:
    - GET /content -> 404
    - GET /frames/0 -> 404
    - POST /inference/analyze-frame -> 404
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Missing File Test", "inspector_name": "Auditor"})
        session_id = s_res.json()["id"]

        img_bytes = _create_minimal_image_bytes("PNG", "temp.png")
        files = {"file": ("temp.png", img_bytes, "image/png")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        media = up_res.json()
        media_id = media["id"]
        stored_path = Path(media["file_path"])

        # Temporarily delete stored file
        original_bytes = stored_path.read_bytes()
        stored_path.unlink()

        try:
            res_content = await client.get(f"/api/v1/media/{media_id}/content")
            assert res_content.status_code == 404

            res_frame = await client.get(f"/api/v1/media/{media_id}/frames/0")
            assert res_frame.status_code == 404

            res_inf = await client.post(
                "/api/v1/inference/analyze-frame",
                json={"session_id": session_id, "media_id": media_id, "frame_index": 0, "confidence_threshold": 0.5}
            )
            assert res_inf.status_code == 404

        finally:
            stored_path.write_bytes(original_bytes)


@pytest.mark.asyncio
async def test_reject_malformed_image_and_video_containers():
    """Ensure that malformed files passing superficial header checks are rejected during upload validation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Decoder Rejection Test", "inspector_name": "Tester"})
        session_id = s_res.json()["id"]

        # Malformed PNG: Valid magic header followed by garbage
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 30
        res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files={"file": ("fake.png", fake_png, "image/png")})
        assert res.status_code == 400
        assert "decoding failed" in res.json()["detail"].lower()

        # Malformed BMP: 'BM' header followed by garbage
        fake_bmp = b"BM" + b"\x00" * 20
        res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files={"file": ("fake.bmp", fake_bmp, "image/bmp")})
        assert res.status_code == 400
        assert "decoding failed" in res.json()["detail"].lower()

        # Malformed WebP: 'RIFF....WEBP' header followed by garbage
        fake_webp = b"RIFF\x20\x00\x00\x00WEBP" + b"\x00" * 20
        res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files={"file": ("fake.webp", fake_webp, "image/webp")})
        assert res.status_code == 400
        assert "decoding failed" in res.json()["detail"].lower()

        # Malformed MP4: '....ftyp' header followed by zero bytes
        fake_mp4 = b"\x00\x00\x00\x20ftypmp42" + b"\x00" * 50
        res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files={"file": ("fake.mp4", fake_mp4, "video/mp4")})
        assert res.status_code == 400
        assert "inspection failed" in res.json()["detail"].lower()
