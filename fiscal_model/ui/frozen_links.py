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
    Explore, ``?type=&rate=&who=…`` on Tailor, ``?policies=&target=&metric=``
    on Build. Frozen links do not invent a policy encoding; they disable
    editing of the one that restored it, by rendering the input widgets
    through :func:`frozen_input_module`.
``spec``
    the policy-spec hash of the instructor's run. Deliberately a *caption*,
    not a refusal: the hash covers every scoring setting, so adding a settings
    key to the app would otherwise invalidate every assignment link ever
    issued. A mismatch is reported where it can be read and acted on rather
    than used to block the page.

``/explore`` and ``/tailor`` honour ``frozen=1`` on the single
:class:`~components.results.ScoredResult` they produce. ``/build`` honours it
on a **package** — the thing a Build student hands in is a checklist and a
deficit target, not one score — through :class:`FrozenBuildPackage` and the
``render_frozen_build_*`` renderers below. Three things differ there and are
worth stating once:

* Build quotes **official list prices**, not model output, so no scoring engine
  and no dynamic setting enters its numbers. The stamps still travel and are
  still enforced (an ``engine=`` this build lacks is a link from another
  version of the app), and the banner says plainly what does the pinning.
* The lock is re-applied on **every** rerun rather than once per distinct link:
  an ordinary ``?policies=`` link is a starting point the reader may then edit,
  and a frozen one is the assignment.
* ``?values=`` / ``?vector=`` packages are freezable, because the composer is
  deterministic. The LLM's only job is turning *free text* into a
  :class:`~fiscal_model.composer.values_schema.ValuesVector`, and free text is
  not what a link carries: ``?values=`` is an archetype slug and ``?vector=``
  the vector itself, both fed to ``composer.select_package``, a pure function
  of tags × vector. A frozen link emitted from the app resolves them to
  ``policies=`` anyway, so a re-scored catalog cannot quietly recompose an
  assignment that was already handed out.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
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
    with contextlib.suppress(Exception):  # pragma: no cover — exotic session_state stand-ins
        st_module.session_state[FROZEN_STATE_KEY] = frozen


def clear_frozen_assignment(st_module: Any) -> None:
    """Forget last run's lock, so an ordinary link is not captioned as frozen."""
    session = getattr(st_module, "session_state", None)
    if session is None:  # pragma: no cover — exotic test doubles
        return
    with contextlib.suppress(Exception):  # pragma: no cover — defensive
        session.pop(FROZEN_STATE_KEY, None)


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
    # ``safe=","`` because Build's ``policies=`` list is comma separated and
    # deliberately unescaped (``share_links.encode_build_share``); re-encoding
    # it here would hand instructors a wall of ``%2C``.
    return urlunparse(parsed._replace(query=urlencode(params, safe=",")))


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


# ---------------------------------------------------------------------------
# Build — freezing a package
# ---------------------------------------------------------------------------
#
#     /build?policies=ss-donut-250k,corporate-28pct&target=3.0&metric=pct_gdp
#           &baseline=february2026&engine=frbus_lite&spec=6f2a1c9d4b77
#           &mode=conventional&frozen=1
#
# Everything from ``baseline=`` on is the lock the other two surfaces already
# carry, decoded by :func:`decode_frozen_assignment` and refused by
# :func:`frozen_refusal` with no Build-specific spelling. What Build adds is
# the *package* half: which policies are ticked, and what the deficit-target
# slider holds.

#: Build's own half of the contract — the same keys ``share_links``' Build
#: codec already emits, named here so the freeze path and the share path
#: cannot drift apart.
BUILD_POLICIES_QUERY_KEY = "policies"
BUILD_TARGET_QUERY_KEY = "target"
BUILD_METRIC_QUERY_KEY = "metric"


@dataclass(frozen=True)
class FrozenBuildPackage:
    """The package one frozen ``/build`` URL asserts.

    ``preset_ids`` are stable ids in selection order — order decides which of
    two overlapping options survives, so it is part of the package rather than
    a presentation detail. ``values_slug`` / ``has_vector`` record that the
    link named a *starting philosophy* instead of a list, which is legal to
    freeze because selection is deterministic from it (module docstring).
    """

    preset_ids: tuple[str, ...]
    target: float | None
    metric: str
    values_slug: str | None = None
    has_vector: bool = False

    @property
    def from_values(self) -> bool:
        """True when the package has to be composed rather than read."""
        return not self.preset_ids and bool(self.values_slug or self.has_vector)

    @property
    def target_label(self) -> str:
        """The deficit target in the metric the link chose, or ``""``.

        Empty when the link names no target: a values link carries its own in
        the vector, and claiming a target the URL never stated would be the
        small lie this module exists to avoid.
        """
        from .share_links import BUILD_METRIC_USD_B

        if self.target is None:
            return ""
        if self.metric == BUILD_METRIC_USD_B:
            return f"${float(self.target):,.0f}B/yr"
        return f"{float(self.target):.1f}% of GDP"

    def as_query_params(self) -> dict[str, str]:
        """The package as URL params. The inverse of :func:`decode_frozen_build`."""
        from .share_links import BUILD_METRIC_PCT_GDP, VALUES_QUERY_KEY

        params: dict[str, str] = {
            BUILD_POLICIES_QUERY_KEY: ",".join(self.preset_ids),
            BUILD_METRIC_QUERY_KEY: self.metric,
        }
        if self.target is not None:
            params[BUILD_TARGET_QUERY_KEY] = (
                f"{float(self.target):.1f}"
                if self.metric == BUILD_METRIC_PCT_GDP
                else f"{float(self.target):.0f}"
            )
        if self.values_slug:
            params[VALUES_QUERY_KEY] = self.values_slug
        return params


