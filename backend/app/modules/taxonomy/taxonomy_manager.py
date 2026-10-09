"""Equipment Taxonomy Management and Decoupled Label Translation."""

from typing import Dict, List, Optional, Tuple, Any
from backend.app.schemas.taxonomy import (
    EquipmentFamily,
    ComponentType,
    DefectCategory,
    MappingConfidence
)


EQUIPMENT_COMPONENT_MAP: Dict[EquipmentFamily, List[ComponentType]] = {
    EquipmentFamily.ENGINES_TURBINES: [
        ComponentType.COMPRESSOR_BLADE,
        ComponentType.TURBINE_BLADE,
        ComponentType.COMBUSTION_CHAMBER,
        ComponentType.NOZZLE_GUIDE_VANE,
        ComponentType.ROTOR_SHAFT,
        ComponentType.BEARING_ASSEMBLY,
        ComponentType.SEAL_RING,
        ComponentType.INTERNAL_CASING,
        ComponentType.OTHER_COMPONENT,
        ComponentType.UNKNOWN_COMPONENT
    ],
    EquipmentFamily.GEARBOXES_TRANSMISSIONS: [
        ComponentType.GEAR_TOOTH_FACE,
        ComponentType.PINION_GEAR,
        ComponentType.PLANETARY_CARRIER,
        ComponentType.INPUT_OUTPUT_SHAFT,
        ComponentType.ROLLER_BEARING,
        ComponentType.INTERNAL_HOUSING,
        ComponentType.LUBRICATION_PORT,
        ComponentType.OTHER_COMPONENT,
        ComponentType.UNKNOWN_COMPONENT
    ],
    EquipmentFamily.OTHER_MECHANICAL_ASSEMBLIES: [
        ComponentType.PUMP_IMPELLER,
        ComponentType.VALVE_SEAT,
        ComponentType.ACTUATOR_BORE,
        ComponentType.MACHINED_HOUSING,
        ComponentType.CASTING_CAVITY,
        ComponentType.FLANGE_SURFACE,
        ComponentType.OTHER_COMPONENT,
        ComponentType.UNKNOWN_COMPONENT
    ],
    EquipmentFamily.UNKNOWN_EQUIPMENT: [
        ComponentType.OTHER_COMPONENT,
        ComponentType.UNKNOWN_COMPONENT
    ]
}


EQUIPMENT_DEFECT_MAP: Dict[EquipmentFamily, List[DefectCategory]] = {
    EquipmentFamily.ENGINES_TURBINES: [
        DefectCategory.CRACK,
        DefectCategory.CHIPPING_FRACTURE,
        DefectCategory.EROSION,
        DefectCategory.CORROSION,
        DefectCategory.PITTING,
        DefectCategory.SCORING_SCRATCH,
        DefectCategory.DEPOSIT_FOULING,
        DefectCategory.FOREIGN_OBJECT_DAMAGE,
        DefectCategory.DEFORMATION,
        DefectCategory.THERMAL_DISCOLORATION,
        DefectCategory.OTHER_DEFECT,
        DefectCategory.UNKNOWN_UNCERTAIN
    ],
    EquipmentFamily.GEARBOXES_TRANSMISSIONS: [
        DefectCategory.CHIPPING_FRACTURE,
        DefectCategory.PITTING,
        DefectCategory.SCORING_SCRATCH,
        DefectCategory.WEAR,
        DefectCategory.CRACK,
        DefectCategory.CORROSION,
        DefectCategory.SURFACE_SPALLING,
        DefectCategory.LUBRICANT_DEBRIS_CONTAMINATION,
        DefectCategory.DEPOSIT_FOULING,
        DefectCategory.OTHER_DEFECT,
        DefectCategory.UNKNOWN_UNCERTAIN
    ],
    EquipmentFamily.OTHER_MECHANICAL_ASSEMBLIES: [
        DefectCategory.CRACK,
        DefectCategory.POROSITY,
        DefectCategory.EROSION,
        DefectCategory.PITTING,
        DefectCategory.SCORING_SCRATCH,
        DefectCategory.DEFORMATION,
        DefectCategory.FOREIGN_OBJECT_DAMAGE,
        DefectCategory.OTHER_DEFECT,
        DefectCategory.UNKNOWN_UNCERTAIN
    ],
    EquipmentFamily.UNKNOWN_EQUIPMENT: [
        DefectCategory.OTHER_DEFECT,
        DefectCategory.UNKNOWN_UNCERTAIN
    ]
}


