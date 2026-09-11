#!/usr/bin/env python3
"""
Transcribe CBO's own statutory tax-parameter schedule from CBO's own GitHub.

WHY THIS SCRIPT EXISTS
----------------------
``fiscal_model/validation/cbo_scores.py`` used to say, in as many words, that a
year-indexed bracket boundary could not be built because *a published post-2025
rate table does not exist*, and ``planning/HIGH_STAKES_ACCURACY.md`` carried the
same verdict in its rejection table.

It exists. ``US-CBO/cbo-data`` ships CBO publication 53724, *Tax Parameters and
Effective Marginal Tax Rates*, as machine-readable CSV under a public-domain
dedication, on three baseline vintages, and the June 2024 edition carries the
whole post-2025 schedule the app was told was unavailable: rates reverting to
10/15/25/28/33/35/39.6 in CY2026 and all seven bracket floors in all four
filing statuses out to CY2034.

WHAT IT READS
-------------
One repository, pinned by commit SHA and verified by SHA-256 of the file
actually read (the same rule as ``scripts/fetch_cbo_baseline.py``):

* ``US-CBO/cbo-data`` - ``data/budget/tax_parameters/annual_cy_{edition}.csv``,
  one row per variable per calendar year, for editions ``2024-06``, ``2025-01``
  and ``2026-02``.

WHAT IT WRITES
--------------
``fiscal_model/data_files/cbo_tax_parameters/cbo_tax_parameters.csv``, long
format (``vintage,calendar_year,variable,value``), **verbatim**: every variable
CBO publishes, not a hand-picked subset, so the file's SHA-256 relationship to
the upstream one is a property a reader can check rather than a claim. And
``PROVENANCE.csv``, one row per vintage, which
``fiscal_model/cbo_tax_parameters.py`` reads to grade each vintage's match.

THE ONE SUBSTITUTION, AND WHY IT IS GRADED RATHER THAN HIDDEN
-------------------------------------------------------------
``cbo-data``'s oldest ``tax_parameters`` edition is ``2024-06``. The app's
``cbo_feb_2024`` vintage - the one the CBO Options battery is scored on - has no
edition of its own, so it is mapped to ``2024-06`` and graded
``nearest_vintage``, never ``exact``.

``scripts/fetch_cbo_baseline.py`` refused the identical substitution for the
*budget* table, and that refusal is kept rather than overridden: what is
substituted here is a different kind of object. A budget projection is a set of
numbers that changes with every edition. A rate schedule is **statute** plus a
projection of the price index that indexes it. The structure - seven brackets,
the CY2026 reversion, the rates on either side of it - was identical in
February and June 2024 because the law was. Only the indexed dollar boundaries
differ, by whatever CBO's chained-CPI assumption moved in four months, and the
size of that is measured rather than asserted: CY2025's ``tp_bracket_4_mfj``
is 207,300 here against the IRS's later actual of 206,700 (Rev. Proc. 2024-40
section 2.01), **+0.29%**, and re-scoring the one benchmark that reads this
boundary with the Revenue Procedure's actuals instead moves it by one cent.

WHAT IT DOES NOT DO
-------------------
It does not reconcile CBO's projected boundaries against the Revenue Procedures
for years the IRS has since published, and it does not blend the two. One
series, one source, one vintage - a seam in the middle of a schedule would make
the CY2026 step unreadable, since a reader could not tell the reversion from the
source change.

USAGE
-----
    python scripts/fetch_cbo_tax_parameters.py                 # verify, rewrite
    python scripts/fetch_cbo_tax_parameters.py --check         # verify only
    python scripts/fetch_cbo_tax_parameters.py --source-dir D  # read clones under D
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
import urllib.request
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "cbo_tax_parameters"

#: Date the pinned commit below was fetched and its digests recorded.
FETCH_DATE = "2026-09-11"

#: Pinned commit, not a branch. Same commit ``fetch_cbo_baseline.py`` pins, so
#: the two transcriptions describe one snapshot of CBO's repository.
REPO_URL = "https://github.com/US-CBO/cbo-data"
REPO_COMMIT = "284a95665f9f2f74ed1f482feb629b43fce323da"
REPO_COMMIT_DATE = "2026-06-12"

#: The app's baseline vintage ids mapped to CBO's own edition tags.
#:
#: ``match`` is the grade :mod:`fiscal_model.cbo_tax_parameters` reports and
#: :mod:`fiscal_model.policies_core` never overrides. ``exact`` means the
#: edition tag is this vintage's own; ``nearest_vintage`` means it is not, and
#: says which edition was read instead.
VINTAGES: dict[str, dict[str, str]] = {
    "cbo_feb_2024": {
        "edition": "2024-06",
        "match": "nearest_vintage",
        "publication": (
            "CBO, Tax Parameters and Effective Marginal Tax Rates "
            "(publication 53724), June 2024 edition"
        ),
        "note": (
            "cbo-data/data/budget/tax_parameters carries 2024-06, 2025-01 and "
            "2026-02 only; there is no February 2024 edition. June 2024 is read "
            "instead. The statutory STRUCTURE is identical - the law did not "
            "change between February and June 2024 - and only the indexed "
            "dollar boundaries differ. Sized: CY2025 tp_bracket_4_mfj is "
            "207,300 here against the IRS actual of 206,700 (Rev. Proc. "
            "2024-40 section 2.01), +0.29%, worth $0.01B on the one benchmark "
            "that reads it."
        ),
    },
    "cbo_jan_2025": {
        "edition": "2025-01",
        "match": "exact",
        "publication": (
            "CBO, Tax Parameters and Effective Marginal Tax Rates "
            "(publication 53724), January 2025 edition"
        ),
        "note": "",
    },
    "cbo_feb_2026": {
        "edition": "2026-02",
        "match": "exact",
        "publication": (
            "CBO, Tax Parameters and Effective Marginal Tax Rates "
            "(publication 53724), February 2026 edition"
        ),
        "note": "",
    },
}

#: SHA-256 of each pinned source file, recorded on :data:`FETCH_DATE`.
DIGESTS: dict[str, str] = {
    "data/budget/tax_parameters/annual_cy_2024-06.csv":
        "c2981a8341e617ba1144cf6c9fab739b0931be40985d626e26dfaaabfa67233f",
    "data/budget/tax_parameters/annual_cy_2025-01.csv":
        "1fb2479edd7e915765a1af9f26c3c59f12d5df9a866274b2e19ec78359353388",
    "data/budget/tax_parameters/annual_cy_2026-02.csv":
        "528f588a15f6aad7f6a31a1619f843ac4805e4301a35bd24abc22bb5a8d43d4d",
}

#: Identities checked on every run, before anything is written. Each is a
#: statement about the LAW that must hold in the transcription, so a silently
#: re-tagged upstream file fails loudly rather than rewriting the schedule.
#:
#: The reversion checks are the point of the whole lane and are asserted on the
#: two vintages whose current law contains it: February 2024 and January 2025
#: are pre-OBBBA and revert in CY2026; February 2026 is post-P.L. 119-21 and
#: does not.
REVERTS_IN_2026 = ("cbo_feb_2024", "cbo_jan_2025")
PERMANENT_RATES = ("cbo_feb_2026",)

#: The seven statutory ordinary rates, in percent, on either side of CY2026.
TCJA_RATES = (10.0, 12.0, 22.0, 24.0, 32.0, 35.0, 37.0)
PRE_TCJA_RATES = (10.0, 15.0, 25.0, 28.0, 33.0, 35.0, 39.6)

FILING_SUFFIXES = ("single", "mfj", "mfs", "hoh")


def _raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/US-CBO/cbo-data/{REPO_COMMIT}/{path}"


def read_source(path: str, source_dir: Path | None) -> tuple[str, str]:
    """Return one pinned file's text and its SHA-256, verifying where recorded."""
    if source_dir is not None:
        raw = (source_dir / "cbo-data" / path).read_bytes()
    else:
        with urllib.request.urlopen(_raw_url(path), timeout=120) as fh:
            raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = DIGESTS.get(path)
    if recorded is not None and digest != recorded:
        raise SystemExit(
            f"SHA-256 mismatch for {path}\n  recorded {recorded}\n  read     {digest}\n"
            "The pinned commit's file changed, or the wrong file was read. "
            "Nothing was written."
        )
    DIGESTS[path] = digest
    return raw.decode("utf-8-sig"), digest


