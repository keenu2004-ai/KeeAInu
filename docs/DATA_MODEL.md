# KeeAInu — Data Model & Schema Specification

**Version**: 1.0.0  
**Storage**: Relational / SQL-backed schema (SQLite for local dev, PostgreSQL for production)

---

## 1. Entity-Relationship Diagram

```mermaid
erDiagram
    SITE ||--o{ ASSET : contains
    ASSET ||--o{ INSPECTION_SESSION : undergoes
    INSPECTION_SESSION ||--o{ MEDIA_ASSET : records
    MEDIA_ASSET ||--o{ AI_FINDING : detects
    AI_FINDING ||--o| REVIEW_DECISION : verified_by
    INSPECTION_SESSION ||--o{ AUDIT_LOG : tracks
    INSPECTION_SESSION ||--o{ REPORT : generates

    SITE {
        uuid id PK
        string name
        string location
        datetime created_at
    }

    ASSET {
        uuid id PK
        uuid site_id FK
        string serial_number
        string asset_type
        string name
        jsonb metadata
        datetime created_at
    }

    INSPECTION_SESSION {
        uuid id PK
        uuid asset_id FK
        string inspector_name
        string status
        string videoscope_model
        datetime started_at
        datetime completed_at
    }

    MEDIA_ASSET {
        uuid id PK
        uuid session_id FK
        string media_type
        string file_path
        string sha256_hash
        int width
        int height
        float duration_seconds
        int total_frames
        float fps
        datetime created_at
    }

    AI_FINDING {
        uuid id PK
        uuid media_id FK
        int frame_index
        float timestamp_ms
        string defect_class
        float confidence_score
        jsonb bbox_normalized
        jsonb polygon_mask
        string model_name
        string model_version
        boolean is_simulated
        datetime created_at
    }

    REVIEW_DECISION {
        uuid id PK
        uuid finding_id FK
        string decision_status
        string severity
        string inspector_notes
        jsonb adjusted_bbox
        string reviewer_id
        datetime reviewed_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid session_id FK
        string action
        string entity_type
        uuid entity_id
        jsonb details
        string performed_by
        datetime timestamp
    }

    REPORT {
        uuid id PK
        uuid session_id FK
        string report_number
        string pdf_path
        string json_path
        string sha256_hash
        datetime generated_at
    }
```

---

## 2. Status Enums & Taxonomies

### 2.1 Inspection Session Status
- `DRAFT`: Session initiated, footage upload/processing underway.
- `IN_REVIEW`: Video processed, inspector actively analyzing and reviewing findings.
- `COMPLETED`: Review finished, session signed off and locked against modifications.
- `ARCHIVED`: Historical session.

### 2.2 Finding Review Status
- `PENDING_REVIEW`: Raw candidate finding detected by AI; not yet reviewed by engineer.
- `CONFIRMED`: Engineer validated defect presence and classification.
- `ADJUSTED`: Engineer modified bounding box, classification, or notes.
- `REJECTED`: Engineer rejected false positive finding.
- `MANUAL_ADD`: Finding directly created by engineer without prior AI detection.

### 2.3 Candidate Defect Taxonomy (Industrial Videoscope Domain)
- `CRACK`: Linear surface fissures or fracture lines.
- `CORROSION`: Surface oxidation, pitting, or rust buildup.
- `WEAR`: Material loss due to friction or abrasion.
- `DEPOSIT`: Foreign material accumulation, slag, or carbon buildup.
- `BLOCKAGE`: Internal obstruction within tube, pipe, or conduit.
- `DEFORMATION`: Mechanical bending, denting, or structural warping.
- `SURFACE_DAMAGE`: Scratches, gouges, or heat discoloration.
