"""Unit tests for explainable relevance scoring and license permission gates."""

from backend.app.schemas.acquisition import LicensePermissionStatus
from backend.app.modules.acquisition.relevance import evaluate_relevance
from backend.app.modules.acquisition.license_gate import infer_initial_license_status, can_acquire_candidate


def test_relevance_scoring_direct_borescope_fidelity():
    """Verify direct borescope/videoscope footage receives highest similarity score."""
    rel = evaluate_relevance(
        title="Industrial Turbine Borescope Inspection Video",
        description="Recorded flexible videoscope probe inspection inside jet engine high pressure compressor.",
        target_domain="MECHANICAL",
        modalities=["video", "still_images"],
        annotation_types=["pixel_segmentation_masks"],
        is_direct_videoscope_declared=True
    )

    assert rel.is_direct_videoscope is True
    assert rel.videoscope_similarity == 30.0  # Max similarity score
    assert rel.domain_match >= 15.0
    assert rel.total_score >= 80.0
    assert len(rel.relevance_explanations) >= 4


def test_relevance_scoring_cross_domain_benchtop():
    """Verify flat benchtop surface footage is scored conservatively with cross-domain explanation."""
    rel = evaluate_relevance(
        title="Benchtop Steel Strip Camera Capture",
        description="Fixed laboratory camera looking at flat polished sheet metal.",
        target_domain="MECHANICAL",
        modalities=["still_images"],
        annotation_types=["classification_labels"],
        is_direct_videoscope_declared=False
    )

    assert rel.is_direct_videoscope is False
    assert rel.videoscope_similarity < 15.0
    assert any("Cross-domain" in exp or "External" in exp for exp in rel.relevance_explanations)


def test_license_status_inference_rules():
    """Verify license identifiers map deterministically to legal permission states."""
    # Permissive commercial
    status, comm, attr = infer_initial_license_status("MIT")
    assert status == LicensePermissionStatus.APPROVED_FOR_EVALUATION
    assert comm is True
    assert attr is True

    status, comm, attr = infer_initial_license_status("CC0-1.0")
    assert status == LicensePermissionStatus.APPROVED_FOR_EVALUATION
    assert comm is True
    assert attr is False  # CC0 does not require attribution

    # Non-commercial research
    status, comm, attr = infer_initial_license_status("CC-BY-NC-4.0")
    assert status == LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH
    assert comm is False
    assert attr is True

    # Unknown
    status, comm, attr = infer_initial_license_status("UNKNOWN")
    assert status == LicensePermissionStatus.LICENSE_UNKNOWN
    assert comm is False


def test_can_acquire_candidate_gate_checks():
    """Verify license gate forbids acquisition for unreviewed, restricted, or non-commercial licenses."""
    # Unknown license blocked
    can_acq, reason = can_acquire_candidate(LicensePermissionStatus.LICENSE_UNKNOWN)
    assert can_acq is False
    assert "reviewed and verified" in reason

    # Rejected blocked
    can_acq, reason = can_acquire_candidate(LicensePermissionStatus.REJECTED)
    assert can_acq is False

    # Noncommercial allowed for evaluation, blocked for commercial training
    can_acq, _ = can_acquire_candidate(LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH, "EVALUATION")
    assert can_acq is True

    can_acq, reason = can_acquire_candidate(LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH, "COMMERCIAL_TRAINING")
    assert can_acq is False
    assert "Commercial training forbidden" in reason
