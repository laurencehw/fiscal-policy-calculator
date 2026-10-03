"""A deep link can never crash a page, drop its own good parameters, or write
Markdown into a trusted banner.

Five defects, one file, each reproduced before it was fixed:

1. ``/tailor?rate=12`` raised ``StreamlitValueAboveMaxError`` -- the slider was
   seeded past ``max_value`` -- and a rate off the 0.5pp grid (``rate=0.026``)
   made the browser log "The `values` property is in conflict with the current
   step, min, max".
2. ``/build?target=nan|inf|1e999`` raised ``ValueError`` / ``OverflowError`` out
   of ``round(float(target) * 2)``.
3. ``/tailor?phase=nan`` or ``duration=inf`` made ``decode_tailor_query`` raise,
   and the page swallowed it, ignoring the *whole* link.
4. ``?frozen=1&baseline=[Click to re-verify](https://evil.example/login)``
   rendered a clickable attacker link inside the app's own ``st.error``; the
   same for ``engine=``, ``spec=`` and an unresolved ``?preset=``.

(Defect 5, the ``$+4,581.9B`` money format, is a display-convention change in
files this lane does not own; see the lane report.)
"""

from __future__ import annotations

import logging
import re
import types

import pytest
from streamlit.testing.v1 import AppTest

from fiscal_model.ui.frozen_links import (
    decode_frozen_assignment,
    frozen_refusal,
    md_literal,
)
from fiscal_model.ui.share_links import (
    TAILOR_RATE_MAX_PP,
    TAILOR_RATE_MIN_PP,
    decode_build_share,
    decode_tailor_query,
)

logging.getLogger("fiscal_model").setLevel(logging.WARNING)

NON_FINITE = ["nan", "NaN", "inf", "-inf", "Infinity", "1e999", "-1e999"]


# ---------------------------------------------------------------------------
# Defect 1 + 3 -- the Tailor decoder (pure)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", NON_FINITE)
@pytest.mark.parametrize("key", ["rate", "phase", "duration"])
def test_a_non_finite_number_reads_as_absent_and_raises_nothing(key, bad):
    decoded = decode_tailor_query({key: bad})
    assert decoded[key] is None
    assert decoded["has_params"] is True  # the link was still a Tailor link


@pytest.mark.parametrize("bad", NON_FINITE)
def test_one_bad_parameter_drops_only_itself(bad):
    """The page used to swallow the exception and ignore every other parameter."""
    decoded = decode_tailor_query(
        {
            "type": "capital_gains",
            "rate": "3",
            "who": "top1m",
            "phase": bad,
            "duration": "7",
            "dynamic": "1",
            "run": "1",
        }
    )
    assert decoded["kind"] == "Capital gains"
    assert decoded["rate"] == 3.0
    assert decoded["threshold"] == 1_000_000
    assert decoded["duration"] == 7
    assert decoded["phase"] is None
    assert decoded["dynamic"] is True and decoded["run"] is True


def test_one_decoder_that_raises_cannot_take_the_others_down(monkeypatch):
    import fiscal_model.ui.share_links as share_links

    def boom(_value):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(share_links, "parse_tailor_who", boom)
    decoded = decode_tailor_query({"type": "income", "rate": "2", "who": "top1m"})
    assert decoded["threshold"] is None
    assert decoded["kind"] == "Income" and decoded["rate"] == 2.0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12", 10.0),
        ("50", 10.0),
        ("-12", -10.0),
        ("1e308", 10.0),
        ("2.6", 2.6),
        ("0.026", 0.026),
        ("2.75", 2.75),
        ("-0.3", -0.3),
        ("2.5", 2.5),
        ("-10", -10.0),
        ("10", 10.0),
    ],
)
def test_rate_is_clamped_into_the_slider_but_never_rounded(raw, expected):
    """A link's rate scores as written: only out-of-range values move."""
    assert decode_tailor_query({"rate": raw})["rate"] == expected


def test_every_decoded_rate_is_inside_the_slider_and_off_grid_values_survive():
    for tenths in range(-1500, 1501, 7):
        raw = tenths / 10
        rate = decode_tailor_query({"rate": f"{raw}"})["rate"]
        assert TAILOR_RATE_MIN_PP <= rate <= TAILOR_RATE_MAX_PP
        if TAILOR_RATE_MIN_PP <= raw <= TAILOR_RATE_MAX_PP:
            assert rate == raw


def test_phase_and_duration_stay_inside_their_sliders():
    decoded = decode_tailor_query({"phase": "99", "duration": "-4"})
    assert decoded["phase"] == 5 and decoded["duration"] == 1
    decoded = decode_tailor_query({"phase": "0", "duration": "99"})
    assert decoded["phase"] == 1 and decoded["duration"] == 10


# ---------------------------------------------------------------------------
# Defect 2 -- the Build target
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad", NON_FINITE)
def test_build_decoder_rejects_a_non_finite_target(bad):
    decoded = decode_build_share({"policies": "a,b", "target": bad})
    assert decoded["target"] is None
    assert decoded["preset_ids"] == ["a", "b"]  # the rest of the link survives


