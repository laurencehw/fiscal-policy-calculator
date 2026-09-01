"""
Build — assemble a package of scored policies against a deficit target.

This is the live "Budget Builder" surface (``/build``); ``package_builder.py``
is dead code and is *not* this page (``planning/redesign/NOTES.md`` §6.1).

Three things are load-bearing here and worth stating once:

**Sign convention.** Every number on this page follows the engine's convention:
**positive increases the deficit, negative reduces it**. ``CBO_SCORE_MAP``'s
``official_score`` is already in those units (TCJA extension ``+4600``, the SS
donut hole ``-2700``), so the page sums them directly and never flips a sign.

**Per-year vs 10-year.** The checklist quotes 10-year totals, because that is
what CBO/JCT publish. The scoreboard, the waterfall and the target comparison
are all *average annual* — the 10-year total divided by the years in the
baseline window. Both units are labelled everywhere they appear.

**Overlap.** The catalog carries ``exclusive_groups`` ("pick at most one of
these — they are alternative settings of the same instrument") and ``subsumes``
("this bundle already contains those"), from :mod:`fiscal_model.preset_ids`.
Before the redesign the page summed whatever was checked, so ticking all three
Social-Security-cap options triple-counted the same revenue. Selection state is
now reconciled against that structure on every render, *before* the checkboxes
are instantiated, so an impossible package cannot exist — not from clicking,
not from a stale session, and not from a hand-edited share link.

Selection lives in ``st.session_state["build_selection"]`` (a plain list of
build ids) and is mirrored onto the ``dt_<build_id>`` checkbox keys. The list is
the source of truth because Streamlit garbage-collects the state of any widget
it does not instantiate in a run — without it, typing in the search box would
silently un-check every policy the filter hides.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from fiscal_model.preset_ids import (
    EXCLUSIVE_GROUPS,
    SUBSUMES,
    exclusive_groups_of,
    label_for_preset_id,
    preset_id_for_token,
)
from fiscal_model.ui.helpers import (
    TEXTBOOK_LINKS,
    escape_markdown_dollars,
    preset_scoring_category,
)
from fiscal_model.ui.session_state import (
    KEY_BUILD_DROPPED_NOTICE,
    KEY_BUILD_METRIC,
    KEY_BUILD_SEARCH,
    KEY_BUILD_SELECTION,
    KEY_BUILD_SHARE_TOKEN,
    KEY_BUILD_TARGET_PCT,
    KEY_BUILD_TARGET_USD,
)
from fiscal_model.ui.share_links import (
    BUILD_METRIC_PCT_GDP,
    BUILD_METRIC_USD_B,
    decode_build_share,
    encode_build_share,
)

CHECKBOX_KEY_PREFIX = "dt_"

METRIC_PCT_LABEL = "% of GDP"
METRIC_USD_LABEL = "$ billions"
METRIC_LABELS: dict[str, str] = {
    BUILD_METRIC_PCT_GDP: METRIC_PCT_LABEL,
    BUILD_METRIC_USD_B: METRIC_USD_LABEL,
}
METRIC_BY_LABEL: dict[str, str] = {label: key for key, label in METRIC_LABELS.items()}

SIGN_CONVENTION = (
    "Sign convention: **+ increases the deficit**, − reduces it — the same "
    "convention the scoring engine and the official scores use."
)

# ── Catalog assembly ─────────────────────────────────────────────────────
# Four ``CBO_SCORE_MAP`` entries are score-only: they carry an official number
# but have no ``PRESET_POLICIES`` row, so ``preset_ids`` has no slug for them.
# Two are genuinely new options (the mortgage and SALT deduction repeals) and
# get a Build-local id; two are alternative estimates of instruments that *do*
# have a slug, so they reuse it and inherit its exclusivity. Build-local ids are
# still stable — they ship in share URLs — they just are not in the registry
# because the registry is keyed on presets the scoring engine can run.
_SCORE_ONLY_ENTRIES: dict[str, dict[str, str]] = {
    "📋 Eliminate Mortgage Deduction (-$300B)": {
        "build_id": "mortgage-deduction-eliminate",
        "area": "Tax Expenditures",
    },
    "📋 Eliminate SALT Deduction (-$1.2T)": {
        "build_id": "salt-deduction-eliminate",
        "area": "Tax Expenditures",
    },
    "🏭 25% Steel & Aluminum Tariff (-$60B)": {
        "build_id": "tariff-steel-aluminum-25pct",
        "area": "Trade / Tariffs",
    },
    "🏭 Reciprocal Tariffs (~20pp) (-$1.2T)": {  # tilde-ok: catalog label key
        "build_id": "tariff-reciprocal",
        "area": "Trade / Tariffs",
    },
}

#: Display names for the scoring-module categories, matching the wireframe.
_AREA_LABELS: dict[str, str] = {
    "TCJA": "TCJA / Individual",
    "Payroll Tax": "Payroll / Social Security",
    "Premium Tax Credits": "Healthcare",
    "Income Tax": "Individual rates",
    "Tax Expenditures": "Tax expenditures",
    "Tax Credits": "Tax credits",
    "Estate Tax": "Estate",
    "International Tax": "International",
    "IRS Enforcement": "IRS enforcement",
    "Drug Pricing": "Drug pricing",
    "Trade / Tariffs": "Trade / tariffs",
    "Climate / Energy": "Climate / energy",
}

#: Order the areas appear in, within each of the two directional sections.
_AREA_ORDER: tuple[str, ...] = (
    "Payroll / Social Security",
    "Individual rates",
    "TCJA / Individual",
    "Corporate",
    "International",
    "Estate",
    "Tax expenditures",
    "AMT",
    "IRS enforcement",
    "Trade / tariffs",
    "Climate / energy",
    "Tax credits",
    "Healthcare",
    "Drug pricing",
    "Other",
)

#: Human copy for the "pick one" chip. The *structure* is data (preset_ids);
#: only the wording lives here.
_GROUP_LABELS: dict[str, str] = {
    "tcja-extension": "TCJA bundle",
    "salt-cap": "SALT option",
    "corporate-rate": "corporate rate",
    "child-tax-credit": "CTC option",
    "estate-regime": "estate regime",
    "ss-wage-cap": "cap option",
    "individual-amt": "individual AMT option",
    "aca-premium-credits": "ACA credit option",
    "top-marginal-rate": "top-rate option",
    "individual-rate-cut": "rate-cut option",
    "international-package": "international option",
    "irs-enforcement": "enforcement option",
    "drug-pricing": "drug-pricing option",
    "carbon-tax": "carbon tax level",
    "ira-clean-energy": "IRA credit option",
    "tariff-regime": "tariff regime",
}


def group_label(group_id: str) -> str:
    """Human name for an exclusive group, for the ``PICK ONE …`` chip."""
    return _GROUP_LABELS.get(group_id, group_id.replace("-", " "))


@dataclass(frozen=True)
class BuildOption:
    """One checkable row in the Build catalog."""

    build_id: str
    label: str
    #: 10-year official score, deficit convention (+ increases the deficit).
    score: float
    area: str
    source: str
    source_date: str = ""
    exclusive_groups: tuple[str, ...] = ()
    subsumes: tuple[str, ...] = ()
    tags: Mapping[str, str] = field(default_factory=dict)

    @property
    def raises_revenue(self) -> bool:
        return self.score < 0

    @property
    def search_blob(self) -> str:
        return " ".join(
            [self.build_id, self.label, self.area, self.source, *self.tags.values()]
        ).lower()

    @property
    def checkbox_key(self) -> str:
        return f"{CHECKBOX_KEY_PREFIX}{self.build_id}"


def build_catalog(cbo_score_map: Mapping[str, Mapping[str, Any]]) -> dict[str, BuildOption]:
    """Index the checkable Build options by stable build id, in catalog order.

    Driven by ``CBO_SCORE_MAP`` — the Build page quotes *official* scores
    ("list prices"), not live model output — and enriched from the catalog
    schema in ``fiscal_model.app_data`` / ``fiscal_model.preset_ids``.
    """
    try:
        from fiscal_model.app_data import PRESETS_BY_ID
    except Exception:  # pragma: no cover — defensive
        PRESETS_BY_ID = {}

    catalog: dict[str, BuildOption] = {}
    for label, data in cbo_score_map.items():
        score = float(data.get("official_score", 0) or 0)
        if score == 0:
            continue

        extra = _SCORE_ONLY_ENTRIES.get(label, {})
        build_id = extra.get("build_id") or preset_id_for_token(label)
        if not build_id or build_id in catalog:
            continue

        entry = PRESETS_BY_ID.get(build_id) or {}
        area = extra.get("area") or preset_scoring_category(entry) or "Other"
        catalog[build_id] = BuildOption(
            build_id=build_id,
            label=label,
            score=score,
            area=_AREA_LABELS.get(area, area),
            source=str(data.get("source", "") or ""),
            source_date=str(data.get("source_date", "") or ""),
            exclusive_groups=tuple(
                entry.get("exclusive_groups") or exclusive_groups_of(build_id)
            ),
            subsumes=tuple(entry.get("subsumes") or SUBSUMES.get(build_id, ())),
            tags=dict(entry.get("tags") or {}),
        )
    return catalog


# ── Overlap reconciliation ───────────────────────────────────────────────
@dataclass(frozen=True)
class DroppedSelection:
    """One selection removed because it overlapped an earlier one."""

    dropped_id: str
    kept_id: str
    #: ``"exclusive"`` (same instrument, different setting) or ``"subsumed"``.
    reason: str
    group_id: str = ""

    def message(self, catalog: Mapping[str, BuildOption]) -> str:
        dropped = _display_name(self.dropped_id, catalog)
        kept = _display_name(self.kept_id, catalog)
        if self.reason == "subsumed":
            return f"**{dropped}** — already included in **{kept}**"
        return (
            f"**{dropped}** — only one {group_label(self.group_id)} at a time; "
            f"kept **{kept}**"
        )


def _display_name(build_id: str, catalog: Mapping[str, BuildOption]) -> str:
    option = catalog.get(build_id)
    if option is not None:
        return short_name(option.label)
    try:
        return short_name(label_for_preset_id(build_id))
    except KeyError:
        return build_id


def short_name(label: str) -> str:
    """Preset label without its emoji prefix or trailing score annotation."""
    from fiscal_model.preset_ids import strip_display_symbols

    text = strip_display_symbols(str(label)).replace("\\", "").strip()
    if text.endswith(")") and "(" in text:
        text = text[: text.rfind("(")].strip()
    return text or str(label)


def resolve_selection(
    candidate_ids: Iterable[str],
    catalog: Mapping[str, BuildOption],
) -> tuple[list[str], list[DroppedSelection]]:
    """Keep the first member of each overlap, drop the rest.

    Order matters and is honoured: the *first* id wins, so a share link's
    ordering decides which of two conflicting options survives. Two passes:

    1. exclusive groups — an id sharing a group with something already kept is
       dropped;
    2. subsumption — a bundle always beats its components, whichever order they
       arrived in, because that is what the checklist shows (checking a bundle
       disables its components, never the reverse).

    Unknown ids are dropped silently; the caller reports them separately.
    """
    kept: list[str] = []
    claimed_groups: dict[str, str] = {}
    dropped: list[DroppedSelection] = []

    seen: set[str] = set()
    for build_id in candidate_ids:
        if build_id not in catalog or build_id in seen:
            continue
        seen.add(build_id)

        conflict: tuple[str, str] | None = None
        for group in catalog[build_id].exclusive_groups:
            owner = claimed_groups.get(group)
            if owner is not None:
                conflict = (group, owner)
                break
        if conflict is not None:
            dropped.append(
                DroppedSelection(build_id, conflict[1], "exclusive", conflict[0])
            )
            continue

        kept.append(build_id)
        for group in catalog[build_id].exclusive_groups:
            claimed_groups.setdefault(group, build_id)

    # Pass 2: a selected bundle evicts its selected components.
    kept_set = set(kept)
    evicted: dict[str, str] = {}
    for parent in kept:
        for child in catalog[parent].subsumes:
            if child in kept_set and child != parent:
                evicted.setdefault(child, parent)
    if evicted:
        kept = [build_id for build_id in kept if build_id not in evicted]
        dropped.extend(
            DroppedSelection(child, parent, "subsumed")
            for child, parent in evicted.items()
        )

    return kept, dropped


def selection_blockers(
    selection: Sequence[str],
    catalog: Mapping[str, BuildOption],
) -> dict[str, tuple[str, str]]:
    """``build_id -> (reason, blocking_id)`` for every option that must be dimmed.

    ``reason`` is ``"exclusive:<group_id>"`` or ``"subsumed"``. Only unselected
    options are ever blocked — a valid selection never disables itself.
    """
    selected = set(selection)
    blockers: dict[str, tuple[str, str]] = {}

    claimed: dict[str, str] = {}
    for build_id in selection:
        option = catalog.get(build_id)
        if option is None:
            continue
        for group in option.exclusive_groups:
            claimed.setdefault(group, build_id)

    for build_id, option in catalog.items():
        if build_id in selected:
            continue
        for group in option.exclusive_groups:
            owner = claimed.get(group)
            if owner is not None:
                blockers[build_id] = (f"exclusive:{group}", owner)
                break

    for parent in selection:
        option = catalog.get(parent)
        if option is None:
            continue
        for child in option.subsumes:
            if child in catalog and child not in selected:
                blockers[child] = ("subsumed", parent)

    return blockers


# ── Session-state plumbing ───────────────────────────────────────────────
def _session(st_module: Any) -> Any:
    return st_module.session_state


def _stored_selection(st_module: Any) -> list[str]:
    raw = _session(st_module).get(KEY_BUILD_SELECTION) or []
    return [str(item) for item in raw]


def current_selection(st_module: Any, catalog: Mapping[str, BuildOption]) -> list[str]:
    """Selection for this run: checkbox state where it exists, list otherwise.

    A checkbox whose state Streamlit garbage-collected (because the search
    filter hid it last run) falls back to the durable list, so filtering never
    silently drops a policy from the package.
    """
    session = _session(st_module)
    stored = _stored_selection(st_module)
    stored_set = set(stored)

    live: list[str] = []
    for build_id in catalog:
        key = f"{CHECKBOX_KEY_PREFIX}{build_id}"
        try:
            has_widget = key in session
        except Exception:  # pragma: no cover — exotic session stand-ins
            has_widget = False
        if has_widget:
            if bool(session[key]):
                live.append(build_id)
        elif build_id in stored_set:
            live.append(build_id)

    # Preserve the stored order for ids that were already selected; append
    # newly-checked ids after them, so "first wins" stays meaningful.
    order = {build_id: index for index, build_id in enumerate(stored)}
    return sorted(live, key=lambda bid: (order.get(bid, len(order)), bid))


def _write_selection(
    st_module: Any,
    selection: Sequence[str],
    catalog: Mapping[str, BuildOption],
) -> None:
    """Mirror the reconciled selection onto the durable list and the widgets.

    Must run **before** the checkboxes are instantiated: Streamlit refuses to
    assign a widget's key once the widget exists in the current run.
    """
    session = _session(st_module)
    selected = set(selection)
    session[KEY_BUILD_SELECTION] = list(selection)
    for build_id in catalog:
        session[f"{CHECKBOX_KEY_PREFIX}{build_id}"] = build_id in selected


def _record_drops(st_module: Any, dropped: Sequence[DroppedSelection]) -> None:
    if not dropped:
        return
    session = _session(st_module)
    existing = list(session.get(KEY_BUILD_DROPPED_NOTICE) or [])
    session[KEY_BUILD_DROPPED_NOTICE] = existing + list(dropped)


def apply_preselection(
    preset_ids: list[str],
    *,
    st_module: Any = None,
    cbo_score_map: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[str]:
    """Load a package into the Build checklist. **The Phase-3b entry point.**

    Pass stable preset ids (``MixComponent.preset_name`` labels resolve too —
    anything ``preset_ids.resolve_preset`` understands). Overlap conflicts are
    resolved with the same first-wins rule the UI uses, and whatever was
    dropped is queued for the ``st.info`` notice on the next render.

    Returns the ids actually applied. Safe to call from a button callback or
    from the top of a page render; it only touches session state, and it must
    run before the checkboxes are instantiated in the current run.
    """
    if st_module is None:  # pragma: no cover — exercised via the real app
        import streamlit as st_module  # type: ignore[no-redef]

    if cbo_score_map is None:
        from fiscal_model.app_data import CBO_SCORE_MAP

        cbo_score_map = CBO_SCORE_MAP

    catalog = build_catalog(cbo_score_map)

    resolved: list[str] = []
    unknown: list[str] = []
    for token in preset_ids or []:
        candidate = str(token).strip()
        if not candidate:
            continue
        build_id = candidate if candidate in catalog else preset_id_for_token(candidate)
        if build_id and build_id in catalog:
            if build_id not in resolved:
                resolved.append(build_id)
        else:
            unknown.append(candidate)

    kept, dropped = resolve_selection(resolved, catalog)
    _write_selection(st_module, kept, catalog)
    _record_drops(st_module, dropped)
    if unknown:
        session = _session(st_module)
        existing = list(session.get(KEY_BUILD_DROPPED_NOTICE) or [])
        session[KEY_BUILD_DROPPED_NOTICE] = existing + [
            f"**{token}** — not a policy in this catalog" for token in unknown
        ]
    return kept


def restore_build_state_from_query(
    st_module: Any,
    query_params: Mapping[str, Any] | None = None,
    *,
    cbo_score_map: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Restore selection + target from ``/build?policies=…&target=…&metric=…``.

    Applied at most once per distinct link (a hash of the request is stored in
    session state), so a shared link seeds the page and then gets out of the
    way instead of re-clobbering the user's edits on every rerun.
    """
    import hashlib
    import json

    if query_params is None:
        query_params = getattr(st_module, "query_params", {}) or {}

    request = decode_build_share(query_params)
    if not request["preset_ids"] and request["target"] is None:
        return None

    token = hashlib.sha256(
        json.dumps(request, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    session = _session(st_module)
    if session.get(KEY_BUILD_SHARE_TOKEN) == token:
        return None
    session[KEY_BUILD_SHARE_TOKEN] = token

    if request["preset_ids"]:
        apply_preselection(
            request["preset_ids"], st_module=st_module, cbo_score_map=cbo_score_map
        )

    metric = request["metric"]
    session[KEY_BUILD_METRIC] = METRIC_LABELS.get(metric, METRIC_PCT_LABEL)
    if request["target"] is not None:
        if metric == BUILD_METRIC_USD_B:
            session[KEY_BUILD_TARGET_USD] = int(
                max(0, min(2000, round(float(request["target"]) / 100) * 100))
            )
        else:
            session[KEY_BUILD_TARGET_PCT] = float(
                max(0.0, min(6.0, round(float(request["target"]) * 2) / 2))
            )
    return request


# ── Export builders (pure, so they can be tested without Streamlit) ──────
def package_rows(
    selection: Sequence[str],
    catalog: Mapping[str, BuildOption],
    n_years: int,
) -> list[dict[str, Any]]:
    """Table rows for the selected package — plain text, no markdown escaping."""
    rows: list[dict[str, Any]] = []
    for build_id in selection:
        option = catalog.get(build_id)
        if option is None:
            continue
        rows.append(
            {
                "Policy ID": option.build_id,
                "Policy": short_name(option.label),
                "Area": option.area,
                "Direction": (
                    "Revenue raiser" if option.raises_revenue else "Tax cut / spending"
                ),
                "10-Year Impact ($B)": f"{option.score:+,.0f}",
                "Per-Year ($B)": f"{option.score / n_years:+,.0f}",
                "Source": " ".join(
                    part for part in (option.source, option.source_date) if part
                ),
            }
        )
    return rows


def export_header_lines(
    *,
    vintage_label: str,
    window_label: str,
    selection: Sequence[str],
    target_label: str,
    comment_prefix: str = "# ",
) -> list[str]:
    """Provenance header shared by the CSV and the copy-summary export."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "Fiscal Policy Impact Calculator — Build package",
        f"Baseline: CBO {vintage_label}",
        f"Window: {window_label}",
        f"Deficit target: {target_label}",
        "Sign convention: + increases the deficit, - reduces it",
        "Scores are official list prices; interaction effects are not modeled",
        f"Policy ids: {','.join(selection) if selection else '(none selected)'}",
        f"Exported: {stamp}",
    ]
    return [f"{comment_prefix}{line}" for line in lines]


def build_package_csv(
    selection: Sequence[str],
    catalog: Mapping[str, BuildOption],
    n_years: int,
    *,
    vintage_label: str,
    window_label: str,
    target_label: str,
) -> str:
    """CSV export: a commented provenance header, then the package table."""
    header = export_header_lines(
        vintage_label=vintage_label,
        window_label=window_label,
        selection=selection,
        target_label=target_label,
    )
    rows = package_rows(selection, catalog, n_years)
    table = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Policy ID", "Policy"])
    return "\n".join(header) + "\n" + table.to_csv(index=False)


def build_copy_summary(
    selection: Sequence[str],
    catalog: Mapping[str, BuildOption],
    n_years: int,
    *,
    vintage_label: str,
    window_label: str,
    target_label: str,
    baseline_annual: float,
    adjusted_annual: float,
    total_impact: float,
    remaining: float,
    share_url: str,
) -> str:
    """Plain-text package summary, carrying the same provenance as the CSV."""
    lines = export_header_lines(
        vintage_label=vintage_label,
        window_label=window_label,
        selection=selection,
        target_label=target_label,
        comment_prefix="",
    )
    count = len(selection)
    lines += [
        "",
        f"Baseline deficit: ${baseline_annual:,.0f}B/yr",
        f"Package ({count} polic{'y' if count == 1 else 'ies'}): "
        f"${total_impact:+,.0f}B over {n_years} years "
        f"(${total_impact / n_years:+,.0f}B/yr)",
        f"Adjusted deficit: ${adjusted_annual:,.0f}B/yr",
        (
            f"Target met with ${abs(remaining):,.0f}B/yr to spare"
            if remaining <= 0
            else f"Remaining gap to target: ${remaining:,.0f}B/yr"
        ),
        "",
        "Policies:",
    ]
    for build_id in selection:
        option = catalog.get(build_id)
        if option is None:
            continue
        lines.append(
            f"  - {short_name(option.label)} ({option.build_id}): "
            f"${option.score:+,.0f}B / {n_years}yr"
            + (f" [{option.source}]" if option.source else "")
        )
    if not selection:
        lines.append("  (none selected)")
    if share_url:
        lines += ["", f"Share: {share_url}"]
    return "\n".join(lines)


# ── Small presentation helpers ───────────────────────────────────────────
def short_vintage(vintage_date: str | None) -> str:
    """``"February 2026"`` -> ``"Feb 2026"``; anything odd passes through."""
    text = str(vintage_date or "").strip()
    parts = text.split()
    if len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit():
        return f"{parts[0][:3]} {parts[1]}"
    return text or "unknown vintage"


def baseline_vintage(baseline: Any) -> str:
    """Short baseline vintage label — never a hard-coded string.

    ``FiscalPolicyScorer.baseline`` is a ``BaselineProjection``: the generator
    that knows the vintage (``CBOBaseline``) is not retained on it, so the
    lookup falls through to the health snapshot, which is the same payload the
    shared chrome pill reads. One source of truth, three ways in.
    """
    for source in (
        getattr(baseline, "baseline_vintage_date", None),
        (getattr(baseline, "metadata", None) or {}).get("vintage_date")
        if isinstance(getattr(baseline, "metadata", None), Mapping)
        else None,
    ):
        if source:
            return short_vintage(str(source))
    try:
        from fiscal_model.ui.cache import get_health_snapshot

        vintage = (get_health_snapshot().get("baseline") or {}).get("vintage")
    except Exception:  # pragma: no cover — health must never break the page
        vintage = None
    return short_vintage(vintage)


def signed_billions(value: float) -> str:
    """``$+800B`` / ``$-2,700B`` / a plain ``$0B`` at exactly zero."""
    return f"${value:,.0f}B" if round(value) == 0 else f"${value:+,.0f}B"


def window_label(years: Sequence[int]) -> str:
    """``FY2026–2035`` from the baseline's own year vector."""
    if len(years) == 0:
        return "unknown window"
    return f"FY{int(years[0])}–{int(years[-1])}"


def _area_sort_key(area: str) -> tuple[int, str]:
    try:
        return (_AREA_ORDER.index(area), area)
    except ValueError:
        return (len(_AREA_ORDER), area)


def _matches_search(option: BuildOption, needles: Sequence[str]) -> bool:
    blob = option.search_blob
    return all(needle in blob for needle in needles)


# ── The page ─────────────────────────────────────────────────────────────
def render_deficit_target_tab(
    st_module: Any,
    cbo_score_map: dict[str, dict[str, Any]],
    fiscal_policy_scorer_cls: Any,
    use_real_data: bool = False,
) -> None:
    """Render the Build page: policy checklist left, sticky scoreboard right."""
    catalog = build_catalog(cbo_score_map)

    # ---- 1. Reconcile selection BEFORE any widget is instantiated ---------
    selection, dropped = resolve_selection(current_selection(st_module, catalog), catalog)
    _record_drops(st_module, dropped)
    _write_selection(st_module, selection, catalog)
    blockers = selection_blockers(selection, catalog)

    # ---- 2. Baseline ------------------------------------------------------
    scorer = fiscal_policy_scorer_cls(use_real_data=use_real_data)
    baseline = scorer.baseline
    if len(baseline.deficit) == 0 or len(baseline.nominal_gdp) == 0:
        st_module.error("Baseline data unavailable.")
        return

    n_years = max(1, len(baseline.years))
    vintage = baseline_vintage(baseline)
    window = window_label(list(baseline.years))
    baseline_annual = float(baseline.deficit.mean())
    baseline_gdp = float(baseline.nominal_gdp.mean())
    baseline_pct = baseline_annual / baseline_gdp * 100 if baseline_gdp > 0 else 0.0

    # ---- 3. Header + target strip ----------------------------------------
    st_module.subheader("Build a package")
    st_module.markdown(
        "Check policies to include; totals update as you go. Scores are "
        "official **list prices** — interactions between policies are not "
        "modeled. " + SIGN_CONVENTION
    )

    strip_metric, strip_target, strip_search = st_module.columns([2, 3, 3])
    with strip_metric:
        metric_label = _render_metric_toggle(st_module)
    metric_key = METRIC_BY_LABEL.get(metric_label, BUILD_METRIC_PCT_GDP)

    with strip_target:
        if metric_key == BUILD_METRIC_PCT_GDP:
            target_value: float = float(
                st_module.slider(
                    "Target deficit (% of GDP)",
                    min_value=0.0,
                    max_value=6.0,
                    step=0.5,
                    key=KEY_BUILD_TARGET_PCT,
                    # ``value=`` is only passed when session state is empty:
                    # supplying both makes Streamlit log a warning on every run.
                    **({} if _has_session_value(st_module, KEY_BUILD_TARGET_PCT)
                       else {"value": 3.0}),
                    help=(
                        f"Baseline: ~{baseline_pct:.1f}%. Economists often cite "
                        "3% as sustainable."
                    ),
                )
            )
            target_deficit = target_value / 100 * baseline_gdp
            target_label = f"{target_value:.1f}% of GDP"
        else:
            target_value = float(
                st_module.slider(
                    "Target deficit ($B/year)",
                    min_value=0,
                    max_value=2000,
                    step=100,
                    key=KEY_BUILD_TARGET_USD,
                    **({} if _has_session_value(st_module, KEY_BUILD_TARGET_USD)
                       else {"value": 1000}),
                    help=f"Baseline: \\~${baseline_annual:,.0f}B/year.",
                )
            )
            target_deficit = float(target_value)
            target_label = f"${target_value:,.0f}B/yr"

    with strip_search:
        search_text = st_module.text_input(
            f"Search {len(catalog)} scored policies",
            key=KEY_BUILD_SEARCH,
            placeholder="e.g. tariff, estate, ss-donut-250k",
        )
    needles = [token for token in str(search_text or "").lower().split() if token]

    _render_dropped_notice(st_module, catalog)

    # ---- 4. Totals --------------------------------------------------------
    total_impact = sum(catalog[bid].score for bid in selection)
    annual_impact = total_impact / n_years
    adjusted_annual = baseline_annual + annual_impact
    adjusted_pct = adjusted_annual / baseline_gdp * 100 if baseline_gdp > 0 else 0.0
    remaining = adjusted_annual - target_deficit

    # ---- 5. Two columns: checklist | sticky scoreboard --------------------
    checklist_col, scoreboard_col = st_module.columns([3, 2])

    with checklist_col:
        _render_checklist(
            st_module,
            catalog=catalog,
            selection=selection,
            blockers=blockers,
            needles=needles,
            n_years=n_years,
        )

    with scoreboard_col, _keyed_container(st_module, "build_scoreboard"):
        _render_scoreboard(
            st_module,
            catalog=catalog,
            selection=selection,
            n_years=n_years,
            baseline_annual=baseline_annual,
            baseline_pct=baseline_pct,
            adjusted_annual=adjusted_annual,
            adjusted_pct=adjusted_pct,
            total_impact=total_impact,
            target_deficit=target_deficit,
            target_label=target_label,
            remaining=remaining,
            metric_key=metric_key,
            target_value=target_value,
            vintage=vintage,
            window=window,
        )

    with st_module.expander("Why a deficit target?", expanded=False):
        st_module.markdown(
            "The federal government spends more than it collects each year; "
            "that gap — the **deficit** — adds to the national debt. CBO "
            "projects large, persistent deficits over the next decade. "
            "Persistent deficits can raise interest rates, crowd out private "
            "investment, and limit the government's ability to respond to "
            "future crises. Many economists treat a deficit near **3% of "
            "GDP** as sustainable — debt then grows no faster than the "
            "economy.\n\n"
            "**Learn more:** "
            f"[The Federal Budget]({TEXTBOOK_LINKS['federal_budget']}) · "
            "[Deficits, Debt & Fiscal Sustainability]"
            f"({TEXTBOOK_LINKS['fiscal_sustainability']})"
        )


def _render_metric_toggle(st_module: Any) -> str:
    """Metric toggle — segmented control where available, radio otherwise."""
    options = [METRIC_PCT_LABEL, METRIC_USD_LABEL]
    segmented = getattr(st_module, "segmented_control", None)
    if segmented is not None:
        # ``required=True`` stops a second click from deselecting the toggle
        # and leaving the page with no metric at all. The kwarg is newer than
        # the widget, hence the two-step call.
        seeded = _has_session_value(st_module, KEY_BUILD_METRIC)
        for extra in ({"required": True}, {}):
            try:
                choice = segmented(
                    "Target metric",
                    options,
                    key=KEY_BUILD_METRIC,
                    **({} if seeded else {"default": METRIC_PCT_LABEL}),
                    **extra,
                )
            except TypeError:  # pragma: no cover — older signature / fakes
                continue
            return choice if choice in METRIC_BY_LABEL else METRIC_PCT_LABEL
    choice = st_module.radio(
        "Target metric", options, horizontal=True, key=KEY_BUILD_METRIC
    )
    return choice if choice in METRIC_BY_LABEL else METRIC_PCT_LABEL


def _has_session_value(st_module: Any, key: str) -> bool:
    """True when session state already holds ``key`` (so skip ``default=``)."""
    try:
        return _session(st_module).get(key) is not None
    except Exception:  # pragma: no cover — exotic session stand-ins
        return False


def _keyed_container(st_module: Any, key: str) -> Any:
    """``st.container(key=…)`` so the CSS has a stable class to hook onto."""
    container = getattr(st_module, "container", None)
    if container is None:  # pragma: no cover — minimal test fakes
        return _NullContext()
    try:
        return container(key=key)
    except TypeError:  # pragma: no cover — Streamlit < 1.51
        return container()


class _NullContext:  # pragma: no cover — minimal test fakes only
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: Any) -> bool:
        return False


def _render_dropped_notice(st_module: Any, catalog: Mapping[str, BuildOption]) -> None:
    """Explain anything the overlap guardrails removed, then clear the queue."""
    session = _session(st_module)
    queued = session.get(KEY_BUILD_DROPPED_NOTICE) or []
    if not queued:
        return
    session[KEY_BUILD_DROPPED_NOTICE] = None

    lines = [
        item.message(catalog) if isinstance(item, DroppedSelection) else str(item)
        for item in queued
    ]
    st_module.info(
        "Some options were dropped because they overlap ones you already "
        "have — they price the same instrument twice:\n\n"
        + "\n".join(f"- {line}" for line in lines)
    )


def _render_checklist(
    st_module: Any,
    *,
    catalog: Mapping[str, BuildOption],
    selection: Sequence[str],
    blockers: Mapping[str, tuple[str, str]],
    needles: Sequence[str],
    n_years: int,
) -> None:
    """Two directional sections, each grouped into collapsible policy areas."""
    del n_years
    selected = set(selection)

    sections = [
        (
            ":green[**Revenue raisers**] — reduce the deficit",
            [opt for opt in catalog.values() if opt.raises_revenue],
            "saves",
        ),
        (
            ":red[**Tax cuts & new spending**] — increase the deficit",
            [opt for opt in catalog.values() if not opt.raises_revenue],
            "costs",
        ),
    ]

    hidden_selected = 0
    for heading, options, verb in sections:
        visible = [opt for opt in options if _matches_search(opt, needles)]
        visible_ids = {opt.build_id for opt in visible}
        hidden_selected += sum(
            1
            for opt in options
            if opt.build_id in selected and opt.build_id not in visible_ids
        )
        st_module.markdown(f"##### {heading}")
        if not visible:
            st_module.caption("No policies match your search.")
            continue

        by_area: dict[str, list[BuildOption]] = {}
        for option in visible:
            by_area.setdefault(option.area, []).append(option)

        for area in sorted(by_area, key=_area_sort_key):
            area_options = by_area[area]
            has_selection = any(opt.build_id in selected for opt in area_options)
            with st_module.expander(
                f"**{area}** ({len(area_options)})",
                expanded=bool(needles) or has_selection,
            ):
                _render_area(
                    st_module,
                    area_options,
                    selected=selected,
                    blockers=blockers,
                    catalog=catalog,
                    verb=verb,
                )

    if hidden_selected:
        st_module.caption(
            f"{hidden_selected} selected polic"
            f"{'y is' if hidden_selected == 1 else 'ies are'} hidden by your "
            "search — still counted in the totals."
        )


def _render_area(
    st_module: Any,
    options: Sequence[BuildOption],
    *,
    selected: set[str],
    blockers: Mapping[str, tuple[str, str]],
    catalog: Mapping[str, BuildOption],
    verb: str,
) -> None:
    """Render one policy area, exclusive groups first with their PICK ONE chip."""
    remaining = list(options)
    rendered: set[str] = set()

    for group_id in EXCLUSIVE_GROUPS:
        members = [
            opt
            for opt in remaining
            if group_id in opt.exclusive_groups and opt.build_id not in rendered
        ]
        if len(members) < 2:
            continue
        st_module.markdown(
            f":orange-badge[PICK ONE {group_label(group_id).upper()}]"
        )
        for option in members:
            _render_option(
                st_module,
                option,
                selected=selected,
                blockers=blockers,
                catalog=catalog,
                verb=verb,
            )
            rendered.add(option.build_id)

    for option in remaining:
        if option.build_id in rendered:
            continue
        _render_option(
            st_module,
            option,
            selected=selected,
            blockers=blockers,
            catalog=catalog,
            verb=verb,
        )


def _render_option(
    st_module: Any,
    option: BuildOption,
    *,
    selected: set[str],
    blockers: Mapping[str, tuple[str, str]],
    catalog: Mapping[str, BuildOption],
    verb: str,
) -> None:
    """One checkbox, dimmed and disabled when an overlap already covers it."""
    blocker = blockers.get(option.build_id)
    name = short_name(option.label)
    amount = f"${abs(option.score):,.0f}B"
    # Checkbox labels render as markdown; a lone second "$" turns the rest of
    # the label into LaTeX, so both dollar signs stay escaped.
    text = escape_markdown_dollars(f"{name} — {verb} {amount}")
    if blocker is not None:
        text = f":gray[{text}]"

    st_module.checkbox(
        text,
        key=option.checkbox_key,
        disabled=blocker is not None,
        help=(
            f"`{option.build_id}` · {option.source} {option.source_date} · "
            f"10-year total"
        ).strip(),
    )

    if blocker is None:
        return
    reason, blocking_id = blocker
    blocking_name = _display_name(blocking_id, catalog)
    if reason == "subsumed":
        st_module.caption(f"↳ included in {blocking_name}")
    else:
        st_module.caption(f"↳ mutually exclusive with {blocking_name}")


def _render_scoreboard(
    st_module: Any,
    *,
    catalog: Mapping[str, BuildOption],
    selection: Sequence[str],
    n_years: int,
    baseline_annual: float,
    baseline_pct: float,
    adjusted_annual: float,
    adjusted_pct: float,
    total_impact: float,
    target_deficit: float,
    target_label: str,
    remaining: float,
    metric_key: str,
    target_value: float,
    vintage: str,
    window: str,
) -> None:
    """The sticky right-hand panel: totals, progress, waterfall, exports."""
    count = len(selection)
    annual_impact = total_impact / n_years

    st_module.markdown("##### Your package")
    st_module.metric(
        "Baseline deficit",
        f"${baseline_annual:,.0f}B/yr",
        delta=f"{baseline_pct:.1f}% of GDP",
        delta_color="off",
    )
    st_module.metric(
        f"Your package ({count} polic{'y' if count == 1 else 'ies'})",
        f"{signed_billions(annual_impact)}/yr",
        delta=f"{signed_billions(total_impact)} over {n_years} years",
        delta_color="off",
    )
    st_module.metric(
        "Adjusted deficit",
        f"${adjusted_annual:,.0f}B/yr",
        delta=f"{adjusted_pct:.1f}% of GDP",
        delta_color="off",
    )
    if remaining <= 0:
        st_module.metric(
            f"Gap to {target_label}",
            "Target met",
            delta=f"${abs(remaining):,.0f}B/yr below target",
            delta_color="normal",
        )
    else:
        st_module.metric(
            f"Remaining gap to {target_label}",
            f"${remaining:,.0f}B/yr",
            delta="more cuts needed",
            delta_color="inverse",
        )

    denominator = baseline_annual - target_deficit
    if denominator > 0:
        progress = max(0.0, min(1.0, (baseline_annual - adjusted_annual) / denominator))
    else:
        progress = 1.0
    st_module.progress(
        progress, text=f"Progress toward {target_label}: {progress * 100:.0f}%"
    )

    _render_waterfall(
        st_module,
        catalog=catalog,
        selection=selection,
        n_years=n_years,
        baseline_annual=baseline_annual,
        adjusted_annual=adjusted_annual,
        target_deficit=target_deficit,
        target_label=target_label,
    )

    _render_exports(
        st_module,
        catalog=catalog,
        selection=selection,
        n_years=n_years,
        vintage=vintage,
        window=window,
        target_label=target_label,
        metric_key=metric_key,
        target_value=target_value,
        baseline_annual=baseline_annual,
        adjusted_annual=adjusted_annual,
        total_impact=total_impact,
        remaining=remaining,
    )

    st_module.caption(
        f"Scored against CBO {vintage} baseline · list prices, no interaction "
        "effects · overlapping options are mutually exclusive"
    )


def _render_waterfall(
    st_module: Any,
    *,
    catalog: Mapping[str, BuildOption],
    selection: Sequence[str],
    n_years: int,
    baseline_annual: float,
    adjusted_annual: float,
    target_deficit: float,
    target_label: str,
) -> None:
    per_year_note = f"per-year, {n_years}-yr totals ÷ {n_years}"
    if not selection:
        st_module.caption(
            f"Waterfall — baseline → policies → adjusted ({per_year_note}). "
            "Check a policy to see it."
        )
        return

    labels = ["Baseline"]
    values: list[float] = [baseline_annual]
    measures = ["absolute"]
    for build_id in selection:
        option = catalog[build_id]
        name = short_name(option.label)
        labels.append(name[:28] + "…" if len(name) > 28 else name)
        values.append(option.score / n_years)
        measures.append("relative")
    labels.append("Adjusted")
    values.append(adjusted_annual)
    measures.append("total")

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=labels,
            y=values,
            text=[
                f"${value:+,.0f}B" if measure == "relative" else f"${value:,.0f}B"
                for value, measure in zip(values, measures)
            ],
            textposition="outside",
            increasing={"marker": {"color": "#dc3545"}},
            decreasing={"marker": {"color": "#28a745"}},
            totals={"marker": {"color": "#1f77b4"}},
        )
    )
    fig.add_hline(
        y=target_deficit,
        line_dash="dash",
        line_color="orange",
        annotation_text=f"Target: {target_label}",
        annotation_position="top right",
    )
    fig.update_layout(
        title={
            "text": f"Waterfall — baseline → policies → adjusted ({per_year_note})",
            "font": {"size": 13},
        },
        margin=dict(l=10, r=10, t=45, b=90),
        height=380,
        yaxis_title="Average annual deficit ($B)",
        xaxis_tickangle=-45,
        showlegend=False,
    )
    st_module.plotly_chart(fig)
    st_module.caption(
        f"Bars are **average annual** effects ({per_year_note}); the checklist "
        "quotes 10-year totals, which is how CBO and JCT publish them."
    )


