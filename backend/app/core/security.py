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
