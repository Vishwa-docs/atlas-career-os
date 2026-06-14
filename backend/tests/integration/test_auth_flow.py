"""Integration: the auth lifecycle (register -> login -> /auth/me) + failure paths.

Requires Docker (testcontainers Postgres) — see ``tests/integration/conftest.py``.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import API, login, register

pytestmark = pytest.mark.asyncio


async def test_register_login_me_happy_path(client) -> None:
    """A candidate can register, log in, and read their identity from /auth/me."""
    user = await register(client, role="candidate", full_name="Ada Lovelace")
    assert user["email"] == user["_email"]
    assert "candidate" in user["roles"]
    # Candidates have no organization.
    assert user.get("org_id") is None

    tokens = await login(client, user["_email"], user["_password"])
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    resp = await client.get(f"{API}/auth/me", headers=headers)
    assert resp.status_code == 200, resp.text
    me = resp.json()
    assert me["id"] == user["id"]
    assert me["email"] == user["_email"]
    assert me["full_name"] == "Ada Lovelace"
    assert "candidate" in me["roles"]


async def test_employer_registration_creates_org(client) -> None:
    """Registering an employer_admin role provisions an organization."""
    user = await register(
        client, role="employer_admin", org_name="Acme Bhd"
    )
    assert user["org_id"] is not None

    tokens = await login(client, user["_email"], user["_password"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = (await client.get(f"{API}/auth/me", headers=headers)).json()
    assert me["org_id"] == user["org_id"]
    assert me["org_name"] == "Acme Bhd"


async def test_login_bad_password_is_401(client) -> None:
    """Wrong password is rejected with 401 and the semantic error envelope."""
    user = await register(client, role="candidate")
    resp = await client.post(
        f"{API}/auth/login",
        data={"username": user["_email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_me_without_token_is_401(client) -> None:
    """The identity endpoint requires authentication."""
    resp = await client.get(f"{API}/auth/me")
    assert resp.status_code == 401
