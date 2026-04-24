"""
Fiscal Policy Calculator — REST API

Programmatic access to CBO-style fiscal policy scoring.

Run with:
    uvicorn api:app --reload

Docs at:
    http://localhost:8000/docs

Note: endpoints are defined as sync ``def`` — not ``async def`` — because
the scoring pipeline (baseline load, FRED retry/backoff, microsim) is
entirely synchronous and may block for seconds. FastAPI automatically
runs sync endpoints in a threadpool worker, which keeps the event loop
free for other requests without forcing the rest of the model to be
rewritten as async. See
https://fastapi.tiangolo.com/async/#path-operation-functions
"""

import logging
import math
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from fiscal_model.api_security import (
    is_auth_enabled,
    require_api_key,
    security_middleware,
)
from fiscal_model.api_serialization import serialize_scoring_result
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.exceptions import (
    FiscalModelError,
    PolicyValidationError,
    ScoringBoundsError,
)
from fiscal_model.health import check_health
from fiscal_model.policies import (
    PolicyType,
    TaxPolicy,
)
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.trade import TariffPolicy

logger = logging.getLogger(__name__)

# Plausible annual revenue / deficit impact, in $B. The entire federal budget
# is ~$7T, so any single-year policy effect outside ±$10T is almost certainly
# numerical overflow or a malformed policy, not a real scoring result.
_MAX_ANNUAL_EFFECT_BILLIONS = 10_000.0


def _validate_serialized_result(
    payload: dict[str, Any],
    *,
    policy_name: str,
) -> None:
    """Sanity-check a serialized scoring result before returning it to API
    clients.

    Raises :class:`ScoringBoundsError` if any numeric field is non-finite or
    outside plausible bounds. This catches pathological inputs (extreme
    elasticities, bad baselines) before they become confusing client errors.
    """
    scalar_keys = (
        "ten_year_deficit_impact",
        "static_revenue_effect",
        "behavioral_offset",
        "final_static_effect",
        "gdp_effect",
        "employment_effect",
        "revenue_feedback",
        "dynamic_adjusted_impact",
    )
    for key in scalar_keys:
        value = payload.get(key)
        if value is None:
            continue
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ScoringBoundsError(
                f"Policy '{policy_name}': non-finite {key}={value!r}"
            )

    raw_ten_year = payload.get("ten_year_deficit_impact") or 0.0
    if not isinstance(raw_ten_year, (int, float)):
        raise ScoringBoundsError(
            f"Policy '{policy_name}': non-numeric ten_year_deficit_impact="
            f"{raw_ten_year!r}"
        )
    ten_year = float(raw_ten_year)
    if abs(ten_year) > _MAX_ANNUAL_EFFECT_BILLIONS * 10:
        raise ScoringBoundsError(
            f"Policy '{policy_name}': ten_year_deficit_impact ${ten_year:.1f}B "
            f"exceeds plausible bounds (±${_MAX_ANNUAL_EFFECT_BILLIONS * 10:.0f}B). "
            "Check policy parameters."
        )

    for entry in payload.get("year_by_year") or []:
        for field_name in ("revenue_effect", "behavioral_offset", "dynamic_feedback", "final_effect"):
            value = entry.get(field_name)
            if value is None:
                continue
            # Guard against non-numeric values before calling float(): a
            # serialization regression that slipped a string into the
            # payload would otherwise surface as a ValueError and bypass
            # the structured error contract.
            if not isinstance(value, (int, float)):
                raise ScoringBoundsError(
                    f"Policy '{policy_name}': non-numeric {field_name}="
                    f"{value!r} in year {entry.get('year')}"
                )
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ScoringBoundsError(
                    f"Policy '{policy_name}': non-finite {field_name} in "
                    f"year {entry.get('year')}"
                )
            if abs(numeric) > _MAX_ANNUAL_EFFECT_BILLIONS:
                raise ScoringBoundsError(
                    f"Policy '{policy_name}': {field_name}=${numeric:.1f}B in "
                    f"year {entry.get('year')} exceeds plausible annual bound "
                    f"±${_MAX_ANNUAL_EFFECT_BILLIONS:.0f}B"
                )

app = FastAPI(
    title="Fiscal Policy Calculator API",
    description="Programmatic access to CBO-style fiscal policy scoring with dynamic effects",
    version="1.0.0",
)

