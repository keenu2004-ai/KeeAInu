"""Equipment-Specific Taxonomy and Decoupled Label API Endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.taxonomy import (
    EquipmentFamily,
    ComponentType,
    DefectCategory,
    MappingConfidence,
    DecoupledAnnotationRecord,
    CreateAnnotationRequest
)
from backend.app.modules.taxonomy.taxonomy_manager import (
    EQUIPMENT_COMPONENT_MAP,
    EQUIPMENT_DEFECT_MAP,
    validate_equipment_taxonomy,
    translate_source_label
)
from backend.app.db.repository import repo

router = APIRouter(prefix="/taxonomy", tags=["Equipment Taxonomy & Annotations"])


@router.get("/structure", response_model=Dict[str, Any])
async def get_taxonomy_structure():
    """Returns the full hierarchical equipment families, components, and defect categories."""
    return {
        "equipment_families": [f.value for f in EquipmentFamily],
        "components_by_family": {
            f.value: [c.value for c in comps] for f, comps in EQUIPMENT_COMPONENT_MAP.items()
        },
        "defects_by_family": {
            f.value: [d.value for d in defects] for f, defects in EQUIPMENT_DEFECT_MAP.items()
        },
        "all_defect_categories": [d.value for d in DefectCategory],
        "mapping_confidence_levels": [c.value for c in MappingConfidence]
    }


@router.post("/translate", response_model=Dict[str, Any])
async def translate_label(
    raw_label: str = Query(..., description="Raw third-party source label string"),
    target_family: EquipmentFamily = Query(EquipmentFamily.ENGINES_TURBINES, description="Target equipment family context")
):
    """Translate third-party raw labels into KeeAInu standard defect category with mapping confidence."""
    defect, confidence, rationale = translate_source_label(raw_label, target_family)
    return {
        "source_raw_label": raw_label,
        "target_family": target_family.value,
        "mapped_defect_category": defect.value,
        "mapping_confidence": confidence.value,
        "rationale": rationale
    }


@router.post("/annotations", response_model=DecoupledAnnotationRecord, status_code=status.HTTP_201_CREATED)
async def create_annotation(payload: CreateAnnotationRequest):
    """
    Create an equipment-aware decoupled annotation without altering original source media.
    Validates equipment family context and preserves source raw label provenance.
    """
    is_valid, error = validate_equipment_taxonomy(
        payload.equipment_family,
        payload.component_type,
        payload.defect_category
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    annot_dict = payload.model_dump()
    if payload.bbox:
        annot_dict["bbox"] = payload.bbox.model_dump()
    
    created = repo.create_decoupled_annotation(annot_dict)
    return created


@router.get("/annotations", response_model=List[DecoupledAnnotationRecord])
async def list_annotations(
    asset_id: Optional[str] = None,
    equipment_family: Optional[EquipmentFamily] = None,
    component_type: Optional[ComponentType] = None,
    defect_category: Optional[DefectCategory] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """List decoupled annotations with equipment context filters."""
    return repo.list_decoupled_annotations(
        asset_id=asset_id,
        equipment_family=equipment_family.value if equipment_family else None,
        component_type=component_type.value if component_type else None,
        defect_category=defect_category.value if defect_category else None,
        skip=skip,
        limit=limit
    )


@router.get("/annotations/{annotation_id}", response_model=DecoupledAnnotationRecord)
async def get_annotation(annotation_id: str):
    """Retrieve specific decoupled annotation by ID."""
    record = repo.get_decoupled_annotation(annotation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Annotation '{annotation_id}' not found.")
    return record
