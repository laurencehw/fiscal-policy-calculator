"""Rebuild the vendored capital-gains data files from their public sources.

Everything under ``fiscal_model/data_files/capital_gains/`` that this lane
(L1, Wave 2 of ``planning/MODELING_IMPROVEMENT.md``) added is produced here, so
the transcription is auditable rather than hand-typed. Run it when a new tax
year or a new Financial Accounts vintage is published::

    python scripts/build_capital_gains_data.py

Sources, all fetched over HTTPS from the publishing agency:

* **IRS SOI Table 3.5** - *Returns with Modified Taxable Income: Tax Generated,
  by Size of Adjusted Gross Income and Tax Rate*, Individual Complete Report
  (Publication 1304).  ``https://www.irs.gov/pub/irs-soi/<yy>in35tr.xls``.
  This is the only public table that reports **income actually taxed at each
  preferential capital-gains rate** (0, 15, 20, 25 and 28 percent) by AGI class,
  which is what a rate change applies to.
* **IRS SOI Table 1.4A** - *Returns with Income or Loss from Sales of Capital
  Assets Reported on Form 1040, Schedule D*, same report.
  ``https://www.irs.gov/pub/irs-soi/<yy>in14acg.xls``.  Supplies the short-term
  / long-term split that decides which part of the base has a timing margin.
* **IRS SOI Table 1.4** - *All Returns: Sources of Income, Adjustments,
  Deductions, and Tax Items*, same report,
  ``https://www.irs.gov/pub/irs-soi/<yy>in14ar.xls``.  Read for one column,
  qualified dividends, and only as a **check**: Table 3.5's preferential base
  already contains them, and this is what says so in the tree rather than in a
  commit message.
* **Federal Reserve Distributional Financial Accounts** (Z.1 companion),
  ``https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip``.
  Household net worth by age of reference person and by net-worth percentile
  group, consistent with the Financial Accounts aggregate (B.101).
* **NCHS, United States Life Tables, 2022** (NVSR 74-02, Table 1),
  ``https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/74-02/Table01.xlsx``.
* **Federal Reserve, Survey of Consumer Finances 2022**, historical tables,
  used only for mean family net worth, which turns the DFA aggregate into a
  household count.
* **IRS SOI Estate Tax Statistics, Table 1**, filing year 2024,
  ``https://www.irs.gov/pub/irs-soi/24es01fy.xlsx``.  The charitable deduction
  and bequests to a surviving spouse by size of gross estate, which is what a
  realization-at-death proposal's charitable carve-out removes and - for the
  spousal column - what it would double-count if it removed it again.  Its
  return counts by size class are also read as a *check* on the fitted decedent
  size distribution, never as an input.

The DFA percentile aggregates are additionally used to fit a **piecewise-Pareto
size distribution of net worth at death** (``decedent_size_distribution.csv``),
so that a per-decedent exclusion is integrated over a distribution rather than
applied to five group means.  The fit reproduces each DFA group's own aggregate
exactly and is deliberately *not* extended below the 90th percentile: the index
it returns there is below one and the median it implies is twice the Survey of
Consumer Finances' published figure, which is what a Pareto refusing a
non-tail looks like.

Two figures are transcribed by hand from papers rather than fetched, and both
carry their page reference in the emitted CSV:

* Poterba, J. and S. Weisbenner (2001), "The Distributional Burden of Taxing
  Estates and Unrealized Capital Gains at Death", in *Rethinking Estate and
  Gift Taxation* (Brookings), Table 8: expected estates $118.9B and expected
  unrealized capital gains at death $42.8B per year, the latter **36 percent**
  of the former, from the 1998 Survey of Consumer Finances; and the same
  table's lower panel, the share of unrealized capital gain held in the primary
  residence and in active business and farm holdings by estate size, which is
  what the section 121 exclusion and the Green Books' family-business deferral
  reach.
* Avery, R., D. Grodzicki and K. Moore (2013), "Estate vs. Capital Gains
  Taxation", FEDS 2013-28, Figure 1: the unrealized-gain share of the gross
  estate by wealth at death, 12.8 percent below $2M rising to 54.9 percent
  above $100M.
"""

from __future__ import annotations

import argparse
import io
import math
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "fiscal_model" / "data_files" / "capital_gains"

SOI_TABLE_35 = "https://www.irs.gov/pub/irs-soi/{yy}in35tr.xls"
SOI_TABLE_14A = "https://www.irs.gov/pub/irs-soi/{yy}in14acg.xls"
SOI_TABLE_14 = "https://www.irs.gov/pub/irs-soi/{yy}in14ar.xls"
SOI_ESTATE_TABLE_1 = "https://www.irs.gov/pub/irs-soi/24es01fy.xlsx"
DFA_ZIP = "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
NCHS_LIFE_TABLE = (
    "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/NVSR/74-02/Table01.xlsx"
)
SCF_TABLES = (
    "https://www.federalreserve.gov/econres/files/"
    "scf2022_tables_public_nominal_historical.xlsx"
)

SOI_YEARS = (2022, 2023)

#: Column offsets in SOI Table 3.5 for each preferential capital-gains rate:
#: (number of returns, income taxed at rate, tax generated at rate).  The 0
#: percent column reports no "tax generated" because there is none.
TABLE_35_RATE_COLUMNS: dict[str, tuple[int, int, int | None]] = {
    "0.00": (6, 7, None),
    "0.15": (17, 18, 19),
    "0.20": (20, 21, 22),
    "0.25": (29, 30, 31),
    "0.28": (32, 33, 34),
}

#: Column offsets in SOI Table 1.4 (all returns, sources of income): the
#: "Qualified dividends [2]" amount.  Read only to *check* that the Table 3.5
#: preferential base already contains qualified dividends; never used as an
#: input, because adding it would double-count.
TABLE_14_QUALIFIED_DIVIDENDS_COLUMN = 26