# Cross-cutting concerns — rate limiting and structured request logging.
# Authentication is enforced per-endpoint via ``Depends(require_api_key)``
# so that OpenAPI docs render the security scheme and discovery endpoints
# (/, /health, /docs) stay open.
app.middleware("http")(security_middleware)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ScorePolicyRequest(BaseModel):
    """Request to score a custom tax policy."""

    name: str = Field("Custom Policy", description="Policy name")
    description: str = Field("User-defined policy", description="Policy description")
    rate_change: float = Field(
        ..., ge=-1.0, le=1.0, description="Rate change in percentage points"
    )
    income_threshold: float = Field(
        0, ge=0, description="Income threshold for affected taxpayers"
    )
    elasticity: float = Field(
        0.25, ge=0, le=2.0, description="Taxable income elasticity"
    )
    duration_years: int = Field(10, ge=1, le=30, description="Policy duration")
    dynamic: bool = Field(False, description="Enable dynamic scoring")
    policy_type: str = Field("income_tax", description="Type of tax policy")


class YearlyEffect(BaseModel):
    """Year-by-year revenue effect."""

    year: int
    revenue_effect: float  # Billions
    behavioral_offset: float  # Billions
    dynamic_feedback: float  # Billions
    final_effect: float  # Billions


class ScorePolicyResponse(BaseModel):
    """Response from scoring a policy."""

    policy_name: str
    policy_description: str
    baseline_vintage: str
    budget_window: str

    # Static and behavioral effects
    ten_year_deficit_impact: float  # Billions
    static_revenue_effect: float  # Billions
    behavioral_offset: float  # Billions
    final_static_effect: float  # Billions

    # Dynamic effects (if enabled)
    gdp_effect: float | None = None  # Percentage points (cumulative)
    employment_effect: float | None = None  # Thousands of jobs
    revenue_feedback: float | None = None  # Billions
    dynamic_adjusted_impact: float | None = None  # Billions

    # Year-by-year breakdown
    year_by_year: list[YearlyEffect]

    # Metadata
    dynamic_scoring_enabled: bool
    error_message: str | None = None


class ScorePresetRequest(BaseModel):
    """Request to score a named preset policy."""

    preset_name: str = Field(..., description="Exact name from /presets endpoint")
    dynamic: bool = Field(False, description="Enable dynamic scoring")


class PresetPolicyInfo(BaseModel):
    """Information about a preset policy."""

    name: str
    description: str
    cbo_score: float | None = None  # Billions (if available)
    cbo_source: str | None = None
    cbo_date: str | None = None


class PresetsResponse(BaseModel):
    """Response listing available presets."""

    presets: list[PresetPolicyInfo]
    count: int


class ScoreTariffRequest(BaseModel):
    """Request to score a tariff policy."""

    name: str = Field("Custom Tariff", description="Tariff name")
    tariff_rate: float = Field(..., ge=0, le=1.0, description="Tariff rate (0-1)")
    import_base_billions: float = Field(
        3200.0, gt=0, description="Import base (billions)"
    )
    target_country: str | None = Field(None, description="Target country code")
    include_consumer_cost: bool = Field(True, description="Include consumer impact")
    include_retaliation: bool = Field(
        True, description="Include retaliation effects"
    )


class TradeSummary(BaseModel):
    """Trade policy impacts."""

    gross_revenue: float  # Billions
    consumer_cost: float  # Billions
    retaliation_cost: float  # Billions
    net_deficit_impact: float  # Billions


class ScoreTariffResponse(BaseModel):
    """Response from scoring a tariff policy."""

    policy_name: str
    ten_year_deficit_impact: float  # Billions
    trade_summary: TradeSummary
    uncertainty_range: dict[str, float] | None = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    overall: str
    timestamp: str
    components: dict[str, Any]


class BenchmarkResult(BaseModel):
    """One CBO/JCT distributional benchmark comparison."""

    policy_id: str
    policy_name: str
    source: str
    source_document: str
    analysis_year: int
    rating: str  # excellent | good | acceptable | needs_improvement | no_overlap
    mean_absolute_share_error_pp: float | None
    matched_rows: int
    benchmark_rows: int


class BenchmarksResponse(BaseModel):
    """Response listing current model accuracy against every benchmark."""

    benchmarks: list[BenchmarkResult]
    count: int
    overall_rating: str  # ok | degraded


