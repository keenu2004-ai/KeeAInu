"""Media Ingestion, Streaming, and Frame Access API Router (Hardened)."""

import hashlib
import uuid
from pathlib import Path
import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, Response
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256, is_path_safe
from backend.app.db.repository import repo
from backend.app.modules.ingestion.validator import (
    validate_media_file,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_DIMENSION,
    MAX_VIDEO_DIMENSION
)
from backend.app.modules.video.extractor import VideoFrameExtractor
from backend.app.modules.video.thumbnails import generate_video_thumbnails

# Apply decompression limits to PIL
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

router = APIRouter(prefix="/media", tags=["Media Ingestion & Frames"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_media(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Safely ingest a video or image file for an inspection session:
    - Streams to temporary file with bounded memory usage.
    - Computes SHA-256 on the fly.
    - Validates file signatures, size limits, and decoder readability.
    - Atomically stores raw media in the immutable Media Vault.
    - Cleans up artifacts on failure.
    - Generates timeline thumbnails for video media.
    """
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection session '{session_id}' not found."
        )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")

    suffix = Path(file.filename).suffix.lower()
    media_id = f"med_{uuid.uuid4().hex[:12]}"
    raw_vault_dir = settings.RAW_MEDIA_DIR
    raw_vault_dir.mkdir(parents=True, exist_ok=True)
    
    # Write to a secure temp file first
    temp_file = raw_vault_dir / f"tmp_{media_id}{suffix}"
    target_file = raw_vault_dir / f"{media_id}{suffix}"
    hasher = hashlib.sha256()
    total_bytes = 0
    header_sample = bytearray()
    moved_to_target = False

    try:
        with open(temp_file, "wb") as f_out:
            while chunk := await file.read(65536):
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes."
                    )
                if len(header_sample) < 64:
                    header_sample.extend(chunk[: 64 - len(header_sample)])
                hasher.update(chunk)
                f_out.write(chunk)

        # Validate file size and magic signatures
        is_valid, err_msg = validate_media_file(file.filename, bytes(header_sample), total_bytes)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

        sha256_hash = hasher.hexdigest()
        
        # Atomically rename temp file to permanent vault destination
        temp_file.replace(target_file)
        moved_to_target = True

        # Inspect media properties & decoder readability
        width, height, duration_sec, fps, total_frames = 0, 0, 0.0, 0.0, 1
        is_readable = False
        media_type = "application/octet-stream"

        if suffix in settings.ALLOWED_IMAGE_EXTENSIONS:
            media_type = f"image/{suffix.replace('.', '').replace('jpg', 'jpeg')}"
            try:
                with Image.open(target_file) as img:
                    img.verify()  # Integrity check on container
                # Re-open after verify to read dimensions safely
                with Image.open(target_file) as img:
                    width, height = img.size
                    if width <= 0 or height <= 0:
                        raise ValueError("Invalid image dimensions (0x0).")
                    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                        raise ValueError(f"Image dimension ({width}x{height}) exceeds maximum limit.")
                    if (width * height) > MAX_IMAGE_PIXELS:
                        raise ValueError(f"Image pixel count exceeds maximum allowed limit.")
                    is_readable = True
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image decoding failed: {str(e)}"
                )
        elif suffix in settings.ALLOWED_VIDEO_EXTENSIONS:
            media_type = "video/mp4" if suffix == ".mp4" else f"video/{suffix.replace('.', '')}"
            try:
                with VideoFrameExtractor(target_file) as extractor:
                    meta = extractor.get_metadata()
                    if not meta.is_readable or meta.total_frames <= 0 or meta.fps <= 0:
                        raise ValueError("Video container is unreadable, corrupt, or contains no decodable frames.")
                    if meta.width > MAX_VIDEO_DIMENSION or meta.height > MAX_VIDEO_DIMENSION:
                        raise ValueError(f"Video resolution ({meta.width}x{meta.height}) exceeds maximum limit.")
                    
                    width, height = meta.width, meta.height
                    duration_sec = meta.duration_seconds
                    fps = meta.fps
                    total_frames = meta.total_frames
                    is_readable = True
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Video container inspection failed: {str(e)}"
                )

        # Persist record in repository
        record = repo.create_media(
            media_id=media_id,
            session_id=session_id,
            filename=file.filename,
            file_path=str(target_file),
            media_type=media_type,
            sha256_hash=sha256_hash,
            width=width,
            height=height,
            duration_seconds=duration_sec,
            fps=fps,
            total_frames=total_frames,
            is_readable=is_readable
        )

        # Auto-generate thumbnails for video
        if suffix in settings.ALLOWED_VIDEO_EXTENSIONS and is_readable:
            try:
                generate_video_thumbnails(media_id, target_file, max_thumbnails=10)
            except Exception:
                pass  # Non-fatal for initial upload

        return record

    except HTTPException:
        # Atomic cleanup on failure
        if temp_file.exists():
            temp_file.unlink()
        if moved_to_target and target_file.exists():
            target_file.unlink()
        raise
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        if moved_to_target and target_file.exists():
            target_file.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media ingestion error: {str(e)}"
        )


@router.get("/{media_id}")
async def get_media_metadata(media_id: str):
    """Retrieve verified media metadata and cryptographic checksum."""
    media = repo.get_media(media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media '{media_id}' not found."
        )
    return media


@router.get("/{media_id}/content")
async def get_media_content(media_id: str):
    """
    Serve the original raw media file for local playback.
    Enforces on-demand SHA-256 evidence integrity check before serving.
    """
    media = repo.get_media(media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Media '{media_id}' not found.")

    file_path = Path(media["file_path"]).resolve()
    if not file_path.exists() or not is_path_safe(file_path, settings.RAW_MEDIA_DIR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored media file missing from vault.")

    # Cryptographic integrity check
    current_hash = calculate_sha256(file_path)
    if current_hash != media["sha256_hash"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence integrity failure: file hash does not match registered evidence digest."
        )

    return FileResponse(
        path=file_path,
        media_type=media["media_type"],
        filename=media["filename"]
    )


@router.get("/{media_id}/thumbnails")
async def list_media_thumbnails(media_id: str):
    """List available timeline preview thumbnails for a media item."""
    media = repo.get_media(media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Media '{media_id}' not found.")
    return repo.list_thumbnails(media_id)


@router.get("/{media_id}/thumbnails/{thumb_id}/content")
async def get_thumbnail_content(media_id: str, thumb_id: str):
    """Serve an individual thumbnail JPEG image."""
    thumb = repo.get_thumbnail(thumb_id)
    if not thumb or thumb["media_id"] != media_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found.")

    thumb_path = Path(thumb["file_path"]).resolve()
    if not thumb_path.exists() or not is_path_safe(thumb_path, settings.DERIVED_MEDIA_DIR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file unavailable.")

    return FileResponse(path=thumb_path, media_type="image/jpeg")


@router.get("/{media_id}/frames/{frame_index}")
async def get_extracted_frame(media_id: str, frame_index: int):
    """Extract and return a specific video frame as an image."""
    if frame_index < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Frame index must be non-negative.")

    media = repo.get_media(media_id)
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Media '{media_id}' not found.")

    file_path = Path(media["file_path"]).resolve()
    if not file_path.exists() or not is_path_safe(file_path, settings.RAW_MEDIA_DIR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source media missing from vault.")

    if not media["media_type"].startswith("video/"):
        # For still images, serve the image directly on frame_index 0
        if frame_index != 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Still images only have frame index 0.")
        return FileResponse(path=file_path, media_type=media["media_type"])

    try:
        with VideoFrameExtractor(file_path) as extractor:
            frame_bgr, frame_meta = extractor.extract_frame(frame_index)
            # Encode frame to JPEG bytes
            success, encoded_jpg = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not success:
                raise RuntimeError("Frame encoding failed.")
            return Response(
                content=encoded_jpg.tobytes(),
                media_type="image/jpeg",
                headers={
                    "X-Frame-Index": str(frame_meta.frame_index),
                    "X-Timestamp-Ms": str(frame_meta.timestamp_ms),
                    "X-Frame-Width": str(frame_meta.width),
                    "X-Frame-Height": str(frame_meta.height),
                }
            )
    except IndexError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
