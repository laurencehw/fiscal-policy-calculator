"""
Tests for the Phase E sectoral validation runners and benchmark provenance.

Two things are under test here:

1. The five sectoral runners (international, trade, pharma, IRS enforcement,
   climate) produce one scorecard entry per registered preset, read their
   targets from ``CBO_SCORE_MAP`` rather than restating them, and carry enough
   metadata for a reader to judge the benchmark.
2. Every calibrated-tier entry carries a ``provenance`` label, and the labels
   partition the tier exactly — so "n calibrated benchmarks" can never again be
   quoted without saying how many of those targets are actually table rows.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.app_data import CBO_SCORE_MAP  # noqa: E402
from fiscal_model.validation.provenance import (  # noqa: E402
    LINE_ITEM,
    MODEL_ESTIMATE,
    NON_PUBLISHED_BENCHMARK_IDS,
    PROVENANCE_LEVELS,
    SECONDHAND,
    UNCLASSIFIED,
    classify_provenance,
    is_round_hundred_scale,
)
from fiscal_model.validation.scorecard import (  # noqa: E402
    DEFAULT_RUNNERS,
    GENERIC_CATEGORY,
    compute_scorecard,
)
from fiscal_model.validation.specialized_sectoral import (  # noqa: E402
    SECTORAL_RUNNERS,
    SECTORAL_SCENARIO_REGISTRIES,
    official_target_for,
    validate_sectoral_policy,
)

SECTORAL_CATEGORIES = tuple(SECTORAL_SCENARIO_REGISTRIES)


@pytest.fixture(scope="module")
def scorecard():
    return compute_scorecard()


@pytest.fixture(scope="module")
def sectoral_results() -> dict[str, list]:
    """Every sectoral runner's output, run once for the module."""
    return {
        category: runner(verbose=False)
        for category, runner in SECTORAL_RUNNERS.items()
    }


# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_runner_returns_one_result_per_preset(category, sectoral_results):
    """A runner that silently drops a scenario would shrink the tier without
    anyone noticing, so assert the counts and the ids match the registry."""
    registry = SECTORAL_SCENARIO_REGISTRIES[category]
    results = sectoral_results[category]

    assert len(results) == len(registry)
    assert {r.policy_id for r in results} == set(registry)


def test_runners_cover_the_five_expected_families():
    assert set(SECTORAL_RUNNERS) == {
        "International",
        "Trade",
        "Pharma",
        "Enforcement",
        "Climate",
    }


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_every_scenario_points_at_a_preset_with_an_official_score(category):
    """Targets are read from ``CBO_SCORE_MAP``, never restated in the registry."""
    for scenario_id, scenario in SECTORAL_SCENARIO_REGISTRIES[category].items():
        preset = scenario["preset"]
        assert preset in CBO_SCORE_MAP, f"{scenario_id} points at an unknown preset"
        assert "expected_10yr" not in scenario, (
            f"{scenario_id} restates a target; sectoral scenarios must read "
            "CBO_SCORE_MAP so validation and the app cannot disagree."
        )
        assert official_target_for(scenario) == float(
            CBO_SCORE_MAP[preset]["official_score"]
        )


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_results_match_the_official_target_and_direction(category, sectoral_results):
    registry = SECTORAL_SCENARIO_REGISTRIES[category]
    for result in sectoral_results[category]:
        expected = official_target_for(registry[result.policy_id])
        assert result.official_10yr == expected
        # Every sectoral target is deficit-reducing and so is every model
        # score; a sign flip would mean the module and the target disagree
        # about what the policy even does.
        assert result.direction_match, f"{result.policy_id} flipped sign"


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_every_result_carries_source_date_and_provenance(category, sectoral_results):
    """Source, date and provenance are mandatory. A document URL is *not*:
    supplying one implies the number can be found in that document, and for
    these rounded headline targets it usually cannot. The next test makes that
    obligation explicit for the one label that does require a document."""
    registry = SECTORAL_SCENARIO_REGISTRIES[category]
    for result in sectoral_results[category]:
        scenario = registry[result.policy_id]
        assert result.official_source.strip()
        assert result.benchmark_date, f"{result.policy_id} has no benchmark date"
        assert scenario["provenance"] in PROVENANCE_LEVELS
        assert result.benchmark_kind == "Calibrated reconstruction"
        assert result.policy_name.strip()


