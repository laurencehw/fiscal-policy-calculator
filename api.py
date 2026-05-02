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
from fiscal_model.readiness import build_readiness_report
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


class ResultCredibilityModel(BaseModel):
    """Validation and uncertainty context attached to one score."""

    category: str
    evidence_type: str
    n_benchmarks: int
    mean_abs_pct_error: float
    median_abs_pct_error: float
    within_15pct: int
    rating_label: str
    is_calibrated: bool
    holdout_status: str
    uncertainty_low: float | None = None
    uncertainty_high: float | None = None
    limitations: list[str] = Field(default_factory=list)
    caption: str


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
    credibility: ResultCredibilityModel | None = None
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


class HealthIssueModel(BaseModel):
    """Flattened health issue for monitoring clients."""

    surface: str
    severity: str  # warn | fail
    name: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class HealthCheckResponse(BaseModel):
    """Health check response."""

    overall: str
    timestamp: str
    components: dict[str, Any]
    issues: list[HealthIssueModel] = Field(default_factory=list)


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


class SummaryIssueModel(BaseModel):
    """Flattened status issue for the summary endpoint."""

    surface: str
    severity: str  # warn | fail
    name: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SummaryResponse(BaseModel):
    """One-call overview: health, benchmarks, and microdata coverage."""

    overall: str  # ok | degraded
    timestamp: str
    health: dict[str, Any]
    benchmarks: list[BenchmarkResult]
    benchmarks_rating: str  # ok | degraded
    microdata_coverage: dict[str, Any]
    auth_required: bool
    issues: list[SummaryIssueModel] = Field(default_factory=list)


class ReadinessCheckModel(BaseModel):
    """One release-readiness criterion."""

    name: str
    status: str  # pass | warn | fail
    required: bool
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ReadinessIssueModel(BaseModel):
    """Flattened release-readiness blocker or warning."""

    name: str
    severity: str  # warn | fail
    required: bool
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    """Aggregate release-readiness verdict."""

    verdict: str  # ready | ready_with_warnings | not_ready
    generated_at: str
    pass_count: int
    warn_count: int
    fail_count: int
    checks: list[ReadinessCheckModel]
    issues: list[ReadinessIssueModel] = Field(default_factory=list)


class ScorecardEntryModel(BaseModel):
    """Single policy's revenue-level model-vs-official comparison."""

    category: str
    policy_id: str
    policy_name: str
    official_10yr_billions: float
    official_source: str
    benchmark_kind: str
    benchmark_date: str | None = None
    benchmark_url: str | None = None
    model_10yr_billions: float
    difference_billions: float
    percent_difference: float
    abs_percent_difference: float
    rating: str  # Excellent | Good | Acceptable | Poor | Error
    direction_match: bool
    known_limitations: list[str] = Field(default_factory=list)
    notes: str = ""
    evidence_type: str = "specialized_benchmark_comparison"
    holdout_status: str = "calibration_reference"


class ScorecardCategorySummary(BaseModel):
    """Per-category roll-up of scorecard accuracy."""

    n: int
    mean_abs_percent_difference: float
    within_15pct: int
    ratings: dict[str, int] = Field(default_factory=dict)


class ScorecardResponse(BaseModel):
    """Consolidated revenue-level validation scorecard."""

    total_entries: int
    within_5pct: int
    within_10pct: int
    within_15pct: int
    within_20pct: int
    direction_match: int
    poor: int
    mean_abs_percent_difference: float
    median_abs_percent_difference: float
    calibrated_entries: int
    generic_entries: int
    holdout_entries: int
    validation_note: str
    ratings_breakdown: dict[str, int]
    by_category: dict[str, ScorecardCategorySummary]
    entries: list[ScorecardEntryModel]


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


def _summary_health_issue_message(component: str, info: dict[str, Any]) -> str:
    if info.get("message"):
        return str(info["message"])
    if info.get("error"):
        return str(info["error"])
    if info.get("load_error"):
        return str(info["load_error"])
    return f"{component} health status is {info.get('status', 'unknown')}."


