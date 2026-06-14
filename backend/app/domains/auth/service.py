"""Auth business logic: registration, login, refresh-rotation, logout, identity."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.roles import EMPLOYER_ROLES, UNIVERSITY_ROLES, Role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.auth.repository import AuthRepository
from app.domains.auth.schemas import RegisterRequest, TokenPair, UserRead
from app.domains.organizations.models import Membership, Organization
from app.domains.users.models import RefreshToken, User


def _org_type_for_role(role: Role) -> str | None:
    if role in EMPLOYER_ROLES:
        return "employer"
    if role in UNIVERSITY_ROLES:
        return "university"
    return None


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


class AuthService:
    """Coordinates the repository, crypto primitives, and semantic errors."""

    def __init__(self, repo: AuthRepository) -> None:
        self.repo = repo
        self.session = repo.session

    # --- Registration ---
    async def register(self, data: RegisterRequest) -> UserRead:
        """Create a user (+ org & admin membership for org-bound roles)."""
        email = data.email.lower()
        if await self.repo.get_user_by_email(email):
            raise ConflictError("An account with this email already exists.")

        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            roles=[data.role.value],
        )
        self.repo.add_user(user)
        await self.session.flush()  # assign user.id

        org: Organization | None = None
        org_type = _org_type_for_role(data.role)
        if org_type is not None:
            org = Organization(
                name=data.org_name or f"{data.full_name}'s organization",
                type=org_type,
            )
            self.repo.add_organization(org)
            await self.session.flush()  # assign org.id
            self.repo.add_membership(
                Membership(user_id=user.id, org_id=org.id, role=data.role.value)
            )

        await self.session.commit()
        return self._to_user_read(
            user, org_id=org.id if org else None, org_name=org.name if org else None
        )

    # --- Login ---
    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.repo.get_user_by_email(email.lower())
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account is disabled.")

        org_id = await self._resolve_org_id(user.id)
        pair = self._issue_token_pair(user, org_id)
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        return pair

    # --- Refresh (rotation) ---
    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid refresh token.") from exc

        jti = payload.get("jti")
        sub = payload.get("sub")
        if not jti or not sub:
            raise UnauthorizedError("Malformed refresh token.")

        record = await self.repo.get_active_refresh_token(_hash_jti(jti))
        if record is None or record.revoked_at is not None:
            raise UnauthorizedError("Refresh token has been revoked.")

        user = await self.repo.get_user_by_id(uuid.UUID(str(sub)))
        if user is None or not user.is_active:
            raise UnauthorizedError("Account is no longer valid.")
        if payload.get("tv", 0) != user.token_version:
            raise UnauthorizedError("Refresh token is stale.")

        # Rotate: revoke the presented token, issue a fresh pair.
        await self.repo.revoke_refresh_token(record, datetime.now(UTC))
        org_id = await self._resolve_org_id(user.id)
        pair = self._issue_token_pair(user, org_id)
        await self.session.commit()
        return pair

    # --- Logout (best-effort revoke) ---
    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            await self.session.commit()
            return
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            jti = payload.get("jti")
            if jti:
                record = await self.repo.get_active_refresh_token(_hash_jti(jti))
                if record is not None and record.revoked_at is None:
                    await self.repo.revoke_refresh_token(record, datetime.now(UTC))
        except jwt.PyJWTError:
            pass  # already-invalid tokens are effectively logged out
        await self.session.commit()

    # --- Identity (/me) ---
    async def get_me(self, user_id: str) -> UserRead:
        user = await self.repo.get_user_by_id(uuid.UUID(user_id))
        if user is None:
            raise UnauthorizedError("Account not found.")
        org_id, org_name = await self._resolve_org(user.id)
        return self._to_user_read(user, org_id=org_id, org_name=org_name)

    # --- Internals ---
    def _issue_token_pair(self, user: User, org_id: uuid.UUID | None) -> TokenPair:
        roles = list(user.roles or [])
        org_str = str(org_id) if org_id else None
        access = create_access_token(str(user.id), roles, org_str, user.token_version)
        refresh, jti = create_refresh_token(str(user.id), user.token_version)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        self.repo.add_refresh_token(
            RefreshToken(user_id=user.id, jti_hash=_hash_jti(jti), expires_at=expires_at)
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    async def _resolve_org_id(self, user_id: uuid.UUID) -> uuid.UUID | None:
        membership = await self.repo.get_membership_for_user(user_id)
        return membership.org_id if membership else None

    async def _resolve_org(self, user_id: uuid.UUID) -> tuple[uuid.UUID | None, str | None]:
        membership = await self.repo.get_membership_for_user(user_id)
        if membership is None:
            return None, None
        org = await self.repo.get_org_by_id(membership.org_id)
        return membership.org_id, (org.name if org else None)

    @staticmethod
    def _to_user_read(user: User, *, org_id: uuid.UUID | None, org_name: str | None) -> UserRead:
        return UserRead(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            roles=[Role(r) for r in (user.roles or []) if r in Role._value2member_map_],
            org_id=str(org_id) if org_id else None,
            org_name=org_name,
            locale=user.locale,
            avatar_url=user.avatar_url,
        )
