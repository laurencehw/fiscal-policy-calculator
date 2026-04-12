"""
Focused tests for specialized validation runner modules.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import fiscal_model.validation.specialized_benefits as benefits
import fiscal_model.validation.specialized_business as business
import fiscal_model.validation.specialized_capital_gains as capital_gains
import fiscal_model.validation.specialized_household as household
import fiscal_model.validation.specialized_tcja as tcja
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


def test_validate_ptc_policy_verbose(monkeypatch, capsys):
    monkeypatch.setattr(
        benefits,
        "PTC_VALIDATION_SCENARIOS_COMPARE",
        {
            "ptc": {
                "description": "PTC scenario",
                "policy_factory": lambda: SimpleNamespace(
                    start_year=2026,
                    scenario=SimpleNamespace(value="extend"),
                    extend_enhanced=True,
                    repeal_ptc=False,
                ),
                "expected_10yr": 350.0,
                "source": "CBO",
                "notes": "note",
            }
        },
    )
    monkeypatch.setattr(benefits, "FiscalPolicyScorer", _scorer_factory(320.0))

    result = benefits.validate_ptc_policy("ptc", verbose=True)
    output = capsys.readouterr().out

    assert result.policy_id == "ptc"
    assert result.model_parameters["scenario"] == "extend"
    assert "PTC Validation: PTC scenario" in output
    assert "Year-by-year:" in output


def test_validate_all_amt_handles_errors_and_prints_summary(monkeypatch, capsys):
    monkeypatch.setattr(benefits, "AMT_VALIDATION_SCENARIOS_COMPARE", {"ok": {}, "bad": {}})

    def fake_validate(scenario_id: str, verbose: bool = True):
        del verbose
        if scenario_id == "bad":
            raise RuntimeError("boom")
        return _result("ok")

    monkeypatch.setattr(benefits, "validate_amt_policy", fake_validate)

    results = benefits.validate_all_amt(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "AMT MODEL VALIDATION" in output
    assert "Error validating bad: boom" in output
    assert "Within 20% accuracy: 1/1" in output


def test_validate_corporate_policy_uses_known_score_and_breakdown(monkeypatch, capsys):
    policy = SimpleNamespace(
        rate_change=0.07,
        baseline_rate=0.21,
        corporate_elasticity=0.2,
        get_component_breakdown=lambda: {
            "rate_change_effect": -1100.0,
            "international_effect": -150.0,
            "behavioral_offset": 50.0,
            "net_effect": -1200.0,
        },
    )
    monkeypatch.setattr(
        business,
        "CORPORATE_VALIDATION_SCENARIOS",
        {
            "corp": {
                "description": "Corporate scenario",
                "policy_factory": lambda: policy,
                "expected_10yr": -900.0,
                "score_id": "corp_score",
                "notes": "note",
            }
        },
    )
    monkeypatch.setattr(
        business,
        "KNOWN_SCORES",
        {"corp_score": SimpleNamespace(ten_year_cost=-1347.0, source=SimpleNamespace(value="Treasury"))},
    )
    monkeypatch.setattr(business, "FiscalPolicyScorer", _scorer_factory(-1300.0))

    result = business.validate_corporate_policy("corp", verbose=True)
    output = capsys.readouterr().out

    assert result.official_10yr == -1347.0
    assert result.official_source == "Treasury"
    assert result.model_parameters["baseline_rate"] == 0.21
    assert "Component breakdown (annual):" in output


def test_validate_all_expenditures_handles_summary(monkeypatch, capsys):
    monkeypatch.setattr(business, "TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE", {"ok": {}})
    monkeypatch.setattr(business, "validate_expenditure_policy", lambda scenario_id, verbose=True: _result(scenario_id))

    results = business.validate_all_expenditures(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "TAX EXPENDITURE MODEL VALIDATION" in output
    assert "KEY CONTEXT: Major Tax Expenditures" in output


def test_validate_capital_gains_policy_applies_step_up_fields(monkeypatch, capsys):
    policy = SimpleNamespace(
        rate_change=0.196,
        affected_income_threshold=400_000,
        baseline_capital_gains_rate=0.238,
        baseline_realizations_billions=100.0,
        short_run_elasticity=0.8,
        long_run_elasticity=0.4,
    )
    monkeypatch.setattr(
        capital_gains,
        "CAPITAL_GAINS_VALIDATION_SCENARIOS",
        {
            "cap": {
                "description": "Capital gains scenario",
                "score_id": "cg_score",
                "baseline_capital_gains_rate": 0.238,
                "baseline_realizations_billions": 100.0,
                "short_run_elasticity": 0.8,
                "long_run_elasticity": 0.4,
                "eliminate_step_up": True,
                "step_up_exemption": 0.0,
                "gains_at_death_billions": 0.0,
                "notes": "note",
            }
        },
    )
    monkeypatch.setattr(
        capital_gains,
        "KNOWN_SCORES",
        {"cg_score": SimpleNamespace(ten_year_cost=113.0, source=SimpleNamespace(value="PWBM"))},
    )
    monkeypatch.setattr(capital_gains, "create_capital_gains_policy_from_score", lambda *args, **kwargs: policy)
    monkeypatch.setattr(capital_gains, "FiscalPolicyScorer", _scorer_factory(120.0))

    result = capital_gains.validate_capital_gains_policy("cap", verbose=True)
    output = capsys.readouterr().out

    assert result.official_source == "PWBM"
    assert policy.eliminate_step_up is True
    assert policy.step_up_exemption == 0.0
    assert "Capital Gains Validation: Capital gains scenario" in output


def test_validate_all_capital_gains_handles_error(monkeypatch, capsys):
    monkeypatch.setattr(capital_gains, "CAPITAL_GAINS_VALIDATION_SCENARIOS", {"ok": {}, "bad": {}})

    def fake_validate(scenario_id: str, verbose: bool = True):
        del verbose
        if scenario_id == "bad":
            raise RuntimeError("no score")
        return _result("ok")

    monkeypatch.setattr(capital_gains, "validate_capital_gains_policy", fake_validate)

    results = capital_gains.validate_all_capital_gains(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "Error validating bad: no score" in output
    assert "KEY INSIGHT: Step-Up Basis Effect" in output


def test_validate_credit_policy_uses_absolute_cost(monkeypatch, capsys):
    monkeypatch.setattr(
        household,
        "TAX_CREDIT_VALIDATION_SCENARIOS",
        {
            "credit": {
                "description": "Credit scenario",
                "policy_factory": lambda: SimpleNamespace(
                    start_year=2026,
                    credit_type=SimpleNamespace(value="ctc"),
                    max_credit_per_unit=3600,
                    units_affected_millions=40.0,
                ),
                "expected_10yr": 1600.0,
                "source": "CBO",
                "notes": "note",
            }
        },
    )
    monkeypatch.setattr(household, "FiscalPolicyScorer", _scorer_factory(-1500.0, annual=[-150.0] * 10))

    result = household.validate_credit_policy("credit", verbose=True)
    output = capsys.readouterr().out

    assert result.model_10yr == 1500.0
    assert result.direction_match is True
    assert "Tax Credit Validation: Credit scenario" in output


def test_validate_all_estate_and_payroll_summaries(monkeypatch, capsys):
    monkeypatch.setattr(household, "ESTATE_TAX_VALIDATION_SCENARIOS", {"estate": {}})
    monkeypatch.setattr(household, "PAYROLL_TAX_VALIDATION_SCENARIOS", {"payroll": {}})
    monkeypatch.setattr(household, "validate_estate_policy", lambda scenario_id, verbose=True: _result(scenario_id))
    monkeypatch.setattr(household, "validate_payroll_policy", lambda scenario_id, verbose=True: _result(scenario_id, accurate=False))

    estate_results = household.validate_all_estate(verbose=True)
    estate_output = capsys.readouterr().out
    payroll_results = household.validate_all_payroll(verbose=True)
    payroll_output = capsys.readouterr().out

    assert len(estate_results) == 1
    assert "KEY CONTEXT: Estate Tax Scoring" in estate_output
    assert len(payroll_results) == 1
    assert "KEY CONTEXT: Payroll Tax Scoring" in payroll_output


def test_validate_tcja_extension_selects_partial_and_salt_paths(monkeypatch, capsys):
    partial_calls = []
    salt_calls = []

    def partial_factory(**kwargs):
        partial_calls.append(kwargs)
        return SimpleNamespace(
            calibration_factor=1.0,
            get_component_breakdown=lambda: None,
        )

    def salt_factory():
        salt_calls.append(True)
        return SimpleNamespace(
            calibration_factor=1.2,
            get_component_breakdown=lambda: {
                "salt": {"name": "SALT", "ten_year_cost": 1100.0, "is_offset": False}
            },
        )

    monkeypatch.setattr(tcja, "create_tcja_extension", partial_factory)
    monkeypatch.setattr(tcja, "create_tcja_repeal_salt_cap", salt_factory)
    monkeypatch.setattr(tcja, "FiscalPolicyScorer", _scorer_factory(3300.0))
    monkeypatch.setattr(
        tcja,
        "TCJA_VALIDATION_SCENARIOS",
        {
            "partial": {
                "description": "Partial extension",
                "extend_all": False,
                "extend_rates": True,
                "extend_standard_deduction": False,
                "keep_exemption_elimination": False,
                "extend_passthrough": False,
                "extend_ctc": False,
                "extend_estate": False,
                "extend_amt": False,
                "keep_salt_cap": False,
                "expected_10yr": 3185.0,
                "notes": "note",
            },
            "salt": {
                "description": "No SALT cap",
                "extend_all": True,
                "keep_salt_cap": False,
                "expected_10yr": 5700.0,
                "notes": "note",
            },
        },
    )

    partial_result = tcja.validate_tcja_extension("partial", verbose=False)
    salt_result = tcja.validate_tcja_extension("salt", verbose=True)
    output = capsys.readouterr().out

    assert partial_result.policy_id == "partial"
    assert partial_calls[0]["extend_all"] is False
    assert salt_result.model_parameters["keep_salt_cap"] is False
    assert salt_calls == [True]
    assert "Component breakdown (calibrated):" in output


def test_validate_all_tcja_summary(monkeypatch, capsys):
    monkeypatch.setattr(tcja, "TCJA_VALIDATION_SCENARIOS", {"one": {}})
    monkeypatch.setattr(tcja, "validate_tcja_extension", lambda scenario_id, verbose=True: _result(scenario_id))

    results = tcja.validate_all_tcja(verbose=True)
    output = capsys.readouterr().out

    assert len(results) == 1
    assert "TCJA EXTENSION MODEL VALIDATION" in output
    assert "KEY CONTEXT: TCJA Extension Scoring" in output
