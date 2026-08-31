"""
Package Studio tab — describe a fiscal philosophy, get scored policy mixes.

Pipeline (see ``fiscal_model/composer/``):

    free text ──(translate_goal_text)──▶ GoalSpec ──(compose_and_score)──▶ [ScoredMix]

Only the translation step is model-driven; the mixes themselves are composed
deterministically from the preset library and scored by the validated engine.
That split is why this tab can carry an exploratory (🔵) badge on the *interface*
while the numbers underneath come from the green-tier core — and why the canned
philosophies work with no API key at all.

Honesty rules this tab enforces (they are load-bearing, not decoration):

* every mix renders its own ``caveats`` plus two fixed captions — components
  are scored independently (no interaction effects), and the distribution
  table covers the revenue side only;
* component rows show their tier, legal status, and — where the underlying
  preset is calibrated to a published score — how the model compares to that
  benchmark, so a reader never mistakes a reconstruction for a prediction;
* every chart ships an accessible description and a data table
  (:func:`fiscal_model.ui.a11y.render_accessible_chart`).

The composer and translator are imported lazily inside
:func:`_compose_and_score` / :func:`_translate_goal_text` so this module stays
importable (and testable) without them, and so tests can swap in fakes.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from fiscal_model.composer.goal_spec import CANNED_GOAL_SPECS
from fiscal_model.ui.a11y import (
    ChartDescription,
    format_currency_rows,
    render_accessible_chart,
)
from fiscal_model.ui.charts import (
    COLOR_DEFICIT_DOWN,
    COLOR_DEFICIT_UP,
    apply_base_layout,
)
from fiscal_model.ui.helpers import escape_markdown_dollars

# ── Fixed, always-rendered honesty text ──────────────────────────────────
MATURITY_CAPTION = (
    "🔵 *Experimental interface powered by the validated scoring core.* "
    "Composed mixes are illustrative packages, not validated estimates."
)
CAVEAT_INTERACTIONS = (
    "Components are scored independently; interactions between policies are "
    "not modeled."
)
CAVEAT_REVENUE_ONLY = (
    "Distribution covers the revenue side only; spending incidence is not "
    "modeled."
)

_PLACEHOLDER = (
    "e.g. Fund universal pre-K and a big infrastructure push, pay for it at "
    "the top of the income distribution, and don't raise taxes on anyone "
    "under $400K."
)

# Session-state keys (private to this tab, mirroring the Ask tab's convention).
_TEXT_KEY = "_ps_goal_text"
_CANNED_KEY = "_ps_canned_choice"
_RESULT_KEY = "_ps_last_result"

_N_MIXES = 3

# Tier chips. Deliberately *not* the 🟢/🟡/🔵 maturity dots: those grade the
# app's feature tiers, and reusing them per component would imply a maturity
# claim the composer isn't making.
_TIER_CHIPS: dict[str, str] = {
    "calibrated": "🎯 Calibrated preset",
    "generic": "📐 Generic model build",
    "spending": "🧾 Uncalibrated spending build",
}


# ── Lazy bridges to the composer package ─────────────────────────────────
#
# Imported inside the functions so the tab renders (and its tests run) even
# when the composer/translator modules are absent, and so tests can monkeypatch
# these two names with fakes.


def _compose_and_score(spec: Any, n_mixes: int = _N_MIXES) -> list[Any]:
    """Score ``n_mixes`` package variants for a GoalSpec."""
    from fiscal_model.composer.composer import compose_and_score

    return compose_and_score(spec, n_mixes=n_mixes)


def _translate_goal_text(text: str) -> tuple[Any | None, str]:
    """Translate free text into a GoalSpec; ``(None, reason)`` when it can't."""
    from fiscal_model.composer.translate import translate_goal_text

    return translate_goal_text(text)


# ── Small helpers ────────────────────────────────────────────────────────


def _input_hash(mode: str, value: str) -> str:
    """Stable cache key for one composition input."""
    digest = hashlib.sha256(f"{mode}:{value}".encode()).hexdigest()
    return f"{mode}:{digest[:16]}"


