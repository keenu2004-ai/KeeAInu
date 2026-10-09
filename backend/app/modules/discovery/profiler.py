"""Visual Quality Profiler and Contact Sheet Generator (Explainable Heuristics)."""

import math
from pathlib import Path
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

from backend.app.core.security import calculate_sha256
from backend.app.schemas.discovery import QualityProfile


def compute_frame_quality_metrics(frame_bgr: np.ndarray) -> Dict[str, float]:
    """
    Calculate lightweight, explainable heuristic image metrics for a single frame.
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return {
            "sharpness": 0.0,
            "brightness_mean": 0.0,
            "contrast_std": 0.0,
            "overexposure_ratio": 0.0,
            "underexposure_ratio": 0.0,
        }

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    total_pixels = gray.size

    # Sharpness via Laplacian variance
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    
    # Brightness mean and contrast standard deviation
    brightness_mean = float(np.mean(gray))
    contrast_std = float(np.std(gray))

    # Overexposed and underexposed ratios
    overexposed_count = np.count_nonzero(gray >= 250)
    underexposed_count = np.count_nonzero(gray <= 10)

    overexposure_ratio = float(overexposed_count / total_pixels) if total_pixels > 0 else 0.0
    underexposure_ratio = float(underexposed_count / total_pixels) if total_pixels > 0 else 0.0

    return {
        "sharpness": round(laplacian_var, 2),
        "brightness_mean": round(brightness_mean, 2),
        "contrast_std": round(contrast_std, 2),
        "overexposure_ratio": round(overexposure_ratio, 4),
        "underexposure_ratio": round(underexposure_ratio, 4),
    }


def compute_near_duplicate_ratio(frames_bgr: List[np.ndarray]) -> float:
    """
    Estimate the ratio of consecutive frames that have minimal visual change (MSE < 35.0).
    """
    if len(frames_bgr) <= 1:
        return 0.0

    duplicates = 0
    comparisons = len(frames_bgr) - 1

    for i in range(comparisons):
        f1, f2 = frames_bgr[i], frames_bgr[i + 1]
        if f1.shape != f2.shape:
            f2 = cv2.resize(f2, (f1.shape[1], f1.shape[0]))
        mse = float(np.mean((f1.astype("float") - f2.astype("float")) ** 2))
        if mse < 35.0:
            duplicates += 1

    return round(duplicates / comparisons, 3) if comparisons > 0 else 0.0


def build_quality_profile(
    frames_bgr: List[np.ndarray],
    width: int,
    height: int,
    is_readable: bool,
    fps: float,
    total_frames: int
) -> QualityProfile:
    """
    Aggregate frame-level heuristics into an explainable asset-level QualityProfile.
    """
    if not is_readable or not frames_bgr:
        return QualityProfile(
            resolution=f"{width}x{height}",
            sharpness_score=0.0,
            blur_detected=True,
            brightness_mean=0.0,
            contrast_std=0.0,
            overexposure_ratio=0.0,
            underexposure_ratio=0.0,
            near_duplicate_ratio=0.0,
            metadata_reliability="LOW",
            explanations=["Media container unreadable or contains no decodable visual frames."]
        )

    metrics_list = [compute_frame_quality_metrics(f) for f in frames_bgr]
    
    avg_sharpness = float(np.mean([m["sharpness"] for m in metrics_list]))
    avg_brightness = float(np.mean([m["brightness_mean"] for m in metrics_list]))
    avg_contrast = float(np.mean([m["contrast_std"] for m in metrics_list]))
    avg_overexp = float(np.mean([m["overexposure_ratio"] for m in metrics_list]))
    avg_underexp = float(np.mean([m["underexposure_ratio"] for m in metrics_list]))
    near_dup_ratio = compute_near_duplicate_ratio(frames_bgr)

    blur_detected = avg_sharpness < 75.0
    
    # Assess metadata reliability
    if fps > 0 and total_frames > 0:
        metadata_rel = "HIGH"
    elif total_frames > 0:
        metadata_rel = "NOMINAL"
    else:
        metadata_rel = "LOW"

    # Human-readable diagnostic observations (heuristic warnings)
    explanations = []
    if blur_detected:
        explanations.append(f"Low edge sharpness ({avg_sharpness:.1f} < 75.0 threshold) indicates optical defocus or motion blur.")
    else:
        explanations.append(f"Edge sharpness ({avg_sharpness:.1f}) is within acceptable range for visual inspection.")

    if avg_brightness < 40.0:
        explanations.append(f"Low average illumination ({avg_brightness:.1f}/255) indicates underexposed borescope lighting.")
    elif avg_brightness > 210.0:
        explanations.append(f"High average illumination ({avg_brightness:.1f}/255) indicates optical glare or overexposure.")

    if avg_contrast < 25.0:
        explanations.append(f"Low visual contrast ({avg_contrast:.1f}) may impede fine surface texture examination.")

    if avg_overexp > 0.15:
        explanations.append(f"Overexposure hotspot ratio ({avg_overexp*100:.1f}%) exceeds recommended 15% threshold.")

    if near_dup_ratio > 0.6:
        explanations.append(f"High static frame ratio ({near_dup_ratio*100:.1f}%) suggests probe was stationary during recording.")

    return QualityProfile(
        resolution=f"{width}x{height}",
        sharpness_score=round(avg_sharpness, 2),
        blur_detected=blur_detected,
        brightness_mean=round(avg_brightness, 2),
        contrast_std=round(avg_contrast, 2),
        overexposure_ratio=round(avg_overexp, 4),
        underexposure_ratio=round(avg_underexp, 4),
        near_duplicate_ratio=round(near_dup_ratio, 3),
        metadata_reliability=metadata_rel,
        explanations=explanations
    )


def generate_contact_sheet(
    frames_bgr: List[np.ndarray],
    frame_indices: List[int],
    output_path: Path,
    target_thumb_size: Tuple[int, int] = (240, 180),
    cols: int = 3
) -> Tuple[Path, str]:
    """
    Assemble sampled video/image frames into a clean contact sheet mosaic.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(frames_bgr)
    if n == 0:
        raise ValueError("Cannot create contact sheet from empty frame list.")

    cols = min(cols, n)
    rows = math.ceil(n / cols)
    tw, th = target_thumb_size
    margin = 8
    header_h = 24

    sheet_w = cols * tw + (cols + 1) * margin
    sheet_h = rows * (th + header_h) + (rows + 1) * margin

    contact_sheet = np.full((sheet_h, sheet_w, 3), 24, dtype=np.uint8)

    for idx, (frame, f_idx) in enumerate(zip(frames_bgr, frame_indices)):
        r = idx // cols
        c = idx % cols

        x0 = margin + c * (tw + margin)
        y0 = margin + r * (th + header_h + margin)

        resized = cv2.resize(frame, (tw, th))
        # Place frame
        contact_sheet[y0 + header_h:y0 + header_h + th, x0:x0 + tw] = resized

        # Draw frame badge / header
        cv2.rectangle(contact_sheet, (x0, y0), (x0 + tw, y0 + header_h), (38, 38, 38), -1)
        cv2.putText(
            contact_sheet,
            f"Frame #{f_idx}",
            (x0 + 6, y0 + 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (6, 182, 212),
            1,
            cv2.LINE_AA
        )

    # Save JPEG
    cv2.imwrite(str(output_path), contact_sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    digest = calculate_sha256(output_path)
    return output_path, digest
