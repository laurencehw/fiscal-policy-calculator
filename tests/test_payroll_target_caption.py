"""Tests for the fitted-payroll-target caption (lane H13).

The caption prints two things a user cannot otherwise see: that the shipped
Social Security figures reproduce their carried targets *by construction*, and
what the module returns when the fitted constant is held out. The second is a
pinned pair of constants, so the load-bearing test here is the **drift test** —
it calls the leave-one-out suite and fails if either constant stops matching.

Lane doc: ``planning/lanes/HSA_h13_payroll_targets.md``.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from fiscal_model.payroll import (
    PayrollTaxPolicy,
    create_expand_niit,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.tabs.results_summary import (
    _PAYROLL_FITTED_TARGETS,
    payroll_fitted_target_caption,
)
from fiscal_model.validation.loo import run_payroll_loo


def _result_for(policy):
    """Score ``policy`` the way the app does, so the caption sees a real run."""
    return FiscalPolicyScorer().score_policy(policy, dynamic=False)


def _stub_result(ten_year: float):
    """A result whose static + behavioural sums to ``ten_year``."""
    return SimpleNamespace(
        static_deficit_effect=np.array([ten_year / 10.0] * 10),
        behavioral_offset=np.zeros(10),
    )


@pytest.fixture(scope="module")
def loo_cases():
    return {case.case_id: case for case in run_payroll_loo().cases}


# ---------------------------------------------------------------------------
# The drift test — the reason a pinned constant is allowed at all
# ---------------------------------------------------------------------------


def test_pinned_held_out_figures_match_the_loo_suite(loo_cases):
    """Every pinned ``held_out_10yr`` equals what ``run_payroll_loo`` returns.

    The caption reads two module-level constants rather than re-scoring three
    benchmarks on a page render (PR #129's footer defect, PR #135's fix). That
    is only safe while this test holds.
    """
    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        case = loo_cases.get(case_id)
        assert case is not None, f"{case_id} is no longer in the payroll LOO suite"
        assert case.included, f"{case_id} is no longer cross-validatable"
        assert case.loo_10yr == pytest.approx(entry["held_out_10yr"], abs=0.05), (
            f"{case_id}: pinned held-out figure {entry['held_out_10yr']} has "
            f"drifted from the suite's {case.loo_10yr}"
        )


def test_pinned_targets_match_the_loo_suite(loo_cases):
    """The carried target each caption quotes is the one the suite scores.

    This test earned its keep on 2026-09-09: lane H9 moved ``ss_donut_250k``'s
    target to CBO Option 62 alternative 2 and this assertion went red, which is
    the only reason the caption did not go on calling -$2,700.0B "the carried
    target" after it stopped being one.
    """
    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        assert loo_cases[case_id].official_10yr == pytest.approx(
            entry["carried_target_10yr"], abs=0.05
        )


def test_by_construction_score_is_the_target(loo_cases):
    """The claim "reproduced to the cent" is checked, not asserted."""
    for case_id, entry in _PAYROLL_FITTED_TARGETS.items():
        assert loo_cases[case_id].calibrated_10yr == pytest.approx(
            entry["by_construction_10yr"], abs=0.05
        )


def test_the_caption_says_when_the_target_has_moved_away_from_the_figure():
    """Two rows, two sentences, because the two rows now differ.

    ``ss_eliminate_cap`` still reproduces its carried target, so its caption
    keeps H13's original wording. ``ss_donut_250k`` does not, and its caption
    has to say so rather than assert an agreement the ledger has withdrawn.
    """
    cap = payroll_fitted_target_caption(
        create_ss_eliminate_cap(), _result_for(create_ss_eliminate_cap())
    )
    assert "is the carried target, reproduced to the cent" in cap
    assert "no longer the carried target" not in cap

    donut = payroll_fitted_target_caption(
        create_ss_donut_hole(), _result_for(create_ss_donut_hole())
    )
    assert "is what the module returns" in donut
    assert "It is no longer the carried target" in donut
    assert "-1,426.8B" in donut
    # -2,700.0 against -1,426.8 is 89.2% high.
    assert "misses by 89.2%" in donut


# ---------------------------------------------------------------------------
# When the caption fires — on a real scored run, not a stub
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("factory", "provision", "target"),
    [
        (create_ss_eliminate_cap, "E2.1", -3_200.0),
        (create_ss_donut_hole, "E2.5", -2_700.0),
    ],
)
def test_caption_fires_on_the_two_shipped_presets(factory, provision, target):
    policy = factory()
    caption = payroll_fitted_target_caption(policy, _result_for(policy))
    assert caption
    assert provision in caption
    assert f"{target:+,.1f}B" in caption
    assert "Office of the Chief Actuary" in caption
    assert "bookkeeping, not agreement" in caption


def test_eliminate_cap_caption_quotes_its_held_out_figure():
    policy = create_ss_eliminate_cap()
    caption = payroll_fitted_target_caption(policy, _result_for(policy))
    assert "-3,319.5B" in caption
    assert "3.7% away" in caption
    assert "2.55% of taxable payroll" in caption
    assert "2059 depletion date" in caption


def test_donut_caption_quotes_its_held_out_figure():
    policy = create_ss_donut_hole()
    caption = payroll_fitted_target_caption(policy, _result_for(policy))
    assert "-2,664.0B" in caption
    assert "1.3% away" in caption
    assert "2.50% of taxable payroll" in caption
    assert "2057 depletion date" in caption
    # CBO's own ten-year dollar figure for the same donut, from the volume this
    # repository already transcribes.
    assert "1,426.8B" in caption


def test_every_dollar_sign_is_escaped():
    """An unescaped ``$`` in a ``st.caption`` renders as a KaTeX math span."""
    for factory in (create_ss_eliminate_cap, create_ss_donut_hole):
        policy = factory()
        caption = payroll_fitted_target_caption(policy, _result_for(policy))
        for index, char in enumerate(caption):
            if char == "$":
                assert index and caption[index - 1] == "\\", caption[
                    max(0, index - 40) : index + 10
                ]


# ---------------------------------------------------------------------------
# When it must not fire — the caption asserts something that must be true
# ---------------------------------------------------------------------------


def test_no_caption_when_the_score_is_not_the_target():
    """A run that stops reproducing the target silences the caption."""
    policy = create_ss_eliminate_cap()
    assert payroll_fitted_target_caption(policy, _stub_result(-3_000.0)) == ""


def test_no_caption_for_a_different_donut_threshold():
    """A $400K donut does not print a carried target, so it gets no caption."""
    policy = create_ss_donut_hole(400_000)
    assert payroll_fitted_target_caption(policy, _result_for(policy)) == ""


def test_no_caption_for_the_other_payroll_benchmarks():
    for factory in (create_ss_cap_90_percent, create_expand_niit):
        policy = factory()
        assert payroll_fitted_target_caption(policy, _result_for(policy)) == ""


def test_no_caption_when_the_annual_is_not_the_fitted_one():
    """Same design, a different annual — the target is no longer reproduced."""
    policy = create_ss_eliminate_cap()
    policy.annual_revenue_change_billions = 300.0
    assert payroll_fitted_target_caption(policy, _stub_result(-3_000.0)) == ""


def test_no_caption_when_the_annual_is_unset():
    policy = PayrollTaxPolicy(
        name="Uncapped, bottom-up",
        description="Eliminate the cap with no fitted annual",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_eliminate_cap=True,
    )
    assert payroll_fitted_target_caption(policy, _stub_result(-3_200.0)) == ""


def test_no_caption_for_a_non_payroll_policy():
    from fiscal_model.policies import TaxPolicy

    policy = TaxPolicy(
        name="Not payroll",
        description="+1pp above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400_000,
    )
    assert payroll_fitted_target_caption(policy, _stub_result(-3_200.0)) == ""


# ---------------------------------------------------------------------------
# The caption is wired into the headline block
# ---------------------------------------------------------------------------


def test_caption_is_rendered_under_the_headline():
    """The block is additive: it appears in ``render_headline_block``'s body."""
    import inspect

    from fiscal_model.ui.tabs.results_summary import render_headline_block

    source = inspect.getsource(render_headline_block)
    assert "payroll_fitted_target_caption(policy, result)" in source
