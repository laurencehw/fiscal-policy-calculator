"""Tests for helpers added in the UI/product review fix pass."""

from __future__ import annotations

from fiscal_model.ui.controller_utils import friendly_error_message
from fiscal_model.ui.helpers import escape_markdown_dollars, validated_policy_count


class TestEscapeMarkdownDollars:
    def test_escapes_currency_pairs(self) -> None:
        text = "Top group: −$18,642 (−4.42% of income); bottom: +$30"
        out = escape_markdown_dollars(text)
        assert "\\$18,642" in out
        assert "\\$30" in out

    def test_leaves_already_escaped_alone(self) -> None:
        assert escape_markdown_dollars("costs \\$1.7T") == "costs \\$1.7T"

    def test_leaves_non_currency_dollars_alone(self) -> None:
        # A `$` not followed by a digit (e.g. LaTeX like $\alpha$) is untouched.
        assert escape_markdown_dollars("$\\alpha$") == "$\\alpha$"

    def test_empty_string(self) -> None:
        assert escape_markdown_dollars("") == ""


class TestValidatedPolicyCount:
    def test_matches_scorecard_total(self) -> None:
        from fiscal_model.validation.scorecard import cached_default_scorecard

        assert validated_policy_count() == cached_default_scorecard().total_entries


class TestFriendlyErrorMessage:
    def test_translates_phase_in_validation(self) -> None:
        msg = friendly_error_message(ValueError("phase_in_years must be >= 1, got 0"))
        assert "phase_in_years" not in msg
        assert "at least 1 year" in msg

    def test_passes_through_unknown_errors(self) -> None:
        msg = friendly_error_message(RuntimeError("boom"))
        assert msg == "boom"


class TestBuildMacroScenario:
    """The macro scenario must carry the conventional deficit path.

    Pins two bugs: behavioral_offset (deficit convention) was added to
    static_revenue_effect (revenue convention), double-counting the offset;
    and spending policies produced an all-zero scenario because their
    impulse lives in static_spending_effect.
    """

    @staticmethod
    def _scenario_for(policy, *, is_spending):
        import numpy as np

        from fiscal_model.models import MacroScenario
        from fiscal_model.scoring import FiscalPolicyScorer
        from fiscal_model.ui.helpers import build_macro_scenario

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)
        scenario = build_macro_scenario(
            policy=policy,
            result=result,
            is_spending_policy=is_spending,
            macro_scenario_cls=MacroScenario,
        )
        return np, result, scenario

    def test_tax_receipts_net_of_behavioral(self) -> None:
        from fiscal_model.policies import PolicyType, TaxPolicy

        policy = TaxPolicy(
            name="raise",
            description="+1pp above 400K",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=400_000,
        )
        np, result, scenario = self._scenario_for(policy, is_spending=False)
        expected = -(result.static_deficit_effect + result.behavioral_offset)
        np.testing.assert_allclose(scenario.receipts_change, expected)
        # Receipts rise, but by less than the static gain (ETI erosion).
        assert scenario.receipts_change.sum() > 0
        assert scenario.receipts_change.sum() < result.static_revenue_effect.sum()
        assert not scenario.outlays_change.any()

    def test_spending_scenario_is_not_all_zero(self) -> None:
        from fiscal_model.policies import PolicyType, SpendingPolicy

        policy = SpendingPolicy(
            name="infra",
            description="$50B/yr infrastructure",
            policy_type=PolicyType.INFRASTRUCTURE,
            annual_spending_change_billions=50.0,
        )
        np, result, scenario = self._scenario_for(policy, is_spending=True)
        assert scenario.outlays_change.any(), (
            "Spending impulse must reach the macro adapter"
        )
        np.testing.assert_allclose(
            scenario.outlays_change,
            result.static_deficit_effect + result.behavioral_offset,
        )
        assert not scenario.receipts_change.any()
