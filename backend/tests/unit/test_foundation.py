"""Smoke tests for the platform foundation: health, security, mock LLM, Glass Box."""

from __future__ import annotations

import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.ai.llm.mock import MockLLMClient
from app.domains.ai.llm.client import ChatMessage
from app.domains.ai.schemas import AIResponse, Confidence, GlassBox


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cr3t-passphrase")
    assert h != "s3cr3t-passphrase"
    assert verify_password("s3cr3t-passphrase", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-123", roles=["candidate"], org_id=None)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["roles"] == ["candidate"]
    assert payload["type"] == "access"


def test_glass_box_schema() -> None:
    gb = GlassBox(
        rationale="Because X and Y.",
        confidence=Confidence.MEDIUM,
        confidence_score=0.6,
        citations=[],
        what_would_change_this=["More verified skills."],
    )
    assert 0.0 <= gb.confidence_score <= 1.0


@pytest.mark.asyncio
async def test_mock_llm_embeddings_are_stable() -> None:
    llm = MockLLMClient()
    a = await llm.embed(["data analyst"])
    b = await llm.embed(["data analyst"])
    assert a == b
    assert len(a[0]) > 0


@pytest.mark.asyncio
async def test_mock_llm_structured_builds_valid_instance() -> None:
    llm = MockLLMClient()
    out = await llm.structured([ChatMessage(role="user", content="hi")], AIResponse)
    assert isinstance(out, AIResponse)
    assert out.glass_box.rationale


@pytest.mark.asyncio
async def test_health_endpoint(client) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
