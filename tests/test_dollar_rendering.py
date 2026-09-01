"""Guard: no rendered markdown turns currency into LaTeX (REDESIGN_PLAN §9.9).

Streamlit renders markdown through KaTeX, so two unescaped ``$`` in one string
can become an inline-math span: ``$4,582 billion</strong> … <strong>$458B``
renders as italic math with the dollar signs eaten. The app has one escaping
helper — :func:`fiscal_model.ui.helpers.escape_markdown_dollars` — and this
test is the reason every markdown-rendered currency string must go through it.

**The invariant checked here** is the helper's own rule, deliberately
conservative: *a single rendered string may carry at most one unescaped ``$``
before a digit.* One amount cannot open and close a span; two can, and whether
they actually do depends on the punctuation between them — which is not
something a caller should have to reason about. Escaping is free; auditing
KaTeX's delimiter rules per string is not.

The check runs the **real router** through ``AppTest`` on the four scoring
surfaces, including ``/explore`` after an actual calculation (the numbers that
matter only exist after a run). A grep over sources would not do: the dangerous
strings are assembled at render time from f-strings, so a source literal can
hold a single ``$`` and still emit a pair.
"""

from __future__ import annotations

import re
import time

import pytest

from fiscal_model.ui import cache as ui_cache

#: An unescaped ``$`` starting an amount. Deliberately wider than the digit-only
#: lookahead in ``escape_markdown_dollars``: signed amounts (``$+4,581.9B``) are
#: how the result panel prints deficit effects, and Streamlit's math parser
#: happily opened a span on one. Two of these in a string is the bug.
UNESCAPED_CURRENCY = re.compile(r"(?<!\\)\$(?=[\d+\-−.])")

#: Inline code and fenced blocks are not math-rendered, so strip them first.
_CODE_SPAN = re.compile(r"`[^`\n]*`|```.*?```", re.DOTALL)

#: CommonMark "HTML block" tags (type 6). A line starting with one of these
#: opens a block that runs to the next blank line and is passed through raw.
#: Inline tags (``<small>``, ``<span>``, ``<b>``…) do **not** — they leave the
#: surrounding text as an ordinary markdown paragraph, which *is* math-parsed.
#: The distinction is load-bearing: the interpretation card (``<p>``) is safe
#: with bare ``$``; the sensitivity line (``<small>``) was not.
_HTML_BLOCK_TAGS = (
    "p",
    "div",
    "table",
    "ul",
    "ol",
    "li",
    "blockquote",
    "pre",
    "section",
    "details",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
)
_HTML_BLOCK_START = re.compile(
    r"^<(" + "|".join(_HTML_BLOCK_TAGS) + r")(\s|>|/>)", re.IGNORECASE
)


def is_raw_html_block(text: str) -> bool:
    """True when Streamlit renders ``text`` as one opaque HTML block.

    Such a block is never tokenized by ``remark-math``, so ``$…$`` inside it is
    currency, not math — and a markdown escape inside it renders its backslash
    literally. The result panel's plain-English interpretation relies on this
    (``results_summary._build_interpretation_html``); verified in a browser,
    that paragraph shows currency and the page has no ``.katex`` node.
    """
    stripped = text.strip()
    return bool(_HTML_BLOCK_START.match(stripped)) and "\n\n" not in stripped


def unescaped_amounts(text: str) -> list[str]:
    """Unescaped currency amounts in ``text`` outside code spans."""
    if not text or "$" not in text:
        return []
    stripped = _CODE_SPAN.sub(" ", text)
    return [stripped[m.start() : m.start() + 12] for m in UNESCAPED_CURRENCY.finditer(stripped)]


def latex_risk(text: str) -> list[str]:
    """The amounts that make ``text`` a LaTeX-span risk, or ``[]`` if safe."""
    if is_raw_html_block(text):
        return []
    found = unescaped_amounts(text)
    return found if len(found) >= 2 else []


HEALTHY_HEALTH: dict = {
    "runtime": {"status": "ok", "python_version": "3.12.0"},
    "baseline": {
        "status": "ok",
        "vintage": "February 2026",
        "vintage_key": "cbo_feb_2026",
        "start_year": 2025,
        "freshness": {"level": "fresh", "is_stale": False, "message": "current"},
    },
    "fred": {"status": "ok", "source": "live", "cache_is_expired": False},
    "irs_soi": {
        "status": "ok",
        "latest_year": 2023,
        "freshness": {"level": "ok", "is_stale": False, "message": "lag 3y"},
    },
    "model": {"status": "ok"},
    "microdata": {"status": "ok"},
    "assistant": {"status": "ok"},
    "overall": "ok",
}