#: Column offsets in SOI Table 1.4A.
TABLE_14A_COLUMNS = {
    "taxable_net_gain_thousands": 2,
    "net_short_term_gain_thousands": 6,
    "net_long_term_gain_thousands": 62,
}

#: NIIT applies to net investment income once modified AGI exceeds $200,000
#: (single) or $250,000 (married filing jointly), 26 U.S.C. 1411.  SOI's AGI
#: classes break at $200,000, so a class whose lower bound is at or above that
#: is treated as facing the surtax and one below it as not.  This is a
#: statutory mapping read off the class boundaries, not a fitted ladder.
NIIT_RATE = 0.038
NIIT_AGI_THRESHOLD = 200_000.0

#: DFA age bands, and the NCHS life-table ages they span.
DFA_AGE_BANDS = {
    "ageunder40": (0, 39),
    "age40to54": (40, 54),
    "age55to69": (55, 69),
    "age70plus": (70, 120),
}

#: DFA net-worth groups and the share of households each contains, by
#: construction of the percentile definition.
DFA_NETWORTH_GROUPS = {
    "TopPt1": 0.001,
    "RemainingTop1": 0.009,
    "Next9": 0.09,
    "Next40": 0.40,
    "Bottom50": 0.50,
}

#: Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1, "Current Law" column:
#: unrealized capital gains as a share of the gross estate, by wealth at death.
#: Keyed by the lower bound of each band in millions of dollars.
AGM_GAIN_SHARE_LADDER: tuple[tuple[float, float], ...] = (
    (0.0, 0.128),
    (2.0, 0.228),
    (3.5, 0.282),
    (5.0, 0.325),
    (10.0, 0.356),
    (20.0, 0.425),
    (50.0, 0.459),
    (100.0, 0.549),
)

#: Poterba & Weisbenner (2001) Table 8, 1998 Survey of Consumer Finances.
PW2001_EXPECTED_ESTATES_BILLIONS = 118.9
PW2001_GAINS_AT_DEATH_BILLIONS = 42.8
PW2001_GAIN_SHARE_OF_ESTATES = 0.36
PW2001_SCF_YEAR = 1998

#: Poterba & Weisbenner (2001) Table 8, lower panel, "Share of Total Unrealized
#: Capital Gain (in percent)", by insurance-augmented net worth of the decedent.
#: Keyed by the lower bound of each class in millions of dollars.  Only the two
#: shares a realization-at-death proposal carves out are carried: the primary
#: residence (which the section 121 exclusion reaches) and active business and
#: farm holdings (which the Green Books' family-business election defers).
#: The table's own note settles two more of the six Green Book reliefs -
#: "Bonds, vehicles, and collectibles are assumed to have no accrued capital
#: gains" and "It is assumed a decedent transfers his/her full estate to a
#: surviving spouse.  Such inter-spousal transfers are not included in the
#: estate totals reported above" - so tangible personal property and spousal
#: transfers are already absent from this base and are emitted as zero.
PW2001_TABLE_8_GAIN_SHARES: tuple[tuple[float, float, float], ...] = (
    # (lower bound of net-worth class, primary residence, active business & farm)
    (0.0, 1.001, 0.006),
    (0.25, 0.831, 0.014),
    (0.50, 0.460, 0.017),
    (1.0, 0.352, 0.114),
    (5.0, 0.102, 0.172),
    (10.0, 0.036, 0.723),
)

#: DFA percentile groups from the top down, as (group, cumulative population
#: share at the group's upper wealth edge, share at its lower one).  These are
#: the boundaries the piecewise-Pareto size distribution is fitted between; they
#: are the DFA's own published percentile definitions and nothing here chooses
#: them.
DFA_CUMULATIVE_EDGES: tuple[tuple[str, float, float], ...] = (
    ("TopPt1", 0.0, 0.001),
    ("RemainingTop1", 0.001, 0.01),
    ("Next9", 0.01, 0.10),
    ("Next40", 0.10, 0.50),
    ("Bottom50", 0.50, 1.00),
)

#: The groups the fitted distribution is integrated over.  Everything below the
#: 90th percentile keeps its group mean, because the fit there returns an index
#: below one and a median twice the SCF's published one - see
#: ``build_size_distribution_table``.
DFA_DISPERSED_GROUPS = ("TopPt1", "RemainingTop1", "Next9")

#: Columns of IRS SOI *Estate Tax Statistics* Table 1 (filing year 2024) that
#: the charitable and marital shares are read from, and the printed size
#: classes, keyed by the lower bound of the class in millions of dollars.
#: Column indices are zero-based positions in the sheet as published.
SOI_ESTATE_COLUMNS = {
    "gross_estate": 2,
    "spousal_bequests": 68,
    "charitable": 70,
    "returns": 1,
}
SOI_ESTATE_ROWS: tuple[tuple[float, float, int], ...] = (
    (0.0, 10.0, 9),  # "Under $10 million"
    (10.0, 20.0, 10),  # "$10 million < $20 million"
    (20.0, 50.0, 11),  # "$20 million < $50 million"
    (50.0, float("inf"), 12),  # "$50 million or more"
)
#: A ladder class whose mean estate is below $1 million gets no charitable
#: share at all.  SOI's table is estate-tax filers only - the filing threshold
#: was $13.61 million for 2023 decedents - so borrowing their propensity for a
#: sub-million-dollar estate would over-state the carve-out.  Zero over-states
#: the model's revenue instead, which is the conservative direction for a
#: channel that already over-predicts.
SOI_ESTATE_FLOOR_MILLIONS = 1.0

#: Dowd, McClelland & Muthitacharoen (2015), National Tax Journal 68(3), and
#: the reference rate CRS R48562 states its Table 4 estimates are adjusted to.
DMM_PERSISTENT_ELASTICITY = 0.72
DMM_TRANSITORY_ELASTICITY = 1.20
ELASTICITY_REFERENCE_RATE = 0.22

