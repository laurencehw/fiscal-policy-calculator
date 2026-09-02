"""
Tests for the AMT module's derived (structural) scoring path — lane L5.

What these lock down:

- **The published path is transcribed faithfully.** Every year of TPC
  T25-0049 loads, and the payer count reconstructed from revenue divided by
  revenue-per-payer agrees with TPC's own rounded count.
- **Derived mode reproduces that path exactly.** Repealing the individual AMT
  from 2026 must score, year by year, the table's own revenue column — no
  smoothing, no re-growth.
- **The engine coupling is pinned.** Derived mode divides the scoring engine's
  uniform growth back out, so the constant it divides by has to equal the one
  the engine applies.
- **The dead exemption branch is alive.** Raising the exemption must lose
  revenue and lower it must raise revenue; both used to score exactly zero.
- **Reported mode did not move.** Every shipped preset scores what it scored
  before the lane.
"""

from __future__ import annotations

import pytest

from fiscal_model.amt import (
    AMT_APP_MODE,
    AMT_ENGINE_GROWTH_RATE,
    AMT_HELD_OUT_MODE,
    AMT_MODE_DERIVED,
    AMT_MODE_REPORTED,
    AMT_SCORECARD_MODE,
    REGIME_POST_SUNSET,
    REGIME_TCJA,
    AMTPolicy,
    AMTType,
    amt_payers_and_liability,
    amt_regime_year,
    amt_revenue_billions,
    create_amt_rate_change,
    create_extend_tcja_amt_relief,
    create_increase_amt_exemption,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
    current_law_amt_exemption_mfj,
    load_tpc_amt_projections,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


def _score(policy) -> object:
    return FiscalPolicyScorer(
        start_year=policy.start_year,
        use_real_data=False,
    ).score_policy(policy, dynamic=False)


# ---------------------------------------------------------------------------
# The transcribed path
# ---------------------------------------------------------------------------


def test_published_path_covers_the_scoring_windows():
    rows = load_tpc_amt_projections()
    assert set(rows) == set(range(2024, 2036))
    assert {rows[2024].regime, rows[2025].regime} == {REGIME_TCJA}
    assert all(rows[year].regime == REGIME_POST_SUNSET for year in range(2026, 2036))


def test_reconstructed_payers_match_tpcs_rounded_count():
    """
    The payer count is rebuilt from revenue / revenue-per-payer because TPC
    rounds its own count column to one decimal of a million. The rebuild must
    still land inside that rounding.
    """
    for row in load_tpc_amt_projections().values():
        assert row.payers / 1e6 == pytest.approx(
            row.printed_payers_millions, abs=0.06
        ), f"{row.year}: {row.payers / 1e6:.3f}M vs printed {row.printed_payers_millions}M"


def test_the_sunset_is_a_cliff_and_the_path_then_grows():
    """
    The finding that overturned the plan's ramp hypothesis, pinned so a future
    data refresh cannot quietly reintroduce it.
    """
    rows = load_tpc_amt_projections()
    assert rows[2026].payers > 25 * rows[2025].payers
    revenues = [rows[year].revenue_billions for year in range(2026, 2036)]
    assert revenues == sorted(revenues)
    assert revenues[-1] > 1.7 * revenues[0]


def test_regime_extrapolation_is_continuous_at_the_last_published_year():
    last = amt_regime_year(REGIME_POST_SUNSET, 2035)
    beyond = amt_regime_year(REGIME_POST_SUNSET, 2036)
    assert beyond.revenue_billions > last.revenue_billions
    assert beyond.revenue_billions < 1.3 * last.revenue_billions


def test_tcja_regime_extends_past_its_last_published_year():
    """TPC publishes no post-2025 TCJA-regime row; the module continues it."""
    published = amt_regime_year(REGIME_TCJA, 2025)
    extended = amt_regime_year(REGIME_TCJA, 2030)
    assert extended.year == 2030
    assert extended.revenue_billions > published.revenue_billions
    # Still an order of magnitude below the post-sunset regime.
    assert extended.revenue_billions < 0.2 * amt_regime_year(
        REGIME_POST_SUNSET, 2030
    ).revenue_billions


# ---------------------------------------------------------------------------
# The exemption response
# ---------------------------------------------------------------------------


def test_revenue_falls_monotonically_as_the_exemption_rises():
    year = 2026
    exemptions = [60_000, 93_000, 110_000, 141_000, 200_000]
    revenues = [amt_revenue_billions(e, year) for e in exemptions]
    assert revenues == sorted(revenues, reverse=True)


def test_payers_fall_monotonically_as_the_exemption_rises():
    year = 2026
    counts = [
        amt_payers_and_liability(e, year)[0]
        for e in (60_000, 93_000, 110_000, 141_000, 200_000)
    ]
    assert counts == sorted(counts, reverse=True)


def test_average_liability_rises_with_the_exemption():
    """Fewer payers left, and the survivors are higher up the distribution."""
    year = 2026
    low = amt_payers_and_liability(93_000, year)[1]
    high = amt_payers_and_liability(141_000, year)[1]
    assert high > low


def test_current_law_exemption_ignores_the_policy():
    policy = create_extend_tcja_amt_relief(mode=AMT_MODE_DERIVED)
    assert policy.get_exemption_for_year(2026, "mfj") == 141_000
    assert current_law_amt_exemption_mfj(2026) == 93_000


def test_affected_taxpayers_take_an_explicit_exemption():
    policy = create_extend_tcja_amt_relief(mode=AMT_MODE_DERIVED)
    reform = policy.estimate_affected_taxpayers(2026)
    baseline = policy.estimate_affected_taxpayers(
        2026, exemption=current_law_amt_exemption_mfj(2026)
    )
    assert baseline > 20 * reform


# ---------------------------------------------------------------------------
# The branch that used to be dead
# ---------------------------------------------------------------------------


def test_raising_the_exemption_loses_revenue():
    """
    The regression this lane exists for. The old branch built both legs from
    the same call, so every exemption change scored exactly 0.0.
    """
    policy = AMTPolicy(
        name="AMT exemption +$25K",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        exemption_change=25_000,
        start_year=2026,
        mode=AMT_MODE_DERIVED,
    )
    effect = policy.estimate_static_revenue_effect(0.0)
    assert effect < 0.0
    assert effect != pytest.approx(0.0)


def test_lowering_the_exemption_raises_revenue():
    policy = AMTPolicy(
        name="AMT exemption -$25K",
        description="probe",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        exemption_change=-25_000,
        start_year=2026,
        mode=AMT_MODE_DERIVED,
    )
    assert policy.estimate_static_revenue_effect(0.0) > 0.0


def test_exemption_effect_scales_with_the_size_of_the_change():
    def effect(change: float) -> float:
        return AMTPolicy(
            name="probe",
            description="probe",
            policy_type=PolicyType.INCOME_TAX,
            exemption_change=change,
            start_year=2026,
            mode=AMT_MODE_DERIVED,
        ).estimate_static_revenue_effect(0.0)

    assert effect(50_000) < effect(25_000) < effect(10_000) < 0.0


def test_rate_change_scales_derived_liability():
    higher = create_amt_rate_change(0.02, start_year=2026, mode=AMT_MODE_DERIVED)
    higher.annual_revenue_change_billions = None
    assert higher.estimate_static_revenue_effect(0.0) > 0.0


# ---------------------------------------------------------------------------
# Derived mode against the scoring engine
# ---------------------------------------------------------------------------


def test_engine_growth_constant_matches_the_engine():
    """
    Derived mode divides the engine's uniform growth back out. If the engine
    ever changes the rate it applies to an AMTPolicy, this must fail loudly
    rather than silently re-tilt every derived path.
    """
    engine = FiscalPolicyScorer(use_real_data=False)
    registered = [
        rate
        for policy_cls, rate, _ in engine._growth_tax_policy_handlers
        if policy_cls is AMTPolicy
    ]
    assert registered == [AMT_ENGINE_GROWTH_RATE]


def test_repeal_reproduces_the_published_revenue_path_year_by_year():
    policy = create_repeal_individual_amt(start_year=2026, mode=AMT_MODE_DERIVED)
    rows = load_tpc_amt_projections()
    result = _score(policy)
    for year, effect in zip(result.years, result.final_deficit_effect, strict=False):
        assert effect == pytest.approx(rows[year].revenue_billions, rel=1e-9), year


def test_derived_ten_year_total_equals_the_paths_own_sum():
    for policy in (
        create_extend_tcja_amt_relief(mode=AMT_MODE_DERIVED),
        create_repeal_individual_amt(start_year=2026, mode=AMT_MODE_DERIVED),
    ):
        expected = -sum(effect for _, effect in policy.derived_revenue_path())
        assert _score(policy).total_10_year_cost == pytest.approx(expected, rel=1e-9)


def test_derived_mode_ignores_the_fitted_annual():
    policy = create_extend_tcja_amt_relief(mode=AMT_MODE_DERIVED)
    assert policy.annual_revenue_change_billions == -39.3
    before = _score(policy).total_10_year_cost
    policy.annual_revenue_change_billions = -1.0
    assert _score(policy).total_10_year_cost == pytest.approx(before)


def test_derived_extend_lands_closer_to_the_published_line_item():
    """
    The lane's actual claim. The carried benchmark is $450B; the sourced
    line item (CRS R48286 Table 1, transcribing CBO pub. 60114, recorded in
    ``validation/benchmark_sources.py``) is $1,357.1B, with a five-year figure
    of $466.2B. The structural path must land nearer the document than the
    fitted constant does.
    """
    line_item = 1_357.1
    fitted = _score(create_extend_tcja_amt_relief(mode=AMT_MODE_REPORTED))
    derived = _score(create_extend_tcja_amt_relief(mode=AMT_MODE_DERIVED))
    assert abs(derived.total_10_year_cost - line_item) < abs(
        fitted.total_10_year_cost - line_item
    )


# ---------------------------------------------------------------------------
# Reported mode is untouched
# ---------------------------------------------------------------------------


def test_app_default_is_reported():
    assert AMT_APP_MODE == AMT_MODE_REPORTED
    assert AMT_SCORECARD_MODE == AMT_MODE_REPORTED
    assert AMT_HELD_OUT_MODE == AMT_MODE_DERIVED
    for factory in (
        create_extend_tcja_amt_relief,
        create_repeal_individual_amt,
        create_repeal_corporate_amt,
        create_increase_amt_exemption,
    ):
        assert factory().mode == AMT_MODE_REPORTED


@pytest.mark.parametrize(
    ("factory", "kwargs", "expected"),
    [
        (create_extend_tcja_amt_relief, {}, 450.5),
        (create_repeal_individual_amt, {"start_year": 2026}, 450.5),
        (create_repeal_corporate_amt, {}, 220.1),
    ],
)
def test_reported_mode_scores_are_unchanged(factory, kwargs, expected):
    result = _score(factory(**kwargs))
    assert result.total_10_year_cost == pytest.approx(expected, abs=0.5)


def test_corporate_amt_has_no_derived_year_path():
    """CAMT keeps its flat base constant; TPC publishes no year path for it."""
    policy = create_repeal_corporate_amt(mode=AMT_MODE_DERIVED)
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(-22.0)
    assert policy.get_phase_in_factor(policy.start_year + 3) == 1.0


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError, match="mode must be one of"):
        AMTPolicy(
            name="probe",
            description="probe",
            policy_type=PolicyType.INCOME_TAX,
            mode="fitted",
        )
