"""Unit tests for Network Safety and SSRF prevention layer."""

import pytest
from backend.app.modules.acquisition.network_safety import validate_url_safe


def test_reject_localhost_and_loopback():
    """Verify SSRF validator blocks localhost and 127.0.0.1 attempts."""
    for bad_url in [
        "http://localhost:8000/api/v1/sessions",
        "http://127.0.0.1:5000/secret",
        "http://127.0.0.2:80",
        "https://localhost.localdomain/data"
    ]:
        is_safe, err = validate_url_safe(bad_url)
        assert is_safe is False
        assert "strictly prohibited" in err or "blocked IP" in err or "Could not resolve" in err


def test_reject_cloud_metadata_link_local():
    """Verify SSRF validator blocks AWS/GCP link-local metadata endpoints."""
    bad_url = "http://169.254.169.254/latest/meta-data/"
    is_safe, err = validate_url_safe(bad_url)
    assert is_safe is False
    assert "blocked IP" in err or "prohibited" in err


def test_reject_unsupported_schemes():
    """Verify non-HTTP/HTTPS schemes are blocked."""
    for bad_url in [
        "file:///etc/passwd",
        "ftp://mirror.example.com/data.tar.gz",
        "gopher://evil.com"
    ]:
        is_safe, err = validate_url_safe(bad_url)
        assert is_safe is False
        assert "Unsupported URL scheme" in err
