# KeeAInu — Project Charter

**Official Name**: KeeAInu  
**Repository**: [https://github.com/keenu2004-ai/KeeAInu](https://github.com/keenu2004-ai/KeeAInu)  
**Name Origin**: Keenu + AI  
**Category**: AI-Assisted Industrial Visual Inspection & Videoscope Intelligence Platform  
**Status**: Active — Phase 0/1 (Foundation)

---

## 1. Vision & Purpose

KeeAInu is an evidence-driven, enterprise-grade industrial inspection platform designed to enhance nondestructive testing (NDT) and remote visual inspection (RVI) workflows using videoscopes and industrial borescopes. 

The platform enables inspection engineers to:
1. **Ingest & Preserve**: Safely ingest videoscope footage from recorded files and future live streams while preserving original, unmodified digital evidence.
2. **Review & Navigate**: Provide frame-accurate playback, timeline annotation, zoom/pan inspection tools, and timestamp synchronization.
3. **AI-Assisted Defect Candidate Detection**: Run pluggable visual inspection models to highlight candidate anomalies (such as cracks, corrosion, surface wear, deposits, blockage, and deformation) with confidence metrics and explainable bounding regions.
4. **Human-in-the-Loop Verification**: Enforce a strict review hierarchy: AI predictions are merely candidate suggestions; human inspectors accept, adjust, reject, or classify all findings.
5. **Traceability & Reporting**: Maintain end-to-end audit logs, session histories, asset inspection histories, cross-inspection comparisons, and exportable engineering inspection reports.

---

## 2. Core Principles & Non-Negotiables

1. **Evidence Integrity**: Original video/image evidence is write-once, read-only. Derived artifacts (annotations, crops, masks, reports) are stored alongside cryptographic hashes and generation metadata without altering the source media.
2. **No False Certainty / Zero Speculation**:
   - AI predictions are never presented as confirmed defects without inspector sign-off.
   - Mock/simulated detectors must be prominently labelled as such in the UI and API metadata.
   - Physical dimensions (e.g. crack depth, width in millimeters) are never estimated from pixels unless certified optical calibration, 3D phase measurement, or stereo measurement data exists.
3. **Hardware Realism**: Initial hardware target includes Yateks G, M, Q, B, and P series videoscopes. Compatibility is claimed only upon documented and verified physical testing of interfaces (e.g., HDMI/UVC capture, RTSP, SD-card import, USB mass storage).
4. **Simplicity & Modularity**: Start with a clean, cohesive modular monolith (FastAPI backend + Modern TypeScript frontend). Avoid speculative microservices, unnecessary distributed message brokers, or heavy cloud infrastructure until justified by measured requirements.
5. **Security & Privacy First**: Zero committed secrets, environment-driven configuration, strict tenant/workspace isolation, safe upload sanitization, and least-privilege access.

---

## 3. Stakeholders & Roles

| Role | Responsibilities |
| :--- | :--- |
| **Inspection Engineer (NDT Inspector)** | Operates videoscopes, uploads footage, reviews AI suggestions, logs verified defect observations, generates sign-off reports. |
| **Quality Manager / Lead Auditor** | Reviews inspection histories, validates compliance against engineering standards, exports auditable NDT packages. |
| **Asset Owner / Maintenance Team** | Consumes inspection findings, tracks asset degradation over time, plans preventative maintenance. |
| **AI / System Engineer** | Evaluates model performance, manages dataset provenance, updates inference pipelines with documented metrics. |

---

## 4. Success Criteria

- **Phase 0 & 1**: Complete baseline audit, project charter, governance docs, architectural blueprints, CI workflows, and developer conventions.
- **Phase 2 & 3**: Verified video ingestion pipeline, frame-accurate inspection UI, pluggable inference interface, and reproducible test suite with sample media.
- **Phase 4 & 5**: Deterministic defect detection baseline with benchmarked metrics, persistent asset/session history, and human-in-the-loop review workflows.
- **Phase 6+**: Live hardware ingestion validation, comparative inspection diffs, and auditable PDF/JSON report exports.
