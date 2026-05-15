"""
Health check utilities for the Fiscal Policy Calculator.
Reports on data freshness, API availability, and model readiness.
"""

import logging
import platform
import sys
from typing import Any

from fiscal_model.data.freshness import (
    CBO_VINTAGE_PUBLICATION_DATES,
    FreshnessLevel,
    FreshnessReport,
    evaluate_cbo_baseline,
    evaluate_irs_soi,
)
from fiscal_model.time_utils import format_utc_timestamp, utc_isoformat

logger = logging.getLogger(__name__)

_SUPPORTED_PYTHON_MIN = (3, 10)
_SUPPORTED_PYTHON_MAX_EXCLUSIVE = (3, 14)
_SUPPORTED_PYTHON_RANGE = ">=3.10,<3.14"
_RECOMMENDED_PYTHON = "3.12"


def _serialize_freshness(report: FreshnessReport | None) -> dict[str, Any] | None:
    if report is None:
        return None
    return {
        "level": report.level.value,
        "age_days": report.age_days,
        "message": report.message,
        "emoji": report.emoji,
        "is_stale": report.is_stale,
    }


def _component_status_from_baseline(
    source: str | None,
    gdp_source: str | None,
    freshness: FreshnessReport | None,
) -> str:
    if source == "hardcoded_fallback" or gdp_source == "irs_ratio_proxy":
        return "degraded"
    if freshness is None or freshness.level in {
        FreshnessLevel.STALE,
        FreshnessLevel.UNKNOWN,
    }:
        return "degraded"
    return "ok"


def _component_status_from_fred(
    source: str | None,
    cache_is_expired: bool,
) -> str:
    if source == "live":
        return "ok"
    if source == "cache" and not cache_is_expired:
        return "ok"
    if source == "bundled" and not cache_is_expired:
        return "ok"
    return "degraded"


def _component_status_from_irs(freshness: FreshnessReport | None) -> str:
    if freshness is None or freshness.level in {
        FreshnessLevel.STALE,
        FreshnessLevel.UNKNOWN,
    }:
        return "degraded"
    return "ok"


def _serialize_fred_status(data_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": data_status.get("source"),
        "last_updated": format_utc_timestamp(data_status.get("last_updated")),
        "cache_age_days": data_status.get("cache_age_days"),
        "cache_is_expired": bool(data_status.get("cache_is_expired", False)),
        "source_max_age_days": data_status.get("source_max_age_days"),
        "api_available": bool(data_status.get("api_available", False)),
        "error": data_status.get("error"),
    }


def _runtime_status(version_info: tuple[int, int, int] | None = None) -> dict[str, Any]:
    """Report whether the current Python runtime matches the supported contract."""
    if version_info is None:
        raw = sys.version_info
        version_tuple = (int(raw.major), int(raw.minor), int(raw.micro))
        python_version = platform.python_version()
    else:
        version_tuple = version_info
        python_version = ".".join(str(part) for part in version_tuple)

    major_minor = version_tuple[:2]
    supported = (
        _SUPPORTED_PYTHON_MIN
        <= major_minor
        < _SUPPORTED_PYTHON_MAX_EXCLUSIVE
    )
    if supported:
        message = (
            f"Python {python_version} is within supported range "
            f"{_SUPPORTED_PYTHON_RANGE}."
        )
    else:
        message = (
            f"Python {python_version} is outside supported range "
            f"{_SUPPORTED_PYTHON_RANGE}; use {_RECOMMENDED_PYTHON} for production."
        )

    return {
        "status": "ok" if supported else "degraded",
        "python_version": python_version,
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "supported_range": _SUPPORTED_PYTHON_RANGE,
        "recommended_version": _RECOMMENDED_PYTHON,
        "message": message,
    }


