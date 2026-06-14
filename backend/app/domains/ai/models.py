"""AI-platform tables: RAG embeddings corpus and the LLM usage/cost ledger."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDMixin

EMBED_DIM = settings.embedding_dimensions


class Embedding(UUIDMixin, TimestampMixin, Base):
    """A chunk-level embedding for RAG over career history, jobs, and market data."""

    __tablename__ = "embeddings"

    # career_history | job_posting | salary_data | labor_market | skill_taxonomy
    owner_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    chunk: Mapped[str] = mapped_column(Text, nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM), nullable=False)
    model_version: Mapped[str] = mapped_column(String(60), default="mock-llm", nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class LlmUsage(UUIDMixin, TimestampMixin, Base):
    """Per-call token + cost accounting, attributable per org/user/feature."""

    __tablename__ = "llm_usage"

    org_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    feature: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
