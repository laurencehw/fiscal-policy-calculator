"""Stable identity, overlap structure, and values tags for the preset catalog.

``PRESET_POLICIES`` (``fiscal_model/app_data.py``) is keyed by an emoji display
label that embeds the official score, e.g.
``"\N{CLASSICAL BUILDING}\N{VARIATION SELECTOR-16} TCJA Full Extension (CBO: $4.6T)"``.
Those labels are a *display* concern: they carry emoji, punctuation and numbers
that change whenever a score is refreshed, and they are a poor thing to put in a
share URL. This module adds the three pieces of catalog schema the redesign
needs, without changing the labels or the iteration order that the rest of the
app keys on today:

1. **Stable ids** — a frozen kebab-case slug per preset (:data:`PRESET_ID_BY_LABEL`).
   Slugs are hand-curated, instrument-descriptive and party-neutral. **They never
   change once shipped**: they go into share links, so a rename breaks every link
   ever pasted. Renaming a *label* is fine; renaming an *id* is not.
2. **Overlap structure** — :data:`EXCLUSIVE_GROUPS` ("pick at most one of these")
   and :data:`SUBSUMES` ("this bundle already contains those"). Today the Budget
   Builder sums whatever is checked, so selecting all three SS-cap options
   triple-counts the same revenue. This is the data the Build UI needs to dim
   siblings.
3. **Values tags** — the five-tag schema from the redesign plan
   (``direction``/``progressivity``/``govt_size``/``base``/``generational``),
   loaded from the generated :mod:`fiscal_model.policy_tags_generated`. See
   ``scripts/derive_policy_tags.py`` for how they are derived and
   ``fiscal_model/data_files/policy_tags_overrides.yaml`` for the hand-set ones.

:func:`attach_catalog_metadata` writes all three onto the ``PRESET_POLICIES``
entries at import time (``app_data`` calls it at the bottom of the module), so
consumers can read ``preset["preset_id"]`` / ``preset["tags"]`` directly, or go
label→id→label through the functions here.

Import direction is one-way: this module never imports ``app_data``, so
``app_data`` can import it.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import unquote_plus

CUSTOM_POLICY_LABEL = "Custom Policy"
CUSTOM_POLICY_ID = "custom-policy"

# ── 1. Stable ids ───────────────────────────────────────────────────────
# Order matches PRESET_POLICIES. FROZEN: ids ship in URLs and must not change.
PRESET_ID_BY_LABEL: dict[str, str] = {
    "Custom Policy": "custom-policy",
    # TCJA
    "🏛️ TCJA Full Extension (CBO: $4.6T)": "tcja-full-extension",
    "🏛️ TCJA Extension (No SALT Cap)": "tcja-extension-no-salt-cap",
    "🏛️ TCJA Rates Only": "tcja-rates-only",
    # Corporate
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": "corporate-28pct",
    "🏢 Trump Corporate 15%": "corporate-15pct",
    # Credits
    "👶 Biden CTC Expansion (CBO: $1.6T)": "ctc-expansion-2021",
    "👶 CTC Extension (CBO: $600B)": "ctc-extension",
    "💼 EITC Childless Expansion (Treasury: $163B)": "eitc-childless-expansion",
    # Estate
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": "estate-extend-tcja",
    "🏠 Biden Estate Reform (-$450B)": "estate-exemption-3-5m",
    "🏠 Eliminate Estate Tax ($350B)": "estate-repeal",
    # Payroll / SS
    "💰 SS Cap to 90% (CBO: -$800B)": "ss-cap-90pct",
    "💰 SS Donut Hole $250K (-$2.7T)": "ss-donut-250k",
    "💰 Eliminate SS Cap (-$3.2T)": "ss-cap-eliminate",
    "💰 Expand NIIT (JCT: -$250B)": "niit-expand",
    # AMT
    "⚖️ AMT: Extend TCJA Relief ($1.36T)": "amt-extend-tcja-relief",
    "⚖️ Repeal Individual AMT ($450B)": "amt-repeal-individual",
    "⚖️ Repeal Corporate AMT (-$220B)": "amt-repeal-corporate",
    # ACA premium tax credits
    "🏥 Extend ACA Enhanced PTCs ($335B)": "aca-ptc-extend-enhanced",
    "🏥 Repeal ACA Premium Credits (-$1.1T)": "aca-ptc-repeal",
    # Tax expenditures
    "📋 Cap Employer Health Exclusion (-$450B)": "cap-employer-health-exclusion",
    "📋 Repeal SALT Cap ($1.17T)": "salt-cap-repeal",
    "📋 Eliminate Step-Up Basis (-$500B)": "step-up-basis-eliminate",
    "📋 Cap Charitable Deduction (-$200B)": "charitable-deduction-cap",
    # Generic individual rate presets (no is_* flag; scored as plain TaxPolicy)
    "Biden 2025 Proposal": "top-rate-39-6",
    "Progressive Millionaire Tax": "millionaire-surtax-5pp",
    "Middle Class Tax Cut": "middle-class-rate-cut-2pp",
    "Flat Tax Reform": "across-the-board-rate-cut-5pp",
    "Warren Ultra-Millionaire Surtax": "ultra-millionaire-surtax-3pp",
    "Top Rate to 45%": "top-rate-45",
    "High-Earner Medicare Surcharge 2pp": "medicare-surcharge-2pp",
    # International
    "🌍 Biden GILTI Reform (-$374B)": "gilti-reform",
    "🌍 Repeal FDII (-$158B)": "fdii-repeal",
    "🌍 Pillar Two Adoption (-$80B)": "pillar-two-adoption",
    "🌍 Biden International Package (-$632B)": "international-package",
    # IRS enforcement
    "🔍 IRA Enforcement Funding (-$180B)": "irs-enforcement-ira",
    "🔍 Double IRS Enforcement (-$340B)": "irs-enforcement-double",
    "🔍 High-Income Enforcement (-$250B)": "irs-enforcement-high-income",
    # Drug pricing
    "💊 Expand Drug Negotiation (-$500B)": "drug-negotiation-expand",
    "💊 Universal Insulin Cap ($11B)": "insulin-cap-universal",
    "💊 International Reference Pricing (-$100B)": "drug-reference-pricing",
    "💊 Comprehensive Drug Reform (-$600B)": "drug-reform-comprehensive",
    # Trade / tariffs
    "🏭 Trump Universal 10% Tariff (-$2.17T)": "tariff-universal-10pct",
    "🏭 Trump 60% China Tariff (-$500B)": "tariff-china-60pct",
    "🏭 25% Auto Tariff (-$386B)": "tariff-auto-25pct",
    "🏭 25% Steel/Aluminum Tariff (-$60B)": "tariff-steel-aluminum-25pct",
    "🏭 Reciprocal Tariffs (-$1.5T)": "tariff-reciprocal",
    # Climate / energy
    "🌱 Repeal IRA Clean Energy Credits ($783B)": "ira-clean-energy-repeal",
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": "carbon-tax-50",
    "🌱 Carbon Tax \\$25/ton (-$1.0T)": "carbon-tax-25",
    "🌱 Repeal EV Credits ($182B)": "ev-credit-repeal",
    "🌱 Extend IRA Credits Beyond 2032 ($400B)": "ira-clean-energy-extend",
}

#: Build-local ids for ``CBO_SCORE_MAP`` entries that carry an official score
#: but have **no ``PRESET_POLICIES`` row** — the scoring engine cannot run them,
#: so they are checkable in Build (which quotes official "list prices") and
#: nowhere else. Minted in ``ui/tabs/deficit_target._SCORE_ONLY_ENTRIES``;
#: promoted here in Phase 5 so they resolve in share links and can join an
#: exclusive group. Same rule as the catalog ids: **frozen once shipped**.
SCORE_ONLY_ID_BY_LABEL: dict[str, str] = {
    "📋 Eliminate Mortgage Deduction (-$300B)": "mortgage-deduction-eliminate",
    "📋 Eliminate SALT Deduction (-$1.62T)": "salt-deduction-eliminate",
}

#: Score-map labels that are an *alternative spelling* of an instrument that
#: already has a slug: they reuse it rather than mint a second id, so a link
#: carrying either spelling lands on the same option.
#:
#: Empty since the Phase E provenance pass. It held exactly two entries, both
#: tariff labels that ``CBO_SCORE_MAP`` spelled differently from
#: ``PRESET_POLICIES`` ("25% Steel & Aluminum Tariff (-$60B)" vs "25%
#: Steel/Aluminum Tariff (-$15B)"; "Reciprocal Tariffs (~20pp) (-$1.2T)" vs
#: "Reciprocal Tariffs (-$1.2T)"). The alias made *share links* resolve, but
#: the two dictionaries still never joined on the label, so both presets showed
#: **no official score at all** in the app. The labels are now identical in
#: both dictionaries and the aliases are unnecessary. Kept as an empty dict
#: rather than deleted: the mechanism is the right fix if a score map ever
#: legitimately carries a second spelling.
SCORE_ONLY_ALIAS_ID_BY_LABEL: dict[str, str] = {}

#: Scorable presets first, then the Build-local score-only ids.
ALL_ID_BY_LABEL: dict[str, str] = {**PRESET_ID_BY_LABEL, **SCORE_ONLY_ID_BY_LABEL}

LABEL_BY_PRESET_ID: dict[str, str] = {
    preset_id: label for label, preset_id in ALL_ID_BY_LABEL.items()
}

#: Reverse map restricted to *scorable* presets. ``resolve_preset`` answers from
#: this one: its contract is "a key of ``PRESET_POLICIES``", and callers index
#: the catalog with what it returns.
_CATALOG_LABEL_BY_ID: dict[str, str] = {
    preset_id: label for label, preset_id in PRESET_ID_BY_LABEL.items()
}

#: Every *scorable* preset except the ``Custom Policy`` sentinel. This is the
#: set the values tagger and the distribution engine have to cover, so the
#: score-only ids are deliberately **not** in it.
CATALOG_PRESET_IDS: tuple[str, ...] = tuple(
    preset_id
    for preset_id in PRESET_ID_BY_LABEL.values()
    if preset_id != CUSTOM_POLICY_ID
)

#: Ordering for anything that has to sort a mixed selection (Build packages):
#: catalog order, then the score-only ids.
SELECTABLE_PRESET_IDS: tuple[str, ...] = tuple(
    preset_id for preset_id in LABEL_BY_PRESET_ID if preset_id != CUSTOM_POLICY_ID
)


# ── 2. Overlap structure ────────────────────────────────────────────────
#: Groups where at most one member may be selected: the members are
#: alternative settings of the *same* instrument, so summing two of them
#: double-counts the same revenue. Group ids are stable (they surface in UI
#: copy and, eventually, in share links).
EXCLUSIVE_GROUPS: dict[str, tuple[str, ...]] = {
    # Nested bundles: "no SALT cap" is full extension plus SALT repeal;
    # "rates only" is a strict subset of full extension.
    "tcja-extension": (
        "tcja-full-extension",
        "tcja-extension-no-salt-cap",
        "tcja-rates-only",
    ),
    # The no-SALT-cap bundle already repeals the cap, and eliminating the
    # deduction outright is the same instrument set the other way: summing any
    # two of these double-counts the SALT base.
    "salt-cap": (
        "tcja-extension-no-salt-cap",
        "salt-cap-repeal",
        "salt-deduction-eliminate",
    ),
    "corporate-rate": ("corporate-28pct", "corporate-15pct"),
    # The 2021 expansion supersedes a straight extension of the $2,000 credit.
    "child-tax-credit": ("ctc-expansion-2021", "ctc-extension"),
    "estate-regime": (
        "estate-extend-tcja",
        "estate-exemption-3-5m",
        "estate-repeal",
    ),
    "ss-wage-cap": ("ss-cap-90pct", "ss-donut-250k", "ss-cap-eliminate"),
    "individual-amt": ("amt-extend-tcja-relief", "amt-repeal-individual"),
    "aca-premium-credits": ("aca-ptc-extend-enhanced", "aca-ptc-repeal"),
    # Alternative increases in the top ordinary-income rate; their bases
    # overlap almost entirely.
    "top-marginal-rate": (
        "top-rate-39-6",
        "top-rate-45",
        "millionaire-surtax-5pp",
        "ultra-millionaire-surtax-3pp",
    ),
    "individual-rate-cut": (
        "middle-class-rate-cut-2pp",
        "across-the-board-rate-cut-5pp",
    ),
    # The package is GILTI reform + FDII repeal; deficit_target.py already
    # warns about this one combination in hard-coded form.
    "international-package": (
        "international-package",
        "gilti-reform",
        "fdii-repeal",
    ),
    "irs-enforcement": (
        "irs-enforcement-ira",
        "irs-enforcement-double",
        "irs-enforcement-high-income",
    ),
    "drug-pricing": (
        "drug-negotiation-expand",
        "drug-reference-pricing",
        "drug-reform-comprehensive",
    ),
    "carbon-tax": ("carbon-tax-50", "carbon-tax-25"),
    "ira-clean-energy": ("ira-clean-energy-repeal", "ira-clean-energy-extend"),
    # Two alternative across-the-board tariff regimes. Sectoral tariffs
    # (China/auto/steel) stack on top and stay additive, matching the curated
    # "Trump Trade Agenda" package.
    "tariff-regime": ("tariff-universal-10pct", "tariff-reciprocal"),
}

#: Containment, where mutual exclusion is the wrong shape: the parent bundle
#: already includes the children, but the children combine freely with each
#: other. Selecting a parent should dim its children, not its siblings.
SUBSUMES: dict[str, tuple[str, ...]] = {
    "tcja-full-extension": (
        "ctc-extension",
        "amt-extend-tcja-relief",
        "estate-extend-tcja",
    ),
    "tcja-extension-no-salt-cap": (
        "ctc-extension",
        "amt-extend-tcja-relief",
        "estate-extend-tcja",
    ),
    "drug-reform-comprehensive": ("insulin-cap-universal",),
    "ira-clean-energy-repeal": ("ev-credit-repeal",),
}

_GROUPS_BY_MEMBER: dict[str, tuple[str, ...]] = {}
for _group, _members in EXCLUSIVE_GROUPS.items():
    for _member in _members:
        _GROUPS_BY_MEMBER[_member] = (*_GROUPS_BY_MEMBER.get(_member, ()), _group)


# ── 3. Values tag schema ────────────────────────────────────────────────
TAG_KEYS: tuple[str, ...] = (
    "direction",
    "progressivity",
    "govt_size",
    "base",
    "generational",
)

#: Allowed values per tag, verbatim from REDESIGN_PLAN.md §5b.1.
ALLOWED_TAG_VALUES: dict[str, tuple[str, ...]] = {
    "direction": ("raise_revenue", "cut_revenue", "cut_spending", "add_spending"),
    "progressivity": (
        "strong_progressive",
        "progressive",
        "neutral",
        "regressive",
        "not_modeled",
    ),
    "govt_size": ("shrink", "grow", "neutral"),
    "base": (
        "individual",
        "corporate",
        "payroll",
        "consumption",
        "estate",
        "enforcement",
        "transfer",
    ),
    "generational": ("current", "future", "mixed"),
}


def _load_generated_tags() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Import the generated tag tables, tolerating a missing/partial module.

    A stale or absent generated module must not take the app down; the
    catalog simply carries no tags and ``tests/test_policy_catalog.py``
    fails loudly instead.
    """
    try:
        from fiscal_model.policy_tags_generated import POLICY_TAGS, TAG_SOURCES
    except Exception:  # pragma: no cover - only hit if the file is broken
        return {}, {}
    return dict(POLICY_TAGS), dict(TAG_SOURCES)


