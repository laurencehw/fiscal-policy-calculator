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
import posixpath
import re
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from fiscal_model.api_security import (
    is_auth_enabled,
    require_api_key,
    security_middleware,
)
from fiscal_model.api_serialization import serialize_scoring_result
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.assistant import FiscalAssistant

try:  # raised when the upstream Anthropic call fails mid-turn
    from fiscal_model.assistant import AssistantUpstreamError
except ImportError:  # pragma: no cover - older assistant package

    class AssistantUpstreamError(RuntimeError):  # type: ignore[no-redef]
        """Placeholder: the assistant package predates upstream-error typing."""

        status_code: int | None = None
        usage: Any = None
from fiscal_model.assistant.rate_limit import RateLimiter, new_session_id
from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.dynamic_view import run_dynamic_view
from fiscal_model.exceptions import (
    FiscalModelError,
    PolicyValidationError,
    ScoringBoundsError,
)
from fiscal_model.health import check_health
from fiscal_model.policies import (
    DEFAULT_ORDINARY_INCOME_BASE,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    income_measure_for_preset,
    ordinary_income_base_for_preset,
)
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.preset_ids import CUSTOM_POLICY_LABEL
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
        "debt_service",
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
        for field_name in (
            "revenue_effect",
            "behavioral_offset",
            "dynamic_feedback",
            "final_effect",
            "debt_service",
            "dynamic_effect",
        ):
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

# =============================================================================
# PUBLIC-OUTPUT HYGIENE
# =============================================================================
# /health, /summary and /readiness are unauthenticated. The component payloads
# they wrap were written for an operator's terminal and carry the server's
# absolute file paths, the Python executable, the usage-database path and
# whether an Anthropic key is configured. None of that is the public's business
# (the first three map the host; the last tells an attacker which of the
# assistant's cost controls to aim at), so it is stripped here, at the API
# boundary, and the CLI (scripts/check_readiness.py) keeps the full detail.

_REPO_ROOT = Path(__file__).resolve().parent

#: Keys dropped wherever they appear in a public payload.
_PUBLIC_REDACTED_KEYS = frozenset(
    {"executable", "python_executable", "api_key_configured", "usage_db_path"}
)

_ABSOLUTE_PATH = re.compile(
    r"(?<![\w:/.])/(?:home|usr|root|tmp|var|opt|app|Users|mnt|srv|etc|workspace)"
    r"/[^\s\"',;)]*"
    r"|(?<![\w])[A-Za-z]:\\[^\s\"',;)]*"
)


def _scrub_path_text(text: str) -> str:
    """Reduce any absolute path inside ``text`` to repo-relative or a basename."""
    root = str(_REPO_ROOT)
    text = text.replace(root + "/", "").replace(root, ".")
    return _ABSOLUTE_PATH.sub(
        lambda match: posixpath.basename(match.group(0).replace("\\", "/")) or "<path>",
        text,
    )


def _public(value: Any) -> Any:
    """Return ``value`` with host-identifying fields removed or shortened."""
    if isinstance(value, dict):
        return {
            key: _public(item)
            for key, item in value.items()
            if key not in _PUBLIC_REDACTED_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    if isinstance(value, str):
        return _scrub_path_text(value)
    return value


#: /readiness runs the whole release gate (every health check, the benchmarks
#: and the scorecard) in ~2s warm and ~8s cold, on an unauthenticated route.
#: One report is shared for this many seconds; it is keyed on the builder so a
#: replaced builder never sees another's report.
READINESS_CACHE_SECONDS = 60.0
_readiness_lock = threading.Lock()
_readiness_cache: tuple[Any, float, Any] | None = None  # (builder, monotonic ts, report)


def _now() -> float:
    """Monotonic clock for the readiness cache (a seam for tests)."""
    return time.monotonic()


def _cached_readiness_report() -> Any:
    global _readiness_cache
    builder = build_readiness_report
    with _readiness_lock:
        now = _now()
        cached = _readiness_cache
        if (
            cached is not None
            and cached[0] is builder
            and now - cached[1] < READINESS_CACHE_SECONDS
        ):
            return cached[2]
        report = builder()
        _readiness_cache = (builder, _now(), report)
        return report


def _clear_readiness_cache() -> None:
    global _readiness_cache
    with _readiness_lock:
        _readiness_cache = None


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
        ...,
        ge=-1.0,
        le=1.0,
        description=(
            "Rate change as a decimal fraction: 0.026 is +2.6 percentage "
            "points, -0.01 is a one-point cut"
        ),
    )
    income_threshold: float = Field(
        0, ge=0, description="Income threshold for affected taxpayers"
    )
    elasticity: float = Field(
        0.25, ge=0, le=2.0, description="Taxable income elasticity"
    )
    ordinary_income_base: bool = Field(
        DEFAULT_ORDINARY_INCOME_BASE,
        description=(
            "If true (default), apply ordinary-bracket rate changes only to "
            "non-preferential income. Set false for AGI-inclusive surtaxes. "
            "The default is the one the app, Tailor, the composer and Ask all "
            "read, so the same specification scores the same everywhere."
        ),
    )
    duration_years: int = Field(10, ge=1, le=30, description="Policy duration")
    dynamic: bool = Field(
        False,
        description=(
            "Add the app's dynamic view (FRB/US-Lite revenue feedback, debt "
            "service and a dynamic total). The conventional headline does not move."
        ),
    )
    policy_type: str = Field(
        "income_tax",
        description=(
            "'income_tax' (individual rate change above ``income_threshold``) "
            "or 'corporate_tax' (a statutory corporate rate change, scored by "
            "the corporate module; ``income_threshold`` must be 0). "
            "'payroll_tax' is rejected: a payroll change is a cap, donut or "
            "program-rate design with no single rate-and-threshold mapping."
        ),
    )


