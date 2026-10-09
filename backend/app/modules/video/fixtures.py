"""Synthetic Inspection Test Media Fixture Generator."""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
import cv2
import numpy as np

from backend.app.core.security import calculate_sha256
from backend.app.schemas.annotation import (
    GroundTruthDatasetRecord,
    GroundTruthAnnotationItem,
    NormalizedBoundingBox,
    ProvenanceType
)


def generate_synthetic_image(
    output_path: Path,
    width: int = 320,
    height: int = 240,
    pattern_type: str = "grid"
) -> Tuple[Path, str]:
    """
    Generate a deterministic synthetic inspection test image.
    Outputs PNG or JPG based on extension.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Background gradient simulating metallic borescope tube interior
    for y in range(height):
        intensity = int(40 + 40 * np.sin(np.pi * y / height))
        img[y, :, :] = (intensity, intensity, intensity + 10)
        
    # Draw reference grid
    grid_spacing = 40
    for x in range(0, width, grid_spacing):
        cv2.line(img, (x, 0), (x, height), (70, 70, 70), 1)
    for y in range(0, height, grid_spacing):
        cv2.line(img, (0, y), (width, y), (70, 70, 70), 1)
        
    if pattern_type == "grid":
        # Draw synthetic test crack
        pts = np.array([[80, 70], [110, 85], [140, 80], [180, 110], [220, 115]], np.int32)
        cv2.polylines(img, [pts], isClosed=False, color=(20, 20, 220), thickness=2)
        cv2.putText(img, "TEST PATTERN: SYNTHETIC CRACK", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
    elif pattern_type == "pit":
        # Draw synthetic circular pit mark
        cv2.circle(img, (160, 120), 25, (30, 30, 30), -1)
        cv2.circle(img, (160, 120), 25, (0, 140, 255), 1)
        cv2.putText(img, "TEST PATTERN: SYNTHETIC PIT", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # Save image
    cv2.imwrite(str(output_path), img)
    digest = calculate_sha256(output_path)
    return output_path, digest


def generate_synthetic_video(
    output_path: Path,
    width: int = 320,
    height: int = 240,
    fps: float = 30.0,
    num_frames: int = 30
) -> Tuple[Path, str, GroundTruthDatasetRecord]:
    """
    Generate a deterministic 30-frame synthetic test video and its matching GroundTruthDatasetRecord.
    Tries robust codecs (mp4v, avc1, FMP4, MJPG) and verifies decodability.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()

    if suffix == ".mp4":
        fourcc_candidates = ["mp4v", "avc1", "FMP4", "H264"]
    elif suffix == ".avi":
        fourcc_candidates = ["MJPG", "XVID"]
    else:
        fourcc_candidates = ["mp4v", "MJPG", "XVID"]

    written_successfully = False
    actual_path = output_path

    for candidate in fourcc_candidates:
        fourcc = cv2.VideoWriter_fourcc(*candidate)
        out = cv2.VideoWriter(str(actual_path), fourcc, fps, (width, height))
        if not out.isOpened():
            continue

        for idx in range(num_frames):
            img = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Background gradient
            for y in range(height):
                base_color = int(50 + 30 * np.sin(np.pi * y / height + idx * 0.1))
                img[y, :, :] = (base_color, base_color + 5, base_color + 10)
                
            # Draw crosshair and frame counter
            cv2.line(img, (width // 2, 0), (width // 2, height), (60, 60, 60), 1)
            cv2.line(img, (0, height // 2), (width, height // 2), (60, 60, 60), 1)
            cv2.putText(img, f"SYNTHETIC TEST - FRAME {idx:02d}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            
            timestamp_ms = (idx / fps) * 1000.0
            cv2.putText(img, f"TS: {timestamp_ms:.1f}ms", (10, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # Synthetic defect pattern present on frames 10 to 20
            if 10 <= idx <= 20:
                x_start = 100 + (idx - 10) * 2
                y_start = 80
                pts = np.array([
                    [x_start, y_start],
                    [x_start + 25, y_start + 20],
                    [x_start + 50, y_start + 15],
                    [x_start + 70, y_start + 35]
                ], np.int32)
                cv2.polylines(img, [pts], isClosed=False, color=(0, 0, 255), thickness=2)

            out.write(img)

        out.release()

        # Verification step: ensure file exists, non-empty, and can be decoded
        if actual_path.exists() and actual_path.stat().st_size > 0:
            cap = cv2.VideoCapture(str(actual_path))
            if cap.isOpened():
                ret, test_frame = cap.read()
                cap.release()
                if ret and test_frame is not None:
                    written_successfully = True
                    break
        
        # If writing or decoding failed with this codec, delete and try next candidate
        if actual_path.exists():
            try:
                actual_path.unlink()
            except OSError:
                pass

    if not written_successfully:
        # Fallback to AVI with MJPG if MP4 codecs failed on this platform
        actual_path = output_path.with_suffix(".avi")
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        out = cv2.VideoWriter(str(actual_path), fourcc, fps, (width, height))
        if not out.isOpened():
            raise RuntimeError(f"Failed to open VideoWriter for synthetic video fallback at {actual_path}")

        for idx in range(num_frames):
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(height):
                base_color = int(50 + 30 * np.sin(np.pi * y / height + idx * 0.1))
                img[y, :, :] = (base_color, base_color + 5, base_color + 10)
            cv2.putText(img, f"SYNTHETIC TEST - FRAME {idx:02d}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
            out.write(img)
        out.release()

        if not actual_path.exists() or actual_path.stat().st_size == 0:
            raise RuntimeError(f"Failed to generate decodable synthetic video fixture at {actual_path}")

    # Build annotations
    annotations = []
    for idx in range(10, 21):
        x_start = 100 + (idx - 10) * 2
        y_start = 80
        timestamp_ms = (idx / fps) * 1000.0
        x_min = float(x_start) / width
        y_min = float(y_start) / height
        x_max = float(x_start + 75) / width
        y_max = float(y_start + 40) / height
        annotations.append(
            GroundTruthAnnotationItem(
                annotation_id=f"ann_synth_f{idx:02d}",
                frame_index=idx,
                timestamp_ms=round(timestamp_ms, 2),
                defect_class="TEST_PATTERN_CRACK_SYNTHETIC",
                bbox=NormalizedBoundingBox(
                    x_min=round(x_min, 4),
                    y_min=round(y_min, 4),
                    x_max=round(x_max, 4),
                    y_max=round(y_max, 4)
                ),
                inspector_notes="Controlled synthetic test crack pattern for pipeline verification",
                metadata={"synthetic_frame": True, "frame_index": idx}
            )
        )

    digest = calculate_sha256(actual_path)
    
    dataset_record = GroundTruthDatasetRecord(
        schema_version="1.0.0",
        dataset_id="dataset_synthetic_test_corpus_v1",
        media_id=actual_path.stem,
        media_sha256=digest,
        media_filename=actual_path.name,
        image_width=width,
        image_height=height,
        provenance=ProvenanceType.SYNTHETIC_GENERATED,
        is_synthetic=True,
        annotations=annotations
    )
    
    return actual_path, digest, dataset_record


def build_synthetic_corpus(output_dir: Path) -> Dict[str, Any]:
    """
    Build the full deterministic test fixture corpus and write manifest.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    img_grid_path, img_grid_hash = generate_synthetic_image(
        output_dir / "synthetic_still_grid.png", pattern_type="grid"
    )
    img_pit_path, img_pit_hash = generate_synthetic_image(
        output_dir / "synthetic_still_pit.jpg", pattern_type="pit"
    )
    video_path, video_hash, dataset_record = generate_synthetic_video(
        output_dir / "synthetic_test_video.mp4"
    )
    
    # Write dataset record JSON
    annotation_file = output_dir / "synthetic_test_video_annotations.json"
    with open(annotation_file, "w", encoding="utf-8") as f:
        f.write(dataset_record.model_dump_json(indent=2))
        
    manifest = {
        "corpus_name": "KeeAInu Synthetic Test Corpus",
        "version": "1.0.0",
        "is_synthetic": True,
        "items": [
            {
                "id": "synthetic_still_grid",
                "filename": img_grid_path.name,
                "sha256": img_grid_hash,
                "type": "image/png",
                "width": 320,
                "height": 240
            },
            {
                "id": "synthetic_still_pit",
                "filename": img_pit_path.name,
                "sha256": img_pit_hash,
                "type": "image/jpeg",
                "width": 320,
                "height": 240
            },
            {
                "id": "synthetic_test_video",
                "filename": video_path.name,
                "sha256": video_hash,
                "type": "video/mp4" if video_path.suffix.lower() == ".mp4" else "video/x-msvideo",
                "width": 320,
                "height": 240,
                "fps": 30.0,
                "frame_count": 30,
                "annotations_file": annotation_file.name
            }
        ]
    }
    
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    return manifest
