"""Unit tests for the synthetic inspection fixtures and generator."""

import json
from pathlib import Path
import tempfile
import pytest

from backend.app.modules.video.fixtures import (
    generate_synthetic_image,
    generate_synthetic_video,
    build_synthetic_corpus
)
from backend.app.schemas.annotation import GroundTruthDatasetRecord


def test_generate_synthetic_images():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        grid_img, grid_hash = generate_synthetic_image(tmp_path / "test_grid.png", 320, 240, "grid")
        pit_img, pit_hash = generate_synthetic_image(tmp_path / "test_pit.jpg", 320, 240, "pit")
        
        assert grid_img.exists()
        assert pit_img.exists()
        assert len(grid_hash) == 64
        assert len(pit_hash) == 64
        assert grid_img.stat().st_size > 0
        assert pit_img.stat().st_size > 0


def test_generate_synthetic_video_and_annotations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        vid_path, vid_hash, dataset = generate_synthetic_video(
            tmp_path / "test_video.mp4",
            width=320,
            height=240,
            fps=30.0,
            num_frames=30
        )
        
        assert vid_path.exists()
        assert len(vid_hash) == 64
        assert vid_path.stat().st_size > 0
        assert isinstance(dataset, GroundTruthDatasetRecord)
        assert dataset.image_width == 320
        assert dataset.image_height == 240
        assert dataset.is_synthetic is True
        # Synthetic defect pattern was generated on frames 10..20 (11 frames)
        assert len(dataset.annotations) == 11
        for ann in dataset.annotations:
            assert ann.defect_class == "TEST_PATTERN_CRACK_SYNTHETIC"
            assert 10 <= ann.frame_index <= 20


def test_build_synthetic_corpus():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        manifest = build_synthetic_corpus(tmp_path)
        
        assert manifest["is_synthetic"] is True
        assert len(manifest["items"]) == 3
        manifest_file = tmp_path / "manifest.json"
        assert manifest_file.exists()
        
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["items"]) == 3
