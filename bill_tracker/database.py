"""
SQLite database interface for the Bill Tracker.

Schema:
  bills             — bill metadata from congress.gov
  cbo_estimates     — CBO cost estimates
  auto_scores       — calculator auto-scores
  mapping_overrides — manual provision overrides
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bill_tracker.auto_scorer import BillScore

from .cbo_fetcher import CBOCostEstimate
from .ingestor import BillMetadata

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS bills (
    bill_id TEXT PRIMARY KEY,
    congress INTEGER,
    chamber TEXT,
    number TEXT,
    bill_type TEXT,
    title TEXT,
    sponsor TEXT,
    introduced_date TEXT,
    latest_action TEXT,
    latest_action_date TEXT,
    status TEXT,
    crs_subjects TEXT,
    summary TEXT,
    url TEXT,
    has_cbo_score INTEGER DEFAULT 0,
    last_fetched TEXT
);

CREATE TABLE IF NOT EXISTS cbo_estimates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id TEXT,
    estimate_date TEXT,
    ten_year_cost_billions REAL,
    annual_costs TEXT,
    budget_function TEXT,
    dynamic_estimate REAL,
    pdf_url TEXT,
    cbo_url TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);

CREATE TABLE IF NOT EXISTS auto_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id TEXT,
    scored_at TEXT,
    ten_year_cost_billions REAL,
    annual_effects TEXT,
    static_cost REAL,
    behavioral_offset REAL,
    confidence TEXT,
    policies_json TEXT,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
);

CREATE TABLE IF NOT EXISTS mapping_overrides (
    bill_id TEXT PRIMARY KEY,
    policies_json TEXT,
    override_reason TEXT,
    mapped_by TEXT,
    mapped_date TEXT
);

CREATE TABLE IF NOT EXISTS pipeline_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class BillDatabase:
    """SQLite database interface for bill tracker data."""

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self._is_memory = self.db_path == ":memory:"
        # For in-memory databases, keep a persistent connection so data
        # survives across _connect() calls (each sqlite3.connect(":memory:")
        # creates a separate, independent database).
        if self._is_memory:
            self._persistent_conn = sqlite3.connect(":memory:")
            self._persistent_conn.row_factory = sqlite3.Row
            self._persistent_conn.execute("PRAGMA foreign_keys = ON")
        else:
            self._persistent_conn = None
        self._init_schema()

    # ------------------------------------------------------------------
    # Context manager for connections
    # ------------------------------------------------------------------

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        if self._is_memory:
            # Reuse the persistent connection for in-memory databases
            try:
                yield self._persistent_conn
                self._persistent_conn.commit()
            except Exception:
                self._persistent_conn.rollback()
                raise
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ------------------------------------------------------------------
    # Bills
    # ------------------------------------------------------------------

    def upsert_bill(self, bill: BillMetadata) -> None:
        """Insert or update a bill record."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO bills (
                    bill_id, congress, chamber, number, bill_type, title, sponsor,
                    introduced_date, latest_action, latest_action_date, status,
                    crs_subjects, summary, url, has_cbo_score, last_fetched
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bill_id) DO UPDATE SET
                    title=excluded.title,
                    sponsor=excluded.sponsor,
                    latest_action=excluded.latest_action,
                    latest_action_date=excluded.latest_action_date,
                    status=excluded.status,
                    crs_subjects=excluded.crs_subjects,
                    summary=excluded.summary,
                    has_cbo_score=excluded.has_cbo_score,
                    last_fetched=excluded.last_fetched
                """,
                (
                    bill.bill_id,
                    bill.congress,
                    bill.chamber,
                    bill.number,
                    bill.bill_type,
                    bill.title,
                    bill.sponsor,
                    _dt_str(bill.introduced_date),
                    bill.latest_action,
                    _dt_str(bill.latest_action_date),
                    bill.status,
                    json.dumps(bill.crs_subjects),
                    bill.summary,
                    bill.url,
                    int(bill.has_cbo_score),
                    _dt_str(bill.last_fetched),
                ),
            )

    def get_bill(self, bill_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bills WHERE bill_id = ?", (bill_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_all_bills(
        self,
        status: str | None = None,
        congress: int | None = None,
        has_cbo_score: bool | None = None,
        limit: int = 500,
    ) -> list[dict]:
        where_clauses: list[str] = []
        params: list[Any] = []

        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if congress:
            where_clauses.append("congress = ?")
            params.append(congress)
        if has_cbo_score is not None:
            where_clauses.append("has_cbo_score = ?")
            params.append(int(has_cbo_score))

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM bills {where_sql} ORDER BY introduced_date DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

    def count_bills(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]

    def update_bill_summary(self, bill_id: str, summary: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE bills SET summary = ? WHERE bill_id = ?",
                (summary, bill_id),
            )

    # ------------------------------------------------------------------
    # CBO Estimates
    # ------------------------------------------------------------------

    def upsert_cbo_score(self, estimate: CBOCostEstimate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO cbo_estimates (
                    bill_id, estimate_date, ten_year_cost_billions, annual_costs,
                    budget_function, dynamic_estimate, pdf_url, cbo_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    estimate.bill_id,
                    _dt_str(estimate.estimate_date),
                    estimate.ten_year_cost_billions,
                    json.dumps(estimate.annual_costs),
                    estimate.budget_function,
                    estimate.dynamic_estimate,
                    estimate.pdf_url,
                    estimate.cbo_url,
                ),
            )
            # Mark the bill as having a CBO score
            conn.execute(
                "UPDATE bills SET has_cbo_score = 1 WHERE bill_id = ?",
                (estimate.bill_id,),
            )

    def get_cbo_score(self, bill_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM cbo_estimates WHERE bill_id = ? ORDER BY estimate_date DESC LIMIT 1",
                (bill_id,),
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Auto Scores
    # ------------------------------------------------------------------

    def upsert_auto_score(self, score: BillScore) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auto_scores (
                    bill_id, scored_at, ten_year_cost_billions, annual_effects,
                    static_cost, behavioral_offset, confidence, policies_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score.bill_id,
                    _dt_str(score.scored_at),
                    score.ten_year_cost_billions,
                    json.dumps(score.annual_effects),
                    score.static_cost,
                    score.behavioral_offset,
                    score.confidence,
                    json.dumps(score.policies_json),
                ),
            )

    def get_auto_score(self, bill_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM auto_scores WHERE bill_id = ? ORDER BY scored_at DESC LIMIT 1",
                (bill_id,),
            ).fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # Manual Overrides
    # ------------------------------------------------------------------

    def upsert_manual_override(
        self,
        bill_id: str,
        policies_json: list[dict],
        override_reason: str = "",
        mapped_by: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mapping_overrides (bill_id, policies_json, override_reason, mapped_by, mapped_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(bill_id) DO UPDATE SET
                    policies_json=excluded.policies_json,
                    override_reason=excluded.override_reason,
                    mapped_by=excluded.mapped_by,
                    mapped_date=excluded.mapped_date
                """,
                (
                    bill_id,
                    json.dumps(policies_json),
                    override_reason,
                    mapped_by,
                    _dt_str(datetime.utcnow()),
                ),
            )

    def has_manual_override(self, bill_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM mapping_overrides WHERE bill_id = ?", (bill_id,)
            ).fetchone()
            return row is not None

    # ------------------------------------------------------------------
    # Pipeline State
    # ------------------------------------------------------------------

    def get_last_update(self) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM pipeline_state WHERE key = 'last_update'"
            ).fetchone()
            if not row:
                return None
            return _parse_dt(row[0])

    def set_last_update(self, dt: datetime) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_state (key, value) VALUES ('last_update', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (_dt_str(dt),),
            )


def _dt_str(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_dt(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None
