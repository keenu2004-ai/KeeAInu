"""KeeAInu Real Footage Annotation Pilot and Dataset Tool.

Features:
1. Inventory and representative selection of genuine source footage (G1_*.jpg).
2. Immutable SHA-256 evidence calculation and metadata tracking.
3. Database ingestion of representative pilot images into a dedicated inspection session.
4. Practical human annotation workflow for real defects and verified defect-free certification.
5. Strict enforcement: Never generates, simulates, or fabricates human labels.
6. Export and validation of versioned YOLO ground-truth datasets.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional, Any
import cv2

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256
from backend.app.db.repository import repo
from backend.app.modules.evaluation.exporter import (
    DatasetExporter,
    validate_yolo_dataset,
    DatasetValidationError,
    EmptyDatasetExportError
)
from backend.app.schemas.taxonomy import DefectCategory


def compute_image_metrics(path: Path) -> Dict[str, Any]:
    """Computes SHA-256 hash, dimensions, and Laplacian variance sharpness."""
    content = path.read_bytes()
    sha256 = calculate_sha256(content)
    img = cv2.imread(str(path))
    if img is None:
        return {
            "path": path,
            "filename": path.name,
            "sha256": sha256,
            "readable": False,
            "width": 0,
            "height": 0,
            "sharpness": 0.0,
            "file_size": len(content)
        }
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    h, w = img.shape[:2]
    return {
        "path": path,
        "filename": path.name,
        "sha256": sha256,
        "readable": True,
        "width": w,
        "height": h,
        "sharpness": round(sharpness, 2),
        "file_size": len(content)
    }


def select_representative_pilot_frames(
    source_dir: Optional[Path] = None,
    sample_count: int = 12
) -> List[Dict[str, Any]]:
    """
    Selects a temporally distributed, high-clarity sample of genuine videoscope images.
    Preserves original files without modifying or copying them.
    """
    src = source_dir or settings.SOURCE_FOOTAGE_DIR
    files = sorted(list(src.glob("G1_*.jpg")))
    if not files:
        files = sorted(list(src.glob("*.jpg")))
    if not files:
        return []

    # Stratified sampling across time sequence
    n = len(files)
    step = max(1, n // sample_count)
    selected_indices = [min(i * step, n - 1) for i in range(sample_count)]
    # De-duplicate while preserving order
    unique_indices = []
    seen = set()
    for idx in selected_indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)

    pilot_items = []
    for idx in unique_indices:
        f = files[idx]
        metrics = compute_image_metrics(f)
        metrics["sequence_index"] = idx
        pilot_items.append(metrics)

    return pilot_items


def cmd_inventory(args):
    """List representative footage inventory with SHA-256 digests."""
    pilot = select_representative_pilot_frames(sample_count=args.count)
    total_files = len(list(settings.SOURCE_FOOTAGE_DIR.glob("*.jpg")))
    print(f"\n=======================================================")
    print(f" KeeAInu Real Footage Inventory & Pilot Cohort")
    print(f" Source Directory: {settings.SOURCE_FOOTAGE_DIR}")
    print(f" Total Real Images Found: {total_files}")
    print(f" Selected Representative Pilot Frames: {len(pilot)}")
    print(f"=======================================================\n")
    print(f"{'Idx':<4} {'Filename':<28} {'Resolution':<12} {'Sharpness':<10} {'SHA-256 (Prefix)':<16} {'Size (KB)'}")
    print(f"-" * 80)
    for p in pilot:
        print(f"{p['sequence_index']:<4} {p['filename']:<28} {p['width']}x{p['height']:<7} {p['sharpness']:<10} {p['sha256'][:14]}... {round(p['file_size']/1024, 1)} KB")
    print(f"-" * 80)
    print(f"\nAll source media preserved with immutable SHA-256 evidence.\n")


def cmd_setup_session(args):
    """Creates a dedicated inspection session and imports representative pilot frames."""
    session_id = args.session_id or "sess_pilot_g1_real"
    existing = repo.get_session(session_id)
    if not existing:
        repo.create_session(
            session_id=session_id,
            title="Real Videoscope Footage Pilot Inspection (G1 Borescope)",
            inspector_name=args.inspector,
            asset_tag="G1_BORESCOPE_20231216"
        )
        print(f"Created dedicated pilot session: {session_id}")
    else:
        print(f"Pilot session '{session_id}' already exists.")

    pilot_frames = select_representative_pilot_frames(sample_count=args.count)
    attached_count = 0
    for p in pilot_frames:
        # Check if already attached to this session
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT id FROM media WHERE session_id = ? AND sha256_hash = ?",
                (session_id, p["sha256"])
            ).fetchone()
            if row:
                continue

        media_id = f"med_pilot_{p['filename'].replace('.', '_')}"
        repo.create_media(
            media_id=media_id,
            session_id=session_id,
            filename=p["filename"],
            file_path=str(p["path"]),
            media_type="image/jpeg",
            sha256_hash=p["sha256"],
            width=p["width"],
            height=p["height"],
            duration_seconds=0.0,
            fps=0.0,
            total_frames=1,
            is_readable=p["readable"]
        )
        attached_count += 1

    print(f"Successfully attached {attached_count} representative real frames to session '{session_id}'.")
    print(f"Inspector '{args.inspector}' can now annotate findings or certify defect-free images via UI or CLI.")


def cmd_readiness(args):
    """Queries and displays ground-truth readiness."""
    report = repo.get_ground_truth_readiness()
    audited_at = report.get("audited_at", datetime.now(timezone.utc).isoformat())
    print(f"\n=======================================================")
    print(f" KeeAInu Ground-Truth Training Readiness Audit")
    print(f" Audited At: {audited_at}")
    print(f"=======================================================")
    print(f" Total Verified Annotations: {report['total_verified_annotations']}")
    print(f" Verified Defect-Free Negatives: {report['total_verified_negatives']}")
    print(f" Training Ready: {'YES' if report['is_training_ready'] else 'NO'}")
    print(f"\n Verified Defect Breakdown:")
    if report["verified_classes_breakdown"]:
        for cls, count in report["verified_classes_breakdown"].items():
            print(f"  - {cls}: {count}")
    else:
        print(f"  (Zero verified annotations recorded)")

    print(f"\n Active Blockers:")
    if report["blockers"]:
        for b in report["blockers"]:
            print(f"  [BLOCKER] {b}")
    else:
        print(f"  (None - dataset meets minimum training threshold)")

    print(f"\n Next Required Action:\n  {report['next_action']}\n")


def cmd_certify_negative(args):
    """Explicitly certifies a media item as defect-free negative sample."""
    res = repo.verify_media_defect_free(
        media_id=args.media_id,
        verified_by=args.inspector,
        notes=args.notes or "Certified defect-free negative ground truth by human inspector."
    )
    print(f"Media '{args.media_id}' certified defect-free by '{args.inspector}'.")
    print(f"Evidence SHA-256: {res.get('evidence_sha256', 'N/A')}")


def cmd_annotate_defect(args):
    """Records a genuine human inspector annotation."""
    bbox = {
        "x_min": args.x_min,
        "y_min": args.y_min,
        "x_max": args.x_max,
        "y_max": args.y_max
    }
    # Validate bbox normalization
    if not (0.0 <= args.x_min < args.x_max <= 1.0 and 0.0 <= args.y_min < args.y_max <= 1.0):
        print(f"Error: Invalid normalized coordinates: {bbox}. All values must be in [0, 1] with min < max.")
        sys.exit(1)

    finding = repo.create_manual_finding(
        media_id=args.media_id,
        defect_class=args.defect_class.upper(),
        bbox=bbox,
        confidence=1.0,
        inspector_name=args.inspector,
        notes=args.notes or "Human inspector verified ground-truth defect."
    )
    print(f"Finding created successfully: {finding['id']}")
    print(f"Defect Class: {finding['defect_class']}")
    print(f"Bounding Box: {finding['bbox']}")
    print(f"Inspector: {args.inspector}")


def cmd_export(args):
    """Exports dataset if eligibility checks pass."""
    exporter = DatasetExporter(repository=repo)
    try:
        manifest = exporter.export_yolo(
            version=args.version,
            include_negatives=args.include_negatives,
            overwrite=args.overwrite
        )
        print(f"\n[SUCCESS] YOLO Dataset exported successfully!")
        print(f" Version: {manifest['dataset_version']}")
        print(f" Total Images: {manifest['total_images']}")
        print(f" Positive Images: {manifest['positive_images']}")
        print(f" Negative Images: {manifest['negative_images']}")
        print(f" Total Annotations: {manifest['total_annotations']}")
        print(f" Output Path: {manifest['output_path']}")
        print(f" Manifest SHA-256: {manifest['manifest_sha256']}")
        print(f" Class Mapping: {manifest['class_mapping']}")
    except EmptyDatasetExportError as e:
        print(f"\n[BLOCKED] Dataset export safely rejected:")
        print(f" {e}")
        print(f"\nHuman inspection is required before exporting a real dataset. Zero synthetic data permitted.")
    except Exception as e:
        print(f"\n[ERROR] Export failed: {e}")


def cmd_validate(args):
    """Validates an exported YOLO dataset directory."""
    path = Path(args.path)
    if not path.is_absolute():
        path = (settings.DATA_DIR / "datasets" / path).resolve()
    try:
        report = validate_yolo_dataset(path)
        print(f"\n[VALID] Dataset passed all integrity and isolation checks!")
        print(f" Dataset Version: {report.get('dataset_version')}")
        print(f" Total Images: {report['total_images']}")
        print(f" Positive Images: {report['positive_images']}")
        print(f" Negative Images: {report['negative_images']}")
        print(f" Total Annotations: {report['total_annotations']}")
        print(f" Splits: {report['splits']}")
        print(f" Classes: {report['classes']}")
    except DatasetValidationError as e:
        print(f"\n[INVALID] Dataset validation failed:\n{e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="KeeAInu Real Footage Annotation Pilot & Dataset CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inventory
    inv_p = subparsers.add_parser("inventory", help="Inspect real source footage and select representative pilot frames")
    inv_p.add_argument("--count", type=int, default=12, help="Number of representative pilot frames to select")
    inv_p.set_defaults(func=cmd_inventory)

    # setup-session
    setup_p = subparsers.add_parser("setup-session", help="Register representative pilot frames into an inspection session")
    setup_p.add_argument("--session-id", type=str, default="sess_pilot_g1_real")
    setup_p.add_argument("--inspector", type=str, default="Lead Inspector")
    setup_p.add_argument("--count", type=int, default=12)
    setup_p.set_defaults(func=cmd_setup_session)

    # readiness
    read_p = subparsers.add_parser("readiness", help="Check current ground-truth readiness and blockers")
    read_p.set_defaults(func=cmd_readiness)

    # certify-negative
    cert_p = subparsers.add_parser("certify-negative", help="Certify a media item as defect-free negative ground truth")
    cert_p.add_argument("--media-id", type=str, required=True)
    cert_p.add_argument("--inspector", type=str, default="Lead Inspector")
    cert_p.add_argument("--notes", type=str, default=None)
    cert_p.set_defaults(func=cmd_certify_negative)

    # annotate
    ann_p = subparsers.add_parser("annotate", help="Record a human verified defect bounding box")
    ann_p.add_argument("--media-id", type=str, required=True)
    ann_p.add_argument("--defect-class", type=str, required=True, help="Defect class (e.g. CRACK, CORROSION, PITTING, CHIPPING, DIRT, RUSTING, THERMAL_CRACKING)")
    ann_p.add_argument("--x-min", type=float, required=True)
    ann_p.add_argument("--y-min", type=float, required=True)
    ann_p.add_argument("--x-max", type=float, required=True)
    ann_p.add_argument("--y-max", type=float, required=True)
    ann_p.add_argument("--inspector", type=str, default="Lead Inspector")
    ann_p.add_argument("--notes", type=str, default=None)
    ann_p.set_defaults(func=cmd_annotate_defect)

    # export
    exp_p = subparsers.add_parser("export", help="Export YOLO dataset from human verified data")
    exp_p.add_argument("--version", type=str, default="v1")
    exp_p.add_argument("--include-negatives", action="store_true", default=True)
    exp_p.add_argument("--overwrite", action="store_true", default=False)
    exp_p.set_defaults(func=cmd_export)

    # validate
    val_p = subparsers.add_parser("validate", help="Validate an exported YOLO dataset directory")
    val_p.add_argument("--path", type=str, required=True, help="Dataset directory name or path")
    val_p.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
