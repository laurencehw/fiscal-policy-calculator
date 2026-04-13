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
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

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
    except Exception:  # pragma: no cover — tests / CLI path
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
def get_cbo_baseline(start_year: int = 2025, use_real_data: bool = True) -> Any:
    """Cached CBO baseline projection keyed by (start_year, use_real_data)."""
    from fiscal_model.baseline import CBOBaseline

    logger.info(
        "Generating CBO baseline (cache miss): start_year=%d use_real_data=%s",
        start_year,
        use_real_data,
    )
    return CBOBaseline(start_year=start_year, use_real_data=use_real_data).generate()


@_cache_resource
def get_default_scorer(start_year: int = 2025, use_real_data: bool = True) -> Any:
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


__all__ = [
    "get_cbo_baseline",
    "get_default_scorer",
    "get_fred_data",
]
