"""Integration tests for Human-Verified Annotations, Defect-Free Negatives, and Dataset Export API."""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import numpy as np
import cv2

from backend.app.main import app
from backend.app.db.repository import repo

TEST_API_KEY = "test-only-ground-truth-key"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def test_session_with_media(client: TestClient, tmp_path: Path):
    """Creates a clean test inspection session with an ingested image file."""
    # 1. Create session
    sess_res = client.post("/api/v1/sessions", json={
        "title": "Ground Truth Inspection Audit",
        "inspector_name": "Chief Inspector Vance",
        "asset_tag": "ASSET-TURBINE-001"
    })
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # 2. Upload test still image
    test_img = np.full((200, 300, 3), 100, dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", test_img)
    files = {"file": ("test_combustor.jpg", encoded.tobytes(), "image/jpeg")}
    upload_res = client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files)
    assert upload_res.status_code == 201
    media_id = upload_res.json()["id"]

    # 3. Upload a second test still image (for negative example)
    test_img2 = np.full((200, 300, 3), 200, dtype=np.uint8)
    _, encoded2 = cv2.imencode(".jpg", test_img2)
    files2 = {"file": ("test_defect_free_flange.jpg", encoded2.tobytes(), "image/jpeg")}
    upload_res2 = client.post("/api/v1/media/upload", data={"session_id": session_id}, files=files2)
    assert upload_res2.status_code == 201
    media_id2 = upload_res2.json()["id"]

    return {
        "session_id": session_id,
        "positive_media_id": media_id,
        "negative_media_id": media_id2
    }


def test_human_ground_truth_annotation_and_provenance(client: TestClient, test_session_with_media):
    """Inspector manually marks a bounding box defect: must have is_simulated=False and CONFIRMED review."""
    media_id = test_session_with_media["positive_media_id"]

    payload = {
        "defect_class": "CRACK",
        "bbox": {
            "x_min": 0.25,
            "y_min": 0.30,
            "x_max": 0.65,
            "y_max": 0.55
        },
        "frame_index": 0,
        "timestamp_ms": 0.0,
        "severity": "CRITICAL",
        "inspector_name": "Dr. Sarah Lin (NDT Level 3)",
        "inspector_notes": "Distinct longitudinal thermal fatigue crack along inner combustor liner."
    }

    res = client.post(f"/api/v1/media/{media_id}/findings", json=payload, headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 201
    finding = res.json()

    assert finding["defect_class"] == "CRACK"
    assert finding["is_simulated"] is False  # Ground truth is NOT simulated!
    assert finding["model_name"] == "HUMAN_INSPECTOR"
    assert finding["decision_status"] == "CONFIRMED"
    assert finding["reviewed_by"] == "Dr. Sarah Lin (NDT Level 3)"
    assert finding["severity"] == "CRITICAL"


def test_explicit_defect_free_negative_verification(client: TestClient, test_session_with_media):
    """Inspector explicitly confirms an image as defect-free negative example."""
    media_id2 = test_session_with_media["negative_media_id"]

    payload = {
        "verified_by": "Chief Inspector Vance",
        "notes": "Surface clean and intact. No visible defects found."
    }

    res = client.post(f"/api/v1/media/{media_id2}/verify-defect-free", json=payload, headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 200
    data = res.json()
    assert data["review_status"] == "DEFECT_FREE"
    assert data["verified_by"] == "Chief Inspector Vance"


def test_training_readiness_audit_endpoint(client: TestClient):
    """GET /api/v1/evaluation/readiness must return verifiable ground-truth counts and blockers."""
    res = client.get("/api/v1/evaluation/readiness", headers={"X-API-Key": TEST_API_KEY})
    assert res.status_code == 200
    report = res.json()

    assert "total_verified_annotations" in report
    assert "verified_classes_breakdown" in report
    assert "total_verified_negatives" in report
    assert "is_training_ready" in report
    assert "blockers" in report
    assert "next_action" in report


def test_export_role_authorization_rejection(client: TestClient):
    """Unauthorized roles (READONLY, GUEST) must be blocked from exporting datasets with HTTP 403."""
    res = client.post(
        "/api/v1/evaluation/datasets/export",
        json={"version": "v_test"},
        headers={"X-API-Key": TEST_API_KEY, "X-Inspector-Role": "READONLY"}
    )
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"]


def test_end_to_end_ground_truth_export_flow(client: TestClient, test_session_with_media, tmp_path: Path):
    """Full workflow: annotate defect + verify negative -> export YOLO dataset -> verify output files and manifest."""
    pos_media_id = test_session_with_media["positive_media_id"]
    neg_media_id = test_session_with_media["negative_media_id"]

    # 1. Annotate positive ground-truth defect
    client.post(f"/api/v1/media/{pos_media_id}/findings", json={
        "defect_class": "CORROSION",
        "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5},
        "frame_index": 0,
        "inspector_name": "Chief Inspector Vance"
    }, headers={"X-API-Key": TEST_API_KEY})

    # 2. Verify negative defect-free sample
    client.post(f"/api/v1/media/{neg_media_id}/verify-defect-free", json={
        "verified_by": "Chief Inspector Vance"
    }, headers={"X-API-Key": TEST_API_KEY})

    # 3. Trigger safe export
    export_payload = {
        "version": "test_e2e_v1",
        "output_dir": "test_e2e_v1",
        "train_ratio": 1.0,
        "val_ratio": 0.0,
        "test_ratio": 0.0,
        "include_negatives": True,
        "overwrite": True
    }

    res = client.post(
        "/api/v1/evaluation/datasets/export",
        json=export_payload,
        headers={"X-API-Key": TEST_API_KEY, "X-Inspector-Role": "LEAD_INSPECTOR"}
    )
    assert res.status_code == 200
    manifest = res.json()

    assert manifest["dataset_version"] == "test_e2e_v1"
    assert manifest["export_format"] == "YOLO"
    assert manifest["total_images"] >= 2
    assert manifest["positive_images"] >= 1
    assert manifest["negative_images"] >= 1
    assert "CORROSION" in manifest["class_mapping"]
    assert manifest["split_leakage_detected"] is False
    assert manifest["manifest_sha256"].startswith("sha256:")

    # 4. Validate exported dataset via POST /api/v1/evaluation/datasets/validate
    val_res = client.post(
        "/api/v1/evaluation/datasets/validate",
        json={"dataset_path": "test_e2e_v1"},
        headers={"X-API-Key": TEST_API_KEY}
    )
    assert val_res.status_code == 200
    val_report = val_res.json()
    assert val_report["valid"] is True
    assert val_report["total_images"] >= 2
    assert val_report["positive_images"] >= 1
    assert val_report["negative_images"] >= 1


def test_sensitive_endpoints_reject_missing_api_key(client: TestClient):
    """Sensitive ground-truth and export routes reject callers without the shared key."""
    assert client.get("/api/v1/evaluation/readiness").status_code == 401

    export_res = client.post(
        "/api/v1/evaluation/datasets/export",
        json={"version": "unauthorized_test"},
    )
    assert export_res.status_code == 401

    annotation_res = client.post(
        "/api/v1/media/med_missing/findings",
        json={
            "defect_class": "CRACK",
            "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5},
            "inspector_name": "Untrusted Caller",
        },
    )
    assert annotation_res.status_code == 401

    negative_res = client.post(
        "/api/v1/media/med_missing/verify-defect-free",
        json={"verified_by": "Untrusted Caller"},
    )
    assert negative_res.status_code == 401
