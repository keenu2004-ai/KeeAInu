"""Video Frame Extraction and Metadata Module."""

from pathlib import Path
from typing import Optional, Tuple, Generator, Union
import cv2
import numpy as np
from pydantic import BaseModel, Field


class FrameMetadata(BaseModel):
    """Metadata for an individual extracted video frame."""
    frame_index: int = Field(..., ge=0)
    timestamp_ms: float = Field(..., ge=0.0)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)


class VideoMetadata(BaseModel):
    """Container metadata extracted from a video source."""
    filename: str
    width: int = Field(..., ge=0)
    height: int = Field(..., ge=0)
    fps: float = Field(..., ge=0.0)
    total_frames: int = Field(..., ge=0)
    duration_seconds: float = Field(..., ge=0.0)
    fourcc: str
    is_readable: bool


class VideoFrameExtractor:
    """
    Robust, frame-accurate video frame extractor.
    Operates in read-only mode and guarantees decoder cleanup.
    """

    def __init__(self, video_path: Union[str, Path]):
        self.video_path = Path(video_path).resolve()
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
        if self.video_path.stat().st_size == 0:
            raise ValueError(f"Video file is empty (0 bytes): {self.video_path}")

        self._cap: Optional[cv2.VideoCapture] = None
        self._metadata: Optional[VideoMetadata] = None

    def __enter__(self) -> "VideoFrameExtractor":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """Open the video capture stream if not already opened."""
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(str(self.video_path))
            if not self._cap.isOpened():
                raise RuntimeError(f"Failed to open video decoder for: {self.video_path}")

    def close(self):
        """Safely release video capture decoder resources."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def get_metadata(self) -> VideoMetadata:
        """
        Extract container metadata from the video stream.
        """
        if self._metadata is not None:
            return self._metadata

        self.open()
        assert self._cap is not None

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_int = int(self._cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

        # If decoder properties failed to report dimensions or frame count, attempt probing
        if width <= 0 or height <= 0 or total_frames <= 0:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, test_frame = self._cap.read()
            if ret and test_frame is not None:
                h, w = test_frame.shape[:2]
                if width <= 0:
                    width = w
                if height <= 0:
                    height = h
                if total_frames <= 0:
                    # Count frames by sequential read
                    frame_count = 1
                    while True:
                        r, _ = self._cap.read()
                        if not r:
                            break
                        frame_count += 1
                    total_frames = frame_count
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        if width <= 0 or height <= 0 or total_frames <= 0:
            duration = 0.0
            is_readable = False
        else:
            duration = (total_frames / fps) if fps > 0.0 else 0.0
            is_readable = True

        self._metadata = VideoMetadata(
            filename=self.video_path.name,
            width=width,
            height=height,
            fps=round(fps, 2) if fps > 0 else 0.0,
            total_frames=total_frames if total_frames > 0 else 0,
            duration_seconds=round(duration, 3),
            fourcc=fourcc_str,
            is_readable=is_readable
        )
        return self._metadata

    def calculate_timestamp_ms(self, frame_index: int, fps: float) -> float:
        """
        Compute timestamp in milliseconds based on nominal CFR policy.
        """
        if fps <= 0:
            return 0.0
        return round((frame_index / fps) * 1000.0, 2)

    def extract_frame(self, frame_index: int) -> Tuple[np.ndarray, FrameMetadata]:
        """
        Extract a single frame by index.
        Returns the BGR numpy array and frame metadata.
        """
        if frame_index < 0:
            raise IndexError(f"Frame index {frame_index} out of bounds (must be non-negative).")

        meta = self.get_metadata()
        if not meta.is_readable:
            raise RuntimeError(f"Cannot extract frames: video is unreadable or has invalid metadata ({self.video_path.name})")

        if meta.total_frames > 0 and frame_index >= meta.total_frames:
            raise IndexError(
                f"Frame index {frame_index} out of bounds for video with {meta.total_frames} frames."
            )

        self.open()
        assert self._cap is not None

        try:
            # Set frame position
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = self._cap.read()
            
            # Fallback to sequential read if seek returned empty frame (common in OpenCV Linux ffmpeg backend)
            if not ret or frame is None:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                curr = 0
                while curr <= frame_index:
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        break
                    if curr == frame_index:
                        break
                    curr += 1

            if not ret or frame is None:
                raise RuntimeError(f"Decoder failed to read frame at index {frame_index}")

            h, w = frame.shape[:2]
            timestamp_ms = self.calculate_timestamp_ms(frame_index, meta.fps)

            frame_meta = FrameMetadata(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                width=w,
                height=h
            )
            return frame, frame_meta
        except Exception:
            raise

    def iter_frames(
        self,
        start_frame: int = 0,
        max_frames: Optional[int] = None
    ) -> Generator[Tuple[np.ndarray, FrameMetadata], None, None]:
        """
        Iterate over frames sequentially without loading the entire video into RAM.
        """
        if start_frame < 0:
            raise ValueError(f"start_frame must be non-negative, got {start_frame}")
        if max_frames is not None and max_frames < 0:
            raise ValueError(f"max_frames must be non-negative, got {max_frames}")

        meta = self.get_metadata()
        if not meta.is_readable:
            raise RuntimeError(f"Cannot iterate frames: video is unreadable ({self.video_path.name})")

        self.open()
        assert self._cap is not None
        
        if start_frame > 0:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        current_idx = start_frame
        yielded_count = 0

        while True:
            if max_frames is not None and yielded_count >= max_frames:
                break
            if meta.total_frames > 0 and current_idx >= meta.total_frames:
                break

            ret, frame = self._cap.read()
            if not ret or frame is None:
                break

            h, w = frame.shape[:2]
            ts = self.calculate_timestamp_ms(current_idx, meta.fps)
            frame_meta = FrameMetadata(
                frame_index=current_idx,
                timestamp_ms=ts,
                width=w,
                height=h
            )
            yield frame, frame_meta

            current_idx += 1
            yielded_count += 1
