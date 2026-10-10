"""Tests for the fail-closed local dataset training gate."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.dataset_pipeline.training_gate import assess_training_gate


def good_inputs():
    audit = {
        "dataset_id": "borescope",
        "source_url": "https://example.org/borescope",
        "archive_sha256": "a" * 64,
    }
    manifest = {
        "dataset_id": "borescope",
        "dataset_version": "release-2026-01",
        "source_url": audit["source_url"],
        "archive_sha256": audit["archive_sha256"],
        "license_id": "CC-BY-4.0",
        "intended_use": "commercial-training",
        "license_review_status": "approved-for-commercial-use",
        "attribution": "Dataset title, creator, source URL, license link.",
        "reviewer": "authorized reviewer",
        "reviewed_at": "2026-10-10",
        "annotation_review_status": "approved",
        "class_mapping_review_status": "approved",
        "split_review_status": "approved",
        "target_task": "object-detection",
        "class_names": ["corrosion", "crack"],
    }
    validation = {
        "task": "yolo-object-detection",
        "readiness": "STRUCTURAL_CHECKS_PASSED_REVIEW_STILL_REQUIRED",
        "missing_label_count": 0,
        "unpaired_label_count": 0,
        "label_error_count": 0,
        "cross_split_exact_duplicate_count": 0,
    }
    return audit, manifest, validation


def test_fully_reviewed_dataset_passes_checklist_not_production_certification():
    audit, manifest, validation = good_inputs()
    report = assess_training_gate(audit, manifest, validation)
    assert report["gate_status"] == "CHECKLIST_PASSED_REQUIRES_INDEPENDENT_SIGNOFF"
    assert report["checks_passed"] == report["checks_total"]
    assert any("not a guarantee" in item for item in report["limitations"])


def test_pending_license_blocks_commercial_training():
    audit, manifest, validation = good_inputs()
    manifest["license_review_status"] = "pending_human_review"
    report = assess_training_gate(audit, manifest, validation)
    assert report["gate_status"] == "BLOCKED"
    assert "rights_approved_for_intended_use" in {
        check["name"] for check in report["checks"] if not check["passed"]
    }


def test_evaluation_approval_does_not_authorize_commercial_training():
    audit, manifest, validation = good_inputs()
    manifest["license_review_status"] = "approved-for-evaluation"
    report = assess_training_gate(audit, manifest, validation)
    assert report["gate_status"] == "BLOCKED"


def test_mismatched_archive_hash_blocks_gate():
    audit, manifest, validation = good_inputs()
    manifest["archive_sha256"] = "b" * 64
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"


def test_unpinned_dataset_version_blocks_gate():
    audit, manifest, validation = good_inputs()
    manifest["dataset_version"] = "latest"
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"


def test_unreviewed_annotations_block_gate():
    audit, manifest, validation = good_inputs()
    manifest["annotation_review_status"] = "pending"
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"


def test_cross_split_duplicates_block_gate():
    audit, manifest, validation = good_inputs()
    validation["cross_split_exact_duplicate_count"] = 2
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"


def test_segmentation_cannot_pass_detection_validator_gate():
    audit, manifest, validation = good_inputs()
    manifest["target_task"] = "instance-segmentation"
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"


def test_unknown_intended_use_blocks_gate():
    audit, manifest, validation = good_inputs()
    manifest["intended_use"] = "anything"
    assert assess_training_gate(audit, manifest, validation)["gate_status"] == "BLOCKED"
