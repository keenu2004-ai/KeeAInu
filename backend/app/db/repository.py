"""SQLite-backed Inspection Repository for Phase 3 Local MVP."""

import json
import sqlite3
import uuid
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

            CREATE TABLE IF NOT EXISTS dataset_sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                base_url TEXT,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                auth_configured INTEGER NOT NULL DEFAULT 0,
                rate_limit_per_min INTEGER NOT NULL DEFAULT 60,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS dataset_candidates (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                title TEXT NOT NULL,
                publisher TEXT NOT NULL,
                external_id TEXT,
                canonical_url TEXT NOT NULL,
                landing_page_url TEXT,
                domain_tag TEXT NOT NULL,
                is_direct_videoscope INTEGER NOT NULL DEFAULT 0,
                modalities_json TEXT NOT NULL,
                approximate_size_bytes INTEGER,
                file_count INTEGER,
                annotation_types_json TEXT NOT NULL,
                license_identifier TEXT NOT NULL,
                license_url TEXT,
                license_status TEXT NOT NULL,
                commercial_use_allowed INTEGER NOT NULL DEFAULT 0,
                attribution_required INTEGER NOT NULL DEFAULT 1,
                relevance_score REAL NOT NULL,
                relevance_breakdown_json TEXT,
                description TEXT,
                limitations_notes TEXT,
                acquisition_status TEXT NOT NULL DEFAULT 'DISCOVERED',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS source_license_reviews (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                reviewed_by TEXT NOT NULL,
                decision_status TEXT NOT NULL,
                commercial_rights_status TEXT NOT NULL,
                license_notes TEXT,
                terms_url TEXT,
                reviewed_at TEXT NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES dataset_candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS acquisition_jobs (
                id TEXT PRIMARY KEY,
                candidate_id TEXT,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                target_directory TEXT NOT NULL,
                bytes_downloaded INTEGER NOT NULL DEFAULT 0,
                files_acquired INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS acquisition_events (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                candidate_id TEXT,
                event_type TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS asset_provenance_links (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                candidate_id TEXT,
                parent_asset_id TEXT,
                provenance_type TEXT NOT NULL,
                generator_info_json TEXT,
                generation_params_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (asset_id) REFERENCES dataset_assets(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS decoupled_annotations (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                sample_id TEXT,
                frame_index INTEGER NOT NULL DEFAULT 0,
                equipment_family TEXT NOT NULL,
                component_type TEXT NOT NULL,
                defect_category TEXT NOT NULL,
                observed_visual_condition TEXT,
                bbox_json TEXT,
                segmentation_mask_path TEXT,
                source_raw_label TEXT,
                mapping_confidence TEXT NOT NULL DEFAULT 'EXACT_MATCH',
                annotator_type TEXT NOT NULL DEFAULT 'HUMAN_EXPERT',
                annotator_id TEXT NOT NULL,
                taxonomy_version TEXT NOT NULL DEFAULT '2.0.0',
                is_synthetic INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidate_findings (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                sample_id TEXT,
                frame_index INTEGER NOT NULL DEFAULT 0,
                timestamp_ms REAL NOT NULL DEFAULT 0.0,
                timestamp_provenance TEXT NOT NULL DEFAULT 'NOMINAL_APPROXIMATE',
                equipment_family TEXT NOT NULL,
                component_type TEXT NOT NULL,
                candidate_defect TEXT NOT NULL,
                candidate_bbox_json TEXT,
                model_prediction_confidence REAL,
                is_simulated INTEGER NOT NULL DEFAULT 1,
                review_state TEXT NOT NULL DEFAULT 'UNREVIEWED',
                severity TEXT NOT NULL DEFAULT 'UNSPECIFIED',
                reviewed_by TEXT,
                reviewer_rationale TEXT,
                engineering_diagnosis TEXT,
                advisory_recommendation TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS finding_decision_history (
                id TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL,
                previous_state TEXT NOT NULL,
                new_state TEXT NOT NULL,
                severity TEXT NOT NULL,
                reviewed_by TEXT NOT NULL,
                reviewer_rationale TEXT NOT NULL,
                adjusted_defect TEXT,
                adjusted_bbox_json TEXT,
                engineering_diagnosis TEXT,
                advisory_recommendation TEXT,
                transitioned_at TEXT NOT NULL,
                FOREIGN KEY (finding_id) REFERENCES candidate_findings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS evaluation_runs (
                id TEXT PRIMARY KEY,
                run_name TEXT NOT NULL,
                dataset_manifest_hash TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inference_records (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                media_id TEXT NOT NULL,
                frame_index INTEGER NOT NULL,
                timestamp_ms REAL NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                engine_name TEXT NOT NULL,
                model_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                prompt_config_json TEXT,
                is_simulated INTEGER NOT NULL,
                processing_duration_ms REAL NOT NULL,
                cache_hit INTEGER NOT NULL DEFAULT 0,
                raw_response_json TEXT,
                normalized_result_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE
            );
            """)

            # Safe schema migration for findings table extensions
            try:
                conn.execute("ALTER TABLE findings ADD COLUMN polygon_mask_json TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE findings ADD COLUMN evidence_sha256 TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE findings ADD COLUMN inference_record_id TEXT")
            except sqlite3.OperationalError:
                pass

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
        model_version: str,
        polygon_mask: Optional[List[List[float]]] = None,
        evidence_sha256: Optional[str] = None,
        inference_record_id: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        bbox_json = json.dumps(bbox_dict)
        poly_json = json.dumps(polygon_mask) if polygon_mask is not None else None
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO findings (
                    id, session_id, media_id, frame_index, timestamp_ms, defect_class,
                    confidence_score, bbox_json, is_simulated, model_name, model_version,
                    polygon_mask_json, evidence_sha256, inference_record_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id, session_id, media_id, frame_index, timestamp_ms, defect_class,
                    confidence_score, bbox_json, 1 if is_simulated else 0, model_name, model_version,
                    poly_json, evidence_sha256, inference_record_id, now
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
            res["polygon_mask"] = json.loads(res["polygon_mask_json"]) if res.get("polygon_mask_json") else None
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
                res["polygon_mask"] = json.loads(res["polygon_mask_json"]) if res.get("polygon_mask_json") else None
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
        limit: int = 500
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

    def delete_samples_for_asset(self, asset_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM dataset_samples WHERE asset_id = ?", (asset_id,))

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

    # --- Multi-Source Discovery & Controlled Acquisition Operations ---

    def save_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for upsert_candidate."""
        return self.upsert_candidate(candidate_data)

    def upsert_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a discovered candidate dataset record."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO dataset_candidates (
                    id, source_id, provider_name, title, publisher, external_id,
                    canonical_url, landing_page_url, domain_tag, is_direct_videoscope,
                    modalities_json, approximate_size_bytes, file_count, annotation_types_json,
                    license_identifier, license_url, license_status, commercial_use_allowed,
                    attribution_required, relevance_score, relevance_breakdown_json,
                    description, limitations_notes, acquisition_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    publisher=excluded.publisher,
                    canonical_url=excluded.canonical_url,
                    landing_page_url=excluded.landing_page_url,
                    domain_tag=excluded.domain_tag,
                    is_direct_videoscope=excluded.is_direct_videoscope,
                    modalities_json=excluded.modalities_json,
                    approximate_size_bytes=excluded.approximate_size_bytes,
                    file_count=excluded.file_count,
                    annotation_types_json=excluded.annotation_types_json,
                    license_identifier=excluded.license_identifier,
                    license_url=excluded.license_url,
                    license_status=excluded.license_status,
                    commercial_use_allowed=excluded.commercial_use_allowed,
                    attribution_required=excluded.attribution_required,
                    relevance_score=excluded.relevance_score,
                    relevance_breakdown_json=excluded.relevance_breakdown_json,
                    description=excluded.description,
                    limitations_notes=excluded.limitations_notes,
                    updated_at=excluded.updated_at
                """,
                (
                    candidate_data["id"],
                    candidate_data["source_id"],
                    candidate_data["provider_name"],
                    candidate_data["title"],
                    candidate_data["publisher"],
                    candidate_data.get("external_id"),
                    candidate_data["canonical_url"],
                    candidate_data.get("landing_page_url"),
                    candidate_data["domain_tag"],
                    1 if candidate_data.get("is_direct_videoscope") else 0,
                    json.dumps(candidate_data.get("modalities", [])),
                    candidate_data.get("approximate_size_bytes"),
                    candidate_data.get("file_count"),
                    json.dumps(candidate_data.get("annotation_types", [])),
                    candidate_data["license_identifier"],
                    candidate_data.get("license_url"),
                    candidate_data.get("license_status", "LICENSE_UNKNOWN"),
                    1 if candidate_data.get("commercial_use_allowed") else 0,
                    1 if candidate_data.get("attribution_required", True) else 0,
                    candidate_data.get("relevance_score", 0.0),
                    json.dumps(candidate_data.get("relevance_breakdown", {})),
                    candidate_data.get("description"),
                    candidate_data.get("limitations_notes"),
                    candidate_data.get("acquisition_status", "DISCOVERED"),
                    candidate_data.get("created_at", now),
                    now
                )
            )
        return self.get_candidate(candidate_data["id"]) # type: ignore

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a candidate dataset."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM dataset_candidates WHERE id = ?", (candidate_id,))
            row = cursor.fetchone()
            if not row:
                return None
            c = dict(row)
            c["is_direct_videoscope"] = bool(c["is_direct_videoscope"])
            c["commercial_use_allowed"] = bool(c["commercial_use_allowed"])
            c["attribution_required"] = bool(c["attribution_required"])
            c["modalities"] = json.loads(c.get("modalities_json") or "[]")
            c["annotation_types"] = json.loads(c.get("annotation_types_json") or "[]")
            if c.get("relevance_breakdown_json"):
                try:
                    c["relevance_breakdown"] = json.loads(c["relevance_breakdown_json"])
                except Exception:
                    c["relevance_breakdown"] = None
            return c

    def list_candidates(
        self,
        source_id: Optional[str] = None,
        domain_tag: Optional[str] = None,
        license_status: Optional[str] = None,
        acquisition_status: Optional[str] = None,
        direct_videoscope_only: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List candidate datasets with multi-attribute filtering."""
        query = "SELECT * FROM dataset_candidates WHERE 1=1"
        params: List[Any] = []

        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if domain_tag:
            query += " AND domain_tag = ?"
            params.append(domain_tag)
        if license_status:
            query += " AND license_status = ?"
            params.append(license_status)
        if acquisition_status:
            query += " AND acquisition_status = ?"
            params.append(acquisition_status)
        if direct_videoscope_only:
            query += " AND is_direct_videoscope = 1"

        query += " ORDER BY relevance_score DESC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                c = dict(r)
                c["is_direct_videoscope"] = bool(c["is_direct_videoscope"])
                c["commercial_use_allowed"] = bool(c["commercial_use_allowed"])
                c["attribution_required"] = bool(c["attribution_required"])
                c["modalities"] = json.loads(c.get("modalities_json") or "[]")
                c["annotation_types"] = json.loads(c.get("annotation_types_json") or "[]")
                if c.get("relevance_breakdown_json"):
                    try:
                        c["relevance_breakdown"] = json.loads(c["relevance_breakdown_json"])
                    except Exception:
                        c["relevance_breakdown"] = None
                results.append(c)
            return results

    def record_license_review(
        self,
        candidate_id: str,
        license_status: str,
        commercial_rights_status: str,
        license_notes: Optional[str],
        terms_url: Optional[str],
        reviewed_by: str
    ) -> Dict[str, Any]:
        """Record formal human license audit for a candidate."""
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise KeyError(f"Candidate '{candidate_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        review_id = f"lrev_{uuid.uuid4().hex[:12]}" if "uuid" in globals() else f"lrev_{now[:10]}"

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO source_license_reviews (
                    id, candidate_id, reviewed_by, decision_status,
                    commercial_rights_status, license_notes, terms_url, reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (review_id, candidate_id, reviewed_by, license_status, commercial_rights_status, license_notes, terms_url, now)
            )

            comm_ok = 1 if commercial_rights_status.upper() == "ALLOWED" else 0
            conn.execute(
                """
                UPDATE dataset_candidates
                SET license_status = ?,
                    commercial_use_allowed = ?,
                    acquisition_status = 'LICENSE_REVIEWED',
                    updated_at = ?
                WHERE id = ?
                """,
                (license_status, comm_ok, now, candidate_id)
            )

        return self.get_candidate(candidate_id) # type: ignore

    def create_acquisition_job(
        self,
        job_id: str,
        candidate_id: Optional[str],
        job_type: str,
        target_directory: str,
        created_by: str
    ) -> Dict[str, Any]:
        """Create and track an acquisition or synthetic generation job."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO acquisition_jobs (
                    id, candidate_id, job_type, status, target_directory,
                    bytes_downloaded, files_acquired, error_message, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, 'PENDING', ?, 0, 0, NULL, ?, ?, ?)
                """,
                (job_id, candidate_id, job_type, target_directory, created_by, now, now)
            )
        return self.get_acquisition_job(job_id) # type: ignore

    def update_acquisition_job(
        self,
        job_id: str,
        status: str,
        bytes_downloaded: int = 0,
        files_acquired: int = 0,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update progress or completion state of an acquisition job."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE acquisition_jobs
                SET status = ?,
                    bytes_downloaded = ?,
                    files_acquired = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, bytes_downloaded, files_acquired, error_message, now, job_id)
            )
        return self.get_acquisition_job(job_id) # type: ignore

    def get_acquisition_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve acquisition job status by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM acquisition_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_acquisition_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List acquisition jobs chronologically."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM acquisition_jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            return [dict(r) for r in cursor.fetchall()]

    def record_audit_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        job_id: Optional[str] = None,
        candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record an immutable compliance and provenance audit event."""
        now = datetime.now(timezone.utc).isoformat()
        event_id = f"aev_{uuid.uuid4().hex[:12]}" if "uuid" in globals() else f"aev_{now[:10]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO acquisition_events (id, job_id, candidate_id, event_type, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_id, job_id, candidate_id, event_type, json.dumps(details), now)
            )
        return {
            "id": event_id,
            "job_id": job_id,
            "candidate_id": candidate_id,
            "event_type": event_type,
            "details": details,
            "created_at": now
        }

    def list_audit_events(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """List compliance audit trail events."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM acquisition_events ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            events = []
            for r in cursor.fetchall():
                e = dict(r)
                e["details"] = json.loads(e.get("details_json") or "{}")
                events.append(e)
            return events

    def record_provenance_link(
        self,
        asset_id: str,
        provenance_type: str,
        candidate_id: Optional[str] = None,
        parent_asset_id: Optional[str] = None,
        generator_info: Optional[Dict[str, Any]] = None,
        generation_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Link an ingested or synthetic asset to its lineage origin."""
        now = datetime.now(timezone.utc).isoformat()
        link_id = f"prv_{uuid.uuid4().hex[:12]}" if "uuid" in globals() else f"prv_{now[:10]}"
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO asset_provenance_links (
                    id, asset_id, candidate_id, parent_asset_id,
                    provenance_type, generator_info_json, generation_params_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link_id,
                    asset_id,
                    candidate_id,
                    parent_asset_id,
                    provenance_type,
                    json.dumps(generator_info or {}),
                    json.dumps(generation_params or {}),
                    now
                )
            )
        return {"id": link_id, "asset_id": asset_id, "provenance_type": provenance_type, "created_at": now}

    # --- Equipment Taxonomy & Decoupled Annotations ---

    def create_decoupled_annotation(self, annot_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert an equipment-aware decoupled annotation."""
        now = datetime.now(timezone.utc).isoformat()
        annot_id = annot_data.get("id") or f"ant_{uuid.uuid4().hex[:12]}"
        bbox_json = json.dumps(annot_data.get("bbox")) if annot_data.get("bbox") else None

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO decoupled_annotations (
                    id, asset_id, sample_id, frame_index, equipment_family,
                    component_type, defect_category, observed_visual_condition,
                    bbox_json, segmentation_mask_path, source_raw_label,
                    mapping_confidence, annotator_type, annotator_id,
                    taxonomy_version, is_synthetic, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    annot_id,
                    annot_data["asset_id"],
                    annot_data.get("sample_id"),
                    annot_data.get("frame_index", 0),
                    annot_data["equipment_family"],
                    annot_data["component_type"],
                    annot_data["defect_category"],
                    annot_data.get("observed_visual_condition"),
                    bbox_json,
                    annot_data.get("segmentation_mask_path"),
                    annot_data.get("source_raw_label"),
                    annot_data.get("mapping_confidence", "EXACT_MATCH"),
                    annot_data.get("annotator_type", "HUMAN_EXPERT"),
                    annot_data.get("annotator_id", "Inspector"),
                    annot_data.get("taxonomy_version", "2.0.0"),
                    1 if annot_data.get("is_synthetic") else 0,
                    annot_data.get("notes"),
                    now,
                    now
                )
            )
        return self.get_decoupled_annotation(annot_id) # type: ignore

    def get_decoupled_annotation(self, annot_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve annotation by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM decoupled_annotations WHERE id = ?", (annot_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_synthetic"] = bool(res["is_synthetic"])
            res["bbox"] = json.loads(res["bbox_json"]) if res.get("bbox_json") else None
            return res

    def list_decoupled_annotations(
        self,
        asset_id: Optional[str] = None,
        equipment_family: Optional[str] = None,
        component_type: Optional[str] = None,
        defect_category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List annotations with equipment taxonomy filters."""
        query = "SELECT * FROM decoupled_annotations WHERE 1=1"
        params: List[Any] = []
        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)
        if equipment_family:
            query += " AND equipment_family = ?"
            params.append(equipment_family)
        if component_type:
            query += " AND component_type = ?"
            params.append(component_type)
        if defect_category:
            query += " AND defect_category = ?"
            params.append(defect_category)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                item = dict(r)
                item["is_synthetic"] = bool(item["is_synthetic"])
                item["bbox"] = json.loads(item["bbox_json"]) if item.get("bbox_json") else None
                results.append(item)
            return results

    # --- Candidate Findings & Human Review State Machine ---

    def create_candidate_finding(self, finding_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new candidate finding observation."""
        now = datetime.now(timezone.utc).isoformat()
        finding_id = finding_data.get("id") or f"fnd_{uuid.uuid4().hex[:12]}"
        bbox_json = json.dumps(finding_data.get("candidate_bbox")) if finding_data.get("candidate_bbox") else None

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO candidate_findings (
                    id, asset_id, sample_id, frame_index, timestamp_ms,
                    timestamp_provenance, equipment_family, component_type,
                    candidate_defect, candidate_bbox_json, model_prediction_confidence,
                    is_simulated, review_state, severity, reviewed_by, reviewer_rationale,
                    engineering_diagnosis, advisory_recommendation, reviewed_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    finding_data["asset_id"],
                    finding_data.get("sample_id"),
                    finding_data.get("frame_index", 0),
                    finding_data.get("timestamp_ms", 0.0),
                    finding_data.get("timestamp_provenance", "NOMINAL_APPROXIMATE"),
                    finding_data["equipment_family"],
                    finding_data["component_type"],
                    finding_data["candidate_defect"],
                    bbox_json,
                    finding_data.get("model_prediction_confidence"),
                    1 if finding_data.get("is_simulated", True) else 0,
                    finding_data.get("review_state", "UNREVIEWED"),
                    finding_data.get("severity", "UNSPECIFIED"),
                    finding_data.get("reviewed_by"),
                    finding_data.get("reviewer_rationale"),
                    finding_data.get("engineering_diagnosis"),
                    finding_data.get("advisory_recommendation"),
                    finding_data.get("reviewed_at"),
                    now,
                    now
                )
            )
        return self.get_candidate_finding(finding_id) # type: ignore

    def get_candidate_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve candidate finding by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM candidate_findings WHERE id = ?", (finding_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_simulated"] = bool(res["is_simulated"])
            res["candidate_bbox"] = json.loads(res["candidate_bbox_json"]) if res.get("candidate_bbox_json") else None
            return res

    def list_candidate_findings(
        self,
        asset_id: Optional[str] = None,
        review_state: Optional[str] = None,
        equipment_family: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List candidate findings with state filters."""
        query = "SELECT * FROM candidate_findings WHERE 1=1"
        params: List[Any] = []
        if asset_id:
            query += " AND asset_id = ?"
            params.append(asset_id)
        if review_state:
            query += " AND review_state = ?"
            params.append(review_state)
        if equipment_family:
            query += " AND equipment_family = ?"
            params.append(equipment_family)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._get_connection() as conn:
            cursor = conn.execute(query, tuple(params))
            results = []
            for r in cursor.fetchall():
                item = dict(r)
                item["is_simulated"] = bool(item["is_simulated"])
                item["candidate_bbox"] = json.loads(item["candidate_bbox_json"]) if item.get("candidate_bbox_json") else None
                results.append(item)
            return results

    def record_finding_decision(
        self,
        finding_id: str,
        review_state: str,
        severity: str,
        reviewed_by: str,
        reviewer_rationale: str,
        adjusted_defect: Optional[str] = None,
        adjusted_bbox: Optional[Dict[str, Any]] = None,
        engineering_diagnosis: Optional[str] = None,
        advisory_recommendation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a human review decision transition with strict audit history tracking.
        """
        current = self.get_candidate_finding(finding_id)
        if not current:
            raise KeyError(f"Finding '{finding_id}' not found.")

        now = datetime.now(timezone.utc).isoformat()
        history_id = f"fhist_{uuid.uuid4().hex[:12]}"
        bbox_json = json.dumps(adjusted_bbox) if adjusted_bbox else current.get("candidate_bbox_json")
        target_defect = adjusted_defect or current["candidate_defect"]

        with self._get_connection() as conn:
            # 1. Insert audit log history
            conn.execute(
                """
                INSERT INTO finding_decision_history (
                    id, finding_id, previous_state, new_state, severity,
                    reviewed_by, reviewer_rationale, adjusted_defect,
                    adjusted_bbox_json, engineering_diagnosis, advisory_recommendation,
                    transitioned_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history_id,
                    finding_id,
                    current["review_state"],
                    review_state,
                    severity,
                    reviewed_by,
                    reviewer_rationale,
                    adjusted_defect,
                    bbox_json,
                    engineering_diagnosis,
                    advisory_recommendation,
                    now
                )
            )

            # 2. Update finding record
            conn.execute(
                """
                UPDATE candidate_findings
                SET review_state = ?,
                    severity = ?,
                    candidate_defect = ?,
                    candidate_bbox_json = ?,
                    reviewed_by = ?,
                    reviewer_rationale = ?,
                    engineering_diagnosis = ?,
                    advisory_recommendation = ?,
                    reviewed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    review_state,
                    severity,
                    target_defect,
                    bbox_json,
                    reviewed_by,
                    reviewer_rationale,
                    engineering_diagnosis,
                    advisory_recommendation,
                    now,
                    now,
                    finding_id
                )
            )

        return self.get_candidate_finding(finding_id) # type: ignore

    def get_finding_decision_history(self, finding_id: str) -> List[Dict[str, Any]]:
        """Retrieve full decision transition history for a finding."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM finding_decision_history WHERE finding_id = ? ORDER BY transitioned_at ASC",
                (finding_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    # --- Evaluation Runs Persistence ---

    def save_evaluation_run(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist an evaluation report and manifest hash."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evaluation_runs (id, run_name, dataset_manifest_hash, report_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report_data["run_id"],
                    report_data["run_name"],
                    report_data["dataset_manifest_hash"],
                    json.dumps(report_data),
                    now
                )
            )
        return self.get_evaluation_run(report_data["run_id"]) # type: ignore

    def get_evaluation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evaluation report by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM evaluation_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return json.loads(row["report_json"])

    def list_evaluation_runs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List historic evaluation runs."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, run_name, dataset_manifest_hash, created_at FROM evaluation_runs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, skip)
            )
            return [dict(r) for r in cursor.fetchall()]

    # --- Inference Records (Provenance & Audit) ---

    def create_inference_record(
        self,
        record_id: str,
        session_id: str,
        media_id: str,
        frame_index: int,
        timestamp_ms: float,
        evidence_sha256: str,
        engine_name: str,
        model_id: str,
        model_version: str,
        is_simulated: bool,
        processing_duration_ms: float,
        prompt_config_dict: Optional[Dict[str, Any]] = None,
        cache_hit: bool = False,
        raw_response_dict: Optional[Dict[str, Any]] = None,
        normalized_result_dict: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Persist full provenance record for an inference run."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO inference_records (
                    id, session_id, media_id, frame_index, timestamp_ms,
                    evidence_sha256, engine_name, model_id, model_version,
                    prompt_config_json, is_simulated, processing_duration_ms,
                    cache_hit, raw_response_json, normalized_result_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id, session_id, media_id, frame_index, timestamp_ms,
                    evidence_sha256, engine_name, model_id, model_version,
                    json.dumps(prompt_config_dict) if prompt_config_dict else None,
                    1 if is_simulated else 0, processing_duration_ms,
                    1 if cache_hit else 0,
                    json.dumps(raw_response_dict) if raw_response_dict else None,
                    json.dumps(normalized_result_dict) if normalized_result_dict else None,
                    now
                )
            )
        return self.get_inference_record(record_id) # type: ignore

    def get_inference_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an inference provenance record."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM inference_records WHERE id = ?", (record_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["is_simulated"] = bool(res["is_simulated"])
            res["cache_hit"] = bool(res["cache_hit"])
            res["prompt_config"] = json.loads(res["prompt_config_json"]) if res.get("prompt_config_json") else None
            res["raw_response"] = json.loads(res["raw_response_json"]) if res.get("raw_response_json") else None
            res["normalized_result"] = json.loads(res["normalized_result_json"]) if res.get("normalized_result_json") else None
            return res

    def list_inference_records(
        self,
        session_id: Optional[str] = None,
        media_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List inference provenance records."""
        query = "SELECT * FROM inference_records WHERE 1=1"
        params: List[Any] = []
        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)
        if media_id:
            query += " AND media_id = ?"
            params.append(media_id)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            records = []
            for row in cursor.fetchall():
                res = dict(row)
                res["is_simulated"] = bool(res["is_simulated"])
                res["cache_hit"] = bool(res["cache_hit"])
                res["prompt_config"] = json.loads(res["prompt_config_json"]) if res.get("prompt_config_json") else None
                res["raw_response"] = json.loads(res["raw_response_json"]) if res.get("raw_response_json") else None
                res["normalized_result"] = json.loads(res["normalized_result_json"]) if res.get("normalized_result_json") else None
                records.append(res)
            return records


repo = InspectionRepository()



