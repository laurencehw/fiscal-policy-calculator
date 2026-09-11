"""Map shipped presets to their validation-scorecard row — and say which tier it is.

Every preset that carries a ``CBO_SCORE_MAP`` ``official_score`` prints that
figure on a surface a user reads, so every one of them needs a row behind it and
a badge that says what kind of row it is. The three tiers mean different things
and must never be collapsed into one "validated within X%" claim (CLAUDE.md,
"Model maturity"):

* **fitted** — a module constant was set to reproduce this target. Agreement is
  bookkeeping: 20 rows at a 1.3% mean. The badge says *calibrated*, not
  "Excellent"; the rating there is measuring arithmetic.
* **reconstruction** — a published figure no constant is fitted to. 21 rows at a
  **70.4%** mean, from 1.1% to **701.0%**. This is where the tariff, pharma,
  international, enforcement and climate presets sit, and until H6 none of them
  carried a badge at all.
* **out-of-sample** — a pre-registered Tier 1 row, entered before it was ever
  scored. 3 rows at a 9.9% mean. The only genuine skill claim in the set.

Keyed by **stable preset id**, never by the display label. Labels embed the
score and are rewritten whenever a target moves (``target_revisions.py`` has
moved sixteen), so a label-keyed map loses entries silently on a rename; ids are
frozen because they ship in share links (``fiscal_model/preset_ids.py``).

Cost: one ``lru_cache``'d scorecard materialisation per process, shared with the
API endpoint and the Validation tab. Nothing here adds a second one — see
``planning/memos/COLD_START.md`` and MODELING_IMPROVEMENT §6.2 item 39, where
``get_validation_badge`` → ``_scorecard_index`` is the ~6.5 s term on a scored
route.
"""

from __future__ import annotations

from functools import lru_cache

from fiscal_model.preset_ids import (
    CATALOG_PRESET_IDS,
    label_for_preset_id,
    preset_id_for_token,
)

