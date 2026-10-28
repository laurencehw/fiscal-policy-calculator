"""FPC-1: the tracker reads the nightly database, never an older snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from bill_tracker.database import BillDatabase
from fiscal_model.ui.tabs.bill_tracker import (
    DEFAULT_DB_PATH,
    POPULATED_DB_PATH,
    _choose_db_path,
    _last_update_of,
)


def _db(path: Path, stamp: datetime | None) -> Path:
    db = BillDatabase(str(path))
    if stamp is not None:
        db.set_last_update(stamp)
    return path


def test_nightly_wins_over_an_older_snapshot(tmp_path):
    nightly = _db(tmp_path / "bills.db", datetime(2026, 10, 28, tzinfo=timezone.utc))
    snapshot = _db(tmp_path / "bills_populated.db", datetime(2026, 4, 1, tzinfo=timezone.utc))
    assert _choose_db_path(nightly, snapshot) == nightly


def test_snapshot_only_when_nightly_is_missing_or_older(tmp_path):
    snapshot = _db(tmp_path / "bills_populated.db", datetime(2026, 4, 1, tzinfo=timezone.utc))
    missing = tmp_path / "bills.db"
    assert _choose_db_path(missing, snapshot) == snapshot
    older = _db(missing, datetime(2026, 3, 1, tzinfo=timezone.utc))
    assert _choose_db_path(older, snapshot) == snapshot


def test_nightly_without_a_stamp_still_beats_an_absent_snapshot(tmp_path):
    nightly = _db(tmp_path / "bills.db", None)
    assert _choose_db_path(nightly, tmp_path / "absent.db") == nightly


def test_committed_tracker_reads_the_newest_database():
    """The page must never read a database older than the nightly one in the repo."""
    chosen = _choose_db_path()
    if not DEFAULT_DB_PATH.exists():
        return
    assert chosen == DEFAULT_DB_PATH or (
        POPULATED_DB_PATH.exists()
        and (_last_update_of(POPULATED_DB_PATH) or datetime.min.replace(tzinfo=timezone.utc))
        > (_last_update_of(DEFAULT_DB_PATH) or datetime.min.replace(tzinfo=timezone.utc))
    )
