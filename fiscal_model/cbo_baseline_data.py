"""
CBO's own baseline tables, as transcribed from CBO's own GitHub organisation.

One reader for the three CSVs :mod:`scripts.fetch_cbo_baseline` writes, so a
transcription error has exactly one place to hide. :mod:`fiscal_model.baseline`
is the only caller; everything here is read-only and cached.

**Why the files exist.** ``baseline.py`` used to state its own blocker in as
many words — *"cbo.gov returns HTTP 403 to this environment and the Wayback
Machine holds no snapshot of the January 2025 or February 2026 budget
projections workbooks… Adding one is a data edit - a block in the CSV - not a
code change."* That is true of ``cbo.gov`` and false of ``github.com/US-CBO``,
which is not blocked and which publishes the same tables as machine-readable
CSV under a public-domain dedication (owner decision (10)).

**What a vintage may and may not claim.** Two vintages have a published budget
table and all three have a published economic one, so the grade this module
returns is **per line, computed from what the transcription actually contains**
rather than asserted by a literal. A vintage whose block is absent cannot be
graded ``transcribed`` by a stale constant, which is the failure mode
``VINTAGE_SOURCING`` acquired when it said ``"sourced"`` for a February 2024
whose real GDP growth is 0.60 percentage points from CBO's own table.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).parent / "data_files" / "cbo_baseline"
BUDGET_PATH = DATA_DIR / "cbo_budget_baseline.csv"
ECONOMIC_PATH = DATA_DIR / "cbo_economic_baseline.csv"
PROVENANCE_PATH = DATA_DIR / "PROVENANCE.csv"

#: Economic series names, in the units :class:`~fiscal_model.baseline.EconomicAssumptions`
#: expects them (fractions, not CBO's printed percentages — the transcription
#: script divides by 100 so nothing here has to remember to).
ASSUMPTION_SERIES = (
    "real_gdp_growth",
    "inflation",
    "unemployment",
    "interest_rate_10yr",
    "labor_force_participation",
)


@dataclass(frozen=True)
class VintageProvenance:
    """Where one vintage's numbers came from, one row per kind."""

    vintage: str
    kind: str
    repository: str
    file_path: str
    commit_sha: str
    sha256: str
    fetch_date: str
    publication: str
    note: str

    @property
    def transcribed(self) -> bool:
        """``True`` when a CBO file was actually read for this line."""
        return bool(self.file_path and self.sha256)


def _read_long(path: Path) -> dict[str, dict[str, dict[int, float]]]:
    """``{vintage: {variable: {fiscal_year: value}}}`` from a ``#``-headed CSV."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    out: dict[str, dict[str, dict[int, float]]] = {}
    for row in csv.DictReader(body):
        out.setdefault(row["vintage"], {}).setdefault(row["variable"], {})[
            int(row["fiscal_year"])
        ] = float(row["value"])
    return out


@lru_cache(maxsize=1)
def budget_tables() -> dict[str, dict[str, dict[int, float]]]:
    """CBO's ten-year budget path, by vintage. Empty dict where none is published."""
    return _read_long(BUDGET_PATH)


@lru_cache(maxsize=1)
def economic_tables() -> dict[str, dict[str, dict[int, float]]]:
    """CBO's fiscal-year economic forecast, by vintage."""
    return _read_long(ECONOMIC_PATH)


@lru_cache(maxsize=1)
def provenance() -> dict[tuple[str, str], VintageProvenance]:
    """``{(vintage, kind): VintageProvenance}`` from ``PROVENANCE.csv``."""
    if not PROVENANCE_PATH.exists():
        return {}
    with open(PROVENANCE_PATH, encoding="utf-8", newline="") as handle:
        body = [line for line in handle if not line.startswith("#")]
    out: dict[tuple[str, str], VintageProvenance] = {}
    for row in csv.DictReader(body):
        record = VintageProvenance(**{k: (v or "") for k, v in row.items()})
        out[(record.vintage, record.kind)] = record
    return out


def has_budget_table(vintage: str) -> bool:
    """Whether CBO publishes a ten-year budget table for this vintage."""
    return bool(budget_tables().get(vintage))


def has_economic_table(vintage: str) -> bool:
    """Whether CBO publishes a fiscal-year economic forecast for this vintage."""
    return bool(economic_tables().get(vintage))


def series(
    table: dict[int, float], first_year: int, count: int
) -> np.ndarray:
    """``count`` values from ``first_year``, continuing the nearest growth rate.

    Outside the transcribed window the nearest observed growth rate is
    continued rather than the value clamped — the rule
    :func:`fiscal_model.corporate.cbo_corporate_receipts` and
    :func:`fiscal_model.payroll.covered_earnings` already apply at the ends of
    their own CBO tables, so a caller asking for a year CBO does not project
    gets an extrapolation it can recognise rather than a flat line it cannot.

    In practice this reaches only the last year or two: February 2026 covers
    FY2025-FY2036 and the app's window is FY2026-FY2035, entirely inside it.
    """
    years = sorted(table)
    if not years:
        raise KeyError("empty CBO series")
    low, high = years[0], years[-1]

    values = []
    for year in range(first_year, first_year + count):
        if year in table:
            values.append(table[year])
        elif year > high:
            growth = table[high] / table[high - 1] - 1.0 if high - 1 in table else 0.0
            values.append(table[high] * (1.0 + growth) ** (year - high))
        else:
            growth = table[low + 1] / table[low] - 1.0 if low + 1 in table else 0.0
            values.append(
                table[low] / (1.0 + growth) ** (low - year) if growth > -1.0
                else table[low]
            )
    return np.array(values, dtype=float)


def assumption_arrays(vintage: str, first_year: int, count: int = 10) -> dict[str, np.ndarray]:
    """This vintage's own economic assumptions over ``count`` years.

    Raises :class:`KeyError` when the vintage has no transcribed economic
    block, rather than borrowing a neighbour's — the behaviour that keeps a
    provenance claim honest.
    """
    table = economic_tables().get(vintage)
    if not table:
        raise KeyError(f"no transcribed economic table for vintage {vintage!r}")
    return {
        name: series(table[name], first_year, count)
        for name in ASSUMPTION_SERIES
        if name in table
    }


def nominal_gdp_table(vintage: str) -> dict[int, float] | None:
    """CBO's own fiscal-year nominal GDP levels, or ``None``.

    Returned whole rather than windowed because
    :meth:`fiscal_model.baseline.BaselineProjection.nominal_income_index` reads
    years *before* the scoring window — the SOI anchor is a tax year several
    years back — and a level CBO publishes should be read rather than
    back-extrapolated from the window's first growth rate.
    """
    table = economic_tables().get(vintage) or {}
    return table.get("nominal_gdp")
