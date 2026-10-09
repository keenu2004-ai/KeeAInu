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


def test_verify_and_resolve_media_file_success():
    from backend.app.core.security import verify_and_resolve_media_file
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        test_file = vault / "sample.png"
        content = b"sample_png_bytes"
        test_file.write_bytes(content)
        digest = calculate_sha256(content)

        record = {"file_path": str(test_file), "sha256_hash": digest}
        resolved = verify_and_resolve_media_file(record, vault)
        assert resolved == test_file.resolve()


def test_verify_and_resolve_media_file_tampered():
    from backend.app.core.security import verify_and_resolve_media_file
    from fastapi import HTTPException
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir)
        test_file = vault / "sample.png"
        test_file.write_bytes(b"sample_png_bytes")

        record = {"file_path": str(test_file), "sha256_hash": "wrong_hash_123"}
        with pytest.raises(HTTPException) as exc_info:
            verify_and_resolve_media_file(record, vault)
        assert exc_info.value.status_code == 409


def test_verify_and_resolve_media_file_missing_and_traversal():
    from backend.app.core.security import verify_and_resolve_media_file
    from fastapi import HTTPException
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir) / "vault"
        vault.mkdir()
        outside = Path(tmpdir) / "outside.txt"
        outside.write_bytes(b"secret")

        # Missing file
        with pytest.raises(HTTPException) as exc_1:
            verify_and_resolve_media_file({"file_path": str(vault / "nonexistent.png"), "sha256_hash": "abc"}, vault)
        assert exc_1.value.status_code == 404

        # Traversal file (outside vault)
        with pytest.raises(HTTPException) as exc_2:
            verify_and_resolve_media_file({"file_path": str(outside), "sha256_hash": calculate_sha256(b"secret")}, vault)
        assert exc_2.value.status_code == 404

