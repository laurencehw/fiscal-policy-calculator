"""
Tests for the Ask assistant's health and readiness integration.

Ensures that:
- ``check_health()`` surfaces the assistant component with the expected sub-
  signals (API key, knowledge corpus, usage db).
- Assistant degradation does NOT drag the overall health status (the
  assistant is an optional component).
- ``build_readiness_report()`` records the assistant as a non-required
  check whose warn doesn't escalate to ``not_ready``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fiscal_model.health import _check_assistant, check_health


class TestCheckAssistant:
    def test_reports_corpus_size(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        result = _check_assistant()
        assert "knowledge_corpus_files" in result
        # The corpus ships with ≥10 hand-curated snapshots (plus README).
        assert result["knowledge_corpus_files"] >= 5

    def test_ok_when_all_three_signals_pass(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        result = _check_assistant()
        assert result["status"] == "ok"
        assert result["api_key_configured"] is True
        assert result["usage_db_writable"] is True
        assert result["knowledge_corpus_files"] > 0

    def test_degraded_when_no_api_key(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        result = _check_assistant()
        assert result["status"] == "degraded"
        assert result["api_key_configured"] is False
        # Other signals still pass.
        assert result["knowledge_corpus_files"] > 0
        assert result["usage_db_writable"] is True


class TestCheckHealthIntegration:
    def test_assistant_present_in_results(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        health = check_health()
        assert "assistant" in health
        for key in ("status", "api_key_configured", "knowledge_corpus_files", "usage_db_writable"):
            assert key in health["assistant"]

    def test_assistant_degradation_does_not_taint_overall(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Missing API key must NOT push overall to degraded."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        health = check_health()
        # Assistant itself should be degraded.
        assert health["assistant"]["status"] == "degraded"
        # But the overall verdict is driven by required components only —
        # if those are healthy the overall stays "ok".
        required_statuses = {
            k: v.get("status")
            for k, v in health.items()
            if k in {"runtime", "model", "baseline", "fred", "irs_soi", "microdata"}
        }
        if all(s == "ok" for s in required_statuses.values()):
            assert health["overall"] == "ok"


class TestReadinessIntegration:
    def test_assistant_check_appears_in_readiness(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        from fiscal_model.readiness import build_readiness_report

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        report = build_readiness_report()
        names = {c.name for c in report.checks}
        assert "assistant" in names

    def test_assistant_warn_does_not_block_readiness(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        from fiscal_model.readiness import build_readiness_report

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.db"))
        report = build_readiness_report()
        assistant_checks = [c for c in report.checks if c.name == "assistant"]
        assert len(assistant_checks) == 1
        assistant_check = assistant_checks[0]
        # API key missing → warn, not fail; and non-required.
        assert assistant_check.status == "warn"
        assert assistant_check.required is False
        # Verdict can be either ready or ready_with_warnings, but never
        # not_ready solely from the assistant.
        assert report.verdict != "not_ready" or any(
            i.required for i in report.issues if i.severity == "fail"
        )
