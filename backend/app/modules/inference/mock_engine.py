"""Deterministic Mock Defect Inference Engine for Testing and Workflows."""

from backend.app.modules.inference.base import (
    BaseInferenceEngine,
    FrameInferenceResult,
    FindingCandidate,
    BoundingBox
)


class MockInferenceEngine(BaseInferenceEngine):
    """
    Mock inference engine providing deterministic defect predictions
    for automated tests and offline pipeline validation.
    
    CRITICAL: is_simulated is explicitly True.
    """
    
    @property
    def engine_name(self) -> str:
        return "DeterministicMockEngine"
        
    @property
    def model_version(self) -> str:
        return "v1.0.0-mock"
        
    @property
    def is_simulated(self) -> bool:
        return True

    async def infer_frame(
        self,
        frame_bytes: bytes,
        frame_index: int,
        timestamp_ms: float,
        confidence_threshold: float = 0.5
    ) -> FrameInferenceResult:
        findings = []
        
        # Deterministic simulation rule: generate a candidate on odd frame indices
        if frame_index % 2 == 1:
            confidence = 0.88
            if confidence >= confidence_threshold:
                findings.append(
                    FindingCandidate(
                        defect_class="CRACK",
                        confidence_score=confidence,
                        bbox=BoundingBox(
                            x_min=0.25,
                            y_min=0.30,
                            x_max=0.65,
                            y_max=0.45
                        ),
                        metadata={"synthetic_flag": True, "test_rule": "odd_frame_crack"}
                    )
                )

        return FrameInferenceResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            engine_name=self.engine_name,
            model_version=self.model_version,
            is_simulated=self.is_simulated,
            findings=findings
        )
