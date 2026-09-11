#!/usr/bin/env python3
"""
Transcribe CBO's own baseline tables from CBO's own GitHub organisation.

WHY THIS SCRIPT EXISTS
----------------------
``fiscal_model/baseline.py`` used to say, in as many words, that the fix for
its reconstructed vintages was "a data edit - a block in the CSV - not a code
change", and that the edit could not be made because *"cbo.gov returns HTTP 403
to this environment and the Wayback Machine holds no snapshot of the January
2025 or February 2026 budget projections workbooks."*

That is true of ``cbo.gov``. It is not true of ``github.com/US-CBO``, which is
not blocked and which carries the same tables as machine-readable CSV under a
public-domain dedication. This script is that data edit.

WHAT IT READS
-------------
Two repositories, both pinned by commit SHA and verified by SHA-256 of the file
actually read (owner decision (10): both count as "CBO's own table"):

* ``US-CBO/cbo-data`` - ``data/budget/ten_year_budget/annual_fy_{vintage}.csv``
  (the ten-year budget path, one row per variable per fiscal year) and
  ``data/economic/economic_projections/fiscal_{vintage}.csv`` (the fiscal-year
  economic forecast behind it).
* ``US-CBO/budgetary-feedback-model`` - ``input/budget_baseline.csv``, used only
  as a **cross-check** on the February 2026 figures, never as a source of
  record, because ``cbo-data`` carries the same vintage in more detail.

WHAT IT WRITES
--------------
``fiscal_model/data_files/cbo_baseline/cbo_budget_baseline.csv`` and
``cbo_economic_baseline.csv``, both long-format
(``vintage,fiscal_year,variable,value``) with a provenance header naming the
repository, file path, commit SHA, SHA-256 and fetch date per vintage, and
``PROVENANCE.csv``, the machine-readable form of that header which
``fiscal_model/baseline.py`` reads to grade each vintage.

WHAT IT DOES NOT DO
-------------------
It does not invent a February 2024 *budget* table. ``cbo-data``'s
``ten_year_budget`` carries ``2024-06``, ``2025-01`` and ``2026-02``; the
February 2024 edition (publication 59710) is not among them, and June 2024 is a
different publication with different numbers. February 2024's *economic* path
**is** published (``economic_projections/fiscal_2024-02.csv``) and is
transcribed; its budget levels stay the reconstruction they were, and
:data:`fiscal_model.baseline.VINTAGE_SOURCING` says so per line rather than
claiming one grade for the vintage as a whole.

USAGE
-----
    python scripts/fetch_cbo_baseline.py                 # verify, rewrite
    python scripts/fetch_cbo_baseline.py --check         # verify only, no write
    python scripts/fetch_cbo_baseline.py --source-dir D  # read clones under D

With no ``--source-dir`` the script fetches each pinned file over HTTPS from
``raw.githubusercontent.com``. Every fetch is checked against the SHA-256
recorded below, so a silently re-tagged file fails loudly instead of rewriting
the repository's baseline.
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
OUT_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "cbo_baseline"

#: Date the pinned commits below were fetched and their digests recorded.
FETCH_DATE = "2026-09-11"

#: Pinned commits. A commit SHA, not a branch: CBO re-publishes these files
#: each time it issues a baseline, and a lane that re-ran this script against
#: ``main`` would silently swap one vintage's numbers for another's.
REPOS = {
    "cbo-data": {
        "url": "https://github.com/US-CBO/cbo-data",
        "commit": "284a95665f9f2f74ed1f482feb629b43fce323da",
        "commit_date": "2026-06-12",
    },
    "budgetary-feedback-model": {
        "url": "https://github.com/US-CBO/budgetary-feedback-model",
        "commit": "9b4dd54e42c13bf9ee9ef67d63fc41ab64a3217e",
        "commit_date": "2026-07-13",
    },
}

#: The app's vintage ids mapped to CBO's own edition tags and publications.
#:
#: ``budget`` is ``None`` where ``cbo-data``'s ``ten_year_budget`` carries no
#: file for that edition. February 2024 is the one such case and it is not an
#: oversight: the repository ships ``2024-06``, which is *An Update to the
#: Budget and Economic Outlook* (publication 60039), a different document with
#: different numbers. Borrowing it would be a false provenance claim of exactly
#: the kind :data:`fiscal_model.baseline.VINTAGE_SOURCING` exists to prevent.
VINTAGES = {
    "cbo_feb_2024": {
        "edition": "2024-02",
        "budget": None,
        "economic": "2024-02",
        "publication": (
            "CBO, The Budget and Economic Outlook: 2024 to 2034 "
            "(February 2024), publication 59710"
        ),
        "budget_note": (
            "cbo-data/data/budget/ten_year_budget carries 2024-06, 2025-01 and "
            "2026-02 only; the February 2024 edition is not published there and "
            "June 2024 (pub. 60039) is a different document. Budget levels for "
            "this vintage remain this module's reconstruction."
        ),
    },
    "cbo_jan_2025": {
        "edition": "2025-01",
        "budget": "2025-01",
        "economic": "2025-01",
        "publication": (
            "CBO, The Budget and Economic Outlook: 2025 to 2035 "
            "(January 2025), publication 61172"
        ),
        "budget_note": "",
    },
    "cbo_feb_2026": {
        "edition": "2026-02",
        "budget": "2026-02",
        "economic": "2026-02",
        "publication": (
            "CBO, The Budget and Economic Outlook: 2026 to 2036 "
            "(February 2026), publication 51118 data release"
        ),
        "budget_note": "",
    },
}

#: SHA-256 of each pinned source file, recorded on ``FETCH_DATE``.
DIGESTS = {
    "cbo-data/data/budget/ten_year_budget/annual_fy_2025-01.csv":
        "076faf484f8c7ebeb59042323ecef5875d8e4830f85336958b3112a5fc7e6c69",
    "cbo-data/data/budget/ten_year_budget/annual_fy_2026-02.csv":
        "c1c3f7f62d481aba1d26f0e30b673796b82a76beda3ae40a5a807ec17b550b31",
    "cbo-data/data/economic/economic_projections/fiscal_2024-02.csv":
        "0814e9a029d6e75b8e2d92993f4b297ce6ea49b51ef127e250f99b1115e12126",
    "cbo-data/data/economic/economic_projections/fiscal_2025-01.csv":
        "4324a5989c0b52c473a70f8e407e395b746c93c0e50ddf88c77559edcc6acdc1",
    "cbo-data/data/economic/economic_projections/fiscal_2026-02.csv":
        "b5b2412a84434711a485bfb6fe4056e14139064c3c9fce731e49e33153cfd016",
    "budgetary-feedback-model/input/budget_baseline.csv":
        "6d646f4cbfe770a6ba35c397458fb338c8b046579bb1e6019024f5e5fa173a7a",
}

# ----------------------------------------------------------------- variables

#: Budget lines transcribed, keyed by the ``BaselineProjection`` attribute each
#: one populates. Each value is a list of alternative CBO variable names, tried
#: in order: CBO renames series between editions and publishes some of them only
#: in their timing-adjusted form (January 2025 carries
#: ``proj_mand_medicare_timing_adj`` but not ``proj_mand_medicare``). The first
#: name present wins, and :func:`transcribe_budget` records which one was used.
BUDGET_VARIABLES: dict[str, list[str]] = {
    "individual_income_tax": ["proj_rev_individual_income"],
    "corporate_income_tax": ["proj_rev_corporate_income"],
    "payroll_taxes": ["proj_rev_payroll"],
    # February 2026 splits customs duties out of "other"; earlier editions do
    # not. Both components are transcribed where present and the loader adds
    # whichever exist, so ``total_revenues`` reproduces CBO's ``proj_rev_total``
    # either way.
    "other_revenues_core": ["proj_rev_other"],
    "other_revenues_customs": ["proj_rev_customs"],
    "social_security_gross": [
        "proj_mand_social_security", "proj_mand_social_security_timing_adj"
    ],
    "social_security_offset": [
        "proj_offset_social_security", "proj_offset_social_security_timing_adj"
    ],
    "medicare_gross": ["proj_mand_medicare", "proj_mand_medicare_timing_adj"],
    "medicare_offset": ["proj_offset_medicare", "proj_offset_medicare_timing_adj"],
    "medicaid": ["proj_mand_medicaid", "proj_mand_medicaid_timing_adj"],
    "discretionary_total": ["proj_outlays_discretionary"],
    # Composition only. January 2025 publishes the defence/nondefence split of
    # *outlays* in its timing-adjusted form alone, and a timing-adjusted pair
    # does not sum to the unadjusted total in a year where October 1 falls on a
    # weekend - FY2024, 2028, 2029, 2033 and 2035 miss by $5-7B each. So the
    # split is taken as a SHARE of ``discretionary_total`` and never as a
    # level, the same "take the composition, apportion onto the published
    # total" rule PR #127 applied to IRS SOI Table 1.2. Where CBO publishes the
    # unadjusted split (February 2026) the rescaling is the identity.
    "defense_share": ["proj_disc_defense", "proj_disc_defense_outlays_timing_adj"],
    "nondefense_share": [
        "proj_disc_nondefense", "proj_disc_nondefense_outlays_timing_adj"
    ],
    "net_interest": ["proj_outlays_net_interest"],
    "debt_held_by_public": [
        "proj_debt_held_by_public_end", "proj_debt_held_by_public"
    ],
    # CBO's own printed totals. The model's categories are built from the
    # components above, but ``other_mandatory`` is a RESIDUAL against these, so
    # that ``total_outlays`` and therefore ``deficit`` reproduce CBO's own
    # figures to the rounding of the source whatever basis a component was
    # published on. Where a component is timing-adjusted and the total is not,
    # the residue lands in ``other_mandatory`` and PROVENANCE.csv says so.
    "revenues_total": ["proj_rev_total"],
    "outlays_total": ["proj_outlays_total"],
    "deficit_total": ["proj_deficit_total"],
}


#: Economic series transcribed, keyed by the name ``baseline.py`` uses.
ECONOMIC_VARIABLES: dict[str, list[str]] = {
    "nominal_gdp": ["gdp"],
    "real_gdp": ["real_gdp"],
    "real_gdp_growth": ["real_gdp_pct_change"],
    "inflation": ["pce_price_index_pct_change"],
    "unemployment": ["unemployment_rate"],
    "interest_rate_10yr": ["treasury_note_rate_10yr"],
    "labor_force_participation": ["lfpr_16yo"],
    "wages_and_salaries": ["wages_and_salaries"],
}

#: Series CBO prints as percentages that this repository stores as fractions.
PERCENT_SERIES = {
    "real_gdp_growth",
    "inflation",
    "unemployment",
    "interest_rate_10yr",
    "labor_force_participation",
}


# ----------------------------------------------------------------- fetching


def _raw_url(repo: str, path: str) -> str:
    commit = REPOS[repo]["commit"]
    return f"https://raw.githubusercontent.com/US-CBO/{repo}/{commit}/{path}"


def read_source(repo: str, path: str, source_dir: Path | None) -> str:
    """Return one pinned file's text, verifying its SHA-256 where recorded."""
    key = f"{repo}/{path}"
    if source_dir is not None:
        raw = (source_dir / repo / path).read_bytes()
    else:
        with urllib.request.urlopen(_raw_url(repo, path), timeout=120) as fh:
            raw = fh.read()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = DIGESTS.get(key)
    if recorded is not None and digest != recorded:
        raise SystemExit(
            f"SHA-256 mismatch for {key}\n  recorded {recorded}\n  read     {digest}\n"
            "The pinned commit's file changed, or the wrong file was read. "
            "Nothing was written."
        )
    DIGESTS[key] = digest
    return raw.decode("utf-8-sig")


