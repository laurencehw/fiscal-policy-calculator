"""Tests for the fitted-payroll-target caption (lane H13).

The caption prints two things a user cannot otherwise see: that the shipped
Social Security figures reproduce their carried targets *by construction*, and
what the module returns when the fitted constant is held out. The second is a
pinned pair of constants, so the load-bearing test here is the **drift test** —
it calls the leave-one-out suite and fails if either constant stops matching.

Lane doc: ``planning/lanes/HSA_h13_payroll_targets.md``.
"""

from __future__ import annotations

import pytest

from fiscal_model.payroll import (
    PayrollTaxPolicy,
    create_expand_niit,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
)
from fiscal_model.policies import PolicyType
from fiscal_model.ui.tabs.results_summary import (
    _PAYROLL_FITTED_TARGETS,
    payroll_fitted_target_caption,
)
from fiscal_model.validation.loo import run_payroll_loo

# ---------------------------------------------------------------------------
# The drift test — the reason a pinned constant is allowed at all
# ---------------------------------------------------------------------------


def test_pinned_held_out_figures_match_the_loo_suite():
    """Every pinned ``held_out_10yr`` equals what ``run_payroll_loo`` returns.

    The caption reads two module-level constants rather than re-scoring three
    benchmarks on a page render (PR #129's footer defect, PR #135's fix). That
    is only safe while this test holds.
    """
    report = run_payroll_loo()
    by_case = {case.case_id: case for case in report.cases}

    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        case = by_case.get(case_id)
        assert case is not None, f"{case_id} is no longer in the payroll LOO suite"
        assert case.included, f"{case_id} is no longer cross-validatable"
        assert case.loo_10yr == pytest.approx(entry["held_out_10yr"], abs=0.05), (
            f"{case_id}: pinned held-out figure {entry['held_out_10yr']} has "
            f"drifted from the suite's {case.loo_10yr}"
        )


def test_pinned_targets_match_the_loo_suite():
    """The carried target each caption quotes is the one the suite scores."""
    report = run_payroll_loo()
    by_case = {case.case_id: case for case in report.cases}

    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        assert by_case[case_id].official_10yr == pytest.approx(entry["target_10yr"], abs=0.05)


def test_pinned_by_construction_score_is_the_target():
    """The claim "reproduced to the cent" is checked, not asserted.

    If a future lane ever makes either module path stop reproducing its target,
    the caption's first sentence becomes false and this test says so.
    """
    report = run_payroll_loo()
    by_case = {case.case_id: case for case in report.cases}

    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        assert by_case[case_id].calibrated_10yr == pytest.approx(entry["target_10yr"], abs=0.05)


# ---------------------------------------------------------------------------
# When the caption fires
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "provision", "target"),
    [
        (create_ss_eliminate_cap, "E2.1", -3_200.0),
        (create_ss_donut_hole, "E2.5", -2_700.0),
    ],
)
def test_caption_fires_on_the_two_shipped_presets(factory, provision, target):
    caption = payroll_fitted_target_caption(factory(), object())
    assert caption
    assert provision in caption
    assert f"{target:+,.1f}B" in caption
    assert "Office of the Chief Actuary" in caption
    assert "bookkeeping, not agreement" in caption


def test_eliminate_cap_caption_quotes_its_held_out_figure():
    caption = payroll_fitted_target_caption(create_ss_eliminate_cap(), object())
    assert "-3,319.5B" in caption
    assert "3.7% away" in caption
    assert "2.55% of taxable payroll" in caption
    assert "2059 depletion date" in caption


def test_donut_caption_quotes_its_held_out_figure():
    caption = payroll_fitted_target_caption(create_ss_donut_hole(), object())
    assert "-2,664.0B" in caption
    assert "1.3% away" in caption
    assert "2.50% of taxable payroll" in caption
    assert "2057 depletion date" in caption
    # CBO's own ten-year dollar figure for the same donut, from the volume this
    # repository already transcribes.
    assert "1,426.8B" in caption


# ---------------------------------------------------------------------------
# When it must not fire — the caption asserts something that must be true
# ---------------------------------------------------------------------------


def test_no_caption_for_a_different_donut_threshold():
    """A $400K donut does not print a carried target, so it gets no caption."""
    assert payroll_fitted_target_caption(create_ss_donut_hole(400_000), object()) == ""


def test_no_caption_for_the_other_payroll_benchmarks():
    for factory in (create_ss_cap_90_percent, create_expand_niit):
        assert payroll_fitted_target_caption(factory(), object()) == ""


def test_no_caption_when_the_annual_is_not_the_fitted_one():
    """Same design, a different annual — the target is no longer reproduced."""
    policy = create_ss_eliminate_cap()
    policy.annual_revenue_change_billions = 300.0
    assert payroll_fitted_target_caption(policy, object()) == ""


def test_no_caption_when_the_annual_is_unset():
    policy = PayrollTaxPolicy(
        name="Uncapped, bottom-up",
        description="Eliminate the cap with no fitted annual",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_eliminate_cap=True,
    )
    assert payroll_fitted_target_caption(policy, object()) == ""


def test_no_caption_for_a_non_payroll_policy():
    from fiscal_model.policies import TaxPolicy

    policy = TaxPolicy(
        name="Not payroll",
        description="+1pp above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400_000,
    )
    assert payroll_fitted_target_caption(policy, object()) == ""


# ---------------------------------------------------------------------------
# The caption is wired into the headline block
# ---------------------------------------------------------------------------


def test_caption_is_rendered_under_the_headline():
    """The block is additive: it appears in ``render_headline_block``'s body."""
    import inspect

    from fiscal_model.ui.tabs.results_summary import render_headline_block

    source = inspect.getsource(render_headline_block)
    assert "payroll_fitted_target_caption(policy, result)" in source
