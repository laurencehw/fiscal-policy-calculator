"""
Integration tests for validation/compare.py — exercises the full validation
pipeline to increase coverage of all validate_*_policy and validate_all_*
functions.
"""

import pytest

from fiscal_model.validation.compare import (
    ValidationResult,
    _rate_accuracy,
    create_capital_gains_policy_from_score,
    create_policy_from_score,
    generate_validation_report,
    quick_validate,
    run_validation_suite,
    validate_all,
    validate_all_amt,
    validate_all_capital_gains,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_expenditures,
    validate_all_payroll,
    validate_all_ptc,
    validate_all_tcja,
    validate_policy,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES, get_validation_targets


# ── Helper tests ────────────────────────────────────────────────────────


class TestRateAccuracy:
    def test_excellent(self):
        assert _rate_accuracy(3.0) == "Excellent"
        assert _rate_accuracy(-4.9) == "Excellent"

    def test_good(self):
        assert _rate_accuracy(7.5) == "Good"

    def test_acceptable(self):
        assert _rate_accuracy(15.0) == "Acceptable"

    def test_poor(self):
        assert _rate_accuracy(25.0) == "Poor"


class TestValidationResult:
    def test_is_accurate(self):
        vr = ValidationResult(
            policy_id="test",
            policy_name="Test",
            official_10yr=100.0,
            official_source="CBO",
            model_10yr=110.0,
            model_first_year=11.0,
            difference=10.0,
            percent_difference=10.0,
            direction_match=True,
            accuracy_rating="Good",
        )
        assert vr.is_accurate

    def test_not_accurate(self):
        vr = ValidationResult(
            policy_id="test",
            policy_name="Test",
            official_10yr=100.0,
            official_source="CBO",
            model_10yr=200.0,
            model_first_year=20.0,
            difference=100.0,
            percent_difference=100.0,
            direction_match=True,
            accuracy_rating="Poor",
        )
        assert not vr.is_accurate

    def test_get_summary(self):
        vr = ValidationResult(
            policy_id="test",
            policy_name="Test Policy",
            official_10yr=100.0,
            official_source="CBO",
            model_10yr=105.0,
            model_first_year=10.5,
            difference=5.0,
            percent_difference=5.0,
            direction_match=True,
            accuracy_rating="Excellent",
        )
        s = vr.get_summary()
        assert "Test Policy" in s
        assert "Excellent" in s


class TestCreatePolicyFromScore:
    def test_income_tax_score(self):
        targets = get_validation_targets()
        for t in targets:
            policy = create_policy_from_score(t)
            if t.policy_type == "income_tax" and t.rate_change is not None:
                assert policy is not None
            break

    def test_non_income_tax_returns_none(self):
        from fiscal_model.validation.cbo_scores import CBOScore, ScoreSource

        s = CBOScore(
            policy_id="test_capgains",
            name="Test Cap Gains",
            description="Test",
            ten_year_cost=-100.0,
            source=ScoreSource.CBO,
            source_date="2025-01",
            policy_type="capital_gains",
        )
        assert create_policy_from_score(s) is None


# ── Full validation suite (exercises all validate_*_policy functions) ───


class TestValidateAll:
    """Run validate_all which exercises validate_policy for each target."""

    def test_validate_all_returns_results(self):
        results = validate_all(dynamic=False, verbose=False)
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert isinstance(r, ValidationResult)

    def test_run_validation_suite(self):
        summary = run_validation_suite(verbose=False)
        assert "total_policies" in summary
        assert summary["total_policies"] > 0
        assert "accuracy_rate" in summary
        assert "ratings" in summary

    def test_generate_report(self):
        results = validate_all(dynamic=False, verbose=False)
        report = generate_validation_report(results)
        assert isinstance(report, str)
        assert "Validation" in report or "validation" in report.lower()


class TestQuickValidate:
    def test_quick_validate_returns_result(self):
        result = quick_validate(
            rate_change=0.026,
            income_threshold=400_000,
            expected_10yr=-250.0,
        )
        assert isinstance(result, ValidationResult)
        assert result.direction_match


# ── Category-specific validate_all_* functions ─────────────────────────


class TestValidateAllCategories:
    """Each of these calls the validate_*_policy function for every policy
    in the category, exercising the bulk of compare.py."""

    def test_validate_all_tcja(self):
        results = validate_all_tcja(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_corporate(self):
        results = validate_all_corporate(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_credits(self):
        results = validate_all_credits(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_estate(self):
        results = validate_all_estate(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_payroll(self):
        results = validate_all_payroll(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_amt(self):
        results = validate_all_amt(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_ptc(self):
        results = validate_all_ptc(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_expenditures(self):
        results = validate_all_expenditures(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_validate_all_capital_gains(self):
        results = validate_all_capital_gains(verbose=False)
        assert isinstance(results, list)
        assert len(results) >= 1
