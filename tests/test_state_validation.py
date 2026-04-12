"""
Unit tests for TAXSIM validation helpers.
"""

from __future__ import annotations

import numpy as np

from fiscal_model.models.state.validation import (
    TAXSIMClient,
    TAXSIMResult,
    ValidationReport,
    _make_cache_key,
    _parse_taxsim_response,
    _r2,
)


def test_validation_report_passes_thresholds():
    report = ValidationReport(
        state="CA",
        n_sample=25,
        federal_mean_abs_error=1000.0,
        federal_r2=0.98,
        state_mean_abs_error=500.0,
        state_r2=0.97,
        combined_mean_abs_error=2000.0,
        combined_r2=0.96,
    )

    assert report.passes()
    assert "CA:" in report.summary()


def test_make_cache_key_is_stable():
    taxpayer = {"year": 2025, "pwages": 100000}

    key1 = _make_cache_key(taxpayer, "CA")
    key2 = _make_cache_key({"pwages": 100000, "year": 2025}, "CA")

    assert key1 == key2


def test_parse_taxsim_response_returns_result():
    response = "fiitax,siitax,fica,frate,srate,tfica\n1000,200,7650,22,8,7.65\n"

    result = _parse_taxsim_response(response)

    assert result == TAXSIMResult(
        fiitax=1000.0,
        siitax=200.0,
        fica=7650.0,
        frate=22.0,
        srate=8.0,
        tfica=7.65,
    )


def test_parse_taxsim_response_rejects_invalid_payload():
    assert _parse_taxsim_response("bad,data") is None


def test_r2_handles_zero_variance_cases():
    assert _r2(np.array([10, 10]), np.array([10, 10])) == 1.0
    assert _r2(np.array([0, 0]), np.array([10, 10])) == 0.0


def test_taxsim_client_uses_cache_before_network(monkeypatch):
    cached = TAXSIMResult(100.0, 50.0, 20.0, 10.0, 5.0, 7.65)
    client = TAXSIMClient(cache={"existing": cached})
    monkeypatch.setattr(
        "fiscal_model.models.state.validation._make_cache_key",
        lambda taxpayer, state: "existing",
    )

    result = client.calculate({"year": 2025}, state="CA")

    assert result is cached


def test_taxsim_client_parses_network_response(monkeypatch):
    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        def read(self):
            return b"fiitax,siitax,fica,frate,srate,tfica\n100,50,20,22,8,7.65\n"

    client = TAXSIMClient()
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: _FakeResponse())
    monkeypatch.setattr("time.time", lambda: 100.0)

    result = client.calculate({"year": 2025, "state": 6, "pwages": 100000}, state="CA")

    assert result is not None
    assert result.fiitax == 100.0
