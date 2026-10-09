"""Multi-Source Dataset Discovery & Controlled Acquisition API Router."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.db.repository import repo
from backend.app.schemas.acquisition import (
    AcquireCandidateRequest,
    AcquisitionAuditEvent,
    AcquisitionJobRecord,
    DatasetCandidateRecord,
    LicenseReviewRequest,
    SearchCandidateQuery,
    SourceProviderInfo,
    SyntheticGenerationRequest
)
from backend.app.modules.acquisition.providers.registry import provider_registry
from backend.app.modules.acquisition.pipeline import execute_acquisition, execute_synthetic_generation


router = APIRouter(prefix="/acquisition", tags=["Multi-Source Discovery & Acquisition"])


@router.get("/providers", response_model=List[SourceProviderInfo])
async def list_providers():
    """List all registered dataset discovery providers and their capabilities."""
    return provider_registry.list_providers()


@router.post("/search", response_model=List[DatasetCandidateRecord])
async def search_candidates(query: SearchCandidateQuery):
    """
    Search for inspection datasets across public catalogs, research archives,
    internal vaults, and synthetic generators. Discovered candidates are stored in the registry.
    """
    try:
        candidates = await provider_registry.search_all(query)
        # Store in database registry for auditability and review
        saved = []
        for c in candidates:
            c_dict = c.model_dump()
            # Serialize breakdown
            if c.relevance_breakdown:
                c_dict["relevance_breakdown"] = c.relevance_breakdown.model_dump()
            res = repo.upsert_candidate(c_dict)
            saved.append(DatasetCandidateRecord(**res))

        repo.record_audit_event(
            event_type="CATALOG_SEARCH_EXECUTED",
            details={"query": query.query, "domain": query.target_domain, "results_found": len(saved)}
        )
        return saved
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery search error: {str(e)}"
        )


@router.get("/candidates", response_model=List[DatasetCandidateRecord])
async def list_candidates(
    source_id: Optional[str] = None,
    domain_tag: Optional[str] = None,
    license_status: Optional[str] = None,
    acquisition_status: Optional[str] = None,
    direct_videoscope_only: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List discovered dataset candidates with multi-faceted filtering."""
    candidates = repo.list_candidates(
        source_id=source_id,
        domain_tag=domain_tag,
        license_status=license_status,
        acquisition_status=acquisition_status,
        direct_videoscope_only=direct_videoscope_only,
        skip=skip,
        limit=limit
    )
    return [DatasetCandidateRecord(**c) for c in candidates]


@router.get("/candidates/{candidate_id}", response_model=DatasetCandidateRecord)
async def get_candidate(candidate_id: str):
    """Retrieve full metadata, relevance breakdown, and rights status for a candidate."""
    cand = repo.get_candidate(candidate_id)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate '{candidate_id}' not found.")
    return DatasetCandidateRecord(**cand)


@router.post("/candidates/{candidate_id}/license-review", response_model=DatasetCandidateRecord)
async def review_candidate_license(candidate_id: str, req: LicenseReviewRequest):
    """Record a formal compliance review and assign legal permission status."""
    try:
        updated = repo.record_license_review(
            candidate_id=candidate_id,
            license_status=req.license_status.value,
            commercial_rights_status=req.commercial_rights_status,
            license_notes=req.license_notes,
            terms_url=req.terms_url,
            reviewed_by=req.reviewed_by
        )
        repo.record_audit_event(
            event_type="LICENSE_REVIEW_UPDATED",
            details={
                "candidate_id": candidate_id,
                "license_status": req.license_status.value,
                "commercial_rights": req.commercial_rights_status,
                "reviewed_by": req.reviewed_by,
                "notes": req.license_notes
            },
            candidate_id=candidate_id
        )
        return DatasetCandidateRecord(**updated)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate '{candidate_id}' not found.")


@router.post("/candidates/{candidate_id}/acquire")
async def acquire_dataset(candidate_id: str, req: AcquireCandidateRequest):
    """
    Trigger controlled acquisition for an approved candidate dataset.
    Strictly verifies license permission gate before downloading.
    """
    if candidate_id != req.candidate_id:
        req.candidate_id = candidate_id

    try:
        result = await execute_acquisition(req)
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Acquisition failed: {str(e)}")


@router.post("/synthetic/generate")
async def generate_synthetic_data(req: SyntheticGenerationRequest):
    """
    Execute controlled procedural synthetic defect generation with full provenance tracking.
    """
    try:
        return execute_synthetic_generation(req)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthetic generation error: {str(e)}"
        )


@router.get("/jobs", response_model=List[AcquisitionJobRecord])
async def list_acquisition_jobs(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    """List historical and active acquisition jobs."""
    jobs = repo.list_acquisition_jobs(skip=skip, limit=limit)
    return [AcquisitionJobRecord(**j) for j in jobs]


@router.get("/audit-trail", response_model=List[AcquisitionAuditEvent])
async def list_audit_trail(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    """Export compliance and provenance audit trail events."""
    events = repo.list_audit_events(skip=skip, limit=limit)
    return [AcquisitionAuditEvent(**e) for e in events]
