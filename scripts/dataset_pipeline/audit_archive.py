#!/usr/bin/env python3
"""Audit a downloaded dataset ZIP without extracting or modifying the archive.

Produces a provenance-aware inventory and flags common annotation layouts.
This script intentionally makes no license decision and performs no model training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
LABEL_EXTENSIONS = {".txt", ".xml", ".json", ".yaml", ".yml", ".csv", ".poly"}
DEFAULT_MAX_FILES = 100_000
DEFAULT_MAX_EXPANDED_BYTES = 20 * 1024**3


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def safe_member_name(name: str) -> bool:
    """Reject absolute paths, Windows drive paths, and traversal segments."""
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        return False
    return all(part not in ("..", "") for part in PurePosixPath(normalized).parts if part != ".")


def classify_layout(names: list[str]) -> dict[str, Any]:
    lowered = [n.lower() for n in names]
    dirs = {PurePosixPath(n).parent.as_posix().lower() for n in lowered}
    has_images = any(PurePosixPath(n).suffix in IMAGE_EXTENSIONS for n in lowered)
    has_txt_labels = any(PurePosixPath(n).suffix == ".txt" for n in lowered)
    has_xml_labels = any(PurePosixPath(n).suffix == ".xml" for n in lowered)
    has_json = any(PurePosixPath(n).suffix == ".json" for n in lowered)
    has_masks = any(
        ("mask" in PurePosixPath(n).parts or "masks" in PurePosixPath(n).parts
         or "segmentation" in PurePosixPath(n).parts)
        for n in lowered
    )
    split_dirs = sorted(
        split for split in ("train", "valid", "val", "test")
        if any(re.search(rf"(^|/){split}(/|$)", d) for d in dirs)
    )
    task_hints = []
    if has_txt_labels or has_xml_labels:
        task_hints.append("object-detection-or-classification-labels-possible")
    if has_json:
        task_hints.append("json-annotation-or-metadata-present")
    if has_masks:
        task_hints.append("mask-like-paths-present")
    if not task_hints:
        task_hints.append("no-common-sidecar-annotation-format-detected")
    return {
        "has_images": has_images,
        "has_txt_labels": has_txt_labels,
        "has_xml_labels": has_xml_labels,
        "has_json_files": has_json,
        "has_mask_like_paths": has_masks,
        "split_directories_detected": split_dirs,
        "annotation_format_hints": task_hints,
        "warning": "File presence and folder names do not validate annotation content or correctness."
    }


def audit_archive(
    archive_path: str,
    dataset_id: str,
    source_url: str,
    license_review_status: str,
    max_files: int = DEFAULT_MAX_FILES,
    max_expanded_bytes: int = DEFAULT_MAX_EXPANDED_BYTES,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > max_files:
            raise ValueError(f"Archive contains {len(infos)} entries; limit is {max_files}.")
        unsafe = [i.filename for i in infos if not safe_member_name(i.filename)]
        encrypted = [i.filename for i in infos if i.flag_bits & 0x1]
        expanded = sum(i.file_size for i in infos if not i.is_dir())
        if unsafe:
            raise ValueError(f"Archive contains unsafe paths (first 5): {unsafe[:5]}")
        if encrypted:
            raise ValueError(f"Encrypted archive members are not supported (first 5): {encrypted[:5]}")
        if expanded > max_expanded_bytes:
            raise ValueError(
                f"Expanded content size {expanded} bytes exceeds limit {max_expanded_bytes}."
            )

        files = [i for i in infos if not i.is_dir()]
        image_members = [i for i in files if PurePosixPath(i.filename.lower()).suffix in IMAGE_EXTENSIONS]
        non_images = [i for i in files if i not in image_members]
        suffix_counts = Counter(PurePosixPath(i.filename.lower()).suffix or "[no extension]" for i in files)
        # Hash the list of file names/sizes rather than opening every file here; the
        # archive hash authenticates the source artifact and full file checksum can
        # be added during a later, bounded extraction stage.
        inventory = [
            {
                "path": i.filename,
                "size_bytes": i.file_size,
                "crc32": f"{i.CRC:08x}",
                "compressed_size_bytes": i.compress_size,
                "is_image_candidate": PurePosixPath(i.filename.lower()).suffix in IMAGE_EXTENSIONS,
                "is_label_or_metadata_candidate": PurePosixPath(i.filename.lower()).suffix in LABEL_EXTENSIONS
            }
            for i in files
        ]

    result: dict[str, Any] = {
        "schema_version": 1,
        "audit_created_at": started,
        "dataset_id": dataset_id,
        "source_url": source_url,
        "archive_path": archive_path,
        "archive_sha256": sha256_file(archive_path),
        "license_review_status": license_review_status,
        "license_note": "This status is operator-supplied; this script does not verify licenses or authorize use.",
        "archive_entry_count": len(infos),
        "file_count": len(files),
        "image_candidate_count": len(image_members),
        "expanded_size_bytes": expanded,
        "file_extension_counts": dict(sorted(suffix_counts.items())),
        "layout_assessment": classify_layout([i.filename for i in files]),
        "files": inventory,
        "training_readiness": "NOT_ASSESSED",
        "next_review_steps": [
            "Check the license and terms at the publisher page for this exact dataset release.",
            "Review several image-label pairs manually and verify annotation schema.",
            "Check for duplicates and near-duplicates before splitting.",
            "Separate train/validation/test by source inspection or sequence, not random adjacent frames.",
            "Do not train until label correctness, rights, and task mapping are approved."
        ]
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Path to a downloaded .zip archive.")
    parser.add_argument("--dataset-id", required=True, help="Stable local dataset identifier.")
    parser.add_argument("--source-url", required=True, help="Canonical publisher landing-page URL.")
    parser.add_argument(
        "--license-review-status",
        choices=["pending", "approved-for-evaluation", "approved-for-noncommercial-research",
                 "commercial-use-review-required", "approved-for-commercial-use", "rejected"],
        default="pending",
        help="Human-reviewed status. Default is pending; this is recorded, not independently verified."
    )
    parser.add_argument("--output", required=True, help="Directory for the JSON audit report.")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-expanded-gb", type=float, default=20.0)
    args = parser.parse_args()

    if args.max_files < 1 or args.max_expanded_gb <= 0:
        parser.error("--max-files and --max-expanded-gb must be positive.")

    try:
        report = audit_archive(
            archive_path=args.archive,
            dataset_id=args.dataset_id,
            source_url=args.source_url,
            license_review_status=args.license_review_status,
            max_files=args.max_files,
            max_expanded_bytes=int(args.max_expanded_gb * 1024**3),
        )
        from pathlib import Path
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "dataset_audit.json"
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({
            "status": "AUDIT_COMPLETED",
            "report": str(output_path),
            "dataset_id": args.dataset_id,
            "image_candidate_count": report["image_candidate_count"],
            "license_review_status": report["license_review_status"],
            "training_readiness": report["training_readiness"]
        }, indent=2))
        return 0
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        print(f"AUDIT_FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