DFA_ANCHOR_QUARTER = "2024:Q4"
SCF_ANCHOR_QUARTER = "2022:Q4"
PW_ANCHOR_QUARTER = "1998:Q4"


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "fiscal-policy-calculator/1.0"})
    with urlopen(request, timeout=180) as response:
        return response.read()


def _agi_bounds(label: str) -> tuple[float, float]:
    """Parse an SOI AGI class label into numeric bounds."""
    text = label.replace(",", "").replace("$", "").strip().lower()
    if text.startswith(("total", "all returns")):
        return (0.0, float("inf"))
    if text.startswith("no adjusted gross income"):
        return (0.0, 0.0)
    if text.startswith("under "):
        return (0.0, float(text.split()[1]))
    if " under " in text:
        low, high = text.split(" under ")
        return (float(low.strip()), float(high.strip()))
    if "or more" in text:
        return (float(text.split()[0]), float("inf"))
    raise ValueError(f"unparsed AGI class: {label!r}")


def _soi_rows(frame: pd.DataFrame, first_data_row: int) -> list[tuple[int, str]]:
    """AGI-class rows of an SOI table, stopping at the footnotes.

    Table 1.4A repeats the whole AGI ladder under a second "Taxable returns,
    total" panel; taking rows only up to that heading keeps the all-returns
    panel, which is the universe Table 3.5 also reports.
    """
    rows: list[tuple[int, str]] = []
    for index in range(first_data_row, frame.shape[0]):
        label = str(frame.iloc[index, 0])
        if label == "nan" or label.startswith(("*", "[", "NOTE", "SOURCE", "**")):
            break
        if rows and "returns, total" in label.lower():
            break
        rows.append((index, label))
    return rows


def build_bracket_table() -> pd.DataFrame:
    """SOI Table 3.5: income taxed at each preferential rate, by AGI class."""
    records = []
    for year in SOI_YEARS:
        raw = _fetch(SOI_TABLE_35.format(yy=str(year)[2:]))
        frame = pd.read_excel(io.BytesIO(raw), header=None)
        for index, label in _soi_rows(frame, first_data_row=9):
            if label.lower().startswith("total"):
                continue
            low, high = _agi_bounds(label)
            for rate, (returns_col, income_col, tax_col) in TABLE_35_RATE_COLUMNS.items():
                income = float(frame.iloc[index, income_col] or 0.0)
                if income <= 0:
                    continue
                records.append(
                    {
                        "tax_year": year,
                        "agi_class": label,
                        "agi_lower": low,
                        "agi_upper": high,
                        "statutory_rate": float(rate),
                        "niit_rate": NIIT_RATE if low >= NIIT_AGI_THRESHOLD else 0.0,
                        "returns": int(float(frame.iloc[index, returns_col] or 0)),
                        "income_taxed_at_rate_thousands": income,
                        "tax_generated_thousands": (
                            float(frame.iloc[index, tax_col] or 0.0) if tax_col else 0.0
                        ),
                    }
                )
    return pd.DataFrame.from_records(records)


def build_holding_period_table() -> pd.DataFrame:
    """SOI Table 1.4A: short-term and long-term net gain, by AGI class."""
    records = []
    for year in SOI_YEARS:
        raw = _fetch(SOI_TABLE_14A.format(yy=str(year)[2:]))
        frame = pd.read_excel(io.BytesIO(raw), header=None)
        for index, label in _soi_rows(frame, first_data_row=9):
            if label.lower().startswith("all returns"):
                continue
            low, high = _agi_bounds(label)
            record = {
                "tax_year": year,
                "agi_class": label,
                "agi_lower": low,
                "agi_upper": high,
            }
            for name, column in TABLE_14A_COLUMNS.items():
                record[name] = float(frame.iloc[index, column] or 0.0)
            records.append(record)
    return pd.DataFrame.from_records(records)


def build_base_coverage_table(
    brackets: pd.DataFrame, aggregate_path: Path
) -> pd.DataFrame:
    """What the Table 3.5 preferential base is made of.  A check, not an input.

    A capital-gains rate option raises the rates on long-term gains **and**
    qualified dividends, so the obvious worry about a base called "realizations"
    is that it holds only the first.  Table 3.5 is not a gains table - its
    preferential-rate columns are the income the capital-gains schedule taxed,
    which is adjusted net capital gain plus qualified dividends - and the
    arithmetic settles it without anyone having to take that on trust: in both
    vendored years the base is **larger than the whole year's realized gains**,
    which a gains-only base cannot be, and the ratio to gains plus qualified
    dividends is stable across a year in which realizations fell 27 percent.

    Nothing reads the emitted file.  It exists so that "qualified dividends are
    already in there" is a number in the tree rather than an assertion in a
    commit message, and so that adding a qualified-dividends column later is
    visibly a double count.
    """
    aggregate = pd.read_csv(aggregate_path)
    records = []
    for year in SOI_YEARS:
        raw = _fetch(SOI_TABLE_14.format(yy=str(year)[2:]))
        frame = pd.read_excel(io.BytesIO(raw), header=None)
        total_row = next(
            index
            for index in range(frame.shape[0])
            if str(frame.iloc[index, 0]).strip().lower().startswith("all returns")
        )
        qualified = (
            float(frame.iloc[total_row, TABLE_14_QUALIFIED_DIVIDENDS_COLUMN]) / 1e6
        )
        base = float(
            brackets.loc[
                brackets["tax_year"] == year, "income_taxed_at_rate_thousands"
            ].sum()
        ) / 1e6
        gains = float(
            aggregate.loc[
                aggregate["tax_year"] == year, "total_realized_capital_gains_billions"
            ].iloc[0]
        )
        records.append(
            {
                "tax_year": year,
                "preferential_base_billions": round(base, 3),
                "net_capital_gain_billions": round(gains, 3),
                "qualified_dividends_billions": round(qualified, 3),
                "base_over_gains_only": round(base / gains, 4),
                "base_over_gains_plus_qualified_dividends": round(
                    base / (gains + qualified), 4
                ),
            }
        )
    return pd.DataFrame.from_records(records)


