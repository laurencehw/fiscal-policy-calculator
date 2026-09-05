"""
Frozen assignment links — a share link an instructor can grade against.

``?mode=classroom`` has always been shareable, but it pins nothing that moves a
number, so two students could open the same assignment and hand in different
answers with both being right. A **frozen link** closes that: it carries the
provenance triple a share link already stamps (``baseline`` / ``spec`` /
``mode``) plus the policy itself, and adds ``frozen=1`` — which turns those
stamps from a *record* of a run into a *lock* on the next one::

    /explore?preset=tcja-full-extension&dynamic=0&run=1
            &baseline=february2026&engine=frbus_lite&spec=6f2a1c9d4b77
            &mode=conventional&frozen=1

(``baseline=`` is ``share_links.baseline_vintage_token`` of the live vintage —
the slug of the string the exports print, so a link and a CSV cannot disagree.)

What a frozen link pins, and how each is enforced:

``baseline``
    the baseline vintage. Not settable in the app, so this is a **check**, not
    a restore: if the deployment is serving a different vintage the page
    refuses to score and says which vintage the assignment wants
    (:func:`frozen_refusal`). Silently scoring against a different baseline is
    the one failure mode a frozen link exists to prevent.
``engine``
    the macro model dynamic scoring runs through (``frbus_lite`` /
    ``simple``). Applied to ``setting_macro_model`` and rendered disabled.
``dynamic``
    conventional vs dynamic. Applied to ``sidebar_setting_dynamic_scoring``
    and rendered disabled, both in the ⚙ popover and inline beside Score.
the policy
    whatever the surface's own contract already carries — ``?preset=`` on
    Explore, ``?type=&rate=&who=…`` on Tailor. Frozen links do not invent a
    policy encoding; they disable editing of the one that restored it, by
    rendering the input widgets through :func:`frozen_input_module`.
``spec``
    the policy-spec hash of the instructor's run. Deliberately a *caption*,
    not a refusal: the hash covers every scoring setting, so adding a settings
    key to the app would otherwise invalidate every assignment link ever
    issued. A mismatch is reported where it can be read and acted on rather
    than used to block the page.

Only ``/explore`` and ``/tailor`` honour ``frozen=1`` — they are the two
surfaces that produce a single :class:`~components.results.ScoredResult`, which
is the thing a student hands in. Build packages are not freezable yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from collections.abc import Mapping
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .session_state import (
    KEY_DYNAMIC_SCORING,
    KEY_SETTING_MACRO_MODEL,
    seed_widget_default,
)
from .share_links import (
    baseline_vintage_token,
    build_share_url,
    normalize_query_value,
    query_flag,
)

#: ``frozen=1`` — the flag that turns provenance stamps into a lock.
FROZEN_QUERY_KEY = "frozen"

#: ``engine=`` — the macro model, the one scoring engine the app lets a reader
#: choose. Its own key because ``mode=`` is already spent on conventional vs
#: dynamic.
ENGINE_QUERY_KEY = "engine"

#: ``classroom=1`` — shows the "Assignment link" control on the result surface.
#: Not part of the lock: it is how an instructor *makes* one.
CLASSROOM_QUERY_KEY = "classroom"

BASELINE_QUERY_KEY = "baseline"
SPEC_QUERY_KEY = "spec"
MODE_QUERY_KEY = "mode"

#: Session key holding the :class:`FrozenAssignment` in force this run, so the
#: shared result panel can caption a score it did not decode the link for.
FROZEN_STATE_KEY = "_frozen_assignment"

#: The label every frozen control carries. One string, so the ⚙ popover, the
#: inline toggle and the tests cannot drift apart.
FROZEN_LABEL = "🔒 Frozen for this assignment"

#: ``engine=`` token -> the ``setting_macro_model`` option it selects.
ENGINE_LABELS: dict[str, str] = {
    "frbus_lite": "FRB/US-Lite (recommended)",
    "simple": "Simple Multiplier",
}


def engine_token(label: Any) -> str | None:
    """Fold a macro-model name to its ``engine=`` token, or ``None``.

    Deliberately tolerant of spelling: the setting reads "FRB/US-Lite
    (recommended)" while a completed run's ``ScoredResult.macro_model`` carries
    whatever the adapter calls itself. Both must land on the same token, or an
    emitted assignment link would pin an engine the reader never chose.
    """
    text = normalize_query_value(label)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in ENGINE_LABELS:
        return lowered
    if "frb" in lowered:
        return "frbus_lite"
    if "simple" in lowered or "multiplier" in lowered:
        return "simple"
    return None


@dataclass(frozen=True)
class FrozenAssignment:
    """The lock one ``frozen=1`` URL asserts. Immutable, like the link."""

    baseline: str | None
    engine: str | None
    dynamic: bool
    spec: str | None
    mode: str | None

    @property
    def engine_label(self) -> str | None:
        """The ``setting_macro_model`` option, or ``None`` if unrecognised."""
        return ENGINE_LABELS.get(self.engine or "")

    @property
    def mode_label(self) -> str:
        return "dynamic" if self.dynamic else "conventional"

    def as_query_params(self) -> dict[str, str]:
        """The lock as URL params. The inverse of :func:`decode_frozen_assignment`."""
        params: dict[str, str] = {"dynamic": "1" if self.dynamic else "0"}
        if self.baseline:
            params[BASELINE_QUERY_KEY] = self.baseline
        if self.engine:
            params[ENGINE_QUERY_KEY] = self.engine
        if self.spec:
            params[SPEC_QUERY_KEY] = self.spec
        params[MODE_QUERY_KEY] = self.mode or self.mode_label
        params[FROZEN_QUERY_KEY] = "1"
        return params


def decode_frozen_assignment(query_params: Mapping[str, Any]) -> FrozenAssignment | None:
    """Read the lock off a URL, or ``None`` when the URL is an ordinary link.

    Pure — no Streamlit, no session state — so the contract is unit-testable
    without a runtime, the same way ``share_links.rewrite_legacy_query`` is.
    """
    if not query_flag(query_params, FROZEN_QUERY_KEY):
        return None
    return FrozenAssignment(
        baseline=normalize_query_value(query_params.get(BASELINE_QUERY_KEY)),
        engine=normalize_query_value(query_params.get(ENGINE_QUERY_KEY)),
        dynamic=query_flag(query_params, "dynamic"),
        spec=normalize_query_value(query_params.get(SPEC_QUERY_KEY)),
        mode=normalize_query_value(query_params.get(MODE_QUERY_KEY)),
    )


def frozen_refusal(
    frozen: FrozenAssignment | None, *, live_vintage: str | None = None
) -> str | None:
    """Why this deployment cannot honour ``frozen``, or ``None`` if it can.

    Two refusals, both about promises the page would otherwise break silently:

    1. **No baseline named.** ``frozen=1`` without ``baseline=`` claims a lock
       on a vintage the link never states, so there is nothing to honour.
    2. **A vintage this deployment is not serving.** The baseline is a property
       of the deployment, not a session setting, so it cannot be restored — and
       scoring anyway would hand the student numbers off a different baseline
       under an assignment link that says otherwise.

    An ``engine=`` token this build does not know is the third: pinning a
    scoring engine that does not exist here is the same silent substitution.
    """
    if frozen is None:
        return None

    if not frozen.baseline:
        return (
            "This assignment link is marked frozen but does not name a baseline "
            "vintage, so there is nothing to pin the numbers to. Ask for a link "
            "made from a scored result."
        )

    live_token = baseline_vintage_token(live_vintage)
    if live_token and frozen.baseline.lower() != live_token.lower():
        live_name = live_vintage or _live_vintage_name()
        return (
            f"This assignment was frozen on the **{_vintage_name(frozen.baseline)}** "
            f"baseline; this deployment is running **{live_name}**. The numbers "
            "would not be the ones your instructor scored, so nothing is scored "
            "here. Ask for a link rebuilt on the current baseline."
        )

    if frozen.engine and frozen.engine_label is None:
        return (
            f"This assignment link pins a scoring engine this deployment does "
            f"not have (`{frozen.engine}`). Ask for a link rebuilt on this "
            "version of the app."
        )

    return None


def _live_vintage_name() -> str:
    from components.results import resolve_baseline_vintage

    try:
        return resolve_baseline_vintage()
    except Exception:  # pragma: no cover — defensive
        return "an unknown vintage"


#: ``february2026`` -> ``February``, ``2026``. The token is
#: ``share_links.baseline_vintage_token``'s slug of the live vintage string, so
#: it is a month name run onto a year with the punctuation stripped out.
_VINTAGE_NAME_RE = re.compile(r"^([a-z]+)(\d{4})$")


def _vintage_name(token: str) -> str:
    """``february2026`` -> ``CBO February 2026`` — a name a student can act on."""
    text = str(token or "").strip()
    if not text:
        return "an unnamed vintage"
    match = _VINTAGE_NAME_RE.match(text.lower())
    if match:
        return f"CBO {match.group(1).capitalize()} {match.group(2)}"
    return f"CBO {text}"


def apply_frozen_assignment(st_module: Any, frozen: FrozenAssignment) -> None:
    """Write the lock into session state, before any widget is instantiated.

    Streamlit only accepts writes to a widget key ahead of the widget itself,
    which is why every caller does this at the top of its ``render``.
    """
    seed_widget_default(st_module, KEY_DYNAMIC_SCORING, bool(frozen.dynamic), force=True)
    label = frozen.engine_label
    if label:
        seed_widget_default(st_module, KEY_SETTING_MACRO_MODEL, label, force=True)
    try:
        st_module.session_state[FROZEN_STATE_KEY] = frozen
    except Exception:  # pragma: no cover — exotic session_state stand-ins
        pass


def clear_frozen_assignment(st_module: Any) -> None:
    """Forget last run's lock, so an ordinary link is not captioned as frozen."""
    session = getattr(st_module, "session_state", None)
    if session is None:  # pragma: no cover — exotic test doubles
        return
    try:
        session.pop(FROZEN_STATE_KEY, None)
    except Exception:  # pragma: no cover — defensive
        pass