class YearlyEffect(BaseModel):
    """Year-by-year effects, in billions.

    ``final_effect`` is the conventional deficit effect (static + behavioral,
    positive = increases the deficit) in every mode. With dynamic scoring on,
    ``dynamic_feedback`` is that year's revenue feedback from the app's macro
    adapter (positive = extra revenue), ``debt_service`` its interest cost
    (positive = adds to the deficit), and ``dynamic_effect`` is
    ``final_effect - dynamic_feedback + debt_service``. The years sum to the
    response's ten-year fields.
    """

    year: int
    revenue_effect: float  # Billions
    behavioral_offset: float  # Billions
    dynamic_feedback: float  # Billions; 0.0 unless dynamic scoring is on
    final_effect: float  # Billions; conventional in every mode
    debt_service: float | None = None  # Billions; dynamic scoring only
    dynamic_effect: float | None = None  # Billions; dynamic scoring only


class ResultCredibilityModel(BaseModel):
    """Accuracy context attached to one score.

    Since Wave C's H4 the accuracy figures are the observed error distribution
    of the policy's own **out-of-sample class** — the 44 pre-registered Tier 1
    rows, bucketed by the same routing the CI per-class gate uses — and not a
    mean over a scorecard category that blended fitted bookkeeping with unfitted
    reconstructions. Every band field is optional, because two thirds of the
    shipped catalog prices a reform the pre-registered battery does not score;
    ``no_band_reason`` says which, and the ``own_row_*`` fields carry this
    policy's own scorecard row and the tier it sits in. The two are separate on
    purpose: collapsing them is the "validated within X%" claim this repository
    does not make.
    """

    category: str
    evidence_type: str
    policy_class: str | None = None
    class_label: str | None = None
    n_tier1_rows: int = 0
    mean_abs_pct_error: float | None = None
    median_abs_pct_error: float | None = None
    max_abs_pct_error: float | None = None
    rows_inside_mean_band: int | None = None
    #: Inner band — the class's mean error applied to this figure. Named for
    #: continuity with every client written before H4.
    uncertainty_low: float | None = None
    uncertainty_high: float | None = None
    #: Outer band — the class's worst observed row.
    outer_low: float | None = None
    outer_high: float | None = None
    no_band_reason: str = ""
    own_row_policy_id: str | None = None
    own_row_tier: str | None = None
    own_row_tier_label: str | None = None
    own_row_abs_pct_error: float | None = None
    own_row_official_billions: float | None = None
    own_row_caption: str = ""
    holdout_status: str
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

    # Dynamic effects (if enabled). Since 2026-09-29 these are the app's
    # dynamic view: one run of the macro adapter the app defaults to
    # (FRB/US-Lite), named in ``dynamic_model``. ``ten_year_deficit_impact``
    # stays the conventional score either way, and
    # dynamic_adjusted_impact = ten_year_deficit_impact - revenue_feedback
    #                           + debt_service.
    gdp_effect: float | None = None  # Percent-years (sum of annual GDP level effects)
    employment_effect: float | None = None  # Thousands of jobs, window average
    revenue_feedback: float | None = None  # Billions; positive = extra revenue
    debt_service: float | None = None  # Billions; positive = adds to the deficit
    dynamic_adjusted_impact: float | None = None  # Billions; deficit convention
    dynamic_model: str | None = None

    # Year-by-year breakdown
    year_by_year: list[YearlyEffect]

    # Metadata
    dynamic_scoring_enabled: bool
    credibility: ResultCredibilityModel | None = None
    error_message: str | None = None


class ScorePresetRequest(BaseModel):
    """Request to score a named preset policy."""

    preset_name: str = Field(..., description="Exact name from /presets endpoint")
    dynamic: bool = Field(
        False,
        description=(
            "Add the app's dynamic view (FRB/US-Lite revenue feedback, debt "
            "service and a dynamic total). The conventional headline does not move."
        ),
    )


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


#: Total US goods imports are ~$3.2T; a base ten times that is a typo, and an
#: unbounded one scored as an overflow (``1e308``) rather than a client error.
_MAX_IMPORT_BASE_BILLIONS = 20_000.0

#: What ``/score/tariff``'s headline is, and which request flags do not move it.
TARIFF_HEADLINE_BASIS = "conventional"
TARIFF_HEADLINE_NOTE = (
    "ten_year_deficit_impact is the conventional net customs score: gross duty "
    "less the import-demand response, avoidance and the income-and-payroll "
    "offset. include_consumer_cost and include_retaliation only decide whether "
    "those columns are reported in trade_summary; neither moves the headline "
    "or uncertainty_range, because retaliation and consumer cost are not part "
    "of a conventional estimate."
)


class ScoreTariffRequest(BaseModel):
    """Request to score a tariff policy."""

    name: str = Field("Custom Tariff", description="Tariff name")
    tariff_rate: float = Field(..., ge=0, le=1.0, description="Tariff rate (0-1)")
    import_base_billions: float = Field(
        3200.0,
        gt=0,
        le=_MAX_IMPORT_BASE_BILLIONS,
        description=(
            "Import base the tariff applies to (billions of dollars a year). "
            "Total US goods imports are about $3,200B; values above "
            f"${_MAX_IMPORT_BASE_BILLIONS:,.0f}B are rejected."
        ),
    )
    target_country: str | None = Field(
        None,
        description=(
            "Not supported: the scorer prices the import base you supply and "
            "has no per-country data behind this field. Send the country's "
            "import base as import_base_billions. A non-null value is "
            "rejected with 422 rather than accepted and ignored."
        ),
    )
    include_consumer_cost: bool = Field(
        True,
        description=(
            "Report consumer cost in trade_summary. Does not move "
            "ten_year_deficit_impact (see headline_basis)."
        ),
    )
    include_retaliation: bool = Field(
        True,
        description=(
            "Report retaliation cost in trade_summary. Does not move "
            "ten_year_deficit_impact (see headline_basis)."
        ),
    )

    @field_validator("target_country")
    @classmethod
    def _target_country_unsupported(cls, value: str | None) -> str | None:
        if value is not None:
            raise ValueError(
                "target_country is not supported: it was accepted and unused. "
                "Send the target country's import base as import_base_billions."
            )
        return value


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
    #: Which estimate the headline is. Always "conventional": the request's
    #: include_* flags change only what trade_summary reports.
    headline_basis: str = TARIFF_HEADLINE_BASIS
    headline_note: str = TARIFF_HEADLINE_NOTE


