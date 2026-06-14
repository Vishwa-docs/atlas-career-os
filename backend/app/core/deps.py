"""Shared FastAPI dependencies: authentication, authorization, DB session.

The :class:`Principal` is built from the access-token claims (no DB round-trip
for authz), and we set RLS context vars so downstream queries are tenant-scoped.
Route guards (``require_roles``) keep authorization declarative.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import current_org_id, current_user_id, get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.roles import Role
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)


@dataclass(slots=True)
class Principal:
    """The authenticated actor for the current request."""

    user_id: str
    roles: list[Role] = field(default_factory=list)
    org_id: str | None = None

    def has_role(self, *roles: Role) -> bool:
        return any(r in self.roles for r in roles)

    @property
    def is_platform_admin(self) -> bool:
        return Role.PLATFORM_ADMIN in self.roles


async def get_current_principal(token: str | None = Depends(oauth2_scheme)) -> Principal:
    if not token:
        raise UnauthorizedError("Not authenticated.")
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid authentication token.") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Malformed token.")

    raw_roles = payload.get("roles", []) or []
    roles = [Role(r) for r in raw_roles if r in Role._value2member_map_]
    org_id = payload.get("org_id")

    # Populate context for RLS GUCs and audit logging.
    current_user_id.set(user_id)
    current_org_id.set(org_id)

    return Principal(user_id=user_id, roles=roles, org_id=org_id)


async def get_optional_principal(
    token: str | None = Depends(oauth2_scheme),
) -> Principal | None:
    if not token:
        return None
    try:
        return await get_current_principal(token)
    except UnauthorizedError:
        return None


def require_roles(*allowed: Role):
    """Dependency factory enforcing that the principal holds one of ``allowed``."""

    allowed_set = set(allowed)

    async def _guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.is_platform_admin or allowed_set & set(principal.roles):
            return principal
        raise ForbiddenError("You do not have permission to perform this action.")

    return _guard


def require_org(principal: Principal = Depends(get_current_principal)) -> Principal:
    """Require the actor to belong to an organization (employer/university)."""
    if not principal.org_id:
        raise ForbiddenError("This action requires an organization context.")
    return principal


def require_same_org(target_org_id: str, principal: Principal) -> None:
    """Assert the principal may act within ``target_org_id`` (BOLA defence)."""
    if principal.is_platform_admin:
        return
    if principal.org_id != target_org_id:
        raise ForbiddenError("Cross-organization access is not permitted.")


# Re-export the session dependency for convenient single-import in routers.
SessionDep = Depends(get_session)


def roles_csv(roles: Iterable[Role]) -> str:
    return ",".join(r.value for r in roles)


__all__ = [
    "Principal",
    "get_current_principal",
    "get_optional_principal",
    "require_roles",
    "require_org",
    "require_same_org",
    "get_session",
    "AsyncSession",
]
