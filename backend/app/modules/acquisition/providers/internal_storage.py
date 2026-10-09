"""Controlled Internal Storage & Company Vault Discovery Provider."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import List, Optional
import uuid

from backend.app.core.config import settings
from backend.app.core.security import is_path_safe, calculate_sha256
from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    CandidateAcquisitionStatus,
    LicensePermissionStatus,
    DiscoveryVerificationStatus,
    DownloadSupportStatus
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.relevance import evaluate_relevance


class InternalStorageProvider(BaseSourceProvider):
    """Controlled Internal Company Storage and Secure Vault Discovery Provider."""

    @property
    def provider_id(self) -> str:
        return "internal_storage"

    @property
    def provider_name(self) -> str:
        return "Internal Company Vault & Ingest Directories"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.INTERNAL_STORAGE

    @property
    def description(self) -> str:
        return "Discovers authorized internal enterprise inspection vaults and configured import directories under strict sandboxing."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()
        
        # Scanned directories are strictly restricted to configured internal roots
        configured_roots = [
            ("source_footage", settings.SOURCE_FOOTAGE_DIR, "Primary Videoscope Footage Repository"),
            ("internal_imports", settings.DATA_DIR / "internal_imports", "Authorized Engineering Media Import Vault")
        ]

        for code, root_dir, display_name in configured_roots:
            if not root_dir.exists():
                continue
            if not is_path_safe(root_dir.resolve(), settings.BASE_DIR):
                continue

            # Gather file statistics safely without recursive boundary escape
            file_count = 0
            total_bytes = 0
            modalities = set()
            has_videoscope = True

            for r, dirs, files in os.walk(root_dir, followlinks=False):
                cur = Path(r).resolve()
                if not is_path_safe(cur, root_dir.resolve()):
                    continue
                for f in files:
                    fp = Path(r) / f
                    if not fp.exists() or not is_path_safe(fp.resolve(), root_dir.resolve()):
                        continue
                    ext = fp.suffix.lower()
                    if ext in settings.ALLOWED_VIDEO_EXTENSIONS:
                        modalities.add("video")
                        file_count += 1
                        total_bytes += fp.stat().st_size
                    elif ext in settings.ALLOWED_IMAGE_EXTENSIONS:
                        modalities.add("still_images")
                        file_count += 1
                        total_bytes += fp.stat().st_size

            if file_count > 0:
                rel = evaluate_relevance(
                    title=display_name,
                    description=f"Internal company footage vault containing {file_count} raw industrial inspection assets.",
                    target_domain=query.target_domain or "UNKNOWN",
                    modalities=list(modalities),
                    annotation_types=["unreviewed"],
                    is_direct_videoscope_declared=True
                )

                cand = DatasetCandidateRecord(
                    id=f"cand_int_{code}",
                    source_id=self.provider_id,
                    provider_name=self.provider_name,
                    title=f"Internal Vault: {display_name}",
                    publisher="KeeAInu Enterprise Ingest",
                    external_id=f"vault_{code}",
                    canonical_url=f"internal://vault/{code}",
                    landing_page_url=None,
                    domain_tag=query.target_domain or "UNKNOWN",
                    is_direct_videoscope=True,
                    modalities=list(modalities) if modalities else ["still_images"],
                    approximate_size_bytes=total_bytes,
                    file_count=file_count,
                    annotation_types=["unreviewed_raw_footage"],
                    license_identifier="PROPRIETARY-INTERNAL",
                    license_status=LicensePermissionStatus.APPROVED_FOR_EVALUATION,
                    commercial_use_allowed=True,
                    attribution_required=False,
                    relevance_score=rel.total_score,
                    relevance_breakdown=rel,
                    description=f"Authorized internal videoscope repository containing {file_count} assets ({total_bytes / (1024*1024):.1f} MB) in '{root_dir.name}'.",
                    limitations_notes="Internal confidential inspection media. Bound by enterprise data governance and export controls.",
                    acquisition_status=CandidateAcquisitionStatus.ACQUISITION_APPROVED,
                    verification_status=DiscoveryVerificationStatus.LIVE_METADATA_VERIFIED,
                    download_support=DownloadSupportStatus.DIRECT_DOWNLOAD_SUPPORTED,
                    created_at=now,
                    updated_at=now
                )
                results.append(cand)

        return results

    async def get_candidate_details(self, candidate_id: str) -> Optional[DatasetCandidateRecord]:
        query = SearchCandidateQuery(query="all", max_results_per_provider=50)
        candidates = await self.search(query)
        for c in candidates:
            if c.id == candidate_id:
                return c
        return None
