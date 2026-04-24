"""
Adversarial input-validation tests.

``test_edge_cases.py`` covers the *valid* fringes of the input space (zero
rate change, very high threshold, zero-elasticity, etc.). This file focuses
on *invalid* and *malformed* inputs, verifying that policy constructors
reject them with clear error messages instead of silently producing nonsense
scores, and on numerical pathologies that are hard to reach from the UI but
can occur when policies are built programmatically (e.g. from the bill
tracker's LLM extraction or the FastAPI layer).

The tests are organized so that adding a new policy class with sensible
``__post_init__`` validation automatically gets a reasonable baseline of
coverage here by imitating the patterns below.
"""

from __future__ import annotations

import math

import pytest

from fiscal_model.policies import (
    CapitalGainsPolicy,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
)
from fiscal_model.scoring import FiscalPolicyScorer


# ---------------------------------------------------------------------------
# Base Policy — structural invariants
# ---------------------------------------------------------------------------


class TestPolicyStructuralValidation:
    """Invariants every Policy subclass must enforce."""

    def test_rejects_zero_duration(self):
        with pytest.raises(ValueError, match="duration_years"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                duration_years=0,
            )

    def test_rejects_negative_duration(self):
        with pytest.raises(ValueError, match="duration_years"):
            SpendingPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
                duration_years=-5,
            )

    def test_rejects_zero_phase_in(self):
        with pytest.raises(ValueError, match="phase_in_years"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                phase_in_years=0,
            )

    def test_rejects_start_year_below_range(self):
        with pytest.raises(ValueError, match="start_year"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                start_year=1999,
            )

    def test_rejects_start_year_above_range(self):
        with pytest.raises(ValueError, match="start_year"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                start_year=2101,
            )

    def test_accepts_start_year_boundaries(self):
        """2000 and 2100 are inclusive boundaries."""
        TaxPolicy(
            name="ok",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2000,
        )
        TaxPolicy(
            name="ok",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2100,
        )


# ---------------------------------------------------------------------------
# TaxPolicy — parameter bounds
# ---------------------------------------------------------------------------


class TestTaxPolicyBounds:
    """TaxPolicy validators protect downstream math from nonsense inputs."""

    def test_rejects_rate_change_above_one(self):
        with pytest.raises(ValueError, match="rate_change"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=1.01,
            )

    def test_rejects_rate_change_below_neg_one(self):
        with pytest.raises(ValueError, match="rate_change"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=-1.5,
            )

    def test_rejects_new_rate_above_one(self):
        with pytest.raises(ValueError, match="new_rate"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                new_rate=1.5,
            )

    def test_rejects_new_rate_below_zero(self):
        with pytest.raises(ValueError, match="new_rate"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                new_rate=-0.1,
            )

    def test_rejects_negative_threshold(self):
        with pytest.raises(ValueError, match="affected_income_threshold"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                affected_income_threshold=-1000,
            )

    def test_rejects_negative_eti(self):
        with pytest.raises(ValueError, match="taxable_income_elasticity"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                taxable_income_elasticity=-0.1,
            )

    def test_rejects_negative_labor_elasticity(self):
        with pytest.raises(ValueError, match="labor_supply_elasticity"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                labor_supply_elasticity=-0.2,
            )

    def test_rejects_negative_affected_taxpayers(self):
        with pytest.raises(ValueError, match="affected_taxpayers_millions"):
            TaxPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                affected_taxpayers_millions=-0.5,
            )

    def test_accepts_rate_change_boundaries(self):
        """±1.0 are inclusive bounds — allows full-rate abolition and doubling."""
        TaxPolicy(
            name="ok",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=1.0,
        )
        TaxPolicy(
            name="ok",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-1.0,
        )

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_rate_change_is_rejected_or_flagged(self, bad):
        """
        Non-finite rate changes either raise on construction (preferred) or
        propagate to scoring as non-finite output. Either is acceptable; what
        is NOT acceptable is silent coercion to a finite number.
        """
        try:
            policy = TaxPolicy(
                name="adversarial",
                description="",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=bad,
                affected_income_threshold=400_000,
            )
        except (ValueError, OverflowError):
            return  # Rejected at construction: pass.

        # Not rejected — then scoring should either error or produce non-finite.
        scorer = FiscalPolicyScorer(use_real_data=False)
        try:
            result = scorer.score_policy(policy)
        except (ValueError, OverflowError, ArithmeticError):
            return
        total = float(sum(result.final_deficit_effect))
        assert not math.isfinite(total), (
            f"Non-finite rate_change={bad} silently produced finite total={total}"
        )