POLICY_TAGS, TAG_SOURCES = _load_generated_tags()


def tags_for(token: str) -> dict[str, str]:
    """Five-tag values dict for a preset id or label. Empty if untagged."""
    preset_id = preset_id_for_token(token)
    if preset_id is None:
        return {}
    return dict(POLICY_TAGS.get(preset_id, {}))


def tag_sources_for(token: str) -> dict[str, str]:
    """Per-tag provenance (``engine:…`` / ``fallback:…`` / ``override``)."""
    preset_id = preset_id_for_token(token)
    if preset_id is None:
        return {}
    return dict(TAG_SOURCES.get(preset_id, {}))


def not_modeled_ids() -> tuple[str, ...]:
    """Catalog ids whose ``progressivity`` the app declines to assert."""
    return tuple(
        preset_id
        for preset_id in CATALOG_PRESET_IDS
        if POLICY_TAGS.get(preset_id, {}).get("progressivity") == "not_modeled"
    )


# ── Normalisation and legacy-label resolution ───────────────────────────
_VARIATION_SELECTORS = {"\ufe0e", "\ufe0f"}
_DROPPED_CATEGORIES = {"So", "Sk", "Cf"}


def strip_display_symbols(text: str) -> str:
    """Drop emoji/pictographs and variation selectors from a display label."""
    return "".join(
        ch
        for ch in text
        if ch not in _VARIATION_SELECTORS
        and unicodedata.category(ch) not in _DROPPED_CATEGORIES
    )


