"""
Health check utilities for the Fiscal Policy Calculator.
Reports on data freshness, API availability, and model readiness.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


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

    # Check baseline
    try:
        from fiscal_model.baseline import CBOBaseline
        b = CBOBaseline(use_real_data=False)
        _proj = b.generate()
        results["baseline"] = {
            "status": "ok",
            "vintage": b.baseline_vintage_date if hasattr(b, 'baseline_vintage_date') else "unknown",
            "start_year": b.start_year,
        }
    except Exception as e:
        results["baseline"] = {"status": "error", "error": str(e)}

    # Check FRED
    try:
        from fiscal_model.data.fred_data import FREDData
        fred = FREDData()
        results["fred"] = {
            "status": "ok" if fred.is_available() else "unavailable",
            "data_status": fred.data_status if hasattr(fred, 'data_status') else {},
        }
    except Exception as e:
        results["fred"] = {"status": "error", "error": str(e)}

    # Check IRS SOI
    try:
        from fiscal_model.data.irs_soi import IRSSOIData
        irs = IRSSOIData()
        results["irs_soi"] = {
            "status": "ok",
            "available_years": sorted(irs.available_years) if hasattr(irs, 'available_years') else [],
        }
    except Exception as e:
        results["irs_soi"] = {"status": "error", "error": str(e)}

    # Check scorer
    try:
        from fiscal_model.policies import PolicyType, TaxPolicy
        from fiscal_model.scoring import FiscalPolicyScorer
        scorer = FiscalPolicyScorer(use_real_data=False)
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
        }
    except Exception as e:
        results["model"] = {"status": "error", "error": str(e)}

    results["timestamp"] = datetime.now().isoformat()
    results["overall"] = "ok" if all(
        r.get("status") == "ok" for k, r in results.items()
        if isinstance(r, dict) and "status" in r
    ) else "degraded"

    return results
