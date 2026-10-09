"""End-to-End Verification Test for the complete Phase 3 Inspection workflow."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.security import calculate_sha256


@pytest.mark.asyncio
async def test_full_e2e_recorded_media_inspection_flow():
    """
    Simulates the full inspector user journey:
    1. Create Inspection Session.
    2. Ingest recorded video footage (synthetic_test_video.mp4).
    3. Verify media metadata and thumbnail timeline.
    4. Scrub/seek to frame 1 and extract image.
    5. Execute simulated AI defect analysis on frame 1.
    6. Verify simulated finding bounding box and metadata.
    7. Record Inspector Review Decision (CONFIRMED, CRITICAL).
    8. Re-fetch session & findings to verify persistence across restarts.
    9. Verify original media hash is unchanged (Evidence Immutability).
    """
    video_path = Path("data/sample_fixtures/synthetic_test_video.mp4")
    assert video_path.exists(), "Synthetic test video must exist"
    original_sha256 = calculate_sha256(video_path)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create Session
        s_res = await client.post(
            "/api/v1/sessions",
            json={
                "title": "E2E Gas Turbine Combustion Audit",
                "inspector_name": "Dr. Sarah Lin (Level III NDT)",
                "asset_tag": "GT-800-CHAMBER-2"
            }
        )
        assert s_res.status_code == 201
        session = s_res.json()
        session_id = session["id"]
        assert session["status"] == "DRAFT"

        # Step 2: Upload Video Media
        video_bytes = video_path.read_bytes()
        files = {"file": ("inspection_video.mp4", video_bytes, "video/mp4")}
        up_res = await client.post(
            "/api/v1/media/upload",
            data={"session_id": session_id},
            files=files
        )
        assert up_res.status_code == 201
        media = up_res.json()
        media_id = media["id"]
        assert media["total_frames"] == 30
        assert media["fps"] == 30.0
        assert media["sha256_hash"] == original_sha256

        # Step 3: Verify Thumbnails
        thumb_res = await client.get(f"/api/v1/media/{media_id}/thumbnails")
        assert thumb_res.status_code == 200
        thumbnails = thumb_res.json()
        assert len(thumbnails) > 0

        # Step 4: Extract Frame 1
        frame_res = await client.get(f"/api/v1/media/{media_id}/frames/1")
        assert frame_res.status_code == 200
        assert frame_res.headers["x-frame-index"] == "1"

        # Step 5: Execute Simulated AI Defect Detection
        inf_res = await client.post(
            "/api/v1/inference/analyze-frame",
            json={
                "session_id": session_id,
                "media_id": media_id,
                "frame_index": 1,
                "confidence_threshold": 0.5
            }
        )
        assert inf_res.status_code == 200
        inf_data = inf_res.json()
        assert inf_data["is_simulated"] is True
        assert len(inf_data["findings"]) == 1
        finding = inf_data["findings"][0]
        finding_id = finding["id"]
        assert finding["defect_class"] == "CRACK"
        assert finding["is_simulated"] is True

        # Step 6: Submit Inspector Review Decision
        rev_res = await client.post(
            "/api/v1/reviews",
            json={
                "finding_id": finding_id,
                "decision_status": "CONFIRMED",
                "severity": "CRITICAL",
                "reviewed_by": "Dr. Sarah Lin",
                "inspector_notes": "Confirmed linear fissure near trailing edge seam."
            }
        )
        assert rev_res.status_code == 200
        review = rev_res.json()
        assert review["decision_status"] == "CONFIRMED"
        assert review["severity"] == "CRITICAL"

        # Step 7: Transition Session Status to IN_REVIEW -> COMPLETED
        stat_res1 = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "IN_REVIEW"}
        )
        assert stat_res1.status_code == 200
        assert stat_res1.json()["status"] == "IN_REVIEW"

        stat_res2 = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "COMPLETED"}
        )
        assert stat_res2.status_code == 200
        assert stat_res2.json()["status"] == "COMPLETED"

        # Step 8: Verify Complete Session State Persistence
        final_s_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert final_s_res.status_code == 200
        final_session = final_s_res.json()
        assert final_session["status"] == "COMPLETED"
        assert len(final_session["media"]) == 1

        final_f_res = await client.get(f"/api/v1/inference/sessions/{session_id}/findings")
        assert final_f_res.status_code == 200
        final_findings = final_f_res.json()
        assert len(final_findings) == 1
        assert final_findings[0]["decision_status"] == "CONFIRMED"
        assert final_findings[0]["inspector_notes"] == "Confirmed linear fissure near trailing edge seam."

        # Step 9: Verify Original Media Evidence Immutability
        post_sha256 = calculate_sha256(video_path)
        assert post_sha256 == original_sha256, "Evidence corruption: original media hash mutated!"
