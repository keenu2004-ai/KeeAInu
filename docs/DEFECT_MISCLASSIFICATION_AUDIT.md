# KeeAInu Defect Misclassification Audit & Confusion Investigation

> **Document Version**: 1.0.0
> **Status**: Verified Engineering Audit & Root-Cause Analysis
> **Repository Branch**: `repair/autonomous-audit-fix`
> **Author**: KeeAInu Defect Intelligence & Vision Architecture

---

## 1. Problem Statement & Root Cause Explanation

### 1.1 The Central Question
Why does the current KeeAInu system label holes, cavities, pitting, or scratches as **cracks**?

### 1.2 Inspection of the Active Inference Pipeline
We audited the actual codebase, model registry, active inference engines, configuration schemas, database records, and filesystem:

| Component | Code Location | State / Implementation | Root Cause Contribution |
| :--- | :--- | :--- | :--- |
| **Inference Registry** | `backend/app/modules/inference/registry.py` | Holds 3 registered engines: `mock`, `roboflow`, `onnx_local` | Factory exposes deterministic mock by default when no local weights exist |
| **Mock Engine** | `backend/app/modules/inference/mock_engine.py` | Line 77: `defect_class = "CRACK"` hardcoded for `frame_index % 2 == 1` with static bbox `[0.25, 0.30, 0.65, 0.45]` | **Primary source of false "CRACK" labels**: Any frame with an odd index is unconditionally stamped as a "CRACK", regardless of visual content (hole, scratch, clean surface) |
| **Roboflow SAM 3 Engine** | `backend/app/modules/inference/roboflow_client.py` & `backend/app/core/config.py` | Prompts defined in `config.py`: `["crack", "pitting", "corrosion", "erosion", "deposit", "mechanical defect"]` | **Semantic Vocabulary Omission**: `"hole"`, `"cavity"`, `"scratch"`, `"dent"` are completely absent. Open-vocabulary models forced to segment dark holes or voids collapse onto `"crack"` or `"mechanical defect"` |
| **Local ONNX Engine** | `backend/app/modules/inference/onnx_engine.py` | Target weights: `data/models/keeainu_defect_detector.onnx` | **File does not exist on disk**: Zero local models have been trained or deployed |
| **Dataset Export** | `data/datasets/keeainu_yolo_v1/manifest.json` | 16 entries from test fixture videos (`inspection_video.mp4`, `feed.mp4`) | All 16 were simulated mock predictions (`is_simulated = 1`) with repeated identical hash (`0e423836...`). Correctly rejected by new export gate |

### 1.3 Key Technical Verdicts
1. **Which engine generated the observed predictions?**
   The predictions observed in the database and initial dataset exports were generated entirely by `MockInferenceEngine` during test suite executions.
2. **Was the output simulated, prompt-based segmentation, pretrained detection, or a locally trained model?**
   It was **100% simulated mock output**. No local neural network was involved, and no cloud Roboflow call was made (cloud inference was gated off with `ROBOFLOW_ALLOW_CLOUD_INFERENCE = False`).
3. **Why would a hole be labelled as a crack?**
   - In the **mock engine**: The engine contains hardcoded logic assigning `"CRACK"` to any odd-indexed frame, ignoring pixels entirely.
   - In the **prompted open-vocabulary engine (Roboflow SAM 3)**: `"hole"` is missing from the prompt dictionary. Because a hole has high-contrast dark internal shadow, the segmentation head aligns the dark boundary with the nearest dark-discontinuity prompt in its vocabulary: `"crack"`.
   - In **classical edge/gradient detectors**: Both holes and cracks exhibit steep light-to-shadow gradients ($-\nabla I$). Under directional videoscope lighting, elliptical holes cast linear crescent shadows with high aspect ratios, fooling naive linear edge filters.
4. **Does the problem originate from the model, prompts, class mapping, annotations, preprocessing, or postprocessing?**
   - **Prompts**: Omitted critical industrial categories (`hole`, `scratch`, `dent`).
   - **Model**: No local model exists; mock engine was standing in.
   - **Annotations**: Zero human-verified ground-truth annotations existed for real footage.
   - **Class Mapping**: Previous mappings lacked distinction between geometric appearance (apertures/scratches) and failure modes (cracks).

---

## 2. Targeted Confusion Analysis: 6 Key Failure Modes

We analyzed the physical, optical, and computer vision mechanisms underlying each major industrial confusion in videoscope non-destructive testing:

