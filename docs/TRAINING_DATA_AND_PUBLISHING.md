# Training Dataset, Experiment Results, and GitHub Publishing Policy

## Decision

Keep the full training dataset outside the public KeeAInu Git repository. Commit reusable code, documentation, tests, and carefully selected text-based experiment summaries. Do not commit raw photos, extracted frame sets, generated segmentation masks, overlay images, model weights, or embedded-image annotation exports.

This is a public repository. A dataset being downloadable does not automatically establish redistribution rights, and large image collections make ordinary Git history heavy. If the dataset license and source terms are later verified, link to the original source and record its exact version, license, and checksum rather than re-uploading it by default.

## Current local layout

The training dataset is a sibling of the KeeAInu project, not a subfolder tracked by its Git repository:

```text
Music/
├── KeeAInu videoscopes/       # KeeAInu Git repository
└── KeeAInu-training/
    └── BorescopeDataset/
        ├── train/images/
        ├── train/labels/
        ├── valid/images/
        ├── valid/labels/
        ├── test/images/
        └── test/labels/
```

For this Windows setup, the dataset path from the KeeAInu repository root is `../KeeAInu-training/BorescopeDataset`. Keep that local layout or set the dataset path explicitly in commands. Do not move or overwrite the original photos or YOLO label files as part of an experiment.

## Snapshot recorded from the local audit

These numbers describe the locally inspected snapshot, not a guarantee about future copies of the dataset.

| Split | Images | Box objects |
| --- | ---: | ---: |
| Train | 6,054 | 46,563 |
| Valid | 110 | 803 |
| Test | 116 | 887 |
| **Total** | **6,280** | **48,253** |

The source labels contain five classes, with these source IDs:

| Source ID | Source class name | Train objects | Valid objects | Test objects |
| ---: | --- | ---: | ---: | ---: |
| 0 | Chipping | 579 | 14 | 5 |
| 1 | Dirt | 9,894 | 183 | 241 |
| 2 | Pitting | 27,657 | 430 | 520 |
| 3 | Rusting | 7,677 | 149 | 117 |
| 4 | ThermalCracking (called Cracking in the pilot scripts) | 756 | 27 | 4 |

The planned KeeAInu taxonomy includes two additional classes—Welded Droplet and Erosion/Corrosion—but those classes are not present in this source label set. Do not assign those classes automatically or pretend the source set already contains examples of them.

The original YOLO labels are bounding boxes, not segmentation ground truth. Audits found suspicious labels/boxes, so they remain candidate hints rather than certified defect labels. Keep class mapping, provenance, and the distinction between source labels, model proposals, and human-reviewed references explicit.

## What the local experiments currently say

These are small exploratory results based on the local experiments described in the development notes. They are not production metrics.

- A manually checked reference set currently covers 18 polygon instances across only four unique images; represented classes are Chipping, Dirt, Rusting, and Erosion/Corrosion. This is too small to claim generalized segmentation accuracy or train a dependable seven-class model.
- With each reference polygon's bounding box supplied to SAM2 as a prompt, the reference-box benchmark reported mean IoU of about 0.73. A separate three-candidate report measured 0.7307 mean IoU for the score-selected candidate and 0.7624 for an oracle-best candidate. Oracle selection depends on the true reference mask and cannot be used in production.
- A prompt-expansion experiment on three difficult examples performed worse with 1.10x and 1.20x expanded boxes than with the tight reference bounding box. An inset experiment had mixed results.
- Source-box prompts and some SAM2 proposals followed pipe ribs/grooves instead of defect boundaries. Geometry warnings, SAM quality scores, and visual overlays are useful triage signals, not evidence that a mask or class is correct.

Treat these numbers as historical experiment notes. When scripts are committed, retain their exact configuration, code revision, source dataset identity, and benchmark reference revision beside any refreshed result. Do not combine scores from different experiments without checking the protocols match.

## What should be committed

**Commit to public GitHub after review:**

- Reusable audit, benchmarking, and training scripts.
- Tests, dependency/version notes, run commands, schemas, and class-mapping documentation.
- Text-based result summaries or metrics CSVs after checking them for secrets, private paths, and sensitive information.
- A dataset manifest recording source URL/name, license status, archive/file SHA-256, split counts, image/label counts, and the commands used to prepare data. The manifest should not contain the photos themselves.

**Keep local or in access-controlled data storage by default:**

- The full `BorescopeDataset` images and original labels until license and redistribution terms are verified.
- Copied pilot images, masks, overlays/contact sheets, videos, caches, downloaded weights, and bulky intermediate outputs.
- Annotation exports until they are checked for embedded `imageData`, private paths, and redistribution/IP considerations.
- Raw near-duplicate reports and audit artifacts if they include sensitive paths or metadata. Publish an aggregated text summary only after review.

Generated images and training assets under `data/segmentation` are ignored by the repository rules. This does not delete local files. Check `git status --ignored` when diagnosing what Git is excluding.

## Safe workflow for the training folder

1. Leave the source dataset in `KeeAInu-training/BorescopeDataset` and treat it as read-only.
2. Generate local inventory/checksum manifests and keep the dataset revision and source license evidence with the experiment notes.
3. Put scripts and documentation in KeeAInu; write masks, overlays, temporary splits, and benchmark outputs into separate, ignored local result directories.
4. Before staging any change, inspect `git status --short` and `git diff --stat`. Do not stage all files blindly with `git add .`.
5. Check for photo formats, video formats, model weights, archives, embedded image payloads, credentials, and `.env` files before committing.
6. If collaboration requires shared training data, choose a private, access-controlled object store or a versioned data system such as DVC with a secured remote after deciding who may access the data. Do not assume Git LFS makes redistribution rights or public exposure safe.
7. Before training, resolve source-label issues, verify duplicate leakage across splits, build a reliable polygon reference set, and document the exact train/validation/test split. Keep held-out test references out of tuning.

## Pending publishing checklist

- [ ] Confirm the origin, exact dataset revision, license, and redistribution terms for `BorescopeDataset`.
- [ ] Confirm all locally created scripts and benchmark documents are in the repository and committed.
- [ ] Inspect manually drawn LabelMe JSON exports to ensure `imageData` is not embedded before any possible publication.
- [ ] Review generated CSV/JSON summaries for local paths or sensitive metadata.
- [ ] Maintain a separate, read-only backup of the original training folder.

## Related documents

- [Dataset discovery and acquisition](DATASET_DISCOVERY_AND_ACQUISITION.md)
- [Local dataset pipeline](LOCAL_DATASET_PIPELINE.md)
- [Annotation schema](ANNOTATION_SCHEMA.md)
- [SAM2 proposal pilot (on its branch until reviewed)](https://github.com/keenu2004-ai/KeeAInu/blob/feat/sam2-mask-proposal-pipeline/scripts/dataset_pipeline/SAM2_MASK_PROPOSAL_PILOT.md)
