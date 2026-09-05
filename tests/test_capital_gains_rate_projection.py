"""
Tests for the projection of the realizations base across the scoring window.

Wave 5 (``planning/lanes/W5_preferential_margin.md``) stopped pricing a
tax-year-2023 SOI flow in every year of a FY2025-2034 window. What is worth
pinning is not a level - no benchmark is reproduced here - but the four claims
the lane rests on:

* the growth rate is the **stock's own**, already in the parameter file, so the
  projection introduces no free parameter;
* it applies only where the base's tax year is known, so a caller-supplied
  aggregate - which carries its own vintage and has nowhere to record it - is
  left exactly as given;
* the static and behavioural legs scale **together**, so the two stay a
  decomposition of the score rather than one absorbing the other;
* the **death** channel does not see it at all, and neither do the realization
  hazard or the lock-in wedge, which are read at a tax year.

The fifth claim, that qualified dividends were already in the base and adding
them would double-count, is pinned against the vendored evidence file rather
than asserted.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fiscal_model.data.capital_gains import CapitalGainsBaseline
from fiscal_model.policies import CapitalGainsPolicy, PolicyType

TAX_YEAR = 2023
START = 2025


def _policy(**kwargs) -> CapitalGainsPolicy:
    defaults = dict(
        name="rate channel",
        description="+2pp on every preferential bracket",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.02,
        affected_income_threshold=0.0,
        start_year=START,
        duration_years=10,
        baseline_capital_gains_rate=0.0,
        baseline_realizations_billions=0.0,
    )
    defaults.update(kwargs)
    return CapitalGainsPolicy(**defaults)


# ---------------------------------------------------------------------------
# The growth rate is the stock's, not a new one
# ---------------------------------------------------------------------------


def test_the_growth_rate_is_the_one_the_stock_already_uses():
    """No new constant enters: it is the parameter file's own net-worth rate."""
    source = CapitalGainsBaseline()
    assert source.realizations_growth_rate() == pytest.approx(
        source._parameters["household_net_worth_growth_rate"]
    )


def test_the_projection_compounds_from_the_tax_year():
    source = CapitalGainsBaseline()
    rate = source.realizations_growth_rate()
    assert source.realizations_projection_factor(TAX_YEAR, TAX_YEAR) == pytest.approx(1.0)
    assert source.realizations_projection_factor(TAX_YEAR, TAX_YEAR + 1) == pytest.approx(
        1.0 + rate
    )
    assert source.realizations_projection_factor(TAX_YEAR, TAX_YEAR - 1) == pytest.approx(
        1.0 / (1.0 + rate)
    )


def test_the_policy_reads_the_resolved_soi_year_not_the_requested_one():
    """Tailor asks for data year 2024; SOI stops at 2023, and 2023 is the anchor.

    Projecting from 2024 when the base is a 2023 base would silently lose a
    year of growth, which is the sort of thing a resolved-year lookup exists to
    prevent.
    """
    source = CapitalGainsBaseline()
    policy = _policy(data_year=2024)
    assert policy.realizations_projection_factor(2030) == pytest.approx(
        source.realizations_projection_factor(
            source._resolve_year(2024), 2030
        )
    )


# ---------------------------------------------------------------------------
# Only a base with a known tax year is projected
# ---------------------------------------------------------------------------


def test_a_caller_supplied_base_is_never_projected():
    """The three reconstruction scenarios carry their own vintage in their base."""
    policy = _policy(
        baseline_realizations_billions=955.0, baseline_capital_gains_rate=0.15
    )
    for year in (START, START + 5, START + 9):
        assert policy.realizations_projection_factor(year) == 1.0
    flat = policy.estimate_static_revenue_effect(0.0, use_real_data=False)
    for year in (START, START + 9):
        assert policy.estimate_static_revenue_effect(
            0.0, use_real_data=False, year=year
        ) == pytest.approx(flat)


def test_the_supplied_flag_survives_auto_population_overwriting_the_field():
    """``get_brackets`` writes the auto-populated level back onto the field.

    So "did the caller supply a base?" cannot be asked after the fact, and the
    answer is captured at construction. Without that, every SOI-populated
    policy would look caller-supplied on its second call and stop projecting.
    """
    policy = _policy()
    assert policy._supplied_realizations is False
    policy.get_brackets(use_real_data=True)
    assert policy.baseline_realizations_billions > 0
    assert policy._supplied_realizations is False
    assert policy.realizations_projection_factor(START + 9) > 1.0


def test_no_year_means_the_data_year_identity():
    policy = _policy()
    assert policy.realizations_projection_factor(None) == 1.0


# ---------------------------------------------------------------------------
# Both legs scale together
# ---------------------------------------------------------------------------


def test_the_static_leg_scales_by_the_projection():
    policy = _policy()
    base = policy.estimate_static_revenue_effect(0.0, year=TAX_YEAR)
    later = policy.estimate_static_revenue_effect(0.0, year=TAX_YEAR + 7)
    assert later == pytest.approx(
        base * policy.realizations_projection_factor(TAX_YEAR + 7)
    )


def test_the_behavioural_leg_scales_by_the_same_projection(monkeypatch):
    """A projection applied to only one leg would give the right total in the
    year it was applied and a nonsense static/behavioural split, which is what
    the headline block reads."""
    policy = _policy()
    projected = [
        policy.estimate_behavioral_offset(0.0, years_since_start=t) for t in (0, 4, 9)
    ]
    factors = [policy.realizations_projection_factor(START + t) for t in (0, 4, 9)]
    assert min(factors) > 1.0  # the projection is doing something in every year
    monkeypatch.setattr(
        CapitalGainsPolicy, "realizations_projection_factor", lambda self, year: 1.0
    )
    unprojected = [
        policy.estimate_behavioral_offset(0.0, years_since_start=t) for t in (0, 4, 9)
    ]
    assert projected == pytest.approx(
        [u * f for u, f in zip(unprojected, factors)]
    )


