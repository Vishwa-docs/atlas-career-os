"""Pydantic schemas for consent grants and data-dignity operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import ORMModel
from app.domains.consent.models import CONSENT_SCOPES


class ConsentCreate(BaseModel):
    """Grant an organization scoped, time-boxed access to my career data."""

    grantee_org_id: uuid.UUID
    scopes: list[str] = Field(min_length=1)
    purpose: str | None = Field(default=None, max_length=300)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def _scopes_subset(cls, v: list[str]) -> list[str]:
        unknown = [s for s in v if s not in CONSENT_SCOPES]
        if unknown:
            raise ValueError(f"Unknown scopes {unknown}; allowed: {CONSENT_SCOPES}")
        # De-dupe while preserving order.
        return list(dict.fromkeys(v))


class ConsentRead(ORMModel):
    """A consent grant (active or historical)."""

    id: uuid.UUID
    candidate_id: uuid.UUID
    grantee_org_id: uuid.UUID
    scopes: list[str] = Field(default_factory=list)
    purpose: str | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class AccessLogEntry(BaseModel):
    """A who-viewed-what row, projected from the audit log."""

    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    org_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DataExport(BaseModel):
    """Portable JSON export of a user's identity + career data."""

    exported_at: datetime
    user: dict[str, Any]
    candidate: dict[str, Any] | None = None
    career_events: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    consent_grants: list[dict[str, Any]] = Field(default_factory=list)
    credentials: list[dict[str, Any]] = Field(default_factory=list)


class ErasureResult(BaseModel):
    """Summary of a right-to-erasure operation."""

    erased: bool
    deleted_counts: dict[str, int] = Field(default_factory=dict)
