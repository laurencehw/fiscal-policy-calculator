"""
The statutory SALT cap path, and the baseline each SALT reform is priced on.

Lane ``planning/lanes/SALT_current_law_baseline.md``. What these pin:

1. **The statute**, year by year and by filing status -- IRC 164(b)(6)-(7) as
   amended by P.L. 119-21 sec. 70120. A transcription error here moves a
   shipped preset, so every figure the statute states is asserted and the ones
   it computes are asserted against the 101 percent rule.
2. **The anchor**, which is what makes an extrapolation to a $40,000 cap
   checkable rather than invented: evaluated at the $10,000 cap the SOI
   `salt_limited` column was measured under, the fitted within-class
   distribution returns the published capped expenditure -- a number with no
   common ancestor with it.
3. **That each benchmark scores its own document's baseline**, and that the
   declaration in ``scenarios.SALT_SCORING_BASELINES`` and the scenario kwarg
   cannot drift apart.
4. **That no constant was fitted**: the two annuals are the values they were,
   and each travels only with the baseline it answers.
"""

from __future__ import annotations

import math

import pytest

from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tax_expenditure_distributions import (
    load_capped_deduction_distribution,
)
from fiscal_model.tax_expenditures import (
    EXPENDITURE_MODE_DERIVED,
    JCT_TAX_EXPENDITURES,
    SaltCapBaseline,
    create_eliminate_salt_deduction,
    create_repeal_salt_cap,
    salt_cap_at,
    salt_cap_schedule,
    salt_expenditure_billions,
    salt_uncapped_expenditure_billions,
)
from fiscal_model.tax_expenditures_core import (
    SALT_CAP_FLOOR,
    SALT_CAP_INDEXATION,
    SALT_PHASEDOWN_RATE,
)
from fiscal_model.tax_expenditures_factory import SALT_FITTED_BASELINES
from fiscal_model.validation.scenarios import (
    SALT_SCORING_BASELINES,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
)

# ---------------------------------------------------------------------------
# 1. The statute
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "limitation", "threshold"),
    [
        # IRC 164(b)(7)(A)(i)(I)-(II) and the threshold amounts, stated.
        (2025, 40_000.00, 500_000.00),
        (2026, 40_400.00, 505_000.00),
        # (III): 101 percent of the preceding year, through 2029.
        (2027, 40_804.00, 510_050.00),
        (2028, 41_212.04, 515_150.50),
        (2029, 41_624.16, 520_302.005),
    ],
)
def test_the_raised_cap_years_are_the_statute(year, limitation, threshold):
    schedule = salt_cap_schedule(year)
    assert schedule.limitation_amount == pytest.approx(limitation, abs=0.005)
    assert schedule.threshold_amount == pytest.approx(threshold, abs=0.005)
    # "half the applicable limitation amount in the case of a married
    # individual filing a separate return" -- IRC 164(b)(6).
    assert schedule.limitation_amount_mfs == pytest.approx(limitation / 2, abs=0.005)
    assert schedule.threshold_amount_mfs == pytest.approx(threshold / 2, abs=0.005)


def test_the_indexation_is_one_percent_and_compounds():
    """Each step is 101 percent of the year before, not of 2026."""
    for year in (2027, 2028, 2029):
        assert salt_cap_schedule(year).limitation_amount == pytest.approx(
            salt_cap_schedule(year - 1).limitation_amount * (1 + SALT_CAP_INDEXATION)
        )


@pytest.mark.parametrize("year", [2018, 2024, 2030, 2035, 2040])
def test_outside_the_window_the_cap_is_ten_thousand_and_does_not_phase_down(year):
    """Both the pre-2025 law and the post-2029 reversion are the same figure."""
    schedule = salt_cap_schedule(year)
    assert schedule.limitation_amount == SALT_CAP_FLOOR
    assert schedule.threshold_amount is None
    assert schedule.cap_at(50_000_000.0) == SALT_CAP_FLOOR


def test_the_phasedown_is_thirty_percent_and_floors_at_ten_thousand():
    schedule = salt_cap_schedule(2026)
    assert schedule.cap_at(505_000.0) == pytest.approx(40_400.0)
    assert schedule.cap_at(555_000.0) == pytest.approx(
        40_400.0 - SALT_PHASEDOWN_RATE * 50_000.0
    )
    # Complete at MAGI = threshold + (limitation - floor) / 0.30.
    assert schedule.phasedown_complete_at == pytest.approx(606_333.3333, abs=1e-3)
    assert schedule.cap_at(606_333.34) == pytest.approx(SALT_CAP_FLOOR)
    assert schedule.cap_at(50_000_000.0) == SALT_CAP_FLOOR