class SummaryResponse(BaseModel):
    """One-call overview: health, benchmarks, and microdata coverage."""

    overall: str  # ok | degraded
    timestamp: str
    health: dict[str, Any]
    benchmarks: list[BenchmarkResult]
    benchmarks_rating: str  # ok | degraded
    microdata_coverage: dict[str, Any]
    auth_required: bool


SUPPORTED_CUSTOM_POLICY_TYPES = {
    PolicyType.INCOME_TAX,
    PolicyType.CORPORATE_TAX,
    PolicyType.PAYROLL_TAX,
}


def _resolve_custom_policy_type(raw_policy_type: str) -> PolicyType:
    """Resolve and validate the generic custom-policy API policy type."""
    try:
        policy_type = PolicyType(raw_policy_type)
    except ValueError as exc:
        supported = ", ".join(sorted(policy.value for policy in SUPPORTED_CUSTOM_POLICY_TYPES))
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported policy_type '{raw_policy_type}'. "
                f"Supported values: {supported}."
            ),
        ) from exc

    if policy_type not in SUPPORTED_CUSTOM_POLICY_TYPES:
        supported = ", ".join(sorted(policy.value for policy in SUPPORTED_CUSTOM_POLICY_TYPES))
        raise HTTPException(
            status_code=400,
            detail=(
                f"policy_type '{raw_policy_type}' is not supported by /score. "
                f"Supported values: {supported}."
            ),
        )
    return policy_type


def _build_preset_policy(preset_name: str) -> tuple[Any, bool]:
    """
    Build a preset policy using the same routing path as the Streamlit UI.

    Returns:
        Tuple of (policy, use_real_data_for_scorer).
    """
    preset = PRESET_POLICIES[preset_name]
    policy = create_policy_from_preset(preset)
    if policy is not None:
        return policy, False

    raw_rate_change = float(preset.get("rate_change", 0.0))
    policy = TaxPolicy(
        name=preset_name,
        description=preset.get("description", ""),
        policy_type=PolicyType.INCOME_TAX,
        rate_change=raw_rate_change / 100.0 if abs(raw_rate_change) > 1 else raw_rate_change,
        affected_income_threshold=float(preset.get("threshold", 0.0)),
        taxable_income_elasticity=0.25,
        duration_years=10,
    )
    return policy, True


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health", response_model=HealthCheckResponse)
def health_check():
    """
    Health check endpoint.

    Returns status of all data sources and models.
    """
    health_data = check_health()
    return HealthCheckResponse(
        overall=health_data.get("overall", "unknown"),
        timestamp=health_data.get("timestamp", ""),
        components={
            k: v
            for k, v in health_data.items()
            if k not in ("overall", "timestamp")
        },
    )


@app.get("/summary", response_model=SummaryResponse)
def summary():
    """
    One-call overview combining /health, /benchmarks, and microdata
    coverage. Suitable for status dashboards and CI gates that need a
    single source of truth.
    """
    from fiscal_model.validation.benchmark_runners import default_model_runner
    from fiscal_model.validation.cbo_distributions import (
        CBO_JCT_BENCHMARKS,
        compare_distribution,
    )

    health_data = check_health()
    overall_health = health_data.get("overall", "unknown")
    microdata = health_data.get("microdata", {})

    benchmark_results: list[BenchmarkResult] = []
    benchmarks_worst = "ok"
    for benchmark in CBO_JCT_BENCHMARKS:
        model_result = default_model_runner(benchmark)
        if model_result is None:
            continue
        comparison = compare_distribution(model_result, benchmark)
        if comparison.overall_rating == "needs_improvement":
            benchmarks_worst = "degraded"
        benchmark_results.append(
            BenchmarkResult(
                policy_id=benchmark.policy_id,
                policy_name=benchmark.policy_name,
                source=benchmark.source.value,
                source_document=benchmark.source_document,
                analysis_year=benchmark.analysis_year,
                rating=comparison.overall_rating,
                mean_absolute_share_error_pp=comparison.mean_absolute_share_error_pp,
                matched_rows=len(comparison.per_group),
                benchmark_rows=len(benchmark.rows),
            )
        )

    # Overall degrades if either health or benchmarks degrade.
    overall = "degraded" if (overall_health != "ok" or benchmarks_worst == "degraded") else "ok"

    return SummaryResponse(
        overall=overall,
        timestamp=health_data.get("timestamp", ""),
        health={
            k: v for k, v in health_data.items()
            if k not in ("overall", "timestamp")
        },
        benchmarks=benchmark_results,
        benchmarks_rating=benchmarks_worst,
        microdata_coverage={
            "returns_coverage_pct": microdata.get("returns_coverage_pct"),
            "agi_coverage_pct": microdata.get("agi_coverage_pct"),
            "calibration_year": microdata.get("calibration_year"),
        },
        auth_required=is_auth_enabled(),
    )