def _normalize(token: str) -> str:
    """Fold a token to the form the alias index is keyed on.

    Handles the four ways a legacy label reaches us in the wild: emoji
    prefixes, the ``\\$`` escaping ``app_data`` bakes into two carbon-tax
    labels, arbitrary whitespace from URL round-trips, and case.
    """
    folded = unicodedata.normalize("NFKC", token)
    folded = strip_display_symbols(folded).replace("\\", "")
    return " ".join(folded.split()).strip().lower()


def _score_suffix_stripped(label: str) -> str:
    """Label without its trailing ``(...)`` score annotation."""
    stripped = label.rstrip()
    if not stripped.endswith(")"):
        return label
    depth = 0
    for index in range(len(stripped) - 1, -1, -1):
        if stripped[index] == ")":
            depth += 1
        elif stripped[index] == "(":
            depth -= 1
            if depth == 0:
                return stripped[:index].rstrip()
    return label


def _leading_noise_stripped(label: str) -> str:
    """Mirror ``policy_input_presets._strip_emoji_prefix``.

    That helper drops everything before the first letter or ``(``, which on
    two tariff labels also eats the rate ("25% Auto Tariff" -> "Auto
    Tariff"). Those lossy strings are what the sidebar selectbox shows and
    what old share links therefore carry, so they have to resolve. Mirrored
    rather than imported: ``ui.helpers`` imports this module, so the arrow
    only points one way.
    """
    for ch in label:
        if ch.isalpha() or ch == "(":
            return label[label.index(ch):]
    return label


