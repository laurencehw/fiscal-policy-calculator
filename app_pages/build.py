"""Build — two doors into one deficit-reduction checklist (``/build``).

Per ``DECISIONS.md`` #3 and ``REDESIGN_PLAN.md`` §5 / §5b, Build has two
entrances and one destination:

* **Start from your values** (the default) — pick a starting philosophy, or
  describe your own, contest the reading, and load the resulting package into
  the checklist. This is Package Studio, folded in: its separate page is gone.
* **Start from scratch** — the checklist itself, unchanged.

**The architecture rule is non-negotiable: the LLM translates, deterministic
code selects.** The model's only job is turning free text into a
:class:`~fiscal_model.composer.values_schema.ValuesVector`; it never sees the
policy catalog and cannot name a policy. Selection is
:func:`~fiscal_model.composer.composer.select_package`, a pure function of
tags × vector, so the same values always produce the same package, every
archetype works with no API key at all, and every pick can be explained.

URL contract:

    /build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp
    /build?values=egalitarian[&load=1]
    /build?vector=<urlsafe-base64 json>[&load=1]

``policies`` opens the checklist; ``values``/``vector`` open the panel. Both
restore *before* the page body renders, because both prime widget-backed
session state and Streamlit refuses a write to a widget key once the widget
exists in the current run. That constraint also explains the one piece of
indirection here: "Load into the checklist" renders below the checkboxes'
reconciliation point, so it queues its ids in ``KEY_VALUES_PENDING_LOAD`` and
:func:`_apply_pending_load` drains them at the top of the next run.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from components.chrome import render_chrome, render_page_footer

PAGE_TITLE = "Build"
URL_PATH = "build"

MODE_VALUES = "Start from your values"
MODE_SCRATCH = "Start from scratch"
#: Build opens on the values panel unless the link names policies (§5b.5).
DEFAULT_MODE = MODE_VALUES

_PLACEHOLDER = (
    "e.g. I'm worried about the debt but I think the middle class has paid "
    "enough. I'd rather fix loopholes than raise rates, and I don't want to "
    "touch Social Security benefits…"
)

STARTING_POINT_NOTICE = (
    "Pre-selects are a **starting point, not a verdict** — everything stays "
    "editable in the checklist, and the scoreboard shows what your values cost."
)
DETERMINISM_NOTE = (
    "Free text is translated into the value dimensions only — policy selection "
    "is deterministic from tags on the policy list, so the same values always "
    "produce the same package."
)


# ---------------------------------------------------------------------------
# Lazy bridges to the composer package
# ---------------------------------------------------------------------------
#
# Imported inside the functions so this page renders (and its tests run)
# without the composer, and so tests can monkeypatch these two names with
# fakes. They are the same two seams Package Studio carried as
# ``_translate_goal_text`` / ``_compose_and_score``; they moved here with the
# surface and now speak the values-vector contract instead of the GoalSpec one.


def _translate_values_text(text: str, *, default_target_pct_gdp: float = 3.0) -> tuple:
    """Free text -> ``(vector, reading, reason)``. The only LLM call on Build."""
    from fiscal_model.composer.translate import translate_values_text

    return translate_values_text(text, default_target_pct_gdp=default_target_pct_gdp)


def _select_package(vector: Any, *, rationale_template: str | None = None) -> Any:
    """Values vector -> a scored, explained package. No LLM, no network."""
    from fiscal_model.composer.composer import compose_values_package, values_catalog

    return compose_values_package(
        vector, values_catalog(), rationale_template=rationale_template
    )


def _anthropic_key_available(st_module: Any) -> bool:
    """True when a key is reachable, promoting ``st.secrets`` → env like Ask.

    Streamlit Cloud surfaces deployment secrets via ``st.secrets`` rather than
    environment variables, so bridge the gap once, here, exactly as the Ask tab
    and the retired Package Studio tab did.
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


