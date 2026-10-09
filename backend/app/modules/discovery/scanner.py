"""Dataset Discovery Scanner: Autonomous Footage Inventory, Sampling & Profiling."""

import os
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import cv2
import numpy as np
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256, is_path_safe
from backend.app.db.repository import repo
from backend.app.modules.ingestion.validator import (
    validate_media_file,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    MAX_VIDEO_DIMENSION
)
from backend.app.modules.video.extractor import VideoFrameExtractor
from backend.app.modules.discovery.profiler import (
    compute_frame_quality_metrics,
    build_quality_profile,
    generate_contact_sheet
)


def is_synthetic_fixture_path(file_path: Path) -> bool:
    """
    Determine if a file is a trusted synthetic test fixture based on directory provenance,
    never based on substring guessing in the filename.
    """
    fixture_dir = (settings.DATA_DIR / "sample_fixtures").resolve()
    try:
        file_path.resolve().relative_to(fixture_dir)
        return True
    except ValueError:
        return False


def _determine_sample_indices(total_frames: int, requested_count: int) -> List[int]:
    """Calculate evenly spaced representative frame indices across video duration."""
    if total_frames <= 0:
        return [0]
    if total_frames == 1 or requested_count <= 1:
        return [0]
    if total_frames <= requested_count:
        return list(range(total_frames))

    # Evenly spaced sampling from start (frame 0) to end (total_frames - 1)
    indices = []
    step = (total_frames - 1) / (requested_count - 1)
    for i in range(requested_count):
        idx = int(round(i * step))
        if idx >= total_frames:
            idx = total_frames - 1
        if idx not in indices:
            indices.append(idx)
    return indices


