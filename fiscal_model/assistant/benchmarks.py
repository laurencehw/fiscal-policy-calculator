"""
Benchmark anchoring for the Ask assistant's capability gate.

``score_hypothetical_policy`` can run the app's engine on parameters nobody
ever validated. Before the redesign it returned that raw number with an
advisory string attached, which the model then quoted as if it were a score.
This module supplies the missing half: for a requested (policy family, rate
change, income threshold) it finds the **nearest officially scored
benchmark(s)** in :mod:`fiscal_model.validation.cbo_scores` and derives a
clearly-labelled linear estimate from them.

The interpolation rule, stated once so it can be argued with:

1. Only benchmarks in the same policy family are candidates, and only those
   that record the parameter (``rate_change``) the request varies.
2. Candidates whose rate change has the **same sign** as the request are
   preferred. A rate cut and a rate increase are scored off different bases
   (the 2017 corporate cut started from a 35% rate; the Biden increase starts
   from 21%), so mixing them across zero produces a worse anchor than
   scaling within one direction.
3. Where the threshold matters (individual income, capital gains), the
   candidates closest to the requested threshold win — measured on a log
   scale, because \\$400K and \\$500K are neighbours while \\$0 and \\$1M are not.
4. If two surviving anchors bracket the requested rate, interpolate linearly
   between them. Otherwise scale the single nearest anchor **through the
   origin** — a zero rate change raises zero revenue, so the origin is itself
   a valid anchor point.

Worked example (the acceptance case in the redesign plan §9.3): a 21% -> 25%
corporate rate is ``rate_change=+0.04``. Two same-sign corporate anchors
bracket it — CBO's Option 64 (21% -> 22%) at -\\$136B and Treasury's
21% -> 28% at -\\$1,347B — so rule 4 interpolates:
``-136 + (-1347 + 136) * (0.04-0.01)/(0.07-0.01) = -$741B``. That is the number
the answer must be anchored to, rather than whatever the engine happens to
return. (Before the CBO Options battery supplied the +1pp anchor, the same
request fell back on rule 4's second clause and scaled the 28% anchor through
the origin to -\\$770B.)
"""

from __future__ import annotations

import math
from typing import Any

from fiscal_model.validation.cbo_scores import KNOWN_SCORES

# Tool ``policy_type`` -> the ``CBOScore.policy_type`` family it should be
# anchored against. Families absent from this map have no parameterised
# benchmark in the database (payroll, estate, spending): the gate says so
# rather than inventing an anchor.
_FAMILY_MAP: dict[str, str] = {
    "income_tax": "income_tax",
    "corporate_tax": "corporate_tax",
    "capital_gains_tax": "capital_gains_tax",
}

# Families where the income threshold selects between structurally different
# bases (a top-rate change is not a scaled all-filers change).
_THRESHOLD_SENSITIVE = {"income_tax", "capital_gains_tax"}

# Beyond this ratio the engine and the official anchors are telling different
# stories; the acceptance criterion is "within ~2x, never 5x".
DIVERGENCE_LIMIT = 2.0


def _log_threshold(value: float | None) -> float:
    """Compress dollar thresholds so \\$400K and \\$500K read as neighbours."""
    return math.log10(max(float(value or 0.0), 0.0) + 1.0)


def _anchor_payload(score: Any) -> dict[str, Any]:
    return {
        "policy_id": score.policy_id,
        "name": score.name,
        "official_ten_year_billions": float(score.ten_year_cost),
        "rate_change": score.rate_change,
        "income_threshold": score.income_threshold,
        "source": score.source.value,
        "source_date": score.source_date,
        "source_url": score.source_url,
        "budget_window": score.budget_window,
    }


def candidate_anchors(
    policy_type: str,
    rate_change: float,
    income_threshold: float | None = None,
) -> list[Any]:
    """Return the ordered shortlist of ``CBOScore`` anchors for a request.

    Ordered nearest-first on rate change, after the family / sign / threshold
    filters described in the module docstring. Empty when the family has no
    parameterised benchmark.
    """
    family = _FAMILY_MAP.get(policy_type)
    if family is None or not rate_change:
        return []

    candidates = [
        score
        for score in KNOWN_SCORES.values()
        if score.policy_type == family and score.rate_change
    ]
    if not candidates:
        return []

    same_sign = [
        score
        for score in candidates
        if (score.rate_change > 0) == (rate_change > 0)
    ]
    if same_sign:
        candidates = same_sign

    if family in _THRESHOLD_SENSITIVE:
        target = _log_threshold(income_threshold)
        distances = {
            score.policy_id: abs(_log_threshold(score.income_threshold) - target)
            for score in candidates
        }
        nearest = min(distances.values())
        candidates = [
            score for score in candidates if distances[score.policy_id] <= nearest + 1e-9
        ]

    candidates.sort(key=lambda s: abs(float(s.rate_change) - rate_change))
    return candidates