@app.get("/benchmarks", response_model=BenchmarksResponse)
def list_benchmarks():
    """
    List current model accuracy against every CBO/JCT distributional benchmark.

    Each benchmark reports the mean-absolute-share error between the
    DistributionalEngine's output and the published official tables.
    ``overall_rating`` degrades when any benchmark is flagged
    ``needs_improvement`` (≥10pp mean error).

    See ``docs/VALIDATION_NOTES.md`` for root-cause analysis of current
    outliers.
    """
    from fiscal_model.validation.benchmark_runners import default_model_runner
    from fiscal_model.validation.cbo_distributions import (
        CBO_JCT_BENCHMARKS,
        compare_distribution,
    )

    results: list[BenchmarkResult] = []
    worst = "ok"
    for benchmark in CBO_JCT_BENCHMARKS:
        model_result = default_model_runner(benchmark)
        if model_result is None:
            continue
        comparison = compare_distribution(model_result, benchmark)
        if comparison.overall_rating == "needs_improvement":
            worst = "degraded"
        results.append(
            BenchmarkResult(
                policy_id=benchmark.policy_id,
                policy_name=benchmark.policy_name,
                source=benchmark.source.value,
                source_document=benchmark.source_document,
                analysis_year=benchmark.analysis_year,
                rating=comparison.overall_rating,
                mean_absolute_share_error_pp=comparison.mean_absolute_share_error_pp,
                matched_rows=len(comparison.per_group),
                benchmark_rows=len(benchmark.rows),
            )
        )

    return BenchmarksResponse(
        benchmarks=results,
        count=len(results),
        overall_rating=worst,
    )


@app.get("/presets", response_model=PresetsResponse)
def list_presets():
    """
    List all available preset policies with CBO scores.

    Returns all preset policies including descriptions and official CBO estimates
    where available.
    """
    presets = []

    for preset_name, preset_data in PRESET_POLICIES.items():
        # Look up CBO score if available
        cbo_info = CBO_SCORE_MAP.get(preset_name, {})

        preset_info = PresetPolicyInfo(
            name=preset_name,
            description=preset_data.get("description", ""),
            cbo_score=cbo_info.get("official_score"),
            cbo_source=cbo_info.get("source"),
            cbo_date=cbo_info.get("source_date"),
        )
        presets.append(preset_info)

    return PresetsResponse(presets=presets, count=len(presets))