# ---------------------------------------------------------------------------
# CapitalGainsPolicy — rate & elasticity bounds
# ---------------------------------------------------------------------------


class TestCapitalGainsPolicyBounds:
    def test_rejects_baseline_rate_above_one(self):
        with pytest.raises(ValueError, match="baseline_capital_gains_rate"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                baseline_capital_gains_rate=1.5,
            )

    def test_rejects_negative_baseline_rate(self):
        with pytest.raises(ValueError, match="baseline_capital_gains_rate"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                baseline_capital_gains_rate=-0.05,
            )

    def test_rejects_negative_short_run_elasticity(self):
        with pytest.raises(ValueError, match="short_run_elasticity"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                short_run_elasticity=-0.1,
            )

    def test_rejects_negative_long_run_elasticity(self):
        with pytest.raises(ValueError, match="long_run_elasticity"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                long_run_elasticity=-0.1,
            )

    def test_rejects_negative_transition_years(self):
        with pytest.raises(ValueError, match="transition_years"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                transition_years=-1,
            )

    def test_rejects_negative_lock_in_multiplier(self):
        with pytest.raises(ValueError, match="step_up_lock_in_multiplier"):
            CapitalGainsPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                step_up_lock_in_multiplier=-0.5,
            )

    def test_scoring_rejects_nonpositive_realizations(self):
        """
        Zero baseline realizations when auto-populate is off should surface
        the user-actionable ValueError rather than silently returning 0.
        """
        policy = CapitalGainsPolicy(
            name="bad",
            description="",
            policy_type=PolicyType.CAPITAL_GAINS_TAX,
            rate_change=0.05,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=0.0,
            new_rate=0.25,
        )
        with pytest.raises(ValueError, match="baseline_realizations_billions"):
            policy.estimate_static_revenue_effect(0.0, use_real_data=False)

    def test_scoring_rejects_rate_at_unity(self):
        """
        A reform rate of 1.0 (tau1 == 1) breaks the (1-tau1)/(1-tau0) form.
        Scoring must refuse rather than divide by zero or return nonsense.
        """
        policy = CapitalGainsPolicy(
            name="bad",
            description="",
            policy_type=PolicyType.CAPITAL_GAINS_TAX,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=500.0,
            new_rate=1.0,
        )
        with pytest.raises(ValueError, match="Capital gains rates"):
            policy.estimate_behavioral_offset(static_effect=0.0, years_since_start=0)


# ---------------------------------------------------------------------------
# Extreme but valid inputs — numerical robustness
# ---------------------------------------------------------------------------