def _dfa_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    archive = zipfile.ZipFile(io.BytesIO(_fetch(DFA_ZIP)))
    age = pd.read_csv(io.BytesIO(archive.read("dfa-age-levels.csv")))
    networth = pd.read_csv(io.BytesIO(archive.read("dfa-networth-levels.csv")))
    return age, networth


def _band_mortality() -> dict[str, float]:
    """Annual deaths per person-year lived, by DFA age band, from the NCHS
    complete life table: sum of ``dx`` over the band divided by sum of ``Lx``."""
    frame = pd.read_excel(
        io.BytesIO(_fetch(NCHS_LIFE_TABLE)),
        header=None,
        skiprows=3,
        names=["age", "qx", "lx", "dx", "Lx", "Tx", "ex"],
    ).dropna(subset=["qx"])
    en_dash = "–"
    ages = []
    for label in frame["age"]:
        text = str(label)
        ages.append(int(text.split(en_dash)[0]) if en_dash in text else 100)
    frame = frame.assign(x=ages)
    rates = {}
    for band, (low, high) in DFA_AGE_BANDS.items():
        span = frame[(frame["x"] >= low) & (frame["x"] <= high)]
        rates[band] = float(span["dx"].sum() / span["Lx"].sum())
    return rates


def _scf_family_net_worth_2022_thousands() -> tuple[float, float]:
    """(median, mean) family net worth in 2022, SCF Table 4, 'All families'.

    The mean turns the DFA aggregate into a household count.  The median is
    read only as the external check that says where the piecewise-Pareto fit
    stops being a tail; nothing downstream multiplies by it.
    """
    frame = pd.read_excel(
        io.BytesIO(_fetch(SCF_TABLES)), sheet_name="Table 4", header=None
    )
    header = [str(value) for value in frame.iloc[2].tolist()]
    column = header.index("2022")  # the "Median" column; "Mean" is the next one
    for index in range(frame.shape[0]):
        if str(frame.iloc[index, 0]).strip() == "All families":
            return float(frame.iloc[index, column]), float(frame.iloc[index, column + 1])
    raise ValueError("SCF Table 4: 'All families' row not found")


def _agm_gain_share(estate_millions: float) -> float:
    share = AGM_GAIN_SHARE_LADDER[0][1]
    for lower, value in AGM_GAIN_SHARE_LADDER:
        if estate_millions >= lower:
            share = value
        else:
            break
    return share


def _soi_estate_bequest_shares() -> list[tuple[float, float, float, float, float]]:
    """Charitable and marital bequest shares by size of gross estate.

    Returns ``(lower, upper, charitable share, marital share, returns)`` per
    printed size class, bounds in millions of dollars.  The charitable
    denominator is the gross estate **net of bequests to a surviving spouse**,
    because the base these shares are applied to - Poterba & Weisbenner's flow
    of unrealized gains at death - already excludes inter-spousal transfers.
    The marital share is over the gross estate and is carried only as the
    magnitude cross-check for what deducting it twice would cost.  The return
    count is carried as the external check on the fitted decedent size
    distribution and is likewise never an input.
    """
    frame = pd.read_excel(io.BytesIO(_fetch(SOI_ESTATE_TABLE_1)), header=None)
    rows = []
    for lower, upper, index in SOI_ESTATE_ROWS:
        gross = float(frame.iloc[index, SOI_ESTATE_COLUMNS["gross_estate"]])
        spousal = float(frame.iloc[index, SOI_ESTATE_COLUMNS["spousal_bequests"]])
        charitable = float(frame.iloc[index, SOI_ESTATE_COLUMNS["charitable"]])
        returns = float(frame.iloc[index, SOI_ESTATE_COLUMNS["returns"]])
        non_marital = gross - spousal
        if gross <= 0 or non_marital <= 0:
            raise ValueError(f"SOI estate Table 1 row {index}: non-positive estate")
        rows.append((lower, upper, charitable / non_marital, spousal / gross, returns))
    return rows


def build_carveout_ladders() -> pd.DataFrame:
    """The carve-out step functions on their own published class boundaries.

    Long format - one row per (source, size class, quantity) - so that nothing
    is collapsed onto a decedent ladder's group means.  The five-class file this
    replaced evaluated Poterba & Weisbenner's six published rows at four points,
    Avery, Grodzicki & Moore's eight at four and SOI's four at three: seven of
    the eighteen published rows were never read by any scored case, including
    the whole $1M-$5M band that both Green Book exclusions sit in.

    ``applied`` is False for the two quantities the base already excludes.  They
    stay in the file as the record of a double count that would be wrong to
    make, and the loader must not hand them to the model.
    """
    records: list[dict] = []
    pw = list(PW2001_TABLE_8_GAIN_SHARES)
    for index, (lower, residence, business) in enumerate(pw):
        upper = pw[index + 1][0] if index + 1 < len(pw) else float("inf")
        for quantity, share in (
            ("residence_gain_share", residence),
            ("active_business_gain_share", business),
        ):
            records.append(
                {
                    "source": "poterba_weisbenner_2001_table8",
                    "size_class_lower_millions_usd": lower,
                    "size_class_upper_millions_usd": upper,
                    "quantity": quantity,
                    "share": share,
                    "applied": True,
                }
            )
    records.append(
        {
            "source": "poterba_weisbenner_2001_table8_note",
            "size_class_lower_millions_usd": 0.0,
            "size_class_upper_millions_usd": float("inf"),
            "quantity": "tangible_personal_property_gain_share",
            "share": 0.0,
            "applied": False,
        }
    )
    for lower, upper, charitable, marital, _returns in _soi_estate_bequest_shares():
        records.append(
            {
                "source": "irs_soi_estate_table1_fy2024",
                "size_class_lower_millions_usd": lower,
                "size_class_upper_millions_usd": upper,
                "quantity": "charitable_bequest_share",
                "share": charitable,
                "applied": True,
            }
        )
        records.append(
            {
                "source": "irs_soi_estate_table1_fy2024",
                "size_class_lower_millions_usd": lower,
                "size_class_upper_millions_usd": upper,
                "quantity": "marital_bequest_share",
                "share": marital,
                "applied": False,
            }
        )
    return pd.DataFrame.from_records(records)