def _spellings(label: str, preset_id: str) -> tuple[str, ...]:
    """Every form of one preset that a link in the wild might carry."""
    return (
        label,
        preset_id,
        preset_id.replace("-", " "),
        preset_id.replace("-", "_"),
        _score_suffix_stripped(label),
        # The two forms the sidebar actually renders, and that old share
        # links therefore carry.
        _leading_noise_stripped(label),
        _leading_noise_stripped(_score_suffix_stripped(label)),
    )


def _build_index(pairs: Mapping[str, str]) -> dict[str, str]:
    """Map every normalised spelling in ``pairs`` to its (single) target.

    Ambiguous aliases (two entries folding to the same token) are dropped
    rather than resolved arbitrarily.
    """
    candidates: dict[str, set[str]] = {}
    for label, target in pairs.items():
        for alias in _spellings(label, ALL_ID_BY_LABEL.get(label, target)):
            key = _normalize(alias)
            if key:
                candidates.setdefault(key, set()).add(target)
    return {
        alias: next(iter(targets))
        for alias, targets in candidates.items()
        if len(targets) == 1
    }


#: normalised spelling -> canonical *catalog* label.
_ALIAS_INDEX: dict[str, str] = _build_index(
    {label: label for label in PRESET_ID_BY_LABEL}
)

