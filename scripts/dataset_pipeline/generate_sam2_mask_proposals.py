#!/usr/bin/env python
"""Generate SAM 2 segmentation-mask proposals from existing YOLO boxes.

Outputs are unverified proposals only. This script never changes source images or labels.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import Sam2Model, Sam2Processor

# Only the five classes actually present in the current source YOLO dataset.
# IDs 5 and 6 are not guessed or inferred by this script.
CLASS_NAMES = {
    0: "Chipping",
    1: "Dirt",
    2: "Pitting",
    3: "Rusting",
    4: "Cracking",
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="BorescopeDataset root")
    parser.add_argument("--split", choices=("train", "valid", "test"), default="train")
    parser.add_argument("--out", default="data/segmentation/sam2_proposals_pilot")
    parser.add_argument("--model", default="facebook/sam2.1-hiera-tiny")
    parser.add_argument("--limit", type=int, default=10, help="Max images; use 10 for first pilot")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--large-box-fraction", type=float, default=0.70)
    return parser.parse_args()


def read_boxes(label_path: Path, width: int, height: int):
    boxes = []
    if not label_path.exists():
        return boxes
    for line_number, line in enumerate(label_path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 5:
            boxes.append({"line": line_number, "error": "fewer_than_5_fields"})
            continue
        try:
            class_id = int(fields[0])
            x_center, y_center, box_width, box_height = map(float, fields[1:5])
        except ValueError:
            boxes.append({"line": line_number, "error": "invalid_numeric_value"})
            continue
        x1 = max(0, min(width - 1, round((x_center - box_width / 2) * width)))
        y1 = max(0, min(height - 1, round((y_center - box_height / 2) * height)))
        x2 = max(0, min(width, round((x_center + box_width / 2) * width)))
        y2 = max(0, min(height, round((y_center + box_height / 2) * height)))
        if x2 <= x1 or y2 <= y1:
            boxes.append({"line": line_number, "error": "invalid_box_geometry"})
            continue
        boxes.append({
            "class_id": class_id,
            "class_name": CLASS_NAMES.get(class_id, f"UNKNOWN_CLASS_{class_id}"),
            "box": [x1, y1, x2, y2],
            "box_area_fraction": ((x2 - x1) * (y2 - y1)) / (width * height),
        })
    return boxes


def largest_polygon(mask: np.ndarray):
    contours, _ = cv2.findContours(mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []
    contour = max(contours, key=cv2.contourArea)
    epsilon = max(1.0, 0.0015 * cv2.arcLength(contour, True))
    points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
    return points.tolist() if len(points) >= 3 else []


def main():
    args = parse_args()
    dataset = Path(args.dataset).expanduser().resolve()
    output = Path(args.out).expanduser().resolve()
    image_dir = dataset / args.split / "images"
    label_dir = dataset / args.split / "labels"
    if not image_dir.is_dir() or not label_dir.is_dir():
        raise FileNotFoundError(f"Expected split folders: {image_dir} and {label_dir}")

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else (
        "cpu" if args.device == "auto" else args.device
    )
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    for folder in ("masks", "overlays", "proposed_yolo_seg"):
        (output / folder).mkdir(parents=True, exist_ok=True)

    print(f"Loading {args.model} on {device}; first run downloads the model weights.")
    processor = Sam2Processor.from_pretrained(args.model)
    model = Sam2Model.from_pretrained(args.model).to(device).eval()
    image_paths = sorted(
        p for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        and (label_dir / f"{p.stem}.txt").exists()
    )

    rows = []
    processed = 0
    for image_path in image_paths:
        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            rows.append({
                "image": image_path.name, "box_index": "", "source_class_id": "",
                "source_class_name": "", "status": "IMAGE_READ_ERROR",
                "box_area_fraction": "", "mask_area_fraction": "", "sam_iou_score": "",
                "notes": str(exc),
            })
            continue

        width, height = image.size
        boxes = read_boxes(label_dir / f"{image_path.stem}.txt", width, height)
        if not boxes:
            continue
        overlay = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        polygon_lines = []

        for index, box_info in enumerate(boxes):
            if "error" in box_info:
                rows.append({
                    "image": image_path.name, "box_index": box_info["line"],
                    "source_class_id": "", "source_class_name": "",
                    "status": "SOURCE_LABEL_PARSE_ERROR", "box_area_fraction": "",
                    "mask_area_fraction": "", "sam_iou_score": "", "notes": box_info["error"],
                })
                continue

            x1, y1, x2, y2 = box_info["box"]
            box_fraction = box_info["box_area_fraction"]
            inputs = processor(
                images=image, input_boxes=[[[x1, y1, x2, y2]]], return_tensors="pt"
            )
            inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
            with torch.inference_mode():
                outputs = model(**inputs)

            masks = processor.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"].cpu())[0]
            scores = outputs.iou_scores.detach().cpu().numpy().reshape(-1)
            best_index = int(np.argmax(scores)) if len(scores) else 0
            mask = masks[0, best_index].numpy() > 0
            if mask.shape != (height, width):
                mask = cv2.resize(mask.astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)

            mask_fraction = float(mask.sum()) / (width * height)
            score = float(scores[best_index]) if len(scores) else float("nan")
            flags = []
            if box_fraction > args.large_box_fraction:
                flags.append("SOURCE_BOX_OVERSIZED")
            if mask_fraction <= 0 or mask_fraction > 0.85:
                flags.append("EMPTY_OR_NEAR_FULL_IMAGE_MASK")
            inside_fraction = float(mask[y1:y2, x1:x2].sum()) / max(1, int(mask.sum()))
            if inside_fraction < 0.5:
                flags.append("MASK_MOSTLY_OUTSIDE_PROMPT_BOX")
            if score < 0.70:
                flags.append("LOW_SAM_SCORE")
            status = "REVIEW_REQUIRED" if flags else "PROPOSAL_GENERATED"

            cv2.imwrite(str(output / "masks" / f"{image_path.stem}_box{index:03d}.png"), mask.astype(np.uint8) * 255)
            green = np.zeros_like(overlay)
            green[:, :, 1] = 255
            overlay[mask] = cv2.addWeighted(overlay[mask], 0.45, green[mask], 0.55, 0)
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(
                overlay, f"PROPOSAL {index} {box_info['class_name']} {score:.2f}",
                (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1
            )

            polygon = largest_polygon(mask)
            if polygon:
                coords = []
                for px, py in polygon:
                    coords.extend((f"{px / width:.6f}", f"{py / height:.6f}"))
                polygon_lines.append(str(box_info["class_id"]) + " " + " ".join(coords))

            rows.append({
                "image": image_path.name, "box_index": index,
                "source_class_id": box_info["class_id"],
                "source_class_name": box_info["class_name"], "status": status,
                "box_area_fraction": round(box_fraction, 7),
                "mask_area_fraction": round(mask_fraction, 7),
                "sam_iou_score": round(score, 5),
                "notes": ";".join(flags) if flags else "Proposal only; source class unverified.",
            })

        cv2.imwrite(str(output / "overlays" / f"{image_path.stem}_overlay.jpg"), overlay)
        if polygon_lines:
            (output / "proposed_yolo_seg" / f"{image_path.stem}.txt").write_text(
                "\n".join(polygon_lines) + "\n", encoding="utf-8"
            )
        processed += 1
        if processed % 5 == 0:
            print(f"Processed {processed} images...")
        if args.limit > 0 and processed >= args.limit:
            break

    columns = [
        "image", "box_index", "source_class_id", "source_class_name", "status",
        "box_area_fraction", "mask_area_fraction", "sam_iou_score", "notes",
    ]
    with (output / "proposal_report.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "model": args.model, "split": args.split, "images_processed": processed,
        "box_records": len(rows),
        "proposal_generated": sum(row.get("status") == "PROPOSAL_GENERATED" for row in rows),
        "review_required": sum(row.get("status") == "REVIEW_REQUIRED" for row in rows),
        "warning": "Unverified mask proposals; class IDs are inherited from source boxes, not predicted.",
        "source_dataset_modified": False,
        "output_dir": str(output),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Report: {output / 'proposal_report.csv'}")


if __name__ == "__main__":
    main()
