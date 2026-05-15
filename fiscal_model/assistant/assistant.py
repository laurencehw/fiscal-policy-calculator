"""
:class:`FiscalAssistant` — orchestrates the Claude tool-use loop with streaming.

Mirrors the lazy-client pattern from ``bill_tracker/provision_mapper.py`` so
the Anthropic SDK is only imported when actually needed.

Streaming contract (used by ``ui/tabs/ask_assistant.py``):

    for chunk in assistant.stream_response(user_message, history, scoring_context):
        ...  # chunk is always ``str``: append to the chat bubble verbatim.

After the generator completes, the caller can read:

* ``assistant.last_provenance`` — list of tool calls performed this turn
* ``assistant.last_usage``      — :class:`TurnUsage`
* ``assistant.last_full_text``  — the raw full answer (post-citation-cleanup)
* ``assistant.last_message``    — appended to history for next turn

The agentic loop is capped at :attr:`MAX_TOOL_ITERATIONS` to prevent infinite
loops in pathological cases.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterator
from typing import Any

from .citations import annotate_unsupported
from .cost import ConversationCost, TurnUsage
from .system_prompt import build_system_prompt, stable_prompt_prefix
from .tools import TOOL_SCHEMAS, AssistantTools, web_search_tool_definition

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "claude-sonnet-4-6"
OPUS_MODEL = "claude-opus-4-7"
MAX_TOOL_ITERATIONS = 4
DEFAULT_MAX_TOKENS = 1600


class FiscalAssistant:
    """Public-finance Q&A assistant with grounded tool use.

    Dependencies are injected so the same assistant can be used from
    Streamlit, FastAPI, or tests. The Anthropic client is lazy.
    """

    def __init__(
        self,
        *,
        scorer: Any,
        baseline: Any,
        cbo_score_map: dict[str, dict[str, Any]],
        presets: dict[str, dict[str, Any]],
        fred_data: Any = None,
        knowledge_dir: Any = None,
        policy_types: Any = None,
        tax_policy_cls: Any = None,
        spending_policy_cls: Any = None,
        anthropic_client: Any = None,
        model: str = DEFAULT_MODEL,
        enable_web_search: bool = True,
    ) -> None:
        self._client = anthropic_client
        self._model = model
        self._enable_web_search = enable_web_search

        searcher = None
        if knowledge_dir is not None:
            try:
                from .knowledge_search import KnowledgeSearcher

                searcher = KnowledgeSearcher(knowledge_dir)
            except Exception:  # noqa: BLE001
                logger.exception("Failed to initialize knowledge searcher")

        self._tools = AssistantTools(
            scorer=scorer,
            baseline=baseline,
            cbo_score_map=cbo_score_map,
            presets=presets,
            fred_data=fred_data,
            knowledge_searcher=searcher,
            policy_types=policy_types,
            tax_policy_cls=tax_policy_cls,
            spending_policy_cls=spending_policy_cls,
        )

        self.cost = ConversationCost()
        self.last_provenance: list[dict[str, Any]] = []
        self.last_usage: TurnUsage | None = None
        self.last_full_text: str = ""
        self.last_message: dict[str, Any] | None = None
        self.last_stripped_markers: list[int] = []
        self.last_web_citations: list[str] = []

    # ---- lazy client -----------------------------------------------------

    @property
    def client(self):  # noqa: D401
        """Return the Anthropic client, initializing it on first use."""
        if self._client is None:
            try:
                import anthropic
            except ImportError as err:  # pragma: no cover
                raise RuntimeError(
                    "anthropic package is required for FiscalAssistant. "
                    "Install it: pip install 'anthropic>=0.49.0'"
                ) from err
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
        return self._client

    def is_available(self) -> bool:
        """Whether the assistant can be used (i.e., API key is present)."""
        if self._client is not None:
            return True
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    # ---- follow-up generation -------------------------------------------

    def suggest_followups(
        self,
        last_question: str,
        last_answer: str,
        max_suggestions: int = 3,
    ) -> list[str]:
        """Ask the model for 2–3 short follow-up questions a reader might want.

        Issues a cheap separate API call with no tools and small max_tokens
        so it doesn't double the cost of the main turn. Returns an empty
        list on any failure — follow-ups are a nicety, not load-bearing.
        """
        if not self.is_available():
            return []
        prompt = (
            "You just answered this user question:\n\n"
            f"USER: {last_question.strip()[:400]}\n\n"
            f"ASSISTANT: {last_answer.strip()[:1500]}\n\n"
            f"Suggest exactly {max_suggestions} short follow-up questions a "
            "thoughtful reader might ask next about THIS topic. Each should "
            "be a single sentence ending in a question mark, on its own line, "
            "with no numbering, bullets, or quotes. Aim for breadth — one "
            "comparison, one mechanism, one policy angle. Do not preface "
            "with anything; output ONLY the questions, one per line."
        )
        try:
            msg = self.client.messages.create(
                model="claude-haiku-4-5-20251001",  # cheap; Haiku is fine
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:  # noqa: BLE001
            logger.warning("Followup suggestion call failed", exc_info=True)
            return []

        # Extract plain text.
        text_parts: list[str] = []
        for block in getattr(msg, "content", None) or []:
            t = getattr(block, "text", None)
            if isinstance(t, str):
                text_parts.append(t)
        text = "\n".join(text_parts).strip()
        if not text:
            return []

        suggestions: list[str] = []
        for raw in text.splitlines():
            cleaned = raw.strip().lstrip("-*•").strip().strip('"').strip("'")
            # Drop numbered prefixes like "1.", "1)" if Claude ignores the
            # instruction.
            if cleaned and cleaned[0].isdigit() and len(cleaned) > 2:
                if cleaned[1] in ".):" and cleaned[2] == " ":
                    cleaned = cleaned[3:].strip()
                elif cleaned[1] == " ":
                    cleaned = cleaned[2:].strip()
            if cleaned and cleaned.endswith("?") and len(cleaned) < 200:
                suggestions.append(cleaned)
            if len(suggestions) >= max_suggestions:
                break
        return suggestions

    # ---- main entry point ------------------------------------------------

    def stream_response(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        scoring_context: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Yield chunks of the assistant's response as it streams.

        Parameters
        ----------
        user_message:
            The user's new question for this turn.
        history:
            Prior conversation, as a list of ``{"role": "user"|"assistant",
            "content": ...}`` dicts. The assistant content may be either a
            string (simple) or a list of content blocks (for resumed
            tool-use turns).
        scoring_context:
            Current scoring result snapshot (optional). Injected into the
            system prompt for grounding.
        """
        # ------------------------------------------------------------------
        # Reset per-turn state.
        # ------------------------------------------------------------------
        self._tools.reset_provenance()
        self._tools.set_scoring_context(scoring_context)
        self.last_provenance = []
        self.last_usage = None
        self.last_full_text = ""
        self.last_message = None
        self.last_stripped_markers = []
        self.last_web_citations = []

        # ------------------------------------------------------------------
        # Build system blocks. We split into a cache-stable prefix and a
        # per-turn context block so Anthropic prompt caching applies to the
        # large stable part.
        # ------------------------------------------------------------------
        prefix = stable_prompt_prefix()
        full_prompt = build_system_prompt(scoring_context)
        context_block = full_prompt[len(prefix):].lstrip()

        system_blocks: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": prefix,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if context_block:
            system_blocks.append({"type": "text", "text": context_block})

        # ------------------------------------------------------------------
        # Assemble messages.
        # ------------------------------------------------------------------
        messages: list[dict[str, Any]] = list(history) + [
            {"role": "user", "content": user_message}
        ]

        tools_param = list(TOOL_SCHEMAS)
        if self._enable_web_search:
            tools_param.append(web_search_tool_definition())

        # ------------------------------------------------------------------
        # Agentic loop.
        # ------------------------------------------------------------------
        accumulated_text = ""
        final_message = None
        hit_iteration_cap = False
        for iteration in range(MAX_TOOL_ITERATIONS):
            stream_result = self._run_one_stream(
                system_blocks=system_blocks,
                messages=messages,
                tools=tools_param,
            )
            iter_text = ""
            for chunk in stream_result["text_chunks"]:
                iter_text += chunk
                yield chunk
            accumulated_text += iter_text

            final_message = stream_result["final_message"]
            self._record_usage(stream_result.get("usage"))

            # Capture any web_search citations from the model's output for
            # later citation cross-referencing.
            self.last_web_citations.extend(
                _extract_web_search_citations(final_message)
            )

            stop_reason = getattr(final_message, "stop_reason", None)
            if stop_reason != "tool_use":
                break

            tool_uses = _collect_tool_uses(final_message)
            if not tool_uses:
                break

            # If this was the last allowed iteration, fall through to the
            # "force final answer" code below WITHOUT running these tools.
            # That way we don't spend $$ on tool calls whose results we'll
            # never let the model consume.
            if iteration == MAX_TOOL_ITERATIONS - 1:
                hit_iteration_cap = True
                break

            # Append the assistant turn (with full content blocks) before the
            # tool results so the next request is valid.
            messages.append(
                {
                    "role": "assistant",
                    "content": _serialize_content_blocks(final_message.content),
                }
            )

            # Run each tool call. We do NOT echo tool names to the user — the
            # final answer should speak for itself, with [^N] citations.
            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                if tu["type"] == "server_tool_use":
                    # Web search is server-side; Anthropic handled it.
                    continue
                tool_name = tu["name"]
                tool_args = tu["input"] or {}
                result = self._tools.dispatch(tool_name, tool_args)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": json.dumps(result, default=str)[:30_000],
                    }
                )

            if not tool_results:
                # Only server-side tools were used; loop again to let the
                # model continue with their results.
                continue

            messages.append({"role": "user", "content": tool_results})

        # If we hit the iteration cap without a clean stop, ask the model
        # one more time WITHOUT tools to write the final answer using
        # whatever it has gathered. Otherwise the user sees only the
        # model's thinking-out-loud preamble and no actual answer.
        if hit_iteration_cap and final_message is not None:
            # Persist the last assistant turn (its tool_use blocks) so the
            # model can summarize from them.
            messages.append(
                {
                    "role": "assistant",
                    "content": _serialize_content_blocks(final_message.content),
                }
            )
            # Synthesize empty tool_results so the conversation is valid.
            tool_uses_for_stub = _collect_tool_uses(final_message)
            stub_results: list[dict[str, Any]] = [
                {
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": json.dumps(
                        {
                            "note": (
                                "Skipped: tool-call budget exhausted. "
                                "Write the final answer with what you already have."
                            )
                        }
                    ),
                }
                for tu in tool_uses_for_stub
                if tu["type"] == "tool_use"
            ]
            if stub_results:
                messages.append({"role": "user", "content": stub_results})
            # One last call, tools disabled, to force a real answer.
            forced = self._run_one_stream(
                system_blocks=system_blocks,
                messages=messages,
                tools=[],  # no tools → model must answer or end_turn
            )
            for chunk in forced["text_chunks"]:
                accumulated_text += chunk
                yield chunk
            final_message = forced["final_message"]
            self._record_usage(forced.get("usage"))

        # ------------------------------------------------------------------
        # Post-process: citation hygiene.
        # ------------------------------------------------------------------
        self.last_provenance = list(self._tools.provenance)
        cleaned, stripped = annotate_unsupported(
            accumulated_text,
            self.last_provenance,
            web_search_citations=self.last_web_citations,
        )
        self.last_full_text = cleaned
        self.last_stripped_markers = stripped

        # If we stripped markers, append a transparency note.
        if stripped:
            note = (
                "\n\n> ⚠️ The model emitted "
                f"{len(stripped)} citation marker(s) without supporting tool "
                "calls or sources. They were replaced with `[citation needed]` "
                "above."
            )
            yield note

        # ------------------------------------------------------------------
        # Build the next-turn history entry.
        # ------------------------------------------------------------------
        if final_message is not None:
            self.last_message = {
                "role": "assistant",
                # Store text-only for simple history threading next turn.
                "content": cleaned,
                "provenance": self.last_provenance,
                "usage": self.last_usage.to_dict() if self.last_usage else None,
                "stripped_markers": stripped,
            }

    # ---- helpers ---------------------------------------------------------

    def _run_one_stream(
        self,
        *,
        system_blocks: list[dict[str, Any]],
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Run a single ``messages.stream`` call. Returns chunks + final msg."""
        text_chunks: list[str] = []
        final_message = None
        usage = None
        client = self.client

        try:
            with client.messages.stream(
                model=self._model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=system_blocks,
                messages=messages,
                tools=tools,
            ) as stream:
                for text in stream.text_stream:
                    text_chunks.append(text)
                final_message = stream.get_final_message()
                usage = getattr(final_message, "usage", None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Anthropic stream failed")
            text_chunks.append(f"\n\n*Error from Anthropic API: {exc}*")

        return {
            "text_chunks": text_chunks,
            "final_message": final_message,
            "usage": usage,
        }

    def _record_usage(self, usage: Any) -> None:
        turn = self.cost.record(usage, self._model)
        if self.last_usage is None:
            self.last_usage = turn
        else:
            self.last_usage = TurnUsage(
                input_tokens=self.last_usage.input_tokens + turn.input_tokens,
                output_tokens=self.last_usage.output_tokens + turn.output_tokens,
                cache_creation_tokens=self.last_usage.cache_creation_tokens + turn.cache_creation_tokens,
                cache_read_tokens=self.last_usage.cache_read_tokens + turn.cache_read_tokens,
                cost_usd=self.last_usage.cost_usd + turn.cost_usd,
            )


# ---------------------------------------------------------------------------
# Anthropic content-block helpers
# ---------------------------------------------------------------------------


def _collect_tool_uses(final_message: Any) -> list[dict[str, Any]]:
    """Extract tool_use / server_tool_use blocks from a final Message."""
    out: list[dict[str, Any]] = []
    content = getattr(final_message, "content", None) or []
    for block in content:
        btype = getattr(block, "type", None) or (
            block.get("type") if isinstance(block, dict) else None
        )
        if btype in ("tool_use", "server_tool_use"):
            out.append(
                {
                    "type": btype,
                    "id": getattr(block, "id", None) or (block.get("id") if isinstance(block, dict) else None),
                    "name": getattr(block, "name", None) or (block.get("name") if isinstance(block, dict) else None),
                    "input": getattr(block, "input", None) or (block.get("input") if isinstance(block, dict) else None) or {},
                }
            )
    return out


def _serialize_content_blocks(content: Any) -> list[dict[str, Any]]:
    """Convert SDK content blocks to plain dicts suitable for re-sending."""
    out: list[dict[str, Any]] = []
    for block in content or []:
        if isinstance(block, dict):
            out.append(block)
            continue
        btype = getattr(block, "type", None)
        if btype == "text":
            out.append({"type": "text", "text": getattr(block, "text", "")})
        elif btype == "tool_use":
            out.append(
                {
                    "type": "tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}) or {},
                }
            )
        elif btype == "server_tool_use":
            out.append(
                {
                    "type": "server_tool_use",
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": getattr(block, "input", {}) or {},
                }
            )
        elif btype == "web_search_tool_result":
            out.append(
                {
                    "type": "web_search_tool_result",
                    "tool_use_id": getattr(block, "tool_use_id", ""),
                    "content": getattr(block, "content", None),
                }
            )
        else:
            # Fall back to a dict-style copy.
            try:
                out.append(block.model_dump())  # pydantic v2
            except Exception:  # noqa: BLE001
                out.append({"type": btype or "unknown"})
    return out


def _extract_web_search_citations(final_message: Any) -> list[str]:
    """Pull URLs out of any ``web_search_tool_result`` blocks."""
    urls: list[str] = []
    content = getattr(final_message, "content", None) or []
    for block in content:
        btype = getattr(block, "type", None) or (
            block.get("type") if isinstance(block, dict) else None
        )
        if btype != "web_search_tool_result":
            continue
        inner = getattr(block, "content", None) or (
            block.get("content") if isinstance(block, dict) else None
        )
        if not inner:
            continue
        for item in inner:
            url = getattr(item, "url", None) or (
                item.get("url") if isinstance(item, dict) else None
            )
            if url:
                urls.append(url)
    return urls


def _brief_args(args: dict[str, Any]) -> str:
    """Render tool args compactly for a status line."""
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        s = repr(v)
        if len(s) > 40:
            s = s[:37] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)


__all__ = [
    "DEFAULT_MODEL",
    "FiscalAssistant",
    "MAX_TOOL_ITERATIONS",
    "OPUS_MODEL",
]
