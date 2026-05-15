"""
Hard usage caps for the Ask assistant.

Protects the deployer's Anthropic credit card from runaway costs by
enforcing four limits on every turn:

1. **Daily spend cap** — total dollar cost across all users today.
   Backed by sqlite so it survives Streamlit reruns and per-user
   session ephemera. Default: $5.00/day.
2. **Per-session message cap** — max turns in one chat. Default: 20.
3. **Per-session cool-down** — minimum seconds between turns from the
   same session. Default: 3s.
4. **Kill switch** — env var ``ASSISTANT_DISABLED=1`` blocks every
   request immediately.

All four are configurable via env vars (see :data:`_ENV_NAMES`).

The same sqlite table doubles as the telemetry log for the assistant
(see ``AssistantEventLog`` / step #11 in the rollout plan). One write
per turn keeps it cheap.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


_ENV_NAMES = {
    "daily_cost_cap_usd": "ASSISTANT_DAILY_COST_CAP_USD",
    "session_message_cap": "ASSISTANT_SESSION_MESSAGE_CAP",
    "cooldown_seconds": "ASSISTANT_COOLDOWN_SECONDS",
    "disabled": "ASSISTANT_DISABLED",
    "db_path": "ASSISTANT_USAGE_DB",
}

_DEFAULT_DAILY_CAP_USD = 5.00
_DEFAULT_SESSION_MESSAGE_CAP = 20
_DEFAULT_COOLDOWN_SECONDS = 3.0


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assistant_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    day_utc TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    elapsed_s REAL DEFAULT 0,
    tools TEXT,
    stripped_markers INTEGER DEFAULT 0,
    error TEXT,
    question_chars INTEGER DEFAULT 0,
    answer_chars INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_assistant_events_day ON assistant_events(day_utc);
CREATE INDEX IF NOT EXISTS idx_assistant_events_session ON assistant_events(session_id);
"""


@dataclass(frozen=True)
class RateLimitConfig:
    daily_cost_cap_usd: float = _DEFAULT_DAILY_CAP_USD
    session_message_cap: int = _DEFAULT_SESSION_MESSAGE_CAP
    cooldown_seconds: float = _DEFAULT_COOLDOWN_SECONDS
    disabled: bool = False
    db_path: str = ""

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        def _float(name: str, default: float) -> float:
            try:
                return float(os.environ.get(_ENV_NAMES[name], default))
            except ValueError:
                return default

        def _int(name: str, default: int) -> int:
            try:
                return int(os.environ.get(_ENV_NAMES[name], default))
            except ValueError:
                return default

        return cls(
            daily_cost_cap_usd=_float("daily_cost_cap_usd", _DEFAULT_DAILY_CAP_USD),
            session_message_cap=_int("session_message_cap", _DEFAULT_SESSION_MESSAGE_CAP),
            cooldown_seconds=_float("cooldown_seconds", _DEFAULT_COOLDOWN_SECONDS),
            disabled=os.environ.get(_ENV_NAMES["disabled"], "").strip()
            in {"1", "true", "TRUE", "yes"},
            db_path=os.environ.get(_ENV_NAMES["db_path"], "").strip(),
        )


def _default_db_path() -> Path:
    """Best-effort writable location for the usage db."""
    explicit = os.environ.get(_ENV_NAMES["db_path"], "").strip()
    if explicit:
        return Path(explicit)
    # Prefer a path under the repo if writable (developer machines, CI).
    repo_data = (
        Path(__file__).resolve().parent.parent / "data_files" / "assistant_usage.db"
    )
    try:
        repo_data.parent.mkdir(parents=True, exist_ok=True)
        # Touch to verify writability.
        with open(repo_data, "a"):
            pass
        return repo_data
    except OSError:
        pass
    # Fall back to user home (works on Streamlit Cloud's writable home).
    home_dir = Path.home() / ".fiscal-policy-calculator"
    try:
        home_dir.mkdir(parents=True, exist_ok=True)
        return home_dir / "assistant_usage.db"
    except OSError:
        # Last resort: in-memory (survives the process only).
        return Path(":memory:")


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str = ""
    today_spend_usd: float = 0.0
    daily_cap_usd: float = 0.0
    session_messages: int = 0
    session_cap: int = 0

    @property
    def budget_remaining_usd(self) -> float:
        return max(0.0, self.daily_cap_usd - self.today_spend_usd)


