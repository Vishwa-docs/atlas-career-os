"""All DB access for the auth domain (users, orgs, memberships, refresh tokens)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Membership, Organization
from app.domains.users.models import RefreshToken, User


class AuthRepository:
    """Encapsulates every query auth/login/refresh needs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Users ---
    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    def add_user(self, user: User) -> None:
        self.session.add(user)

    # --- Organizations / memberships ---
    def add_organization(self, org: Organization) -> None:
        self.session.add(org)

    def add_membership(self, membership: Membership) -> None:
        self.session.add(membership)

    async def get_membership_for_user(self, user_id: uuid.UUID) -> Membership | None:
        result = await self.session.execute(
            select(Membership).where(Membership.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_org_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self.session.get(Organization, org_id)

    # --- Refresh tokens ---
    def add_refresh_token(self, token: RefreshToken) -> None:
        self.session.add(token)

    async def get_active_refresh_token(self, jti_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.jti_hash == jti_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken, when: datetime) -> None:
        token.revoked_at = when
