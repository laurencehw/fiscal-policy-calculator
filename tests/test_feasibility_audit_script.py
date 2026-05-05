"""Tests for the executable feasibility audit CLI wiring."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_feasibility_audit.py"
SPEC = importlib.util.spec_from_file_location("run_feasibility_audit_script", SCRIPT_PATH)
assert SPEC is not None
run_feasibility_audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = run_feasibility_audit
SPEC.loader.exec_module(run_feasibility_audit)


class _FakeAudit:
    ready_for_spike = True

    def to_dict(self) -> dict:
        return {"ready_for_spike": True}


class _FakeBundle:
    results = []
    errors = {}
    max_gap = None

    def to_dict(self) -> dict:
        return {"results": [], "errors": {}, "max_gap": None}


class _FakeAssessment:
    ready_for_spike = True

    def to_dict(self) -> dict:
        return {"ready_for_spike": True, "status": "ready"}


def test_model_pilot_uses_real_data_by_default(monkeypatch, capsys):
    seen: dict[str, object] = {}

    monkeypatch.setattr(run_feasibility_audit, "audit_cps_microsim_readiness", lambda **kwargs: _FakeAudit())
    monkeypatch.setattr(
        run_feasibility_audit,
        "build_default_comparison_models",
        lambda scorer, **kwargs: seen.setdefault("model_kwargs", kwargs) or [],
    )
    monkeypatch.setattr(run_feasibility_audit, "compare_policy_models", lambda *args, **kwargs: _FakeBundle())
    monkeypatch.setattr(run_feasibility_audit, "assess_model_pilot_comparison", lambda bundle: _FakeAssessment())
    monkeypatch.setattr(sys, "argv", ["run_feasibility_audit", "--include-model-pilot", "--json"])

    assert run_feasibility_audit.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert seen["model_kwargs"]["use_real_data"] is True
    assert payload["model_pilot_config"] == {
        "include_experimental_pwbm": False,
        "use_real_data": True,
    }


def test_model_pilot_can_use_synthetic_cbo(monkeypatch, capsys):
    seen: dict[str, object] = {}

    monkeypatch.setattr(run_feasibility_audit, "audit_cps_microsim_readiness", lambda **kwargs: _FakeAudit())
    monkeypatch.setattr(
        run_feasibility_audit,
        "build_default_comparison_models",
        lambda scorer, **kwargs: seen.setdefault("model_kwargs", kwargs) or [],
    )
    monkeypatch.setattr(run_feasibility_audit, "compare_policy_models", lambda *args, **kwargs: _FakeBundle())
    monkeypatch.setattr(run_feasibility_audit, "assess_model_pilot_comparison", lambda bundle: _FakeAssessment())
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_feasibility_audit", "--include-model-pilot", "--use-synthetic-cbo", "--json"],
    )

    assert run_feasibility_audit.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert seen["model_kwargs"]["use_real_data"] is False
    assert payload["model_pilot_config"]["use_real_data"] is False
