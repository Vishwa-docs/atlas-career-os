"""Organization business logic: read own org, fetch/update by id (scoped)."""

from __future__ import annotations

import uuid

from app.core.deps import Principal
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.roles import ORG_ADMIN_ROLES
from app.domains.organizations.models import Organization
from app.domains.organizations.repository import OrganizationRepository
from app.domains.organizations.schemas import OrganizationRead, OrganizationUpdate


class OrganizationService:
    def __init__(self, repo: OrganizationRepository) -> None:
        self.repo = repo
        self.session = repo.session

    async def get_my_org(self, principal: Principal) -> OrganizationRead:
        """Resolve the current user's organization via membership."""
        org_id = await self._principal_org_id(principal)
        if org_id is None:
            raise NotFoundError("You are not a member of any organization.")
        org = await self.repo.get_by_id(org_id)
        if org is None:
            raise NotFoundError("Organization not found.")
        return OrganizationRead.model_validate(self._with_str_id(org))

    async def get_org(self, org_id: str, principal: Principal) -> OrganizationRead:
        org = await self._require_org(org_id)
        self._authorize_same_org(str(org.id), principal)
        return OrganizationRead.model_validate(self._with_str_id(org))

    async def update_org(
        self, org_id: str, data: OrganizationUpdate, principal: Principal
    ) -> OrganizationRead:
        """Org admins (or platform admins) may edit their own organization."""
        org = await self._require_org(org_id)
        self._authorize_org_admin(str(org.id), principal)

        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(org, field, value)
        await self.session.commit()
        await self.session.refresh(org)
        return OrganizationRead.model_validate(self._with_str_id(org))

    # --- Internals ---
    async def _require_org(self, org_id: str) -> Organization:
        try:
            oid = uuid.UUID(org_id)
        except (ValueError, AttributeError) as exc:
            raise NotFoundError("Organization not found.") from exc
        org = await self.repo.get_by_id(oid)
        if org is None:
            raise NotFoundError("Organization not found.")
        return org

    async def _principal_org_id(self, principal: Principal) -> uuid.UUID | None:
        if principal.org_id:
            return uuid.UUID(principal.org_id)
        membership = await self.repo.get_membership_for_user(uuid.UUID(principal.user_id))
        return membership.org_id if membership else None

    @staticmethod
    def _authorize_same_org(target_org_id: str, principal: Principal) -> None:
        if principal.is_platform_admin:
            return
        if principal.org_id != target_org_id:
            raise ForbiddenError("Cross-organization access is not permitted.")

    @staticmethod
    def _authorize_org_admin(target_org_id: str, principal: Principal) -> None:
        if principal.is_platform_admin:
            return
        if principal.org_id != target_org_id:
            raise ForbiddenError("Cross-organization access is not permitted.")
        if not principal.has_role(*ORG_ADMIN_ROLES):
            raise ForbiddenError("Only organization admins may edit the organization.")

    @staticmethod
    def _with_str_id(org: Organization) -> dict:
        return {
            "id": str(org.id),
            "name": org.name,
            "type": org.type,
            "tier": org.tier,
            "country": org.country,
            "industry": org.industry,
            "website": org.website,
            "logo_url": org.logo_url,
            "description": org.description,
            "size": org.size,
        }