def interpolate_from_anchors(
    anchors: list[Any],
    rate_change: float,
) -> dict[str, Any] | None:
    """Derive a labelled linear estimate from an ordered anchor shortlist."""
    if not anchors or not rate_change:
        return None

    primary = anchors[0]
    p_rate = float(primary.rate_change)
    p_cost = float(primary.ten_year_cost)

    # Two anchors that bracket the request: interpolate between them.
    for other in anchors[1:]:
        o_rate = float(other.rate_change)
        lo, hi = sorted((p_rate, o_rate))
        if lo <= rate_change <= hi and not math.isclose(p_rate, o_rate):
            o_cost = float(other.ten_year_cost)
            weight = (rate_change - p_rate) / (o_rate - p_rate)
            estimate = p_cost + (o_cost - p_cost) * weight
            return {
                "estimate_ten_year_billions": round(estimate, 1),
                "method": (
                    f"linear interpolation between {primary.name} "
                    f"({p_rate:+.3f} -> ${p_cost:,.0f}B) and {other.name} "
                    f"({o_rate:+.3f} -> ${o_cost:,.0f}B)"
                ),
                "anchors_used": [primary.policy_id, other.policy_id],
            }

    estimate = p_cost * (rate_change / p_rate)
    return {
        "estimate_ten_year_billions": round(estimate, 1),
        "method": (
            f"linear scaling through the origin from {primary.name} "
            f"({p_rate:+.3f} -> ${p_cost:,.0f}B), applied at {rate_change:+.3f}"
        ),
        "anchors_used": [primary.policy_id],
    }


def build_capability_gate(
    *,
    policy_type: str,
    rate_change: float,
    income_threshold: float | None,
    engine_estimate_billions: float,
    calibrated: bool,
    max_anchors: int = 2,
) -> dict[str, Any]:
    """Return the benchmark-anchored payload for a hypothetical score.

    Keys returned:

    ``estimate_basis``
        ``official_benchmark_interpolation`` | ``calibrated_module`` |
        ``uncalibrated_model_only``.
    ``headline_estimate_billions``
        The number the assistant should quote.
    ``uncalibrated_model_estimate_billions``
        The raw engine run, present whenever the path is not calibrated, so it
        can be reported *alongside* the anchor rather than as the answer.
    ``official_benchmark_anchors`` / ``benchmark_interpolation``
        The official scores and the labelled arithmetic that got from them to
        the headline.
    """
    anchors = candidate_anchors(policy_type, rate_change, income_threshold)[:max_anchors]
    interpolation = interpolate_from_anchors(anchors, rate_change)
    payload: dict[str, Any] = {
        "official_benchmark_anchors": [_anchor_payload(a) for a in anchors],
        "benchmark_interpolation": interpolation,
    }

    if interpolation is None:
        payload["estimate_basis"] = (
            "calibrated_module" if calibrated else "uncalibrated_model_only"
        )
        payload["headline_estimate_billions"] = round(float(engine_estimate_billions), 1)
        if not calibrated:
            payload["uncalibrated_model_estimate_billions"] = round(
                float(engine_estimate_billions), 1
            )
            payload["capability_note"] = (
                "No officially scored benchmark exists for this policy family "
                "and parameter, so there is nothing to anchor against. Present "
                "the number as an uncalibrated model estimate, directional "
                "only, and say that no official score covers this case."
            )
        else:
            payload["capability_note"] = (
                "Scored through a calibrated module; no parameterised official "
                "benchmark was available for a side-by-side anchor."
            )
        return payload

    anchored = float(interpolation["estimate_ten_year_billions"])
    engine = float(engine_estimate_billions)
    ratio = None
    if anchored:
        ratio = abs(engine / anchored)
        payload["engine_vs_anchor_ratio"] = round(ratio, 2)

    diverges = ratio is not None and (
        ratio > DIVERGENCE_LIMIT or ratio < 1.0 / DIVERGENCE_LIMIT
    )

    if calibrated and not diverges:
        payload["estimate_basis"] = "calibrated_module"
        payload["headline_estimate_billions"] = round(engine, 1)
        payload["capability_note"] = (
            "Scored through a calibrated module whose result agrees with the "
            "official anchor(s) within a factor of "
            f"{DIVERGENCE_LIMIT:.0f}. Quote the module figure and cite the "
            "official anchor(s) alongside it."
        )
        return payload

    payload["estimate_basis"] = "official_benchmark_interpolation"
    payload["headline_estimate_billions"] = round(anchored, 1)
    payload["uncalibrated_model_estimate_billions"] = round(engine, 1)
    if diverges:
        payload["capability_warning"] = (
            f"The engine run (${engine:,.0f}B) differs from the "
            f"benchmark-anchored estimate (${anchored:,.0f}B) by more than a "
            f"factor of {DIVERGENCE_LIMIT:.0f}. Answer from the anchors."
        )
    payload["capability_note"] = (
        "This parameterisation has no validated score of its own. Answer with "
        "the benchmark-anchored estimate, name the official anchor(s) and the "
        "arithmetic used, and mention the raw engine figure only as an "
        "uncalibrated model estimate."
    )
    return payload


__all__ = [
    "DIVERGENCE_LIMIT",
    "build_capability_gate",
    "candidate_anchors",
    "interpolate_from_anchors",
]
