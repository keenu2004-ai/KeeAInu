"""Dataset Partitioning and Evidence Provenance Schemas."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DatasetPartition(str, Enum):
    """Enforced dataset partitions ensuring separation of real vs synthetic data."""
    REAL_INTERNAL = "REAL_INTERNAL"
    REAL_PUBLIC = "REAL_PUBLIC"
    REAL_LICENSED = "REAL_LICENSED"
    SYNTHETIC = "SYNTHETIC"
    AUGMENTED = "AUGMENTED"
    UNVERIFIED = "UNVERIFIED"


class EvidenceIntegrityStatus(str, Enum):
    """Integrity state of inspection evidence."""
    VERIFIED_IMMUTABLE = "VERIFIED_IMMUTABLE"
    HASH_MISMATCH_TAMPERED = "HASH_MISMATCH_TAMPERED"
    FILE_MISSING = "FILE_MISSING"
    UNVERIFIED_PENDING = "UNVERIFIED_PENDING"


class AssetPartitionRecord(BaseModel):
    """Partition assignment and full lineage provenance record."""
    asset_id: str
    partition: DatasetPartition
    source_dataset_id: Optional[str] = None
    canonical_source_url: Optional[str] = None
    original_sha256: str
    current_sha256: str
    integrity_status: EvidenceIntegrityStatus
    parent_asset_id: Optional[str] = None
    generator_version: Optional[str] = None
    generation_seed: Optional[int] = None
    generation_parameters: Optional[Dict[str, Any]] = None
    license_status: str
    commercial_use_allowed: bool
    created_at: str
    updated_at: str
