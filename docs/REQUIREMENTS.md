# KeeAInu — System Requirements Specification

**Version**: 1.0.0  
**Status**: Approved Foundation Scope  
**Domain**: Remote Visual Inspection (RVI) & Videoscope Intelligence

---

## 1. Functional Requirements

### 1.1 Media Ingestion & Evidence Preservation (FR-INGEST)
- **FR-INGEST-01**: Support drag-and-drop and file-picker ingestion for recorded videos (`.mp4`, `.avi`, `.mov`, `.mkv`) and still images (`.jpg`, `.png`, `.bmp`).
- **FR-INGEST-02**: Compute cryptographic hash (SHA-256) on upload to guarantee evidence immutability.
- **FR-INGEST-03**: Extract and store video container metadata (resolution, frame rate, total duration, frame count, codec).
- **FR-INGEST-04**: Validate file signatures, MIME types, and maximum payload limits before processing to prevent malicious uploads.
- **FR-INGEST-05**: Maintain original media in a dedicated read-only storage directory; derived artifacts (thumbnails, downscaled proxies, annotations) must be stored in separate namespaces.

### 1.2 Inspection Playback & Frame Navigation (FR-VIEW)
- **FR-VIEW-01**: Provide high-performance, frame-accurate video playback (1x, 0.5x, 0.25x, 2x speeds).
- **FR-VIEW-02**: Support frame-by-frame stepping (previous frame / next frame) and direct jump to timestamp.
- **FR-VIEW-03**: Interactive inspection timeline showing detected anomaly markers, engineer bookmarks, and inspection notes.
- **FR-VIEW-04**: Viewport inspection tools: Digital zoom (1x to 8x), pan, brightness/contrast adjustments, and full-screen inspection mode.
- **FR-VIEW-05**: Canvas-based annotation overlay layer rendering bounding boxes, polygon masks, and measurement rulers.

### 1.3 Pluggable AI Defect Candidate Detection (FR-AI)
- **FR-AI-01**: Pluggable inference interface decoupling detection models from the core application pipeline.
- **FR-AI-02**: Support candidate defect classes (Cracks, Corrosion, Wear, Deposits, Blockage, Deformation, Surface Damage).
- **FR-AI-03**: Real-time / on-demand inference execution per frame or across selected video intervals.
- **FR-AI-04**: Every inference prediction must include: `bbox` / `mask`, `confidence_score` (0.00 to 1.00), `defect_class`, `model_name`, `model_version`, and `timestamp_ms`.
- **FR-AI-05**: Prominent indicators distinguishing real model predictions from simulated/mock outputs.

### 1.4 Human-in-the-Loop Review & Decision Workflow (FR-REVIEW)
- **FR-REVIEW-01**: Inspection engineers can review any candidate defect and transition status: `PENDING_REVIEW` -> `CONFIRMED` | `ADJUSTED` | `REJECTED`.
- **FR-REVIEW-02**: Ability to manually create new defect annotations on any frame.
- **FR-REVIEW-03**: Severity classification (`CRITICAL`, `MAJOR`, `MINOR`, `INFORMATIONAL`) and engineer commentary.
- **FR-REVIEW-04**: Complete audit log recording who changed a finding, the prior state, new state, and timestamp.

### 1.5 Inspection Sessions, History & Asset Registry (FR-ASSET)
- **FR-ASSET-01**: Manage hierarchical asset catalog: `Site` -> `Asset` (e.g. Turbine 4, Boiler Pipe 12) -> `Component` -> `Inspection Sessions`.
- **FR-ASSET-02**: Track historical inspections for each asset to monitor defect progression over time.
- **FR-ASSET-03**: Side-by-side comparison of inspection frames across different dates for the same asset.

### 1.6 Traceable Reporting & Export (FR-REPORT)
- **FR-REPORT-01**: Generate auditable NDT inspection summary reports in PDF and structured JSON formats.
- **FR-REPORT-02**: Reports must include asset metadata, inspector credentials, inspection date/time, original media hashes, model identifiers, confirmed findings with high-res annotated frame captures, and engineering remarks.
- **FR-REPORT-03**: Export standalone evidence packages (zip containing raw footage, annotations JSON, and PDF report).

---

## 2. Non-Functional Requirements

### 2.1 Reliability & Data Integrity (NFR-REL)
- **NFR-REL-01**: Zero data corruption; original inspection media must never be overwritten or mutated.
- **NFR-REL-02**: Graceful error handling for corrupt media files with descriptive error diagnostics.
- **NFR-REL-03**: Reversible database migrations with deterministic schema versions.

### 2.2 Performance (NFR-PERF)
- **NFR-PERF-01**: API response time for session queries and metadata retrieval < 100ms.
- **NFR-PERF-02**: Frame extraction and rendering latency < 50ms for smooth timeline scrubbing.
- **NFR-PERF-03**: Modular inference worker capable of asynchronous batch processing without blocking UI playback.

### 2.3 Security & Compliance (NFR-SEC)
- **NFR-SEC-01**: Zero hard-coded credentials; strict configuration via environment variables.
- **NFR-SEC-02**: Safe media file processing avoiding arbitrary code execution or path traversal vulnerabilities.
- **NFR-SEC-03**: Comprehensive input sanitization on all API routes.
