"""
CBO's own statutory tax-parameter schedule, as transcribed from CBO's GitHub.

One reader for the two CSVs :mod:`scripts.fetch_cbo_tax_parameters` writes, so
a transcription error has exactly one place to hide. Everything here is
read-only and cached.

**Why the files exist.** ``fiscal_model/validation/cbo_scores.py`` used to say,
in as many words, that ``cbo_opt45_top4_brackets_2pp`` could not be scored with
a year-indexed threshold because *a published post-2025 rate table does not
exist*. ``github.com/US-CBO`` is not blocked and publishes exactly that table -
CBO publication 53724, *Tax Parameters and Effective Marginal Tax Rates* - on
three vintages, in four filing statuses, out to CY2036.

**What is wired and what is not.** The transcription is verbatim: 130 to 150
variables per vintage, covering brackets, rates, AMT exemptions and phase-outs,
sixteen EITC parameters, five CTC parameters, SALT limits, standard deductions,
the Social Security taxable maximum, both price indices and CBO's own effective
marginal tax rates. **Only the ordinary-income bracket floors and rates are read
by anything today.** The rest is reachable and deliberately unused: each one
belongs to a module (``amt.py``, ``credits.py``, ``tax_expenditures_core.py``,
``payroll.py``) whose benchmarks sit in the calibrated tier, and wiring any of
them is a lane of its own - see ``planning/lanes/R4_parameter_schedule.md`` §5.

**The rule about what this may be used for.** A rate schedule is *law*, so
reading it introduces no fitted quantity and no leakage on the statutory side.
It must never be used to re-fit a constant: the gain this module exists for is
**expressiveness, not error**.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data_files" / "cbo_tax_parameters"
PARAMETERS_PATH = DATA_DIR / "cbo_tax_parameters.csv"
PROVENANCE_PATH = DATA_DIR / "PROVENANCE.csv"

#: How many ordinary-income brackets the statute defines. Seven under both the
#: TCJA schedule and the pre-2018 one that returns in CY2026 on the vintages
#: whose current law contains the reversion, which is why one index serves both.
BRACKET_COUNT = 7

#: ``fiscal_model.data.irs_soi.FILING_STATUSES`` mapped to CBO's own suffixes.
#:
#: The two vocabularies are not the same and neither is wrong: SOI names the
#: populations it tabulates, CBO names the schedules in the Internal Revenue
#: Code. This mapping is the whole of the translation and is stated once here so
#: that no caller has to know both.
FILING_STATUS_SUFFIX: dict[str, str] = {
    "joint": "mfj",
    "separate": "mfs",
    "head_of_household": "hoh",
    "single": "single",
}

#: The baseline vintage a policy is scored on, when it names none.
#:
#: :class:`fiscal_model.baseline.CBOBaseline` defaults to February 2026, so a
#: policy built by Tailor, Ask, Build or the API is scored on that vintage's own
#: law. Stated here rather than imported to keep this module free of a cycle:
#: ``baseline.py`` has no reason to know about tax parameters, and a mismatch
#: would be caught by :func:`schedule_vintages` returning a key nothing serves.
DEFAULT_BASELINE_VINTAGE = "cbo_feb_2026"


class TaxParameterError(LookupError):
    """A parameter the schedule does not carry for that vintage and year."""


@lru_cache(maxsize=1)
def _table() -> dict[tuple[str, str, int], float]:
    """``{(vintage, variable, calendar_year): value}`` for every row on file."""
    table: dict[tuple[str, str, int], float] = {}
    if not PARAMETERS_PATH.exists():  # pragma: no cover - packaging guard
        return table
    with PARAMETERS_PATH.open(encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        for row in rows:
            table[(row["vintage"], row["variable"], int(row["calendar_year"]))] = float(
                row["value"]
            )
    return table


@lru_cache(maxsize=1)
def provenance() -> dict[str, dict[str, str]]:
    """One record per vintage: which CBO edition was read, and how well it matches.

    ``match`` is ``"exact"`` where the edition tag is that vintage's own and
    ``"nearest_vintage"`` where it is not. Nothing in the scoring path may
    override the grade, which is the point of computing it from the
    transcription rather than declaring it in code.
    """
    records: dict[str, dict[str, str]] = {}
    if not PROVENANCE_PATH.exists():  # pragma: no cover - packaging guard
        return records
    with PROVENANCE_PATH.open(encoding="utf-8") as handle:
        rows = csv.DictReader(line for line in handle if not line.startswith("#"))
        for row in rows:
            records[row["vintage"]] = dict(row)
    return records


def schedule_vintages() -> tuple[str, ...]:
    """Baseline vintage ids the schedule serves, in transcription order."""
    return tuple(provenance())


def is_available() -> bool:
    """Whether the transcription is present and non-empty."""
    return bool(_table())


def years_available(vintage: str) -> tuple[int, ...]:
    """Calendar years this vintage's edition covers, ascending."""
    return tuple(sorted({year for key_v, _var, year in _table() if key_v == vintage}))