def decode_frozen_build(query_params: Mapping[str, Any]) -> FrozenBuildPackage | None:
    """Read the package off a frozen ``/build`` URL, or ``None`` if it is open.

    Delegates the ids, the target and the metric to
    ``share_links.decode_build_share`` — the ordinary Build share codec — so a
    frozen link and a plain one resolve their tokens through exactly the same
    path, legacy emoji labels included.
    """
    if not query_flag(query_params, FROZEN_QUERY_KEY):
        return None

    from .share_links import (
        VALUES_QUERY_KEY,
        VECTOR_QUERY_KEY,
        decode_build_share,
    )

    request = decode_build_share(query_params)
    return FrozenBuildPackage(
        preset_ids=tuple(request["preset_ids"]),
        target=request["target"],
        metric=str(request["metric"]),
        values_slug=normalize_query_value(query_params.get(VALUES_QUERY_KEY)),
        has_vector=bool(normalize_query_value(query_params.get(VECTOR_QUERY_KEY))),
    )


def frozen_build_refusal(package: FrozenBuildPackage | None) -> str | None:
    """Build's own refusal, on top of :func:`frozen_refusal`'s three.

    A frozen ``/build`` link naming neither policies nor a starting philosophy
    pins nothing: the checklist would be whatever the reader's session already
    held, under a banner saying an instructor set it. That is the failure a
    frozen link exists to prevent, so it is refused rather than approximated —
    the same call :func:`frozen_refusal` makes for a link with no ``baseline=``.
    """
    if package is None:
        return None
    if package.preset_ids or package.values_slug or package.has_vector:
        return None
    return (
        "This assignment link is marked frozen but names no package — no "
        "policies and no starting philosophy — so there is nothing to lock. "
        "Ask for a link made from a package in the checklist."
    )


def frozen_build_unresolved_refusal(
    package: FrozenBuildPackage | None, applied_ids: Any
) -> str | None:
    """The same refusal one step later: named, but not rebuildable here.

    ``frozen_build_refusal`` catches a link that names nothing. This catches a
    link that names something this deployment does not have — every id retired
    from the catalog, or a starting philosophy that is not in its
    ``archetypes.yaml``. Both would otherwise render an *empty* checklist under
    a banner saying an instructor chose it, which is a worse lie than either
    the empty link or the honest refusal.
    """
    if package is None or list(applied_ids or ()):
        return None
    if package.from_values:
        return (
            "This assignment link is frozen on a starting philosophy this "
            f"deployment does not have (`{package.values_slug or 'unnamed'}`), "
            "so the package it names cannot be rebuilt here. Ask for a link "
            "made from this version of the app."
        )
    return (
        "This assignment link is frozen on policies that are not in this "
        "catalog, so there is no package to show. They may have been renamed "
        "or retired since the link was made — ask for a rebuilt link."
    )


