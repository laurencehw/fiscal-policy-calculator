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
  spousal column - what it would double-count if it removed it again.

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
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "fiscal_model" / "data_files" / "capital_gains"

SOI_TABLE_35 = "https://www.irs.gov/pub/irs-soi/{yy}in35tr.xls"
SOI_TABLE_14A = "https://www.irs.gov/pub/irs-soi/{yy}in14acg.xls"
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

#: Columns of IRS SOI *Estate Tax Statistics* Table 1 (filing year 2024) that
#: the charitable and marital shares are read from, and the printed size
#: classes, keyed by the lower bound of the class in millions of dollars.
#: Column indices are zero-based positions in the sheet as published.
SOI_ESTATE_COLUMNS = {"gross_estate": 2, "spousal_bequests": 68, "charitable": 70}
SOI_ESTATE_ROWS: tuple[tuple[float, int], ...] = (
    (0.0, 9),  # "Under $10 million"
    (10.0, 10),  # "$10 million < $20 million"
    (20.0, 11),  # "$20 million < $50 million"
    (50.0, 12),  # "$50 million or more"
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


def _mean_family_net_worth_2022_thousands() -> float:
    frame = pd.read_excel(
        io.BytesIO(_fetch(SCF_TABLES)), sheet_name="Table 4", header=None
    )
    header = [str(value) for value in frame.iloc[2].tolist()]
    column = header.index("2022") + 1  # the "Mean" column of the 2022 pair
    for index in range(frame.shape[0]):
        if str(frame.iloc[index, 0]).strip() == "All families":
            return float(frame.iloc[index, column])
    raise ValueError("SCF Table 4: 'All families' row not found")


def _agm_gain_share(estate_millions: float) -> float:
    share = AGM_GAIN_SHARE_LADDER[0][1]
    for lower, value in AGM_GAIN_SHARE_LADDER:
        if estate_millions >= lower:
            share = value
        else:
            break
    return share


def _pw_gain_shares(estate_millions: float) -> tuple[float, float]:
    """Residence and active-business shares of unrealized gain at this estate size."""
    residence, business = PW2001_TABLE_8_GAIN_SHARES[0][1:]
    for lower, res, bus in PW2001_TABLE_8_GAIN_SHARES:
        if estate_millions >= lower:
            residence, business = res, bus
        else:
            break
    return residence, business


def _soi_estate_bequest_shares() -> list[tuple[float, float, float]]:
    """Charitable and marital bequest shares by size of gross estate.

    Returns ``(lower bound in millions, charitable share, marital share)``.  The
    charitable denominator is the gross estate **net of bequests to a surviving
    spouse**, because the base these shares are applied to - Poterba &
    Weisbenner's flow of unrealized gains at death - already excludes
    inter-spousal transfers.  The marital share is over the gross estate and is
    carried only as the magnitude cross-check for what deducting it twice would
    cost.
    """
    frame = pd.read_excel(io.BytesIO(_fetch(SOI_ESTATE_TABLE_1)), header=None)
    rows = []
    for lower, index in SOI_ESTATE_ROWS:
        gross = float(frame.iloc[index, SOI_ESTATE_COLUMNS["gross_estate"]])
        spousal = float(frame.iloc[index, SOI_ESTATE_COLUMNS["spousal_bequests"]])
        charitable = float(frame.iloc[index, SOI_ESTATE_COLUMNS["charitable"]])
        non_marital = gross - spousal
        if gross <= 0 or non_marital <= 0:
            raise ValueError(f"SOI estate Table 1 row {index}: non-positive estate")
        rows.append((lower, charitable / non_marital, spousal / gross))
    return rows


def _soi_charitable_share(
    estate_millions: float, ladder: list[tuple[float, float, float]]
) -> tuple[float, float]:
    if estate_millions < SOI_ESTATE_FLOOR_MILLIONS:
        return 0.0, 0.0
    charitable, marital = ladder[0][1], ladder[0][2]
    for lower, share, spousal in ladder:
        if estate_millions >= lower:
            charitable, marital = share, spousal
        else:
            break
    return charitable, marital


def build_carveout_table(ladder: pd.DataFrame) -> pd.DataFrame:
    """Shares of decedent unrealized gain each stated carve-out removes."""
    soi = _soi_estate_bequest_shares()
    records = []
    for _, row in ladder.iterrows():
        mean_millions = float(row["mean_net_worth_millions_usd"])
        residence, business = _pw_gain_shares(mean_millions)
        charitable, marital = _soi_charitable_share(mean_millions, soi)
        records.append(
            {
                "group": row["group"],
                "mean_net_worth_millions_usd": mean_millions,
                "residence_gain_share": residence,
                "active_business_gain_share": business,
                "charitable_bequest_share": charitable,
                # Carried, never applied: see the file header.
                "marital_bequest_share": marital,
                "tangible_personal_property_gain_share": 0.0,
            }
        )
    return pd.DataFrame.from_records(records)


def build_stock_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Accrued-gains stock parameters, the decedent ladder, and the AGM ladder."""
    age_levels, networth_levels = _dfa_frames()
    mortality = _band_mortality()
    mean_family_net_worth = _mean_family_net_worth_2022_thousands()

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
    return parameters, ladder, agm


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
    "decedent_carveout_shares.csv": (
        "# Shares of decedent unrealized capital gain that a realization-at-death",
        "# proposal's stated carve-outs remove, by the decedent ladder's own",
        "# estate-size classes.",
        "#",
        "# residence_gain_share and active_business_gain_share: Poterba, J. and",
        "#   S. Weisbenner (2001), 'The Distributional Burden of Taxing Estates and",
        "#   Unrealized Capital Gains at Death', in Rethinking Estate and Gift",
        "#   Taxation (Brookings), Table 8, lower panel ('Share of Total Unrealized",
        "#   Capital Gain'), by insurance-augmented net worth of the decedent.",
        "#   Matched to a ladder class by that class's mean estate.",
        "# charitable_bequest_share: IRS Statistics of Income, Estate Tax Statistics,",
        "#   Table 1, filing year 2024 (https://www.irs.gov/pub/irs-soi/24es01fy.xlsx):",
        "#   the charitable deduction over the gross estate NET of bequests to a",
        "#   surviving spouse, by size of gross estate.  Zero for a class whose mean",
        "#   estate is under $1,000,000, which is far below SOI's filing threshold.",
        "# marital_bequest_share: the same table's bequests to a surviving spouse",
        "#   over the gross estate.  CARRIED AND NEVER APPLIED.  Poterba &",
        "#   Weisbenner's note reads 'It is assumed a decedent transfers his/her full",
        "#   estate to a surviving spouse.  Such inter-spousal transfers are not",
        "#   included in the estate totals reported above', so the spousal carve-out",
        "#   is already absent from the base and deducting it again would be a",
        "#   double count.  This column records what that double count would cost.",
        "# tangible_personal_property_gain_share: zero, for the same reason.  The",
        "#   same note reads 'Bonds, vehicles, and collectibles are assumed to have",
        "#   no accrued capital gains', and the Green Books exclude collectibles from",
        "#   their tangible-personal-property exclusion in any case.",
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
    _write("soi_capital_gains_by_rate_bracket.csv", build_bracket_table())
    _write("soi_gains_by_holding_period.csv", build_holding_period_table())
    parameters, ladder, agm = build_stock_tables()
    _write("accrued_gains_parameters.csv", parameters)
    _write("decedent_estate_ladder.csv", ladder)
    _write("agm_unrealized_gain_share_by_estate_size.csv", agm)
    _write("decedent_carveout_shares.csv", build_carveout_table(ladder))


if __name__ == "__main__":
    main()
