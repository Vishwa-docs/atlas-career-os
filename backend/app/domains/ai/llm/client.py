"""The provider-agnostic LLM contract.

Everything in Atlas talks to this :class:`LLMClient` Protocol — never to the
Azure SDK directly. That keeps the provider swappable, lets us inject a
deterministic mock in tests, and gives us one place to enforce retries, timeouts,
token accounting, and guardrails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class ChatResult(BaseModel):
    content: str
    usage: TokenUsage = TokenUsage()
    tool_calls: list[dict[str, Any]] = []
    model: str | None = None


@runtime_checkable
class LLMClient(Protocol):
    """The interface every AI feature depends on."""

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult: ...

    def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield content deltas (SSE-friendly)."""
        ...

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        schema: type[T],
        *,
        temperature: float = 0.0,
    ) -> T:
        """Return a validated instance of ``schema`` (constrained decoding)."""
        ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input string."""
        ...
