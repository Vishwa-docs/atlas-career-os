"""Azure OpenAI implementation of :class:`LLMClient`.

Wraps the official ``openai`` SDK (AsyncAzureOpenAI). Adds exponential-backoff
retries on transient failures, hard timeouts, structured-output parsing, and
streaming. The deployment names and API version come from settings so the same
code runs against any Azure OpenAI resource.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, TypeVar

from openai import APIConnectionError, APITimeoutError, AsyncAzureOpenAI, RateLimitError
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.config import settings
from app.core.exceptions import LLMError
from app.domains.ai.llm.client import ChatMessage, ChatResult, TokenUsage

T = TypeVar("T", bound=BaseModel)

_RETRYABLE = (RateLimitError, APITimeoutError, APIConnectionError)


def _to_openai(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.name:
            item["name"] = m.name
        if m.tool_call_id:
            item["tool_call_id"] = m.tool_call_id
        out.append(item)
    return out


class AzureOpenAIClient:
    def __init__(self) -> None:
        if not settings.azure_configured:
            raise LLMError("Azure OpenAI is not configured (endpoint/key missing).")
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            timeout=settings.llm_request_timeout_seconds,
            max_retries=0,  # we own retries via tenacity
        )
        self._chat_model = settings.azure_openai_deployment
        self._embed_model = settings.azure_openai_embedding_deployment

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_random_exponential(min=1, max=20),
        stop=stop_after_attempt(settings.llm_max_retries),
        reraise=True,
    )
    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        try:
            resp = await self._client.chat.completions.create(
                model=self._chat_model,
                messages=_to_openai(messages),  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,  # type: ignore[arg-type]
            )
        except _RETRYABLE:
            raise
        except Exception as exc:  # pragma: no cover - provider errors
            raise LLMError(f"Azure chat completion failed: {exc}") from exc

        choice = resp.choices[0]
        tool_calls = [tc.model_dump() for tc in (choice.message.tool_calls or [])]
        usage = TokenUsage(
            prompt_tokens=getattr(resp.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(resp.usage, "completion_tokens", 0) or 0,
        )
        return ChatResult(
            content=choice.message.content or "",
            usage=usage,
            tool_calls=tool_calls,
            model=resp.model,
        )

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        try:
            stream = await self._client.chat.completions.create(
                model=self._chat_model,
                messages=_to_openai(messages),  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as exc:  # pragma: no cover - provider errors
            raise LLMError(f"Azure streaming failed: {exc}") from exc

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_random_exponential(min=1, max=20),
        stop=stop_after_attempt(settings.llm_max_retries),
        reraise=True,
    )
    async def structured(
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> T:
        try:
            resp = await self._client.beta.chat.completions.parse(
                model=self._chat_model,
                messages=_to_openai(messages),  # type: ignore[arg-type]
                temperature=temperature,
                response_format=schema,
            )
            parsed = resp.choices[0].message.parsed
            if parsed is None:
                raise LLMError("Model returned no parseable structured output.")
            return parsed
        except _RETRYABLE:
            raise
        except Exception as exc:  # pragma: no cover - provider errors
            raise LLMError(f"Azure structured output failed: {exc}") from exc

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        wait=wait_random_exponential(min=1, max=20),
        stop=stop_after_attempt(settings.llm_max_retries),
        reraise=True,
    )
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            resp = await self._client.embeddings.create(
                model=self._embed_model,
                input=list(texts),
                dimensions=settings.embedding_dimensions,
            )
            return [d.embedding for d in resp.data]
        except _RETRYABLE:
            raise
        except Exception as exc:  # pragma: no cover - provider errors
            raise LLMError(f"Azure embedding failed: {exc}") from exc
