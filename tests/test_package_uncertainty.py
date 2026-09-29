"""A package's uncertainty band comes from its composition, not its list order.

``planning/ROUTE_TO_9.md`` reproduced two defects in the engine's uncertainty
arrays (``ScoringResult.low_estimate`` / ``high_estimate``), which reach the
``/score/tariff`` API, the model-comparison table, the CSV export and the
cumulative chart:

1. ``score_package`` passed ``package.policies[0]`` to ``_calculate_uncertainty``
   and applied that one policy's factor to the net total. A 1pp income-tax
   increase listed before a $50B/yr spending increase scored -$1,038.83B either
   way, with a band **1.5x wider** in one order than the other.
2. The spread multiplied the *signed* estimate, so for every deficit-reducing
   estimate ``low`` sat above ``high``, and the wider side went to the
   favourable outcome instead of the one ``ASYMMETRY_HIGH`` documents
   ("costs tend higher").

The package band is now the sum of each component's own band, which is
order-free, reduces to the single-policy band for one policy or for components
of one type and sign, and cannot be narrowed by cutting a policy into pieces.
"""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model import FiscalPolicyScorer, PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.constants import ASYMMETRY_HIGH, ASYMMETRY_LOW
from fiscal_model.policies import PolicyPackage


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    # The configuration ROUTE_TO_9 used for its reproduction.
    return FiscalPolicyScorer(use_real_data=False)


def _income_tax(rate_change: float = 0.01, name: str = "+1pp income tax") -> TaxPolicy:
    return TaxPolicy(
        name=name,
        description="Rate change on every ordinary bracket",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate_change,
        affected_income_threshold=0,
    )


def _discretionary(annual_billions: float = 50.0) -> SpendingPolicy:
    return SpendingPolicy(
        name="+$50B/yr discretionary",
        description="Nondefense discretionary increase",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=annual_billions,
    )


def _assert_same_band(a, b) -> None:
    np.testing.assert_allclose(a.low_estimate, b.low_estimate)
    np.testing.assert_allclose(a.high_estimate, b.high_estimate)


# ---------------------------------------------------------------------------
# Defect 1 — the reproduction, then the properties that make the fix principled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dynamic", [False, True], ids=["conventional", "dynamic"])
def test_reversing_a_package_changes_neither_its_total_nor_its_band(scorer, dynamic) -> None:
    tax_first = scorer.score_package(
        PolicyPackage("tax first", "", [_income_tax(), _discretionary()]), dynamic=dynamic
    )
    spending_first = scorer.score_package(
        PolicyPackage("spending first", "", [_discretionary(), _income_tax()]), dynamic=dynamic
    )

    np.testing.assert_allclose(
        tax_first.final_deficit_effect, spending_first.final_deficit_effect
    )
    _assert_same_band(tax_first, spending_first)


def test_the_reproduction_total_is_the_one_route_to_9_reported(scorer) -> None:
    """Pins the configuration, so the test above is testing the defect it names."""
    package = scorer.score_package(
        PolicyPackage("mixed", "", [_income_tax(), _discretionary()])
    )
    assert float(np.sum(package.final_deficit_effect)) == pytest.approx(-1038.83, abs=0.01)


def test_the_package_band_is_the_sum_of_its_components_bands(scorer) -> None:
    """Offsetting components leave a small net total, not a small error."""
    tax, spending = _income_tax(), _discretionary()
    package = scorer.score_package(PolicyPackage("mixed", "", [tax, spending]))
    parts = [scorer.score_policy(tax), scorer.score_policy(spending)]

    width = package.high_estimate - package.low_estimate
    np.testing.assert_allclose(
        width, sum(part.high_estimate - part.low_estimate for part in parts)
    )
    # ...which is wider than either component alone, where the old band (the
    # first policy's factor on the net total) was narrower than the tax
    # component's own band in both orders.
    for part in parts:
        assert np.all(width >= part.high_estimate - part.low_estimate)


def test_a_one_policy_package_carries_that_policys_band(scorer) -> None:
    policy = _income_tax()
    _assert_same_band(
        scorer.score_package(PolicyPackage("one", "", [policy])),
        scorer.score_policy(policy),
    )


