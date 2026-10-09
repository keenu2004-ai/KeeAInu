"""Dataset Discovery, Footage Profiling & Domain Review API Router (Phase 4A)."""

from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from backend.app.core.config import settings
from backend.app.core.security import is_path_safe
from backend.app.db.repository import repo
from backend.app.modules.discovery.scanner import scan_source_directories, scan_and_profile_file
from backend.app.schemas.discovery import (
    AssetRecord,
    DomainCategory,
    ScanDirectoryRequest,
    UpdateDomainRequest,
    UpdateSampleReviewRequest,
    DiscoveryReport,
    DatasetManifest,
    SampleItem
)

router = APIRouter(prefix="/discovery", tags=["Dataset Discovery & Profiling"])


@router.post("/scan", status_code=status.HTTP_200_OK)
async def run_discovery_scan(req: ScanDirectoryRequest):
    """
    Trigger a reproducible discovery scan of source footage and raw vaults.
    Profiles visual quality, extracts representative samples, and registers assets.
    """
    custom_path = None
    if req.source_directory:
        # Prevent traversal
        custom_path = (settings.BASE_DIR / req.source_directory).resolve()
        if not is_path_safe(custom_path, settings.BASE_DIR):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source directory escapes application boundary."
            )
        if not custom_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source directory '{req.source_directory}' does not exist."
            )

    try:
        profiled_assets = scan_source_directories(
            custom_dir=custom_path,
            sample_count_per_video=req.sample_count_per_video,
            force_rescan=req.force_rescan
        )
        return {
            "status": "COMPLETED",
            "scanned_count": len(profiled_assets),
            "summary": repo.get_discovery_summary()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Discovery scan error: {str(e)}"
        )


@router.get("/assets", response_model=List[AssetRecord])
async def list_dataset_assets(
    domain: Optional[DomainCategory] = None,
    is_synthetic: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000)
):
    """List discovered dataset assets with optional domain and synthetic filters."""
    domain_str = domain.value if domain else None
    return repo.list_assets(domain=domain_str, is_synthetic=is_synthetic, skip=skip, limit=limit)


@router.get("/assets/{asset_id}", response_model=AssetRecord)
async def get_dataset_asset(asset_id: str):
    """Retrieve detailed metadata, quality profile, and samples for an asset."""
    asset = repo.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")
    return asset


@router.get("/assets/{asset_id}/contact-sheet")
async def get_asset_contact_sheet(asset_id: str):
    """Serve the derived contact sheet image for visual gallery inspection."""
    asset = repo.get_asset(asset_id)
    if not asset or not asset.get("contact_sheet_path"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact sheet unavailable.")

    cs_path = Path(asset["contact_sheet_path"]).resolve()
    if not cs_path.exists() or not is_path_safe(cs_path, settings.DERIVED_MEDIA_DIR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact sheet file missing.")

    return FileResponse(path=cs_path, media_type="image/jpeg")


@router.get("/samples/{sample_id}/content")
async def get_sample_content(sample_id: str):
    """Serve an individual derived representative sample frame image."""
    sample = repo.get_sample(sample_id)
    if not sample or not sample.get("file_path"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample frame unavailable.")

    sample_path = Path(sample["file_path"]).resolve()
    if not sample_path.exists() or not is_path_safe(sample_path, settings.DERIVED_MEDIA_DIR):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample image file missing.")

    return FileResponse(path=sample_path, media_type="image/jpeg")


@router.patch("/assets/{asset_id}/domain", response_model=AssetRecord)
async def update_asset_domain(asset_id: str, req: UpdateDomainRequest):
    """Assign candidate inspection domain to an asset (Mechanical, Pipes, Moulds, Other, Unknown)."""
    try:
        return repo.update_asset_domain(
            asset_id=asset_id,
            domain_assignment=req.domain_assignment.value,
            domain_confidence=req.domain_confidence.value,
            domain_notes=req.domain_notes,
            reviewed_by=req.reviewed_by
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")


@router.patch("/samples/{sample_id}/review", response_model=SampleItem)
async def update_sample_review(sample_id: str, req: UpdateSampleReviewRequest):
    """Record human review defect status for an individual sampled frame."""
    try:
        return repo.update_sample_review(
            sample_id=sample_id,
            review_status=req.review_status.value,
            suspected_category=req.suspected_category,
            reviewer_notes=req.reviewer_notes,
            reviewed_by=req.reviewed_by
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample '{sample_id}' not found.")


@router.get("/report", response_model=DiscoveryReport)
async def get_discovery_report():
    """Generate high-level dataset discovery summary and readiness report."""
    summary = repo.get_discovery_summary()
    return DiscoveryReport(**summary)


@router.get("/manifest", response_model=DatasetManifest)
async def get_dataset_manifest():
    """Export machine-readable versioned discovery dataset manifest."""
    assets = repo.list_assets(limit=1000)
    summary = repo.get_discovery_summary()
    
    return DatasetManifest(
        schema_version="1.0.0",
        dataset_name="KeeAInu Discovery & Profiling Corpus",
        generated_at=summary["generated_at"],
        total_assets=len(assets),
        items=assets
    )
