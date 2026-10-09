# KeeAInu — Contributor & Coding Agent Instructions (AGENTS.md)

This document defines the strict engineering standards, behavioral rules, and verification requirements for human contributors and AI coding agents working on KeeAInu.

---

## 1. Core Engineering Principles (Karpathy Guidelines)

1. **Think Before Coding**:
   - Always state assumptions, verified constraints, and trade-offs before writing or editing code.
   - Clarify ambiguous requirements instead of guessing.
2. **Simplicity First**:
   - Prefer the simplest design that satisfies demonstrated requirements.
   - Do NOT introduce speculative microservices, extra distributed message brokers, duplicate CSS frameworks, or unnecessary wrapper layers.
3. **Surgical, Minimal Changes**:
   - Make minimal, targeted edits. Do not refactor unrelated files or make gratuitous stylistic changes.
   - Preserve existing working code and documentation integrity.
4. **Goal-Driven & Evidence-Based Execution**:
   - Define concrete, verifiable acceptance tests for every change.
   - Run tests and report actual command outputs. Never fabricate test passes or benchmark numbers.

---

## 2. Non-Negotiable Project Rules

- **Evidence Integrity**: Never alter or overwrite raw inspection media. All findings must be linked to immutable frame indexes and SHA-256 hashes.
- **AI Transparency**: Never represent simulated/mock AI predictions as real model inferences. Never represent AI detections as certified defects without human inspector verification.
- **Security & Secrets**: Never commit `.env`, credentials, private keys, API keys, or proprietary inspection footage to the repository.
- **Hardware Realism**: Do not assume Yateks hardware interfaces work without verified documentation and physical test evidence.
- **Cross-Platform Compatibility**: Always use `pathlib.Path` or `os.path` for path manipulation (supporting Windows and Linux).

---

## 3. Standard Verification Commands

- **Backend Tests**: `pytest` or `uv run pytest`
- **Backend Linting**: `ruff check .` and `mypy app`
- **Frontend Typecheck & Build**: `npm run build` or `npm test`
- **Pre-commit Verification**: Run test suites and verify diffs before staging commits.