def test_married_filing_separately_halves_both_sides_of_the_phasedown():
    schedule = salt_cap_schedule(2025)
    assert schedule.cap_at(250_000.0, married_filing_separately=True) == pytest.approx(
        20_000.0
    )
    assert schedule.cap_at(300_000.0, married_filing_separately=True) == pytest.approx(
        20_000.0 - SALT_PHASEDOWN_RATE * 50_000.0
    )
    # And floors at $5,000 rather than $10,000.
    assert schedule.cap_at(
        5_000_000.0, married_filing_separately=True
    ) == pytest.approx(SALT_CAP_FLOOR / 2)


# ---------------------------------------------------------------------------
# 2. The three baselines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("year", [2025, 2026, 2029, 2030, 2035])
def test_permanent_ten_thousand_never_moves_and_never_phases_down(year):
    assert salt_cap_at(SaltCapBaseline.PERMANENT_10K, year, 0.0) == SALT_CAP_FLOOR
    assert (
        salt_cap_at(SaltCapBaseline.PERMANENT_10K, year, 50_000_000.0)
        == SALT_CAP_FLOOR
    )


def test_the_lapsed_baseline_is_uncapped_from_2026():
    """CBO Option 49: 'Beginning in 2026, deductions ... will not be limited.'"""
    assert salt_cap_at(SaltCapBaseline.LAPSED_CAP, 2025, 0.0) == SALT_CAP_FLOOR
    assert math.isinf(salt_cap_at(SaltCapBaseline.LAPSED_CAP, 2026, 0.0))
    assert salt_expenditure_billions(
        SaltCapBaseline.LAPSED_CAP, 2026
    ) == pytest.approx(salt_uncapped_expenditure_billions())


def test_current_law_steps_down_at_the_2030_reversion():
    """The cliff a window-average of two constants cannot express."""
    raised = salt_expenditure_billions(SaltCapBaseline.CURRENT_LAW, 2029)
    reverted = salt_expenditure_billions(SaltCapBaseline.CURRENT_LAW, 2030)
    assert raised > reverted
    # The reverted level is the $10,000 world, with one year of base growth.
    assert reverted == pytest.approx(
        salt_expenditure_billions(SaltCapBaseline.PERMANENT_10K, 2030)
    )


def test_current_law_sits_between_the_other_two_while_the_raised_cap_binds():
    for year in (2026, 2027, 2028, 2029):
        capped = salt_expenditure_billions(SaltCapBaseline.PERMANENT_10K, year)
        current = salt_expenditure_billions(SaltCapBaseline.CURRENT_LAW, year)
        uncapped = salt_expenditure_billions(SaltCapBaseline.LAPSED_CAP, year)
        assert capped < current < uncapped


def test_a_nominal_cap_against_a_growing_base_bites_harder_each_year():
    """The statute indexes the cap at 1%/yr; the base grows at the record's 3%.

    So the *share* of the deduction the cap denies rises across a window with
    no new constant -- the mechanism a flat annual grown at 3% cannot carry.
    """
    growth = 1.0 + JCT_TAX_EXPENDITURES["salt"]["growth_rate"]
    shares = []
    for offset, year in enumerate(range(2030, 2036)):
        aging = growth**offset
        capped = salt_expenditure_billions(SaltCapBaseline.CURRENT_LAW, year, aging)
        uncapped = salt_uncapped_expenditure_billions(aging)
        shares.append(1.0 - capped / uncapped)
    assert shares == sorted(shares)
    assert shares[-1] > shares[0]


# ---------------------------------------------------------------------------
# 3. The anchor: the extrapolation is checkable
# ---------------------------------------------------------------------------


def test_at_the_observed_cap_the_fit_returns_the_published_capped_column():
    """Two numbers with no common ancestor, agreeing.

    The within-class dispersion is identified by SOI's own ``salt_limited``
    column, so evaluating it at $10,000 must return that column's value; the
    record's ``annual_cost = 25.0`` was transcribed from JCT and reaches this
    file by a different route entirely.
    """
    at_ten_thousand = salt_expenditure_billions(SaltCapBaseline.PERMANENT_10K, 2026)
    assert at_ten_thousand == pytest.approx(
        JCT_TAX_EXPENDITURES["salt"]["annual_cost"], rel=1e-3
    )
    assert salt_uncapped_expenditure_billions() == pytest.approx(
        JCT_TAX_EXPENDITURES["salt"]["annual_cost_no_cap"]
    )


