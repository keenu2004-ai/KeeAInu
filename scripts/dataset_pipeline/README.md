# KeeAInu Local Dataset Pipeline

This pipeline prepares externally downloaded datasets for local experiments without requiring Roboflow at runtime. It does **not** download from Roboflow, train a model, or grant data rights.

## Source workflow

1. Open each publisher page in `sources.json`; verify the actual terms and dataset revision.
2. Download the archive to a local directory outside the repository (recommended: `data/external_datasets/inbox/`).
3. Record the archive path and the license decision in a source manifest. Never set `license_review_status` to approved until an authorized reviewer has checked the publisher's applicable terms.
4. Run the audit tool against a specific archive.
5. Inspect `dataset_audit.json` and its annotation/quality warnings before any training.
6. Keep original archives immutable. Derived/normalized files belong in a separate output directory.

## Commands

From the repository root, with Python 3.11+:

```bash
python scripts/dataset_pipeline/audit_archive.py --help
python scripts/dataset_pipeline/audit_archive.py \
  --archive /absolute/path/to/downloaded-dataset.zip \
  --dataset-id borescope-2245 \
  --source-url https://universe.roboflow.com/class-ipagk/borescope \
  --license-review-status pending \
  --output data/external_datasets/audits/borescope-2245
```

The audit reads ZIP member names and metadata without extracting files, rejects path traversal entries and encrypted archives, applies file-count/expanded-size limits, hashes the original archive, and produces a JSON inventory of image/label files. It does not execute archive content or alter the input archive.

## Validate an extracted YOLO detection dataset

After downloading and extracting a reviewed export into local storage, validate it before training:

```bash
python scripts/dataset_pipeline/validate_yolo_dataset.py \
  --root /absolute/path/to/extracted-dataset \
  --class-count 5 \
  --output data/external_datasets/audits/borescope-yolo-validation.json
```

The validator checks image/label pairing, normalized YOLO detection rows, optional class ID bounds, missing/orphan labels, exact duplicate images and exact duplicates across split directories. It rejects segmentation polygon rows rather than misreading them as boxes. It does not determine whether a label visually matches its image.

## Fail-closed training readiness checklist

Copy `manifest.template.json` to a private/local review file and fill in the exact dataset export version, archive SHA-256 from the audit report, license and intended-use decision, attribution, reviewer, task/class mapping, annotation review, and split review. Keep pending fields pending until a human has actually reviewed them.

Run the gate after the archive audit and (for object detection) the YOLO structural validator:

```bash
python scripts/dataset_pipeline/training_gate.py \
  --audit data/external_datasets/audits/borescope-2245/dataset_audit.json \
  --manifest /absolute/path/to/borescope-review-manifest.json \
  --validation data/external_datasets/audits/borescope-yolo-validation.json \
  --output data/external_datasets/audits/borescope-training-gate.json
```

Exit code `0` means the documented checklist passed; exit code `1` means training is blocked; exit code `2` means an input could not be read. A passed result is still a checklist, not independent legal advice, proof that labels are correct, or a production/safety certification. Do not treat it as automatic authorization to train or deploy.

## Important limits

- Public catalog counts shown in source listings are provisional until the downloaded release is inspected.
- The current tool detects label/annotation file presence and common directory layouts; it does not prove labels are correct or comparable.
- Never merge object-detection boxes, segmentation masks, and image-level severity labels into a single target format without an explicit conversion and validation step.
- Split by inspection/video/sequence or source identity before evaluation to avoid near-duplicate leakage.
- Commercial training requires a separate rights review. A public URL or visible dataset does not imply commercial-use permission.
- This is data auditing/preparation only; no model has been trained by running it.
