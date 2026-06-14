"""Verifiable credentials — the Lifelong Learning Wallet.

Modelled on W3C Verifiable Credentials / Open Badges 3.0: an issuer (university)
signs a credential asserting skills (referenced to taxonomy IDs); the holder
(candidate) stores it; a verifier checks the cryptographic proof. Credentials
feed the skill graph, not just a badge wall.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Credential(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "credentials"

    issuer_org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    holder_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # degree | micro_credential | badge | certificate | course
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_slugs: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    # Cryptographic proof + OBv3/VC JSON-LD payload (mock-signed in the demo).
    proof: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # active | expired | revoked
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
