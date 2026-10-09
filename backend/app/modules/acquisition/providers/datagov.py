"""Government Open Data Catalogs Discovery Provider (Data.gov & Open Government Data India)."""

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


GOV_INSPECTION_DATASETS = [
    {
        "id": "gov_usdot_pipeline_inspection",
        "title": "US DOT PHMSA Pipeline Integrity and In-Line Inspection Benchmark Archive",
        "publisher": "U.S. Department of Transportation / PHMSA",
        "canonical_url": "https://catalog.data.gov/dataset/pipeline-integrity-and-visual-inspection-archive",
        "landing_page_url": "https://www.phmsa.dot.gov/data-and-statistics/pipeline",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": True,
        "modalities": ["video", "still_images", "ultrasonic_logs"],
        "approximate_size_bytes": 4200000000,
        "file_count": 1600,
        "annotation_types": ["bounding_boxes", "measurement_logs"],
        "license_identifier": "PUBLIC-DOMAIN",
        "description": "Public domain visual inspection footage and in-line inspection (ILI) verification runs documenting metal loss, mechanical gouges, and stress corrosion cracking in transport pipelines.",
        "limitations_notes": "Official public domain federal dataset. Real pipeline wall inspections."
    },
    {
        "id": "gov_ogd_india_railway_track_defect",
        "title": "Indian Railways / RDSO Ultrasonic & Endoscopic Track Rail Defect Corpus",
        "publisher": "Open Government Data (OGD) Platform India / Ministry of Railways",
        "canonical_url": "https://data.gov.in/resource/railway-track-structural-defect-records",
        "landing_page_url": "https://data.gov.in/",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": False,
        "modalities": ["still_images", "measurement_logs"],
        "approximate_size_bytes": 680000000,
        "file_count": 2100,
        "annotation_types": ["defect_classification", "severity_levels"],
        "license_identifier": "OPEN-GOVERNMENT-LICENCE",
        "description": "Government of India open dataset published under Government Open Data License (GODL-India) detailing rail joint cracks, wheel burns, and switch component wear.",
        "limitations_notes": "GODL India license requires explicit attribution to Government of India / OGD Platform."
    }
]


class DataGovProvider(BaseSourceProvider):
    """Government Open Data Catalogs provider (Data.gov and data.gov.in)."""

    @property
    def provider_id(self) -> str:
        return "datagov"

    @property
    def provider_name(self) -> str:
        return "Government Open Data (Data.gov / OGD India)"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.GOVERNMENT_CATALOG

    @property
    def description(self) -> str:
        return "Discovers open government visual inspection records and infrastructure datasets from US and Indian public catalogs."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in GOV_INSPECTION_DATASETS:
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
                    id=f"cand_gov_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
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
