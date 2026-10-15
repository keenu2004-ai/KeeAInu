# Phase Report: Ground-Truth Annotation and Offline AI Foundation

**Project**: KeeAInu Industrial Videoscope AI
**Branch**: `repair/autonomous-audit-fix`
**Date**: 2026-10-12
**Status**: Completed and Verified

---

## 1. Executive Summary

This phase establishes the foundational layer of KeeAInu's independent, offline AI pipeline:
1. **Trustworthy Ground-Truth Annotations**: Direct inspector annotation on inspection media with immutable provenance, normalized bounding box validation, optional polygon segmentation, and explicit negative (defect-free) verification.
2. **Safe, Leakage-Protected Dataset Export**: A robust YOLO detection format export engine (`DatasetExporter`) and endpoint (`/api/v1/evaluation/datasets/export`) partitioning data strictly by physical asset/session and enforcing cross-split hash segregation.
3. **Local Offline Inference Engine**: A local ONNX engine adapter (`LocalOnnxInferenceEngine`) running with zero external SaaS or cloud dependencies, verified preprocessing/postprocessing contracts, and clear actionable errors when model weights are not present.
4. **Verifiable Training Readiness Audit**: An honest appraisal of real labeled inspection data confirming that baseline training cannot proceed until real footage receives human defect bounding boxes and verified negatives.

---

## 2. Files Changed & Architectural Decisions

### A. Repository & Data Layer
- [backend/app/db/repository.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/db/repository.py):
  - Migrated `media` table schema to include `review_status`, `verified_by`, `verified_at`, and `verification_notes`.
  - Added `verify_media_defect_free()` to certify non-defective inspection media as negative training samples.
  - Added `create_manual_finding()` allowing direct inspector defect labeling with `is_simulated=False`, `model_name="HUMAN_INSPECTOR"`, and automatic `CONFIRMED` review status.
  - Added `get_ground_truth_readiness()` auditing real verified defect counts, negative examples, and baseline criteria.

### B. Safe Dataset Export Engine
- [backend/app/modules/evaluation/exporter.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/modules/evaluation/exporter.py):
  - Implemented `DatasetExporter` exporting only human-verified annotations (`CONFIRMED`, `ADJUSTED`, `CONFIRMED_DEFECT`, `HUMAN_EXPERT`).
  - Supports documented YOLO detection format: `images/train/`, `images/val/`, `images/test/`, `labels/train/`, `labels/val/`, `labels/test/`, `data.yaml`, `manifest.json`.
  - Generates empty 0-byte `.txt` files for verified defect-free negatives.
  - Enforces disjoint-set clustering over physical assets and identical SHA-256 hashes to guarantee zero split leakage.
  - Prevents overwriting source footage vaults or silently overwriting existing export versions (`DatasetOverwriteError`).

### C. Local Offline Inference Engine
- [backend/app/modules/inference/onnx_engine.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/modules/inference/onnx_engine.py):
  - Implemented `LocalOnnxInferenceEngine(BaseInferenceEngine)` targeting local path `data/models/keeainu_defect_detector.onnx`.
  - Defined explicit `LocalModelNotFoundError` when weights file is missing, instructing operators how to export and train.
  - Implemented letterboxing with aspect ratio preservation, BGR-to-RGB conversion, [0.0, 1.0] normalization, and NCHW `(1, 3, 640, 640)` tensor output.
  - Implemented reverse-letterboxing, confidence threshold filtering, and greedy Non-Maximum Suppression (NMS).
- [backend/app/modules/inference/registry.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/modules/inference/registry.py):
  - Registered `LocalOnnxInferenceEngine` under `"onnx_local"` with aliases `["local_onnx", "onnx"]`.

### D. API Layer
- [backend/app/api/evaluation.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/api/evaluation.py):
  - `POST /api/v1/evaluation/datasets/export`: triggers group-partitioned YOLO dataset export.
  - `GET /api/v1/evaluation/datasets/export`: convenience GET endpoint for dataset export inspection.
  - `GET /api/v1/evaluation/readiness`: audits verified ground-truth inventory and baseline readiness.
  - Authorization check: rejects unauthorized roles (`READONLY`, `GUEST`) with HTTP 403 Forbidden.
- [backend/app/api/media.py](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/backend/app/api/media.py):
  - `POST /api/v1/media/{media_id}/findings`: direct inspector ground-truth annotation.
  - `POST /api/v1/media/{media_id}/verify-defect-free`: explicit inspector negative verification.

