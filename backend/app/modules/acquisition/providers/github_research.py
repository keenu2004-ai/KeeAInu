"""GitHub Research & Academic Repositories Discovery Provider."""

from datetime import datetime, timezone
from typing import List, Optional
import uuid

from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    CandidateAcquisitionStatus,
    DiscoveryVerificationStatus,
    DownloadSupportStatus
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.relevance import evaluate_relevance
from backend.app.modules.acquisition.license_gate import infer_initial_license_status


GITHUB_RESEARCH_DATASETS = [
    {
        "id": "gh_kolektorsdd_surface_cracks",
        "title": "Kolektor Surface-Defect Dataset (KolektorSDD2 Electrical Commutator)",
        "publisher": "University of Ljubljana / Visual Cognitive Systems Lab",
        "canonical_url": "https://github.com/vicoslab/kolektorsdd2",
        "landing_page_url": "https://www.vicos.si/resources/kolektorsdd2/",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": False,
        "modalities": ["still_images", "high_resolution_rgb"],
        "approximate_size_bytes": 1300000000,
        "file_count": 3335,
        "annotation_types": ["pixel_segmentation_masks"],
        "license_identifier": "CC-BY-NC-4.0",
        "description": "3,335 images of electrical commutators embedded with microscopic surface cracks, fractures, and uneven embedding matrices with pixel-level ground truth.",
        "limitations_notes": "High-precision microscopic cracks on cylindrical mechanical components. Non-commercial research license."
    },
    {
        "id": "gh_industrial_weld_xray_gDX",
        "title": "GDXray Weld Defect Radiography and Optical Inspection Benchmark",
        "publisher": "Pontificia Universidad Catolica de Chile / Domingo Mery",
        "canonical_url": "https://github.com/domingomery/gdxray",
        "landing_page_url": "http://dmery.ing.puc.cl/index.php/material/gdxray/",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": False,
        "modalities": ["still_images", "radiographs"],
        "approximate_size_bytes": 3500000000,
        "file_count": 19400,
        "annotation_types": ["bounding_boxes", "defect_classification"],
        "license_identifier": "RESEARCH-ONLY",
        "description": "Comprehensive NDT dataset of industrial pipes, castings, and weld seams containing porosity, inclusions, and cracks.",
        "limitations_notes": "Radiographic NDT modality. Academic research use only."
    }
]


class GitHubResearchProvider(BaseSourceProvider):
    """GitHub Research & Academic Repositories provider."""

    @property
    def provider_id(self) -> str:
        return "github_research"

    @property
    def provider_name(self) -> str:
        return "GitHub Research Repositories"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.RESEARCH_INSTITUTION

    @property
    def description(self) -> str:
        return "Discovers peer-reviewed academic inspection datasets and code repositories on GitHub."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in GITHUB_RESEARCH_DATASETS:
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
                    id=f"cand_gh_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
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

        return results

    async def get_candidate_details(self, candidate_id: str) -> Optional[DatasetCandidateRecord]:
        query = SearchCandidateQuery(query="all", max_results_per_provider=50)
        candidates = await self.search(query)
        for c in candidates:
            if c.id == candidate_id:
                return c
        return None