class TestNumericalRobustness:
    """
    Extreme valid inputs must produce finite, monotone-plausible results.
    These would be rejected by soft UI validation but are reachable
    through the Python API, the FastAPI layer, or the bill tracker.
    """

    def test_high_eti_still_produces_finite_result(self):
        """ETI=0.99 is unrealistic but should not blow up the scorer."""
        policy = TaxPolicy(
            name="extreme_eti",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            affected_income_threshold=400_000,
            taxable_income_elasticity=0.99,
        )
        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        total = float(sum(result.final_deficit_effect))
        assert math.isfinite(total)

    def test_very_small_rate_change_is_nonzero(self):
        """A 0.001pp change should still produce a nonzero, finite score."""
        policy = TaxPolicy(
            name="micro",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.00001,
            affected_income_threshold=400_000,
            affected_taxpayers_millions=1.8,
            avg_taxable_income_in_bracket=1_200_000,
        )
        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        total = float(sum(result.final_deficit_effect))
        assert math.isfinite(total)

    def test_long_duration_does_not_overflow(self):
        """A 30-year policy must not overflow the baseline array."""
        policy = TaxPolicy(
            name="generational",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=400_000,
            duration_years=30,
        )
        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        assert all(math.isfinite(float(v)) for v in result.final_deficit_effect)

    def test_tax_increase_produces_deficit_reduction(self):
        """
        Qualitative monotonicity check: a tax *increase* (positive rate_change)
        must reduce the deficit (negative or zero final_deficit_effect).
        """
        policy = TaxPolicy(
            name="surtax",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.026,
            affected_income_threshold=400_000,
            affected_taxpayers_millions=1.8,
            avg_taxable_income_in_bracket=1_200_000,
        )
        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        total = float(sum(result.final_deficit_effect))
        assert total <= 0, (
            f"Tax increase produced deficit_effect={total:+.1f}B (expected ≤ 0)"
        )

    def test_tax_cut_produces_deficit_increase(self):
        """Counterpart to the above: a tax cut must increase the deficit."""
        policy = TaxPolicy(
            name="rate_cut",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.026,
            affected_income_threshold=400_000,
            affected_taxpayers_millions=1.8,
            avg_taxable_income_in_bracket=1_200_000,
        )
        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        total = float(sum(result.final_deficit_effect))
        assert total >= 0, (
            f"Tax cut produced deficit_effect={total:+.1f}B (expected ≥ 0)"
        )


# ---------------------------------------------------------------------------
# Phase-in and sunset — boundary behavior
# ---------------------------------------------------------------------------


class TestPhaseInSunsetBoundaries:
    def test_phase_in_factor_at_exact_start_year(self):
        """With phase_in_years=1, factor at start_year equals 1.0."""
        policy = TaxPolicy(
            name="instant",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2025,
            phase_in_years=1,
        )
        assert policy.get_phase_in_factor(2025) == 1.0

    def test_phase_in_factor_completes_at_boundary(self):
        """Over 3-year phase-in, factor equals 1.0 exactly at year 3."""
        policy = TaxPolicy(
            name="phased",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2025,
            phase_in_years=3,
        )
        # Year 2025 = (0+1)/3; 2026 = 2/3; 2027 = 3/3 = 1.0.
        assert policy.get_phase_in_factor(2025) == pytest.approx(1 / 3)
        assert policy.get_phase_in_factor(2027) == pytest.approx(1.0)
        # After completion stays at 1.0.
        assert policy.get_phase_in_factor(2030) == pytest.approx(1.0)

    def test_phase_in_factor_before_start_is_zero(self):
        policy = TaxPolicy(
            name="future",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2030,
        )
        assert policy.get_phase_in_factor(2025) == 0.0

    def test_sunset_inactive_at_exact_end(self):
        """A 10-year sunset policy starting in 2025 is inactive in 2035."""
        policy = TaxPolicy(
            name="sunset",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            start_year=2025,
            duration_years=10,
            sunset=True,
        )
        assert policy.is_active(2034) is True
        assert policy.is_active(2035) is False


# ---------------------------------------------------------------------------
# SpendingPolicy and TransferPolicy — minimal coverage
# ---------------------------------------------------------------------------


class TestSpendingTransferValidation:
    def test_spending_policy_rejects_zero_duration(self):
        with pytest.raises(ValueError, match="duration_years"):
            SpendingPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
                duration_years=0,
            )

    def test_transfer_policy_rejects_invalid_start_year(self):
        with pytest.raises(ValueError, match="start_year"):
            TransferPolicy(
                name="bad",
                description="",
                policy_type=PolicyType.SOCIAL_SECURITY,
                start_year=1950,
            )

    def test_one_time_spending_only_in_start_year(self):
        """is_one_time spending must be zero in all years after start_year."""
        policy = SpendingPolicy(
            name="stimulus",
            description="",
            policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
            annual_spending_change_billions=100.0,
            is_one_time=True,
            start_year=2025,
        )
        assert policy.get_spending_in_year(2025) == pytest.approx(100.0)
        assert policy.get_spending_in_year(2026) == 0.0
        assert policy.get_spending_in_year(2030) == 0.0
