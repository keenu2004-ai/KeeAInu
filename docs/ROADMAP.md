# KeeAInu — Phased Implementation Roadmap

This roadmap defines the verified milestone sequence for developing the KeeAInu platform.

---

## Phase 0 — Audit & Environment Verification
- [x] Initial non-destructive repository and environment audit.
- [x] Runtime & tooling inventory (Python, Node, Docker, uv, Git).
- [x] External skills & integration evaluation register.
- [x] Baseline governance files (`REPOSITORY_AUDIT.md`, `ENVIRONMENT_AUDIT.md`).

## Phase 1 — Foundation & Governance (Current Milestone)
- [x] Project charter, requirements, architecture, data model, security, and test strategy.
- [x] Architecture Decision Records (`DECISIONS.md`).
- [x] Contributor guidelines (`AGENTS.md`) and `.gitignore`.
- [ ] Minimal project structure (backend and frontend configurations, type baseline).
- [ ] Initial automated test harness & verification suite.

## Phase 2 — Inspection Data Workflow & Sample Test Corpus (Completed)
- [x] Domain taxonomy definition (cracks, corrosion, wear, deposits, blockage).
- [x] Versioned machine-readable annotation contract (`docs/ANNOTATION_SCHEMA.md` & Pydantic models).
- [x] Authorized synthetic inspection test corpus generation (`scripts/generate_synthetic_fixtures.py`).
- [x] Frame extraction & video container metadata extraction harness (`backend/app/modules/video/extractor.py`).
- [x] Deterministic test harness & evidence immutability verification suite.

## Phase 3 — Recorded-Media Inspection MVP (Completed)
- [x] Secure video & image ingestion pipeline with SHA-256 evidence hashing.
- [x] Fast frame extractor & bounded thumbnail generator.
- [x] Pluggable `InferenceEngine` interface with deterministic `MockInferenceEngine`.
- [x] Frame-accurate web inspection viewport with timeline scrubber and canvas overlay.
- [x] Inspector finding review & verification workflow (`CONFIRMED`, `ADJUSTED`, `REJECTED`).
- [x] SQLite-backed session, media, finding, and review persistence.

## Phase 4 — Real AI Defect Detection Baseline
- [ ] Integrate lightweight real vision model (e.g. YOLO/ONNX defect detector).
- [ ] Benchmark precision, recall, and inference latency on test corpus.
- [ ] Establish confidence thresholds and transparent model version tracking.

## Phase 5 — Full Inspection Application & Asset Persistence
- [ ] Relational persistence for Sites, Assets, Sessions, Findings, and Audit Logs.
- [ ] Asset history viewer and defect degradation tracking across inspection dates.
- [ ] Role-based access control and inspector sign-off state machine.

## Phase 6 — Live Hardware Integration
- [ ] Document and test physical Yateks G, M, Q, B, and P series interfaces (UVC, HDMI capture, RTSP).
- [ ] Graceful fallback and live stream ingest adapter.

## Phase 7 — Traceable Reporting & Evidence Packaging
- [ ] Automated PDF & JSON NDT report generator.
- [ ] Side-by-side comparative inspection diffs.
- [ ] Cryptographically verifiable evidence export bundles.

## Phase 8 — Production Hardening & Field Pilot
- [ ] Performance optimization, containerized deployment (Docker Compose).
- [ ] Field evaluation with NDT engineers.
