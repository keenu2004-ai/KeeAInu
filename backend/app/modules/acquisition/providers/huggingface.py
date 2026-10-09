"""Hugging Face Datasets Discovery Provider."""

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


# Curated catalog entries for industrial inspection and borescope benchmarking on Hugging Face
HF_INSPECTION_DATASETS = [
    {
        "id": "hf_mvtec_ad",
        "title": "MVTec Anomaly Detection Dataset (Industrial Anomaly Benchmark)",
        "publisher": "MVTec Software GmbH",
        "canonical_url": "https://huggingface.co/datasets/MVTec/anomaly-detection",
        "landing_page_url": "https://www.mvtec.com/company/research/datasets/mvtec-ad",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": False,
        "modalities": ["still_images", "high_resolution_rgb"],
        "approximate_size_bytes": 5200000000,
        "file_count": 5354,
        "annotation_types": ["pixel_segmentation_masks", "anomaly_classification"],
        "license_identifier": "CC-BY-NC-SA-4.0",
        "description": "5,354 high-resolution industrial images across 15 structural and object classes (screws, metal nuts, pipes, grids) with pixel-accurate ground truth for defect segmentation.",
        "limitations_notes": "Captured under controlled studio benchtop lighting; not recorded through flexible industrial borescopes. Non-commercial license."
    },
    {
        "id": "hf_crack500",
        "title": "CRACK500 Road and Concrete Structural Defect Dataset",
        "publisher": "Temple University / CVPR",
        "canonical_url": "https://huggingface.co/datasets/keremberke/crack-segmentation",
        "landing_page_url": "https://huggingface.co/datasets/keremberke/crack-segmentation",
        "domain_tag": "PIPES_CHANNELS",
        "is_direct_videoscope": False,
        "modalities": ["still_images"],
        "approximate_size_bytes": 450000000,
        "file_count": 500,
        "annotation_types": ["pixel_segmentation_masks"],
        "license_identifier": "MIT",
        "description": "Pixel-level crack annotations for industrial structure surfaces, wall fractures, and channel lining inspections.",
        "limitations_notes": "Surface masonry/concrete cracks; useful transfer representation for pipeline inner-wall fracture segmentation."
    },
    {
        "id": "hf_industrial_surface_flaws",
        "title": "NEU Surface Defect Database (Hot-Rolled Steel Strips)",
        "publisher": "Northeastern University",
        "canonical_url": "https://huggingface.co/datasets/industrial-vision/neu-surface-defects",
        "landing_page_url": "https://huggingface.co/datasets/industrial-vision/neu-surface-defects",
        "domain_tag": "MECHANICAL",
        "is_direct_videoscope": False,
        "modalities": ["still_images", "grayscale"],
        "approximate_size_bytes": 120000000,
        "file_count": 1800,
        "annotation_types": ["bounding_boxes", "defect_classification"],
        "license_identifier": "CC-BY-4.0",
        "description": "1,800 images covering six common industrial steel surface defects: rolled-in scale, patches, crazing, pitted surface, inclusion and scratches.",
        "limitations_notes": "Flat steel strip textures. Cross-domain transfer reference for metallic pitting and scratches."
    }
]


class HuggingFaceProvider(BaseSourceProvider):
    """Hugging Face Datasets catalog and metadata provider."""

    @property
    def provider_id(self) -> str:
        return "huggingface"

    @property
    def provider_name(self) -> str:
        return "Hugging Face Datasets"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.PUBLIC_CATALOG

    @property
    def description(self) -> str:
        return "Discovers open computer vision datasets, dataset cards, and defect benchmarks on Hugging Face."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        q_lower = query.query.lower()
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()

        for item in HF_INSPECTION_DATASETS:
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
                    id=f"cand_hf_{uuid.uuid5(uuid.NAMESPACE_URL, item['canonical_url']).hex[:10]}",
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
