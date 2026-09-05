"""
Tests for the corporate module's derived (structural) rate identity — lane W5.

What these lock down:

- **The transcribed base is the statutory base, and that is checkable.** SOI's
  own "income tax" line is 21.0% of "income subject to tax" in every post-TCJA
  year on the file. If a transcription slips, this fails.
- **The credit ratio is not a free parameter.** The average after/before ratio
  the module applies and an explicit section 904 decomposition built from the
  same rows agree to about 1%.
- **The engine coupling is pinned.** The derived path ages SOI's base at the
  growth rate the scoring engine applies to a ``CorporateTaxPolicy``, so the
  two constants must be the same one.
- **IRC section 6655 timing is exactly a phase factor.** 0.75 in the first
  year, ``0.75 + 0.25/(1+g)`` after.
- **The identity is concave in the rate step.** Reported yields the same
  dollars per percentage point at 1pp and 7pp; derived does not, which is the
  whole point of the row.
- **The offset's sign follows the parent's contract in derived mode**, and
  deliberately does not in reported mode — that defect is pinned, not fixed,
  because a fitted benchmark is scored through it.
- **Derived reads no baseline level**, so the score is the same on every
  vintage, which is the property ``validation/cbo_options.py`` claims for every
  uncalibrated shape.
- **Reported mode did not move.** Every shipped preset scores what it scored
  before the lane.
"""

from __future__ import annotations

import pytest

from fiscal_model.baseline import BaselineVintage
from fiscal_model.corporate import (
    BASELINE_TAXABLE_PROFITS_BILLIONS,
    CORPORATE_APP_MODE,
    CORPORATE_BASE_GROWTH,
    CORPORATE_MODE_DERIVED,
    CORPORATE_MODE_REPORTED,
    CORPORATE_VALIDATION_MODE,
    CURRENT_CORPORATE_RATE,
    ESTIMATED_PAYMENT_SAME_FY_SHARE,
    PROFIT_SHIFTING_SEMI_ELASTICITY,
    CorporateTaxPolicy,
    create_biden_corporate_proposal,
    create_biden_corporate_rate_only,
    create_corporate_rate_change,
    create_republican_corporate_cut,
    create_tcja_corporate_repeal,
    credit_realization_ratio,
    latest_soi_tax_year,
    load_soi_table11,
    section_904_realization_ratio,
    soi_row,
    statutory_base_billions,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import build_scorer_for_vintage, create_policy_from_score


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    return FiscalPolicyScorer(start_year=2025, use_real_data=False)


def _ten_year(scorer: FiscalPolicyScorer, policy: CorporateTaxPolicy) -> float:
    return float(scorer.score_policy(policy, dynamic=False).total_10_year_cost)


# ---------------------------------------------------------------------------
# The transcribed SOI file
# ---------------------------------------------------------------------------


def test_every_transcribed_year_puts_the_statutory_rate_on_the_base():
    """SOI's "income tax" line is 21% of "income subject to tax", every year.

    This is the identity that says "income subject to tax" is the base a
    statutory rate change reaches. TY2018 is off the file because the section
    15 blended-rate transition breaks it; every year that is on the file must
    hold it.
    """
    rows = load_soi_table11()
    assert len(rows) >= 4
    for row in rows:
        base = float(row["income_subject_to_tax_thousands"])
        tax = float(row["income_tax_thousands"])
        assert tax / base == pytest.approx(CURRENT_CORPORATE_RATE, abs=0.001), row[
            "tax_year"
        ]


def test_the_latest_year_is_the_one_the_module_reads():
    assert latest_soi_tax_year() == 2022
    assert statutory_base_billions() == pytest.approx(2879.101, abs=0.001)
    assert credit_realization_ratio() == pytest.approx(0.708526, abs=1e-6)


def test_the_fitted_aggregate_is_a_third_below_the_published_base():
    """The finding, as an assertion rather than a paragraph."""
    ratio = BASELINE_TAXABLE_PROFITS_BILLIONS / statutory_base_billions()
    assert 0.60 < ratio < 0.70


def test_the_credit_ratio_survives_a_section_904_decomposition():
    """Average absorption against an explicit foreign/domestic split.

    Treat the FTC as exactly the statutory tax on the foreign-source share of
    the base (which is what the section 904 limitation makes it, for a taxpayer
    in an excess-credit position) and the rest of the credits as absorbing the
    domestic remainder at their own average. The two constructions must agree
    closely or the marginal-equals-average substitution is not defensible.
    """
    average = credit_realization_ratio()
    explicit = section_904_realization_ratio()
    assert abs(explicit - average) / average < 0.015


def test_a_missing_tax_year_is_an_error_not_a_silent_fallback():
    with pytest.raises(KeyError):
        soi_row(1999)


# ---------------------------------------------------------------------------
# Coupling to the engine and to the statute
# ---------------------------------------------------------------------------


def test_the_derived_growth_constant_is_the_engine_s_own(scorer):
    registered = {
        cls.__name__: rate for cls, rate, _ in scorer._growth_tax_policy_handlers
    }
    assert registered["CorporateTaxPolicy"] == CORPORATE_BASE_GROWTH


def test_section_6655_timing_is_exactly_a_phase_factor():
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    carry = 1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    steady = ESTIMATED_PAYMENT_SAME_FY_SHARE + carry / (1.0 + CORPORATE_BASE_GROWTH)

    assert policy.get_phase_in_factor(policy.start_year) == pytest.approx(
        ESTIMATED_PAYMENT_SAME_FY_SHARE
    )
    for year in range(policy.start_year + 1, policy.start_year + 10):
        assert policy.get_phase_in_factor(year) == pytest.approx(steady)
    assert policy.get_phase_in_factor(policy.start_year - 1) == 0.0


def test_reported_mode_keeps_the_base_class_phase_factor():
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_REPORTED)
    for year in range(policy.start_year, policy.start_year + 10):
        assert policy.get_phase_in_factor(year) == 1.0


