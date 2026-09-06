"""
What a repeal of IRC section 36B removes — lane W7.

Every figure pinned here is transcribed from a document, and the tests say
which. See ``planning/lanes/W7_ptc_repeal_shape.md``.
"""

from __future__ import annotations

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.ptc import (
    CBO_OFFSETTING_SHARE,
    PTC_BASELINE_VINTAGE,
    PTC_EXTENSION_GROSS_10YR_BILLIONS,
    PTC_EXTENSION_NET_10YR_BILLIONS,
    PTC_NET_TO_GROSS,
    PremiumTaxCreditPolicy,
    baseline_credit_cost,
    create_extend_enhanced_ptc,
    create_repeal_ptc,
    ptc_baseline_by_fiscal_year,
)
from fiscal_model.scoring import FiscalPolicyScorer

# ---------------------------------------------------------------------------
# The transcription
# ---------------------------------------------------------------------------


def test_june_2024_block_reproduces_cbos_printed_window_totals():
    """CBO/JCT pub. 51298 (June 2024) Table 2, report p. 3, FY2025-2034.

    CBO prints $966B of outlays and $176B of revenue reductions. The outlays
    column sums exactly; the revenue column sums to 177 against a printed 176,
    which is CBO's rounding to the billion and is recorded in the data file's
    own header.
    """
    rows = ptc_baseline_by_fiscal_year("cbo_jun_2024")
    window = [row for row in rows if 2025 <= row[0] <= 2034]

    assert len(window) == 10
    assert sum(row[1] for row in window) == pytest.approx(966.0)
    assert sum(row[2] for row in window) == pytest.approx(177.0)
    assert abs(sum(row[2] for row in window) - 176.0) <= 1.0


def test_february_2026_block_reproduces_cbos_printed_window_totals():
    """CBO/JCT pub. 51298 (February 2026) Table 2, page 4 of 5, FY2027-2036.

    CBO prints $878B of outlays and $103B of revenue reductions over its own
    stated 2027-2036 column. Both sums land within CBO's rounding.
    """
    rows = ptc_baseline_by_fiscal_year("cbo_feb_2026")
    window = [row for row in rows if 2027 <= row[0] <= 2036]

    assert len(window) == 10
    assert abs(sum(row[1] for row in window) - 878.0) <= 2.0
    assert abs(sum(row[2] for row in window) - 103.0) <= 1.0


def test_the_two_vintages_are_different_shapes_not_two_speeds():
    """The enhancement lapsed at the end of calendar 2025, and the table prices it.

    On the February 2026 vintage the credit's two legs fall from $105B in FY2026
    to $74B in FY2028 and do not regain the FY2026 level until FY2033. A 4%/yr
    ramp — which is what the module used before this lane — cannot express that.
    """
    assert baseline_credit_cost(2026, "cbo_feb_2026") == pytest.approx(105.0)
    assert baseline_credit_cost(2027, "cbo_feb_2026") == pytest.approx(78.0)
    assert baseline_credit_cost(2028, "cbo_feb_2026") == pytest.approx(74.0)
    assert baseline_credit_cost(2032, "cbo_feb_2026") < 105.0
    assert baseline_credit_cost(2033, "cbo_feb_2026") >= 105.0

    # The June 2024 vintage still has FY2025 — the last full year of the
    # enhancement, and the largest year in that table — inside its window.
    assert baseline_credit_cost(2025, "cbo_jun_2024") == pytest.approx(129.0)


def test_an_untranscribed_vintage_raises_rather_than_falling_back():
    with pytest.raises(KeyError, match="cbo_jan_2025"):
        ptc_baseline_by_fiscal_year("cbo_jan_2025")


def test_extrapolation_holds_the_level_below_and_continues_growth_above():
    """Asymmetric on purpose: the early years carry a policy cliff.

    Continuing FY2026 -> FY2027's -26% backwards would invent a FY2025 credit of
    about $141B where CBO prints $111B of outlays alone. The late years grow
    smoothly, so the last observed rate is continued there — the rule
    ``payroll.covered_earnings`` and ``corporate.cbo_corporate_receipts`` use.
    """
    first = baseline_credit_cost(2026, "cbo_feb_2026")
    assert baseline_credit_cost(2025, "cbo_feb_2026") == pytest.approx(first)
    assert baseline_credit_cost(2019, "cbo_feb_2026") == pytest.approx(first)

    last = baseline_credit_cost(2036, "cbo_feb_2026")
    penultimate = baseline_credit_cost(2035, "cbo_feb_2026")
    growth = last / penultimate
    assert baseline_credit_cost(2037, "cbo_feb_2026") == pytest.approx(last * growth)
    assert growth > 1.0


# ---------------------------------------------------------------------------
# The offsetting-effects ratio
# ---------------------------------------------------------------------------


