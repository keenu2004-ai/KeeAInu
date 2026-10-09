"""Security and Evidence Integrity Utilities."""

import hashlib
from pathlib import Path
from typing import Union


def calculate_sha256(file_path_or_bytes: Union[str, Path, bytes]) -> str:
    """
    Compute a deterministic SHA-256 checksum for evidence preservation.
    Accepts a filepath (reads in chunks) or raw bytes.
    """
    hasher = hashlib.sha256()
    
    if isinstance(file_path_or_bytes, bytes):
        hasher.update(file_path_or_bytes)
        return hasher.hexdigest()
    
    path = Path(file_path_or_bytes)
    if not path.exists():
        raise FileNotFoundError(f"File not found for hash calculation: {path}")
        
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
            
    return hasher.hexdigest()


def is_path_safe(target_path: Union[str, Path], base_directory: Union[str, Path]) -> bool:
    """
    Mitigate path traversal vulnerabilities by verifying that target_path
    strictly resolves inside base_directory.
    """
    try:
        resolved_base = Path(base_directory).resolve()
        resolved_target = Path(target_path).resolve()
        return resolved_base in resolved_target.parents or resolved_base == resolved_target
    except Exception:
        return False


def verify_and_resolve_media_file(
    media_record: dict,
    storage_root: Union[str, Path]
) -> Path:
    """
    Verify and resolve a registered media record against its expected storage root
    and cryptographic SHA-256 digest before consumption.

    Raises:
        HTTPException(404): If the file is missing from vault or path is outside storage_root.
        HTTPException(409): If calculated SHA-256 does not match media_record["sha256_hash"].

    Returns:
        Path: The resolved, verified file path.
    """
    from fastapi import HTTPException, status

    raw_path_str = media_record.get("file_path")
    if not raw_path_str:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media record contains no file path."
        )

    file_path = Path(raw_path_str).resolve()
    if not file_path.exists() or not is_path_safe(file_path, storage_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored media file missing from vault."
        )

    expected_hash = media_record.get("sha256_hash")
    if not expected_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence integrity failure: media record lacks registered SHA-256 digest."
        )

    actual_hash = calculate_sha256(file_path)
    if actual_hash != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence integrity failure: file hash does not match registered evidence digest."
        )

    return file_path

