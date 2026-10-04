"""The cost cap is only as honest as its price table.

``cost._MODEL_PRICES`` had Haiku 4.5 at $0.80/$4.00 (it is $1/$5) and Opus 4.7
at $15/$75 (it is $5/$25), and it omitted Fable 5.1, so the "price an unknown
model at the dearest tier" fallback was not the dearest model at all.
"""

from __future__ import annotations

import pytest

from fiscal_model.assistant.cost import _MODEL_PRICES, _prices_for

# Anthropic first-party list prices per million tokens, (input, output).
PUBLISHED = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


@pytest.mark.parametrize(("model", "price"), sorted(PUBLISHED.items()))
def test_published_prices(model, price):
    assert _prices_for(model) == price


def test_a_dated_snapshot_prices_as_its_own_model_not_a_shorter_prefix():
    # ``claude-opus-5-5-…`` also starts with ``claude-opus-5-``; the two differ.
    assert _prices_for("claude-opus-5-5-20270101") == (4.0, 20.0)
    assert _prices_for("claude-opus-5-20270101") == (5.0, 25.0)


def test_an_unknown_model_is_priced_at_the_dearest_listed_tier():
    dearest = max(_MODEL_PRICES.values(), key=lambda p: (p[1], p[0]))
    assert dearest == (10.0, 50.0)
    assert _prices_for("claude-hypothetical-9") == dearest