def _render_exports(
    st_module: Any,
    *,
    catalog: Mapping[str, BuildOption],
    selection: Sequence[str],
    n_years: int,
    vintage: str,
    window: str,
    target_label: str,
    metric_key: str,
    target_value: float,
    baseline_annual: float,
    adjusted_annual: float,
    total_impact: float,
    remaining: float,
) -> None:
    """Share link · CSV · copy summary, all carrying the same provenance."""
    share_url = encode_build_share(list(selection), target_value, metric_key)
    csv_data = build_package_csv(
        selection,
        catalog,
        n_years,
        vintage_label=vintage,
        window_label=window,
        target_label=target_label,
    )
    summary = build_copy_summary(
        selection,
        catalog,
        n_years,
        vintage_label=vintage,
        window_label=window,
        target_label=target_label,
        baseline_annual=baseline_annual,
        adjusted_annual=adjusted_annual,
        total_impact=total_impact,
        remaining=remaining,
        share_url=share_url,
    )

    share_col, csv_col, copy_col = st_module.columns(3)
    with share_col, _disclosure(st_module, "Share link"):
        st_module.caption("Restores this package and target.")
        st_module.code(share_url, language=None)
    with csv_col:
        st_module.download_button(
            "Download CSV",
            data=csv_data,
            file_name="build_package.csv",
            mime="text/csv",
            key="build_download_csv",
        )
    with copy_col, _disclosure(st_module, "Copy summary"):
        st_module.code(summary, language=None)

    if selection:
        rows = package_rows(selection, catalog, n_years)
        with st_module.expander(f"Selected policies ({len(rows)})", expanded=False):
            st_module.dataframe(pd.DataFrame(rows), hide_index=True)


def _disclosure(st_module: Any, label: str) -> Any:
    """Popover where available, expander otherwise (mirrors components.chrome)."""
    popover = getattr(st_module, "popover", None)
    if popover is not None:
        try:
            return popover(label, width="stretch")
        except TypeError:  # pragma: no cover — older signature / test fakes
            return popover(label)
    return st_module.expander(label, expanded=False)
