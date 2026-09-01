"""
Provenance labels for validation benchmarks.

Phase E of ``planning/VALIDATION_EXPANSION.md`` §5.1 asks a question the
scorecard could not previously answer: *where did each calibrated target
actually come from?* "Validated against CBO" is doing a lot of work when
17 of the 29 pre-Phase-E targets are exact round hundred-scale numbers
(450, 350, -1100, -2700, -3200, ...) with no table reference — those are
summaries, not line items, and an error against them is partly target
error.

Three labels, plus an explicit "we do not know" bucket:

``line_item``
    The target is a specific row in a cited document (a JCX table, a CBO
    cost-estimate table, a Green Book revenue line). The strongest kind of
    benchmark: the number and the document that states it are both known.
``secondhand``
    The target came from a summary, a press description, or a rounded
    headline figure. Usually a round hundred-scale number attributed to an
    agency but not to a table.
``model_estimate``
    No official score exists for this policy shape. The "benchmark" is a
    model or illustrative figure, so scoring against it measures internal
    consistency, not accuracy. These are kept as *illustrations* and are
    reported separately from the calibrated count (plan §5.2).
``unclassified``
    The record does not unambiguously fall into any of the above from its
    own ``official_source`` / ``benchmark_url``. Deliberately not guessed:
    promoting one of these to ``line_item`` requires finding the table.

Provenance is orthogonal to accuracy. A ``line_item`` benchmark can still
be missed badly, and a ``secondhand`` one can be matched exactly (often
*because* the module carries a constant fit to it).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

LINE_ITEM = "line_item"
SECONDHAND = "secondhand"
MODEL_ESTIMATE = "model_estimate"
UNCLASSIFIED = "unclassified"

#: Every label the scorecard can emit, in reporting order.
PROVENANCE_LEVELS: tuple[str, ...] = (
    LINE_ITEM,
    SECONDHAND,
    MODEL_ESTIMATE,
    UNCLASSIFIED,
)

#: Revenue-scorecard entries the plan (§5.2) names as *not* published
#: benchmarks. They stay in the scorecard as labelled illustrations but are
#: excluded from the headline calibrated count.
NON_PUBLISHED_BENCHMARK_IDS: frozenset[str] = frozenset(
    {
        "tcja_no_salt_cap",  # "~$1.1T added" — no published score for this variant
        "tcja_rates_only",  # illustrative decomposition of the full extension
        "trump_corporate_15",  # scenario notes: "expected estimate derived from model"
        "eliminate_estate_tax",  # scenario source literally reads "Model estimate"
    }
)

#: The other two §5.2 entries live in ``distributional_validation.py`` and are
#: keyed by benchmark *name*, not policy id. Listed here so the plan's "six
#: non-published benchmarks" is auditable from one place.
NON_PUBLISHED_DISTRIBUTIONAL_BENCHMARKS: tuple[str, ...] = (
    "Corporate Rate Increase 21%->28%",  # TPC_CORPORATE_RATE_INCREASE
    "Capital Gains Rate Increase",  # TPC_CAPITAL_GAINS_INCREASE
)

# Source strings that say, in the record's own words, that the target is not a
# published score.
_MODEL_ESTIMATE_SOURCE = re.compile(
    r"model estimate|derived from model|estimate derived|cbo-style|illustrative",
    re.IGNORECASE,
)

# ``round hundred-scale`` in the plan's sense: 450, 350, -1100, -2700, -3200.
# Those are multiples of 50 at hundred-billion scale, not strictly of 100.
_ROUND_STEP = 50.0


def is_round_hundred_scale(value: float) -> bool:
    """Return whether a 10-year target is a round hundred-scale figure.

    The plan's tell for a secondhand target: a number that ends in 00 or 50
    at billions scale. A real table row is almost never that round.
    """
    return abs(value) >= _ROUND_STEP and abs(value) % _ROUND_STEP == 0.0


def _is_deep_link(url: str | None) -> bool:
    """Return whether a URL points at a specific document, not a bare domain.

    ``https://www.cbo.gov/publication/60271`` → True.
    ``https://www.taxpolicycenter.org/`` → False (a homepage is not a cite).
    """
    if not url:
        return False
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return False
    return bool(parsed.path.strip("/"))


def classify_provenance(
    *,
    policy_id: str,
    official_source: str,
    benchmark_url: str | None = None,
    official_10yr: float = 0.0,
    benchmark_kind: str | None = None,
    declared: str | None = None,
) -> str:
    """Return the provenance label for one benchmark record.

    A runner that knows its own provenance passes ``declared`` and that wins.
    Otherwise the label is inferred *only* from what the record already
    states — its source string, its URL, and the roundness of its target —
    so no judgement is smuggled in beyond the rules documented above.
    """
    if declared:
        if declared not in PROVENANCE_LEVELS:
            raise ValueError(
                f"Unknown provenance {declared!r} for {policy_id!r}; "
                f"expected one of {PROVENANCE_LEVELS}."
            )
        return declared

    if policy_id in NON_PUBLISHED_BENCHMARK_IDS:
        return MODEL_ESTIMATE
    if _MODEL_ESTIMATE_SOURCE.search(official_source or ""):
        return MODEL_ESTIMATE
    if benchmark_kind and _MODEL_ESTIMATE_SOURCE.search(benchmark_kind):
        return MODEL_ESTIMATE
    if _is_deep_link(benchmark_url):
        return LINE_ITEM
    if is_round_hundred_scale(official_10yr):
        return SECONDHAND
    return UNCLASSIFIED


__all__ = [
    "LINE_ITEM",
    "MODEL_ESTIMATE",
    "NON_PUBLISHED_BENCHMARK_IDS",
    "NON_PUBLISHED_DISTRIBUTIONAL_BENCHMARKS",
    "PROVENANCE_LEVELS",
    "SECONDHAND",
    "UNCLASSIFIED",
    "classify_provenance",
    "is_round_hundred_scale",
]
