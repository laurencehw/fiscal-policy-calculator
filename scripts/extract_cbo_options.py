#!/usr/bin/env python3
"""
Rebuild the CBO *Options for Reducing the Deficit: 2025 to 2034* data files.

Source
------
Congressional Budget Office, *Options for Reducing the Deficit: 2025 to 2034*
(December 2024; reposted with updates October 2025), publication 60557.

* Landing page: https://www.cbo.gov/publication/60557
* PDF: https://www.cbo.gov/system/files/2024-12/60557-budget-options.pdf

Baseline the options are built on (PDF page 2, "Notes About This Report"):

* **Spending options** — CBO, *An Update to the Budget and Economic Outlook:
  2024 to 2034* (**June 2024**), publication 60039.
* **Revenue options** — CBO, *The Budget and Economic Outlook: 2024 to 2034*
  (**February 2024**), publication 59710.

Both are 2024 vintages. The repository carries ``BaselineVintage.CBO_FEB_2024``
but has no June-2024 vintage, so the spending options in the validation battery
are scored on Feb 2024 and the mismatch is recorded on each pre-registration
row (see ``fiscal_model/validation/preregistered.py``).

Outputs
-------
``fiscal_model/data_files/validation/cbo_options_2025_2034.csv``
    One row per option (76 rows), transcribed from **Table 1-1, "Projected
    Savings From Options for Reducing the Deficit"** (report pages 2-3 = PDF
    pages 8-9). Carries both sign conventions:

    * ``savings_*`` — CBO's own convention, **positive = reduces the deficit**.
    * ``deficit_effect_*`` — this app's convention, **positive = increases the
      deficit** (i.e. the negation of ``savings_*``).

``fiscal_model/data_files/validation/cbo_options_2025_2034_alternatives.csv``
    One row per *alternative* (or per reported line) inside an option's own
    table, with the 2025-2029 and 2025-2034 totals CBO publishes for it. This
    is the level at which the validation battery is scored: Table 1-1 reports a
    *range* whenever an option has several alternatives, and a range cannot be
    compared with a model score.

Every row carries ``extracted_by`` (``script`` or ``manual``) so a partial
extraction is visible in the data rather than silently filled in.

Usage
-----
    python scripts/extract_cbo_options.py --pdf path/to/60557-budget-options.pdf

``--pdf`` may be omitted if the PDF sits next to the CSVs as
``60557-budget-options.pdf``. Without a readable PDF the script refuses to
overwrite the committed CSVs (cbo.gov serves a bot challenge to plain HTTP
clients, so the download is a manual step).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUT_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "validation"
OPTIONS_CSV = OUT_DIR / "cbo_options_2025_2034.csv"
ALTERNATIVES_CSV = OUT_DIR / "cbo_options_2025_2034_alternatives.csv"

PUBLICATION = "CBO, Options for Reducing the Deficit: 2025 to 2034 (December 2024)"
PUBLICATION_URL = "https://www.cbo.gov/publication/60557"
PDF_URL = "https://www.cbo.gov/system/files/2024-12/60557-budget-options.pdf"
N_OPTIONS = 76

#: Baseline each chapter's options were scored against (PDF page 2).
BASELINE_BY_CATEGORY = {
    "mandatory": "CBO June 2024 baseline (An Update to the Budget and Economic Outlook: 2024 to 2034, pub. 60039)",
    "discretionary": "CBO June 2024 baseline (An Update to the Budget and Economic Outlook: 2024 to 2034, pub. 60039)",
    "revenue": "CBO February 2024 baseline (The Budget and Economic Outlook: 2024 to 2034, pub. 59710)",
}

#: Table 1-1's three section headers, in the order they appear.
_SECTION_HEADERS = (
    ("Mandatory Spending", "mandatory"),
    ("Discretionary Spending", "discretionary"),
    ("Revenues", "revenue"),
)

# Footnote markers CBO attaches to a savings figure in Table 1-1.
_FOOTNOTES = {
    "a": "For options affecting primarily mandatory spending or revenues, savings "
         "include effects on both mandatory spending and revenues; for discretionary "
         "options the savings shown are the decrease in discretionary outlays.",
    "b": "Savings do not encompass all budgetary effects.",
}


@dataclass
class OptionRow:
    """One row of Table 1-1."""

    option_number: int
    title: str
    category: str
    budget_area: str = ""
    savings_low_billions: float | None = None
    savings_high_billions: float | None = None
    footnote: str = ""
    report_page: int | None = None
    pdf_page: int | None = None
    extracted_by: str = "script"

    @property
    def has_range(self) -> bool:
        return (
            self.savings_low_billions is not None
            and self.savings_high_billions is not None
            and self.savings_low_billions != self.savings_high_billions
        )


@dataclass
class AlternativeRow:
    """One reported line inside an option's own table."""

    option_number: int
    alternative_id: str
    label: str
    measure: str
    savings_5yr_billions: float | None
    savings_10yr_billions: float | None
    report_page: int | None
    pdf_page: int | None
    extracted_by: str = "script"
    annual_savings_billions: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Normalise the mojibake pdfplumber leaves behind on this document."""
    replacements = {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "�": "'", " ": " ",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _to_float(token: str) -> float | None:
    """Parse a CBO table cell into a float; ``*`` and ``**`` mean ~zero."""
    token = token.strip().replace(",", "").replace("$", "")
    if token in {"*", "**", "n.a.", ""}:
        return 0.0
    try:
        return float(token)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Table 1-1
# ---------------------------------------------------------------------------

_TABLE_ROW_RE = re.compile(
    r"^(?P<num>\d{1,2})\s+(?P<rest>[A-Z\"'].*)$"
)
_SAVINGS_RE = re.compile(
    r"(?P<low>\d[\d,]*)(?:\s+to\s+(?P<high>\d[\d,]*))?\s*(?P<fn>[ab])?\s*$"
)


def parse_table_1_1(pages: list[str]) -> list[OptionRow]:
    """Parse Table 1-1 from the two PDF pages that carry it."""
    rows: list[OptionRow] = []
    category = ""
    pending: list[str] = []
    expected = 1

    for page in pages:
        for raw in page.splitlines():
            line = _clean(raw).strip()
            if not line:
                continue
            header = next(
                (cat for label, cat in _SECTION_HEADERS if line == label), None
            )
            if header:
                category = header
                pending = []
                continue
            if line.startswith(("Table 1-1", "Projected Savings", "Billions of dollars",
                                "Savings,", "Option Title", "Continued", "Data sources:",
                                "VA = ", "a. ", "b. ", "CHAPTER 1", "OPTIONS FOR REDUCING")):
                pending = []
                continue

            match = _TABLE_ROW_RE.match(line)
            if match and int(match.group("num")) == expected:
                pending = [match.group("rest")]
            elif pending:
                pending.append(line)
            else:
                continue

            blob = " ".join(pending)
            savings = _SAVINGS_RE.search(blob)
            if not savings:
                continue
            low = _to_float(savings.group("low"))
            high = _to_float(savings.group("high")) if savings.group("high") else low
            title = blob[: savings.start()].strip().rstrip(".")
            if not title:
                continue
            rows.append(
                OptionRow(
                    option_number=expected,
                    title=title,
                    category=category,
                    savings_low_billions=low,
                    savings_high_billions=high,
                    footnote=_FOOTNOTES.get(savings.group("fn") or "", ""),
                )
            )
            expected += 1
            pending = []

    return rows


# ---------------------------------------------------------------------------
# Table of contents (budget area + report page)
# ---------------------------------------------------------------------------

_TOC_RE = re.compile(r"^Option (?P<num>\d{1,2})\.\s+(?P<title>.*?)\s+(?P<page>\d{1,3})$")


def parse_contents(pages: list[str]) -> dict[int, tuple[str, int]]:
    """Map option number -> (budget area heading, report page) from the TOC."""
    out: dict[int, tuple[str, int]] = {}
    area = ""
    pending = ""
    for page in pages:
        for raw in page.splitlines():
            line = _clean(raw).strip()
            if not line:
                continue
            candidate = f"{pending} {line}".strip() if pending else line
            match = _TOC_RE.match(candidate)
            if match:
                out[int(match.group("num"))] = (area, int(match.group("page")))
                pending = ""
                continue
            if candidate.startswith("Option "):
                # Title wrapped onto the next line; keep accumulating.
                pending = candidate
                continue
            pending = ""
            if line in {"Mandatory Spending", "Discretionary Spending", "Revenues"}:
                continue
            if not any(ch.isdigit() for ch in line):
                area = line
    return out


# ---------------------------------------------------------------------------
# Per-option tables (alternatives)
# ---------------------------------------------------------------------------

_OPTION_HEADER_RE = re.compile(r"^Option (?P<num>\d{1,2})\s*[-—]+\s*(?P<kind>.+)$")
_NUM_TOKEN = r"(?:-?\d[\d,]*(?:\.\d+)?|\*+|0)"
_VALUE_TAIL_RE = re.compile(rf"(?:{_NUM_TOKEN})(?:\s+(?:{_NUM_TOKEN}))*$")

_MEASURE_LABELS = {
    "Budget authority": "budget_authority",
    "Spending authority": "spending_authority",
    "Outlays": "outlays",
    "Change in mandatory outlays": "mandatory_outlays",
}

_STOP_PREFIXES = (
    "Data source", "Data sources", "This option would take effect",
    "Related Option", "Related CBO", "Extended Discussion", "Note:", "Notes:",
    "* =", "** =", "a. ", "b. ", "n.a. ",
)

#: Section banners inside an option's table that label the *sign convention* or
#: the spending concept rather than an alternative. They carry no information
#: about which alternative a row belongs to, so they never enter a row label.
_BANNER_LINES = {
    "Decrease (-) in the deficit",
    "Increase (-) in the deficit",
    "Change in spending",
    "Change in discretionary spending",
    "Change in planned defense spending",
    "Change in mandatory spending",
    "Change in revenues",
}


def _split_values(line: str) -> tuple[str, list[float]]:
    """Split a table line into its label and its trailing numeric cells."""
    match = _VALUE_TAIL_RE.search(line)
    if match is None:
        return line.strip(), []
    label = line[: match.start()].strip()
    values = [_to_float(tok) for tok in match.group(0).split()]
    if any(v is None for v in values):
        return line.strip(), []
    return label, [v for v in values if v is not None]


def parse_option_tables(
    page_texts: list[str],
    contents: dict[int, tuple[str, int]],
    titles: dict[int, str],
) -> list[AlternativeRow]:
    """Extract every 12-cell data line from each option's own table."""
    rows: list[AlternativeRow] = []

    for index, raw_page in enumerate(page_texts):
        page = _clean(raw_page)
        header = None
        for line in page.splitlines():
            header = _OPTION_HEADER_RE.match(line.strip())
            if header:
                break
        if header is None:
            continue
        number = int(header.group("num"))
        if not 1 <= number <= N_OPTIONS:
            continue

        report_page = contents.get(number, ("", None))[1]
        pdf_page = index + 1

        started = False
        pending: list[str] = []
        section = ""
        seq = 0
        for raw_line in page.splitlines():
            line = _clean(raw_line).strip()
            if not line:
                continue
            if line.startswith("Billions of dollars"):
                started = True
                pending = []
                continue
            if not started:
                continue
            if line.startswith(_STOP_PREFIXES):
                break
            if line in _BANNER_LINES:
                continue

            label, values = _split_values(line)
            if len(values) != 12:
                # Not a data line. Keep the *whole* line — a wrapped alternative
                # label often ends in a dollar amount ("above $100,000"), and
                # stripping that tail would silently mutilate the label.
                pending.append(line)
                continue

            measure = _MEASURE_LABELS.get(label, "")
            if measure:
                full_label = " ".join(pending).strip()
                if full_label:
                    section = full_label
                display = f"{section} - {label}".strip(" -") if section else label
            else:
                display = " ".join([*pending, label]).strip()
                measure = "deficit_effect"
            pending = []
            if not display or display in _BANNER_LINES:
                display = titles.get(number, "")

            seq += 1
            rows.append(
                AlternativeRow(
                    option_number=number,
                    alternative_id=f"{number}.{seq}",
                    label=re.sub(r"\s+", " ", display),
                    measure=measure,
                    savings_5yr_billions=-values[10],
                    savings_10yr_billions=-values[11],
                    annual_savings_billions=[-v for v in values[:10]],
                    report_page=report_page,
                    pdf_page=pdf_page,
                )
            )

    return rows


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def build(pdf_path: Path) -> tuple[list[OptionRow], list[AlternativeRow]]:
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        page_texts = [page.extract_text() or "" for page in pdf.pages]

    options = parse_table_1_1(page_texts[7:9])
    if len(options) != N_OPTIONS:
        raise SystemExit(
            f"Table 1-1 parse produced {len(options)} rows, expected {N_OPTIONS}. "
            "Refusing to overwrite the committed CSV."
        )

    contents = parse_contents(page_texts[3:6])
    for row in options:
        area, report_page = contents.get(row.option_number, ("", None))
        row.budget_area = area
        row.report_page = report_page
        row.pdf_page = (report_page + 6) if report_page else None

    titles = {row.option_number: row.title for row in options}
    alternatives = parse_option_tables(page_texts, contents, titles)
    return options, alternatives