# ---------------------------------------------------------------------------
# The badge map — preset id -> scorecard policy_id
# ---------------------------------------------------------------------------
#: Every preset with a scorecard row of any tier, in catalog order. The set is
#: pinned equal to the set of presets carrying a ``CBO_SCORE_MAP``
#: ``official_score`` by ``tests/test_no_headline_without_row.py``: a preset
#: that prints an official figure without a row, or a badge for a preset with no
#: official figure, are both failures.
PRESET_ID_TO_SCORECARD_ID: dict[str, str] = {
    "tcja-full-extension": "tcja_full_extension",  # fitted, 0.4%
    "tcja-extension-no-salt-cap": "tcja_no_salt_cap",  # fitted, 13.9%
    "tcja-rates-only": "tcja_rates_only",  # fitted, 2.2%
    "corporate-28pct": "biden_corporate_28",  # fitted, 3.7%
    "corporate-15pct": "trump_corporate_15",  # reconstruction, 121.6% (range)
    "ctc-expansion-2021": "biden_ctc_2021",  # fitted, 0.0%
    "ctc-extension": "ctc_extension",  # fitted, 0.0%
    "eitc-childless-expansion": "biden_eitc_childless",  # reconstruction, 9.5%
    "estate-extend-tcja": "extend_tcja_exemption",  # fitted, 0.0%
    "estate-exemption-3-5m": "biden_estate_reform",  # fitted, 0.0%
    "estate-repeal": "eliminate_estate_tax",  # fitted, 0.0%
    "ss-cap-90pct": "ss_cap_90_pct",  # fitted, 0.0%
    "ss-donut-250k": "ss_donut_250k",  # fitted, 0.0%
    "ss-cap-eliminate": "ss_eliminate_cap",  # fitted, 0.0%
    "niit-expand": "expand_niit",  # fitted, 0.0%
    "amt-extend-tcja-relief": "extend_tcja_amt",  # reconstruction, 66.8%
    "amt-repeal-individual": "repeal_individual_amt",  # fitted, 0.1%
    "amt-repeal-corporate": "repeal_corporate_amt",  # fitted, 0.0%
    "aca-ptc-extend-enhanced": "extend_enhanced_ptc",  # reconstruction, 9.3%
    "aca-ptc-repeal": "repeal_ptc",  # reconstruction, 29.6%
    "cap-employer-health-exclusion": "cap_employer_health",  # fitted, 0.1%
    "salt-cap-repeal": "repeal_salt_cap",  # reconstruction, 1.1%
    "step-up-basis-eliminate": "eliminate_step_up",  # fitted, 4.7%
    "charitable-deduction-cap": "cap_charitable",  # reconstruction, 12.5%
    # ── added by H6: a row existed for every one of these; no badge did ──
    "top-rate-39-6": "biden_high_income_tax",  # out-of-sample, 9.2%
    # ultra-millionaire-surtax-3pp and medicare-surcharge-2pp sat here
    # until lane R2 retired both scorecard rows: neither target could be
    # traced to any published document, so both presets lost their
    # CBO_SCORE_MAP official_score and a badge with no row would be a
    # claim with nothing behind it. Both presets still score and still
    # show the model's own estimate.
    "gilti-reform": "biden_gilti_reform",  # reconstruction, 38.4%
    "fdii-repeal": "fdii_repeal",  # reconstruction, 29.9%
    "pillar-two-adoption": "pillar_two_adoption",  # reconstruction, 23.5% (range)
    "international-package": "biden_full_international",  # reconstruction, 44.1%
    "irs-enforcement-ira": "ira_enforcement",  # reconstruction, 4.7%
    "irs-enforcement-double": "double_enforcement",  # reconstruction, 82.3%
    "drug-negotiation-expand": "expand_drug_negotiation",  # reconstruction, 93.3%
    "insulin-cap-universal": "universal_insulin_cap",  # reconstruction, 39.0%
    "drug-reference-pricing": "international_reference_pricing",  # reconstr., 701.0%
    "tariff-universal-10pct": "trump_universal_10",  # reconstruction, 42.0%
    "tariff-china-60pct": "trump_china_60",  # reconstruction, 44.3%
    "tariff-auto-25pct": "auto_tariff_25",  # reconstruction, 52.8%
    "tariff-steel-aluminum-25pct": "steel_tariff_25",  # reconstruction, 11.9%
    "tariff-reciprocal": "reciprocal_tariffs",  # reconstruction, 6.9% (range)
    "ira-clean-energy-repeal": "repeal_ira_credits",  # fitted, 0.0%
    "carbon-tax-50": "carbon_tax_50",  # fitted, 0.9%
    "ev-credit-repeal": "repeal_ev_credits",  # reconstruction, 25.3%
}

#: The 24 presets :data:`PRESET_TO_SCORECARD_ID` carried before H6, kept as its
#: membership **unchanged and on purpose**.
#:
#: Two modules outside this one read that map's membership as a *claim*:
#: ``composer._tier_for`` returns ``"calibrated"`` on it, and
#: ``ui/tabs/results_summary._resolve_tier`` renders "Calibrated reference" on
#: it and "Benchmarked preset" otherwise. Widening it would relabel every
#: tariff, pharma and enforcement preset "Calibrated reference" on a surface a
#: user reads — a false claim, and a worse one than a missing badge. So the new
#: coverage lands in :data:`PRESET_ID_TO_SCORECARD_ID`, which
#: :func:`get_validation_badge` reads, and those two call sites are left for
#: their own owners to route through :func:`badge_tier`.
LEGACY_CALIBRATED_PRESET_IDS: frozenset[str] = frozenset(
    {
        "tcja-full-extension",
        "tcja-extension-no-salt-cap",
        "tcja-rates-only",
        "corporate-28pct",
        "corporate-15pct",
        "ctc-expansion-2021",
        "ctc-extension",
        "eitc-childless-expansion",
        "estate-extend-tcja",
        "estate-exemption-3-5m",
        "estate-repeal",
        "ss-cap-90pct",
        "ss-donut-250k",
        "ss-cap-eliminate",
        "niit-expand",
        "amt-extend-tcja-relief",
        "amt-repeal-individual",
        "amt-repeal-corporate",
        "aca-ptc-extend-enhanced",
        "aca-ptc-repeal",
        "cap-employer-health-exclusion",
        "salt-cap-repeal",
        "step-up-basis-eliminate",
        "charitable-deduction-cap",
    }
)

