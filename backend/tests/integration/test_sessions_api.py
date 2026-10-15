"""Integration tests for Sessions API."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_create_and_get_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        res = await client.post(
            "/api/v1/sessions",
            json={
                "title": "Turbine Chamber Inspection #4",
                "inspector_name": "Dr. Sarah Lin",
                "asset_tag": "TURB-004-BLADES"
            }
        )
        assert res.status_code == 201
        data = res.json()
        session_id = data["id"]
        assert data["title"] == "Turbine Chamber Inspection #4"
        assert data["status"] == "DRAFT"
        assert data["inspector_name"] == "Dr. Sarah Lin"

        # Get session
        get_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_res.status_code == 200
        get_data = get_res.json()
        assert get_data["id"] == session_id
        assert "media" in get_data


@pytest.mark.asyncio
async def test_session_status_transitions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_res = await client.post(
            "/api/v1/sessions",
            json={"title": "Status Test Session", "inspector_name": "Tester"}
        )
        session_id = create_res.json()["id"]

        # Valid transition: DRAFT -> IN_REVIEW
        t1 = await client.patch(f"/api/v1/sessions/{session_id}/status", json={"status": "IN_REVIEW"})
        assert t1.status_code == 200
        assert t1.json()["status"] == "IN_REVIEW"

        # Invalid transition: IN_REVIEW -> DRAFT -> COMPLETED is valid, but invalid state name will fail
        t_bad = await client.patch(f"/api/v1/sessions/{session_id}/status", json={"status": "NON_EXISTENT_STATE"})
        assert t_bad.status_code == 400

        # Valid transition: IN_REVIEW -> COMPLETED
        t2 = await client.patch(f"/api/v1/sessions/{session_id}/status", json={"status": "COMPLETED"})
        assert t2.status_code == 200
        assert t2.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_get_non_existent_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/sessions/sess_non_existent_999")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_media_count_consistency_and_lifecycle():
    """Verify media_count is accurate, numeric, and identical across list and detail endpoints."""
    import io
    from PIL import Image

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create fresh session
        create_res = await client.post(
            "/api/v1/sessions",
            json={"title": "Media Count Lifecycle Audit", "inspector_name": "Auditor"}
        )
        assert create_res.status_code == 201
        session_id = create_res.json()["id"]

        # 0 media check
        detail_res = await client.get(f"/api/v1/sessions/{session_id}")
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        assert detail_data.get("media_count") == 0
        assert len(detail_data.get("media", [])) == 0

        list_res = await client.get("/api/v1/sessions")
        assert list_res.status_code == 200
        listed_item = next(s for s in list_res.json() if s["id"] == session_id)
        assert listed_item.get("media_count") == 0

        # Upload first image
        img1 = Image.new("RGB", (32, 32), color=(255, 0, 0))
        buf1 = io.BytesIO()
        img1.save(buf1, format="PNG")
        files1 = {"file": ("inspection_img1.png", buf1.getvalue(), "image/png")}
        up1 = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files1)
        assert up1.status_code == 201

        # 1 media check
        detail1 = (await client.get(f"/api/v1/sessions/{session_id}")).json()
        assert detail1.get("media_count") == 1
        assert len(detail1.get("media", [])) == 1

        list1 = (await client.get("/api/v1/sessions")).json()
        listed_item1 = next(s for s in list1 if s["id"] == session_id)
        assert listed_item1.get("media_count") == 1

        # Upload second image
        img2 = Image.new("RGB", (32, 32), color=(0, 255, 0))
        buf2 = io.BytesIO()
        img2.save(buf2, format="PNG")
        files2 = {"file": ("inspection_img2.png", buf2.getvalue(), "image/png")}
        up2 = await client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files2)
        assert up2.status_code == 201

        # 2 media check
        detail2 = (await client.get(f"/api/v1/sessions/{session_id}")).json()
        assert detail2.get("media_count") == 2
        assert len(detail2.get("media", [])) == 2

        list2 = (await client.get("/api/v1/sessions")).json()
        listed_item2 = next(s for s in list2 if s["id"] == session_id)
        assert listed_item2.get("media_count") == 2


@pytest.mark.asyncio
async def test_exhaustive_status_transitions_and_rejections():
    """Verify all allowed and rejected state transitions according to the state machine contract."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Branch 1: DRAFT -> ARCHIVED direct archive
        res1 = await client.post("/api/v1/sessions", json={"title": "Archive Test 1", "inspector_name": "QA"})
        s1 = res1.json()["id"]
        arch_res = await client.patch(f"/api/v1/sessions/{s1}/status", json={"status": "ARCHIVED"})
        assert arch_res.status_code == 200
        assert arch_res.json()["status"] == "ARCHIVED"

        # ARCHIVED is terminal -> cannot transition back to DRAFT or COMPLETED
        rej1 = await client.patch(f"/api/v1/sessions/{s1}/status", json={"status": "DRAFT"})
        assert rej1.status_code == 400
        rej2 = await client.patch(f"/api/v1/sessions/{s1}/status", json={"status": "COMPLETED"})
        assert rej2.status_code == 400

        # Branch 2: DRAFT -> COMPLETED is illegal (must pass through IN_REVIEW)
        res2 = await client.post("/api/v1/sessions", json={"title": "Flow Test 2", "inspector_name": "QA"})
        s2 = res2.json()["id"]
        rej_comp = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "COMPLETED"})
        assert rej_comp.status_code == 400

        # DRAFT -> IN_REVIEW -> DRAFT (return to draft is allowed)
        r_rev = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "IN_REVIEW"})
        assert r_rev.status_code == 200
        r_draft = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "DRAFT"})
        assert r_draft.status_code == 200

        # DRAFT -> IN_REVIEW -> COMPLETED
        await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "IN_REVIEW"})
        r_completed = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "COMPLETED"})
        assert r_completed.status_code == 200

        # COMPLETED cannot revert to DRAFT or IN_REVIEW
        rej_revert1 = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "DRAFT"})
        assert rej_revert1.status_code == 400
        rej_revert2 = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "IN_REVIEW"})
        assert rej_revert2.status_code == 400

        # COMPLETED -> ARCHIVED is allowed
        r_final_arch = await client.patch(f"/api/v1/sessions/{s2}/status", json={"status": "ARCHIVED"})
        assert r_final_arch.status_code == 200
        assert r_final_arch.json()["status"] == "ARCHIVED"
