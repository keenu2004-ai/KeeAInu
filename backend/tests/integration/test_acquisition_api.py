"""Integration tests for Multi-Source Dataset Discovery & Controlled Acquisition API."""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_list_discovery_providers():
    """Verify GET /api/v1/acquisition/providers lists all supported discovery engines."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/acquisition/providers")
        assert response.status_code == 200
        providers = response.json()
        assert len(providers) >= 8
        ids = [p["id"] for p in providers]
        assert "huggingface" in ids
        assert "kaggle" in ids
        assert "google_dataset_search" in ids
        assert "internal_storage" in ids
        assert "synthetic_generator" in ids


@pytest.mark.asyncio
async def test_search_and_registry_population():
    """Verify POST /api/v1/acquisition/search discovers and registers candidate datasets."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "query": "pipeline borescope crack",
            "target_domain": "PIPES_CHANNELS",
            "direct_videoscope_only": False,
            "max_results_per_provider": 5
        }
        response = await client.post("/api/v1/acquisition/search", json=payload)
        assert response.status_code == 200
        candidates = response.json()
        assert len(candidates) >= 1

        # Check candidate structure
        first = candidates[0]
        assert "id" in first
        assert "relevance_score" in first
        assert first["domain_tag"] != ""
        assert "relevance_breakdown" in first


@pytest.mark.asyncio
async def test_license_review_and_gate_enforcement():
    """Verify human compliance license review and license gate enforcement on acquisition."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Search to populate registry
        search_res = await client.post(
            "/api/v1/acquisition/search",
            json={"query": "kolektor surface crack", "target_domain": "MECHANICAL"}
        )
        candidates = search_res.json()
        assert len(candidates) > 0
        candidate_id = candidates[0]["id"]

        # 2. Set to REJECTED license state
        review_payload = {
            "license_status": "REJECTED",
            "commercial_rights_status": "FORBIDDEN",
            "license_notes": "Terms prohibit any external ingestion.",
            "reviewed_by": "Compliance Lead"
        }
        rev_res = await client.post(f"/api/v1/acquisition/candidates/{candidate_id}/license-review", json=review_payload)
        assert rev_res.status_code == 200
        assert rev_res.json()["license_status"] == "REJECTED"

        # 3. Attempt acquisition -> MUST be 403 Forbidden
        acq_payload = {"candidate_id": candidate_id, "max_files_limit": 5, "max_megabytes_limit": 50}
        acq_res = await client.post(f"/api/v1/acquisition/candidates/{candidate_id}/acquire", json=acq_payload)
        assert acq_res.status_code == 403
        assert "License Gate Violation" in acq_res.json()["detail"]

        # 4. Update to APPROVED_FOR_EVALUATION
        approve_payload = {
            "license_status": "APPROVED_FOR_EVALUATION",
            "commercial_rights_status": "ALLOWED",
            "license_notes": "Approved for evaluation test harness.",
            "reviewed_by": "Lead Counsel"
        }
        app_res = await client.post(f"/api/v1/acquisition/candidates/{candidate_id}/license-review", json=approve_payload)
        assert app_res.status_code == 200
        assert app_res.json()["license_status"] == "APPROVED_FOR_EVALUATION"

        # 5. Acquire public candidate -> MUST return MANUAL_ACTION_REQUIRED (no fake placeholders generated)
        acq_success = await client.post(f"/api/v1/acquisition/candidates/{candidate_id}/acquire", json=acq_payload)
        assert acq_success.status_code == 200
        acq_data = acq_success.json()
        assert acq_data["status"] == "MANUAL_ACTION_REQUIRED"
        assert acq_data["acquired_assets_count"] == 0
        assert "unavailable" in acq_data["error_message"].lower() or "manual" in acq_data["error_message"].lower()

        # 6. Test internal storage candidate -> Automated ingestion succeeds
        internal_search = await client.post(
            "/api/v1/acquisition/search",
            json={"query": "internal", "target_domain": "PIPES_CHANNELS"}
        )
        int_candidates = internal_search.json()
        int_cand = next((c for c in int_candidates if c["source_id"] == "internal_storage"), None)
        if int_cand:
            int_acq = await client.post(
                f"/api/v1/acquisition/candidates/{int_cand['id']}/acquire",
                json={"candidate_id": int_cand["id"], "max_files_limit": 5, "max_megabytes_limit": 50}
            )
            assert int_acq.status_code == 200
            int_data = int_acq.json()
            assert int_data["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_procedural_synthetic_generation_api():
    """Verify POST /api/v1/acquisition/synthetic/generate creates synthetic assets with traceable provenance."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "generation_type": "PROCEDURAL_SURFACE",
            "target_domain": "PIPES_CHANNELS",
            "defect_type": "CRACK",
            "count": 2,
            "lighting_variation": 0.3,
            "noise_level": 0.1,
            "random_seed": 12345,
            "requested_by": "AI Benchmark Lead"
        }
        res = await client.post("/api/v1/acquisition/synthetic/generate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "COMPLETED"
        assert data["generated_count"] == 2
        assets = data["assets"]
        assert len(assets) == 2
        for a in assets:
            assert a["is_synthetic"] is True
            assert a["is_readable"] is True
            assert len(a["samples"]) >= 1


@pytest.mark.asyncio
async def test_acquisition_audit_trail_api():
    """Verify GET /api/v1/acquisition/audit-trail exports verifiable compliance events."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/acquisition/audit-trail")
        assert res.status_code == 200
        events = res.json()
        assert isinstance(events, list)
        assert len(events) >= 1
        for e in events:
            assert "event_type" in e
            assert "details" in e
            assert "created_at" in e