def test_sectoral_urls_are_absolute_when_present(sectoral_results):
    seen_url = False
    for results in sectoral_results.values():
        for result in results:
            if result.benchmark_url:
                seen_url = True
                assert result.benchmark_url.startswith("https://")
    assert seen_url, "at least some sectoral entries should cite a document"


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_poor_results_are_documented(category, sectoral_results):
    """``readiness.py --strict`` hard-fails on an undocumented Poor in any
    tier, and a Poor without an explanation is useless to a reader anyway."""
    for result in sectoral_results[category]:
        if result.accuracy_rating == "Poor":
            assert result.known_limitations, (
                f"{result.policy_id} rates Poor with no known_limitations note"
            )


def test_unfitted_scenarios_are_the_ones_that_miss(sectoral_results):
    """Sanity check on the honesty of the ``calibrated_to_target`` flag: every
    Poor sectoral entry must be one the module was never fitted to. If a
    *fitted* one drifts to Poor, that is a regression and the readiness gate
    should be blocking on it."""
    for category, results in sectoral_results.items():
        registry = SECTORAL_SCENARIO_REGISTRIES[category]
        for result in results:
            if result.accuracy_rating == "Poor":
                assert not registry[result.policy_id]["calibrated_to_target"], (
                    f"{result.policy_id} is fitted to its target yet rates Poor"
                )


def test_sectoral_scores_do_not_depend_on_the_scorer_start_year(sectoral_results):
    """The suite scores on `_SCORER_START_YEAR` (2025, matching the policies'
    own start year and the FY2025-2034 window the targets are quoted for).

    All five modules build their effect paths from the policy's start year and
    their own duration, so the scorer's baseline window does not move any of
    these numbers. Pinned rather than assumed: if a module later becomes
    window-sensitive, the error against a FY2025-2034 target would silently
    shift and this catches it.
    """
    from fiscal_model.scoring import FiscalPolicyScorer

    alt = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    for category, results in sectoral_results.items():
        registry = SECTORAL_SCENARIO_REGISTRIES[category]
        for result in results:
            policy = registry[result.policy_id]["policy_factory"]()
            rescored = alt.score_policy(policy, dynamic=False).total_10_year_cost
            assert rescored == pytest.approx(result.model_10yr, rel=1e-9), (
                f"{result.policy_id} moved when the scorer's start year changed"
            )


def test_a_failing_scenario_becomes_an_error_row_not_a_missing_one(monkeypatch):
    """A runner that swallowed an exception would silently shrink the
    calibrated tier and hide the failure from the readiness gate. The row must
    survive with an ``Error`` rating, which readiness hard-fails on."""

    def _boom():
        raise RuntimeError("module exploded")

    monkeypatch.setitem(
        SECTORAL_SCENARIO_REGISTRIES["Trade"]["auto_tariff_25"],
        "policy_factory",
        _boom,
    )
    results = SECTORAL_RUNNERS["Trade"](verbose=False)

    assert len(results) == len(SECTORAL_SCENARIO_REGISTRIES["Trade"])
    failed = next(r for r in results if r.policy_id == "auto_tariff_25")
    assert failed.accuracy_rating == "Error"
    assert failed.known_limitations, "an Error row still needs a note"
    assert "module exploded" in failed.notes
    # The target stays readable even when the module is broken.
    assert failed.official_10yr == official_target_for(
        SECTORAL_SCENARIO_REGISTRIES["Trade"]["auto_tariff_25"]
    )
    assert not failed.direction_match
    # A zero model score against a non-zero target is a 100% miss. Reporting
    # 0.0 would let the failure count inside every accuracy band and pull the
    # tier mean down — the opposite of surfacing it.
    assert failed.abs_percent_difference == 100.0


def test_validate_sectoral_policy_rejects_unknown_inputs():
    with pytest.raises(ValueError, match="Unknown sectoral category"):
        validate_sectoral_policy("Nope", "whatever", verbose=False)
    with pytest.raises(ValueError, match="Unknown scenario"):
        validate_sectoral_policy("Trade", "not_a_scenario", verbose=False)


def test_official_target_for_rejects_a_preset_without_a_score():
    with pytest.raises(KeyError):
        official_target_for({"preset": "Not A Real Preset"})


# ---------------------------------------------------------------------------
# Scorecard registration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_runner_is_registered_in_the_scorecard(category, scorecard):
    assert DEFAULT_RUNNERS[category] is SECTORAL_RUNNERS[category]
    entries = [e for e in scorecard.entries if e.category == category]
    assert len(entries) == len(SECTORAL_SCENARIO_REGISTRIES[category])
    # Calibrated tier, not the out-of-sample one.
    assert all(e.category != GENERIC_CATEGORY for e in entries)


def test_sectoral_entries_are_in_the_calibrated_tier(scorecard):
    sectoral = [e for e in scorecard.entries if e.category in SECTORAL_CATEGORIES]
    assert len(sectoral) == sum(
        len(reg) for reg in SECTORAL_SCENARIO_REGISTRIES.values()
    )
    assert scorecard.calibrated_entries >= len(sectoral)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def test_every_entry_has_a_known_provenance_label(scorecard):
    for entry in scorecard.entries:
        assert entry.provenance in PROVENANCE_LEVELS


