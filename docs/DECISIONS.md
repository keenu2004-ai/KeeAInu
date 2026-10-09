# KeeAInu — Architecture Decision Records (ADRs)

This document tracks foundational architectural decisions, context, consequences, and rationale for the KeeAInu platform.

---

## ADR-0001: Repository Foundation and Branching Model

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: The GitHub repository `keenu2004-ai/KeeAInu` was verified to be empty with no prior history. A robust version control convention is needed from day zero.
- **Decision**: 
  - Use `main` as the default protected branch.
  - Require atomic, testable, and reviewed pull requests or feature branches (`feat/*`, `fix/*`, `docs/*`).
  - Follow Conventional Commits format (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **Consequences**: Ensures clean traceability and continuous delivery readiness.

---

## ADR-0002: Architecture Pattern — Modular Monolith

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: The platform needs video ingestion, media storage, metadata persistence, AI inference execution, and UI workflows. Starting with microservices or distributed queues introduces massive operational overhead and latency for initial stages.
- **Decision**: 
  - Build KeeAInu as a **Modular Monolith** with clear domain boundaries (`ingestion`, `media`, `inference`, `inspection`, `reporting`, `hardware`).
  - Keep modules decoupled via typed service interfaces and domain contracts.
  - If high-throughput async processing is later required, individual modules can be transitioned into worker processes without rewrites.
- **Consequences**: High development speed, single deployment footprint, trivial local testing, and zero distributed system complexity.

---

## ADR-0003: Backend & Computer Vision Core

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Video ingestion, frame extraction, computer vision operations, and machine learning inference require rich scientific and CV ecosystem support.
- **Decision**: 
  - Use **Python (>= 3.11)** with **FastAPI** for high-performance async REST APIs and typed schemas (Pydantic v2).
  - Use **OpenCV (`opencv-python-headless`)** and **`imageio-ffmpeg` / `PyAV`** for programmatic video decoding and frame extraction.
  - Manage Python environments and dependencies with `uv` / standard virtual environments.
- **Consequences**: Direct compatibility with AI/ML libraries (PyTorch, ONNX Runtime), high throughput async endpoints, and automated OpenAPI documentation.

---

## ADR-0004: Frontend User Interface Stack

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Inspection engineers need a responsive, low-latency UI for video playback, timeline scrubbing, bounding box/mask overlays, zoom/pan inspection, and report generation.
- **Decision**: 
  - Use **React 18/19** with **TypeScript** and **Vite** for rapid bundling and fast HMR.
  - Use **Vanilla CSS / Modern CSS Variables & Design Tokens** (dark mode, glassmorphic accents, high-contrast inspection overlays) to deliver a bespoke, high-performance UI without heavy CSS framework bloat.
  - Use HTML5 Canvas / WebGL for frame overlay rendering and defect annotation.
- **Consequences**: Sub-millisecond frame rendering, type safety across API contracts, and no external CSS build lock-ins.

---

## ADR-0005: Pluggable AI Inference Interface & Evidence Integrity

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Defect detection algorithms evolve (YOLO, RT-DETR, Segment Anything, custom PyTorch models, rule-based CV). Hard-coding a single model couples the application and prevents easy benchmarking.
- **Decision**: 
  - Define a formal `InferenceEngine` interface:
    ```python
    class InferenceEngine(ABC):
        @abstractmethod
        async def infer_frame(self, frame: np.ndarray, metadata: FrameMeta) -> InferenceResult: ...
        @abstractmethod
        async def infer_batch(self, frames: List[np.ndarray], metadata: List[FrameMeta]) -> List[InferenceResult]: ...
    ```
  - Implement a `MockInferenceEngine` for deterministic testing and workflow verification.
  - Label all outputs explicitly with `engine_name`, `model_version`, `confidence_threshold`, and `is_simulated: bool`.
  - Raw original media is strictly read-only; annotations and findings are stored as linked vector/JSON metadata referencing specific frame indices and timestamps.
- **Consequences**: Any AI model can be plugged in without changing UI or database code. Zero risk of presenting mock detections as real inferences.

---

## ADR-0006: External Tools & Skills Adoption Strategy

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Evaluated external toolkits: `multica-ai/andrej-karpathy-skills`, `WorldFlowAI/everything-claude-code`, `oraios/serena`, `upstash/context7`.
- **Decision**: 
  - Extract the core engineering principles of Karpathy (simplicity first, surgical edits, goal-driven execution) directly into `AGENTS.md`.
  - Rely on native IDE and builtin tools rather than installing external package dependencies, unverified setup scripts, or third-party MCP servers.
  - Re-evaluate specialized AST tools (e.g., Serena) if codebase scale exceeds 10,000 lines.
- **Consequences**: Zero supply chain attack surface, zero extraneous dependencies, and total reproducibility across developer machines.

---

## ADR-0007: Hardware Compatibility Validation Strategy

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Yateks G, M, Q, B, and P series videoscopes feature different hardware interfaces (HDMI capture, USB-C/UVC, Wi-Fi RTSP streaming, SD Card media import).
- **Decision**: 
  - Provide a clean `HardwareSourceAdapter` contract.
  - Phase 2/3 supports standard recorded media ingestion (MP4, AVI, MOV, MKV, JPG, PNG).
  - Phase 6 introduces verified hardware adapters only after physical documentation and capture card/UVC signal validation.
  - No speculative hardware protocols will be implemented without verified hardware specifications.
- **Consequences**: Eliminates hardware speculation; prevents bugs from untested communication protocols.

---

## ADR-0008: Multi-Source Dataset Discovery & Controlled Acquisition Architecture

- **Status**: Accepted
- **Date**: 2026-10-09
- **Context**: Borescope inspection footage is scarce and varies across candidate domains (Mechanical, Pipes, Mould Cavities). Uncontrolled web scraping, untracked synthetic data, and license ambiguities risk legal violations and data leakage.
- **Decision**:
  - Implement a pluggable `BaseSourceProvider` architecture supporting public catalogs (Hugging Face, Kaggle, Google Dataset Search, Data.gov, AWS Open Data, GitHub Research), internal sandboxed storage, and procedural synthetic generators.
  - Implement an explainable multi-factor relevance scoring engine ($0-100$) that evaluates videoscope visual similarity, domain match, modality, defect utility, annotation quality, and provenance completeness.
  - Enforce a **hard legal license and permission gate** (`APPROVED_FOR_EVALUATION`, `APPROVED_FOR_NONCOMMERCIAL_RESEARCH`, `COMMERCIAL_USE_REVIEW_REQUIRED`, `ACCESS_RESTRICTED`, `DOWNLOAD_NOT_AUTHORIZED`, `REJECTED`). Downloads are prohibited without explicit recorded approval.
  - Protect remote fetches with SSRF prevention (rejecting loopback, link-local metadata, and private IP blocks) and bounded size/timeout limits.
  - Isolate synthetic data with explicit `is_synthetic = True` flags, deterministic seeds, generation parameters, and parent-source linkage.
- **Consequences**: Enables systematic data acquisition across multiple open and internal sources with guaranteed evidence integrity, legal compliance, and zero unverified AI model contamination.

