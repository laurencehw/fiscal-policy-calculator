#!/usr/bin/env python3
"""
Transcribe CBO's own projection of the individual income tax base.

WHY THIS SCRIPT EXISTS
----------------------
The generic scoring path reads a dated IRS SOI base (tax year 2023) and projects
it onto each scored year with the vintage's **nominal GDP** index
(``BaselineProjection.nominal_income_index``). CBO does not project the base that
way: it projects adjusted gross income and taxable income themselves, and their
path departs from GDP wherever the law changes the base (the CY2026 TCJA
reversion in the 2024-06 and 2025-01 editions, P.L. 119-21 in 2026-02) or the
income mix moves (the CY2022 capital-gains fall).

``US-CBO/cbo-data`` ships those projections as machine-readable CSV under a
public-domain dedication: ``data/budget/revenue_detail/annual_cy_iit_{edition}.csv``
(CBO's *Revenue Projections, by Category*, Individual Income Tax Details), on the
same three editions ``scripts/fetch_cbo_tax_parameters.py`` reads. Lane B2a
(``planning/lanes/B2a_cbo_income_path.md``) wires two of its series into the
base projection; this script only transcribes them.

WHAT IT READS
-------------
One repository, pinned by commit SHA (the same commit the baseline and the
tax-parameter transcriptions pin) and verified by SHA-256 of the **bytes
raw.githubusercontent.com serves**, never of a working-tree copy (see PR #167
and ``scripts/fetch_cbo_baseline.py``: a Windows checkout with
``core.autocrlf=true`` rewrites every line and every digest with it).

WHAT IT WRITES
--------------
* ``fiscal_model/data_files/cbo_income_detail/cbo_income_detail.csv``, long
  format (``vintage,calendar_year,variable,value``), **verbatim**: every variable
  CBO publishes, not a chosen subset.
* ``PROVENANCE.csv``, one row per vintage, with the edition read and its match
  grade.
* ``sources/cbo-data/...``, the served bytes themselves, marked ``-text`` in
  ``sources/.gitattributes`` so ``--offline-check`` can verify every pin on every
  CI run without a network.

THE ONE SUBSTITUTION, GRADED RATHER THAN HIDDEN
-----------------------------------------------
``cbo-data``'s oldest ``revenue_detail`` edition is ``2024-06``. The app's
``cbo_feb_2024`` vintage - the one every CBO Options volume row is scored on,
including the 2018, 2020 and 2022 volumes - has no edition of its own, so it
reads ``2024-06`` and is graded ``nearest_vintage``, exactly as
``cbo_tax_parameters`` grades the same substitution. CBO's archived
publication 51138 editions for the older baselines were not reachable from the
lane's environment (cbo.gov refused the connection) and are not transcribed;
the rows that would read them say so in ``known_limitations``.

USAGE
-----
    python scripts/fetch_cbo_income_detail.py                  # fetch, verify, rewrite
    python scripts/fetch_cbo_income_detail.py --check          # fetch and verify only
    python scripts/fetch_cbo_income_detail.py --offline-check  # verify pins, no network
    python scripts/fetch_cbo_income_detail.py --source-dir D   # read a clone under D/cbo-data
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "cbo_income_detail"
SOURCE_CACHE = OUT_DIR / "sources"

#: Date the pinned files were fetched and their digests recorded.
FETCH_DATE = "2026-11-06"

REPO_URL = "https://github.com/US-CBO/cbo-data"
REPO_COMMIT = "284a95665f9f2f74ed1f482feb629b43fce323da"
REPO_COMMIT_DATE = "2026-06-12"

_PUBLICATION = "CBO, Revenue Projections, by Category: Individual Income Tax Details"

VINTAGES: dict[str, dict[str, str]] = {
    "cbo_feb_2024": {
        "edition": "2024-06",
        "match": "nearest_vintage",
        "publication": f"{_PUBLICATION}, June 2024 edition",
        "note": (
            "cbo-data/data/budget/revenue_detail carries 2024-06, 2025-01 and "
            "2026-02 only; there is no February 2024 edition. June 2024 is read "
            "instead, as cbo_tax_parameters does. The 2018, 2020 and 2022 CBO "
            "Options volumes are scored on this vintage too; their own baselines' "
            "income detail (CBO publication 51138 archives) is not transcribed. "
            "rev_iit_taxable_ordinary is absent from this edition."
        ),
    },
    "cbo_jan_2025": {
        "edition": "2025-01",
        "match": "exact",
        "publication": f"{_PUBLICATION}, January 2025 edition",
        "note": "",
    },
    "cbo_feb_2026": {
        "edition": "2026-02",
        "match": "exact",
        "publication": f"{_PUBLICATION}, February 2026 edition",
        "note": "",
    },
}

#: SHA-256 of the bytes raw.githubusercontent.com serves at the pinned commit.
#: An unpinned path is an error, never a new pin.
DIGESTS: dict[str, str] = {
    "data/budget/revenue_detail/annual_cy_iit_2024-06.csv":
        "6778eb60f376f54d2a745c56870fc2f09247bf024e2027c59738733cdc0a3e70",
    "data/budget/revenue_detail/annual_cy_iit_2025-01.csv":
        "62428a585f85a5a61bbd2573f7200934909dd512c191daac1bd1e1944b32ae55",
    "data/budget/revenue_detail/annual_cy_iit_2026-02.csv":
        "18fa9e57a67009f2c704659cae31eca382eb03a77a86eb7191bb9b313b2cccf6",
}

#: The two series lane B2a reads. Both must exist in every vintage.
REQUIRED_SERIES = ("rev_iit_agi", "rev_iit_taxable_income")


def _raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/US-CBO/cbo-data/{REPO_COMMIT}/{path}"


def _vendored(path: str) -> Path:
    return SOURCE_CACHE / "cbo-data" / path.replace("/", "__")


def read_source(path: str, source_dir: Path | None) -> bytes:
    """Return one pinned file's bytes, refusing any digest but the pinned one."""
    recorded = DIGESTS.get(path)
    if recorded is None:
        raise SystemExit(f"{path} is not pinned in DIGESTS; refusing to mint a pin.")
    if source_dir is not None:
        raw = (source_dir / "cbo-data" / path).read_bytes()
    else:
        with urllib.request.urlopen(_raw_url(path), timeout=120) as fh:
            raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != recorded:
        hint = (
            " The bytes contain CR characters: this looks like a working-tree copy "
            "converted by core.autocrlf, not the served file."
            if b"\r\n" in raw
            else ""
        )
        raise SystemExit(
            f"SHA-256 mismatch for {path}\n  pinned {recorded}\n  read   {digest}\n"
            f"Nothing was written.{hint}"
        )
    return raw


