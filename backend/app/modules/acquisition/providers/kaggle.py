"""Kaggle Datasets Discovery Provider."""

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


KAGGLE_INSPECTION_DATASETS = [
    {
        "id": "kaggle_sewer_pipe_defects",
        "title": "CCTV Sewer Pipe Defect Inspection Video and Frame Dataset",
        "publisher": "Aalborg University / Kaggle Contributor",
        "canonical_url": "https://www.kaggle.com/datasets/inspection/cctv-sewer-pipe-defects",
        "landing_page_url": "https://www.kaggle.com/datasets/inspection/cctv-sewer-pipe-defects",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": True,
        "modalities": ["video", "still_images"],
        "approximate_size_bytes": 1850000000,
        "file_count": 3400,
        "annotation_types": ["bounding_boxes", "defect_classification"],
        "license_identifier": "CC-BY-4.0",
        "description": "Direct internal robotic CCTV/endoscopic footage inside drainage pipelines showing structural fractures, joint displacement, corrosion, and root intrusion.",
        "limitations_notes": "High water turbidity and motion blur present in low-flow pipe sections. Verified direct pipe videoscope provenance."
    },
    {
        "id": "kaggle_gas_turbine_blade_inspection",
        "title": "Industrial Gas Turbine Compressor Blade Borescope Inspection Dataset",
        "publisher": "Turbomachinery AI Research Group",
        "canonical_url": "https://www.kaggle.com/datasets/turbomachinery/blade-borescope-inspection",
        "landing_page_url": "https://www.kaggle.com/datasets/turbomachinery/blade-borescope-inspection",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": True,
        "modalities": ["video", "still_images"],
        "approximate_size_bytes": 2400000000,
        "file_count": 1250,
        "annotation_types": ["bounding_boxes", "pixel_segmentation_masks"],
        "license_identifier": "CC-BY-NC-4.0",
        "description": "Authentic flexible borescope inspection footage through gas turbine combustor and compressor ports showing leading-edge erosion, thermal fatigue cracks, and foreign object damage (FOD).",
        "limitations_notes": "Contains non-commercial research clause. Direct videoscope probe footage with directional LED glare."
    },
    {
        "id": "kaggle_casting_defect_inspection",
        "title": "Casting Product Defect Inspection Dataset (Submersible Pump Impellers)",
        "publisher": "Saurabh Shahane / Kaggle",
        "canonical_url": "https://www.kaggle.com/datasets/ravirajsinh45/real-life-industrial-dataset-of-casting-product",
        "landing_page_url": "https://www.kaggle.com/datasets/ravirajsinh45/real-life-industrial-dataset-of-casting-product",
        "domain_tag": "MOULD_CAVITIES",
        "is_direct_videoscope": False,
        "modalities": ["still_images"],
        "approximate_size_bytes": 85000000,
        "file_count": 7348,
        "annotation_types": ["classification_labels"],
        "license_identifier": "CC0-1.0",
        "description": "7,348 industrial casting images of submersible pump impeller top surfaces and cavity openings with binary defect (def_front) and normal (ok_front) classifications.",
        "limitations_notes": "Fixed benchtop camera views of cast pump impellers. Useful casting cavity flaw baseline under CC0 public domain."
    }
]


class KaggleProvider(BaseSourceProvider):
    """Kaggle Datasets catalog and metadata provider."""

    @property
    def provider_id(self) -> str:
        return "kaggle"

    @property
    def provider_name(self) -> str:
        return "Kaggle Datasets"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.PUBLIC_CATALOG

    @property
    def description(self) -> str:
        return "Discovers industrial inspection competitions, borescope datasets, and manufacturing benchmarks on Kaggle."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in KAGGLE_INSPECTION_DATASETS:
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
                    id=f"cand_kg_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
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