def scan_and_profile_file(
    file_path: Path,
    sample_count: int = 5,
    force_rescan: bool = False,
    source_root: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Profile a single video or image file, extract representative samples,
    and persist into the dataset inventory.
    """
    resolved_path = file_path.resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {resolved_path}")

    # Boundary check: ensure path is inside application base and permitted source root
    if not is_path_safe(resolved_path, settings.BASE_DIR):
        raise ValueError(f"Target file '{resolved_path}' escapes application boundary.")
    if source_root and not is_path_safe(resolved_path, source_root.resolve()):
        raise ValueError(f"Target file '{resolved_path}' escapes permitted source root '{source_root}'.")

    # Initial Bounded SHA-256 calculation before reading/extracting
    initial_sha256 = calculate_sha256(resolved_path)
    file_size = resolved_path.stat().st_size
    filename = resolved_path.name
    suffix = resolved_path.suffix.lower()
    asset_id = f"ast_{initial_sha256[:12]}"

    # Check if already scanned and not force_rescan
    existing = repo.get_asset(asset_id)
    if existing and not force_rescan:
        return existing

    if existing and force_rescan:
        repo.delete_samples_for_asset(asset_id)

    # Check provenance strictly by directory location
    is_synth = is_synthetic_fixture_path(resolved_path)

    asset_type = "video" if suffix in settings.ALLOWED_VIDEO_EXTENSIONS else "image"

    # Read header sample for magic bytes validation
    with open(resolved_path, "rb") as f:
        header_sample = f.read(64)

    is_valid, err_msg = validate_media_file(filename, header_sample, file_size)
    if not is_valid:
        return repo.upsert_asset(
            asset_id=asset_id,
            source_path=str(resolved_path),
            filename=filename,
            asset_type=asset_type,
            extension=suffix,
            file_size_bytes=file_size,
            sha256_hash=initial_sha256,
            is_readable=False,
            width=0,
            height=0,
            duration_seconds=0.0,
            fps=0.0,
            total_frames=0,
            is_synthetic=is_synth,
            validation_status="MALFORMED",
            error_details=err_msg
        )

    # Ensure output derived directories exist
    settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    settings.CONTACT_SHEETS_DIR.mkdir(parents=True, exist_ok=True)

    extracted_frames_bgr: List[np.ndarray] = []
    extracted_frame_indices: List[int] = []
    sample_records: List[Dict[str, Any]] = []

    width, height, duration_sec, fps, total_frames = 0, 0, 0.0, 0.0, 1
    is_readable = False
    validation_status = "VALID"
    error_details = None

    if asset_type == "image":
        try:
            with Image.open(resolved_path) as img:
                img.verify()
            with Image.open(resolved_path) as img:
                width, height = img.size
                if width <= 0 or height <= 0 or width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    raise ValueError(f"Image dimensions ({width}x{height}) invalid or out of bounds.")
                if (width * height) > MAX_IMAGE_PIXELS:
                    raise ValueError("Image exceeds maximum allowed pixel count.")

            # Load image using OpenCV for sample extraction
            frame_bgr = cv2.imread(str(resolved_path))
            if frame_bgr is None:
                raise ValueError("Decoder failed to decode image frame.")

            is_readable = True
            extracted_frames_bgr.append(frame_bgr)
            extracted_frame_indices.append(0)

            # Save sample frame
            sample_id = f"smp_{uuid.uuid4().hex[:12]}"
            sample_dest = settings.SAMPLES_DIR / f"{asset_id}_f00.jpg"
            write_ok = cv2.imwrite(str(sample_dest), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not write_ok or not sample_dest.exists() or sample_dest.stat().st_size == 0:
                raise RuntimeError(f"Failed to write sample frame to {sample_dest}")

            sample_hash = calculate_sha256(sample_dest)
            q_metrics = compute_frame_quality_metrics(frame_bgr)
            sample_rec = repo.create_sample(
                sample_id=sample_id,
                asset_id=asset_id,
                frame_index=0,
                timestamp_ms=0.0,
                timestamp_provenance="EXACT",
                file_path=str(sample_dest),
                sha256_hash=sample_hash,
                width=width,
                height=height,
                sharpness_score=q_metrics["sharpness"],
                brightness_score=q_metrics["brightness_mean"],
                contrast_score=q_metrics["contrast_std"]
            )
            sample_records.append(sample_rec)

        except Exception as e:
            is_readable = False
            validation_status = "UNREADABLE"
            error_details = f"Image inspection error: {str(e)}"

    elif asset_type == "video":
        try:
            with VideoFrameExtractor(resolved_path) as extractor:
                meta = extractor.get_metadata()
                if not meta.is_readable or meta.total_frames <= 0:
                    raise ValueError(f"Video stream is unreadable or contains 0 frames ({resolved_path.name}).")
                if meta.width > MAX_VIDEO_DIMENSION or meta.height > MAX_VIDEO_DIMENSION:
                    raise ValueError(f"Video resolution ({meta.width}x{meta.height}) exceeds max limits.")

                width, height = meta.width, meta.height
                duration_sec = meta.duration_seconds
                fps = meta.fps
                total_frames = meta.total_frames
                is_readable = True

                indices = _determine_sample_indices(total_frames, sample_count)
                for f_idx in indices:
                    frame_bgr, f_meta = extractor.extract_frame(f_idx)
                    extracted_frames_bgr.append(frame_bgr)
                    extracted_frame_indices.append(f_idx)

                    # Save sample frame JPEG
                    sample_id = f"smp_{uuid.uuid4().hex[:12]}"
                    sample_dest = settings.SAMPLES_DIR / f"{asset_id}_f{f_idx:04d}.jpg"
                    write_ok = cv2.imwrite(str(sample_dest), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    if not write_ok or not sample_dest.exists() or sample_dest.stat().st_size == 0:
                        raise RuntimeError(f"Failed to write video sample frame to {sample_dest}")

                    sample_hash = calculate_sha256(sample_dest)
                    q_metrics = compute_frame_quality_metrics(frame_bgr)
                    sample_rec = repo.create_sample(
                        sample_id=sample_id,
                        asset_id=asset_id,
                        frame_index=f_idx,
                        timestamp_ms=f_meta.timestamp_ms,
                        timestamp_provenance="NOMINAL_APPROXIMATE" if fps > 0.0 else "UNAVAILABLE",
                        file_path=str(sample_dest),
                        sha256_hash=sample_hash,
                        width=width,
                        height=height,
                        sharpness_score=q_metrics["sharpness"],
                        brightness_score=q_metrics["brightness_mean"],
                        contrast_score=q_metrics["contrast_std"]
                    )
                    sample_records.append(sample_rec)

        except Exception as e:
            is_readable = False
            validation_status = "UNREADABLE"
            error_details = f"Video inspection error: {str(e)}"

    # Post-scan evidence integrity check: ensure original file was never mutated
    post_sha256 = calculate_sha256(resolved_path)
    if post_sha256 != initial_sha256:
        raise RuntimeError(
            f"Evidence integrity violation: source media file '{filename}' was modified during discovery processing."
        )

    # Generate contact sheet and quality profile if readable
    contact_sheet_path = None
    quality_profile_dict = None

    if is_readable and extracted_frames_bgr:
        try:
            cs_dest = settings.CONTACT_SHEETS_DIR / f"{asset_id}_contact.jpg"
            generate_contact_sheet(extracted_frames_bgr, extracted_frame_indices, cs_dest)
            if cs_dest.exists() and cs_dest.stat().st_size > 0:
                contact_sheet_path = str(cs_dest)
        except Exception:
            pass

        q_profile = build_quality_profile(
            extracted_frames_bgr,
            width=width,
            height=height,
            is_readable=is_readable,
            fps=fps,
            total_frames=total_frames
        )
        quality_profile_dict = q_profile.model_dump()

    return repo.upsert_asset(
        asset_id=asset_id,
        source_path=str(resolved_path),
        filename=filename,
        asset_type=asset_type,
        extension=suffix,
        file_size_bytes=file_size,
        sha256_hash=initial_sha256,
        is_readable=is_readable,
        width=width,
        height=height,
        duration_seconds=duration_sec,
        fps=fps,
        total_frames=total_frames,
        is_synthetic=is_synth,
        validation_status=validation_status,
        error_details=error_details,
        contact_sheet_path=contact_sheet_path,
        quality_profile_dict=quality_profile_dict
    )


def scan_source_directories(
    custom_dir: Optional[Path] = None,
    sample_count_per_video: int = 5,
    force_rescan: bool = False
) -> List[Dict[str, Any]]:
    """
    Scan all configured footage directories for videoscope media.
    """
    dirs_to_scan: List[Path] = []
    
    if custom_dir:
        resolved_custom = custom_dir.resolve()
        if not is_path_safe(resolved_custom, settings.BASE_DIR):
            raise ValueError(f"Custom directory '{custom_dir}' escapes base application boundary.")
        if not resolved_custom.exists():
            raise FileNotFoundError(f"Custom directory '{custom_dir}' does not exist.")
        if not resolved_custom.is_dir():
            raise ValueError(f"Custom path '{custom_dir}' is not a directory.")
        dirs_to_scan.append(resolved_custom)
    else:
        # Default directories for footage discovery: Source Footage & Sample Fixtures
        for default_dir in [settings.SOURCE_FOOTAGE_DIR, settings.DATA_DIR / "sample_fixtures"]:
            if default_dir.exists() and default_dir.is_dir():
                dirs_to_scan.append(default_dir.resolve())

    allowed_exts = set(settings.ALLOWED_IMAGE_EXTENSIONS + settings.ALLOWED_VIDEO_EXTENSIONS)
    discovered_files: List[Tuple[Path, Path]] = []

    for d in dirs_to_scan:
        if not is_path_safe(d, settings.BASE_DIR):
            continue
        for root, dirs, files in os.walk(d, followlinks=False):
            current_root = Path(root).resolve()
            if not is_path_safe(current_root, d):
                continue
            for fname in files:
                p = Path(root) / fname
                resolved_p = p.resolve()
                # Ensure resolved file path is inside root d (guards against symlink escapes)
                if not is_path_safe(resolved_p, d) or not is_path_safe(resolved_p, settings.BASE_DIR):
                    continue
                if p.suffix.lower() in allowed_exts and not fname.startswith("."):
                    discovered_files.append((resolved_p, d))

    results = []
    for fpath, root_dir in discovered_files:
        try:
            asset = scan_and_profile_file(
                fpath,
                sample_count=sample_count_per_video,
                force_rescan=force_rescan,
                source_root=root_dir
            )
            results.append(asset)
        except Exception as e:
            # Non-fatal per-file error logging
            print(f"Failed to scan {fpath}: {e}")

    return results
