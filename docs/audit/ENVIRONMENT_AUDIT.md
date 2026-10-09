# KeeAInu — Environment Audit Report (Phase 0)

**Date**: 2026-10-09  
**Host Operating System**: Microsoft Windows  
**Shell**: PowerShell 7 / Windows PowerShell  
**Audit Purpose**: Verify installed developer tooling, runtimes, package managers, and execution constraints.

---

## 1. Runtime & Tool Inventory

| Tool / Runtime | Detected Version | Status | Suitability & Notes |
| :--- | :--- | :--- | :--- |
| **Git** | `2.53.0.windows.2` | **Verified** | Modern Git client; supports all workflow & commit signing needs. |
| **Python** | `3.14.6` | **Verified** | Modern Python runtime available. |
| **Pip** | `26.1.2` | **Verified** | Package installer available. |
| **uv** | `0.12.21` | **Verified** | High-performance Python project/package manager available. |
| **Node.js** | `v24.16.0` | **Verified** | Modern LTS/Current Node runtime. |
| **npm** | `10.7.0` | **Verified** | Standard package manager for frontend/JS dependencies. |
| **Docker** | `29.6.1` (build `8900f1d`) | **Verified** | Container runtime available for isolated testing and future containerization. |
| **FFmpeg** | *Not found on PATH* | **Confirmed Gap** | System ffmpeg CLI not installed in PATH. Video handling will leverage OpenCV (`cv2.VideoCapture`), `imageio-ffmpeg`, or `pyav` inside Python virtual environments, with explicit checks. |

---

## 2. Environment Constraints & Mitigation Strategy

1. **Operating System (Windows)**:
   - File path separators: Code must strictly use `os.path` / `pathlib.Path` cross-platform conventions to prevent POSIX vs Windows backslash issues.
   - Long path support and temporary file locking handling in Python tests.

2. **FFmpeg CLI Availability**:
   - Because `ffmpeg` is not globally on the system PATH, the video ingestion pipeline must not assume shell execution of `ffmpeg.exe`.
   - **Mitigation**: Use Python bindings with bundled static binaries (e.g. `imageio-ffmpeg` or `av` / `opencv-python`) and validate video container decoding programmatically.

3. **Python & Virtual Environment Management**:
   - Use `uv` or `venv` to create dedicated virtual environments (`.venv`) for isolation.
   - Ensure native C-extensions (such as OpenCV and PyTorch) are compatible with the target Python release.

4. **Security & Privacy Boundary**:
   - Zero committed secrets: Enforced via `.gitignore` and environment variable configuration via `.env.example`.
   - Never commit raw customer inspection footage or proprietary CAD/videoscope recordings.

---

## 3. Tooling Verification Matrix

- [x] Python execution verified
- [x] Node.js & npm execution verified
- [x] Docker CLI presence verified
- [x] uv package manager presence verified
- [x] Git version control initialized and verified
- [!] Global FFmpeg CLI absent — fallback pipeline strategy documented
