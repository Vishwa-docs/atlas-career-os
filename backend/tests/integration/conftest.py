"""Shared helpers for integration tests.

These tests drive the *real* API surface through the ``client`` fixture (an
async httpx client bound to the FastAPI app), backed by a real Postgres
testcontainer and the deterministic mock LLM. Each test runs in a transaction
that is rolled back, so users/orgs created here never leak between tests.

NOTE: running this package requires Docker — ``testcontainers`` spins up a
``pgvector/pgvector:pg16`` Postgres for the session (see ``tests/conftest.py``).
Without a Docker daemon these tests are skipped/errored at collection of the
session-scoped Postgres fixture.

The helpers below register users and authenticate them purely through HTTP, so
the tests exercise the same code paths a frontend client would.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from httpx import AsyncClient

API = "/api/v1"


@dataclass
class Actor:
    """An authenticated test user with its auth header and identity."""

    email: str
    password: str
    role: str
    access_token: str
    refresh_token: str
    user_id: str
    org_id: str | None
    headers: dict[str, str]


def _unique_email(role: str) -> str:
    """A collision-free email so tests stay independent of each other."""
    return f"{role}-{uuid.uuid4().hex[:12]}@example.com"


async def register(
    client: AsyncClient,
    *,
    role: str,
    password: str = "supersecret123",
    full_name: str | None = None,
    org_name: str | None = None,
    email: str | None = None,
) -> dict:
    """Register a user via ``POST /auth/register`` and return the user payload."""
    email = email or _unique_email(role)
    body = {
        "email": email,
        "password": password,
        "full_name": full_name or f"Test {role}",
        "role": role,
    }
    if org_name is not None:
        body["org_name"] = org_name
    resp = await client.post(f"{API}/auth/register", json=body)
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    payload["_email"] = email
    payload["_password"] = password
    return payload


async def login(client: AsyncClient, email: str, password: str) -> dict:
    """Authenticate via the OAuth2 password grant; returns the token pair."""
    resp = await client.post(
        f"{API}/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def make_actor(
    client: AsyncClient,
    *,
    role: str,
    org_name: str | None = None,
) -> Actor:
    """Register + log in a user, returning a ready-to-use :class:`Actor`."""
    user = await register(client, role=role, org_name=org_name)
    tokens = await login(client, user["_email"], user["_password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return Actor(
        email=user["_email"],
        password=user["_password"],
        role=role,
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user_id=user["id"],
        org_id=user.get("org_id"),
        headers=headers,
    )


async def candidate_profile_id(client: AsyncClient, actor: Actor) -> str:
    """Ensure the candidate profile exists and return its id (BOLA-safe self view)."""
    resp = await client.get(f"{API}/candidates/me", headers=actor.headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["profile"]["id"]


async def create_job(client: AsyncClient, employer: Actor, **overrides) -> dict:
    """Create a job posting as ``employer`` and return the job payload."""
    body = {
        "title": "Senior Data Analyst",
        "description": "Own analytics pipelines and partner with product teams.",
        "requirements": ["3+ years SQL", "Dashboards"],
        "skills_required": ["sql", "python", "dashboards"],
        "location": "Kuala Lumpur",
        "work_mode": "hybrid",
        "seniority": "senior",
        "comp_min": 8000,
        "comp_max": 12000,
        "growth_into": ["Analytics Manager"],
    }
    body.update(overrides)
    resp = await client.post(f"{API}/jobs", json=body, headers=employer.headers)
    assert resp.status_code == 201, resp.text
    return resp.json()
