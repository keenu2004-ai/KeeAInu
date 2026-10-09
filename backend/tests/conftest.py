"""Pytest Configuration and Fixture Bootstrap for KeeAInu Backend Tests."""

import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings
from backend.app.modules.video.fixtures import build_synthetic_corpus


@pytest.fixture(scope="session", autouse=True)
def ensure_synthetic_fixtures():
    """
    Session-level fixture to guarantee deterministic synthetic test corpus exists
    prior to any test suite execution.
    """
    fixtures_dir = settings.DATA_DIR / "sample_fixtures"
    video_file = fixtures_dir / "synthetic_test_video.mp4"
    grid_img = fixtures_dir / "synthetic_still_grid.png"
    pit_img = fixtures_dir / "synthetic_still_pit.jpg"
    manifest_file = fixtures_dir / "manifest.json"

    if not (video_file.exists() and grid_img.exists() and pit_img.exists() and manifest_file.exists()):
        build_synthetic_corpus(fixtures_dir)
