"""License & Permission Gating Module for Multi-Source Dataset Acquisition."""

from typing import Tuple, Optional
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


def can_acquire_candidate(
    license_status: LicensePermissionStatus,
    target_usage: str = "EVALUATION"
) -> Tuple[bool, Optional[str]]:
    """
    Verify whether a candidate dataset passes the strict license & permission gate
    before any downloading, ingestion, or copying is permitted.
    """
    if license_status == LicensePermissionStatus.REJECTED:
        return False, "Acquisition rejected by compliance / legal review."

    if license_status in (LicensePermissionStatus.DOWNLOAD_NOT_AUTHORIZED, LicensePermissionStatus.ACCESS_RESTRICTED):
        return False, f"Acquisition blocked: current permission state is '{license_status.value}'."

    if license_status == LicensePermissionStatus.LICENSE_UNKNOWN:
        return False, "Acquisition blocked: license and usage terms must be reviewed and verified first."

    if target_usage.upper() == "COMMERCIAL_TRAINING":
        if license_status != LicensePermissionStatus.APPROVED_FOR_EVALUATION:
            return False, f"Commercial training forbidden under license state '{license_status.value}'."

    if target_usage.upper() == "EVALUATION":
        if license_status not in (
            LicensePermissionStatus.APPROVED_FOR_EVALUATION,
            LicensePermissionStatus.APPROVED_FOR_NONCOMMERCIAL_RESEARCH
        ):
            return False, f"Evaluation acquisition requires formal review. Current state: '{license_status.value}'."

    return True, None
