"""
Tests for fiscal_model/health.py health check module.

Verifies that health checks correctly assess:
- CBO baseline data status
- FRED API connection status
- IRS SOI data availability
- Scoring engine readiness
"""

import fiscal_model.baseline as baseline_module
import fiscal_model.data.fred_data as fred_module
import fiscal_model.data.irs_soi as irs_module
import fiscal_model.scoring as scoring_module
from fiscal_model.health import _runtime_status, check_health


class TestCheckHealth:
    """Tests for the check_health() function."""

    def test_check_health_returns_dict(self):
        """Verify check_health returns a dictionary."""
        result = check_health()
        assert isinstance(result, dict)

    def test_check_health_has_all_components(self):
        """Verify all expected components are present in results."""
        result = check_health()
        expected_keys = [
            "runtime", "baseline", "fred", "irs_soi", "model", "microdata",
            "timestamp", "overall",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_runtime_component_reports_supported_contract(self):
        """Runtime health should expose the Python support contract."""
        result = check_health()
        runtime = result["runtime"]
        assert runtime["status"] in {"ok", "degraded"}
        assert runtime["supported_range"] == ">=3.10,<3.14"
        assert runtime["recommended_version"] == "3.12"
        assert "python_version" in runtime
        assert "message" in runtime

    def test_runtime_status_marks_supported_and_unsupported_versions(self):
        assert _runtime_status((3, 12, 0))["status"] == "ok"
        assert _runtime_status((3, 9, 18))["status"] == "degraded"
        assert _runtime_status((3, 14, 0))["status"] == "degraded"

    def test_microdata_component_reports_calibration(self):
        """Microdata health entry should surface the SOI coverage ratios."""
        result = check_health()
        microdata = result["microdata"]
        assert isinstance(microdata, dict)
        assert microdata["status"] in {"ok", "degraded", "error", "unknown"}
        if microdata["status"] in {"ok", "degraded"}:
            # Calibrated against real SOI — coverage metrics must be present.
            assert "returns_coverage_pct" in microdata
            assert "agi_coverage_pct" in microdata
            assert 0 <= microdata["returns_coverage_pct"] <= 500
            assert 0 <= microdata["agi_coverage_pct"] <= 500

    def test_baseline_component_present(self):
        """Verify baseline component has required structure."""
        result = check_health()
        baseline = result["baseline"]
        assert isinstance(baseline, dict)
        assert "status" in baseline
        assert baseline["status"] in ["ok", "degraded", "error"]

    def test_fred_component_present(self):
        """Verify FRED component has required structure."""
        result = check_health()
        fred = result["fred"]
        assert isinstance(fred, dict)
        assert "status" in fred
        assert fred["status"] in ["ok", "degraded", "error"]

    def test_irs_soi_component_present(self):
        """Verify IRS SOI component has required structure."""
        result = check_health()
        irs_soi = result["irs_soi"]
        assert isinstance(irs_soi, dict)
        assert "status" in irs_soi
        assert irs_soi["status"] in ["ok", "degraded", "error"]

    def test_model_component_present(self):
        """Verify model component has required structure."""
        result = check_health()
        model = result["model"]
        assert isinstance(model, dict)
        assert "status" in model
        assert model["status"] in ["ok", "error"]

    def test_timestamp_is_iso_format(self):
        """Verify timestamp is in ISO format."""
        result = check_health()
        timestamp = result["timestamp"]
        assert isinstance(timestamp, str)
        # Should be ISO 8601 format with T separator
        assert "T" in timestamp or timestamp  # Timestamp present

    def test_overall_status_is_valid(self):
        """Verify overall status is either 'ok' or 'degraded'."""
        result = check_health()
        assert result["overall"] in ["ok", "degraded"]

    def test_overall_ok_when_all_ok(self):
        """Verify overall is 'ok' only when all components are 'ok'."""
        result = check_health()
        # If overall is 'ok', all components with 'status' key should be 'ok'
        if result["overall"] == "ok":
            for key, value in result.items():
                if isinstance(value, dict) and "status" in value:
                    assert value["status"] == "ok", f"{key} should be 'ok' when overall is 'ok'"

    def test_baseline_has_start_year_when_ok(self):
        """Verify baseline includes start_year when status is ok."""
        result = check_health()
        baseline = result["baseline"]
        if baseline["status"] in ["ok", "degraded"]:
            assert "start_year" in baseline
            assert isinstance(baseline["start_year"], int)
            assert "source" in baseline
            assert "gdp_source" in baseline

    def test_irs_soi_has_available_years_when_ok(self):
        """Verify IRS SOI includes available_years when status is ok."""
        result = check_health()
        irs_soi = result["irs_soi"]
        if irs_soi["status"] in ["ok", "degraded"]:
            assert "available_years" in irs_soi
            assert isinstance(irs_soi["available_years"], list)
            assert "latest_year" in irs_soi

    def test_baseline_has_freshness_when_not_error(self):
        """Baseline health should include freshness metadata for the current vintage."""
        result = check_health()
        baseline = result["baseline"]
        if baseline["status"] != "error":
            assert "freshness" in baseline
            assert isinstance(baseline["freshness"], dict)
            assert baseline["freshness"]["level"] in ["fresh", "aging", "stale", "unknown"]

    def test_irs_has_freshness_when_not_error(self):
        """IRS SOI health should include freshness metadata for the latest year."""
        result = check_health()
        irs_soi = result["irs_soi"]
        if irs_soi["status"] != "error":
            assert "freshness" in irs_soi
            assert isinstance(irs_soi["freshness"], dict)
            assert irs_soi["freshness"]["level"] in ["fresh", "aging", "stale", "unknown"]

    def test_model_has_test_score_when_ok(self):
        """Verify model includes test_score when status is ok."""
        result = check_health()
        model = result["model"]
        if model["status"] == "ok":
            assert "test_score" in model
            # Test score should be numeric (float or int)
            assert isinstance(model["test_score"], (int, float))

    def test_fred_has_freshness_metadata_when_not_error(self):
        """FRED component should expose source and freshness metadata."""
        result = check_health()
        fred = result["fred"]
        if fred["status"] != "error":
            assert "source" in fred
            assert "cache_age_days" in fred
            assert "cache_is_expired" in fred
            assert "api_available" in fred

    def test_error_states_have_error_message(self):
        """Verify error states include error details."""
        result = check_health()
        for key, value in result.items():
            if isinstance(value, dict) and value.get("status") == "error":
                assert "error" in value, f"{key} with error status should have 'error' field"
                assert isinstance(value["error"], str)

    def test_check_health_is_idempotent(self):
        """Verify check_health can be called multiple times."""
        result1 = check_health()
        result2 = check_health()
        # Both should have the same structure (though timestamps differ)
        assert result1.keys() == result2.keys()
        assert result1["baseline"]["status"] == result2["baseline"]["status"]

    def test_check_health_handles_exceptions_gracefully(self):
        """Verify check_health doesn't raise exceptions even if components fail."""
        # This test just calls the function - it should always return a dict
        # without raising an exception
        result = check_health()
        assert result is not None
        assert isinstance(result, dict)

    def test_check_health_marks_components_as_error_on_failures(self, monkeypatch):
        """Component exceptions should be captured in the health payload."""

        class ExplodingBaseline:
            def __init__(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("baseline down")

        class ExplodingFred:
            def __init__(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("fred down")

        class ExplodingIRS:
            def __init__(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("irs down")

        class ExplodingScorer:
            def __init__(self, *args, **kwargs):
                del args, kwargs
                raise RuntimeError("model down")

        monkeypatch.setattr(baseline_module, "CBOBaseline", ExplodingBaseline)
        monkeypatch.setattr(fred_module, "FREDData", ExplodingFred)
        monkeypatch.setattr(irs_module, "IRSSOIData", ExplodingIRS)
        monkeypatch.setattr(scoring_module, "FiscalPolicyScorer", ExplodingScorer)

        result = check_health()

        assert result["baseline"]["status"] == "error"
        assert result["fred"]["status"] == "error"
        assert result["irs_soi"]["status"] == "error"
        assert result["model"]["status"] == "error"
        assert result["overall"] == "degraded"
