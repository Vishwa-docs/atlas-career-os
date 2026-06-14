"""Integration: candidate applies, employer lists pipeline, PATCHes status.

Requires Docker (testcontainers Postgres) — see ``tests/integration/conftest.py``.
"""

from __future__ import annotations

import pytest

from tests.integration.conftest import (
    API,
    candidate_profile_id,
    create_job,
    make_actor,
)

pytestmark = pytest.mark.asyncio


async def test_apply_pipeline_and_status_transition(client) -> None:
    """End-to-end application loop across the candidate and employer sides."""
    employer = await make_actor(client, role="employer_admin", org_name="HireCo")
    candidate = await make_actor(client, role="candidate")

    # Candidate must have a profile before applying.
    cand_id = await candidate_profile_id(client, candidate)
    job = await create_job(client, employer)

    # Candidate applies.
    apply_resp = await client.post(
        f"{API}/applications",
        json={"job_id": job["id"], "cover_note": "Keen to contribute."},
        headers=candidate.headers,
    )
    assert apply_resp.status_code == 201, apply_resp.text
    application = apply_resp.json()
    assert application["job_id"] == job["id"]
    assert application["candidate_id"] == cand_id
    assert application["status"] == "applied"

    # Candidate sees it in their own list with the job summary.
    mine = await client.get(f"{API}/applications", headers=candidate.headers)
    assert mine.status_code == 200, mine.text
    rows = mine.json()
    assert any(r["application"]["id"] == application["id"] for r in rows)

    # Employer sees it in the job pipeline.
    pipeline = await client.get(
        f"{API}/jobs/{job['id']}/applications", headers=employer.headers
    )
    assert pipeline.status_code == 200, pipeline.text
    entries = pipeline.json()
    assert any(e["application"]["id"] == application["id"] for e in entries)

    # Employer advances the application to 'shortlisted'.
    patched = await client.patch(
        f"{API}/applications/{application['id']}/status",
        json={"status": "shortlisted", "note": "Strong SQL background."},
        headers=employer.headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "shortlisted"


async def test_employer_cannot_advance_other_orgs_application(client) -> None:
    """BOLA defence: an unrelated employer cannot patch another org's pipeline."""
    owner = await make_actor(client, role="employer_admin", org_name="OwnerCo")
    other = await make_actor(client, role="employer_admin", org_name="OtherCo")
    candidate = await make_actor(client, role="candidate")
    await candidate_profile_id(client, candidate)

    job = await create_job(client, owner)
    application = (
        await client.post(
            f"{API}/applications",
            json={"job_id": job["id"]},
            headers=candidate.headers,
        )
    ).json()

    resp = await client.patch(
        f"{API}/applications/{application['id']}/status",
        json={"status": "rejected"},
        headers=other.headers,
    )
    assert resp.status_code in (403, 404), resp.text