@pytest.fixture(autouse=True)
def _offline_and_healthy(monkeypatch):
    """Seed the health cache and make the assistant unreachable.

    Seeding the TTL cache keeps these runs off the slow real ``check_health``
    probe. Dropping the API key keeps them off the network entirely — a
    rendering guard must never depend on (or spend) a live API budget, and it
    matches how CI runs the app.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = HEALTHY_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


def _run(page: str | None, *, query: dict[str, str] | None = None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    if query:
        at.query_params.update(query)
    if page is not None:
        at.switch_page(page)
    at.run()
    return at


def _rendered_text(at) -> list[tuple[str, str]]:
    """Every markdown-rendered string on the page, tagged with its element."""
    out: list[tuple[str, str]] = []
    for name in ("markdown", "caption", "warning", "error", "info", "success"):
        for element in getattr(at, name, []):
            value = getattr(element, "value", None)
            if isinstance(value, str):
                out.append((name, value))
    return out


EXPLORE_RUN = {"preset": "tcja-full-extension", "run": "1"}


@pytest.mark.parametrize(
    ("page", "query", "label"),
    [
        (None, None, "ask-home"),
        ("app_pages/build.py", None, "build"),
        ("app_pages/tailor.py", None, "tailor"),
        ("app_pages/explore.py", EXPLORE_RUN, "explore-after-a-run"),
    ],
)
def test_no_unescaped_latex_spans_in_rendered_markdown(page, query, label):
    at = _run(page, query=query)
    assert not at.exception, [e.message for e in at.exception]

    offenders = [
        (name, text, risk) for name, text in _rendered_text(at) if (risk := latex_risk(text))
    ]
    assert not offenders, (
        f"{label}: {len(offenders)} rendered string(s) carry two or more "
        "unescaped currency amounts, which Streamlit can render as a LaTeX "
        "span instead of money. Wrap them in "
        "fiscal_model.ui.helpers.escape_markdown_dollars. First offender: "
        f"{offenders[0][0]} -> {offenders[0][1][:200]!r}"
    )


def test_explore_run_actually_rendered_currency():
    """Guards the guard: the /explore case above must really have scored.

    Without this, a routing regression that renders an empty page would make
    the assertion above pass vacuously.
    """
    at = _run("app_pages/explore.py", query=EXPLORE_RUN)
    assert not at.exception, [e.message for e in at.exception]
    joined = " ".join(text for _, text in _rendered_text(at))
    assert "$" in joined, "no currency rendered — the auto-run did not score"


# ── The detector itself ──────────────────────────────────────────────────


def test_detector_flags_the_shape_it_is_meant_to_catch():
    assert latex_risk("Today's budget ($5.00 of $6.00 used)")
    assert latex_risk("Bottom quintile -$18,642 vs top $4,421")
    assert latex_risk("Deficit rises $4,582B; revenue falls $458B.")


def test_detector_flags_signed_amounts():
    """The live offender was ``$+4,581.9B to $+4,581.9B`` — a signed pair."""
    assert latex_risk("Sensitivity range: $+4,581.9B to $+4,581.9B (ETI 0.15-0.35)")
    assert latex_risk("From $-1,040B to $-960B")


def test_detector_exempts_block_level_html_but_not_inline():
    """``<p>`` opens an opaque HTML block; ``<small>`` does not."""
    assert is_raw_html_block(
        "<p>This policy would <strong>add approximately $4,582 billion</strong> "
        "to the federal deficit, roughly <strong>$458B per year</strong>.</p>"
    )
    assert latex_risk("<p>$4,582 billion</strong> … <strong>$458B/yr</p>") == []
    # An inline tag leaves an ordinary markdown paragraph, which IS math-parsed.
    assert not is_raw_html_block("<small><b>Range:</b> $+1B to $+2B</small>")
    assert latex_risk("<small><b>Range:</b> $+1B to $+2B</small>")
    # A markdown paragraph that merely *contains* HTML later on is not a block.
    assert not is_raw_html_block("Totals below.\n\n<span>$5.00 of $6.00</span>")


def test_detector_accepts_safe_currency():
    from fiscal_model.ui.helpers import escape_markdown_dollars

    assert latex_risk("A single amount of $4,600B is fine") == []
    assert latex_risk("escaped \\$5.00 and \\$6.00") == []
    assert latex_risk("`$5.00 of $6.00` in code") == []
    assert latex_risk(escape_markdown_dollars("$5.00 of $6.00")) == []


def test_rate_limit_over_cap_message_is_escaped():
    """NOTES §11.22 named this string as the known live offender."""
    from fiscal_model.assistant.rate_limit import RateLimitConfig, RateLimiter

    limiter = RateLimiter(config=RateLimitConfig(daily_cost_cap_usd=0.0))
    decision = limiter.check(
        session_id="dollar-rendering-test",
        session_message_count=0,
        last_message_ts=None,
    )
    assert not decision.allowed
    assert "budget is exhausted" in decision.reason
    assert latex_risk(decision.reason) == []
