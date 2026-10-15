"""Unit tests for KeeAInu Dataset Exporter and Split Leakage Prevention."""

from pathlib import Path
import pytest
import numpy as np
import cv2

from backend.app.modules.evaluation.exporter import (
    DatasetExporter,
    ExportItem,
    DatasetExportError,
    DatasetOverwriteError,
    EmptyDatasetExportError,
    SplitLeakageError,
    InvalidAnnotationError
)
from backend.app.core.security import calculate_sha256
from backend.app.core.config import settings


@pytest.fixture
def dataset_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Use a temporary approved dataset vault for exporter tests."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(settings, "DATA_DIR", data_dir)
    return data_dir / "datasets"


@pytest.fixture
def dummy_images_dir(tmp_path: Path):
    """Creates dummy images for testing."""
    img_dir = tmp_path / "dummy_images"
    img_dir.mkdir()

    paths = {}
    for name in ["asset1_frame0.jpg", "asset1_frame1.jpg", "asset2_frame0.jpg", "asset3_frame0.jpg", "neg_asset4.jpg"]:
        p = img_dir / name
        # Create small test image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:, :] = (len(name) * 10) % 255
        cv2.imwrite(str(p), img)
        paths[name] = p

    return paths


def test_yolo_coordinate_conversion_and_export(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """Verifies that YOLO coordinate conversion, labels, data.yaml, and manifest are created accurately."""
    p1 = dummy_images_dir["asset1_frame0.jpg"]
    sha1 = calculate_sha256(p1.read_bytes())

    item = ExportItem(
        item_id="item_01",
        group_id="asset_01",
        source_path=p1,
        media_filename="asset1_frame0.jpg",
        evidence_sha256=sha1,
        width=100,
        height=100,
        is_negative=False,
        annotations=[
            {
                "defect_class": "CRACK",
                "bbox": {"x_min": 0.2, "y_min": 0.3, "x_max": 0.6, "y_max": 0.7}
            }
        ]
    )

    exporter = DatasetExporter()
    out_dir = dataset_root / "export_v1"

    # Mock collect_verified_items to return our item
    exporter.collect_verified_items = lambda **kw: [item]

    manifest = exporter.export_yolo(
        version="v1",
        output_dir=out_dir,
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
        overwrite=True
    )

    assert manifest["total_images"] == 1
    assert manifest["total_annotations"] == 1
    assert "CRACK" in manifest["class_mapping"]
    assert (out_dir / "data.yaml").exists()
    assert (out_dir / "manifest.json").exists()

    lbl_file = out_dir / "labels" / "train" / "item_01.txt"
    assert lbl_file.exists()
    content = lbl_file.read_text().strip()
    parts = content.split()
    assert len(parts) == 5
    # class_id is 0
    assert parts[0] == "0"
    # xc = (0.2 + 0.6) / 2 = 0.4
    assert pytest.approx(float(parts[1]), 0.001) == 0.4
    # yc = (0.3 + 0.7) / 2 = 0.5
    assert pytest.approx(float(parts[2]), 0.001) == 0.5
    # w = 0.6 - 0.2 = 0.4
    assert pytest.approx(float(parts[3]), 0.001) == 0.4
    # h = 0.7 - 0.3 = 0.4
    assert pytest.approx(float(parts[4]), 0.001) == 0.4


def test_defect_free_negative_sample_generates_empty_txt(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """Verified defect-free negative samples must generate an empty 0-byte .txt label file."""
    p_neg = dummy_images_dir["neg_asset4.jpg"]
    sha_neg = calculate_sha256(p_neg.read_bytes())

    neg_item = ExportItem(
        item_id="neg_item_01",
        group_id="asset_04",
        source_path=p_neg,
        media_filename="neg_asset4.jpg",
        evidence_sha256=sha_neg,
        width=100,
        height=100,
        is_negative=True,
        annotations=[]
    )

    exporter = DatasetExporter()
    out_dir = dataset_root / "export_neg"
    exporter.collect_verified_items = lambda **kw: [neg_item]

    manifest = exporter.export_yolo(
        version="v_neg",
        output_dir=out_dir,
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
        overwrite=True
    )

    assert manifest["negative_images"] == 1
    assert manifest["positive_images"] == 0
    lbl_file = out_dir / "labels" / "train" / "neg_item_01.txt"
    assert lbl_file.exists()
    assert lbl_file.read_text().strip() == ""


def test_split_leakage_prevention_by_group(tmp_path: Path, dummy_images_dir):
    """Frames belonging to the same physical asset group must never be split across train and val."""
    p1 = dummy_images_dir["asset1_frame0.jpg"]
    p2 = dummy_images_dir["asset1_frame1.jpg"]
    p3 = dummy_images_dir["asset2_frame0.jpg"]
    p4 = dummy_images_dir["asset3_frame0.jpg"]

    items = [
        ExportItem("it1", "asset_A", p1, "f1.jpg", "sha_A1", 100, 100, False, [{"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}}]),
        ExportItem("it2", "asset_A", p2, "f2.jpg", "sha_A2", 100, 100, False, [{"defect_class": "CRACK", "bbox": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.6, "y_max": 0.6}}]),
        ExportItem("it3", "asset_B", p3, "f3.jpg", "sha_B1", 100, 100, False, [{"defect_class": "CORROSION", "bbox": {"x_min": 0.3, "y_min": 0.3, "x_max": 0.7, "y_max": 0.7}}]),
        ExportItem("it4", "asset_C", p4, "f4.jpg", "sha_C1", 100, 100, False, [{"defect_class": "PITTING", "bbox": {"x_min": 0.4, "y_min": 0.4, "x_max": 0.8, "y_max": 0.8}}]),
    ]

    exporter = DatasetExporter()
    splits = exporter.partition_items(items, train_ratio=0.5, val_ratio=0.5, test_ratio=0.0, random_seed=42)

    train_groups = {it.group_id for it in splits["train"]}
    val_groups = {it.group_id for it in splits["val"]}

    # Crucial assertion: asset_A frames (it1 and it2) must stay in the same split!
    it1_split = "train" if any(it.item_id == "it1" for it in splits["train"]) else "val"
    it2_split = "train" if any(it.item_id == "it2" for it in splits["train"]) else "val"
    assert it1_split == it2_split

    # No group overlap between train and val
    assert len(train_groups & val_groups) == 0


def test_split_leakage_duplicate_content_hash(tmp_path: Path, dummy_images_dir):
    """Images with identical SHA-256 hashes must be forced into the same split to prevent duplicate content leakage."""
    p1 = dummy_images_dir["asset1_frame0.jpg"]
    p2 = dummy_images_dir["asset2_frame0.jpg"]
    p3 = dummy_images_dir["asset3_frame0.jpg"]

    # it1 and it2 have different group names but IDENTICAL evidence SHA-256
    shared_hash = "identical_sha256_hash_12345"
    items = [
        ExportItem("it1", "group_X", p1, "f1.jpg", shared_hash, 100, 100, False, [{"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}}]),
        ExportItem("it2", "group_Y", p2, "f2.jpg", shared_hash, 100, 100, False, [{"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}}]),
        ExportItem("it3", "group_Z", p3, "f3.jpg", "unique_sha_67890", 100, 100, False, [{"defect_class": "CORROSION", "bbox": {"x_min": 0.2, "y_min": 0.2, "x_max": 0.6, "y_max": 0.6}}]),
    ]

    exporter = DatasetExporter()
    splits = exporter.partition_items(items, train_ratio=0.5, val_ratio=0.5, test_ratio=0.0, random_seed=42)

    it1_split = "train" if any(it.item_id == "it1" for it in splits["train"]) else "val"
    it2_split = "train" if any(it.item_id == "it2" for it in splits["train"]) else "val"
    assert it1_split == it2_split


def test_overwrite_protection(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """Exporting to an existing directory without overwrite=True must raise DatasetOverwriteError."""
    p1 = dummy_images_dir["asset1_frame0.jpg"]
    out_dir = dataset_root / "protected_version"
    out_dir.mkdir(parents=True)
    (out_dir / "existing_file.txt").write_text("pre-existing content")

    item = ExportItem("it1", "grp1", p1, "f1.jpg", "sha1", 100, 100, False, [{"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}}])
    exporter = DatasetExporter()
    exporter.collect_verified_items = lambda **kw: [item]

    with pytest.raises(DatasetOverwriteError, match="already exists"):
        exporter.export_yolo(version="v1", output_dir=out_dir, overwrite=False)


def test_empty_export_rejection(dataset_root: Path):
    """Attempting export when zero verified items exist must raise EmptyDatasetExportError."""
    exporter = DatasetExporter()
    exporter.collect_verified_items = lambda **kw: []

    with pytest.raises(EmptyDatasetExportError, match="No eligible human-verified annotations"):
        exporter.export_yolo(version="v_empty_test", output_dir=dataset_root / "empty_out", overwrite=True)


def test_yolo_dataset_validation_passes_on_valid_export(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """An exported YOLO dataset must pass all integrity and split isolation checks."""
    from backend.app.modules.evaluation.exporter import validate_yolo_dataset

    p1 = dummy_images_dir["asset1_frame0.jpg"]
    p_neg = dummy_images_dir["neg_asset4.jpg"]

    item_pos = ExportItem("pos_01", "asset_1", p1, "f1.jpg", "sha_p1", 100, 100, False, [
        {"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.6}}
    ])
    item_neg = ExportItem("neg_01", "asset_2", p_neg, "f2.jpg", "sha_n1", 100, 100, True, [])

    exporter = DatasetExporter()
    out_dir = dataset_root / "valid_dataset"
    exporter.collect_verified_items = lambda **kw: [item_pos, item_neg]

    exporter.export_yolo(
        version="v_test_val",
        output_dir=out_dir,
        train_ratio=0.5,
        val_ratio=0.5,
        test_ratio=0.0,
        overwrite=True
    )

    res = validate_yolo_dataset(out_dir)
    assert res["valid"] is True
    assert res["total_images"] == 2
    assert res["positive_images"] == 1
    assert res["negative_images"] == 1
    assert res["total_annotations"] == 1
    assert len(res["errors"]) == 0


def test_yolo_dataset_validation_catches_tampered_labels(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """Validation must detect invalid or out-of-bounds YOLO coordinates."""
    from backend.app.modules.evaluation.exporter import validate_yolo_dataset, DatasetValidationError

    p1 = dummy_images_dir["asset1_frame0.jpg"]
    item_pos = ExportItem("pos_01", "asset_1", p1, "f1.jpg", "sha_p1", 100, 100, False, [
        {"defect_class": "CRACK", "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.6}}
    ])

    exporter = DatasetExporter()
    out_dir = dataset_root / "tampered_dataset"
    exporter.collect_verified_items = lambda **kw: [item_pos]
    exporter.export_yolo(version="v_tamper", output_dir=out_dir, train_ratio=1.0, val_ratio=0.0, test_ratio=0.0, overwrite=True)

    # Tamper with the label file by inserting invalid coordinates > 1.0
    lbl_file = out_dir / "labels" / "train" / "pos_01.txt"
    lbl_file.write_text("0 1.500000 0.500000 0.400000 0.400000\n")

    with pytest.raises(DatasetValidationError, match="Coordinates out of \\[0, 1\\] bounds"):
        validate_yolo_dataset(out_dir)


def test_target_classes_fixed_ordering_and_rejection(tmp_path: Path, dummy_images_dir, dataset_root: Path):
    """Specifying target_classes enforces deterministic IDs and rejects unmapped classes."""
    p1 = dummy_images_dir["asset1_frame0.jpg"]
    item = ExportItem("pos_01", "asset_1", p1, "f1.jpg", "sha_p1", 100, 100, False, [
        {"defect_class": "CORROSION", "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.6}}
    ])

    exporter = DatasetExporter()
    exporter.collect_verified_items = lambda **kw: [item]
    out_dir = dataset_root / "fixed_classes_dataset"

    canonical = ["CRACK", "CORROSION", "PITTING", "CHIPPING", "DIRT", "RUSTING", "THERMAL_CRACKING"]
    manifest = exporter.export_yolo(
        version="v_fixed",
        output_dir=out_dir,
        target_classes=canonical,
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
        overwrite=True
    )

    # CORROSION must have class index 1 (since CRACK=0, CORROSION=1 in canonical)
    assert manifest["class_mapping"]["CORROSION"] == 1
    assert manifest["class_mapping"]["CRACK"] == 0

    # If item has a class outside target_classes, export must raise InvalidAnnotationError
    item_unknown = ExportItem("pos_02", "asset_1", p1, "f1.jpg", "sha_p1", 100, 100, False, [
        {"defect_class": "SOME_UNDEFINED_DEFECT", "bbox": {"x_min": 0.1, "y_min": 0.2, "x_max": 0.5, "y_max": 0.6}}
    ])
    exporter.collect_verified_items = lambda **kw: [item_unknown]
    with pytest.raises(InvalidAnnotationError, match="not in declared target_classes"):
        exporter.export_yolo(
            version="v_fail",
            output_dir=dataset_root / "fail_dir",
            target_classes=canonical,
            overwrite=True
        )


@pytest.mark.parametrize("path_style", ["absolute", "traversal"])
def test_export_rejects_destination_outside_dataset_root(
    tmp_path: Path, dataset_root: Path, path_style: str
):
    """Reject external destinations before data collection or overwrite deletion."""
    outside = dataset_root.parent / f"outside_{path_style}"
    outside.mkdir(parents=True)
    sentinel = outside / "keep.txt"
    sentinel.write_text("do not delete", encoding="utf-8")

    requested_path = outside if path_style == "absolute" else Path("..") / outside.name

    exporter = DatasetExporter()

    def unexpected_collect(**kwargs):
        pytest.fail("Destination must be validated before collecting dataset items.")

    exporter.collect_verified_items = unexpected_collect

    with pytest.raises(DatasetExportError, match="must be a child"):
        exporter.export_yolo(
            version="path_guard_test",
            output_dir=requested_path,
            overwrite=True,
        )

    assert sentinel.read_text(encoding="utf-8") == "do not delete"
