"""Unit tests for Multi-Source Dataset Discovery Providers and Registry."""

import pytest
from backend.app.schemas.acquisition import SearchCandidateQuery, SourceProviderCategory
from backend.app.modules.acquisition.providers.registry import provider_registry


@pytest.mark.asyncio
async def test_provider_registry_initialization():
    """Verify all 8 source discovery providers are registered with proper metadata."""
    providers = provider_registry.list_providers()
    assert len(providers) >= 8

    provider_ids = {p.id for p in providers}
    expected_ids = {
        "huggingface", "kaggle", "google_dataset_search", "datagov",
        "aws_open_data", "github_research", "internal_storage", "synthetic_generator"
    }
    assert expected_ids.issubset(provider_ids)

    for p in providers:
        assert p.name
        assert isinstance(p.category, SourceProviderCategory)
        assert p.rate_limit_per_min > 0


@pytest.mark.asyncio
async def test_huggingface_provider_search():
    """Verify Hugging Face provider searches and normalizes candidate dataset cards."""
    hf = provider_registry.get_provider("huggingface")
    assert hf is not None

    query = SearchCandidateQuery(query="anomaly defect", target_domain="MECHANICAL")
    results = await hf.search(query)
    assert len(results) >= 1

    candidate = results[0]
    assert candidate.source_id == "huggingface"
    assert candidate.canonical_url.startswith("https://huggingface.co/")
    assert candidate.relevance_score > 0
    assert candidate.relevance_breakdown is not None
    assert candidate.license_identifier != ""


@pytest.mark.asyncio
async def test_kaggle_provider_search():
    """Verify Kaggle provider finds sewer pipe and turbine borescope datasets."""
    kg = provider_registry.get_provider("kaggle")
    assert kg is not None

    query = SearchCandidateQuery(query="sewer pipe videoscope", target_domain="PIPES_CHANNELS")
    results = await kg.search(query)
    assert len(results) >= 1

    candidate = results[0]
    assert candidate.source_id == "kaggle"
    assert candidate.is_direct_videoscope is True
    assert "video" in candidate.modalities or "still_images" in candidate.modalities


@pytest.mark.asyncio
async def test_synthetic_generator_provider_search():
    """Verify Synthetic Generator provider marks all candidate offerings with is_direct_videoscope=False."""
    synth = provider_registry.get_provider("synthetic_generator")
    assert synth is not None

    query = SearchCandidateQuery(query="synth pipe crack", target_domain="PIPES_CHANNELS")
    results = await synth.search(query)
    assert len(results) >= 1

    candidate = results[0]
    assert candidate.source_id == "synthetic_generator"
    assert candidate.is_direct_videoscope is False  # Never claim synthetic is real videoscope
    assert "SYNTHETIC" in candidate.license_identifier