def test_derived_reproduces_the_closed_form(scorer):
    """The whole derived identity, recomputed here from the published inputs."""
    delta = 0.01
    policy = create_corporate_rate_change(delta, mode=CORPORATE_MODE_DERIVED)
    reform_rate = CURRENT_CORPORATE_RATE + delta

    years = policy.start_year - latest_soi_tax_year()
    base = statutory_base_billions() * (1 + CORPORATE_BASE_GROWTH) ** years
    static0 = delta * base * credit_realization_ratio()

    carry = 1.0 - ESTIMATED_PAYMENT_SAME_FY_SHARE
    expected = 0.0
    for t in range(10):
        phase = (
            ESTIMATED_PAYMENT_SAME_FY_SHARE
            if t == 0
            else ESTIMATED_PAYMENT_SAME_FY_SHARE + carry / (1 + CORPORATE_BASE_GROWTH)
        )
        revenue = static0 * (1 + CORPORATE_BASE_GROWTH) ** t * phase
        expected += -revenue + revenue * PROFIT_SHIFTING_SEMI_ELASTICITY * reform_rate

    assert _ten_year(scorer, policy) == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------------
# What the derived path buys
# ---------------------------------------------------------------------------


def test_reported_is_exactly_linear_in_the_rate_step(scorer):
    """The property that makes one target 3.7% and the other 47.1%.

    Steps are kept below the 29.6% pass-through kink: above it the
    C-corp-to-pass-through branch fires and adds the module's only other
    curvature, which is not what this test is about.
    """
    per_point = [
        abs(_ten_year(scorer, create_corporate_rate_change(d))) / (d * 100)
        for d in (0.01, 0.02, 0.05, 0.07)
    ]
    for value in per_point[1:]:
        assert value == pytest.approx(per_point[0], rel=1e-9)


def test_derived_is_concave_in_the_rate_step(scorer):
    """A bigger rate rise must yield fewer dollars per point, not the same."""
    per_point = [
        abs(_ten_year(scorer, create_corporate_rate_change(d, mode=CORPORATE_MODE_DERIVED)))
        / (d * 100)
        for d in (0.01, 0.02, 0.05, 0.07)
    ]
    assert per_point == sorted(per_point, reverse=True)
    assert per_point[0] > per_point[-1] * 1.05


def test_derived_erodes_a_rate_cut_instead_of_amplifying_it(scorer):
    """The signed-offset contract ``policies_core`` documents.

    A corporate rate cut's behavioural response recovers some of the revenue,
    so the deficit effect must be *smaller* in magnitude than the static
    effect. Reported mode gets this backwards and the second half of this test
    pins that, so that changing it is a decision rather than an accident: the
    fitted ``trump_corporate_15`` benchmark is scored through it.
    """
    cut_derived = CorporateTaxPolicy(
        name="cut",
        description="21% to 15%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=-0.06,
        mode=CORPORATE_MODE_DERIVED,
        include_passthrough_effects=False,
    )
    static = cut_derived.estimate_static_revenue_effect(0.0)
    offset = cut_derived.estimate_behavioral_offset(static)
    assert static < 0
    assert offset < 0  # signed with the static effect
    assert abs(-static + offset) < abs(static)

    cut_reported = CorporateTaxPolicy(
        name="cut",
        description="21% to 15%",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=-0.06,
        mode=CORPORATE_MODE_REPORTED,
        include_passthrough_effects=False,
    )
    static_r = cut_reported.estimate_static_revenue_effect(0.0)
    offset_r = cut_reported.estimate_behavioral_offset(static_r)
    assert offset_r > 0
    assert abs(-static_r + offset_r) > abs(static_r)


