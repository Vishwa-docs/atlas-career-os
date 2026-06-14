"""Deterministic mock LLM.

Used whenever Azure OpenAI is not configured (or ``USE_MOCK_LLM=true``) and in
every test. It implements the full :class:`LLMClient` contract: chat, streaming,
structured outputs (it builds a *valid* instance of any requested Pydantic
schema), and embeddings (stable pseudo-vectors derived from a content hash, so
similarity is reproducible). This means the entire product is demoable and the
test-suite is hermetic without ever calling a paid API.
"""

from __future__ import annotations

import hashlib
import math
import types
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from app.core.config import settings
from app.domains.ai.llm.client import ChatMessage, ChatResult, TokenUsage


def _stable_floats(text: str, n: int) -> list[float]:
    """Deterministic unit-norm vector of length ``n`` from ``text``."""
    vals: list[float] = []
    counter = 0
    while len(vals) < n:
        digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
        for b in digest:
            vals.append((b / 255.0) * 2.0 - 1.0)
            if len(vals) >= n:
                break
        counter += 1
    norm = math.sqrt(sum(v * v for v in vals)) or 1.0
    return [v / norm for v in vals]


class MockLLMClient:
    """A predictable stand-in for a real LLM."""

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatResult:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        reply = (
            "Here's how I'd think about that. Based on what you've shared, a few "
            "realistic options stand out — each with trade-offs. "
            f'(Reflecting on: "{last_user[:160]}") '
            "I've flagged where I'm confident and where the picture is fuzzier."
        )
        return ChatResult(
            content=reply,
            usage=TokenUsage(prompt_tokens=len(last_user) // 4, completion_tokens=64),
            model="mock-llm",
        )

    async def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        result = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        for word in result.content.split(" "):
            yield word + " "

    async def structured(
        self,
        messages: Sequence[ChatMessage],
        schema: type[BaseModel],
        *,
        temperature: float = 0.0,
    ) -> BaseModel:
        seed = next((m.content for m in reversed(messages) if m.role == "user"), "atlas")
        return _build_instance(schema, seed)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        dims = settings.embedding_dimensions
        return [_stable_floats(t, dims) for t in texts]


# --------------------------------------------------------------------------- #
# Schema faker — builds a valid instance of an arbitrary Pydantic model.
# --------------------------------------------------------------------------- #
def _build_instance(schema: type[BaseModel], seed: str) -> BaseModel:
    values: dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        values[name] = _fake_for_annotation(field.annotation, name, seed)
    return schema.model_validate(values)


def _is_optional(annotation: Any) -> tuple[bool, Any]:
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(annotation) if a is not type(None)]
        return (len(args) < len(get_args(annotation)), args[0] if args else str)
    return (False, annotation)


def _fake_for_annotation(annotation: Any, field_name: str, seed: str) -> Any:  # noqa: C901
    optional, inner = _is_optional(annotation)
    annotation = inner
    origin = get_origin(annotation)

    if origin in (list, set, tuple):
        (item_type,) = (get_args(annotation) or (str,))[:1]
        return [_fake_for_annotation(item_type, field_name, seed)]
    if origin is dict:
        return {}

    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _build_instance(annotation, seed)
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        members = list(annotation)
        # Prefer a "medium"-ish member when present (confidence bands etc.).
        for m in members:
            if str(m.value).lower() in ("medium", "med"):
                return m
        return members[len(members) // 2] if members else None
    if annotation is bool:
        return True
    if annotation is int:
        return 1
    if annotation is float:
        lname = field_name.lower()
        if "score" in lname or "confidence" in lname or "probability" in lname:
            return 0.62
        return 1.0
    if annotation is datetime:
        return datetime.now(UTC)
    if annotation is str:
        return _fake_str(field_name, seed)
    return None if optional else _fake_str(field_name, seed)


def _fake_str(field_name: str, seed: str) -> str:
    lname = field_name.lower()
    if "rationale" in lname or "reason" in lname or "explanation" in lname:
        return (
            "This conclusion is grounded in the candidate's recent roles and the "
            "current market signal; it is a realistic range, not a prediction."
        )
    if "title" in lname or "name" in lname or "label" in lname:
        return "Senior Data Analyst"
    if "snippet" in lname:
        return f"Supporting evidence relevant to {seed[:40]}"
    if "caveat" in lname or "change" in lname:
        return "More verified skills or recent achievements would sharpen this."
    return f"{field_name.replace('_', ' ').title()} (mock)"