def test_provenance_counts_sum_to_the_calibrated_total(scorecard):
    """The whole point of the breakdown: it must partition the tier, so the
    headline count can never be quoted without its provenance split."""
    breakdown = scorecard.calibrated_provenance_breakdown
    assert set(breakdown) == set(PROVENANCE_LEVELS)
    assert sum(breakdown.values()) == scorecard.calibrated_entries
    assert scorecard.calibrated_entries == sum(
        1 for e in scorecard.entries if e.category != GENERIC_CATEGORY
    )


def test_published_and_model_estimate_counts_partition_the_tier(scorecard):
    assert (
        scorecard.calibrated_published_entries
        + scorecard.calibrated_model_estimate_entries
        == scorecard.calibrated_entries
    )
    assert (
        scorecard.calibrated_model_estimate_entries
        == scorecard.calibrated_provenance_breakdown[MODEL_ESTIMATE]
    )


def test_full_provenance_breakdown_sums_to_all_entries(scorecard):
    assert sum(scorecard.provenance_breakdown.values()) == scorecard.total_entries


def test_non_published_benchmarks_are_labelled_model_estimate(scorecard):
    """Plan §5.2: these are illustrations, not benchmarks. They stay in the
    scorecard, labelled, and out of the headline calibrated count."""
    by_id = {e.policy_id: e for e in scorecard.entries}
    for policy_id in NON_PUBLISHED_BENCHMARK_IDS:
        assert policy_id in by_id, f"{policy_id} disappeared from the scorecard"
        assert by_id[policy_id].provenance == MODEL_ESTIMATE


def test_tcja_full_extension_is_a_line_item(scorecard):
    """The single most load-bearing calibrated benchmark cites CBO's May 2024
    "Budgetary Outcomes Under Alternative Assumptions About Spending and
    Revenues" (publication 60271), so it is a line item — not one of the
    round-hundred summaries.

    Pinned deliberately: it used to point at publication 59710, which is the
    February 2024 *Budget and Economic Outlook* (the baseline the CBO options
    battery is scored against), not the source of the $4.6T figure."""
    entry = next(e for e in scorecard.entries if e.policy_id == "tcja_full_extension")
    assert entry.provenance == LINE_ITEM
    assert entry.benchmark_url == "https://www.cbo.gov/publication/60271"


def test_classify_declared_provenance_wins():
    assert (
        classify_provenance(
            policy_id="x",
            official_source="Congressional Budget Office",
            benchmark_url="https://www.cbo.gov/publication/1",
            official_10yr=-100.0,
            declared=SECONDHAND,
        )
        == SECONDHAND
    )


def test_classify_rejects_an_unknown_declared_label():
    with pytest.raises(ValueError, match="Unknown provenance"):
        classify_provenance(
            policy_id="x",
            official_source="CBO",
            official_10yr=-100.0,
            declared="hearsay",
        )


def test_classify_bare_domain_is_not_a_line_item():
    """A homepage is not a citation: the Warren/top-rate TPC targets carry a
    bare taxpolicycenter.org URL and must not be promoted to ``line_item``."""
    assert (
        classify_provenance(
            policy_id="x",
            official_source="Tax Policy Center",
            benchmark_url="https://www.taxpolicycenter.org/",
            official_10yr=-350.0,
        )
        == SECONDHAND
    )


def test_classify_deep_link_is_a_line_item():
    assert (
        classify_provenance(
            policy_id="x",
            official_source="Congressional Budget Office",
            benchmark_url="https://www.cbo.gov/budget-options/54788",
            official_10yr=-70.0,
        )
        == LINE_ITEM
    )


def test_classify_model_estimate_source():
    assert (
        classify_provenance(
            policy_id="x",
            official_source="Model estimate",
            official_10yr=350.0,
        )
        == MODEL_ESTIMATE
    )


def test_classify_falls_back_to_unclassified():
    """A non-round target with no URL is not guessed at — promoting it needs
    someone to find the table."""
    assert (
        classify_provenance(
            policy_id="x",
            official_source="U.S. Treasury",
            official_10yr=-1347.0,
        )
        == UNCLASSIFIED
    )


@pytest.mark.parametrize(
    "value,expected",
    [(450.0, True), (-2700.0, True), (-1200.0, True), (1347.0, False), (167.0, False)],
)
def test_round_hundred_scale_detection(value, expected):
    assert is_round_hundred_scale(value) is expected
