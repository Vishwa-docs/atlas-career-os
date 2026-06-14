"""Organization read/update schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.schemas import ORMModel


class OrganizationRead(ORMModel):
    id: str
    name: str
    type: str
    tier: str | None = None
    country: str = "MY"
    industry: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    size: str | None = None


class OrganizationUpdate(BaseModel):
    """Org-admin editable fields. All optional (partial update)."""

    name: str | None = Field(default=None, max_length=200)
    tier: str | None = Field(default=None, max_length=40)
    country: str | None = Field(default=None, max_length=2)
    industry: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=300)
    logo_url: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=2000)
    size: str | None = Field(default=None, max_length=40)
