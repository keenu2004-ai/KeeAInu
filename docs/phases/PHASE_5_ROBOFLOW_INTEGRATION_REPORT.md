# KeeAInu Phase 5 — Roboflow Integration & Vision Validation Report

**Milestone:** Phase 5 — Roboflow Integration and Vision Validation  
**Repository:** `keenu2004-ai/KeeAInu`  
**Status:** Completed & Verified  

---

## 1. Executive Summary

In Phase 5, KeeAInu was extended from simulated mock defect detection into real AI vision integration with the private Roboflow **Videoscope Defect Segmentation** (SAM 3 / Hosted Inference) configuration. 

All engineering requirements were implemented with strict adherence to evidence integrity, privacy gating, reviewer isolation, deterministic caching, and mathematical evaluation transparency.

---

## 2. Completed Architecture & Deliverables

### A. Dedicated Roboflow Adapter (`backend/app/modules/inference/roboflow_client.py`)
- **Backend-Only Client**: Uses `httpx.AsyncClient` with configurable timeout (`ROBOFLOW_TIMEOUT_SECONDS`), retries (`ROBOFLOW_MAX_RETRIES`), and payload size validation (`ROBOFLOW_MAX_IMAGE_SIZE_BYTES`).
- **Privacy Gating**: Cloud inference fails closed with `RoboflowPrivacyError` unless operator consent (`ROBOFLOW_ALLOW_CLOUD_INFERENCE` or `allow_cloud_inference=True`) is explicitly given.
- **Transparent Errors**: Missing keys raise `RoboflowAuthError`, timeouts raise `RoboflowTimeoutError`, and bad gateways raise `RoboflowApiError`. Predictions are **never fabricated** on provider failure.
- **SAM 3 & Polygon Normalization**: Automatically normalizes center-based pixel bounding boxes (`x`, `y`, `w`, `h`) and polygon segmentations (`points: [{"x": ..., "y": ...}]`) into unit floats `[0.0, 1.0]`.

### B. Inference Caching & Frame Sampling (`backend/app/modules/inference/cache.py`)
- **Deterministic Keying**: Caching keys are computed via `SHA-256(evidence_sha256 + engine_name + model_version + confidence_threshold + prompts)`. Results are never cross-contaminated between different prompts or model versions.
- **Cost & Rate Control**: Prevents duplicate cloud calls on retries, and includes `should_sample_frame` to avoid sending redundant adjacent video frames.

### C. Inspection Inference API & Provenance (`backend/app/api/inference.py` & `backend/app/db/repository.py`)
- **API Endpoints**:
  - `POST /api/v1/inference/analyze-frame`: Dispatches to `roboflow` or `mock`, enforcing session consistency, SHA-256 evidence hashing, provenance persistence, and returning normalized findings.
  - `GET /api/v1/inference/engines`: Lists registered vision engines and runtime privacy status.
  - `GET /api/v1/inference/records`: Queries persistent inference run records with full provenance metadata.
  - `GET /api/v1/inference/records/{record_id}`: Retrieves raw and normalized prediction references.
  - `POST /api/v1/inference/cache/clear`: Clears in-memory cache.
- **Database Schema**: Added `inference_records` table and extended `findings` with `polygon_mask_json`, `evidence_sha256`, and `inference_record_id`.

### D. Honest Segmentation Evaluation (`backend/app/modules/evaluation/evaluator.py`)
- **Polygon Mask IoU**: Implemented `compute_polygon_mask_iou` using 2D grid rasterization (`cv2.fillPoly`) to compute true polygon mask IoU for segmentation predictions against ground truth.
- **Ground Truth Integrity**: Strict segregation of real and simulated baseline records.

### E. Frontend Review Interface (`frontend/src/`)
- **Polygon Rendering (`CanvasOverlay.tsx`)**: Renders semi-transparent filled polygon contours alongside corner brackets and tags (`[SAM 3 MASK]` vs `[SIM]`).
- **Vision Controls (`InspectionWorkspace.tsx`)**: Engine selector (`Roboflow SAM 3` vs `Mock Baseline`), prompt editor, confidence threshold, cache toggle, and cloud privacy consent.
- **Provenance Bar**: Displays engine name, model version, latency (ms), cache status, and SHA-256 evidence hash.

