"""Unit tests for the transparent matching scorers.

These exercise the pure, deterministic component scorers and the grounded
heuristic Glass Box directly — no DB, no network, no LLM round-trip — so they
are fast and hermetic. The contract under test: every sub-score and the blended
overall score live in [0, 1], and the Glass Box names every sub-score band.
"""

from __future__ import annotations

import types

import pytest

from app.domains.ai.schemas import Confidence, GlassBox
from app.domains.matching.service import (
    WEIGHTS,
    _heuristic_glass_box,
    cosine,
    salary_fit,
    weighted_jaccard,
)


def _fake_job(**kw):
    """A minimal duck-typed Job for the pure scorers."""
    defaults = dict(
        id="00000000-0000-0000-0000-000000000001",
        comp_min=8000,
        comp_max=12000,
        skills_required=["sql", "python"],
        title="Senior Data Analyst",
        seniority="senior",
        description="Build analytics.",
        growth_into=[],
        occupation_id=None,
    )
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


def _fake_candidate(**kw):
    defaults = dict(
        id="00000000-0000-0000-0000-0000000000aa",
        embedding=None,
        target_occupation_id=None,
        current_occupation_id=None,
        aspirations=None,
    )
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


# --------------------------------------------------------------------------- #
# cosine
# --------------------------------------------------------------------------- #
def test_cosine_identical_vectors_is_max() -> None:
    v = [0.1, 0.2, 0.3, 0.4]
    score = cosine(v, v)
    assert score is not None
    assert 0.0 <= score <= 1.0
    assert score == pytest.approx(1.0, abs=1e-6)


def test_cosine_missing_or_mismatched_returns_none() -> None:
    assert cosine(None, [1.0]) is None
    assert cosine([1.0, 2.0], [1.0]) is None
    assert cosine([0.0, 0.0], [1.0, 1.0]) is None


def test_cosine_opposite_vectors_is_min() -> None:
    score = cosine([1.0, 0.0], [-1.0, 0.0])
    assert score is not None
    assert 0.0 <= score <= 1.0
    assert score == pytest.approx(0.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# weighted_jaccard
# --------------------------------------------------------------------------- #
def test_skill_overlap_in_unit_range() -> None:
    assert 0.0 <= weighted_jaccard(["sql", "python"], ["sql", "python"]) <= 1.0
    # Full coverage scores higher than no coverage.
    full = weighted_jaccard(["sql", "python"], ["sql", "python"])
    none = weighted_jaccard(["java"], ["sql", "python"])
    assert full > none


def test_skill_overlap_no_requirements_is_neutral() -> None:
    assert weighted_jaccard(["anything"], []) == 0.5


# --------------------------------------------------------------------------- #
# salary_fit
# --------------------------------------------------------------------------- #
def test_salary_fit_in_unit_range_and_rewards_above_market() -> None:
    cand = _fake_candidate()
    above = salary_fit(_fake_job(comp_min=12000, comp_max=14000), cand, 8000)
    below = salary_fit(_fake_job(comp_min=4000, comp_max=5000), cand, 8000)
    for s in (above, below):
        assert 0.0 <= s <= 1.0
    assert above > below


def test_salary_fit_missing_data_is_neutral() -> None:
    cand = _fake_candidate()
    assert salary_fit(_fake_job(comp_min=None, comp_max=None), cand, None) == 0.5


# --------------------------------------------------------------------------- #
# blended score weights
# --------------------------------------------------------------------------- #
def test_weights_sum_to_one_so_blend_stays_in_unit_range() -> None:
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)
    # Any convex combination of in-range sub-scores stays in range.
    sub = {"semantic": 1.0, "skill_overlap": 0.0, "trajectory_fit": 0.5, "salary_fit": 0.25}
    blended = sum(sub[k] * WEIGHTS[k] for k in WEIGHTS)
    assert 0.0 <= blended <= 1.0


# --------------------------------------------------------------------------- #
# heuristic Glass Box
# --------------------------------------------------------------------------- #
def test_heuristic_glass_box_is_valid_and_grounded() -> None:
    sub_scores = {
        "semantic": 0.8,
        "skill_overlap": 0.6,
        "trajectory_fit": 0.4,
        "salary_fit": 0.9,
    }
    score = 0.7
    gb = _heuristic_glass_box(
        sub_scores=sub_scores,
        score=score,
        job=_fake_job(),
        have_skills=["sql", "python"],
    )
    assert isinstance(gb, GlassBox)
    assert 0.0 <= gb.confidence_score <= 1.0
    assert gb.confidence in (Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH)
    assert gb.rationale
    # It must surface the strongest and weakest components honestly.
    assert "salary fit" in gb.rationale  # strongest (0.9)
    assert "trajectory fit" in gb.rationale  # weakest (0.4)
    assert gb.citations and gb.what_would_change_this and gb.caveats