def check_health() -> dict[str, Any]:
    """
    Run a comprehensive health check on all data sources and models.

    Returns a dict with status for each component:
    - baseline: status of CBO baseline data
    - fred: status of FRED API connection
    - irs_soi: status of IRS SOI data files
    - model: status of scoring engine
    """
    results = {}

    # Runtime contract. This is intentionally first and cheap: it catches
    # deployments that boot on an unsupported Python even if every model
    # component happens to import successfully.
    results["runtime"] = _runtime_status()

    # Check baseline
    try:
        from fiscal_model.baseline import CBOBaseline
        b = CBOBaseline(use_real_data=True)
        _proj = b.generate()
        baseline_metadata = b.metadata
        vintage_key = baseline_metadata.get("vintage")
        freshness_report = evaluate_cbo_baseline(
            CBO_VINTAGE_PUBLICATION_DATES.get(vintage_key)
        )
        status = _component_status_from_baseline(
            baseline_metadata.get("source"),
            baseline_metadata.get("gdp_source"),
            freshness_report,
        )
        results["baseline"] = {
            "status": status,
            "vintage": baseline_metadata.get("vintage_date")
            or (b.baseline_vintage_date if hasattr(b, "baseline_vintage_date") else "unknown"),
            "vintage_key": vintage_key,
            "publication_date": format_utc_timestamp(
                CBO_VINTAGE_PUBLICATION_DATES.get(vintage_key)
            ),
            "start_year": b.start_year,
            "source": baseline_metadata.get("source"),
            "requested_real_data": bool(baseline_metadata.get("requested_real_data")),
            "load_error": baseline_metadata.get("load_error"),
            "irs_data_year": baseline_metadata.get("irs_data_year"),
            "gdp_source": baseline_metadata.get("gdp_source"),
            "fred": _serialize_fred_status(baseline_metadata.get("fred", {})),
            "freshness": _serialize_freshness(freshness_report),
        }
    except Exception as e:
        results["baseline"] = {"status": "error", "error": str(e)}

    # Check FRED
    try:
        from fiscal_model.data.fred_data import FREDData
        fred = FREDData()
        _gdp = fred.get_gdp(nominal=True)
        fred_status = _serialize_fred_status(
            fred.data_status if hasattr(fred, "data_status") else {}
        )
        results["fred"] = {
            "status": _component_status_from_fred(
                fred_status.get("source"),
                bool(fred_status.get("cache_is_expired", False)),
            ),
            **fred_status,
        }
    except Exception as e:
        results["fred"] = {"status": "error", "error": str(e)}

    # Check IRS SOI
    try:
        from fiscal_model.data.irs_soi import IRSSOIData
        irs = IRSSOIData()
        available_years = irs.get_data_years_available()
        latest_year = max(available_years) if available_years else None
        freshness_report = evaluate_irs_soi(latest_year)
        results["irs_soi"] = {
            "status": _component_status_from_irs(freshness_report),
            "available_years": available_years,
            "latest_year": latest_year,
            "update_cadence": "Annual release with multi-year lag",
            "freshness": _serialize_freshness(freshness_report),
        }
    except Exception as e:
        results["irs_soi"] = {"status": "error", "error": str(e)}

    # Check scorer
    try:
        from fiscal_model.policies import PolicyType, TaxPolicy
        from fiscal_model.scoring import FiscalPolicyScorer
        scorer = FiscalPolicyScorer(use_real_data=True)
        test_policy = TaxPolicy(
            name="health_check",
            description="Health check test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=400000,
        )
        result = scorer.score_policy(test_policy)
        results["model"] = {
            "status": "ok",
            "test_score": round(result.final_deficit_effect[0], 1),
            "use_real_data": True,
        }
    except Exception as e:
        results["model"] = {"status": "error", "error": str(e)}

    # Check microdata (CPS-derived tax units) + SOI calibration summary.
    # Kept lightweight so /health stays fast: only the two top-level
    # coverage ratios are reported here; the full bracket report lives
    # in calibrate_to_soi for callers that want it.
    try:
        from fiscal_model.data.cps_asec import describe_microdata, load_tax_microdata
        from fiscal_model.microsim.soi_calibration import calibrate_to_soi

        descriptor = describe_microdata()
        microdata_entry: dict[str, Any] = {"status": "unknown", **descriptor}

        if descriptor.get("status") in {"synthetic", "real"}:
            df, _ = load_tax_microdata()
            calibration_year = (
                results.get("irs_soi", {}).get("latest_year") or 2022
            )
            report = calibrate_to_soi(df, year=int(calibration_year))
            summary = report.summary()
            returns_coverage = summary.get("returns_coverage_pct", 0.0)
            agi_coverage = summary.get("agi_coverage_pct", 0.0)

            # Coverage bands chosen to surface the real-tail undercount
            # documented in docs/VALIDATION_NOTES.md: a microdata file
            # whose top-bracket AGI is <70% of SOI's will produce
            # distributional output that should not be taken literally.
            if agi_coverage < 70 or returns_coverage < 70 or descriptor.get("status") == "synthetic":
                calibration_status = "degraded"
            else:
                calibration_status = "ok"

            microdata_entry.update(
                {
                    "status": calibration_status,
                    "calibration_year": int(calibration_year),
                    "returns_coverage_pct": round(returns_coverage, 1),
                    "agi_coverage_pct": round(agi_coverage, 1),
                }
            )
        results["microdata"] = microdata_entry
    except Exception as e:
        results["microdata"] = {"status": "error", "error": str(e)}

    # Ask assistant — three sub-checks, all soft (assistant is optional)
    results["assistant"] = _check_assistant()

    results["timestamp"] = utc_isoformat()
    # The Ask assistant is an *optional* component — a missing API key on a
    # CI runner or local dev box must not drag the overall status. The
    # readiness layer carries it as required=False; reflect the same here.
    _required_components = {
        "runtime",
        "model",
        "baseline",
        "fred",
        "irs_soi",
        "microdata",
    }
    results["overall"] = (
        "ok"
        if all(
            r.get("status") == "ok"
            for k, r in results.items()
            if k in _required_components and isinstance(r, dict) and "status" in r
        )
        else "degraded"
    )

    return results


