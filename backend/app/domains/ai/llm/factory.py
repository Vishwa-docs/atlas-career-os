"""LLM client selection + FastAPI dependency.

We return the deterministic mock unless live Azure use is both enabled and
configured. The instance is cached per process. Inject ``LLMClient`` into
services/routers via ``Depends(get_llm)`` so tests can override it trivially.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger
from app.domains.ai.llm.client import LLMClient
from app.domains.ai.llm.mock import MockLLMClient

log = get_logger(__name__)


@lru_cache
def _build_client() -> LLMClient:
    if settings.use_live_llm:
        from app.domains.ai.llm.azure import AzureOpenAIClient

        log.info("llm.client.selected", provider="azure_openai")
        return AzureOpenAIClient()
    if not settings.use_mock_llm and not settings.azure_configured:
        log.warning("llm.client.fallback_mock", reason="azure_not_configured")
    else:
        log.info("llm.client.selected", provider="mock")
    return MockLLMClient()


def get_llm() -> LLMClient:
    return _build_client()
