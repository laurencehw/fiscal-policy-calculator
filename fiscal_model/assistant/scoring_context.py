"""
The scoring context a caller may attach to an Ask turn, as a typed, bounded
shape.

The context goes into the system prompt, so an unbounded ``dict[str, Any]``
was a prompt-injection and token-amplification channel for anyone who could
call the engine directly. Only the fields the Streamlit Ask tab builds
(``fiscal_model/ui/tabs/ask_assistant.py::_scoring_context``) are accepted;
strings are length-capped and numbers bounded. The website sends no scoring
context at all.

:func:`coerce_scoring_context` is applied inside the assistant as well as at
the HTTP boundary, so every path into the prompt goes through the same shape.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)

#: Bound on any dollar figure (billions). The largest preset is a few
#: trillion over ten years; a million billion is far outside any real score.
_MAX_BILLIONS = 1_000_000.0
#: Bound on a percentage error.
_MAX_PCT = 100_000.0

_SHORT = 64
_NAME = 200
_REASON = 500


class ScoringCredibility(BaseModel):
    """The credibility summary of the scored policy (all fields optional)."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    evidence_type: str | None = Field(None, max_length=_SHORT)
    policy_class: str | None = Field(None, max_length=_NAME)
    n_out_of_sample_rows: int | None = Field(None, ge=0, le=10_000)
    mean_abs_pct_error: float | None = Field(None, ge=0, le=_MAX_PCT)
    max_abs_pct_error: float | None = Field(None, ge=0, le=_MAX_PCT)
    no_band_reason: str | None = Field(None, max_length=_REASON)


class ScoringContext(BaseModel):
    """A policy the caller has already scored, for grounding the answer."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    policy_name: str | None = Field(None, max_length=_NAME)
    policy_type: str | None = Field(None, max_length=_SHORT)
    ten_year_deficit_impact_billions: float | None = Field(
        None, ge=-_MAX_BILLIONS, le=_MAX_BILLIONS
    )
    static_total_billions: float | None = Field(None, ge=-_MAX_BILLIONS, le=_MAX_BILLIONS)
    is_dynamic: bool | None = None
    dynamic_model: str | None = Field(None, max_length=_SHORT)
    revenue_feedback_10yr_billions: float | None = Field(
        None, ge=-_MAX_BILLIONS, le=_MAX_BILLIONS
    )
    debt_service_10yr_billions: float | None = Field(
        None, ge=-_MAX_BILLIONS, le=_MAX_BILLIONS
    )
    dynamic_total_10yr_billions: float | None = Field(
        None, ge=-_MAX_BILLIONS, le=_MAX_BILLIONS
    )
    credibility: ScoringCredibility | None = None


def _nan_to_none(value: Any) -> Any:
    """A missing figure the app computes as NaN means "no figure", not junk."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _nan_to_none(v) for k, v in value.items()}
    return value


def coerce_scoring_context(raw: Any) -> dict[str, Any] | None:
    """The context as a plain dict of known, bounded fields, or ``None``.

    Accepts a :class:`ScoringContext` or a mapping. Anything that does not
    fit the shape is dropped (and logged) rather than passed to the model.
    """
    if raw is None:
        return None
    if isinstance(raw, ScoringContext):
        model = raw
    else:
        try:
            model = ScoringContext.model_validate(_nan_to_none(raw))
        except ValidationError as exc:
            logger.warning(
                "Dropping a scoring context that does not fit the schema (%d errors)",
                exc.error_count(),
            )
            return None
    data = model.model_dump(exclude_none=True)
    return data or None


__all__ = ["ScoringContext", "ScoringCredibility", "coerce_scoring_context"]
