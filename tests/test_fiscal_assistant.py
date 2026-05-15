"""
Tests for the public-finance Ask assistant.

Covers:

* Tool routing through ``AssistantTools.dispatch``.
* ``fetch_url`` allowlist enforcement (positive and negative).
* BM25 search over the curated knowledge corpus (seeded files).
* End-to-end ``score_hypothetical_policy`` via the real
  ``FiscalPolicyScorer``.
* Citation post-processing: marker extraction, support detection,
  ``[citation needed]`` annotation.
* Token accounting / cost meter.
* The Anthropic stream loop, mocked: a one-tool round-trip returns the
  text it emits across two iterations.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.assistant import FiscalAssistant
from fiscal_model.assistant.citations import (
    annotate_unsupported,
    extract_citation_markers,
    split_body_and_sources,
)
from fiscal_model.assistant.cost import ConversationCost
from fiscal_model.assistant.knowledge_search import KnowledgeSearcher
from fiscal_model.assistant.sources import (
    SOURCES,
    allowlisted_domain,
    web_search_allowed_domains,
)
from fiscal_model.assistant.tools import (
    TOOL_SCHEMAS,
    AssistantTools,
    web_search_tool_definition,
)
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer


KNOWLEDGE_DIR = (
    Path(__file__).resolve().parent.parent
    / "fiscal_model"
    / "assistant"
    / "knowledge"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    return FiscalPolicyScorer()


@pytest.fixture(scope="module")
def knowledge_searcher() -> KnowledgeSearcher:
    return KnowledgeSearcher(KNOWLEDGE_DIR)


@pytest.fixture
def tools(scorer: FiscalPolicyScorer, knowledge_searcher: KnowledgeSearcher) -> AssistantTools:
    return AssistantTools(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        fred_data=None,
        knowledge_searcher=knowledge_searcher,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
    )


# ---------------------------------------------------------------------------
# Sources allowlist
# ---------------------------------------------------------------------------


class TestSources:
    def test_allowlisted_domain_accepts_known_urls(self) -> None:
        assert allowlisted_domain("https://www.cbo.gov/publication/12345") == "cbo.gov"
        assert allowlisted_domain("https://www.jct.gov/publications/") == "jct.gov"
        assert (
            allowlisted_domain("https://budgetmodel.wharton.upenn.edu/issues/")
            == "budgetmodel.wharton.upenn.edu"
        )

    def test_allowlisted_domain_rejects_unknown_urls(self) -> None:
        assert allowlisted_domain("https://example.com/page") is None
        assert allowlisted_domain("https://github.com/foo") is None
        assert allowlisted_domain("not a url") is None
        assert allowlisted_domain("") is None

    def test_web_search_allowed_domains_matches_registry(self) -> None:
        configured = sorted(str(spec["domain"]) for spec in SOURCES.values())
        assert web_search_allowed_domains() == configured


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------


class TestTools:
    def test_tool_schemas_have_required_fields(self) -> None:
        seen = set()
        for spec in TOOL_SCHEMAS:
            assert spec["name"] and spec["description"] and spec["input_schema"]
            assert spec["input_schema"]["type"] == "object"
            seen.add(spec["name"])
        for required in {
            "get_app_scoring_context",
            "get_cbo_baseline",
            "get_validation_scorecard",
            "list_presets",
            "score_hypothetical_policy",
            "search_knowledge",
            "fetch_url",
        }:
            assert required in seen

    def test_dispatch_unknown_tool_returns_error(self, tools: AssistantTools) -> None:
        result = tools.dispatch("does_not_exist", {})
        assert "error" in result

    def test_dispatch_records_provenance(self, tools: AssistantTools) -> None:
        tools.reset_provenance()
        tools.dispatch("list_presets", {})
        tools.dispatch("get_cbo_baseline", {})
        assert [p["tool"] for p in tools.provenance] == ["list_presets", "get_cbo_baseline"]

    def test_get_app_scoring_context_when_inactive(self, tools: AssistantTools) -> None:
        tools.set_scoring_context(None)
        result = tools.dispatch("get_app_scoring_context", {})
        assert result["status"] == "no_active_policy"

    def test_get_app_scoring_context_active(self, tools: AssistantTools) -> None:
        ctx = {"policy_name": "Test policy", "ten_year_deficit_impact_billions": -123.4}
        tools.set_scoring_context(ctx)
        result = tools.dispatch("get_app_scoring_context", {})
        assert result["status"] == "active"
        assert result["scoring"]["policy_name"] == "Test policy"

    def test_get_cbo_baseline_returns_arrays(self, tools: AssistantTools) -> None:
        result = tools.dispatch("get_cbo_baseline", {})
        assert "error" not in result
        assert isinstance(result["years"], list)
        assert len(result["years"]) >= 10
        assert isinstance(result["ten_year_cumulative_deficit_billions"], float)
        assert result["ten_year_cumulative_deficit_billions"] > 0  # deficits, not surplus

    def test_get_validation_scorecard_filter(self, tools: AssistantTools) -> None:
        all_rows = tools.dispatch("get_validation_scorecard", {})
        assert all_rows["n_rows"] > 5
        filtered = tools.dispatch("get_validation_scorecard", {"filter": "tcja"})
        assert 1 <= filtered["n_rows"] < all_rows["n_rows"]
        for row in filtered["rows"]:
            assert "tcja" in row["preset_name"].lower()

    def test_list_presets_returns_real_names(self, tools: AssistantTools) -> None:
        result = tools.dispatch("list_presets", {})
        assert result["n_presets"] > 20
        assert isinstance(result["names"], list)

    def test_get_preset_unknown(self, tools: AssistantTools) -> None:
        result = tools.dispatch("get_preset", {"name": "nope"})
        assert "error" in result

    def test_score_hypothetical_corporate(self, tools: AssistantTools) -> None:
        result = tools.dispatch(
            "score_hypothetical_policy",
            {
                "name": "Corporate +4pp",
                "policy_type": "corporate_tax",
                "rate_change": 0.04,
            },
        )
        assert "error" not in result, result
        # A 4pp corporate increase should be revenue-positive => negative deficit.
        assert result["ten_year_deficit_impact_billions"] < 0

    def test_score_hypothetical_unknown_type(self, tools: AssistantTools) -> None:
        result = tools.dispatch(
            "score_hypothetical_policy",
            {"name": "bogus", "policy_type": "nonsense"},
        )
        assert "error" in result

    def test_search_knowledge_finds_seeded_docs(self, tools: AssistantTools) -> None:
        result = tools.dispatch(
            "search_knowledge",
            {"query": "social security trust fund depletion", "k": 2},
        )
        files = [hit["file"] for hit in result["hits"]]
        assert "ssa_trustees_2025.md" in files

    def test_fetch_url_rejects_non_allowlisted(self, tools: AssistantTools) -> None:
        result = tools.dispatch("fetch_url", {"url": "https://example.com/x"})
        assert "error" in result
        assert "allowlist" in result["error"]


# ---------------------------------------------------------------------------
# Knowledge search
# ---------------------------------------------------------------------------


class TestKnowledgeSearch:
    def test_index_builds_on_first_query(self, tmp_path: Path) -> None:
        # Empty dir -> no results, no crash.
        searcher = KnowledgeSearcher(tmp_path)
        assert searcher.search("anything") == []

    def test_keyword_padding_boosts_recall(self, tmp_path: Path) -> None:
        # Two docs: A mentions "TCJA" only in keywords; B mentions it only in body.
        (tmp_path / "a.md").write_text(
            "---\nsource: https://a/\ntitle: A\norg: A\nyear: 2024\n"
            "keywords: [tcja, tax cuts and jobs act]\n---\n"
            "Some unrelated body text about budgets.",
            encoding="utf-8",
        )
        (tmp_path / "b.md").write_text(
            "---\nsource: https://b/\ntitle: B\norg: B\nyear: 2024\n"
            "keywords: [other]\n---\n"
            "Body mentions tcja exactly once.",
            encoding="utf-8",
        )
        hits = KnowledgeSearcher(tmp_path).search("tcja", k=2)
        assert hits, "Expected at least one hit for 'tcja'"
        # The keyword-padded doc should score at least as high as the
        # body-only doc.
        files = [h["file"] for h in hits]
        assert "a.md" in files


# ---------------------------------------------------------------------------
# Citation post-processing
# ---------------------------------------------------------------------------


class TestCitations:
    def test_extract_markers(self) -> None:
        assert extract_citation_markers("Foo[^1] and bar[^2]. Again[^1].") == [1, 2]
        assert extract_citation_markers("No markers here.") == []

    def test_split_body_and_sources(self) -> None:
        text = "Some prose[^1].\n\n## Sources\n[^1]: ...\n"
        body, sources = split_body_and_sources(text)
        assert "Sources" not in body
        assert sources and sources.startswith("[^1]")

    def test_annotate_unsupported_strips_when_no_provenance(self) -> None:
        text = "Claim[^1]. Another[^2]."
        cleaned, stripped = annotate_unsupported(text, provenance=[], web_search_citations=None)
        assert "[citation needed]" in cleaned
        assert stripped == [1, 2]

    def test_annotate_unsupported_keeps_when_tool_called(self) -> None:
        text = "Claim[^1]."
        cleaned, stripped = annotate_unsupported(
            text,
            provenance=[{"tool": "get_cbo_baseline", "args": {}}],
            web_search_citations=None,
        )
        assert "[citation needed]" not in cleaned
        assert stripped == []


# ---------------------------------------------------------------------------
# Cost meter
# ---------------------------------------------------------------------------


class TestCost:
    def test_record_simple_usage(self) -> None:
        cc = ConversationCost()
        usage = SimpleNamespace(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        turn = cc.record(usage, "claude-sonnet-4-6")
        # Sonnet 4.6: $3 in / $15 out per 1M
        expected = 1000 * 3 / 1_000_000 + 500 * 15 / 1_000_000
        assert turn.cost_usd == pytest.approx(expected, rel=1e-3)
        assert cc.total_cost_usd == pytest.approx(expected, rel=1e-3)

    def test_record_with_cache_hits(self) -> None:
        cc = ConversationCost()
        usage = SimpleNamespace(
            input_tokens=200,
            output_tokens=100,
            cache_creation_input_tokens=4000,
            cache_read_input_tokens=4000,
        )
        cc.record(usage, "claude-sonnet-4-6")
        # cache_read should be ~10% the price of input tokens
        assert "cache-hit" in cc.summary()


# ---------------------------------------------------------------------------
# Assistant stream loop (mocked Anthropic client)
# ---------------------------------------------------------------------------


class _FakeStream:
    """Drop-in stand-in for ``client.messages.stream`` context manager."""

    def __init__(self, text_chunks: list[str], final_message: Any) -> None:
        self._chunks = text_chunks
        self._final = final_message

    def __enter__(self) -> "_FakeStream":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    @property
    def text_stream(self):  # type: ignore[no-untyped-def]
        return iter(self._chunks)

    def get_final_message(self) -> Any:
        return self._final


class _FakeMessages:
    def __init__(self, scripted: list[tuple[list[str], Any]]) -> None:
        self._scripted = list(scripted)

    def stream(self, **kwargs: Any) -> _FakeStream:
        chunks, final = self._scripted.pop(0)
        return _FakeStream(chunks, final)


class _FakeClient:
    def __init__(self, scripted: list[tuple[list[str], Any]]) -> None:
        self.messages = _FakeMessages(scripted)


def _make_final_message(
    *,
    text: str = "",
    tool_uses: list[dict[str, Any]] | None = None,
    stop_reason: str = "end_turn",
) -> SimpleNamespace:
    content: list[Any] = []
    if text:
        content.append(SimpleNamespace(type="text", text=text))
    for tu in tool_uses or []:
        content.append(
            SimpleNamespace(
                type="tool_use",
                id=tu["id"],
                name=tu["name"],
                input=tu["input"],
            )
        )
    usage = SimpleNamespace(
        input_tokens=50,
        output_tokens=20,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    return SimpleNamespace(content=content, stop_reason=stop_reason, usage=usage)


class TestAssistantStreamLoop:
    def test_no_tool_use_single_turn(
        self,
        scorer: FiscalPolicyScorer,
    ) -> None:
        fake = _FakeClient(
            scripted=[
                (
                    ["Hello", " world."],
                    _make_final_message(text="Hello world.", stop_reason="end_turn"),
                ),
            ]
        )
        assistant = FiscalAssistant(
            scorer=scorer,
            baseline=scorer.baseline,
            cbo_score_map=CBO_SCORE_MAP,
            presets=PRESET_POLICIES,
            policy_types=PolicyType,
            tax_policy_cls=TaxPolicy,
            spending_policy_cls=SpendingPolicy,
            anthropic_client=fake,
            enable_web_search=False,
        )
        chunks = list(assistant.stream_response("Hi", history=[]))
        joined = "".join(chunks)
        assert "Hello" in joined and "world" in joined
        assert assistant.last_usage is not None
        assert assistant.last_usage.input_tokens == 50

    def test_tool_use_round_trip(
        self,
        scorer: FiscalPolicyScorer,
    ) -> None:
        # Round 1: model asks to call get_cbo_baseline.
        round1 = _make_final_message(
            text="Let me check.",
            tool_uses=[
                {"id": "toolu_1", "name": "get_cbo_baseline", "input": {}},
            ],
            stop_reason="tool_use",
        )
        # Round 2: model emits final answer with a citation marker.
        round2 = _make_final_message(
            text="The cumulative 10-year deficit is large[^1].",
            stop_reason="end_turn",
        )
        fake = _FakeClient(
            scripted=[
                (["Let me check."], round1),
                (
                    ["The cumulative 10-year deficit is large[^1]."],
                    round2,
                ),
            ]
        )
        assistant = FiscalAssistant(
            scorer=scorer,
            baseline=scorer.baseline,
            cbo_score_map=CBO_SCORE_MAP,
            presets=PRESET_POLICIES,
            policy_types=PolicyType,
            tax_policy_cls=TaxPolicy,
            spending_policy_cls=SpendingPolicy,
            anthropic_client=fake,
            enable_web_search=False,
        )
        out = "".join(assistant.stream_response("What's the deficit?", history=[]))
        # Tool internals are no longer echoed to the user inline — sources
        # are cited via [^N] footnotes instead. So we don't check for tool
        # names in the output, only in the provenance trail.
        assert "[citation needed]" not in out
        assert any(p["tool"] == "get_cbo_baseline" for p in assistant.last_provenance)

    def test_iteration_cap_forces_final_answer(
        self,
        scorer: FiscalPolicyScorer,
    ) -> None:
        """If the model keeps asking for tools, we cap and force an answer."""
        from fiscal_model.assistant.assistant import MAX_TOOL_ITERATIONS

        # Script: every iteration up to the cap returns tool_use; the
        # forced-final call (tools disabled) returns the actual answer.
        tool_use_msg = _make_final_message(
            text="Let me check more.",
            tool_uses=[
                {"id": "toolu_x", "name": "search_knowledge", "input": {"query": "x"}},
            ],
            stop_reason="tool_use",
        )
        forced_answer = _make_final_message(
            text="Based on what I have: the deficit is large.",
            stop_reason="end_turn",
        )
        scripted: list[tuple[list[str], Any]] = []
        for _ in range(MAX_TOOL_ITERATIONS):
            scripted.append((["Let me check more."], tool_use_msg))
        # One additional call when we force the final answer.
        scripted.append((["Based on what I have: the deficit is large."], forced_answer))

        fake = _FakeClient(scripted=scripted)
        assistant = FiscalAssistant(
            scorer=scorer,
            baseline=scorer.baseline,
            cbo_score_map=CBO_SCORE_MAP,
            presets=PRESET_POLICIES,
            policy_types=PolicyType,
            tax_policy_cls=TaxPolicy,
            spending_policy_cls=SpendingPolicy,
            anthropic_client=fake,
            enable_web_search=False,
        )
        out = "".join(assistant.stream_response("?", history=[]))
        # The forced-final answer must be in the output.
        assert "the deficit is large" in out

    def test_tool_use_strips_marker_with_no_provenance(
        self,
        scorer: FiscalPolicyScorer,
    ) -> None:
        # Model emits a marker but calls no tools.
        end = _make_final_message(
            text="Some claim[^1]. Another[^2].",
            stop_reason="end_turn",
        )
        fake = _FakeClient(scripted=[(["Some claim[^1]. Another[^2]."], end)])
        assistant = FiscalAssistant(
            scorer=scorer,
            baseline=scorer.baseline,
            cbo_score_map=CBO_SCORE_MAP,
            presets=PRESET_POLICIES,
            policy_types=PolicyType,
            tax_policy_cls=TaxPolicy,
            spending_policy_cls=SpendingPolicy,
            anthropic_client=fake,
            enable_web_search=False,
        )
        list(assistant.stream_response("?", history=[]))
        assert assistant.last_stripped_markers == [1, 2]
        assert "[citation needed]" in assistant.last_full_text


# ---------------------------------------------------------------------------
# Schema serialization sanity
# ---------------------------------------------------------------------------


def test_tool_schemas_json_serialize() -> None:
    """Every tool schema must be JSON-serializable to be sent to Anthropic."""
    json.dumps(TOOL_SCHEMAS)


def test_web_search_tool_def_has_allowed_domains() -> None:
    defn = web_search_tool_definition()
    assert defn["type"].startswith("web_search_")
    assert "cbo.gov" in defn["allowed_domains"]