def write_csvs(options: list[OptionRow], alternatives: list[AlternativeRow]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    header_lines = [
        f"# Source: {PUBLICATION}",
        f"# Landing page: {PUBLICATION_URL}",
        f"# PDF: {PDF_URL}",
        "# Table 1-1, 'Projected Savings From Options for Reducing the Deficit',"
        " report pages 2-3 (PDF pages 8-9).",
        "# Sign conventions: savings_* follow CBO (positive = reduces the deficit);",
        "#   deficit_effect_* follow this app (positive = increases the deficit).",
        "# Baselines (PDF page 2, 'Notes About This Report'): spending options are"
        " measured against CBO's",
        "#   June 2024 baseline (pub. 60039); revenue options against the February"
        " 2024 baseline (pub. 59710).",
        "# Rebuilt by scripts/extract_cbo_options.py.",
    ]

    with OPTIONS_CSV.open("w", encoding="utf-8", newline="") as handle:
        for line in header_lines:
            handle.write(line + "\n")
        writer = csv.writer(handle)
        writer.writerow([
            "option_number", "title", "category", "budget_area",
            "savings_low_billions", "savings_high_billions",
            "deficit_effect_low_billions", "deficit_effect_high_billions",
            "has_range", "footnote", "table_ref", "report_page", "pdf_page",
            "baseline_vintage", "extracted_by",
        ])
        for row in sorted(options, key=lambda r: r.option_number):
            writer.writerow([
                row.option_number,
                row.title,
                row.category,
                row.budget_area,
                row.savings_low_billions,
                row.savings_high_billions,
                None if row.savings_high_billions is None else -row.savings_high_billions,
                None if row.savings_low_billions is None else -row.savings_low_billions,
                "yes" if row.has_range else "no",
                row.footnote,
                "Table 1-1 (report pp. 2-3; PDF pp. 8-9)",
                row.report_page,
                row.pdf_page,
                BASELINE_BY_CATEGORY.get(row.category, ""),
                row.extracted_by,
            ])

    with ALTERNATIVES_CSV.open("w", encoding="utf-8", newline="") as handle:
        for line in header_lines[:3]:
            handle.write(line + "\n")
        handle.write(
            "# One row per reported line in an option's own table (report pages"
            " 5-88; PDF pages 11-94).\n"
        )
        handle.write(
            "# savings_* follow CBO (positive = reduces the deficit);"
            " deficit_effect_* follow this app.\n"
        )
        handle.write("# Rebuilt by scripts/extract_cbo_options.py.\n")
        writer = csv.writer(handle)
        writer.writerow([
            "option_number", "alternative_id", "label", "measure",
            "savings_5yr_billions", "savings_10yr_billions",
            "deficit_effect_10yr_billions",
            *[f"savings_{year}_billions" for year in range(2025, 2035)],
            "report_page", "pdf_page", "extracted_by",
        ])
        for row in alternatives:
            writer.writerow([
                row.option_number,
                row.alternative_id,
                row.label,
                row.measure,
                row.savings_5yr_billions,
                row.savings_10yr_billions,
                None if row.savings_10yr_billions is None else -row.savings_10yr_billions,
                *(row.annual_savings_billions + [None] * 10)[:10],
                row.report_page,
                row.pdf_page,
                row.extracted_by,
            ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        type=Path,
        default=OUT_DIR / "60557-budget-options.pdf",
        help="Path to the downloaded 60557-budget-options.pdf.",
    )
    args = parser.parse_args(argv)

    if not args.pdf.exists():
        print(
            f"PDF not found at {args.pdf}.\n"
            f"Download it from {PDF_URL} (cbo.gov serves a bot challenge to plain\n"
            "HTTP clients, so fetch it with a browser) and pass --pdf.",
            file=sys.stderr,
        )
        return 2

    options, alternatives = build(args.pdf)
    write_csvs(options, alternatives)
    print(
        f"Wrote {len(options)} options to {OPTIONS_CSV.relative_to(PROJECT_ROOT)} and "
        f"{len(alternatives)} alternative rows to "
        f"{ALTERNATIVES_CSV.relative_to(PROJECT_ROOT)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