def _anthropic_key_available(st_module: Any) -> bool:
    """True when a key is reachable, promoting ``st.secrets`` → env like Ask.

    Streamlit Cloud surfaces deployment secrets via ``st.secrets`` rather than
    environment variables, so mirror the Ask tab and bridge the gap once.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True

    secrets = getattr(st_module, "secrets", None)
    if secrets is None:
        return False
    try:
        value = secrets["ANTHROPIC_API_KEY"]
    except Exception:
        value = getattr(secrets, "ANTHROPIC_API_KEY", None)
    if isinstance(value, str) and value:
        os.environ["ANTHROPIC_API_KEY"] = value
        return True
    return False


def _money(value: float) -> str:
    """Format billions with an explicit sign, for raw-text widgets.

    Use this for ``st.metric`` values and dataframe cells, which render text
    verbatim. Markdown needs :func:`_money_md` instead.
    """
    return f"${value:+,.0f}B"


def _money_md(value: float) -> str:
    """Format billions for markdown: sign *outside* the ``$``, then escaped.

    ``escape_markdown_dollars`` only escapes a ``$`` that is followed by a
    digit, so ``$-1,250B`` would slip through unescaped and turn the line into
    LaTeX math the moment a second amount appears. Putting the sign first
    (``-$1,250B``) keeps the shared escape effective.
    """
    return escape_markdown_dollars(f"{'+' if value >= 0 else '-'}${abs(value):,.0f}B")


def _deficit_direction(total: float) -> str:
    if total > 0:
        return "Increases the deficit"
    if total < 0:
        return "Reduces the deficit"
    return "Deficit-neutral as scored"


def _status_cell(status: Any) -> str:
    """Render a PolicyStatus as ``icon label``; empty string when absent."""
    if status is None:
        return ""
    icon = getattr(status, "icon", "")
    label = getattr(status, "label", "") or getattr(status, "status", "")
    return f"{icon} {label}".strip()


def _benchmark_cell(badge: dict[str, Any] | None) -> str:
    """One-line 'calibrated vs official benchmark' note from a badge payload."""
    if not badge:
        return ""
    official = badge.get("official")
    model = badge.get("model")
    source = badge.get("source") or "official score"
    signed = badge.get("signed_pct")
    if official is None or model is None:
        return f"Calibrated vs {source}"
    note = f"Calibrated vs {source}: official {_money(float(official))}, model {_money(float(model))}"
    if isinstance(signed, int | float):
        note += f" ({float(signed):+.1f}%)"
    return note


# ── Rendering ────────────────────────────────────────────────────────────


def render_package_studio_tab(st_module: Any) -> None:
    """Render the Package Studio tab.

    Args:
        st_module: Streamlit module (injected for testability).
    """
    state = st_module.session_state

    st_module.header("🧭 Package Studio")
    st_module.caption(MATURITY_CAPTION)
    st_module.markdown(
        "Describe the fiscal package you have in mind — what it should buy and "
        "who should pay for it. The description is translated into a structured "
        "goal, and a deterministic composer assembles two or three candidate "
        "mixes from the preset policy library, each scored by the same engine "
        "the Calculator uses. Compare them on deficit impact, composition, and "
        "who bears the revenue side."
    )

    have_key = _anthropic_key_available(st_module)
    if not have_key:
        _render_no_key_notice(st_module)

    text, canned_choice, compose_clicked = _render_inputs(
        st_module, have_key=have_key
    )

    _maybe_compose(
        st_module,
        state=state,
        text=text,
        canned_choice=canned_choice,
        compose_clicked=compose_clicked,
        have_key=have_key,
    )

    cached = state.get(_RESULT_KEY)
    if not cached:
        st_module.info(
            "Pick a philosophy (or describe one) and press **Compose package "
            "mixes** to see scored candidates."
        )
        return

    _render_results(st_module, cached)


def _render_no_key_notice(st_module: Any) -> None:
    """Explain plainly that free text needs a key, and point at the canned list."""
    st_module.info(
        "✍️ **Free-text descriptions need an `ANTHROPIC_API_KEY`**, and this "
        "deployment doesn't have one configured. Everything else on this tab "
        "still works: pick one of the canned philosophies below — each maps to "
        "a fixed goal spec and is composed and scored entirely offline."
    )
    with st_module.expander("How to set the key", expanded=False):
        st_module.markdown(
            "**Streamlit Cloud** — Settings → Secrets, add:\n\n"
            "```toml\n"
            'ANTHROPIC_API_KEY = "sk-ant-..."\n'
            "```\n\n"
            "**Local** — set an env var before launching:\n\n"
            "```bash\n"
            "export ANTHROPIC_API_KEY=sk-ant-...\n"
            "streamlit run app.py\n"
            "```"
        )


def _render_inputs(st_module: Any, *, have_key: bool) -> tuple[str, str, bool]:
    """Render the description box, canned selector, and Compose button."""
    canned_names = list(CANNED_GOAL_SPECS)

    text = st_module.text_area(
        "Describe what you want a fiscal package to do…",
        placeholder=_PLACEHOLDER,
        height=120,
        key=_TEXT_KEY,
        disabled=not have_key,
        help=(
            "Plain English. Say what you want funded and where the money should "
            "come from."
            if have_key
            else "Unavailable without an API key — use the canned philosophies."
        ),
    )

    cols = st_module.columns([3, 1])
    with cols[0]:
        canned_choice = st_module.selectbox(
            "…or start from a canned philosophy",
            canned_names,
            index=0,
            key=_CANNED_KEY,
            help=(
                "Fixed goal specs that always work — no API key, no translation "
                "step."
            ),
        )
    with cols[1]:
        compose_clicked = st_module.button(
            "Compose package mixes",
            type="primary",
            use_container_width=True,
        )

    fallback = canned_names[0] if canned_names else ""
    return (text or ""), (canned_choice or fallback), bool(compose_clicked)


def _resolve_spec(
    st_module: Any,
    *,
    text: str,
    canned_choice: str,
    have_key: bool,
) -> tuple[Any | None, str, str]:
    """Resolve the input into ``(spec, cache_mode, source_label)``.

    Free text is translated when a key is available; every other path (no key,
    empty box, refused translation, invalid spec) falls back to the canned
    selection, which is always usable.
    """
    use_text = bool(text.strip()) and have_key
    if use_text:
        try:
            spec, reason = _translate_goal_text(text.strip())
        except Exception as exc:  # translation is best-effort, never fatal
            spec, reason = None, f"{type(exc).__name__}: {exc}"
        if spec is None:
            st_module.info(
                escape_markdown_dollars(
                    f"Couldn't turn that description into a goal spec: "
                    f"{reason or 'no reason given'}. Using the canned "
                    f"philosophy **{canned_choice}** instead."
                )
            )
        else:
            problems = list(spec.validate()) if hasattr(spec, "validate") else []
            if problems:
                st_module.warning(
                    escape_markdown_dollars(
                        "The translated goal spec didn't validate ("
                        + "; ".join(problems)
                        + f"). Using the canned philosophy **{canned_choice}** "
                        "instead."
                    )
                )
            else:
                return spec, _input_hash("text", text.strip()), "your description"

    spec = CANNED_GOAL_SPECS.get(canned_choice)
    if spec is None:
        return None, "", canned_choice
    return spec, _input_hash("canned", canned_choice), canned_choice


def _maybe_compose(
    st_module: Any,
    *,
    state: Any,
    text: str,
    canned_choice: str,
    compose_clicked: bool,
    have_key: bool,
) -> None:
    """Compose + score on click, reusing the cached result for the same input."""
    if not compose_clicked:
        return

    # The free-text path makes a network call inside _resolve_spec — keep a
    # spinner over it or the page looks frozen for the whole round-trip
    # (the canned path resolves instantly, so the spinner never shows).
    with st_module.spinner("Reading your description…"):
        spec, cache_key, source_label = _resolve_spec(
            st_module, text=text, canned_choice=canned_choice, have_key=have_key
        )
    if spec is None:
        st_module.warning(
            "No usable goal spec — pick a canned philosophy to compose a package."
        )
        return

    cached = state.get(_RESULT_KEY)
    if cached and cached.get("key") == cache_key:
        # Same input as the stored run: reuse it rather than re-scoring.
        return

    with st_module.spinner("Composing and scoring policy mixes…"):
        try:
            mixes = list(_compose_and_score(spec, n_mixes=_N_MIXES))
        except ImportError:
            st_module.error(
                "The policy composer isn't available in this build, so no mix "
                "can be scored. Everything else on this tab is unaffected."
            )
            return
        except Exception as exc:
            st_module.error(f"Could not compose a package: {type(exc).__name__}: {exc}")
            return

    if not mixes:
        st_module.warning(
            "The composer returned no mixes for that goal — try a different "
            "philosophy or a simpler description."
        )
        return

    state[_RESULT_KEY] = {
        "key": cache_key,
        "mixes": mixes,
        "source_label": source_label,
        "notes": getattr(spec, "notes", "") or "",
    }


def _render_results(st_module: Any, cached: dict[str, Any]) -> None:
    """Render the comparison row plus one stacked detail section per mix."""
    mixes = list(cached.get("mixes") or [])
    if not mixes:
        return

    st_module.markdown("---")
    st_module.subheader("Candidate packages")
    st_module.caption(
        f"Composed from: {cached.get('source_label', 'a goal spec')}. "
        "Positive numbers increase the deficit; negative numbers reduce it."
    )
    notes = cached.get("notes")
    if notes:
        st_module.caption(escape_markdown_dollars(f"Goal notes: {notes}"))

    # One headline metric per mix, side by side, so the packages are
    # comparable before the reader scrolls into the detail.
    cols = st_module.columns(len(mixes))
    for col, scored in zip(cols, mixes):
        with col:
            total = float(scored.ten_year_deficit_billions)
            st_module.metric(
                "10-Year Deficit Impact",
                _money(total),
                delta=_deficit_direction(total),
                delta_color="off",
            )
            st_module.caption(escape_markdown_dollars(f"**{scored.mix.name}**"))

    for idx, scored in enumerate(mixes):
        _render_mix_detail(st_module, scored, idx)


def _render_mix_detail(st_module: Any, scored: Any, idx: int) -> None:
    """Render one mix: rationale, components, budget path, distribution, caveats."""
    mix = scored.mix
    st_module.markdown("---")
    st_module.markdown(escape_markdown_dollars(f"### {mix.name}"))
    st_module.markdown(escape_markdown_dollars(mix.rationale or ""))

    total = float(scored.ten_year_deficit_billions)
    st_module.markdown(
        f"**10-year total: {_money_md(total)}** — {_deficit_direction(total).lower()}. "
        f"Revenue components {_money_md(float(scored.revenue_10yr_billions))}; "
        f"spending components {_money_md(float(scored.spending_10yr_billions))}."
    )

    _render_components_table(st_module, scored)
    _render_deficit_path_chart(st_module, scored, idx)
    _render_revenue_distribution(st_module, scored)
    _render_caveats(st_module, scored)


def _render_components_table(st_module: Any, scored: Any) -> None:
    """Components with tier chip, legal status, and benchmark note."""
    components = list(getattr(scored.mix, "components", ()) or ())
    if not components:
        st_module.caption("This mix has no scored components.")
        return

    # ``st.dataframe`` renders raw text (not markdown), so plain ``$`` is safe
    # here — escaping would show the backslashes.
    rows = [
        {
            "Component": comp.label,
            "Side": "Revenue" if comp.kind == "revenue" else "Spending",
            "10-yr $B": _money(float(comp.ten_year_billions)),
            "Avg annual $B": _money(float(comp.annual_billions)),
            "Tier": _TIER_CHIPS.get(comp.tier, comp.tier),
            "Status": _status_cell(getattr(comp, "policy_status", None)),
            "Benchmark": _benchmark_cell(getattr(comp, "validation_badge", None)),
        }
        for comp in components
    ]
    st_module.dataframe(
        pd.DataFrame(rows), hide_index=True, use_container_width=True
    )
    st_module.caption(
        "Tier: 🎯 calibrated presets reproduce a published official score; "
        "📐 generic builds are scored bottom-up; 🧾 spending builds are "
        "uncalibrated. Status reflects whether the modeled policy was enacted."
    )


def _render_deficit_path_chart(st_module: Any, scored: Any, idx: int) -> None:
    """Year-by-year deficit path, with an accessible description + data table."""
    years = [str(int(y)) for y in getattr(scored, "years", ()) or ()]
    path = [float(v) for v in getattr(scored, "deficit_path_billions", ()) or ()]
    if not years or not path or len(years) != len(path):
        st_module.caption("No year-by-year budget path available for this mix.")
        return

    fig = go.Figure(
        go.Bar(
            x=years,
            y=path,
            marker_color=[
                COLOR_DEFICIT_UP if v > 0 else COLOR_DEFICIT_DOWN for v in path
            ],
            hovertemplate="%{x}: %{y:+,.1f}B<extra></extra>",
        )
    )
    apply_base_layout(
        fig,
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="Fiscal year",
        yaxis_title="Deficit impact ($B, + = increases deficit)",
        showlegend=False,
    )
    render_accessible_chart(
        st_module,
        fig,
        ChartDescription(
            title=f"Annual deficit impact — {scored.mix.name}",
            summary=(
                "Bar chart of the combined package's annual deficit impact in "
                "billions of dollars. Bars above zero increase the deficit; "
                "bars below zero reduce it."
            ),
            data_rows=format_currency_rows(zip(years, path)),
        ),
        key=f"_ps_path_{idx}",
    )


def _render_revenue_distribution(st_module: Any, scored: Any) -> None:
    """Revenue-side quintile table — explicitly not a full incidence picture."""
    rows = [dict(row) for row in getattr(scored, "revenue_distribution_rows", ()) or ()]
    st_module.markdown("**Who pays the revenue side**")
    if not rows:
        st_module.caption(
            "No revenue-side distribution available for this mix "
            "(the distributional engine covers the revenue components it can "
            "map to filers)."
        )
    else:
        st_module.dataframe(
            pd.DataFrame(rows), hide_index=True, use_container_width=True
        )
    st_module.caption(CAVEAT_REVENUE_ONLY)


def _render_caveats(st_module: Any, scored: Any) -> None:
    """Always render the mix's own caveats plus the two fixed captions."""
    caveats = [str(c) for c in (getattr(scored, "caveats", ()) or ())]
    st_module.markdown("**Read this before quoting the number**")
    for caveat in caveats:
        st_module.markdown(escape_markdown_dollars(f"- {caveat}"))
    st_module.caption(CAVEAT_INTERACTIONS)
    st_module.caption(
        "Mixes are illustrative compositions, not proposals — and not "
        "validated estimates."
    )


__all__ = [
    "CAVEAT_INTERACTIONS",
    "CAVEAT_REVENUE_ONLY",
    "MATURITY_CAPTION",
    "render_package_studio_tab",
]
