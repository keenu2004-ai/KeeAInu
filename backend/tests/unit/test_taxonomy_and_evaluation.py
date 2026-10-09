"""Unit tests for Equipment Taxonomy, Decoupled Labels, and Evaluation Engine."""

import pytest
from backend.app.schemas.taxonomy import (
    EquipmentFamily,
    ComponentType,
    DefectCategory,
    MappingConfidence
)
from backend.app.schemas.evaluation import (
    EvaluationRunConfig,
    SplitStrategy,
    SyntheticEvalHandling,
    MetricStatus
)
from backend.app.modules.taxonomy.taxonomy_manager import (
    validate_equipment_taxonomy,
    translate_source_label
)
from backend.app.modules.evaluation.evaluator import (
    compute_classification_metrics,
    compute_bounding_box_iou,
    compute_polygon_mask_iou,
    EvaluationEngine
)


def test_taxonomy_equipment_validation():
    """Verify that component and defect validation respects equipment family boundaries."""
    # Valid engine blade and crack
    valid, err = validate_equipment_taxonomy(
        EquipmentFamily.ENGINES_TURBINES,
        ComponentType.COMPRESSOR_BLADE,
        DefectCategory.CRACK
    )
    assert valid is True
    assert err is None

    # Invalid component for Engines (e.g. Gear tooth face)
    invalid, err = validate_equipment_taxonomy(
        EquipmentFamily.ENGINES_TURBINES,
        ComponentType.GEAR_TOOTH_FACE,
        DefectCategory.CRACK
    )
    assert invalid is False
    assert "GEAR_TOOTH_FACE" in err


def test_source_label_translation_and_uncertainty():
    """Verify third-party label translation preserves confidence and tracks unknown states."""
    defect, conf, rationale = translate_source_label("pitting")
    assert defect == DefectCategory.PITTING
    assert conf == MappingConfidence.EXACT_MATCH

    # Semantic equivalent mapping
    defect, conf, rationale = translate_source_label("crazing")
    assert defect == DefectCategory.CRACK
    assert conf == MappingConfidence.SEMANTIC_EQUIVALENT

    # Completely unknown label maps to UNKNOWN_UNCERTAIN without guessing
    defect, conf, rationale = translate_source_label("random_weird_glitch")
    assert defect == DefectCategory.UNKNOWN_UNCERTAIN
    assert conf == MappingConfidence.UNCERTAIN


def test_compute_classification_metrics_zero_support():
    """Verify that 0-support edge cases return UNDEFINED_ZERO_SUPPORT rather than fabricated 0.0."""
    metric = compute_classification_metrics(tp=0, fp=0, fn=0, tn=0)
    assert metric.status == MetricStatus.UNDEFINED_ZERO_SUPPORT
    assert metric.precision is None
    assert metric.recall is None
    assert metric.f1_score is None
    assert metric.support == 0


def test_compute_classification_metrics_valid():
    """Verify standard mathematically valid precision, recall, and F1 calculations."""
    metric = compute_classification_metrics(tp=8, fp=2, fn=2, tn=10)
    assert metric.status == MetricStatus.VALID
    assert metric.precision == 0.8 # 8 / 10
    assert metric.recall == 0.8 # 8 / 10
    assert metric.f1_score == 0.8
    assert metric.support == 10


def test_compute_bounding_box_iou():
    """Verify spatial IoU calculation for defect localization."""
    box1 = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
    box2 = {"x_min": 0.1, "y_min": 0.1, "x_max": 0.5, "y_max": 0.5}
    assert compute_bounding_box_iou(box1, box2) == 1.0

    box_disjoint = {"x_min": 0.6, "y_min": 0.6, "x_max": 0.9, "y_max": 0.9}
    assert compute_bounding_box_iou(box1, box_disjoint) == 0.0


def test_compute_polygon_mask_iou():
    """Verify polygon segmentation mask IoU raster calculation."""
    # Identical squares
    poly1 = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]
    poly2 = [[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]]
    iou_identical = compute_polygon_mask_iou(poly1, poly2)
    assert iou_identical >= 0.99

    # Disjoint polygons
    poly_disjoint = [[0.6, 0.6], [0.9, 0.6], [0.9, 0.9], [0.6, 0.9]]
    assert compute_polygon_mask_iou(poly1, poly_disjoint) == 0.0

    # Half overlapping rectangles
    poly_half = [[0.3, 0.1], [0.7, 0.1], [0.7, 0.5], [0.3, 0.5]]
    iou_half = compute_polygon_mask_iou(poly1, poly_half)
    assert 0.30 <= iou_half <= 0.40


def test_leak_free_dataset_partitioning():
    """Verify that video recordings are split at asset boundary without adjacent frame leakage."""
    assets = [f"video_recording_{i}" for i in range(10)]
    config = EvaluationRunConfig(
        train_ratio=0.70,
        val_ratio=0.15,
        test_ratio=0.15,
        random_seed=123
    )

    splits = EvaluationEngine.partition_dataset_without_leakage(assets, config)
    assert len(splits["train"]) == 7
    assert len(splits["val"]) == 2
    assert len(splits["test"]) == 1

    # Disjointness check
    assert len(set(splits["train"]).intersection(set(splits["val"]))) == 0
    assert len(set(splits["train"]).intersection(set(splits["test"]))) == 0
    assert len(set(splits["val"]).intersection(set(splits["test"]))) == 0


def test_equipment_evaluation_engine():
    """Verify evaluation execution with synthetic data segregation and slice breakdown."""
    annotations = [
        {
            "asset_id": "ast_real_01",
            "equipment_family": EquipmentFamily.ENGINES_TURBINES.value,
            "component_type": ComponentType.COMPRESSOR_BLADE.value,
            "defect_category": DefectCategory.CRACK.value,
            "is_synthetic": False
        },
        {
            "asset_id": "ast_synth_01",
            "equipment_family": EquipmentFamily.ENGINES_TURBINES.value,
            "component_type": ComponentType.COMPRESSOR_BLADE.value,
            "defect_category": DefectCategory.CRACK.value,
            "is_synthetic": True
        }
    ]
    predictions = [
        {
            "asset_id": "ast_real_01",
            "defect_category": DefectCategory.CRACK.value,
            "confidence": 0.92
        }
    ]

    config = EvaluationRunConfig(
        synthetic_handling=SyntheticEvalHandling.EXCLUDE_FROM_EVAL
    )

    report = EvaluationEngine.run_equipment_evaluation(annotations, predictions, config)
    assert report.total_samples_evaluated == 1 # Synthetic excluded
    assert report.real_samples_count == 1
    assert report.synthetic_samples_count == 1
    assert report.overall_classification.true_positives == 1
    assert report.overall_classification.precision == 1.0
