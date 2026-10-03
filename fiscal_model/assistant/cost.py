"""
Token / dollar accounting and cache-hit telemetry.

Anthropic's ``Message.usage`` returns:

* ``input_tokens``
* ``output_tokens``
* ``cache_creation_input_tokens``  — wrote to cache this turn (full price)
* ``cache_read_input_tokens``      — read from cache this turn (10% price)

This module converts those into dollars using a small price table and
exposes a running tally across a multi-turn conversation.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Approximate list-price per million tokens (USD), as of 2026.
# Update when Anthropic publishes new pricing or new models. Cache writes
# are billed at 1.25x base input; cache reads at 0.1x base input.
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    # model_id: (input_per_million, output_per_million)
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
}

# Anthropic's published price for the server-side web search tool: $10 per
# 1,000 searches, billed per request on top of the tokens the results occupy.
WEB_SEARCH_USD_PER_1000 = 10.0

_warned_models: set[str] = set()
_warned_lock = threading.Lock()


def _prices_for(model: str) -> tuple[float, float]:
    """Per-million-token (input, output) price for ``model``.

    An id this table does not know is **not** priced as Sonnet: guessing the
    cheapest plausible tier lets the daily cost cap under-count exactly when a
    newer, dearer model is configured. It is priced at the most expensive tier
    in the table instead (over-counting spends the cap early; under-counting
    spends money the cap cannot see), and a warning names the id, once.
    """
    if model in _MODEL_PRICES:
        return _MODEL_PRICES[model]
    # A dated snapshot of a model we do know (``claude-sonnet-4-6-20260301``)
    # prices as that model.
    for known, price in _MODEL_PRICES.items():
        if model.startswith(known + "-"):
            return price
    fallback = max(_MODEL_PRICES.values(), key=lambda p: (p[1], p[0]))
    with _warned_lock:
        first = model not in _warned_models
        _warned_models.add(model)
    if first:
        logger.warning(
            "No price registered for model %r; pricing at the most expensive "
            "known tier (%.2f in / %.2f out per million tokens) so the cost cap "
            "cannot under-count. Add it to cost._MODEL_PRICES.",
            model,
            *fallback,
        )
    return fallback


def _web_search_requests(usage: Any) -> int:
    """``usage.server_tool_use.web_search_requests`` (object or dict), else 0."""
    server = getattr(usage, "server_tool_use", None)
    if server is None and isinstance(usage, dict):
        server = usage.get("server_tool_use")
    if server is None:
        return 0
    n = getattr(server, "web_search_requests", None)
    if n is None and isinstance(server, dict):
        n = server.get("web_search_requests")
    # Real counts only: a test double's auto-attribute must not bill a search.
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return 0
    return max(int(n), 0)


@dataclass
class TurnUsage:
    """Per-turn token + cost numbers."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    web_search_requests: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cost_usd": round(self.cost_usd, 5),
            "web_search_requests": self.web_search_requests,
        }


@dataclass
class ConversationCost:
    """Running tally across multiple turns in a single session."""

    turns: list[TurnUsage] = field(default_factory=list)

    def record(self, usage: Any, model: str) -> TurnUsage:
        """Convert an Anthropic ``usage`` payload to dollars and append."""
        if usage is None:
            t = TurnUsage()
            self.turns.append(t)
            return t

        # ``usage`` may be a pydantic model or a plain dict depending on SDK
        # version.
        def _get(key: str) -> int:
            v = getattr(usage, key, None)
            if v is None and isinstance(usage, dict):
                v = usage.get(key)
            try:
                return int(v) if v is not None else 0
            except (TypeError, ValueError):
                return 0

        in_tok = _get("input_tokens")
        out_tok = _get("output_tokens")
        cache_w = _get("cache_creation_input_tokens")
        cache_r = _get("cache_read_input_tokens")

        searches = _web_search_requests(usage)

        in_price, out_price = _prices_for(model)
        cost = (
            in_tok * in_price
            + out_tok * out_price
            + cache_w * (in_price * 1.25)
            + cache_r * (in_price * 0.10)
        ) / 1_000_000.0 + searches * WEB_SEARCH_USD_PER_1000 / 1000.0

        turn = TurnUsage(
            input_tokens=in_tok,
            output_tokens=out_tok,
            cache_creation_tokens=cache_w,
            cache_read_tokens=cache_r,
            cost_usd=cost,
            web_search_requests=searches,
        )
        self.turns.append(turn)
        return turn

    @property
    def total_cost_usd(self) -> float:
        return sum(t.cost_usd for t in self.turns)

    @property
    def total_tokens(self) -> int:
        return sum(
            t.input_tokens + t.output_tokens + t.cache_creation_tokens + t.cache_read_tokens
            for t in self.turns
        )

    def summary(self) -> str:
        if not self.turns:
            return "_No usage recorded._"
        cache_read = sum(t.cache_read_tokens for t in self.turns)
        cache_hit_ratio = (
            cache_read / sum(t.input_tokens + t.cache_read_tokens + t.cache_creation_tokens for t in self.turns)
            if self.turns
            else 0.0
        )
        return (
            f"{len(self.turns)} turn(s) · "
            f"${self.total_cost_usd:.4f} · "
            f"{self.total_tokens:,} tokens · "
            f"cache-hit {cache_hit_ratio:.0%}"
        )


__all__ = ["ConversationCost", "TurnUsage"]
