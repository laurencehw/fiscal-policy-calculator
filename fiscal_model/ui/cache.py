"""
Streamlit-aware caching for expensive app bootstraps.

The scoring model loads a CBO baseline (JSON files, IRS SOI tables, FRED
data) on every instantiation. Without caching, every Streamlit rerun pays
that cost — slow, and noisy in logs because FRED is re-queried each time.

These helpers wrap the heavy objects in ``st.cache_resource`` so that
within a single server process the baseline, FRED client, and default
scorer are constructed at most once per unique config. If Streamlit is
unavailable (e.g. unit tests importing the UI module), we fall back to a
plain ``functools.lru_cache`` so semantics stay identical in both
environments.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

from fiscal_model.baseline import APP_DEFAULT_START_YEAR

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _streamlit_cache_resource() -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Return Streamlit's ``cache_resource`` decorator when available.

    Falls back to ``functools.lru_cache(maxsize=None)`` outside of Streamlit.
    The fallback preserves per-argument memoization so tests behave the same
    as a live app.
    """
    try:
        import streamlit as st  # type: ignore
    except ImportError:  # pragma: no cover — tests / CLI path
        return lru_cache(maxsize=None)  # type: ignore[return-value]

    decorator = getattr(st, "cache_resource", None)
    if decorator is None:  # pragma: no cover — very old Streamlit
        return lru_cache(maxsize=None)  # type: ignore[return-value]

    def wrap(func: Callable[..., T]) -> Callable[..., T]:
        # show_spinner=False keeps the sidebar quiet on warm starts
        return decorator(show_spinner=False)(func)

    return wrap


_cache_resource = _streamlit_cache_resource()


def get_fred_data() -> Any:
    """Return a :class:`FREDData` instance for the current request.

    Deliberately NOT memoized: the cost of constructing ``FREDData`` is
    small (it just inspects env and cache files), and the real work —
    FRED API calls — is already file-cached inside ``FREDData``. Skipping
    process-level caching here keeps tests that monkeypatch ``FREDData``
    honest, and lets operators pick up env changes (e.g. a freshly
    configured ``FRED_API_KEY``) without a server restart.
    """
    from fiscal_model.data.fred_data import FREDData

    logger.debug("Constructing FREDData")
    return FREDData()


@_cache_resource
def get_cbo_baseline(
    start_year: int = APP_DEFAULT_START_YEAR, use_real_data: bool = True
) -> Any:
    """Cached CBO baseline projection keyed by (start_year, use_real_data)."""
    from fiscal_model.baseline import CBOBaseline

    logger.info(
        "Generating CBO baseline (cache miss): start_year=%d use_real_data=%s",
        start_year,
        use_real_data,
    )
    return CBOBaseline(start_year=start_year, use_real_data=use_real_data).generate()


@_cache_resource
def get_default_scorer(
    start_year: int = APP_DEFAULT_START_YEAR, use_real_data: bool = True
) -> Any:
    """Cached :class:`FiscalPolicyScorer` sharing the cached baseline.

    Avoids re-running baseline construction on every Streamlit rerun. The
    scorer itself is cheap; reuse is almost entirely about the baseline.
    """
    from fiscal_model.scoring import FiscalPolicyScorer

    baseline = get_cbo_baseline(start_year=start_year, use_real_data=use_real_data)
    logger.debug(
        "Constructing scorer from cached baseline: start_year=%d",
        start_year,
    )
    return FiscalPolicyScorer(
        baseline=baseline,
        start_year=start_year,
        use_real_data=use_real_data,
    )


# ---------------------------------------------------------------------------
# Health snapshot
# ---------------------------------------------------------------------------
#
# ``fiscal_model.health.check_health`` regenerates the CBO baseline, stats the
# IRS SOI tables and probes FRED. That used to be paid once per rerun, in the
# Calculator sidebar. The redesign promotes the data-status indicator into the
# shared chrome, so it is now on *every* page — and a Streamlit popover body
# executes on every rerun even while closed. A short TTL keeps the pill honest
# without paying the full probe on each navigation.
#
# Deliberately a hand-rolled TTL rather than ``st.cache_data``: the existing
# ``render_data_status`` tests monkeypatch ``fiscal_model.health.check_health``,
# and ``clear_health_snapshot()`` gives them a cheap escape hatch.

_HEALTH_TTL_SECONDS = 300.0
_health_snapshot: dict[str, Any] = {}


def get_health_snapshot(ttl_seconds: float = _HEALTH_TTL_SECONDS) -> dict[str, Any]:
    """Return a TTL-cached ``check_health()`` payload."""
    from fiscal_model.health import check_health

    now = time.monotonic()
    cached = _health_snapshot.get("value")
    if cached is not None and (now - float(_health_snapshot.get("at", 0.0))) < ttl_seconds:
        return cached

    value = check_health()
    _health_snapshot["value"] = value
    _health_snapshot["at"] = now
    return value


def clear_health_snapshot() -> None:
    """Drop the cached health payload (tests, or after a data refresh)."""
    _health_snapshot.clear()


__all__ = [
    "clear_health_snapshot",
    "get_cbo_baseline",
    "get_default_scorer",
    "get_fred_data",
    "get_health_snapshot",
]
