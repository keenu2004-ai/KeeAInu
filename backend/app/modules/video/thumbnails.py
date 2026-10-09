"""Thumbnail Generation and Derived Media Workflow (Hardened)."""

import uuid
from pathlib import Path
from typing import List, Dict, Any
import cv2

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256
from backend.app.db.repository import repo
from backend.app.modules.video.extractor import VideoFrameExtractor


def generate_video_thumbnails(
    media_id: str,
    video_path: Path,
    max_thumbnails: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate bounded timeline preview thumbnails for a recorded video.
    Stores thumbnails in derived media storage and registers them in the repository.
    Verifies write success before returning records.
    """
    # Check if already generated
    existing = repo.list_thumbnails(media_id)
    if existing:
        return existing

    out_dir = settings.THUMBNAILS_DIR / media_id
    out_dir.mkdir(parents=True, exist_ok=True)

    generated = []

    with VideoFrameExtractor(video_path) as extractor:
        meta = extractor.get_metadata()
        if not meta.is_readable or meta.total_frames <= 0:
            return []

        total_frames = meta.total_frames
        count = min(max_thumbnails, total_frames)
        
        # Calculate evenly spaced frame indices
        if count == 1:
            frame_indices = [0]
        else:
            step = (total_frames - 1) / (count - 1)
            frame_indices = [int(round(i * step)) for i in range(count)]

        for idx in frame_indices:
            frame, frame_meta = extractor.extract_frame(idx)
            
            # Downscale thumbnail to width 160px
            thumb_w = 160
            h, w = frame.shape[:2]
            thumb_h = int(round(h * (thumb_w / float(w))))
            resized = cv2.resize(frame, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)

            thumb_id = f"thumb_{uuid.uuid4().hex[:12]}"
            thumb_file = out_dir / f"{thumb_id}.jpg"
            
            # Encode and save with return value check
            write_ok = cv2.imwrite(str(thumb_file), resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not write_ok or not thumb_file.exists():
                raise IOError(f"Failed to write thumbnail artifact to disk: {thumb_file.name}")

            thumb_hash = calculate_sha256(thumb_file)

            record = repo.add_thumbnail(
                thumb_id=thumb_id,
                media_id=media_id,
                frame_index=idx,
                timestamp_ms=frame_meta.timestamp_ms,
                file_path=str(thumb_file),
                sha256_hash=thumb_hash
            )
            generated.append(record)

    return generated