#: Presets whose scorecard row does **not** score the object the preset builds,
#: with the divergence measured on 2026-09-09 and its cause. A badge asserts
#: something about the number on the screen, so this list is the exception to
#: that and it is declared rather than discovered:
#: ``tests/test_no_headline_without_row.py`` fails on any *undeclared*
#: divergence above 1%.
#:
#: The two ``base_rule`` entries this registry used to carry
#: (``ultra-millionaire-surtax-3pp`` and ``medicare-surcharge-2pp``) are gone,
#: and not because lane H1 closed them: lane R2 retired both scorecard rows for
#: want of a published target, so there is no row left for the app's headline to
#: diverge from. A future ``base_rule`` entry should still be deleted when the
#: shared ``ordinary_income_base`` default makes it moot. ``runner_shape`` entries are structural
#: — the validation runners build their own policy from the ``CBOScore`` record
#: and score it on the validation window, not the app's FY2026 one — so the test
#: asserts they *still* diverge, and the registry cannot rot into a blanket
#: exemption.
#:
#: ``baseline`` is the third kind and the sharpest, because it is the one case
#: where the divergence is the *point* rather than a residue: the app scores
#: **current law** and the benchmark scores **its own document's**
#: counterfactual, and for SALT those are worth a factor of six to each other
#: (Penn Wharton prices repealing the cap at $1,169B against a permanent
#: $10,000 cap and at $197B against a world where it lapses, in the same
#: paper). A benchmark that moved onto current law would stop checking its
#: document, and an app that stayed on the document's baseline would print a
#: number for a reform that does not exist until 2030. So both are right and
#: the badge is the thing that cannot say it — which is why
#: ``results_summary.salt_current_law_caption`` carries the sentence and this
#: entry carries the measurement. Asserted to persist, like ``runner_shape``.
HEADLINE_ROW_DIVERGENCE: dict[str, tuple[str, str]] = {
    "drug-negotiation-expand": (
        "runner_shape",
        "app -41.8 vs row -33.5 (24.8%): -37.6 on the validation window, so "
        "+4.2 is the app's FY2026 window (PR #115) and 12.3% the runner's own "
        "policy build.",
    ),
    "top-rate-39-6": (
        "runner_shape",
        "app -216.5 vs row -223.3 (3.1%): -194.8 on the validation window, so "
        "+21.6 is the window and 12.7% the runner's own policy build.",
    ),
    "salt-cap-repeal": (
        "baseline",
        "app +740.3 vs row +1,155.6 (35.9%): the app scores current law and "
        "the row scores PWBM's own baseline. P.L. 119-21 sec. 70120 sets the "
        "SALT cap at $40,400 in 2026 rising 1%/yr through 2029 and $10,000 "
        "from 2030, while PWBM's Table 3 prices repeal against a permanent "
        "$10,000 cap -- and the same paper prices it at $197B against a "
        "baseline where the cap lapses, so the counterfactual is worth a "
        "factor of six here and cannot be left implicit. The benchmark stays "
        "on its document's baseline (validation/scenarios.SALT_SCORING_"
        "BASELINES) because that is what a benchmark is for; the app scores "
        "the law. `results_summary.salt_current_law_caption` says so beside "
        "the headline. See planning/lanes/SALT_current_law_baseline.md.",
    ),
}

#: Tolerance, in percent, for "the row scores the headline".
HEADLINE_ROW_TOLERANCE_PCT = 1.0

# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------
TIER_FITTED = "fitted"
TIER_RECONSTRUCTION = "reconstruction"
TIER_OUT_OF_SAMPLE = "out_of_sample"
TIER_NO_ROW = "no_row"

#: Short label per tier, for a surface with room for three words.
TIER_LABELS: dict[str, str] = {
    TIER_FITTED: "Calibrated reference",
    TIER_RECONSTRUCTION: "Unfitted reconstruction",
    TIER_OUT_OF_SAMPLE: "Out-of-sample prediction",
    TIER_NO_ROW: "Exploratory — not validated",
}

#: One sentence per tier, with no figure in it. The figures go in the caption.
TIER_NOTES: dict[str, str] = {
    TIER_FITTED: (
        "reproduces its published target by construction (calibrated) — "
        "agreement here is bookkeeping, not an independent test"
    ),
    TIER_RECONSTRUCTION: (
        "an unfitted reconstruction: no constant in the model is fitted to this "
        "published figure"
    ),
    TIER_OUT_OF_SAMPLE: (
        "a pre-registered out-of-sample prediction, entered before it was scored"
    ),
    TIER_NO_ROW: (
        "exploratory — no published benchmark is scored against this policy"
    ),
}