#: normalised spelling -> stable id, for the score-only Build options. Consulted
#: only after ``_ALIAS_INDEX`` misses, so a catalog preset always wins a clash.
_SCORE_ONLY_INDEX: dict[str, str] = _build_index(
    {**SCORE_ONLY_ID_BY_LABEL, **SCORE_ONLY_ALIAS_ID_BY_LABEL}
)


def all_preset_ids() -> tuple[str, ...]:
    """Every known id: catalog order, ``custom-policy``, then score-only ids."""
    return tuple(LABEL_BY_PRESET_ID)


def all_preset_labels() -> tuple[str, ...]:
    """Every canonical preset label, in catalog order."""
    return tuple(PRESET_ID_BY_LABEL)


def preset_id_for_label(label: str) -> str:
    """Stable id for a canonical preset label.

    Raises ``KeyError`` for an unknown label — use :func:`resolve_preset`
    when the input might be a legacy or user-supplied spelling.
    """
    return PRESET_ID_BY_LABEL[label]


def label_for_preset_id(preset_id: str) -> str:
    """Canonical display label for a stable preset id."""
    return LABEL_BY_PRESET_ID[preset_id]


def resolve_preset(token: Any) -> str | None:
    """Canonical preset label for an id *or* any legacy label spelling.

    Accepts, in order: a canonical label, a stable id, the URL-decoded form
    of either, and the emoji-stripped / score-stripped / whitespace-
    normalised / case-folded form of either. Returns ``None`` when nothing
    matches, so callers can fall through to their own default.
    """
    if token is None:
        return None
    text = str(token).strip()
    if not text:
        return None

    for candidate in (text, unquote_plus(text)):
        if candidate in PRESET_ID_BY_LABEL:
            return candidate
        if candidate in _CATALOG_LABEL_BY_ID:
            return _CATALOG_LABEL_BY_ID[candidate]

    for candidate in (text, unquote_plus(text)):
        hit = _ALIAS_INDEX.get(_normalize(candidate))
        if hit is not None:
            return hit
    return None


