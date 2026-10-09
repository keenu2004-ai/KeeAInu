"""Comprehensive Integration Tests for Dataset Discovery, Profiling & Domain Review (Phase 4A)."""

from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.schemas.discovery import DomainCategory, DomainConfidence, SampleReviewStatus


@pytest.mark.asyncio
async def test_discovery_scan_and_inventory():
    """Verify that discovery scan indexes synthetic fixtures and vaults, generates quality profiles & samples."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run scan
        scan_res = await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 4, "force_rescan": True})
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        assert scan_data["status"] == "COMPLETED"
        assert scan_data["scanned_count"] > 0
        summary = scan_data["summary"]
        assert summary["total_assets"] >= 3
        assert summary["synthetic_assets_count"] >= 3

        # List assets
        assets_res = await client.get("/api/v1/discovery/assets")
        assert assets_res.status_code == 200
        assets = assets_res.json()
        assert len(assets) >= 3

        # Find synthetic video asset
        video_asset = next((a for a in assets if a["filename"] == "synthetic_test_video.mp4"), None)
        assert video_asset is not None
        assert video_asset["is_readable"] is True
        assert video_asset["is_synthetic"] is True
        assert video_asset["width"] == 320
        assert video_asset["height"] == 240
        assert video_asset["fps"] == 30.0
        assert video_asset["quality_profile"] is not None
        assert "sharpness_score" in video_asset["quality_profile"]
        assert len(video_asset["samples"]) >= 1

        # Check contact sheet endpoint
        cs_res = await client.get(f"/api/v1/discovery/assets/{video_asset['id']}/contact-sheet")
        assert cs_res.status_code == 200
        assert cs_res.headers["content-type"] == "image/jpeg"

        # Check sample content endpoint
        sample_id = video_asset["samples"][0]["id"]
        sample_res = await client.get(f"/api/v1/discovery/samples/{sample_id}/content")
        assert sample_res.status_code == 200
        assert sample_res.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_domain_assignment_workflow():
    """Verify human reviewer domain assignment lifecycle across candidate categories."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger scan
        await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3})

        assets_res = await client.get("/api/v1/discovery/assets")
        assets = assets_res.json()
        target_asset = assets[0]
        asset_id = target_asset["id"]

        # 1. Assign MECHANICAL domain
        dom_res1 = await client.patch(
            f"/api/v1/discovery/assets/{asset_id}/domain",
            json={
                "domain_assignment": "MECHANICAL",
                "domain_confidence": "PROVISIONAL",
                "domain_notes": "Appearance resembles gas turbine stage 1 nozzle guide vanes.",
                "reviewed_by": "Inspector Alice"
            }
        )
        assert dom_res1.status_code == 200
        d1 = dom_res1.json()
        assert d1["domain_assignment"] == "MECHANICAL"
        assert d1["domain_confidence"] == "PROVISIONAL"
        assert d1["domain_reviewed_by"] == "Inspector Alice"

        # 2. Re-assign to PIPES_CHANNELS
        dom_res2 = await client.patch(
            f"/api/v1/discovery/assets/{asset_id}/domain",
            json={
                "domain_assignment": "PIPES_CHANNELS",
                "domain_confidence": "CERTAIN",
                "domain_notes": "Confirmed 2-inch stainless steel boiler feed tube.",
                "reviewed_by": "Chief Inspector Bob"
            }
        )
        assert dom_res2.status_code == 200
        d2 = dom_res2.json()
        assert d2["domain_assignment"] == "PIPES_CHANNELS"
        assert d2["domain_confidence"] == "CERTAIN"

        # 3. Allow UNKNOWN and OTHER options without forcing candidate domains
        dom_res3 = await client.patch(
            f"/api/v1/discovery/assets/{asset_id}/domain",
            json={
                "domain_assignment": "UNKNOWN",
                "domain_confidence": "UNCERTAIN",
                "domain_notes": "Visual evidence insufficient to determine industrial domain.",
                "reviewed_by": "Auditor"
            }
        )
        assert dom_res3.status_code == 200
        assert dom_res3.json()["domain_assignment"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_sample_defect_review_workflow():
    """Verify human reviewer triage of sampled representative frames."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger scan
        await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3})

        assets_res = await client.get("/api/v1/discovery/assets")
        assets = assets_res.json()
        video_asset = next((a for a in assets if a["asset_type"] == "video" and len(a["samples"]) > 0), None)
        assert video_asset is not None
        sample = video_asset["samples"][0]
        sample_id = sample["id"]

        # Update review to SUSPECTED_ANOMALY
        rev_res1 = await client.patch(
            f"/api/v1/discovery/samples/{sample_id}/review",
            json={
                "review_status": "SUSPECTED_ANOMALY",
                "suspected_category": "SURFACE_CRACK",
                "reviewer_notes": "Linear dark indication along weld toe.",
                "reviewed_by": "Inspector Sarah"
            }
        )
        assert rev_res1.status_code == 200
        r1 = rev_res1.json()
        assert r1["review_status"] == "SUSPECTED_ANOMALY"
        assert r1["suspected_category"] == "SURFACE_CRACK"
        assert r1["reviewed_by"] == "Inspector Sarah"

        # Update review to CONFIRMED_DEFECT
        rev_res2 = await client.patch(
            f"/api/v1/discovery/samples/{sample_id}/review",
            json={
                "review_status": "CONFIRMED_DEFECT",
                "suspected_category": "FATIGUE_CRACK",
                "reviewer_notes": "Confirmed via dye penetrant follow-up.",
                "reviewed_by": "Lead NDT Level III"
            }
        )
        assert rev_res2.status_code == 200
        assert rev_res2.json()["review_status"] == "CONFIRMED_DEFECT"


@pytest.mark.asyncio
async def test_discovery_report_and_manifest():
    """Verify generation of discovery summary report and machine-readable manifest."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger scan
        await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3})

        # 1. Report
        rep_res = await client.get("/api/v1/discovery/report")
        assert rep_res.status_code == 200
        rep = rep_res.json()
        assert rep["total_assets"] >= 3
        assert rep["metadata_completeness_percent"] > 0.0
        assert "evaluation_split_recommendation" in rep
        assert len(rep["unresolved_questions"]) >= 1

        # 2. Manifest
        man_res = await client.get("/api/v1/discovery/manifest")
        assert man_res.status_code == 200
        man = man_res.json()
        assert man["schema_version"] == "1.0.0"
        assert man["total_assets"] >= 3
        assert len(man["items"]) >= 3
        assert "sha256_hash" in man["items"][0]