def test_splitting_a_policy_into_pieces_does_not_narrow_its_band(scorer) -> None:
    """A root-sum-of-squares rule would narrow it by sqrt(2) — a gaming vector."""
    whole = scorer.score_policy(_income_tax(0.01))
    halves = scorer.score_package(
        PolicyPackage(
            "halves",
            "",
            [_income_tax(0.005, "first half"), _income_tax(0.005, "second half")],
        )
    )
    np.testing.assert_allclose(whole.final_deficit_effect, halves.final_deficit_effect)
    _assert_same_band(whole, halves)


def test_the_band_is_taken_around_the_interaction_adjusted_total(scorer) -> None:
    policy = _income_tax()
    package = scorer.score_package(
        PolicyPackage("damped", "", [policy], interaction_factor=0.5)
    )
    low, high = scorer._calculate_uncertainty(policy, package.final_deficit_effect, None)
    np.testing.assert_allclose(package.low_estimate, low)
    np.testing.assert_allclose(package.high_estimate, high)


# ---------------------------------------------------------------------------
# Defect 2 — ordered bounds, for costs and savings alike
# ---------------------------------------------------------------------------


def _results(scorer):
    tax_increase = scorer.score_policy(_income_tax(0.01))
    tax_cut = scorer.score_policy(_income_tax(-0.01, "-1pp income tax"))
    spending = scorer.score_policy(_discretionary())
    package = scorer.score_package(
        PolicyPackage("mixed", "", [_income_tax(), _discretionary()])
    )
    return {
        "revenue raiser": tax_increase,
        "tax cut": tax_cut,
        "spending increase": spending,
        "mixed package": package,
    }


def test_bounds_bracket_the_estimate_every_year(scorer) -> None:
    for label, result in _results(scorer).items():
        assert np.all(result.low_estimate <= result.final_deficit_effect), label
        assert np.all(result.final_deficit_effect <= result.high_estimate), label


def test_a_revenue_raiser_is_one_of_the_cases_it_used_to_invert(scorer) -> None:
    """The fixture exercises the broken case, not only the one that always worked."""
    raiser = _results(scorer)["revenue raiser"]
    assert np.all(raiser.final_deficit_effect < 0)


def test_the_wider_side_is_always_the_higher_deficit_side(scorer) -> None:
    """'Costs tend higher' — and savings tend smaller — for every sign."""
    for label, result in _results(scorer).items():
        above = result.high_estimate - result.final_deficit_effect
        below = result.final_deficit_effect - result.low_estimate
        nonzero = np.abs(result.final_deficit_effect) > 1e-9
        # Directions first: the ratio alone cannot see the old inversion, where
        # both spreads were negative for a saving and their ratio was the same.
        assert np.all(above[nonzero] > 0), label
        assert np.all(below[nonzero] > 0), label
        np.testing.assert_allclose(
            above[nonzero] / below[nonzero],
            ASYMMETRY_HIGH / ASYMMETRY_LOW,
            err_msg=label,
        )


def test_a_single_policys_band_is_as_wide_as_it_was(scorer) -> None:
    """The fix orders the bounds; it does not re-size a single policy's band."""
    from fiscal_model.constants import (
        BASE_UNCERTAINTY,
        TAX_UNCERTAINTY_FACTOR,
        UNCERTAINTY_GROWTH_PER_YEAR,
    )

    result = scorer.score_policy(_income_tax(0.01))
    central = result.final_deficit_effect
    u = np.array(
        [BASE_UNCERTAINTY + UNCERTAINTY_GROWTH_PER_YEAR * t for t in range(len(central))]
    ) * TAX_UNCERTAINTY_FACTOR
    # The old, signed formula's width, written out independently of the engine.
    old_low = central * (1 - u * ASYMMETRY_LOW)
    old_high = central * (1 + u * ASYMMETRY_HIGH)
    np.testing.assert_allclose(
        result.high_estimate - result.low_estimate, np.abs(old_high - old_low)
    )