```
+-------------------------------------------------------------------------------------------------+
|                                 VIDEOSCOPE OPTICAL CONFUSION MODES                              |
+------------------------------+----------------------------------+-------------------------------+
| 1. Hole vs. Crack            | 2. Crack vs. Scratch             | 3. Pitting vs. Cavity / Hole  |
| Direct illumination shadow   | Linear aspect ratio similarity   | Localized concave depression  |
| High-contrast interior       | Micro-tortuosity vs striation    | Diameter < 3mm vs through-wall|
+------------------------------+----------------------------------+-------------------------------+
| 4. Rust/Dirt vs. Defect      | 5. Reflection / Glare Anomaly    | 6. Motion Blur / Resolution   |
| Surface patina vs base loss  | Coaxial LED specular saturation  | Probe articulation movement   |
| Loose soot vs spall cavity   | Gradient threshold artifacts     | Loss of micro-fissure tips    |
+------------------------------+----------------------------------+-------------------------------+
```

### Case 1: Holes Predicted as Cracks
* **Optical Mechanism**: Direct coaxial illumination into a through-hole or cooling passage yields almost zero backscattered light, creating a deep black interior ($I \approx 0$). When viewed at an acute angle ($> 45^\circ$), the circular aperture projects as a narrow ellipse with a high major-to-minor axis ratio.
* **Computer Vision Failure**: Convolutional feature maps and edge detectors respond to the extreme contrast gradient ($\partial I / \partial x$). If the vocabulary lacks `Hole`, max-pooling and linear filters match the elongated dark boundary to `Crack`.
* **Remedy & Invariant**:
  - Enforce explicit `Hole` class in both prompts and training annotations.
  - Geometry invariant: Holes have smooth, continuous curvature ($d^2 y / dx^2$ smooth) and non-propagating rounded terminations; cracks have non-differentiable jagged turns with sharp tapering tips ($w_{tip} \to 0$).

### Case 2: Cracks Predicted as Scratches (and vice versa)
* **Optical Mechanism**: Both features are high-aspect-ratio linear structures. However, a scratch is caused by abrasive plowing, which displaces metal upward onto both flanks (producing raised reflective berms). Under front illumination, a scratch reflects light along its flanks and groove base. A crack is a deep tensile fissure that absorbs light within its trough.
* **Computer Vision Failure**: At low resolution or when the image is over-exposed, the specular reflection from a scratch's flank saturates adjacent pixels, blurring the groove into a dark trough that resembles a crack.
* **Remedy & Invariant**:
  - Cross-illumination or multi-angle lighting verification.
  - Trajectory invariant: Scratches follow straight tool paths or gentle machining arcs; fatigue cracks follow stress trajectories, fillet radii, or grain boundaries, exhibiting tortuous branching.

### Case 3: Pitting Predicted as Holes or Cavities
* **Optical Mechanism**: Pitting consists of isolated or clustered micro-craters (diameter $\le 3\text{ mm}$). Direct lighting casts a shadow inside each pit.
* **Computer Vision Failure**: Detectors without spatial scale or depth cues cannot distinguish a $1\text{ mm}$ pit from a $10\text{ mm}$ through-hole or casting shrinkage void.
* **Remedy & Invariant**:
  - Contextual scale calibration (pixel-per-millimeter based on probe tip distance or component geometry).
  - Pits occur in clusters with visible crater floors and specular lip rings; holes are solitary or orderly patterns (cooling grids) with dark open depth.

### Case 4: Rust or Dirt Predicted as Structural Defects
* **Optical Mechanism**: Combustion soot, unburned fuel residue, and loose ferrous rust flakes deposit as irregular dark or amber patches on hot-gas components.
* **Computer Vision Failure**: Dark soot patches mimic spalled thermal barrier coating (TBC) or shallow cavity voids because both appear darker than surrounding ceramic/metal.
* **Remedy & Invariant**:
  - Color space and texture analysis: Soot has a matte, low-reflectance, non-geometric texture without defined boundary steps. Spalling exhibits sharp, crisp fractured borders with an exposed underlying bond coat.

### Case 5: Specular Reflections, Shadows, and Lens Flare Predicted as Defects
* **Optical Mechanism**: Internal inspection involves metallic reflective surfaces (titanium, nickel, chrome) illuminated by intense probe-tip LEDs. This produces specular blooming ("hot spots") bordered immediately by steep fall-off shadows.
* **Computer Vision Failure**: The dark border immediately adjacent to a specular bloom creates an artificial high-contrast line that triggers false-positive crack or notch detections.
* **Remedy & Invariant**:
  - Dynamic articulation tracking: Optical glare shifts position when the probe articulates even fractions of a degree, whereas physical defects remain pinned to the asset coordinates.
  - Glare mask preprocessing: Suppress false detections located within $k$ pixels of saturated highlight clusters ($I > 250$).

### Case 6: Genuine Defects Missed by Model (False Negatives)
* **Optical Mechanism**: Fine tight cracks ($< 0.05\text{ mm}$ aperture) closed under compression produce virtually no shadow under diffuse lighting.
* **Remedy**:
  - High-resolution zoom inspection and angled edge illumination.

---

## 3. Data Inventory & Provenance Audit

We inspected all media, annotation records, and dataset exports currently residing in the repository:

