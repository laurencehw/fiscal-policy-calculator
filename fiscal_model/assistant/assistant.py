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
* ``assistant.last_error``      — ``None``, or the message of the upstream
  failure that ended the turn (see :class:`AssistantUpstreamError`)

Concurrency: those ``last_*`` attributes are per-turn state, so one
``FiscalAssistant`` serves one turn at a time. A server handling concurrent
requests must call :meth:`FiscalAssistant.spawn` per request.

The agentic loop is capped at :attr:`MAX_TOOL_ITERATIONS` to prevent infinite
loops in pathological cases.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
import time
from collections.abc import Callable, Iterator
from typing import Any

from .citations import annotate_unsupported
from .cost import ConversationCost, TurnUsage
from .rate_limit import (
    EVENT_ROLE_FOLLOWUPS,
    EVENT_ROLE_PREWARM,
    RateLimiter,
)
from .system_prompt import build_system_prompt, stable_prompt_prefix
from .tools import TOOL_SCHEMAS, AssistantTools, web_search_tool_definition

logger = logging.getLogger(__name__)


DEFAULT_MODEL = "claude-sonnet-4-6"
#: The cheap model the follow-up chips are generated with.
FOLLOWUP_MODEL = "claude-haiku-4-5-20251001"
OPUS_MODEL = "claude-opus-4-7"
MAX_TOOL_ITERATIONS = 4
# Tighter than the SDK default — most public-finance answers are 200-400
# output tokens, and the cap prevents accidental long-form rambling. 800
# proved too tight in practice: answers with a small comparison table were
# cut off mid-row; 1200 still cut off distributional answers that carry a
# decile table *and* a Sources block. 1600 finishes those while keeping
# latency and per-turn cost bounded (the daily cost cap, not this number, is
# the real budget control: at Sonnet output pricing 1600 tokens is ~$0.02).
# Override with ASSISTANT_MAX_TOKENS for local experiments.
DEFAULT_MAX_TOKENS = 1600
# Hard ceiling on the override so a stray env var cannot blow the daily cap.
MAX_MAX_TOKENS = 4000


