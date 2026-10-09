"""Integration tests for Simulated Inference and Inspector Review workflows."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_inference_and_review_lifecycle():
    video_path = Path("data/sample_fixtures/synthetic_test_video.mp4")
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Session
        s_res = await client.post(
            "/api/v1/sessions",
            json={"title": "Inference Lifecycle Session", "inspector_name": "Dr. Miller"}
        )
        session_id = s_res.json()["id"]

        # 2. Upload Video
        files = {"file": ("feed.mp4", video_path.read_bytes(), "video/mp4")}
        up_res = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
        media_id = up_res.json()["id"]

        # 3. Analyze Frame 1 (Odd frame produces candidate in MockEngine)
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
        assert inf_data["findings_count"] == 1
        finding = inf_data["findings"][0]
        finding_id = finding["id"]
        assert finding["defect_class"] == "CRACK"
        assert finding["is_simulated"] is True
        assert finding["decision_status"] == "PENDING_REVIEW"

        # 4. List Session Findings
        list_res = await client.get(f"/api/v1/inference/sessions/{session_id}/findings")
        assert list_res.status_code == 200
        findings = list_res.json()
        assert len(findings) == 1
        assert findings[0]["id"] == finding_id

        # 5. Submit Review: CONFIRMED
        rev_res = await client.post(
            "/api/v1/reviews",
            json={
                "finding_id": finding_id,
                "decision_status": "CONFIRMED",
                "severity": "CRITICAL",
                "reviewed_by": "Dr. Miller",
                "inspector_notes": "Confirmed hairline crack on turbine blade leading edge."
            }
        )
        assert rev_res.status_code == 200
        rev_data = rev_res.json()
        assert rev_data["decision_status"] == "CONFIRMED"
        assert rev_data["severity"] == "CRITICAL"
        assert rev_data["inspector_notes"] == "Confirmed hairline crack on turbine blade leading edge."
        assert rev_data["reviewed_by"] == "Dr. Miller"

        # 6. Reject Invalid Review Decision Status
        bad_rev = await client.post(
            "/api/v1/reviews",
            json={
                "finding_id": finding_id,
                "decision_status": "INVALID_STATUS",
                "severity": "CRITICAL",
                "reviewed_by": "Dr. Miller"
            }
        )
        assert bad_rev.status_code == 400