def test_derived_reads_no_baseline_level(scorer):
    """Same score on every vintage — cbo_options.py's stated property."""
    policy = create_corporate_rate_change(0.01, mode=CORPORATE_MODE_DERIVED)
    scores = {
        vintage: build_scorer_for_vintage(vintage).score_policy(policy).total_10_year_cost
        for vintage in (None, BaselineVintage.CBO_FEB_2024)
    }
    assert len(set(round(float(v), 9) for v in scores.values())) == 1


def test_the_breakdown_follows_the_mode():
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        policy = create_corporate_rate_change(0.07, mode=mode)
        breakdown = policy.get_component_breakdown()
        assert breakdown["rate_change_effect"] == pytest.approx(
            policy.estimate_static_revenue_effect(0.0)
        )


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match="Unknown corporate scoring mode"):
        CorporateTaxPolicy(
            name="x",
            description="x",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=0.01,
            mode="fitted",
        )


def test_no_factory_sets_a_per_case_elasticity():
    """MODELING_IMPROVEMENT.md §4: one frozen value per mechanism."""
    for factory in (
        create_biden_corporate_rate_only,
        create_biden_corporate_proposal,
        create_republican_corporate_cut,
        create_tcja_corporate_repeal,
    ):
        policy = factory(mode=CORPORATE_MODE_DERIVED)
        assert policy.profit_shifting_semi_elasticity == PROFIT_SHIFTING_SEMI_ELASTICITY


# ---------------------------------------------------------------------------
# Nothing shipped moved
# ---------------------------------------------------------------------------


def test_the_app_default_is_reported():
    assert CORPORATE_APP_MODE == CORPORATE_MODE_REPORTED
    default = CorporateTaxPolicy(
        name="x", description="x", policy_type=PolicyType.CORPORATE_TAX
    )
    assert default.mode == CORPORATE_MODE_REPORTED


def test_reported_mode_scores_exactly_what_it_scored_before_the_lane(scorer):
    """Regression pins, transcribed from ``1d35f1b`` before any code change."""
    assert _ten_year(scorer, create_biden_corporate_rate_only()) == pytest.approx(
        -1397.21, abs=0.01
    )
    assert _ten_year(scorer, create_republican_corporate_cut()) == pytest.approx(
        1917.98, abs=0.01
    )


def test_derived_mode_loses_decision_1_on_the_carried_benchmarks(scorer):
    """The comparison the app default turns on, as a test rather than a claim."""
    targets = {
        create_biden_corporate_rate_only: -1347.0,
        create_republican_corporate_cut: 1920.0,
    }
    means = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        errors = [
            abs(_ten_year(scorer, factory(mode=mode)) - target) / abs(target)
            for factory, target in targets.items()
        ]
        means[mode] = sum(errors) / len(errors)
    assert means[CORPORATE_MODE_REPORTED] < means[CORPORATE_MODE_DERIVED]
    assert CORPORATE_APP_MODE == CORPORATE_MODE_REPORTED


# ---------------------------------------------------------------------------
# The validation shape
# ---------------------------------------------------------------------------


def test_the_option_64_shape_is_pinned_to_derived():
    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt64_corporate_rate_1pp"])
    assert isinstance(policy, CorporateTaxPolicy)
    assert policy.mode == CORPORATE_VALIDATION_MODE == CORPORATE_MODE_DERIVED
    assert policy.start_year == 2025


def test_the_uncalibrated_path_never_reads_the_fitted_aggregate():
    """The leakage guard for this shape, stated directly."""
    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt64_corporate_rate_1pp"])
    static = policy.estimate_static_revenue_effect(0.0)
    fitted = policy.rate_change * BASELINE_TAXABLE_PROFITS_BILLIONS
    assert abs(static - fitted) / abs(fitted) > 0.15


def test_the_corporate_runner_prints_both_modes():
    """Decision 1's comparison has a runner, as ``validate_amt_policy`` does."""
    from fiscal_model.validation.specialized_business import validate_all_corporate

    means = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        rows = validate_all_corporate(verbose=False, mode=mode)
        assert len(rows) == 2
        means[mode] = sum(abs(row.percent_difference) for row in rows) / len(rows)

    assert means[CORPORATE_MODE_REPORTED] == pytest.approx(1.92, abs=0.01)
    assert means[CORPORATE_MODE_DERIVED] == pytest.approx(9.67, abs=0.01)

    default = validate_all_corporate(verbose=False)
    reported = validate_all_corporate(verbose=False, mode=CORPORATE_APP_MODE)
    assert [row.model_10yr for row in default] == [row.model_10yr for row in reported]


def test_the_corporate_runner_refuses_an_unknown_mode():
    from fiscal_model.validation.specialized_business import validate_corporate_policy

    with pytest.raises(ValueError, match="mode must be one of"):
        validate_corporate_policy("biden_corporate_28", verbose=False, mode="fitted")