def _solve_pareto_beta(target: float, ratio: float) -> float:
    """``beta`` such that ``(ratio**beta - 1) / beta == target``.

    ``beta = 1 - 1/alpha``.  The left-hand side rises monotonically from
    ``ln(ratio)`` at ``beta -> 0`` to ``ratio - 1`` at ``beta = 1``, so a target
    below ``ln(ratio)`` returns a negative beta - an index below one, which is
    what a segment that is not a Pareto tail looks like.
    """
    low, high = -0.999, 0.999
    for _ in range(200):
        middle = 0.5 * (low + high)
        value = (
            math.log(ratio)
            if abs(middle) < 1e-12
            else (ratio**middle - 1.0) / middle
        )
        if value < target:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def build_size_distribution_table(
    ladder: pd.DataFrame, households_millions: float, scf_median_thousands: float
) -> pd.DataFrame:
    """Piecewise-Pareto size distribution of net worth at death.

    Fitted to the DFA's own percentile-group aggregates and to nothing else.
    For a Pareto segment anchored at wealth ``x_lo`` at cumulative population
    share ``s_lo``, the wealth it holds down to ``s_hi`` is
    ``N * x_lo * s_lo * (r**beta - 1) / beta`` with ``r = s_hi / s_lo``, so each
    segment has one unknown and one equation: **the group's own aggregate**.
    ``threshold_millions_usd`` is the fitted wealth at ``percentile_share_upper``
    - the group's own *lower* wealth bound.

    The open-ended top class takes the index of the class below it, which is the
    convention ``CapitalGainsBaseline.pareto_tail_index`` already applies to
    SOI's open-ended top AGI class.  With that closure the top two groups are
    one Pareto and ``beta = ln(1 + W2/W1) / ln(10)``.

    Below the 90th percentile the fit **refuses**, and the row records both
    refusals: the index comes back below one, and the median it implies is twice
    the Survey of Consumer Finances' published 2022 figure.  Those groups keep
    their group mean, exactly as the five-class ladder did.
    """
    households = households_millions * 1e6
    aggregate = {
        str(row["group"]): float(row["net_worth_millions_usd"])
        for _, row in ladder.iterrows()
    }

    top_group, _, top_edge = DFA_CUMULATIVE_EDGES[0]
    second_group, _, second_edge = DFA_CUMULATIVE_EDGES[1]
    beta = math.log1p(aggregate[second_group] / aggregate[top_group]) / math.log(
        second_edge / top_edge
    )
    threshold = beta * aggregate[top_group] / (households * top_edge)

    records: list[dict] = []
    for group, lower_share, upper_share in DFA_CUMULATIVE_EDGES:
        if group == top_group:
            group_beta, group_threshold = beta, threshold
            note = (
                "open-ended top class; index taken from the class below it, the "
                "convention pareto_tail_index already uses for SOI's top AGI class"
            )
        else:
            ratio = upper_share / lower_share
            group_beta = _solve_pareto_beta(
                aggregate[group] / (households * lower_share * threshold), ratio
            )
            group_threshold = threshold * ratio ** (group_beta - 1.0)
            note = "fitted so the group's own DFA aggregate is reproduced exactly"
        alpha = 1.0 / (1.0 - group_beta) if group_beta < 1.0 else float("inf")
        dispersed = group in DFA_DISPERSED_GROUPS
        if not dispersed and abs(upper_share - 0.5) < 1e-9:
            note = (
                f"NOT integrated: fitted index {alpha:.4f} is below 1, so there "
                f"is no finite-mean Pareto here, and the 50th-percentile net "
                f"worth it implies (${group_threshold * 1e3:,.1f}k) is "
                f"{group_threshold * 1e3 / scf_median_thousands:.2f}x the SCF's "
                f"published 2022 median of ${scf_median_thousands:,.1f}k. The "
                f"group keeps its mean"
            )
        elif not dispersed:
            note = (
                "NOT integrated: below the 90th percentile, where the fit is "
                "refused - see the group above. beta is at the solver bound and "
                "the figures on this row are not used by anything"
            )
        records.append(
            {
                "group": group,
                "percentile_share_lower": lower_share,
                "percentile_share_upper": upper_share,
                "aggregate_net_worth_millions_usd": aggregate[group],
                "pareto_beta": group_beta,
                "pareto_alpha": alpha,
                "threshold_millions_usd": group_threshold,
                "dispersed": dispersed,
                "note": note,
            }
        )
        if group != top_group:
            threshold = group_threshold
    return pd.DataFrame.from_records(records)