def _long_rows(text: str) -> list[dict]:
    """Parse CBO's ``date,variable,value`` long format, dropping blank values."""
    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("value") or "").strip()
        if not value:
            continue
        raw_year = (row.get("date") or "").strip()
        year = int(raw_year[2:]) if raw_year.upper().startswith("CY") else int(raw_year)
        out.append(
            {"calendar_year": year, "variable": row["variable"], "value": float(value)}
        )
    return out


def transcribe(source_dir: Path | None) -> tuple[list[dict], list[dict], list[str]]:
    rows: list[dict] = []
    provenance: list[dict] = []
    notes: list[str] = []

    for vintage, spec in VINTAGES.items():
        path = f"data/budget/tax_parameters/annual_cy_{spec['edition']}.csv"
        text, digest = read_source(path, source_dir)
        parsed = _long_rows(text)
        for row in parsed:
            rows.append({"vintage": vintage, **row})

        variables = {row["variable"] for row in parsed}
        years = sorted({row["calendar_year"] for row in parsed})
        missing = [
            f"tp_bracket_{i}_{s}"
            for i in range(1, 8)
            for s in FILING_SUFFIXES
            if f"tp_bracket_{i}_{s}" not in variables
        ]
        if missing:
            notes.append(f"{vintage}: bracket series absent: {', '.join(missing)}")

        provenance.append(
            {
                "vintage": vintage,
                "edition": spec["edition"],
                "match": spec["match"],
                "repository": REPO_URL,
                "file_path": path,
                "commit_sha": REPO_COMMIT,
                "sha256": digest,
                "fetch_date": FETCH_DATE,
                "rows": len(parsed),
                "variables": len(variables),
                "first_year": years[0] if years else "",
                "last_year": years[-1] if years else "",
                "publication": spec["publication"],
                "note": spec["note"],
            }
        )

    return rows, provenance, notes


