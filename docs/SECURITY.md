# KeeAInu — Security & Privacy Baseline

**Version**: 1.0.0  
**Classification**: Engineering Governance  

---

## 1. Security Principles

1. **Least Privilege & Role-Based Access Control**: Backend endpoints enforce permission boundaries. Inspection sessions and raw evidence can only be modified or audited by authorized operators.
2. **Zero Hardcoded Secrets**: Secrets, tokens, and storage credentials must never be committed to source control. Enforce `.gitignore` and `.env.example` templates.
3. **Safe Media Processing & Input Validation**:
   - File uploads must undergo file signature validation (magic bytes) to prevent executable upload tricks.
   - Restrict allowable file extensions (`.mp4`, `.avi`, `.mov`, `.mkv`, `.jpg`, `.jpeg`, `.png`, `.bmp`).
   - Enforce hard limits on maximum upload file size and request timeouts.
   - Mitigate path traversal attacks by resolving and validating absolute file storage paths strictly within the designated storage sandbox.
4. **Evidence Immutability & Consumption Verification**:
   - SHA-256 checksums calculated upon receipt using memory-bounded (64KB chunk) streaming.
   - Cryptographic integrity strictly verified before every raw evidence consumption point (content download, frame extraction, model inference) via `verify_and_resolve_media_file`.
   - Tampered evidence is rejected with HTTP 409 Conflict; missing or traversal files are rejected with HTTP 404.
   - Original registered SHA-256 digests are immutable and cannot be overwritten.
   - Derived artifacts (timeline thumbnails, proxy frames) are stored separately in `data/media/derived/`, sandboxed to prevent cache poisoning, and regenerable on demand from verified primary evidence.
   - All status transitions, finding rejections, and inspector edits generate timestamped audit records.
5. **Safe AI Model Execution**:
   - Load models exclusively from verified local checkpoints or cryptographically signed artifacts.
   - Disallow unsafe arbitrary Python deserialization (`pickle.load` on untrusted sources). Use ONNX or safe tensor weights (`safetensors`).

---

## 2. Security Vulnerability Response

Report any security vulnerabilities directly to the maintainers at `security@keenu-ai.internal`. Do not open public issues for sensitive security defects.
