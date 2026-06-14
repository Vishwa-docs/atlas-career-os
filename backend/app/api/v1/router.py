"""Aggregates all domain routers under /api/v1.

Each domain exposes ``router`` (an ``APIRouter``). Add new domains here. Routers
are imported lazily-safely at module import; keep this file boring and flat.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()


def _include(module_path: str, attr: str = "router") -> None:
    """Include a domain router if it exists, so the app boots incrementally
    as domains are implemented (useful during the phased build)."""
    import importlib

    try:
        module = importlib.import_module(module_path)
        api_router.include_router(getattr(module, attr))
    except (ModuleNotFoundError, AttributeError):
        # Domain not implemented yet — skip without breaking the app.
        pass


for _domain in (
    "app.domains.auth.router",
    "app.domains.users.router",
    "app.domains.candidates.router",
    "app.domains.employers.router",
    "app.domains.universities.router",
    "app.domains.jobs.router",
    "app.domains.applications.router",
    "app.domains.matching.router",
    "app.domains.taxonomy.router",
    "app.domains.signals.router",
    "app.domains.consent.router",
    "app.domains.credentials.router",
    "app.domains.notifications.router",
    "app.domains.admin.router",
    "app.domains.ai.router",
):
    _include(_domain)