@pytest.mark.parametrize("metric", ["pct_gdp", "usd_b"])
@pytest.mark.parametrize("bad", NON_FINITE)
def test_restore_build_state_survives_a_non_finite_target(bad, metric):
    from fiscal_model.ui.tabs import deficit_target as dt

    query = {"target": bad, "metric": metric}
    st = types.SimpleNamespace(session_state={}, query_params=query)
    dt.restore_build_state_from_query(st, query, cbo_score_map={})
    assert dt.KEY_BUILD_TARGET_PCT not in st.session_state
    assert dt.KEY_BUILD_TARGET_USD not in st.session_state  # default stands


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_apply_build_target_itself_refuses_a_non_finite_value(bad):
    """Defence in depth: the frozen path reaches this without the decoder."""
    from fiscal_model.ui.tabs import deficit_target as dt

    for metric in ("pct_gdp", "usd_b"):
        st = types.SimpleNamespace(session_state={})
        dt.apply_build_target(st, bad, metric)
        assert dt.KEY_BUILD_TARGET_PCT not in st.session_state
        assert dt.KEY_BUILD_TARGET_USD not in st.session_state


def test_a_finite_target_still_clamps_and_snaps():
    from fiscal_model.ui.tabs import deficit_target as dt

    st = types.SimpleNamespace(session_state={})
    dt.apply_build_target(st, 99.0, "pct_gdp")
    assert st.session_state[dt.KEY_BUILD_TARGET_PCT] == 6.0
    dt.apply_build_target(st, 2.6, "pct_gdp")
    assert st.session_state[dt.KEY_BUILD_TARGET_PCT] == 2.5


# ---------------------------------------------------------------------------
# AppTest -- the pages themselves
# ---------------------------------------------------------------------------


def _tailor_page():
    from pathlib import Path

    import streamlit as st

    import app as app_module
    from app_pages import tailor

    deps = app_module._default_deps_builder(pd_module=__import__("pandas"))
    tailor.render(st, deps, Path("."))


def _build_page():
    from pathlib import Path

    import streamlit as st

    import app as app_module
    from app_pages import build

    deps = app_module._default_deps_builder(pd_module=__import__("pandas"))
    build.render(st, deps, Path("."))


def _explore_page():
    from pathlib import Path

    import streamlit as st

    import app as app_module
    from app_pages import explore

    deps = app_module._default_deps_builder(pd_module=__import__("pandas"))
    explore.render(st, deps, Path("."))


def _run(page, params: dict[str, str]) -> AppTest:
    at = AppTest.from_function(page, default_timeout=300)
    at.query_params.update(params)
    at.run()
    return at


def _slider(at: AppTest, label_prefix: str):
    return next(s for s in at.slider if s.label.startswith(label_prefix))


@pytest.mark.parametrize("rate", ["12", "50", "1e300", "-40"])
def test_tailor_rate_outside_the_slider_does_not_crash(rate):
    at = _run(_tailor_page, {"type": "income", "rate": rate})
    assert not at.exception, [e.message for e in at.exception]
    value = _slider(at, "Rate change").value
    assert TAILOR_RATE_MIN_PP <= value <= TAILOR_RATE_MAX_PP


def test_tailor_rate_off_the_grid_is_kept_as_written():
    """+2.6pp is the repository's reference reproduction (-$302.2B); a link
    that says 2.6 must seed 2.6, not a rounded 2.5 that scores differently."""
    at = _run(_tailor_page, {"type": "income", "rate": "2.6"})
    assert not at.exception
    assert _slider(at, "Rate change").value == 2.6
    at = _run(_tailor_page, {"type": "income", "rate": "0.026"})
    assert not at.exception
    assert _slider(at, "Rate change").value == 0.026


def test_tailor_capital_gains_top1m_link_seeds_in_range_sliders():
    at = _run(
        _tailor_page,
        {"type": "capital_gains", "who": "top1m", "rate": "2.6", "phase": "3", "duration": "7"},
    )
    assert not at.exception
    for slider in at.slider:
        assert slider.min <= slider.value <= slider.max, (slider.label, slider.value)
    assert _slider(at, "Phase-in").value == 3
    assert _slider(at, "Duration").value == 7


@pytest.mark.parametrize(
    "bad", [{"phase": "nan"}, {"duration": "inf"}, {"phase": "1e999"}, {"phase": "-inf"}]
)
def test_tailor_one_bad_parameter_does_not_discard_the_rest_of_the_link(bad):
    at = _run(_tailor_page, {"type": "capital_gains", "rate": "3", "who": "top1m", **bad})
    assert not at.exception, [e.message for e in at.exception]
    # Before the fix the whole link was ignored and these read as the defaults.
    assert _slider(at, "Rate change").value == 3.0
    assert at.session_state["tailor_tax_threshold_choice"].startswith("Millionaires")
    assert at.session_state["tailor_policy_kind"] == "Capital gains"


@pytest.mark.parametrize("target", ["nan", "inf", "-inf", "1e999"])
@pytest.mark.parametrize("metric", ["pct_gdp", "usd_b"])
def test_build_page_survives_a_non_finite_target(target, metric):
    at = _run(_build_page, {"policies": "tcja-full-extension", "target": target, "metric": metric})
    assert not at.exception, [e.message for e in at.exception]