@pytest.mark.asyncio
async def test_discovery_security_and_traversal_rejection():
    """Verify that path traversal attempts in custom directory scans are strictly rejected."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Traversal outside workspace
        trav_res = await client.post(
            "/api/v1/discovery/scan",
            json={"source_directory": "../../../../windows/system32"}
        )
        assert trav_res.status_code == 400
        assert "escapes application boundary" in trav_res.json()["detail"].lower()

        # Nonexistent path
        non_res = await client.post(
            "/api/v1/discovery/scan",
            json={"source_directory": "data/non_existent_folder_xyz"}
        )
        assert non_res.status_code == 404


@pytest.mark.asyncio
async def test_repeated_scan_idempotency_and_force_rescan():
    """Verify that repeating scans without changes does not duplicate sample records, and force_rescan replaces them cleanly."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Initial scan
        res1 = await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3, "force_rescan": True})
        assert res1.status_code == 200
        assets1 = (await client.get("/api/v1/discovery/assets")).json()
        target = next((a for a in assets1 if len(a["samples"]) > 0), None)
        assert target is not None
        initial_sample_count = len(target["samples"])

        # Second scan without force_rescan
        res2 = await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3, "force_rescan": False})
        assert res2.status_code == 200
        asset_after_rescan = (await client.get(f"/api/v1/discovery/assets/{target['id']}")).json()
        assert len(asset_after_rescan["samples"]) == initial_sample_count

        # Third scan WITH force_rescan=True
        res3 = await client.post("/api/v1/discovery/scan", json={"sample_count_per_video": 3, "force_rescan": True})
        assert res3.status_code == 200
        asset_after_force = (await client.get(f"/api/v1/discovery/assets/{target['id']}")).json()
        # Verify samples count did not accumulate or double
        assert len(asset_after_force["samples"]) == initial_sample_count


@pytest.mark.asyncio
async def test_provenance_strictly_by_directory_not_filename(tmp_path_factory):
    """Verify that footage is classified as synthetic only via trusted directory provenance, not filename substrings."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a real footage file in source_footage with 'synth' in the name
        source_dir = settings.SOURCE_FOOTAGE_DIR
        source_dir.mkdir(parents=True, exist_ok=True)
        test_file = source_dir / "synthetic_test_named_user_pipe.png"
        
        from PIL import Image
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(test_file)

        try:
            scan_res = await client.post("/api/v1/discovery/scan", json={"force_rescan": True})
            assert scan_res.status_code == 200
            
            assets = (await client.get("/api/v1/discovery/assets")).json()
            user_asset = next((a for a in assets if a["filename"] == "synthetic_test_named_user_pipe.png"), None)
            assert user_asset is not None
            # Must be False because it is in source_footage, despite 'synthetic' in the filename!
            assert user_asset["is_synthetic"] is False
        finally:
            if test_file.exists():
                test_file.unlink()