def build_package_spec_hash(
    preset_ids: Any,
    target: float | None = None,
    metric: str | None = None,
) -> str:
    """``spec=`` for a Build package: the ids, the target and the metric.

    The counterpart of ``components.results.compute_policy_spec_hash``, and the
    same 12 hex characters, because it answers the same question — *which run
    produced this link?* On Build the answer is the package alone: the page
    quotes published list prices, so no model setting can move a number
    underneath one.
    """
    import hashlib
    import json

    from .share_links import normalize_build_metric

    payload = json.dumps(
        {
            "policies": [str(item) for item in (preset_ids or ())],
            "target": None if target is None else round(float(target), 3),
            "metric": normalize_build_metric(metric),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_package_assignment_url(
    preset_ids: Any,
    target: float | None = None,
    metric: str | None = None,
    *,
    engine: Any = None,
    values_slug: str | None = None,
    baseline: str | None = None,
    dynamic: bool = False,
    public_app_url: str | None = None,
) -> str:
    """The frozen ``/build`` link for a package and its deficit target.

    Built on ``share_links.encode_build_share`` — one place knows the Build URL
    shape — plus the provenance stamps and :func:`freeze_url`'s flag, so an
    assignment link differs from the share link beside it by exactly the stamps
    and the lock.
    """
    from .share_links import encode_build_share, normalize_build_metric

    metric_value = normalize_build_metric(metric)
    kwargs: dict[str, Any] = {}
    if public_app_url is not None:
        kwargs["public_app_url"] = public_app_url
    share_url = encode_build_share(list(preset_ids), target, metric_value, **kwargs)

    parsed = urlparse(share_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if values_slug:
        from .share_links import VALUES_QUERY_KEY

        # The philosophy travels as a *label*: the ids above are what is
        # pinned, so a re-scored catalog cannot recompose an assignment that
        # has already been handed out. ``load=1`` is absent for the same reason.
        params[VALUES_QUERY_KEY] = str(values_slug)

    token = baseline if baseline is not None else baseline_vintage_token()
    if token:
        params[BASELINE_QUERY_KEY] = token
    params[SPEC_QUERY_KEY] = build_package_spec_hash(preset_ids, target, metric_value)
    params[MODE_QUERY_KEY] = "dynamic" if dynamic else "conventional"
    params["dynamic"] = "1" if dynamic else "0"

    url = urlunparse(parsed._replace(query=urlencode(params, safe=",")))
    return freeze_url(url, engine=engine)


BUILD_ASSIGNMENT_LINK_CAPTION = (
    "Send this instead of a plain link: it pins the policies, the deficit "
    "target and the baseline vintage, and shows students that it is frozen. "
    "The checklist opens read-only; the exports still work."
)


def render_build_assignment_link_block(
    st_module: Any,
    preset_ids: Any,
    target: float | None = None,
    metric: str | None = None,
    *,
    engine: Any = None,
    values_slug: str | None = None,
) -> None:
    """The instructor's control on Build.

    The package equivalent of :func:`render_assignment_link_block`: same label,
    same placement beside the ordinary share link, and the same refusal to
    invent one — there it is a run that cannot be addressed by a URL, here it
    is an empty checklist.
    """
    st_module.markdown("**🔒 Assignment link**")
    ids = [str(item) for item in (preset_ids or ())]
    if not ids:
        st_module.caption(
            "Check at least one policy first — an assignment link pins a "
            "package, and this one is empty."
        )
        return
    st_module.code(
        build_package_assignment_url(
            ids,
            target,
            metric,
            engine=engine,
            values_slug=values_slug,
        ),
        language=None,
    )
    st_module.caption(BUILD_ASSIGNMENT_LINK_CAPTION)


def frozen_build_summary(
    frozen: FrozenAssignment,
    package: FrozenBuildPackage,
    *,
    count: int | None = None,
) -> str:
    """One line naming everything the Build link pinned."""
    total = len(package.preset_ids) if count is None else int(count)
    parts = [
        _vintage_name(frozen.baseline or ""),
        f"{total} polic{'y' if total == 1 else 'ies'}",
    ]
    if package.target_label:
        parts.append(f"target {package.target_label}")
    return " · ".join(parts)


def render_frozen_build_banner(
    st_module: Any,
    frozen: FrozenAssignment,
    package: FrozenBuildPackage,
    *,
    count: int | None = None,
) -> None:
    """Build's page-level lock label.

    Deliberately not :func:`render_frozen_banner`: that one promises the
    scoring engine and the scoring mode are set by the link, which on Build
    would be a lock nobody is holding — the page quotes published list prices
    and runs no engine. Same :data:`FROZEN_LABEL`, honest sentence.
    """
    st_module.info(
        f"**{FROZEN_LABEL}.** {frozen_build_summary(frozen, package, count=count)}. "
        "The policies, the deficit target and the baseline vintage are set by "
        "this link, so everyone who opens it sees the same scoreboard. The "
        "checklist is read-only; the exports are not."
    )
    if package.from_values:
        st_module.caption(
            "This package was composed from the starting philosophy the link "
            "names. Selection is deterministic from the policy tags — the "
            "model only ever translates free text into values, and a link "
            "carries the values, never the text — so the same link always "
            "produces the same package."
        )


def render_frozen_build_provenance(
    st_module: Any,
    frozen: FrozenAssignment,
    *,
    applied_ids: Any,
    target: float | None,
    metric: str | None,
    vintage: str | None = None,
) -> None:
    """The compact line above the scoreboard — Build's requirement (c).

    The spec check follows the convention the other two surfaces set: a
    mismatch is **captioned, not refused**, because the hash covers the whole
    package and one id retired from the catalog would otherwise retire every
    assignment link ever issued. That same caption is what a hand-edited
    ``policies=`` or ``target=`` trips, because the hash is recomputed from
    what the page actually applied rather than from what the URL claims.
    """
    st_module.caption(
        f"Scored against CBO {vintage or _live_vintage_name()} baseline · "
        "official list prices · frozen by your instructor"
    )
    spec_hash = build_package_spec_hash(applied_ids, target, metric)
    if frozen.spec and frozen.spec != spec_hash:
        st_module.caption(
            f"⚠️ This package's spec hash is `{spec_hash}`; the link records "
            f"`{frozen.spec}`. The policies or the deficit target in this URL "
            "are not the ones that were frozen — check `policies=` and "
            "`target=` against the link your instructor sent."
        )
