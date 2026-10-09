"""CLI Script to generate deterministic synthetic test fixtures for KeeAInu."""

import sys
from pathlib import Path

# Add workspace root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.modules.video.fixtures import build_synthetic_corpus


def main():
    target_dir = Path(__file__).resolve().parent.parent / "data" / "sample_fixtures"
    print(f"Generating deterministic synthetic test corpus in: {target_dir}")
    manifest = build_synthetic_corpus(target_dir)
    print(f"Corpus generated successfully! Items: {len(manifest['items'])}")
    for item in manifest["items"]:
        print(f" - {item['filename']} (SHA256: {item['sha256'][:12]}...)")


if __name__ == "__main__":
    main()
