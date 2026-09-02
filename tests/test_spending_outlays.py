"""
The budget-authority -> outlay spend-out model.

These tests protect the three properties that make the spend-out layer a
mechanism rather than a fit:

1. **Nothing leaks.** No profile rate is derived from an option the battery
   scores, and no rate is keyed to a benchmark id.
2. **The identity still holds.** A policy that does not declare an account
   class outlays its authority exactly as it did before this layer existed, so
   the layer cannot silently move anything it was not pointed at.
3. **Authority and outlays are distinct quantities**, and the window truncates
   the tail rather than the head.
"""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model.policies import PolicyType, SpendingPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.spending_outlays import (
    DATA_FILE,
    IMMEDIATE,
    IMMEDIATE_PROFILE,
    OutlayProfile,
    account_classes,
    get_outlay_profile,
    load_outlay_profiles,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import (
    _SPENDING_OUTLAY_CLASS,
    create_policy_from_score,
    spending_outlay_class,
)

#: Options the out-of-sample battery scores. Mirrors
#: ``scripts.fit_outlay_rates.SCORED_OPTIONS``; duplicated deliberately so the
#: assertion below fails if either side is edited alone.
SCORED_OPTIONS = frozenset({37, 38, 39, 42, 43})


def _spending_policy(**kwargs) -> SpendingPolicy:
    defaults = dict(
        name="test",
        description="test spending policy",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=-10.0,
        start_year=2026,
        duration_years=10,
    )
    defaults.update(kwargs)
    return SpendingPolicy(**defaults)


# --------------------------------------------------------------------------
# 1. Anti-leakage
# --------------------------------------------------------------------------


def test_no_scored_option_donates_to_any_profile():
    """The rule from MODELING_IMPROVEMENT.md §4: never fit on the case scored.

    Every profile the battery's spending cases use must be built from options
    the battery does *not* score. If this fails, the spend-out layer is
    reproducing answers rather than predicting them.
    """
    for account_class, profile in load_outlay_profiles().items():
        leaked = set(profile.donor_options) & SCORED_OPTIONS
        assert not leaked, (
            f"{account_class} is fitted on scored option(s) {sorted(leaked)}; "
            "a profile may only use options outside the battery"
        )


def test_every_class_the_battery_uses_has_real_donors():
    """No class used by a scored case may be a bare assertion."""
    for policy_id, account_class in _SPENDING_OUTLAY_CLASS.items():
        profile = get_outlay_profile(account_class)
        assert profile.donor_options, (
            f"{policy_id} is classified {account_class!r}, which carries no "
            "donor options - its rates would have no provenance"
        )
        assert profile.rationale, f"{account_class} has no recorded rationale"


def test_profiles_are_reproducible_from_the_donor_data():
    """The committed CSV is what the documented fit produces, not a hand edit."""
    from scripts.fit_outlay_rates import fit_profiles

    refit = fit_profiles()
    committed = load_outlay_profiles()
    for account_class, shares in refit.items():
        stored = committed[account_class].shares
        np.testing.assert_allclose(shares[: len(stored)], stored, atol=5e-5)


def test_data_file_records_its_provenance():
    header = "".join(
        line for line in DATA_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
        if line.startswith("#")
    )
    assert "publication/60557" in header
    assert "A-11" in header  # the source decision 2 named, and why it is not used


# --------------------------------------------------------------------------
# 2. Profile shape
# --------------------------------------------------------------------------


def test_profiles_are_non_negative_and_do_not_over_spend():
    for account_class, profile in load_outlay_profiles().items():
        assert all(share >= 0 for share in profile.shares), account_class
        assert sum(profile.shares) <= 1.0 + 1e-6, account_class


def test_spend_out_speed_is_ordered_as_the_account_types_imply():
    """Pay disburses fastest, construction slowest. If this inverts, the
    donor assignment in ``scripts/fit_outlay_rates.py`` is wrong."""
    profiles = load_outlay_profiles()
    order = [
        "construction_and_capital",
        "grants_and_procurement",
        "operations_and_support",
        "personnel_and_benefits",
    ]
    rates = [profiles[name].first_year_rate for name in order]
    assert rates == sorted(rates), dict(zip(order, rates))
    assert profiles["mandatory_benefit"].first_year_rate > 0.9


def test_rejects_a_profile_that_outlays_more_than_it_is_given():
    with pytest.raises(ValueError, match=r"above 1\.0"):
        OutlayProfile(account_class="bad", shares=(0.8, 0.5))
    with pytest.raises(ValueError, match=">= 0"):
        OutlayProfile(account_class="bad", shares=(1.0, -0.1))


def test_unknown_account_class_fails_loudly():
    with pytest.raises(ValueError, match="Unknown outlay account class"):
        get_outlay_profile("no_such_class")
    with pytest.raises(ValueError, match="Unknown outlay account class"):
        _spending_policy(outlay_account_class="no_such_class")


def test_account_classes_includes_the_identity():
    assert IMMEDIATE in account_classes()
    assert get_outlay_profile(None) is IMMEDIATE_PROFILE
    assert get_outlay_profile(IMMEDIATE) is IMMEDIATE_PROFILE


# --------------------------------------------------------------------------
# 3. The identity is preserved
# --------------------------------------------------------------------------


def test_default_policy_outlays_authority_one_for_one():
    """The pre-spend-out behaviour, unchanged, for anything not classified."""
    policy = _spending_policy()
    assert policy.outlay_account_class == IMMEDIATE
    for year in range(2026, 2036):
        assert policy.get_outlays_in_year(year) == pytest.approx(
            policy.get_budget_authority_in_year(year)
        )
        assert policy.get_spending_in_year(year) == pytest.approx(
            policy.get_budget_authority_in_year(year)
        )


def test_default_growth_path_is_untouched():
    policy = _spending_policy(annual_spending_change_billions=100.0, annual_growth_rate=0.02)
    assert policy.get_spending_in_year(2026) == pytest.approx(100.0)
    assert policy.get_spending_in_year(2029) == pytest.approx(100.0 * 1.02**3)


def test_a_zero_start_amount_override_means_zero_authority():
    """A caller overriding the level with 0.0 means zero, and must not get the
    policy's own level back through a truthiness test."""
    policy = _spending_policy(annual_spending_change_billions=-10.0, annual_growth_rate=0.0)
    assert policy.get_budget_authority_in_year(2026, 0.0) == 0.0
    assert policy.get_outlays_in_year(2026, 0.0) == 0.0
    assert policy.get_spending_in_year(2026, 0.0) == 0.0
    # None still means "use my own level".
    assert policy.get_budget_authority_in_year(2026, None) == pytest.approx(-10.0)
    assert policy.get_budget_authority_in_year(2026, -4.0) == pytest.approx(-4.0)


def test_unmapped_validation_case_falls_back_to_the_identity():
    assert spending_outlay_class("a_case_nobody_classified") == IMMEDIATE


# --------------------------------------------------------------------------
# 4. The convolution
# --------------------------------------------------------------------------


def test_outlays_are_the_convolution_of_authority_with_the_profile():
    profile = OutlayProfile(account_class="third", shares=(0.5, 0.3, 0.2))
    assert profile.outlays([100.0, 0.0, 0.0]) == pytest.approx([50.0, 30.0, 20.0])
    assert profile.outlays([100.0, 100.0, 100.0]) == pytest.approx([50.0, 80.0, 100.0])


def test_a_single_year_profile_below_one_still_applies_its_rate(monkeypatch):
    """Guards the identity short-circuit in ``get_outlays_in_year``: it must key
    on the *rate* being a whole dollar, not on the profile having one entry. A
    profile that outlays 60 cents in year 0 and lapses the rest is not the
    identity, and short-circuiting it would silently outlay the full dollar."""
    lapsing = OutlayProfile(account_class="lapsing", shares=(0.6,))
    assert lapsing.outlays([100.0, 100.0]) == pytest.approx([60.0, 60.0])

    from fiscal_model import policies_core

    monkeypatch.setattr(policies_core, "get_outlay_profile", lambda _name: lapsing)
    policy = _spending_policy(annual_spending_change_billions=-10.0, annual_growth_rate=0.0)
    assert policy.get_budget_authority_in_year(2026) == pytest.approx(-10.0)
    assert policy.get_outlays_in_year(2026) == pytest.approx(-6.0)


def test_outlays_past_the_end_of_the_path_are_dropped():
    """Tail truncation - the reason a 10-year outlay total sits below its
    10-year budget-authority total."""
    profile = OutlayProfile(account_class="third", shares=(0.5, 0.3, 0.2))
    assert profile.outlays([100.0]) == pytest.approx([50.0])
    assert sum(profile.outlays([100.0, 100.0])) == pytest.approx(130.0)


def test_policy_outlays_lag_its_authority():
    policy = _spending_policy(
        annual_spending_change_billions=-10.0,
        annual_growth_rate=0.0,
        outlay_account_class="grants_and_procurement",
    )
    first_year_share = get_outlay_profile("grants_and_procurement").first_year_rate
    assert policy.get_budget_authority_in_year(2026) == pytest.approx(-10.0)
    assert policy.get_outlays_in_year(2026) == pytest.approx(-10.0 * first_year_share)
    # Later years accumulate the tails of earlier authority.
    assert abs(policy.get_outlays_in_year(2031)) > abs(policy.get_outlays_in_year(2026))


def test_no_outlays_before_the_policy_starts():
    policy = _spending_policy(outlay_account_class="construction_and_capital")
    assert policy.get_outlays_in_year(2025) == 0.0


def test_explicit_authority_path_expresses_a_hump():
    """The half of the mechanism a level cannot reach: an authorization that
    front-loads and then ends."""
    policy = _spending_policy(
        annual_spending_change_billions=0.0,
        budget_authority_path=(163.0, 70.1, 68.5, 68.1, 66.2, 2.0),
        outlay_account_class="construction_and_capital",
    )
    authority = [policy.get_budget_authority_in_year(y) for y in range(2026, 2036)]
    assert authority[:6] == pytest.approx([163.0, 70.1, 68.5, 68.1, 66.2, 2.0])
    assert authority[6:] == [0.0] * 4
    outlays = [policy.get_outlays_in_year(y) for y in range(2026, 2036)]
    # A humped authority path produces a humped outlay path that peaks later.
    assert outlays.index(max(outlays)) > authority.index(max(authority))
    assert sum(outlays) < sum(authority)


# --------------------------------------------------------------------------
# 5. The result exposes both quantities
# --------------------------------------------------------------------------


def test_result_reports_authority_and_outlays_separately():
    scorer = FiscalPolicyScorer()
    policy = _spending_policy(
        annual_spending_change_billions=-23.0,
        outlay_account_class="grants_and_procurement",
    )
    result = scorer.score_policy(policy)
    authority = float(np.sum(result.budget_authority_effect))
    outlays = float(np.sum(result.static_spending_effect))
    assert abs(outlays) < abs(authority)
    assert result.outlay_rate_in_window == pytest.approx(outlays / authority)
    assert 0.5 < result.outlay_rate_in_window < 1.0


def test_immediate_policy_reports_equal_authority_and_outlays():
    scorer = FiscalPolicyScorer()
    result = scorer.score_policy(_spending_policy(annual_spending_change_billions=-23.0))
    np.testing.assert_allclose(
        result.budget_authority_effect, result.static_spending_effect
    )
    assert result.outlay_rate_in_window == pytest.approx(1.0)


def test_tax_policy_result_still_carries_a_budget_authority_array():
    from fiscal_model.policies import TaxPolicy

    scorer = FiscalPolicyScorer()
    result = scorer.score_policy(
        TaxPolicy(
            name="t",
            description="+1pp above 400K",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=400_000,
        )
    )
    assert result.budget_authority_effect.shape == result.static_spending_effect.shape


# --------------------------------------------------------------------------
# 6. The validation battery's classification
# --------------------------------------------------------------------------


def test_every_spending_case_in_the_battery_is_classified():
    from fiscal_model.validation.cbo_scores import validation_shape

    unclassified = [
        policy_id
        for policy_id, score in KNOWN_SCORES.items()
        if validation_shape(score) == "spending" and policy_id not in _SPENDING_OUTLAY_CLASS
    ]
    assert not unclassified, (
        f"spending cases with no account class: {unclassified}. Classify them "
        "from the account type the source describes, not from their error."
    )


def test_benefit_payments_are_not_treated_as_a_spend_out_case():
    """The WEP/GPO repeal outlays benefits in the year they are owed. Its ~10%
    residual is a benefit-growth-rate miss and must survive this lane intact -
    a mapping that closed it would be a fitted mapping."""
    score = KNOWN_SCORES["ssfa_wep_gpo_repeal_outlays"]
    policy = create_policy_from_score(score)
    assert policy.outlay_account_class == "mandatory_benefit"
    result = FiscalPolicyScorer().score_policy(policy)
    assert result.outlay_rate_in_window > 0.99


def test_classified_spending_cases_build_with_their_class():
    for policy_id, account_class in _SPENDING_OUTLAY_CLASS.items():
        policy = create_policy_from_score(KNOWN_SCORES[policy_id])
        assert isinstance(policy, SpendingPolicy)
        assert policy.outlay_account_class == account_class


# --------------------------------------------------------------------------
# 7. A source that states a schedule, not a level (IIJA)
# --------------------------------------------------------------------------


def test_iija_carries_the_sources_own_authorization_schedule():
    """``iija_2021_discretionary.v2`` scores the path CBO's table states, not a
    level carried forward. The path is a *pre-registered shape input*: it must
    sum to the estimate's own $446,306M of budget authority, and its first year
    must be the $162,996M CBO states for FY2022."""
    policy = create_policy_from_score(KNOWN_SCORES["iija_2021_discretionary"])
    path = policy.budget_authority_path
    assert path is not None, "the level shape was superseded by the schedule"
    assert path[0] == pytest.approx(162.996)
    assert sum(path) == pytest.approx(446.306, abs=0.01)
    # Humped, not level: every year after the first is far below it, and the
    # last five are the "about $2B/yr" tail.
    assert all(year < path[0] / 2 for year in path[1:])
    assert all(year == pytest.approx(2.082) for year in path[5:])


def test_iija_authority_path_beats_the_level_it_superseded():
    """The point of the v2 shape. Scored on the level, IIJA provided about four
    times CBO's authority; on the schedule it provides exactly CBO's."""
    score = KNOWN_SCORES["iija_2021_discretionary"]
    on_path = create_policy_from_score(score)
    years = range(on_path.start_year, on_path.start_year + on_path.duration_years)

    level = SpendingPolicy(
        name="IIJA on the superseded v1 level shape",
        description="level carried forward at 2%/yr",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=float(score.annual_amount_billions),
        annual_growth_rate=score.annual_growth_rate,
        category=score.spending_category,
        outlay_account_class=on_path.outlay_account_class,
        start_year=on_path.start_year,
        duration_years=on_path.duration_years,
    )

    path_authority = sum(on_path.get_budget_authority_in_year(y) for y in years)
    level_authority = sum(level.get_budget_authority_in_year(y) for y in years)
    assert path_authority == pytest.approx(446.306, abs=0.01)
    assert level_authority > 3.5 * path_authority


def test_only_a_score_that_states_a_schedule_gets_one():
    """Every other spending case keeps its level shape. A path silently
    appearing on a case whose source states a level would be a shape change
    with no manifest row behind it."""
    with_paths = [
        policy_id
        for policy_id in _SPENDING_OUTLAY_CLASS
        if KNOWN_SCORES[policy_id].annual_authority_path_billions is not None
    ]
    assert with_paths == ["iija_2021_discretionary"]
    for policy_id in _SPENDING_OUTLAY_CLASS:
        if policy_id in with_paths:
            continue
        built = create_policy_from_score(KNOWN_SCORES[policy_id])
        assert built.budget_authority_path is None