def _long_rows(text: str) -> dict[str, dict[int, float]]:
    """Parse CBO's ``date,variable,value`` long format into ``{var: {year: v}}``."""
    table: dict[str, dict[int, float]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        value = (row.get("value") or "").strip()
        if not value:
            continue
        raw_year = (row.get("date") or "").strip()
        year = int(raw_year[2:]) if raw_year.upper().startswith("FY") else int(raw_year)
        table.setdefault(row["variable"], {})[year] = float(value)
    return table


def _pick(table: dict[str, dict[int, float]], names: list[str]) -> tuple[str, dict[int, float]] | None:
    for name in names:
        if name in table:
            return name, table[name]
    return None


# ------------------------------------------------------------- transcription


def transcribe(source_dir: Path | None) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    budget_rows: list[dict] = []
    econ_rows: list[dict] = []
    provenance: list[dict] = []
    notes: list[str] = []

    for vintage, spec in VINTAGES.items():
        # --- economic path (published for all three editions) ---------------
        econ_path = f"data/economic/economic_projections/fiscal_{spec['economic']}.csv"
        econ = _long_rows(read_source("cbo-data", econ_path, source_dir))
        used_econ = []
        for attr, names in ECONOMIC_VARIABLES.items():
            picked = _pick(econ, names)
            if picked is None:
                notes.append(f"{vintage}: economic series {names} absent")
                continue
            name, series = picked
            used_econ.append(f"{attr}={name}")
            scale = 0.01 if attr in PERCENT_SERIES else 1.0
            for year, value in sorted(series.items()):
                econ_rows.append({
                    "vintage": vintage,
                    "fiscal_year": year,
                    "variable": attr,
                    "value": round(value * scale, 8),
                    "cbo_variable": name,
                })
        provenance.append({
            "vintage": vintage,
            "kind": "economic",
            "repository": REPOS["cbo-data"]["url"],
            "file_path": econ_path,
            "commit_sha": REPOS["cbo-data"]["commit"],
            "sha256": DIGESTS[f"cbo-data/{econ_path}"],
            "fetch_date": FETCH_DATE,
            "publication": spec["publication"],
            "note": "; ".join(used_econ),
        })

        # --- budget path (February 2024 has none; see VINTAGES) --------------
        if spec["budget"] is None:
            provenance.append({
                "vintage": vintage,
                "kind": "budget",
                "repository": "",
                "file_path": "",
                "commit_sha": "",
                "sha256": "",
                "fetch_date": FETCH_DATE,
                "publication": spec["publication"],
                "note": spec["budget_note"],
            })
            notes.append(f"{vintage}: no budget table published on CBO's GitHub")
            continue

        bud_path = f"data/budget/ten_year_budget/annual_fy_{spec['budget']}.csv"
        bud = _long_rows(read_source("cbo-data", bud_path, source_dir))
        used_bud = []
        for attr, names in BUDGET_VARIABLES.items():
            picked = _pick(bud, names)
            if picked is None:
                notes.append(f"{vintage}: budget series {names} absent")
                continue
            name, series = picked
            used_bud.append(f"{attr}={name}")
            for year, value in sorted(series.items()):
                budget_rows.append({
                    "vintage": vintage,
                    "fiscal_year": year,
                    "variable": attr,
                    "value": round(value, 6),
                    "cbo_variable": name,
                })
        _apportion_discretionary(budget_rows, vintage)
        provenance.append({
            "vintage": vintage,
            "kind": "budget",
            "repository": REPOS["cbo-data"]["url"],
            "file_path": bud_path,
            "commit_sha": REPOS["cbo-data"]["commit"],
            "sha256": DIGESTS[f"cbo-data/{bud_path}"],
            "fetch_date": FETCH_DATE,
            "publication": spec["publication"],
            "note": "; ".join(used_bud),
        })

    return budget_rows, econ_rows, provenance, notes


def _apportion_discretionary(rows: list[dict], vintage: str) -> None:
    """Turn the defence/nondefence *shares* into levels on CBO's own total.

    ``defense_share`` and ``nondefense_share`` arrive as whatever CBO published
    - unadjusted levels in February 2026, timing-adjusted ones in January 2025.
    Only their ratio is kept; the level comes from ``discretionary_total``,
    which is unadjusted in every edition. Where CBO publishes both unadjusted
    this is the identity, to the cent.
    """
    by_year: dict[int, dict[str, dict]] = {}
    for row in rows:
        if row["vintage"] != vintage:
            continue
        by_year.setdefault(row["fiscal_year"], {})[row["variable"]] = row

    for row in by_year.values():
        total = row.get("discretionary_total")
        dfn, ndf = row.get("defense_share"), row.get("nondefense_share")
        if total is None or dfn is None or ndf is None:
            continue
        split = dfn["value"] + ndf["value"]
        if split <= 0:
            continue
        scale = total["value"] / split
        dfn["variable"], ndf["variable"] = "defense_discretionary", "nondefense_discretionary"
        dfn["value"] = round(dfn["value"] * scale, 6)
        ndf["value"] = round(ndf["value"] * scale, 6)
        if abs(scale - 1.0) > 1e-9:
            dfn["cbo_variable"] += " (apportioned onto proj_outlays_discretionary)"
            ndf["cbo_variable"] += " (apportioned onto proj_outlays_discretionary)"


# ------------------------------------------------------------- falsification


def check_totals(budget_rows: list[dict]) -> list[str]:
    """CBO's own printed totals must come back out of what was transcribed.

    Three identities, each of which would catch a different transcription
    error: revenue components against ``proj_rev_total`` (a dropped customs
    column), the outlay build-up against ``proj_outlays_total`` (a gross line
    used where a net one was meant), and the discretionary split against its
    own total (a timing-adjusted half paired with an unadjusted one).
    """
    by = {}
    for r in budget_rows:
        by.setdefault((r["vintage"], r["fiscal_year"]), {})[r["variable"]] = r["value"]

    problems = []
    for (vintage, year), row in sorted(by.items()):
        def g(name, _row=row):
            return _row.get(name, 0.0)

        rev = (g("individual_income_tax") + g("corporate_income_tax")
               + g("payroll_taxes") + g("other_revenues_core")
               + g("other_revenues_customs"))
        if "revenues_total" in row and abs(rev - row["revenues_total"]) > 0.35:
            problems.append(
                f"{vintage} FY{year}: revenue components {rev:.1f} vs CBO "
                f"{row['revenues_total']:.1f}")

        # ``other_mandatory`` is a residual against CBO's own outlay total, so
        # the identity that matters is that every OTHER outlay line is smaller
        # than the total it is carved out of - a residual that came out
        # negative would mean a gross line had been read where a net one was
        # meant, which is the error this check exists to catch.
        named = (g("social_security_gross") + g("social_security_offset")
                 + g("medicare_gross") + g("medicare_offset") + g("medicaid"))
        residual = (row.get("outlays_total", 0.0) - g("discretionary_total")
                    - g("net_interest") - named)
        if "outlays_total" in row and residual < 0:
            problems.append(
                f"{vintage} FY{year}: other-mandatory residual {residual:.1f} is "
                f"negative (named mandatory {named:.1f})")

        disc = g("defense_discretionary") + g("nondefense_discretionary")
        if "discretionary_total" in row and abs(disc - row["discretionary_total"]) > 0.35:
            problems.append(
                f"{vintage} FY{year}: discretionary split {disc:.1f} vs CBO "
                f"{row['discretionary_total']:.1f}")

        if {"deficit_total", "outlays_total", "revenues_total"} <= row.keys():
            implied = row["outlays_total"] - row["revenues_total"]
            if abs(implied + row["deficit_total"]) > 0.35:
                problems.append(
                    f"{vintage} FY{year}: outlays-revenues {implied:.1f} vs CBO "
                    f"deficit {-row['deficit_total']:.1f}")
    return problems


def cross_check_bfm(budget_rows: list[dict], source_dir: Path | None) -> list[str]:
    """February 2026 against the same figures in a *second* CBO repository.

    ``budgetary-feedback-model/input/budget_baseline.csv`` is CBO's own
    February 2026 budget path in the model it feeds. It is never a source of
    record here - ``cbo-data`` carries the same edition in more detail - but
    two independent CBO files agreeing is the strongest available check that
    the right rows were read.
    """
    text = read_source("budgetary-feedback-model", "input/budget_baseline.csv", source_dir)
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return ["budgetary-feedback-model/input/budget_baseline.csv is empty"]

    fields = [f for f in rows[0] if f]
    year_field = fields[0]
    bfm: dict[int, dict[str, float]] = {}
    for row in rows:
        raw = (row.get(year_field) or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            continue
        bfm[int(digits)] = {
            k: float(v.replace(",", "")) for k, v in row.items()
            if k and k != year_field and (v or "").strip()
            not in ("", "NA", "nan")
        }

    ours = {}
    for r in budget_rows:
        if r["vintage"] == "cbo_feb_2026":
            ours.setdefault(r["fiscal_year"], {})[r["variable"]] = r["value"]

    # Match BFM's own column names loosely: its header is CBO's internal
    # shorthand and has changed between releases, so look for a column whose
    # name contains the tokens rather than assuming one spelling.
    def find(*tokens):
        for name in (bfm.get(next(iter(bfm), 0)) or {}):
            low = name.lower()
            if all(t in low for t in tokens):
                return name
        return None

    problems = []
    pairs = [
        ("individual_income_tax", find("individual")),
        ("corporate_income_tax", find("corporate")),
        ("payroll_taxes", find("payroll")),
        ("net_interest", find("interest")),
    ]
    for attr, col in pairs:
        if col is None:
            problems.append(f"BFM cross-check: no column matching {attr}")
            continue
        for year in sorted(set(ours) & set(bfm)):
            a, b = ours[year].get(attr), bfm[year].get(col)
            if a is None or b is None:
                continue
            if abs(a - b) > max(1.0, abs(b) * 0.005):
                problems.append(
                    f"BFM cross-check FY{year} {attr}: cbo-data {a:.1f} vs BFM {b:.1f}")
    return problems


# ------------------------------------------------------------------ writing

_BUDGET_HEADER = """\
# CBO's own TEN-YEAR BUDGET BASELINE, by fiscal year, by vintage.
#
# Generated by scripts/fetch_cbo_baseline.py. Do not hand-edit: rerun the
# script, which verifies each source file's SHA-256 against a pinned commit
# before writing anything.
#
# Source of record: {repo} at commit {commit} ({commit_date}),
# file data/budget/ten_year_budget/annual_fy_<edition>.csv. Per-vintage
# repository, path, commit, SHA-256 and fetch date are in PROVENANCE.csv.
#
# Units: BILLIONS of dollars, as CBO prints them. Offsetting receipts
# ("*_offset") are NEGATIVE, as CBO prints them, so a net program level is
# gross + offset.
#
# NOT A CBO PRODUCT. This is a transcription of CBO data; CBO has not
# reviewed it. CBO's own files are public domain (US-CBO/cbo-data LICENSE).
"""

_ECON_HEADER = """\
# CBO's own FISCAL-YEAR ECONOMIC FORECAST, by vintage.
#
# Generated by scripts/fetch_cbo_baseline.py. Do not hand-edit.
#
# Source of record: {repo} at commit {commit} ({commit_date}),
# file data/economic/economic_projections/fiscal_<edition>.csv.
#
# FISCAL year, not calendar: every budget quantity in this repository is on a
# fiscal-year basis, and CBO publishes the forecast both ways. The calendar
# table is data/economic/economic_projections/calendar_<edition>.csv and is
# deliberately NOT read here - mixing the two would make a ratio between two
# years mean something different at each end.
#
# Units: nominal_gdp, real_gdp and wages_and_salaries in BILLIONS of dollars.
# real_gdp_growth, inflation, unemployment, interest_rate_10yr and
# labor_force_participation are FRACTIONS (CBO prints them as percentages;
# this file divides by 100 so the values drop straight into
# fiscal_model.baseline.EconomicAssumptions).
#
# NOT A CBO PRODUCT. CBO's own files are public domain.
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

    budget_rows, econ_rows, provenance, notes = transcribe(args.source_dir)

    problems = check_totals(budget_rows)
    try:
        problems += cross_check_bfm(budget_rows, args.source_dir)
    except Exception as exc:  # a cross-check, not a source of record
        notes.append(f"BFM cross-check unavailable: {exc}")

    for note in notes:
        print(f"  note: {note}")
    for problem in problems:
        print(f"  PROBLEM: {problem}")

    if problems:
        print(f"\n{len(problems)} identity problem(s); nothing written.")
        return 1

    print(f"\nbudget rows {len(budget_rows)}  economic rows {len(econ_rows)}")
    for p in provenance:
        print(f"  {p['vintage']:14s} {p['kind']:9s} "
              f"{p['file_path'] or '(none published)'} "
              f"{(p['sha256'] or '')[:12]}")

    if args.check:
        print("\n--check: verified, nothing written.")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = dict(repo=REPOS["cbo-data"]["url"], commit=REPOS["cbo-data"]["commit"],
                commit_date=REPOS["cbo-data"]["commit_date"])
    write_csv(OUT_DIR / "cbo_budget_baseline.csv", _BUDGET_HEADER.format(**meta),
              budget_rows, ["vintage", "fiscal_year", "variable", "value", "cbo_variable"])
    write_csv(OUT_DIR / "cbo_economic_baseline.csv", _ECON_HEADER.format(**meta),
              econ_rows, ["vintage", "fiscal_year", "variable", "value", "cbo_variable"])
    write_csv(
        OUT_DIR / "PROVENANCE.csv",
        "# One row per vintage per kind: where the numbers came from.\n"
        f"# Written by scripts/fetch_cbo_baseline.py on {date.today().isoformat()}.\n",
        provenance,
        ["vintage", "kind", "repository", "file_path", "commit_sha", "sha256",
         "fetch_date", "publication", "note"],
    )
    print(f"\nwrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
