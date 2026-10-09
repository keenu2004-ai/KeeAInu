"""Unit tests for VideoFrameExtractor and metadata handling."""

from pathlib import Path
import tempfile
import pytest
import numpy as np

from backend.app.modules.video.extractor import VideoFrameExtractor, VideoMetadata, FrameMetadata
from backend.app.modules.video.fixtures import generate_synthetic_video


@pytest.fixture(scope="module")
def sample_video_path(tmp_path_factory):
    fn = tmp_path_factory.mktemp("video_fixtures")
    video_path, _, _ = generate_synthetic_video(
        fn / "test_sample.mp4",
        width=320,
        height=240,
        fps=30.0,
        num_frames=30
    )
    return video_path


def test_video_metadata_extraction(sample_video_path):
    with VideoFrameExtractor(sample_video_path) as extractor:
        meta = extractor.get_metadata()
        assert isinstance(meta, VideoMetadata)
        assert meta.width == 320
        assert meta.height == 240
        assert meta.fps == 30.0
        assert meta.total_frames == 30
        assert meta.duration_seconds == 1.0
        assert meta.is_readable is True


def test_extract_specific_frames(sample_video_path):
    with VideoFrameExtractor(sample_video_path) as extractor:
        # First frame
        frame_0, meta_0 = extractor.extract_frame(0)
        assert isinstance(frame_0, np.ndarray)
        assert frame_0.shape == (240, 320, 3)
        assert meta_0.frame_index == 0
        assert meta_0.timestamp_ms == 0.0

        # Mid frame (15)
        frame_15, meta_15 = extractor.extract_frame(15)
        assert meta_15.frame_index == 15
        assert meta_15.timestamp_ms == 500.0  # 15 / 30 * 1000 = 500ms

        # Last frame (29)
        frame_29, meta_29 = extractor.extract_frame(29)
        assert meta_29.frame_index == 29
        assert meta_29.timestamp_ms == round((29 / 30.0) * 1000.0, 2)


def test_iter_frames_sequential(sample_video_path):
    with VideoFrameExtractor(sample_video_path) as extractor:
        frames = list(extractor.iter_frames(start_frame=0, max_frames=5))
        assert len(frames) == 5
        for i, (frame, meta) in enumerate(frames):
            assert meta.frame_index == i
            assert frame.shape == (240, 320, 3)


def test_extract_out_of_bounds_frame(sample_video_path):
    with VideoFrameExtractor(sample_video_path) as extractor:
        with pytest.raises(IndexError) as exc:
            extractor.extract_frame(999)
        assert "out of bounds" in str(exc.value).lower()

        with pytest.raises(IndexError) as exc:
            extractor.extract_frame(-1)
        assert "out of bounds" in str(exc.value).lower()


def test_handle_missing_video_file():
    with pytest.raises(FileNotFoundError):
        VideoFrameExtractor(Path("/non/existent/video.mp4"))


def test_handle_empty_video_file():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with pytest.raises(ValueError) as exc:
            VideoFrameExtractor(tmp_path)
        assert "empty" in str(exc.value).lower()
    finally:
        tmp_path.unlink()