def parameter(vintage: str, variable: str, year: int) -> float:
    """One published parameter, or raise :class:`TaxParameterError`.

    Years outside the edition's own range are **not** extrapolated. A schedule
    is law for the years the law is written for, and inventing a CY2040 bracket
    by compounding a price index would be a projection wearing a statute's
    clothes. Callers that need a year outside the range clamp to the nearest
    published one themselves, visibly - see
    :func:`fiscal_model.policies_core.TaxPolicy.statutory_threshold_for_year`.
    """
    try:
        return _table()[(vintage, variable, int(year))]
    except KeyError as exc:
        raise TaxParameterError(
            f"no {variable!r} for vintage {vintage!r} in CY{year}; "
            f"this edition covers {years_available(vintage) or '(nothing)'}"
        ) from exc


def bracket_floor(vintage: str, index: int, filing_status: str, year: int) -> float:
    """Floor of statutory ordinary-income bracket ``index`` (1-7), in dollars.

    ``filing_status`` is one of :data:`fiscal_model.data.irs_soi.FILING_STATUSES`,
    translated here to CBO's own suffix. Bracket 1's floor is $0 in every year of
    every vintage, which :func:`scripts.fetch_cbo_tax_parameters.check_identities`
    asserts on every transcription - two validation rows depend on it returning
    today's number to the cent.
    """
    if not 1 <= int(index) <= BRACKET_COUNT:
        raise ValueError(
            f"bracket index must be 1-{BRACKET_COUNT}, got {index!r}"
        )
    try:
        suffix = FILING_STATUS_SUFFIX[filing_status]
    except KeyError as exc:
        raise ValueError(
            f"unknown filing status {filing_status!r}; expected one of "
            f"{', '.join(FILING_STATUS_SUFFIX)}"
        ) from exc
    return parameter(vintage, f"tp_bracket_{int(index)}_{suffix}", year)


def ordinary_rate(vintage: str, index: int, year: int) -> float:
    """Statutory rate on bracket ``index`` (1-7), as a fraction.

    CBO publishes these as percentages; this returns 0.24 rather than 24.0, the
    unit every rate in this repository is carried in. Nothing scores with it
    today - it is here because a reader asking "did the schedule revert?" should
    not have to divide by a hundred to find out.
    """
    if not 1 <= int(index) <= BRACKET_COUNT:
        raise ValueError(
            f"bracket index must be 1-{BRACKET_COUNT}, got {index!r}"
        )
    return parameter(vintage, f"tp_rate_{int(index)}", year) / 100.0


def bracket_floors_by_status(
    vintage: str, index: int, year: int
) -> dict[str, float]:
    """All four filing statuses' floors for one bracket and year.

    The shape :class:`~fiscal_model.policies_core.TaxPolicy`'s per-status path
    consumes. Read it as the answer to "what does the law say this boundary is,
    for each population SOI tabulates, in this year, under this vintage's
    current law" - four numbers that need not move together, and do not: at the
    CY2026 reversion on the February 2024 vintage the joint floor of bracket 4
    falls 3.5% while the head-of-household floor rises 65.5%.
    """
    return {
        status: bracket_floor(vintage, index, status, year)
        for status in FILING_STATUS_SUFFIX
    }