def _index(rows: list[dict]) -> dict[tuple[str, str, int], float]:
    return {(r["vintage"], r["variable"], r["calendar_year"]): r["value"] for r in rows}


def check_identities(rows: list[dict]) -> list[str]:
    """Statements about the law that must hold in what was just read."""
    problems: list[str] = []
    table = _index(rows)

    def value(vintage: str, variable: str, year: int) -> float | None:
        return table.get((vintage, variable, year))

    for vintage in VINTAGES:
        # Bracket 1's floor is $0 in every year and every status. The two
        # bracket-1 validation rows depend on it, and a non-zero value would
        # move a row that must not move.
        for status in FILING_SUFFIXES:
            values = [
                row["value"]
                for row in rows
                if row["vintage"] == vintage and row["variable"] == f"tp_bracket_1_{status}"
            ]
            if not values:
                problems.append(f"{vintage}: tp_bracket_1_{status} absent")
            elif any(value != 0.0 for value in values):
                problems.append(
                    f"{vintage}: tp_bracket_1_{status} is not 0 in every year"
                )

        # Brackets ascend within each year and status.
        years = sorted(
            {row["calendar_year"] for row in rows if row["vintage"] == vintage}
        )
        for year in years:
            for status in FILING_SUFFIXES:
                floors = [
                    value(vintage, f"tp_bracket_{i}_{status}", year)
                    for i in range(1, 8)
                ]
                if any(f is None for f in floors):
                    continue
                if any(a >= b for a, b in zip(floors, floors[1:])):
                    problems.append(
                        f"{vintage} CY{year} {status}: bracket floors do not ascend"
                    )

    # The reversion, on the two vintages whose current law contains it.
    for vintage in REVERTS_IN_2026:
        before = tuple(value(vintage, f"tp_rate_{i}", 2025) for i in range(1, 8))
        after = tuple(value(vintage, f"tp_rate_{i}", 2026) for i in range(1, 8))
        if before != TCJA_RATES:
            problems.append(f"{vintage}: CY2025 rates {before} are not the TCJA schedule")
        if after != PRE_TCJA_RATES:
            problems.append(
                f"{vintage}: CY2026 rates {after} are not the pre-TCJA schedule - "
                "this vintage's current law is supposed to revert"
            )

    for vintage in PERMANENT_RATES:
        before = tuple(value(vintage, f"tp_rate_{i}", 2025) for i in range(1, 8))
        after = tuple(value(vintage, f"tp_rate_{i}", 2026) for i in range(1, 8))
        if before != after:
            problems.append(
                f"{vintage}: rates change at CY2026 ({before} -> {after}) - this "
                "vintage is post-P.L. 119-21 and is supposed to be permanent"
            )

    return problems