class StatusIssueModel(BaseModel):
    """Flattened status issue for monitoring and validation clients."""

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
    issues: list[StatusIssueModel] = Field(default_factory=list)


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
    #: The universe the source ranks — "household" (CBO's tables) or
    #: "tax_unit" (JCT's) — and therefore the one the runner *requests*. It is
    #: a statement about the document, not about this run.
    ranking_universe: str = "tax_unit"
    #: The universe the model was actually scored on, read off
    #: ``DistributionalAnalysis.unit``. It differs from ``ranking_universe``
    #: when a household request cannot reach the return-level microsim: every
    #: TCJA-extension and corporate policy takes the synthetic bracket path,
    #: which aggregates IRS return counts and has no household layer, so the
    #: request degrades to tax units. null when the model reported no
    #: universe. Two benchmarks with the same error mean different things if
    #: they were scored on different populations, so this is the field to read
    #: beside the number.
    scored_universe: str | None = None
    #: True when ``scored_universe`` differs from ``ranking_universe`` — the
    #: comparison is against a population the source does not use.
    universe_fell_back: bool = False


class BenchmarksResponse(BaseModel):
    """Response listing current model accuracy against every benchmark."""

    benchmarks: list[BenchmarkResult]
    count: int
    overall_rating: str  # ok | degraded
    issues: list[StatusIssueModel] = Field(default_factory=list)


class SummaryResponse(BaseModel):
    """One-call overview: health, benchmarks, and microdata coverage."""

    overall: str  # ok | degraded
    timestamp: str
    health: dict[str, Any]
    benchmarks: list[BenchmarkResult]
    benchmarks_rating: str  # ok | degraded
    microdata_coverage: dict[str, Any]
    auth_required: bool
    issues: list[StatusIssueModel] = Field(default_factory=list)


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
    # Where the *target* came from: line_item | line_item_differs | secondhand |
    # model_estimate | unclassified. Orthogonal to accuracy — see
    # fiscal_model/validation/provenance.py.
    provenance: str = "unclassified"
    # Whether the module carries a constant fitted to reproduce this target.
    # False once a target has been revised: the constant is fitted to the
    # superseded figure, never to the replacement.
    calibrated_to_target: bool = True
    # What the runner declared, before a revision was applied. The two differ
    # on exactly the rows a target revision moved out of the fitted tier, which
    # is what lets a client reconstruct the "held in place" reading without
    # also folding in the sectoral rows that were never fitted.
    declared_calibrated_to_target: bool = True
    # Set when this benchmark's target has been *moved* to a published figure
    # through fiscal_model/validation/target_revisions.py. The three fields say
    # which ledger row is in force, what the target used to be, and why it was
    # retired — so a client can tell "the model changed" from "the target did".
    target_revision_id: str | None = None
    superseded_10yr_billions: float | None = None
    target_revision_reason: str = ""
    # Set when the ledger has WITHDRAWN this benchmark's target with nothing to
    # replace it - the third state, distinct from a revision. The figure the
    # entry then carries is the withdrawn one, kept only so the row still
    # prints, and its percent_difference measures nothing. A retired row leaves
    # the reconstruction tier's mean; retired_target_entries counts it, and
    # cold_holdout.py reports that tier a second time with the retired rows
    # folded back at the error they carried, so a mean that fell because a row
    # was withdrawn is readable as such.
    target_retired: bool = False
    target_retirement_reason: str = ""
    # Set when the live ledger row records a published *range* rather than a
    # point — the case where the agency scored the policy under several
    # scenarios and published no single figure. When these are set,
    # percent_difference is a distance from an editorial midpoint and is not a
    # measurement of accuracy: read within_published_range instead.
    published_range_low_billions: float | None = None
    published_range_high_billions: float | None = None
    within_published_range: bool | None = None
    distance_to_published_range_billions: float | None = None
    # Table/row/page reference for a target transcribed from a primary document.
    benchmark_table: str | None = None
    # The figure the primary document actually prints, when it disagrees with
    # official_10yr_billions. Set only for provenance == "line_item_differs":
    # a sourcing pass records the gap, it never moves a calibrated target.
    official_10yr_billions_line_item: float | None = None
    # One line on what the transcription established, or what was searched.
    sourcing_note: str = ""
    # True when somebody opened the primary document and read the row, as
    # opposed to the entry merely being *labelled* line_item from a deep link.
    # Deliberately stricter than `provenance`, and the summary's
    # `transcribed_entries` counts exactly these: without the per-entry flag a
    # client could see the count but not which rows it refers to.
    transcribed: bool = False
    evidence_type: str = "specialized_benchmark_comparison"
    holdout_status: str = "calibration_reference"


class ScorecardIssueModel(BaseModel):
    """Flattened scorecard issue for validation clients."""

    surface: str = "revenue_scorecard"
    severity: str  # warn | fail
    policy_id: str
    category: str
    rating: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


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
    # Provenance of the *targets*, so a client can separate "reproduces a
    # published table row" from "reproduces a rounded headline" from
    # "reproduces a model estimate with no published score at all".
    provenance_breakdown: dict[str, int] = Field(default_factory=dict)
    calibrated_provenance_breakdown: dict[str, int] = Field(default_factory=dict)
    calibrated_published_entries: int = 0
    calibrated_model_estimate_entries: int = 0
    # Headline counts across both tiers. ``published_entries`` is what the app
    # footer and the README quote; ``total_entries`` additionally includes the
    # illustrations, which have no official score to be validated against.
    published_entries: int = 0
    model_estimate_entries: int = 0
    transcribed_entries: int = 0
    line_item_differs_entries: int = 0
    # Entries whose target has been moved to a published figure. Each one also
    # leaves the fitted-calibrated tier, so a client computing a fitted mean
    # needs this count to know the denominator moved.
    revised_target_entries: int = 0
    # Entries whose target the ledger has withdrawn. Never merely dropped:
    # see ScorecardEntryModel.target_retired.
    retired_target_entries: int = 0
    by_category: dict[str, ScorecardCategorySummary]
    entries: list[ScorecardEntryModel]
    issues: list[ScorecardIssueModel] = Field(default_factory=list)


