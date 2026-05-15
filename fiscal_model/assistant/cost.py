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

from dataclasses import dataclass, field
from typing import Any


# Approximate list-price per million tokens (USD), as of 2026.
# Update when Anthropic publishes new pricing or new models. Cache writes
# are billed at 1.25x base input; cache reads at 0.1x base input.
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    # model_id: (input_per_million, output_per_million)
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
}


def _prices_for(model: str) -> tuple[float, float]:
    if model in _MODEL_PRICES:
        return _MODEL_PRICES[model]
    # Sensible default if a new model id rolls out.
    return _MODEL_PRICES["claude-sonnet-4-6"]


@dataclass
class TurnUsage:
    """Per-turn token + cost numbers."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cost_usd": round(self.cost_usd, 5),
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

        in_price, out_price = _prices_for(model)
        cost = (
            in_tok * in_price
            + out_tok * out_price
            + cache_w * (in_price * 1.25)
            + cache_r * (in_price * 0.10)
        ) / 1_000_000.0

        turn = TurnUsage(
            input_tokens=in_tok,
            output_tokens=out_tok,
            cache_creation_tokens=cache_w,
            cache_read_tokens=cache_r,
            cost_usd=cost,
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
