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
from fiscal_model.validation.benchmark_sources import (  # noqa: E402
    BENCHMARK_SOURCES,
    CONFIRMATION_TOLERANCE_PCT,
    provenance_for,
    source_for,
)
from fiscal_model.validation.provenance import (  # noqa: E402
    LINE_ITEM,
    LINE_ITEM_DIFFERS,
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


#: The one sectoral row where the module and its stored target legitimately
#: disagree about direction, because the *target* points the wrong way.
#: ``benchmark_sources.py`` records it as ``line_item_differs``: CBO scores a
#: $35 insulin cost-sharing cap extended to private plans at +$6.566B of outlays
#: and -$4.793B of revenues over FY2022-2031 — about +$11.4B **added** to the
#: deficit (publication 57957) — against the -$15B of savings the repository
#: carries. Lane L7 fixed the module side; moving the target is provenance work
#: through the manifest's ``superseded_by`` rule. Until that lands, requiring
#: this row to point the same way as its benchmark would require the module to
#: be wrong on purpose.
KNOWN_TARGET_SIGN_INVERSIONS = {"universal_insulin_cap"}


@pytest.mark.parametrize("category", SECTORAL_CATEGORIES)
def test_results_match_the_official_target_and_direction(category, sectoral_results):
    registry = SECTORAL_SCENARIO_REGISTRIES[category]
    for result in sectoral_results[category]:
        expected = official_target_for(registry[result.policy_id])
        assert result.official_10yr == expected
        if result.policy_id in KNOWN_TARGET_SIGN_INVERSIONS:
            continue
        # Every other sectoral target is deficit-reducing and so is every model
        # score; a sign flip would mean the module and the target disagree
        # about what the policy even does.
        assert result.direction_match, f"{result.policy_id} flipped sign"


def test_the_insulin_cap_is_the_only_sign_disagreement_and_it_agrees_with_cbo():
    """Pin the exception so it cannot quietly grow to cover a real regression.

    Two claims: exactly one sectoral row disagrees with its target on sign, and
    that row disagrees in the direction CBO's own estimate points — a
    cost-sharing cap *adds* to the deficit. Any second row flipping sign, or
    this one flipping back to a modelled saving, fails here.
    """
    flipped = {
        result.policy_id
        for results in (
            validate_sectoral_policy(category, scenario_id, verbose=False)
            for category in SECTORAL_CATEGORIES
            for scenario_id in SECTORAL_SCENARIO_REGISTRIES[category]
        )
        for result in (results,)
        if not result.direction_match
    }
    assert flipped == KNOWN_TARGET_SIGN_INVERSIONS

    insulin = validate_sectoral_policy("Pharma", "universal_insulin_cap", verbose=False)
    assert insulin.official_10yr < 0, "the stored target still reads as a saving"
    assert insulin.model_10yr > 0, (
        "the module must score an insulin cost-sharing cap as widening the "
        "deficit, the direction CBO publication 57957 scores it"
    )


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
        assert "provenance" not in scenario, (
            f"{result.policy_id} restates its provenance in the scenario "
            "registry; provenance lives only in benchmark_sources.py"
        )
        assert provenance_for(result.policy_id) in PROVENANCE_LEVELS
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


def test_social_security_fairness_cites_the_right_bill():
    """The record used to point at publication 59434 — CBO's estimate of
    H.R. 3938, the Build It in America Act, which has nothing to do with
    WEP/GPO. The $196B is a rounding of the $195.65B WEP/GPO repeal component
    in CBO's 9 September 2024 estimate of H.R. 82, and the citation must say
    so. Pinned because a plausible-looking cbo.gov link is exactly the kind of
    error nothing else notices."""
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES
    from fiscal_model.validation.preregistered import get_case

    record = KNOWN_SCORES["social_security_fairness_2023"]
    assert record.source_url == "https://www.cbo.gov/system/files/2024-09/hr82.pdf"
    assert record.source_date == "2024-09"
    assert record.ten_year_cost == 196.0
    assert "195.65" in record.notes

    # The manifest row and the score record must cite the same document; the
    # pre-registered target is the unrounded figure the same estimate states.
    case = get_case("ssfa_wep_gpo_repeal_outlays")
    assert case.source_url == record.source_url
    assert case.official_10yr_billions == 195.65


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


# ---------------------------------------------------------------------------
# Phase E provenance pass — the transcription registry
#
# The Phase E *labelling* pass could tell a rounded headline from a table row
# by inspecting the record. It could not tell whether the row exists. These
# tests guard the pass that went and looked.
# ---------------------------------------------------------------------------


def test_no_calibrated_entry_is_unclassified(scorecard):
    """``unclassified`` means "nobody has looked". After the sourcing pass no
    calibrated benchmark may be in that state: a target is either transcribed,
    or it carries a record of what was searched and not found."""
    unclassified = [
        e.policy_id
        for e in scorecard.entries
        if e.category != GENERIC_CATEGORY and e.provenance == UNCLASSIFIED
    ]
    assert unclassified == []
    assert scorecard.calibrated_provenance_breakdown[UNCLASSIFIED] == 0


#: Calibrated benchmarks still labelled ``line_item`` by *inference* — they
#: cite a deep link to a real document, and the Phase E labelling pass took
#: that as evidence of a table row, but nobody has opened the document and read
#: the row. They are the remaining backlog for the sourcing pass and the set
#: may shrink, never grow. (The CBO-options entries are excluded separately:
#: those *were* transcribed, by scripts/extract_cbo_options.py, with report and
#: PDF page numbers recorded in the CSV and the pre-registration manifest.)
CITED_BUT_NOT_TRANSCRIBED = {
    "tcja_full_extension",  # CBO pub 60271; cbo.gov blocks non-browser clients
    "cbo_2pp_all_brackets",  # CBO budget-options 54788
    "pwbm_39_with_stepup",  # PWBM April 2021 brief
    "pwbm_39_no_stepup",  # PWBM April 2021 brief
    # Phase D's three enacted-law components. Their targets are unrounded to
    # three decimals and their manifest notes quote the estimates' own outlay
    # paths, so the Phase D lane plainly read the tables — but the sourcing pass
    # could not re-read them to record a row (all three deep links return HTTP
    # 403 to every non-browser client, checked again on 2026-09-01), and this
    # registry only records what was actually opened. They stay `line_item` on
    # the strength of the deep link and join the backlog.
    "ssfa_wep_gpo_repeal_outlays",  # CBO, H.R. 82 (2024-09)
    "fra_2023_discretionary_caps",  # CBO, H.R. 3746 letter to Speaker McCarthy
    "iija_2021_discretionary",  # CBO, H.R. 3684 / S.Amdt. 2137
}


def test_pl119_21_sources_match_the_transcribed_csv():
    """The P.L. 119-21 provenance records restate figures that live in
    ``pl119_21_jct_line_items.csv``, which is where the runner reads its
    targets. Two copies of a transcribed number is one copy too many unless
    something checks them, so this does."""
    from fiscal_model.validation.specialized_pl119_21 import (
        PL119_21_LINE_ITEMS,
        mapped_line_items,
    )

    by_id = {item.provision_id: item for item in PL119_21_LINE_ITEMS}
    mapped = {item.provision_id for item in mapped_line_items()}
    sourced = {s.policy_id for s in BENCHMARK_SOURCES if s.policy_id in by_id}
    assert sourced == mapped, (
        "every mapped JCT line item needs a provenance record, and only the "
        f"mapped ones may have one; symmetric difference {sourced ^ mapped}"
    )

    for policy_id in mapped:
        item = by_id[policy_id]
        source = source_for(policy_id)
        assert source.provenance == LINE_ITEM
        assert source.published_10yr_billions == item.deficit_effect_10yr_billions
        assert source.page == f"PDF p. {item.pdf_page}"
        assert item.provision in source.row
        assert f"(item {item.jct_item})" in source.row
        assert item.chapter in source.table


def test_transcribed_entries_cite_a_document(scorecard):
    """A transcription is a claim that somebody opened a document and read a
    row. Without a URL, a date and a table reference it is unverifiable, and no
    better than the rounded headline it replaced."""
    for entry in scorecard.entries:
        if not entry.transcribed:
            continue
        assert entry.benchmark_url, f"{entry.policy_id}: transcribed with no URL"
        assert entry.benchmark_url.startswith("https://")
        assert entry.benchmark_date, f"{entry.policy_id}: transcribed with no date"
        assert entry.benchmark_table, (
            f"{entry.policy_id}: transcribed with no table/row reference"
        )
        assert entry.sourcing_note, f"{entry.policy_id}: transcribed with no note"


def test_untranscribed_line_items_are_a_named_backlog(scorecard):
    """``line_item`` without a transcription is the weakest thing the scorecard
    says, so the set that is in that state is enumerated rather than inferred.
    Every such entry must still carry a real document link and date."""
    inferred = {
        e.policy_id
        for e in scorecard.entries
        if e.provenance in (LINE_ITEM, LINE_ITEM_DIFFERS)
        and not e.transcribed
        and not e.policy_id.startswith("cbo_opt")
    }
    assert inferred <= CITED_BUT_NOT_TRANSCRIBED, (
        f"new untranscribed line_item entries: {sorted(inferred - CITED_BUT_NOT_TRANSCRIBED)}"
    )
    by_id = {e.policy_id: e for e in scorecard.entries}
    for policy_id in inferred:
        entry = by_id[policy_id]
        assert entry.benchmark_url and entry.benchmark_url.startswith("https://")
        assert entry.benchmark_date


def test_line_item_differs_carries_the_published_figure(scorecard):
    """The point of the label: the gap has to be *visible*. A row that
    disagrees with its source but does not say by how much has hidden the one
    thing the pass was run to surface."""
    differs = [e for e in scorecard.entries if e.provenance == LINE_ITEM_DIFFERS]
    assert differs, "expected at least one transcription to disagree"
    for entry in differs:
        published = entry.official_10yr_billions_line_item
        assert published is not None
        gap = abs(published - entry.official_10yr_billions) / max(abs(published), 1e-9)
        assert gap * 100 > CONFIRMATION_TOLERANCE_PCT, (
            f"{entry.policy_id} is labelled line_item_differs but its published "
            f"figure {published} is within rounding of the carried target "
            f"{entry.official_10yr_billions}"
        )


def test_confirmed_line_items_agree_with_their_source(scorecard):
    """The mirror image: a ``line_item`` row must sit within the rounding
    tolerance of the figure transcribed for it, or the label is a quiet way of
    adopting a number the document does not support."""
    for entry in scorecard.entries:
        if entry.provenance != LINE_ITEM:
            continue
        source = source_for(entry.policy_id)
        if source is None or source.published_10yr_billions is None:
            continue
        published = source.published_10yr_billions
        gap = abs(published - entry.official_10yr_billions) / max(abs(published), 1e-9)
        assert gap * 100 <= CONFIRMATION_TOLERANCE_PCT, (
            f"{entry.policy_id}: target {entry.official_10yr_billions} is "
            f"{gap * 100:.1f}% from the transcribed {published}; that is a "
            "line_item_differs, not a confirmation"
        )


def test_target_values_were_not_moved_to_match_a_transcription(scorecard):
    """A sourcing pass records disagreements; it does not resolve them by
    editing a calibrated target. Every calibrated target has a module constant
    fitted to it, so moving one silently turns a 0% row into a miss that says
    nothing about the model."""
    for entry in scorecard.entries:
        if entry.official_10yr_billions_line_item is None:
            continue
        assert entry.official_10yr_billions != entry.official_10yr_billions_line_item


def test_secondhand_rows_record_what_was_searched():
    """"Not located" is a finding and has to be written down, so the next
    person does not repeat the search."""
    for source in BENCHMARK_SOURCES:
        if source.provenance != SECONDHAND:
            continue
        assert len(source.searched.strip()) > 80, (
            f"{source.policy_id}: left secondhand with no real search record"
        )


def test_registry_covers_every_calibrated_benchmark(scorecard):
    """Coverage is the claim being made — "we went through all of them" — so it
    is asserted rather than counted by hand."""
    calibrated = {
        e.policy_id for e in scorecard.entries if e.category != GENERIC_CATEGORY
    }
    covered = {s.policy_id for s in BENCHMARK_SOURCES}
    uncovered = calibrated - covered - CITED_BUT_NOT_TRANSCRIBED
    assert uncovered == set(), f"not sourced: {sorted(uncovered)}"


def test_headline_counts_exclude_the_illustrations(scorecard):
    """``published_entries`` is what the footer, the README and the docs quote;
    ``total_entries`` additionally includes rows with no official score.

    ``unclassified`` is excluded too. "No published score exists" and "nobody
    has established whether one exists" are different states, and neither
    belongs in a count captioned "against a published figure" — so if a future
    benchmark lands unclassified, the headline shrinks until someone sources
    it. The bucket is empty today, which is what the partition below asserts.
    """
    assert (
        scorecard.published_entries
        + scorecard.model_estimate_entries
        + scorecard.provenance_breakdown[UNCLASSIFIED]
        == scorecard.total_entries
    )
    assert scorecard.model_estimate_entries > 0
    assert scorecard.published_entries == sum(
        1
        for e in scorecard.entries
        if e.provenance not in (MODEL_ESTIMATE, UNCLASSIFIED)
    )
    for policy_id in NON_PUBLISHED_BENCHMARK_IDS:
        entry = next(e for e in scorecard.entries if e.policy_id == policy_id)
        assert entry.provenance == MODEL_ESTIMATE


def test_ui_tables_partition_the_scorecard_the_same_way_the_counts_do(scorecard):
    """The Validation tab's accessors must slice the scorecard exactly the way
    :class:`ScorecardSummary` counts it.

    The tab's ``published_entries`` used to exclude only ``model_estimate``,
    so an ``unclassified`` row would have been rendered inside the table
    captioned "against a published figure" while the count printed beside it
    excluded that row — the metrics and their own caption would have been
    describing different sets. Pinned row-for-row, not merely by count.
    """
    from fiscal_model.ui.tabs.validation_scorecard import (
        illustration_entries,
        published_entries,
        unsourced_entries,
    )

    buckets = {
        "published": published_entries(scorecard),
        "illustrations": illustration_entries(scorecard),
        "unsourced": unsourced_entries(scorecard),
    }

    assert len(buckets["published"]) == scorecard.published_entries
    assert len(buckets["illustrations"]) == scorecard.model_estimate_entries
    assert len(buckets["unsourced"]) == scorecard.provenance_breakdown[UNCLASSIFIED]
    assert sum(len(g) for g in buckets.values()) == scorecard.total_entries

    for entry in scorecard.entries:
        hits = [
            name
            for name, group in buckets.items()
            if any(e is entry for e in group)
        ]
        assert hits == [
            "published"
            if entry.provenance not in (MODEL_ESTIMATE, UNCLASSIFIED)
            else "illustrations"
            if entry.provenance == MODEL_ESTIMATE
            else "unsourced"
        ], f"{entry.policy_id} ({entry.provenance}) landed in {hits}"


def test_transcribed_rows_name_the_row_not_just_the_table(scorecard):
    """A table reference without the row inside it is not checkable, which is
    exactly what the ``line_item`` label claims to be."""
    for source in BENCHMARK_SOURCES:
        if source.provenance not in (LINE_ITEM, LINE_ITEM_DIFFERS):
            continue
        assert source.row and source.row.strip(), (
            f"{source.policy_id}: transcribed with a table but no row label"
        )


def test_transcribed_and_differs_counts_match_the_entries(scorecard):
    assert scorecard.transcribed_entries == sum(
        1 for e in scorecard.entries if e.transcribed
    )
    assert scorecard.line_item_differs_entries == sum(
        1 for e in scorecard.entries if e.provenance == LINE_ITEM_DIFFERS
    )
    # Transcribed is deliberately the stricter count: it is a subset of the
    # rows labelled line_item / line_item_differs, because a deep link is a
    # document and not a row.
    labelled = sum(
        1 for e in scorecard.entries if e.provenance in (LINE_ITEM, LINE_ITEM_DIFFERS)
    )
    assert scorecard.transcribed_entries < labelled


def test_illustrative_distributional_benchmarks_are_not_counted():
    """Plan §5.2's other two non-published benchmarks. They stay runnable and
    visible; they simply may not be counted as published tables."""
    from fiscal_model.validation.distributional_validation import (
        DISTRIBUTIONAL_BENCHMARKS,
        ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS,
        PUBLISHED_DISTRIBUTIONAL_BENCHMARKS,
    )
    from fiscal_model.validation.provenance import (
        NON_PUBLISHED_DISTRIBUTIONAL_BENCHMARKS,
    )

    published = set(PUBLISHED_DISTRIBUTIONAL_BENCHMARKS)
    illustrative = set(ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS)
    assert published | illustrative == set(DISTRIBUTIONAL_BENCHMARKS)
    assert published & illustrative == set()
    assert {
        b.name for b in ILLUSTRATIVE_DISTRIBUTIONAL_BENCHMARKS.values()
    } == set(NON_PUBLISHED_DISTRIBUTIONAL_BENCHMARKS)
    assert len(published) == 2


def test_tariff_presets_join_their_official_score():
    """Two ``CBO_SCORE_MAP`` keys were spelled differently from their
    ``PRESET_POLICIES`` counterparts, so the app showed no official score for
    either preset. Pinned here because the join is by label string and nothing
    else would notice it breaking again."""
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.preset_ids import PRESET_ID_BY_LABEL

    for label in (
        "\U0001f3ed 25% Steel/Aluminum Tariff (-$60B)",
        "\U0001f3ed Reciprocal Tariffs (-$1.2T)",
    ):
        assert label in CBO_SCORE_MAP, f"{label} lost its official score"
        assert label in PRESET_POLICIES, f"{label} lost its preset row"
        assert label in PRESET_ID_BY_LABEL


def test_no_score_map_key_shadows_a_preset_under_another_spelling():
    """The general form of the same bug: every ``CBO_SCORE_MAP`` label that
    resolves to a catalog preset id must *be* that preset's own label."""
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.preset_ids import PRESET_ID_BY_LABEL

    label_by_id = {pid: label for label, pid in PRESET_ID_BY_LABEL.items()}
    for label in CBO_SCORE_MAP:
        preset_id = PRESET_ID_BY_LABEL.get(label)
        if preset_id is None:
            continue
        assert label_by_id[preset_id] == label
        assert label in PRESET_POLICIES
