"""Integration: employer posts a job, candidate searches & finds it, GET /jobs/{id}.

Requires Docker (testcontainers Postgres) — see ``tests/integration/conftest.py``.
"""

from __future__ import annotations

import uuid

import pytest

from tests.integration.conftest import API, create_job, make_actor

pytestmark = pytest.mark.asyncio


async def test_employer_creates_job_candidate_finds_it(client) -> None:
    """An employer creates a posting; a candidate finds it via search + detail."""
    employer = await make_actor(client, role="employer_admin", org_name="DataCo")
    candidate = await make_actor(client, role="candidate")

    # Distinctive title so the keyword search is unambiguous in a shared DB.
    marker = uuid.uuid4().hex[:8]
    title = f"Quantum Pipeline Engineer {marker}"
    job = await create_job(client, employer, title=title)
    assert job["org_id"] == employer.org_id
    assert job["status"] == "open"

    # Candidate keyword-searches and finds exactly this posting.
    resp = await client.get(
        f"{API}/jobs", params={"q": marker}, headers=candidate.headers
    )
    assert resp.status_code == 200, resp.text
    page = resp.json()
    assert page["total"] >= 1
    titles = [item["title"] for item in page["items"]]
    assert title in titles

    # And can open its detail by id.
    detail = await client.get(f"{API}/jobs/{job['id']}", headers=candidate.headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == job["id"]
    assert detail.json()["title"] == title


async def test_candidate_cannot_create_job(client) -> None:
    """Job creation is employer-only (role guard → 403)."""
    candidate = await make_actor(client, role="candidate")
    resp = await client.post(
        f"{API}/jobs",
        json={
            "title": "Sneaky Posting",
            "description": "Should be rejected.",
        },
        headers=candidate.headers,
    )
    assert resp.status_code == 403, resp.text


async def test_get_unknown_job_is_404(client) -> None:
    """A well-formed but unknown job id returns 404."""
    candidate = await make_actor(client, role="candidate")
    resp = await client.get(
        f"{API}/jobs/{uuid.uuid4()}", headers=candidate.headers
    )
    assert resp.status_code == 404
