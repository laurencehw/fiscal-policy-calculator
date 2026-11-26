"""How far out this number is likely to be — read off the out-of-sample tier.

A headline needs a band, and until Wave C's H4 it got one of two that carried no
information about accuracy:

* **The ETI ±0.1 sweep** (``ui/tabs/results_summary._sensitivity_band``). For a
  plain ``TaxPolicy`` the headline is ``0.875 × static`` and the sweep's width is
  ``0.8 × 0.125 × static``, so the band is **0.1 / 0.875 = 11.43% of the
  headline for every policy, every rate, every threshold** — the across-the-board 5pp cut at
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
    "International Tax": "International",
    "IRS Enforcement": "Enforcement",
    "Drug Pricing": "Pharma",
    "Trade / Tariffs": "Trade",
    "Climate / Energy": "Climate",
    # H12's demoted group (`app_data.ILLUSTRATIVE_GROUP_LABEL`, spelled out
    # here rather than imported so a validation module keeps no dependency on
    # the app's preset data; `tests/test_illustrative_group.py` pins the two
    # equal). `category_for_result` resolves each member to its underlying
    # module category (`Pharma` or `Enforcement`) instead of dumping the
    # entire Generic benchmark list onto it.
    "Illustrative - unfitted reconstructions": "Illustrative",
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
    #: The non-zero ``rate_change`` each of the class's rows scores, signed, as
    #: its benchmark record states it. Empty for a class whose rows are not rate
    #: changes (spending paths, a deduction cap). The band describes reforms of
    #: these sizes and says nothing about one several times larger, or of the
    #: other sign: see :func:`outside_tested_range_reason`.
    tested_rate_changes: tuple[float, ...] = ()

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
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES
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
            tested_rate_changes=_tested_rate_changes(
                [policy_id for _, policy_id in rows], KNOWN_SCORES
            ),
        )
    return out


def _tested_rate_changes(policy_ids: list[str], scores: Any) -> tuple[float, ...]:
    rates = set()
    for policy_id in policy_ids:
        rate = getattr(scores.get(policy_id), "rate_change", None)
        if rate:
            rates.add(float(rate))
    return tuple(sorted(rates))


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

    A lookup by type label alone, with no policy object and so no check of the
    reform's size or sign. **Not for the bill tracker**: a band there would put
    the scoring engine's error on a number whose main uncertainty is the
    automated reading of the bill, which no row measures
    (:func:`band_for_bill_reading`).
    """
    if not policy_type:
        return None
    return band_for_policy_class(POLICY_TYPE_TO_TIER1_CLASS.get(policy_type))


def band_for_bill_reading(policy_type: str | None) -> None:
    """A bill-tracker reading carries no band, whatever its provision type.

    The class bands measure the scoring engine on reforms a person specified.
    A tracker figure is the engine applied to a language model's reading of
    bill text, and the reading is the larger and unmeasured source of error:
    on the night of the 23 Nov 2026 review it put a clergy housing bill at
    -$14.2 trillion. Returning ``None`` here, rather than deleting the call,
    keeps the decision in one named place.
    """
    return None


def _points(rate: float) -> str:
    return f"{abs(rate) * 100:g}"


def outside_tested_range_reason(policy: Any) -> str | None:
    """Why a policy's class band does not apply to it, or ``None`` if it does.

    A class band is the error on that class's pre-registered rows, and those
    rows are small rate rises: the four corporate rows are each +1 point. A
    reform of the other sign, or larger than the largest row, is outside what
    the rows test. The corporate preset at 15% misses its published score by
    far more than the four +1-point rows miss theirs, which is the case this
    rule exists for (outside review, 23 Nov 2026).

    Only a policy carrying a plain non-zero ``rate_change`` is checked, against
    the rows of its own class that do too. No threshold is chosen here: the
    range is the rows' own.
    """
    band = band_for_policy_class(classify_policy_object(policy))
    if band is None or not band.tested_rate_changes:
        return None
    rate = getattr(policy, "rate_change", None)
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not rate:
        return None
    same_sign = [t for t in band.tested_rate_changes if (t > 0) == (rate > 0)]
    rows = f"the {band.n} pre-registered {band.class_label} rows"
    if not same_sign:
        direction = "cut" if rate < 0 else "increase"
        tested = "increases" if rate < 0 else "cuts"
        return (
            f"{rows} are all rate {tested}; no row tests a rate {direction}, so "
            "the class's error does not carry over to this one"
        )
    limit = max(abs(t) for t in same_sign)
    if abs(rate) > limit + 1e-9:
        return (
            f"{rows} test changes of up to {_points(limit)} points; this one is "
            f"{_points(rate)} points, outside the range their error describes"
        )
    return None


