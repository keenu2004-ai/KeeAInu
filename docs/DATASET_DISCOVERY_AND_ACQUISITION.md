# KeeAInu — Multi-Source Dataset Discovery & Controlled Acquisition

## 1. Executive Summary & Objective

The **KeeAInu Multi-Source Dataset Discovery & Controlled Acquisition** platform extends the core videoscope inspection system into a domain-agnostic, multi-source data discovery, licensing audit, and safe acquisition engine.

Prior to selecting, training, or fine-tuning industrial computer vision models, KeeAInu enables systematic exploration, relevance scoring, and legal rights verification across candidate domains:
1. **Mechanical Components**: Aircraft engines, gas/steam turbines, compressor blades, bearings, gearboxes, rotating machinery.
2. **Pipes & Channels**: Internal pipeline walls, tube bundles, sewer conduits, heat exchangers, boiler tubes.
3. **Mould Cavities & Dies**: Injection moulds, die casting cavities, internal cooling channels.
4. **Other / Cross-Domain Benchmarks**: Benchtop surface defect detection, anomaly segmentation datasets.
5. **Unknown / Unclassified Media**: Indeterminate or preliminary exploratory video assets.

---

## 2. Architecture & Provider System

```
                           +-------------------------------------+
                           |    KeeAInu Discovery Hub (UI)       |
                           +------------------+------------------+
                                              |
                     +------------------------+------------------------+
                     |                                                 |
       +-------------v--------------+                   +--------------v-------------+
       | Multi-Source Provider Reg  |                   | Local Ingest & Profiling   |
       +-------------+--------------+                   +--------------+-------------+
                     |                                                 |
    +----------------+----------------+                 +--------------+-------------+
    | Hugging Face Datasets           |                 | Visual Quality Profiler    |
    | Kaggle Datasets & Competitions  |                 | Contact Sheet Generator    |
    | Google Dataset Search Links     |                 | Frame Extractor (OpenCV)   |
    | Data.gov & OGD India Catalogs   |                 | Ingestion Validator        |
    | AWS Registry of Open Data       |                 +----------------------------+
    | GitHub Research Repositories    |
    | Internal Vaults (Sandboxed)     |
    | Synthetic Defect Studio         |
    +----------------+----------------+
                     |
       +-------------v--------------+
       | Explainable Relevance (0-100)|
       +-------------+--------------+
                     |
       +-------------v--------------+
       | License & Permission Gate  |
       | (Hard Compliance Barrier)  |
       +-------------+--------------+
                     |
       +-------------v--------------+
       | Controlled Ingestion Exec  |
       | (SSRF Safe, Bounded Limits)|
       +-------------+--------------+
                     |
       +-------------v--------------+
       | Raw Vault (Read-Only)      |
       | Derived Media & Provenance |
       +----------------------------+
```

### Supported Source Providers

| Provider ID | Provider Name | Category | Scope & Ingestion Mode |
| :--- | :--- | :--- | :--- |
| `huggingface` | Hugging Face Datasets | `PUBLIC_CATALOG` | Discovers open computer vision benchmarks, defect segmentation cards, and weights. |
| `kaggle` | Kaggle Datasets | `PUBLIC_CATALOG` | Discovers industrial inspection competitions, CCTV sewer pipe datasets, and casting archives. |
| `google_dataset_search` | Google Dataset Search | `PUBLIC_CATALOG` | Dynamic query aggregator pointing to Zenodo, Dryad, IEEE DataPort, and university repositories. |
| `datagov` | Data.gov / OGD India | `GOVERNMENT_CATALOG` | Discovers open public infrastructure, PHMSA pipeline integrity, and RDSO railway flaw datasets. |
| `aws_open_data` | AWS Registry of Open Data | `CLOUD_REGISTRY` | Cloud-hosted open ocean ROV, robotic probe, and infrastructure inspection archives. |
| `github_research` | GitHub Research Repositories | `RESEARCH_INSTITUTION` | Discovers peer-reviewed academic benchmark datasets (e.g., KolektorSDD, GDXray). |
| `internal_storage` | Internal Company Storage | `INTERNAL_STORAGE` | Controlled ingestion from authorized local/network import vaults under strict boundary sandboxing. |
| `synthetic_generator` | Synthetic Defect Studio | `SYNTHETIC_GENERATOR` | Parametric procedural defect generator (fractures, corrosion pitting, erosion, mould scratches). |

---

## 3. Explainable Multi-Factor Relevance Scoring

Each candidate dataset receives an explainable multi-factor relevance score ($0 - 100$) combining six transparent criteria:

$$\text{Relevance Score} = S_{\text{videoscope}} + S_{\text{domain}} + S_{\text{modality}} + S_{\text{defect}} + S_{\text{annotation}} + S_{\text{provenance}}$$

1. **Videoscope Similarity ($0 - 30$ points)**:
   - Direct borescope/endoscope/probe footage with internal perspective and directional LED lighting $\rightarrow 30\text{ pts}$.
   - Related internal-cavity visual context $\rightarrow 15\text{ pts}$.
   - External benchtop/flat surface imagery $\rightarrow 5\text{ pts}$ (labeled as cross-domain exploratory data).
2. **Domain Match ($0 - 25$ points)**:
   - Target domain match with keyword semantic alignment (e.g., turbine, blade, compressor, pipe, sewer, mould).
