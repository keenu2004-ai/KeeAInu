"""Pytest Configuration and Fixture Bootstrap for KeeAInu Backend Tests."""

import atexit
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure repo root is on sys.path.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings

# Redirect all writable application data before test modules import the app.
# This is deliberately done at conftest import time to protect against
# database initialization and other side effects during test collection.
_PATH_SETTING_NAMES = (
    "BASE_DIR",
    "DATA_DIR",
    "RAW_MEDIA_DIR",
    "DERIVED_MEDIA_DIR",
    "THUMBNAILS_DIR",
    "SAMPLES_DIR",
    "CONTACT_SHEETS_DIR",
    "SOURCE_FOOTAGE_DIR",
    "ARTIFACTS_DIR",
    "DB_DIR",
    "DB_PATH",
)

_ORIGINAL_PATH_SETTINGS = {
    name: getattr(settings, name) for name in _PATH_SETTING_NAMES
}
_ORIGINAL_GROUND_TRUTH_API_KEY = settings.GROUND_TRUTH_API_KEY
settings.GROUND_TRUTH_API_KEY = "test-only-ground-truth-key"

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="keeainu-pytest-")).resolve()
atexit.register(shutil.rmtree, _TEST_ROOT, ignore_errors=True)

_TEST_DATA_DIR = _TEST_ROOT / "data"
_TEST_PATHS = {
    "BASE_DIR": _TEST_ROOT,
    "DATA_DIR": _TEST_DATA_DIR,
    "RAW_MEDIA_DIR": _TEST_DATA_DIR / "media" / "raw",
    "DERIVED_MEDIA_DIR": _TEST_DATA_DIR / "media" / "derived",
    "THUMBNAILS_DIR": _TEST_DATA_DIR / "media" / "derived" / "thumbnails",
    "SAMPLES_DIR": _TEST_DATA_DIR / "media" / "derived" / "samples",
    "CONTACT_SHEETS_DIR": _TEST_DATA_DIR / "media" / "derived" / "contact_sheets",
    "SOURCE_FOOTAGE_DIR": _TEST_DATA_DIR / "source_footage",
    "ARTIFACTS_DIR": _TEST_DATA_DIR / "artifacts",
    "DB_DIR": _TEST_DATA_DIR / "db",
    "DB_PATH": _TEST_DATA_DIR / "db" / "keeainu.sqlite",
}

for name, path in _TEST_PATHS.items():
    setattr(settings, name, path)
    if name != "DB_PATH":
        path.mkdir(parents=True, exist_ok=True)

from backend.app.modules.video.fixtures import build_synthetic_corpus


@pytest.fixture(scope="session", autouse=True)
def isolate_test_database():
    """Use a temporary database and restore application settings after testing."""
    from backend.app.db.repository import repo

    repo.db_path = settings.DB_PATH
    repo._init_db()

    try:
        yield settings.DB_PATH
    finally:
        repo.db_path = _ORIGINAL_PATH_SETTINGS["DB_PATH"]
        for name, value in _ORIGINAL_PATH_SETTINGS.items():
            setattr(settings, name, value)
        settings.GROUND_TRUTH_API_KEY = _ORIGINAL_GROUND_TRUTH_API_KEY
        shutil.rmtree(_TEST_ROOT, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def ensure_synthetic_fixtures(isolate_test_database):
    """Build any missing synthetic fixtures inside the temporary test directory."""
    fixtures_dir = settings.DATA_DIR / "sample_fixtures"
    video_file = fixtures_dir / "synthetic_test_video.mp4"
    grid_img = fixtures_dir / "synthetic_still_grid.png"
    pit_img = fixtures_dir / "synthetic_still_pit.jpg"
    manifest_file = fixtures_dir / "manifest.json"

    if not all(path.exists() for path in (video_file, grid_img, pit_img, manifest_file)):
        build_synthetic_corpus(fixtures_dir)