class AssistantUpstreamError(RuntimeError):
    """The Anthropic API failed mid-turn.

    Raised from :meth:`FiscalAssistant.stream_response` instead of splicing an
    ``*Error from Anthropic API: ...*`` string into the answer, which the HTTP
    layer then returned as a normal 200 and the rate limiter recorded as a
    successful, error-free turn. ``api.py`` maps it to HTTP 502.

    Attributes
    ----------
    status_code:
        The upstream HTTP status when the SDK exposed one, else ``None``.
    partial_text:
        Text produced before the failure (may be empty).
    usage:
        :class:`TurnUsage` for the calls that *did* complete earlier in the
        same turn (paid for, so still to be recorded), or ``None``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        partial_text: str = "",
        usage: TurnUsage | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.partial_text = partial_text
        self.usage = usage


#: Signature of the optional per-turn callback: it receives one dict with
#: ``usage`` (dict), ``tools_used``, ``stripped_markers``, ``elapsed_s``,
#: ``answer_chars``, ``error`` (``str | None``) and ``disconnected`` (``bool``).
TurnEndCallback = Callable[[dict[str, Any]], None]

_client_init_lock = threading.Lock()


def resolve_max_tokens() -> int:
    """Output-token budget for one call, honouring ``ASSISTANT_MAX_TOKENS``."""
    raw = os.environ.get("ASSISTANT_MAX_TOKENS", "").strip()
    if not raw:
        return DEFAULT_MAX_TOKENS
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Ignoring non-integer ASSISTANT_MAX_TOKENS=%r", raw)
        return DEFAULT_MAX_TOKENS
    return max(256, min(value, MAX_MAX_TOKENS))


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
        on_turn_end: TurnEndCallback | None = None,
    ) -> None:
        self._client = anthropic_client
        self._on_turn_end = on_turn_end
        self._model = model
        self._enable_web_search = enable_web_search

        searcher = None
        if knowledge_dir is not None:
            try:
                from .knowledge_search import KnowledgeSearcher

                searcher = KnowledgeSearcher(knowledge_dir)
            except Exception:
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
        # ``stop_reason`` of the final API call; ``last_truncated`` is the
        # single flag the UI needs to offer a "continue" affordance instead
        # of leaving an answer that stops mid-table.
        self.last_stop_reason: str | None = None
        self.last_truncated: bool = False
        # Back-compat for callers that used to find upstream failures spliced
        # into the answer text: they can now test this instead.
        self.last_error: str | None = None
        self._turn_text: str = ""
        self._cache_prewarmed: bool = False

    # ---- per-request instances -------------------------------------------

    def spawn(self, *, enable_web_search: bool | None = None) -> FiscalAssistant:
        """Return a cheap per-request copy that shares everything immutable.

        A ``FiscalAssistant`` carries per-turn state: ``last_usage``,
        ``last_full_text``, ``last_provenance``, the tools' provenance trail
        and scoring context, and the ``_enable_web_search`` toggle. Two
        requests on one instance overwrite each other's (one request's usage
        was billed to another's session and one user's scoring context leaked
        into another's prompt). A server must therefore call ``spawn()`` once
        per request and use the copy for that request only.

        The copy shares the Anthropic client (created here if need be, once),
        the scorer, baseline, presets and the BM25 knowledge index; it gets a
        fresh :class:`AssistantTools` (empty provenance, no scoring context),
        a fresh :class:`ConversationCost` and cleared ``last_*`` fields.
        ``enable_web_search`` overrides the toggle for the copy only.
        """
        if self._client is None and self.is_available():
            with _client_init_lock:
                _ = self.client  # initialise once, share with every copy
        clone = copy.copy(self)
        clone._tools = self._tools.spawn()
        clone.cost = ConversationCost()
        clone._reset_turn_state()
        if enable_web_search is not None:
            clone._enable_web_search = bool(enable_web_search)
        return clone

    def _reset_turn_state(self) -> None:
        self.last_provenance = []
        self.last_usage = None
        self.last_full_text = ""
        self.last_message = None
        self.last_stripped_markers = []
        self.last_web_citations = []
        self.last_stop_reason = None
        self.last_truncated = False
        self.last_error = None
        self._turn_text = ""

    # ---- lazy client -----------------------------------------------------

    @property
    def client(self):
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

    # ---- cache warming --------------------------------------------------

    # ---- auxiliary paid calls and the cap ledger ------------------------

    @staticmethod
    def _aux_ledger(limiter: RateLimiter | None) -> RateLimiter:
        """The ledger the daily cap reads; the default one when none is given.

        There is deliberately no way to make an auxiliary paid call *without*
        a ledger: omitting ``limiter`` uses the same default sqlite db the Ask
        page and the API construct, so the spend still counts.
        """
        return limiter if limiter is not None else RateLimiter()

    @staticmethod
    def _aux_budget_allows(ledger: RateLimiter) -> bool:
        """Kill switch + daily cap, checked before spending. Fails closed."""
        try:
            return bool(ledger.check_budget().allowed)
        except Exception:
            logger.warning("Budget check failed; skipping auxiliary call", exc_info=True)
            return False

    @staticmethod
    def _record_aux_usage(
        ledger: RateLimiter,
        *,
        role: str,
        model: str,
        usage: Any,
        session_id: str,
        elapsed_s: float,
    ) -> None:
        """Book one auxiliary call's cost in ``assistant_events``.

        Priced with the same table as a turn but kept out of ``self.cost``
        (the per-session meter counts answers, and a pre-warm belongs to no
        session).
        """
        try:
            turn = ConversationCost().record(usage, model)
            ledger.record_turn(
                session_id=session_id,
                role=role,
                model=model,
                usage_dict=turn.to_dict(),
                elapsed_s=elapsed_s,
            )
        except Exception:
            logger.warning("Failed to record %s usage", role, exc_info=True)

    def prewarm_cache(
        self,
        *,
        limiter: RateLimiter | None = None,
        session_id: str = "prewarm",
    ) -> bool:
        """Issue a tiny request to seed Anthropic's prompt cache.

        The cached system block is large (~3 KB); paying its creation cost
        once at app boot means a real user's first turn skips that ~1-2s
        cache-write delay and pays only the cheap cache-read cost.

        Idempotent across the cache TTL (≈5 min). Failures are swallowed
        — pre-warming is opportunistic, not load-bearing.
        Returns True on success.

        It is a paid call (it *writes* the cache, at 1.25x input price), so it
        is skipped when the kill switch is on or today's cap is spent, and
        its cost is booked in ``limiter``'s ledger as an
        :data:`~.rate_limit.EVENT_ROLE_PREWARM` row.
        """
        if not self.is_available() or self._cache_prewarmed:
            return False
        ledger = self._aux_ledger(limiter)
        if not self._aux_budget_allows(ledger):
            return False
        started = time.time()
        try:
            stable = stable_prompt_prefix()
            client = self.client
            msg = client.messages.create(
                model=self._model,
                max_tokens=8,  # smallest plausible; we discard the output
                system=[
                    {
                        "type": "text",
                        "text": stable,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": "OK"}],
            )
            self._cache_prewarmed = True
        except Exception:
            logger.info("Cache pre-warm failed (non-fatal)", exc_info=True)
            return False
        self._record_aux_usage(
            ledger,
            role=EVENT_ROLE_PREWARM,
            model=self._model,
            usage=getattr(msg, "usage", None),
            session_id=session_id,
            elapsed_s=time.time() - started,
        )
        return True

    # ---- follow-up generation -------------------------------------------

    def suggest_followups(
        self,
        last_question: str,
        last_answer: str,
        max_suggestions: int = 3,
        *,
        limiter: RateLimiter | None = None,
        session_id: str = "unknown",
    ) -> list[str]:
        """Ask the model for 2–3 short follow-up questions a reader might want.

        Issues a cheap separate API call with no tools and small max_tokens
        so it doesn't double the cost of the main turn. Returns an empty
        list on any failure — follow-ups are a nicety, not load-bearing.

        Still a paid call: it is skipped (empty list) when the kill switch is
        on or today's cap is spent, and its cost is booked in ``limiter``'s
        ledger as an :data:`~.rate_limit.EVENT_ROLE_FOLLOWUPS` row under
        ``session_id``.
        """
        if not self.is_available():
            return []
        ledger = self._aux_ledger(limiter)
        if not self._aux_budget_allows(ledger):
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
        started = time.time()
        try:
            msg = self.client.messages.create(
                model=FOLLOWUP_MODEL,  # cheap; Haiku is fine
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            logger.warning("Followup suggestion call failed", exc_info=True)
            return []
        self._record_aux_usage(
            ledger,
            role=EVENT_ROLE_FOLLOWUPS,
            model=FOLLOWUP_MODEL,
            usage=getattr(msg, "usage", None),
            session_id=session_id,
            elapsed_s=time.time() - started,
        )

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
        *,
        on_turn_end: TurnEndCallback | None = None,
    ) -> Iterator[str]:
        """Yield chunks of the assistant's response as it streams.

        Raises
        ------
        AssistantUpstreamError
            If the Anthropic API fails. Nothing is appended to the answer;
            ``last_error`` is set and the turn-end callback still fires with
            ``error=...`` and the usage of any calls that did complete.

        The paid model call finishes before its text is yielded, so usage is
        recorded the moment each call returns and the turn-end callback runs
        in a ``finally`` — a client that disconnects mid-stream (the
        generator is closed with ``GeneratorExit``) is still billed against
        the daily cap. ``on_turn_end`` (or the constructor's) receives one
        dict: ``usage``, ``tools_used``, ``stripped_markers``, ``elapsed_s``,
        ``answer_chars``, ``error`` and ``disconnected``; callers should record
        the turn from it rather than from code after the ``for`` loop, which a
        disconnect never reaches. The callback fires exactly once per turn.

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
        self._tools.reset_provenance()
        self._tools.set_scoring_context(scoring_context)
        self._reset_turn_state()
        callback = on_turn_end or self._on_turn_end
        started = time.time()
        error: str | None = None
        disconnected = False
        try:
            yield from self._stream_turn(user_message, history, scoring_context)
        except GeneratorExit:
            disconnected = True
            raise
        except BaseException as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.last_error = error
            raise
        finally:
            self._finish_turn(callback, started, error, disconnected)

    def _finish_turn(
        self,
        callback: TurnEndCallback | None,
        started: float,
        error: str | None,
        disconnected: bool,
    ) -> None:
        """Settle per-turn state and fire the turn-end callback, once."""
        if not self.last_provenance:
            self.last_provenance = list(self._tools.provenance)
        answer = self.last_full_text or self._turn_text
        if callback is None:
            return
        info = {
            "usage": self.last_usage.to_dict() if self.last_usage else {},
            "tools_used": [p.get("tool", "") for p in self.last_provenance],
            "stripped_markers": len(self.last_stripped_markers or []),
            "elapsed_s": time.time() - started,
            "answer_chars": len(answer),
            "error": error,
            "disconnected": disconnected,
        }
        try:
            callback(info)
        except Exception:
            logger.exception("turn-end callback failed")

    def _stream_turn(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        scoring_context: dict[str, Any] | None,
    ) -> Iterator[str]:
        """The tool-use loop behind :meth:`stream_response` (state is reset there)."""

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
        messages: list[dict[str, Any]] = [
            *history,
            {"role": "user", "content": user_message},
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
            # The call is paid for as soon as it returns: book it *before*
            # yielding, so a client that disconnects while we yield cannot
            # leave a completed, billed call off the ledger.
            self._record_usage(stream_result.get("usage"))
            final_message = stream_result["final_message"]
            iter_text = ""
            for chunk in stream_result["text_chunks"]:
                iter_text += chunk
                self._turn_text += chunk
                yield chunk
            accumulated_text += iter_text

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
            self._record_usage(forced.get("usage"))
            final_message = forced["final_message"]
            for chunk in forced["text_chunks"]:
                accumulated_text += chunk
                self._turn_text += chunk
                yield chunk

        # ------------------------------------------------------------------
        # If the final call ran out of output budget, say so rather than
        # ending mid-sentence (or mid-table) as if the answer were complete.
        # ------------------------------------------------------------------
        self.last_stop_reason = getattr(final_message, "stop_reason", None)
        if self.last_stop_reason == "max_tokens":
            self.last_truncated = True
            truncation_note = (
                "\n\n> ✂️ *This answer hit its length budget and may end "
                "abruptly. Use **Continue the answer** below, or ask a "
                "follow-up.*"
            )
            accumulated_text += truncation_note
            self._turn_text += truncation_note
            yield truncation_note

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
                max_tokens=resolve_max_tokens(),
                system=system_blocks,
                messages=messages,
                tools=tools,
            ) as stream:
                for text in stream.text_stream:
                    text_chunks.append(text)
                final_message = stream.get_final_message()
                usage = getattr(final_message, "usage", None)
        except Exception as exc:
            logger.exception("Anthropic stream failed")
            raise AssistantUpstreamError(
                f"Anthropic API error: {exc}",
                status_code=getattr(exc, "status_code", None),
                partial_text="".join(text_chunks),
                usage=self.last_usage,
            ) from exc

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
                web_search_requests=(
                    self.last_usage.web_search_requests + turn.web_search_requests
                ),
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
            except Exception:
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
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL",
    "MAX_TOOL_ITERATIONS",
    "OPUS_MODEL",
    "AssistantUpstreamError",
    "FiscalAssistant",
    "TurnEndCallback",
    "resolve_max_tokens",
]
