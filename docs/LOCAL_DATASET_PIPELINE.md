# Local Dataset Pipeline & Roboflow Independence

## Purpose

KeeAInu owns its own dataset inventory, normalization, model interface, evaluation, and inference runtime. External annotation or hosted-inference platforms are optional tools, not runtime dependencies.

The current repository already has controlled acquisition, license gating, source provenance, quality profiling, and a pluggable inference registry. This milestone adds a local audit utility and a registry of five candidate public datasets/tasks discussed for the first vision baseline.

## Local KeeAInu-training dataset

The currently audited `BorescopeDataset` lives outside this repository, in a sibling folder named `KeeAInu-training`. On the Windows development machine, from the KeeAInu repository root the dataset path is:

```powershell
..\KeeAInu-training\BorescopeDataset
```

The audited local snapshot contains 6,054 train images, 110 validation images, and 116 test images. Its labels are YOLO bounding boxes for five source classes; they are not segmentation masks and have not been accepted as verified ground truth. Two planned KeeAInu classes (Welded Droplet and Erosion/Corrosion) should not be synthesized from the source labels. For the detailed historical counts, experiment limitations, storage guidance, and publishing checklist, see [Training Data & Publishing Policy](TRAINING_DATA_AND_PUBLISHING.md).

Keep the source dataset outside public Git by default. The repository's `.gitignore` excludes local `data/segmentation/`, `data/external_datasets/`, `data/training_data/`, and `data/experiments/` outputs, but ignores do not delete existing files and do not protect files already committed. Always inspect Git status and the final staged diff before pushing. Verify source license and redistribution terms before sharing any images or labels.

## Candidate datasets (verification pending)

See `scripts/dataset_pipeline/sources.json`. The historical image counts and class names are leads from initial discovery, not guarantees about the latest public release. Before use, verify the exact revision, source terms, license, exported annotations and task type. No dataset should be described as approved for commercial training until rights have been reviewed.

## Milestone delivered

- Candidate source registry under version control (metadata only; no images).
- Read-only ZIP inventory with archive SHA-256, bounds, annotation-layout hints and explicit pending review defaults.
- Archive path traversal and encrypted member checks before any extraction.
- JSON report kept in a caller-selected output directory; raw archive is not modified or extracted.
- Unit tests for the archive auditor.

## Dataset registry and label-validation milestone

The registry records public page metadata and keeps license review pending. Publicly displayed CC BY 4.0 metadata is evidence to review, not a blanket determination that every file or intended commercial use is cleared. Preserve source attribution and the exact dataset version in the audit trail.

The YOLO object-detection validator is available at `scripts/dataset_pipeline/validate_yolo_dataset.py`. Run it against an extracted dataset in local storage. It catches structural errors (including normalized boxes whose rectangles extend beyond image edges) and exact duplicate images across split directories; it deliberately does not accept segmentation polygons or declare data training-ready.

## Next milestone

Once specific downloaded archives and their licenses are verified:
1. Add an explicit, testable parser for each actual annotation format.
2. Normalize to one selected training task (start with box detection if the borescope archive provides valid boxes).
3. Validate class mapping and image/label pairs.
4. Deduplicate, then split by inspection sequence/source.
5. Train a baseline with a pinned configuration and record weights, hashes, metrics and dataset provenance.
6. Compare performance on held-out real Yateks footage.

This milestone has not trained a model and does not assert that any dataset is fit for commercial use or production decisions.