def active_frozen_assignment(st_module: Any) -> FrozenAssignment | None:
    session = getattr(st_module, "session_state", None)
    if session is None:  # pragma: no cover — exotic test doubles
        return None
    try:
        value = session.get(FROZEN_STATE_KEY)
    except Exception:  # pragma: no cover — defensive
        return None
    return value if isinstance(value, FrozenAssignment) else None


# ---------------------------------------------------------------------------
# What the reader sees
# ---------------------------------------------------------------------------

FROZEN_REFUSAL_HEADING = "🔒 This assignment link cannot be scored here"


def render_frozen_refusal(st_module: Any, problem: str) -> None:
    """Say why, and score nothing. The honest half of requirement (d)."""
    st_module.error(f"**{FROZEN_REFUSAL_HEADING}**\n\n{problem}")


def frozen_summary(frozen: FrozenAssignment) -> str:
    """One line naming everything the link pinned."""
    parts = [_vintage_name(frozen.baseline or ""), frozen.mode_label]
    if frozen.dynamic and frozen.engine_label:
        parts.append(frozen.engine_label)
    return " · ".join(parts)


def render_frozen_banner(st_module: Any, frozen: FrozenAssignment) -> None:
    """The page-level label: what is locked, and that a person locked it."""
    st_module.info(
        f"**{FROZEN_LABEL}.** {frozen_summary(frozen)}. The baseline, the "
        "scoring engine, the scoring mode and the policy are set by this link, "
        "so everyone who opens it scores the same thing."
    )