_HEADER = """\
# CBO's own STATUTORY TAX PARAMETER SCHEDULE, by calendar year, by vintage.
#
# Generated by scripts/fetch_cbo_tax_parameters.py. Do not hand-edit: rerun the
# script, which verifies each source file's SHA-256 against a pinned commit and
# re-checks the statutory identities before writing anything.
#
# Source of record: {repo} at commit {commit} ({commit_date}),
# file data/budget/tax_parameters/annual_cy_<edition>.csv, one edition per
# vintage. CBO publication 53724, "Tax Parameters and Effective Marginal Tax
# Rates". Public domain (17 U.S.C. 105).
#
# Transcribed VERBATIM - every variable CBO publishes, not a subset - so that
# the relationship between this file and the upstream one is checkable rather
# than asserted. Most of these series are wired to nothing today; see
# fiscal_model/cbo_tax_parameters.py for what reads which.
#
# Per-vintage provenance, including which vintages are an exact edition match
# and which are not, is in PROVENANCE.csv beside this file.
"""


def write_csv(path: Path, header: str, rows: list[dict], fields: list[str]) -> None:
    buf = io.StringIO()
    buf.write(header)
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_text(buf.getvalue(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify sources and identities; write nothing")
    parser.add_argument("--source-dir", type=Path, default=None,
                        help="read clones from this directory instead of fetching")
    args = parser.parse_args(argv)

    rows, provenance, notes = transcribe(args.source_dir)
    problems = check_identities(rows)

    for note in notes:
        print(f"  note: {note}")
    for problem in problems:
        print(f"  PROBLEM: {problem}")

    if problems:
        print(f"\n{len(problems)} identity problem(s); nothing written.")
        return 1

    print(f"\nparameter rows {len(rows)}")
    for entry in provenance:
        print(
            f"  {entry['vintage']:14s} {entry['edition']}  {entry['match']:15s} "
            f"{entry['variables']:3d} vars  CY{entry['first_year']}-CY{entry['last_year']}  "
            f"{entry['sha256'][:12]}"
        )

    if args.check:
        print("\n--check: verified, nothing written.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT_DIR / "cbo_tax_parameters.csv",
        _HEADER.format(repo=REPO_URL, commit=REPO_COMMIT, commit_date=REPO_COMMIT_DATE),
        rows,
        ["vintage", "calendar_year", "variable", "value"],
    )
    write_csv(
        OUT_DIR / "PROVENANCE.csv",
        "# One row per vintage: which CBO edition was read, and whether it is\n"
        "# that vintage's own edition or the nearest published one.\n"
        f"# Written by scripts/fetch_cbo_tax_parameters.py on {date.today().isoformat()}.\n",
        provenance,
        ["vintage", "edition", "match", "repository", "file_path", "commit_sha",
         "sha256", "fetch_date", "rows", "variables", "first_year", "last_year",
         "publication", "note"],
    )
    print(f"\nwrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
