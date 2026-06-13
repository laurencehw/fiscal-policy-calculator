"""
Tests for ``summarize_data_degradation`` — the plain-language reducer that turns
a ``check_health()`` dict into a user-facing degraded-mode banner summary.
"""

from fiscal_model.health import summarize_data_degradation


def _ok_health() -> dict:
    return {
        "baseline": {"status": "ok", "source": "real", "freshness": {"is_stale": False}},
        "fred": {"status": "ok", "source": "live"},
        "irs_soi": {"status": "ok", "freshness": {"is_stale": False}},
        "microdata": {"status": "ok"},
        "runtime": {"status": "ok"},
    }


class TestHealthyState:
    def test_all_ok_is_not_degraded(self):
        summary = summarize_data_degradation(_ok_health())
        assert summary["severity"] == "ok"
        assert summary["is_degraded"] is False
        assert summary["reasons"] == []

    def test_empty_health_is_ok(self):
        # Missing components shouldn't crash or fabricate reasons.
        summary = summarize_data_degradation({})
        assert summary["severity"] == "ok"
        assert summary["reasons"] == []


class TestDegradedState:
    def test_hardcoded_baseline_is_degraded(self):
        health = _ok_health()
        health["baseline"]["source"] = "hardcoded_fallback"
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "degraded"
        assert any("baseline" in r.lower() for r in summary["reasons"])

    def test_stale_baseline_is_degraded(self):
        health = _ok_health()
        health["baseline"]["freshness"] = {"is_stale": True}
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "degraded"

    def test_fred_fallback_is_degraded(self):
        health = _ok_health()
        health["fred"] = {"status": "ok", "source": "fallback"}
        summary = summarize_data_degradation(health)
        assert summary["is_degraded"] is True
        assert any("FRED" in r for r in summary["reasons"])

    def test_stale_bundled_fred_seed_reports_age(self):
        health = _ok_health()
        health["fred"] = {
            "status": "ok", "source": "bundled",
            "cache_is_expired": True, "cache_age_days": 95,
        }
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "degraded"
        assert any("95 days" in r for r in summary["reasons"])

    def test_degraded_microdata_flags_top_tail(self):
        health = _ok_health()
        health["microdata"] = {"status": "degraded"}
        summary = summarize_data_degradation(health)
        assert any("Microdata" in r for r in summary["reasons"])

    def test_stale_irs_is_degraded(self):
        health = _ok_health()
        health["irs_soi"] = {"status": "ok", "freshness": {"is_stale": True}}
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "degraded"


class TestErrorState:
    def test_component_error_escalates_to_error(self):
        health = _ok_health()
        health["baseline"]["status"] = "error"
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "error"
        assert summary["is_degraded"] is True

    def test_error_dominates_degraded(self):
        # A degraded FRED plus an errored baseline -> overall error.
        health = _ok_health()
        health["baseline"]["status"] = "error"
        health["fred"] = {"status": "ok", "source": "fallback"}
        summary = summarize_data_degradation(health)
        assert summary["severity"] == "error"
        # Both reasons should be present.
        assert len(summary["reasons"]) >= 2

    def test_runtime_degraded_uses_message(self):
        health = _ok_health()
        health["runtime"] = {"status": "degraded", "message": "Python 3.8 is EOL"}
        summary = summarize_data_degradation(health)
        assert "Python 3.8 is EOL" in summary["reasons"]