# ---------------------------------------------------------------------------
# Panel state
# ---------------------------------------------------------------------------


def _session(st_module: Any) -> Any:
    return st_module.session_state


def _vector_from_session(st_module: Any) -> Any:
    """Read the reflection panel's widgets back as a validated vector.

    The widgets are the source of truth, not a stored copy: that is what makes
    "edit any dial, the package changes, no LLM call" true by construction
    rather than by remembering to invalidate a cache.
    """
    from fiscal_model.composer.values_schema import ValuesVector
    from fiscal_model.ui.session_state import (
        KEY_VALUES_PROTECTED,
        KEY_VALUES_TARGET_PCT,
        VALUES_DIMENSION_KEYS,
    )

    session = _session(st_module)
    payload: dict[str, Any] = {
        name: session.get(key) for name, key in VALUES_DIMENSION_KEYS.items()
    }
    payload["protected"] = list(session.get(KEY_VALUES_PROTECTED) or [])
    payload["target_pct_gdp"] = session.get(KEY_VALUES_TARGET_PCT)
    return ValuesVector.from_dict(payload)


def _write_vector(st_module: Any, vector: Any, *, archetype_id: str | None = None) -> None:
    """Push a vector onto the panel's widget keys and the Build target.

    Only ever called *before* the widgets it writes are instantiated — from a
    card click (which renders above the dials), from a share link, or from the
    pending-load drain at the top of a run.
    """
    from fiscal_model.ui.session_state import (
        KEY_BUILD_TARGET_PCT,
        KEY_VALUES_ARCHETYPE,
        KEY_VALUES_PROTECTED,
        KEY_VALUES_TARGET_PCT,
        VALUES_DIMENSION_KEYS,
    )

    session = _session(st_module)
    vector = vector.clamped()
    for name, key in VALUES_DIMENSION_KEYS.items():
        # Snap to the dial's own 0.05 step. Every archetype value and every
        # translator band is a multiple of it, so a vector survives the round
        # trip through the widgets unchanged — which is what keeps the panel's
        # package identical to the one the symmetry harness scores.
        session[key] = round(float(getattr(vector, name)) * 20) / 20
    session[KEY_VALUES_PROTECTED] = list(vector.protected)
    # Snap to the target slider's own 0.5 step so the panel and the strip agree
    # on a value the strip can actually represent.
    target = round(float(vector.target_pct_gdp) * 2) / 2
    session[KEY_VALUES_TARGET_PCT] = target
    session[KEY_BUILD_TARGET_PCT] = target
    session[KEY_VALUES_ARCHETYPE] = archetype_id


def _ensure_panel_state(st_module: Any) -> None:
    """Seed the panel's widget keys once, from the archetype the URL implies.

    A first visit lands on the leading archetype rather than on an all-neutral
    vector, because a package is the point of the panel and a neutral vector
    produces a bland one.
    """
    from fiscal_model.composer.archetypes import archetype_ids, get_archetype
    from fiscal_model.ui.session_state import KEY_VALUES_PROTECTED, KEY_VALUES_TARGET_PCT

    session = _session(st_module)
    if session.get(KEY_VALUES_TARGET_PCT) is None or session.get(
        KEY_VALUES_PROTECTED
    ) is None:
        ids = archetype_ids()
        if ids:
            _write_vector(st_module, get_archetype(ids[0]).vector, archetype_id=ids[0])
        else:  # pragma: no cover — only with an empty archetypes.yaml
            session[KEY_VALUES_PROTECTED] = []
            session[KEY_VALUES_TARGET_PCT] = 3.0


