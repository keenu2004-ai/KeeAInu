"""Equipment-Specific Taxonomy and Defect Label Schemas."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EquipmentFamily(str, Enum):
    """Primary industrial mechanical equipment families."""
    ENGINES_TURBINES = "ENGINES_TURBINES"
    GEARBOXES_TRANSMISSIONS = "GEARBOXES_TRANSMISSIONS"
    OTHER_MECHANICAL_ASSEMBLIES = "OTHER_MECHANICAL_ASSEMBLIES"
    UNKNOWN_EQUIPMENT = "UNKNOWN_EQUIPMENT"


class ComponentType(str, Enum):
    """Component categories across equipment families."""
    # Engines & Turbines
    COMPRESSOR_BLADE = "COMPRESSOR_BLADE"
    TURBINE_BLADE = "TURBINE_BLADE"
    COMBUSTION_CHAMBER = "COMBUSTION_CHAMBER"
    NOZZLE_GUIDE_VANE = "NOZZLE_GUIDE_VANE"
    ROTOR_SHAFT = "ROTOR_SHAFT"
    BEARING_ASSEMBLY = "BEARING_ASSEMBLY"
    SEAL_RING = "SEAL_RING"
    INTERNAL_CASING = "INTERNAL_CASING"
    
    # Gearboxes & Transmissions
    GEAR_TOOTH_FACE = "GEAR_TOOTH_FACE"
    PINION_GEAR = "PINION_GEAR"
    PLANETARY_CARRIER = "PLANETARY_CARRIER"
    INPUT_OUTPUT_SHAFT = "INPUT_OUTPUT_SHAFT"
    ROLLER_BEARING = "ROLLER_BEARING"
    INTERNAL_HOUSING = "INTERNAL_HOUSING"
    LUBRICATION_PORT = "LUBRICATION_PORT"

    # Other Assemblies
    PUMP_IMPELLER = "PUMP_IMPELLER"
    VALVE_SEAT = "VALVE_SEAT"
    ACTUATOR_BORE = "ACTUATOR_BORE"
    MACHINED_HOUSING = "MACHINED_HOUSING"
    CASTING_CAVITY = "CASTING_CAVITY"
    FLANGE_SURFACE = "FLANGE_SURFACE"

    # General / Fallback
    OTHER_COMPONENT = "OTHER_COMPONENT"
    UNKNOWN_COMPONENT = "UNKNOWN_COMPONENT"


class DefectCategory(str, Enum):
    """Standardized mechanical defect classifications."""
    CRACK = "CRACK"
    CHIPPING_FRACTURE = "CHIPPING_FRACTURE"
    EROSION = "EROSION"
    CORROSION = "CORROSION"
    PITTING = "PITTING"
    SCORING_SCRATCH = "SCORING_SCRATCH"
    DEPOSIT_FOULING = "DEPOSIT_FOULING"
    FOREIGN_OBJECT_DAMAGE = "FOREIGN_OBJECT_DAMAGE"
    DEFORMATION = "DEFORMATION"
    THERMAL_DISCOLORATION = "THERMAL_DISCOLORATION"
    SURFACE_SPALLING = "SURFACE_SPALLING"
    WEAR = "WEAR"
    LUBRICANT_DEBRIS_CONTAMINATION = "LUBRICANT_DEBRIS_CONTAMINATION"
    POROSITY = "POROSITY"
    OTHER_DEFECT = "OTHER_DEFECT"
    UNKNOWN_UNCERTAIN = "UNKNOWN_UNCERTAIN"


class MappingConfidence(str, Enum):
    """Confidence level when translating source labels to KeeAInu taxonomy."""
    EXACT_MATCH = "EXACT_MATCH"
    SEMANTIC_EQUIVALENT = "SEMANTIC_EQUIVALENT"
    PROVISIONAL_INFERRED = "PROVISIONAL_INFERRED"
    UNCERTAIN = "UNCERTAIN"


class BoundingBox(BaseModel):
    """Normalized spatial bounding box coordinates (0.0 to 1.0)."""
    x_min: float = Field(..., ge=0.0, le=1.0)
    y_min: float = Field(..., ge=0.0, le=1.0)
    x_max: float = Field(..., ge=0.0, le=1.0)
    y_max: float = Field(..., ge=0.0, le=1.0)


class DecoupledAnnotationRecord(BaseModel):
    """Complete traceable annotation with equipment context and decoupled lineage."""
    id: str
    asset_id: str
    sample_id: Optional[str] = None
    frame_index: int = 0
    equipment_family: EquipmentFamily
    component_type: ComponentType
    defect_category: DefectCategory
    observed_visual_condition: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    segmentation_mask_path: Optional[str] = None
    source_raw_label: Optional[str] = Field(None, description="Original unchanged third-party label")
    mapping_confidence: MappingConfidence = MappingConfidence.EXACT_MATCH
    annotator_type: str = Field(..., description="'SOURCE_DATASET', 'HUMAN_EXPERT', 'MODEL_PREDICTION'")
    annotator_id: str
    taxonomy_version: str = "2.0.0"
    is_synthetic: bool = False
    notes: Optional[str] = None
    created_at: str
    updated_at: str


class CreateAnnotationRequest(BaseModel):
    """Payload to register an equipment-aware annotation."""
    asset_id: str
    sample_id: Optional[str] = None
    frame_index: int = 0
    equipment_family: EquipmentFamily
    component_type: ComponentType
    defect_category: DefectCategory
    observed_visual_condition: Optional[str] = None
    bbox: Optional[BoundingBox] = None
    source_raw_label: Optional[str] = None
    mapping_confidence: MappingConfidence = MappingConfidence.EXACT_MATCH
    annotator_id: str = Field("Inspector", min_length=1)
    notes: Optional[str] = None
