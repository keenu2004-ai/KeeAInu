"""Local Offline ONNX Defect Detection Inference Engine.

Designed for KeeAInu's independent local AI pipeline:
- Zero external cloud or SaaS dependencies (completely offline).
- Strictly verified preprocessing (letterboxing, normalization, NCHW formatting).
- Strictly verified postprocessing (un-letterboxing, confidence filtering, NMS).
- Explicit, actionable errors when weights file is missing.
- Transparent is_simulated=False real ML detection contract.
"""

from datetime import datetime, timezone
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import cv2
import numpy as np

from backend.app.core.config import settings
from backend.app.core.security import calculate_sha256
from backend.app.modules.inference.base import (
    BaseInferenceEngine,
    BoundingBox,
    FindingCandidate,
    FrameInferenceResult
)
from backend.app.schemas.taxonomy import DefectCategory


class LocalModelError(Exception):
    """Base exception for local offline model execution."""
    pass


class LocalModelNotFoundError(LocalModelError):
    """Raised when the local model weights file does not exist."""
    pass


class LocalInferenceRuntimeError(LocalModelError):
    """Raised when the ONNX runtime environment fails to execute the model."""
    pass


DEFAULT_MODEL_CLASSES = [
    DefectCategory.CRACK.value,
    DefectCategory.CORROSION.value,
    DefectCategory.PITTING.value,
    DefectCategory.WEAR.value,
    DefectCategory.CHIPPING_FRACTURE.value,
    DefectCategory.DEFORMATION.value,
    DefectCategory.EROSION.value,
    DefectCategory.SCORING_SCRATCH.value
]


