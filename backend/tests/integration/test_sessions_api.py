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