def _health_issue_payloads(health_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten non-ok health components into serializable issue payloads."""
    issues: list[dict[str, Any]] = []
    for component, info in health_data.items():
        if component in {"overall", "timestamp"} or not isinstance(info, dict):
            continue
        status = info.get("status")
        if status in {None, "ok"}:
            continue
        severity = (
            "fail"
            if status == "error" or component in {"runtime", "model"}
            else "warn"
        )
        issues.append(
            {
                "surface": "health",
                "severity": severity,
                "name": component,
                "message": _summary_health_issue_message(component, info),
                "details": info,
            }
        )
    return issues


def _health_issues(health_data: dict[str, Any]) -> list[HealthIssueModel]:
    """Return /health issue models for degraded components."""
    return [HealthIssueModel(**issue) for issue in _health_issue_payloads(health_data)]


def _summary_health_issues(health_data: dict[str, Any]) -> list[SummaryIssueModel]:
    """Flatten non-ok health components for /summary consumers."""
    return [SummaryIssueModel(**issue) for issue in _health_issue_payloads(health_data)]


def _summary_benchmark_issues(
    benchmark_results: list[BenchmarkResult],
) -> list[SummaryIssueModel]:
    """Flatten failing distributional benchmarks for /summary consumers."""
    return [
        SummaryIssueModel(
            surface="distributional_benchmarks",
            severity="fail",
            name=benchmark.policy_id,
            message=(
                "Distributional benchmark needs improvement: "
                f"{benchmark.policy_name}."
            ),
            details={
                "policy_id": benchmark.policy_id,
                "rating": benchmark.rating,
                "mean_absolute_share_error_pp": benchmark.mean_absolute_share_error_pp,
                "matched_rows": benchmark.matched_rows,
                "benchmark_rows": benchmark.benchmark_rows,
            },
        )
        for benchmark in benchmark_results
        if benchmark.rating == "needs_improvement"
    ]


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
    components = {
        k: v
        for k, v in health_data.items()
        if k not in ("overall", "timestamp")
    }
    return HealthCheckResponse(
        overall=health_data.get("overall", "unknown"),
        timestamp=health_data.get("timestamp", ""),
        components=components,
        issues=_health_issues(health_data),
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
    issues = [
        *_summary_health_issues(health_data),
        *_summary_benchmark_issues(benchmark_results),
    ]

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
        issues=issues,
    )


@app.get("/readiness", response_model=ReadinessResponse)
def readiness():
    """
    Machine-readable release-readiness gate.

    Combines runtime support, health checks, distributional benchmarks,
    and revenue scorecard status into one verdict:
    ``ready``, ``ready_with_warnings``, or ``not_ready``.
    """
    report = build_readiness_report()
    return ReadinessResponse(
        verdict=report.verdict,
        generated_at=report.generated_at,
        pass_count=report.pass_count,
        warn_count=report.warn_count,
        fail_count=report.fail_count,
        checks=[
            ReadinessCheckModel(
                name=check.name,
                status=check.status,
                required=check.required,
                summary=check.summary,
                details=check.details,
            )
            for check in report.checks
        ],
        issues=[
            ReadinessIssueModel(
                name=issue.name,
                severity=issue.severity,
                required=issue.required,
                summary=issue.summary,
                details=issue.details,
            )
            for issue in report.issues
        ],
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


@app.get("/validation/scorecard", response_model=ScorecardResponse)
def validation_scorecard():
    """
    Consolidated revenue-level scorecard: every published CBO/JCT/Treasury
    score the model is calibrated against, plus what the model produces today.

    Each entry reports the official 10-year score, the model's score, the
    signed % difference, and a rating (Excellent ≤5%, Good ≤10%, Acceptable
    ≤20%, Poor >20%). Generic-category entries use raw rate/threshold
    auto-population — drift there is expected and reflects the limits of
    parameter-only scoring rather than a calibration regression.

    Use the per-category breakdown to see where the calibrated specialized
    paths stand vs. where the naive generic path lands.
    """
    from fiscal_model.validation.holdout import (
        DEFAULT_HOLDOUT_PROTOCOL,
        evidence_type_for_entry,
        holdout_entries,
        holdout_status_for_entry,
    )
    from fiscal_model.validation.scorecard import cached_default_scorecard

    # Cached for the process lifetime — the underlying validation data
    # is code-resident, so recomputing on every request would only burn
    # CPU and amplify DoS attempts.
    summary = cached_default_scorecard()
    holdouts = holdout_entries(summary.entries)

    return ScorecardResponse(
        total_entries=summary.total_entries,
        within_5pct=summary.within_5pct,
        within_10pct=summary.within_10pct,
        within_15pct=summary.within_15pct,
        within_20pct=summary.within_20pct,
        direction_match=summary.direction_match,
        poor=summary.poor,
        mean_abs_percent_difference=summary.mean_abs_percent_difference,
        median_abs_percent_difference=summary.median_abs_percent_difference,
        calibrated_entries=sum(1 for entry in summary.entries if entry.category != "Generic"),
        generic_entries=sum(1 for entry in summary.entries if entry.category == "Generic"),
        holdout_entries=len(holdouts),
        validation_note=(
            "Scorecard entries are published-score benchmark comparisons. "
            f"The post-lock holdout protocol {DEFAULT_HOLDOUT_PROTOCOL.protocol_id} "
            f"was locked on {DEFAULT_HOLDOUT_PROTOCOL.locked_at}; holdout labels are "
            "future regression checkpoints, not retroactive historical out-of-sample claims."
        ),
        ratings_breakdown=summary.ratings_breakdown,
        by_category={
            cat: ScorecardCategorySummary(**sub) for cat, sub in summary.by_category.items()
        },
        entries=[
            ScorecardEntryModel(
                **{
                    **entry.__dict__,
                    "evidence_type": evidence_type_for_entry(entry),
                    "holdout_status": holdout_status_for_entry(entry),
                }
            )
            for entry in summary.entries
        ],
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
            "readiness": "GET /readiness",
            "validation_scorecard": "GET /validation/scorecard",
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
