"""Equipment-Aware Evaluation and Benchmarking API Endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.evaluation import (
    EvaluationRunConfig,
    EvaluationReportRecord
)
from backend.app.modules.evaluation.evaluator import EvaluationEngine
from backend.app.db.repository import repo

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
            "defect_category": f.get("candidate_defect"),
            "confidence": f.get("model_prediction_confidence")
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
