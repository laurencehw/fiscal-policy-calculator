"""
Focused tests for the full FRB/US adapter path using fake pyfrbus modules.
"""

from __future__ import annotations

import sys
import types

import numpy as np
import pandas as pd

from fiscal_model.models import FiscalClosureType, FRBUSAdapter, MacroScenario


def _install_fake_pyfrbus(monkeypatch):
    periods = pd.period_range("2025Q1", "2036Q4", freq="Q")
    base = pd.DataFrame(
        {
            "xgdp": np.full(len(periods), 22_000.0),
            "xgdpn": np.full(len(periods), 30_000_000.0),
            "lur": np.full(len(periods), 4.0),
            "rff": np.full(len(periods), 4.5),
            "rg10": np.full(len(periods), 4.2),
            "picxfe": np.full(len(periods), 2.3),
            "gfexpn": np.full(len(periods), 6_500_000.0),
            "gfrecn": np.full(len(periods), 5_800_000.0),
            "gtn": np.full(len(periods), 4_000_000.0),
            "gfdbtn": np.full(len(periods), 34_000_000.0),
            "gfintn": np.full(len(periods), 900_000.0),
            "dfpdbt": np.zeros(len(periods)),
            "dfpsrp": np.zeros(len(periods)),
            "gfrecn_aerr": np.zeros(len(periods)),
            "gtn_aerr": np.zeros(len(periods)),
            "gfexpn_aerr": np.zeros(len(periods)),
        },
        index=periods,
    )

    class DummyFrbus:
        def __init__(self, model_path, mce=None):
            self.model_path = model_path
            self.mce = mce
            self.solve_flags: list[tuple[float, float]] = []

        def init_trac(self, start, end, data):
            del start, end
            return data.copy()

        def solve(self, start, end, data):
            result = data.copy()
            self.solve_flags.append(
                (
                    float(result.loc[start, "dfpdbt"]),
                    float(result.loc[start, "dfpsrp"]),
                )
            )

            receipts = result.loc[start:end, "gfrecn_aerr"].to_numpy(dtype=float)
            outlays = result.loc[start:end, "gfexpn_aerr"].to_numpy(dtype=float)
            debt_change = np.cumsum(outlays - receipts)
            gdp_shock = outlays * 0.002 - receipts * 0.001

            result.loc[start:end, "xgdp"] = result.loc[start:end, "xgdp"] + gdp_shock
            result.loc[start:end, "lur"] = result.loc[start:end, "lur"] - gdp_shock / 10_000
            result.loc[start:end, "rff"] = result.loc[start:end, "rff"] + debt_change / 1_000_000
            result.loc[start:end, "rg10"] = result.loc[start:end, "rg10"] + debt_change / 800_000
            result.loc[start:end, "gfdbtn"] = result.loc[start:end, "gfdbtn"] + debt_change
            return result

    frbus_mod = types.ModuleType("pyfrbus.frbus")
    frbus_mod.Frbus = DummyFrbus
    load_data_mod = types.ModuleType("pyfrbus.load_data")
    load_data_mod.load_data = lambda path: base.copy()
    pkg_mod = types.ModuleType("pyfrbus")

    monkeypatch.setitem(sys.modules, "pyfrbus", pkg_mod)
    monkeypatch.setitem(sys.modules, "pyfrbus.frbus", frbus_mod)
    monkeypatch.setitem(sys.modules, "pyfrbus.load_data", load_data_mod)


def test_frbus_adapter_run_and_baseline_with_fake_backend(monkeypatch):
    _install_fake_pyfrbus(monkeypatch)
    adapter = FRBUSAdapter(
        model_path="model.xml",
        data_path="LONGBASE.TXT",
        use_mce=True,
    )
    scenario = MacroScenario(
        name="Stimulus",
        description="Test",
        start_year=2025,
        horizon_years=2,
        receipts_change=np.array([-100.0, -50.0]),
        outlays_change=np.array([50.0, 25.0]),
    )

    result = adapter.run(scenario)
    baseline = adapter.get_baseline()

    assert adapter._model.mce == "mcap+wp"
    assert adapter._baseline_gdp == 30.0
    assert result.model_name == "FRB/US"
    assert len(result.years) == 2
    assert result.gdp_level_pct[0] > 0
    assert result.revenue_feedback_billions[0] > 0
    assert result.interest_cost_billions[0] > 0
    assert adapter._model.solve_flags[0] == (0.0, 1.0)
    assert len(baseline) == 10
    assert list(baseline.columns) == [
        "Year",
        "GDP ($T)",
        "Real GDP ($T)",
        "Unemployment (%)",
        "Fed Funds (%)",
        "10Y Rate (%)",
        "Core PCE (%)",
    ]


def test_frbus_adapter_respects_debt_accumulation_closure(monkeypatch):
    _install_fake_pyfrbus(monkeypatch)
    adapter = FRBUSAdapter(
        model_path="model.xml",
        data_path="LONGBASE.TXT",
        fiscal_closure=FiscalClosureType.DEBT_ACCUMULATION,
    )

    adapter.run(
        MacroScenario(
            name="Debt accumulation",
            description="Test",
            start_year=2025,
            horizon_years=1,
            receipts_change=np.array([0.0]),
            outlays_change=np.array([100.0]),
        )
    )

    assert adapter._model.solve_flags[0] == (0.0, 0.0)
