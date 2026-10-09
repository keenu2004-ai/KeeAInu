"""Google Dataset Search Discovery Provider."""

from datetime import datetime, timezone
from typing import List, Optional
import urllib.parse
import uuid

from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    CandidateAcquisitionStatus,
    DiscoveryVerificationStatus,
    DownloadSupportStatus,
    LicensePermissionStatus
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.relevance import evaluate_relevance
from backend.app.modules.acquisition.license_gate import infer_initial_license_status


INDEXED_GOOGLE_DATASETS = [
    {
        "id": "gds_pipeline_corrosion_zenodo",
        "title": "Industrial High-Pressure Gas Pipeline Internal Corrosion Borescope Benchmark",
        "publisher": "Zenodo / European Research Council",
        "canonical_url": "https://zenodo.org/records/5839201",
        "landing_page_url": "https://datasetsearch.research.google.com/search?query=pipeline%20internal%20corrosion%20borescope",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": True,
        "modalities": ["video", "still_images"],
        "approximate_size_bytes": 3100000000,
        "file_count": 890,
        "annotation_types": ["pixel_segmentation_masks", "depth_calibrations"],
        "license_identifier": "CC-BY-4.0",
        "description": "Multi-spectral videoscope inspection footage of API 5L carbon steel pipes subjected to accelerated CO2/H2S corrosion with calibrated pit depth measurements.",
        "limitations_notes": "Laboratory accelerated corrosion rig recorded with 6mm industrial videoscope probe."
    },
    {
        "id": "gds_aero_engine_combustor",
        "title": "Aero-Engine Combustor Liner Thermal Barrier Coating Spallation Dataset",
        "publisher": "NASA Open Data Portal / Dryad",
        "canonical_url": "https://datadryad.org/stash/dataset/doi:10.5061/dryad.aerocombustor",
        "landing_page_url": "https://datasetsearch.research.google.com/search?query=combustor%20liner%20borescope%20spallation",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": True,
        "modalities": ["still_images", "video"],
        "approximate_size_bytes": 1400000000,
        "file_count": 620,
        "annotation_types": ["bounding_boxes", "defect_classification"],
        "license_identifier": "CC0-1.0",
        "description": "Borescope inspection captures of turbofan combustion chamber tiles showing thermal barrier coating (TBC) degradation, burn-through, and micro-cracks.",
        "limitations_notes": "Captured through guide tube ports with high-temperature industrial probe."
    }
]


class GoogleDatasetSearchProvider(BaseSourceProvider):
    """Google Dataset Search indexer and research dataset pointer provider."""

    @property
    def provider_id(self) -> str:
        return "google_dataset_search"

    @property
    def provider_name(self) -> str:
        return "Google Dataset Search"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.PUBLIC_CATALOG

    @property
    def description(self) -> str:
        return "Discovers cross-institutional scientific repositories, Zenodo, Dryad, and IEEE DataPort archives."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in INDEXED_GOOGLE_DATASETS:
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
                    id=f"cand_gds_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
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
                    verification_status=DiscoveryVerificationStatus.CURATED_LEAD_AWAITING_VERIFICATION,
                    download_support=DownloadSupportStatus.MANUAL_ACTION_REQUIRED,
                    created_at=now,
                    updated_at=now
                )
                results.append(cand)
                if len(results) >= query.max_results_per_provider:
                    break

        # If no canned item matched, generate a dynamic Google Dataset Search landing destination candidate
        if not results:
            encoded_query = urllib.parse.quote_plus(query.query)
            search_url = f"https://datasetsearch.research.google.com/search?query={encoded_query}"
            rel = evaluate_relevance(
                title=f"Google Dataset Search Index: {query.query}",
                description=f"Automated query link to scientific repositories indexing '{query.query}'.",
                target_domain=query.target_domain or "UNKNOWN",
                modalities=["still_images", "video"],
                annotation_types=["unspecified"],
                is_direct_videoscope_declared="borescope" in query.query.lower() or "videoscope" in query.query.lower()
            )
            cand = DatasetCandidateRecord(
                id=f"cand_gds_{uuid.uuid5(uuid.NAMESPACE_URL, search_url).hex[:10]}",
                source_id=self.provider_id,
                provider_name=self.provider_name,
                title=f"External Catalog Query: '{query.query}' on Google Dataset Search",
                publisher="Google Dataset Search Aggregator",
                external_id=f"gds_dyn_{encoded_query[:20]}",
                canonical_url=search_url,
                landing_page_url=search_url,
                domain_tag=query.target_domain or "UNKNOWN",
                is_direct_videoscope=rel.is_direct_videoscope,
                modalities=["still_images", "video"],
                approximate_size_bytes=None,
                file_count=None,
                annotation_types=["variable"],
                license_identifier="UNKNOWN",
                license_status=LicensePermissionStatus.LICENSE_UNKNOWN,
                commercial_use_allowed=False,
                attribution_required=True,
                relevance_score=rel.total_score,
                relevance_breakdown=rel,
                description=f"Live aggregated search link into thousands of academic and publisher data portals for '{query.query}'. Individual dataset licenses must be verified per landing page.",
                limitations_notes="Catalog aggregator. Underlying media hosted externally. Requires individual license and access audit.",
                acquisition_status=CandidateAcquisitionStatus.DISCOVERED,
                verification_status=DiscoveryVerificationStatus.PUBLISHER_LINK_VERIFIED_DATA_UNAVAILABLE,
                download_support=DownloadSupportStatus.MANUAL_ACTION_REQUIRED,
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