def test_every_agi_class_admits_a_dispersion():
    """Every class's SALT dispersion is identified by the two published columns.

    A class that fell back to a point mass would be scored as if every return
    in it claimed the class average, which is the approximation this lane
    exists to remove.
    """
    distribution = load_capped_deduction_distribution()
    assert len(distribution.classes) == 22
    for bracket in distribution.classes:
        assert bracket.sigma is not None, bracket.agi_lower


def test_the_agi_fit_holds_wherever_a_phasedown_can_reach():
    """And falls back harmlessly where it cannot.

    A bounded Pareto on a narrow class cannot produce an arbitrary mean: on
    $5,000-$10,000 the highest mean it can reach is $6,931 and SOI publishes
    $7,777, so the class is flatter than Pareto and falls back to its own mean.
    Fifteen classes do, the $100,000-$200,000 one among them. That is not a
    defect and is not hidden: the phase-out range of every published SALT
    design lies above $250,000, so a class that falls back receives the same
    cap either way. Every class the phasedown reaches carries the fit.
    """
    distribution = load_capped_deduction_distribution()
    reachable = [c for c in distribution.classes if c.agi_lower >= 200_000]
    assert len(reachable) == 7
    for bracket in reachable:
        assert bracket.agi_alpha is not None, bracket.agi_lower
        assert len(bracket.agi_slices()) > 1
    for bracket in distribution.classes:
        if bracket.agi_alpha is None:
            assert bracket.agi_upper is not None
            assert bracket.agi_upper <= 200_000
            assert bracket.agi_slices() == ((1.0, bracket.agi_mean),)


def test_the_deductible_amount_is_monotone_in_the_cap():
    distribution = load_capped_deduction_distribution()
    levels = [
        distribution.deductible_benefit_billions(lambda _magi, c=cap: c)
        for cap in (5_000.0, 10_000.0, 20_000.0, 40_000.0, 100_000.0)
    ]
    assert levels == sorted(levels)
    assert levels[-1] < distribution.uncapped_benefit_billions()


def test_within_class_agi_dispersion_matters_at_the_phasedown_and_nowhere_else():
    """The refinement is taken because it is a step at a published boundary.

    SOI's $500,000-$1,000,000 class has a mean AGI of about $681,000, above the
    2026 phase-out completion of $606,333 -- so read at the class mean the
    whole class drops to $10,000 while the Pareto keeps part of it above.
    """
    distribution = load_capped_deduction_distribution()
    schedule = salt_cap_schedule(2026)
    at_slices = distribution.deductible_benefit_billions(schedule.cap_at)
    # The same SALT dispersion, with the cap read once at each class's own mean
    # AGI: only the AGI treatment differs.
    at_means = sum(
        bracket.deductible_benefit_billions(
            lambda _magi, cap=schedule.cap_at(bracket.agi_mean): cap
        )
        for bracket in distribution.classes
    )
    assert at_slices > at_means
    # And only through the classes the phase-out range runs into: below
    # $500,000 and above the completion point the two agree exactly.
    below = [c for c in distribution.classes if c.agi_lower < 500_000]
    assert sum(
        c.deductible_benefit_billions(schedule.cap_at) for c in below
    ) == pytest.approx(
        sum(
            c.deductible_benefit_billions(
                lambda _magi, cap=schedule.cap_at(c.agi_mean): cap
            )
            for c in below
        )
    )


# ---------------------------------------------------------------------------
# 4. Each benchmark scores its own document's baseline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("benchmark_id", sorted(SALT_SCORING_BASELINES))
def test_the_declared_baseline_is_the_one_the_scenario_scores(benchmark_id):
    """The declaration and the kwarg cannot drift apart.

    ``SALT_SCORING_BASELINES`` went in one commit before the one that made it
    the scoring input, which is the two-commit discipline `preregistered.py`
    uses; this is the check that keeps them together afterwards.
    """
    declared = SaltCapBaseline(SALT_SCORING_BASELINES[benchmark_id]["baseline"])
    scenario = TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE[benchmark_id]
    assert scenario["kwargs"]["salt_baseline"] is declared
    assert SALT_FITTED_BASELINES[benchmark_id] is declared
    assert SALT_SCORING_BASELINES[benchmark_id]["document"].strip()