def _long_rows(text: str) -> list[dict]:
    """Parse CBO's ``date,variable,value,...`` long format, dropping blanks."""
    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("value") or "").strip()
        if not value:
            continue
        raw_year = (row.get("date") or "").strip()
        year = int(raw_year[2:]) if raw_year.upper().startswith("CY") else int(raw_year)
        out.append({"calendar_year": year, "variable": row["variable"], "value": float(value)})
    return out


def transcribe(raw_by_path: dict[str, bytes]) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    provenance: list[dict] = []
    for vintage, spec in VINTAGES.items():
        path = f"data/budget/revenue_detail/annual_cy_iit_{spec['edition']}.csv"
        parsed = _long_rows(raw_by_path[path].decode("utf-8-sig"))
        rows.extend({"vintage": vintage, **row} for row in parsed)
        variables = {row["variable"] for row in parsed}
        years = sorted({row["calendar_year"] for row in parsed})
        provenance.append(
            {
                "vintage": vintage,
                "edition": spec["edition"],
                "match": spec["match"],
                "repository": REPO_URL,
                "file_path": path,
                "commit_sha": REPO_COMMIT,
                "sha256": DIGESTS[path],
                "fetch_date": FETCH_DATE,
                "rows": len(parsed),
                "variables": len(variables),
                "first_year": years[0],
                "last_year": years[-1],
                "publication": spec["publication"],
                "note": spec["note"],
            }
        )
    return rows, provenance