# Mapping dictionary for third-party public dataset labels
SOURCE_LABEL_TRANSLATION_RULES: Dict[str, Tuple[DefectCategory, MappingConfidence]] = {
    "crack": (DefectCategory.CRACK, MappingConfidence.EXACT_MATCH),
    "fracture": (DefectCategory.CHIPPING_FRACTURE, MappingConfidence.EXACT_MATCH),
    "chipping": (DefectCategory.CHIPPING_FRACTURE, MappingConfidence.EXACT_MATCH),
    "pitting": (DefectCategory.PITTING, MappingConfidence.EXACT_MATCH),
    "pitted_surface": (DefectCategory.PITTING, MappingConfidence.EXACT_MATCH),
    "erosion": (DefectCategory.EROSION, MappingConfidence.EXACT_MATCH),
    "corrosion": (DefectCategory.CORROSION, MappingConfidence.EXACT_MATCH),
    "scratch": (DefectCategory.SCORING_SCRATCH, MappingConfidence.EXACT_MATCH),
    "scratches": (DefectCategory.SCORING_SCRATCH, MappingConfidence.EXACT_MATCH),
    "scoring": (DefectCategory.SCORING_SCRATCH, MappingConfidence.EXACT_MATCH),
    "spalling": (DefectCategory.SURFACE_SPALLING, MappingConfidence.EXACT_MATCH),
    "wear": (DefectCategory.WEAR, MappingConfidence.EXACT_MATCH),
    "fod": (DefectCategory.FOREIGN_OBJECT_DAMAGE, MappingConfidence.EXACT_MATCH),
    "foreign_object_damage": (DefectCategory.FOREIGN_OBJECT_DAMAGE, MappingConfidence.EXACT_MATCH),
    "crazing": (DefectCategory.CRACK, MappingConfidence.SEMANTIC_EQUIVALENT),
    "inclusion": (DefectCategory.POROSITY, MappingConfidence.SEMANTIC_EQUIVALENT),
    "rolled_in_scale": (DefectCategory.DEPOSIT_FOULING, MappingConfidence.SEMANTIC_EQUIVALENT),
    "burn_mark": (DefectCategory.THERMAL_DISCOLORATION, MappingConfidence.SEMANTIC_EQUIVALENT),
    "bent_wire": (DefectCategory.DEFORMATION, MappingConfidence.SEMANTIC_EQUIVALENT),
    "anomaly": (DefectCategory.OTHER_DEFECT, MappingConfidence.PROVISIONAL_INFERRED),
    "defect": (DefectCategory.OTHER_DEFECT, MappingConfidence.PROVISIONAL_INFERRED)
}


def validate_equipment_taxonomy(
    family: EquipmentFamily,
    component: ComponentType,
    defect: DefectCategory
) -> Tuple[bool, Optional[str]]:
    """
    Validate that component type and defect category belong to the declared equipment family context.
    """
    valid_components = EQUIPMENT_COMPONENT_MAP.get(family, [])
    if component not in valid_components:
        return False, f"Component '{component.value}' is not valid for equipment family '{family.value}'."

    valid_defects = EQUIPMENT_DEFECT_MAP.get(family, [])
    if defect not in valid_defects:
        return False, f"Defect '{defect.value}' is not standard for equipment family '{family.value}'."

    return True, None


def translate_source_label(
    raw_label: str,
    target_family: EquipmentFamily = EquipmentFamily.ENGINES_TURBINES
) -> Tuple[DefectCategory, MappingConfidence, str]:
    """
    Translate a third-party source annotation into KeeAInu defect category
    while tracking provenance and translation uncertainty.
    """
    cleaned = raw_label.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in SOURCE_LABEL_TRANSLATION_RULES:
        defect, conf = SOURCE_LABEL_TRANSLATION_RULES[cleaned]
        return defect, conf, f"Mapped '{raw_label}' -> '{defect.value}' ({conf.value})"

    # Fallback to UNKNOWN_UNCERTAIN without guessing
    return DefectCategory.UNKNOWN_UNCERTAIN, MappingConfidence.UNCERTAIN, f"Unmapped source label '{raw_label}' recorded as UNKNOWN_UNCERTAIN."
