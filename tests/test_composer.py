"""
Tests for the Package Studio composer (fiscal_model/composer/composer.py).

The composer scores the whole preset revenue library on first use, so the
suite leans on its module-level cache: the first test that touches
``revenue_candidates()`` pays a couple of seconds and the rest are free.
Nothing here re-validates the scoring engine — these tests pin the
composer's own contract: determinism, sign conventions, sizing against the
deficit stance, philosophy separation, and graceful handling of presets
the distributional engine cannot represent.
"""

from __future__ import annotations

import pytest

from fiscal_model.composer.composer import (
    COVERAGE_TOLERANCE,
    INVEST_COVERAGE_SHARE,
    MAX_REVENUE_COMPONENTS,
    MIN_DEFICIT_REDUCTION_BILLIONS,
    OVERSHOOT_ALLOWANCE,
    WINDOW_YEARS,
    _build_caveats,
    _score_mix,
    compose_and_score,
    revenue_candidates,
    revenue_target_billions,
    top_quintile_burden_share,
)
from fiscal_model.composer.goal_spec import CANNED_GOAL_SPECS, GoalSpec, SpendingGoal
from fiscal_model.composer.progressivity import (
    INCIDENCE_FALLBACKS,
    incidence_family,
)

# A spec with real spending on both sides of the budget, reused so the
# philosophy comparisons all size against the same target.
SPENDING_GOALS = (
    SpendingGoal(label="Child care and pre-K", category="education", annual_billions=40.0),
    SpendingGoal(label="Infrastructure", category="infrastructure", annual_billions=60.0),
)


def _spec(philosophy: str, stance: str = "neutral", **kwargs) -> GoalSpec:
    return GoalSpec(
        revenue_philosophy=philosophy,
        deficit_stance=stance,
        spending_goals=SPENDING_GOALS,
        **kwargs,
    )


def _revenue_components(scored):
    return [c for c in scored.mix.components if c.kind == "revenue"]


def _spending_components(scored):
    return [c for c in scored.mix.components if c.kind == "spending"]


# ── Candidate library ───────────────────────────────────────────────────
def test_candidate_library_only_holds_revenue_raisers():
    candidates = revenue_candidates()

    assert candidates, "expected the preset library to yield revenue raisers"
    assert all(c.ten_year_billions < 0 for c in candidates)
    assert all(c.magnitude > 0 for c in candidates)
    assert "Custom Policy" not in {c.preset_name for c in candidates}
    assert all(len(c.deficit_path) == WINDOW_YEARS for c in candidates)


def test_candidate_library_is_memoized():
    assert revenue_candidates() is revenue_candidates()


def test_every_candidate_carries_a_top_quintile_share():
    for candidate in revenue_candidates():
        assert 0.0 <= candidate.top_quintile_share <= 1.0
        if not candidate.incidence.representable:
            # Unrepresentable presets must land on a documented fallback.
            assert candidate.incidence.family in INCIDENCE_FALLBACKS
            assert candidate.incidence.note


def test_incidence_family_classification():
    assert incidence_family({"is_payroll": True, "payroll_type": "donut_250k"}) == (
        "payroll_above_cap"
    )
    assert incidence_family({"is_payroll": True, "payroll_type": "expand_niit"}) == "niit"
    assert incidence_family({"is_estate": True}) == "estate"
    assert incidence_family({"is_corporate": True}) == "corporate"
    assert incidence_family({"is_international": True}) == "corporate"
    assert incidence_family({"is_trade": True}) == "consumption"
    assert incidence_family({"is_climate": True, "climate_type": "carbon_50"}) == "consumption"
    assert incidence_family({"is_climate": True, "climate_type": "repeal_ira"}) == "credit_repeal"
    assert incidence_family({"rate_change": 2.0}) == "unclassified"


# ── Determinism ─────────────────────────────────────────────────────────
def test_compose_is_deterministic():
    spec = _spec("progressive")

    first = compose_and_score(spec, n_mixes=3)
    second = compose_and_score(spec, n_mixes=3)

    assert [m.mix.name for m in first] == [m.mix.name for m in second]
    for left, right in zip(first, second):
        assert [c.label for c in left.mix.components] == [
            c.label for c in right.mix.components
        ]
        assert left.deficit_path_billions == right.deficit_path_billions
        assert left.ten_year_deficit_billions == right.ten_year_deficit_billions
        assert left.revenue_distribution_rows == right.revenue_distribution_rows
        assert left.caveats == right.caveats


def test_equal_specs_compose_identically():
    """Two separately built but equal specs must give the same mixes."""
    left = compose_and_score(_spec("mixed", "reduce"), n_mixes=3)
    right = compose_and_score(_spec("mixed", "reduce"), n_mixes=3)

    assert [
        (m.mix.name, tuple(c.label for c in m.mix.components)) for m in left
    ] == [(m.mix.name, tuple(c.label for c in m.mix.components)) for m in right]


