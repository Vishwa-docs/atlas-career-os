"""Resilient LLM wrapper: try a primary client, fall back to a secondary one.

In the live demo the primary is Azure OpenAI and the fallback is the
deterministic mock. If Azure ever fails — content-filter rejection, timeout,
rate limit, transient 5xx — the feature still returns sensible, schema-valid
output instead of going blank. Real answers when Azure is happy; graceful,
on-brand output when it isn't.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.logging import get_logger
from app.domains.ai.llm.client import ChatMessage, ChatResult, LLMClient

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class ResilientLLMClient:
    def __init__(self, primary: LLMClient, fallback: LLMClient) -> None:
        self._primary = primary
        self._fallback = fallback

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        try:
            return await self._primary.chat(
                messages, temperature=temperature, max_tokens=max_tokens, tools=tools
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("llm.fallback", method="chat", error=str(exc)[:160])
            return await self._fallback.chat(
                messages, temperature=temperature, max_tokens=max_tokens, tools=tools
            )

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> T:
        try:
            return await self._primary.structured(messages, schema, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            log.warning("llm.fallback", method="structured", error=str(exc)[:160])
            return await self._fallback.structured(messages, schema, temperature=temperature)

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        started = False
        try:
            async for delta in self._primary.stream_chat(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                started = True
                yield delta
        except Exception as exc:  # noqa: BLE001
            # Only fall back if nothing was streamed yet (avoid duplicate text).
            if started:
                log.warning("llm.fallback", method="stream_chat", note="mid-stream error")
                return
            log.warning("llm.fallback", method="stream_chat", error=str(exc)[:160])
            async for delta in self._fallback.stream_chat(
                messages, temperature=temperature, max_tokens=max_tokens
            ):
                yield delta

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            return await self._primary.embed(texts)
        except Exception as exc:  # noqa: BLE001
            log.warning("llm.fallback", method="embed", error=str(exc)[:160])
            return await self._fallback.embed(texts)
