"""
Read-only queries over the assistant_events sqlite table.

Powers the admin dashboard in ``fiscal_model/ui/tabs/assistant_admin.py``.
All functions accept a :class:`RateLimiter` (which owns the db path) and
return plain dicts / pandas frames suitable for Streamlit charts.

The dashboard itself is **token-gated** — only visible when the URL has
``?admin=<token>`` matching ``ASSISTANT_ADMIN_TOKEN`` in the env/secrets.
This module assumes the caller has already cleared that gate.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pandas as pd

from .rate_limit import RateLimiter

logger = logging.getLogger(__name__)


ADMIN_TOKEN_ENV = "ASSISTANT_ADMIN_TOKEN"


def admin_token_configured() -> bool:
    """Whether an admin token is set in env/secrets."""
    return bool(os.environ.get(ADMIN_TOKEN_ENV, "").strip())


def is_admin_request(query_params: Any) -> bool:
    """Return True if the URL's ``?admin=<token>`` matches the env token.

    Accepts both Streamlit's new ``st.query_params`` (dict-like) and the
    legacy ``st.experimental_get_query_params`` shape (values as lists).
    """
    if not admin_token_configured():
        return False
    expected = os.environ[ADMIN_TOKEN_ENV].strip()
    try:
        raw = query_params.get("admin") if hasattr(query_params, "get") else None
    except Exception:  # noqa: BLE001
        return False
    if raw is None:
        return False
    candidate = raw[0] if isinstance(raw, list) and raw else raw
    return str(candidate).strip() == expected


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@dataclass
class AdminSnapshot:
    """Top-line numbers shown at the head of the dashboard."""

    total_turns: int
    total_cost_usd: float
    today_turns: int
    today_cost_usd: float
    daily_cap_usd: float
    avg_cost_per_turn_usd: float
    cache_hit_ratio: float
    error_rate_pct: float
    avg_elapsed_s: float
    n_unique_sessions_30d: int


def _connect_readonly(limiter: RateLimiter) -> sqlite3.Connection:
    if limiter.db_path == ":memory:":
        # In-memory limiter shares its connection.
        return limiter._connect()  # noqa: SLF001
    conn = sqlite3.connect(limiter.db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn


def snapshot(limiter: RateLimiter) -> AdminSnapshot:
    """Compute headline KPIs in a single sqlite round trip."""
    today_utc = datetime.now(timezone.utc).date()
    today_iso = today_utc.isoformat()
    thirty_days_ago = (today_utc - timedelta(days=30)).isoformat()
    conn = _connect_readonly(limiter)
    try:
        all_rows = conn.execute(
            """
            SELECT
                COUNT(*) AS n,
                COALESCE(SUM(cost_usd), 0) AS total_cost,
                COALESCE(AVG(cost_usd), 0) AS avg_cost,
                COALESCE(SUM(cache_read_tokens), 0) AS cache_r,
                COALESCE(SUM(input_tokens + cache_read_tokens + cache_creation_tokens), 0) AS total_in,
                COALESCE(SUM(CASE WHEN error IS NOT NULL AND error != '' THEN 1 ELSE 0 END), 0) AS errors,
                COALESCE(AVG(elapsed_s), 0) AS avg_elapsed
            FROM assistant_events
            """
        ).fetchone()

        today_row = conn.execute(
            """
            SELECT COUNT(*) AS n, COALESCE(SUM(cost_usd), 0) AS cost
            FROM assistant_events
            WHERE day_utc = ?
            """,
            (today_iso,),
        ).fetchone()

        sessions_row = conn.execute(
            """
            SELECT COUNT(DISTINCT session_id) AS n
            FROM assistant_events
            WHERE day_utc >= ?
            """,
            (thirty_days_ago,),
        ).fetchone()
    finally:
        if limiter.db_path != ":memory:":
            conn.close()

    total = int(all_rows["n"] or 0)
    cache_r = int(all_rows["cache_r"] or 0)
    total_in = int(all_rows["total_in"] or 0)
    cache_hit_ratio = (cache_r / total_in) if total_in > 0 else 0.0
    error_rate_pct = (100.0 * (all_rows["errors"] or 0) / total) if total > 0 else 0.0

    return AdminSnapshot(
        total_turns=total,
        total_cost_usd=float(all_rows["total_cost"] or 0.0),
        today_turns=int(today_row["n"] or 0),
        today_cost_usd=float(today_row["cost"] or 0.0),
        daily_cap_usd=float(limiter.config.daily_cost_cap_usd),
        avg_cost_per_turn_usd=float(all_rows["avg_cost"] or 0.0),
        cache_hit_ratio=float(cache_hit_ratio),
        error_rate_pct=float(error_rate_pct),
        avg_elapsed_s=float(all_rows["avg_elapsed"] or 0.0),
        n_unique_sessions_30d=int(sessions_row["n"] or 0),
    )


def daily_spend_series(limiter: RateLimiter, days: int = 30) -> pd.DataFrame:
    """Daily cost over the last ``days`` days (UTC). Fills missing days with 0."""
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    conn = _connect_readonly(limiter)
    try:
        rows = conn.execute(
            """
            SELECT day_utc, SUM(cost_usd) AS cost, COUNT(*) AS turns
            FROM assistant_events
            WHERE day_utc >= ?
            GROUP BY day_utc
            ORDER BY day_utc
            """,
            (start.isoformat(),),
        ).fetchall()
    finally:
        if limiter.db_path != ":memory:":
            conn.close()
    actual = {r["day_utc"]: r for r in rows}
    out: list[dict[str, Any]] = []
    for offset in range(days):
        d = (start + timedelta(days=offset)).isoformat()
        r = actual.get(d)
        out.append(
            {
                "day": d,
                "cost_usd": float(r["cost"]) if r else 0.0,
                "turns": int(r["turns"]) if r else 0,
            }
        )
    return pd.DataFrame(out)


def tool_usage_counts(limiter: RateLimiter, days: int = 30) -> pd.DataFrame:
    """How often each tool has been called in the last ``days`` days."""
    cutoff = (
        datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    ).isoformat()
    conn = _connect_readonly(limiter)
    try:
        rows = conn.execute(
            "SELECT tools FROM assistant_events WHERE day_utc >= ? AND tools IS NOT NULL",
            (cutoff,),
        ).fetchall()
    finally:
        if limiter.db_path != ":memory:":
            conn.close()
    counts: dict[str, int] = {}
    for r in rows:
        for tool in (r["tools"] or "").split(","):
            tool = tool.strip()
            if tool:
                counts[tool] = counts.get(tool, 0) + 1
    df = pd.DataFrame(
        sorted(counts.items(), key=lambda t: t[1], reverse=True),
        columns=["tool", "calls"],
    )
    return df


def recent_turns(limiter: RateLimiter, limit: int = 20) -> pd.DataFrame:
    """Most recent N turns with cost, tools, error flag, elapsed."""
    conn = _connect_readonly(limiter)
    try:
        rows = conn.execute(
            """
            SELECT ts_utc, session_id, model, cost_usd, elapsed_s, tools,
                   stripped_markers, error, question_chars, answer_chars
            FROM assistant_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        if limiter.db_path != ":memory:":
            conn.close()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        [
            {
                "ts_utc": r["ts_utc"],
                "session": (r["session_id"] or "")[:8],
                "model": r["model"],
                "cost_usd": round(float(r["cost_usd"] or 0.0), 5),
                "elapsed_s": round(float(r["elapsed_s"] or 0.0), 2),
                "tools": r["tools"] or "",
                "stripped": int(r["stripped_markers"] or 0),
                "q_chars": int(r["question_chars"] or 0),
                "a_chars": int(r["answer_chars"] or 0),
                "error": (r["error"] or "")[:80],
            }
            for r in rows
        ]
    )


def estimate_runway_days(snap: AdminSnapshot, window_days: int = 7) -> dict[str, Any]:
    """How long until the monthly burn would exhaust a hypothetical $X budget?

    Uses average daily spend over the last ``window_days`` to project forward.
    """
    return {
        "today_pct_of_cap": (
            round(100.0 * snap.today_cost_usd / snap.daily_cap_usd, 1)
            if snap.daily_cap_usd > 0
            else 0.0
        ),
        "projected_30d_burn": round(snap.today_cost_usd * 30, 2)
        if snap.today_turns > 0
        else 0.0,
    }


__all__ = [
    "ADMIN_TOKEN_ENV",
    "AdminSnapshot",
    "admin_token_configured",
    "daily_spend_series",
    "estimate_runway_days",
    "is_admin_request",
    "recent_turns",
    "snapshot",
    "tool_usage_counts",
]