# ── Shape and sign conventions ──────────────────────────────────────────
def test_mix_shape_matches_the_contract():
    for scored in compose_and_score(_spec("progressive"), n_mixes=3):
        assert len(scored.years) == WINDOW_YEARS
        assert len(scored.deficit_path_billions) == len(scored.years)
        assert scored.years == tuple(range(scored.years[0], scored.years[0] + WINDOW_YEARS))
        assert scored.mix.name and "$" not in scored.mix.name
        assert scored.mix.rationale.endswith(".")
        assert len(_revenue_components(scored)) <= MAX_REVENUE_COMPONENTS


def test_sign_conventions_are_deficit_convention():
    for scored in compose_and_score(_spec("progressive"), n_mixes=3):
        revenue = _revenue_components(scored)
        spending = _spending_components(scored)

        assert revenue, "a funded package needs revenue components"
        assert all(c.ten_year_billions < 0 for c in revenue)
        assert all(c.annual_billions < 0 for c in revenue)
        assert all(c.ten_year_billions > 0 for c in spending)
        assert all(c.annual_billions > 0 for c in spending)

        assert scored.revenue_10yr_billions < 0
        assert scored.spending_10yr_billions > 0
        assert scored.ten_year_deficit_billions == pytest.approx(
            scored.revenue_10yr_billions + scored.spending_10yr_billions, abs=1e-6
        )
        assert sum(scored.deficit_path_billions) == pytest.approx(
            scored.ten_year_deficit_billions, abs=1e-6
        )


def test_component_metadata_is_populated():
    scored = compose_and_score(_spec("progressive"), n_mixes=1)[0]

    for component in _revenue_components(scored):
        assert component.preset_name == component.label
        assert component.tier in {"calibrated", "generic"}
        if component.tier == "calibrated":
            # Scorecard-backed presets carry a live accuracy badge.
            assert component.validation_badge is not None
            assert "rating" in component.validation_badge

    for component in _spending_components(scored):
        assert component.preset_name is None
        assert component.tier == "spending"
        assert component.validation_badge is None


# ── Sizing against the deficit stance ───────────────────────────────────
def test_neutral_stance_covers_the_spending():
    for scored in compose_and_score(_spec("progressive", "neutral"), n_mixes=3):
        raised = abs(scored.revenue_10yr_billions)
        spending = scored.spending_10yr_billions
        assert raised >= spending * (1 - COVERAGE_TOLERANCE)
        assert raised <= spending * (1 + OVERSHOOT_ALLOWANCE)


def test_reduce_stance_raises_more_than_it_spends():
    spec = _spec("mixed", "reduce")
    for scored in compose_and_score(spec, n_mixes=3):
        # "reduce" is a floor, not a target: the mix must clear the
        # spending *and* the standing minimum net reduction.
        net_reduction = -scored.ten_year_deficit_billions
        assert net_reduction >= MIN_DEFICIT_REDUCTION_BILLIONS


def test_user_revenue_floor_is_a_floor():
    spec = _spec("progressive", "neutral", min_revenue_10yr_billions=4_000.0)
    for scored in compose_and_score(spec, n_mixes=3):
        assert abs(scored.revenue_10yr_billions) >= 4_000.0


def test_invest_stance_leaves_part_of_the_spending_unfunded():
    for scored in compose_and_score(_spec("progressive", "invest"), n_mixes=3):
        raised = abs(scored.revenue_10yr_billions)
        spending = scored.spending_10yr_billions
        assert raised < spending, "invest should not fully fund the spending"
        assert raised >= spending * INVEST_COVERAGE_SHARE * (1 - COVERAGE_TOLERANCE)


def test_revenue_target_respects_the_users_floor():
    spending = 1_000.0
    assert revenue_target_billions(
        GoalSpec(revenue_philosophy="mixed", deficit_stance="neutral"), spending
    ) == pytest.approx(spending)
    assert revenue_target_billions(
        GoalSpec(
            revenue_philosophy="mixed",
            deficit_stance="neutral",
            min_revenue_10yr_billions=3_000.0,
        ),
        spending,
    ) == pytest.approx(3_000.0)
    # "reduce" always clears the floor by at least the standing minimum.
    assert revenue_target_billions(
        GoalSpec(revenue_philosophy="mixed", deficit_stance="reduce"), spending
    ) == pytest.approx(spending + MIN_DEFICIT_REDUCTION_BILLIONS)


def test_spending_goal_without_a_size_is_still_scored():
    spec = GoalSpec(
        revenue_philosophy="mixed",
        deficit_stance="neutral",
        spending_goals=(SpendingGoal(label="Unsized program", category="other"),),
    )
    scored = compose_and_score(spec, n_mixes=1)[0]
    spending = _spending_components(scored)

    assert len(spending) == 1
    assert spending[0].ten_year_billions > 0


# ── Philosophy separation ───────────────────────────────────────────────
def test_progressive_is_more_top_heavy_than_broad_base():
    progressive = compose_and_score(_spec("progressive"), n_mixes=3)[0]
    broad_base = compose_and_score(_spec("broad_base"), n_mixes=3)[0]

    progressive_share = top_quintile_burden_share(progressive.mix.components)
    broad_base_share = top_quintile_burden_share(broad_base.mix.components)

    assert progressive_share > broad_base_share
    assert progressive.mix.name == "Top-heavy"
    assert broad_base.mix.name == "Broader base"


