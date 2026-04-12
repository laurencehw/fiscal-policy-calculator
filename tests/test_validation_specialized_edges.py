from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import fiscal_model.validation.specialized_benefits as benefits
import fiscal_model.validation.specialized_household as household
from fiscal_model.validation.core import ValidationResult


def _scorer_factory(total_10yr: float, annual: list[float] | None = None):
    years = np.arange(2026, 2036)
    annual_path = np.array(
        annual if annual is not None else [total_10yr / len(years)] * len(years),
        dtype=float,
    )

    class DummyScorer:
        def __init__(self, *args, **kwargs):
            del args, kwargs

        def score_policy(self, policy, dynamic=False):
            del policy
            assert dynamic is False
            return SimpleNamespace(
                total_10_year_cost=total_10yr,
                final_deficit_effect=annual_path,
                years=years,
            )

    return DummyScorer


def _result(policy_id: str, *, accurate: bool = True) -> ValidationResult:
    percent_diff = 5.0 if accurate else 25.0
    return ValidationResult(
        policy_id=policy_id,
        policy_name=policy_id,
        official_10yr=100.0,
        official_source="Test",
        model_10yr=105.0 if accurate else 130.0,
        model_first_year=10.0,
        difference=5.0 if accurate else 30.0,
        percent_difference=percent_diff,
        direction_match=accurate,
        accuracy_rating="Excellent" if accurate else "Poor",
    )


def test_validate_amt_policy_rejects_unknown_scenario(monkeypatch):
    monkeypatch.setattr(benefits, "AMT_VALIDATION_SCENARIOS_COMPARE", {"known": {}})

    with pytest.raises(ValueError, match="Unknown scenario: missing"):
        benefits.validate_amt_policy("missing", verbose=False)


def test_validate_amt_policy_prints_verbose_details(monkeypatch, capsys):
    monkeypatch.setattr(
        benefits,
        "AMT_VALIDATION_SCENARIOS_COMPARE",
        {
            "amt": {
                "description": "AMT scenario",
                "policy_factory": lambda **kwargs: SimpleNamespace(
                    start_year=2026,
                    extend_tcja_relief=kwargs["extend_tcja_relief"],
                    repeal_individual_amt=False,
                    repeal_corporate_amt=True,
                ),
                "kwargs": {"extend_tcja_relief": True},
                "expected_10yr": 225.0,
                "notes": "amt note",
            }
        },
    )
    monkeypatch.setattr(benefits, "FiscalPolicyScorer", _scorer_factory(220.0))

    result = benefits.validate_amt_policy("amt", verbose=True)
    output = capsys.readouterr().out

    assert result.model_parameters["amt_type"] == "unknown"
    assert result.model_parameters["extend_tcja_relief"] is True
    assert result.model_parameters["repeal_corporate_amt"] is True
    assert "AMT Validation: AMT scenario" in output
    assert "Notes: amt note" in output


def test_validate_ptc_policy_rejects_unknown_scenario(monkeypatch):
    monkeypatch.setattr(benefits, "PTC_VALIDATION_SCENARIOS_COMPARE", {"known": {}})

    with pytest.raises(ValueError, match="Unknown scenario: missing"):
        benefits.validate_ptc_policy("missing", verbose=False)


