# Local Dataset Pipeline & Roboflow Independence

## Purpose

KeeAInu owns its own dataset inventory, normalization, model interface, evaluation, and inference runtime. External annotation or hosted-inference platforms are optional tools, not runtime dependencies.

The current repository already has controlled acquisition, license gating, source provenance, quality profiling, and a pluggable inference registry. This milestone adds a local audit utility and a registry of the three candidate public datasets discussed for the first vision baseline.

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

The YOLO object-detection validator is available at `scripts/dataset_pipeline/validate_yolo_dataset.py`. Run it against an extracted dataset in local storage. It catches structural errors and exact duplicate images across split directories; it deliberately does not accept segmentation polygons or declare data training-ready.

## Next milestone

Once specific downloaded archives and their licenses are verified:
1. Add an explicit, testable parser for each actual annotation format.
2. Normalize to one selected training task (start with box detection if the borescope archive provides valid boxes).
3. Validate class mapping and image/label pairs.
4. Deduplicate, then split by inspection sequence/source.
5. Train a baseline with a pinned configuration and record weights, hashes, metrics and dataset provenance.
6. Compare performance on held-out real Yateks footage.

This milestone has not trained a model and does not assert that any dataset is fit for commercial use or production decisions.
