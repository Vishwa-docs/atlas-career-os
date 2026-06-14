"""Pydantic schemas for verifiable credentials (Lifelong Learning Wallet)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel

_CREDENTIAL_TYPES = ("degree", "micro_credential", "badge", "certificate", "course")


class CredentialIssue(BaseModel):
    """Payload to issue a new credential for a candidate."""

    holder_candidate_id: uuid.UUID
    type: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    skill_slugs: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class CredentialRead(ORMModel):
    """A credential as stored in the wallet."""

    id: uuid.UUID
    issuer_org_id: uuid.UUID | None = None
    holder_candidate_id: uuid.UUID
    type: str
    title: str
    description: str | None = None
    skill_slugs: list[str] = Field(default_factory=list)
    proof: dict[str, Any] = Field(default_factory=dict)
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    status: str
    created_at: datetime


class CredentialVerification(BaseModel):
    """Result of recomputing and checking a credential's mock proof."""

    valid: bool
    issuer: uuid.UUID | None = None
    holder: uuid.UUID
    skills: list[str] = Field(default_factory=list)
    issued_at: datetime | None = None


def is_valid_type(value: str) -> bool:
    """Whether ``value`` is a recognised credential type."""
    return value in _CREDENTIAL_TYPES
