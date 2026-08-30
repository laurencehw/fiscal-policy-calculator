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
