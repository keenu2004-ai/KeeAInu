"""License & Permission Gating Module for Multi-Source Dataset Acquisition.

Separates permissions by intended use:
- Metadata discovery
- Download and local storage
- Benchmark evaluation
- Non-commercial research
- Commercial model training
- Redistribution and publication
"""

from typing import Tuple, Optional, Dict, Any
from backend.app.schemas.acquisition import LicensePermissionStatus


KNOWN_COMMERCIAL_LICENSES = {
    "MIT", "APACHE-2.0", "BSD-3-CLAUSE", "BSD-2-CLAUSE", "CC0-1.0",
    "CC-BY-4.0", "CC-BY-3.0", "OPEN-GOVERNMENT-LICENCE", "PUBLIC-DOMAIN"
}

KNOWN_NONCOMMERCIAL_LICENSES = {
    "CC-BY-NC-4.0", "CC-BY-NC-SA-4.0", "CC-BY-NC-ND-4.0", "RESEARCH-ONLY", "ACADEMIC-USE-ONLY"
}


def infer_initial_license_status(
    license_id: Optional[str]
) -> Tuple[LicensePermissionStatus, bool, bool]:
    """
    Deterministically classify license identifier into safe initial permission state,
    commercial usability flag, and attribution requirement.
    """
    if not license_id or license_id.strip() == "" or license_id.upper() in ("UNKNOWN", "NONE", "UNSPECIFIED"):
        return LicensePermissionStatus.LICENSE_UNKNOWN, False, True

    norm = license_id.strip().upper()

    if norm in KNOWN_COMMERCIAL_LICENSES:
        attr_req = not (norm in ("CC0-1.0", "PUBLIC-DOMAIN"))
        return LicensePermissionStatus.APPROVED_FOR_EVALUATION, True, attr_req

    if norm in KNOWN_NONCOMMERCIAL_LICENSES:
        return LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH, False, True

    if "COMMERCIAL" in norm and "RESTRICTED" in norm:
        return LicensePermissionStatus.COMMERCIAL_USE_REVIEW_REQUIRED, False, True

    if "PROPRIETARY" in norm or "CONFIDENTIAL" in norm or "GATED" in norm:
        return LicensePermissionStatus.ACCESS_RESTRICTED, False, True

    return LicensePermissionStatus.LICENSE_UNKNOWN, False, True


def can_discover_metadata(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """Metadata discovery is permitted for all public sources to index candidates."""
    return True, None


def can_download_media(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """Media download requires verified non-restricted status."""
    if license_status in (
        LicensePermissionStatus.REJECTED,
        LicensePermissionStatus.DOWNLOAD_NOT_AUTHORIZED,
        LicensePermissionStatus.ACCESS_RESTRICTED
    ):
        return False, f"Download forbidden: permission state is '{license_status.value}'."

    if license_status == LicensePermissionStatus.LICENSE_UNKNOWN:
        return False, "Download blocked: license terms must be audited and approved first."

    return True, None


def can_use_for_evaluation(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """Evaluation requires approved evaluation or noncommercial research license."""
    if license_status not in (
        LicensePermissionStatus.APPROVED_FOR_EVALUATION,
        LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH
    ):
        return False, f"Evaluation forbidden: current license state '{license_status.value}' is not approved."
    return True, None


def can_use_for_noncommercial_research(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """Research usage allowed for CC-BY, CC-NC, and open public domain data."""
    if license_status in (
        LicensePermissionStatus.APPROVED_FOR_EVALUATION,
        LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH
    ):
        return True, None
    return False, f"Non-commercial research forbidden under license state '{license_status.value}'."


def can_use_for_commercial_training(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """
    Commercial training strictly fails closed. Only licenses explicitly verified
    and cleared for commercial training are authorized.
    """
    if license_status == LicensePermissionStatus.APPROVED_FOR_EVALUATION:
        return True, None
    return False, f"Commercial training forbidden: license state '{license_status.value}' lacks commercial rights."


def can_redistribute(license_status: LicensePermissionStatus) -> Tuple[bool, Optional[str]]:
    """Redistribution rights check."""
    if license_status in (
        LicensePermissionStatus.ACCESS_RESTRICTED,
        LicensePermissionStatus.DOWNLOAD_NOT_AUTHORIZED,
        LicensePermissionStatus.REJECTED,
        LicensePermissionStatus.LICENSE_UNKNOWN,
        LicensePermissionStatus.COMMERCIAL_USE_REVIEW_REQUIRED
    ):
        return False, f"Redistribution blocked for '{license_status.value}'."
    return True, None


def evaluate_all_permissions(license_status: LicensePermissionStatus) -> Dict[str, bool]:
    """Return dictionary of all fine-grained permissions for an asset/candidate."""
    return {
        "discover_metadata": can_discover_metadata(license_status)[0],
        "download_media": can_download_media(license_status)[0],
        "benchmark_evaluation": can_use_for_evaluation(license_status)[0],
        "noncommercial_research": can_use_for_noncommercial_research(license_status)[0],
        "commercial_training": can_use_for_commercial_training(license_status)[0],
        "redistribution": can_redistribute(license_status)[0]
    }


def can_acquire_candidate(
    license_status: LicensePermissionStatus,
    target_usage: str = "EVALUATION"
) -> Tuple[bool, Optional[str]]:
    """
    Verify whether a candidate dataset passes the strict license & permission gate
    before any downloading, ingestion, or copying is permitted.
    """
    # First check basic download rights
    dl_ok, dl_err = can_download_media(license_status)
    if not dl_ok:
        return False, dl_err

    # Check target usage authorization
    if target_usage.upper() == "COMMERCIAL_TRAINING":
        return can_use_for_commercial_training(license_status)

    if target_usage.upper() == "NONCOMMERCIAL_RESEARCH":
        return can_use_for_noncommercial_research(license_status)

    # Default to evaluation
    return can_use_for_evaluation(license_status)
