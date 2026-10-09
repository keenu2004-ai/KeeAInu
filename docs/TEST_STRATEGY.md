# KeeAInu — Test & Verification Strategy

**Version**: 1.0.0  
**Status**: Active  

---

## 1. Test Pyramid & Gate Hierarchy

```
        /  E2E Inspection  \      -> Cypress / Playwright (Full workflow)
       /  Integration Tests \     -> Pytest + FastAPI TestClient + SQLite
      /   Deterministic AI   \    -> Mock & ONNX Engine Evaluation
     / Unit Tests & Validation\   -> Fast Unit Tests (Ingestion, Hashing, Codecs)
    ----------------------------
```

### 1.1 Unit Tests (`backend/tests/unit/`, `frontend/src/**/*.test.ts`)
- Cryptographic hash computation and validation.
- Video container parsing and metadata extraction.
- Coordinate transformations (normalized bounding box to pixel coordinates).
- Ingestion security checks (magic bytes, path traversal rejection, size limit enforcement).

### 1.2 Integration Tests (`backend/tests/integration/`)
- API endpoints: Upload media, create session, retrieve frames, run inference, confirm findings, export reports.
- Database persistence and transaction rollbacks.
- Media store read/write sandboxing.

### 1.3 Deterministic AI & Inference Tests (`backend/tests/inference/`)
- Test `MockInferenceEngine` produces reproducible output fixtures for given seed frames.
- Test engine switching without breaking API contracts.
- Validate `is_simulated` flag propagation.

### 1.4 End-to-End Inspection Workflow Tests
- Ingest sample video fixture -> Step through timeline -> Verify overlay rendering -> Confirm finding -> Generate PDF report.

---

## 2. Release & Acceptance Gates

Every release and milestone must satisfy:
1. **Pass all unit and integration tests** (`pytest` exits with code 0).
2. **Clean linting & type checks** (`mypy` / `ruff` for Python, `tsc` for TypeScript).
3. **Zero security secrets detected** in git tree.
4. **No regression on deterministic benchmark test suite**.
