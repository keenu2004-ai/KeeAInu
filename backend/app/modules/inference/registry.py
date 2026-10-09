"""Inference Engine Registry and Factory for KeeAInu.

Provides decoupled, pluggable engine lookup (Mock vs Roboflow vs Local).
"""

from typing import Dict, Optional, List, Any
from backend.app.modules.inference.base import BaseInferenceEngine
from backend.app.modules.inference.mock_engine import MockInferenceEngine
from backend.app.modules.inference.roboflow_client import RoboflowInferenceEngine


class InferenceEngineRegistry:
    """Registry maintaining active AI vision engines."""

    def __init__(self):
        self._engines: Dict[str, BaseInferenceEngine] = {}
        mock = MockInferenceEngine()
        rf = RoboflowInferenceEngine()
        self.register(mock, aliases=["mock", "deterministicmockengine"])
        self.register(rf, aliases=["roboflow", "sam3"])

    def register(self, engine: BaseInferenceEngine, aliases: Optional[List[str]] = None) -> None:
        self._engines[engine.engine_name.lower()] = engine
        if aliases:
            for alias in aliases:
                self._engines[alias.lower()] = engine

    def get_engine(self, engine_name: str) -> Optional[BaseInferenceEngine]:
        return self._engines.get(engine_name.lower())

    def list_engines(self) -> List[Dict[str, Any]]:
        seen = set()
        results = []
        for eng in self._engines.values():
            if eng.engine_name in seen:
                continue
            seen.add(eng.engine_name)
            results.append({
                "engine_name": "mock" if eng.is_simulated else eng.engine_name,
                "display_name": eng.engine_name,
                "model_version": eng.model_version,
                "is_simulated": eng.is_simulated,
                "auth_configured": getattr(eng, "is_auth_configured", lambda: True)()
            })
        return results


engine_registry = InferenceEngineRegistry()

