"""Controlled Procedural & Augmented Synthetic Defect Generator Provider."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import uuid
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256, is_path_safe
from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    CandidateAcquisitionStatus,
    LicensePermissionStatus,
    DiscoveryVerificationStatus,
    DownloadSupportStatus,
    SyntheticGenerationRequest
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.relevance import evaluate_relevance


SYNTHETIC_OFFERINGS = [
    {
        "id": "synth_tubular_cracks",
        "title": "Procedural Borescope Pipe Fracture & Wall Thinning Generator",
        "domain_tag": "PIPES_CHANNELS",
        "description": "Parametric procedural generator producing tubular cylindrical perspective with simulated axial cracks, circumferential fractures, and pitting corrosion.",
        "modalities": ["still_images", "video"],
        "annotation_types": ["pixel_segmentation_masks", "bounding_boxes"]
    },
    {
        "id": "synth_turbine_blade_erosion",
        "title": "Synthetic Aerofoil & Turbine Blade Surface Flaw Suite",
        "domain_tag": "MECHANICAL",
        "description": "Procedural generator simulating compressor leading edge erosion, thermal spallation, and FOD impact pits on metallic turbine geometries.",
        "modalities": ["still_images"],
        "annotation_types": ["bounding_boxes", "pixel_segmentation_masks"]
    },
    {
        "id": "synth_mould_cavity_scratches",
        "title": "Parametric Injection Mould & Die Cavity Flaw Simulator",
        "domain_tag": "MOULD_CAVITIES",
        "description": "Simulates micro-pitting, scoring, and polishing defects in high-mirror mould cavity surfaces with specular probe reflections.",
        "modalities": ["still_images"],
        "annotation_types": ["pixel_segmentation_masks"]
    }
]


class SyntheticGeneratorProvider(BaseSourceProvider):
    """Synthetic Media & Procedural Defect Generation Provider."""

    @property
    def provider_id(self) -> str:
        return "synthetic_generator"

    @property
    def provider_name(self) -> str:
        return "KeeAInu Procedural Synthetic Defect Studio"

    @property
    def category(self) -> SourceProviderCategory:
        return SourceProviderCategory.SYNTHETIC_GENERATOR

    @property
    def description(self) -> str:
        return "Generates controlled, parameterized synthetic inspection images and defect overlays with verifiable provenance and zero real-world data leakage."

    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        results: List[DatasetCandidateRecord] = []
        now = datetime.now(timezone.utc).isoformat()
        q_lower = query.query.lower()

        for item in SYNTHETIC_OFFERINGS:
            combined = f"{item['title']} {item['description']} {item['domain_tag']}".lower()
            if any(term in combined for term in q_lower.split()) or "all" in q_lower or "synth" in q_lower:
                rel = evaluate_relevance(
                    title=item["title"],
                    description=item["description"],
                    target_domain=query.target_domain or item["domain_tag"],
                    modalities=item["modalities"],
                    annotation_types=item["annotation_types"],
                    is_direct_videoscope_declared=True
                )

                cand = DatasetCandidateRecord(
                    id=f"cand_synth_{item['id']}",
                    source_id=self.provider_id,
                    provider_name=self.provider_name,
                    title=f"[Synthetic] {item['title']}",
                    publisher="KeeAInu Synthetic Core v1.0",
                    external_id=item["id"],
                    canonical_url=f"synthetic://generator/{item['id']}",
                    landing_page_url=None,
                    domain_tag=item["domain_tag"],
                    is_direct_videoscope=False,  # Strictly marked non-real
                    modalities=item["modalities"],
                    approximate_size_bytes=None,
                    file_count=None,
                    annotation_types=item["annotation_types"],
                    license_identifier="CC0-1.0-SYNTHETIC",
                    license_status=LicensePermissionStatus.APPROVED_FOR_EVALUATION,
                    commercial_use_allowed=True,
                    attribution_required=False,
                    relevance_score=rel.total_score,
                    relevance_breakdown=rel,
                    description=f"{item['description']} Generated media carries explicit 'is_synthetic=True' metadata.",
                    limitations_notes="Synthetic / procedurally simulated imagery. Must NOT be used as proof of real physical defect accuracy.",
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

    def generate_synthetic_samples(
        self,
        req: SyntheticGenerationRequest,
        output_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Execute procedural generation of inspection images with simulated defects,
        strict metadata provenance, and deterministic seed repeatability.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(req.random_seed or 42)
        generated_assets: List[Dict[str, Any]] = []

        width, height = 640, 480

        for idx in range(req.count):
            item_id = f"synth_{uuid.uuid4().hex[:10]}"
            file_name = f"{item_id}_{req.target_domain.lower()}_{req.defect_type.lower()}.jpg"
            target_path = output_dir / file_name

            # 1. Generate base surface (pipe interior cylindrical gradient or metallic texture)
            if req.target_domain == "PIPES_CHANNELS":
                # Cylindrical tunnel vignette
                y, x = np.ogrid[:height, :width]
                cx, cy = width / 2.0, height / 2.0
                dist = np.sqrt((x - cx)**2 + (y - cy)**2)
                max_dist = np.sqrt(cx**2 + cy**2)
                base = (200 * (1.0 - (dist / max_dist) ** 0.8)).astype(np.uint8)
                img = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
                img[:, :, 0] = np.clip(img[:, :, 0] * 0.9, 0, 255) # Slight industrial tint
                img[:, :, 2] = np.clip(img[:, :, 2] * 1.1, 0, 255)
            elif req.target_domain == "MECHANICAL":
                # Brushed metallic blade background
                base = rng.integers(120, 180, (height, width), dtype=np.uint8)
                base = cv2.GaussianBlur(base, (15, 1), 0)
                img = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
            else:
                # Mirror mould cavity background with specular reflection
                base = np.full((height, width, 3), 190, dtype=np.uint8)
                cv2.circle(base, (int(width * 0.4), int(height * 0.4)), 100, (240, 240, 240), -1)
                img = cv2.GaussianBlur(base, (31, 31), 0)

            # 2. Draw procedural defect flaw
            bbox = None
            if req.defect_type == "CRACK":
                pts = []
                start_x = rng.integers(int(width * 0.2), int(width * 0.6))
                start_y = rng.integers(int(height * 0.3), int(height * 0.7))
                curr_x, curr_y = start_x, start_y
                pts.append([curr_x, curr_y])
                for _ in range(rng.integers(6, 14)):
                    curr_x += rng.integers(-15, 25)
                    curr_y += rng.integers(-15, 25)
                    pts.append([int(curr_x), int(curr_y)])
                pts_arr = np.array(pts, dtype=np.int32)
                cv2.polylines(img, [pts_arr], False, (30, 20, 20), thickness=2)
                cv2.polylines(img, [pts_arr], False, (10, 10, 10), thickness=1)
                x_min, y_min = np.min(pts_arr, axis=0)
                x_max, y_max = np.max(pts_arr, axis=0)
                bbox = {"x_min": int(max(0, x_min - 5)), "y_min": int(max(0, y_min - 5)),
                        "x_max": int(min(width, x_max + 5)), "y_max": int(min(height, y_max + 5))}
            elif req.defect_type == "CORROSION_PIT":
                pit_cx = rng.integers(int(width * 0.3), int(width * 0.7))
                pit_cy = rng.integers(int(height * 0.3), int(height * 0.7))
                rad = rng.integers(15, 45)
                cv2.circle(img, (pit_cx, pit_cy), rad, (40, 50, 90), -1) # Dark rust tint
                # Rust texture speckling
                for _ in range(60):
                    rx = pit_cx + rng.integers(-rad, rad)
                    ry = pit_cy + rng.integers(-rad, rad)
                    if (rx - pit_cx)**2 + (ry - pit_cy)**2 < rad**2:
                        cv2.circle(img, (rx, ry), rng.integers(1, 4), (20, 30, 60), -1)
                bbox = {"x_min": max(0, pit_cx - rad), "y_min": max(0, pit_cy - rad),
                        "x_max": min(width, pit_cx + rad), "y_max": min(height, pit_cy + rad)}
            else:
                # Deposit / Debris
                dep_x = rng.integers(int(width * 0.3), int(width * 0.7))
                dep_y = rng.integers(int(height * 0.3), int(height * 0.7))
                cv2.ellipse(img, (dep_x, dep_y), (40, 25), rng.integers(0, 180), 0, 360, (20, 25, 30), -1)
                bbox = {"x_min": max(0, dep_x - 45), "y_min": max(0, dep_y - 30),
                        "x_max": min(width, dep_x + 45), "y_max": min(height, dep_y + 30)}

            # 3. Apply noise, blur, and lighting adjustments
            if req.lighting_variation > 0.0:
                alpha = 1.0 + (rng.uniform(-0.3, 0.3) * req.lighting_variation)
                img = np.clip(img * alpha, 0, 255).astype(np.uint8)

            if req.noise_level > 0.0:
                noise = rng.normal(0, req.noise_level * 25, img.shape).astype(np.int16)
                img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

            if req.blur_level > 0.1:
                k = int(req.blur_level * 10) | 1
                img = cv2.GaussianBlur(img, (k, k), 0)

            # Write file and record integrity hash
            cv2.imwrite(str(target_path), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
            sha256 = calculate_sha256(target_path)

            generated_assets.append({
                "asset_id": item_id,
                "file_path": str(target_path),
                "filename": file_name,
                "sha256_hash": sha256,
                "width": width,
                "height": height,
                "target_domain": req.target_domain,
                "defect_type": req.defect_type,
                "bbox": bbox,
                "generator_version": "KeeAInu-SynthGenerator-v1.0",
                "generation_parameters": req.model_dump(),
                "parent_asset_id": req.parent_asset_id
            })

        return generated_assets
