"""How far out this number is likely to be — read off the out-of-sample tier.

A headline needs a band, and until Wave C's H4 it got one of two that carried no
information about accuracy:

* **The ETI ±0.1 sweep** (``ui/tabs/results_summary._sensitivity_band``). For a
  plain ``TaxPolicy`` the headline is ``0.875 × static`` and the sweep's width is
  ``0.8 × 0.125 × static``, so the band is **0.1 / 0.875 = 11.43% of the
  headline for every policy, every rate, every threshold** — Flat Tax Reform at
  +$6,239.4B and the Medicare surcharge at −$426.6B were handed the identical
  ribbon. Where a module zeroes the behavioural offset it fell through to the
  engine's own uncertainty path, which is a second fixed fraction (38.0% for
  climate and pharma, 45.6% for estate, credits and payroll, 46.8–47.1% for
  TCJA, AMT and PTC). Both are restatements of a parameter, printed as if they
  were statements about accuracy.
* **The category ``ConfidenceBand``**, computed over ``summary.by_category``,
  which mixes fitted bookkeeping with unfitted reconstructions under one rating
  word — ``Estate n=3 4.7% "Excellent"``, ``Credits n=3 3.2% "Excellent"`` — and
  which fell back to ``Generic`` for every unmapped preset area. ``Generic``
  **is** the Tier 1 tier, so **31 of 56 shipped runs printed "±14.7% across 26
  calibrated runs"**, including every tariff, pharma, international, enforcement
  and climate preset, none of which has a single Tier 1 row behind it. The worst
  instance was on a user-facing surface: *International Reference Pricing* drew a
  ±14.7% band while its own scorecard row is **701.0%** from its target.

What replaces them is the **error distribution of the policy's own class**, read
off the **26 pre-registered out-of-sample rows and nothing else**, keyed by the
same routing the CI gate uses (``validation/policy_classes.py``, imported rather
than forked). Fitted rows and reconstructions are excluded by construction:
agreement in those tiers is bookkeeping or a target's provenance, and neither is
evidence about a number the user just produced.

**Two half-widths and a measured coverage.** The inner half-width is the class's
**mean** absolute percent error — the statistic ``HIGH_STAKES_ACCURACY.md`` §2's
table, ``cold_holdout.py --max-class-mean-error``'s eight ceilings and CLAUDE.md
all quote, and the only one estimable at n = 1–6. The outer half-width is the
class's **worst** row. The share of the class's own rows that falls inside the
inner band is **computed, not assumed**: it is not ≥ 50% everywhere, and
``ordinary rate change`` covers **1 of 4** because its mean is dragged by a
24.5% row while its median is 16.4%. Both statistics are computed on each row's
error *as reported* — rounded to one decimal, the figure ``cold_holdout.py``
prints — so the app cannot sit a tenth of a point from the published record.

**A policy whose class has no Tier 1 row gets no band and says why.** That is
two thirds of the shipped catalog, and it is the measurement rather than a gap.
Where such a policy has a scorecard row of any tier, that row's own error and
tier print beside the absence — read from ``ui/preset_validation``, which
already knows them and shares the one ``cached_default_scorecard``
materialisation this module also uses. Nothing here recomputes the scorecard.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from fiscal_model.validation.policy_classes import (
    POLICY_CLASS_LABELS,
    classify_policy,
    classify_policy_object,
    no_tier1_class_reason,
)

# Map preset categories from PRESET_POLICIES (`_preset_category`) to scorecard
# categories from compute_scorecard. These no longer carry an accuracy claim —
# that moved onto the Tier 1 classes above. They still route the per-category
# **limitations** list and the holdout-availability label, which are facts about
# a category rather than about a model's error.
PRESET_AREA_TO_SCORECARD_CATEGORY: dict[str, str] = {
    "TCJA / Individual": "TCJA",
    "Corporate": "Corporate",
    "Tax Credits": "Credits",
    "Estate Tax": "Estate",
    "Payroll / SS": "Payroll",
    "AMT": "AMT",
    "ACA / Healthcare": "PTC",
    "Tax Expenditures": "Expenditures",
    "Income Tax": "Generic",
    "International Tax": "Generic",
    "IRS Enforcement": "Generic",
    "Drug Pricing": "Generic",
    "Trade / Tariffs": "Generic",
    "Climate / Energy": "Generic",
    # H12's demoted group (`app_data.ILLUSTRATIVE_GROUP_LABEL`, spelled out
    # here rather than imported so a validation module keeps no dependency on
    # the app's preset data; `tests/test_illustrative_group.py` pins the two
    # equal). "Generic" is what all five members already resolved to through
    # `Drug Pricing` and `IRS Enforcement`, so the limitations list and the
    # holdout label they show are unchanged — the entry is here because
    # `test_mapping_dicts_cover_every_preset_area` requires a new area to be a
    # decision rather than a silent fallback, which is the right requirement.
    "Illustrative - unfitted reconstructions": "Generic",
}


# Map raw PolicyType enum values to scorecard categories. Same standing as the
# map above: limitations and holdout status, never an accuracy figure.
POLICY_TYPE_TO_SCORECARD_CATEGORY: dict[str, str] = {
    "corporate_tax": "Corporate",
    "estate_tax": "Estate",
    "payroll_tax": "Payroll",
    "tax_credit": "Credits",
    "tax_deduction": "Expenditures",
    "capital_gains_tax": "CapitalGains",
    "income_tax": "Generic",
    "excise_tax": "Generic",
    "discretionary_defense": "Generic",
    "discretionary_nondefense": "Generic",
    "mandatory_spending": "Generic",
    "infrastructure": "Generic",
    "social_security": "Payroll",
    "medicare": "Generic",
    "medicaid": "Generic",
    "unemployment": "Generic",
    "snap": "Generic",
    "other_transfer": "Generic",
}


#: Raw ``policy_type`` string -> Tier 1 class, for the one caller that has a
#: type string and no policy object: the bill tracker's LLM-extracted provisions
#: (``ui/tabs/bill_tracker._render_bill_calibration_band``). Deliberately
#: **partial**: a type with no unambiguous Tier 1 class is absent, and absence
#: means no band. ``income_tax`` resolves to the ordinary-rate class because
#: that is what ``DEFAULT_ORDINARY_INCOME_BASE`` gives a policy nobody told
#: otherwise (PR #142); an extractor cannot know a bill's statutory base.
POLICY_TYPE_TO_TIER1_CLASS: dict[str, str] = {
    "corporate_tax": "corporate",
    "payroll_tax": "payroll",
    "social_security": "payroll",
    "capital_gains_tax": "capital_gains",
    "tax_deduction": "tax_expenditure",
    "income_tax": "ordinary_rate_change",
    "discretionary_defense": "discretionary_spending",
    "discretionary_nondefense": "discretionary_spending",
}


_ALL_RESULTS_LIMITATIONS = [
    "holdout labels follow the locked post-2026-05-02 regression protocol; they are not retroactive historical out-of-sample claims.",
]


# ---------------------------------------------------------------------------
# The band
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmpiricalBand:
    """One policy class's observed out-of-sample error distribution.

    Every field is a count or a percentage read off the 26 pre-registered Tier 1
    rows. Nothing here is fitted, chosen, or rounded to look tidy.
    """

    policy_class: str
    class_label: str
    n: int
    #: Inner half-width: the class's mean absolute percent error.
    mean_abs_pct_error: float
    #: Carried beside the mean so a reader can see the skew. Not the band.
    median_abs_pct_error: float
    #: Outer half-width: the class's worst row.
    max_abs_pct_error: float
    #: How many of ``n`` fall inside the inner band. Computed, not assumed.
    rows_inside_mean_band: int
    worst_policy_id: str
    policy_ids: tuple[str, ...]

    @property
    def is_single_row(self) -> bool:
        """One observation is not a distribution, and the caption must say so."""
        return self.n <= 1

    def inner_dollars(self, point_estimate: float) -> tuple[float, float]:
        half = abs(point_estimate) * (self.mean_abs_pct_error / 100.0)
        return point_estimate - half, point_estimate + half

    def outer_dollars(self, point_estimate: float) -> tuple[float, float]:
        half = abs(point_estimate) * (self.max_abs_pct_error / 100.0)
        return point_estimate - half, point_estimate + half


def _round1(value: float) -> float:
    """One decimal — the resolution ``cold_holdout.py`` reports and docs quote."""
    return round(float(value), 1)


@lru_cache(maxsize=1)
def tier1_class_bands() -> dict[str, EmpiricalBand]:
    """The eight bands, materialised once per process from the live scorecard.

    Reads ``cached_default_scorecard`` — the same one materialisation the
    Validation tab, the API endpoint and ``ui/preset_validation`` share — and
    keeps only the out-of-sample tier, bucketed by
    :func:`~fiscal_model.validation.policy_classes.classify_policy`.
    """
    from fiscal_model.validation import cached_default_scorecard
    from fiscal_model.validation.scorecard import GENERIC_CATEGORY

    summary = cached_default_scorecard()
    buckets: dict[str, list[tuple[float, str]]] = {}
    for entry in summary.entries:
        if entry.category != GENERIC_CATEGORY:
            continue
        slug = classify_policy(entry.policy_id)
        if slug not in POLICY_CLASS_LABELS:
            # An unclassified Tier 1 row is a gate failure, not a band. It is
            # dropped here and `cold_holdout.py --max-class-mean-error` is what
            # fails on it, so a ninth class cannot arrive un-gated by way of a
            # silently widened band.
            continue
        buckets.setdefault(slug, []).append(
            (_round1(entry.abs_percent_difference), entry.policy_id)
        )

    out: dict[str, EmpiricalBand] = {}
    for slug, rows in buckets.items():
        rows.sort()
        errs = [err for err, _ in rows]
        mid = len(errs) // 2
        median = errs[mid] if len(errs) % 2 else (errs[mid - 1] + errs[mid]) / 2
        mean = _round1(sum(errs) / len(errs))
        worst = _round1(errs[-1])
        out[slug] = EmpiricalBand(
            policy_class=slug,
            class_label=POLICY_CLASS_LABELS[slug],
            n=len(errs),
            mean_abs_pct_error=mean,
            median_abs_pct_error=_round1(median),
            max_abs_pct_error=worst,
            rows_inside_mean_band=sum(1 for err in errs if err <= mean),
            worst_policy_id=rows[-1][1],
            policy_ids=tuple(policy_id for _, policy_id in rows),
        )
    return out


def reset_confidence_cache() -> None:
    """Clear the memoized band index. Mainly for tests."""
    cache_clear = getattr(tier1_class_bands, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def band_for_policy_class(policy_class: str | None) -> EmpiricalBand | None:
    """The band for one Tier 1 class slug, or ``None``."""
    if not policy_class:
        return None
    try:
        return tier1_class_bands().get(policy_class)
    except Exception:  # pragma: no cover — a scorecard failure must not render
        return None


def band_for_policy_type(policy_type: str | None) -> EmpiricalBand | None:
    """The band implied by a raw ``policy_type`` string, or ``None``.

    For the bill tracker, which has an extractor's type label and no policy
    object. Returns ``None`` for every type with no unambiguous Tier 1 class —
    which is most of them, and is the honest answer for a demo-grade extraction.
    """
    if not policy_type:
        return None
    return band_for_policy_class(POLICY_TYPE_TO_TIER1_CLASS.get(policy_type))


def band_for_policy(policy: Any) -> EmpiricalBand | None:
    """The band for a live policy object, or ``None`` when its class has no row."""
    return band_for_policy_class(classify_policy_object(policy))


def format_band_caption(
    band: EmpiricalBand | None,
    *,
    point_estimate: float | None = None,
    reason: str = "",
) -> str:
    """One or two sentences: what the band is, and what it is not.

    Never a "validated within X%" claim — the number is always attached to its
    class, its ``n`` and its tier.
    """
    if band is None:
        base = "No out-of-sample band"
        if reason:
            base += f": {reason}"
        return (
            base
            + ". The 26 pre-registered Tier 1 rows are the only tier that "
            "measures this model's accuracy, and none of them scores a policy "
            "of this kind."
        )

    if band.is_single_row:
        head = (
            f"Out-of-sample accuracy, {band.class_label}: the single "
            f"pre-registered row of this class misses its published score by "
            f"{band.mean_abs_pct_error:.1f}% (n=1 — one observation, not a "
            f"distribution)."
        )
    else:
        falls = "falls" if band.rows_inside_mean_band == 1 else "fall"
        head = (
            f"Out-of-sample accuracy, {band.class_label}: {band.n} "
            f"pre-registered rows miss their published scores by "
            f"{band.mean_abs_pct_error:.1f}% on average "
            f"(median {band.median_abs_pct_error:.1f}%), worst "
            f"{band.max_abs_pct_error:.1f}% — {band.rows_inside_mean_band} of "
            f"the {band.n} {falls} inside the average."
        )

    if point_estimate is not None:
        low, high = band.inner_dollars(point_estimate)
        outer_low, outer_high = band.outer_dollars(point_estimate)
        head += f" On this figure that is ${low:+,.1f}B to ${high:+,.1f}B"
        if band.max_abs_pct_error > band.mean_abs_pct_error:
            head += (
                f" typical, ${outer_low:+,.1f}B to ${outer_high:+,.1f}B at the "
                f"worst row."
            )
        else:
            # One row, or a class whose worst row *is* its mean. Printing the
            # same interval twice under two labels would read as two findings.
            head += "."

    return head + (
        " Read off the out-of-sample tier only — not the calibrated tiers, "
        "whose agreement is by construction. It is the observed spread of this "
        "model against published scores for this class of policy, not a "
        "confidence interval."
    )


# ---------------------------------------------------------------------------
# Per-category facts that are not accuracy claims
# ---------------------------------------------------------------------------


def _category_for_preset_area(area: str | None) -> str:
    if not area:
        return "Generic"
    return PRESET_AREA_TO_SCORECARD_CATEGORY.get(area, "Generic")


def _category_for_policy_type(policy_type: str | None) -> str:
    if not policy_type:
        return "Generic"
    return POLICY_TYPE_TO_SCORECARD_CATEGORY.get(policy_type, "Generic")


def category_for_result(
    *, policy_name: str | None = None, policy: Any = None
) -> str:
    """Scorecard category for a run — for limitations and holdout status only."""
    if policy_name:
        try:
            from fiscal_model.app_data import PRESET_POLICIES
            from fiscal_model.ui.policy_input_presets import _preset_category

            preset = PRESET_POLICIES.get(policy_name)
            if preset is not None:
                return _category_for_preset_area(_preset_category(preset))
        except Exception:
            # Preset lookup is best-effort; fall through to policy_type.
            pass
    if policy is not None:
        raw = getattr(getattr(policy, "policy_type", None), "value", None)
        if raw:
            return _category_for_policy_type(raw)
    return "Generic"


def _category_entry_limitations(category: str) -> list[str]:
    """Collect known limitations from scorecard entries in a category."""
    try:
        from fiscal_model.validation import cached_default_scorecard

        summary = cached_default_scorecard()
    except Exception:
        return []

    limitations: list[str] = []
    for entry in summary.entries:
        if entry.category != category:
            continue
        for limitation in entry.known_limitations:
            if limitation not in limitations:
                limitations.append(limitation)
    return limitations


def _category_holdout_status(category: str) -> str:
    """Return category-level holdout availability."""
    try:
        from fiscal_model.validation import cached_default_scorecard
        from fiscal_model.validation.holdout import category_holdout_status

        summary = cached_default_scorecard()
    except Exception:
        return "unknown"

    return category_holdout_status(category, list(summary.entries))


# ---------------------------------------------------------------------------
# This policy's own scorecard row, beside the class band
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OwnRow:
    """The scorecard row for the policy being scored, and which tier it sits in.

    Read from ``ui/preset_validation.get_validation_badge`` rather than
    recomputed: it already resolves a preset label *or* a stable id to a row,
    already knows the tier, and already shares the single cached scorecard.
    """

    policy_id: str
    tier: str
    tier_label: str
    abs_pct_error: float
    official_billions: float
    caption: str


def own_row_for(policy_name: str | None) -> OwnRow | None:
    """The scorecard row this preset prints against, or ``None``."""
    if not policy_name:
        return None
    try:
        from fiscal_model.ui.preset_validation import get_validation_badge

        badge = get_validation_badge(policy_name)
    except Exception:  # pragma: no cover — defensive
        return None
    if not badge:
        return None
    return OwnRow(
        policy_id=str(badge.get("policy_id", "")),
        tier=str(badge.get("tier", "")),
        tier_label=str(badge.get("tier_label", "")),
        abs_pct_error=float(badge.get("abs_pct", 0.0) or 0.0),
        official_billions=float(badge.get("official", 0.0) or 0.0),
        caption=str(badge.get("caption", "")),
    )


# ---------------------------------------------------------------------------
# The object every surface renders from
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultCredibility:
    """Machine-readable accuracy note for one scoring result."""

    category: str
    evidence_type: str
    policy_class: str | None
    class_label: str | None
    n_tier1_rows: int
    mean_abs_pct_error: float | None
    median_abs_pct_error: float | None
    max_abs_pct_error: float | None
    rows_inside_mean_band: int | None
    #: Inner band in dollars. Kept under the names the API has always used.
    uncertainty_low: float | None
    uncertainty_high: float | None
    #: Outer band in dollars — the class's worst observed row.
    outer_low: float | None
    outer_high: float | None
    no_band_reason: str
    own_row_policy_id: str | None
    own_row_tier: str | None
    own_row_tier_label: str | None
    own_row_abs_pct_error: float | None
    own_row_official_billions: float | None
    own_row_caption: str
    holdout_status: str
    limitations: list[str]
    caption: str


def get_credibility_for_result(
    *,
    point_estimate: float,
    policy_name: str | None = None,
    policy: Any = None,
) -> ResultCredibility | None:
    """Build the accuracy note for one scoring result.

    Always returns an object for a scored policy: the absence of a band is
    itself the finding and has to reach the surface, which is why this no longer
    returns ``None`` when a category lookup fails.
    """
    if policy is None and not policy_name:
        return None

    band = band_for_policy(policy)
    reason = "" if band is not None else no_tier1_class_reason(policy)
    category = category_for_result(policy_name=policy_name, policy=policy)
    own = own_row_for(policy_name)

    limitations = list(_ALL_RESULTS_LIMITATIONS)
    if band is None:
        limitations.append(
            "No pre-registered out-of-sample row scores a policy of this class, "
            "so this model's accuracy on one has not been measured."
        )
    for limitation in _category_entry_limitations(category):
        if limitation not in limitations:
            limitations.append(limitation)

    if band is None:
        inner = outer = (None, None)
    else:
        inner = band.inner_dollars(point_estimate)
        outer = band.outer_dollars(point_estimate)

    return ResultCredibility(
        category=category,
        evidence_type=(
            "out_of_sample_class_distribution"
            if band is not None
            else "no_out_of_sample_benchmark"
        ),
        policy_class=None if band is None else band.policy_class,
        class_label=None if band is None else band.class_label,
        n_tier1_rows=0 if band is None else band.n,
        mean_abs_pct_error=None if band is None else band.mean_abs_pct_error,
        median_abs_pct_error=None if band is None else band.median_abs_pct_error,
        max_abs_pct_error=None if band is None else band.max_abs_pct_error,
        rows_inside_mean_band=None if band is None else band.rows_inside_mean_band,
        uncertainty_low=inner[0],
        uncertainty_high=inner[1],
        outer_low=outer[0],
        outer_high=outer[1],
        no_band_reason=reason,
        own_row_policy_id=None if own is None else own.policy_id,
        own_row_tier=None if own is None else own.tier,
        own_row_tier_label=None if own is None else own.tier_label,
        own_row_abs_pct_error=None if own is None else own.abs_pct_error,
        own_row_official_billions=None if own is None else own.official_billions,
        own_row_caption="" if own is None else own.caption,
        holdout_status=_category_holdout_status(category),
        limitations=limitations,
        caption=format_band_caption(band, point_estimate=point_estimate, reason=reason),
    )


def credibility_to_dict(credibility: ResultCredibility | None) -> dict[str, Any] | None:
    """Serialize credibility metadata for API responses."""
    if credibility is None:
        return None
    return asdict(credibility)


__all__ = [
    "POLICY_TYPE_TO_SCORECARD_CATEGORY",
    "POLICY_TYPE_TO_TIER1_CLASS",
    "PRESET_AREA_TO_SCORECARD_CATEGORY",
    "EmpiricalBand",
    "OwnRow",
    "ResultCredibility",
    "band_for_policy",
    "band_for_policy_class",
    "band_for_policy_type",
    "category_for_result",
    "credibility_to_dict",
    "format_band_caption",
    "get_credibility_for_result",
    "own_row_for",
    "reset_confidence_cache",
    "tier1_class_bands",
]
