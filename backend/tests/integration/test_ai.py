"""Integration: signature AI endpoints return Glass-Box-wrapped verdicts.

Every AI judgement embeds a ``glass_box`` envelope (the trust contract). These
tests assert the shape of that envelope on the deterministic mock LLM.

Requires Docker (testcontainers Postgres) — see ``tests/integration/conftest.py``.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import API, candidate_profile_id, make_actor

pytestmark = pytest.mark.asyncio


def _assert_glass_box(gb: dict) -> None:
    """A Glass Box must carry a rationale, a confidence band, and a 0..1 score."""
    assert isinstance(gb, dict), gb
    assert gb.get("rationale"), "Glass Box must explain its reasoning."
    assert gb["confidence"] in {"low", "medium", "high"}
    assert 0.0 <= gb["confidence_score"] <= 1.0
    assert isinstance(gb.get("citations"), list)
    assert isinstance(gb.get("what_would_change_this"), list)
    assert isinstance(gb.get("caveats"), list)


@pytest.fixture
async def candidate(client):
    """A candidate with an auto-created profile (AI features resolve it)."""
    actor = await make_actor(client, role="candidate")
    await candidate_profile_id(client, actor)
    return actor


async def test_fair_pay_returns_glass_box(client, candidate) -> None:
    resp = await client.post(
        f"{API}/ai/fair-pay", json={"current_pay": 7000}, headers=candidate.headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "verdict" in body
    assert "negotiation" in body and "talking_points" in body["negotiation"]
    assert body["your_pay"] == 7000
    _assert_glass_box(body["glass_box"])


async def test_atlas_returns_routes_with_glass_box(client, candidate) -> None:
    resp = await client.post(
        f"{API}/ai/atlas", json={"horizon_years": 5}, headers=candidate.headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "current" in body and "routes" in body
    _assert_glass_box(body["glass_box"])
    # Each route carries its own Glass Box too.
    for route in body["routes"]:
        _assert_glass_box(route["glass_box"])


async def test_coach_returns_message_and_glass_box(client, candidate) -> None:
    resp = await client.post(
        f"{API}/ai/coach",
        json={"message": "How do I move into data leadership?"},
        headers=candidate.headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("message"), "Coach must return a non-empty message."
    _assert_glass_box(body["glass_box"])


async def test_ai_requires_authentication(client) -> None:
    """Unauthenticated AI calls are rejected before reaching the model."""
    resp = await client.post(f"{API}/ai/fair-pay", json={})
    assert resp.status_code == 401
