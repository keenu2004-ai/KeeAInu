"""Roboflow SAM 3 & Hosted Vision Inference Client Adapter for KeeAInu.

Strictly enforces:
1. Secure credential handling (Backend env vars only, never leaked to client or logs).
2. Transparent error reporting (No fabricated predictions when service is unavailable).
3. Evidence integrity & SHA-256 provenance tracking.
4. Privacy gating (Rejects cloud transmission unless explicitly authorized).
5. Normalized polygon segmentation & bounding box extraction.
"""

import base64
import time
from typing import List, Optional, Dict, Any, Tuple
import httpx

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256
from backend.app.modules.inference.base import (
    BaseInferenceEngine,
    FrameInferenceResult,
    FindingCandidate,
    BoundingBox
)


class RoboflowError(Exception):
    """Base exception for all Roboflow integration errors."""
    pass


class RoboflowAuthError(RoboflowError):
    """Raised when Roboflow API key is missing or unauthorized."""
    pass


class RoboflowTimeoutError(RoboflowError):
    """Raised when inference request times out."""
    pass


class RoboflowApiError(RoboflowError):
    """Raised when Roboflow returns a non-200 status or malformed response."""
    def __init__(self, message: str, status_code: Optional[int] = None, raw_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw_body = raw_body


class RoboflowPrivacyError(RoboflowError):
    """Raised when cloud inference is requested without explicit privacy consent."""
    pass


class RoboflowInferenceEngine(BaseInferenceEngine):
    """
    Dedicated Roboflow adapter for Videoscope Defect Segmentation & SAM 3 workflows.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model_id: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        allow_cloud_inference: Optional[bool] = None
    ):
        self._api_key = api_key
        self._api_url = api_url
        self._model_id = model_id
        self._timeout_seconds = timeout_seconds
        self._allow_cloud_inference = allow_cloud_inference

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or settings.ROBOFLOW_API_KEY

    @property
    def api_url(self) -> str:
        return self._api_url or settings.ROBOFLOW_API_URL

    @property
    def model_id(self) -> str:
        return self._model_id or settings.ROBOFLOW_MODEL_ID

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds if self._timeout_seconds is not None else settings.ROBOFLOW_TIMEOUT_SECONDS

    @property
    def allow_cloud_inference(self) -> bool:
        return self._allow_cloud_inference if self._allow_cloud_inference is not None else settings.ROBOFLOW_ALLOW_CLOUD_INFERENCE

    @property
    def engine_name(self) -> str:
        return "roboflow"

    @property
    def model_version(self) -> str:
        return self.model_id

    @property
    def is_simulated(self) -> bool:
        # Real ML inference model adapter
        return False

    def is_auth_configured(self) -> bool:
        """Check if a valid API key is present."""
        key = self.api_key
        return bool(key and len(key.strip()) > 0)

    async def infer_frame(
        self,
        frame_bytes: bytes,
        frame_index: int,
        timestamp_ms: float,
        confidence_threshold: float = 0.50,
        prompts: Optional[List[str]] = None,
        allow_cloud_override: Optional[bool] = None
    ) -> FrameInferenceResult:
        """
        Execute defect segmentation on frame bytes using Roboflow API.
        """
        start_time = time.perf_counter()
        evidence_hash = calculate_sha256(frame_bytes)

        # 1. Privacy Gate Check
        cloud_permitted = (
            allow_cloud_override
            if allow_cloud_override is not None
            else self.allow_cloud_inference
        )
        if not cloud_permitted:
            raise RoboflowPrivacyError(
                "Privacy Gate Restriction: Cloud inference is disabled. "
                "Explicit operator consent is required to transmit videoscope inspection frames to hosted cloud services."
            )

        # 2. Authentication Check
        if not self.is_auth_configured():
            raise RoboflowAuthError(
                "Roboflow API key is not configured. "
                "Set ROBOFLOW_API_KEY in backend environment variables to enable live Roboflow SAM 3 vision inference."
            )

        # 3. Request Preparation
        prompts_to_use = prompts or settings.ROBOFLOW_SAM_PROMPTS
        b64_image = base64.b64encode(frame_bytes).decode("ascii")

        endpoint_url = f"{self.api_url.rstrip('/')}/{self.model_id.lstrip('/')}"
        params = {
            "api_key": self.api_key,
            "confidence": confidence_threshold,
            "format": "json"
        }

        # 4. HTTP Dispatch with Retry & Timeout Handling
        raw_response_data: Dict[str, Any] = {}
        last_exception: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for attempt in range(settings.ROBOFLOW_MAX_RETRIES + 1):
                try:
                    response = await client.post(
                        endpoint_url,
                        params=params,
                        data=b64_image,
                        headers={"Content-Type": "application/x-www-form-urlencoded"}
                    )

                    if response.status_code in (401, 403):
                        raise RoboflowAuthError(
                            f"Roboflow authentication failed (HTTP {response.status_code}). "
                            "Verify ROBOFLOW_API_KEY and workspace permissions."
                        )

                    if response.status_code != 200:
                        raise RoboflowApiError(
                            f"Roboflow API returned error status {response.status_code}: {response.text[:200]}",
                            status_code=response.status_code,
                            raw_body=response.text
                        )

                    raw_response_data = response.json()
                    break

                except httpx.TimeoutException as te:
                    last_exception = RoboflowTimeoutError(
                        f"Roboflow request timed out after {self._timeout_seconds}s (attempt {attempt + 1})."
                    )
                    if attempt == settings.ROBOFLOW_MAX_RETRIES:
                        raise last_exception
                except httpx.RequestError as re:
                    last_exception = RoboflowApiError(
                        f"Failed to connect to Roboflow inference server: {str(re)}"
                    )
                    if attempt == settings.ROBOFLOW_MAX_RETRIES:
                        raise last_exception

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # 5. Parse & Normalize Response
        return self.parse_roboflow_response(
            raw_data=raw_response_data,
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            evidence_hash=evidence_hash,
            duration_ms=duration_ms,
            confidence_threshold=confidence_threshold,
            prompts_used=prompts_to_use
        )

    def parse_roboflow_response(
        self,
        raw_data: Dict[str, Any],
        frame_index: int,
        timestamp_ms: float,
        evidence_hash: str,
        duration_ms: float,
        confidence_threshold: float = 0.50,
        prompts_used: Optional[List[str]] = None
    ) -> FrameInferenceResult:
        """
        Parse and normalize Roboflow prediction dictionary into standard FrameInferenceResult.
        Handles both center-based boxes and segmentation polygon points.
        """
        image_meta = raw_data.get("image", {})
        img_w = float(image_meta.get("width", 1.0)) or 1.0
        img_h = float(image_meta.get("height", 1.0)) or 1.0

        predictions_list = raw_data.get("predictions", [])
        findings: List[FindingCandidate] = []

        for p in predictions_list:
            conf = float(p.get("confidence", 0.0))
            if conf < confidence_threshold:
                continue

            defect_class = p.get("class") or p.get("label") or "DEFECT"

            # Parse bounding box coordinates
            # Roboflow hosted inference standard: x, y (center), width, height in pixels
            if "x" in p and "y" in p and "width" in p and "height" in p:
                cx, cy, bw, bh = float(p["x"]), float(p["y"]), float(p["width"]), float(p["height"])
                x_min = max(0.0, min(1.0, (cx - bw / 2.0) / img_w))
                y_min = max(0.0, min(1.0, (cy - bh / 2.0) / img_h))
                x_max = max(0.0, min(1.0, (cx + bw / 2.0) / img_w))
                y_max = max(0.0, min(1.0, (cy + bh / 2.0) / img_h))
            elif "bbox" in p:
                b = p["bbox"]
                x_min, y_min = float(b.get("x_min", 0.0)), float(b.get("y_min", 0.0))
                x_max, y_max = float(b.get("x_max", 1.0)), float(b.get("y_max", 1.0))
            else:
                x_min, y_min, x_max, y_max = 0.0, 0.0, 1.0, 1.0

            bbox = BoundingBox(
                x_min=round(x_min, 4),
                y_min=round(y_min, 4),
                x_max=round(x_max, 4),
                y_max=round(y_max, 4)
            )

            # Parse segmentation polygon points
            polygon_mask: Optional[List[List[float]]] = None
            if "points" in p and isinstance(p["points"], list) and len(p["points"]) >= 3:
                norm_points = []
                for pt in p["points"]:
                    if isinstance(pt, dict) and "x" in pt and "y" in pt:
                        px = float(pt["x"]) / img_w if float(pt["x"]) > 1.0 else float(pt["x"])
                        py = float(pt["y"]) / img_h if float(pt["y"]) > 1.0 else float(pt["y"])
                        norm_points.append([round(max(0.0, min(1.0, px)), 4), round(max(0.0, min(1.0, py)), 4)])
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        px = float(pt[0]) / img_w if float(pt[0]) > 1.0 else float(pt[0])
                        py = float(pt[1]) / img_h if float(pt[1]) > 1.0 else float(pt[1])
                        norm_points.append([round(max(0.0, min(1.0, px)), 4), round(max(0.0, min(1.0, py)), 4)])
                if len(norm_points) >= 3:
                    polygon_mask = norm_points

            findings.append(
                FindingCandidate(
                    defect_class=defect_class,
                    confidence_score=round(conf, 4),
                    bbox=bbox,
                    polygon_mask=polygon_mask,
                    metadata={
                        "raw_prediction": p,
                        "class_id": p.get("class_id"),
                        "detection_id": p.get("detection_id")
                    }
                )
            )

        return FrameInferenceResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            engine_name=self.engine_name,
            model_version=self.model_version,
            is_simulated=False,
            findings=findings,
            processing_duration_ms=round(duration_ms, 2),
            evidence_sha256=evidence_hash,
            cache_hit=False,
            image_width=int(img_w) if img_w > 1.0 else None,
            image_height=int(img_h) if img_h > 1.0 else None,
            prompts_used=prompts_used or [],
            raw_response=raw_data
        )
