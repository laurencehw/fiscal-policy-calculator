"""Pinned headline counts for the validation scorecard.

**Why this file exists.** The page footer prints one clause — *"N policies
benchmarked against published scores"* — and ``N`` is
:attr:`ScorecardSummary.published_entries`. Obtaining it used to mean
*computing the whole scorecard*: every specialized validator over all 81 rows,
on the critical path of the very first script run. Measured at **7.65s of the
landing page's 8.40s first run** (91%) on the tree that shipped this file; see
``planning/memos/COLD_START.md`` §3 and §5. It is ``lru_cache``d process-wide,
so exactly one visitor per container paid it — the cold-start visitor.

**Why it is a generated artifact and not a constant.** The clause is a
*validation claim*. A hand-typed number would be a claim about coverage that
nothing checks, which is the failure mode the zero-fallback in
:func:`fiscal_model.ui.helpers.validated_policy_count` already exists to
prevent. So the number is generated from the live scorecard by
``scripts/build_validation_headline.py`` and pinned by
``tests/test_validation_headline.py``, which recomputes the scorecard and fails
if the two disagree. That is the same generate-then-pin pattern
``scripts/fit_outlay_rates.py`` + ``tests/test_spending_outlays.py`` use for the
outlay profiles, and ``scripts/derive_policy_tags.py`` for the policy tags.

**No timestamp is recorded, deliberately.** The payload is a pure function of
the tree, so regenerating an unchanged tree must produce a byte-identical file;
a "generated at" field would churn the diff on every run and could not be
checked by the test that makes the number trustworthy.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

#: The committed artifact. Lives beside the other generated validation data
#: files (CBO options, the P.L. 119-21 line items, the corporate rate scores).
HEADLINE_PATH: Path = (
    Path(__file__).resolve().parents[1]
    / "data_files"
    / "validation"
    / "headline_counts.json"
)

#: Written into the file so a reader who opens it knows what regenerates it.
GENERATOR = "scripts/build_validation_headline.py"

#: ``ScorecardEntry.category`` for the pre-registered out-of-sample battery —
#: the rows ``cold_holdout.py`` reports as Tier 1.
GENERIC_CATEGORY = "Generic"

_NOTE = (
    "Generated file - do not hand-edit. The footer's benchmark count is a "
    "validation claim, so it is derived from the live scorecard rather than "
    "typed. Regenerate with: python " + GENERATOR
)


def build_payload(summary: Any) -> dict[str, Any]:
    """Assemble the pinned payload from a computed :class:`ScorecardSummary`.

    Only counts, never errors or model figures: this artifact answers "how many
    rows are benchmarked against a published figure", and nothing that moves
    when a *model* number moves belongs in it.
    """
    provenance = dict(getattr(summary, "provenance_breakdown", {}) or {})
    entries = tuple(getattr(summary, "entries", ()) or ())
    return {
        "_note": _NOTE,
        "generated_by": GENERATOR,
        "published_entries": int(summary.published_entries),
        "total_entries": int(summary.total_entries),
        "model_estimate_entries": int(summary.model_estimate_entries),
        "unclassified_entries": int(provenance.get("unclassified", 0)),
        # How many rows are the pre-registered out-of-sample tier. A **count**,
        # like the four above it, so it obeys this payload's own rule: it moves
        # when a case is registered or retired and not when a model number
        # moves. The tier's *errors* deliberately stay out — those are exactly
        # what "nothing that moves when a model number moves" excludes, and any
        # surface wanting them has to compute them.
        "out_of_sample_entries": sum(
            1 for e in entries if str(getattr(e, "category", "")) == GENERIC_CATEGORY
        ),
    }


def write_payload(payload: dict[str, Any], path: Path | None = None) -> Path:
    """Write the artifact, stably formatted, and drop the read cache."""
    target = path or HEADLINE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    reset_cache()
    return target


@lru_cache(maxsize=1)
def load_headline() -> dict[str, Any] | None:
    """Read the committed artifact once per process, or ``None`` if unreadable.

    Cheap by construction: stdlib ``json`` over a file of a handful of keys. It
    must stay that way — the whole point is that the footer's clause costs
    nothing on the first script run.
    """
    try:
        data = json.loads(HEADLINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _pinned_count(key: str) -> int | None:
    data = load_headline()
    if data is None:
        return None
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def pinned_published_entries() -> int | None:
    """The pinned ``published_entries``, or ``None`` if it cannot be read.

    ``None`` rather than 0: "the artifact is missing" and "the scorecard
    benchmarks nothing" are different states, and only the caller knows which
    of them warrants dropping the clause.
    """
    return _pinned_count("published_entries")


def pinned_out_of_sample_entries() -> int | None:
    """How many rows are the pre-registered out-of-sample tier; ``None`` if unread.

    Same contract as :func:`pinned_published_entries`, and the same reason for
    existing: a surface that names the tier's size must not type the number,
    and must not pay for the scorecard to learn it.
    """
    return _pinned_count("out_of_sample_entries")


def reset_cache() -> None:
    """Clear the memoized read. For tests and for the generator script."""
    cache_clear = getattr(load_headline, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


__all__ = [
    "GENERATOR",
    "GENERIC_CATEGORY",
    "HEADLINE_PATH",
    "build_payload",
    "load_headline",
    "pinned_out_of_sample_entries",
    "pinned_published_entries",
    "reset_cache",
    "write_payload",
]
