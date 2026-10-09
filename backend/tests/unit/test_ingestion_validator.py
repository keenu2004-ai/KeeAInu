"""Unit tests for media ingestion validator and signature checks."""

import pytest
from backend.app.modules.ingestion.validator import validate_media_file


def test_validate_valid_jpeg():
    # Valid JPEG header \xFF\xD8\xFF
    sample_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01"
    is_valid, error = validate_media_file("probe_frame.jpg", sample_bytes, len(sample_bytes))
    assert is_valid is True
    assert error is None


def test_validate_valid_png():
    # Valid PNG header \x89PNG\r\n\x1a\n
    sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    is_valid, error = validate_media_file("borescope_snapshot.png", sample_bytes, len(sample_bytes))
    assert is_valid is True
    assert error is None


def test_validate_valid_mp4():
    # Valid MP4 container with 'ftyp' box
    sample_bytes = b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00"
    is_valid, error = validate_media_file("inspection_run.mp4", sample_bytes, 1024)
    assert is_valid is True
    assert error is None


def test_reject_empty_file():
    is_valid, error = validate_media_file("empty.mp4", b"", 0)
    assert is_valid is False
    assert "empty" in error.lower()


def test_reject_unsupported_extension():
    sample_bytes = b"\x4D\x5A\x90\x00\x03\x00\x00\x00"  # MZ executable
    is_valid, error = validate_media_file("malicious.exe", sample_bytes, 500)
    assert is_valid is False
    assert "unsupported file extension" in error.lower()


def test_reject_mismatched_magic_bytes():
    # File named .jpg but contains text
    sample_bytes = b"This is not a real jpeg file header"
    is_valid, error = validate_media_file("fake.jpg", sample_bytes, len(sample_bytes))
    assert is_valid is False
    assert "invalid jpeg header" in error.lower()