# ---------------------------------------------------------------------------
# Defect 4 -- Markdown injection from URL parameters
# ---------------------------------------------------------------------------

EVIL = "https://evil.example/login"
INJECTIONS = {
    "baseline": f"[Click to re-verify your account]({EVIL})",
    "engine": f"x` [fix]({EVIL}) `",
    "spec": f"zz` [fix]({EVIL}) `",
    "preset": f"[Sign in to see this proposal]({EVIL})",
    "autolink": EVIL,
    "emphasis": "**bold** and :red[colored] and <b>html</b>",
    "backticks": "``` ``` ` [x](" + EVIL + ")",
    "newline": f"x\n\n[a]({EVIL})\n\n",
}

_CODE_SPAN = re.compile(r"(`+)(.+?)\1(?!`)", re.DOTALL)


def _outside_code(text: str) -> str:
    """The Markdown that is left once inline code spans are removed."""
    return _CODE_SPAN.sub(" ", text)


def _renders_a_link(text: str) -> bool:
    markdown_it = pytest.importorskip("markdown_it")
    html = (
        markdown_it.MarkdownIt("commonmark").enable("linkify").render(text)
        if _has_linkify()
        else (markdown_it.MarkdownIt("commonmark").render(text))
    )
    return "<a " in html or "<img" in html


def _has_linkify() -> bool:
    try:
        import linkify_it  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.parametrize("name", sorted(INJECTIONS))
def test_md_literal_cannot_be_broken_out_of(name):
    literal = md_literal(INJECTIONS[name])
    assert "\n" not in literal
    assert not _renders_a_link(literal), literal
    assert "evil.example" not in _outside_code(literal)
    # And the same inside the sentence shapes the banners put it in.
    for template in ("**{}**", "This said {}.", "({})"):
        sentence = template.format(literal)
        assert not _renders_a_link(sentence), sentence


def test_md_literal_truncates_and_never_returns_an_empty_span():
    assert len(md_literal("x" * 5000)) < 200
    assert md_literal("").strip("` ") == ""
    assert not _renders_a_link(md_literal(""))


@pytest.mark.parametrize("field", ["baseline", "engine"])
def test_the_frozen_refusal_never_contains_a_link(field):
    params = {"frozen": "1", "baseline": "february2026", "engine": "frbus_lite"}
    params[field] = INJECTIONS[field]
    problem = frozen_refusal(decode_frozen_assignment(params), live_vintage="CBO February 2026")
    assert problem is not None
    assert not _renders_a_link(problem), problem
    assert "evil.example" not in _outside_code(problem)


def test_the_frozen_refusal_for_an_unminted_baseline_does_not_echo_it_as_markdown():
    params = {"frozen": "1", "baseline": INJECTIONS["autolink"]}
    problem = frozen_refusal(decode_frozen_assignment(params), live_vintage="CBO February 2026")
    assert not _renders_a_link(problem)


def test_a_legitimate_baseline_is_still_named_plainly():
    params = {"frozen": "1", "baseline": "january2025"}
    problem = frozen_refusal(decode_frozen_assignment(params), live_vintage="CBO February 2026")
    assert "**CBO January 2025**" in problem


def _every_message(at: AppTest) -> list[str]:
    """Everything the page says in a Markdown-rendering element."""
    out: list[str] = []
    for kind in ("error", "info", "warning", "success", "caption", "markdown"):
        for element in at.get(kind):
            try:
                value = getattr(element, "value", None)
            except Exception:
                continue
            if isinstance(value, str):
                out.append(value)
    return out


def _assert_no_injected_link(at: AppTest) -> None:
    for message in _every_message(at):
        assert "evil.example" not in _outside_code(message), message
        assert not ("evil.example" in message and _renders_a_link(message)), message


@pytest.mark.parametrize("page", ["_explore_page", "_tailor_page"])
@pytest.mark.parametrize("field", ["baseline", "engine"])
def test_frozen_pages_do_not_render_an_injected_link(page, field):
    params = {"frozen": "1", "baseline": "february2026", "engine": "frbus_lite"}
    params[field] = INJECTIONS[field]
    at = _run(globals()[page], params)
    assert not at.exception, [e.message for e in at.exception]
    assert at.get("error"), "the refusal should have been shown"
    _assert_no_injected_link(at)


def test_frozen_build_page_does_not_render_an_injected_link():
    params = {
        "frozen": "1",
        "baseline": INJECTIONS["baseline"],
        "policies": "tcja-full-extension",
        "target": "3",
    }
    at = _run(_build_page, params)
    assert not at.exception, [e.message for e in at.exception]
    _assert_no_injected_link(at)


def test_an_unresolved_preset_is_shown_as_a_literal_not_markdown():
    at = _run(_explore_page, {"preset": INJECTIONS["preset"]})
    assert not at.exception, [e.message for e in at.exception]
    notes = [m for m in _every_message(at) if m.startswith("No proposal matches")]
    assert notes, "the unresolved-preset note should have been shown"
    _assert_no_injected_link(at)
