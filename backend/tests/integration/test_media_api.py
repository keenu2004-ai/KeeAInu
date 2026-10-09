"""Integration tests for Media Upload, Streaming, and Frame Access."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.core.config import settings
from backend.app.main import app


@pytest.fixture(scope="module")
def sample_media_fixtures():
    fixtures_dir = settings.DATA_DIR / "sample_fixtures"
    grid_path = fixtures_dir / "synthetic_still_grid.png"
    video_path = fixtures_dir / "synthetic_test_video.mp4"
    assert grid_path.exists(), "Sample still fixture must exist"
    assert video_path.exists(), "Sample video fixture must exist"
    return {"grid": grid_path, "video": video_path}


@pytest.mark.asyncio
async def test_upload_and_inspect_image(sample_media_fixtures):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session first
        s_res = await client.post("/api/v1/sessions", json={"title": "Image Test", "inspector_name": "Tester"})
        session_id = s_res.json()["id"]

        # Upload image
        image_bytes = sample_media_fixtures["grid"].read_bytes()
        files = {"file": ("probe_grid.png", image_bytes, "image/png")}
        data = {"session_id": session_id}

        up_res = await client.post("/api/v1/media/upload", data=data, files=files)
        assert up_res.status_code == 201
        media = up_res.json()
        assert media["session_id"] == session_id
        assert media["width"] == 320
        assert media["height"] == 240
        assert media["is_readable"] is True
        assert len(media["sha256_hash"]) == 64
        media_id = media["id"]

        # Fetch metadata
        meta_res = await client.get(f"/api/v1/media/{media_id}")
        assert meta_res.status_code == 200
        assert meta_res.json()["id"] == media_id

        # Fetch content
        content_res = await client.get(f"/api/v1/media/{media_id}/content")
        assert content_res.status_code == 200
        assert content_res.headers["content-type"] == "image/png"
        assert len(content_res.content) == len(image_bytes)

        # Frame extraction on image frame 0
        frame_res = await client.get(f"/api/v1/media/{media_id}/frames/0")
        assert frame_res.status_code == 200


@pytest.mark.asyncio
async def test_upload_and_process_video(sample_media_fixtures):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        s_res = await client.post("/api/v1/sessions", json={"title": "Video Test", "inspector_name": "Tester"})
        session_id = s_res.json()["id"]

        # Upload video
        video_bytes = sample_media_fixtures["video"].read_bytes()
        files = {"file": ("inspection_feed.mp4", video_bytes, "video/mp4")}
        data = {"session_id": session_id}

        up_res = await client.post("/api/v1/media/upload", data=data, files=files)
        assert up_res.status_code == 201
        media = up_res.json()
        assert media["total_frames"] == 30
        assert media["fps"] == 30.0
        assert media["width"] == 320
        assert media["height"] == 240
        assert media["is_readable"] is True
        media_id = media["id"]

        # Check thumbnails
        thumbs_res = await client.get(f"/api/v1/media/{media_id}/thumbnails")
        assert thumbs_res.status_code == 200
        thumbs = thumbs_res.json()
        assert len(thumbs) > 0

        # Fetch first thumbnail image content
        first_thumb_id = thumbs[0]["id"]
        t_content_res = await client.get(f"/api/v1/media/{media_id}/thumbnails/{first_thumb_id}/content")
        assert t_content_res.status_code == 200
        assert t_content_res.headers["content-type"] == "image/jpeg"

        # Frame extraction on specific frame index
        frame_res = await client.get(f"/api/v1/media/{media_id}/frames/15")
        assert frame_res.status_code == 200
        assert frame_res.headers["content-type"] == "image/jpeg"
        assert frame_res.headers["x-frame-index"] == "15"
        assert frame_res.headers["x-timestamp-ms"] == "500.0"

        # Out of bounds frame extraction
        bad_frame_res = await client.get(f"/api/v1/media/{media_id}/frames/999")
        assert bad_frame_res.status_code == 400


@pytest.mark.asyncio
async def test_upload_rejection_invalid_extension():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        s_res = await client.post("/api/v1/sessions", json={"title": "Reject Test", "inspector_name": "Tester"})
        session_id = s_res.json()["id"]

        files = {"file": ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-dosexec")}
        res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        assert res.status_code == 400
        assert "unsupported file extension" in res.json()["detail"].lower()
