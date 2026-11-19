"""Frozen research snapshots (scripts/site_snapshots.py): append-only, hash-chained."""

from __future__ import annotations

import json
import shutil
from itertools import pairwise
from pathlib import Path

import pytest

from scripts import site_snapshots

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "site_data"


def _export_copy(tmp_path: Path) -> Path:
    """The committed export without its tracker or snapshots, as a source to snapshot."""
    out = tmp_path / "site_data"
    shutil.copytree(COMMITTED, out, ignore=shutil.ignore_patterns("tracker", "snapshots"))
    return out


def test_the_committed_snapshots_verify():
    assert site_snapshots.verify(COMMITTED) == []
    entries = site_snapshots.index_entries(COMMITTED / "snapshots")
    manifest = json.loads((COMMITTED / "manifest.json").read_text(encoding="utf-8"))
    assert entries[-1]["id"] == f"{manifest['scores_date']}-{manifest['scores_fingerprint']}"
    # Every snapshot after the first names its predecessor and that file's sha256.
    for before, after in pairwise(entries):
        assert after["previous_snapshot_id"] == before["id"]
        assert after["previous_sha256"] == before["sha256"]


def test_a_snapshot_is_written_once_and_never_rewritten(tmp_path: Path):
    site = _export_copy(tmp_path)
    entry = site_snapshots.write_snapshot(site, previous_id="2026-01-01-0123456789ab")
    assert entry is not None
    path = site / "snapshots" / entry["file"]
    first = path.read_bytes()
    # The same export again: nothing to do.
    assert site_snapshots.write_snapshot(site) is None
    assert path.read_bytes() == first
    # A file under that name holding other figures is refused, not overwritten.
    payload = json.loads(first)
    payload["scores_fingerprint"] = "ffffffffffff"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(site_snapshots.SnapshotConflict):
        site_snapshots.write_snapshot(site)


def test_a_snapshot_holds_the_exported_figures(tmp_path: Path):
    site = _export_copy(tmp_path)
    snapshot = site_snapshots.snapshot_payload(site)
    index = json.loads((site / "presets" / "index.json").read_text(encoding="utf-8"))["presets"]
    assert [row["id"] for row in snapshot["presets"]] == [row["id"] for row in index]
    for row in snapshot["presets"]:
        data = json.loads((site / "presets" / f"{row['id']}.json").read_text(encoding="utf-8"))
        conventional, dynamic = data["conventional"], data["dynamic"]
        assert row["conventional"]["ten_year_deficit_impact"] == pytest.approx(
            conventional["ten_year_deficit_impact"], abs=1e-4
        )
        if dynamic.get("dynamic_adjusted_impact") is not None:
            assert row["dynamic"]["dynamic_adjusted_impact"] == pytest.approx(
                dynamic["dynamic_adjusted_impact"], abs=1e-4
            )
        years = [y["final_effect"] for y in row["conventional"]["year_by_year"]]
        assert years == pytest.approx(
            [y["final_effect"] for y in conventional["year_by_year"]], abs=1e-4
        )
    catalog = json.loads((site / "build-catalog.json").read_text(encoding="utf-8"))
    assert [r["list_price_billions"] for r in snapshot["build_catalog"]] == pytest.approx(
        [r["score"] for r in catalog]
    )
    assert snapshot["sign_convention"].startswith("Billions of dollars")


def test_an_edit_to_an_old_snapshot_breaks_the_chain(tmp_path: Path):
    site = tmp_path / "site_data"
    shutil.copytree(COMMITTED / "snapshots", site / "snapshots")
    entries = site_snapshots.index_entries(site / "snapshots")
    oldest = site / "snapshots" / entries[0]["file"]
    oldest.write_bytes(oldest.read_bytes().replace(b'"presets":', b'"presets" :', 1))
    problems = site_snapshots.verify(site)
    assert any(entries[0]["file"] in problem and "changed after" in problem for problem in problems)
    # A stray file is reported too.
    (site / "snapshots" / "notes.txt").write_text("x", encoding="utf-8")
    assert any("notes.txt" in problem for problem in site_snapshots.verify(site))
