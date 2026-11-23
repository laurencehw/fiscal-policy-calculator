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
5. **Per-session daily cap** — answers to one session id per UTC day,
   counted by the ledger rather than by the caller's own history, so a
   caller that sends a stable id per visitor (the website does) caps each
   visitor. Default: 30.

All five are configurable via env vars (see :data:`_ENV_NAMES`).

Check-then-record is a race: two concurrent requests both read spend under
the cap, both call Anthropic, and both book afterwards. The HTTP endpoints
therefore use :meth:`RateLimiter.reserve_turn`, which checks the caps and
books an estimated per-turn cost (``ASSISTANT_TURN_RESERVATION_USD``, default
0.10 USD), the session's turn and its cool-down in one atomic step — one
``BEGIN IMMEDIATE`` sqlite transaction, or atomic counters in the shared
store — and :meth:`RateLimiter.record_turn` with ``reservation=`` replaces
the estimate with the turn's actual cost. Concurrent turns can then overshoot
the daily cap only by what each spends beyond its estimate.

On a serverless host every instance has its own sqlite file, so the daily
spend and the per-session daily count are also kept in a shared store when
one is configured (:mod:`.shared_ledger`); the caps then read that store.

The same sqlite table doubles as the telemetry log for the assistant
(see ``AssistantEventLog`` / step #11 in the rollout plan). One write
per turn keeps it cheap.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .shared_ledger import SharedLedger

logger = logging.getLogger(__name__)


_ENV_NAMES = {
    "daily_cost_cap_usd": "ASSISTANT_DAILY_COST_CAP_USD",
    "session_message_cap": "ASSISTANT_SESSION_MESSAGE_CAP",
    "cooldown_seconds": "ASSISTANT_COOLDOWN_SECONDS",
    "disabled": "ASSISTANT_DISABLED",
    "session_daily_cap": "ASSISTANT_SESSION_DAILY_CAP",
    "db_path": "ASSISTANT_USAGE_DB",
    "turn_reservation_usd": "ASSISTANT_TURN_RESERVATION_USD",
}

#: ``assistant_events.role`` values. Every paid Anthropic call writes one row
#: so :meth:`RateLimiter.today_spend_usd` — the daily cap — sees all spend.
#: A user-facing answer is a *turn*; the two auxiliary calls are labelled
#: separately so the admin dashboard can count turns and still sum all spend.
EVENT_ROLE_TURN = "assistant"
EVENT_ROLE_FOLLOWUPS = "followups"
EVENT_ROLE_PREWARM = "prewarm"
#: Build's free-text → values/goal translation (``composer/translate.py``).
EVENT_ROLE_TRANSLATE = "translate"
#: A turn's estimated cost, booked *before* its Anthropic calls by
#: :meth:`RateLimiter.reserve_turn` and replaced by the turn's own row.
EVENT_ROLE_RESERVATION = "reservation"

_DEFAULT_DAILY_CAP_USD = 5.00
_DEFAULT_SESSION_MESSAGE_CAP = 20
_DEFAULT_COOLDOWN_SECONDS = 3.0
_DEFAULT_SESSION_DAILY_CAP = 30
#: Estimated cost of one Ask turn, reserved before the paid calls are made.
#: A typical Sonnet turn with two or three tool calls costs 0.03-0.08 USD.
_DEFAULT_TURN_RESERVATION_USD = 0.10

_UNREADABLE_REASON = (
    "The assistant cannot check today's budget just now, so it is "
    "not answering. Please try again in a few minutes."
)


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
    session_daily_cap: int = _DEFAULT_SESSION_DAILY_CAP
    disabled: bool = False
    db_path: str = ""
    turn_reservation_usd: float = _DEFAULT_TURN_RESERVATION_USD

    @classmethod
    def from_env(cls) -> RateLimitConfig:
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
            session_daily_cap=_int("session_daily_cap", _DEFAULT_SESSION_DAILY_CAP),
            disabled=os.environ.get(_ENV_NAMES["disabled"], "").strip()
            in {"1", "true", "TRUE", "yes"},
            db_path=os.environ.get(_ENV_NAMES["db_path"], "").strip(),
            turn_reservation_usd=max(
                0.0, _float("turn_reservation_usd", _DEFAULT_TURN_RESERVATION_USD)
            ),
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
class TurnReservation:
    """A turn's estimated cost and its turn count, booked before it runs.

    Settle it with ``RateLimiter.record_turn(..., reservation=...)``.
    """

    session_id: str
    day: str
    estimate_usd: float
    #: The sqlite ``reservation`` row, when the local ledger holds the caps.
    row_id: int | None = None
    #: True when the shared store holds the estimate and the turn count.
    shared: bool = False
    settled: bool = False


@dataclass
class RateLimitDecision:
    allowed: bool
    reason: str = ""
    today_spend_usd: float = 0.0
    daily_cap_usd: float = 0.0
    session_messages: int = 0
    session_cap: int = 0
    #: Set by :meth:`RateLimiter.reserve_turn` when the turn is allowed.
    reservation: TurnReservation | None = None

    @property
    def budget_remaining_usd(self) -> float:
        return max(0.0, self.daily_cap_usd - self.today_spend_usd)


class RateLimiter:
    """Sqlite-backed daily-cap + per-session limiter + event logger.

    Thread-safe enough for Streamlit (single-writer, frequent reads);
    the underlying connection is opened per call rather than cached so
    Streamlit reruns don't trip the "thread X is not in thread Y" check.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        db_path: Path | None = None,
        shared: SharedLedger | bool | None = True,
    ):
        """``shared=True`` reads the shared store from the environment; pass a
        ledger to use that one, or ``None`` for sqlite alone."""
        self.config = config or RateLimitConfig.from_env()
        self.shared: SharedLedger | None = SharedLedger.from_env() if shared is True else (shared or None)
        if db_path is not None:
            path: Path = Path(db_path)
        elif self.config.db_path:
            path = Path(self.config.db_path)
        else:
            path = _default_db_path()
        self.db_path = str(path)
        self._in_memory_conn: sqlite3.Connection | None = None
        # Serialises reservations within this process (the in-memory
        # connection is shared); BEGIN IMMEDIATE serialises across processes.
        self._reserve_lock = threading.Lock()
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
        unreadable = False
        try:
            # The shared store is read strictly: an unreachable store must not
            # read as nothing spent across a fleet of instances.
            today_spend = self.today_spend_usd(strict=self.shared is not None)
        except Exception:
            logger.warning("Shared spend ledger unreadable; refusing the turn", exc_info=True)
            today_spend, unreadable = 0.0, True
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

        if unreadable:
            decision.allowed = False
            decision.reason = _UNREADABLE_REASON
            return decision

        if today_spend >= self.config.daily_cost_cap_usd:
            decision.allowed = False
            decision.reason = self._budget_reason(today_spend)
            return decision

        if session_message_count >= self.config.session_message_cap:
            decision.allowed = False
            decision.reason = self._conversation_cap_reason()
            return decision

        try:
            session_turns = self.session_turns_today(session_id, strict=True)
        except Exception:
            # Fail closed: an unreadable count must not read as "no turns yet".
            logger.error("Session turn count unreadable; refusing the turn", exc_info=True)
            decision.allowed = False
            decision.reason = _UNREADABLE_REASON
            return decision
        if session_turns >= self.config.session_daily_cap:
            decision.allowed = False
            decision.reason = self._session_cap_reason()
            return decision

        if last_message_ts is not None:
            elapsed = time.time() - last_message_ts
            if elapsed < self.config.cooldown_seconds:
                decision.allowed = False
                decision.reason = self._cooldown_reason(
                    self.config.cooldown_seconds - elapsed
                )
                return decision

        return decision

    # ---- user-facing reasons -------------------------------------------

    def _budget_reason(self, today_spend: float) -> str:
        # ``reason`` is rendered as markdown (``st.warning``), and an
        # unescaped ``$…$`` pair is a KaTeX span — the two amounts below
        # would render as math, not money. Escaped at the source so every
        # caller is safe.
        return (
            f"Today's free-tier budget is exhausted "
            f"(\\${today_spend:.2f} of "
            f"\\${self.config.daily_cost_cap_usd:.2f} "
            "used across all visitors). The cap resets at UTC midnight."
        )

    def _conversation_cap_reason(self) -> str:
        return (
            f"This conversation has reached {self.config.session_message_cap} "
            "turns. Please clear it to start a new one."
        )

    def _session_cap_reason(self) -> str:
        return (
            f"You have asked {self.config.session_daily_cap} questions today, "
            "the daily limit per visitor. The limit resets at UTC midnight."
        )

    @staticmethod
    def _cooldown_reason(wait: float) -> str:
        return (
            f"Please wait {wait:.0f}s between messages. "
            "(Rate-limit to keep the free-tier budget alive.)"
        )

    # ---- atomic reservation ---------------------------------------------

    def reserve_turn(
        self,
        *,
        session_id: str,
        session_message_count: int,
        estimate_usd: float | None = None,
    ) -> RateLimitDecision:
        """Check every cap and book the turn before any paid call is made.

        In one atomic step this checks the kill switch, the daily spend cap
        (counting the estimate), the session's daily turn cap and its
        cool-down (read from the ledger, so a caller cannot opt out of it),
        then books ``estimate_usd`` and one turn. When the turn is allowed
        the decision carries a :class:`TurnReservation`; pass it to
        :meth:`record_turn` so the estimate is replaced by the actual cost.

        Fails closed: a ledger that cannot be read or written refuses the turn.
        """
        estimate = (
            self.config.turn_reservation_usd
            if estimate_usd is None
            else max(0.0, float(estimate_usd))
        )
        decision = RateLimitDecision(
            allowed=True,
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
        if session_message_count >= self.config.session_message_cap:
            decision.allowed = False
            decision.reason = self._conversation_cap_reason()
            return decision
        if self.shared is not None:
            return self._reserve_shared(decision, session_id, estimate)
        return self._reserve_sqlite(decision, session_id, estimate)

    def _over_budget(self, spend: float, estimate: float) -> bool:
        cap = self.config.daily_cost_cap_usd
        return spend >= cap or spend + estimate > cap

    def _reserve_sqlite(
        self, decision: RateLimitDecision, session_id: str, estimate: float
    ) -> RateLimitDecision:
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        with self._reserve_lock:
            try:
                conn = self._connect()
            except sqlite3.Error:
                logger.error("Usage ledger unavailable; refusing the turn", exc_info=True)
                decision.allowed = False
                decision.reason = _UNREADABLE_REASON
                return decision
            try:
                if conn.in_transaction:
                    conn.commit()
                # One write-locked transaction: no other process or thread can
                # read the same spend between this read and the insert below.
                conn.execute("BEGIN IMMEDIATE")
                spend_row = conn.execute(
                    "SELECT COALESCE(SUM(cost_usd), 0) FROM assistant_events WHERE day_utc = ?",
                    (today,),
                ).fetchone()
                spend = float(spend_row[0] or 0.0) if spend_row else 0.0
                session_row = conn.execute(
                    "SELECT COUNT(*), MAX(ts_utc) FROM assistant_events "
                    "WHERE day_utc = ? AND session_id = ? AND role IN (?, ?)",
                    (today, session_id, EVENT_ROLE_TURN, EVENT_ROLE_RESERVATION),
                ).fetchone()
                turns = int(session_row[0] or 0) if session_row else 0
                last_ts = session_row[1] if session_row else None
                decision.today_spend_usd = spend

                refusal = ""
                if self._over_budget(spend, estimate):
                    refusal = self._budget_reason(spend)
                elif turns >= self.config.session_daily_cap:
                    refusal = self._session_cap_reason()
                elif last_ts and self.config.cooldown_seconds > 0:
                    elapsed = (now - datetime.fromisoformat(last_ts)).total_seconds()
                    if elapsed < self.config.cooldown_seconds:
                        refusal = self._cooldown_reason(
                            self.config.cooldown_seconds - elapsed
                        )
                if refusal:
                    conn.rollback()
                    decision.allowed = False
                    decision.reason = refusal
                    return decision

                cursor = conn.execute(
                    "INSERT INTO assistant_events "
                    "(ts_utc, day_utc, session_id, role, cost_usd) VALUES (?, ?, ?, ?, ?)",
                    (now.isoformat(), today, session_id, EVENT_ROLE_RESERVATION, estimate),
                )
                conn.commit()
                decision.reservation = TurnReservation(
                    session_id=session_id,
                    day=today,
                    estimate_usd=estimate,
                    row_id=cursor.lastrowid,
                )
                return decision
            except (sqlite3.Error, ValueError):
                logger.error("Could not reserve an Ask turn; refusing it", exc_info=True)
                with contextlib.suppress(sqlite3.Error):
                    conn.rollback()
                decision.allowed = False
                decision.reason = _UNREADABLE_REASON
                return decision
            finally:
                if self.db_path != ":memory:":
                    conn.close()

    def _reserve_shared(
        self, decision: RateLimitDecision, session_id: str, estimate: float
    ) -> RateLimitDecision:
        shared = self.shared
        assert shared is not None
        today = datetime.now(timezone.utc).date().isoformat()
        counted_turn = False
        booked = False
        try:
            if self.config.cooldown_seconds > 0 and not shared.claim_cooldown(
                session_id, self.config.cooldown_seconds
            ):
                decision.allowed = False
                decision.reason = self._cooldown_reason(self.config.cooldown_seconds)
                return decision
            turns = shared.incr_turn(today, session_id)
            counted_turn = True
            if turns > self.config.session_daily_cap:
                shared.decr_turn(today, session_id)
                counted_turn = False
                decision.allowed = False
                decision.reason = self._session_cap_reason()
                return decision
            total = shared.incr_spend(today, estimate)
            booked = True
            spend_before = max(0.0, total - estimate)
            decision.today_spend_usd = spend_before
            if self._over_budget(spend_before, estimate):
                shared.incr_spend(today, -estimate)
                booked = False
                shared.decr_turn(today, session_id)
                counted_turn = False
                decision.allowed = False
                decision.reason = self._budget_reason(spend_before)
                return decision
        except Exception:
            logger.error("Shared ledger unavailable; refusing the turn", exc_info=True)
            # Undo what was booked, best effort; failing that the store
            # over-counts, which errs on the side of the budget.
            try:
                if booked:
                    shared.incr_spend(today, -estimate)
                if counted_turn:
                    shared.decr_turn(today, session_id)
            except Exception:
                logger.warning("Could not undo a partial reservation", exc_info=True)
            decision.allowed = False
            decision.reason = _UNREADABLE_REASON
            return decision
        decision.reservation = TurnReservation(
            session_id=session_id, day=today, estimate_usd=estimate, shared=True
        )
        return decision

    def check_budget(self) -> RateLimitDecision:
        """The money gate alone: kill switch and daily spend cap.

        For the auxiliary paid calls (follow-up chips, prompt-cache
        pre-warm), which are not user turns and so are not subject to the
        per-session message cap or cool-down, but must never spend once the
        operator has disabled Ask or the day's budget is gone.
        """
        # Strict read: an unreadable ledger raises here instead of reading as
        # $0 spent, so ``budget_allows`` fails closed rather than spending blind.
        today_spend = self.today_spend_usd(strict=True)
        decision = RateLimitDecision(
            allowed=True,
            today_spend_usd=today_spend,
            daily_cap_usd=self.config.daily_cost_cap_usd,
        )
        if self.config.disabled:
            decision.allowed = False
            decision.reason = "disabled"
        elif today_spend >= self.config.daily_cost_cap_usd:
            decision.allowed = False
            decision.reason = "daily cost cap reached"
        return decision

    def today_spend_usd(self, *, strict: bool = False) -> float:
        """Total cost recorded today (UTC) across all sessions.

        A read failure returns ``0.0`` for display callers; ``strict=True``
        re-raises it, for gates that must not mistake "unreadable" for "unspent".
        """
        today = datetime.now(timezone.utc).date().isoformat()
        if self.shared is not None:
            try:
                return self.shared.spend_usd(today)
            except Exception:
                if strict:
                    raise
                logger.warning("Failed to read today's shared assistant spend", exc_info=True)
                return 0.0
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
            if strict:
                raise
            logger.exception("Failed to read today's assistant spend")
            return 0.0

    def session_turns_today(self, session_id: str, *, strict: bool = False) -> int:
        """Answers recorded today (UTC) for one session id.

        A read failure returns ``0`` for display callers; ``strict=True``
        re-raises it, so :meth:`check` fails closed rather than mistaking
        "unreadable" for "no turns yet".
        """
        today = datetime.now(timezone.utc).date().isoformat()
        if self.shared is not None:
            try:
                return self.shared.session_turns(today, session_id)
            except Exception:
                if strict:
                    raise
                logger.warning("Failed to read the shared session count", exc_info=True)
                return 0
        try:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM assistant_events WHERE day_utc = ? AND session_id = ? AND role = ?",
                    (today, session_id, EVENT_ROLE_TURN),
                ).fetchone()
                return int(row[0] or 0) if row else 0
            finally:
                if self.db_path != ":memory:":
                    conn.close()
        except sqlite3.Error:
            if strict:
                raise
            logger.exception("Failed to count today's session turns")
            return 0

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
        reservation: TurnReservation | None = None,
        charge_at_least_reservation: bool = False,
    ) -> None:
        """Persist a single turn's metrics. Idempotent on row-level.

        With ``reservation`` (from :meth:`reserve_turn`) the reserved estimate
        is replaced by this turn's actual cost: the sqlite reservation row is
        deleted in the transaction that writes the turn, or the shared store
        is adjusted by the difference (the turn itself was counted when it
        was reserved). ``charge_at_least_reservation`` books
        ``max(actual, estimate)``, for a turn cut off before the usage of its
        last call could be read.
        """
        now = datetime.now(timezone.utc)
        usage = dict(usage_dict or {})
        live = reservation if reservation is not None and not reservation.settled else None
        if live is not None and charge_at_least_reservation:
            usage["cost_usd"] = max(
                float(usage.get("cost_usd", 0.0) or 0.0), live.estimate_usd
            )
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
                if live is not None and live.row_id is not None:
                    conn.execute(
                        "DELETE FROM assistant_events WHERE id = ? AND role = ?",
                        (live.row_id, EVENT_ROLE_RESERVATION),
                    )
                conn.commit()
            finally:
                if self.db_path != ":memory:":
                    conn.close()
        except sqlite3.Error:
            # The reservation row, if any, stays and keeps the estimate
            # counted: a failed write errs on the budget's side.
            logger.exception("Failed to log assistant turn")
        if live is not None:
            live.settled = True
        if self.shared is not None:
            try:
                cost = float(usage.get("cost_usd", 0.0) or 0.0)
                if live is not None and live.shared:
                    # The estimate and the turn are already in the store; book
                    # the difference on the reservation's own day.
                    delta = cost - live.estimate_usd
                    if delta:
                        self.shared.add_spend(live.day, delta)
                else:
                    if cost > 0:
                        self.shared.add_spend(now.date().isoformat(), cost)
                    if role == EVENT_ROLE_TURN:
                        self.shared.add_turn(now.date().isoformat(), session_id)
            except Exception:
                logger.error("Failed to record the turn in the shared ledger", exc_info=True)


def budget_allows(ledger: RateLimiter) -> bool:
    """Kill switch + daily cap, for a paid call that is not a user turn.

    Checked *before* spending. Fails closed: if the ledger cannot be read,
    the call is skipped rather than made blind.
    """
    try:
        return bool(ledger.check_budget().allowed)
    except Exception:
        logger.warning("Budget check failed; skipping paid call", exc_info=True)
        return False


def record_paid_call(
    ledger: RateLimiter,
    *,
    role: str,
    model: str,
    usage: Any,
    session_id: str,
    elapsed_s: float = 0.0,
) -> None:
    """Book one paid call's cost in ``assistant_events`` under ``role``.

    Priced with the same table as an Ask turn (:mod:`.cost`). Never raises.
    """
    try:
        from .cost import ConversationCost

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


def new_session_id() -> str:
    """A short, opaque session identifier for telemetry / per-session caps."""
    return uuid.uuid4().hex[:16]


__all__ = [
    "EVENT_ROLE_FOLLOWUPS",
    "EVENT_ROLE_PREWARM",
    "EVENT_ROLE_RESERVATION",
    "EVENT_ROLE_TRANSLATE",
    "EVENT_ROLE_TURN",
    "RateLimitConfig",
    "RateLimitDecision",
    "RateLimiter",
    "TurnReservation",
    "budget_allows",
    "new_session_id",
    "record_paid_call",
]
