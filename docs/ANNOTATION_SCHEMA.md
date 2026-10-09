# KeeAInu — Annotation Schema & Metadata Specification

**Schema Version**: `1.0.0`  
**Status**: Active  
**Domain**: Remote Visual Inspection (RVI) & Videoscope Intelligence  

---

## 1. Overview & Principles

The KeeAInu Annotation Schema defines a versioned, machine-readable format for representing ground-truth annotations and inspection datasets.

### Strict Separation: Ground Truth vs. Inference Output
- **Ground-Truth Annotations (`GroundTruthAnnotationRecord`)**: Represent certified, human-verified, or synthetically controlled benchmark labels for training and testing.
- **Inference Outputs (`FrameInferenceResult`)**: Represent candidate predictions generated dynamically by AI/CV models.
- **Non-Negotiable**: Ground truth and model predictions are stored in distinct data structures and must never be merged into an ambiguous format.

---

## 2. Coordinate System Specification

KeeAInu standardizes on **Normalized Coordinates** for all 2D bounding boxes:

```
(0.0, 0.0) --------------------- (1.0, 0.0)
     |                                 |
     |         [x_min, y_min]          |
     |               +-------+         |
     |               |  BBOX |         |
     |               +-------+         |
     |                      [x_max, y_max]
     |                                 |
(0.0, 1.0) --------------------- (1.0, 1.0)
```

- **`x_min`**: Horizontal start coordinate, normalized to $[0.0, 1.0]$.
- **`y_min`**: Vertical start coordinate (from top), normalized to $[0.0, 1.0]$.
- **`x_max`**: Horizontal end coordinate, normalized to $[0.0, 1.0]$.
- **`y_max`**: Vertical end coordinate, normalized to $[0.0, 1.0]$.
- **Validation Invariants**:
  $$0.0 \le x_{\text{min}} < x_{\text{max}} \le 1.0$$
  $$0.0 \le y_{\text{min}} < y_{\text{max}} \le 1.0$$

---

## 3. Data Schema (JSON Schema v1.0.0)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "KeeAInuGroundTruthDataset",
  "version": "1.0.0",
  "type": "object",
  "required": [
    "schema_version",
    "dataset_id",
    "media_id",
    "media_sha256",
    "provenance",
    "annotations"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "dataset_id": {
      "type": "string",
      "description": "Unique identifier of the dataset or benchmark run"
    },
    "media_id": {
      "type": "string",
      "description": "Unique identifier of the source video or image"
    },
    "media_sha256": {
      "type": "string",
      "pattern": "^[a-f0-9]{64}$",
      "description": "SHA-256 cryptographic digest of the source media file"
    },
    "media_filename": {
      "type": "string"
    },
    "image_width": {
      "type": "integer",
      "minimum": 1
    },
    "image_height": {
      "type": "integer",
      "minimum": 1
    },
    "provenance": {
      "type": "string",
      "enum": ["SYNTHETIC_GENERATED", "HUMAN_VERIFIED", "EXPERT_AUDITED"]
    },
    "is_synthetic": {
      "type": "boolean"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "annotations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "annotation_id",
          "frame_index",
          "timestamp_ms",
          "defect_class",
          "bbox"
        ],
        "properties": {
          "annotation_id": {
            "type": "string"
          },
          "frame_index": {
            "type": "integer",
            "minimum": 0
          },
          "timestamp_ms": {
            "type": "number",
            "minimum": 0.0
          },
          "defect_class": {
            "type": "string",
            "enum": [
              "CRACK",
              "CORROSION",
              "WEAR",
              "DEPOSIT",
              "BLOCKAGE",
              "DEFORMATION",
              "SURFACE_DAMAGE",
              "TEST_PATTERN_CRACK_SYNTHETIC",
              "TEST_PATTERN_GRID_SYNTHETIC"
            ]
          },
          "bbox": {
            "type": "object",
            "required": ["x_min", "y_min", "x_max", "y_max"],
            "properties": {
              "x_min": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "y_min": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "x_max": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "y_max": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
            }
          },
          "polygon_mask": {
            "type": "array",
            "items": {
              "type": "array",
              "minItems": 2,
              "maxItems": 2,
              "items": { "type": "number" }
            }
          },
          "inspector_notes": {
            "type": "string"
          },
          "metadata": {
            "type": "object"
          }
        }
      }
    }
  }
}
```

---

## 4. Synthetic Data Labeling Rules

- Any synthetic pattern created for testing (e.g. drawn lines, checkerboards, calibration grids) must use `provenance = "SYNTHETIC_GENERATED"` and `is_synthetic = true`.
- Defect classes for synthetic patterns must use the `TEST_PATTERN_*_SYNTHETIC` naming convention (e.g., `TEST_PATTERN_CRACK_SYNTHETIC`).
- Synthetic fixtures must never be used to claim real-world model accuracy or certification.
