"""Composite LLM client: generative calls to one backend, embeddings to another.

Why: in the live demo we point chat / structured-output / streaming at the real
Azure OpenAI deployment (impressive, authentic answers), but keep embeddings on
the deterministic mock. The seeded corpus was embedded with the mock embedder,
so query vectors must come from the *same* embedder for semantic search and
matching to stay coherent — and the demo Azure resource exposes a chat
deployment but not necessarily an embeddings one. This adapter composes the two
behind the single :class:`LLMClient` contract.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from app.domains.ai.llm.client import ChatMessage, ChatResult, LLMClient

T = TypeVar("T", bound=BaseModel)


class CompositeLLMClient:
    """Delegate generative methods to ``chat`` and embeddings to ``embed``."""

    def __init__(self, chat_client: LLMClient, embed_client: LLMClient) -> None:
        self._chat = chat_client
        self._embed = embed_client

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        return await self._chat.chat(
            messages, temperature=temperature, max_tokens=max_tokens, tools=tools
        )

    def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        return self._chat.stream_chat(messages, temperature=temperature, max_tokens=max_tokens)

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> T:
        return await self._chat.structured(messages, schema, temperature=temperature)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed.embed(texts)