3. **Modality Match ($0 - 15$ points)**:
   - Continuous video sequences ($15\text{ pts}$), high-resolution still images ($12\text{ pts}$), non-standard modalities ($5\text{ pts}$).
4. **Defect Flaw Utility ($0 - 15$ points)**:
   - Confirmed defect categories present (cracks, pitting, corrosion, erosion, spalling) vs normal-only samples.
5. **Annotation Quality ($0 - 10$ points)**:
   - Pixel-accurate segmentation masks ($10\text{ pts}$), spatial bounding boxes ($8\text{ pts}$), classification tags ($5\text{ pts}$), unannotated ($2\text{ pts}$).
6. **Provenance Completeness ($0 - 5$ points)**:
   - Verified publisher, documentation integrity, and reproducible access methods.

---

## 4. License and Permission Gating System

KeeAInu treats legal compliance as a **hard gate**, not a weighted score. Public visibility does NOT imply license authorization.

### Permitted License States

- `APPROVED_FOR_EVALUATION`: Verified permissive or open license suitable for evaluation test harnesses.
- `APPROVED_FOR_NONCOMMERCIAL_RESEARCH`: Non-commercial research license (e.g., CC-BY-NC-4.0). Forbidden from commercial training.
- `COMMERCIAL_USE_REVIEW_REQUIRED`: Commercial rights unverified; requires formal legal audit before ingestion.
- `LICENSE_UNKNOWN`: Default state for unverified sources; acquisition is strictly blocked.
- `ACCESS_RESTRICTED`: Gated or authentication-required resource.
- `DOWNLOAD_NOT_AUTHORIZED`: Explicitly forbidden from acquisition.
- `REJECTED`: Compliance officer rejected the dataset; acquisition blocked.

### Controlled Acquisition Workflow

$$\text{Search} \longrightarrow \text{Inspect Metadata} \longrightarrow \text{Relevance Review} \longrightarrow \text{License Audit} \longrightarrow \text{Approve} \longrightarrow \text{Safe Fetch} \longrightarrow \text{Hash \& Ingest}$$

---

## 5. Network Safety & SSRF Prevention

The network layer (`network_safety.py`) enforces strict security rules before any remote metadata fetch or acquisition:
1. **SSRF Blocking**: Automatically rejects loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and cloud metadata IP ranges (`169.254.169.254`).
2. **Scheme Restriction**: Permits only `http` and `https`; rejects `file://`, `ftp://`, `gopher://`.
3. **Redirect Revalidation**: Validates target IPs across HTTP 3xx redirects.
4. **Bounded Limits**: Maximum metadata size (5 MB), maximum acquisition size (configurable, default 200 MB), bounded request timeouts (5.0s).

---

## 6. Curated Benchmark Shortlist

| Dataset Name | Domain | Modality | Publisher | License | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CCTV Sewer Pipe Defect Dataset** | `PIPES_CHANNELS` | Video / Stills | Aalborg Univ. / Kaggle | `CC-BY-4.0` | `APPROVED_FOR_EVALUATION` |
| **Gas Turbine Blade Borescope Dataset** | `MECHANICAL` | Video / Stills | Turbomachinery AI / Kaggle | `CC-BY-NC-4.0` | `APPROVED_FOR_NONCOMMERCIAL_RESEARCH` |
| **High-Pressure Gas Pipeline Borescope** | `PIPES_CHANNELS` | Video / Stills | Zenodo / EU Research | `CC-BY-4.0` | `APPROVED_FOR_EVALUATION` |
| **Aero-Engine Combustor Liner TBC Spallation** | `MECHANICAL` | Stills / Video | NASA Open Data / Dryad | `CC0-1.0` | `APPROVED_FOR_EVALUATION` |
| **US DOT PHMSA Pipeline Integrity Archive** | `PIPES_CHANNELS` | Video / Logs | U.S. DOT PHMSA | `PUBLIC-DOMAIN` | `APPROVED_FOR_EVALUATION` |
| **MVTec Anomaly Detection (Benchtop)** | `MECHANICAL` | High-Res Stills | MVTec GmbH | `CC-BY-NC-SA-4.0` | `APPROVED_FOR_NONCOMMERCIAL_RESEARCH` |
| **Kolektor Surface Defect Dataset (KolektorSDD2)** | `MECHANICAL` | High-Res Stills | Univ. of Ljubljana | `CC-BY-NC-4.0` | `APPROVED_FOR_NONCOMMERCIAL_RESEARCH` |
| **Casting Product Defect Dataset** | `MOULD_CAVITIES` | Stills | Kaggle / Industrial Castings | `CC0-1.0` | `APPROVED_FOR_EVALUATION` |
| **NEU Surface Defect Database** | `MECHANICAL` | Grayscale Stills | Northeastern University | `CC-BY-4.0` | `APPROVED_FOR_EVALUATION` |

---

## 7. Synthetic Data Studio & Safeguards

The procedural generator (`providers/synthetic_generator.py`) supports defect synthesis across all candidate domains:
- **Procedural Defects**: Stress corrosion cracks, localized pitting corrosion, leading-edge erosion, particulate scale/deposits.
- **Strict Provenance**: Every generated asset carries `is_synthetic = True`, `generator_version = "KeeAInu-SynthGenerator-v1.0"`, deterministic seed tracking, and parent asset linkage (`asset_provenance_links`).
- **Anti-Leakage Safeguard**: Synthetic defect masks and generated samples are strictly isolated and never classified as verified physical findings.
