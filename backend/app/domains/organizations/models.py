"""Organizations (employers & universities) and user memberships — the tenant core."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Organization(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    # "employer" | "university"
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    # Employer tier (MNC/GLC/LLO/TECH) or university type (PUBLIC/PRIVATE/...).
    tier: Mapped[str | None] = mapped_column(String(40), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="MY", nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    size: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Membership(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_memberships_user_org"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Role within the org, mirrors RBAC roles (employer_admin, university_staff, ...).
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