def preset_id_for_token(token: Any) -> str | None:
    """Stable id for an id *or* any legacy label spelling; ``None`` if unknown.

    Resolves the score-only Build options too (:data:`SCORE_ONLY_ID_BY_LABEL`),
    which :func:`resolve_preset` cannot: they have no ``PRESET_POLICIES`` row,
    so there is no catalog label to return.
    """
    label = resolve_preset(token)
    if label is not None:
        return PRESET_ID_BY_LABEL[label]
    if token is None:
        return None
    text = str(token).strip()
    if not text:
        return None
    for candidate in (text, unquote_plus(text)):
        hit = _SCORE_ONLY_INDEX.get(_normalize(candidate))
        if hit is not None:
            return hit
    return None


# ── Exclusivity helpers for the Build UI ────────────────────────────────
def exclusive_groups_for(
    labels_or_ids: Iterable[Any],
) -> dict[str, list[str]]:
    """Group id → the selected members that belong to it, in catalog order.

    Accepts labels, ids, or a mix. Unknown tokens and presets that are in no
    group are ignored. Every group the selection touches is reported, even
    when only one member is selected — the Build UI needs that to render the
    "pick one" chip *before* a second box is ticked.
    """
    selected: list[str] = []
    for token in labels_or_ids:
        preset_id = preset_id_for_token(token)
        if preset_id is not None and preset_id not in selected:
            selected.append(preset_id)

    ordered = [pid for pid in SELECTABLE_PRESET_IDS if pid in selected]
    groups: dict[str, list[str]] = {}
    for preset_id in ordered:
        for group in _GROUPS_BY_MEMBER.get(preset_id, ()):
            groups.setdefault(group, []).append(preset_id)
    return groups


