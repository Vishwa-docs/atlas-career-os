"""Atlas API — application factory.

Wires logging, middleware (request-id, CORS), rate limiting, exception handlers,
and the versioned router. Keep this file thin: configuration lives in
``core/``, behaviour lives in the domains.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id to every request, response, and log line."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["x-request-id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(
        "app.startup",
        env=settings.environment,
        llm="azure" if settings.use_live_llm else "mock",
    )
    yield
    log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        default_response_class=JSONResponse,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    register_exception_handlers(app)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "atlas-api",
            "environment": settings.environment,
            "llm": "azure" if settings.use_live_llm else "mock",
        }

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"name": settings.app_name, "docs": "/docs"}

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "rate_limited", "message": "Too many requests."}},
    )


app = create_app()