def test_validate_all_ptc_handles_errors_and_prints_context(monkeypatch, capsys):
    monkeypatch.setattr(benefits, "PTC_VALIDATION_SCENARIOS_COMPARE", {"ok": {}, "bad": {}})

    def fake_validate(scenario_id: str, verbose: bool = True):
        del verbose
        if scenario_id == "bad":
            raise RuntimeError("ptc boom")
        return _result("ok", accurate=False)

    monkeypatch.setattr(benefits, "validate_ptc_policy", fake_validate)

    results = benefits.validate_all_ptc(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "PREMIUM TAX CREDIT MODEL VALIDATION" in output
    assert "Error validating bad: ptc boom" in output
    assert "KEY CONTEXT: Premium Tax Credits (ACA)" in output
    assert "Direction match: 0/1" in output


def test_validate_credit_policy_handles_zero_expected_and_missing_attrs(monkeypatch):
    monkeypatch.setattr(
        household,
        "TAX_CREDIT_VALIDATION_SCENARIOS",
        {
            "credit": {
                "description": "Zero baseline credit",
                "policy_factory": lambda: SimpleNamespace(start_year=2026),
                "expected_10yr": 0.0,
            }
        },
    )
    monkeypatch.setattr(household, "FiscalPolicyScorer", _scorer_factory(-25.0, annual=[-2.5] * 10))

    result = household.validate_credit_policy("credit", verbose=False)

    assert result.model_10yr == 25.0
    assert result.percent_difference == 0.0
    assert result.difference == 25.0
    assert result.model_parameters["credit_type"] == "unknown"
    assert result.model_parameters["max_credit_per_unit"] == 0
    assert result.model_parameters["units_affected_millions"] == 0


def test_validate_all_credits_handles_errors_and_prints_context(monkeypatch, capsys):
    monkeypatch.setattr(household, "TAX_CREDIT_VALIDATION_SCENARIOS", {"ok": {}, "bad": {}})

    def fake_validate(scenario_id: str, verbose: bool = True):
        del verbose
        if scenario_id == "bad":
            raise RuntimeError("credit boom")
        return _result("ok")

    monkeypatch.setattr(household, "validate_credit_policy", fake_validate)

    results = household.validate_all_credits(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "TAX CREDIT MODEL VALIDATION" in output
    assert "Error validating bad: credit boom" in output
    assert "KEY CONTEXT: Tax Credit Scoring" in output


def test_validate_estate_policy_rejects_unknown_scenario(monkeypatch):
    monkeypatch.setattr(household, "ESTATE_TAX_VALIDATION_SCENARIOS", {"known": {}})

    with pytest.raises(ValueError, match="Unknown scenario: missing"):
        household.validate_estate_policy("missing", verbose=False)


def test_validate_estate_policy_prints_verbose_details(monkeypatch, capsys):
    monkeypatch.setattr(
        household,
        "ESTATE_TAX_VALIDATION_SCENARIOS",
        {
            "estate": {
                "description": "Estate scenario",
                "policy_factory": lambda: SimpleNamespace(
                    start_year=2026,
                    exemption_change=-7_000_000,
                    new_exemption=7_000_000,
                    extend_tcja_exemption=False,
                    rate_change=0.05,
                ),
                "expected_10yr": -450.0,
                "source": "Treasury",
                "notes": "estate note",
            }
        },
    )
    monkeypatch.setattr(household, "FiscalPolicyScorer", _scorer_factory(-480.0))

    result = household.validate_estate_policy("estate", verbose=True)
    output = capsys.readouterr().out

    assert result.model_parameters["new_exemption"] == 7_000_000
    assert result.model_parameters["rate_change"] == 0.05
    assert "Estate Tax Validation: Estate scenario" in output
    assert "Notes: estate note" in output


def test_validate_all_estate_handles_errors(monkeypatch, capsys):
    monkeypatch.setattr(household, "ESTATE_TAX_VALIDATION_SCENARIOS", {"ok": {}, "bad": {}})

    def fake_validate(scenario_id: str, verbose: bool = True):
        del verbose
        if scenario_id == "bad":
            raise RuntimeError("estate boom")
        return _result("ok")

    monkeypatch.setattr(household, "validate_estate_policy", fake_validate)

    results = household.validate_all_estate(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "ESTATE TAX MODEL VALIDATION" in output
    assert "Error validating bad: estate boom" in output


def test_validate_payroll_policy_rejects_unknown_scenario(monkeypatch):
    monkeypatch.setattr(household, "PAYROLL_TAX_VALIDATION_SCENARIOS", {"known": {}})

    with pytest.raises(ValueError, match="Unknown scenario: missing"):
        household.validate_payroll_policy("missing", verbose=False)


def test_validate_payroll_policy_prints_verbose_details(monkeypatch, capsys):
    monkeypatch.setattr(
        household,
        "PAYROLL_TAX_VALIDATION_SCENARIOS",
        {
            "payroll": {
                "description": "Payroll scenario",
                "policy_factory": lambda: SimpleNamespace(
                    start_year=2026,
                    ss_eliminate_cap=True,
                    ss_cover_90_pct=False,
                    ss_donut_hole_start=250_000,
                    expand_niit_to_passthrough=True,
                ),
                "expected_10yr": -2_700.0,
                "notes": "payroll note",
            }
        },
    )
    monkeypatch.setattr(household, "FiscalPolicyScorer", _scorer_factory(-2_400.0))

    result = household.validate_payroll_policy("payroll", verbose=True)
    output = capsys.readouterr().out

    assert result.model_parameters["ss_eliminate_cap"] is True
    assert result.model_parameters["ss_donut_hole_start"] == 250_000
    assert result.model_parameters["expand_niit"] is True
    assert "Payroll Tax Validation: Payroll scenario" in output
    assert "Notes: payroll note" in output
