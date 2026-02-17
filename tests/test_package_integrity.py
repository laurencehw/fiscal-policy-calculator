"""
Regression tests for package wiring and baseline/data fallbacks.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.baseline import CBOBaseline
from fiscal_model.data import CapitalGainsBaseline, FREDData, IRSSOIData
from fiscal_model.preset_handler import create_policy_from_preset


def test_package_level_app_data_imports():
    assert isinstance(PRESET_POLICIES, dict)
    assert isinstance(CBO_SCORE_MAP, dict)
    assert len(PRESET_POLICIES) > 0


def test_preset_factory_covers_flagged_presets():
    flag_keys = [
        "is_tcja",
        "is_corporate",
        "is_credit",
        "is_estate",
        "is_payroll",
        "is_amt",
        "is_ptc",
        "is_expenditure",
    ]

    for name, preset in PRESET_POLICIES.items():
        if name == "Custom Policy":
            continue

        policy = create_policy_from_preset(preset)
        is_flagged = any(bool(preset.get(key, False)) for key in flag_keys)

        if is_flagged:
            assert policy is not None, f"Expected policy for preset: {name}"
        else:
            assert policy is None, f"Expected None for simple preset: {name}"


def test_irs_soi_loader_smoke():
    irs = IRSSOIData()
    years = irs.get_data_years_available()
    assert len(years) >= 1

    year = max(years)
    revenue = irs.get_total_revenue(year)
    assert revenue > 0

    filers = irs.get_filers_by_bracket(year=year, threshold=400_000)
    assert filers["num_filers"] > 0
    assert filers["avg_taxable_income"] >= 0


def test_capital_gains_baseline_smoke():
    baseline = CapitalGainsBaseline()
    result = baseline.get_baseline_above_threshold_with_rate_method(
        year=2024,
        threshold=400_000,
        rate_method="statutory_by_agi",
    )

    assert result["net_capital_gain_billions"] > 0
    assert 0 < result["average_effective_tax_rate"] < 1


def test_fred_data_is_available_returns_bool():
    fred = FREDData()
    assert isinstance(fred.is_available(), bool)


def test_cbo_baseline_fallback_when_data_load_fails(monkeypatch):
    def _raise_load_error(self):
        raise RuntimeError("forced load failure")

    monkeypatch.setattr(CBOBaseline, "_load_from_data_sources", _raise_load_error)

    baseline = CBOBaseline(use_real_data=True)
    projection = baseline.generate()

    assert len(projection.years) == 10
    assert projection.nominal_gdp[0] > 0
