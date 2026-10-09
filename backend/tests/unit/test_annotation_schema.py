"""Unit tests for the KeeAInu annotation schema and coordinate validators."""

import pytest
from pydantic import ValidationError
from backend.app.schemas.annotation import (
    GroundTruthDatasetRecord,
    GroundTruthAnnotationItem,
    NormalizedBoundingBox,
    ProvenanceType
)


def test_valid_bounding_box():
    bbox = NormalizedBoundingBox(x_min=0.1, y_min=0.2, x_max=0.5, y_max=0.8)
    assert bbox.x_min == 0.1
    assert bbox.x_max == 0.5


def test_reject_inverted_x_coordinates():
    with pytest.raises(ValidationError) as exc:
        NormalizedBoundingBox(x_min=0.6, y_min=0.2, x_max=0.3, y_max=0.8)
    assert "x_min" in str(exc.value) and "strictly less than x_max" in str(exc.value)


def test_reject_inverted_y_coordinates():
    with pytest.raises(ValidationError) as exc:
        NormalizedBoundingBox(x_min=0.1, y_min=0.9, x_max=0.5, y_max=0.4)
    assert "y_min" in str(exc.value) and "strictly less than y_max" in str(exc.value)


def test_reject_out_of_bounds_coordinates():
    with pytest.raises(ValidationError) as exc:
        NormalizedBoundingBox(x_min=-0.1, y_min=0.2, x_max=0.5, y_max=0.8)
    assert "x_min" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        NormalizedBoundingBox(x_min=0.1, y_min=0.2, x_max=1.5, y_max=0.8)
    assert "x_max" in str(exc.value)


def test_valid_dataset_record():
    record = GroundTruthDatasetRecord(
        schema_version="1.0.0",
        dataset_id="ds_test_001",
        media_id="vid_001",
        media_sha256="a" * 64,
        media_filename="sample_run.mp4",
        image_width=640,
        image_height=480,
        provenance=ProvenanceType.SYNTHETIC_GENERATED,
        is_synthetic=True,
        annotations=[
            GroundTruthAnnotationItem(
                annotation_id="ann_01",
                frame_index=5,
                timestamp_ms=166.67,
                defect_class="TEST_PATTERN_CRACK_SYNTHETIC",
                bbox=NormalizedBoundingBox(x_min=0.2, y_min=0.3, x_max=0.6, y_max=0.7)
            )
        ]
    )
    assert record.schema_version == "1.0.0"
    assert len(record.annotations) == 1
    assert record.annotations[0].defect_class == "TEST_PATTERN_CRACK_SYNTHETIC"


def test_reject_unsupported_schema_version():
    with pytest.raises(ValidationError) as exc:
        GroundTruthDatasetRecord(
            schema_version="2.0.0",
            dataset_id="ds_test_001",
            media_id="vid_001",
            media_sha256="a" * 64,
            media_filename="sample_run.mp4",
            image_width=640,
            image_height=480,
            provenance=ProvenanceType.HUMAN_VERIFIED,
            is_synthetic=False
        )
    assert "Unsupported schema version" in str(exc.value)


def test_reject_invalid_sha256_format():
    with pytest.raises(ValidationError) as exc:
        GroundTruthDatasetRecord(
            schema_version="1.0.0",
            dataset_id="ds_test_001",
            media_id="vid_001",
            media_sha256="not_a_valid_sha256",
            media_filename="sample_run.mp4",
            image_width=640,
            image_height=480,
            provenance=ProvenanceType.HUMAN_VERIFIED,
            is_synthetic=False
        )
    assert "media_sha256" in str(exc.value)


def test_enforce_synthetic_provenance_flag():
    # If provenance is SYNTHETIC_GENERATED, is_synthetic must be True
    with pytest.raises(ValidationError) as exc:
        GroundTruthDatasetRecord(
            schema_version="1.0.0",
            dataset_id="ds_test_001",
            media_id="vid_001",
            media_sha256="b" * 64,
            media_filename="sample.mp4",
            image_width=320,
            image_height=240,
            provenance=ProvenanceType.SYNTHETIC_GENERATED,
            is_synthetic=False  # Invalid combination
        )
    assert "is_synthetic must be True" in str(exc.value)