def build_stock_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    """Accrued-gains parameters, the decedent ladder, the AGM ladder, the median."""
    age_levels, networth_levels = _dfa_frames()
    mortality = _band_mortality()
    median_family_net_worth, mean_family_net_worth = (
        _scf_family_net_worth_2022_thousands()
    )

    def total_net_worth(quarter: str) -> float:
        rows = networth_levels[networth_levels["Date"] == quarter]
        return float(rows["Net worth"].sum())  # millions of dollars

    anchor_nw = total_net_worth(DFA_ANCHOR_QUARTER)
    scf_nw = total_net_worth(SCF_ANCHOR_QUARTER)
    pw_nw = total_net_worth(PW_ANCHOR_QUARTER)

    anchor_year = int(DFA_ANCHOR_QUARTER.split(":")[0])
    pw_year = int(PW_ANCHOR_QUARTER.split(":")[0])
    growth = (anchor_nw / pw_nw) ** (1.0 / (anchor_year - pw_year)) - 1.0

    # Households implied by the DFA aggregate and the SCF mean, both for 2022.
    households_millions = scf_nw / (mean_family_net_worth * 1_000.0)

    # Mortality-weighted share of household net worth held by people who die
    # this year: DFA net worth by age of head against NCHS band mortality.
    age_rows = age_levels[age_levels["Date"] == DFA_ANCHOR_QUARTER].set_index("Category")
    weighted = sum(
        float(age_rows.loc[band, "Net worth"]) * rate for band, rate in mortality.items()
    )
    mortality_weighted_share = weighted / float(age_rows["Net worth"].sum())

    ladder_rows = []
    group_rows = networth_levels[networth_levels["Date"] == DFA_ANCHOR_QUARTER]
    group_rows = group_rows.set_index("Category")
    for group, household_share in DFA_NETWORTH_GROUPS.items():
        group_net_worth = float(group_rows.loc[group, "Net worth"])  # millions
        group_households = households_millions * household_share  # millions
        mean_estate_millions = group_net_worth / (group_households * 1_000_000.0)
        ladder_rows.append(
            {
                "group": group,
                "household_share": household_share,
                "net_worth_millions_usd": group_net_worth,
                "mean_net_worth_millions_usd": mean_estate_millions,
                "unrealized_gain_share": _agm_gain_share(mean_estate_millions),
            }
        )
    ladder = pd.DataFrame.from_records(ladder_rows)

    agm = pd.DataFrame(
        [
            {"wealth_at_death_lower_millions_usd": lower, "unrealized_gain_share": share}
            for lower, share in AGM_GAIN_SHARE_LADDER
        ]
    )

    parameters = pd.DataFrame.from_records(
        [
            {
                "key": "household_net_worth_anchor_millions_usd",
                "value": anchor_nw,
                "source": f"Federal Reserve DFA (Z.1), {DFA_ANCHOR_QUARTER}",
            },
            {
                "key": "household_net_worth_anchor_year",
                "value": float(anchor_year),
                "source": f"Federal Reserve DFA (Z.1), {DFA_ANCHOR_QUARTER}",
            },
            {
                "key": "household_net_worth_growth_rate",
                "value": growth,
                "source": (
                    f"Federal Reserve DFA (Z.1), compound annual growth "
                    f"{PW_ANCHOR_QUARTER} to {DFA_ANCHOR_QUARTER}"
                ),
            },
            {
                "key": "households_millions",
                "value": households_millions,
                "source": (
                    "Federal Reserve DFA (Z.1) 2022:Q4 aggregate divided by SCF 2022 "
                    "Table 4 mean family net worth"
                ),
            },
            {
                "key": "estate_flow_rate",
                "value": PW2001_EXPECTED_ESTATES_BILLIONS * 1_000.0 / pw_nw,
                "source": (
                    "Poterba & Weisbenner (2001) Table 8 expected estates $118.9B over "
                    f"Federal Reserve DFA household net worth, {PW_ANCHOR_QUARTER}"
                ),
            },
            {
                "key": "gains_at_death_share_of_net_worth",
                "value": PW2001_GAINS_AT_DEATH_BILLIONS * 1_000.0 / pw_nw,
                "source": (
                    "Poterba & Weisbenner (2001) Table 8 expected unrealized gains at "
                    f"death $42.8B over DFA household net worth, {PW_ANCHOR_QUARTER}"
                ),
            },
            {
                "key": "gain_share_of_estates",
                "value": PW2001_GAIN_SHARE_OF_ESTATES,
                "source": "Poterba & Weisbenner (2001) Table 8",
            },
            {
                "key": "mortality_weighted_net_worth_share",
                "value": mortality_weighted_share,
                "source": (
                    "NCHS United States Life Tables 2022 (NVSR 74-02) Table 1 against "
                    f"Federal Reserve DFA net worth by age of head, {DFA_ANCHOR_QUARTER}"
                ),
            },
            {
                "key": "accrued_gain_share_of_net_worth",
                "value": sum(
                    row["net_worth_millions_usd"] * row["unrealized_gain_share"]
                    for row in ladder_rows
                )
                / anchor_nw,
                "source": (
                    "Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1 evaluated on "
                    f"Federal Reserve DFA net worth by percentile group, {DFA_ANCHOR_QUARTER}"
                ),
            },
            {
                "key": "persistent_elasticity",
                "value": DMM_PERSISTENT_ELASTICITY,
                "source": "Dowd, McClelland & Muthitacharoen (2015), NTJ 68(3)",
            },
            {
                "key": "transitory_elasticity",
                "value": DMM_TRANSITORY_ELASTICITY,
                "source": "Dowd, McClelland & Muthitacharoen (2015), NTJ 68(3)",
            },
            {
                "key": "elasticity_reference_rate",
                "value": ELASTICITY_REFERENCE_RATE,
                "source": (
                    "CRS R48562 (2025) Table 4 note: estimates adjusted to a 22 percent "
                    "tax rate; the semi-log coefficient is the elasticity over this rate"
                ),
            },
        ]
    )
    for band, rate in mortality.items():
        parameters.loc[len(parameters)] = {
            "key": f"mortality_rate_{band}",
            "value": rate,
            "source": "NCHS United States Life Tables 2022 (NVSR 74-02) Table 1",
        }
    # Rules and checks the decedent size distribution reads.  The floor is a
    # rule about SOI's coverage; the last three are checks, never inputs.
    estate_returns = _soi_estate_bequest_shares()
    parameters.loc[len(parameters)] = {
        "key": "soi_estate_charitable_floor_millions_usd",
        "value": SOI_ESTATE_FLOOR_MILLIONS,
        "source": (
            "IRS SOI Estate Tax Statistics Table 1 covers estate-tax filers only "
            "(the threshold for 2023 decedents was $12.92 million), so an estate "
            "below this size is given no charitable share rather than the filing "
            "population's propensity"
        ),
    }
    parameters.loc[len(parameters)] = {
        "key": "scf_2022_median_family_net_worth_thousands",
        "value": median_family_net_worth,
        "source": (
            "Federal Reserve Survey of Consumer Finances 2022, Table 4, All "
            "families, Median. CHECK ONLY - the size distribution is fitted to "
            "the DFA aggregates and this is what says where the fit stops"
        ),
    }
    parameters.loc[len(parameters)] = {
        "key": "soi_fy2024_estate_filing_threshold_millions_usd",
        "value": 12.92,
        "source": (
            "IRC 2010(c)(3) as adjusted, Rev. Proc. 2022-38: the basic exclusion "
            "amount for decedents dying in 2023, which is SOI Table 1's own "
            "filing threshold for filing year 2024. CHECK ONLY"
        ),
    }
    parameters.loc[len(parameters)] = {
        "key": "soi_fy2024_estate_returns_above_filing_threshold",
        "value": float(sum(row[4] for row in estate_returns)),
        "source": (
            "IRS SOI Estate Tax Statistics Table 1, filing year 2024, all "
            "returns, summed over the printed size classes. CHECK ONLY on the "
            "fitted decedent size distribution's own count above that threshold"
        ),
    }
    return parameters, ladder, agm, median_family_net_worth


