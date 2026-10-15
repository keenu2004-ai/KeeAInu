"""Comprehensive Multi-Media End-to-End Workflow & Isolation Regression Test.

Verifies:
1. Complete inspection workflow lifecycle:
   - Session creation
   - Multi-media upload (Image 1 and Image 2)
   - Media count synchronization
   - Frame defect candidate inference
   - Finding metadata isolation (zero bleed between media records)
   - Finding selection & review decision recording
   - State machine transitions (DRAFT -> IN_REVIEW -> COMPLETED -> ARCHIVED)
   - Complete persistence across state reload
"""

import io
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256


def _make_test_image(color: tuple, format_name: str = "PNG") -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_complete_multi_media_inspection_workflow_and_isolation():
    """
    Simulates inspector executing full multi-media inspection:
    - Verifies media-specific findings never bleed across files in the same session.
    - Verifies review decisions persist accurately.
    - Verifies session status transitions and reload integrity.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create Session
        s_res = await client.post(
            "/api/v1/sessions",
            json={
                "title": "Combustor Liner Multi-Probe Inspection",
                "inspector_name": "Chief Inspector Marcus Vance",
                "asset_tag": "COMB-902-LINER"
            }
        )
        assert s_res.status_code == 201
        session = s_res.json()
        session_id = session["id"]
        assert session["status"] == "DRAFT"
        assert session.get("media_count") == 0

        # Step 2: Upload Media 1 (Video feed)
        video_path = settings.DATA_DIR / "sample_fixtures" / "synthetic_test_video.mp4"
        video_bytes = video_path.read_bytes()
        hash_1 = calculate_sha256(video_bytes)
        up_res_1 = await client.post(
            "/api/v1/media/upload",
            data={"session_id": session_id},
            files={"file": ("combustor_sector_a.mp4", video_bytes, "video/mp4")}
        )
        assert up_res_1.status_code == 201
        media_1 = up_res_1.json()
        media_1_id = media_1["id"]
        assert media_1["sha256_hash"] == hash_1

        # Step 3: Upload Media 2 (Still image sample)
        bytes_2 = _make_test_image((30, 144, 255), "PNG")
        hash_2 = calculate_sha256(bytes_2)
        up_res_2 = await client.post(
            "/api/v1/media/upload",
            data={"session_id": session_id},
            files={"file": ("combustor_sector_b.png", bytes_2, "image/png")}
        )
        assert up_res_2.status_code == 201
        media_2 = up_res_2.json()
        media_2_id = media_2["id"]
        assert media_2["sha256_hash"] == hash_2
        assert media_1_id != media_2_id

        # Verify media count on session detail and list
        detail_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["media_count"] == 2
        assert len(detail_res.json()["media"]) == 2

        # Step 4: Execute Defect Candidate Inference on Media 1 (Frame 1)
        inf_res_1 = await client.post(
            "/api/v1/inference/analyze-frame",
            json={
                "session_id": session_id,
                "media_id": media_1_id,
                "frame_index": 1,
                "confidence_threshold": 0.5,
                "engine": "mock"
            }
        )
        assert inf_res_1.status_code == 200
        inf_data_1 = inf_res_1.json()
        assert inf_data_1["media_id"] == media_1_id
        assert inf_data_1["is_simulated"] is True
        assert len(inf_data_1["findings"]) >= 1

        finding_1 = inf_data_1["findings"][0]
        finding_1_id = finding_1["id"]
        assert finding_1["media_id"] == media_1_id
        assert finding_1["frame_index"] == 1
        assert finding_1["is_simulated"] is True

        # Step 5: STRICT ISOLATION CHECK — Media 2 must have NO findings
        all_findings_res = await client.get(f"/api/v1/inference/sessions/{session_id}/findings")
        assert all_findings_res.status_code == 200
        session_findings = all_findings_res.json()

        # All existing findings MUST belong to Media 1; ZERO bleed to Media 2
        for f in session_findings:
            assert f["media_id"] == media_1_id, f"Finding bleed detected! Finding {f['id']} belongs to {f['media_id']}, expected {media_1_id}"

        # Inference records for Media 2 must be empty
        rec_res_2 = await client.get(f"/api/v1/inference/records?media_id={media_2_id}")
        assert rec_res_2.status_code == 200
        assert len(rec_res_2.json()) == 0

        # Step 6: Submit Inspector Review Decision on Finding 1
        rev_res = await client.post(
            "/api/v1/reviews",
            json={
                "finding_id": finding_1_id,
                "decision_status": "CONFIRMED",
                "severity": "CRITICAL",
                "reviewed_by": "Chief Inspector Marcus Vance",
                "inspector_notes": "Thermal stress fracture confirmed on Sector A trailing lip."
            }
        )
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert rev_data["decision_status"] == "CONFIRMED"
        assert rev_data["severity"] == "CRITICAL"

        # Step 7: Progress Inspection Lifecycle: DRAFT -> IN_REVIEW -> COMPLETED
        trans_1 = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "IN_REVIEW"}
        )
        assert trans_1.status_code == 200
        assert trans_1.json()["status"] == "IN_REVIEW"

        trans_2 = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "COMPLETED"}
        )
        assert trans_2.status_code == 200
        assert trans_2.json()["status"] == "COMPLETED"

        # Step 8: Persistence Verification after Page Reload / Server Re-query
        reload_s_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert reload_s_res.status_code == 200
        reloaded_session = reload_s_res.json()
        assert reloaded_session["status"] == "COMPLETED"
        assert reloaded_session["media_count"] == 2
        assert len(reloaded_session["media"]) == 2

        reload_f_res = await client.get(f"/api/v1/inference/sessions/{session_id}/findings")
        assert reload_f_res.status_code == 200
        reloaded_findings = reload_f_res.json()
        assert len(reloaded_findings) >= 1
        persisted_f1 = next(f for f in reloaded_findings if f["id"] == finding_1_id)
        assert persisted_f1["decision_status"] == "CONFIRMED"
        assert persisted_f1["severity"] == "CRITICAL"
        assert persisted_f1["inspector_notes"] == "Thermal stress fracture confirmed on Sector A trailing lip."
        assert persisted_f1["media_id"] == media_1_id

        # Step 9: Archive Transition
        trans_arch = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "ARCHIVED"}
        )
        assert trans_arch.status_code == 200
        assert trans_arch.json()["status"] == "ARCHIVED"

        # Verify terminal state rejects further transitions
        trans_illegal = await client.patch(
            f"/api/v1/sessions/{session_id}/status",
            json={"status": "DRAFT"}
        )
        assert trans_illegal.status_code == 400
