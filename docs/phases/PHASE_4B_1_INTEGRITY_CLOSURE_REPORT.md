# KeeAInu Phase 4B.1 — Functional Integrity Closure Report

## 1. Executive Summary & Objective

Phase 4B.1 addresses and closes all functional integrity discrepancies identified during independent source code review of Phase 4B. This phase rigorously enforces honesty, evidence integrity, mathematical validity of evaluation metrics, reviewer authorization on certified defect dispositions, and use-based license gating.

No new product features or AI model training were introduced.

---

## 2. Identified Discrepancies & Corrective Actions

### Issue 1: Simulated Public Discovery
- **Root Cause**: Public catalog providers previously returned static candidate items with ambiguous verification claims, sometimes implying live remote API verification when results were actually curated catalog entries.
- **Correction**:
  - Implemented explicit verification statuses on every candidate record: `LIVE_METADATA_VERIFIED`, `CURATED_LEAD_AWAITING_VERIFICATION`, `PUBLISHER_LINK_VERIFIED_DATA_UNAVAILABLE`, `SOURCE_UNREACHABLE`, `LICENSE_OR_ACCESS_UNKNOWN`.
  - Providers (Hugging Face, Kaggle, Google Dataset Search, AWS Open Data, Data.gov, GitHub Research) now explicitly distinguish verified live assets from curated leads.
  - Google Dataset Search now honestly routes to canonical publisher discovery and live search links without pretending to execute an unauthenticated live API query.

### Issue 2: Fake Public Acquisition Placeholders
- **Root Cause**: `backend/app/modules/acquisition/pipeline.py` previously generated a synthetic placeholder JPEG image and registered it as real acquired public data.
- **Correction**:
  - Completely removed placeholder image generation for external public providers.
  - Public acquisition requests now explicitly and honestly return `MANUAL_ACTION_REQUIRED` status with clear canonical publisher URLs and operator instructions to import archives into `data/internal_imports/`.
  - Added regression test `test_public_acquisition_never_generates_fake_media` verifying that zero files are written and `MANUAL_ACTION_REQUIRED` is recorded.

### Issue 3: Fabricated Evaluation Metrics & Fixed IoU
- **Root Cause**: `evaluator.py` previously contained a fixed fallback mean IoU of `0.78` and did not compute real intersection-over-union across predicted and ground-truth bounding boxes. Additionally, mock evaluation runs set `is_simulated_baseline=False`.
- **Correction**:
  - Removed all hardcoded metric fallbacks.
  - Implemented mathematical IoU computation via `compute_bounding_box_iou(box1, box2)` with exact intersection over union areas. If no bounding boxes are present or support is zero, `mean_iou` is set to `None` with status `UNDEFINED_ZERO_SUPPORT`.
  - Evaluator automatically sets `is_simulated_baseline=True` whenever simulated findings or mock predictions are present.
  - Implemented deterministic dataset manifest hashing (`compute_manifest_hash`) computing reproducible SHA-256 digests over sorted partition contents.

### Issue 4: Missing Reviewer Role Authorization
- **Root Cause**: Defect confirmation transitions permitted arbitrary client-provided names without backend role enforcement.
- **Correction**:
  - Enforced backend authorization in `backend/app/api/findings.py`.
  - Unauthorized roles (`TRAINEE`, `GUEST`, `UNAUTHORIZED`, `ANONYMOUS`, `READONLY`) are rejected with `HTTP 403 Forbidden` on defect confirmation attempts.
  - Certified confirmation requires authorized roles (`LEAD_INSPECTOR`, `NDT_LEVEL_3`, `CHIEF_INSPECTOR`, `AUTHORIZED_REVIEWER`, `CERTIFIED_INSPECTOR`).
  - Added integration regression tests verifying authorization rejection and approval flows.

### Issue 5: Coarse License Gating vs Intended Use Separation
- **Root Cause**: License gating previously treated evaluation, research, and commercial training under a single binary check.
- **Correction**:
  - Separated permission evaluations into fine-grained intended-use gates:
    - `can_discover_metadata(status)`
    - `can_download_media(status)`
    - `can_use_for_evaluation(status)`
    - `can_use_for_noncommercial_research(status)`
    - `can_use_for_commercial_training(status)` (strictly fails closed for non-commercial or unreviewed licenses)
    - `can_redistribute(status)`
  - Added unit tests covering all permutations in `test_relevance_and_licenses.py` and `test_phase_4b_1_integrity.py`.

---

## 3. Real Provider Capabilities Matrix

| Provider ID | Provider Name | Verification Status | Download Support | Acquisition Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `internal_storage` | Internal Vault & Ingest | `LIVE_METADATA_VERIFIED` | `DIRECT_DOWNLOAD_SUPPORTED` | Safe local copy & profiling |
| `synthetic_generator` | Procedural Defect Studio | `LIVE_METADATA_VERIFIED` | `DIRECT_DOWNLOAD_SUPPORTED` | Procedural synthesis with `is_synthetic=True` |
| `huggingface` | Hugging Face Datasets | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to canonical Hugging Face URL |
| `kaggle` | Kaggle Datasets | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to Kaggle dataset repository |
| `google_dataset_search` | Google Dataset Search | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to Google search query & landing page |
| `aws_open_data` | AWS Open Data Registry | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to AWS S3 open data registry |
| `datagov` | Data.gov / OGD India | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to federal open data catalog |
| `github_research` | GitHub Research Repos | `CURATED_LEAD_AWAITING_VERIFICATION` | `MANUAL_ACTION_REQUIRED` | Directs to GitHub academic source code |

---

## 4. Verification Evidence

### Backend Tests:
- **Command**: `python -m pytest backend/tests -v`
- **Result**: `92 passed, 2 warnings in 175.23s` (100% pass rate)
- **New Regression Tests**:
  - `test_public_acquisition_never_generates_fake_media` (PASSED)
  - `test_true_spatial_box_iou_calculation` (PASSED)
  - `test_deterministic_manifest_hash` (PASSED)
  - `test_evaluation_pipeline_marks_simulated_baseline_honestly` (PASSED)
  - `test_reviewer_authorization_on_defect_confirmation` (PASSED)
  - `test_intended_use_license_permissions_isolation` (PASSED)

### Frontend Build:
- **Command**: `npm run build` (in `frontend/`)
- **Result**: Vite production build succeeded in 4.75s with 0 TypeScript/compilation errors.

---

## 5. Remaining Limitations & Boundaries
- Automated API downloading with user API tokens (e.g. Kaggle API keys, Hugging Face tokens) is intentionally deferred; operators currently utilize manual ingestion into `data/internal_imports/`.
- No real AI models or weights are bundled in this phase; all baseline detections remain transparently marked with `is_simulated=True`.
