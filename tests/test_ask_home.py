"""
End-to-end tests for the Ask home page (Phase 2 of the ask-first redesign).

These drive the real router through ``streamlit.testing.v1.AppTest`` with the
LLM replaced by a stub, so they cover the things unit tests cannot: that Ask
is what ``/`` renders, that the hero / chat input / suggestion chips / doorway
links are all actually on the page, that ``?q=`` asks exactly one question,
and that a finished answer carries a Sources row and no dangling ``[^N]``.

Building the real ``AppDependencies`` is the slow part (~5s), so it is done
once per module and the stub assistant is swapped in per test.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from fiscal_model.ui.tabs.ask_assistant import HERO_TITLE

DEPS_SESSION_KEY = "_app_dependencies"

# A model answer in the shape the system prompt asks for: inline markers plus
# a ``## Sources`` block.
ANSWER_WITH_SOURCES = (
    "CBO projects a cumulative deficit of about \\$21 trillion over the "
    "10-year window.[^1] Interest costs are the fastest-growing line.[^2]\n\n"
    "## Sources\n"
    '[^1]: CBO (2026), "The Budget and Economic Outlook", '
    "https://www.cbo.gov/publication/61116\n"
    '[^2]: CBO (2026), "Long-Term Budget Outlook", '
    "https://www.cbo.gov/topics/budget/long-term-budget-projections\n"
)

PROVENANCE = [
    {
        "tool": "search_knowledge",
        "args": {"query": "cbo deficit outlook"},
        "urls": ["https://www.cbo.gov/publication/61116"],
        "sources": [
            {
                "title": "The Budget and Economic Outlook 2025 to 2035",
                "publisher": "CBO",
                "date": "2026",
                "url": "https://www.cbo.gov/publication/61116",
            }
        ],
    },
    {
        "tool": "get_cbo_baseline",
        "args": {},
        "urls": [],
        "sources": [
            {
                "title": "CBO baseline as loaded by this app",
                "publisher": None,
                "date": None,
                "url": None,
            }
        ],
    },
]


class _StubCost:
    def __init__(self) -> None:
        self.turns: list[Any] = []

    def summary(self) -> str:
        return "No usage yet"


class StubAssistant:
    """Minimal stand-in for :class:`FiscalAssistant`; never calls an API."""

    def __init__(
        self,
        answer: str = ANSWER_WITH_SOURCES,
        provenance: list[dict[str, Any]] | None = None,
        truncated: bool = False,
    ) -> None:
        self._answer = answer
        self._model = "stub-model"
        self.cost = _StubCost()
        self.last_provenance = list(provenance if provenance is not None else PROVENANCE)
        self.last_usage = None
        self.last_full_text = answer
        self.last_stripped_markers: list[int] = []
        self.last_truncated = truncated
        self.last_stop_reason = "max_tokens" if truncated else "end_turn"
        self.questions: list[str] = []

    def is_available(self) -> bool:
        return True

    def stream_response(self, user_message, history=None, scoring_context=None):
        self.questions.append(user_message)
        self.last_scoring_context = scoring_context
        # Split mid-word so the $-safe re-chunker is genuinely exercised.
        midpoint = len(self._answer) // 2
        yield self._answer[:midpoint]
        yield self._answer[midpoint:]

    def suggest_followups(self, last_question, last_answer, max_suggestions=3):
        return []


@pytest.fixture(scope="module")
def base_deps():
    from fiscal_model.ui.dependencies import build_app_dependencies

    return build_app_dependencies(pd_module=pd)


@pytest.fixture(autouse=True)
def _isolated_usage_db(tmp_path, monkeypatch):
    """Keep the rate limiter off the developer's real usage database.

    The inter-turn cooldown is also switched off: it is real behaviour (a
    second question inside 3 seconds is refused with a warning), but every
    multi-turn test here fires instantly and would trip it.
    """
    monkeypatch.setenv("ASSISTANT_USAGE_DB", str(tmp_path / "usage.sqlite"))
    monkeypatch.setenv("ASSISTANT_COOLDOWN_SECONDS", "0")
    monkeypatch.delenv("ASSISTANT_DISABLED", raising=False)


def _app(base_deps, assistant: StubAssistant | None = None, **query) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=180)
    deps = dataclasses.replace(
        base_deps, fiscal_assistant=assistant or StubAssistant()
    )
    at.session_state[DEPS_SESSION_KEY] = deps
    for key, value in query.items():
        at.query_params[key] = value
    return at


def _all_markdown(at: AppTest) -> str:
    return "\n".join(element.value for element in at.markdown)


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def test_default_page_is_ask_and_renders_the_hero(base_deps):
    at = _app(base_deps).run()
    assert not at.exception, [e.message for e in at.exception]
    assert HERO_TITLE in _all_markdown(at)


def test_hero_carries_a_chat_input(base_deps):
    at = _app(base_deps).run()
    assert len(at.chat_input) == 1


def test_suggestion_chips_offer_at_least_six_questions(base_deps):
    at = _app(base_deps).run()
    groups = at.get("button_group")
    assert groups, "no st.pills row rendered"
    assert len(groups[0].proto.options) >= 6


def test_doorway_links_point_at_build_and_tailor(base_deps):
    at = _app(base_deps).run()
    targets = {link.proto.page for link in at.get("page_link")}
    assert {"build", "tailor"} <= targets


def test_worked_example_cards_render_with_status_chips(base_deps):
    at = _app(base_deps).run()
    labels = [button.label for button in at.button]
    assert labels.count("Ask this →") == 4
    rendered = _all_markdown(at) + "\n".join(c.value for c in at.caption)
    assert "P.L. 119-21" in rendered or "Enacted" in rendered
    assert "Proposal" in rendered


def test_clicking_a_worked_example_prefills_and_asks_it(base_deps):
    """Cards prefill the chat now; they no longer run a preset."""
    assistant = StubAssistant()
    at = _app(base_deps, assistant).run()
    next(b for b in at.button if b.label == "Ask this →").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert assistant.questions, "card click did not reach the assistant"
    assert assistant.questions[0].endswith("?")
    history = at.session_state["ask_history"]
    assert history[0]["content"] == assistant.questions[0]
    # The preset picker must NOT have been driven by the click.
    assert "results" not in at.session_state or at.session_state["results"] is None


def test_clicking_a_suggestion_chip_asks_that_question(base_deps):
    assistant = StubAssistant()
    at = _app(base_deps, assistant).run()
    at.get("button_group")[0].set_value("Explain dynamic scoring").run()
    assert not at.exception, [e.message for e in at.exception]
    assert assistant.questions, "chip click did not reach the assistant"
    assert "dynamic scoring" in assistant.questions[0].lower()


# ---------------------------------------------------------------------------
# ?q= prefill
# ---------------------------------------------------------------------------


def test_query_prefill_asks_once_and_lands_in_the_transcript(base_deps):
    assistant = StubAssistant()
    at = _app(base_deps, assistant, q="What does CBO project for the deficit?").run()
    assert not at.exception, [e.message for e in at.exception]
    assert assistant.questions == ["What does CBO project for the deficit?"]
    history = at.session_state["ask_history"]
    assert [turn["role"] for turn in history] == ["user", "assistant"]
    assert history[0]["content"] == "What does CBO project for the deficit?"


def test_query_prefill_does_not_re_ask_on_rerun(base_deps):
    assistant = StubAssistant()
    at = _app(base_deps, assistant, q="Explain dynamic scoring.").run()
    at.run()
    assert assistant.questions == ["Explain dynamic scoring."]


def test_blank_query_prefill_asks_nothing(base_deps):
    assistant = StubAssistant()
    _app(base_deps, assistant, q="   ").run()
    assert assistant.questions == []


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------


def test_answer_renders_a_sources_row_with_a_link(base_deps):
    at = _app(base_deps, StubAssistant(), q="What is the deficit?").run()
    rendered = _all_markdown(at)
    assert "Sources (" in rendered
    assert re.search(r"\]\(https?://", rendered), "no linked source rendered"


def test_no_bare_footnote_markers_survive_to_the_page(base_deps):
    at = _app(base_deps, StubAssistant(), q="What is the deficit?").run()
    assert "[^" not in _all_markdown(at)


def test_dollar_amounts_are_escaped_not_rendered_as_math(base_deps):
    at = _app(base_deps, StubAssistant(), q="What is the deficit?").run()
    rendered = _all_markdown(at)
    assert "\\$21 trillion" in rendered


def test_truncated_answer_offers_a_continue_button(base_deps):
    assistant = StubAssistant(answer="A table that stops mid-", truncated=True)
    at = _app(base_deps, assistant, q="Give me a table.").run()
    assert any("Continue the answer" in button.label for button in at.button)


def test_untruncated_answer_offers_no_continue_button(base_deps):
    at = _app(base_deps, StubAssistant(), q="What is the deficit?").run()
    assert not any("Continue the answer" in button.label for button in at.button)


def test_continuing_a_truncated_answer_does_not_collide_on_widget_keys(base_deps):
    """A truncated continuation renders two Continue buttons in one run."""
    assistant = StubAssistant(answer="Row 1 | Row 2 | Row", truncated=True)
    at = _app(base_deps, assistant, q="Give me a table.").run()
    continues = [b for b in at.button if "Continue the answer" in b.label]
    assert len(continues) == 1
    continues[0].click().run()
    assert not at.exception, [e.message for e in at.exception]
    from fiscal_model.ui.tabs.ask_assistant import CONTINUE_PROMPT

    assert assistant.questions[-1] == CONTINUE_PROMPT


# ---------------------------------------------------------------------------
# Context chip
# ---------------------------------------------------------------------------


def test_context_chip_hidden_when_nothing_is_scored(base_deps):
    at = _app(base_deps).run()
    captions = "\n".join(c.value for c in at.caption)
    assert "Using current scored policy" not in captions


def test_context_chip_names_the_current_policy(base_deps):
    at = _app(base_deps)
    at.session_state["results"] = {
        "policy_name": "TCJA Full Extension",
        "result": None,
        "is_spending": False,
    }
    at.run()
    captions = "\n".join(c.value for c in at.caption)
    assert "Using current scored policy" in captions
    assert "TCJA Full Extension" in captions


class TestCurrentPolicyNameHelper:
    """Reads defensively across the legacy dict and the Phase-4 result object."""

    def test_legacy_results_dict(self):
        from fiscal_model.ui.tabs.ask_assistant import _current_policy_name

        assert _current_policy_name({"policy_name": "Biden Corporate 28%"}) == (
            "Biden Corporate 28%"
        )

    def test_result_object_attribute(self):
        from types import SimpleNamespace

        from fiscal_model.ui.tabs.ask_assistant import _current_policy_name

        result = SimpleNamespace(policy_name="Estate Reform", policy=None)
        assert _current_policy_name(result) == "Estate Reform"

    def test_falls_back_to_the_policy_object(self):
        from types import SimpleNamespace

        from fiscal_model.ui.tabs.ask_assistant import _current_policy_name

        result = SimpleNamespace(policy=SimpleNamespace(name="SS Donut Hole"))
        assert _current_policy_name(result) == "SS Donut Hole"

    def test_none_when_nothing_scored(self):
        from fiscal_model.ui.tabs.ask_assistant import _current_policy_name

        assert _current_policy_name(None) is None
        assert _current_policy_name({}) is None
