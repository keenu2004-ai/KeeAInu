
from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT.parent / "KeeAInu-training" / "BorescopeDataset"
OUTPUT_DIR = PROJECT_ROOT / "data" / "segmentation" / "review"
OUTPUT_CSV = OUTPUT_DIR / "image_quality_audit.csv"

SPLITS = ("train", "valid", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def inspect_image(path: Path) -> dict:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    result = {
        "image_path": str(path.resolve()),
        "readable": False,
        "width": "",
        "height": "",
        "mean_brightness": "",
        "dark_pixel_pct": "",
        "bright_pixel_pct": "",
        "grayscale_stddev": "",
        "laplacian_variance": "",
        "quality_flags": "",
    }

    if image is None:
        result["quality_flags"] = "UNREADABLE"
        return result

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    dark_pct = float(np.mean(gray < 20) * 100)
    bright_pct = float(np.mean(gray >= 245) * 100)
    contrast = float(np.std(gray))
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    flags = []

    # Screening flags only; these are not automatic rejection criteria.
    if bright_pct >= 20:
        flags.append("POSSIBLE_OVEREXPOSURE")
    if dark_pct >= 20:
        flags.append("POSSIBLE_UNDEREXPOSURE")
    if contrast < 25:
        flags.append("LOW_CONTRAST")
    if laplacian_var < 30:
        flags.append("POSSIBLE_BLUR")
    if width < 320 or height < 240:
        flags.append("LOW_RESOLUTION")

    result.update({
        "readable": True,
        "width": width,
        "height": height,
        "mean_brightness": round(brightness, 3),
        "dark_pixel_pct": round(dark_pct, 3),
        "bright_pixel_pct": round(bright_pct, 3),
        "grayscale_stddev": round(contrast, 3),
        "laplacian_variance": round(laplacian_var, 3),
        "quality_flags": ";".join(flags) if flags else "NO_BASIC_FLAG",
    })

    return result


def main() -> None:
    if not DATASET_ROOT.is_dir():
        raise FileNotFoundError(
            f"Dataset directory not found: {DATASET_ROOT}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    for split in SPLITS:
        image_dir = DATASET_ROOT / split / "images"

        if not image_dir.is_dir():
            print(f"WARNING: Missing image directory: {image_dir}")
            continue

        paths = sorted(
            path for path in image_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )

        print(f"Auditing {split}: {len(paths)} images")

        for index, path in enumerate(paths, start=1):
            record = inspect_image(path)
            record["split"] = split
            records.append(record)

            if index % 500 == 0 or index == len(paths):
                print(f"  {split}: {index}/{len(paths)}")

    fieldnames = [
        "split",
        "image_path",
        "readable",
        "width",
        "height",
        "mean_brightness",
        "dark_pixel_pct",
        "bright_pixel_pct",
        "grayscale_stddev",
        "laplacian_variance",
        "quality_flags",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    unreadable = sum(not row["readable"] for row in records)
    flagged = sum(
        row["quality_flags"] != "NO_BASIC_FLAG"
        for row in records
    )

    print("\nAudit complete")
    print(f"Images scanned: {len(records)}")
    print(f"Unreadable images: {unreadable}")
    print(f"Images with screening flags: {flagged}")
    print(f"CSV report: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