class LocalOnnxInferenceEngine(BaseInferenceEngine):
    """
    Offline local defect detection engine executing ONNX models.
    Decoupled from cloud services and fully testable with mock/synthetic tensors.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        model_version: str = "1.0.0-offline",
        class_names: Optional[List[str]] = None,
        input_size: Tuple[int, int] = (640, 640)
    ):
        self._model_path = Path(
            model_path or (settings.DATA_DIR / "models" / "keeainu_defect_detector.onnx")
        ).resolve()
        self._model_version = model_version
        self._class_names = class_names or list(DEFAULT_MODEL_CLASSES)
        self._input_size = input_size
        self._session = None

    @property
    def engine_name(self) -> str:
        return "onnx_local"

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def is_simulated(self) -> bool:
        """Local ONNX engine represents real machine learning inference, not simulated data."""
        return False

    @property
    def model_path(self) -> Path:
        return self._model_path

    def is_auth_configured(self) -> bool:
        """Local engine requires zero cloud API keys or external authentication."""
        return True

    def is_model_present(self) -> bool:
        """Returns True if local model weights file is present on the filesystem."""
        return self._model_path.is_file()

    def letterbox(
        self,
        image: np.ndarray,
        target_size: Tuple[int, int] = (640, 640),
        color: Tuple[int, int, int] = (114, 114, 114)
    ) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Resize image and pad to target_size while strictly preserving aspect ratio.
        Returns: (padded_image, scale_factor, (pad_w, pad_h)).
        """
        shape = image.shape[:2]  # [height, width]
        target_w, target_h = target_size

        r = min(target_w / shape[1], target_h / shape[0])
        new_unpad = (int(round(shape[1] * r)), int(round(shape[0] * r)))

        dw = target_w - new_unpad[0]
        dh = target_h - new_unpad[1]

        dw_half = dw // 2
        dh_half = dh // 2

        if shape[::-1] != new_unpad:
            resized = cv2.resize(image, new_unpad, interpolation=cv2.INTER_LINEAR)
        else:
            resized = image.copy()

        top = dh_half
        bottom = dh - dh_half
        left = dw_half
        right = dw - dw_half

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right,
            cv2.BORDER_CONSTANT, value=color
        )
        return padded, r, (left, top)

    def preprocess(
        self,
        frame_bytes: bytes,
        target_size: Optional[Tuple[int, int]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Deterministic preprocessing pipeline:
        1. Decodes raw bytes to BGR image.
        2. Letterboxes to target_size (preserving aspect ratio with padding).
        3. Converts BGR to RGB.
        4. Normalizes pixel values from [0, 255] to [0.0, 1.0].
        5. Formats to NCHW batch tensor (1, 3, H, W) float32.
        """
        if not frame_bytes:
            raise ValueError("Empty frame bytes provided to preprocessor.")

        arr = np.frombuffer(frame_bytes, np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Failed to decode frame bytes into image buffer.")

        orig_h, orig_w = image.shape[:2]
        size = target_size or self._input_size

        padded, scale, (pad_w, pad_h) = self.letterbox(image, target_size=size)

        # BGR -> RGB
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)

        # Normalize to [0.0, 1.0] and transpose to CHW
        tensor = rgb.astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))  # (3, H, W)
        tensor = np.expand_dims(tensor, axis=0)  # (1, 3, H, W)

        meta = {
            "orig_w": orig_w,
            "orig_h": orig_h,
            "target_w": size[0],
            "target_h": size[1],
            "scale": scale,
            "pad_w": pad_w,
            "pad_h": pad_h
        }
        return tensor, meta

    def nms(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        iou_threshold: float = 0.45
    ) -> List[int]:
        """
        Greedy Non-Maximum Suppression (NMS) over normalized boxes.
        boxes: shape (N, 4) in format [x1, y1, x2, y2]
        scores: shape (N,)
        """
        if len(boxes) == 0:
            return []

        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]

        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]

        keep: List[int] = []
        while order.size > 0:
            i = int(order[0])
            keep.append(i)

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            union = areas[i] + areas[order[1:]] - inter
            iou = np.where(union > 0, inter / union, 0.0)

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]

        return keep

    def postprocess(
        self,
        raw_output: np.ndarray,
        meta: Dict[str, Any],
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45
    ) -> List[FindingCandidate]:
        """
        Decodes raw model output tensor, applies un-letterboxing,
        confidence thresholding, and Non-Maximum Suppression (NMS).
        Supports output shape (1, 4 + num_classes, num_anchors) or (1, num_anchors, 4 + num_classes).
        """
        # Ensure 2D (num_anchors, 4 + num_classes)
        preds = np.squeeze(raw_output)
        if preds.ndim != 2:
            raise ValueError(f"Expected 2D or 3D prediction tensor, got shape {raw_output.shape}")

        num_classes = len(self._class_names)
        if preds.shape[0] == (4 + num_classes) and preds.shape[1] != (4 + num_classes):
            # Transpose (4 + nc, anchors) -> (anchors, 4 + nc)
            preds = preds.T

        if preds.shape[1] < 4 + num_classes:
            raise ValueError(
                f"Output tensor channels ({preds.shape[1]}) fewer than 4 coords + {num_classes} classes."
            )

        boxes_cxcywh = preds[:, :4]
        class_scores = preds[:, 4:4 + num_classes]

        best_class_ids = np.argmax(class_scores, axis=1)
        best_scores = class_scores[np.arange(len(class_scores)), best_class_ids]

        # Filter by confidence threshold
        mask = best_scores >= confidence_threshold
        if not np.any(mask):
            return []

        filtered_boxes = boxes_cxcywh[mask]
        filtered_scores = best_scores[mask]
        filtered_classes = best_class_ids[mask]

        # Convert cx, cy, w, h -> x1, y1, x2, y2 in letterbox pixel coords
        scale = meta["scale"]
        pad_w = meta["pad_w"]
        pad_h = meta["pad_h"]
        orig_w = meta["orig_w"]
        orig_h = meta["orig_h"]

        cx = filtered_boxes[:, 0]
        cy = filtered_boxes[:, 1]
        w = filtered_boxes[:, 2]
        h = filtered_boxes[:, 3]

        x1_pad = cx - w / 2.0
        y1_pad = cy - h / 2.0
        x2_pad = cx + w / 2.0
        y2_pad = cy + h / 2.0

        # Un-pad and restore to original image scale
        x1_orig = (x1_pad - pad_w) / scale
        y1_orig = (y1_pad - pad_h) / scale
        x2_orig = (x2_pad - pad_w) / scale
        y2_orig = (y2_pad - pad_h) / scale

        # Normalize to [0.0, 1.0]
        norm_x1 = np.clip(x1_orig / orig_w, 0.0, 1.0)
        norm_y1 = np.clip(y1_orig / orig_h, 0.0, 1.0)
        norm_x2 = np.clip(x2_orig / orig_w, 0.0, 1.0)
        norm_y2 = np.clip(y2_orig / orig_h, 0.0, 1.0)

        # Enforce valid box dimensions
        valid_box_mask = (norm_x2 > norm_x1) & (norm_y2 > norm_y1)
        if not np.any(valid_box_mask):
            return []

        norm_boxes = np.column_stack([norm_x1, norm_y1, norm_x2, norm_y2])[valid_box_mask]
        final_scores = filtered_scores[valid_box_mask]
        final_classes = filtered_classes[valid_box_mask]

        # Non-Maximum Suppression
        keep_indices = self.nms(norm_boxes, final_scores, iou_threshold=iou_threshold)

        candidates: List[FindingCandidate] = []
        for idx in keep_indices:
            cls_idx = int(final_classes[idx])
            cls_name = self._class_names[cls_idx] if cls_idx < len(self._class_names) else "UNKNOWN_DEFECT"
            score = float(round(float(final_scores[idx]), 4))

            bx = norm_boxes[idx]
            bbox = BoundingBox(
                x_min=float(round(bx[0], 4)),
                y_min=float(round(bx[1], 4)),
                x_max=float(round(bx[2], 4)),
                y_max=float(round(bx[3], 4))
            )
            candidates.append(
                FindingCandidate(
                    defect_class=cls_name,
                    confidence_score=score,
                    bbox=bbox,
                    metadata={
                        "engine": self.engine_name,
                        "class_index": cls_idx,
                        "nms_retained": True
                    }
                )
            )

        return candidates

    async def infer_frame(
        self,
        frame_bytes: bytes,
        frame_index: int,
        timestamp_ms: float,
        confidence_threshold: float = 0.5
    ) -> FrameInferenceResult:
        """
        Executes offline defect candidate detection on a single frame.
        Fails with clear, actionable guidance if model weights are not present.
        """
        start_time = time.perf_counter()

        if not self.is_model_present():
            raise LocalModelNotFoundError(
                f"Local defect detector model weights not found at '{self._model_path}'. "
                f"KeeAInu requires a locally trained ONNX model for offline inference. "
                f"To train a model, export human-verified inspection annotations via "
                f"'/api/v1/evaluation/datasets/export' and place the trained model weights at '{self._model_path}'."
            )

        evidence_sha256 = calculate_sha256(frame_bytes)

        # Lazy load ONNX runtime session
        try:
            import onnxruntime as ort  # type: ignore
        except ImportError:
            raise LocalInferenceRuntimeError(
                "onnxruntime is not installed. To execute local ONNX model inferences offline, "
                "install onnxruntime in your Python environment."
            )

        if self._session is None:
            try:
                self._session = ort.InferenceSession(
                    str(self._model_path),
                    providers=["CPUExecutionProvider"]
                )
            except Exception as e:
                raise LocalInferenceRuntimeError(f"Failed to load ONNX model session: {e}")

        tensor, meta = self.preprocess(frame_bytes)
        input_name = self._session.get_inputs()[0].name

        try:
            raw_outputs = self._session.run(None, {input_name: tensor})
        except Exception as e:
            raise LocalInferenceRuntimeError(f"ONNX inference execution failed: {e}")

        findings = self.postprocess(
            raw_outputs[0],
            meta=meta,
            confidence_threshold=confidence_threshold
        )
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return FrameInferenceResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            engine_name=self.engine_name,
            model_version=self.model_version,
            is_simulated=False,
            findings=findings,
            processing_duration_ms=duration_ms,
            evidence_sha256=evidence_sha256,
            cache_hit=False,
            image_width=meta["orig_w"],
            image_height=meta["orig_h"],
            prompts_used=[],
            raw_response={"detections_count": len(findings)}
        )
