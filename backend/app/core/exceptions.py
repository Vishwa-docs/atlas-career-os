"""Domain exception hierarchy and FastAPI handlers.

Services raise these semantic errors; routers stay free of HTTP plumbing. A
single handler maps them to RFC-9457-style problem responses so the API speaks
consistent error shapes to the frontend.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse


class AppError(Exception):
    """Base for all expected, mapped application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, *, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"


class ConsentRequiredError(ForbiddenError):
    """Raised when an actor tries to access career data without an active grant."""

    code = "consent_required"


class LLMError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "llm_error"


def _problem(
    status_code: int, code: str, message: str, details: Any | None = None
) -> ORJSONResponse:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return ORJSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> ORJSONResponse:
        return _problem(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> ORJSONResponse:
        return _problem(
            422,
            "validation_error",
            "Request validation failed.",
            exc.errors(),
        )
