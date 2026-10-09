# KeeAInu — Risk Register & Mitigation Strategy

**Version**: 1.0.0  
**Status**: Active  

---

| Risk ID | Category | Risk Description | Severity | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RISK-01** | AI / Safety | Inspector over-relies on AI detection, missing unflagged critical defects. | **High** | Medium | Prominent UI warnings that AI predictions are candidate suggestions only; qualified inspector confirmation strictly required before sign-off. |
| **RISK-02** | Hardware | Yateks models have divergent video output protocols or lack public SDKs. | **High** | High | Abstract hardware interface; treat live stream capture via standard UVC/HDMI capture cards; validate each model individually before claiming compatibility. |
| **RISK-03** | Data Integrity | Original inspection media corrupted or tampered during ingestion/storage. | **High** | Low | Compute SHA-256 hash immediately on upload; store raw media in write-protected storage sandbox; separate derived thumbnails/annotations completely. |
| **RISK-04** | Performance | Large 4K/60fps video files cause out-of-memory or high playback latency. | **Medium** | High | Stream media with chunked range requests; extract lightweight low-resolution proxy frames for scrubbing; run heavy inference asynchronously. |
| **RISK-05** | Security | Malicious media files or path traversal attacks during file upload. | **High** | Medium | Magic byte file signature validation; strict path normalization inside storage sandbox; execution in non-root sandboxes. |
| **RISK-06** | System Bloat | Speculative microservices and dependencies cause maintenance collapse. | **Medium** | High | Enforce Modular Monolith pattern (ADR-0002); require ADR approval for any external infrastructure or dependency addition. |
