"""Auth endpoints (thin). Mounted at /api/v1/auth."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, get_current_principal, get_session
from app.domains.auth.repository import AuthRepository
from app.domains.auth.schemas import (
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserRead,
)
from app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(session: AsyncSession) -> AuthService:
    return AuthService(AuthRepository(session))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """Self-service signup. Employer/university roles also create the org."""
    return await _service(session).register(body)


@router.post("/login", response_model=TokenPair)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """OAuth2 password grant: ``username`` is the email."""
    return await _service(session).login(form.username, form.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenPair:
    """Rotate the refresh token, returning a fresh access/refresh pair."""
    return await _service(session).refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Best-effort revocation of the presented refresh token."""
    await _service(session).logout(body.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """The authenticated user, with resolved org name."""
    return await _service(session).get_me(principal.user_id)