def test_corporate_philosophy_leads_with_corporate_side_raisers():
    scored = compose_and_score(_spec("corporate"), n_mixes=1)[0]
    by_name = {c.preset_name: c for c in revenue_candidates()}

    assert scored.mix.name == "With corporate"
    leading = _revenue_components(scored)[0]
    assert by_name[leading.preset_name].incidence.is_corporate


def test_each_philosophy_yields_distinct_variants():
    for philosophy in ("progressive", "broad_base", "corporate", "mixed"):
        mixes = compose_and_score(_spec(philosophy), n_mixes=3)
        assert len(mixes) == 3
        names = [m.mix.name for m in mixes]
        assert len(set(names)) == len(names)
        selections = [
            frozenset(c.label for c in _revenue_components(m)) for m in mixes
        ]
        assert len(set(selections)) == len(selections)
        assert all(m.mix.rationale for m in mixes)


# ── Distribution rows and caveats ───────────────────────────────────────
def test_distribution_rows_are_display_ready():
    scored = compose_and_score(_spec("progressive"), n_mixes=1)[0]
    rows = scored.revenue_distribution_rows

    assert rows, "the top-heavy mix should have representable components"
    assert list(rows[0]) == ["Income Group", "Tax Change ($B)", "Share of Total"]
    assert [row["Income Group"] for row in rows][-1] == "Top Quintile"
    assert sum(row["Share of Total"] for row in rows) == pytest.approx(100.0, abs=0.5)
    assert all(isinstance(row["Tax Change ($B)"], float) for row in rows)


def test_every_mix_carries_the_standing_caveats():
    for philosophy in ("progressive", "broad_base", "corporate", "mixed"):
        for scored in compose_and_score(_spec(philosophy), n_mixes=3):
            joined = " ".join(scored.caveats)
            assert "scored independently" in joined
            assert "revenue side only" in joined
            assert "Spending incidence is not modeled" in joined


def test_unrepresentable_component_is_caveated_not_crashed():
    """Payroll, estate and tariff presets return no household rows."""
    unrepresentable = [c for c in revenue_candidates() if not c.incidence.representable]
    assert unrepresentable, "expected some presets the engine cannot represent"

    candidate = unrepresentable[0]
    scored = _score_mix(
        name="Unrepresentable only",
        rationale="Single component the distributional engine cannot place.",
        chosen=[candidate],
        spending_components=[],
        spending_paths=[],
        target_billions=candidate.magnitude,
    )

    assert scored.revenue_distribution_rows == ()
    assert scored.ten_year_deficit_billions == pytest.approx(candidate.ten_year_billions)
    joined = " ".join(scored.caveats)
    assert "no household rows" in joined
    assert candidate.preset_name.replace("$", "\\$") in joined


def test_caveats_flag_an_uncoverable_target():
    candidate = min(revenue_candidates(), key=lambda c: c.magnitude)
    caveats = _build_caveats(
        chosen=[candidate],
        spending_components=[],
        unrepresented=[],
        revenue_10yr=candidate.ten_year_billions,
        target_billions=candidate.magnitude * 10,
    )

    assert any("closes the gap more precisely" in caveat for caveat in caveats)


def test_caveats_are_markdown_safe():
    """Two raw ``$`` in one string render as LaTeX in Streamlit markdown."""
    for philosophy in ("progressive", "broad_base", "corporate", "mixed"):
        for scored in compose_and_score(_spec(philosophy), n_mixes=3):
            for text in (*scored.caveats, scored.mix.rationale):
                unescaped = [
                    index
                    for index, char in enumerate(text)
                    if char == "$" and (index == 0 or text[index - 1] != "\\")
                ]
                assert len(unescaped) <= 1, text


# ── Edge cases ──────────────────────────────────────────────────────────
def test_invalid_spec_is_rejected():
    with pytest.raises(ValueError, match="unknown revenue_philosophy"):
        compose_and_score(
            GoalSpec(revenue_philosophy="anarchist", deficit_stance="neutral")
        )


def test_n_mixes_is_respected():
    assert compose_and_score(_spec("progressive"), n_mixes=1).__len__() == 1
    assert compose_and_score(_spec("progressive"), n_mixes=0) == []


def test_spec_with_no_target_returns_an_empty_package_not_a_crash():
    """Neutral stance with nothing to fund implies no revenue is needed."""
    mixes = compose_and_score(
        GoalSpec(revenue_philosophy="mixed", deficit_stance="neutral"), n_mixes=3
    )

    assert len(mixes) == 1
    assert mixes[0].mix.components == ()
    assert mixes[0].ten_year_deficit_billions == pytest.approx(0.0)
    assert len(mixes[0].deficit_path_billions) == WINDOW_YEARS


@pytest.mark.parametrize("label", sorted(CANNED_GOAL_SPECS))
def test_canned_specs_compose(label):
    mixes = compose_and_score(CANNED_GOAL_SPECS[label], n_mixes=3)

    assert 1 <= len(mixes) <= 3
    for scored in mixes:
        assert scored.mix.components
        assert len(scored.deficit_path_billions) == len(scored.years)