#: Types ``/score`` can score honestly from a rate and a threshold. Corporate
#: goes through ``CorporateTaxPolicy`` (profits base, the corporate module's
#: own calibration); a plain ``TaxPolicy`` labelled corporate would be priced on
#: the individual income-tax base — -$1,420.3B for +1pp against the corporate
#: module's -$198.9B — which is why it is built separately below.
SUPPORTED_CUSTOM_POLICY_TYPES = {
    PolicyType.INCOME_TAX,
    PolicyType.CORPORATE_TAX,
}

#: Known types ``/score`` refuses, with the reason. A payroll change is a wage
#: cap, a donut hole, a program rate or a new flat tax; "rate_change at
#: income_threshold" names none of them, and the only way to price it was to
#: score it on the individual income-tax base, which is the wrong base.
UNSUPPORTED_CUSTOM_POLICY_REASONS = {
    PolicyType.PAYROLL_TAX: (
        "policy_type 'payroll_tax' is not supported by /score: a payroll-tax "
        "change is a wage-cap, donut-hole or program-rate design that a single "
        "rate_change and income_threshold cannot express, and scoring it as an "
        "income-tax rate change would price it on the wrong base. Use /score/preset "
        "with a payroll preset, or the app's payroll module."
    ),
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

    if policy_type in UNSUPPORTED_CUSTOM_POLICY_REASONS:
        raise HTTPException(
            status_code=400,
            detail=UNSUPPORTED_CUSTOM_POLICY_REASONS[policy_type],
        )

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


#: The budget window every API score is reported over.
_SCORING_WINDOW_YEARS = 10


def _build_custom_policy(request: ScorePolicyRequest, policy_type: PolicyType) -> Any:
    """Build the policy ``/score`` scores, on the base its type names.

    ``duration_years`` is honoured by the policy classes only when ``sunset`` is
    set, so it is set whenever the duration is shorter than the window — left
    off, every duration scored identically.
    """
    sunset = request.duration_years < _SCORING_WINDOW_YEARS
    if policy_type == PolicyType.CORPORATE_TAX:
        if request.income_threshold:
            raise PolicyValidationError(
                "income_threshold does not apply to policy_type 'corporate_tax': "
                "a corporate rate change is priced on the profits base. Send "
                "income_threshold 0."
            )
        from fiscal_model.corporate import CorporateTaxPolicy

        return CorporateTaxPolicy(
            name=request.name,
            description=request.description,
            policy_type=policy_type,
            rate_change=request.rate_change,
            corporate_elasticity=request.elasticity,
            start_year=APP_DEFAULT_START_YEAR,
            duration_years=request.duration_years,
            sunset=sunset,
        )
    return TaxPolicy(
        name=request.name,
        description=request.description,
        policy_type=policy_type,
        rate_change=request.rate_change,
        affected_income_threshold=request.income_threshold,
        taxable_income_elasticity=request.elasticity,
        start_year=APP_DEFAULT_START_YEAR,
        duration_years=request.duration_years,
        sunset=sunset,
        ordinary_income_base=request.ordinary_income_base,
    )


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
        start_year=APP_DEFAULT_START_YEAR,
        duration_years=10,
        ordinary_income_base=ordinary_income_base_for_preset(preset),
        income_measure=income_measure_for_preset(preset),
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
        # An out-of-range-but-functional runtime (e.g. Python 3.14 in dev)
        # is a warning, not a failure — it boots and scores correctly. A
        # genuine error, or a degraded scoring engine, still fails.
        severity = (
            "fail"
            if status == "error" or component == "model"
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


def _health_issues(health_data: dict[str, Any]) -> list[StatusIssueModel]:
    """Return /health issue models for degraded components."""
    return [StatusIssueModel(**issue) for issue in _health_issue_payloads(health_data)]


def _summary_health_issues(health_data: dict[str, Any]) -> list[StatusIssueModel]:
    """Flatten non-ok health components for /summary consumers."""
    return [StatusIssueModel(**issue) for issue in _health_issue_payloads(health_data)]


def _benchmark_issue_payloads(
    benchmark_results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Flatten failing distributional benchmarks into serializable payloads."""
    return [
        {
            "surface": "distributional_benchmarks",
            "severity": "fail",
            "name": benchmark.policy_id,
            "message": (
                "Distributional benchmark needs improvement: "
                f"{benchmark.policy_name}."
            ),
            "details": {
                "policy_id": benchmark.policy_id,
                "rating": benchmark.rating,
                "mean_absolute_share_error_pp": benchmark.mean_absolute_share_error_pp,
                "matched_rows": benchmark.matched_rows,
                "benchmark_rows": benchmark.benchmark_rows,
            },
        }
        for benchmark in benchmark_results
        if benchmark.rating == "needs_improvement"
    ]


def _benchmark_issues(
    benchmark_results: list[BenchmarkResult],
) -> list[StatusIssueModel]:
    """Return /benchmarks issue models for failing benchmark rows."""
    return [
        StatusIssueModel(**issue)
        for issue in _benchmark_issue_payloads(benchmark_results)
    ]


def _summary_benchmark_issues(
    benchmark_results: list[BenchmarkResult],
) -> list[StatusIssueModel]:
    """Flatten failing distributional benchmarks for /summary consumers."""
    return [
        StatusIssueModel(**issue)
        for issue in _benchmark_issue_payloads(benchmark_results)
    ]


def _scorecard_entry_issues(entries: list[Any]) -> list[ScorecardIssueModel]:
    """Flatten material revenue scorecard issues for API clients."""
    issues: list[ScorecardIssueModel] = []
    for entry in entries:
        rating = getattr(entry, "rating", "unknown")
        direction_match = bool(getattr(entry, "direction_match", False))
        category = str(getattr(entry, "category", "unknown"))
        policy_id = str(getattr(entry, "policy_id", "unknown"))
        known_limitations = list(getattr(entry, "known_limitations", []) or [])

        if rating == "Error":
            severity = "fail"
            reason = "error_rating"
            message = f"{policy_id} has an Error revenue scorecard rating."
        elif not direction_match:
            severity = "fail"
            reason = "direction_mismatch"
            message = f"{policy_id} has the wrong revenue-impact direction."
        elif rating == "Poor":
            documented_or_generic = bool(known_limitations) or category == "Generic"
            severity = "warn" if documented_or_generic else "fail"
            reason = (
                "documented_or_generic_poor"
                if documented_or_generic
                else "undocumented_poor"
            )
            message = f"{policy_id} has a Poor revenue scorecard rating."
        else:
            continue

        issues.append(
            ScorecardIssueModel(
                severity=severity,
                policy_id=policy_id,
                category=category,
                rating=rating,
                message=message,
                details={
                    "reason": reason,
                    "direction_match": direction_match,
                    "abs_percent_difference": getattr(
                        entry,
                        "abs_percent_difference",
                        None,
                    ),
                    "known_limitations": known_limitations,
                    "holdout_status": getattr(entry, "holdout_status", None),
                },
            )
        )
    return issues


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health", response_model=HealthCheckResponse)
def health_check():
    """
    Health check endpoint.

    Returns status of all data sources and models.
    """
    health_data = _public(check_health())
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

    health_data = _public(check_health())
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
                ranking_universe=benchmark.ranking_universe,
                scored_universe=comparison.scored_universe,
                universe_fell_back=comparison.universe_fell_back,
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
    report = _cached_readiness_report()
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
                summary=_scrub_path_text(check.summary),
                details=_public(check.details),
            )
            for check in report.checks
        ],
        issues=[
            ReadinessIssueModel(
                name=issue.name,
                severity=issue.severity,
                required=issue.required,
                summary=_scrub_path_text(issue.summary),
                details=_public(issue.details),
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
                ranking_universe=benchmark.ranking_universe,
                scored_universe=comparison.scored_universe,
                universe_fell_back=comparison.universe_fell_back,
            )
        )

    return BenchmarksResponse(
        benchmarks=results,
        count=len(results),
        overall_rating=worst,
        issues=_benchmark_issues(results),
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
    serialized_entries = [
        ScorecardEntryModel(
            **{
                **entry.__dict__,
                "evidence_type": evidence_type_for_entry(entry),
                "holdout_status": holdout_status_for_entry(entry),
            }
        )
        for entry in summary.entries
    ]

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
        provenance_breakdown=summary.provenance_breakdown,
        calibrated_provenance_breakdown=summary.calibrated_provenance_breakdown,
        calibrated_published_entries=summary.calibrated_published_entries,
        calibrated_model_estimate_entries=summary.calibrated_model_estimate_entries,
        published_entries=summary.published_entries,
        model_estimate_entries=summary.model_estimate_entries,
        transcribed_entries=summary.transcribed_entries,
        line_item_differs_entries=summary.line_item_differs_entries,
        revised_target_entries=summary.revised_target_entries,
        retired_target_entries=summary.retired_target_entries,
        by_category={
            cat: ScorecardCategorySummary(**sub) for cat, sub in summary.by_category.items()
        },
        entries=serialized_entries,
        issues=_scorecard_entry_issues(serialized_entries),
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
        # The UI's "Custom Policy" is a placeholder for the user's own inputs,
        # not a proposal; listing it would invite scoring a -2pp-at-$500K
        # stand-in as if somebody had proposed it.
        if preset_name == CUSTOM_POLICY_LABEL:
            continue
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


def _score_and_serialize(
    scorer: Any,
    policy: Any,
    *,
    policy_name: str,
    policy_description: str,
    dynamic: bool,
) -> dict[str, Any]:
    """Score ``policy`` the way the app does and serialize it.

    The engine always runs conventionally. A dynamic request then runs the
    app's own dynamic view (:func:`fiscal_model.dynamic_view.run_dynamic_view`,
    FRB/US-Lite, the app's default model) on that conventional path, so the
    API returns the dynamic figures the app displays for the same policy.
    ``EconomicModel``, which ``score_policy(dynamic=True)`` would run, is not
    consulted. A macro-model failure degrades the dynamic fields to null with
    an ``error_message``; it never fails the conventional score.
    """
    result = scorer.score_policy(policy, dynamic=False)
    dynamic_view = macro_result = None
    if dynamic:
        dynamic_view, macro_result = run_dynamic_view(policy, result)
    return serialize_scoring_result(
        result,
        policy_name=policy_name,
        policy_description=policy_description,
        dynamic_scoring_enabled=dynamic,
        dynamic_view=dynamic_view,
        macro_result=macro_result,
    )


@app.post("/score", response_model=ScorePolicyResponse)
def score_policy(
    request: ScorePolicyRequest,
    _api_key_label: str = Depends(require_api_key),
):
    """
    Score a custom tax policy.

    Scores static and behavioral effects of a user-defined tax policy. With
    ``"dynamic": true`` it adds the app's dynamic view (FRB/US-Lite revenue
    feedback, debt service and a dynamic total); the headline
    ``ten_year_deficit_impact`` stays the conventional score either way.
    """
    try:
        # Validate inputs
        if request.duration_years < 1:
            raise PolicyValidationError("duration_years must be at least 1")
        policy_type = _resolve_custom_policy_type(request.policy_type)

        policy = _build_custom_policy(request, policy_type)

        # Score policy
        scorer = FiscalPolicyScorer(
            start_year=APP_DEFAULT_START_YEAR, use_real_data=True
        )
        payload = _score_and_serialize(
            scorer,
            policy,
            policy_name=request.name,
            policy_description=request.description,
            dynamic=request.dynamic,
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

    Scores a policy from the preset library. ``"dynamic": true`` adds the
    app's dynamic view, exactly as ``/score`` does.
    """
    try:
        if request.preset_name == CUSTOM_POLICY_LABEL:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{CUSTOM_POLICY_LABEL}' is the app's placeholder for a "
                    "user's own inputs, not a preset. Use POST /score to score "
                    "a custom policy, or /presets for the scorable presets."
                ),
            )
        # Look up preset
        if request.preset_name not in PRESET_POLICIES:
            raise ValueError(
                f"Unknown preset: {request.preset_name}. "
                f"Use /presets to see available presets."
            )

        preset = PRESET_POLICIES[request.preset_name]
        policy, use_real_data = _build_preset_policy(request.preset_name)

        scorer = FiscalPolicyScorer(
            start_year=max(
                int(getattr(policy, "start_year", APP_DEFAULT_START_YEAR)),
                APP_DEFAULT_START_YEAR,
            ),
            use_real_data=use_real_data,
        )
        payload = _score_and_serialize(
            scorer,
            policy,
            policy_name=request.preset_name,
            policy_description=preset.get("description", ""),
            dynamic=request.dynamic,
        )
        _validate_serialized_result(payload, policy_name=request.preset_name)
        return ScorePolicyResponse(**payload)

    except HTTPException:
        raise
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
            start_year=max(
                int(getattr(policy, "start_year", APP_DEFAULT_START_YEAR)),
                APP_DEFAULT_START_YEAR,
            ),
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

        # The same sanity check /score runs on its payload: non-finite or
        # implausibly large figures are an error, never a 200.
        _validate_serialized_result(
            {
                "ten_year_deficit_impact": net_impact,
                "year_by_year": [
                    {"year": int(year), "final_effect": float(value)}
                    for year, value in zip(
                        result.years, result.final_deficit_effect, strict=False
                    )
                ],
            },
            policy_name=request.name,
        )
        for field_name, value in trade_summary.model_dump().items():
            if not math.isfinite(value):
                raise ScoringBoundsError(
                    f"Policy '{request.name}': non-finite trade_summary.{field_name}"
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

    except HTTPException:
        raise
    except (PolicyValidationError, ValueError) as e:
        logger.info("Tariff '%s' invalid input: %s", request.name, e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FiscalModelError as e:
        logger.warning("Tariff '%s' scoring error: %s", request.name, e)
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error scoring tariff '%s'", request.name)
        raise HTTPException(status_code=500, detail="Internal scoring error") from e


# =============================================================================
# ASK ASSISTANT ENDPOINT
# =============================================================================


class AskMessage(BaseModel):
    """One turn in an Ask conversation."""

    role: str = Field(
        ..., description="'user' or 'assistant'", pattern=r"^(user|assistant)$"
    )
    content: str = Field(..., description="Plain-text message content")


class AskRequest(BaseModel):
    """Request to the Ask assistant."""

    question: str = Field(
        ..., min_length=1, max_length=4000, description="The user's question"
    )
    history: list[AskMessage] = Field(
        default_factory=list,
        description="Prior turns, in order. The new question is NOT included here.",
    )
    scoring_context: dict[str, Any] | None = Field(
        None,
        description=(
            "Optional context describing a policy the caller has already "
            "scored — e.g. {policy_name, ten_year_deficit_impact_billions, "
            "credibility}. Injected into the assistant's system prompt for "
            "grounding."
        ),
    )
    session_id: str | None = Field(
        None,
        description=(
            "Stable identifier for rate-limiting and telemetry. If omitted, a "
            "new id is generated per request (defeats per-session caps for "
            "the caller's own benefit — pass a stable id to keep "
            "conversations rate-limited as one)."
        ),
        max_length=64,
    )
    enable_web_search: bool = Field(
        True,
        description=(
            "If true, allow the model to use Anthropic's domain-restricted "
            "web_search tool to fetch live authoritative pages. Disable for "
            "deterministic / offline runs."
        ),
    )


class AskToolCall(BaseModel):
    """Provenance entry for a single tool invocation during the turn."""

    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_summary: str | None = None


class AskUsage(BaseModel):
    """Per-turn token + dollar accounting."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0


class AskResponse(BaseModel):
    """Response from /ask."""

    answer: str = Field(
        ..., description="The assistant's full answer (post-citation-cleanup)."
    )
    model: str = Field(..., description="Anthropic model used for this turn.")
    tool_calls: list[AskToolCall] = Field(default_factory=list)
    stripped_citation_markers: list[int] = Field(
        default_factory=list,
        description=(
            "Citation markers the model emitted without supporting tool calls; "
            "they were replaced with `[citation needed]` in the answer."
        ),
    )
    usage: AskUsage
    session_id: str = Field(
        ..., description="Echoed session id (generated if the caller omitted one)."
    )
    elapsed_s: float


# Built once per process. The FiscalAssistant's Anthropic client is lazy,
# so this is cheap; FREDData hits cache; KnowledgeSearcher lazily indexes.
def _build_api_assistant() -> FiscalAssistant:
    from pathlib import Path

    from fiscal_model.data.fred_data import FREDData

    knowledge_dir = (
        Path(__file__).resolve().parent
        / "fiscal_model"
        / "assistant"
        / "knowledge"
    )
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    return FiscalAssistant(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        fred_data=FREDData(),
        knowledge_dir=knowledge_dir,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
    )


_ASK_ASSISTANT: FiscalAssistant | None = None
_ASK_LIMITER: RateLimiter | None = None


def _get_ask_assistant() -> FiscalAssistant:
    global _ASK_ASSISTANT
    if _ASK_ASSISTANT is None:
        _ASK_ASSISTANT = _build_api_assistant()
    return _ASK_ASSISTANT


def _get_ask_limiter() -> RateLimiter:
    global _ASK_LIMITER
    if _ASK_LIMITER is None:
        _ASK_LIMITER = RateLimiter()
    return _ASK_LIMITER


def _spawn_request_assistant(
    base: FiscalAssistant, *, enable_web_search: bool
) -> FiscalAssistant:
    """The assistant one request should use.

    A ``FiscalAssistant`` holds per-turn state (``last_usage``,
    ``last_full_text``, its tools' provenance and scoring context,
    ``_enable_web_search``), so two concurrent requests on the shared instance
    overwrite each other's: one request's usage was billed to another's
    session and one caller's scoring context reached another's prompt. Each
    request therefore gets its own copy, sharing the client, scorer and
    knowledge index, and the per-request web-search toggle is set on that copy
    only — never on the singleton.

    Falls back to the shared instance, and leaves its toggle alone, when the
    assistant package offers no per-request copy.
    """
    for name in ("spawn", "clone_for_request"):
        factory = getattr(base, name, None)
        if not callable(factory):
            continue
        try:
            return factory(enable_web_search=enable_web_search)
        except TypeError:
            clone = factory()
            if clone is not base:
                clone._enable_web_search = bool(enable_web_search)
            return clone
    return base


_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_tokens",
    "cache_read_tokens",
    "cost_usd",
)


def _upstream_detail(exc: BaseException) -> str:
    """Client-safe text for an upstream failure (no raw SDK message)."""
    status = getattr(exc, "status_code", None)
    suffix = f" (upstream HTTP {status})" if status else ""
    return f"The assistant's upstream model call failed{suffix}. Try again shortly."


def _record_ask_turn(
    limiter: RateLimiter,
    *,
    session_id: str,
    assistant: FiscalAssistant,
    question: str,
    elapsed_s: float,
    error: str | None,
    exc: BaseException | None = None,
    answer: str | None = None,
) -> dict[str, Any]:
    """Write one ledger row for a turn, successful or not, and return its usage.

    Usage of calls that completed before a failure was still paid for, so it is
    recorded with the error rather than dropped. The upstream error carries it
    when the assistant package attaches one; the assistant's own ``last_usage``
    is the fallback.
    """
    usage = getattr(exc, "usage", None) or assistant.last_usage
    usage_dict = usage.to_dict() if usage else {}
    final_text = answer if answer is not None else (assistant.last_full_text or "")
    tools_used = [p.get("tool", "") for p in (assistant.last_provenance or [])]
    try:
        limiter.record_turn(
            session_id=session_id,
            role="assistant",
            model=assistant._model,
            usage_dict=usage_dict,
            elapsed_s=elapsed_s,
            tools_used=tools_used,
            stripped_markers=len(assistant.last_stripped_markers or []),
            error=error,
            question_chars=len(question),
            answer_chars=len(final_text),
        )
    except Exception:  # a ledger failure must not turn a good answer into a 500
        logger.exception("Could not record the Ask turn in the usage ledger")
    return usage_dict


@app.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    _api_key_label: str = Depends(require_api_key),
) -> AskResponse:
    """
    Pose a public-finance question to the citation-grounded assistant.

    The assistant answers using the app's own scoring engine and a curated
    set of authoritative external sources (CBO, JCT, PWBM, Yale Budget Lab,
    Tax Policy Center, Peterson, BEA, BLS, SSA Trustees, FRED). Every
    substantive claim is cited; unsupported citation markers are stripped
    automatically.

    Subject to the same daily-cost cap and per-session limits as the
    Streamlit Ask tab — both share a single sqlite ledger so a busy API
    caller doesn't drain the UI budget.

    Returns the full answer in one response (non-streaming). Streaming
    via SSE may be added in a future revision.
    """
    import time

    shared = _get_ask_assistant()
    limiter = _get_ask_limiter()

    if not shared.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Ask assistant is not configured: set ANTHROPIC_API_KEY in "
                "the server environment."
            ),
        )

    session_id = request.session_id or new_session_id()
    user_turn_count = sum(1 for m in request.history if m.role == "user")

    decision = limiter.check(
        session_id=session_id,
        session_message_count=user_turn_count,
        last_message_ts=None,  # API callers self-pace; no cooldown enforced
    )
    if not decision.allowed:
        raise HTTPException(status_code=429, detail=decision.reason)

    # This request's own assistant: per-turn state and the web_search toggle
    # live on the copy, never on the shared instance.
    assistant = _spawn_request_assistant(
        shared, enable_web_search=request.enable_web_search
    )

    history_for_api = [
        {"role": m.role, "content": m.content} for m in request.history
    ]

    start = time.time()
    try:
        chunks = list(
            assistant.stream_response(
                user_message=request.question,
                history=history_for_api,
                scoring_context=request.scoring_context,
            )
        )
    except AssistantUpstreamError as exc:
        # The upstream call failed: that is a 502, not a 200 carrying an
        # error string, and the ledger row says so.
        logger.warning("Ask upstream failure: %s", exc)
        _record_ask_turn(
            limiter,
            session_id=session_id,
            assistant=assistant,
            question=request.question,
            elapsed_s=time.time() - start,
            error=f"{type(exc).__name__}: {exc}",
            exc=exc,
            answer=getattr(exc, "partial_text", "") or "",
        )
        raise HTTPException(status_code=502, detail=_upstream_detail(exc)) from exc
    except Exception as exc:
        logger.exception("Ask endpoint failed")
        _record_ask_turn(
            limiter,
            session_id=session_id,
            assistant=assistant,
            question=request.question,
            elapsed_s=time.time() - start,
            error=f"{type(exc).__name__}: {exc}",
        )
        if type(exc).__module__.startswith("anthropic"):
            # An SDK error that escaped the assistant's own wrapping is still
            # the upstream's failure, not ours.
            raise HTTPException(status_code=502, detail=_upstream_detail(exc)) from exc
        raise HTTPException(status_code=500, detail="Internal assistant error") from exc
    elapsed = time.time() - start
    final_text = assistant.last_full_text or "".join(chunks)

    # Persist for telemetry + daily cap accounting.
    usage_dict = _record_ask_turn(
        limiter,
        session_id=session_id,
        assistant=assistant,
        question=request.question,
        elapsed_s=elapsed,
        error=None,
        answer=final_text,
    )

    return AskResponse(
        answer=final_text,
        model=assistant._model,
        tool_calls=[
            AskToolCall(
                tool=p.get("tool", ""),
                args=p.get("args") or {},
                result_summary=p.get("result_summary"),
            )
            for p in assistant.last_provenance
        ],
        stripped_citation_markers=list(assistant.last_stripped_markers or []),
        usage=AskUsage(**{k: usage_dict.get(k, 0) for k in _USAGE_FIELDS}),
        session_id=session_id,
        elapsed_s=round(elapsed, 3),
    )


@app.post("/ask/stream")
def ask_stream(
    request: AskRequest,
    _api_key_label: str = Depends(require_api_key),
) -> StreamingResponse:
    """
    Streaming variant of POST /ask using Server-Sent Events.

    Emits a sequence of ``event: token`` frames carrying chunks of the
    answer, followed by a final ``event: done`` frame with structured
    metadata (tool_calls, usage, stripped_markers, session_id) as JSON.
    On error, emits an ``event: error`` frame with a JSON ``{detail}``.

    SSE format (each frame ends with a blank line):

        event: token
        data: Federal debt held by the public

        event: token
        data:  rose to $28 trillion in FY2024.

        event: done
        data: {"model": "...", "tool_calls": [...], "usage": {...},
               "stripped_citation_markers": [], "session_id": "...",
               "elapsed_s": 5.41}

    Subject to the same daily-cost cap and per-session limits as the
    non-streaming /ask and the Streamlit Ask tab — they share one sqlite
    ledger.
    """
    import json as _json
    import time as _time

    shared = _get_ask_assistant()
    limiter = _get_ask_limiter()

    if not shared.is_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Ask assistant is not configured: set ANTHROPIC_API_KEY in "
                "the server environment."
            ),
        )

    session_id = request.session_id or new_session_id()
    user_turn_count = sum(1 for m in request.history if m.role == "user")

    decision = limiter.check(
        session_id=session_id,
        session_message_count=user_turn_count,
        last_message_ts=None,
    )
    if not decision.allowed:
        raise HTTPException(status_code=429, detail=decision.reason)

    # Per-request copy: state and the web_search toggle never touch the
    # shared instance (see _spawn_request_assistant).
    assistant = _spawn_request_assistant(
        shared, enable_web_search=request.enable_web_search
    )

    history_for_api = [
        {"role": m.role, "content": m.content} for m in request.history
    ]

    def _sse(event: str, data: str) -> str:
        """Serialize one SSE frame. Multi-line data is split per spec."""
        lines = data.split("\n") if data else [""]
        framed = "\n".join(f"data: {ln}" for ln in lines)
        return f"event: {event}\n{framed}\n\n"

    def _generate() -> Any:
        start = _time.time()
        accumulated: list[str] = []
        recorded = False
        stream = assistant.stream_response(
            user_message=request.question,
            history=history_for_api,
            scoring_context=request.scoring_context,
        )

        def _record(error: str | None, exc: BaseException | None = None) -> dict[str, Any]:
            nonlocal recorded
            recorded = True
            return _record_ask_turn(
                limiter,
                session_id=session_id,
                assistant=assistant,
                question=request.question,
                elapsed_s=_time.time() - start,
                error=error,
                exc=exc,
                answer=(
                    "".join(accumulated)
                    if error is not None
                    else assistant.last_full_text or "".join(accumulated)
                ),
            )

        try:
            for chunk in stream:
                accumulated.append(chunk)
                # SSE clients render tokens as they arrive. Empty chunks
                # would still be valid frames; skip them to reduce noise.
                if chunk:
                    yield _sse("token", chunk)

            elapsed = _time.time() - start
            # Persist to the same ledger as the non-streaming path.
            usage_dict = _record(None)

            done_payload = {
                "model": assistant._model,
                "tool_calls": [
                    {
                        "tool": p.get("tool", ""),
                        "args": p.get("args") or {},
                        "result_summary": p.get("result_summary"),
                    }
                    for p in assistant.last_provenance
                ],
                "stripped_citation_markers": list(
                    assistant.last_stripped_markers or []
                ),
                "usage": {k: usage_dict.get(k, 0) for k in _USAGE_FIELDS},
                "session_id": session_id,
                "elapsed_s": round(elapsed, 3),
            }
            yield _sse("done", _json.dumps(done_payload))
        except AssistantUpstreamError as exc:
            logger.warning("Ask stream upstream failure: %s", exc)
            _record(f"{type(exc).__name__}: {exc}", exc)
            # Clients should treat any 'error' event as terminal regardless
            # of position in the stream.
            yield _sse(
                "error",
                _json.dumps(
                    {
                        "detail": _upstream_detail(exc),
                        "status": 502,
                        "upstream_status": getattr(exc, "status_code", None),
                    }
                ),
            )
        except GeneratorExit:
            # The client went away. The paid call may already have finished,
            # so the turn is still written to the ledger.
            stream.close()
            if not recorded:
                _record("client_disconnected")
            raise
        except Exception as exc:
            logger.exception("Ask stream failed")
            _record(f"{type(exc).__name__}: {exc}")
            yield _sse(
                "error",
                _json.dumps({"detail": "Internal assistant error", "status": 500}),
            )

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering so chunks flush immediately.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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
            "ask": "POST /ask",
            "ask_stream": "POST /ask/stream (Server-Sent Events)",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json",
        },
        "docs_url": "http://localhost:8000/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
