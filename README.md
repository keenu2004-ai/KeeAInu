# KeeAInu 🔍🔬

> **AI-Assisted Industrial Visual Inspection & Videoscope Intelligence Platform**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-Phase%200%2F1%20Foundation-green.svg)](docs/ROADMAP.md)

---

## 📖 Overview

**KeeAInu** (*Keenu + AI*) is an industrial-grade visual inspection platform engineered for remote visual inspection (RVI) and nondestructive testing (NDT) using videoscopes and industrial borescopes (with targeted support for Yateks G, M, Q, B, and P series devices).

The platform enables inspection engineers to safely ingest recorded and live videoscope footage, scrub and inspect frames with sub-pixel accuracy, run pluggable AI defect detection models (for cracks, corrosion, wear, blockage, deformation, and deposits), perform human-in-the-loop review, track asset degradation over time, and generate auditable, evidence-backed inspection reports.

---

## 📐 Architecture & Principles

KeeAInu is built on strict engineering principles:
1. **Evidence Immutability**: Original inspection media is write-once, read-only. All derived artifacts and findings reference cryptographic SHA-256 hashes.
2. **Zero False Certainty**: AI predictions are strictly candidate suggestions; qualified engineer confirmation is required for all defect records.
3. **Modular Monolith**: Clean domain boundaries (`ingestion`, `video`, `inference`, `inspection`, `reporting`, `hardware`) without speculative microservices overhead.
4. **Pluggable AI Inference**: Clean interface decoupling the application from specific AI models (supporting rule-based CV, ONNX, PyTorch, and mock test engines).

---

## 📂 Repository Structure

```
├── docs/                     # Governance, audit, architecture, and specifications
│   ├── audit/                # Phase 0 repository & environment audits
│   ├── PROJECT_CHARTER.md    # Mission, principles, and stakeholders
│   ├── REQUIREMENTS.md       # Functional & non-functional requirements
│   ├── ARCHITECTURE.md       # Modular Monolith architecture & data flows
│   ├── DATA_MODEL.md         # Relational entity schemas & taxonomies
│   ├── DECISIONS.md          # Architecture Decision Records (ADRs)
│   ├── SECURITY.md           # Security baseline & input validation policies
│   ├── TEST_STRATEGY.md      # Test pyramid & release acceptance gates
│   ├── ROADMAP.md            # Phased milestone roadmap
│   └── RISK_REGISTER.md      # Risk matrix & mitigation plans
├── backend/                  # Python / FastAPI modular backend (Phase 1+)
├── frontend/                 # React / TypeScript inspection portal (Phase 1+)
├── data/                     # Local storage vault (raw media, artifacts, sqlite)
├── AGENTS.md                 # Contributor and AI coding agent guidelines
└── README.md                 # Project summary and quickstart
```

---

## 🚀 Quick Start (Development)

### Prerequisites
- **Python**: >= 3.11
- **Node.js**: >= 20
- **Git**

### Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
pytest
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📜 Documentation Index

- [Project Charter](docs/PROJECT_CHARTER.md)
- [Architecture & Design](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [Requirements Specification](docs/REQUIREMENTS.md)
- [Architecture Decision Records (ADRs)](docs/DECISIONS.md)
- [Security Baseline](docs/SECURITY.md)
- [Test Strategy](docs/TEST_STRATEGY.md)
- [Phased Roadmap](docs/ROADMAP.md)
- [Risk Register](docs/RISK_REGISTER.md)
- [Repository Audit Report](docs/audit/REPOSITORY_AUDIT.md)
- [Environment Audit Report](docs/audit/ENVIRONMENT_AUDIT.md)
- [Coding Agent Guidelines](AGENTS.md)