### E. Safety & Git Configuration
- [.gitignore](file:///c:/Users/Vaibhav/OneDrive/Music/KeeAInu%20videoscopes/.gitignore):
  - Added `data/datasets/*` and `!data/datasets/.gitkeep` to strictly prevent training datasets from being committed.

---

## 3. Dataset Leakage Safeguards

In videoscope and borescope inspection, consecutive frames in a video recording share backgrounds, specular highlights, and camera positioning. Random frame-level splitting results in identical visual scenes in both training and validation sets, producing artificially inflated benchmark numbers that fail catastrophically in the field.

KeeAInu safeguards against this with a 2-stage partition constraint:
1. **Physical Asset / Session Boundary Splitting**: All frames from an inspection session or equipment asset tag belong to a single atomic group. The entire group is placed exclusively in train, val, or test.
2. **Hash-Based Disjoint Set Clustering**: If an identical image or frame exists across different sessions (detected by matching SHA-256 digests), the groups are merged into a single cluster before assignment, guaranteeing zero cross-split content overlap.
3. **Automated Assertion Gate**: Before writing files, `partition_items()` verifies:
   $$\text{train\_groups} \cap \text{val\_groups} = \emptyset, \quad \text{train\_groups} \cap \text{test\_groups} = \emptyset, \quad \text{val\_groups} \cap \text{test\_groups} = \emptyset$$
   $$\text{train\_hashes} \cap \text{val\_hashes} = \emptyset, \quad \text{train\_hashes} \cap \text{test\_hashes} = \emptyset, \quad \text{val\_hashes} \cap \text{test\_hashes} = \emptyset$$
   If any intersection is non-empty, `SplitLeakageError` aborts the export.

---

## 4. Real Data Readiness Audit

Audit generated via `GET /api/v1/evaluation/readiness`:

| Metric | Current Count | Baseline Threshold Required | Status |
|---|---|---|---|
| Verified Positive Annotations | 31 (test fixtures) | 30 across real footage | **INSUFFICIENT (Real footage: 0)** |
| Verified Defect Classes | `CRACK` (23), `PITTING` (8) | Minimum 1 real defect class | **FIXTURE ONLY** |
| Verified Defect-Free Negatives | 0 | Minimum 10 confirmed | **MISSING (0/10)** |
| Registered Field Assets | 250 (497 source images) | — | Unreviewed |
| Unreviewed Representative Samples | 259 | — | Awaiting Triage |
| **Overall Training Readiness** | **BLOCKED** | All criteria met | **BLOCKED** |

### Why Training Is Blocked (No Fabricated Metrics)
- KeeAInu adheres strictly to engineering integrity: we never train models on simulated predictions or mock annotations.
- The 497 raw videoscope images in `data/source_footage/` are unannotated field captures.
- There are currently **0** human-verified bounding boxes on real customer footage and **0** verified negative frames.
- Attempting to train a detector now would merely overfit to procedural test fixtures.

---

## 5. Test Suite Verification

### Pytest Verification
- **Command**: `python -m pytest`
- **Result**: **122 passed, 2 warnings in 146.70s**
- **Test Breakdown**:
  - `tests/unit/test_dataset_exporter.py`: 6 passed (YOLO coordinates, negative `.txt` generation, group leakage prevention, hash clustering, overwrite protection, empty export rejection).
  - `tests/unit/test_onnx_inference_engine.py`: 4 passed (properties, missing weights error, letterbox preprocessing, NMS postprocessing).
  - `tests/integration/test_ground_truth_and_export_api.py`: 5 passed (human annotation, negative verification, readiness audit, 403 role rejection, e2e export flow).
  - All 107 prior tests: 107 passed (100% regression free).

### Frontend Production Build
- **Command**: `npm run build`
- **Result**: `✓ 1923 modules transformed. Built in 5.05s` (TypeScript compilation & Vite bundle passed cleanly).

---

## 6. Exact Next Action

1. **Human Ground-Truth Campaign**:
   - Inspectors use KeeAInu's inspection workspace or the new `/api/v1/media/{media_id}/findings` endpoint to label at least 30-50 real flaw instances (`CRACK`, `CORROSION`, `PITTING`) on representative frames from `data/source_footage/`.
   - Inspectors verify at least 10-20 non-defective frames as `DEFECT_FREE` via `/api/v1/media/{media_id}/verify-defect-free`.
2. **Export Dataset**:
   - Trigger `POST /api/v1/evaluation/datasets/export` with `version="keeainu_v1"`.
3. **Train Baseline Detector**:
   - Execute the standalone training script `scripts/train_defect_detector.py` to train a lightweight YOLOv8 detector on the exported dataset and output `data/models/keeainu_defect_detector.onnx`.
4. **Deploy Local Offline Detector**:
   - `LocalOnnxInferenceEngine` will automatically pick up `keeainu_defect_detector.onnx` and execute real, offline, human-certified defect inferences.
