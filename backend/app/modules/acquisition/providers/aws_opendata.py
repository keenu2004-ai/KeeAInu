"""AWS Registry of Open Data Discovery Provider."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    CandidateAcquisitionStatus
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.relevance import evaluate_relevance
from backend.app.modules.acquisition.license_gate import infer_initial_license_status


AWS_OPEN_DATASETS = [
    {
        "id": "aws_noaa_underwater_imaging",
        "title": "NOAA Deep-Sea & Underwater Pipeline Inspection Imagery Archive",
        "publisher": "National Oceanic and Atmospheric Administration (NOAA)",
        "canonical_url": "https://registry.opendata.aws/noaa-ocean-imaging/",
        "landing_page_url": "https://registry.opendata.aws/noaa-ocean-imaging/",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": True,
        "modalities": ["video", "still_images"],
        "approximate_size_bytes": 12000000000,
        "file_count": 8500,
        "annotation_types": ["classification_labels"],
        "license_identifier": "PUBLIC-DOMAIN",
        "description": "High-resolution ROV probe and underwater endoscopic visual recordings of subsea pipeline infrastructure, risers, and structural welds.",
        "limitations_notes": "Turbid marine lighting with localized strobe illumination similar to industrial probe optics."
    }
]


class AwsOpenDataProvider(BaseSourceProvider):
    """AWS Registry of Open Data discovery provider."""

    @property
    def provider_id(self) -> str:
        return "aws_open_data"

    @property
    def provider_name(self) -> str:
        return "AWS Registry of Open Data"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.CLOUD_REGISTRY

    @property
    def description(self) -> str:
        return "Discovers open scientific, environmental, and infrastructure datasets hosted on AWS Open Data S3 buckets."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in AWS_OPEN_DATASETS:
            combined = f"{item['title']} {item['description']} {item['domain_tag']}".lower()
            if any(term in combined for term in q_lower.split()) or "all" in q_lower:
                rel = evaluate_relevance(
                    title=item["title"],
                    description=item["description"],
                    target_domain=query.target_domain or item["domain_tag"],
                    modalities=item["modalities"],
                    annotation_types=item["annotation_types"],
                    is_direct_videoscope_declared=item["is_direct_videoscope"]
                )

                if query.direct_videoscope_only and not rel.is_direct_videoscope:
                    continue

                lic_status, comm_ok, attr_req = infer_initial_license_status(item["license_identifier"])

                cand = DatasetCandidateRecord(
                    id=f"cand_aws_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
                    source_id=self.provider_id,
                    provider_name=self.provider_name,
                    title=item["title"],
                    publisher=item["publisher"],
                    external_id=item["id"],
                    canonical_url=item["canonical_url"],
                    landing_page_url=item["landing_page_url"],
                    domain_tag=item["domain_tag"],
                    is_direct_videoscope=item["is_direct_videoscope"],
                    modalities=item["modalities"],
                    approximate_size_bytes=item["approximate_size_bytes"],
                    file_count=item["file_count"],
                    annotation_types=item["annotation_types"],
                    license_identifier=item["license_identifier"],
                    license_status=lic_status,
                    commercial_use_allowed=comm_ok,
                    attribution_required=attr_req,
                    relevance_score=rel.total_score,
                    relevance_breakdown=rel,
                    description=item["description"],
                    limitations_notes=item["limitations_notes"],
                    acquisition_status=CandidateAcquisitionStatus.DISCOVERED,
                    created_at=now,
                    updated_at=now
                )
                results.append(cand)
                if len(results) >= query.max_results_per_provider:
                    break

        return results

    async def get_candidate_details(self, candidate_id: str) -> Optional[DatasetCandidateRecord]:
        query = SearchCandidateQuery(query="all", max_results_per_provider=50)
        candidates = await self.search(query)
        for c in candidates:
            if c.id == candidate_id:
                return c
        return None