@pytest.mark.parametrize(
    ("factory", "fitted"),
    [(create_repeal_salt_cap, -96.0), (create_eliminate_salt_deduction, 104.7)],
)
def test_a_fitted_annual_travels_only_with_the_baseline_it_answers(factory, fitted):
    """No constant was retuned, and none is reused on a baseline it did not fit.

    -96.0/yr is the cost of repealing a permanent $10,000 cap and 104.7/yr the
    value of an uncapped deduction. Asked the current-law question, the factory
    hands over ``None`` and `reported` falls through to the cap path -- which
    is how one preset moves while neither benchmark does.
    """
    name = "repeal_salt_cap" if factory is create_repeal_salt_cap else "eliminate_salt"
    on_its_own = factory(salt_baseline=SALT_FITTED_BASELINES[name])
    assert on_its_own.annual_revenue_change_billions == pytest.approx(fitted)

    for other in SaltCapBaseline:
        if other is SALT_FITTED_BASELINES[name]:
            continue
        assert factory(salt_baseline=other).annual_revenue_change_billions is None


def test_the_app_default_is_current_law():
    for factory in (create_repeal_salt_cap, create_eliminate_salt_deduction):
        assert factory().salt_baseline is SaltCapBaseline.CURRENT_LAW


def test_repealing_the_cap_costs_less_under_current_law_than_under_a_permanent_one():
    """The whole point of the lane, as a single inequality.

    Current law already gives most of the cap relief through 2029, so repeal is
    worth far less than PWBM's permanent-$10,000-cap figure -- and a
    current-law score that landed near $1,169B would mean the baseline was not
    reaching the result.
    """
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    current = scorer.score_policy(create_repeal_salt_cap(), dynamic=False)
    permanent = scorer.score_policy(
        create_repeal_salt_cap(salt_baseline=SaltCapBaseline.PERMANENT_10K),
        dynamic=False,
    )
    assert current.total_10_year_cost < permanent.total_10_year_cost
    assert current.total_10_year_cost / permanent.total_10_year_cost < 0.75
    # And the first four years, where the raised cap binds, fall furthest.
    assert current.final_deficit_effect[0] < 0.60 * permanent.final_deficit_effect[0]


def test_the_current_law_path_is_not_a_flat_annual():
    """It steps at the 2030 reversion, which is what a constant cannot do."""
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    path = scorer.score_policy(create_repeal_salt_cap(), dynamic=False)
    annual = path.final_deficit_effect
    step = annual[4] / annual[3]
    assert step > 1.3, "the reversion to $10,000 in 2030 should be visible"
    growth = 1.0 + JCT_TAX_EXPENDITURES["salt"]["growth_rate"]
    assert annual[3] / annual[2] == pytest.approx(growth, rel=0.02)


def test_the_module_reproduces_jcts_own_score_of_section_70120_within_a_quarter():
    """An anchor the lane does not fit to, and reports rather than closes.

    JCT's JCX-35-25 line 20 scores sec. 70120 itself at +$946,209M over
    FY2025-2034 -- the current-law cap path against a baseline in which the cap
    lapses, which is this module's repeal quantity with the sign reversed. The
    model returns about $720B, 24% low, and the gap has a named direction: SOI
    tax year 2023 observes only the population that itemised under a $10,000
    cap, so the filers a $40,000 cap pulls into itemising are absent from the
    base at every income.
    """
    policy = create_repeal_salt_cap(start_year=2025)
    scored = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
        policy, dynamic=False
    )
    error = abs(scored.total_10_year_cost - 946.209) / 946.209
    assert 0.15 < error < 0.35, scored.total_10_year_cost


def test_derived_mode_still_ignores_the_annual_on_the_fitted_baseline():
    """Derived must not fall back to the answer it was handed."""
    policy = create_repeal_salt_cap(
        mode=EXPENDITURE_MODE_DERIVED, salt_baseline=SaltCapBaseline.PERMANENT_10K
    )
    assert policy.annual_revenue_change_billions == pytest.approx(-96.0)
    assert policy.estimate_static_revenue_effect(0.0) != pytest.approx(-96.0)