def band_for_policy(policy: Any) -> EmpiricalBand | None:
    """The band for a live policy object, or ``None``.

    ``None`` when the policy's class has no pre-registered row, and also when
    the class has rows but this reform is outside the range they test
    (:func:`outside_tested_range_reason`).
    """
    if outside_tested_range_reason(policy) is not None:
        return None
    return band_for_policy_class(classify_policy_object(policy))


def _signed_billions(value: float) -> str:
    """``-$348.5B`` / ``+$12.0B``: the sign before the dollar, as the UI prints it.

    Plain text on purpose — the API and the Ask assistant return this sentence
    verbatim, so it carries no markdown escape. The UI renders it inside an HTML
    block, which the math parser does not tokenize. Digits are Python's own
    ``{:+,.1f}`` with only the sign moved (``fiscal_model.ui.formatting``'s rule,
    restated here so the validation layer does not import the UI).
    """
    text = f"{value:+,.1f}"
    return f"{text[0]}${text[1:]}B"


def format_band_caption(
    band: EmpiricalBand | None,
    *,
    point_estimate: float | None = None,
    reason: str = "",
    outside_range: bool = False,
) -> str:
    """One or two sentences: what the band is, and what it is not.

    Never a "validated within X%" claim — the number is always attached to its
    class, its ``n`` and its tier.
    """
    if band is None:
        base = "No out-of-sample band"
        if reason:
            base += f": {reason}"
        if outside_range:
            return (
                base
                + ". The 44 pre-registered Tier 1 rows are the only tier that "
                "measures this model's accuracy, and none of them scores a "
                "reform of this size and direction."
            )
        return (
            base
            + ". The 44 pre-registered Tier 1 rows are the only tier that "
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
        head += (
            f" On this figure that is {_signed_billions(low)} to "
            f"{_signed_billions(high)}"
        )
        if band.max_abs_pct_error > band.mean_abs_pct_error:
            head += (
                f" typical, {_signed_billions(outer_low)} to "
                f"{_signed_billions(outer_high)} at the worst row."
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


_POLICY_CLASS_LIMITATIONS: dict[str, list[str]] = {
    "ordinary_rate_change": [
        "Thresholds are statutory taxable-income boundaries applied to IRS SOI AGI size classes; real bracket creep is not modelled.",
        "Behavioral response uses a static Elasticity of Taxable Income (ETI) formula without income-shifting or multi-year timing lags.",
    ],
    "agi_inclusive_surtax": [
        "Applies to IRS SOI AGI above the stated threshold; unindexed nominal thresholds grow implicitly with the projected base.",
        "Behavioral response uses a static Elasticity of Taxable Income (ETI) formula without multi-year timing lags.",
    ],
    "capital_gains": [
        "Capital-gains realizations are sensitive to lock-in effects and enactment-year timing; the module does not model fiscal-year receipts lags.",
    ],
    "corporate": [
        "Corporate rate changes are priced on CBO's corporate receipts path converted to a statutory base with a calibrated marginal credit-absorption factor.",
        "Corporate Alternative Minimum Tax (CAMT) interactions and firm-level carryforward constraints are not modelled separately.",
    ],
    "payroll": [
        "Payroll estimates grow covered earnings with CBO's wage path and model compensation shifting with a single ETI parameter.",
    ],
    "tax_expenditure": [
        "Tax expenditure estimates rely on aggregate IRS SOI / JCT expenditure bases rather than return-level itemization transitions.",
    ],
    "discretionary_spending": [
        "Discretionary outlay paths apply account-class spend-out profiles rather than program-specific obligation schedules.",
    ],
    "enacted_law_spending": [
        "Mandatory and enacted-law spending paths rely on simplified growth and spend-out assumptions rather than program-level microsimulation.",
    ],
}

_POLICY_CLASS_NAME_TO_CATEGORY: dict[str, str] = {
    "TariffPolicy": "Trade",
    "ClimateEnergyPolicy": "Climate",
    "InternationalTaxPolicy": "International",
    "DrugPricingPolicy": "Pharma",
    "IRSEnforcementPolicy": "Enforcement",
    "CorporateTaxPolicy": "Corporate",
    "TCJAExtensionPolicy": "TCJA",
    "TaxCreditPolicy": "Credits",
    "EstateTaxPolicy": "Estate",
    "PayrollTaxPolicy": "Payroll",
    "AMTPolicy": "AMT",
    "PremiumTaxCreditPolicy": "PTC",
    "TaxExpenditurePolicy": "Expenditures",
    "CapitalGainsPolicy": "CapitalGains",
    "CapitalGainsTaxPolicy": "CapitalGains",
}


def _sanitize_limitation(text: str) -> str | None:
    """Strip internal repo/engineering references from a limitation string.

    Scorecard ``known_limitations`` entries double as provenance notes in the
    validation ledger and often mention internal PR numbers, review waves,
    planning-lane files, or benchmark revision IDs. Those belong in the repo
    audit trail, not on public preset pages.
    """
    import re

    cleaned = text.strip()
    if not cleaned:
        return None

    # Drop whole sentences that are purely internal engineering / revision notes.
    internal_sentence_re = re.compile(
        r"\b(?:PR\s*#\d+|Wave\s+[0-9A-Z]+|lane\s+[A-Za-z0-9_-]+|"
        r"planning/[A-Za-z0-9_./-]+|scripts/[A-Za-z0-9_./-]+|tests/[A-Za-z0-9_./-]+|"
        r"loo\.py|owner Decision \d+|registered regression|Phase [A-Z])\b",
        re.IGNORECASE,
    )
    # Split on sentence boundaries (keeping decimal numbers intact).
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z(])", cleaned)
    kept: list[str] = []
    for sentence in sentences:
        if internal_sentence_re.search(sentence):
            continue
        # Remove inline revision-ID parentheticals like `(foo.v1 -> .v2)`.
        s = re.sub(r"\s*\([^()]*\.v\d+[^()]*\)", "", sentence)
        # Remove leading rating labels like "Poor: " that only make sense in a scorecard table.
        s = re.sub(r"^(?:Poor|Fair|Acceptable|Good|Excellent):\s*", "", s)
        s = re.sub(r"\s{2,}", " ", s).strip()
        if s:
            kept.append(s)

    if not kept:
        return None
    result = " ".join(kept)
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def _category_for_preset_area(area: str | None) -> str:
    if not area:
        return "Generic"
    return PRESET_AREA_TO_SCORECARD_CATEGORY.get(area, "Generic")


def _category_for_policy_type(policy_type: str | None) -> str:
    if not policy_type:
        return "Generic"
    return POLICY_TYPE_TO_SCORECARD_CATEGORY.get(policy_type, "Generic")


def _category_for_preset_dict(preset: dict[str, Any], area_category: str) -> str:
    """Resolve an illustrative preset to its underlying module category."""
    if area_category != "Illustrative":
        return area_category
    if preset.get("is_pharma"):
        return "Pharma"
    if preset.get("is_enforcement"):
        return "Enforcement"
    if preset.get("is_trade"):
        return "Trade"
    if preset.get("is_climate"):
        return "Climate"
    if preset.get("is_international"):
        return "International"
    return area_category


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
                area_cat = _category_for_preset_area(_preset_category(preset))
                return _category_for_preset_dict(preset, area_cat)
        except Exception:
            # Preset lookup is best-effort; fall through to policy class / type.
            pass
    if policy is not None:
        cls_cat = _POLICY_CLASS_NAME_TO_CATEGORY.get(type(policy).__name__)
        if cls_cat:
            return cls_cat
        raw = getattr(getattr(policy, "policy_type", None), "value", None)
        if raw:
            return _category_for_policy_type(raw)
    return "Generic"


def _category_entry_limitations(
    category: str,
    *,
    own_policy_id: str | None = None,
    policy_class: str | None = None,
) -> list[str]:
    """Collect user-facing limitations for a policy or its category.

    When ``own_policy_id`` matches a scorecard entry, only that entry's
    limitations are surfaced (preventing unrelated policies in the same
    category from leaking onto a preset page). Generic runs without a matching
    row use concise class-level caveats instead of concatenating all 44
    out-of-sample rows.
    """
    try:
        from fiscal_model.validation import cached_default_scorecard

        summary = cached_default_scorecard()
    except Exception:
        summary = None

    limitations: list[str] = []

    def _add(raw_items: list[str]) -> None:
        for raw in raw_items:
            cleaned = _sanitize_limitation(raw)
            if cleaned and cleaned not in limitations:
                limitations.append(cleaned)

    if summary is not None and own_policy_id:
        for entry in summary.entries:
            if entry.policy_id == own_policy_id:
                _add(list(entry.known_limitations))
                break
        if limitations:
            return limitations

    if category == "Generic":
        if policy_class and policy_class in _POLICY_CLASS_LIMITATIONS:
            return list(_POLICY_CLASS_LIMITATIONS[policy_class])
        return list(_POLICY_CLASS_LIMITATIONS["ordinary_rate_change"])

    if summary is not None:
        for entry in summary.entries:
            if entry.category != category:
                continue
            _add(list(entry.known_limitations))
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
    #: The model's figure on the scorecard row, which is scored on the
    #: published estimate's own window and terms. It can differ from the
    #: figure a page shows (e.g. FY2025-2034 vs the page's FY2026-2035), and
    #: ``abs_pct_error`` is measured against this one, not the page's.
    model_billions: float | None = None
    #: The budget window the published figure covers, as transcribed in
    #: ``benchmark_sources``; ``None`` where no transcription records one.
    window: str | None = None


def _published_window(policy_id: str) -> str | None:
    """The window of the published figure this row is scored against, if transcribed."""
    try:
        from fiscal_model.validation.benchmark_sources import source_for

        source = source_for(policy_id)
    except Exception:  # pragma: no cover — defensive
        return None
    if source is None or not source.window:
        return None
    return source.window.strip() or None


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
        model_billions=None if badge.get("model") is None else float(badge["model"]),
        window=_published_window(str(badge.get("policy_id", ""))),
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
    own_row_model_billions: float | None
    #: The window of the published figure in ``own_row_official_billions``,
    #: which can differ from the window the page's own figure is on.
    own_row_window: str | None
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
    reason = ""
    if band is None:
        reason = outside_tested_range_reason(policy) or no_tier1_class_reason(policy)
    outside_range = band is None and classify_policy_object(policy) is not None
    category = category_for_result(policy_name=policy_name, policy=policy)
    own = own_row_for(policy_name)

    limitations = list(_ALL_RESULTS_LIMITATIONS)
    if outside_range:
        limitations.append(
            "The pre-registered out-of-sample rows of this class test smaller "
            "changes or changes of the other sign, so this model's accuracy on "
            "a reform of this size has not been measured."
        )
    elif band is None:
        limitations.append(
            "No pre-registered out-of-sample row scores a policy of this class, "
            "so this model's accuracy on one has not been measured."
        )
    for limitation in _category_entry_limitations(
        category,
        own_policy_id=None if own is None else own.policy_id,
        policy_class=None if band is None else band.policy_class,
    ):
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
        own_row_model_billions=None if own is None else own.model_billions,
        own_row_window=None if own is None else own.window,
        holdout_status=_category_holdout_status(category),
        limitations=limitations,
        caption=format_band_caption(
            band,
            point_estimate=point_estimate,
            reason=reason,
            outside_range=outside_range,
        ),
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
    "band_for_bill_reading",
    "band_for_policy",
    "band_for_policy_class",
    "band_for_policy_type",
    "category_for_result",
    "credibility_to_dict",
    "format_band_caption",
    "get_credibility_for_result",
    "outside_tested_range_reason",
    "own_row_for",
    "reset_confidence_cache",
    "tier1_class_bands",
]
