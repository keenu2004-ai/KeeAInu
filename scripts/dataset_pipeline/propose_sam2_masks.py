#!/usr/bin/env python
"""Generate SAM 2.1 mask proposals from YOLO boxes. These are NOT verified labels."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image
from transformers import Sam2Model, Sam2Processor

CLASS_NAMES = {0: "Chipping", 1: "Dirt", 2: "Pitting", 3: "Rusting", 4: "Cracking"}
DEFAULT_MODEL = "facebook/sam2.1-hiera-tiny"

def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", required=True, help="BorescopeDataset path (train/images and train/labels)")
    p.add_argument("--split", choices=("train", "valid", "test"), default="train")
    p.add_argument("--out", default="data/segmentation/sam2_proposals_pilot")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--limit", type=int, default=10, help="Images to process; start small")
    p.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return p.parse_args()

def read_boxes(path: Path, width: int, height: int):
    boxes = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = line.split()
        if not parts:
            continue
        try:
            cls = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:5])
            x1 = max(0, min(width - 1, int((xc - bw / 2) * width)))
            y1 = max(0, min(height - 1, int((yc - bh / 2) * height)))
            x2 = max(0, min(width - 1, int((xc + bw / 2) * width)))
            y2 = max(0, min(height - 1, int((yc + bh / 2) * height)))
            if x2 <= x1 or y2 <= y1:
                raise ValueError("invalid box geometry")
            boxes.append({"line": line_no, "class_id": cls,
                          "class_name": CLASS_NAMES.get(cls, f"UNKNOWN_{cls}"),
                          "xyxy": [x1, y1, x2, y2],
                          "area_fraction": ((x2-x1)*(y2-y1))/(width*height)})
        except (ValueError, IndexError) as exc:
            boxes.append({"line": line_no, "error": str(exc)})
    return boxes

def polygon_from_mask(mask: np.ndarray):
    contours, _ = cv2.findContours(mask.astype(np.uint8)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    points = cv2.approxPolyDP(contour, max(1.0, 0.0015*cv2.arcLength(contour, True)), True).reshape(-1, 2)
    return points if len(points) >= 3 else []

def main():
    args = parse_args()
    dataset = Path(args.dataset).expanduser().resolve()
    image_dir, label_dir = dataset/args.split/"images", dataset/args.split/"labels"
    if not image_dir.is_dir() or not label_dir.is_dir():
        raise FileNotFoundError(f"Expected directories: {image_dir} and {label_dir}")
    out = Path(args.out).resolve()
    masks_dir, overlays_dir, seg_dir = out/"masks", out/"overlays", out/"proposed_yolo_seg"
    for folder in (out, masks_dir, overlays_dir, seg_dir):
        folder.mkdir(parents=True, exist_ok=True)
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable.")
    print(f"Loading {args.model} on {device}; first run downloads weights.")
    processor = Sam2Processor.from_pretrained(args.model)
    model = Sam2Model.from_pretrained(args.model).to(device).eval()
    image_paths = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"})
    records, processed = [], 0

    for image_path in image_paths:
        label_path = label_dir/(image_path.stem + ".txt")
        if not label_path.exists():
            continue
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            records.append({"image": image_path.name, "box_index": "", "source_class_id": "",
                "source_class_name": "", "status": "IMAGE_READ_ERROR", "box_area_fraction": "",
                "mask_area_fraction": "", "sam_score": "", "notes": str(exc)})
            continue
        width, height = image.size
        boxes = read_boxes(label_path, width, height)
        overlay = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        seg_lines = []

        for box_index, box in enumerate(boxes):
            if "error" in box:
                records.append({"image": image_path.name, "box_index": box_index, "source_class_id": "",
                    "source_class_name": "", "status": "SOURCE_LABEL_ERROR", "box_area_fraction": "",
                    "mask_area_fraction": "", "sam_score": "", "notes": box["error"]})
                continue
            x1, y1, x2, y2 = box["xyxy"]
            box_fraction = box["area_fraction"]
            if box_fraction < 0.00005:
                records.append({"image": image_path.name, "box_index": box_index,
                    "source_class_id": box["class_id"], "source_class_name": box["class_name"],
                    "status": "SKIPPED_TINY_BOX", "box_area_fraction": round(box_fraction, 8),
                    "mask_area_fraction": "", "sam_score": "", "notes": "Tiny source box"})
                continue

            inputs = processor(images=image, input_boxes=[[[x1, y1, x2, y2]]], return_tensors="pt")
            inputs = {k: v.to(device) if hasattr(v, "to") else v for k, v in inputs.items()}
            with torch.inference_mode():
                outputs = model(**inputs)
            masks = processor.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"].cpu())[0]
            scores = outputs.iou_scores.detach().cpu().numpy().reshape(-1)
            best = int(np.argmax(scores)) if len(scores) else 0
            mask = masks[0, best].numpy() > 0
            if mask.shape != (height, width):
                mask = cv2.resize(mask.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
            mask_fraction = float(mask.sum())/(width*height)
            score = float(scores[best]) if len(scores) else float("nan")
            points = polygon_from_mask(mask)
            flags = []
            if box_fraction > 0.70: flags.append("SOURCE_BOX_OVERSIZED")
            if mask_fraction <= 0 or len(points) < 3: flags.append("EMPTY_OR_INVALID_MASK")
            if mask_fraction > 0.85: flags.append("MASK_COVERS_MOST_OF_IMAGE")
            if float(mask[y1:y2, x1:x2].sum())/max(1, int(mask.sum())) < 0.5: flags.append("MASK_MOSTLY_OUTSIDE_BOX")
            if score < 0.70: flags.append("LOW_SAM_SCORE")
            status = "REVIEW_REQUIRED" if flags else "PROPOSAL_ONLY"

            cv2.imwrite(str(masks_dir/f"{image_path.stem}_box{box_index:03d}.png"), mask.astype(np.uint8)*255)
            green = np.zeros_like(overlay); green[:, :, 1] = 255
            overlay[mask] = cv2.addWeighted(overlay[mask], 0.45, green[mask], 0.55, 0)
            cv2.rectangle(overlay, (x1,y1), (x2,y2), (0,0,255), 2)
            cv2.putText(overlay, f"PROPOSAL {box_index} {box['class_name']} {score:.2f}",
                (x1, max(18,y1-5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
            if len(points) >= 3:
                coords = []
                for x, y in points:
                    coords.extend((f"{x/width:.6f}", f"{y/height:.6f}"))
                seg_lines.append(str(box["class_id"]) + " " + " ".join(coords))
            records.append({"image": image_path.name, "box_index": box_index,
                "source_class_id": box["class_id"], "source_class_name": box["class_name"],
                "status": status, "box_area_fraction": round(box_fraction, 8),
                "mask_area_fraction": round(mask_fraction, 8), "sam_score": round(score, 5),
                "notes": ";".join(flags) if flags else "Mask proposal only; source class remains unverified"})

        cv2.imwrite(str(overlays_dir/f"{image_path.stem}_overlay.jpg"), overlay)
        if seg_lines:
            (seg_dir/f"{image_path.stem}.txt").write_text("\n".join(seg_lines)+"\n", encoding="utf-8")
        processed += 1
        if processed % 5 == 0: print(f"Processed {processed} images")
        if args.limit > 0 and processed >= args.limit: break

    fields = ["image","box_index","source_class_id","source_class_name","status","box_area_fraction","mask_area_fraction","sam_score","notes"]
    with (out/"proposal_report.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(records)
    summary = {"model": args.model, "split": args.split, "images_processed": processed,
        "box_records": len(records), "proposal_only": sum(r.get("status")=="PROPOSAL_ONLY" for r in records),
        "review_required": sum(r.get("status")=="REVIEW_REQUIRED" for r in records),
        "warning": "Masks and inherited classes are unverified proposals. Do not train on them as ground truth.",
        "output_dir": str(out)}
    (out/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {out/'proposal_report.csv'}")

if __name__ == "__main__":
    main()
