"""Safe Dataset Exporter for KeeAInu Defect Detection.

Requirements & Guarantees:
1. Export ONLY eligible, human-verified annotations and verified negatives.
2. Never automatically convert simulated model findings into ground truth.
3. Support YOLO detection format (images/, labels/, data.yaml, manifest.json).
4. Preserve original evidence and record SHA-256 digests.
5. Prevent split leakage: partition strictly by physical asset / session group.
6. Prevent duplicate content from crossing dataset splits.
7. Validate coordinates, missing labels, empty classes, and split leakage.
8. Never overwrite source footage or silently overwrite existing dataset versions.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Dict, List, Optional, Any, Set, Tuple
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256, is_path_safe
from backend.app.db.repository import repo as default_repo, InspectionRepository
from backend.app.schemas.annotation import NormalizedBoundingBox
from backend.app.modules.video.extractor import VideoFrameExtractor


class DatasetExportError(Exception):
    """Base exception for dataset export operations."""
    pass


class DatasetOverwriteError(DatasetExportError):
    """Raised when an existing dataset version directory would be overwritten without explicit consent."""
    pass


class EmptyDatasetExportError(DatasetExportError):
    """Raised when no eligible human-verified data exists to export."""
    pass


class SplitLeakageError(DatasetExportError):
    """Raised when items from the same physical asset or identical hashes cross dataset splits."""
    pass


class InvalidAnnotationError(DatasetExportError):
    """Raised when bounding box coordinates violate normalization or spatial invariants."""
    pass


class DatasetValidationError(DatasetExportError):
    """Raised when an exported dataset fails integrity or isolation validation."""
    pass


class ExportItem:
    """An individual image item with its verified annotations ready for partitioning."""

    def __init__(
        self,
        item_id: str,
        group_id: str,
        source_path: Path,
        media_filename: str,
        evidence_sha256: str,
        width: int,
        height: int,
        is_negative: bool = False,
        annotations: Optional[List[Dict[str, Any]]] = None,
        frame_index: int = 0,
        is_video_frame: bool = False,
        verified_by: str = "Inspector",
        verified_at: Optional[str] = None
    ):
        self.item_id = item_id
        self.group_id = group_id
        self.source_path = source_path
        self.media_filename = media_filename
        self.evidence_sha256 = evidence_sha256
        self.width = width
        self.height = height
        self.is_negative = is_negative
        self.annotations = annotations or []
        self.frame_index = frame_index
        self.is_video_frame = is_video_frame
        self.verified_by = verified_by
        self.verified_at = verified_at or datetime.now(timezone.utc).isoformat()


class DatasetExporter:
    """Safely extracts, validates, partitions, and exports human-verified datasets."""

    def __init__(self, repository: Optional[InspectionRepository] = None):
        self.repo = repository or default_repo

    def collect_verified_items(
        self,
        include_negatives: bool = True,
        include_synthetic: bool = False,
        include_simulated: bool = False
    ) -> List[ExportItem]:
        """
        Gathers only human-verified annotations and explicitly verified defect-free negatives.
        Strictly excludes unadjusted simulated baseline findings and unverified empty images.
        """
        items_by_media_frame: Dict[Tuple[str, int], ExportItem] = {}

        # 1. Operational Inspection Reviews (CONFIRMED or ADJUSTED)
        with self.repo._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    f.id as finding_id,
                    f.session_id,
                    s.asset_tag,
                    f.media_id,
                    m.file_path as media_file_path,
                    m.media_type,
                    m.sha256_hash as media_sha256,
                    m.width,
                    m.height,
                    m.filename as media_filename,
                    f.frame_index,
                    f.timestamp_ms,
                    f.defect_class,
                    f.bbox_json,
                    f.polygon_mask_json,
                    f.is_simulated,
                    r.decision_status,
                    r.adjusted_bbox_json,
                    r.reviewed_by,
                    r.reviewed_at
                FROM reviews r
                JOIN findings f ON r.finding_id = f.id
                JOIN media m ON f.media_id = m.id
                JOIN sessions s ON f.session_id = s.id
                WHERE r.decision_status IN ('CONFIRMED', 'ADJUSTED')
                """
            )
            for row in cursor.fetchall():
                r = dict(row)
                # Never treat unadjusted simulated model findings as genuine human ground truth
                if r["is_simulated"] and not include_simulated:
                    if r["decision_status"] != "ADJUSTED" or not r.get("adjusted_bbox_json"):
                        continue

                media_path = Path(r["media_file_path"]).resolve()
                if not media_path.exists():
                    continue

                # Use adjusted bounding box if provided, otherwise confirmed initial box
                raw_bbox = json.loads(r["adjusted_bbox_json"]) if r.get("adjusted_bbox_json") else json.loads(r["bbox_json"])
                try:
                    norm_bbox = NormalizedBoundingBox(**raw_bbox)
                except Exception as e:
                    raise InvalidAnnotationError(
                        f"Finding '{r['finding_id']}' has invalid bounding box coordinates: {e}"
                    )

                group_id = (r.get("asset_tag") or "").strip() or r["session_id"]
                key = (r["media_id"], r["frame_index"])

                if key not in items_by_media_frame:
                    is_video = r["media_type"].startswith("video/")
                    items_by_media_frame[key] = ExportItem(
                        item_id=f"{r['media_id']}_f{r['frame_index']}",
                        group_id=group_id,
                        source_path=media_path,
                        media_filename=r["media_filename"],
                        evidence_sha256=r["media_sha256"],
                        width=r["width"],
                        height=r["height"],
                        is_negative=False,
                        annotations=[],
                        frame_index=r["frame_index"],
                        is_video_frame=is_video,
                        verified_by=r["reviewed_by"],
                        verified_at=r["reviewed_at"]
                    )

                items_by_media_frame[key].annotations.append({
                    "defect_class": r["defect_class"].strip().upper(),
                    "bbox": norm_bbox.model_dump(),
                    "polygon_mask": json.loads(r["polygon_mask_json"]) if r.get("polygon_mask_json") else None
                })

            # 2. Candidate Findings with review_state = 'CONFIRMED_DEFECT'
            c_cursor = conn.execute(
                """
                SELECT
                    cf.id as finding_id,
                    cf.asset_id,
                    cf.frame_index,
                    cf.candidate_defect,
                    cf.candidate_bbox_json,
                    cf.reviewed_by,
                    cf.reviewed_at,
                    ast.source_path,
                    ast.filename,
                    ast.sha256_hash,
                    ast.width,
                    ast.height,
                    ast.is_synthetic
                FROM candidate_findings cf
                JOIN dataset_assets ast ON cf.asset_id = ast.id
                WHERE cf.review_state = 'CONFIRMED_DEFECT'
                """
            )
            for row in c_cursor.fetchall():
                c = dict(row)
                if c["is_synthetic"] and not include_synthetic:
                    continue

                source_path = Path(c["source_path"]).resolve()
                if not source_path.exists():
                    continue

                if not c.get("candidate_bbox_json"):
                    continue

                raw_bbox = json.loads(c["candidate_bbox_json"])
                try:
                    norm_bbox = NormalizedBoundingBox(**raw_bbox)
                except Exception as e:
                    raise InvalidAnnotationError(
                        f"Candidate finding '{c['finding_id']}' has invalid bounding box: {e}"
                    )

                key = (c["asset_id"], c["frame_index"])
                if key not in items_by_media_frame:
                    items_by_media_frame[key] = ExportItem(
                        item_id=f"{c['asset_id']}_f{c['frame_index']}",
                        group_id=c["asset_id"],
                        source_path=source_path,
                        media_filename=c["filename"],
                        evidence_sha256=c["sha256_hash"],
                        width=c["width"],
                        height=c["height"],
                        is_negative=False,
                        annotations=[],
                        frame_index=c["frame_index"],
                        is_video_frame=False,
                        verified_by=c["reviewed_by"] or "Inspector",
                        verified_at=c["reviewed_at"]
                    )

                items_by_media_frame[key].annotations.append({
                    "defect_class": c["candidate_defect"].strip().upper(),
                    "bbox": norm_bbox.model_dump(),
                    "polygon_mask": None
                })

            # 3. Decoupled Annotations with HUMAN_EXPERT
            d_cursor = conn.execute(
                """
                SELECT
                    da.id as annotation_id,
                    da.asset_id,
                    da.frame_index,
                    da.defect_category,
                    da.bbox_json,
                    da.annotator_id,
                    da.created_at,
                    ast.source_path,
                    ast.filename,
                    ast.sha256_hash,
                    ast.width,
                    ast.height,
                    ast.is_synthetic
                FROM decoupled_annotations da
                JOIN dataset_assets ast ON da.asset_id = ast.id
                WHERE da.annotator_type IN ('HUMAN_EXPERT', 'EXPERT_AUDITED')
                """
            )
            for row in d_cursor.fetchall():
                d = dict(row)
                if d["is_synthetic"] and not include_synthetic:
                    continue

                source_path = Path(d["source_path"]).resolve()
                if not source_path.exists() or not d.get("bbox_json"):
                    continue

                raw_bbox = json.loads(d["bbox_json"])
                try:
                    norm_bbox = NormalizedBoundingBox(**raw_bbox)
                except Exception as e:
                    raise InvalidAnnotationError(
                        f"Decoupled annotation '{d['annotation_id']}' has invalid bounding box: {e}"
                    )

                key = (d["asset_id"], d["frame_index"])
                if key not in items_by_media_frame:
                    items_by_media_frame[key] = ExportItem(
                        item_id=f"{d['asset_id']}_f{d['frame_index']}",
                        group_id=d["asset_id"],
                        source_path=source_path,
                        media_filename=d["filename"],
                        evidence_sha256=d["sha256_hash"],
                        width=d["width"],
                        height=d["height"],
                        is_negative=False,
                        annotations=[],
                        frame_index=d["frame_index"],
                        is_video_frame=False,
                        verified_by=d["annotator_id"] or "Inspector",
                        verified_at=d["created_at"]
                    )

                items_by_media_frame[key].annotations.append({
                    "defect_class": d["defect_category"].strip().upper(),
                    "bbox": norm_bbox.model_dump(),
                    "polygon_mask": None
                })

            # 4. Verified Defect-Free Negatives (Explicitly confirmed!)
            if include_negatives:
                # 4a. Inspection Media explicitly marked as DEFECT_FREE
                try:
                    neg_media_cursor = conn.execute(
                        """
                        SELECT
                            m.id as media_id,
                            m.session_id,
                            s.asset_tag,
                            m.file_path,
                            m.filename,
                            m.sha256_hash,
                            m.width,
                            m.height,
                            m.verified_by,
                            m.verified_at
                        FROM media m
                        JOIN sessions s ON m.session_id = s.id
                        WHERE m.review_status = 'DEFECT_FREE'
                        """
                    )
                    for row in neg_media_cursor.fetchall():
                        m = dict(row)
                        media_path = Path(m["file_path"]).resolve()
                        if not media_path.exists():
                            continue
                        key = (m["media_id"], 0)
                        if key not in items_by_media_frame:
                            group_id = (m.get("asset_tag") or "").strip() or m["session_id"]
                            items_by_media_frame[key] = ExportItem(
                                item_id=f"{m['media_id']}_negative",
                                group_id=group_id,
                                source_path=media_path,
                                media_filename=m["filename"],
                                evidence_sha256=m["sha256_hash"],
                                width=m["width"],
                                height=m["height"],
                                is_negative=True,
                                annotations=[],
                                frame_index=0,
                                is_video_frame=False,
                                verified_by=m.get("verified_by") or "Inspector",
                                verified_at=m.get("verified_at")
                            )
                except Exception:
                    pass

                # 4b. Discovery Samples explicitly triaged as NO_VISIBLE_DEFECT
                s_cursor = conn.execute(
                    """
                    SELECT
                        ds.id as sample_id,
                        ds.asset_id,
                        ds.frame_index,
                        ds.file_path,
                        ds.sha256_hash,
                        ds.width,
                        ds.height,
                        ds.reviewed_by,
                        ds.reviewed_at,
                        ast.filename,
                        ast.is_synthetic
                    FROM dataset_samples ds
                    JOIN dataset_assets ast ON ds.asset_id = ast.id
                    WHERE ds.review_status = 'NO_VISIBLE_DEFECT'
                    """
                )
                for row in s_cursor.fetchall():
                    s = dict(row)
                    if s["is_synthetic"] and not include_synthetic:
                        continue
                    sample_path = Path(s["file_path"]).resolve()
                    if not sample_path.exists():
                        continue
                    key = (s["asset_id"], s["frame_index"])
                    if key not in items_by_media_frame:
                        items_by_media_frame[key] = ExportItem(
                            item_id=f"{s['asset_id']}_s{s['frame_index']}_negative",
                            group_id=s["asset_id"],
                            source_path=sample_path,
                            media_filename=s["filename"],
                            evidence_sha256=s["sha256_hash"],
                            width=s["width"],
                            height=s["height"],
                            is_negative=True,
                            annotations=[],
                            frame_index=s["frame_index"],
                            is_video_frame=False,
                            verified_by=s.get("reviewed_by") or "Inspector",
                            verified_at=s.get("reviewed_at")
                        )

        return list(items_by_media_frame.values())

    def partition_items(
        self,
        items: List[ExportItem],
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        random_seed: int = 42
    ) -> Dict[str, List[ExportItem]]:
        """
        Partitions items into train, val, and test splits strictly by group_id (asset/session)
        and prevents duplicate evidence SHA-256 hashes from crossing splits.
        """
        if not items:
            return {"train": [], "val": [], "test": []}

        # 1. Cluster groups sharing duplicate content (SHA-256)
        # Disjoint Set / Union-Find over groups
        hash_to_first_group: Dict[str, str] = {}
        group_parent: Dict[str, str] = {}

        def find(g: str) -> str:
            if group_parent.setdefault(g, g) != g:
                group_parent[g] = find(group_parent[g])
            return group_parent[g]

        def union(g1: str, g2: str):
            p1 = find(g1)
            p2 = find(g2)
            if p1 != p2:
                group_parent[p2] = p1

        for it in items:
            g = it.group_id
            find(g)
            if it.evidence_sha256 in hash_to_first_group:
                union(g, hash_to_first_group[it.evidence_sha256])
            else:
                hash_to_first_group[it.evidence_sha256] = g

        # Group items by their root cluster
        cluster_items: Dict[str, List[ExportItem]] = {}
        for it in items:
            root = find(it.group_id)
            cluster_items.setdefault(root, []).append(it)

        clusters = sorted(list(cluster_items.keys()))
        rng = np.random.default_rng(random_seed)
        shuffled = list(clusters)
        rng.shuffle(shuffled)

        n = len(shuffled)
        if n == 1:
            # Single group: place in train
            return {
                "train": cluster_items[shuffled[0]],
                "val": [],
                "test": []
            }

        n_train = max(1, int(round(n * train_ratio)))
        n_val = max(1 if n > 1 and val_ratio > 0 else 0, int(round(n * val_ratio)))
        if n_train + n_val > n:
            n_train = max(1, n - n_val)

        train_clusters = set(shuffled[:n_train])
        val_clusters = set(shuffled[n_train:n_train + n_val])
        test_clusters = set(shuffled[n_train + n_val:])

        splits: Dict[str, List[ExportItem]] = {"train": [], "val": [], "test": []}
        for c in train_clusters:
            splits["train"].extend(cluster_items[c])
        for c in val_clusters:
            splits["val"].extend(cluster_items[c])
        for c in test_clusters:
            splits["test"].extend(cluster_items[c])

        # 2. Strict leakage assertion
        train_groups = {it.group_id for it in splits["train"]}
        val_groups = {it.group_id for it in splits["val"]}
        test_groups = {it.group_id for it in splits["test"]}

        train_hashes = {it.evidence_sha256 for it in splits["train"]}
        val_hashes = {it.evidence_sha256 for it in splits["val"]}
        test_hashes = {it.evidence_sha256 for it in splits["test"]}

        if train_groups & val_groups:
            raise SplitLeakageError(f"Group leakage between train and val: {train_groups & val_groups}")
        if train_groups & test_groups:
            raise SplitLeakageError(f"Group leakage between train and test: {train_groups & test_groups}")
        if val_groups & test_groups:
            raise SplitLeakageError(f"Group leakage between val and test: {val_groups & test_groups}")

        if train_hashes & val_hashes:
            raise SplitLeakageError(f"SHA-256 duplicate content leakage between train and val")
        if train_hashes & test_hashes:
            raise SplitLeakageError(f"SHA-256 duplicate content leakage between train and test")
        if val_hashes & test_hashes:
            raise SplitLeakageError(f"SHA-256 duplicate content leakage between val and test")

        return splits

    def export_yolo(
        self,
        version: str = "v1",
        output_dir: Optional[Path] = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        random_seed: int = 42,
        include_negatives: bool = True,
        include_synthetic: bool = False,
        include_simulated: bool = False,
        overwrite: bool = False,
        target_classes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes complete YOLO dataset export pipeline with safety validation.
        """
        datasets_root = (settings.DATA_DIR / "datasets").resolve()
        if output_dir:
            out_p = Path(output_dir)
            if not out_p.is_absolute():
                export_root = (datasets_root / out_p).resolve()
            else:
                export_root = out_p.resolve()
        else:
            export_root = (datasets_root / f"keeainu_yolo_{version}").resolve()

        # Keep exports and overwrite deletion inside the approved dataset vault.
        # resolve() also detects existing symlinks that point outside the vault.
        if export_root == datasets_root or not export_root.is_relative_to(datasets_root):
            raise DatasetExportError(
                f"Export destination must be a child of the approved dataset directory '{datasets_root}'."
            )

        items = self.collect_verified_items(
            include_negatives=include_negatives,
            include_synthetic=include_synthetic,
            include_simulated=include_simulated
        )

        if not items:
            raise EmptyDatasetExportError(
                "No eligible human-verified annotations or verified defect-free negatives found for export."
            )

        for protected in [settings.RAW_MEDIA_DIR, settings.SOURCE_FOOTAGE_DIR, settings.DB_PATH.parent]:
            if export_root == protected or is_path_safe(export_root, protected):
                raise DatasetExportError(f"Target directory '{export_root}' conflicts with protected data vault.")

        if export_root.exists() and any(export_root.iterdir()):
            if not overwrite:
                raise DatasetOverwriteError(
                    f"Dataset version directory '{export_root}' already exists and contains files. "
                    f"Set overwrite=True to re-export."
                )
            else:
                shutil.rmtree(export_root)

        # Collect stable class mappings
        all_classes: Set[str] = set()
        for it in items:
            for annot in it.annotations:
                all_classes.add(annot["defect_class"])

        if not all_classes and not any(it.is_negative for it in items):
            raise EmptyDatasetExportError("Zero defect annotations and zero negatives found.")

        if target_classes:
            class_to_id = {cls_name: i for i, cls_name in enumerate(target_classes)}
            for cls_name in all_classes:
                if cls_name not in class_to_id:
                    raise InvalidAnnotationError(
                        f"Annotated class '{cls_name}' is not in declared target_classes: {target_classes}"
                    )
        else:
            class_to_id = {cls_name: i for i, cls_name in enumerate(sorted(list(all_classes)))}
        id_to_class = {i: cls_name for cls_name, i in class_to_id.items()}

        splits = self.partition_items(
            items=items,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            random_seed=random_seed
        )

        # Create directory layout
        export_root.mkdir(parents=True, exist_ok=True)
        for split_name in ["train", "val", "test"]:
            (export_root / "images" / split_name).mkdir(parents=True, exist_ok=True)
            (export_root / "labels" / split_name).mkdir(parents=True, exist_ok=True)

        exported_manifest_items = []
        class_counts: Dict[str, int] = {c: 0 for c in class_to_id}
        split_summary: Dict[str, Dict[str, Any]] = {}

        for split_name, split_items in splits.items():
            split_pos = 0
            split_neg = 0
            split_annots = 0

            for it in split_items:
                target_filename = f"{it.item_id}.jpg"
                img_dest = export_root / "images" / split_name / target_filename
                lbl_dest = export_root / "labels" / split_name / f"{it.item_id}.txt"

                # Extract or copy image
                if it.is_video_frame:
                    with VideoFrameExtractor(it.source_path) as extractor:
                        frame_bgr, _ = extractor.extract_frame(it.frame_index)
                        cv2.imwrite(str(img_dest), frame_bgr)
                else:
                    shutil.copy2(it.source_path, img_dest)

                image_sha256 = calculate_sha256(img_dest.read_bytes())

                # Write YOLO label file
                lines = []
                if it.is_negative:
                    split_neg += 1
                else:
                    split_pos += 1
                    for ann in it.annotations:
                        cls_name = ann["defect_class"]
                        cls_id = class_to_id[cls_name]
                        bbox = ann["bbox"]
                        # Convert normalized bbox [x_min, y_min, x_max, y_max] to YOLO [x_center, y_center, w, h]
                        xc = (bbox["x_min"] + bbox["x_max"]) / 2.0
                        yc = (bbox["y_min"] + bbox["y_max"]) / 2.0
                        w = bbox["x_max"] - bbox["x_min"]
                        h = bbox["y_max"] - bbox["y_min"]

                        lines.append(f"{cls_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
                        class_counts[cls_name] += 1
                        split_annots += 1

                lbl_dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

                exported_manifest_items.append({
                    "item_id": it.item_id,
                    "group_id": it.group_id,
                    "split": split_name,
                    "image_path": f"images/{split_name}/{target_filename}",
                    "label_path": f"labels/{split_name}/{it.item_id}.txt",
                    "evidence_sha256": image_sha256,
                    "is_negative": it.is_negative,
                    "annotation_count": len(it.annotations),
                    "verified_by": it.verified_by,
                    "verified_at": it.verified_at
                })

            split_summary[split_name] = {
                "images_count": len(split_items),
                "positive_images": split_pos,
                "negative_images": split_neg,
                "annotations_count": split_annots
            }

        # Write data.yaml
        yaml_lines = [
            f"path: {export_root.as_posix()}",
            "train: images/train",
            "val: images/val",
        ]
        if split_summary.get("test", {}).get("images_count", 0) > 0:
            yaml_lines.append("test: images/test")
        yaml_lines.append(f"nc: {len(class_to_id)}")
        yaml_lines.append("names:")
        for idx, name in id_to_class.items():
            yaml_lines.append(f"  {idx}: {name}")

        (export_root / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

        # Compute deterministic manifest hash
        manifest_payload = {
            "schema_version": "1.0.0",
            "dataset_version": version,
            "export_format": "YOLO",
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "output_path": export_root.as_posix(),
            "class_mapping": class_to_id,
            "total_images": len(items),
            "total_annotations": sum(len(it.annotations) for it in items),
            "positive_images": sum(1 for it in items if not it.is_negative),
            "negative_images": sum(1 for it in items if it.is_negative),
            "class_distribution": class_counts,
            "split_summary": split_summary,
            "split_leakage_detected": False,
            "items": exported_manifest_items
        }

        manifest_bytes = json.dumps(manifest_payload, sort_keys=True).encode("utf-8")
        manifest_sha256 = f"sha256:{hashlib.sha256(manifest_bytes).hexdigest()}"
        manifest_payload["manifest_sha256"] = manifest_sha256

        (export_root / "manifest.json").write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

        return manifest_payload

    def validate_dataset(self, dataset_dir: Path) -> Dict[str, Any]:
        """Convenience instance method for dataset validation."""
        return validate_yolo_dataset(dataset_dir)


def validate_yolo_dataset(dataset_dir: Path) -> Dict[str, Any]:
    """
    Validates a YOLO dataset export directory against all integrity invariants:
    1. Structure: data.yaml, manifest.json, images/ and labels/ directories.
    2. data.yaml: parse yaml, check path/splits, check nc matches number of classes.
    3. manifest.json: check schema, manifest SHA-256 integrity, split leakage status.
    4. Image/Label integrity:
       - Every image has a matching .txt label file.
       - Image file is readable and non-corrupt.
       - Every label entry has valid class_id and normalized coordinates in [0, 1].
       - Empty label file is verified as negative image.
    5. Split isolation:
       - Group IDs across splits are strictly disjoint.
       - Evidence SHA-256 hashes across splits are strictly disjoint (no duplicate leakage).
    """
    dataset_dir = Path(dataset_dir).resolve()
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise DatasetValidationError(f"Dataset directory '{dataset_dir}' does not exist.")

    yaml_path = dataset_dir / "data.yaml"
    manifest_path = dataset_dir / "manifest.json"

    errors: List[str] = []

    if not yaml_path.exists():
        errors.append("Missing data.yaml file.")
    if not manifest_path.exists():
        errors.append("Missing manifest.json file.")

    if errors:
        raise DatasetValidationError(f"Dataset structure invalid: {'; '.join(errors)}")

    # Parse data.yaml
    yaml_text = yaml_path.read_text(encoding="utf-8")
    nc = None
    names_dict: Dict[int, str] = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if line.startswith("nc:"):
            try:
                nc = int(line.split(":", 1)[1].strip())
            except ValueError:
                errors.append(f"Invalid nc in data.yaml: {line}")
        elif line.startswith("names:"):
            pass
        elif ":" in line and line.split(":", 1)[0].strip().isdigit():
            k, v = line.split(":", 1)
            names_dict[int(k.strip())] = v.strip()

    if nc is not None and len(names_dict) != nc:
        errors.append(f"Declared nc ({nc}) does not match number of names ({len(names_dict)}).")

    # Parse manifest.json
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DatasetValidationError(f"Failed to parse manifest.json: {e}")

    # Verify manifest hash if present
    recorded_hash = manifest_data.get("manifest_sha256")
    if recorded_hash:
        manifest_copy = dict(manifest_data)
        manifest_copy.pop("manifest_sha256", None)
        computed_hash = f"sha256:{hashlib.sha256(json.dumps(manifest_copy, sort_keys=True).encode('utf-8')).hexdigest()}"
        if recorded_hash != computed_hash:
            errors.append(f"Manifest SHA-256 tamper detected: expected {computed_hash}, got {recorded_hash}")

    # Inspect images and labels
    total_images = 0
    total_annotations = 0
    positive_images = 0
    negative_images = 0
    split_group_ids: Dict[str, Set[str]] = {}
    split_hashes: Dict[str, Set[str]] = {}

    splits_found = set()
    images_dir = dataset_dir / "images"
    if images_dir.exists():
        for split_dir in images_dir.iterdir():
            if split_dir.is_dir():
                splits_found.add(split_dir.name)

    for split in sorted(list(splits_found)):
        img_split_dir = dataset_dir / "images" / split
        lbl_split_dir = dataset_dir / "labels" / split
        if not lbl_split_dir.exists():
            errors.append(f"Missing labels directory for split: {split}")
            continue

        split_group_ids[split] = set()
        split_hashes[split] = set()

        img_files = list(img_split_dir.glob("*.jpg")) + list(img_split_dir.glob("*.png"))
        for img_p in img_files:
            total_images += 1
            lbl_p = lbl_split_dir / f"{img_p.stem}.txt"
            if not lbl_p.exists():
                errors.append(f"Missing label file for image {img_p.name}")
                continue

            img = cv2.imread(str(img_p))
            if img is None:
                errors.append(f"Corrupt or unreadable image file: {img_p.name}")
                continue

            lbl_content = lbl_p.read_text(encoding="utf-8").strip()
            if not lbl_content:
                negative_images += 1
            else:
                positive_images += 1
                for line_idx, line in enumerate(lbl_content.splitlines(), start=1):
                    parts = line.strip().split()
                    if len(parts) != 5:
                        errors.append(f"Invalid label format in {lbl_p.name}:{line_idx}: expected 5 parts, got {len(parts)}")
                        continue
                    try:
                        cls_id = int(parts[0])
                        xc = float(parts[1])
                        yc = float(parts[2])
                        w = float(parts[3])
                        h = float(parts[4])
                    except ValueError as e:
                        errors.append(f"Invalid numeric values in {lbl_p.name}:{line_idx}: {e}")
                        continue

                    if nc is not None and not (0 <= cls_id < nc):
                        errors.append(f"Class ID {cls_id} out of bounds [0, {nc}) in {lbl_p.name}:{line_idx}")

                    if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                        errors.append(f"Coordinates out of [0, 1] bounds in {lbl_p.name}:{line_idx}: xc={xc}, yc={yc}, w={w}, h={h}")

                    if xc - w / 2 < -1e-4 or xc + w / 2 > 1.0 + 1e-4 or yc - h / 2 < -1e-4 or yc + h / 2 > 1.0 + 1e-4:
                        errors.append(f"Bounding box extends beyond image bounds in {lbl_p.name}:{line_idx}")

                    total_annotations += 1

    # Check split leakage from manifest items
    manifest_items = manifest_data.get("items", [])
    for it in manifest_items:
        s = it.get("split")
        g = it.get("group_id")
        h = it.get("evidence_sha256")
        if s and g:
            split_group_ids.setdefault(s, set()).add(g)
        if s and h:
            split_hashes.setdefault(s, set()).add(h)

    splits_list = list(split_group_ids.keys())
    for i in range(len(splits_list)):
        for j in range(i + 1, len(splits_list)):
            s1, s2 = splits_list[i], splits_list[j]
            overlap_g = split_group_ids[s1] & split_group_ids[s2]
            if overlap_g:
                errors.append(f"Physical asset group leakage between {s1} and {s2}: {overlap_g}")
            overlap_h = split_hashes[s1] & split_hashes[s2]
            if overlap_h:
                errors.append(f"SHA-256 duplicate content leakage between {s1} and {s2}: {overlap_h}")

    if errors:
        raise DatasetValidationError(f"Dataset validation failed with {len(errors)} error(s): " + "; ".join(errors[:10]))

    return {
        "valid": True,
        "dataset_version": manifest_data.get("dataset_version"),
        "total_images": total_images,
        "positive_images": positive_images,
        "negative_images": negative_images,
        "total_annotations": total_annotations,
        "splits": list(splits_found),
        "classes": names_dict,
        "manifest_sha256": manifest_data.get("manifest_sha256"),
        "errors": []
    }