@app.post("/score", response_model=ScorePolicyResponse)
def score_policy(
    request: ScorePolicyRequest,
    _api_key_label: str = Depends(require_api_key),
):
    """
    Score a custom tax policy.

    Scores static and behavioral effects of a user-defined tax policy,
    with optional dynamic feedback.
    """
    try:
        # Validate inputs
        if request.duration_years < 1:
            raise PolicyValidationError("duration_years must be at least 1")
        policy_type = _resolve_custom_policy_type(request.policy_type)

        # Create policy
        policy = TaxPolicy(
            name=request.name,
            description=request.description,
            policy_type=policy_type,
            rate_change=request.rate_change,
            affected_income_threshold=request.income_threshold,
            taxable_income_elasticity=request.elasticity,
            duration_years=request.duration_years,
        )

        # Score policy
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=request.dynamic)

        payload = serialize_scoring_result(
            result,
            policy_name=request.name,
            policy_description=request.description,
            dynamic_scoring_enabled=request.dynamic,
        )
        _validate_serialized_result(payload, policy_name=request.name)
        return ScorePolicyResponse(**payload)

    except HTTPException:
        raise
    except PolicyValidationError as e:
        # Caller-induced validation problem — return 400 so clients can fix.
        logger.info("Policy '%s' validation error: %s", request.name, e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FiscalModelError as e:
        # Internal model error with enough context to be a 422 (unprocessable).
        logger.warning("Policy '%s' scoring error: %s", request.name, e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except ValueError as e:
        # Policy constructors (TaxPolicy.__post_init__ and friends) raise
        # plain ValueError for out-of-range or inconsistent inputs. Treat
        # these as client errors so the caller sees a 400 with the exact
        # reason rather than a generic 200 with error_message.
        logger.info("Policy '%s' invalid input: %s", request.name, e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # Unknown failure — log with traceback and surface a real 500 so
        # clients don't mistake a failed score for a successful zero-impact
        # result.
        logger.exception("Unexpected error scoring policy '%s'", request.name)
        raise HTTPException(status_code=500, detail="Internal scoring error") from e


@app.post("/score/preset", response_model=ScorePolicyResponse)
def score_preset(
    request: ScorePresetRequest,
    _api_key_label: str = Depends(require_api_key),
):
    """
    Score a named preset policy.

    Scores a policy from the preset library, with optional dynamic feedback.
    """
    try:
        # Look up preset
        if request.preset_name not in PRESET_POLICIES:
            raise ValueError(
                f"Unknown preset: {request.preset_name}. "
                f"Use /presets to see available presets."
            )

        preset = PRESET_POLICIES[request.preset_name]
        policy, use_real_data = _build_preset_policy(request.preset_name)

        scorer = FiscalPolicyScorer(
            start_year=getattr(policy, "start_year", 2025),
            use_real_data=use_real_data,
        )
        result = scorer.score_policy(policy, dynamic=request.dynamic)

        payload = serialize_scoring_result(
            result,
            policy_name=request.preset_name,
            policy_description=preset.get("description", ""),
            dynamic_scoring_enabled=request.dynamic,
        )
        _validate_serialized_result(payload, policy_name=request.preset_name)
        return ScorePolicyResponse(**payload)

    except PolicyValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FiscalModelError as e:
        logger.warning("Preset '%s' scoring error: %s", request.preset_name, e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error scoring preset '%s'", request.preset_name)
        raise HTTPException(status_code=500, detail="Internal scoring error") from e


@app.post("/score/tariff", response_model=ScoreTariffResponse)
def score_tariff(
    request: ScoreTariffRequest,
    _api_key_label: str = Depends(require_api_key),
):
    """
    Score a tariff policy with consumer impact.

    Estimates revenue, consumer costs, and retaliation effects of tariffs.
    """
    try:
        policy = TariffPolicy(
            name=request.name,
            description=f"{request.tariff_rate:.0%} tariff policy",
            tariff_rate_change=request.tariff_rate,
            target_country=request.target_country,
            import_base_billions=request.import_base_billions,
            include_consumer_cost=request.include_consumer_cost,
            include_retaliation=request.include_retaliation,
        )
        scorer = FiscalPolicyScorer(
            start_year=getattr(policy, "start_year", 2025),
            use_real_data=False,
        )
        result = scorer.score_policy(policy, dynamic=False)
        annual_summary = policy.get_trade_summary()
        duration_years = getattr(policy, "duration_years", 10)
        gross_revenue = annual_summary["tariff_revenue"] * duration_years
        consumer_cost = (
            annual_summary["consumer_cost"] * duration_years
            if request.include_consumer_cost
            else 0.0
        )
        retaliation_cost = (
            annual_summary["retaliation_cost"] * duration_years
            if request.include_retaliation
            else 0.0
        )
        net_impact = float(np.sum(result.final_deficit_effect))

        trade_summary = TradeSummary(
            gross_revenue=gross_revenue,
            consumer_cost=consumer_cost,
            retaliation_cost=retaliation_cost,
            net_deficit_impact=net_impact,
        )

        return ScoreTariffResponse(
            policy_name=request.name,
            ten_year_deficit_impact=net_impact,
            trade_summary=trade_summary,
            uncertainty_range={
                "low": float(np.sum(result.low_estimate)),
                "central": net_impact,
                "high": float(np.sum(result.high_estimate)),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# =============================================================================
# ROOT ENDPOINT
# =============================================================================


@app.get("/")
def root():
    """
    API root endpoint.

    Provides information about available endpoints.
    """
    return {
        "service": "Fiscal Policy Calculator API",
        "version": "1.0.0",
        "auth_required": is_auth_enabled(),
        "auth_header": "X-API-Key",
        "endpoints": {
            "health": "GET /health",
            "benchmarks": "GET /benchmarks",
            "summary": "GET /summary",
            "presets": "GET /presets",
            "score_custom": "POST /score",
            "score_preset": "POST /score/preset",
            "score_tariff": "POST /score/tariff",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json",
        },
        "docs_url": "http://localhost:8000/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