# ---------------------------------------------------------------------------
# The death channel, the hazard and the wedge do not see it
# ---------------------------------------------------------------------------


def test_the_death_channel_does_not_read_the_projection(monkeypatch):
    policy = _policy(
        rate_change=0.0, eliminate_step_up=True, step_up_exemption=0.0
    )
    before = [policy.estimate_step_up_elimination_revenue(t) for t in range(10)]
    monkeypatch.setattr(
        CapitalGainsPolicy, "realizations_projection_factor", lambda self, year: 7.0
    )
    after = [policy.estimate_step_up_elimination_revenue(t) for t in range(10)]
    assert after == pytest.approx(before)


def test_the_hazard_and_the_wedge_are_read_at_a_tax_year(monkeypatch):
    """Both are ratios of two quantities measured in the same year.

    Projecting the numerator alone would move the hazard, and the hazard is
    what the lock-in wedge, the stock ratio and the family-business recapture
    all run on.
    """
    policy = _policy(eliminate_step_up=True)
    hazard = policy._realization_hazard()
    wedge = policy.lock_in_wedge()
    monkeypatch.setattr(
        CapitalGainsPolicy, "realizations_projection_factor", lambda self, year: 7.0
    )
    assert policy._realization_hazard() == pytest.approx(hazard)
    assert policy.lock_in_wedge() == pytest.approx(wedge)


def test_a_zero_rate_change_has_no_rate_channel_to_project():
    """CBO Option 51's shape: constructive realization at death, no rate move."""
    policy = _policy(
        rate_change=0.0, eliminate_step_up=True, step_up_exemption=0.0
    )
    for t in (0, 9):
        static = policy.estimate_static_revenue_effect(0.0, year=START + t)
        assert static == pytest.approx(0.0)
        assert policy.estimate_behavioral_offset(
            static, years_since_start=t
        ) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Qualified dividends were already in the base
# ---------------------------------------------------------------------------


def test_the_preferential_base_exceeds_the_years_realized_gains():
    """Which a base holding only capital gains cannot do.

    This is the whole of the qualified-dividends question: SOI Table 3.5's
    preferential columns are what the capital-gains schedule taxed, which is
    adjusted net capital gain *plus* qualified dividends, so adding a
    qualified-dividends column would double-count $313-336B of base.
    """
    source = CapitalGainsBaseline()
    coverage = pd.read_csv(
        source.data_dir / "soi_preferential_base_coverage.csv", comment="#"
    )
    assert len(coverage) == 2
    assert (coverage["base_over_gains_only"] > 1.0).all()
    assert coverage["base_over_gains_plus_qualified_dividends"].between(0.80, 0.90).all()
    assert (coverage["qualified_dividends_billions"] > 300.0).all()


def test_the_coverage_file_is_carried_and_never_read():
    """It is evidence, not an input, and nothing may start scoring through it."""
    source = CapitalGainsBaseline()
    names = {
        value
        for key, value in vars(CapitalGainsBaseline).items()
        if key.endswith("_FILE") and isinstance(value, str)
    }
    assert "soi_preferential_base_coverage.csv" not in names
    assert (source.data_dir / "soi_preferential_base_coverage.csv").exists()


# ---------------------------------------------------------------------------
# The note that ships with the projection (Decision 6)
# ---------------------------------------------------------------------------


def _score(policy):
    from fiscal_model.scoring import FiscalPolicyScorer

    return FiscalPolicyScorer(baseline=None, use_real_data=True).score_policy(
        policy, dynamic=False
    )


def test_the_note_names_the_tax_year_the_rate_and_both_endpoints():
    """A reader has to be able to tell that the base is dated and that it grows.

    Four of the five capital-gains rows on the Tailor form move by 26% to 110%
    in this lane, so the number ships with its explanation rather than in
    silence.
    """
    from fiscal_model.ui.tabs.results_summary import realizations_projection_caption

    policy = _policy(data_year=2024)
    caption = realizations_projection_caption(policy, _score(policy)).replace("\\", "")
    assert "IRS SOI tax year 2023" in caption
    assert "5.8% a year" in caption
    assert "in 2025" in caption and "in 2034" in caption
    assert "hazard falling" in caption


def test_the_note_reports_the_policys_own_projection_factors():
    """Computed from the factors, so it cannot drift from the score above it."""
    from fiscal_model.ui.tabs.results_summary import realizations_projection_caption

    policy = _policy(data_year=2024)
    result = _score(policy)
    caption = realizations_projection_caption(policy, result).replace("\\", "")
    reported = [
        float(chunk.split("B in")[0].split("$")[-1].replace(",", ""))
        for chunk in caption.split("so the base is ")[1].split(" and ")
    ]
    base = float(policy.baseline_realizations_billions)
    expected = [
        base * policy.realizations_projection_factor(int(result.years[0])),
        base * policy.realizations_projection_factor(int(result.years[-1])),
    ]
    assert reported == pytest.approx(expected, abs=0.5)


def test_no_note_where_no_rate_channel_was_projected():
    from fiscal_model.ui.tabs.results_summary import realizations_projection_caption

    supplied = _policy(
        baseline_realizations_billions=955.0, baseline_capital_gains_rate=0.15
    )
    assert realizations_projection_caption(supplied, _score(supplied)) == ""
    death_only = _policy(
        rate_change=0.0, eliminate_step_up=True, step_up_exemption=0.0
    )
    assert realizations_projection_caption(death_only, _score(death_only)) == ""
    assert realizations_projection_caption(object(), None) == ""