def restore_values_from_query(
    st_module: Any,
    query_params: Any = None,
) -> dict[str, Any] | None:
    """Restore the panel from ``?values=`` / ``?vector=`` (chip ⑮).

    Applied at most once per distinct link, like the checklist's own share
    restore: a shared link seeds the panel and then gets out of the way instead
    of clobbering the reader's edits on every rerun. ``&load=1`` additionally
    queues the package for the checklist, which is what makes a values link
    usable as a classroom assignment.
    """
    from fiscal_model.ui.session_state import KEY_VALUES_PENDING_LOAD, KEY_VALUES_SHARE_TOKEN
    from fiscal_model.ui.share_links import decode_values_share

    if query_params is None:
        query_params = getattr(st_module, "query_params", {}) or {}

    request = decode_values_share(query_params)
    if not request["archetype_id"] and request["vector"] is None:
        return None

    token = hashlib.sha256(
        json.dumps(
            {
                "archetype_id": request["archetype_id"],
                "vector": request["vector"].to_dict() if request["vector"] else None,
                "load": request["load"],
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:12]
    session = _session(st_module)
    if session.get(KEY_VALUES_SHARE_TOKEN) == token:
        return None
    session[KEY_VALUES_SHARE_TOKEN] = token

    from fiscal_model.composer.archetypes import get_archetype

    archetype = get_archetype(request["archetype_id"])
    # An explicit vector wins: it is the reader's own edit, and the slug is
    # kept only as the label for the reading.
    vector = request["vector"] or (archetype.vector if archetype else None)
    if vector is None:
        return None
    _write_vector(
        st_module, vector, archetype_id=archetype.id if archetype else None
    )

    if request["load"]:
        package = _select_package(
            vector,
            rationale_template=archetype.rationale_template if archetype else None,
        )
        session[KEY_VALUES_PENDING_LOAD] = list(package.policy_ids)
    return request


def _apply_pending_load(st_module: Any, deps: Any) -> bool:
    """Drain ``KEY_VALUES_PENDING_LOAD`` into the checklist. Returns True if it did."""
    from fiscal_model.ui.session_state import KEY_BUILD_MODE, KEY_VALUES_PENDING_LOAD
    from fiscal_model.ui.tabs.deficit_target import apply_preselection

    session = _session(st_module)
    pending = session.get(KEY_VALUES_PENDING_LOAD)
    if not pending:
        return False
    session[KEY_VALUES_PENDING_LOAD] = None
    apply_preselection(
        [str(item) for item in pending],
        st_module=st_module,
        cbo_score_map=deps.CBO_SCORE_MAP,
    )
    # Land the reader in the checklist they just filled, per §5b.5.
    session[KEY_BUILD_MODE] = MODE_SCRATCH
    return True


# ---------------------------------------------------------------------------
# Panel rendering
# ---------------------------------------------------------------------------


def _money(value: float) -> str:
    """``-$3,200B`` — sign outside the ``$`` so the shared escape still bites."""
    return f"{'+' if value >= 0 else '-'}${abs(float(value)):,.0f}B"


def _render_archetype_cards(st_module: Any) -> None:
    """Five cards, three chips each (chip ⑫). Clicking one writes the vector."""
    from fiscal_model.composer.archetypes import load_archetypes
    from fiscal_model.ui.session_state import KEY_VALUES_ARCHETYPE

    archetypes = list(load_archetypes().values())
    selected = _session(st_module).get(KEY_VALUES_ARCHETYPE)

    st_module.caption("PICK A STARTING PHILOSOPHY — OR WRITE YOUR OWN BELOW")
    columns = st_module.columns(2)
    for index, archetype in enumerate(archetypes):
        with columns[index % 2], _card(st_module):
            marker = " ✓" if archetype.id == selected else ""
            st_module.markdown(f"**{archetype.name}**{marker}")
            st_module.caption(archetype.one_line)
            if archetype.chips:
                st_module.caption(" · ".join(f"`{chip}`" for chip in archetype.chips))
            if st_module.button(
                "Use this philosophy",
                key=f"values_card_{archetype.id}",
                width="stretch",
            ):
                _write_vector(st_module, archetype.vector, archetype_id=archetype.id)
                _set_reading(st_module, archetype.one_line)

    st_module.caption(
        "Archetypes are value language, never party language — and every one "
        "gets a steelman package."
    )


def _card(st_module: Any) -> Any:
    """A bordered container where the Streamlit version has one."""
    container = getattr(st_module, "container", None)
    if container is None:  # pragma: no cover — minimal fakes
        return _NullContext()
    try:
        return container(border=True)
    except TypeError:  # pragma: no cover — pre-1.29 signature
        return container()


class _NullContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: Any) -> bool:
        return False


def _set_reading(st_module: Any, reading: str) -> None:
    from fiscal_model.ui.session_state import KEY_VALUES_READING

    _session(st_module)[KEY_VALUES_READING] = str(reading or "")


def _render_free_text(st_module: Any, *, have_key: bool) -> None:
    """The philosophy box and its Translate button (chip ⑬).

    Hidden entirely without a key, rather than shown disabled: the archetype
    cards above are a complete surface on their own, and a permanently greyed
    control reads as something broken instead of something absent.
    """
    from fiscal_model.ui.session_state import (
        KEY_VALUES_NOTICE,
        KEY_VALUES_TARGET_PCT,
        KEY_VALUES_TEXT,
    )

    session = _session(st_module)
    notice = session.get(KEY_VALUES_NOTICE)
    if notice:
        session[KEY_VALUES_NOTICE] = None
        st_module.info(notice)

    if not have_key:
        st_module.caption(
            "Describing your philosophy in your own words needs an "
            "`ANTHROPIC_API_KEY`, which this deployment doesn't have. The "
            "philosophies above work entirely offline — pick one and edit the "
            "reading beside it."
        )
        return

    st_module.caption("OR DESCRIBE YOUR PHILOSOPHY")
    text = st_module.text_area(
        "Describe your fiscal philosophy",
        placeholder=_PLACEHOLDER,
        height=110,
        key=KEY_VALUES_TEXT,
        label_visibility="collapsed",
    )
    if not st_module.button("Translate to a package", type="primary", key="values_translate"):
        return

    with st_module.spinner("Reading your philosophy…"):
        try:
            vector, reading, reason = _translate_values_text(
                str(text or ""),
                default_target_pct_gdp=float(session.get(KEY_VALUES_TARGET_PCT) or 3.0),
            )
        except Exception as exc:  # translation is best-effort, never fatal
            vector, reading, reason = None, "", f"{type(exc).__name__}: {exc}"

    if vector is None:
        st_module.info(
            f"Couldn't read that as a set of values: {reason or 'no reason given'}. "
            "Pick a starting philosophy above and edit it instead — the cards "
            "need no API key, and the dials beside them take any edit you make."
        )
        return

    _write_vector(st_module, vector, archetype_id=None)
    _set_reading(st_module, reading)
    _rerun(st_module)


def _rerun(st_module: Any) -> None:
    rerun = getattr(st_module, "rerun", None) or getattr(st_module, "experimental_rerun", None)
    if rerun is not None:
        rerun()


def _render_dials(st_module: Any) -> None:
    """The reflected interpretation, as controls the reader can contest (⑭)."""
    from fiscal_model.composer.values_schema import (
        DIMENSION_BOUNDS,
        DIMENSION_LABELS,
        PROTECTED_KEYS,
        PROTECTED_LABELS,
        band,
    )
    from fiscal_model.ui.session_state import (
        KEY_VALUES_PROTECTED,
        KEY_VALUES_TARGET_PCT,
        VALUES_DIMENSION_KEYS,
    )

    session = _session(st_module)
    for name, key in VALUES_DIMENSION_KEYS.items():
        low, high = DIMENSION_BOUNDS[name]
        current = float(session.get(key) or 0.0)
        st_module.slider(
            f"{DIMENSION_LABELS[name]} — **{band(name, current)}**",
            min_value=float(low),
            max_value=float(high),
            step=0.05,
            key=key,
        )

    if session.get(KEY_VALUES_PROTECTED) is None:
        session[KEY_VALUES_PROTECTED] = []
    st_module.multiselect(
        "Protected — nothing in the package may touch these",
        options=list(PROTECTED_KEYS),
        format_func=lambda key: PROTECTED_LABELS.get(key, key),
        key=KEY_VALUES_PROTECTED,
    )
    st_module.slider(
        "Deficit target (% of GDP)",
        min_value=0.0,
        max_value=6.0,
        step=0.5,
        key=KEY_VALUES_TARGET_PCT,
        on_change=_push_target_to_build,
        args=(st_module,),
        help="The same target the strip below uses — moving it here moves it there.",
    )


def _push_target_to_build(st_module: Any) -> None:
    """Mirror the panel's target onto the checklist's slider key.

    Runs as an ``on_change`` callback, i.e. before any widget exists in the
    next run, which is the only moment Streamlit permits the write.
    """
    from fiscal_model.ui.session_state import KEY_BUILD_TARGET_PCT, KEY_VALUES_TARGET_PCT

    session = _session(st_module)
    value = session.get(KEY_VALUES_TARGET_PCT)
    if value is not None:
        session[KEY_BUILD_TARGET_PCT] = float(value)


def _render_package_preview(st_module: Any, package: Any, *, reading: str) -> None:
    """Coverage line, then one row per pick: policy · why · $ (⑭)."""
    from fiscal_model.composer.values_schema import PROTECTED_LABELS
    from fiscal_model.ui.helpers import escape_markdown_dollars

    vector = package.vector
    st_module.markdown(
        escape_markdown_dollars(
            f"That implies **{package.summary()}** — the package scores "
            f"{_money(package.total_billions)} over the window against a gap of "
            f"${package.gap_billions:,.0f}B to a "
            f"{float(vector.target_pct_gdp):.1f}%-of-GDP target."
        )
    )
    if reading:
        st_module.caption(escape_markdown_dollars(reading))
    if vector.protected:
        st_module.caption(
            "Protected: "
            + ", ".join(PROTECTED_LABELS[key].lower() for key in vector.protected)
        )

    if not package.picks:
        st_module.info(
            "No policy in the catalog fits those values without violating one "
            "of your protections. Loosen a protection or move a dial."
        )
        return

    for pick in package.picks:
        # Escape the label, which markdown renders; leave the code span alone.
        # Markdown does not process escapes inside a code span (and does not
        # run KaTeX in one either), so escaping the amount is what put a
        # literal backslash on screen — "-\$3,200B" (external UI review,
        # 2026-09-01).
        st_module.markdown(
            f"**{escape_markdown_dollars(pick.label)}** — `{_money(pick.score)}`"
        )
        st_module.caption(escape_markdown_dollars(pick.why))
        with st_module.expander(f"Tags behind {pick.label}", expanded=False):
            if pick.tags:
                st_module.markdown(
                    "\n".join(
                        f"- **{key.replace('_', ' ')}**: {value}"
                        for key, value in sorted(pick.tags.items())
                    )
                )
            else:
                st_module.markdown(
                    "- No values tags are asserted for this policy in the "
                    "catalog, which is why it was held back until the target "
                    "could not be reached without it."
                )
            st_module.caption(
                "Tags are honest metadata derived from the app's own "
                "distribution engine where the policy is representable "
                "(`scripts/derive_policy_tags.py`), and hand-set otherwise."
            )


def render_values_panel(deps: Any, on_load_selection: Any, *, st_module: Any = None) -> None:
    """The "Start from your values" panel — Build's opening screen (§5b).

    ``on_load_selection(preset_ids)`` is the bridge into the checklist
    (:func:`~fiscal_model.ui.tabs.deficit_target.apply_preselection`), which
    applies the same overlap guardrails the checklist enforces, so a composed
    package can never load a double-counted mix. It is not called inline: the
    button lives below the checkboxes' reconciliation point, so the ids are
    queued and drained at the top of the next run.
    """
    if st_module is None:  # pragma: no cover — real app always passes one
        import streamlit as st_module  # type: ignore[no-redef]

    del deps

    from fiscal_model.composer.archetypes import rationale_template_for
    from fiscal_model.ui.session_state import (
        KEY_VALUES_ARCHETYPE,
        KEY_VALUES_PENDING_LOAD,
        KEY_VALUES_READING,
    )

    session = _session(st_module)
    _ensure_panel_state(st_module)

    left, right = st_module.columns([3, 2])

    # Left column runs first, so a card click or a translation can still write
    # the dial keys before the dials on the right are instantiated.
    with left:
        _render_archetype_cards(st_module)
        _render_free_text(st_module, have_key=_anthropic_key_available(st_module))

    with right, _card(st_module):
        st_module.caption("HOW I READ YOUR PHILOSOPHY — CONTEST ANY OF IT")
        _render_dials(st_module)

        vector = _vector_from_session(st_module)
        package = _select_package(
            vector,
            rationale_template=rationale_template_for(session.get(KEY_VALUES_ARCHETYPE)),
        )
        _render_package_preview(
            st_module, package, reading=str(session.get(KEY_VALUES_READING) or "")
        )

        load_col, share_col = st_module.columns([3, 2])
        with load_col:
            if st_module.button(
                "Load into the checklist",
                type="primary",
                key="values_load",
                width="stretch",
                disabled=not package.picks,
            ):
                session[KEY_VALUES_PENDING_LOAD] = list(package.policy_ids)
                _rerun(st_module)
        with share_col:
            _render_share(st_module, vector, session.get(KEY_VALUES_ARCHETYPE))

        st_module.caption(STARTING_POINT_NOTICE)

    st_module.caption(DETERMINISM_NOTE)
    # ``on_load_selection`` is the documented bridge and stays in the
    # signature; the pending-load drain calls the same ``apply_preselection``
    # one run earlier, where the write is legal.
    del on_load_selection


def _render_share(st_module: Any, vector: Any, archetype_id: Any) -> None:
    """The ⑮ share control: a values link, copyable from a popover or a caption."""
    from fiscal_model.ui.share_links import encode_values_share

    url = encode_values_share(archetype_id, vector, load=True)
    popover = getattr(st_module, "popover", None)
    if popover is None:  # pragma: no cover — older Streamlit / fakes
        st_module.caption(url)
        return
    with popover("Share", width="stretch"):
        st_module.caption(
            "Anyone opening this link gets the same package — selection is "
            "deterministic from these values."
        )
        st_module.code(url, language=None)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


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

    from fiscal_model.ui.session_state import KEY_BUILD_MODE
    from fiscal_model.ui.styles import apply_build_scoreboard_styles
    from fiscal_model.ui.tabs.deficit_target import (
        apply_preselection,
        render_deficit_target_tab,
        restore_build_state_from_query,
    )

    apply_build_scoreboard_styles(st_module)

    query_params = getattr(st_module, "query_params", {}) or {}

    # Restore from ``?policies=…&target=…&metric=…`` before any Build widget
    # exists: Streamlit only accepts writes to a widget's key ahead of the
    # widget itself. Applied once per distinct link, so it seeds the page
    # without clobbering later edits.
    restored = restore_build_state_from_query(
        st_module,
        query_params,
        cbo_score_map=deps.CBO_SCORE_MAP,
    )
    if restored and restored.get("preset_ids"):
        # A link that names policies wants the checklist, not the panel.
        st_module.session_state[KEY_BUILD_MODE] = MODE_SCRATCH

    restore_values_from_query(st_module, query_params)
    _apply_pending_load(st_module, deps)

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
