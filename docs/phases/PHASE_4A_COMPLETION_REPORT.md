# KeeAInu Phase 4A Completion Report — Domain-Agnostic Dataset Discovery & Profiling

**Date**: October 9, 2026  
**Status**: Completed  
**Repository**: [https://github.com/keenu2004-ai/KeeAInu](https://github.com/keenu2004-ai/KeeAInu)  
**Starting Commit**: `4e7a9a2` (verified base on `main`)  

---

## 1. Executive Summary & Objective

In Phase 4A, KeeAInu established an end-to-end, domain-agnostic media discovery, repeatable inventorying, visual sampling, and explainable quality profiling pipeline. 

When videoscope footage is acquired in the field, its inspection domain (mechanical components, pipes/channels, mould cavities, or other industrial cavities) and defect status are initially unknown. Rather than forcing footage into premature or arbitrary classifications, Phase 4A provides a human-guided profiling workflow that extracts visual evidence, generates contact sheets, computes transparent heuristic indicators, and records human reviewer provenance.

### Core Architectural Guarantees:
1. **Strict Evidence Immutability**: Original raw footage files are never altered or overwritten. Frame hashes, source SHA-256 digests, and extraction metadata are tracked immutably.
2. **Strict Boundary & Sandboxing**: Discovery scanner enforces path sandboxing (`is_path_safe`) to prevent path traversal and symlink escapes.
3. **No Unwarranted Real AI**: No machine learning model weights, YOLO detectors, or heuristic auto-defect conclusions are introduced. Explainable heuristics (Laplacian variance, brightness/contrast, over/underexposure ratios) are explicitly documented as diagnostic aids rather than engineering conclusions.
4. **Data Isolation & Synthetic Fixture Separation**: Synthetic test fixtures are strictly distinguished (`is_synthetic=True`) from real user footage (`is_synthetic=False`).

---

## 2. Implemented Components & Architecture

### Backend Modules (`backend/app/`)
- **`app/core/config.py`**: Added `SOURCE_FOOTAGE_DIR` (`data/source_footage`), `SAMPLES_DIR` (`data/media/derived/samples`), and `CONTACT_SHEETS_DIR` (`data/media/derived/contact_sheets`).
- **`app/schemas/discovery.py`**: Pydantic schemas for domain categories (`MECHANICAL`, `PIPES_CHANNELS`, `MOULD_CAVITIES`, `OTHER`, `UNKNOWN`), sample defect review states (`UNREVIEWED`, `NO_VISIBLE_DEFECT`, `SUSPECTED_ANOMALY`, `CONFIRMED_DEFECT`, `UNCERTAIN_NEEDS_EXPERT`, `UNUSABLE`), quality profiles, and dataset manifests.
- **`app/db/repository.py`**: SQLite tables `dataset_assets` and `dataset_samples` with idempotent upserting and review audit tracking.
- **`app/modules/discovery/profiler.py`**:
  - `compute_frame_quality_metrics`: Computes Laplacian variance for sharpness, pixel mean/std dev for lighting, and over/underexposure percentages.
  - `compute_near_duplicate_ratio`: Frame stability indicator across sampled indices.
  - `generate_contact_sheet`: Generates an ordered visual mosaic grid of representative frame thumbnails.
- **`app/modules/discovery/scanner.py`**:
  - `scan_source_directories`: Safely scans configured storage directories, computing SHA-256 digests, probing video streams via OpenCV, and saving extracted representative frames.
- **`app/api/discovery.py`**: FastAPI router providing:
  - `POST /api/v1/discovery/scan` — Scan and inventory configured source directories.
  - `GET /api/v1/discovery/assets` — Filterable inventory list (by domain, synthetic status).
  - `GET /api/v1/discovery/assets/{asset_id}` — Single asset detail with samples & quality metrics.
  - `GET /api/v1/discovery/assets/{asset_id}/contact-sheet` — Direct PNG mosaic serving.
  - `GET /api/v1/discovery/samples/{sample_id}/content` — Sample frame image serving.
  - `PATCH /api/v1/discovery/assets/{asset_id}/domain` — Human domain classification & notes.
  - `PATCH /api/v1/discovery/samples/{sample_id}/review` — Frame-level defect status triage.
  - `GET /api/v1/discovery/report` — Measured dataset discovery summary.
  - `GET /api/v1/discovery/manifest` — Machine-readable dataset manifest for training/eval readiness.

### Frontend UI (`frontend/src/`)
- **`src/types/discovery.ts`** & **`src/services/api.ts`**: Complete typed client definitions for discovery endpoints.
- **`src/components/DatasetDiscoveryView.tsx`**:
  - Top metrics summary cards (Total Assets, Synthetic vs Real, Domain Distribution, Review Progress).
  - Directory Scanner trigger with status alerts.
  - Asset gallery with contact sheet thumbnails, quality badges, and domain indicators.
  - Slide-out Detail Drawer displaying explainable quality indicators, full contact sheet, representative frame gallery, human domain assignment dropdown, and per-sample defect review triage buttons.
  - Discovery Report & Manifest Modal for viewing summary metrics and training evaluation guidelines.
- **`src/components/Header.tsx`** & **`src/App.tsx`**: Tabbed navigation between *Inspection Sessions* and *Dataset Discovery & Profiling*.

---

## 3. Footage Ingestion & User Instructions

If no real footage is currently found in the application repository:
1. **Target Directory**: Place raw videoscope recordings (`.mp4`, `.avi`, `.mov`, `.mkv`, `.jpg`, `.png`) into:
   ```
   data/source_footage/
   ```
2. **Trigger Scan**:
   - In the Web UI: Click **Scan Storage Directories** in the Dataset Discovery tab.
   - Via API: `POST /api/v1/discovery/scan`
3. **Data Safety**:
   - `data/source_footage/` is ignored in `.gitignore` to prevent proprietary inspection footage from ever being committed to Git.
   - Files placed in `data/source_footage/` are classified as `is_synthetic=False` (Real Inspection Footage).

---

## 4. Verification & Test Evidence

### Backend Tests:
- **Integration Tests**: `test_discovery_api.py` (scan execution, domain assignment, frame review, report/manifest generation).
- **Unit Tests**: `test_profiler.py` (sharpness, exposure, near-duplicate analysis, contact sheet generation).
- **Security Tests**: Path traversal checks, symlink escapes, missing metadata handling, corrupted media tolerance.
- **Suite Result**: 57 passed tests across `backend/tests`.

### Frontend Production Build:
- `tsc && vite build`: Successful production bundle generated (`dist/assets/index-*.js`, `dist/assets/index-*.css`) with zero TypeScript errors.

---

## 5. Domain Comparison & Evaluation Readiness

| Candidate Domain | Key Visual Indicators | Key Ambiguities / Counter-Evidence |
| :--- | :--- | :--- |
| **Mechanical Components** (Engines, Turbines, Gearboxes) | Blading, gears, machined faces, carbon deposits, combustion residue. | Dark cavities without recognizable blading geometry can be confused with general castings. |
| **Pipes and Channels** (Tubes, Internal lines) | Cylindrical symmetry, weld seams, longitudinal scale/rust, pitting. | Curved mould cooling passages can look nearly identical without engineering drawings. |
| **Mould Cavities & Channels** | Complex geometric tooling, milled surfaces, parting lines, cooling passages. | Smooth channel surfaces can resemble industrial piping. |
| **Other / Unknown** | Indeterminate geometry, low lighting, heavy obstruction. | Requires human inspection review; never force-classified. |

### Evaluation Split Recommendation for Next Phase (Phase 4B):
- **Never perform random frame-level train/test splits**: Neighboring frames in video inspections share background, lighting, and camera perspective, causing data leakage.
- **Group splits strictly by `source_asset_id` or physical inspection session**.