def check_identities(rows: list[dict]) -> list[str]:
    """Accounting statements that must hold in what was just read."""
    problems: list[str] = []
    table = {(r["vintage"], r["variable"], r["calendar_year"]): r["value"] for r in rows}
    for vintage in VINTAGES:
        years = sorted({r["calendar_year"] for r in rows if r["vintage"] == vintage})
        for year in years:
            agi = table.get((vintage, "rev_iit_agi", year))
            taxable = table.get((vintage, "rev_iit_taxable_income", year))
            if agi is None or taxable is None:
                missing = [s for s in REQUIRED_SERIES if (vintage, s, year) not in table]
                problems.append(f"{vintage} CY{year}: {', '.join(missing)} absent")
                continue
            if not 0 < taxable < agi:
                problems.append(f"{vintage} CY{year}: taxable income not in (0, AGI)")
            brackets = [table.get((vintage, f"rev_iit_bracket_{k}", year)) for k in range(1, 8)]
            if any(b is None for b in brackets):
                continue
            total = sum(b for b in brackets if b is not None)
            if total >= taxable:
                problems.append(
                    f"{vintage} CY{year}: bracket income {total:.1f} is not below "
                    f"taxable income {taxable:.1f} (it excludes preferential income)"
                )
            ordinary = table.get((vintage, "rev_iit_taxable_ordinary", year))
            if ordinary is not None and abs(total - ordinary) > 0.001 * ordinary:
                problems.append(
                    f"{vintage} CY{year}: bracket income {total:.1f} does not sum "
                    f"to taxable ordinary income {ordinary:.1f}"
                )
    return problems


_HEADER = """\
# CBO projection of the individual income tax base, by calendar year.
# Written by scripts/fetch_cbo_income_detail.py - do not edit by hand; rerun the
# script, which verifies every source digest and accounting identity first.
#
# Source of record: {repo} at commit {commit} ({commit_date}),
# file data/budget/revenue_detail/annual_cy_iit_<edition>.csv, one edition per
# vintage. Public domain (17 U.S.C. 105). Transcribed VERBATIM (every variable).
# Lane B2a reads rev_iit_taxable_income and rev_iit_agi; see
# fiscal_model/cbo_income_detail.py. Per-vintage match grades: PROVENANCE.csv.
"""


def write_csv(path: Path, header: str, rows: list[dict], fields: list[str]) -> None:
    buf = io.StringIO()
    buf.write(header)
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="fetch and verify against the pins; write nothing")
    mode.add_argument("--offline-check", action="store_true",
                      help="verify the vendored copies and identities; no network")
    parser.add_argument("--source-dir", type=Path, default=None,
                        help="read a clone under this directory instead of fetching")
    args = parser.parse_args(argv)

    if args.check and args.source_dir is not None:
        raise SystemExit("--check asks what the pinned URLs serve; it cannot be "
                         "answered from a local tree.")

    raw_by_path: dict[str, bytes] = {}
    for path in DIGESTS:
        if args.offline_check:
            vendored = _vendored(path)
            raw = vendored.read_bytes() if vendored.exists() else b""
            digest = hashlib.sha256(raw).hexdigest()
            if digest != DIGESTS[path]:
                print(f"  PROBLEM: {vendored} hashes {digest}, pin says {DIGESTS[path]}")
                return 1
        else:
            raw = read_source(path, args.source_dir)
        raw_by_path[path] = raw

    rows, provenance = transcribe(raw_by_path)
    problems = check_identities(rows)
    for problem in problems:
        print(f"  PROBLEM: {problem}")
    if problems:
        print(f"\n{len(problems)} identity problem(s); nothing written.")
        return 1

    for entry in provenance:
        print(f"  {entry['vintage']:14s} {entry['edition']}  {entry['match']:15s} "
              f"{entry['variables']:3d} vars  CY{entry['first_year']}-CY{entry['last_year']}  "
              f"{entry['sha256'][:12]}")

    if args.check or args.offline_check:
        print(f"\nverified {len(DIGESTS)} pins and every identity; nothing written.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, raw in raw_by_path.items():
        target = _vendored(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    write_csv(
        OUT_DIR / "cbo_income_detail.csv",
        _HEADER.format(repo=REPO_URL, commit=REPO_COMMIT, commit_date=REPO_COMMIT_DATE),
        rows,
        ["vintage", "calendar_year", "variable", "value"],
    )
    write_csv(
        OUT_DIR / "PROVENANCE.csv",
        "# One row per vintage: which CBO edition was read, and whether it is\n"
        "# that vintage's own edition or the nearest published one.\n"
        f"# Written by scripts/fetch_cbo_income_detail.py; pins fetched {FETCH_DATE}.\n",
        provenance,
        ["vintage", "edition", "match", "repository", "file_path", "commit_sha",
         "sha256", "fetch_date", "rows", "variables", "first_year", "last_year",
         "publication", "note"],
    )
    print(f"\nwrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
