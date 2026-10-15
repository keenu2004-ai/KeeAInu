# KeeAInu Defect Taxonomy & Class Resolution Contract

**Date**: 2026-10-12
**Status**: APPROVED & ENFORCED
**Component**: `backend/app/schemas/taxonomy.py`, `backend/app/modules/taxonomy/taxonomy_manager.py`, `backend/app/modules/evaluation/exporter.py`

---

## 1. Executive Summary & Architectural Motivation

In industrial videoscope inspection, collapsing distinct physical degradation modes into generic catch-all labels causes severe real-world failure:
- **Silent collapse degrades model specificity**: Treating thermal fatigue crazing (`THERMAL_CRACKING`) as general structural fatigue (`CRACK`) conceals high-temperature operating risks.
- **Conflating surface oxidation with localized pitting**: Treating cavity-forming localized micro-corrosion (`PITTING`) as uniform oxidation (`CORROSION` or `RUSTING`) masks catastrophic stress-riser conditions.
- **Misclassifying deposits as permanent defects**: Conflating removable soot or foreign particulate (`DIRT`) with permanent metal oxidation (`CORROSION` / `RUSTING`) or structural flaking (`CHIPPING`) triggers costly, unnecessary component teardowns.

Under KeeAInu engineering standards and user guidelines, the taxonomy explicitly separates these degradation modes across all equipment families (`ENGINES_TURBINES`, `GEARBOXES_TRANSMISSIONS`, `OTHER_MECHANICAL_ASSEMBLIES`).

---

## 2. Distinct Mechanical Defect Taxonomy

The table below documents the resolved defect classifications, their physical failure mechanisms, and their explicit mapping guarantees:

| Defect Class | Physical Degradation Description | Distinct From | Translation Rule | YOLO Class Isolation |
| :--- | :--- | :--- | :--- | :--- |
| **`CRACK`** | Structural, mechanical, or fatigue fracture propagating through component parent material. | `THERMAL_CRACKING`, `CHIPPING_FRACTURE` | `"crack" -> CRACK (EXACT_MATCH)` | Retains distinct index; never merged. |
| **`THERMAL_CRACKING`** | Fine micro-crazing and thermal fatigue cracks induced by cyclic thermal expansion and cooling. | `CRACK`, `THERMAL_DISCOLORATION` | `"thermal_cracking", "thermal_crack" -> THERMAL_CRACKING (EXACT_MATCH)` | Retains distinct index; never collapsed into `CRACK`. |
| **`CHIPPING`** | Localized spalling, flaking, or missing material edge along coated or thin-walled surfaces. | `CHIPPING_FRACTURE`, `SURFACE_SPALLING`, `FOREIGN_OBJECT_DAMAGE` | `"chipping" -> CHIPPING (EXACT_MATCH)` | Retains distinct index; coating/edge flaking isolated. |
| **`CORROSION`** | Chemical or electrochemical oxidation / material loss across base metal alloys. | `RUSTING`, `PITTING`, `DIRT` | `"corrosion" -> CORROSION (EXACT_MATCH)` | Base chemical degradation; not collapsed with rust. |
| **`RUSTING`** | Ferrous oxide accumulation specific to iron/steel surfaces. | `CORROSION`, `DIRT`, `DEPOSIT_FOULING` | `"rust", "rusting" -> RUSTING (EXACT_MATCH)` | Distinct ferrous oxidation marker; never merged with chemical corrosion. |
| **`PITTING`** | Highly localized, deep cavity-forming galvanic or chemical attack acting as stress risers. | `CORROSION`, `EROSION`, `POROSITY` | `"pitting", "pitted_surface" -> PITTING (EXACT_MATCH)` | High-criticality cavity defect; strictly segregated. |
| **`DIRT`** | Removable external particulate, loose dust, carbon soot, or oily debris. | `CORROSION`, `RUSTING`, `DEPOSIT_FOULING` | `"dirt", "soot" -> DIRT (EXACT_MATCH)` | Removable surface fouling; never marked as certified defect. |

---

## 3. Canonical Export Class Mapping

When exporting versioned YOLO datasets (`DatasetExporter.export_yolo`), class IDs are either:
1. Enforced via canonical target class list:
   ```python
   canonical = [
       "CRACK",
       "CORROSION",
       "PITTING",
       "CHIPPING",
       "DIRT",
       "RUSTING",
       "THERMAL_CRACKING"
   ]
   ```
2. Or derived deterministically using sorted unique classes in eligible ground truth.

Unmapped classes raise `InvalidAnnotationError` rather than silently assigning unpredictable class IDs or corrupting label indices.

---

## 4. Verification & Invariant Enforcement

1. **Enum Strictness**: All defect classes are explicitly declared in `DefectCategory` (`backend/app/schemas/taxonomy.py`).
2. **Equipment Compatibility**: Verified via `validate_equipment_taxonomy()` in `taxonomy_manager.py`.
3. **Translation Certainty**: Verified via `translate_source_label()`.
4. **Automated Regression Suite**:
   - `test_source_label_translation_and_uncertainty` (`backend/tests/unit/test_taxonomy_and_evaluation.py`)
   - `test_target_classes_fixed_ordering_and_rejection` (`backend/tests/unit/test_dataset_exporter.py`)
