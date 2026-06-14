"""Record LLM token usage + estimated cost per feature/org for the AI cost ledger."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.llm.client import TokenUsage
from app.domains.ai.models import LlmUsage

# Rough USD per 1K tokens (gpt-4o-class). Tune per deployment.
_PROMPT_COST_PER_1K = 0.0025
_COMPLETION_COST_PER_1K = 0.01


def estimate_cost(usage: TokenUsage) -> float:
    return round(
        usage.prompt_tokens / 1000 * _PROMPT_COST_PER_1K
        + usage.completion_tokens / 1000 * _COMPLETION_COST_PER_1K,
        6,
    )


async def record_usage(
    session: AsyncSession,
    *,
    feature: str,
    model: str,
    usage: TokenUsage,
    org_id: str | uuid.UUID | None = None,
    user_id: str | uuid.UUID | None = None,
) -> None:
    session.add(
        LlmUsage(
            org_id=uuid.UUID(str(org_id)) if org_id else None,
            user_id=uuid.UUID(str(user_id)) if user_id else None,
            feature=feature,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            cost_usd=estimate_cost(usage),
        )
    )
