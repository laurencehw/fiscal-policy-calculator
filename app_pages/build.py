"""Build — the deficit-reduction package builder (``/build``).

Two doors into the same checklist, per ``DECISIONS.md`` #3 and
``REDESIGN_PLAN.md`` §5b: *Start from your values* (Phase 3b — Package Studio
folded in, still a stub here) and *Start from scratch* (the checklist, live).
Whichever door you come through, there is one scoreboard and one export path.

URL contract (Phase 3):

    /build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp

``policies`` carries stable ``preset_id`` slugs; legacy emoji labels still
resolve, because :func:`~fiscal_model.ui.share_links.decode_build_share` runs
every token through ``preset_ids.resolve_preset``. Restoration happens *before*
the page body renders, since it primes widget-backed session state.
"""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Build"
URL_PATH = "build"

MODE_VALUES = "Start from your values"
MODE_SCRATCH = "Start from scratch"
#: Phase 3b flips the default to ``MODE_VALUES`` once the panel is real.
DEFAULT_MODE = MODE_SCRATCH


def render_values_panel(deps: Any, on_load_selection: Any, *, st_module: Any = None) -> None:
    """Placeholder for Phase 3b's "Start from your values" panel.

    Phase 3b replaces this body with the folded-in Package Studio: free text or
    an archetype card in, a values vector out, a deterministic selector picking
    policies from the tags, and a "Load into the checklist" button. That button
    is the only wiring this stub owes the next phase, and it already exists —
    ``on_load_selection(preset_ids)`` runs
    :func:`fiscal_model.ui.tabs.deficit_target.apply_preselection`, which
    applies the same overlap guardrails the checklist enforces, so a composed
    package can never load a double-counted mix.
    """
    del deps, on_load_selection
    if st_module is None:  # pragma: no cover — real app always passes one
        import streamlit as st_module  # type: ignore[no-redef]

    st_module.info(
        "Coming next: describe your priorities and get a starting package."
    )


def _render_mode_toggle(st_module: Any) -> str:
    """Values / scratch toggle. Degrades to a radio on older Streamlit."""
    options = [MODE_VALUES, MODE_SCRATCH]
    segmented = getattr(st_module, "segmented_control", None)
    if segmented is not None:
        # ``default=`` alongside a session-state value logs a Streamlit
        # warning, and session state is seeded for this key on every page.
        seeded = bool((getattr(st_module, "session_state", None) or {}).get("build_mode"))
        for extra in ({"required": True}, {}):
            try:
                choice = segmented(
                    "Start from",
                    options,
                    key="build_mode",
                    label_visibility="collapsed",
                    **({} if seeded else {"default": DEFAULT_MODE}),
                    **extra,
                )
            except TypeError:  # pragma: no cover — older signature / fakes
                continue
            return choice if choice in options else DEFAULT_MODE
    choice = st_module.radio(
        "Start from",
        options,
        horizontal=True,
        index=options.index(DEFAULT_MODE),
        key="build_mode",
        label_visibility="collapsed",
    )
    return choice if choice in options else DEFAULT_MODE


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Build surface.

    This is ``ui/tabs/deficit_target.py`` — the live "Budget Builder" tab —
    **not** ``ui/tabs/package_builder.py``, which has no production call site
    (see ``planning/redesign/NOTES.md`` section 6.1).
    """
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    from fiscal_model.ui.styles import apply_build_scoreboard_styles
    from fiscal_model.ui.tabs.deficit_target import (
        apply_preselection,
        render_deficit_target_tab,
        restore_build_state_from_query,
    )

    apply_build_scoreboard_styles(st_module)

    # Restore from ``?policies=…&target=…&metric=…`` before any Build widget
    # exists: Streamlit only accepts writes to a widget's key ahead of the
    # widget itself. Applied once per distinct link, so it seeds the page
    # without clobbering later edits.
    restore_build_state_from_query(
        st_module,
        getattr(st_module, "query_params", {}) or {},
        cbo_score_map=deps.CBO_SCORE_MAP,
    )

    mode = _render_mode_toggle(st_module)
    if mode == MODE_VALUES:
        render_values_panel(
            deps,
            lambda preset_ids: apply_preselection(
                list(preset_ids),
                st_module=st_module,
                cbo_score_map=deps.CBO_SCORE_MAP,
            ),
            st_module=st_module,
        )
        st_module.markdown("---")

    render_deficit_target_tab(
        st_module=st_module,
        cbo_score_map=deps.CBO_SCORE_MAP,
        fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
        use_real_data=True,
    )

    render_page_footer(st_module)