def render_frozen_provenance(
    st_module: Any, scored: Any, frozen: FrozenAssignment, *, spec_hash: str | None = None
) -> None:
    """The compact line under the number — requirement (c)."""
    st_module.caption(
        f"Scored on {getattr(scored, 'baseline_vintage', None) or _live_vintage_name()} "
        f"baseline · {getattr(scored, 'mode', None) or frozen.mode_label} · "
        "frozen by your instructor"
    )
    if frozen.spec and spec_hash and frozen.spec != spec_hash:
        # Not a refusal: the spec hash covers every scoring setting, so a new
        # setting in a later release would otherwise retire every assignment
        # link ever issued. Report it where it can be read and acted on.
        st_module.caption(
            f"⚠️ This run's spec hash is `{spec_hash}`; the link records "
            f"`{frozen.spec}`. Something outside the frozen controls differs — "
            "check the Data & methodology options in ⚙."
        )


# ---------------------------------------------------------------------------
# Disabling the policy inputs
# ---------------------------------------------------------------------------

#: Streamlit callables that take user input. ``button`` and ``download_button``
#: are deliberately absent: the student still has to be able to press Score,
#: and an export is not an edit.
_INPUT_WIDGETS = frozenset(
    {
        "checkbox",
        "color_picker",
        "date_input",
        "multiselect",
        "number_input",
        "pills",
        "radio",
        "segmented_control",
        "select_slider",
        "selectbox",
        "slider",
        "text_area",
        "text_input",
        "time_input",
        "toggle",
    }
)


