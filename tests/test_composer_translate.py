"""
Tests for ``fiscal_model.composer.translate``.

Fully mocked — no network, no API key required. Covers:

* Happy path — a forced ``set_goal_spec`` tool call becomes a valid GoalSpec.
* Fallback reasons — empty text, missing key, API exception, no tool block,
  malformed tool input, and a spec that fails ``GoalSpec.validate()``.
* Coercion — unknown category/philosophy/stance are clamped, not fatal.
* Request shape — forced tool choice, small max_tokens, model from
  ``PACKAGE_STUDIO_MODEL``, and user text confined to the user message.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from fiscal_model.composer.goal_spec import GoalSpec
from fiscal_model.composer.translate import (
    DEFAULT_MODEL,
    MODEL_ENV_VAR,
    TOOL_NAME,
    translate_goal_text,
)

SAMPLE_TEXT = "I want progressive taxes to pay for childcare and infrastructure."

VALID_PAYLOAD: dict[str, Any] = {
    "revenue_philosophy": "progressive",
    "deficit_stance": "neutral",
    "spending_goals": [
        {"label": "Universal child care", "category": "education", "annual_billions": 40},
        {"label": "Roads and bridges", "category": "infrastructure", "annual_billions": None},
    ],
    "notes": "User asked to avoid taxing under $400K.",
    "min_revenue_10yr_billions": 1000,
}


def _tool_block(payload: Any, name: str = TOOL_NAME) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id="toolu_1", name=name, input=payload)


def _mock_client(*blocks: Any) -> MagicMock:
    """Anthropic client whose messages.create returns the given content blocks."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=list(blocks), stop_reason="tool_use"
    )
    return client


@pytest.fixture(autouse=True)
def _no_ambient_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a developer's real key leak into these tests."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv(MODEL_ENV_VAR, raising=False)


class TestHappyPath:
    def test_parses_tool_use_into_goal_spec(self) -> None:
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=client)

        assert reason == ""
        assert isinstance(spec, GoalSpec)
        assert spec.revenue_philosophy == "progressive"
        assert spec.deficit_stance == "neutral"
        assert spec.min_revenue_10yr_billions == 1000.0
        assert spec.notes.startswith("User asked")
        assert [g.label for g in spec.spending_goals] == [
            "Universal child care",
            "Roads and bridges",
        ]
        assert [g.category for g in spec.spending_goals] == [
            "education",
            "infrastructure",
        ]
        assert spec.spending_goals[0].annual_billions == 40.0
        assert spec.spending_goals[1].annual_billions is None
        assert spec.validate() == []

    def test_accepts_plain_dict_content_blocks(self) -> None:
        """The SDK may hand back dicts (e.g. replayed history) — parse those too."""
        block = {"type": "tool_use", "id": "toolu_1", "name": TOOL_NAME, "input": VALID_PAYLOAD}
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(block))
        assert reason == ""
        assert spec is not None and spec.revenue_philosophy == "progressive"

    def test_no_spending_goals_is_valid(self) -> None:
        payload = {
            "revenue_philosophy": "mixed",
            "deficit_stance": "reduce",
            "spending_goals": [],
            "notes": "",
            "min_revenue_10yr_billions": 2000,
        }
        spec, reason = translate_goal_text("Cut the deficit.", client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert spec.spending_goals == ()
        assert spec.deficit_stance == "reduce"


class TestRequestShape:
    def test_forces_the_tool_and_keeps_user_text_out_of_the_prompt(self) -> None:
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        translate_goal_text(SAMPLE_TEXT, client=client)

        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
        assert [t["name"] for t in kwargs["tools"]] == [TOOL_NAME]
        assert kwargs["max_tokens"] <= 500
        # User text is data: it appears in the user message and nowhere else.
        assert kwargs["messages"] == [{"role": "user", "content": SAMPLE_TEXT}]
        assert SAMPLE_TEXT not in kwargs["system"]
        assert SAMPLE_TEXT not in str(kwargs["tools"])

    def test_default_model_is_the_cheap_one(self) -> None:
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        translate_goal_text(SAMPLE_TEXT, client=client)
        assert client.messages.create.call_args.kwargs["model"] == DEFAULT_MODEL

    def test_model_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(MODEL_ENV_VAR, "claude-sonnet-4-6")
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        translate_goal_text(SAMPLE_TEXT, client=client)
        assert client.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"

    def test_long_input_is_truncated(self) -> None:
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        translate_goal_text("spend " * 5_000, client=client)
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert len(sent) <= 2_000


class TestFallbackReasons:
    def test_empty_text_never_calls_the_api(self) -> None:
        client = _mock_client(_tool_block(VALID_PAYLOAD))
        spec, reason = translate_goal_text("   ", client=client)
        assert spec is None
        assert reason
        client.messages.create.assert_not_called()

    def test_missing_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        spec, reason = translate_goal_text(SAMPLE_TEXT)
        assert spec is None
        assert "key" in reason.lower()

    def test_api_exception_is_reported_not_raised(self) -> None:
        client = MagicMock()
        client.messages.create.side_effect = RuntimeError("overloaded_error")
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=client)
        assert spec is None
        assert "overloaded_error" in reason

    def test_no_tool_block_in_response(self) -> None:
        text_only = SimpleNamespace(type="text", text="Sure, here's a package idea!")
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(text_only))
        assert spec is None
        assert reason

    def test_malformed_tool_input(self) -> None:
        """A non-object tool input is a fallback, not a crash."""
        spec, reason = translate_goal_text(
            SAMPLE_TEXT, client=_mock_client(_tool_block("progressive"))
        )
        assert spec is None
        assert "malformed" in reason.lower()

    def test_empty_content_list(self) -> None:
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client())
        assert spec is None
        assert reason

    def test_invalid_spec_reports_validate_problems(self) -> None:
        payload = {
            "revenue_philosophy": "progressive",
            "deficit_stance": "invest",
            "spending_goals": [
                {"label": "Negative program", "category": "climate", "annual_billions": -25}
            ],
            "notes": "",
        }
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert spec is None
        assert "negative" in reason.lower()


