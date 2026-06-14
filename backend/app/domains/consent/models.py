"""Consent grants — the data-dignity backbone.

A candidate owns their graph. Employers/universities see it only through an
active, time-boxed, revocable :class:`ConsentGrant`. Repositories filter reads
of candidate data by these grants.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin

# Scopes a grant can cover.
CONSENT_SCOPES = (
    "profile",
    "career_history",
    "skills",
    "salary",
    "contact",
    "trajectory",
)


class ConsentGrant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "consent_grants"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grantee_org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(300), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