#: A fitted row does not get the rating's green tick: the rating is measuring
#: arithmetic there, and "Estate: n=3, 0.0%, Excellent" is the failure mode this
#: replaces (HIGH_STAKES_ACCURACY.md §2). Every other tier keeps the rating's own
#: icon, which does carry information about the error.
_TIER_ICON = {TIER_FITTED: "🎯"}

_RATING_ICON = {
    "Excellent": "🟢",
    "Good": "🟢",
    "Acceptable": "🟡",
    "Poor": "🔴",
    "Error": "⚫",
}


def _label_for(preset_id: str) -> str | None:
    try:
        return label_for_preset_id(preset_id)
    except KeyError:  # pragma: no cover - an id with no catalog label
        return None


def _label_view(preset_ids: frozenset[str] | None) -> dict[str, str]:
    """Label-keyed view of the id map, restricted to ``preset_ids`` if given."""
    view: dict[str, str] = {}
    for preset_id, score_id in PRESET_ID_TO_SCORECARD_ID.items():
        if preset_ids is not None and preset_id not in preset_ids:
            continue
        label = _label_for(preset_id)
        if label is not None:
            view[label] = score_id
    return view


#: Label-keyed view of the **whole** badge map. Derived, so a preset renamed in
#: ``app_data`` (and, as ``tests/test_policy_catalog.py`` requires, in
#: ``preset_ids``) carries its badge across the rename for free.
BADGE_SCORECARD_ID_BY_LABEL: dict[str, str] = _label_view(None)

#: Legacy label-keyed view — the 24 members it has always had. See
#: :data:`LEGACY_CALIBRATED_PRESET_IDS` for why it is not widened here.
PRESET_TO_SCORECARD_ID: dict[str, str] = _label_view(LEGACY_CALIBRATED_PRESET_IDS)


@lru_cache(maxsize=1)
def _scorecard_index() -> dict[str, dict]:
    """Materialize the live scorecard once per process and key by policy_id.

    Backed by ``cached_default_scorecard`` so the API endpoint, the
    Validation tab, the per-preset accuracy badge, and the confidence-
    band helper all share a single computation per process — repeat
    Streamlit reruns or API hits never trigger a re-validation.
    """
    from fiscal_model.validation import cached_default_scorecard

    summary = cached_default_scorecard()
    return {
        e.policy_id: {
            "rating": e.rating,
            "abs_pct": e.abs_percent_difference,
            "signed_pct": e.percent_difference,
            "policy_name": e.policy_name,
            "official": e.official_10yr_billions,
            "model": e.model_10yr_billions,
            "source": e.official_source,
            "url": e.benchmark_url,
            "category": e.category,
            "provenance": e.provenance,
            "calibrated_to_target": e.calibrated_to_target,
            "declared_calibrated_to_target": e.declared_calibrated_to_target,
            "range_low": e.published_range_low_billions,
            "range_high": e.published_range_high_billions,
            "within_range": e.within_published_range,
            "range_distance": e.distance_to_published_range_billions,
        }
        for e in summary.entries
    }


