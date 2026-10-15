"""Equipment-Aware Evaluation and Benchmarking API Endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.evaluation import (
    EvaluationRunConfig,
    EvaluationReportRecord
)
from backend.app.modules.evaluation.evaluator import EvaluationEngine
from backend.app.db.repository import repo
from backend.app.core.config import settings
from backend.app.core.access_control import require_ground_truth_api_key

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarking"])


@router.post("/run", response_model=EvaluationReportRecord, status_code=status.HTTP_201_CREATED)
async def execute_evaluation_run(config: EvaluationRunConfig):
    """
    Execute an equipment-aware evaluation benchmark across mechanical component slices,
    preventing data leakage and enforcing real vs. synthetic segregation.
    """
    # Load decoupled annotations from repository
    annotations = repo.list_decoupled_annotations(limit=1000)
    
    # Load candidate predictions/findings from repository
    findings = repo.list_candidate_findings(limit=1000)
    predictions = [
        {
            "asset_id": f.get("asset_id"),
            "frame_index": f.get("frame_index", 0),
            "defect_category": f.get("candidate_defect"),
            "confidence": f.get("model_prediction_confidence"),
            "bbox": f.get("candidate_bbox"),
            "is_simulated": f.get("is_simulated", True)
        }
        for f in findings
    ]

    report = EvaluationEngine.run_equipment_evaluation(
        annotations=annotations,
        predictions=predictions,
        config=config
    )

    # Persist the evaluation report
    repo.save_evaluation_run(report.model_dump())
    return report


@router.get("/runs", response_model=List[Dict[str, Any]])
async def list_evaluation_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """List historical evaluation runs and manifest hashes."""
    return repo.list_evaluation_runs(skip=skip, limit=limit)


@router.get("/runs/{run_id}", response_model=EvaluationReportRecord)
async def get_evaluation_run(run_id: str):
    """Retrieve full evaluation benchmark report by run ID."""
    report = repo.get_evaluation_run(run_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evaluation run '{run_id}' not found.")
    return report


# --- Dataset Export & Training Readiness Endpoints ---

from fastapi import Depends, Header
from pydantic import BaseModel, Field
from backend.app.modules.evaluation.exporter import (
    DatasetExporter,
    DatasetExportError,
    DatasetOverwriteError,
    EmptyDatasetExportError,
    SplitLeakageError,
    InvalidAnnotationError,
    DatasetValidationError,
    validate_yolo_dataset
)

EXPORTER_UNAUTHORIZED_ROLES = {"TRAINEE", "GUEST", "READONLY", "UNAUTHORIZED", "ANONYMOUS"}


class DatasetExportRequest(BaseModel):
    """Configuration for safe YOLO dataset export."""
    version: str = Field("v1", min_length=1, pattern=r"^[a-zA-Z0-9_\-\.]+$", description="Dataset export version identifier")
    output_dir: Optional[str] = Field(None, description="Custom export directory path relative to project DATA_DIR/datasets")
    train_ratio: float = Field(0.70, ge=0.1, le=1.0)
    val_ratio: float = Field(0.20, ge=0.0, le=0.5)
    test_ratio: float = Field(0.10, ge=0.0, le=0.5)
    random_seed: int = Field(42)
    include_negatives: bool = Field(True, description="Include verified defect-free images as negative samples")
    include_synthetic: bool = Field(False, description="Strictly exclude synthetic data from ground-truth exports by default")
    include_simulated: bool = Field(False, description="Strictly exclude simulated/mock model findings from ground-truth exports by default")
    overwrite: bool = Field(False, description="Explicit flag required to overwrite an existing export directory")
    target_classes: Optional[List[str]] = Field(None, description="Explicit target defect classes for fixed YOLO class index mapping")


class DatasetValidateRequest(BaseModel):
    """Request to validate an exported YOLO dataset directory."""
    dataset_path: str = Field(..., description="Dataset directory name inside DATA_DIR/datasets or absolute path")


@router.get("/readiness", status_code=status.HTTP_200_OK, dependencies=[Depends(require_ground_truth_api_key)])
async def get_training_readiness():
    """
    Audit actual human-verified ground truth annotations and verified negatives.
    Provides verifiable training baseline readiness and remaining blockers.
    """
    return repo.get_ground_truth_readiness()


@router.post("/datasets/export", status_code=status.HTTP_200_OK, dependencies=[Depends(require_ground_truth_api_key)])
async def export_dataset(
    req: DatasetExportRequest,
    x_inspector_role: Optional[str] = Header(None, alias="X-Inspector-Role"),
    x_inspector_id: Optional[str] = Header(None, alias="X-Inspector-Id")
):
    """
    Safely export human-verified defect annotations into documented YOLO detection format.
    Enforces group-based partition splitting (by asset/session) to prevent split leakage,
    hashes all media evidence, and validates box coordinates and class distributions.
    """
    # Enforce role authorization if specified
    if x_inspector_role:
        role_clean = x_inspector_role.strip().upper()
        if role_clean in EXPORTER_UNAUTHORIZED_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{x_inspector_role}' is not authorized to export ground truth datasets."
            )

    exporter = DatasetExporter(repository=repo)
    try:
        manifest = exporter.export_yolo(
            version=req.version,
            output_dir=None if not req.output_dir else (settings.DATA_DIR / "datasets" / req.output_dir),
            train_ratio=req.train_ratio,
            val_ratio=req.val_ratio,
            test_ratio=req.test_ratio,
            random_seed=req.random_seed,
            include_negatives=req.include_negatives,
            include_synthetic=req.include_synthetic,
            include_simulated=req.include_simulated,
            overwrite=req.overwrite,
            target_classes=req.target_classes
        )
        return manifest
    except EmptyDatasetExportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatasetOverwriteError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except SplitLeakageError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except InvalidAnnotationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except DatasetExportError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {str(e)}")


@router.post("/datasets/validate", status_code=status.HTTP_200_OK, dependencies=[Depends(require_ground_truth_api_key)])
async def validate_dataset_endpoint(req: DatasetValidateRequest):
    """
    Validate exported YOLO dataset directory structure, coordinates, and split isolation.
    """
    from pathlib import Path
    datasets_root = (settings.DATA_DIR / "datasets").resolve()
    requested_path = Path(req.dataset_path)
    if requested_path.is_absolute():
        target_p = requested_path.resolve()
    else:
        target_p = (datasets_root / requested_path).resolve()

    if target_p == datasets_root or not target_p.is_relative_to(datasets_root):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset path must identify a directory inside the approved dataset directory."
        )

    try:
        res = validate_yolo_dataset(target_p)
        return res
    except DatasetValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
