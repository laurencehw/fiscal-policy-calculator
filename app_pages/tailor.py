"""Tailor — define your own tax or spending policy (``/tailor``).

Wireframe: ``planning/redesign/wireframes/03-tailor.png``. A left-column form
card (start from blank or a preset, policy type, rate, who is affected, timing,
advanced) with the primary Score button and the dynamic-scoring toggle inline
beside it; the shared result panel on the right.

URL contract (redesign plan §7)::

    /tailor?type=income|corporate|capital_gains|spending
           &rate=2&who=top400k&phase=1&duration=10&dynamic=0|1&run=1

Every field is optional. ``who`` is the enum in
``ui/share_links.TAILOR_WHO_THRESHOLDS`` (``all``, ``top50k``, ``top100k``,
``top200k``, ``top400k``, ``top500k``, ``top1m``); a bare amount
(``who=275000``, ``who=400k``) becomes a custom threshold. ``rate`` is in
percentage points, ``+`` for a tax increase. See :func:`_apply_query_params`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from components.chrome import render_chrome, render_page_footer
from components.results import render_score_surface
from fiscal_model.ui.calculation_controller import (
    CUSTOM_ANALYSIS_MODE,
    SPENDING_ANALYSIS_MODE,
)
from fiscal_model.ui.session_state import (
    KEY_DYNAMIC_SCORING,
    KEY_QS_CALCULATE,
    KEY_TAILOR_POLICY_KIND,
    KEY_TAILOR_SEED_APPLIED,
    KEY_TAILOR_SEED_PRESET,
    KEY_TAILOR_START_FROM,
    KEY_TAILOR_TAX_CUSTOM_THRESHOLD,
    KEY_TAILOR_TAX_DURATION,
    KEY_TAILOR_TAX_ETI,
    KEY_TAILOR_TAX_ORDINARY_BASE,
    KEY_TAILOR_TAX_PHASE_IN,
    KEY_TAILOR_TAX_POLICY_NAME,
    KEY_TAILOR_TAX_RATE_CHANGE_PCT,
    KEY_TAILOR_TAX_THRESHOLD_CHOICE,
    KEY_TAILOR_TAX_TYPE,
    mirror_widget_value,
    seed_widget_default,
)
from fiscal_model.ui.settings_controller import claim_inline_dynamic_toggle
from fiscal_model.ui.share_links import decode_tailor_query

PAGE_TITLE = "Tailor"
URL_PATH = "tailor"

#: Guards the query-param seed so it applies once per distinct ``/tailor`` link.
_QUERY_TOKEN_KEY = "_applied_tailor_share_token"

#: The wireframe's policy-type chips, mapped onto the engine's own type names.
#: "Spending" selects the spending analysis mode instead of a tax type.
POLICY_KINDS: tuple[str, ...] = ("Income", "Corporate", "Capital gains", "Spending")
_KIND_TO_TAX_TYPE: dict[str, str] = {
    "Income": "Income Tax Rate",
    "Corporate": "Corporate Tax",
    "Capital gains": "Capital Gains",
}

START_FROM_OPTIONS: tuple[str, ...] = ("Blank", "A preset")

#: Threshold values the "Who is affected" picker offers, so a preset's
#: threshold can be seeded onto the label the widget actually holds.
_THRESHOLD_LABELS: dict[int, str] = {
    0: "All taxpayers ($0+)",
    50_000: "Middle income ($50K+)",
    100_000: "Upper-middle ($100K+)",
    200_000: "Higher income ($200K+)",
    400_000: "Top earners ($400K+)",
    500_000: "High income ($500K+)",
    1_000_000: "Millionaires ($1M+)",
}


def _segmented(st_module: Any, label: str, options: tuple[str, ...], key: str, *, help: str | None = None) -> str:
    """Render a segmented control, falling back to a radio on older runtimes.

    ``st.segmented_control`` allows *deselection*, which would leave the page
    with no policy type at all — so an empty selection falls back to the stored
    value rather than to ``None``.
    """
    previous = st_module.session_state.get(key, options[0])
    widget = getattr(st_module, "segmented_control", None)
    if widget is None:
        widget = st_module.radio
        chosen = widget(label, list(options), key=key, help=help, horizontal=True)
    else:
        chosen = widget(label, list(options), key=key, help=help)
    if chosen is None:
        st_module.session_state[key] = previous
        chosen = previous
    mirror_widget_value(st_module, key)
    return str(chosen)


def _seed_form_from_preset(st_module: Any, preset_name: str, preset_data: dict[str, Any]) -> None:
    """Copy a preset's parameters into the Tailor form fields.

    Only fires when the chosen preset changes, so a manual edit made after
    seeding survives the next rerun. Presets whose scoring lives in a
    specialized module (TCJA, estate, PTC …) still seed rate/threshold/timing —
    the form scores them on the generic path, which is exactly the
    "start from a preset, then change it" story the wireframe describes.
    """
    if st_module.session_state.get(KEY_TAILOR_SEED_APPLIED) == preset_name:
        return
    st_module.session_state[KEY_TAILOR_SEED_APPLIED] = preset_name

    rate_pct = float(preset_data.get("rate_change", 0.0) or 0.0)
    threshold = int(preset_data.get("threshold", 0) or 0)
    seed_widget_default(st_module, KEY_TAILOR_TAX_POLICY_NAME, preset_name, force=True)
    seed_widget_default(st_module, KEY_TAILOR_TAX_RATE_CHANGE_PCT, rate_pct, force=True)
    seed_widget_default(
        st_module,
        KEY_TAILOR_TAX_DURATION,
        int(preset_data.get("duration_years", 10) or 10),
        force=True,
    )
    # Engine contract: phase_in_years >= 1 (chip ⑨). A preset that stores 0
    # must not seed a value the engine rejects.
    seed_widget_default(
        st_module,
        KEY_TAILOR_TAX_PHASE_IN,
        max(1, int(preset_data.get("phase_in_years", 1) or 1)),
        force=True,
    )
    seed_widget_default(
        st_module, KEY_TAILOR_TAX_ETI, float(preset_data.get("eti", 0.25) or 0.25), force=True
    )
    seed_widget_default(
        st_module,
        KEY_TAILOR_TAX_ORDINARY_BASE,
        not bool(preset_data.get("agi_inclusive_base", False)),
        force=True,
    )
    label = _THRESHOLD_LABELS.get(threshold)
    if label is None:
        seed_widget_default(st_module, KEY_TAILOR_TAX_THRESHOLD_CHOICE, "Custom amount", force=True)
        seed_widget_default(st_module, KEY_TAILOR_TAX_CUSTOM_THRESHOLD, threshold, force=True)
    else:
        seed_widget_default(st_module, KEY_TAILOR_TAX_THRESHOLD_CHOICE, label, force=True)


def _render_form_header(st_module: Any, deps: Any) -> None:
    """"Start from" + policy-type chips, above the rest of the form card."""
    seed_widget_default(st_module, KEY_TAILOR_START_FROM, START_FROM_OPTIONS[0])
    start_from = _segmented(
        st_module,
        "Start from",
        START_FROM_OPTIONS,
        KEY_TAILOR_START_FROM,
        help=(
            "**Blank** — an empty form. **A preset** — seed the rate, "
            "threshold and timing from a scored proposal, then change it."
        ),
    )

    if start_from == "A preset":
        preset_names = [name for name in deps.PRESET_POLICIES if name != "Custom Policy"]
        if preset_names:
            seed_widget_default(st_module, KEY_TAILOR_SEED_PRESET, preset_names[0])
            if st_module.session_state.get(KEY_TAILOR_SEED_PRESET) not in preset_names:
                seed_widget_default(
                    st_module, KEY_TAILOR_SEED_PRESET, preset_names[0], force=True
                )
            chosen = st_module.selectbox(
                "Seed the form from",
                options=preset_names,
                key=KEY_TAILOR_SEED_PRESET,
                help="Copies this proposal's parameters into the form below.",
            )
            mirror_widget_value(st_module, KEY_TAILOR_SEED_PRESET)
            _seed_form_from_preset(st_module, chosen, deps.PRESET_POLICIES[chosen])
            st_module.caption(
                "Seeded from the preset's published parameters. The score below "
                "is the generic (uncalibrated) path, so it will not reproduce "
                "the preset's calibrated benchmark exactly — Explore does that."
            )
    else:
        st_module.session_state.pop(KEY_TAILOR_SEED_APPLIED, None)

    seed_widget_default(st_module, KEY_TAILOR_POLICY_KIND, POLICY_KINDS[0])
    _segmented(
        st_module,
        "Policy type",
        POLICY_KINDS,
        KEY_TAILOR_POLICY_KIND,
        help=(
            "**Income** and **Capital gains** score individual filers; "
            "**Corporate** scores taxable corporate profits; "
            "**Spending** switches to the outlay form."
        ),
    )


def _resolve_kind(st_module: Any) -> str:
    """Read the policy-type chip chosen on the previous run."""
    kind = st_module.session_state.get(KEY_TAILOR_POLICY_KIND, POLICY_KINDS[0])
    return kind if kind in POLICY_KINDS else POLICY_KINDS[0]


def _apply_query_params(st_module: Any) -> None:
    """Seed the form from ``/tailor?type=…&rate=…&who=…&phase=…&run=1``.

    Applied once per distinct query string: the decoded request is hashed into
    ``_applied_tailor_share_token``, so a rerun (or the user editing a field
    after arriving on the link) is not overwritten, and ``run=1`` spends
    exactly one automatic score.

    Runs before any widget on the page, so these are plain pre-seeds rather
    than the "cannot be modified after instantiation" error.
    """
    query_params = getattr(st_module, "query_params", None) or {}
    try:
        request = decode_tailor_query(query_params)
    except Exception:  # pragma: no cover — a bad link must not break the page
        return
    if not request["has_params"]:
        return

    token = hashlib.sha256(
        json.dumps(request, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    if st_module.session_state.get(_QUERY_TOKEN_KEY) == token:
        return
    st_module.session_state[_QUERY_TOKEN_KEY] = token

    if request["kind"]:
        seed_widget_default(st_module, KEY_TAILOR_POLICY_KIND, request["kind"], force=True)
        if request["kind"] != "Spending":
            seed_widget_default(
                st_module,
                KEY_TAILOR_TAX_TYPE,
                _KIND_TO_TAX_TYPE[request["kind"]],
                force=True,
            )
        # A link that names a policy type is describing a policy, not a preset.
        seed_widget_default(st_module, KEY_TAILOR_START_FROM, "Blank", force=True)

    if request["rate"] is not None:
        seed_widget_default(
            st_module, KEY_TAILOR_TAX_RATE_CHANGE_PCT, float(request["rate"]), force=True
        )
    if request["threshold"] is not None:
        label = _THRESHOLD_LABELS.get(request["threshold"])
        if label is None:
            seed_widget_default(
                st_module, KEY_TAILOR_TAX_THRESHOLD_CHOICE, "Custom amount", force=True
            )
            seed_widget_default(
                st_module,
                KEY_TAILOR_TAX_CUSTOM_THRESHOLD,
                int(request["threshold"]),
                force=True,
            )
        else:
            seed_widget_default(
                st_module, KEY_TAILOR_TAX_THRESHOLD_CHOICE, label, force=True
            )
    if request["phase"] is not None:
        seed_widget_default(st_module, KEY_TAILOR_TAX_PHASE_IN, request["phase"], force=True)
    if request["duration"] is not None:
        seed_widget_default(
            st_module, KEY_TAILOR_TAX_DURATION, request["duration"], force=True
        )

    if request["has_dynamic"]:
        st_module.session_state[KEY_DYNAMIC_SCORING] = bool(request["dynamic"])
    if request["run"]:
        st_module.session_state[KEY_QS_CALCULATE] = True


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Tailor surface."""
    # Before every widget on the page: a ``/tailor?…`` link seeds the form.
    _apply_query_params(st_module)
    # Claim the dynamic toggle before the chrome builds its settings popover:
    # two widgets sharing ``sidebar_setting_dynamic_scoring`` in one run is a
    # Streamlit DuplicateWidgetID error, and the shared key is what keeps the
    # chrome, share links and this page in agreement.
    claim_inline_dynamic_toggle(st_module)
    settings = render_chrome(st_module=st_module, deps=deps)

    st_module.markdown("## Tailor a policy")
    st_module.caption(
        "Set the parameters yourself; the score carries its confidence tier "
        "and a sensitivity band."
    )

    kind = _resolve_kind(st_module)
    if kind == "Spending":
        modes: tuple[str, ...] = (SPENDING_ANALYSIS_MODE,)
    else:
        modes = (CUSTOM_ANALYSIS_MODE,)
        # The page owns the type chip, so write the engine's type name here and
        # tell the form not to render a second widget on the same key.
        seed_widget_default(
            st_module, KEY_TAILOR_TAX_TYPE, _KIND_TO_TAX_TYPE[kind], force=True
        )

    render_score_surface(
        st_module=st_module,
        deps=deps,
        settings=settings,
        app_root=app_root,
        modes=modes,
        inputs_heading="Define your policy",
        score_label="Score this policy",
        show_quick_start=False,
        split_layout=True,
        before_inputs=lambda: _render_form_header(st_module, deps),
        tax_input_kwargs={"show_type_selector": False},
    )

    render_page_footer(st_module)
