"""
Tests for the bracket-specific calibration warning in the Distribution tab.

The warning is the user-facing surface for the SOI calibration work in
``fiscal_model.microsim.soi_calibration``. It must trigger when the
policy's target band is underweighted in the microdata and stay silent
when the band is well-covered or when no threshold applies.
"""

from __future__ import annotations

from types import SimpleNamespace

from fiscal_model.microsim.soi_calibration import BracketComparison, CalibrationReport
from fiscal_model.ui.tabs import distribution_analysis


class _StubStreamlit:
    def __init__(self):
        self.warnings: list[str] = []
        self.session_state: dict = {}

    def warning(self, text: str):
        self.warnings.append(text)


def _make_report(*brackets: tuple[float, float | None, float, float, float, float]) -> CalibrationReport:
    rows = [
        BracketComparison(
            lower=lower,
            upper=upper,
            microsim_returns=m_r,
            soi_returns=s_r,
            microsim_agi_billions=m_a,
            soi_agi_billions=s_a,
        )
        for lower, upper, m_r, s_r, m_a, s_a in brackets
    ]
    return CalibrationReport(year=2022, brackets=rows)


def test_warning_fires_when_agi_ratio_below_70pct():
    st = _StubStreamlit()
    report = _make_report(
        (0.0, 500_000.0, 100.0, 100.0, 100.0, 100.0),  # well-covered
        (500_000.0, None, 40.0, 100.0, 30.0, 100.0),   # 30% AGI ratio
    )
    st.session_state[distribution_analysis._CALIBRATION_SESSION_KEY] = report

    policy = SimpleNamespace(affected_income_threshold=750_000)
    distribution_analysis._render_calibration_warning(st, policy)

    assert st.warnings, "Expected a warning for <70% covered band"
    msg = st.warnings[0]
    assert "coverage warning" in msg.lower()
    assert "30%" in msg  # reports the ratio
    assert "VALIDATION_NOTES" in msg  # points at diagnostic doc


def test_no_warning_when_agi_ratio_above_threshold():
    st = _StubStreamlit()
    report = _make_report(
        (0.0, 500_000.0, 100.0, 100.0, 100.0, 100.0),
        (500_000.0, None, 95.0, 100.0, 95.0, 100.0),  # 95% ratio — fine
    )
    st.session_state[distribution_analysis._CALIBRATION_SESSION_KEY] = report

    policy = SimpleNamespace(affected_income_threshold=750_000)
    distribution_analysis._render_calibration_warning(st, policy)

    assert not st.warnings


def test_no_warning_when_no_threshold():
    st = _StubStreamlit()
    report = _make_report((500_000.0, None, 10.0, 100.0, 5.0, 100.0))
    st.session_state[distribution_analysis._CALIBRATION_SESSION_KEY] = report

    policy = SimpleNamespace(affected_income_threshold=0)
    distribution_analysis._render_calibration_warning(st, policy)

    assert not st.warnings


def test_no_warning_when_threshold_lands_in_well_covered_band():
    st = _StubStreamlit()
    report = _make_report(
        (0.0, 500_000.0, 100.0, 100.0, 100.0, 100.0),  # well-covered
        (500_000.0, None, 40.0, 100.0, 30.0, 100.0),   # under-covered
    )
    st.session_state[distribution_analysis._CALIBRATION_SESSION_KEY] = report

    # Threshold sits in the well-covered bracket (< $500K).
    policy = SimpleNamespace(affected_income_threshold=100_000)
    distribution_analysis._render_calibration_warning(st, policy)

    assert not st.warnings


def test_warning_handles_missing_policy_attribute():
    """Spending policies have no ``affected_income_threshold`` — must not crash."""
    st = _StubStreamlit()
    policy = SimpleNamespace()  # no threshold attribute at all
    distribution_analysis._render_calibration_warning(st, policy)
    assert not st.warnings


def test_calibration_report_is_cached_in_session(monkeypatch):
    """The loader+calibration must only run once per session."""
    st = _StubStreamlit()
    calls = {"count": 0}

    def fake_calibrate(*args, **kwargs):
        calls["count"] += 1
        return _make_report((0.0, None, 100.0, 100.0, 100.0, 100.0))

    def fake_load():
        return object(), object()

    monkeypatch.setattr(distribution_analysis, "_CALIBRATION_SESSION_KEY", "_test_key")
    # Reroute the lazy import inside _render_calibration_warning.
    import fiscal_model.data.cps_asec as loader_mod
    import fiscal_model.microsim.soi_calibration as cal_mod

    monkeypatch.setattr(cal_mod, "calibrate_to_soi", fake_calibrate)
    monkeypatch.setattr(loader_mod, "load_tax_microdata", fake_load)

    policy = SimpleNamespace(affected_income_threshold=100_000)
    distribution_analysis._render_calibration_warning(st, policy)
    distribution_analysis._render_calibration_warning(st, policy)

    assert calls["count"] == 1, "Calibration recomputed on second call"