class _FrozenInputs:
    """A Streamlit stand-in that renders every input widget disabled.

    The policy forms are ~40 widgets across three modules; threading a
    ``disabled=`` argument through all of them would touch far more code than
    the lock is worth and would be one missed keyword away from a control that
    silently still edits a frozen assignment. Intercepting the widget factories
    instead makes "frozen" a property of *how the form is rendered* rather than
    of each widget in it.

    Everything else — ``session_state``, ``columns``, ``markdown``, the layout
    context managers — is the real module, so the widgets still hold their
    values and still return them to the scoring pipeline.
    """

    def __init__(self, st_module: Any) -> None:
        self._st = st_module

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._st, name)
        if name not in _INPUT_WIDGETS or not callable(attr):
            return attr

        def _disabled(*args: Any, **kwargs: Any) -> Any:
            kwargs["disabled"] = True
            try:
                return attr(*args, **kwargs)
            except TypeError:  # pragma: no cover — fakes without the keyword
                kwargs.pop("disabled", None)
                return attr(*args, **kwargs)

        return _disabled


def frozen_input_module(st_module: Any, frozen: FrozenAssignment | None) -> Any:
    """``st_module``, or a stand-in that disables every input widget on it."""
    return st_module if frozen is None else _FrozenInputs(st_module)


# ---------------------------------------------------------------------------
# Making one
# ---------------------------------------------------------------------------


def freeze_url(url: str, *, engine: str | None = None) -> str:
    """Add ``engine=`` and ``frozen=1`` to a share URL, keeping the rest.

    Takes a URL rather than result data so there is exactly one place that
    knows how to build a share link (``share_links.build_share_url``) and this
    one only adds the lock.
    """
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    token = engine_token(engine)
    if token:
        params[ENGINE_QUERY_KEY] = token
    params[FROZEN_QUERY_KEY] = "1"
    return urlunparse(parsed._replace(query=urlencode(params)))


def build_assignment_url(
    result_data: Mapping[str, Any],
    scored: Any,
    *,
    public_app_url: str | None = None,
    engine: Any = None,
) -> str | None:
    """The frozen link for a completed run, or ``None`` if it is not shareable.

    ``engine`` defaults to the macro model the run itself reports; a caller
    with the live setting in hand (which is set even for a conventional run)
    should pass it, so the assignment pins the engine a later dynamic re-run
    would use.
    """
    kwargs: dict[str, Any] = {"result_data": dict(result_data), "scored": scored}
    if public_app_url is not None:
        kwargs["public_app_url"] = public_app_url
    share_url = build_share_url(**kwargs)
    if not share_url:
        return None
    return freeze_url(share_url, engine=engine or getattr(scored, "macro_model", None))


def is_classroom_request(query_params: Mapping[str, Any]) -> bool:
    """True when this surface should offer the "Assignment link" control."""
    return query_flag(query_params, CLASSROOM_QUERY_KEY) or (
        normalize_query_value(query_params.get("mode")) == "classroom"
    )


ASSIGNMENT_LINK_CAPTION = (
    "Send this instead of a plain link: it pins the baseline, the scoring "
    "engine, dynamic scoring and the policy, and shows students that it is "
    "frozen. Every student scores the same numbers."
)


def render_assignment_link_block(
    st_module: Any, scored: Any, result_data: Mapping[str, Any], *, engine: Any = None
) -> None:
    """The instructor's control on the result surface."""
    st_module.markdown("**🔒 Assignment link**")
    url = build_assignment_url(result_data, scored, engine=engine)
    if not url:
        st_module.caption(
            "This run cannot be turned into an assignment link — assignment "
            "links cover catalog proposals, preset spending programs and "
            "tailored tax policies."
        )
        return
    st_module.code(url, language=None)
    st_module.caption(ASSIGNMENT_LINK_CAPTION)