---

## 3. Environment Variables

| Variable Name | Description | Default |
| :--- | :--- | :--- |
| `ROBOFLOW_API_KEY` | Private Roboflow API key (backend only, never exposed to client) | `None` |
| `ROBOFLOW_API_URL` | Roboflow Hosted Inference Base URL | `https://infer.roboflow.com` |
| `ROBOFLOW_MODEL_ID` | Model / Workflow ID for Videoscope Defect Segmentation | `videoscope-defect-segmentation/1` |
| `ROBOFLOW_SAM_PROMPTS` | Default SAM 3 prompt labels | `["crack", "pitting", "corrosion", "erosion", "deposit", "mechanical defect"]` |
| `ROBOFLOW_TIMEOUT_SECONDS` | Network timeout for inference API calls | `30.0` |
| `ROBOFLOW_MAX_RETRIES` | Max retries on transient network errors | `2` |
| `ROBOFLOW_CACHE_ENABLED` | Enable deterministic inference result caching | `True` |
| `ROBOFLOW_ALLOW_CLOUD_INFERENCE` | Global privacy gate for transmitting frames to cloud | `False` |
| `ROBOFLOW_MAX_IMAGE_SIZE_BYTES`| Maximum frame buffer size in bytes | `26214400` (25 MB) |
| `ROBOFLOW_RATE_LIMIT_PER_MINUTE`| Maximum outbound requests per minute | `60` |

---

## 4. API Request and Response Examples

### Request: `POST /api/v1/inference/analyze-frame`
```json
{
  "session_id": "sess_8b417c802f1a",
  "media_id": "med_cf1923984d7a",
  "frame_index": 45,
  "confidence_threshold": 0.50,
  "engine": "roboflow",
  "prompts": ["crack", "pitting"],
  "allow_cloud_inference": true,
  "use_cache": true
}
```

### Response: `200 OK`
```json
{
  "inference_record_id": "inf_0e2b69f8c14a",
  "media_id": "med_cf1923984d7a",
  "frame_index": 45,
  "timestamp_ms": 1500.0,
  "engine_name": "roboflow",
  "model_version": "videoscope-defect-segmentation/1",
  "is_simulated": false,
  "evidence_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
  "processing_duration_ms": 142.6,
  "cache_hit": false,
  "findings_count": 1,
  "findings": [
    {
      "id": "fnd_789acde12044",
      "session_id": "sess_8b417c802f1a",
      "media_id": "med_cf1923984d7a",
      "frame_index": 45,
      "timestamp_ms": 1500.0,
      "defect_class": "crack",
      "confidence_score": 0.942,
      "bbox": {
        "x_min": 0.4219,
        "y_min": 0.4306,
        "x_max": 0.5781,
        "y_max": 0.5694
      },
      "polygon_mask": [
        [0.4219, 0.4306],
        [0.5781, 0.4306],
        [0.5781, 0.5694],
        [0.4219, 0.5694]
      ],
      "evidence_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
      "inference_record_id": "inf_0e2b69f8c14a",
      "is_simulated": false,
      "model_name": "roboflow",
      "model_version": "videoscope-defect-segmentation/1",
      "decision_status": "PENDING_REVIEW",
      "severity": "INFORMATIONAL"
    }
  ]
}
```

---

## 5. Verification & Test Evidence

### Backend Test Suite (`pytest backend/tests -v`)
- **Total Tests**: 103 passed, 0 failed, 0 errors.
- **Key Modules Tested**:
  - `backend/tests/unit/test_roboflow_client.py`: 7 tests covering privacy gating, missing API keys, timeout handling, HTTP error handling, normalized coordinate parsing, cache determinism, and frame sampling.
  - `backend/tests/integration/test_roboflow_inference_api.py`: 3 tests covering engine listing, privacy gate blocking (403), and end-to-end inference lifecycle with polygon mask persistence and caching.
  - `backend/tests/unit/test_taxonomy_and_evaluation.py`: polygon mask IoU unit tests.

### Frontend Production Build (`npm run build`)
- **TypeScript**: 0 compiler errors.
- **Vite Production Bundle**: 1923 modules transformed, `dist/assets/index-CQxOueFT.js` (277.55 kB).
