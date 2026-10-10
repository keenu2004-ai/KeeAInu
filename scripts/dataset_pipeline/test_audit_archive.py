"""Unit tests for safe ZIP archive auditing."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.dataset_pipeline.audit_archive import audit_archive, safe_member_name


def test_safe_member_name_rejects_traversal_and_absolute_paths():
    assert not safe_member_name("../evil.jpg")
    assert not safe_member_name("folder/../../evil.jpg")
    assert not safe_member_name("/tmp/evil.jpg")
    assert not safe_member_name("C:\\\\evil.jpg")
    assert safe_member_name("train/images/frame.jpg")


def test_audit_counts_images_and_annotation_hints(tmp_path: Path):
    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("train/images/frame1.jpg", b"fake-image-content")
        archive.writestr("train/labels/frame1.txt", "0 0.5 0.5 0.2 0.2")
        archive.writestr("valid/images/frame2.png", b"fake-image-content-2")
        archive.writestr("README.txt", "dataset notes")
    report = audit_archive(
        str(archive_path), "test-dataset", "https://example.org/dataset", "pending"
    )
    assert report["image_candidate_count"] == 2
    assert report["layout_assessment"]["has_txt_files"] is True
    assert report["layout_assessment"]["has_txt_label_candidates"] is True
    assert report["layout_assessment"]["split_directories_detected"] == ["train", "valid"]
    assert report["training_readiness"] == "NOT_ASSESSED"
    assert report["license_review_status"] == "pending"


def test_audit_rejects_path_traversal(tmp_path: Path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.jpg", b"bad")
    try:
        audit_archive(str(archive_path), "unsafe", "https://example.org", "pending")
    except ValueError as exc:
        assert "unsafe paths" in str(exc)
    else:
        raise AssertionError("Expected unsafe archive paths to be rejected")


def test_audit_report_serializes_to_json(tmp_path: Path):
    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("images/frame.jpg", b"x")
    report = audit_archive(str(archive_path), "test", "https://example.org", "pending")
    json.dumps(report)



def test_readme_txt_is_not_misclassified_as_label(tmp_path: Path):
    archive_path = tmp_path / "readme-only.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("images/frame1.jpg", b"fake-image-content")
        archive.writestr("README.txt", "documentation only")
    report = audit_archive(
        str(archive_path), "readme-only", "https://example.org/dataset", "pending"
    )
    layout = report["layout_assessment"]
    assert layout["has_txt_files"] is True
    assert layout["has_txt_label_candidates"] is False
    assert layout["annotation_format_hints"] == ["no-common-annotation-layout-detected"]
