"""
Fiscal Policy Calculator — REST API

Programmatic access to CBO-style fiscal policy scoring.

Run with:
    uvicorn api:app --reload

Docs at:
    http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any
import numpy as np

from fiscal_model.health import check_health
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.policies import (
    TaxPolicy,
    SpendingPolicy,
    PolicyType,
    TransferPolicy,
)
from fiscal_model.baseline import CBOBaseline
from fiscal_model.app_data import PRESET_POLICIES, CBO_SCORE_MAP
from fiscal_model.models.macro_adapter import FRBUSAdapterLite, MacroScenario

app = FastAPI(
    title="Fiscal Policy Calculator API",
    description="Programmatic access to CBO-style fiscal policy scoring with dynamic effects",
    version="1.0.0",
)


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
    gdp_effect: Optional[float] = None  # Percentage points (cumulative)
    employment_effect: Optional[float] = None  # Thousands of jobs
    revenue_feedback: Optional[float] = None  # Billions
    dynamic_adjusted_impact: Optional[float] = None  # Billions

    # Year-by-year breakdown
    year_by_year: list[YearlyEffect]

    # Metadata
    dynamic_scoring_enabled: bool
    error_message: Optional[str] = None


class ScorePresetRequest(BaseModel):
    """Request to score a named preset policy."""

    preset_name: str = Field(..., description="Exact name from /presets endpoint")
    dynamic: bool = Field(False, description="Enable dynamic scoring")


class PresetPolicyInfo(BaseModel):
    """Information about a preset policy."""

    name: str
    description: str
    cbo_score: Optional[float] = None  # Billions (if available)
    cbo_source: Optional[str] = None
    cbo_date: Optional[str] = None


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
    target_country: Optional[str] = Field(None, description="Target country code")
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
    uncertainty_range: Optional[dict[str, float]] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""

    overall: str
    timestamp: str
    components: dict[str, Any]


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
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


@app.get("/presets", response_model=PresetsResponse)
async def list_presets():
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
async def score_policy(request: ScorePolicyRequest):
    """
    Score a custom tax policy.

    Scores static and behavioral effects of a user-defined tax policy,
    with optional dynamic feedback.
    """
    try:
        # Validate inputs
        if request.duration_years < 1:
            raise ValueError("duration_years must be at least 1")

        # Create policy
        policy = TaxPolicy(
            name=request.name,
            description=request.description,
            policy_type=PolicyType.INCOME_TAX,
            rate_change=request.rate_change,
            affected_income_threshold=request.income_threshold,
            taxable_income_elasticity=request.elasticity,
            duration_years=request.duration_years,
        )

        # Score policy
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=request.dynamic)

        # Build year-by-year breakdown
        year_by_year = []
        for i, year in enumerate(result.years):
            year_by_year.append(
                YearlyEffect(
                    year=int(year),
                    revenue_effect=float(result.static_revenue_effect[i]),
                    behavioral_offset=float(
                        result.behavioral_offset[i]
                        if hasattr(result, "behavioral_offset")
                        else 0.0
                    ),
                    dynamic_feedback=float(
                        result.revenue_feedback[i]
                        if hasattr(result, "revenue_feedback") and result.revenue_feedback is not None
                        else 0.0
                    ),
                    final_effect=float(result.final_deficit_effect[i]),
                )
            )

        # Get baseline info
        baseline = result.baseline
        baseline_vintage = (
            baseline.baseline_vintage_date
            if hasattr(baseline, "baseline_vintage_date")
            else "2024"
        )

        # Compute totals
        ten_year_impact = float(np.sum(result.final_deficit_effect))
        static_total = float(np.sum(result.static_revenue_effect))
        behavioral_total = float(
            np.sum(result.behavioral_offset)
            if hasattr(result, "behavioral_offset")
            else 0.0
        )
        dynamic_feedback_total = float(
            np.sum(result.revenue_feedback)
            if hasattr(result, "revenue_feedback") and result.revenue_feedback is not None
            else 0.0
        )

        # GDP and employment effects (if dynamic)
        gdp_effect = None
        employment_effect = None
        if request.dynamic and hasattr(result, "gdp_effect"):
            gdp_effect = float(result.gdp_effect)
        if request.dynamic and hasattr(result, "employment_effect"):
            employment_effect = float(result.employment_effect)

        return ScorePolicyResponse(
            policy_name=request.name,
            policy_description=request.description,
            baseline_vintage=baseline_vintage,
            budget_window=f"FY{int(result.years[0])}-{int(result.years[-1])}",
            ten_year_deficit_impact=ten_year_impact,
            static_revenue_effect=static_total,
            behavioral_offset=behavioral_total,
            final_static_effect=static_total + behavioral_total,
            gdp_effect=gdp_effect,
            employment_effect=employment_effect,
            revenue_feedback=dynamic_feedback_total,
            dynamic_adjusted_impact=(
                ten_year_impact + dynamic_feedback_total if request.dynamic else None
            ),
            year_by_year=year_by_year,
            dynamic_scoring_enabled=request.dynamic,
        )

    except Exception as e:
        return ScorePolicyResponse(
            policy_name=request.name,
            policy_description=request.description,
            baseline_vintage="error",
            budget_window="",
            ten_year_deficit_impact=0.0,
            static_revenue_effect=0.0,
            behavioral_offset=0.0,
            final_static_effect=0.0,
            year_by_year=[],
            dynamic_scoring_enabled=False,
            error_message=str(e),
        )


@app.post("/score/preset", response_model=ScorePolicyResponse)
async def score_preset(request: ScorePresetRequest):
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

        # For now, handle simple income tax presets
        # TODO: Extend to handle TCJA, corporate, credits, etc.
        if preset.get("is_tcja"):
            raise HTTPException(
                status_code=400,
                detail="TCJA presets require specialized scoring. Use /score with custom parameters.",
            )

        if preset.get("is_corporate"):
            raise HTTPException(
                status_code=400,
                detail="Corporate presets require specialized scoring. Use /score with custom parameters.",
            )

        # Create a basic tax policy from preset
        policy = TaxPolicy(
            name=request.preset_name,
            description=preset.get("description", ""),
            policy_type=PolicyType.INCOME_TAX,
            rate_change=preset.get("rate_change", 0.0),
            affected_income_threshold=preset.get("threshold", 0.0),
            taxable_income_elasticity=0.25,
            duration_years=10,
        )

        # Score it
        scorer = FiscalPolicyScorer(use_real_data=True)
        result = scorer.score_policy(policy, dynamic=request.dynamic)

        # Build response
        year_by_year = []
        for i, year in enumerate(result.years):
            year_by_year.append(
                YearlyEffect(
                    year=int(year),
                    revenue_effect=float(result.static_revenue_effect[i]),
                    behavioral_offset=float(
                        result.behavioral_offset[i]
                        if hasattr(result, "behavioral_offset")
                        else 0.0
                    ),
                    dynamic_feedback=float(
                        result.revenue_feedback[i]
                        if hasattr(result, "revenue_feedback") and result.revenue_feedback is not None
                        else 0.0
                    ),
                    final_effect=float(result.final_deficit_effect[i]),
                )
            )

        baseline = result.baseline
        baseline_vintage = (
            baseline.baseline_vintage_date
            if hasattr(baseline, "baseline_vintage_date")
            else "2024"
        )

        ten_year_impact = float(np.sum(result.final_deficit_effect))
        static_total = float(np.sum(result.static_revenue_effect))
        behavioral_total = float(
            np.sum(result.behavioral_offset)
            if hasattr(result, "behavioral_offset")
            else 0.0
        )

        return ScorePolicyResponse(
            policy_name=request.preset_name,
            policy_description=preset.get("description", ""),
            baseline_vintage=baseline_vintage,
            budget_window=f"FY{int(result.years[0])}-{int(result.years[-1])}",
            ten_year_deficit_impact=ten_year_impact,
            static_revenue_effect=static_total,
            behavioral_offset=behavioral_total,
            final_static_effect=static_total + behavioral_total,
            year_by_year=year_by_year,
            dynamic_scoring_enabled=request.dynamic,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/score/tariff", response_model=ScoreTariffResponse)
async def score_tariff(request: ScoreTariffRequest):
    """
    Score a tariff policy with consumer impact.

    Estimates revenue, consumer costs, and retaliation effects of tariffs.
    """
    try:
        # Simple tariff scoring model
        # Revenue = tariff_rate * import_base
        gross_revenue = request.tariff_rate * request.import_base_billions * 10

        # Consumer cost (rough estimate: tariff costs passed to consumers)
        consumer_cost = (
            gross_revenue * 1.2 if request.include_consumer_cost else 0.0
        )

        # Retaliation cost (rough estimate: 30-50% of revenue as trade loss)
        retaliation_cost = (
            gross_revenue * 0.4 if request.include_retaliation else 0.0
        )

        # Net deficit impact
        # Revenue is positive (reduces deficit), costs are negative
        net_impact = gross_revenue - (consumer_cost + retaliation_cost) / 1e3

        trade_summary = TradeSummary(
            gross_revenue=gross_revenue,
            consumer_cost=consumer_cost,
            retaliation_cost=retaliation_cost,
            net_deficit_impact=net_impact,
        )

        return ScoreTariffResponse(
            policy_name=request.name,
            ten_year_deficit_impact=-gross_revenue,  # Negative = revenue raiser
            trade_summary=trade_summary,
            uncertainty_range={
                "low": -gross_revenue * 0.7,
                "central": -gross_revenue,
                "high": -gross_revenue * 1.3,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# ROOT ENDPOINT
# =============================================================================


@app.get("/")
async def root():
    """
    API root endpoint.

    Provides information about available endpoints.
    """
    return {
        "service": "Fiscal Policy Calculator API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
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