def conflicting_selections(
    selected: Iterable[Any],
) -> list[tuple[str, list[str]]]:
    """Exclusive groups with two or more members selected: a live double-count.

    Returned in ``EXCLUSIVE_GROUPS`` declaration order so UI copy is stable.
    """
    groups = exclusive_groups_for(selected)
    return [
        (group, groups[group])
        for group in EXCLUSIVE_GROUPS
        if len(groups.get(group, ())) > 1
    ]


def subsumed_selections(
    selected: Iterable[Any],
) -> list[tuple[str, list[str]]]:
    """``(parent, children)`` pairs where a selected bundle contains a selected
    component — the other way a package silently double-counts."""
    selected_ids = {
        pid
        for pid in (preset_id_for_token(token) for token in selected)
        if pid is not None
    }
    conflicts: list[tuple[str, list[str]]] = []
    for parent, children in SUBSUMES.items():
        if parent not in selected_ids:
            continue
        overlap = [child for child in children if child in selected_ids]
        if overlap:
            conflicts.append((parent, overlap))
    return conflicts


def exclusive_groups_of(token: Any) -> tuple[str, ...]:
    """Every exclusive group one preset belongs to (usually zero or one)."""
    preset_id = preset_id_for_token(token)
    return () if preset_id is None else _GROUPS_BY_MEMBER.get(preset_id, ())


# ── Attachment onto the catalog ─────────────────────────────────────────
def attach_catalog_metadata(
    preset_policies: Mapping[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Write ``preset_id`` / exclusivity / ``tags`` onto each preset entry.

    Mutates the entry dicts in place (they are the app's single catalog) and
    returns an id-keyed view of the same dicts. Labels and iteration order
    are untouched — other code still keys on labels.
    """
    by_id: dict[str, dict[str, Any]] = {}
    for label, entry in preset_policies.items():
        preset_id = PRESET_ID_BY_LABEL.get(label)
        if preset_id is None:  # a preset added without an id: leave it alone
            continue
        groups = _GROUPS_BY_MEMBER.get(preset_id, ())
        entry["preset_id"] = preset_id
        entry["exclusive_groups"] = groups
        # Plan §5.3 names a singular field; the plural is authoritative
        # because a few presets (the no-SALT-cap bundle) sit in two groups.
        entry["exclusive_group"] = groups[0] if groups else None
        entry["subsumes"] = SUBSUMES.get(preset_id, ())
        if preset_id in POLICY_TAGS:
            entry["tags"] = dict(POLICY_TAGS[preset_id])
            entry["tag_sources"] = dict(TAG_SOURCES.get(preset_id, {}))
        by_id[preset_id] = entry
    return by_id


__all__ = [
    "ALLOWED_TAG_VALUES",
    "ALL_ID_BY_LABEL",
    "CATALOG_PRESET_IDS",
    "CUSTOM_POLICY_ID",
    "CUSTOM_POLICY_LABEL",
    "EXCLUSIVE_GROUPS",
    "LABEL_BY_PRESET_ID",
    "POLICY_TAGS",
    "PRESET_ID_BY_LABEL",
    "SCORE_ONLY_ALIAS_ID_BY_LABEL",
    "SCORE_ONLY_ID_BY_LABEL",
    "SELECTABLE_PRESET_IDS",
    "SUBSUMES",
    "TAG_KEYS",
    "TAG_SOURCES",
    "all_preset_ids",
    "all_preset_labels",
    "attach_catalog_metadata",
    "conflicting_selections",
    "exclusive_groups_for",
    "exclusive_groups_of",
    "label_for_preset_id",
    "not_modeled_ids",
    "preset_id_for_label",
    "preset_id_for_token",
    "resolve_preset",
    "strip_display_symbols",
    "subsumed_selections",
    "tag_sources_for",
    "tags_for",
]
