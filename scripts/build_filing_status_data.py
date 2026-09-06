#!/usr/bin/env python3
"""Rebuild the vendored IRS SOI Table 1.2 transcription.

Why this exists
---------------
Every income-tax threshold a scorekeeper publishes is stated *per filing
status* — CBO's Option 46 surtax at "$20,000 for single filers and $40,000 for
joint filers", the statutory brackets Option 45 raises, the four amounts the
Green Book prints for the top marginal rate. Until lane W7 the model had one
threshold and one pooled base, because the only SOI table it read (Table 1.1)
has no filing-status dimension.

**Table 1.2** does. It reports the same AGI size classes as Table 1.1, but split
five ways — all returns, joint (including surviving spouses), separate, heads of
households, single — with returns, AGI, itemised and standard deductions,
taxable income, income tax after credits and total income tax for each.

Source
------
IRS, Statistics of Income Division, *Individual Income Tax Returns Complete
Report* (Publication 1304), **Table 1.2, "All Returns: Adjusted Gross Income,
Deductions, and Tax Items, by Size of Adjusted Gross Income and by Filing
Status"**, tax year 2023 (filing year 2024), published March 2026.

* Landing page: https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics
* Workbook: https://www.irs.gov/pub/irs-soi/23in12ms.xls

Output
------
``fiscal_model/data_files/irs_soi/table_1_2_<year>.csv`` — a faithful dump of
the workbook's single sheet, cell for cell, in the same convention as the
``table_1_1_*.csv`` files already in that directory: the IRS's own multi-row
header block is preserved, nothing is renamed, and the loader
(:class:`fiscal_model.data.irs_soi.IRSSOIData`) finds its columns from the
sheet's own status headings rather than from hard-coded offsets.

The ``.xls`` itself is **not** tracked — ``.gitignore`` excludes ``*.xls`` — so
the CSV is the auditable artefact and the workbook is local provenance. Anyone
can re-download it and diff.

Usage
-----
    python scripts/build_filing_status_data.py                 # 2023
    python scripts/build_filing_status_data.py --year 2023
    python scripts/build_filing_status_data.py --xls path/to/23in12ms.xls

With no ``--xls`` the script looks for the workbook next to the CSVs and, only
if it is absent, downloads it from irs.gov.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from urllib.request import Request, urlopen

import xlrd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "fiscal_model" / "data_files" / "irs_soi"

SOI_TABLE_12_URL = "https://www.irs.gov/pub/irs-soi/{yy}in12ms.xls"
SOI_TABLE_12_FILENAME = "{yy}in12ms.xls"

#: Expected on the sheet's first cell, as a guard against a silent re-layout.
TITLE_MARKER = "Table 1.2"


def _workbook_path(year: int, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    yy = f"{year % 100:02d}"
    return OUT_DIR / SOI_TABLE_12_FILENAME.format(yy=yy)


def _download(year: int, destination: Path) -> None:
    yy = f"{year % 100:02d}"
    url = SOI_TABLE_12_URL.format(yy=yy)
    print(f"  downloading {url}")
    request = Request(url, headers={"User-Agent": "fiscal-policy-calculator/1.0"})
    with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed irs.gov host
        payload = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    print(f"  saved {len(payload):,} bytes to {destination}")


def _format(value, cell_type: int) -> str:
    """Render one workbook cell the way a Save-As-CSV would."""
    if cell_type == xlrd.XL_CELL_EMPTY:
        return ""
    if cell_type == xlrd.XL_CELL_NUMBER:
        number = float(value)
        if number.is_integer():
            return str(int(number))
        return repr(number)
    return str(value)


def transcribe(workbook_path: Path, out_path: Path) -> int:
    """Write the workbook's sheet to ``out_path``. Returns the row count."""
    book = xlrd.open_workbook(workbook_path)
    sheet = book.sheet_by_index(0)

    title = str(sheet.cell_value(0, 0))
    if TITLE_MARKER not in title:
        raise ValueError(
            f"{workbook_path.name} does not look like SOI Table 1.2 - "
            f"first cell reads {title!r}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row_index in range(sheet.nrows):
            writer.writerow(
                [
                    _format(sheet.cell_value(row_index, col), sheet.cell_type(row_index, col))
                    for col in range(sheet.ncols)
                ]
            )
    return sheet.nrows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2023, help="SOI tax year (default 2023)")
    parser.add_argument("--xls", type=Path, default=None, help="path to the Table 1.2 workbook")
    args = parser.parse_args()

    workbook_path = _workbook_path(args.year, args.xls)
    if not workbook_path.exists():
        _download(args.year, workbook_path)

    out_path = OUT_DIR / f"table_1_2_{args.year}.csv"
    rows = transcribe(workbook_path, out_path)
    print(f"  wrote {out_path.relative_to(REPO_ROOT)} ({rows} rows)")


if __name__ == "__main__":
    main()