class TestCoercion:
    def test_unknown_category_becomes_other(self) -> None:
        payload = {
            "revenue_philosophy": "progressive",
            "deficit_stance": "neutral",
            "spending_goals": [
                {"label": "Space elevator", "category": "space_program", "annual_billions": 12}
            ],
        }
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert spec.spending_goals[0].category == "other"
        assert spec.spending_goals[0].label == "Space elevator"

    def test_unknown_philosophy_and_stance_are_clamped(self) -> None:
        payload = {
            "revenue_philosophy": "flat_tax",
            "deficit_stance": "balanced_budget",
            "spending_goals": [],
        }
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert spec.revenue_philosophy == "mixed"
        assert spec.deficit_stance == "neutral"

    def test_missing_optional_fields_default_cleanly(self) -> None:
        payload = {"revenue_philosophy": "corporate", "deficit_stance": "invest"}
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert spec.spending_goals == ()
        assert spec.notes == ""
        assert spec.min_revenue_10yr_billions is None

    def test_junk_numbers_and_entries_are_dropped(self) -> None:
        payload = {
            "revenue_philosophy": "broad_base",
            "deficit_stance": "neutral",
            "spending_goals": [
                {"label": "Rail", "category": "infrastructure", "annual_billions": "lots"},
                "not an object",
                {"label": "", "category": "safety_net"},
            ],
            "min_revenue_10yr_billions": "unspecified",
        }
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert len(spec.spending_goals) == 2
        assert spec.spending_goals[0].annual_billions is None
        assert spec.spending_goals[1].label == "Safety Net"  # label falls back to category
        assert spec.min_revenue_10yr_billions is None

    def test_too_many_goals_are_capped(self) -> None:
        payload = {
            "revenue_philosophy": "mixed",
            "deficit_stance": "neutral",
            "spending_goals": [
                {"label": f"Program {i}", "category": "other"} for i in range(20)
            ],
        }
        spec, reason = translate_goal_text(SAMPLE_TEXT, client=_mock_client(_tool_block(payload)))
        assert reason == ""
        assert spec is not None
        assert len(spec.spending_goals) == 8
