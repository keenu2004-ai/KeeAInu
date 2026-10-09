"""SQLite-backed Inspection Repository for Phase 3 Local MVP."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from backend.app.core.config import settings


VALID_SESSION_TRANSITIONS = {
    "DRAFT": ["IN_REVIEW", "ARCHIVED"],
    "IN_REVIEW": ["COMPLETED", "DRAFT", "ARCHIVED"],
    "COMPLETED": ["ARCHIVED"],
    "ARCHIVED": []
}

VALID_REVIEW_STATUSES = ["PENDING_REVIEW", "CONFIRMED", "ADJUSTED", "REJECTED"]
VALID_SEVERITIES = ["CRITICAL", "MAJOR", "MINOR", "INFORMATIONAL"]


class InspectionRepository:
    """Encapsulates SQLite persistence for sessions, media, findings, and reviews."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or settings.DB_PATH).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                inspector_name TEXT NOT NULL,
                status TEXT NOT NULL,
                asset_tag TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS media (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                media_type TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                fps REAL NOT NULL,
                total_frames INTEGER NOT NULL,
                is_readable INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS thumbnails (
                id TEXT PRIMARY KEY,
                media_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp_ms REAL NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                media_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp_ms REAL NOT NULL,
                defect_class TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                bbox_json TEXT NOT NULL,
                is_simulated INTEGER NOT NULL,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL UNIQUE,
                decision_status TEXT NOT NULL,
                severity TEXT NOT NULL,
                inspector_notes TEXT,
                adjusted_bbox_json TEXT,
                reviewed_by TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                FOREIGN KEY (finding_id) REFERENCES findings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS dataset_assets (
                id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                filename TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                extension TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                sha256_hash TEXT NOT NULL,
                is_readable INTEGER NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                fps REAL NOT NULL,
                total_frames INTEGER NOT NULL,
                is_synthetic INTEGER NOT NULL,
                validation_status TEXT NOT NULL,
                error_details TEXT,
                contact_sheet_path TEXT,
                quality_profile_json TEXT,
                domain_assignment TEXT DEFAULT 'UNKNOWN',
                domain_confidence TEXT DEFAULT 'UNCERTAIN',
                domain_notes TEXT,
                domain_reviewed_by TEXT,
                domain_reviewed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dataset_samples (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp_ms REAL NOT NULL,
                timestamp_provenance TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                width INTEGER NOT NULL,
                height INTEGER NOT NULL,
                sharpness_score REAL NOT NULL,
                brightness_score REAL NOT NULL,
                contrast_score REAL NOT NULL,
                review_status TEXT NOT NULL DEFAULT 'UNREVIEWED',
                suspected_category TEXT,
                reviewer_notes TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES dataset_assets(id) ON DELETE CASCADE
            );
            """)

    # --- Session Operations ---

    def create_session(
        self,
        session_id: str,
        title: str,
        inspector_name: str,
        asset_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, title, inspector_name, status, asset_tag, created_at, updated_at)
                VALUES (?, ?, ?, 'DRAFT', ?, ?, ?)
                """,
                (session_id, title, inspector_name, asset_tag, now, now)
            )
        return self.get_session(session_id) # type: ignore

    def list_sessions(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            session = dict(row)
            # Fetch attached media
            media_cursor = conn.execute(
                "SELECT * FROM media WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,)
            )
            session["media"] = [dict(m) for m in media_cursor.fetchall()]
            return session

    def update_session_status(self, session_id: str, new_status: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Session '{session_id}' not found.")
            
        current_status = session["status"]
        if new_status not in VALID_SESSION_TRANSITIONS.get(current_status, []):
            raise ValueError(
                f"Invalid session status transition from '{current_status}' to '{new_status}'. "
                f"Valid next states: {VALID_SESSION_TRANSITIONS.get(current_status, [])}"
            )
            
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now, session_id)
            )
        return self.get_session(session_id) # type: ignore

    # --- Media Operations ---

    def create_media(
        self,
        media_id: str,
        session_id: str,
        filename: str,
        file_path: str,
        media_type: str,
        sha256_hash: str,
        width: int,
        height: int,
        duration_seconds: float,
        fps: float,
        total_frames: int,
        is_readable: bool
    ) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"Cannot attach media: Session '{session_id}' does not exist.")

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO media (
                    id, session_id, filename, file_path, media_type, sha256_hash,
                    width, height, duration_seconds, fps, total_frames, is_readable, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id, session_id, filename, file_path, media_type, sha256_hash,
                    width, height, duration_seconds, fps, total_frames, 1 if is_readable else 0, now
                )
            )
        return self.get_media(media_id) # type: ignore

    def get_media(self, media_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,))
            row = cursor.fetchone()
            if not row:
                return None
            media = dict(row)
            media["is_readable"] = bool(media["is_readable"])
            return media

    # --- Thumbnails ---

    def add_thumbnail(
        self,
        thumb_id: str,
        media_id: str,
        frame_index: int,
        timestamp_ms: float,
        file_path: str,
        sha256_hash: str
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO thumbnails (id, media_id, frame_index, timestamp_ms, file_path, sha256_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (thumb_id, media_id, frame_index, timestamp_ms, file_path, sha256_hash, now)
            )
        return {
            "id": thumb_id,
            "media_id": media_id,
            "frame_index": frame_index,
            "timestamp_ms": timestamp_ms,
            "file_path": file_path,
            "sha256_hash": sha256_hash,
            "created_at": now
        }

    def list_thumbnails(self, media_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM thumbnails WHERE media_id = ? ORDER BY frame_index ASC",
                (media_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_thumbnail(self, thumb_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM thumbnails WHERE id = ?", (thumb_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Findings & Reviews ---

    def add_finding(
        self,
        finding_id: str,
        session_id: str,
        media_id: str,
        frame_index: int,
        timestamp_ms: float,
        defect_class: str,
        confidence_score: float,
        bbox_dict: Dict[str, Any],
        is_simulated: bool,
        model_name: str,
        model_version: str
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        bbox_json = json.dumps(bbox_dict)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    id, session_id, media_id, frame_index, timestamp_ms, defect_class,
                    confidence_score, bbox_json, is_simulated, model_name, model_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id, session_id, media_id, frame_index, timestamp_ms, defect_class,
                    confidence_score, bbox_json, 1 if is_simulated else 0, model_name, model_version, now
                )
            )
            # Create default pending review
            review_id = f"rev_{finding_id}"
            conn.execute(
                """
                INSERT INTO reviews (
                    id, finding_id, decision_status, severity, inspector_notes,
                    adjusted_bbox_json, reviewed_by, reviewed_at
                ) VALUES (?, ?, 'PENDING_REVIEW', 'INFORMATIONAL', NULL, NULL, 'system', ?)
                """,
                (review_id, finding_id, now)
            )
        return self.get_finding(finding_id) # type: ignore

    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT f.*, r.id as review_id, r.decision_status, r.severity,
                       r.inspector_notes, r.adjusted_bbox_json, r.reviewed_by, r.reviewed_at
                FROM findings f
                LEFT JOIN reviews r ON f.id = r.finding_id
                WHERE f.id = ?
                """,
                (finding_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_simulated"] = bool(res["is_simulated"])
            res["bbox"] = json.loads(res["bbox_json"]) if res.get("bbox_json") else None
            if res.get("adjusted_bbox_json"):
                res["adjusted_bbox"] = json.loads(res["adjusted_bbox_json"])
            else:
                res["adjusted_bbox"] = None
            return res

    def list_findings(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT f.*, r.id as review_id, r.decision_status, r.severity,
                       r.inspector_notes, r.adjusted_bbox_json, r.reviewed_by, r.reviewed_at
                FROM findings f
                LEFT JOIN reviews r ON f.id = r.finding_id
                WHERE f.session_id = ?
                ORDER BY f.frame_index ASC
                """,
                (session_id,)
            )
            findings = []
            for row in cursor.fetchall():
                res = dict(row)
                res["is_simulated"] = bool(res["is_simulated"])
                res["bbox"] = json.loads(res["bbox_json"]) if res.get("bbox_json") else None
                if res.get("adjusted_bbox_json"):
                    res["adjusted_bbox"] = json.loads(res["adjusted_bbox_json"])
                else:
                    res["adjusted_bbox"] = None
                findings.append(res)
            return findings

    def update_review(
        self,
        finding_id: str,
        decision_status: str,
        severity: str,
        reviewed_by: str,
        inspector_notes: Optional[str] = None,
        adjusted_bbox_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if decision_status not in VALID_REVIEW_STATUSES:
            raise ValueError(f"Invalid review decision_status '{decision_status}'. Allowed: {VALID_REVIEW_STATUSES}")
        if severity not in VALID_SEVERITIES:
            raise ValueError(f"Invalid severity '{severity}'. Allowed: {VALID_SEVERITIES}")

        finding = self.get_finding(finding_id)
        if not finding:
            raise KeyError(f"Finding '{finding_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        adj_json = json.dumps(adjusted_bbox_dict) if adjusted_bbox_dict else None

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE reviews
                SET decision_status = ?, severity = ?, inspector_notes = ?,
                    adjusted_bbox_json = ?, reviewed_by = ?, reviewed_at = ?
                WHERE finding_id = ?
                """,
                (decision_status, severity, inspector_notes, adj_json, reviewed_by, now, finding_id)
            )
        return self.get_finding(finding_id) # type: ignore

    # --- Discovery & Dataset Profiling Operations (Phase 4A) ---

    def upsert_asset(
        self,
        asset_id: str,
        source_path: str,
        filename: str,
        asset_type: str,
        extension: str,
        file_size_bytes: int,
        sha256_hash: str,
        is_readable: bool,
        width: int,
        height: int,
        duration_seconds: float,
        fps: float,
        total_frames: int,
        is_synthetic: bool = False,
        validation_status: str = "VALID",
        error_details: Optional[str] = None,
        contact_sheet_path: Optional[str] = None,
        quality_profile_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        q_json = json.dumps(quality_profile_dict) if quality_profile_dict else None
        
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT id FROM dataset_assets WHERE id = ?", (asset_id,))
            existing = cursor.fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE dataset_assets
                    SET source_path = ?, filename = ?, asset_type = ?, extension = ?,
                        file_size_bytes = ?, sha256_hash = ?, is_readable = ?,
                        width = ?, height = ?, duration_seconds = ?, fps = ?,
                        total_frames = ?, is_synthetic = ?, validation_status = ?,
                        error_details = ?, contact_sheet_path = ?, quality_profile_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        source_path, filename, asset_type, extension,
                        file_size_bytes, sha256_hash, int(is_readable),
                        width, height, duration_seconds, fps,
                        total_frames, int(is_synthetic), validation_status,
                        error_details, contact_sheet_path, q_json,
                        now, asset_id
                    )
                )
            else:
                conn.execute(
                    """
                    INSERT INTO dataset_assets (
                        id, source_path, filename, asset_type, extension,
                        file_size_bytes, sha256_hash, is_readable,
                        width, height, duration_seconds, fps,
                        total_frames, is_synthetic, validation_status,
                        error_details, contact_sheet_path, quality_profile_json,
                        domain_assignment, domain_confidence, domain_notes,
                        domain_reviewed_by, domain_reviewed_at,
                        created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        'UNKNOWN', 'UNCERTAIN', NULL,
                        NULL, NULL,
                        ?, ?
                    )
                    """,
                    (
                        asset_id, source_path, filename, asset_type, extension,
                        file_size_bytes, sha256_hash, int(is_readable),
                        width, height, duration_seconds, fps,
                        total_frames, int(is_synthetic), validation_status,
                        error_details, contact_sheet_path, q_json,
                        now, now
                    )
                )
        return self.get_asset(asset_id) # type: ignore

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM dataset_assets WHERE id = ?", (asset_id,))
            row = cursor.fetchone()
            if not row:
                return None
            asset = dict(row)
            asset["is_readable"] = bool(asset["is_readable"])
            asset["is_synthetic"] = bool(asset["is_synthetic"])
            if asset.get("quality_profile_json"):
                asset["quality_profile"] = json.loads(asset["quality_profile_json"])
            else:
                asset["quality_profile"] = None
            asset["samples"] = self.list_samples(asset_id)
            asset["samples_count"] = len(asset["samples"])
            return asset

    def get_asset_by_hash(self, sha256_hash: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM dataset_assets WHERE sha256_hash = ?", (sha256_hash,))
            row = cursor.fetchone()
            if not row:
                return None
            return self.get_asset(row["id"])

    def list_assets(
        self,
        domain: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM dataset_assets WHERE 1=1"
        params: List[Any] = []
        if domain:
            query += " AND domain_assignment = ?"
            params.append(domain)
        if is_synthetic is not None:
            query += " AND is_synthetic = ?"
            params.append(int(is_synthetic))
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            assets = []
            for row in cursor.fetchall():
                asset = dict(row)
                asset["is_readable"] = bool(asset["is_readable"])
                asset["is_synthetic"] = bool(asset["is_synthetic"])
                if asset.get("quality_profile_json"):
                    asset["quality_profile"] = json.loads(asset["quality_profile_json"])
                else:
                    asset["quality_profile"] = None
                asset["samples"] = self.list_samples(asset["id"])
                asset["samples_count"] = len(asset["samples"])
                assets.append(asset)
            return assets

    def update_asset_domain(
        self,
        asset_id: str,
        domain_assignment: str,
        domain_confidence: str,
        domain_notes: Optional[str],
        reviewed_by: str
    ) -> Dict[str, Any]:
        asset = self.get_asset(asset_id)
        if not asset:
            raise KeyError(f"Asset '{asset_id}' not found.")
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE dataset_assets
                SET domain_assignment = ?, domain_confidence = ?, domain_notes = ?,
                    domain_reviewed_by = ?, domain_reviewed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (domain_assignment, domain_confidence, domain_notes, reviewed_by, now, now, asset_id)
            )
        return self.get_asset(asset_id) # type: ignore

    def create_sample(
        self,
        sample_id: str,
        asset_id: str,
        frame_index: int,
        timestamp_ms: float,
        timestamp_provenance: str,
        file_path: str,
        sha256_hash: str,
        width: int,
        height: int,
        sharpness_score: float,
        brightness_score: float,
        contrast_score: float
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO dataset_samples (
                    id, asset_id, frame_index, timestamp_ms, timestamp_provenance,
                    file_path, sha256_hash, width, height,
                    sharpness_score, brightness_score, contrast_score,
                    review_status, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    'UNREVIEWED', ?
                )
                """,
                (
                    sample_id, asset_id, frame_index, timestamp_ms, timestamp_provenance,
                    file_path, sha256_hash, width, height,
                    sharpness_score, brightness_score, contrast_score,
                    now
                )
            )
        return self.get_sample(sample_id) # type: ignore

    def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM dataset_samples WHERE id = ?", (sample_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    def list_samples(self, asset_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM dataset_samples WHERE asset_id = ? ORDER BY frame_index ASC",
                (asset_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_sample_review(
        self,
        sample_id: str,
        review_status: str,
        suspected_category: Optional[str],
        reviewer_notes: Optional[str],
        reviewed_by: str
    ) -> Dict[str, Any]:
        sample = self.get_sample(sample_id)
        if not sample:
            raise KeyError(f"Sample '{sample_id}' not found.")
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE dataset_samples
                SET review_status = ?, suspected_category = ?, reviewer_notes = ?,
                    reviewed_by = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (review_status, suspected_category, reviewer_notes, reviewed_by, now, sample_id)
            )
        return self.get_sample(sample_id) # type: ignore

    def get_discovery_summary(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            total_assets = conn.execute("SELECT COUNT(*) FROM dataset_assets").fetchone()[0]
            real_count = conn.execute("SELECT COUNT(*) FROM dataset_assets WHERE is_synthetic = 0").fetchone()[0]
            synthetic_count = conn.execute("SELECT COUNT(*) FROM dataset_assets WHERE is_synthetic = 1").fetchone()[0]
            readable_count = conn.execute("SELECT COUNT(*) FROM dataset_assets WHERE is_readable = 1").fetchone()[0]
            unreadable_count = conn.execute("SELECT COUNT(*) FROM dataset_assets WHERE is_readable = 0").fetchone()[0]
            samples_count = conn.execute("SELECT COUNT(*) FROM dataset_samples").fetchone()[0]

            # Domain breakdown
            domain_cursor = conn.execute("SELECT domain_assignment, COUNT(*) FROM dataset_assets GROUP BY domain_assignment")
            domain_breakdown = {row[0] or "UNKNOWN": row[1] for row in domain_cursor.fetchall()}

            # Review breakdown
            review_cursor = conn.execute("SELECT review_status, COUNT(*) FROM dataset_samples GROUP BY review_status")
            review_breakdown = {row[0]: row[1] for row in review_cursor.fetchall()}

            # Quality metrics
            sharpness_row = conn.execute("SELECT AVG(sharpness_score) FROM dataset_samples").fetchone()
            avg_sharpness = float(sharpness_row[0]) if sharpness_row and sharpness_row[0] is not None else 0.0

            # Meta completeness
            if total_assets > 0:
                complete_meta = conn.execute(
                    "SELECT COUNT(*) FROM dataset_assets WHERE width > 0 AND height > 0 AND fps >= 0"
                ).fetchone()[0]
                completeness_pct = round((complete_meta / total_assets) * 100.0, 1)
            else:
                completeness_pct = 0.0

            blur_count = conn.execute("SELECT COUNT(*) FROM dataset_samples WHERE sharpness_score < 75.0").fetchone()[0]

            return {
                "total_assets": total_assets,
                "real_assets_count": real_count,
                "synthetic_assets_count": synthetic_count,
                "readable_assets_count": readable_count,
                "unreadable_assets_count": unreadable_count,
                "total_samples_extracted": samples_count,
                "metadata_completeness_percent": completeness_pct,
                "domain_breakdown": domain_breakdown,
                "defect_review_breakdown": review_breakdown,
                "average_sharpness": round(avg_sharpness, 2),
                "blur_flagged_assets_count": blur_count,
                "evaluation_split_recommendation": (
                    "Source-Asset / Inspection Session split required for evaluation. "
                    "Neighboring frames from identical videos must NOT be shuffled between training and test sets."
                ),
                "unresolved_questions": [
                    "What industrial inspection standard or criteria applies to customer footage?",
                    "Are defects present in the unreviewed representative frames?",
                    "What ground-truth provenance verification exists for candidate domain classifications?"
                ],
                "generated_at": datetime.now(timezone.utc).isoformat()
            }


repo = InspectionRepository()

