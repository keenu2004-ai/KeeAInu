"""Media Ingestion Validation and Safety Checks."""

from pathlib import Path
from typing import Tuple, Optional
from backend.app.core.config import settings


# Magic byte signatures for authorized media formats
MAGIC_SIGNATURES = {
    # Images
    "jpeg": [b"\xFF\xD8\xFF"],
    "png": [b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"],
    "bmp": [b"\x42\x4D"],
    "webp": [b"\x52\x49\x46\x46"],  # RIFF....WEBP
    # Videos
    "mp4": [b"\x66\x74\x79\x70"],  # 'ftyp' box offset at byte 4
    "mkv": [b"\x1A\x45\xDF\xA3"],  # Matroska header
    "avi": [b"\x52\x49\x46\x46"],  # RIFF....AVI
}


def validate_media_file(
    filename: str,
    file_bytes_sample: bytes,
    file_size_bytes: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a media file is safe to ingest:
    1. Size within allowed bounds.
    2. Extension is allowed.
    3. File header matches expected magic bytes.
    """
    if file_size_bytes <= 0:
        return False, "File is empty."
        
    if file_size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        return False, f"File size ({file_size_bytes} bytes) exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
        
    suffix = Path(filename).suffix.lower()
    allowed = settings.ALLOWED_VIDEO_EXTENSIONS + settings.ALLOWED_IMAGE_EXTENSIONS
    if suffix not in allowed:
        return False, f"Unsupported file extension '{suffix}'. Allowed: {', '.join(allowed)}"
        
    # Check magic bytes
    if len(file_bytes_sample) < 12:
        return False, "File header too short for validation."

    # Validate signature based on extension
    if suffix in [".jpg", ".jpeg"]:
        if not file_bytes_sample.startswith(b"\xFF\xD8\xFF"):
            return False, "Invalid JPEG header signature."
    elif suffix == ".png":
        if not file_bytes_sample.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG header signature."
    elif suffix == ".bmp":
        if not file_bytes_sample.startswith(b"BM"):
            return False, "Invalid BMP header signature."
    elif suffix == ".mkv":
        if not file_bytes_sample.startswith(b"\x1A\x45\xDF\xA3"):
            return False, "Invalid Matroska/MKV header signature."
    elif suffix == ".mp4":
        # MP4 standard: ftyp box appears at byte offset 4
        if b"ftyp" not in file_bytes_sample[:16]:
            return False, "Invalid MP4/ISOBMFF container header signature."
            
    return True, None
