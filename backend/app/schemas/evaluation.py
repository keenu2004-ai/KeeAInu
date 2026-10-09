"""Equipment-Aware Evaluation and Benchmarking Schemas."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.schemas.taxonomy import EquipmentFamily, ComponentType, DefectCategory


class SplitStrategy(str, Enum):
    """Dataset partition splitting strategies to prevent data leakage."""
    ASSET_SESSION_SPLIT = "ASSET_SESSION_SPLIT" # Entire video/session kept in one split
    EQUIPMENT_INSTANCE_SPLIT = "EQUIPMENT_INSTANCE_SPLIT" # Equipment serial/instance split


class SyntheticEvalHandling(str, Enum):
    """Rules for handling synthetic media in evaluation."""
    EXCLUDE_FROM_EVAL = "EXCLUDE_FROM_EVAL" # Strictly exclude synthetic data from eval/test
    SYNTHETIC_BENCHMARK_ONLY = "SYNTHETIC_BENCHMARK_ONLY" # Evaluate separately as synthetic stress test


class MetricStatus(str, Enum):
    """Indication of metric mathematical validity."""
    VALID = "VALID"
    UNDEFINED_ZERO_SUPPORT = "UNDEFINED_ZERO_SUPPORT"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"


class ClassificationMetric(BaseModel):
    """Classification metric with explicit support and validity indicators."""
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    support: int
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    status: MetricStatus = MetricStatus.VALID


class LocalizationMetric(BaseModel):
    """Spatial bounding box / pixel mask localization metrics."""
    mean_iou: Optional[float] = None
    pixel_precision: Optional[float] = None
    pixel_recall: Optional[float] = None
    pixel_f1: Optional[float] = None
    evaluated_objects_count: int
    status: MetricStatus = MetricStatus.VALID


class EquipmentSliceResult(BaseModel):
    """Evaluation breakdown slice per equipment family and component."""
    equipment_family: EquipmentFamily
    component_type: Optional[ComponentType] = None
    defect_category: Optional[DefectCategory] = None
    sample_count: int
    is_synthetic: bool = False
    classification: ClassificationMetric
    localization: Optional[LocalizationMetric] = None


class EvaluationRunConfig(BaseModel):
    """Configuration to execute a deterministic evaluation benchmark."""
    name: str = Field("Mechanical Borescope Evaluation Run", min_length=1)
    target_equipment_families: List[EquipmentFamily] = Field(
        default_factory=lambda: [EquipmentFamily.ENGINES_TURBINES, EquipmentFamily.GEARBOXES_TRANSMISSIONS]
    )
    split_strategy: SplitStrategy = SplitStrategy.ASSET_SESSION_SPLIT
    train_ratio: float = Field(0.70, ge=0.5, le=0.9)
    val_ratio: float = Field(0.15, ge=0.05, le=0.3)
    test_ratio: float = Field(0.15, ge=0.05, le=0.3)
    synthetic_handling: SyntheticEvalHandling = SyntheticEvalHandling.EXCLUDE_FROM_EVAL
    min_samples_threshold: int = Field(2, ge=1)
    random_seed: int = Field(42)
    evaluator_identity: str = Field("Benchmark Engineer", min_length=1)


class EvaluationReportRecord(BaseModel):
    """Comprehensive, equipment-aware evaluation benchmark report."""
    run_id: str
    run_name: str
    dataset_manifest_hash: str
    total_assets_evaluated: int
    total_samples_evaluated: int
    real_samples_count: int
    synthetic_samples_count: int
    split_strategy: SplitStrategy
    overall_classification: ClassificationMetric
    equipment_slices: List[EquipmentSliceResult]
    confusion_matrix_labels: List[str]
    confusion_matrix: List[List[int]]
    is_simulated_baseline: bool = Field(False, description="Flag indicating mock/simulated pipeline test")
    limitations: List[str] = Field(default_factory=list)
    created_at: str