def test_the_offsetting_share_is_cbos_own_published_net_to_gross():
    """CBO/JCT pub. 60437 (24 June 2024), report p. 3, FY2025-2034.

    "$335 billion ... reflects an estimated $415 billion increase in the cost of
    the premium tax credit ... net of an offsetting increase in revenues."
    """
    assert PTC_EXTENSION_NET_10YR_BILLIONS == 335.0
    assert PTC_EXTENSION_GROSS_10YR_BILLIONS == 415.0
    assert PTC_NET_TO_GROSS == pytest.approx(335.0 / 415.0)
    assert CBO_OFFSETTING_SHARE == pytest.approx(0.192771, abs=1e-6)


def test_the_sourced_offset_supersedes_the_two_unsourced_knobs():
    policy = PremiumTaxCreditPolicy(
        name="Repeal",
        description="Repeal",
        policy_type=PolicyType.TAX_CREDIT,
        repeal_ptc=True,
        # Both would otherwise fire; the sourced share is the whole response.
        coverage_elasticity=0.3,
        adverse_selection_factor=0.1,
        coverage_offset_share=CBO_OFFSETTING_SHARE,
    )

    assert policy.estimate_behavioral_offset(100.0) == pytest.approx(19.2771, abs=1e-3)


def test_the_offset_still_carries_the_static_effects_sign():
    """The contract ``tests/test_offset_sign_contract.py`` enforces module-wide.

    ``scoring_engine`` books ``deficit = -revenue + behavioural``, so a
    same-signed offset erodes the revenue change in both directions.
    """
    policy = create_repeal_ptc()

    assert policy.estimate_behavioral_offset(100.0) > 0.0
    assert policy.estimate_behavioral_offset(-100.0) < 0.0
    assert policy.estimate_behavioral_offset(0.0) == 0.0


def test_no_factory_but_the_repeal_carries_a_coverage_offset_share():
    """Everything else in the module keeps the paths it had."""
    assert create_repeal_ptc().coverage_offset_share == pytest.approx(
        CBO_OFFSETTING_SHARE
    )
    assert create_extend_enhanced_ptc().coverage_offset_share is None


# ---------------------------------------------------------------------------
# The score
# ---------------------------------------------------------------------------


def test_the_repeal_factory_carries_no_fitted_annual():
    """83.0 was 1100 / (1.10 x sum of 1.04^t) — the target run backwards."""
    policy = create_repeal_ptc()

    assert policy.annual_revenue_change_billions is None
    assert policy.uses_baseline_credit_path() is True
    assert policy.baseline_vintage == PTC_BASELINE_VINTAGE


def test_the_engine_asks_for_the_year_and_does_not_regrow_the_path():
    """The static path must be CBO's cells, not CBO's cells compounded at 4%."""
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(create_repeal_ptc(), dynamic=False)

    expected = [
        baseline_credit_cost(year, "cbo_feb_2026") for year in range(2026, 2036)
    ]
    assert list(result.static_revenue_effect) == pytest.approx(expected)
    assert sum(expected) == pytest.approx(959.0)


def test_the_shipped_repeal_score_is_the_path_times_cbos_net_to_gross():
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(create_repeal_ptc(), dynamic=False)

    assert float(result.total_10_year_cost) == pytest.approx(-774.13, abs=0.05)
    assert float(result.total_10_year_cost) == pytest.approx(
        -959.0 * PTC_NET_TO_GROSS, abs=0.05
    )


def test_the_june_2024_vintage_reproduces_what_the_target_is_a_rounding_of():
    """The lane's own falsification material, pinned so it cannot rot.

    Scored on the vintage and window the carried -$1,100B came from, and with no
    coverage response, the mechanism returns $1,143B — 0.09% from the $1,142B
    PR #122 traced in pub. 51298 Table 2. That is not a validation of the model:
    it is the demonstration that the target is a baseline projection, which is
    why ``benchmark_sources.py`` still declines to adopt it.
    """
    rows = ptc_baseline_by_fiscal_year("cbo_jun_2024")
    gross = sum(row[1] + row[2] for row in rows if 2025 <= row[0] <= 2034)

    assert gross == pytest.approx(1143.0)
    assert abs(gross - 1142.0) / 1142.0 < 0.001

    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    result = scorer.score_policy(
        create_repeal_ptc(start_year=2025, baseline_vintage="cbo_jun_2024"),
        dynamic=False,
    )
    assert float(result.total_10_year_cost) == pytest.approx(-922.66, abs=0.05)


def test_the_extension_benchmark_is_untouched_by_this_lane():
    """No derived path, and no movement. §1.5 of the lane says why: the only
    published quantity that would drive one is CBO's own score of that same
    policy, which is its target."""
    policy = create_extend_enhanced_ptc()
    assert policy.annual_revenue_change_billions == pytest.approx(-30.5)
    assert policy.uses_baseline_credit_path() is False

    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    assert float(result.total_10_year_cost) == pytest.approx(366.1863, abs=0.01)