### 3.1 Raw Media Assets
| Asset Category | Location | Item Count | Provenance | Status |
| :--- | :--- | :---: | :--- | :--- |
| **Real G1 Videoscope Frames** | `data/media/pilot_g1_real/` | **12** | Genuine Olympus/Yateks videoscope inspection images (`G1_20231216*.jpg`) | Ingested into session `sess_pilot_g1_real`; **Awaiting human inspector labeling** |
| **Test Fixture Videos** | `data/media/` | 2 | `inspection_video.mp4`, `feed.mp4` synthetic test clips | Used for automated API testing; **Excluded from training** |
| **Simulated Mock Findings** | Database `findings` table | 16 | Generated by `MockInferenceEngine` during test runs | All flagged `is_simulated = 1`; **Excluded from training** |
| **Exported Dataset v1** | `data/datasets/keeainu_yolo_v1/` | 16 | Historical export containing simulated frames | Preserved as audit artifact; **Locked from model training** |

### 3.2 Current Human Ground-Truth Annotation Counts
- **Human-Verified Positive Defect Annotations on Real Footage**: **0**
- **Human-Verified Defect-Free Negative Images**: **0**
- **Trained Local Model Weights**: **0** (No `.onnx` or `.pt` checkpoint exists)

### 3.3 The 12 Pilot Images Requiring Human Review
The following 12 genuine videoscope images are staged in `sess_pilot_g1_real` and require human inspector verification before baseline model training can proceed:

1. `G1_20231216142144.jpg` (SHA-256: `64a7c1dd...`)
2. `G1_20231216142145.jpg` (SHA-256: `78e35fbb...`)
3. `G1_20231216142146.jpg` (SHA-256: `12bf98ea...`)
4. `G1_20231216142147.jpg` (SHA-256: `3a45c61d...`)
5. `G1_20231216142148.jpg` (SHA-256: `9bc4512e...`)
6. `G1_20231216142149.jpg` (SHA-256: `41e89f2a...`)
7. `G1_20231216142150.jpg` (SHA-256: `7d33b8a1...`)
8. `G1_20231216142151.jpg` (SHA-256: `2f10d9e4...`)
9. `G1_20231216142152.jpg` (SHA-256: `8c66e4a2...`)
10. `G1_20231216142153.jpg` (SHA-256: `b512a890...`)
11. `G1_20231216142154.jpg` (SHA-256: `f1498c11...`)
12. `G1_20231216142155.jpg` (SHA-256: `a9372bd3...`)

---

## 4. Prioritized List of Missing Annotations

To break the false-confusion deadlock and build a reliable videoscope defect detector, the following annotations must be acquired and certified by human inspectors:

| Priority | Defect Category | Target Sample Count | Critical Visual Feature to Teach | Rationale |
| :---: | :--- | :---: | :--- | :--- |
| **P0** | **Hole (Engineered & Punctures)** | $\ge 25$ | Round, smooth-rimmed, black interior without floor | Prevents false crack alerts on standard cooling holes |
| **P0** | **Crack (Structural Fatigue)** | $\ge 25$ | Tortuous, razor-sharp tips, non-linear trajectory | Primary flight-safety critical defect |
| **P0** | **Defect-Free Negatives** | $\ge 30$ | Clean turbine blades, smooth bores, weld beads | Suppresses false-alarm flood across normal surfaces |
| **P1** | **Scratch (Mechanical)** | $\ge 20$ | Straight lines with bright raised plowing berms | Stops non-critical handling marks from halting flights |
| **P1** | **Pitting / Cavitation** | $\ge 20$ | Clustered micro-craters with visible bottom floors | Distinguishes localized etching from through-wall holes |
| **P2** | **Corrosion & Rust** | $\ge 15$ | Diffuse mottled scaling and amber iron oxide stains | Differentiates chemical patina from geometric cracks |
| **P2** | **Dents & Foreign Object Damage** | $\ge 15$ | Smooth concave depressions with unbroken surface skin | Catches impact deformation without confusion with spalling |
| **P3** | **Weld Defect Suite** | $\ge 15$ | Spatter globules, undercut, porosity pinholes | Dedicated joining inspection capability |

---

## 5. Technical Path Forward

1. **Human Inspector Review of the 12 Pilot Images**:
   - Inspectors use the Inspection Workspace UI (`/sessions`) or the REST API (`POST /api/v1/media/{media_id}/findings` or `POST /api/v1/media/{media_id}/verify-defect-free`) to review each of the 12 pilot frames.
2. **Safe Dataset Export**:
   - Execute `POST /api/v1/evaluation/datasets/export` to compile `keeainu_yolo_v2_real`. The export strictly requires human verification (`is_simulated = False`).
3. **Automated Reproducible Baseline Training**:
   - Provide `scripts/train_defect_detector.py` implementing YOLOv8n fine-tuning with group-based cross-validation, confusion matrix calculation, and automated export to ONNX (`data/models/keeainu_defect_detector.onnx`).
