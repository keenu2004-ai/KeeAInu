"""Provider Registry and Multi-Source Search Orchestration."""

from typing import Dict, List, Optional
from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderInfo
)
from backend.app.modules.acquisition.providers.base import BaseSourceProvider
from backend.app.modules.acquisition.providers.huggingface import HuggingFaceProvider
from backend.app.modules.acquisition.providers.kaggle import KaggleProvider
from backend.app.modules.acquisition.providers.google_dataset import GoogleDatasetSearchProvider
from backend.app.modules.acquisition.providers.datagov import DataGovProvider
from backend.app.modules.acquisition.providers.aws_opendata import AwsOpenDataProvider
from backend.app.modules.acquisition.providers.github_research import GitHubResearchProvider
from backend.app.modules.acquisition.providers.internal_storage import InternalStorageProvider
from backend.app.modules.acquisition.providers.synthetic_generator import SyntheticGeneratorProvider


class ProviderRegistry:
    """Central registry of all discovery and acquisition providers."""

    def __init__(self):
        self._providers: Dict[str, BaseSourceProvider] = {}
        self._register_default_providers()

    def _register_default_providers(self):
        default_instances = [
            HuggingFaceProvider(),
            KaggleProvider(),
            GoogleDatasetSearchProvider(),
            DataGovProvider(),
            AwsOpenDataProvider(),
            GitHubResearchProvider(),
            InternalStorageProvider(),
            SyntheticGeneratorProvider()
        ]
        for p in default_instances:
            self._providers[p.provider_id] = p

    def list_providers(self) -> List[SourceProviderInfo]:
        """List all registered discovery providers."""
        return [p.get_info() for p in self._providers.values()]

    def get_provider(self, provider_id: str) -> Optional[BaseSourceProvider]:
        """Retrieve a specific provider by ID."""
        return self._providers.get(provider_id)

    async def search_all(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        """
        Execute parallel or aggregate search across all selected providers.
        """
        active_providers = []
        if query.provider_ids:
            for pid in query.provider_ids:
                if pid in self._providers:
                    active_providers.append(self._providers[pid])
        else:
            active_providers = list(self._providers.values())

        aggregated_results: List[DatasetCandidateRecord] = []
        for prov in active_providers:
            try:
                prov_results = await prov.search(query)
                aggregated_results.extend(prov_results)
            except Exception:
                # Isolate individual provider failures
                continue

        # Sort aggregated results by relevance score descending
        aggregated_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return aggregated_results


provider_registry = ProviderRegistry()
