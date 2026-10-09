"""Media Ingestion Validation and Safety Checks (Hardened)."""

from pathlib import Path
from typing import Tuple, Optional
from backend.app.core.config import settings

# Max decompression limits to prevent resource exhaustion / decompression bombs
MAX_IMAGE_PIXELS = 50_000_000  # 50 Megapixels
MAX_IMAGE_DIMENSION = 16_384   # 16K max width or height
MAX_VIDEO_DIMENSION = 8_192    # 8K max width or height


def validate_media_file(
    filename: str,
    file_bytes_sample: bytes,
    file_size_bytes: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a media file is safe to ingest:
    1. Size is within configured non-zero bounds.
    2. Extension is in allowed whitelist.
    3. Header signature (magic bytes) strictly matches the container format.
    """
    if file_size_bytes <= 0:
        return False, "File is empty (0 bytes)."
        
    if file_size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        return False, f"File size ({file_size_bytes} bytes) exceeds limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
        
    suffix = Path(filename).suffix.lower()
    allowed = settings.ALLOWED_VIDEO_EXTENSIONS + settings.ALLOWED_IMAGE_EXTENSIONS
    if suffix not in allowed:
        return False, f"Unsupported file extension '{suffix}'. Allowed: {', '.join(allowed)}"
        
    # Check minimum header length for initial sanity
    if len(file_bytes_sample) < 4:
        return False, "File header too short for format signature validation."

    # --- Image Format Signature Checks ---
    if suffix in [".jpg", ".jpeg"]:
        if not file_bytes_sample.startswith(b"\xFF\xD8\xFF"):
            return False, "Invalid JPEG header signature (expected 0xFFD8FF)."
            
    elif suffix == ".png":
        if not file_bytes_sample.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG header signature (expected 0x89PNG)."
            
    elif suffix == ".bmp":
        if not file_bytes_sample.startswith(b"BM"):
            return False, "Invalid BMP header signature (expected 'BM')."
            
    elif suffix == ".webp":
        if not (file_bytes_sample[:4] == b"RIFF" and file_bytes_sample[8:12] == b"WEBP"):
            return False, "Invalid WEBP header signature (expected RIFF....WEBP)."

    # --- Video Container Format Signature Checks ---
    elif suffix == ".mp4":
        # ISOBMFF box header: 4-byte box size, then box type at offset 4
        box_type = file_bytes_sample[4:8]
        if box_type not in [b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip"] and b"ftyp" not in file_bytes_sample[:64]:
            return False, "Invalid MP4 header signature (expected ISOBMFF box header)."
            
    elif suffix == ".mov":
        # QuickTime / ISO BMFF: ftyp, moov, wide, or mdat box at offset 4
        box_type = file_bytes_sample[4:8]
        if box_type not in [b"ftyp", b"moov", b"wide", b"mdat"]:
            return False, "Invalid MOV/QuickTime container header signature."

    elif suffix == ".avi":
        # RIFF container with 'AVI ' form type at offset 8
        if not (file_bytes_sample[:4] == b"RIFF" and file_bytes_sample[8:12] == b"AVI "):
            return False, "Invalid AVI header signature (expected RIFF....AVI )."

    elif suffix == ".mkv":
        # Matroska / EBML header ID: 0x1A45DFA3 at offset 0
        if not file_bytes_sample.startswith(b"\x1A\x45\xDF\xA3"):
            return False, "Invalid Matroska (MKV) EBML header signature."

    elif suffix == ".wmv":
        # ASF Header Object GUID: 30 26 B2 75 8E 66 CF 11 A6 D9 00 AA 00 62 CE 6C
        asf_guid = b"\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C"
        if not file_bytes_sample.startswith(asf_guid):
            return False, "Invalid WMV/ASF header signature."

    return True, None
