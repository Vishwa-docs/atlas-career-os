"""DB access for the organizations domain."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.organizations.models import Membership, Organization


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        return await self.session.get(Organization, org_id)

    async def get_membership_for_user(self, user_id: uuid.UUID) -> Membership | None:
        result = await self.session.execute(
            select(Membership).where(Membership.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()
