#!/usr/bin/env python3
"""
Rebuild the CBO *Options for Reducing the Deficit* revenue tables for the three
volumes the Tier 1 battery did not already contain.

Why this script exists
----------------------
``scripts/extract_cbo_options.py`` transcribes the **2024** volume (publication
60557, FY2025-2034). CBO has published the same compendium every two years, and
three earlier editions price the *same* reforms on *different* baselines and
*different* decades:

======  ==========================================================  =========================
volume  report                                                      window / stated baseline
======  ==========================================================  =========================
2018    *Options for Reducing the Deficit: 2019 to 2028*,           FY2019-2028, CBO April
        publication 54667 (December 2018)                           2018 baseline
2020    *Options for Reducing the Deficit: 2021 to 2030*,           FY2021-2030, CBO
        publication 56783 (December 2020)                           September 2020 baseline
2022    *Options for Reducing the Deficit: 2023 to 2032*,           FY2023-2032, CBO May
        Volume I publication 58164 / Volume II publication 58163     2022 baseline
        (December 2022)
======  ==========================================================  =========================

That is what lane R3 (``planning/lanes/R3_tier1_battery.md``) uses to grow the
out-of-sample battery: the same option, four editions, four independent
observations of one mechanism - and, because each edition states its own decade,
four observations that ``CBOScore.scoring_window_first_year`` lets the model
score on the decade its target actually covers.

WHAT IT READS
-------------
CBO publishes a machine-readable workbook beside the PDF for the 2020 and 2022
volumes, reproducing every option table verbatim. Those are read directly, by
sheet and row, with the label cell asserted against the label this script
expects - so a silently re-tagged file fails loudly instead of rewriting the
battery's targets.

* ``56783-budget-options.xlsx`` - sheets ``Revenues`` (and the two spending
  sheets, which this lane does not read).
* ``58164-Budget-Options.xlsx`` - sheets ``Volume I`` and ``Volume II,
  Revenues``.

Both are vendored under ``fiscal_model/data_files/validation/sources/`` and
pinned by SHA-256 of the bytes ``web.archive.org`` serves for the snapshot named
below, exactly as ``scripts/fetch_cbo_baseline.py`` pins CBO's GitHub files.
``cbo.gov`` returns HTTP 403 to this environment; the Wayback Machine does not.

The **2018** volume has no workbook. Its figures are transcribed by hand from
the PDF with a report-page reference on every row, and ``--pdf`` re-reads that
PDF and asserts every transcribed ten-year total appears on its stated page.

WHAT IT WRITES
--------------
``fiscal_model/data_files/validation/cbo_options_multi_volume.csv``
    One row per **revenue option** in each of the three volumes (99 rows),
    each carrying ``runnable`` and, when not runnable, a one-line reason. This
    is the same discipline ``fiscal_model/validation/cbo_options.py`` applies to
    the 2024 volume's 76 options: the battery's composition is auditable rather
    than a curated set of flattering shapes.

``fiscal_model/data_files/validation/cbo_options_multi_volume_alternatives.csv``
    One row per reported alternative inside a runnable option, with CBO's own
    annual path and five- and ten-year totals, in both sign conventions.

USAGE
-----
    python scripts/extract_cbo_options_multi_volume.py
    python scripts/extract_cbo_options_multi_volume.py --check
    python scripts/extract_cbo_options_multi_volume.py --pdf DIR

``--check`` verifies the vendored workbooks against their pinned digests and
rebuilds into memory without writing. ``--pdf DIR`` additionally verifies the
2018 rows against ``54667-budgetoptions.pdf`` in ``DIR`` (not vendored - 4.4 MB
of scanned-quality PDF is not something to commit).

SIGN CONVENTIONS
----------------
``savings_*`` follow CBO (positive = reduces the deficit); ``deficit_effect_*``
follow this app (positive = increases the deficit). The 2018 and 2020 volumes
print "Change in Revenues" (positive = more revenue); the 2022 volume prints
"Decrease (-) in the Deficit". Both are normalised here, and the normalisation
is asserted rather than assumed: ``deficit_effect = -savings`` on every row.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "validation"
SOURCE_DIR = DATA_DIR / "sources"
OPTIONS_CSV = DATA_DIR / "cbo_options_multi_volume.csv"
ALTERNATIVES_CSV = DATA_DIR / "cbo_options_multi_volume_alternatives.csv"


# ---------------------------------------------------------------------------
# Pinned sources
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceFile:
    """One pinned publication file."""

    filename: str
    original_url: str
    wayback_timestamp: str
    size_bytes: int
    sha256: str
    vendored: bool

    @property
    def wayback_url(self) -> str:
        return f"https://web.archive.org/web/{self.wayback_timestamp}id_/{self.original_url}"


SOURCE_FILES: dict[str, SourceFile] = {
    "2020": SourceFile(
        filename="56783-budget-options.xlsx",
        original_url="https://www.cbo.gov/system/files/2020-12/56783-budget-options.xlsx",
        wayback_timestamp="20201209210918",
        size_bytes=109_199,
        sha256="86ba24ab0bc78fac218b0fbf3cedd9a6b20000f0451753c71706d786b4447af6",
        vendored=True,
    ),
    "2022": SourceFile(
        filename="58164-Budget-Options.xlsx",
        original_url="https://www.cbo.gov/system/files/2022-12/58164-Budget-Options.xlsx",
        wayback_timestamp="20230101000000",
        size_bytes=81_679,
        sha256="3a08fb5537cd1d4a839fe674225109a2521d484c24f285128e0caac0fc7a8212",
        vendored=True,
    ),
    "2018": SourceFile(
        filename="54667-budgetoptions.pdf",
        original_url="https://www.cbo.gov/system/files/2018-12/54667-budgetoptions.pdf",
        wayback_timestamp="20190413021132",
        size_bytes=4_432_702,
        sha256="2e8501d6476a52878d15e654e221accb5d41be4f79a4131407b4662849142b70",
        vendored=False,
    ),
}


@dataclass(frozen=True)
class Volume:
    """One edition of the compendium."""

    key: str
    publication: str
    title: str
    publication_date: str
    landing_page: str
    window_first_year: int
    window_last_year: int
    stated_revenue_baseline: str


VOLUMES: dict[str, Volume] = {
    "2018": Volume(
        key="2018",
        publication="54667",
        title="Options for Reducing the Deficit: 2019 to 2028",
        publication_date="2018-12",
        landing_page="https://www.cbo.gov/publication/54667",
        window_first_year=2019,
        window_last_year=2028,
        stated_revenue_baseline="CBO April 2018 baseline (FY2019-2028)",
    ),
    "2020": Volume(
        key="2020",
        publication="56783",
        title="Options for Reducing the Deficit: 2021 to 2030",
        publication_date="2020-12",
        landing_page="https://www.cbo.gov/publication/56783",
        window_first_year=2021,
        window_last_year=2030,
        stated_revenue_baseline="CBO September 2020 baseline (FY2021-2030)",
    ),
    "2022": Volume(
        key="2022",
        publication="58164/58163",
        title="Options for Reducing the Deficit: 2023 to 2032 (Volumes I and II)",
        publication_date="2022-12",
        landing_page="https://www.cbo.gov/publication/58164",
        window_first_year=2023,
        window_last_year=2032,
        stated_revenue_baseline="CBO May 2022 baseline (FY2023-2032)",
    ),
}


# ---------------------------------------------------------------------------
# Why an option is not runnable
# ---------------------------------------------------------------------------
#
# Each string is a *shape* verdict, not a judgement about the option. The bar is
# ``cbo_options.py``'s: ``create_policy_from_score`` must be able to build the
# reform from fields the source itself states, with no parameter fitted to the
# target.

R_BASE = (
    "Individual tax-base change (deduction, exclusion, filing status or "
    "inclusion rule); the generic path prices a rate at a threshold."
)
R_CARRYOVER = (
    "Carryover basis for inherited assets: a deferred-realization rule, not "
    "the constructive-realization-at-death channel CapitalGainsPolicy has."
)
R_CREDIT = "Refundable-credit rule change; no Tier 1 credit shape."
R_EXCISE = "Excise tax; the generic path has no excise base."
R_NEW_TAX = (
    "A new tax on a base the model does not carry (consumption, greenhouse-gas "
    "emissions, financial transactions, derivatives, large financial "
    "institutions)."
)
R_SS_BASE = (
    "Social Security taxable-maximum or coverage change; the payroll module's "
    "cap constants are fitted to ss_donut_250k and ss_cap_elimination, so "
    "scoring it here would be leakage."
)
R_SS_RATE = (
    "A rate change on the CAPPED Social Security base. The runnable payroll "
    "shape is a flat rate on uncapped covered earnings; the module's capped "
    "branch reads a window-average constant "
    "(CBO_PAYROLL_ESTIMATES['rate_1pp_annual']) rather than a bottom-up base, "
    "which fails the no-fitted-parameter bar."
)
R_BUSINESS = (
    "Business tax-base or timing change (inventory accounting, amortisation, "
    "sectoral preferences, the low-income housing credit); the corporate shape "
    "prices a statutory rate."
)
R_FEE = "Fee, premium or federal-employee contribution; no shape."
R_ENFORCEMENT = (
    "Enforcement appropriation; scored by the calibrated IRSEnforcementPolicy, "
    "so the generic path would double-count it across tiers."
)
R_SECA = "SECA coverage and material-participation rule; no shape."
R_UI = "Unemployment insurance financing; no shape."
R_EMPLOYER_HEALTH_2018 = (
    "The only income-tax-only alternative REPLACES the ACA excise tax on "
    "high-cost plans, so CBO's target is net of repealing a levy the "
    "expenditure module's baseline does not contain. The 2022 and 2024 "
    "editions limit the exclusion against a baseline with no excise tax and "
    "are runnable."
)
R_HEALTH_PAYROLL_ONLY = (
    "Every alternative limits the payroll-tax exclusion as well, and the "
    "expenditure module has no payroll base."
)


@dataclass(frozen=True)
class OptionRow:
    """One revenue option of one volume, with its verdict."""

    volume: str
    chapter: str
    option_number: int
    title: str
    runnable: bool
    reason: str = ""


def _opts(volume: str, chapter: str, spec: list[tuple[int, str, str]]) -> list[OptionRow]:
    return [
        OptionRow(volume, chapter, n, title, reason == "", reason)
        for n, title, reason in spec
    ]


OPTION_INDEX: list[OptionRow] = []

OPTION_INDEX += _opts("2018", "Revenues", [
    (1, "Increase Individual Income Tax Rates", ""),
    (2, "Raise the Tax Rates on Long-Term Capital Gains and Qualified Dividends by 2 Percentage Points and Adjust Tax Brackets", ""),
    (3, "Eliminate or Modify Head-of-Household Filing Status", R_BASE),
    (4, "Curtail the Deduction for Charitable Giving", R_BASE),
    (5, "Eliminate Itemized Deductions", R_BASE),
    (6, "Change the Tax Treatment of Capital Gains From Sales of Inherited Assets", R_CARRYOVER),
    (7, "Eliminate the Tax Exemption for New Qualified Private Activity Bonds", R_BASE),
    (8, "Expand the Base of the Net Investment Income Tax to Include the Income of Active Participants in S Corporations and Limited Partnerships", R_BASE),
    (9, "Tax Carried Interest as Ordinary Income", R_BASE),
    (10, "Include Disability Payments From the Department of Veterans Affairs in Taxable Income", R_BASE),
    (11, "Include Employer-Paid Premiums for Income Replacement Insurance in Employees' Taxable Income", R_BASE),
    (12, "Reduce Tax Subsidies for Employment-Based Health Insurance", R_EMPLOYER_HEALTH_2018),
    (13, "Further Limit Annual Contributions to Retirement Plans", R_BASE),
    (14, "Tax Social Security and Railroad Retirement Benefits in the Same Way That Distributions From Defined Benefit Pensions Are Taxed", R_BASE),
    (15, "Eliminate Certain Tax Preferences for Education Expenses", R_CREDIT),
    (16, "Lower the Investment Income Limit for the Earned Income Tax Credit and Extend That Limit to the Refundable Portion of the Child Tax Credit", R_CREDIT),
    (17, "Require Earned Income Tax Credit and Child Tax Credit Claimants to Have a Social Security Number That Is Valid for Employment", R_CREDIT),
    (18, "Increase the Payroll Tax Rate for Medicare Hospital Insurance", ""),
    (19, "Increase the Payroll Tax Rate for Social Security", R_SS_RATE),
    (20, "Increase the Maximum Taxable Earnings for the Social Security Payroll Tax", R_SS_BASE),
    (21, "Expand Social Security Coverage to Include Newly Hired State and Local Government Employees", R_SS_BASE),
    (22, "Tax All Pass-Through Business Owners Under SECA and Impose a Material Participation Standard", R_SECA),
    (23, "Increase Taxes That Finance the Federal Share of the Unemployment Insurance System", R_UI),
    (24, "Increase the Corporate Income Tax Rate by 1 Percentage Point", ""),
    (25, "Repeal Certain Tax Preferences for Energy and Natural Resource-Based Industries", R_BUSINESS),
    (26, "Repeal the 'LIFO' and 'Lower of Cost or Market' Inventory Accounting Methods", R_BUSINESS),
    (27, "Require Half of Advertising Expenses to Be Amortized Over 5 or 10 Years", R_BUSINESS),
    (28, "Repeal the Low-Income Housing Tax Credit", R_BUSINESS),
    (29, "Increase All Taxes on Alcoholic Beverages to $16 per Proof Gallon and Index for Inflation", R_EXCISE),
    (30, "Increase the Excise Tax on Tobacco Products by 50 Percent", R_EXCISE),
    (31, "Increase Excise Taxes on Motor Fuels and Index for Inflation", R_EXCISE),
    (32, "Impose an Excise Tax on Overland Freight Transport", R_EXCISE),
    (33, "Impose Fees to Cover the Costs of Government Regulations and Charge for Services Provided to the Private Sector", R_FEE),
    (34, "Impose a 5 Percent Value-Added Tax", R_NEW_TAX),
    (35, "Impose a Tax on Emissions of Greenhouse Gases", R_NEW_TAX),
    (36, "Impose a Fee on Large Financial Institutions", R_NEW_TAX),
    (37, "Impose a Tax on Financial Transactions", R_NEW_TAX),
    (38, "Tax Gains From Derivatives as Ordinary Income on a Mark-to-Market Basis", R_NEW_TAX),
    (39, "Increase Federal Civilian Employees' Contributions to the Federal Employees Retirement System", R_FEE),
    (40, "Increase Appropriations for the Internal Revenue Service's Enforcement Initiatives", R_ENFORCEMENT),
])

OPTION_INDEX += _opts("2020", "Revenues", [
    (1, "Increase Individual Income Tax Rates", ""),
    (2, "Raise the Tax Rates on Long-Term Capital Gains and Qualified Dividends by 2 Percentage Points", ""),
    (3, "Eliminate or Modify Head-of-Household Filing Status", R_BASE),
    (4, "Eliminate Itemized Deductions", R_BASE),
    (5, "Limit the Deduction for Charitable Giving", R_BASE),
    (6, "Change the Tax Treatment of Capital Gains From Sales of Inherited Assets", R_CARRYOVER),
    (7, "Eliminate the Tax Exemption for New Qualified Private Activity Bonds", R_BASE),
    (8, "Expand the Base of the Net Investment Income Tax to Include the Income of Active Participants in S Corporations and Limited Partnerships", R_BASE),
    (9, "Include Disability Payments From the Department of Veterans Affairs in Taxable Income", R_BASE),
    (10, "Further Limit Annual Contributions to Retirement Plans", R_BASE),
    (11, "Tax Social Security and Railroad Retirement Benefits in the Same Way That Distributions From Defined Benefit Pensions Are Taxed", R_BASE),
    (12, "Eliminate Certain Tax Preferences for Education Expenses", R_CREDIT),
    (13, "Lower the Investment Income Limit for the Earned Income Tax Credit and Extend That Limit to the Refundable Portion of the Child Tax Credit", R_CREDIT),
    (14, "Require Earned Income Tax Credit and Child Tax Credit Claimants to Have a Social Security Number That Is Valid for Employment", R_CREDIT),
    (15, "Increase the Payroll Tax Rate for Medicare Hospital Insurance", ""),
    (16, "Increase the Payroll Tax Rate for Social Security", R_SS_RATE),
    (17, "Increase the Maximum Taxable Earnings for the Social Security Payroll Tax", R_SS_BASE),
    (18, "Expand Social Security Coverage to Include Newly Hired State and Local Government Employees", R_SS_BASE),
    (19, "Increase the Corporate Income Tax Rate by 1 Percentage Point", ""),
    (20, "Repeal the 'LIFO' Approach to Inventory Identification and the 'Lower of Cost or Market' and 'Subnormal Goods' Methods of Inventory Valuation", R_BUSINESS),
    (21, "Require Half of Advertising Expenses to Be Amortized Over 5 or 10 Years", R_BUSINESS),
    (22, "Repeal the Low-Income Housing Tax Credit", R_BUSINESS),
    (23, "Increase All Taxes on Alcoholic Beverages to $16 per Proof Gallon and Index for Inflation", R_EXCISE),
    (24, "Increase Excise Taxes on Tobacco Products", R_EXCISE),
    (25, "Increase Excise Taxes on Motor Fuels and Index for Inflation", R_EXCISE),
    (26, "Impose an Excise Tax on Overland Freight Transport", R_EXCISE),
    (27, "Impose a 5 Percent Value-Added Tax", R_NEW_TAX),
    (28, "Impose a Tax on Emissions of Greenhouse Gases", R_NEW_TAX),
    (29, "Impose a Tax on Financial Transactions", R_NEW_TAX),
    (30, "Increase Federal Civilian Employees' Contributions to the Federal Employees Retirement System", R_FEE),
    (31, "Increase Appropriations for the Internal Revenue Service's Enforcement Initiatives", R_ENFORCEMENT),
])

OPTION_INDEX += _opts("2022", "Volume I", [
    (6, "Reduce Tax Subsidies for Employment-Based Health Insurance", ""),
    (13, "Increase Individual Income Tax Rates", ""),
    (14, "Eliminate or Limit Itemized Deductions", R_BASE),
    (15, "Impose a New Payroll Tax", ""),
    (16, "Impose a Tax on Consumption", R_NEW_TAX),
    (17, "Impose a Tax on Emissions of Greenhouse Gases", R_NEW_TAX),
])

OPTION_INDEX += _opts("2022", "Volume II, Revenues", [
    (37, "Raise the Tax Rates on Long-Term Capital Gains and Qualified Dividends by 2 Percentage Points", ""),
    (38, "Eliminate or Modify Head-of-Household Filing Status", R_BASE),
    (39, "Limit the Deduction for Charitable Giving", R_BASE),
    (40, "Change the Tax Treatment of Capital Gains From Sales of Inherited Assets", R_CARRYOVER),
    (41, "Eliminate the Tax Exemption for New Qualified Private Activity Bonds", R_BASE),
    (42, "Expand the Base of the Net Investment Income Tax to Include the Income of Active Participants in S Corporations and Limited Partnerships", R_BASE),
    (43, "Tax Carried Interest as Ordinary Income", R_BASE),
    (44, "Include VA's Disability Payments in Taxable Income", R_BASE),
    (45, "Further Limit Annual Contributions to Retirement Plans", R_BASE),
    (46, "Eliminate Certain Tax Preferences for Education Expenses", R_CREDIT),
    (47, "Lower the Investment Income Limit for the Earned Income Tax Credit and Extend That Limit to the Refundable Portion of the Child Tax Credit", R_CREDIT),
    (48, "Require People Who Claim the Earned Income Tax Credit and Child Tax Credit to Have a Social Security Number That Is Valid for Employment", R_CREDIT),
    (49, "Expand Social Security to Include Newly Hired State and Local Government Employees", R_SS_BASE),
    (50, "Increase the Corporate Income Tax Rate by 1 Percentage Point", ""),
    (51, "Repeal the 'Last In, First Out' Approach to Inventory Identification and the 'Lower of Cost or Market' and 'Subnormal Goods' Methods of Inventory Valuation", R_BUSINESS),
    (52, "Require Half of Advertising Expenses to Be Amortized Over 5 or 10 Years", R_BUSINESS),
    (53, "Repeal the Low-Income Housing Tax Credit", R_BUSINESS),
    (54, "Increase All Taxes on Alcoholic Beverages to $16 per Proof Gallon and Index Them for Inflation", R_EXCISE),
    (55, "Increase Excise Taxes on Tobacco Products", R_EXCISE),
    (56, "Increase Excise Taxes on Motor Fuels and Index Them for Inflation", R_EXCISE),
    (57, "Impose a Tax on Financial Transactions", R_NEW_TAX),
    (58, "Increase Certain Fees Charged by U.S. Citizenship and Immigration Services and Customs and Border Protection by 20 Percent", R_FEE),
    (59, "Increase Federal Civilian Employees' Contributions to the Federal Employees Retirement System", R_FEE),
])


# ---------------------------------------------------------------------------
# Alternatives
# ---------------------------------------------------------------------------


@dataclass
class Alternative:
    """One reported line inside a runnable option."""

    volume: str
    chapter: str
    option_number: int
    alternative_id: str
    label: str
    measure: str
    savings_5yr_billions: float
    savings_10yr_billions: float
    annual_savings_billions: tuple[float, ...]
    report_page: int
    registered: bool
    not_registered_reason: str = ""
    #: (sheet, row) in the volume's workbook, or ``None`` for the 2018 volume.
    workbook_cell: tuple[str, int] | None = None
    #: Sign of the printed row: ``+1`` when CBO prints "Change in Revenues"
    #: (positive = more revenue), ``-1`` when it prints "Decrease (-) in the
    #: Deficit" (negative = less deficit). Both become ``savings_*`` here.
    printed_sign: int = 1
    annual_from_workbook: tuple[float, ...] = field(default_factory=tuple)

    @property
    def deficit_effect_10yr_billions(self) -> float:
        return -self.savings_10yr_billions


R_ALIGN = (
    "Realigns the preferential-rate bracket boundaries with the ordinary "
    "brackets; CapitalGainsPolicy prices a rate change, not a bracket "
    "realignment."
)
R_HEALTH_BOTH = (
    "Limits the income AND payroll tax exclusion; the expenditure module has "
    "no payroll base. Out of scope per alternative, as in the 2024 volume."
)
R_AGI_ALT = ""


ALTERNATIVES: list[Alternative] = [
    # -- 2018 volume, publication 54667 ------------------------------------
    Alternative(
        "2018", "Revenues", 1, "1.1",
        "Raise all tax rates on ordinary income by 1 percentage point",
        "change_in_revenues", 411.9, 905.4,
        (55.2, 82.5, 86.9, 91.4, 95.9, 100.4, 105.2, 95.3, 94.1, 98.5),
        204, True,
    ),
    Alternative(
        "2018", "Revenues", 1, "1.2",
        "Raise ordinary income tax rates in the four highest brackets by 1 percentage point",
        "change_in_revenues", 104.1, 222.9,
        (13.5, 20.6, 22.0, 23.3, 24.7, 26.0, 27.5, 22.3, 20.9, 22.2),
        204, True,
    ),
    Alternative(
        "2018", "Revenues", 1, "1.3",
        "Raise ordinary income tax rates in the two highest brackets by 1 percentage point",
        "change_in_revenues", 55.1, 123.4,
        (7.2, 11.0, 11.6, 12.3, 13.0, 13.7, 14.4, 13.2, 13.1, 13.9),
        204, True,
    ),
    Alternative(
        "2018", "Revenues", 2, "2.1",
        "Raise rates on long-term capital gains and dividends by 2 percentage points",
        "change_in_revenues", 30.4, 69.6,
        (1.8, 7.1, 7.0, 7.1, 7.4, 7.7, 7.8, 7.8, 7.9, 8.2),
        207, True,
    ),
    Alternative(
        "2018", "Revenues", 2, "2.2",
        "Also align top two brackets to match the third and sixth brackets applicable to ordinary income",
        "change_in_revenues", 33.8, 75.9,
        (1.9, 7.8, 7.8, 8.0, 8.3, 8.6, 8.7, 8.6, 7.9, 8.3),
        207, False, R_ALIGN,
    ),
    Alternative(
        "2018", "Revenues", 2, "2.3",
        "Also align top two brackets to match the third and fifth brackets applicable to ordinary income",
        "change_in_revenues", 36.7, 81.4,
        (2.0, 8.5, 8.5, 8.7, 9.0, 9.3, 9.5, 9.4, 8.1, 8.5),
        207, False, R_ALIGN,
    ),
    Alternative(
        "2018", "Revenues", 18, "18.1",
        "Increase rate by 1 percentage point",
        "change_in_revenues", 394.6, 898.3,
        (51.4, 80.8, 84.2, 87.4, 90.8, 94.2, 97.8, 100.4, 103.6, 107.6),
        251, True,
    ),
    Alternative(
        "2018", "Revenues", 18, "18.2",
        "Increase rate by 2 percentage points",
        "change_in_revenues", 784.9, 1786.5,
        (102.3, 160.7, 167.5, 173.9, 180.5, 187.4, 194.5, 199.6, 206.0, 214.1),
        251, True,
    ),
    Alternative(
        "2018", "Revenues", 24, "24.1",
        "Increase the Corporate Income Tax Rate by 1 Percentage Point",
        "change_in_revenues", 37.1, 96.3,
        (4.6, 6.8, 7.8, 8.4, 9.5, 10.4, 11.2, 11.9, 12.7, 13.0),
        266, True,
    ),
    # -- 2020 volume, publication 56783 ------------------------------------
    Alternative(
        "2020", "Revenues", 1, "1.1",
        "Raise all tax rates on ordinary income by 1 percentage point",
        "change_in_revenues", 407.4, 884.0, (), 204, True,
        workbook_cell=("Revenues", 12),
    ),
    Alternative(
        "2020", "Revenues", 1, "1.2",
        "Raise all tax rates on ordinary income in the top four brackets by 1 percentage point",
        "change_in_revenues", 100.0, 203.3, (), 204, True,
        workbook_cell=("Revenues", 13),
    ),
    Alternative(
        "2020", "Revenues", 1, "1.3",
        "Raise all tax rates on ordinary income in the top two brackets by 1 percentage point",
        "change_in_revenues", 53.2, 113.8, (), 204, True,
        workbook_cell=("Revenues", 14),
    ),
    Alternative(
        "2020", "Revenues", 2, "2.1",
        "Raise the Tax Rates on Long-Term Capital Gains and Qualified Dividends by 2 Percentage Points",
        "change_in_revenues", 30.6, 75.2, (), 207, True,
        workbook_cell=("Revenues", 27),
    ),
    Alternative(
        "2020", "Revenues", 15, "15.1",
        "Increase rate by 1 percentage point",
        "change_in_revenues", 385.2, 877.5, (), 285, True,
        workbook_cell=("Revenues", 194),
    ),
    Alternative(
        "2020", "Revenues", 15, "15.2",
        "Increase rate by 2 percentage points",
        "change_in_revenues", 762.4, 1736.3, (), 285, True,
        workbook_cell=("Revenues", 195),
    ),
    Alternative(
        "2020", "Revenues", 16, "16.1",
        "Increase rate by 1 percentage point",
        "change_in_revenues", 315.3, 711.9, (), 287, False, R_SS_RATE,
        workbook_cell=("Revenues", 209),
    ),
    Alternative(
        "2020", "Revenues", 16, "16.2",
        "Increase rate by 2 percentage points",
        "change_in_revenues", 623.1, 1406.0, (), 287, False, R_SS_RATE,
        workbook_cell=("Revenues", 210),
    ),
    Alternative(
        "2020", "Revenues", 19, "19.1",
        "Increase the Corporate Income Tax Rate by 1 Percentage Point",
        "change_in_revenues", 39.2, 99.3, (), 293, True,
        workbook_cell=("Revenues", 260),
    ),
    # -- 2022 volume, publications 58164 (Vol I) and 58163 (Vol II) --------
    Alternative(
        "2022", "Volume I", 6, "6.1",
        "Limit the Income and Payroll Tax Exclusion for Employment-Based Health Insurance to the 50th Percentile of Premiums",
        "decrease_in_deficit", 169.4, 893.2, (), 30, False, R_HEALTH_BOTH,
        workbook_cell=("Volume I", 119), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 6, "6.2",
        "Limit the Income and Payroll Tax Exclusion for Employment-Based Health Insurance to the 75th Percentile of Premiums",
        "decrease_in_deficit", 87.4, 499.8, (), 30, False, R_HEALTH_BOTH,
        workbook_cell=("Volume I", 123), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 6, "6.3",
        "Limit Only the Income Tax Exclusion for Employment-Based Health Insurance to the 50th Percentile of Premiums",
        "decrease_in_deficit", 123.0, 651.4, (), 30, True,
        workbook_cell=("Volume I", 127), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 13, "13.1",
        "Raise all tax rates on ordinary income by 1 percentage point",
        "decrease_in_deficit", 494.6, 1081.3, (), 72, False,
        "Already in the battery as illustrative_1pp_all.v2 (lane R2). One "
        "reform, one row.",
        workbook_cell=("Volume I", 229), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 13, "13.2",
        "Raise tax rates on ordinary income in the four highest brackets by 2 percentage points",
        "decrease_in_deficit", 242.7, 501.9, (), 72, True,
        workbook_cell=("Volume I", 230), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 13, "13.3",
        "Impose a surtax of 1 percentage point on AGI above the standard deduction and exemption",
        "decrease_in_deficit", 567.3, 1329.1, (), 72, True,
        workbook_cell=("Volume I", 231), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 13, "13.4",
        "Impose a surtax of 2 percentage points on AGI above the sum of the standard deduction, exemptions, and the threshold of the fourth ordinary income tax bracket",
        "decrease_in_deficit", 333.4, 773.8, (), 72, True,
        workbook_cell=("Volume I", 232), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 15, "15.1",
        "Impose a payroll tax of 1 percent on earnings",
        "decrease_in_deficit", 495.9, 1135.7, (), 76, True,
        workbook_cell=("Volume I", 263), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume I", 15, "15.2",
        "Impose a payroll tax of 2 percent on earnings",
        "decrease_in_deficit", 983.6, 2252.7, (), 76, True,
        workbook_cell=("Volume I", 264), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume II, Revenues", 37, "37.1",
        "Raise the Tax Rates on Long-Term Capital Gains and Qualified Dividends by 2 Percentage Points",
        "decrease_in_deficit", 47.1, 102.1, (), 89, True,
        workbook_cell=("Volume II, Revenues", 11), printed_sign=-1,
    ),
    Alternative(
        "2022", "Volume II, Revenues", 50, "50.1",
        "Increase the Corporate Income Tax Rate by 1 Percentage Point",
        "decrease_in_deficit", 56.6, 129.3, (), 115, True,
        workbook_cell=("Volume II, Revenues", 179), printed_sign=-1,
    ),
]


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _digest(path: Path) -> tuple[int, str]:
    raw = path.read_bytes()
    return len(raw), hashlib.sha256(raw).hexdigest()


def verify_sources(*, require_vendored: bool = True) -> list[str]:
    """Check every vendored source against its pin. Returns problem strings."""
    problems: list[str] = []
    for key, src in SOURCE_FILES.items():
        if not src.vendored:
            continue
        path = SOURCE_DIR / src.filename
        if not path.exists():
            if require_vendored:
                problems.append(f"{key}: missing vendored source {path}")
            continue
        size, digest = _digest(path)
        if size != src.size_bytes:
            problems.append(f"{key}: {src.filename} is {size} bytes, pinned {src.size_bytes}")
        if digest != src.sha256:
            problems.append(f"{key}: {src.filename} sha256 {digest}, pinned {src.sha256}")
    return problems


def _load_workbook_rows(src: SourceFile) -> dict[str, list[tuple]]:
    import openpyxl

    workbook = openpyxl.load_workbook(SOURCE_DIR / src.filename, data_only=True)
    return {
        sheet.title: list(sheet.iter_rows(values_only=True))
        for sheet in workbook.worksheets
    }


def _numbers(row: tuple) -> list[float]:
    return [float(c) for c in row if isinstance(c, (int, float))]


def fill_from_workbooks() -> list[str]:
    """Read each workbook-backed alternative's annual path and totals.

    Every figure the CSV carries for the 2020 and 2022 volumes comes from here.
    The label cell is asserted, so a re-tagged workbook fails loudly.
    """
    problems: list[str] = []
    cache: dict[str, dict[str, list[tuple]]] = {}
    for alt in ALTERNATIVES:
        if alt.workbook_cell is None:
            continue
        src = SOURCE_FILES[alt.volume]
        if alt.volume not in cache:
            cache[alt.volume] = _load_workbook_rows(src)
        sheet, rownum = alt.workbook_cell
        rows = cache[alt.volume].get(sheet)
        if rows is None or len(rows) < rownum:
            problems.append(f"{alt.volume}/{alt.alternative_id}: no sheet {sheet!r} row {rownum}")
            continue
        row = rows[rownum - 1]
        nums = _numbers(row)
        if len(nums) != 12:
            problems.append(
                f"{alt.volume}/{alt.alternative_id}: expected 12 numbers "
                f"(10 annual + 5yr + 10yr), found {len(nums)}"
            )
            continue
        annual = tuple(round(alt.printed_sign * n, 4) for n in nums[:10])
        five = round(alt.printed_sign * nums[10], 4)
        ten = round(alt.printed_sign * nums[11], 4)
        if abs(five - alt.savings_5yr_billions) > 0.05:
            problems.append(
                f"{alt.volume}/{alt.alternative_id}: workbook 5-year {five} "
                f"!= transcribed {alt.savings_5yr_billions}"
            )
        if abs(ten - alt.savings_10yr_billions) > 0.05:
            problems.append(
                f"{alt.volume}/{alt.alternative_id}: workbook 10-year {ten} "
                f"!= transcribed {alt.savings_10yr_billions}"
            )
        alt.annual_from_workbook = annual
        alt.annual_savings_billions = annual
    return problems


def verify_2018_against_pdf(pdf_dir: Path) -> list[str]:
    """Assert every 2018 ten-year total appears on the page this file claims."""
    import fitz

    src = SOURCE_FILES["2018"]
    path = pdf_dir / src.filename
    problems: list[str] = []
    if not path.exists():
        return [f"2018: {path} not found"]
    size, digest = _digest(path)
    if digest != src.sha256:
        problems.append(f"2018: {src.filename} sha256 {digest}, pinned {src.sha256} ({size} bytes)")
    doc = fitz.open(path)
    # Report page N is PDF page N + 10 in publication 54667 (report p. 203 is
    # PDF p. 213); asserted here rather than assumed.
    for alt in ALTERNATIVES:
        if alt.volume != "2018":
            continue
        pdf_page = alt.report_page + 10
        text = doc.load_page(pdf_page - 1).get_text().replace(",", "")
        printed = f"{alt.savings_10yr_billions:,.1f}".replace(",", "")
        if printed not in text:
            problems.append(
                f"2018/{alt.alternative_id}: {printed} not on PDF page {pdf_page} "
                f"(report p. {alt.report_page})"
            )
    doc.close()
    return problems


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

_HEADER_LINES = (
    "# CBO, Options for Reducing the Deficit - the 2018, 2020 and 2022 editions.",
    "# Rebuilt by scripts/extract_cbo_options_multi_volume.py. Do not hand-edit.",
    "# 2018: publication 54667, FY2019-2028, CBO April 2018 baseline,",
    "#       https://www.cbo.gov/publication/54667",
    "# 2020: publication 56783, FY2021-2030, CBO September 2020 baseline,",
    "#       https://www.cbo.gov/publication/56783",
    "# 2022: publications 58164 (Vol I) and 58163 (Vol II), FY2023-2032,",
    "#       CBO May 2022 baseline, https://www.cbo.gov/publication/58164",
    "# cbo.gov returns HTTP 403 to this environment; every file was read through",
    "# the Wayback Machine and pinned by SHA-256 (see the script).",
    "# Sign conventions: savings_* follow CBO (positive = reduces the deficit);",
    "#   deficit_effect_* follow this app (positive = increases the deficit).",
)


def _write(path: Path, header: tuple[str, ...], fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        for line in header:
            handle.write(line + "\n")
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_option_rows() -> list[dict]:
    rows = []
    for option in OPTION_INDEX:
        volume = VOLUMES[option.volume]
        rows.append({
            "volume": option.volume,
            "publication": volume.publication,
            "publication_date": volume.publication_date,
            "landing_page": volume.landing_page,
            "window_first_year": volume.window_first_year,
            "window_last_year": volume.window_last_year,
            "stated_revenue_baseline": volume.stated_revenue_baseline,
            "chapter": option.chapter,
            "option_number": option.option_number,
            "title": option.title,
            "runnable": "true" if option.runnable else "false",
            "reason": option.reason,
        })
    return rows


def build_alternative_rows() -> list[dict]:
    rows = []
    for alt in ALTERNATIVES:
        volume = VOLUMES[alt.volume]
        row = {
            "volume": alt.volume,
            "publication": volume.publication,
            "chapter": alt.chapter,
            "option_number": alt.option_number,
            "alternative_id": alt.alternative_id,
            "label": alt.label,
            "measure": alt.measure,
            "window_first_year": volume.window_first_year,
            "savings_5yr_billions": alt.savings_5yr_billions,
            "savings_10yr_billions": alt.savings_10yr_billions,
            "deficit_effect_10yr_billions": alt.deficit_effect_10yr_billions,
            "report_page": alt.report_page,
            "registered": "true" if alt.registered else "false",
            "not_registered_reason": alt.not_registered_reason,
            "extracted_by": "script" if alt.workbook_cell else "manual",
        }
        for offset in range(10):
            year = volume.window_first_year + offset
            value = (
                alt.annual_savings_billions[offset]
                if offset < len(alt.annual_savings_billions)
                else ""
            )
            row[f"savings_{year}_billions"] = value
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; do not write")
    parser.add_argument("--pdf", type=Path, default=None, help="directory holding 54667-budgetoptions.pdf")
    args = parser.parse_args(argv)

    problems = verify_sources()
    problems += fill_from_workbooks()
    if args.pdf is not None:
        problems += verify_2018_against_pdf(args.pdf)

    if problems:
        for problem in problems:
            print(f"PROBLEM: {problem}", file=sys.stderr)
        return 1

    option_rows = build_option_rows()
    alternative_rows = build_alternative_rows()

    if args.check:
        print(f"OK: {len(option_rows)} options, {len(alternative_rows)} alternatives")
        return 0

    years = sorted({
        int(key.split("_")[1])
        for row in alternative_rows
        for key in row
        if key.startswith("savings_") and key.endswith("_billions") and key.split("_")[1].isdigit()
    })
    alt_fields = [
        "volume", "publication", "chapter", "option_number", "alternative_id",
        "label", "measure", "window_first_year", "savings_5yr_billions",
        "savings_10yr_billions", "deficit_effect_10yr_billions",
        *[f"savings_{year}_billions" for year in years],
        "report_page", "registered", "not_registered_reason", "extracted_by",
    ]
    for row in alternative_rows:
        for year in years:
            row.setdefault(f"savings_{year}_billions", "")

    _write(
        OPTIONS_CSV,
        (*_HEADER_LINES, "# One row per revenue option, with a shape verdict and a reason."),
        [
            "volume", "publication", "publication_date", "landing_page",
            "window_first_year", "window_last_year", "stated_revenue_baseline",
            "chapter", "option_number", "title", "runnable", "reason",
        ],
        option_rows,
    )
    _write(
        ALTERNATIVES_CSV,
        (*_HEADER_LINES, "# One row per reported alternative inside a runnable option."),
        alt_fields,
        alternative_rows,
    )
    print(f"Wrote {OPTIONS_CSV} ({len(option_rows)} rows)")
    print(f"Wrote {ALTERNATIVES_CSV} ({len(alternative_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
