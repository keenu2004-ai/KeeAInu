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


repo = InspectionRepository()
