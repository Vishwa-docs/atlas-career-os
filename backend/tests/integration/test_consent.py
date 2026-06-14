"""Integration: the consent gate on the external candidate view.

A candidate owns their graph. An employer sees it only through an active,
scoped consent grant. Without a grant the view is forbidden; with a 'profile'
grant for the employer's org it succeeds and is trimmed to the granted scopes.

Requires Docker (testcontainers Postgres) — see ``tests/integration/conftest.py``.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import API, candidate_profile_id, make_actor

pytestmark = pytest.mark.asyncio


async def test_view_without_grant_is_forbidden(client) -> None:
    """An employer without a consent grant gets 403 (consent_required)."""
    employer = await make_actor(client, role="employer_admin", org_name="ViewerCo")
    candidate = await make_actor(client, role="candidate")
    cand_id = await candidate_profile_id(client, candidate)

    resp = await client.get(
        f"{API}/candidates/{cand_id}", headers=employer.headers
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "consent_required"


async def test_view_with_grant_succeeds(client) -> None:
    """After the candidate grants 'profile' scope, the employer can view."""
    employer = await make_actor(client, role="employer_admin", org_name="GrantedCo")
    candidate = await make_actor(client, role="candidate")
    cand_id = await candidate_profile_id(client, candidate)

    # Candidate grants the employer's org scoped access.
    grant_resp = await client.post(
        f"{API}/consent",
        json={
            "grantee_org_id": employer.org_id,
            "scopes": ["profile", "skills"],
            "purpose": "Recruiting for an analytics role.",
        },
        headers=candidate.headers,
    )
    assert grant_resp.status_code == 201, grant_resp.text
    grant = grant_resp.json()
    assert grant["grantee_org_id"] == employer.org_id
    assert "profile" in grant["scopes"]

    # Now the employer can view the (scope-trimmed) public profile.
    resp = await client.get(
        f"{API}/candidates/{cand_id}", headers=employer.headers
    )
    assert resp.status_code == 200, resp.text
    public = resp.json()
    assert public["id"] == cand_id
    assert "profile" in public["scopes"]
