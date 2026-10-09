#!/usr/bin/env python3
"""Validate an extracted YOLO object-detection dataset without modifying it.

Expected layout: train/images + train/labels, valid/images + valid/labels,
and optionally test/images + test/labels. Segmentation polygon rows are rejected.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
SPLIT_NAMES = {"train", "valid", "val", "test"}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def parse_detection_label(path: Path, class_count: int | None) -> list[str]:
    errors = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [f"cannot_read_label:{type(exc).__name__}"]
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 5:
            errors.append(f"line_{line_number}:expected_5_values_got_{len(parts)}")
            continue
        try:
            class_value = float(parts[0])
            coords = [float(value) for value in parts[1:]]
        except ValueError:
            errors.append(f"line_{line_number}:non_numeric_value")
            continue
        if not math.isfinite(class_value) or not class_value.is_integer() or class_value < 0:
            errors.append(f"line_{line_number}:invalid_class_id")
        elif class_count is not None and class_value >= class_count:
            errors.append(f"line_{line_number}:class_id_out_of_range")
        if not all(math.isfinite(value) for value in coords):
            errors.append(f"line_{line_number}:non_finite_coordinate")
        elif any(value < 0 or value > 1 for value in coords):
            errors.append(f"line_{line_number}:coordinate_out_of_range")
        elif coords[2] <= 0 or coords[3] <= 0:
            errors.append(f"line_{line_number}:non_positive_box_size")
    return errors

def infer_split(path: Path, root: Path) -> str:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return "unspecified"
    for part in parts:
        p = part.lower()
        if p in {"val", "valid", "validation"}:
            return "valid"
        if p in SPLIT_NAMES:
            return p
    return "unspecified"

def validate_dataset(root: Path, class_count: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Dataset root is not a directory: {root}")
    images = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
    if not images:
        raise ValueError("No supported image files found under dataset root.")
    # Only treat text files inside conventional labels directories as label candidates;\n    # dataset READMEs and other documentation must not be counted as orphan labels.\n    label_files = sorted(p for p in root.rglob("*.txt") if p.is_file() and p.parent.name.lower() == "labels")
    labels_by_parent_stem: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for label in label_files:
        labels_by_parent_stem[(label.parent.resolve(), label.stem)].append(label)

    errors, missing_labels, records = [], [], []
    label_paths_seen = set()
    duplicate_hashes: dict[str, list[str]] = defaultdict(list)
    hash_splits: dict[str, set[str]] = defaultdict(set)
    class_ids, box_count, empty_labels = set(), 0, 0

    for image in images:
        split = infer_split(image, root)
        label_path = None
        for ancestor in image.parents:
            if ancestor.name.lower() == "images":
                matches = labels_by_parent_stem.get(((ancestor.parent / "labels").resolve(), image.stem), [])
                if matches:
                    label_path = matches[0]
                break
        if label_path is None:
            fallback = root / "labels" / image.relative_to(root)
            fallback = fallback.with_suffix(".txt")
            if fallback.is_file():
                label_path = fallback
        rel_image = image.relative_to(root).as_posix()
        if label_path is None:
            missing_labels.append(rel_image)
        else:
            label_paths_seen.add(label_path.resolve())
            for message in parse_detection_label(label_path, class_count):
                errors.append({"image": rel_image, "label": label_path.relative_to(root).as_posix(), "error": message})
            try:
                label_text = label_path.read_text(encoding="utf-8")
                if not label_text.strip():
                    empty_labels += 1
                for line in label_text.splitlines():
                    parts = line.split()
                    if len(parts) == 5:
                        try:
                            class_value = float(parts[0])
                            if class_value.is_integer() and class_value >= 0:
                                class_ids.add(int(class_value))
                                box_count += 1
                        except ValueError:
                            pass
            except (OSError, UnicodeError):
                pass
        digest = sha256_file(image)
        duplicate_hashes[digest].append(rel_image)
        hash_splits[digest].add(split)
        records.append({"path": rel_image, "split": split, "sha256": digest, "label_found": label_path is not None})

    duplicates = [paths for paths in duplicate_hashes.values() if len(paths) > 1]
    cross_split = [
        {"sha256": digest, "paths": paths, "splits": sorted(hash_splits[digest])}
        for digest, paths in duplicate_hashes.items()
        if len(paths) > 1 and len(hash_splits[digest]) > 1
    ]
    unpaired = [p.relative_to(root).as_posix() for p in label_files if p.resolve() not in label_paths_seen]
    split_counts = Counter(r["split"] for r in records)
    has_issues = bool(errors or missing_labels or unpaired or cross_split)
    return {
        "schema_version": 1, "dataset_root": str(root), "task": "yolo-object-detection",
        "class_count_constraint": class_count, "image_count": len(images), "label_file_count": len(label_files),
        "split_image_counts": dict(sorted(split_counts.items())),
        "missing_label_count": len(missing_labels), "missing_label_images": missing_labels,
        "unpaired_label_count": len(unpaired), "unpaired_labels": unpaired,
        "empty_label_count": empty_labels, "detection_row_count": box_count,
        "class_ids_observed": sorted(class_ids), "label_error_count": len(errors), "label_errors": errors,
        "exact_duplicate_image_group_count": len(duplicates), "exact_duplicate_image_groups": duplicates,
        "cross_split_exact_duplicate_count": len(cross_split), "cross_split_exact_duplicates": cross_split,
        "images": records,
        "readiness": "REVIEW_REQUIRED" if has_issues else "STRUCTURAL_CHECKS_PASSED_REVIEW_STILL_REQUIRED",
        "limitations": [
            "Checks pairing and YOLO detection label structure only; it does not verify visual correctness.",
            "Detects exact SHA-256 duplicates, not perceptual or near-duplicates.",
            "Split membership is inferred from directory names; unspecified splits require manual review.",
            "Not for segmentation polygon exports or classification-only datasets.",
            "Structural pass does not imply license approval or production readiness."
        ]
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Path to extracted dataset directory.")
    parser.add_argument("--class-count", type=int, default=None, help="Optional expected number of classes.")
    parser.add_argument("--output", required=True, help="Path to write JSON report.")
    args = parser.parse_args()
    if args.class_count is not None and args.class_count < 1:
        parser.error("--class-count must be positive.")
    try:
        report = validate_dataset(Path(args.root), args.class_count)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": "VALIDATION_COMPLETED", "report": str(output),
            "image_count": report["image_count"], "label_error_count": report["label_error_count"],
            "missing_label_count": report["missing_label_count"],
            "cross_split_exact_duplicate_count": report["cross_split_exact_duplicate_count"],
            "readiness": report["readiness"]}, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
