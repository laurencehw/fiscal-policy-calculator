"""
Tests for fiscal_model/reporting.py — BudgetReport and helpers.

Covers:
- BudgetReport initialization with a ScoringResult
- generate_text_report (format_summary) returns a string
- Year-by-year table in report
- create_comparison_table works with multiple results
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for CI

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.reporting import BudgetReport, create_comparison_table
from fiscal_model.scoring import FiscalPolicyScorer

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def scorer():
    return FiscalPolicyScorer(use_real_data=False)


@pytest.fixture
def simple_policy():
    return TaxPolicy(
        name="Test Tax Increase",
        description="2pp increase on income above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
    )


@pytest.fixture
def second_policy():
    return TaxPolicy(
        name="Another Tax Change",
        description="1pp cut for all income",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.01,
        affected_income_threshold=0,
    )


@pytest.fixture
def scoring_result(scorer, simple_policy):
    return scorer.score_policy(simple_policy, dynamic=False)


@pytest.fixture
def second_result(scorer, second_policy):
    return scorer.score_policy(second_policy, dynamic=False)


@pytest.fixture
def report(scoring_result):
    return BudgetReport(scoring_result)


# =============================================================================
# INITIALIZATION
# =============================================================================

class TestBudgetReportInit:

    def test_init_stores_result(self, report, scoring_result):
        assert report.result is scoring_result

    def test_init_stores_years(self, report):
        assert report.years is not None
        assert len(report.years) == 10


# =============================================================================
# TEXT REPORT
# =============================================================================

class TestGenerateTextReport:

    def test_returns_string(self, report):
        text = report.generate_text_report()
        assert isinstance(text, str)

    def test_contains_policy_name(self, report):
        text = report.generate_text_report()
        assert "Test Tax Increase" in text

    def test_contains_year_headers(self, report):
        text = report.generate_text_report()
        # Report should have a "Year" header and individual year values
        assert "Year" in text
        # Should contain at least the first year
        assert "2025" in text

    def test_contains_key_metrics(self, report):
        text = report.generate_text_report()
        assert "Static Cost" in text or "Static" in text
        assert "Behavioral" in text or "Offset" in text

    def test_contains_notes_section(self, report):
        text = report.generate_text_report()
        assert "NOTES" in text

    def test_contains_uncertainty_range(self, report):
        text = report.generate_text_report()
        assert "Uncertainty" in text or "CI" in text


# =============================================================================
# COMPARISON TABLE
# =============================================================================

class TestCreateComparisonTable:

    def test_compare_returns_string(self, scoring_result, second_result):
        table = create_comparison_table([scoring_result, second_result])
        assert isinstance(table, str)

    def test_compare_contains_policy_names(self, scoring_result, second_result):
        table = create_comparison_table([scoring_result, second_result])
        assert "Test Tax Increase" in table
        assert "Another Tax Change" in table

    def test_compare_contains_combined_total(self, scoring_result, second_result):
        table = create_comparison_table([scoring_result, second_result])
        assert "COMBINED TOTAL" in table

    def test_compare_single_policy_no_total(self, scoring_result):
        table = create_comparison_table([scoring_result])
        assert "COMBINED TOTAL" not in table

    def test_compare_header(self, scoring_result, second_result):
        table = create_comparison_table([scoring_result, second_result])
        assert "POLICY COMPARISON TABLE" in table


# =============================================================================
# PLOT (smoke test — just verify no crash)
# =============================================================================

class TestPlotBudgetEffects:

    def test_plot_returns_figure(self, report):
        import matplotlib.pyplot as plt
        fig = report.plot_budget_effects(show=False)
        assert fig is not None
        plt.close(fig)

    def test_plot_comparison_callable(self, report, second_result):
        """plot_comparison is callable."""
        import matplotlib.pyplot as plt
        plt.ion()
        try:
            fig = report.plot_comparison([second_result])
            assert fig is not None
            plt.close(fig)
        finally:
            plt.ioff()
