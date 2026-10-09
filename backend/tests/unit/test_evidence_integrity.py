"""Unit tests for evidence immutability and storage sandboxing."""

from pathlib import Path
import pytest

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256, is_path_safe
from backend.app.modules.video.extractor import VideoFrameExtractor


def test_original_video_remains_unmodified_during_extraction():
    video_path = (settings.DATA_DIR / "sample_fixtures" / "synthetic_test_video.mp4").resolve()
    assert video_path.exists(), "Sample fixture video must exist"

    # Compute digest prior to extraction
    hash_before = calculate_sha256(video_path)

    # Perform multiple extractions and iterations
    with VideoFrameExtractor(video_path) as extractor:
        meta = extractor.get_metadata()
        frame_0, _ = extractor.extract_frame(0)
        frame_mid, _ = extractor.extract_frame(15)
        _ = list(extractor.iter_frames(start_frame=0, max_frames=10))

    # Compute digest post extraction
    hash_after = calculate_sha256(video_path)

    # Non-negotiable requirement: source evidence is strictly immutable
    assert hash_before == hash_after, "Original video media was mutated during read!"


def test_storage_path_sandboxing_rules():
    base_vault = settings.RAW_MEDIA_DIR.resolve()
    
    valid_incoming_path = base_vault / "2026-10-09" / "session_123.mp4"
    assert is_path_safe(valid_incoming_path, base_vault) is True

    # Path traversal attack vectors
    traversal_1 = base_vault / ".." / ".." / "system32" / "cmd.exe"
    traversal_2 = base_vault / ".." / "app" / "core" / "config.py"
    traversal_3 = Path("C:/Windows/System32/drivers/etc/hosts")

    assert is_path_safe(traversal_1, base_vault) is False
    assert is_path_safe(traversal_2, base_vault) is False
    assert is_path_safe(traversal_3, base_vault) is False
