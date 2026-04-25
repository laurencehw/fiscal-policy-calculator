"""
Consolidated revenue-level validation scorecard.

Aggregates every category of validation runner (specialized TCJA, corporate,
credits, estate, payroll, AMT, PTC, capital gains, tax expenditures, plus
the generic fallback) into one scorecard with summary statistics. Powers
the ``/validation/scorecard`` API endpoint and the Streamlit Validation tab.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Callable

from .core import ValidationResult, validate_all
from .specialized import (
    validate_all_amt,
    validate_all_capital_gains,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_expenditures,
    validate_all_payroll,
    validate_all_ptc,
    validate_all_tcja,
)

# Order matters — specialized runners first (they produce calibrated results
# for the published presets), generic last (raw-parameter auto-population for
# remaining KNOWN_SCORES targets, where larger drift is expected).
DEFAULT_RUNNERS: dict[str, Callable[..., list[ValidationResult]]] = {
    "TCJA": validate_all_tcja,
    "Corporate": validate_all_corporate,
    "Credits": validate_all_credits,
    "Estate": validate_all_estate,
    "Payroll": validate_all_payroll,
    "AMT": validate_all_amt,
    "PTC": validate_all_ptc,
    "CapitalGains": validate_all_capital_gains,
    "Expenditures": validate_all_expenditures,
    "Generic": validate_all,
}


@dataclass
class ScorecardEntry:
    """Single policy's model-vs-official comparison."""

    category: str
    policy_id: str
    policy_name: str
    official_10yr_billions: float
    official_source: str
    benchmark_kind: str
    benchmark_date: str | None
    benchmark_url: str | None
    model_10yr_billions: float
    difference_billions: float
    percent_difference: float
    abs_percent_difference: float
    rating: str
    direction_match: bool
    known_limitations: list[str]
    notes: str

    @classmethod
    def from_result(cls, category: str, r: ValidationResult) -> "ScorecardEntry":
        return cls(
            category=category,
            policy_id=r.policy_id,
            policy_name=r.policy_name,
            official_10yr_billions=float(r.official_10yr),
            official_source=r.official_source,
            benchmark_kind=r.benchmark_kind,
            benchmark_date=r.benchmark_date,
            benchmark_url=r.benchmark_url,
            model_10yr_billions=float(r.model_10yr),
            difference_billions=float(r.difference),
            percent_difference=float(r.percent_difference),
            abs_percent_difference=float(abs(r.percent_difference)),
            rating=r.accuracy_rating,
            direction_match=bool(r.direction_match),
            known_limitations=list(r.known_limitations),
            notes=r.notes or "",
        )


@dataclass
class ScorecardSummary:
    """Aggregate accuracy statistics across all validation entries."""

    total_entries: int
    within_5pct: int
    within_10pct: int
    within_15pct: int
    within_20pct: int
    direction_match: int
    poor: int
    mean_abs_percent_difference: float
    median_abs_percent_difference: float
    ratings_breakdown: dict[str, int]
    by_category: dict[str, dict]
    entries: list[ScorecardEntry] = field(default_factory=list)


def _percentile(values: list[float], p: float) -> float:
    """Linear-interpolation percentile (numpy-free for trivial inputs)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (p / 100.0) * (len(sorted_vals) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_vals) - 1)
    weight = rank - lower
    return sorted_vals[lower] * (1 - weight) + sorted_vals[upper] * weight


def _category_summary(entries: list[ScorecardEntry]) -> dict:
    """Per-category roll-up (n, mean abs % error, ratings breakdown)."""
    if not entries:
        return {
            "n": 0,
            "mean_abs_percent_difference": 0.0,
            "within_15pct": 0,
            "ratings": {},
        }
    abs_diffs = [e.abs_percent_difference for e in entries]
    return {
        "n": len(entries),
        "mean_abs_percent_difference": sum(abs_diffs) / len(abs_diffs),
        "within_15pct": sum(1 for d in abs_diffs if d <= 15.0),
        "ratings": dict(Counter(e.rating for e in entries)),
    }


def compute_scorecard(
    runners: dict[str, Callable[..., list[ValidationResult]]] | None = None,
) -> ScorecardSummary:
    """Run every validation category and aggregate into a single scorecard.

    Args:
        runners: Optional override mapping ``category -> validate_all_*``
            callable. Each callable must accept ``verbose: bool`` and return
            ``list[ValidationResult]``. Defaults to :data:`DEFAULT_RUNNERS`.

    Returns:
        :class:`ScorecardSummary` with per-entry detail and aggregate
        statistics suitable for serialization.
    """
    runners = runners if runners is not None else DEFAULT_RUNNERS

    entries: list[ScorecardEntry] = []
    for category, runner in runners.items():
        results = runner(verbose=False)
        for r in results:
            entries.append(ScorecardEntry.from_result(category, r))

    abs_diffs = [e.abs_percent_difference for e in entries]
    ratings = Counter(e.rating for e in entries)

    by_cat: dict[str, dict] = {}
    for cat in runners.keys():
        cat_entries = [e for e in entries if e.category == cat]
        by_cat[cat] = _category_summary(cat_entries)

    return ScorecardSummary(
        total_entries=len(entries),
        within_5pct=sum(1 for d in abs_diffs if d <= 5.0),
        within_10pct=sum(1 for d in abs_diffs if d <= 10.0),
        within_15pct=sum(1 for d in abs_diffs if d <= 15.0),
        within_20pct=sum(1 for d in abs_diffs if d <= 20.0),
        direction_match=sum(1 for e in entries if e.direction_match),
        poor=sum(1 for e in entries if e.rating == "Poor"),
        mean_abs_percent_difference=(sum(abs_diffs) / len(abs_diffs)) if abs_diffs else 0.0,
        median_abs_percent_difference=_percentile(abs_diffs, 50.0),
        ratings_breakdown=dict(ratings),
        by_category=by_cat,
        entries=entries,
    )


def scorecard_to_dict(summary: ScorecardSummary) -> dict:
    """Serialize a scorecard to a plain dict suitable for JSON / Pydantic."""
    payload = asdict(summary)
    # asdict already converts nested dataclasses; nothing else to do.
    return payload


@lru_cache(maxsize=1)
def cached_default_scorecard() -> ScorecardSummary:
    """Memoized default scorecard.

    The full scorecard takes ~50ms because it runs every specialized
    validator (TCJA, Corporate, Credits, Estate, Payroll, AMT, PTC,
    CapitalGains, Expenditures) plus the generic fallback. The result
    is static for the lifetime of the process — the underlying CBO
    score database, validation runners, and engine all live in code.

    Streamlit reruns every tab body on every interaction (clicks,
    sidebar widget changes), and the API endpoint is publicly reachable,
    so calling ``compute_scorecard()`` directly on each request would
    add seconds of latency or amplify any DoS attempt against
    ``/validation/scorecard``. This cached entry point fixes both.

    Use ``compute_scorecard(runners=...)`` directly when you want a
    one-off run with stub runners (e.g., in tests).
    """
    return compute_scorecard()


def reset_scorecard_cache() -> None:
    """Clear the memoized default scorecard. Mainly for tests that
    monkeypatch the underlying validators."""
    cache_clear = getattr(cached_default_scorecard, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


__all__ = [
    "DEFAULT_RUNNERS",
    "ScorecardEntry",
    "ScorecardSummary",
    "cached_default_scorecard",
    "compute_scorecard",
    "reset_scorecard_cache",
    "scorecard_to_dict",
]
