"""
Tests for the consolidated revenue-level validation scorecard.

These tests pin the contract (entry shape, summary stats, category rollup)
without asserting exact accuracy numbers — those vary as the model and
benchmark database evolve. The point is to catch silent regressions in
which categories are exercised and that the summary math is internally
consistent with the per-entry rows.
"""

from __future__ import annotations

import pytest

from fiscal_model.validation import compute_scorecard
from fiscal_model.validation.core import ValidationResult
from fiscal_model.validation.scorecard import (
    DEFAULT_RUNNERS,
    ScorecardEntry,
    ScorecardSummary,
    _percentile,
    scorecard_to_dict,
)


def _stub_result(
    policy_id: str = "stub",
    *,
    official: float = 100.0,
    model: float = 105.0,
    rating: str = "Excellent",
    direction_match: bool = True,
    limitations: list[str] | None = None,
) -> ValidationResult:
    diff = model - official
    pct = (diff / abs(official)) * 100.0 if official else 0.0
    return ValidationResult(
        policy_id=policy_id,
        policy_name=policy_id.replace("_", " ").title(),
        official_10yr=official,
        official_source="Stub Source",
        model_10yr=model,
        model_first_year=model / 10.0,
        difference=diff,
        percent_difference=pct,
        direction_match=direction_match,
        accuracy_rating=rating,
        notes="",
        benchmark_kind="Test",
        benchmark_date="2025-01",
        benchmark_url="https://example.test/score",
        known_limitations=list(limitations or []),
    )


def _runner(*results: ValidationResult):
    def _fn(verbose: bool = False) -> list[ValidationResult]:
        return list(results)
    return _fn


@pytest.fixture
def synthetic_runners():
    """Three categories with known shapes to make assertions deterministic."""
    return {
        "Excellent": _runner(
            _stub_result("a", model=101, official=100, rating="Excellent"),
            _stub_result("b", model=104, official=100, rating="Excellent"),
        ),
        "Acceptable": _runner(
            _stub_result("c", model=115, official=100, rating="Acceptable"),
        ),
        "Poor": _runner(
            _stub_result("d", model=200, official=100, rating="Poor",
                         limitations=["base data too coarse"]),
        ),
    }


def test_compute_scorecard_aggregates_all_runners(synthetic_runners):
    summary = compute_scorecard(runners=synthetic_runners)

    assert summary.total_entries == 4
    assert {e.policy_id for e in summary.entries} == {"a", "b", "c", "d"}
    # Within-bucket counts sum coherently with the per-entry abs diffs.
    abs_diffs = [e.abs_percent_difference for e in summary.entries]
    assert summary.within_5pct == sum(1 for d in abs_diffs if d <= 5.0)
    assert summary.within_15pct == sum(1 for d in abs_diffs if d <= 15.0)
    assert summary.within_20pct == sum(1 for d in abs_diffs if d <= 20.0)
    assert summary.within_5pct <= summary.within_10pct <= summary.within_15pct <= summary.within_20pct


def test_compute_scorecard_per_category_rollup(synthetic_runners):
    summary = compute_scorecard(runners=synthetic_runners)

    assert summary.by_category["Excellent"]["n"] == 2
    assert summary.by_category["Acceptable"]["n"] == 1
    assert summary.by_category["Poor"]["n"] == 1
    # Each category's mean equals the unweighted mean of its entries.
    excellent_diffs = [e.abs_percent_difference for e in summary.entries if e.category == "Excellent"]
    expected = sum(excellent_diffs) / len(excellent_diffs)
    assert summary.by_category["Excellent"]["mean_abs_percent_difference"] == pytest.approx(expected)


def test_ratings_breakdown_matches_entries(synthetic_runners):
    summary = compute_scorecard(runners=synthetic_runners)

    counted = {}
    for e in summary.entries:
        counted[e.rating] = counted.get(e.rating, 0) + 1
    assert summary.ratings_breakdown == counted


def test_known_limitations_propagate(synthetic_runners):
    summary = compute_scorecard(runners=synthetic_runners)
    poor = next(e for e in summary.entries if e.policy_id == "d")
    assert poor.known_limitations == ["base data too coarse"]


def test_scorecard_to_dict_is_json_serializable(synthetic_runners):
    import json

    summary = compute_scorecard(runners=synthetic_runners)
    payload = scorecard_to_dict(summary)
    # Must round-trip through JSON without a custom encoder.
    json.dumps(payload)
    assert payload["total_entries"] == 4
    assert isinstance(payload["entries"], list)
    assert payload["entries"][0]["policy_id"] in {"a", "b", "c", "d"}


def test_default_runners_is_a_dict_of_callables():
    assert isinstance(DEFAULT_RUNNERS, dict)
    assert DEFAULT_RUNNERS  # non-empty
    for cat, fn in DEFAULT_RUNNERS.items():
        assert callable(fn), f"Runner for category {cat!r} is not callable"


def test_real_scorecard_entries_carry_required_fields():
    """The real scorecard produces entries with the contract fields populated."""
    summary = compute_scorecard()
    assert summary.total_entries > 0
    assert isinstance(summary, ScorecardSummary)
    for e in summary.entries:
        assert isinstance(e, ScorecardEntry)
        assert e.category in DEFAULT_RUNNERS
        assert e.policy_id and e.policy_name
        assert e.rating in {"Excellent", "Good", "Acceptable", "Poor", "Error"}
        assert e.abs_percent_difference >= 0


def test_percentile_handles_edges():
    assert _percentile([], 50.0) == 0.0
    assert _percentile([42.0], 50.0) == 42.0
    assert _percentile([0.0, 10.0], 50.0) == pytest.approx(5.0)
    assert _percentile([0.0, 10.0, 20.0, 30.0], 50.0) == pytest.approx(15.0)


def test_cached_default_scorecard_memoizes_compute():
    """Second call must hit the lru_cache rather than recomputing 33+
    specialized validators. The API endpoint and Streamlit Validation
    tab depend on this — without it, every user interaction or request
    would burn ~50ms of CPU and amplify any DoS attempt."""
    from fiscal_model.validation import (
        cached_default_scorecard,
        reset_scorecard_cache,
    )
    from fiscal_model.validation.scorecard import cached_default_scorecard as direct

    reset_scorecard_cache()
    info_before = direct.cache_info()
    first = cached_default_scorecard()
    second = cached_default_scorecard()
    info_after = direct.cache_info()

    # Same object identity — cache hit, not a fresh recompute.
    assert first is second
    assert info_after.misses == info_before.misses + 1
    assert info_after.hits == info_before.hits + 1


def test_reset_scorecard_cache_forces_recompute():
    from fiscal_model.validation import (
        cached_default_scorecard,
        reset_scorecard_cache,
    )
    from fiscal_model.validation.scorecard import cached_default_scorecard as direct

    cached_default_scorecard()  # warm the cache
    info_warm = direct.cache_info()
    assert info_warm.currsize >= 1

    reset_scorecard_cache()
    info_cleared = direct.cache_info()
    assert info_cleared.currsize == 0
