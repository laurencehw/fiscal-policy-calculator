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
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # Non-interactive backend for CI

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.reporting import BudgetReport, create_comparison_table
from fiscal_model.scoring import FiscalPolicyScorer, ScoringResult

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
def dynamic_result(scorer, simple_policy):
    return scorer.score_policy(simple_policy, dynamic=True)


@pytest.fixture
def report(scoring_result):
    return BudgetReport(scoring_result)


@pytest.fixture
def dynamic_report(dynamic_result):
    return BudgetReport(dynamic_result)


@pytest.fixture
def zero_report(scoring_result):
    zeros = np.zeros_like(scoring_result.years, dtype=float)
    result = ScoringResult(
        policy=scoring_result.policy,
        baseline=scoring_result.baseline,
        years=scoring_result.years,
        static_revenue_effect=zeros.copy(),
        static_spending_effect=zeros.copy(),
        static_deficit_effect=zeros.copy(),
        behavioral_offset=zeros.copy(),
        dynamic_effects=None,
        final_deficit_effect=zeros.copy(),
        low_estimate=zeros.copy(),
        high_estimate=zeros.copy(),
    )
    return BudgetReport(result)


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

    def test_dynamic_report_contains_economic_effects(self, dynamic_report):
        text = dynamic_report.generate_text_report()
        assert "ECONOMIC EFFECTS" in text
        assert "Economic Feedback" in text


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

    def test_plot_budget_effects_dynamic_returns_figure(self, dynamic_report):
        import matplotlib.pyplot as plt
        fig = dynamic_report.plot_budget_effects(show=False)
        assert fig is not None
        plt.close(fig)

    def test_plot_budget_effects_save_path(self, report, tmp_path):
        import matplotlib.pyplot as plt
        output = tmp_path / "budget-effects.png"
        fig = report.plot_budget_effects(save_path=str(output), show=False)
        assert output.exists()
        plt.close(fig)

    def test_plot_budget_effects_show_true_avoids_backend_warning(self, report):
        import matplotlib.pyplot as plt
        fig = report.plot_budget_effects(show=True)
        assert fig is not None
        plt.close(fig)

    def test_plot_budget_effects_handles_zero_components(self, zero_report):
        import matplotlib.pyplot as plt
        fig = zero_report.plot_budget_effects(show=False)
        assert any(text.get_text() == "No significant components" for text in fig.axes[3].texts)
        plt.close(fig)

    def test_plot_comparison_callable(self, report, second_result):
        """plot_comparison is callable."""
        import matplotlib.pyplot as plt
        fig = report.plot_comparison([second_result], show=True)
        assert fig is not None
        plt.close(fig)

    def test_plot_comparison_save_path(self, report, second_result, tmp_path):
        import matplotlib.pyplot as plt
        output = tmp_path / "comparison.png"
        fig = report.plot_comparison([second_result], save_path=str(output), show=False)
        assert output.exists()
        plt.close(fig)

    def test_export_to_csv_writes_file(self, report, tmp_path):
        output = tmp_path / "budget-effects.csv"
        report.export_to_csv(str(output))
        assert output.exists()
        csv_text = output.read_text(encoding="utf-8")
        assert "Year" in csv_text
        assert "Final Deficit Effect ($B)" in csv_text

    def test_export_to_excel_writes_expected_sheets(self, dynamic_report, tmp_path):
        output = tmp_path / "budget-effects.xlsx"
        dynamic_report.export_to_excel(str(output))
        assert output.exists()
        workbook = pd.ExcelFile(output)
        assert set(workbook.sheet_names) == {"Budget Effects", "Summary", "Economic Effects"}
