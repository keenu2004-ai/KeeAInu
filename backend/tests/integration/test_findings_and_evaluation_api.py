"""Integration tests for Equipment Taxonomy, Human Findings Review, and Evaluation APIs."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.repository import repo

client = TestClient(app)


def test_taxonomy_api_endpoints():
    """Verify taxonomy structure, label translation, and decoupled annotation registration."""
    # 1. Structure endpoint
    res = client.get("/api/v1/taxonomy/structure")
    assert res.status_code == 200
    struct = res.json()
    assert "ENGINES_TURBINES" in struct["equipment_families"]
    assert "GEARBOXES_TRANSMISSIONS" in struct["equipment_families"]

    # 2. Translate endpoint
    res = client.post("/api/v1/taxonomy/translate?raw_label=pitted_surface")
    assert res.status_code == 200
    trans = res.json()
    assert trans["mapped_defect_category"] == "PITTING"
    assert trans["mapping_confidence"] == "EXACT_MATCH"

    # 3. Create decoupled annotation
    annot_payload = {
        "asset_id": "test_asset_engine_01",
        "equipment_family": "ENGINES_TURBINES",
        "component_type": "COMPRESSOR_BLADE",
        "defect_category": "CRACK",
        "observed_visual_condition": "Stress crack along leading edge",
        "annotator_id": "Senior NDT Inspector"
    }
    res = client.post("/api/v1/taxonomy/annotations", json=annot_payload)
    assert res.status_code == 201
    created = res.json()
    assert created["equipment_family"] == "ENGINES_TURBINES"
    assert created["defect_category"] == "CRACK"

    # 4. List annotations
    res = client.get("/api/v1/taxonomy/annotations?equipment_family=ENGINES_TURBINES")
    assert res.status_code == 200
    annots = res.json()
    assert len(annots) >= 1


def test_candidate_findings_and_state_machine_flow():
    """Verify complete lifecycle of candidate findings and human decision state machine."""
    import uuid
    finding_id = f"fnd_test_{uuid.uuid4().hex[:8]}"

    # 1. Create candidate finding (defaults to UNREVIEWED)
    payload = {
        "id": finding_id,
        "asset_id": "ast_test_gearbox_01",
        "frame_index": 5,
        "timestamp_ms": 166.7,
        "timestamp_provenance": "NOMINAL_APPROXIMATE",
        "equipment_family": "GEARBOXES_TRANSMISSIONS",
        "component_type": "GEAR_TOOTH_FACE",
        "candidate_defect": "PITTING",
        "model_prediction_confidence": 0.88,
        "is_simulated": True,
        "review_state": "UNREVIEWED",
        "severity": "UNSPECIFIED",
        "created_at": "2026-10-09T00:00:00Z",
        "updated_at": "2026-10-09T00:00:00Z"
    }
    res = client.post("/api/v1/findings", json=payload)
    assert res.status_code == 201
    finding = res.json()
    assert finding["review_state"] == "UNREVIEWED"

    # 2. Reject confirmation if rationale is blank
    bad_decision = {
        "review_state": "CONFIRMED_DEFECT",
        "severity": "CRITICAL",
        "reviewed_by": "Inspector",
        "reviewer_role": "CERTIFIED_INSPECTOR",
        "reviewer_rationale": "   " # Blank rationale should fail
    }
    res = client.post(f"/api/v1/findings/{finding_id}/decision", json=bad_decision)
    assert res.status_code == 422

    # 3. Transition to UNDER_REVIEW
    res = client.post(
        f"/api/v1/findings/{finding_id}/decision",
        json={
            "review_state": "UNDER_REVIEW",
            "severity": "MINOR",
            "reviewed_by": "NDT Level 2",
            "reviewer_role": "CERTIFIED_INSPECTOR",
            "reviewer_rationale": "Escalating for closer metallurgical review"
        }
    )
    assert res.status_code == 200
    assert res.json()["review_state"] == "UNDER_REVIEW"

    # 4. Confirm Defect with full engineering rationale
    confirm_decision = {
        "review_state": "CONFIRMED_DEFECT",
        "severity": "MAJOR",
        "reviewed_by": "NDT Level 3 Lead",
        "reviewer_role": "CERTIFIED_INSPECTOR",
        "reviewer_rationale": "Micro-pitting clusters verified exceeding 0.5mm threshold.",
        "engineering_diagnosis": "Lubrication degradation surface contact wear",
        "advisory_recommendation": "Advisory: Drain and replace gearbox oil within 25 operating hours."
    }
    res = client.post(f"/api/v1/findings/{finding_id}/decision", json=confirm_decision)
    assert res.status_code == 200
    confirmed = res.json()
    assert confirmed["review_state"] == "CONFIRMED_DEFECT"
    assert confirmed["severity"] == "MAJOR"

    # 5. Check immutable decision history
    res = client.get(f"/api/v1/findings/{finding_id}/history")
    assert res.status_code == 200
    history = res.json()
    assert len(history) == 2 # UNDER_REVIEW, then CONFIRMED_DEFECT


def test_evaluation_api_workflow():
    """Verify evaluation run trigger, persistence, and reporting endpoints."""
    eval_config = {
        "name": "Integration Benchmark Test",
        "target_equipment_families": [
            "ENGINES_TURBINES",
            "GEARBOXES_TRANSMISSIONS"
        ],
        "split_strategy": "ASSET_SESSION_SPLIT",
        "train_ratio": 0.70,
        "val_ratio": 0.15,
        "test_ratio": 0.15,
        "synthetic_handling": "EXCLUDE_FROM_EVAL",
        "min_samples_threshold": 1,
        "random_seed": 42,
        "evaluator_identity": "Automated CI Test Suite"
    }

    res = client.post("/api/v1/evaluation/run", json=eval_config)
    assert res.status_code == 201
    report = res.json()
    assert "run_id" in report
    assert "dataset_manifest_hash" in report
    assert len(report["equipment_slices"]) >= 2

    # Verify listing historic runs
    res = client.get("/api/v1/evaluation/runs")
    assert res.status_code == 200
    runs = res.json()
    assert len(runs) >= 1

    # Verify getting individual report
    run_id = report["run_id"]
    res = client.get(f"/api/v1/evaluation/runs/{run_id}")
    assert res.status_code == 200
    assert res.json()["run_id"] == run_id
