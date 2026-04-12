"""
Tests for the fiscal policy scoring engine.

Tests cover:
- FiscalPolicyScorer initialization
- Scoring TaxPolicy, SpendingPolicy, TransferPolicy
- Dynamic scoring
- ScoringResult properties and methods
- Policy packages
- Behavioral offsets
- Phase-in factors
- Uncertainty ranges
- quick_score convenience function
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.baseline import CBOBaseline
from fiscal_model.policies import (
    PolicyPackage,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
)
from fiscal_model.scoring import FiscalPolicyScorer, ScoringResult, quick_score

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def scorer():
    """FiscalPolicyScorer using hardcoded fallback data."""
    return FiscalPolicyScorer(use_real_data=False)


@pytest.fixture
def scorer_with_baseline():
    """FiscalPolicyScorer with an explicit baseline."""
    gen = CBOBaseline(start_year=2025, use_real_data=False)
    baseline = gen.generate()
    return FiscalPolicyScorer(baseline=baseline, use_real_data=False)


@pytest.fixture
def income_tax_increase():
    """Income tax rate increase on high earners."""
    return TaxPolicy(
        name="High Earner Tax Increase",
        description="2.6pp increase on income above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
        affected_income_threshold=400_000,
        affected_taxpayers_millions=1.8,
        avg_taxable_income_in_bracket=1_200_000,
    )


@pytest.fixture
def income_tax_cut():
    """Broad income tax cut."""
    return TaxPolicy(
        name="Broad Tax Cut",
        description="1pp cut for all income",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.01,
        affected_income_threshold=0,
    )


@pytest.fixture
def spending_policy():
    """Discretionary spending increase."""
    return SpendingPolicy(
        name="Infrastructure Spending",
        description="$50B annual infrastructure investment",
        policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
        annual_spending_change_billions=50.0,
        annual_growth_rate=0.02,
        gdp_multiplier=1.5,
        start_year=2025,
    )


@pytest.fixture
def transfer_policy():
    """Social Security benefit increase."""
    return TransferPolicy(
        name="SS Benefit Increase",
        description="5% increase in Social Security benefits",
        policy_type=PolicyType.SOCIAL_SECURITY,
        benefit_change_percent=0.05,
        start_year=2025,
    )


@pytest.fixture
def phased_policy():
    """Tax policy with a 3-year phase-in."""
    return TaxPolicy(
        name="Phased Tax Increase",
        description="Gradually phased in tax increase",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.03,
        affected_income_threshold=200_000,
        phase_in_years=3,
        start_year=2025,
    )


@pytest.fixture
def scored_result(scorer, income_tax_increase):
    """A pre-computed scoring result for a tax increase."""
    return scorer.score_policy(income_tax_increase)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

class TestFiscalPolicyScorerInit:
    """Test FiscalPolicyScorer initialization."""

    def test_init_without_real_data(self):
        """Scorer initializes with hardcoded fallback when use_real_data=False."""
        scorer = FiscalPolicyScorer(use_real_data=False)
        assert scorer.baseline is not None, "Baseline should be generated"
        assert len(scorer.baseline.years) == 10, "Should have 10-year window"

    def test_init_with_explicit_baseline(self):
        """Scorer accepts a pre-computed baseline projection."""
        gen = CBOBaseline(start_year=2026, use_real_data=False)
        baseline = gen.generate()
        scorer = FiscalPolicyScorer(baseline=baseline, start_year=2026, use_real_data=False)
        assert scorer.baseline is baseline, "Should use the provided baseline"
        assert scorer.baseline.start_year == 2026

    def test_init_creates_economic_model(self, scorer):
        """Scorer should create an economic model for dynamic scoring."""
        assert scorer.economic_model is not None

    def test_start_year_default(self, scorer):
        """Default start year should be 2025."""
        assert scorer.start_year == 2025
        assert scorer.baseline.years[0] == 2025

    def test_start_year_custom(self):
        """Custom start year is respected."""
        scorer = FiscalPolicyScorer(start_year=2030, use_real_data=False)
        assert scorer.start_year == 2030
        assert scorer.baseline.years[0] == 2030


# =============================================================================
# TAX POLICY SCORING
# =============================================================================

class TestScoreTaxPolicy:
    """Test scoring of TaxPolicy proposals."""

    def test_tax_increase_produces_negative_deficit(self, scorer, income_tax_increase):
        """A tax increase should reduce the deficit (negative final_deficit_effect)."""
        result = scorer.score_policy(income_tax_increase)
        # Tax increase => positive revenue => negative deficit effect (reduces deficit)
        assert result.total_10_year_cost < 0, (
            "Tax increase should reduce total deficit (negative cost)"
        )

    def test_tax_cut_produces_positive_deficit(self, scorer, income_tax_cut):
        """A tax cut should increase the deficit (positive final_deficit_effect)."""
        result = scorer.score_policy(income_tax_cut)
        assert result.total_10_year_cost > 0, (
            "Tax cut should increase total deficit (positive cost)"
        )

    def test_static_revenue_nonzero(self, scorer, income_tax_increase):
        """Static revenue effect should be nonzero for a rate change."""
        result = scorer.score_policy(income_tax_increase)
        assert np.any(result.static_revenue_effect != 0), (
            "Static revenue effect should not be all zeros for a rate change"
        )

    def test_static_spending_zero_for_tax(self, scorer, income_tax_increase):
        """Spending effect should be zero for a pure tax policy."""
        result = scorer.score_policy(income_tax_increase)
        assert np.all(result.static_spending_effect == 0), (
            "Tax policy should have zero spending effect"
        )

    def test_result_has_10_years(self, scorer, income_tax_increase):
        """Result arrays should have 10 elements."""
        result = scorer.score_policy(income_tax_increase)
        assert len(result.years) == 10
        assert len(result.static_revenue_effect) == 10
        assert len(result.final_deficit_effect) == 10


# =============================================================================
# SPENDING POLICY SCORING
# =============================================================================

class TestScoreSpendingPolicy:
    """Test scoring of SpendingPolicy proposals."""

    def test_spending_increases_deficit(self, scorer, spending_policy):
        """Spending increase should increase the deficit."""
        result = scorer.score_policy(spending_policy)
        assert result.total_10_year_cost > 0, (
            "Spending increase should raise the deficit"
        )

    def test_spending_static_revenue_zero(self, scorer, spending_policy):
        """Revenue effect should be zero for a spending policy."""
        result = scorer.score_policy(spending_policy)
        assert np.all(result.static_revenue_effect == 0), (
            "Spending policy should not affect revenue"
        )

    def test_spending_grows_over_time(self, scorer, spending_policy):
        """Spending with positive growth rate should increase each year."""
        result = scorer.score_policy(spending_policy)
        for i in range(1, 10):
            assert result.static_spending_effect[i] > result.static_spending_effect[i - 1], (
                f"Spending in year {i + 1} should exceed year {i} with positive growth"
            )

    def test_spending_behavioral_offset_zero(self, scorer, spending_policy):
        """Behavioral offset should be zero for spending policies."""
        result = scorer.score_policy(spending_policy)
        assert np.all(result.behavioral_offset == 0), (
            "Spending policies should have no behavioral offset"
        )


# =============================================================================
# TRANSFER POLICY SCORING
# =============================================================================

class TestScoreTransferPolicy:
    """Test scoring of TransferPolicy proposals."""

    def test_transfer_increases_deficit(self, scorer, transfer_policy):
        """Benefit increase should increase the deficit."""
        result = scorer.score_policy(transfer_policy)
        assert result.total_10_year_cost > 0, (
            "Transfer benefit increase should raise the deficit"
        )

    def test_transfer_revenue_zero(self, scorer, transfer_policy):
        """Revenue effect should be zero for a transfer policy."""
        result = scorer.score_policy(transfer_policy)
        assert np.all(result.static_revenue_effect == 0), (
            "Transfer policy should not affect revenue"
        )

    def test_transfer_behavioral_offset_zero(self, scorer, transfer_policy):
        """Behavioral offset should be zero for transfer policies."""
        result = scorer.score_policy(transfer_policy)
        assert np.all(result.behavioral_offset == 0), (
            "Transfer policies should have no behavioral offset"
        )


class TestScoringEngineBranches:
    """Test internal scoring branches that are easy to regress during refactors."""

    def test_policy_branch_type_checks(self, scorer, income_tax_increase, spending_policy, transfer_policy):
        n_years = len(scorer.baseline.years)

        with pytest.raises(TypeError, match="Expected TaxPolicy"):
            scorer._score_tax_policy_branch(spending_policy, n_years)

        with pytest.raises(TypeError, match="Expected SpendingPolicy"):
            scorer._score_spending_policy_branch(transfer_policy, n_years)

        with pytest.raises(TypeError, match="Expected TransferPolicy"):
            scorer._score_transfer_policy_branch(income_tax_increase, n_years)

    def test_cost_estimate_branch_requires_estimator(self, scorer, income_tax_increase):
        with pytest.raises(TypeError, match="Unsupported policy type"):
            scorer._score_cost_estimate_policy_branch(
                income_tax_increase,
                len(scorer.baseline.years),
            )

    def test_cost_estimate_branch_respects_activity_and_phase(self, scorer):
        class EstimatedCostPolicy:
            def is_active(self, year):
                return year >= 2027

            def get_phase_in_factor(self, year):
                return 0.5 if year == 2027 else 1.0

            def estimate_cost_effect(self, base_cost):
                del base_cost
                return 10.0

        revenue, spending, behavioral = scorer._score_cost_estimate_policy_branch(
            EstimatedCostPolicy(),
            len(scorer.baseline.years),
        )

        assert np.all(revenue == 0)
        assert np.all(behavioral == 0)
        assert spending[0] == 0.0
        assert spending[1] == 0.0
        assert spending[2] == pytest.approx(5.0)
        assert spending[3] == pytest.approx(10.0)

    def test_get_baseline_revenue_for_payroll_tax(self, scorer):
        payroll_tax = TaxPolicy(
            name="Payroll Test",
            description="Payroll revenue lookup",
            policy_type=PolicyType.PAYROLL_TAX,
            rate_change=0.01,
            affected_income_threshold=0,
        )

        revenue = scorer._get_baseline_revenue_for_tax_policy(payroll_tax, 0)
        assert revenue == scorer.baseline.payroll_taxes[0]

    @pytest.mark.parametrize(
        ("policy_type", "baseline_field"),
        [
            (PolicyType.MEDICARE, "medicare"),
            (PolicyType.MEDICAID, "medicaid"),
            (PolicyType.MANDATORY_SPENDING, "other_mandatory"),
        ],
    )
    def test_transfer_policy_uses_expected_baseline_series(
        self,
        scorer,
        policy_type,
        baseline_field,
    ):
        policy = TransferPolicy(
            name=f"{policy_type.value} transfer",
            description="Baseline selector",
            policy_type=policy_type,
            benefit_change_percent=0.05,
            start_year=2026,
        )

        cost = scorer._score_transfer_policy(policy)

        assert cost[0] == 0.0
        expected_year_two = policy.estimate_cost_effect(getattr(scorer.baseline, baseline_field)[1])
        assert cost[1] == pytest.approx(expected_year_two)


# =============================================================================
# DYNAMIC SCORING
# =============================================================================

class TestDynamicScoring:
    """Test dynamic scoring (macroeconomic feedback)."""

    def test_dynamic_flag_produces_effects(self, scorer, income_tax_increase):
        """Dynamic scoring should produce non-None dynamic_effects."""
        result = scorer.score_policy(income_tax_increase, dynamic=True)
        assert result.dynamic_effects is not None, (
            "Dynamic scoring should produce dynamic effects"
        )
        assert result.is_dynamic is True

    def test_static_flag_no_dynamic(self, scorer, income_tax_increase):
        """Static scoring should have None dynamic_effects."""
        result = scorer.score_policy(income_tax_increase, dynamic=False)
        assert result.dynamic_effects is None
        assert result.is_dynamic is False

    def test_dynamic_has_revenue_feedback(self, scorer, income_tax_increase):
        """Dynamic scoring should produce nonzero revenue feedback."""
        result = scorer.score_policy(income_tax_increase, dynamic=True)
        assert np.any(result.dynamic_effects.revenue_feedback != 0), (
            "Dynamic scoring should produce revenue feedback"
        )

    def test_dynamic_changes_final_deficit(self, scorer, income_tax_increase):
        """Dynamic scoring should change the final deficit vs static."""
        static_result = scorer.score_policy(income_tax_increase, dynamic=False)
        dynamic_result = scorer.score_policy(income_tax_increase, dynamic=True)
        assert not np.allclose(
            static_result.final_deficit_effect,
            dynamic_result.final_deficit_effect,
        ), "Dynamic scoring should produce different final deficit than static"

    def test_dynamic_spending_policy(self, scorer, spending_policy):
        """Dynamic scoring should also work for spending policies."""
        result = scorer.score_policy(spending_policy, dynamic=True)
        assert result.dynamic_effects is not None


# =============================================================================
# SCORING RESULT PROPERTIES
# =============================================================================

class TestScoringResultProperties:
    """Test ScoringResult computed properties."""

    def test_total_10_year_cost(self, scored_result):
        """total_10_year_cost should equal sum of final_deficit_effect."""
        expected = np.sum(scored_result.final_deficit_effect)
        assert scored_result.total_10_year_cost == pytest.approx(expected), (
            "total_10_year_cost should be sum of final_deficit_effect"
        )

    def test_total_static_cost(self, scored_result):
        """total_static_cost should equal sum of static_deficit_effect."""
        expected = np.sum(scored_result.static_deficit_effect)
        assert scored_result.total_static_cost == pytest.approx(expected), (
            "total_static_cost should be sum of static_deficit_effect"
        )

    def test_revenue_feedback_10yr_static(self, scored_result):
        """Revenue feedback should be 0 for static scoring."""
        assert scored_result.revenue_feedback_10yr == 0.0, (
            "Static scoring should have zero revenue feedback"
        )

    def test_revenue_feedback_10yr_dynamic(self, scorer, income_tax_increase):
        """Revenue feedback should be nonzero for dynamic scoring."""
        result = scorer.score_policy(income_tax_increase, dynamic=True)
        assert result.revenue_feedback_10yr != 0.0, (
            "Dynamic scoring should have nonzero revenue feedback"
        )

    def test_average_annual_cost(self, scored_result):
        """average_annual_cost should be total / 10."""
        expected = scored_result.total_10_year_cost / 10
        assert scored_result.average_annual_cost == pytest.approx(expected), (
            "average_annual_cost should be total_10_year_cost / number of years"
        )


# =============================================================================
# SCORING RESULT METHODS
# =============================================================================

class TestScoringResultMethods:
    """Test ScoringResult methods."""

    def test_get_year_effect_valid(self, scored_result):
        """get_year_effect should return a dict with expected keys for a valid year."""
        year = scored_result.years[0]
        effect = scored_result.get_year_effect(year)
        assert isinstance(effect, dict)
        expected_keys = {
            'year', 'static_revenue', 'static_spending', 'static_deficit',
            'behavioral_offset', 'final_deficit', 'low_estimate', 'high_estimate',
        }
        assert expected_keys.issubset(effect.keys()), (
            f"get_year_effect missing keys: {expected_keys - effect.keys()}"
        )
        assert effect['year'] == year

    def test_get_year_effect_last_year(self, scored_result):
        """get_year_effect works for the last year in the window."""
        last_year = scored_result.years[-1]
        effect = scored_result.get_year_effect(last_year)
        assert effect['year'] == last_year

    def test_get_year_effect_dynamic_keys(self, scorer, income_tax_increase):
        """Dynamic result should include GDP and employment in get_year_effect."""
        result = scorer.score_policy(income_tax_increase, dynamic=True)
        effect = result.get_year_effect(result.years[0])
        dynamic_keys = {'gdp_effect', 'gdp_pct', 'employment', 'revenue_feedback'}
        assert dynamic_keys.issubset(effect.keys()), (
            f"Dynamic get_year_effect missing keys: {dynamic_keys - effect.keys()}"
        )

    def test_to_dataframe_columns(self, scored_result):
        """to_dataframe should return DataFrame with expected columns."""
        df = scored_result.to_dataframe()
        expected_cols = [
            'Year',
            'Static Revenue Effect ($B)',
            'Static Spending Effect ($B)',
            'Static Deficit Effect ($B)',
            'Behavioral Offset ($B)',
            'Final Deficit Effect ($B)',
            'Low Estimate ($B)',
            'High Estimate ($B)',
        ]
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_to_dataframe_row_count(self, scored_result):
        """to_dataframe should have one row per year."""
        df = scored_result.to_dataframe()
        assert len(df) == 10, "DataFrame should have 10 rows (one per year)"

    def test_to_dataframe_dynamic_extra_columns(self, scorer, income_tax_increase):
        """Dynamic result DataFrame should include GDP and feedback columns."""
        result = scorer.score_policy(income_tax_increase, dynamic=True)
        df = result.to_dataframe()
        assert 'GDP Effect ($B)' in df.columns
        assert 'Revenue Feedback ($B)' in df.columns

    def test_display_summary_dynamic_prints_economic_section(
        self,
        scorer,
        income_tax_increase,
        monkeypatch,
    ):
        """display_summary should print the dynamic summary section."""
        printed = []

        def fake_print(self, *args, **kwargs):
            del kwargs
            printed.extend(args)

        monkeypatch.setattr("rich.console.Console.print", fake_print)

        result = scorer.score_policy(income_tax_increase, dynamic=True)
        result.display_summary()

        assert any(
            isinstance(item, str) and "Economic Effects" in item
            for item in printed
        )


# =============================================================================
# POLICY PACKAGES
# =============================================================================

class TestScorePackage:
    """Test scoring of PolicyPackage."""

    def test_package_combines_policies(self, scorer, income_tax_increase, spending_policy):
        """Package should aggregate effects of multiple policies."""
        package = PolicyPackage(
            name="Test Package",
            description="Tax increase + spending increase",
            policies=[income_tax_increase, spending_policy],
        )
        result = scorer.score_package(package)
        assert result is not None
        assert len(result.years) == 10

    def test_package_result_has_policy_name(self, scorer, income_tax_increase, spending_policy):
        """Package result should carry the package name."""
        package = PolicyPackage(
            name="My Package",
            description="Test",
            policies=[income_tax_increase, spending_policy],
        )
        result = scorer.score_package(package)
        assert result.policy.name == "My Package"

    def test_package_interaction_factor(self, scorer, income_tax_increase):
        """Interaction factor should scale combined effects."""
        package_1x = PolicyPackage(
            name="No interaction",
            description="",
            policies=[income_tax_increase],
            interaction_factor=1.0,
        )
        package_half = PolicyPackage(
            name="Half interaction",
            description="",
            policies=[income_tax_increase],
            interaction_factor=0.5,
        )
        result_1x = scorer.score_package(package_1x)
        result_half = scorer.score_package(package_half)
        # The static revenue (and therefore deficit) should be scaled
        assert abs(result_half.total_static_cost) < abs(result_1x.total_static_cost), (
            "Interaction factor 0.5 should reduce magnitude of static cost"
        )

    def test_package_dynamic(self, scorer, income_tax_increase, spending_policy):
        """Package scoring should support dynamic mode."""
        package = PolicyPackage(
            name="Dynamic Package",
            description="",
            policies=[income_tax_increase, spending_policy],
        )
        result = scorer.score_package(package, dynamic=True)
        assert result.dynamic_effects is not None


# =============================================================================
# BEHAVIORAL OFFSET
# =============================================================================

class TestBehavioralOffset:
    """Test that behavioral offsets are applied correctly."""

    def test_tax_increase_has_positive_behavioral_offset(self, scorer, income_tax_increase):
        """Tax increase should have positive behavioral offset (revenue lost)."""
        result = scorer.score_policy(income_tax_increase)
        # Behavioral offset should be positive (people reduce income, losing revenue)
        assert np.all(result.behavioral_offset >= 0), (
            "Behavioral offset for tax increase should be non-negative"
        )

    def test_behavioral_offset_included_in_final(self, scorer, income_tax_increase):
        """Final deficit should include behavioral offset."""
        result = scorer.score_policy(income_tax_increase)
        # final = static_deficit + behavioral (for static scoring)
        expected_final = result.static_deficit_effect + result.behavioral_offset
        np.testing.assert_allclose(
            result.final_deficit_effect, expected_final,
            rtol=1e-10,
            err_msg="Final deficit should equal static deficit + behavioral offset"
        )

    def test_behavioral_offset_uses_eti(self):
        """Behavioral offset should scale with ETI parameter."""
        scorer = FiscalPolicyScorer(use_real_data=False)
        low_eti = TaxPolicy(
            name="Low ETI",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=200_000,
            taxable_income_elasticity=0.1,
        )
        high_eti = TaxPolicy(
            name="High ETI",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=200_000,
            taxable_income_elasticity=0.5,
        )
        result_low = scorer.score_policy(low_eti)
        result_high = scorer.score_policy(high_eti)
        assert np.sum(result_high.behavioral_offset) > np.sum(result_low.behavioral_offset), (
            "Higher ETI should produce larger behavioral offset"
        )


# =============================================================================
# PHASE-IN FACTOR
# =============================================================================

class TestPhaseIn:
    """Test phase-in factor application in scoring."""

    def test_phased_policy_ramps_up(self, scorer, phased_policy):
        """Policy with phase_in_years=3 should ramp up over first 3 years."""
        result = scorer.score_policy(phased_policy)
        # Revenue effect magnitude should increase across first 3 years
        effects = np.abs(result.static_revenue_effect)
        # Year 1 < Year 3 because phase-in is gradual
        assert effects[0] < effects[2], (
            "Phase-in policy should have smaller effect in year 1 than year 3"
        )

    def test_fully_phased_after_period(self, scorer, phased_policy):
        """After phase-in period, effect should be at full strength."""
        result = scorer.score_policy(phased_policy)
        effects = np.abs(result.static_revenue_effect)
        # Year 3 should be at full phase-in; years 3-9 grow only by baseline growth
        # Year 3 effect should be close to year 4 (both fully phased in)
        ratio = effects[3] / effects[2] if effects[2] != 0 else 0
        assert 0.95 < ratio < 1.15, (
            "Years after full phase-in should have similar effect magnitudes"
        )


# =============================================================================
# UNCERTAINTY RANGES
# =============================================================================

class TestUncertaintyRanges:
    """Test uncertainty range calculations."""

    def test_low_less_than_central_for_positive(self, scorer, spending_policy):
        """When central > 0, low estimate should be less than central."""
        result = scorer.score_policy(spending_policy)
        # Spending has positive deficit effect
        for i in range(10):
            if result.final_deficit_effect[i] > 0:
                assert result.low_estimate[i] < result.final_deficit_effect[i], (
                    f"Year {i}: low estimate should be below central for positive deficit effect"
                )

    def test_high_greater_than_central_for_positive(self, scorer, spending_policy):
        """When central > 0, high estimate should be greater than central."""
        result = scorer.score_policy(spending_policy)
        for i in range(10):
            if result.final_deficit_effect[i] > 0:
                assert result.high_estimate[i] > result.final_deficit_effect[i], (
                    f"Year {i}: high estimate should be above central for positive deficit effect"
                )

    def test_uncertainty_ordering(self, scorer, spending_policy):
        """Low < central < high for each year (when central > 0)."""
        result = scorer.score_policy(spending_policy)
        for i in range(10):
            if result.final_deficit_effect[i] > 0:
                assert result.low_estimate[i] < result.final_deficit_effect[i] < result.high_estimate[i], (
                    f"Year {i}: should have low < central < high"
                )

    def test_uncertainty_widens_over_time(self, scorer, spending_policy):
        """Uncertainty range should widen over the forecast horizon."""
        result = scorer.score_policy(spending_policy)
        range_first = result.high_estimate[0] - result.low_estimate[0]
        range_last = result.high_estimate[9] - result.low_estimate[9]
        # Absolute range grows because both base effect and uncertainty % grow
        assert range_last > range_first, (
            "Uncertainty range should widen over the 10-year window"
        )

    def test_no_uncertainty_when_disabled(self, scorer, income_tax_increase):
        """When include_uncertainty=False, low and high should equal central."""
        result = scorer.score_policy(income_tax_increase, include_uncertainty=False)
        np.testing.assert_array_equal(
            result.low_estimate, result.final_deficit_effect,
            err_msg="Low should equal central when uncertainty disabled"
        )
        np.testing.assert_array_equal(
            result.high_estimate, result.final_deficit_effect,
            err_msg="High should equal central when uncertainty disabled"
        )


# =============================================================================
# QUICK SCORE CONVENIENCE FUNCTION
# =============================================================================

class TestQuickScore:
    """Test the quick_score convenience function."""

    def test_quick_score_returns_result(self, income_tax_increase):
        """quick_score should return a ScoringResult."""
        result = quick_score(income_tax_increase)
        assert isinstance(result, ScoringResult)

    def test_quick_score_static(self, income_tax_increase):
        """quick_score with dynamic=False should produce static result."""
        result = quick_score(income_tax_increase, dynamic=False)
        assert result.is_dynamic is False

    def test_quick_score_dynamic(self, income_tax_increase):
        """quick_score with dynamic=True should produce dynamic result."""
        result = quick_score(income_tax_increase, dynamic=True)
        assert result.is_dynamic is True

    def test_quick_score_nonzero(self, income_tax_increase):
        """quick_score should produce nonzero effects."""
        result = quick_score(income_tax_increase)
        assert result.total_10_year_cost != 0.0, (
            "quick_score should produce a nonzero 10-year cost"
        )
