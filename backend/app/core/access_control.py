"""Interim access guard for ground-truth and dataset operations."""

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from backend.app.core.config import settings


def require_ground_truth_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> None:
    """Fail closed unless a configured server-side key matches the request."""
    expected = (settings.GROUND_TRUTH_API_KEY or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ground-truth access is disabled until GROUND_TRUTH_API_KEY is configured.",
        )

    supplied = (x_api_key or "").strip()
    if not supplied or not hmac.compare_digest(
        supplied.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key.",
        )