HEADERS = {
    "soi_capital_gains_by_rate_bracket.csv": (
        "# IRS Statistics of Income, Individual Complete Report (Publication 1304),",
        "# Table 3.5, Returns with Modified Taxable Income: Tax Generated, by Size of",
        "# Adjusted Gross Income and by Tax Rate.  Tax years 2022 and 2023.",
        "# https://www.irs.gov/pub/irs-soi/22in35tr.xls",
        "# https://www.irs.gov/pub/irs-soi/23in35tr.xls",
        "# Money amounts are thousands of dollars, as published.",
        "# statutory_rate is the preferential capital-gains rate the income was taxed",
        "# at; niit_rate is 3.8 percent where the AGI class lies at or above the",
        "# section 1411 threshold of $200,000 and zero below it.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "soi_gains_by_holding_period.csv": (
        "# IRS Statistics of Income, Individual Complete Report (Publication 1304),",
        "# Table 1.4A, Returns with Income or Loss from Sales of Capital Assets",
        "# Reported on Form 1040, Schedule D, by Size of Adjusted Gross Income.",
        "# Tax years 2022 and 2023.",
        "# https://www.irs.gov/pub/irs-soi/22in14acg.xls",
        "# https://www.irs.gov/pub/irs-soi/23in14acg.xls",
        "# Money amounts are thousands of dollars, as published.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "accrued_gains_parameters.csv": (
        "# Parameters of the accrued-gains stock and the gains-at-death channel.",
        "# Sources are named per row.  Nothing here is fitted to a benchmark: the",
        "# level of gains at death comes from Poterba & Weisbenner (2001) Table 8",
        "# over 1998 household net worth, the mortality weighting from the NCHS",
        "# 2022 life table against Federal Reserve DFA net worth by age, and the",
        "# realization elasticities from Dowd, McClelland & Muthitacharoen (2015)",
        "# with the reference rate CRS R48562 states they are adjusted to.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "decedent_estate_ladder.csv": (
        "# Decedent estate-size classes: Federal Reserve DFA household net worth by",
        "# percentile group at the anchor quarter, with the unrealized-gain share of",
        "# the gross estate that Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1",
        "# reports for an estate of that size.  Household counts come from the DFA",
        "# aggregate divided by the SCF 2022 mean, so mean_net_worth_millions_usd is",
        "# a group mean and carries no within-group dispersion.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "agm_unrealized_gain_share_by_estate_size.csv": (
        "# Avery, R., D. Grodzicki and K. Moore (2013), 'Estate vs. Capital Gains",
        "# Taxation: An Evaluation of Prospective Policies for Taxing Wealth at the",
        "# Time of Death', Federal Reserve FEDS 2013-28, Figure 1, 'Current Law'",
        "# series.  Unrealized capital gains as a share of the gross estate, by",
        "# wealth at death, projected over 2013-2023.",
        "# https://www.federalreserve.gov/pubs/feds/2013/201328/figure_data.html",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "soi_preferential_base_coverage.csv": (
        "# What the Table 3.5 preferential base is made of.  CARRIED AND NEVER",
        "# READ.  A capital-gains rate option raises the rates on long-term gains",
        "# AND qualified dividends, so this file records that both are already in",
        "# the base the model prices, and that adding a qualified-dividends column",
        "# would double-count.",
        "#",
        "# preferential_base_billions: IRS SOI Table 3.5, every preferential rate",
        "#   (0, 15, 20, 25, 28 percent), summed over AGI classes - the same",
        "#   quantity soi_capital_gains_by_rate_bracket.csv carries.",
        "# net_capital_gain_billions: Tax Foundation, Federal Capital Gains Tax",
        "#   Collections, the vendored taxfoundation_capital_gains_2022_2024.csv.",
        "# qualified_dividends_billions: IRS SOI Table 1.4, All Returns: Sources of",
        "#   Income, column 'Qualified dividends [2]', all-returns total",
        "#   (https://www.irs.gov/pub/irs-soi/22in14ar.xls, .../23in14ar.xls).",
        "#",
        "# Read base_over_gains_only first: it exceeds 1.0 in both years, and a",
        "# base holding only capital gains cannot exceed the year's capital gains.",
        "# base_over_gains_plus_qualified_dividends is then stable at 0.84-0.88",
        "# across a year in which realizations fell 27 percent; the shortfall is",
        "# gains and dividends on returns with no modified taxable income, which",
        "# no rate schedule reaches.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "decedent_carveout_ladders.csv": (
        "# Shares of decedent unrealized capital gain that a realization-at-death",
        "# proposal's stated carve-outs remove, by size of estate, on each",
        "# source's OWN published class boundaries.  Long format: one row per",
        "# (source, size class, quantity).  size_class_upper_millions_usd is inf",
        "# for the open-ended top class of each ladder.",
        "#",
        "# poterba_weisbenner_2001_table8 -- Poterba, J. and S. Weisbenner (2001),",
        "#   'The Distributional Burden of Taxing Estates and Unrealized Capital",
        "#   Gains at Death', in Rethinking Estate and Gift Taxation (Brookings),",
        "#   Table 8, lower panel ('Share of Total Unrealized Capital Gain', in",
        "#   percent), by insurance-augmented net worth of the decedent, 1998",
        "#   Survey of Consumer Finances.  Six published classes, all six carried:",
        "#   residence_gain_share is what the section 121 exclusion reaches and",
        "#   active_business_gain_share what the Green Books' family-owned-business",
        "#   election defers.",
        "# poterba_weisbenner_2001_table8_note -- the same table's note, which",
        "#   reads 'Bonds, vehicles, and collectibles are assumed to have no",
        "#   accrued capital gains'.  CARRIED AND NEVER APPLIED (applied=False):",
        "#   the tangible-personal-property relief removes nothing this base",
        "#   contains, and the Green Books exclude collectibles from it anyway.",
        "# irs_soi_estate_table1_fy2024 -- IRS Statistics of Income, Estate Tax",
        "#   Statistics, Table 1, filing year 2024 (all returns), workbook",
        "#   https://www.irs.gov/pub/irs-soi/24es01fy.xlsx, sheet columns 2",
        "#   (gross estate), 68 (bequests to a surviving spouse) and 70",
        "#   (charitable deduction), rows 9-12; money amounts as published, in",
        "#   thousands of dollars.  charitable_bequest_share is the charitable",
        "#   deduction over the gross estate NET of spousal bequests, which is the",
        "#   right denominator because the base is Poterba & Weisbenner's flow and",
        "#   that flow already excludes inter-spousal transfers.  Below",
        "#   soi_estate_charitable_floor_millions_usd (accrued_gains_parameters.csv)",
        "#   the share is not applied at all: SOI's table is estate-tax filers only.",
        "# marital_bequest_share -- the same table's bequests to a surviving spouse",
        "#   over the gross estate.  CARRIED AND NEVER APPLIED (applied=False).",
        "#   Poterba & Weisbenner's note reads 'It is assumed a decedent transfers",
        "#   his/her full estate to a surviving spouse.  Such inter-spousal",
        "#   transfers are not included in the estate totals reported above', so",
        "#   deducting the spousal relief again would be a double count.  This",
        "#   column records what that double count would cost.",
        "#",
        "# This file replaced decedent_carveout_shares.csv, which evaluated all",
        "# three ladders at five decedent-class means and therefore never read",
        "# seven of their eighteen published rows.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
    "decedent_size_distribution.csv": (
        "# Piecewise-Pareto size distribution of household net worth at death,",
        "# fitted to the Federal Reserve Distributional Financial Accounts' own",
        "# percentile-group aggregates (Z.1 companion, dfa-networth-levels.csv,",
        "# anchor quarter as recorded in accrued_gains_parameters.csv) and to",
        "# nothing else.  It is what lets a per-decedent exclusion be integrated",
        "# over a distribution instead of applied to five group means.",
        "#",
        "# For a Pareto segment anchored at wealth x_lo at cumulative population",
        "# share s_lo, the wealth it holds down to s_hi is",
        "#   N * x_lo * s_lo * (r**beta - 1) / beta,   r = s_hi / s_lo,",
        "# with beta = 1 - 1/alpha.  One unknown, one equation per segment, and",
        "# the equation is the group's own published aggregate -- so every",
        "# aggregate_net_worth_millions_usd below is reproduced exactly.  The",
        "# open-ended top class takes the index of the class below it, which is",
        "# the convention CapitalGainsBaseline.pareto_tail_index already applies",
        "# to SOI's open-ended top AGI class.",
        "#",
        "# threshold_millions_usd is the fitted wealth at percentile_share_upper,",
        "# which is the group's own LOWER wealth bound -- i.e. the 99.9th, 99th,",
        "# 90th and 50th percentiles of household net worth.",
        "#",
        "# dispersed says whether the model integrates over the segment.  Below",
        "# the 90th percentile it does not, and the note on those rows carries",
        "# both reasons the fit refuses: the index comes back below one (no",
        "# finite-mean tail) and the median it implies is twice the Survey of",
        "# Consumer Finances' published 2022 figure.  Those groups keep the group",
        "# mean in decedent_estate_ladder.csv, exactly as the five-class ladder",
        "# did, and they hold 13.4 percent of gains at death between them.",
        "# Regenerate with: python scripts/build_capital_gains_data.py",
    ),
}


def _write(name: str, frame: pd.DataFrame) -> None:
    path = OUT_DIR / name
    body = frame.to_csv(index=False, lineterminator="\n")
    path.write_text("\n".join(HEADERS[name]) + "\n" + body, encoding="utf-8")
    print(f"wrote {path.relative_to(REPO_ROOT)}  ({len(frame)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    brackets = build_bracket_table()
    _write("soi_capital_gains_by_rate_bracket.csv", brackets)
    _write("soi_gains_by_holding_period.csv", build_holding_period_table())
    _write(
        "soi_preferential_base_coverage.csv",
        build_base_coverage_table(
            brackets, OUT_DIR / "taxfoundation_capital_gains_2022_2024.csv"
        ),
    )
    parameters, ladder, agm, scf_median = build_stock_tables()
    households = float(
        parameters.loc[parameters["key"] == "households_millions", "value"].iloc[0]
    )
    _write("accrued_gains_parameters.csv", parameters)
    _write("decedent_estate_ladder.csv", ladder)
    _write("agm_unrealized_gain_share_by_estate_size.csv", agm)
    _write("decedent_carveout_ladders.csv", build_carveout_ladders())
    _write(
        "decedent_size_distribution.csv",
        build_size_distribution_table(ladder, households, scf_median),
    )
    stale = OUT_DIR / "decedent_carveout_shares.csv"
    if stale.exists():
        stale.unlink()
        print(f"removed {stale.relative_to(REPO_ROOT)}  (five-class collapse retired)")


if __name__ == "__main__":
    main()
