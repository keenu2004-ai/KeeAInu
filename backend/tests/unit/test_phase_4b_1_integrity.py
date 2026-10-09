"""Phase 4B.1 Functional Integrity & Honesty Regression Tests.

Verifies:
1. Public acquisition never creates fake placeholder JPEGs and returns explicit MANUAL_ACTION_REQUIRED.
2. Evaluation computes genuine spatial IoU (not hardcoded 0.78), deterministic SHA-256 manifest hash, and flags mock baselines honestly.
3. Reviewer role authorization prevents unauthorized users from confirming findings.
4. Intended-use license gates fail closed for unapproved uses (e.g. noncommercial -> commercial training).
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from backend.app.main import app
from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    CandidateAcquisitionStatus,
    LicensePermissionStatus,
    DiscoveryVerificationStatus,
    DownloadSupportStatus,
    AcquireCandidateRequest
)
from backend.app.modules.acquisition.pipeline import execute_acquisition
from backend.app.db.repository import repo
from backend.app.schemas.evaluation import (
    EvaluationRunConfig,
    SplitStrategy,
    SyntheticEvalHandling,
    MetricStatus
)
from backend.app.schemas.taxonomy import EquipmentFamily, DefectCategory
from backend.app.modules.evaluation.evaluator import (
    compute_bounding_box_iou,
    compute_manifest_hash,
    compute_classification_metrics,
    EvaluationEngine
)
from backend.app.modules.acquisition.license_gate import (
    can_discover_metadata,
    can_download_media,
    can_use_for_evaluation,
    can_use_for_commercial_training,
    can_use_for_noncommercial_research,
    evaluate_all_permissions
)


# ---------------------------------------------------------------------------
# 1. Honest Public Acquisition Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_public_acquisition_never_generates_fake_media():
    """
    Ensure that attempting to acquire a public dataset candidate never synthesizes
    or fabricates a fake JPEG, and instead returns MANUAL_ACTION_REQUIRED.
    """
    public_candidate = DatasetCandidateRecord(
        id="cand_pub_test_123",
        source_id="huggingface",
        provider_name="Hugging Face Datasets",
        title="MVTec Anomaly Detection",
        publisher="MVTec Software GmbH",
        canonical_url="https://huggingface.co/datasets/MVTec/anomaly-detection",
        domain_tag="MECHANICAL",
        is_direct_videoscope=False,
        modalities=["still_images"],
        annotation_types=["pixel_segmentation_masks"],
        license_identifier="CC-BY-NC-SA-4.0",
        license_status=LicensePermissionStatus.APPROVED_FOR_EVALUATION,
        commercial_use_allowed=False,
        attribution_required=True,
        relevance_score=85.0,
        acquisition_status=CandidateAcquisitionStatus.DISCOVERED,
        verification_status=DiscoveryVerificationStatus.CURATED_LEAD_AWAITING_VERIFICATION,
        download_support=DownloadSupportStatus.MANUAL_ACTION_REQUIRED,
        created_at="2026-10-09T00:00:00Z",
        updated_at="2026-10-09T00:00:00Z"
    )

    repo.save_candidate(public_candidate.model_dump())

    res = await execute_acquisition(
        AcquireCandidateRequest(
            candidate_id=public_candidate.id,
            max_files_limit=10,
            max_megabytes_limit=50,
            requested_by="Test Runner"
        )
    )

    # Must NOT report COMPLETED
    assert res["status"] == "MANUAL_ACTION_REQUIRED"
    assert res["acquired_assets_count"] == 0
    assert "unavailable" in (res.get("error_message") or "").lower()


# ---------------------------------------------------------------------------
# 2. Honest Evaluation Metrics & IoU Tests
# ---------------------------------------------------------------------------

def test_true_spatial_box_iou_calculation():
    """Verify compute_bounding_box_iou computes genuine intersection-over-union, not constant 0.78."""
    # 1. Exact identical boxes -> IoU = 1.0
    box_a = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
    box_b = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
    assert compute_bounding_box_iou(box_a, box_b) == pytest.approx(1.0, abs=1e-4)

    # 2. Non-overlapping boxes -> IoU = 0.0
    box_c = {"x_min": 0.6, "y_min": 0.6, "x_max": 0.9, "y_max": 0.9}
    assert compute_bounding_box_iou(box_a, box_c) == pytest.approx(0.0, abs=1e-4)

    # 3. Partial overlap
    # Box 1: [0.0, 0.0, 0.5, 0.5] -> Area 0.25
    # Box 2: [0.25, 0.0, 0.75, 0.5] -> Area 0.25
    # Intersection: [0.25, 0.0, 0.5, 0.5] -> Area 0.125
    # Union: 0.25 + 0.25 - 0.125 = 0.375 -> IoU = 0.125 / 0.375 = 0.3333...
    box_1 = {"x_min": 0.0, "y_min": 0.0, "x_max": 0.5, "y_max": 0.5}
    box_2 = {"x_min": 0.25, "y_min": 0.0, "x_max": 0.75, "y_max": 0.5}
    assert compute_bounding_box_iou(box_1, box_2) == pytest.approx(0.125 / 0.375, abs=1e-3)


def test_deterministic_manifest_hash():
    """Verify compute_manifest_hash is deterministic and key-order independent."""
    config = EvaluationRunConfig(
        name="Deterministic Hash Verification",
        target_equipment_families=[EquipmentFamily.ENGINES_TURBINES],
        split_strategy=SplitStrategy.ASSET_SESSION_SPLIT,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        synthetic_handling=SyntheticEvalHandling.EXCLUDE_FROM_EVAL,
        random_seed=42
    )

    annots_1 = [
        {"asset_id": "ast_1", "frame_index": 0, "defect_category": "CRACK"},
        {"asset_id": "ast_2", "frame_index": 5, "defect_category": "PITTING"}
    ]
    annots_2 = [
        {"frame_index": 5, "defect_category": "PITTING", "asset_id": "ast_2"},
        {"asset_id": "ast_1", "frame_index": 0, "defect_category": "CRACK"}
    ]

    hash_1 = compute_manifest_hash(annots_1, config)
    hash_2 = compute_manifest_hash(annots_2, config)

    assert hash_1.startswith("sha256:")
    assert hash_1 == hash_2


def test_evaluation_pipeline_marks_simulated_baseline_honestly():
    """Verify that when mock/baseline predictions are evaluated, is_simulated_baseline is True."""
    config = EvaluationRunConfig(
        name="Simulated Baseline Honesty Test",
        target_equipment_families=[EquipmentFamily.ENGINES_TURBINES],
        split_strategy=SplitStrategy.ASSET_SESSION_SPLIT,
        train_ratio=0.5,
        val_ratio=0.25,
        test_ratio=0.25,
        synthetic_handling=SyntheticEvalHandling.SYNTHETIC_BENCHMARK_ONLY,
        random_seed=42
    )

    ground_truth = [
        {
            "asset_id": "ast_eval_01",
            "frame_index": 0,
            "equipment_family": "ENGINES_TURBINES",
            "component_type": "COMPRESSOR_BLADE",
            "defect_category": "CRACK",
            "bounding_box": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5},
            "is_synthetic": True
        }
    ]

    predictions = [
        {
            "asset_id": "ast_eval_01",
            "frame_index": 0,
            "equipment_family": "ENGINES_TURBINES",
            "component_type": "COMPRESSOR_BLADE",
            "defect_category": "CRACK",
            "candidate_bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5},
            "model_prediction_confidence": 0.95,
            "is_simulated": True
        }
    ]

    report = EvaluationEngine.run_equipment_evaluation(
        annotations=ground_truth,
        predictions=predictions,
        config=config
    )

    # Must be honestly flagged as simulated baseline
    assert report.is_simulated_baseline is True
    assert report.total_samples_evaluated >= 1
    assert len(report.equipment_slices) >= 1
    assert report.equipment_slices[0].localization.mean_iou == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# 3. Reviewer Authorization Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reviewer_authorization_on_defect_confirmation():
    """Verify that only authorized reviewer roles can confirm defects (HTTP 403 for unauthorized)."""
    import uuid
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register a finding
        finding_id = f"fnd_auth_{uuid.uuid4().hex[:8]}"
        finding_payload = {
            "id": finding_id,
            "asset_id": "ast_auth_test_01",
            "frame_index": 0,
            "equipment_family": "ENGINES_TURBINES",
            "component_type": "NOZZLE_GUIDE_VANE",
            "candidate_defect": "CRACK",
            "model_prediction_confidence": 0.88,
            "is_simulated": True
        }
        f_res = await client.post("/api/v1/findings", json=finding_payload)
        assert f_res.status_code == 201

        # Attempt confirmation with UNAUTHORIZED role -> MUST be 403
        unauth_review = {
            "review_state": "CONFIRMED_DEFECT",
            "severity": "CRITICAL",
            "reviewed_by": "Trainee User",
            "reviewer_role": "TRAINEE",
            "reviewer_rationale": "Unauthorized confirmation attempt"
        }
        unauth_res = await client.post(f"/api/v1/findings/{finding_id}/decision", json=unauth_review)
        assert unauth_res.status_code == 403
        assert "not authorized" in unauth_res.json()["detail"].lower()

        # Attempt confirmation with AUTHORIZED role -> MUST succeed (200)
        auth_review = {
            "review_state": "CONFIRMED_DEFECT",
            "severity": "CRITICAL",
            "reviewed_by": "Lead Inspector",
            "reviewer_role": "CERTIFIED_INSPECTOR",
            "reviewer_rationale": "Authorized confirmation by certified inspector",
            "engineering_diagnosis": "High-cycle fatigue crack",
            "advisory_recommendation": "Replace nozzle vane set before next cycle"
        }
        auth_res = await client.post(f"/api/v1/findings/{finding_id}/decision", json=auth_review)
        assert auth_res.status_code == 200
        assert auth_res.json()["review_state"] == "CONFIRMED_DEFECT"


# ---------------------------------------------------------------------------
# 4. Intended-Use License Gate Separation Tests
# ---------------------------------------------------------------------------

def test_intended_use_license_permissions_isolation():
    """Verify license gate evaluates individual use-cases independently and strictly."""
    # 1. Non-commercial dataset (e.g. CC-BY-NC)
    nc_status = LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH

    disc_ok, _ = can_discover_metadata(nc_status)
    dl_ok, _ = can_download_media(nc_status)
    eval_ok, _ = can_use_for_evaluation(nc_status)
    res_ok, _ = can_use_for_noncommercial_research(nc_status)
    comm_ok, comm_err = can_use_for_commercial_training(nc_status)

    assert disc_ok is True
    assert dl_ok is True
    assert eval_ok is True
    assert res_ok is True
    assert comm_ok is False
    assert "Commercial training forbidden" in (comm_err or "")

    # 2. Unknown or restricted license fails closed
    unk_status = LicensePermissionStatus.LICENSE_UNKNOWN
    perms = evaluate_all_permissions(unk_status)
    assert perms["discover_metadata"] is True
    assert perms["download_media"] is False
    assert perms["benchmark_evaluation"] is False
    assert perms["noncommercial_research"] is False
    assert perms["commercial_training"] is False
    assert perms["redistribution"] is False
