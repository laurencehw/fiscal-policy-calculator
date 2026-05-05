"""Tests for the bundled FRED seed refresh script."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refresh_fred_seed.py"
SPEC = importlib.util.spec_from_file_location("refresh_fred_seed_script", SCRIPT_PATH)
assert SPEC is not None
refresh_fred_seed = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = refresh_fred_seed
SPEC.loader.exec_module(refresh_fred_seed)


class DummyFred:
    bundled_seed_max_age_days = 120

    def __init__(self, available: bool = True):
        self.available = available
        self.requested_series: list[str] = []

    def is_available(self) -> bool:
        return self.available

    def require_live(self, series_id: str) -> pd.Series:
        self.requested_series.append(series_id)
        index = pd.date_range("2026-01-01", periods=10, freq="D")
        return pd.Series(range(10), index=index, name=series_id)


def test_build_seed_payload_uses_live_series_with_provenance():
    fred = DummyFred()
    fetched_at = datetime(2026, 5, 1, 12, 30, tzinfo=timezone.utc)

    payload = refresh_fred_seed.build_seed_payload(
        fred,
        observation_count=3,
        fetched_at=fetched_at,
    )

    expected_series = {"GDP", "GDPC1", "UNRATE", "DGS10"}
    assert set(payload["series"]) == expected_series
    assert fred.requested_series == ["GDP", "GDPC1", "UNRATE", "DGS10"]
    assert payload["updated_at"] == "2026-05-01T12:30:00Z"
    assert payload["generated_at"] == "2026-05-01T12:30:00Z"
    assert payload["max_age_days"] == 120
    assert "hardcoded" not in payload["source"].lower()

    gdp = payload["series"]["GDP"]
    assert gdp["series_id"] == "GDP"
    assert gdp["source_url"] == "https://fred.stlouisfed.org/series/GDP"
    assert gdp["observations"] == 3
    assert gdp["latest_observation"] == "2026-01-10 00:00:00"
    assert gdp["values"] == {
        "2026-01-08 00:00:00": 7.0,
        "2026-01-09 00:00:00": 8.0,
        "2026-01-10 00:00:00": 9.0,
    }


def test_refresh_seed_writes_seed_json_atomically(tmp_path):
    output_path = tmp_path / "fred_seed.json"
    fetched_at = datetime(2026, 5, 1, 12, 30, tzinfo=timezone.utc)

    payload = refresh_fred_seed.refresh_seed(
        output_path,
        observation_count=2,
        fred_client=DummyFred(),
        fetched_at=fetched_at,
    )

    stored = json.loads(output_path.read_text(encoding="utf-8"))
    assert stored == payload
    assert stored["series"]["GDPC1"]["observations"] == 2
    assert not output_path.with_name("fred_seed.json.tmp").exists()


def test_refresh_seed_dry_run_does_not_write(tmp_path):
    output_path = tmp_path / "fred_seed.json"

    payload = refresh_fred_seed.refresh_seed(
        output_path,
        observation_count=1,
        dry_run=True,
        fred_client=DummyFred(),
    )

    assert payload["series"]["DGS10"]["observations"] == 1
    assert not output_path.exists()


def test_refresh_seed_requires_live_fred_client(tmp_path):
    with pytest.raises(refresh_fred_seed.FREDUnavailableError, match="FRED API"):
        refresh_fred_seed.refresh_seed(
            tmp_path / "fred_seed.json",
            fred_client=DummyFred(available=False),
        )


def test_main_dry_run_prints_json_without_writing(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "fred_seed.json"
    monkeypatch.setattr(
        refresh_fred_seed,
        "FREDData",
        lambda timeout_seconds: DummyFred(),
    )

    exit_code = refresh_fred_seed.main(
        ["--output", str(output_path), "--observations", "1", "--dry-run"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out)["series"]["GDP"]["observations"] == 1
    assert captured.err == ""
    assert not output_path.exists()


def test_main_returns_2_when_fred_is_unavailable(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "fred_seed.json"
    monkeypatch.setattr(
        refresh_fred_seed,
        "FREDData",
        lambda timeout_seconds: DummyFred(available=False),
    )

    exit_code = refresh_fred_seed.main(["--output", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "FRED API is not configured" in captured.err
    assert captured.out == ""
    assert not output_path.exists()
