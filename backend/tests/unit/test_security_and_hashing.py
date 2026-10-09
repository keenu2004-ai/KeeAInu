"""Unit tests for SHA-256 evidence hashing and path safety checks."""

import tempfile
from pathlib import Path
import pytest
from backend.app.core.security import calculate_sha256, is_path_safe


def test_calculate_sha256_from_bytes():
    data = b"videoscope_frame_sample_12345"
    expected_hash = "f3f081442db4e08c9a3aea28e3535adf68ca47e22551c94457eba077833623d2"
    assert calculate_sha256(data) == expected_hash


def test_calculate_sha256_from_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"videoscope_frame_sample_12345")
        tmp_path = Path(tmp.name)
        
    try:
        expected_hash = "f3f081442db4e08c9a3aea28e3535adf68ca47e22551c94457eba077833623d2"
        assert calculate_sha256(tmp_path) == expected_hash
    finally:
        tmp_path.unlink()


def test_is_path_safe():
    base_dir = Path("/sandbox/vault").resolve()
    safe_child = Path("/sandbox/vault/media/video.mp4").resolve()
    unsafe_parent = Path("/sandbox/secrets.json").resolve()
    traversal_attempt = Path("/sandbox/vault/../../etc/passwd").resolve()
    
    assert is_path_safe(safe_child, base_dir) is True
    assert is_path_safe(unsafe_parent, base_dir) is False
    assert is_path_safe(traversal_attempt, base_dir) is False