def _check_assistant() -> dict[str, Any]:
    """Health of the Ask assistant stack.

    Soft checks — none of these fail the overall app:
    - API key present (env var or st.secrets-promoted)
    - Knowledge corpus directory exists and is non-empty
    - Usage sqlite db is writable

    Returns ``status: "ok"`` when all three pass, ``"degraded"`` when any
    one fails, and ``"error"`` only on unexpected exceptions.
    """
    import os
    from pathlib import Path

    try:
        api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))

        knowledge_dir = (
            Path(__file__).resolve().parent / "assistant" / "knowledge"
        )
        knowledge_count = (
            sum(1 for _ in knowledge_dir.glob("*.md")) if knowledge_dir.exists() else 0
        )

        # Verify the usage db can be initialized (creates schema, writes nothing).
        usage_db_ok = False
        usage_db_path: str | None = None
        try:
            from fiscal_model.assistant.rate_limit import RateLimiter

            rl = RateLimiter()
            usage_db_path = rl.db_path
            # Touch a read to confirm schema is queryable.
            rl.today_spend_usd()
            usage_db_ok = True
        except Exception as exc:  # noqa: BLE001
            logger.info("Assistant usage db check failed: %s", exc)
            usage_db_ok = False

        status = (
            "ok"
            if api_key_set and knowledge_count > 0 and usage_db_ok
            else "degraded"
        )
        return {
            "status": status,
            "api_key_configured": api_key_set,
            "knowledge_corpus_files": knowledge_count,
            "usage_db_writable": usage_db_ok,
            "usage_db_path": usage_db_path,
            "note": (
                "Soft component — degradation here doesn't prevent the rest "
                "of the app from working. To configure, set "
                "ANTHROPIC_API_KEY (env var or Streamlit secret)."
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)}