def reset_scorecard_cache() -> None:
    """Clear the memoized scorecard. Mainly for tests."""
    cache_clear = getattr(_scorecard_index, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def tier_for_entry(entry: dict) -> str:
    """Which of the three tiers a scorecard row sits in.

    The category test comes **first**: a ``Generic`` (Tier 1) row also carries
    ``calibrated_to_target=True`` by default, so asking the flag first would
    report the repository's only out-of-sample rows as fitted ones.
    """
    if str(entry.get("category", "")) == "Generic":
        return TIER_OUT_OF_SAMPLE
    return TIER_FITTED if entry.get("calibrated_to_target") else TIER_RECONSTRUCTION


def badge_tier(preset: str) -> str:
    """Tier for a preset label or id; :data:`TIER_NO_ROW` when it has no row."""
    badge = get_validation_badge(preset)
    return badge["tier"] if badge else TIER_NO_ROW


def is_calibrated_reference(preset: str) -> bool:
    """True when this preset's row is one the model was *fitted* to reproduce."""
    return badge_tier(preset) == TIER_FITTED


def _money(billions: float) -> str:
    """``-1347.0`` -> ``"-$1.35T"``; ``162.6`` -> ``"$163B"``; ``3.2`` -> ``"$3.2B"``.

    Whole billions are the right resolution for a $163B target and the wrong one
    for a **distance to a published range**, which is the one place this format
    is asked to print a small number: ``reciprocal_tariffs`` sits $3.2B outside
    its nearer bound, and rounding that to "$3B" — or a sub-$0.5B distance to
    "$0B", which reads as *inside* the range — states something the row does not.
    So one decimal below $10B, whole billions above it.
    """
    sign = "-" if billions < 0 else ""
    value = abs(float(billions))
    if value >= 1000.0:
        return f"{sign}${value / 1000.0:.2f}T"
    if value < 10.0:
        return f"{sign}${value:.1f}B"
    return f"{sign}${value:.0f}B"


#: Longest source name a caption will carry. Several are a full citation with a
#: title and a parenthetical; a badge has one line.
_SOURCE_MAX_CHARS = 44


def _source(entry: dict) -> str:
    """Short estimator name: the first clause, capped."""
    text = str(entry.get("source") or "").strip()
    if not text:
        return "the published estimate"
    head = text.split(",")[0].strip()
    # Several sources put a comma *inside* a parenthetical ("Tax Foundation
    # (tracker, 2025)"); cutting there leaves an unclosed bracket.
    if head.count("(") != head.count(")"):
        head = text
    if len(head) > _SOURCE_MAX_CHARS:
        head = head[: _SOURCE_MAX_CHARS - 1].rstrip() + "…"
    return head


def _range_clause(entry: dict) -> str:
    """"inside/outside the published range" — never a percentage."""
    low, high = entry.get("range_low"), entry.get("range_high")
    if low is None or high is None:
        return ""
    bounds = f"[{_money(low)}, {_money(high)}]"
    model = _money(entry["model"])
    if entry.get("within_range"):
        return (
            f" Published range {bounds}: the model's {model} is inside it, so "
            "the % is a distance from an anchor, not a measure of accuracy."
        )
    distance = entry.get("range_distance")
    gap = f" by {_money(distance)}" if distance else ""
    return f" Published range {bounds}: the model's {model} is outside it{gap}."


def _provenance_clause(entry: dict) -> str:
    """Name a target that is not a published figure. Six rows still are not."""
    if str(entry.get("provenance", "")) == "model_estimate":
        return " The target itself is this model's own estimate, not a published score."
    return ""


def _caption(entry: dict, tier: str) -> str:
    """One short, tier-correct sentence. Never a "validated within X%" claim."""
    source = _source(entry)
    official = _money(entry["official"])
    if tier == TIER_FITTED:
        head = (
            f"Calibrated to reproduce {official} ({source}) — agreement is by "
            "construction, not an independent test."
        )
    elif tier == TIER_OUT_OF_SAMPLE:
        head = (
            f"Out-of-sample prediction, {entry['abs_pct']:.1f}% from {official} "
            f"({source}) — pre-registered before it was scored."
        )
    else:
        head = (
            f"Unfitted reconstruction, {entry['abs_pct']:.1f}% from {official} "
            f"({source}) — no constant is fitted to this figure."
        )
    return head + _provenance_clause(entry) + _range_clause(entry)


def get_validation_badge(preset_name: str) -> dict | None:
    """Validation info for a preset label **or** stable id; ``None`` if untracked.

    The dict carries the scorecard row's rating and figures, the **tier** the
    row sits in (``tier`` / ``tier_label`` / ``tier_note``), a ready-made
    ``caption`` for a markdown sink, and the published range when the target is
    one. ``rating`` stays the scorecard's own word; ``rating_label`` is what a
    surface should print, because a fitted row's "Excellent" is arithmetic.
    """
    score_id = BADGE_SCORECARD_ID_BY_LABEL.get(preset_name)
    if score_id is None:
        preset_id = preset_id_for_token(preset_name)
        if preset_id is not None:
            score_id = PRESET_ID_TO_SCORECARD_ID.get(preset_id)
    if score_id is None:
        return None
    try:
        index = _scorecard_index()
    except Exception:
        return None
    entry = index.get(score_id)
    if entry is None:
        return None
    tier = tier_for_entry(entry)
    rating_label = entry["rating"]
    icon = _TIER_ICON.get(tier) or _RATING_ICON.get(entry["rating"], "⚪")
    if tier == TIER_FITTED:
        rating_label = "Calibrated"
    elif entry.get("within_range"):
        # The rating is computed against an in-range anchor, so it can read
        # "Poor" for a model the publisher's own range contains.
        rating_label, icon = "Within published range", "🟢"
    return {
        **entry,
        "policy_id": score_id,
        "tier": tier,
        "tier_label": TIER_LABELS[tier],
        "tier_note": TIER_NOTES[tier],
        "rating_label": rating_label,
        "caption": _caption(entry, tier),
        "icon": icon,
    }


# ---------------------------------------------------------------------------
# The illustrative caption (H12)
# ---------------------------------------------------------------------------
#: Figure-free line for a demoted preset, for a surface that must not pay for a
#: scorecard materialisation to render one row.
#:
#: Measured on 2026-09-11: the first ``get_validation_badge`` call in a process
#: costs **6.187 s** (``_scorecard_index`` runs every specialized validator over
#: all 81 rows), and Build's checklist does not materialise the scorecard today.
#: Printing a live figure on every illustrative checkbox would therefore have
#: put ~6.2 s on Build's first paint — the same defect ``planning/memos/
#: COLD_START.md`` found in the page footer and PR #135 removed. So Build names
#: the tier and says where the figure is; Explore, which already calls
#: ``get_validation_badge`` for its badge caption, prints the figure itself.
ILLUSTRATIVE_ROW_NOTE_NO_FIGURE = (
    "↳ Illustrative — an unfitted reconstruction, not a validated score. "
    "Its distance from the published figure is on Explore and in the "
    "validation scorecard."
)


def illustrative_note(preset: str) -> str:
    """One line for a demoted preset, naming the tier its row sits in.

    Deliberately **figure-free**, and it never materialises the scorecard —
    including the "has this preset a row at all" test, which asks
    :data:`PRESET_ID_TO_SCORECARD_ID` rather than calling
    :func:`get_validation_badge`. See
    :data:`ILLUSTRATIVE_ROW_NOTE_NO_FIGURE` for the measurement behind that.

    A preset with no scorecard row of any tier gets a line saying so, because a
    silent absence reads like agreement. That is the branch Explore takes: it
    prints this line exactly where a badge caption would have gone, so the
    figure comes from the badge wherever there is one and from here where there
    is not.
    """
    preset_id = preset_id_for_token(preset) or preset
    if preset_id not in PRESET_ID_TO_SCORECARD_ID:
        from fiscal_model.app_data import ILLUSTRATIVE_NO_ROW_NOTE

        return f"↳ Illustrative — {ILLUSTRATIVE_NO_ROW_NOTE}"
    return ILLUSTRATIVE_ROW_NOTE_NO_FIGURE


def presets_without_a_row() -> tuple[str, ...]:
    """Catalog preset ids with no scorecard row of any tier.

    These are the presets whose label may not carry a dollar figure: the app
    prints a model number for them and nothing checks it.
    """
    return tuple(
        preset_id
        for preset_id in CATALOG_PRESET_IDS
        if preset_id not in PRESET_ID_TO_SCORECARD_ID
    )


__all__ = [
    "BADGE_SCORECARD_ID_BY_LABEL",
    "HEADLINE_ROW_DIVERGENCE",
    "HEADLINE_ROW_TOLERANCE_PCT",
    "ILLUSTRATIVE_ROW_NOTE_NO_FIGURE",
    "LEGACY_CALIBRATED_PRESET_IDS",
    "PRESET_ID_TO_SCORECARD_ID",
    "PRESET_TO_SCORECARD_ID",
    "TIER_FITTED",
    "TIER_LABELS",
    "TIER_NOTES",
    "TIER_NO_ROW",
    "TIER_OUT_OF_SAMPLE",
    "TIER_RECONSTRUCTION",
    "badge_tier",
    "get_validation_badge",
    "illustrative_note",
    "is_calibrated_reference",
    "presets_without_a_row",
    "reset_scorecard_cache",
    "tier_for_entry",
]
