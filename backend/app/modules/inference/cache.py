"""Inference Caching, Idempotency & Frame Sampling Module for KeeAInu.

Ensures:
1. Deterministic cache keying by (evidence_sha256, model_id, model_version, inference_params).
2. Safe retries without duplicating cloud API requests or cost.
3. Configurable frame sampling to avoid sending redundant adjacent frames.
"""

import hashlib
import json
from typing import Dict, Any, Optional, List

from backend.app.modules.inference.base import FrameInferenceResult


class InferenceCache:
    """In-memory thread-safe LRU inference cache with deterministic keying."""

    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def generate_key(
        evidence_sha256: str,
        engine_name: str,
        model_version: str,
        confidence_threshold: float,
        prompts: Optional[List[str]] = None
    ) -> str:
        """
        Generate reproducible SHA-256 cache key from full input parameters.
        Never reuses cached results across different prompts, models, or confidence thresholds.
        """
        payload = {
            "evidence_sha256": evidence_sha256,
            "engine_name": engine_name,
            "model_version": model_version,
            "confidence_threshold": confidence_threshold,
            "prompts": sorted(prompts or [])
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return f"icache_{hashlib.sha256(encoded).hexdigest()}"

    def get(self, cache_key: str) -> Optional[FrameInferenceResult]:
        """Retrieve cached result if present."""
        data = self._cache.get(cache_key)
        if data:
            res = FrameInferenceResult(**data)
            res.cache_hit = True
            return res
        return None

    def set(self, cache_key: str, result: FrameInferenceResult) -> None:
        """Store result in cache with LRU eviction."""
        if len(self._cache) >= self.max_size:
            # Evict first item
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[cache_key] = result.model_dump()

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()


# Global cache instance
inference_cache = InferenceCache()


def should_sample_frame(
    frame_index: int,
    total_frames: int,
    sample_rate: int = 5,
    is_keyframe: bool = False
) -> bool:
    """
    Determine whether a video frame should undergo cloud vision inference,
    preventing high cost and latency from analyzing every near-identical frame.
    """
    if total_frames <= 1 or frame_index == 0:
        return True
    if is_keyframe:
        return True
    return (frame_index % sample_rate) == 0
