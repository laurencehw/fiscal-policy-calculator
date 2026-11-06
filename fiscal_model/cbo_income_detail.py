"""
CBO's own projection of the individual income tax base, by calendar year.

One reader for the CSV :mod:`scripts.fetch_cbo_income_detail` writes
(``cbo-data`` ``revenue_detail/annual_cy_iit_{edition}.csv``, CBO's *Revenue
Projections, by Category*). Read-only and cached.

**What is wired.** Two series, by lane B2a
(``planning/lanes/B2a_cbo_income_path.md``): ``rev_iit_taxable_income`` and
``rev_iit_agi``, read by
:meth:`fiscal_model.baseline.BaselineProjection.income_base_index` as a growth
index for the SOI income base. Only ratios are used, so the level cancels. The
per-bracket series (``rev_iit_bracket_k``) are transcribed but are never a
growth index: their numbering changes meaning in CY2026 in the 2024-06 and
2025-01 editions. ``scripts/ordinary_base_decomposition.py`` reads them as
levels.

**What it may be used for.** Like the tax-parameter schedule, this is CBO's own
projection, transcribed; it must never be used to re-fit a constant.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data_files" / "cbo_income_detail"
DETAIL_PATH = DATA_DIR / "cbo_income_detail.csv"
PROVENANCE_PATH = DATA_DIR / "PROVENANCE.csv"

#: ``TaxPolicy.income_measure`` values mapped to the CBO series that projects
#: that base. Anything else reads taxable income, the default measure.
SERIES_BY_INCOME_MEASURE: dict[str, str] = {
    "taxable_income": "rev_iit_taxable_income",
    "agi": "rev_iit_agi",
}
DEFAULT_SERIES = "rev_iit_taxable_income"


def _data_lines(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("#"):
                yield line


@lru_cache(maxsize=1)
def _table() -> dict[tuple[str, str], dict[int, float]]:
    if not DETAIL_PATH.exists():
        return {}
    table: dict[tuple[str, str], dict[int, float]] = {}
    for row in csv.DictReader(_data_lines(DETAIL_PATH)):
        key = (row["vintage"], row["variable"])
        table.setdefault(key, {})[int(row["calendar_year"])] = float(row["value"])
    return table


@lru_cache(maxsize=1)
def provenance() -> dict[str, dict[str, str]]:
    """One row per vintage: the edition read and its match grade."""
    if not PROVENANCE_PATH.exists():
        return {}
    return {row["vintage"]: dict(row) for row in csv.DictReader(_data_lines(PROVENANCE_PATH))}


def series_for_income_measure(income_measure: str | None) -> str:
    """The CBO series that projects a policy's income base."""
    return SERIES_BY_INCOME_MEASURE.get(str(income_measure or ""), DEFAULT_SERIES)


def series(vintage: str, variable: str) -> dict[int, float]:
    """``{calendar_year: value}`` for one vintage and variable; empty if absent."""
    return dict(_table().get((str(vintage), str(variable)), {}))


def match_grade(vintage: str) -> str | None:
    """``exact`` or ``nearest_vintage`` for a transcribed vintage, else ``None``."""
    entry = provenance().get(str(vintage))
    return entry["match"] if entry else None
