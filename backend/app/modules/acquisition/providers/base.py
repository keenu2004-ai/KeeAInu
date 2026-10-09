"""Base Source Provider Interface for Multi-Source Dataset Discovery."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from backend.app.schemas.acquisition import (
    DatasetCandidateRecord,
    SearchCandidateQuery,
    SourceProviderCategory,
    SourceProviderInfo
)


class BaseSourceProvider(ABC):
    """Abstract interface for all dataset catalog and discovery providers."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique provider identifier (e.g., 'huggingface', 'kaggle', 'internal_storage')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def category(self) -> SourceProviderCategory:
        """Provider category classification."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Provider description and scope."""
        pass

    def get_info(self) -> SourceProviderInfo:
        """Get structured provider metadata."""
        return SourceProviderInfo(
            id=self.provider_id,
            name=self.provider_name,
            category=self.category,
            description=self.description,
            is_enabled=True,
            auth_configured=False,
            rate_limit_per_min=60
        )

    @abstractmethod
    async def search(self, query: SearchCandidateQuery) -> List[DatasetCandidateRecord]:
        """
        Execute rate-limited, safe discovery search against the source catalog or internal store.
        """
        pass

    @abstractmethod
    async def get_candidate_details(self, candidate_id: str) -> Optional[DatasetCandidateRecord]:
        """
        Retrieve complete metadata and provenance card for a specific discovered candidate.
        """
        pass