class RateLimiter:
    """Sqlite-backed daily-cap + per-session limiter + event logger.

    Thread-safe enough for Streamlit (single-writer, frequent reads);
    the underlying connection is opened per call rather than cached so
    Streamlit reruns don't trip the "thread X is not in thread Y" check.
    """

    def __init__(self, config: RateLimitConfig | None = None, db_path: Path | None = None):
        self.config = config or RateLimitConfig.from_env()
        if db_path is not None:
            path: Path = Path(db_path)
        elif self.config.db_path:
            path = Path(self.config.db_path)
        else:
            path = _default_db_path()
        self.db_path = str(path)
        self._in_memory_conn: sqlite3.Connection | None = None
        self._init_schema()

    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self.db_path == ":memory:":
            if self._in_memory_conn is None:
                self._in_memory_conn = sqlite3.connect(":memory:")
                self._in_memory_conn.row_factory = sqlite3.Row
            return self._in_memory_conn
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        try:
            conn = self._connect()
            try:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
            finally:
                if self.db_path != ":memory:":
                    conn.close()
        except sqlite3.Error:
            logger.exception("Failed to init assistant usage schema")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(
        self,
        *,
        session_id: str,
        session_message_count: int,
        last_message_ts: float | None,
    ) -> RateLimitDecision:
        """Decide whether a new turn from ``session_id`` is permitted.

        Returns a :class:`RateLimitDecision`. If ``allowed`` is False,
        ``reason`` is a user-facing string explaining why.
        """
        today_spend = self.today_spend_usd()
        decision = RateLimitDecision(
            allowed=True,
            today_spend_usd=today_spend,
            daily_cap_usd=self.config.daily_cost_cap_usd,
            session_messages=session_message_count,
            session_cap=self.config.session_message_cap,
        )

        if self.config.disabled:
            decision.allowed = False
            decision.reason = (
                "The Ask assistant is temporarily disabled by the site "
                "operator. Please try again later."
            )
            return decision

        if today_spend >= self.config.daily_cost_cap_usd:
            decision.allowed = False
            decision.reason = (
                f"Today's free-tier budget is exhausted "
                f"(${today_spend:.2f} of ${self.config.daily_cost_cap_usd:.2f} "
                "used across all visitors). The cap resets at UTC midnight."
            )
            return decision

        if session_message_count >= self.config.session_message_cap:
            decision.allowed = False
            decision.reason = (
                f"This conversation has reached {self.config.session_message_cap} "
                "turns. Please clear it to start a new one."
            )
            return decision

        if last_message_ts is not None:
            elapsed = time.time() - last_message_ts
            if elapsed < self.config.cooldown_seconds:
                wait = self.config.cooldown_seconds - elapsed
                decision.allowed = False
                decision.reason = (
                    f"Please wait {wait:.0f}s between messages. "
                    "(Rate-limit to keep the free-tier budget alive.)"
                )
                return decision

        return decision

    def today_spend_usd(self) -> float:
        """Total cost recorded today (UTC) across all sessions."""
        today = date.today().isoformat()
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT COALESCE(SUM(cost_usd), 0) FROM assistant_events WHERE day_utc = ?",
                    (today,),
                ).fetchone()
                return float(row[0] or 0.0) if row else 0.0
            finally:
                if self.db_path != ":memory:":
                    conn.close()
        except sqlite3.Error:
            logger.exception("Failed to read today's assistant spend")
            return 0.0

    def record_turn(
        self,
        *,
        session_id: str,
        role: str,
        model: str | None = None,
        usage_dict: dict[str, Any] | None = None,
        elapsed_s: float = 0.0,
        tools_used: list[str] | None = None,
        stripped_markers: int = 0,
        error: str | None = None,
        question_chars: int = 0,
        answer_chars: int = 0,
    ) -> None:
        """Persist a single turn's metrics. Idempotent on row-level."""
        now = datetime.now(timezone.utc)
        usage = usage_dict or {}
        row = (
            now.isoformat(),
            now.date().isoformat(),
            session_id,
            role,
            model,
            int(usage.get("input_tokens", 0) or 0),
            int(usage.get("output_tokens", 0) or 0),
            int(usage.get("cache_creation_tokens", 0) or 0),
            int(usage.get("cache_read_tokens", 0) or 0),
            float(usage.get("cost_usd", 0.0) or 0.0),
            float(elapsed_s or 0.0),
            ",".join(tools_used or []),
            int(stripped_markers or 0),
            (error or "")[:1000] or None,
            int(question_chars or 0),
            int(answer_chars or 0),
        )
        try:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO assistant_events
                        (ts_utc, day_utc, session_id, role, model,
                         input_tokens, output_tokens, cache_creation_tokens,
                         cache_read_tokens, cost_usd, elapsed_s, tools,
                         stripped_markers, error, question_chars, answer_chars)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    row,
                )
                conn.commit()
            finally:
                if self.db_path != ":memory:":
                    conn.close()
        except sqlite3.Error:
            logger.exception("Failed to log assistant turn")


def new_session_id() -> str:
    """A short, opaque session identifier for telemetry / per-session caps."""
    return uuid.uuid4().hex[:16]


__all__ = [
    "RateLimitConfig",
    "RateLimitDecision",
    "RateLimiter",
    "new_session_id",
]
