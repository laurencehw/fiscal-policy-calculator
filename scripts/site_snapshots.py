"""Frozen research snapshots of the site's scored figures, one per scores fingerprint.

``scripts/export_static.py`` rewrites ``site_data/`` every night, so the figures a
reader saw last month are gone from the live export. A snapshot keeps them: each
time the scores fingerprint changes, the export writes
``site_data/snapshots/<scores_date>-<fingerprint>.json``. A snapshot is
written once and never rewritten (``write_snapshot`` refuses), and each records
the sha256 of the one before it, so the files form a hash chain that
``--verify`` checks.

What a snapshot holds, read back from the exported files only (so the same
function can rebuild a snapshot from an old export in git history):

- every Explore preset's conventional and dynamic ten-year figures, their
  components and year-by-year paths, the published score it is checked
  against, its law status, and the error band the page draws;
- Build's list prices;
- the validation tiers the Methods page quotes.

The scores fingerprint covers the conventional and dynamic ten-year preset
figures, Build's list prices and the baseline vintages, rounded to $0.1B.
Everything else in a snapshot (year-by-year paths, published comparison scores,
labels, validation tiers) is recorded as it stood when that fingerprint was
first exported.

Usage:
    python scripts/site_snapshots.py                       # snapshot site_data/ if new
    python scripts/site_snapshots.py --verify              # check the hash chain
    python scripts/site_snapshots.py --list                # every snapshot, oldest first
    python scripts/site_snapshots.py --from OLD_EXPORT \\
        --source-commit SHA --previous ID                  # backfill from an old export
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_DATA = ROOT / "site_data"
SNAPSHOT_DIR = "snapshots"
SNAPSHOT_SCHEMA = "fiscal-policy-calculator/snapshot/v1"
REPOSITORY = "https://github.com/laurencehw/fiscal-policy-calculator"
#: Billions to four decimals is $0.1M, finer than any figure the site prints.
DECIMALS = 4

COVERED_NOTE = (
    "The scores fingerprint covers each preset's conventional and dynamic ten-year "
    "figures, Build's list prices and the baseline vintages, rounded to $0.1B. The "
    "rest of this file (year-by-year paths, published comparison scores, labels, "
    "validation tiers) is recorded as it stood when the fingerprint was first exported."
)


class SnapshotConflict(RuntimeError):
    """A snapshot that already exists would be rewritten with different bytes."""


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _num(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return round(float(value), DECIMALS) + 0.0
    return value


def _pick(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: _num(source.get(key)) for key in keys if key in source}


def _years(rows: list[dict[str, Any]] | None, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    return [{"year": row.get("year"), **_pick(row, keys)} for row in rows or []]


CONVENTIONAL_KEYS = (
    "ten_year_deficit_impact",
    "static_revenue_effect",
    "behavioral_offset",
    "final_static_effect",
)
DYNAMIC_KEYS = (
    "dynamic_adjusted_impact",
    "ten_year_deficit_impact",
    "revenue_feedback",
    "debt_service",
    "gdp_effect",
    "employment_effect",
)
CREDIBILITY_KEYS = (
    "evidence_type",
    "class_label",
    "n_tier1_rows",
    "mean_abs_pct_error",
    "max_abs_pct_error",
    "uncertainty_low",
    "uncertainty_high",
    "outer_low",
    "outer_high",
    "no_band_reason",
    "own_row_policy_id",
    "own_row_tier",
    "own_row_tier_label",
    "own_row_abs_pct_error",
    "own_row_official_billions",
    "own_row_model_billions",
    "own_row_window",
)


def _preset(info: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    conventional = data.get("conventional") or {}
    dynamic = data.get("dynamic") or {}
    status = info.get("status") or {}
    credibility = conventional.get("credibility") or {}
    return {
        "id": info["id"],
        "name": info.get("name") or conventional.get("policy_name") or info["id"],
        "law_status": status.get("status") if isinstance(status, dict) else None,
        "published": {
            "billions": _num(info.get("cbo_score")),
            "source": info.get("cbo_source"),
            "date": info.get("cbo_date"),
            "is_published_score": info.get("cbo_published"),
        },
        "conventional": {
            "budget_window": conventional.get("budget_window"),
            "baseline_vintage": conventional.get("baseline_vintage"),
            **_pick(conventional, CONVENTIONAL_KEYS),
            "year_by_year": _years(
                conventional.get("year_by_year"),
                ("revenue_effect", "behavioral_offset", "final_effect"),
            ),
        },
        "dynamic": {
            "model": dynamic.get("dynamic_model"),
            **_pick(dynamic, DYNAMIC_KEYS),
            "year_by_year": _years(
                dynamic.get("year_by_year"),
                ("final_effect", "dynamic_feedback", "debt_service", "dynamic_effect"),
            ),
        },
        "error_band": _pick(credibility, CREDIBILITY_KEYS) if isinstance(credibility, dict) else {},
    }


def _build_row(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get("status") or {}
    return {
        "build_id": row.get("build_id"),
        "label": row.get("label"),
        "area": row.get("area"),
        "list_price_billions": _num(row.get("score")),
        "source": row.get("source"),
        "source_date": row.get("source_date"),
        "is_published_score": row.get("cbo_published"),
        "illustrative": row.get("illustrative"),
        "law_status": status.get("status") if isinstance(status, dict) else None,
    }


def _validation(site_data: Path) -> dict[str, Any] | None:
    path = site_data / "validation" / "evidence.json"
    if not path.exists():
        return None
    evidence = _read(path)
    keep = (
        "out_of_sample",
        "out_of_sample_classes",
        "calibrated",
        "leave_one_out",
        "data_vintages",
    )
    return {key: evidence[key] for key in keep if key in evidence}


def snapshot_id(manifest: dict[str, Any]) -> str:
    return f"{manifest['scores_date']}-{manifest['scores_fingerprint']}"


def snapshot_payload(site_data: Path, *, source_commit: str | None = None) -> dict[str, Any]:
    """The snapshot of the export in ``site_data``, built from its files alone."""
    manifest = _read(site_data / "manifest.json")
    if not manifest.get("scores_date") or not manifest.get("scores_fingerprint"):
        raise ValueError(f"{site_data}/manifest.json has no scores_date/scores_fingerprint")
    index = _read(site_data / "presets" / "index.json")["presets"]
    presets = [_preset(info, _read(site_data / "presets" / f"{info['id']}.json")) for info in index]
    catalog_path = site_data / "build-catalog.json"
    catalog = [_build_row(row) for row in _read(catalog_path)] if catalog_path.exists() else []
    payload: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA,
        "id": snapshot_id(manifest),
        "scores_date": manifest["scores_date"],
        "scores_fingerprint": manifest["scores_fingerprint"],
        "export_schema_version": manifest.get("schema_version"),
        "baseline_vintages": manifest.get("baseline_vintages", []),
        "budget_windows": manifest.get("budget_windows", []),
        "sign_convention": manifest.get("sign_convention"),
        "units": "Billions of nominal dollars.",
        "fingerprint_covers": COVERED_NOTE,
        "repository": REPOSITORY,
        "license": "Data CC BY 4.0; code MIT (see the repository)",
        "presets": presets,
        "build_catalog": catalog,
        "validation": _validation(site_data),
    }
    if source_commit:
        payload["source_commit"] = source_commit
    return payload


def _text(payload: dict[str, Any]) -> str:
    # Compact: a snapshot is never edited, so there is no diff to keep readable.
    return json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_files(snapshot_dir: Path) -> list[Path]:
    return sorted(
        path for path in snapshot_dir.glob("*.json") if SNAPSHOT_NAME.fullmatch(path.name)
    )


SNAPSHOT_NAME = re.compile(r"\d{4}-\d{2}-\d{2}-[0-9a-f]{12}\.json")


def index_entries(snapshot_dir: Path) -> list[dict[str, Any]]:
    """Every snapshot in ``snapshot_dir``, oldest first.

    There is no committed index file: two branches that each add a snapshot
    would conflict on it, and the nightly job would overwrite one. The order is
    the scores date, then each snapshot's ``previous_snapshot_id`` chain within
    a day, then the id. ``web/lib/research.ts`` orders the same way.
    """
    entries: dict[str, dict[str, Any]] = {}
    for path in _snapshot_files(snapshot_dir):
        payload = _read(path)
        entries[payload["id"]] = {
            "id": payload["id"],
            "scores_date": payload["scores_date"],
            "scores_fingerprint": payload["scores_fingerprint"],
            "file": path.name,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "presets": len(payload.get("presets", [])),
            "build_rows": len(payload.get("build_catalog", [])),
            "previous_snapshot_id": payload.get("previous_snapshot_id"),
            "previous_sha256": payload.get("previous_sha256"),
            "source_commit": payload.get("source_commit"),
        }

    def depth(entry: dict[str, Any]) -> int:
        seen, count, current = set(), 0, entry
        while True:
            parent = entries.get(current.get("previous_snapshot_id") or "")
            if not parent or parent["scores_date"] != entry["scores_date"] or parent["id"] in seen:
                return count
            seen.add(parent["id"])
            count, current = count + 1, parent

    return sorted(entries.values(), key=lambda e: (e["scores_date"], depth(e), e["id"]))


def write_snapshot(
    site_data: Path,
    *,
    source: Path | None = None,
    source_commit: str | None = None,
    previous_id: str | None = None,
) -> dict[str, Any] | None:
    """Add the snapshot of ``source`` (default ``site_data``) under ``site_data/snapshots``.

    ``previous_id`` names the snapshot the site showed before this one (the
    previous export's scores date and fingerprint); its sha256 is recorded too,
    so the snapshots form a hash chain and an edit to an old one shows.

    Returns the new entry, or None when this snapshot already exists with the
    same figures. Raises ``SnapshotConflict`` rather than rewrite one.
    """
    snapshot_dir = site_data / SNAPSHOT_DIR
    payload = snapshot_payload(source or site_data, source_commit=source_commit)
    path = snapshot_dir / f"{payload['id']}.json"
    if path.exists():
        existing = _read(path)
        if existing.get("scores_fingerprint") != payload["scores_fingerprint"]:
            raise SnapshotConflict(
                f"{path} holds a different fingerprint; refusing to overwrite it"
            )
        return None
    if previous_id and previous_id != payload["id"]:
        previous = snapshot_dir / f"{previous_id}.json"
        payload["previous_snapshot_id"] = previous_id
        payload["previous_sha256"] = sha256_of(previous) if previous.exists() else None
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(_text(payload), encoding="utf-8", newline="\n")
    return next(entry for entry in index_entries(snapshot_dir) if entry["id"] == payload["id"])


def verify(site_data: Path) -> list[str]:
    """Problems with the committed snapshots: a misnamed file, or a broken hash chain."""
    snapshot_dir = site_data / SNAPSHOT_DIR
    problems: list[str] = []
    for path in snapshot_dir.glob("*"):
        if not SNAPSHOT_NAME.fullmatch(path.name):
            problems.append(f"{path.name}: not a snapshot file name")
    entries = {entry["id"]: entry for entry in index_entries(snapshot_dir)}
    for entry in entries.values():
        payload = _read(snapshot_dir / entry["file"])
        if f"{payload.get('scores_date')}-{payload.get('scores_fingerprint')}" != entry["id"]:
            problems.append(f"{entry['file']}: its id does not match its date and fingerprint")
        if entry["file"] != f"{entry['id']}.json":
            problems.append(f"{entry['file']}: file name differs from its id {entry['id']}")
        parent = entries.get(entry.get("previous_snapshot_id") or "")
        if parent and entry.get("previous_sha256") and parent["sha256"] != entry["previous_sha256"]:
            problems.append(f"{parent['file']}: changed after {entry['file']} recorded its sha256")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--site-data", type=Path, default=DEFAULT_SITE_DATA)
    parser.add_argument(
        "--from", dest="source", type=Path, default=None, help="an older export to snapshot"
    )
    parser.add_argument(
        "--source-commit", default=None, help="the commit the older export came from"
    )
    parser.add_argument("--previous", default=None, help="the id of the snapshot before this one")
    parser.add_argument(
        "--verify", action="store_true", help="check the committed snapshots and exit"
    )
    parser.add_argument("--list", action="store_true", help="print every snapshot, oldest first")
    args = parser.parse_args(argv)
    if args.verify:
        problems = verify(args.site_data)
        print("\n".join(problems) or "snapshots OK")
        return 1 if problems else 0
    if args.list:
        print(json.dumps(index_entries(args.site_data / SNAPSHOT_DIR), indent=2))
        return 0
    entry = write_snapshot(
        args.site_data,
        source=args.source,
        source_commit=args.source_commit,
        previous_id=args.previous,
    )
    print(json.dumps(entry, indent=2) if entry else "No new snapshot: this one already exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
