# SAM 2 Mask Proposal Pilot

This is a model-assisted annotation utility for the KeeAInu industrial-inspection dataset. It uses Hugging Face Transformers' SAM 2.1 promptable segmenter to propose pixel masks from existing YOLO bounding boxes.

## Important limitations

- These are **pseudo-label proposals**, not verified ground truth.
- SAM 2 segments a prompted region; it does not decide whether the source class is truly Chipping, Dirt, Pitting, Rusting, or Cracking.
- Bad or oversized source boxes can produce bad masks. A high SAM score estimates mask quality, not defect-class correctness.
- The current source dataset has IDs 0–4. This script deliberately does not invent labels for target classes 5 and 6.
- Original images and labels are read-only. All generated files are written to a separate output directory.

## Run from the KeeAInu videoscopes project folder

Install the additional dependencies into the active virtual environment:

```powershell
python -m pip install --upgrade "transformers>=4.57.0" pillow opencv-python
```

Run a 10-image pilot first (the dataset is a sibling folder named `KeeAInu-training` in the user's current setup):

```powershell
python .\scripts\dataset_pipeline\generate_sam2_mask_proposals.py `
  --dataset "..\KeeAInu-training\BorescopeDataset" `
  --split train `
  --out ".\data\segmentation\sam2_proposals_pilot" `
  --model "facebook/sam2.1-hiera-tiny" `
  --limit 10 `
  --device cpu
```

The first run downloads model weights. CPU inference will be slow on a low-power CPU. If a CUDA GPU is available in a cloud notebook, use `--device cuda` there.

## Outputs

- `proposal_report.csv`: one record per source box with mask area, SAM score, and automatic warning flags.
- `summary.json`: run configuration and counts.
- `masks/`: binary PNG proposal for each box.
- `overlays/`: source image overlaid with the candidate mask and original bounding box.
- `proposed_yolo_seg/`: candidate polygon labels, stored separately from the source dataset.

Do not train on these files until class identity and mask boundaries have been independently validated. The next development step should compare proposals against a small trusted seed of masks, measure boundary quality, and then decide whether to scale up or move inference to a GPU.
