"""Tests for the local YOLO detection dataset validator."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.dataset_pipeline.validate_yolo_dataset import validate_dataset

def make_pair(root: Path, split: str, stem: str, label: str, image_bytes: bytes | None = None):
    image_dir = root / split / "images"
    label_dir = root / split / "labels"
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / f"{stem}.jpg").write_bytes(image_bytes if image_bytes is not None else f"fake-{stem}".encode())
    (label_dir / f"{stem}.txt").write_text(label, encoding="utf-8")

def test_valid_yolo_detection_layout(tmp_path: Path):
    make_pair(tmp_path, "train", "a", "0 0.5 0.5 0.2 0.3\n")
    make_pair(tmp_path, "valid", "b", "1 0.4 0.4 0.1 0.1\n")
    report = validate_dataset(tmp_path, class_count=2)
    assert report["image_count"] == 2
    assert report["missing_label_count"] == 0
    assert report["label_error_count"] == 0
    assert report["detection_row_count"] == 2
    assert report["split_image_counts"] == {"train": 1, "valid": 1}

def test_out_of_range_box_and_class_are_reported(tmp_path: Path):
    make_pair(tmp_path, "train", "a", "4 1.4 0.5 -0.2 0.1\n")
    report = validate_dataset(tmp_path, class_count=2)
    messages = [item["error"] for item in report["label_errors"]]
    assert any("class_id_out_of_range" in message for message in messages)
    assert any("coordinate_out_of_range" in message for message in messages)
    assert any("non_positive_box_size" in message for message in messages)

def test_missing_and_unpaired_labels_are_reported(tmp_path: Path):
    image_dir = tmp_path / "train" / "images"
    image_dir.mkdir(parents=True)
    (image_dir / "no_label.jpg").write_bytes(b"image")
    labels_dir = tmp_path / "train" / "labels"
    labels_dir.mkdir(parents=True)
    (labels_dir / "orphan.txt").write_text("0 0.5 0.5 0.2 0.2", encoding="utf-8")
    report = validate_dataset(tmp_path)
    assert report["missing_label_count"] == 1
    assert report["unpaired_label_count"] == 1

def test_exact_duplicates_across_splits_are_flagged(tmp_path: Path):
    same = b"same-image-bytes"
    make_pair(tmp_path, "train", "a", "0 0.5 0.5 0.2 0.2", same)
    make_pair(tmp_path, "test", "b", "0 0.5 0.5 0.2 0.2", same)
    report = validate_dataset(tmp_path)
    assert report["exact_duplicate_image_group_count"] == 1
    assert report["cross_split_exact_duplicate_count"] == 1
    assert report["readiness"] == "REVIEW_REQUIRED"

def test_segmentation_polygon_rows_are_not_silently_accepted(tmp_path: Path):
    make_pair(tmp_path, "train", "a", "0 0.1 0.2 0.3 0.4 0.5 0.6")
    report = validate_dataset(tmp_path)
    assert report["label_error_count"] == 1
    assert "expected_5_values" in report["label_errors"][0]["error"]


def test_readme_text_is_not_counted_as_orphan_label(tmp_path: Path):
    make_pair(tmp_path, "train", "a", "0 0.5 0.5 0.2 0.2")
    (tmp_path / "README.txt").write_text("dataset notes", encoding="utf-8")
    report = validate_dataset(tmp_path)
    assert report["unpaired_label_count"] == 0
