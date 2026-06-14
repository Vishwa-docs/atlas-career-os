"""Auth request/response schemas (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.core.roles import Role
from app.core.schemas import ORMModel


class RegisterRequest(BaseModel):
    """Self-service signup. Org-bound roles also create an Organization."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    role: Role
    org_name: str | None = Field(default=None, max_length=200)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRead(ORMModel):
    """The authenticated user as the frontend expects from /auth/me & /auth/register."""

    id: str
    email: str
    full_name: str
    roles: list[Role]
    org_id: str | None = None
    org_name: str | None = None
    locale: str = "en"
    avatar_url: str | None = None
