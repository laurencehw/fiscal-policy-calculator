"""
Baseline Budget Projections

Provides baseline projections for federal revenues, spending, and deficits
following CBO methodology and current law assumptions.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from . import cbo_baseline_data as cbo_data
from .constants import BASELINE_GROWTH, GDP_RATIOS

logger = logging.getLogger(__name__)


class BaselineVintage(Enum):
    """CBO baseline vintage/edition selector."""
    CBO_FEB_2024 = "cbo_feb_2024"
    CBO_JAN_2025 = "cbo_jan_2025"
    CBO_FEB_2026 = "cbo_feb_2026"


#: The fiscal year every **app** surface opens its ten-year window on.
#:
#: Ask, Build, Tailor, Explore, the classroom engine and the public API all
#: score FY2026-FY2035, which is the window :data:`BaselineVintage`'s own app
#: default (``CBO_FEB_2026``) projects. Before this constant existed the window
#: was whatever the policy in hand happened to carry: a calibrated preset that
#: named 2026 rendered "FY2026-FY2035" while a generic Tailor run took
#: ``Policy.start_year``'s 2025 and rendered "FY2025-FY2034" on the next page
#: over, for the same baseline.
#:
#: Deliberately **not** the library default. ``Policy.start_year``,
#: ``FiscalPolicyScorer.start_year`` and ``BaselineProjection.start_year`` stay
#: at 2025 because the validation suite's targets are quoted on the windows
#: their documents used, and the suite reaches the same policy factories the
#: app does. Moving the app's window is a presentation-and-baseline decision;
#: moving a benchmark's window would be a target revision, which is a different
#: lane with a different ledger. Everything the user sees routes through here;
#: nothing under ``fiscal_model/validation/`` does.
APP_DEFAULT_START_YEAR = 2026


# CBO February 2024 economic assumptions (legacy)
_CBO_FEB_2024_ASSUMPTIONS = {
    'real_gdp_growth': np.array([
        0.024, 0.021, 0.019, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018
    ]),
    'inflation': np.array([
        0.023, 0.022, 0.021, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020
    ]),
    'unemployment': np.array([
        0.042, 0.044, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045
    ]),
    'interest_rate_10yr': np.array([
        0.044, 0.043, 0.042, 0.041, 0.040, 0.040, 0.040, 0.040, 0.040, 0.040
    ]),
    'labor_force_participation': np.array([
        0.622, 0.620, 0.618, 0.616, 0.614, 0.612, 0.610, 0.608, 0.606, 0.604
    ]),
}

# CBO February 2026 economic assumptions (updated)
_CBO_FEB_2026_ASSUMPTIONS = {
    'real_gdp_growth': np.array([
        0.019, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018
    ]),
    'inflation': np.array([
        0.025, 0.022, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020
    ]),
    'unemployment': np.array([
        0.044, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045
    ]),
    'interest_rate_10yr': np.array([
        0.045, 0.043, 0.041, 0.040, 0.039, 0.039, 0.039, 0.039, 0.039, 0.039
    ]),
    'labor_force_participation': np.array([
        0.620, 0.619, 0.618, 0.616, 0.614, 0.612, 0.610, 0.608, 0.606, 0.602
    ]),
}


# CBO January 2025 economic assumptions - SOURCED, not interpolated.
#
# Source: Congressional Budget Office, *The Budget and Economic Outlook: 2025 to
# 2035* (January 2025), publication 61172, whose supplemental economic data file
# (publication 60870, ``51135-2025-01-Economic-Projections.xlsx``, sheet
# "2. Calendar Year") carries the year-by-year forecast. Calendar years
# 2025-2034, from the sheet's own rows:
#
#   real_gdp_growth            "Real GDP", percentage change
#   inflation                  "Price index, personal consumption expenditures
#                              (PCE)", percentage change
#   unemployment               "Unemployment rate, civilian, 16 years or older"
#   interest_rate_10yr         "10-Year Treasury note"
#   labor_force_participation  "Labor force participation rate, 16 years or older"
#
# Before Phase D this vintage carried a 0.5/0.5 interpolation between the
# February 2024 and February 2026 assumption sets. That interpolation is kept
# below as :func:`interpolated_jan_2025_assumptions` - it is the documented
# fallback - and :data:`VINTAGE_SOURCING` records which of the two is in force
# so the distinction cannot be lost in a report.
_CBO_JAN_2025_ASSUMPTIONS = {
    'real_gdp_growth': np.array([
        0.0212, 0.0183, 0.0176, 0.0174, 0.0179, 0.0182, 0.0182, 0.0184, 0.0183, 0.0180
    ]),
    'inflation': np.array([
        0.0219, 0.0212, 0.0202, 0.0200, 0.0198, 0.0197, 0.0197, 0.0196, 0.0196, 0.0196
    ]),
    'unemployment': np.array([
        0.0428, 0.0436, 0.0439, 0.0440, 0.0438, 0.0438, 0.0437, 0.0436, 0.0435, 0.0433
    ]),
    'interest_rate_10yr': np.array([
        0.0409, 0.0394, 0.0391, 0.0389, 0.0387, 0.0385, 0.0384, 0.0383, 0.0381, 0.0380
    ]),
    'labor_force_participation': np.array([
        0.6265, 0.6242, 0.6211, 0.6188, 0.6173, 0.6163, 0.6155, 0.6148, 0.6143, 0.6139
    ]),
}

#: Base-year (FY2025) budget levels for the January 2025 vintage, in billions of
#: dollars, from CBO's own baseline tables in publication 60870 (the data file
#: behind publication 61172):
#:
#: * **Table B-1** - revenues by source, total outlays by category, debt held by
#:   the public and GDP.
#: * **Table B-4** - mandatory outlays by program, and the offsetting receipts
#:   that turn gross Social Security and Medicare into the net figures the
#:   model's spending categories represent.
#: * **Table B-5** - 2025 discretionary *budget authority* split between defense
#:   ($861.6B) and nondefense ($962.0B). CBO's abbreviated January 2025 report
#:   publishes no defense/nondefense split of discretionary *outlays*, so the
#:   $1,847.9B outlay total is divided in that budget-authority ratio (47.25% /
#:   52.75%). Those two numbers are derived rather than transcribed and say so.
_CBO_JAN_2025_BASE_LEVELS = {
    'base_gdp': 30_136.0,                   # Table B-1, addendum "GDP", 2025
    'base_individual_income_tax': 2_621.0,  # Table B-1, "Individual income taxes"
    'base_corporate_tax': 524.0,            # Table B-1, "Corporate income taxes"
    'base_payroll_tax': 1_759.0,            # Table B-1, "Payroll taxes"
    'base_other_revenue': 259.0,            # Table B-1, "Other"
    # Table B-4: 1,572.108 gross - 23.368 Social Security offsetting receipts.
    'base_social_security': 1_548.7,
    # Table B-4: 1,145.447 gross - 203.243 Medicare offsetting receipts.
    'base_medicare': 942.2,
    'base_medicaid': 655.9,                 # Table B-4, "Medicaid"
    # Table B-1 mandatory total 4,227.993 less the three named programs above.
    'base_other_mandatory': 1_081.2,
    'base_defense': 873.1,                  # derived: 1,847.890 x 861.567/1,823.539
    'base_nondefense': 974.8,               # derived: 1,847.890 x 961.972/1,823.539
    'base_debt': 30_103.0,                  # Table B-1, "Debt held by the public"
}

def _vintage_key(vintage: BaselineVintage) -> str:
    """The id ``fiscal_model.cbo_baseline_data`` keys a vintage by.

    The enum's own ``value``, which is also the ``vintage`` column of the
    transcription CSVs, so the two cannot drift apart silently.
    """
    return vintage.value


#: How each vintage's numbers were obtained, **per line**.
#:
#: ``"transcribed"``
#:     Read from that vintage's own published CBO table, through
#:     ``fiscal_model/data_files/cbo_baseline/``. ``PROVENANCE.csv`` names the
#:     repository, file, commit SHA and SHA-256 behind it.
#: ``"reconstructed"``
#:     This module's own rule. Reportable as "this model's estimate for the
#:     <date> vintage" and **not** as "CBO's <date> figures".
#:
#: Computed from what the transcription actually contains rather than asserted
#: by a literal, because the literal was wrong. Before this lane the map held
#: one string per vintage and said ``"sourced"`` for all three, defined as
#: "every economic assumption and base level was transcribed from that
#: vintage's own published tables" - while February 2024's real GDP growth sits
#: **0.60 percentage points** from CBO's own fiscal 2024-02 table, February
#: 2026's ten-year note **falls 4.5% to 3.9% where CBO's rises 4.10% to 4.38%**,
#: and no vintage's budget levels were transcribed at all under the app's own
#: ``use_real_data=True`` default, which built them from eleven ``GDP_RATIOS``
#: applied to whatever nominal GDP FRED last reported.
#:
#: February 2024 is ``economic: transcribed`` / ``budget: reconstructed``, and
#: that combination is why the grade had to grow a second field:
#: ``cbo-data``'s ``ten_year_budget`` carries 2024-06, 2025-01 and 2026-02, and
#: June 2024 is *An Update to the Budget and Economic Outlook* (publication
#: 60039), a different document - its FY2025 deficit is $1,937.9B against the
#: January 2025 edition's $1,865.3B for the same year.
def vintage_sourcing(vintage: BaselineVintage) -> dict[str, str]:
    """``{"economic": ..., "budget": ...}`` for one vintage, computed not declared."""
    key = _vintage_key(vintage)
    return {
        "economic": (
            "transcribed" if cbo_data.has_economic_table(key) else "reconstructed"
        ),
        "budget": (
            "transcribed" if cbo_data.has_budget_table(key) else "reconstructed"
        ),
    }


#: Mapping surface kept for existing callers, which index it by
#: :class:`BaselineVintage`. Each value is now the two-field record above
#: rather than one string, so a report cannot call a vintage "sourced" when
#: only half of it is.
VINTAGE_SOURCING: dict[BaselineVintage, dict[str, str]] = {
    vintage: vintage_sourcing(vintage) for vintage in BaselineVintage
}

#: Base-year corporate income tax receipts per vintage, in billions.
#:
#: One map, read by **both** the real-data loader and the hardcoded fallback, so
#: the two cannot disagree about what a vintage projects. Before this existed
#: they disagreed by 8.6% on February 2026 and 35.5% on January 2025, because
#: :meth:`CBOBaseline._load_from_data_sources` overrode every vintage's figure
#: with ``individual income tax x GDP_RATIOS["corporate_tax_to_income_tax"]`` -
#: 18% of the latest IRS SOI *tax year* on file, a quantity with no vintage in
#: it. That override is why all three vintages returned one corporate base level
#: to the cent (386.62) under the app's own default; see
#: ``planning/lanes/FIX_baseline_corporate_path.md`` section 1.2 and
#: ``planning/MODELING_IMPROVEMENT.md`` section 6.2 item 30.
#:
#: :data:`CORPORATE_RECEIPTS_SOURCING` grades each entry. Two are transcribed
#: from a CBO table and one is this module's own estimate, and the grade says
#: which is which rather than leaving a reader to assume.
_VINTAGE_CORPORATE_BASE_LEVELS: dict[BaselineVintage, float] = {
    # Base year 2024. Superseded for projection purposes by the published
    # annual path below, which starts at FY2025; kept because
    # ``base_corporate_tax`` is part of this class's surface.
    BaselineVintage.CBO_FEB_2024: 450.0,
    # Table B-1, "Corporate income taxes", FY2025 - the same transcription
    # _CBO_JAN_2025_BASE_LEVELS carries, and pinned equal to it by a test.
    BaselineVintage.CBO_JAN_2025: 524.0,
    # This module's own base-year figure for the vintage, transcribed from no
    # table. Graded ``vintage_estimate`` below for exactly that reason.
    BaselineVintage.CBO_FEB_2026: 420.0,
}

#: How each vintage's **corporate receipts line** is obtained, which is a
#: narrower question than :data:`VINTAGE_SOURCING`'s and has a different answer.
#:
#: ``published_path``
#:     Every year of the projection is CBO's own published figure for that
#:     vintage, read from
#:     ``data_files/corporate/cbo_corporate_receipts.csv``.
#: ``published_base_level``
#:     The base year is CBO's published figure for that vintage; the shape is
#:     this module's reconstruction (GDP growth + inflation + a 1pp corporate
#:     profit premium), which on February 2024's assumptions compounds to
#:     4.88%/yr against CBO's own 1.21%.
#: ``vintage_estimate``
#:     Neither the level nor the shape is transcribed. Reportable as "this
#:     model's estimate for the February 2026 vintage" and **not** as "CBO's
#:     February 2026 corporate receipts".
#:
#: All three are now ``published_path``. The note this map used to carry -
#: *"cbo.gov returns HTTP 403 to this environment and the Wayback Machine holds
#: no snapshot of the January 2025 or February 2026 budget projections
#: workbooks… Adding one is a data edit - a block in the CSV - not a code
#: change"* - was right about the remedy and wrong about the obstacle.
#: ``github.com/US-CBO`` is not blocked, and
#: ``cbo-data/data/budget/ten_year_budget/annual_fy_{2025-01,2026-02}.csv``
#: carries ``proj_rev_corporate_income`` for both missing vintages. That is the
#: data edit, and it lives in ``data_files/cbo_baseline/`` (owner decision (10)).
#:
#: February 2024 keeps reading ``data_files/corporate/cbo_corporate_receipts.csv``
#: - PR #121's transcription of publication 59710 Table 1-1 - because CBO's
#: GitHub publishes no February 2024 budget table and June 2024 is a different
#: document. Two files, one grade, and the grade is computed below.
def corporate_receipts_sourcing(vintage: BaselineVintage) -> str:
    """``published_path`` when some CBO table supplies every year, else weaker."""
    key = _vintage_key(vintage)
    if cbo_data.has_budget_table(key):
        return "published_path"
    if vintage == BaselineVintage.CBO_FEB_2024:
        # Publication 59710 Table 1-1, via fiscal_model.corporate's own loader.
        return "published_path"
    return "vintage_estimate"


CORPORATE_RECEIPTS_SOURCING: dict[BaselineVintage, str] = {
    vintage: corporate_receipts_sourcing(vintage) for vintage in BaselineVintage
}

#: Citation per vintage, so a report can name the document it scored against.
VINTAGE_SOURCE_DOCUMENT: dict[BaselineVintage, str] = {
    BaselineVintage.CBO_FEB_2024: (
        "CBO, The Budget and Economic Outlook: 2024 to 2034 (February 2024), "
        "publication 59710"
    ),
    BaselineVintage.CBO_JAN_2025: (
        "CBO, The Budget and Economic Outlook: 2025 to 2035 (January 2025), "
        "publication 61172; baseline tables B-1, B-4 and B-5 plus the economic "
        "projections in the accompanying data files (publication 60870)"
    ),
    BaselineVintage.CBO_FEB_2026: (
        "CBO, The Budget and Economic Outlook: 2026 to 2036 (February 2026)"
    ),
}


def cbo_baseline_budget(
    vintage: BaselineVintage,
) -> dict[str, dict[int, float]] | None:
    """CBO's own transcribed ten-year budget table for a vintage, or ``None``.

    ``None`` where CBO's GitHub publishes no budget table for that edition -
    February 2024 today - rather than substituting a neighbouring one.
    """
    return cbo_data.budget_tables().get(_vintage_key(vintage)) or None


def interpolated_jan_2025_assumptions() -> dict:
    """Pre-Phase-D fallback: interpolate Jan 2025 from its neighbouring vintages.

    Kept, and kept callable, because it is the honest fallback if the sourced
    figures above ever have to be withdrawn. It is **not** used by
    :func:`vintage_assumptions`; a vintage built from it would have to be
    reported as ``interpolated`` in :data:`VINTAGE_SOURCING`.
    """
    return {
        key: _CBO_FEB_2024_ASSUMPTIONS[key] * 0.5 + _CBO_FEB_2026_ASSUMPTIONS[key] * 0.5
        for key in _CBO_FEB_2024_ASSUMPTIONS
    }


#: First window year each vintage's hand-entered assumption block above was
#: written for, so a transcribed replacement is read on the same years.
#: February 2024 and January 2025 open on FY2025; February 2026 on FY2026.
_ASSUMPTION_FIRST_YEAR: dict[BaselineVintage, int] = {
    BaselineVintage.CBO_FEB_2024: 2025,
    BaselineVintage.CBO_JAN_2025: 2025,
    BaselineVintage.CBO_FEB_2026: 2026,
}

_HAND_ENTERED_ASSUMPTIONS: dict[BaselineVintage, dict] = {
    BaselineVintage.CBO_FEB_2024: _CBO_FEB_2024_ASSUMPTIONS,
    BaselineVintage.CBO_JAN_2025: _CBO_JAN_2025_ASSUMPTIONS,
    BaselineVintage.CBO_FEB_2026: _CBO_FEB_2026_ASSUMPTIONS,
}


def vintage_assumptions(
    vintage: BaselineVintage, first_year: int | None = None
) -> dict:
    """Economic assumptions for a vintage, from its own published CBO table.

    Reads ``fiscal_model/data_files/cbo_baseline/cbo_economic_baseline.csv``,
    which is CBO's **fiscal-year** forecast for this vintage's own edition -
    ``real_gdp_pct_change``, ``pce_price_index_pct_change``,
    ``unemployment_rate``, ``treasury_note_rate_10yr`` and ``lfpr_16yo``,
    stored as fractions. The hand-entered blocks above are the documented
    fallback for a vintage with no transcribed block, and
    :func:`vintage_sourcing` says which path was taken.

    The blocks the transcription replaces were not close on two of the three
    vintages. Measured over the ten-year window, February 2024's real GDP
    growth was out by up to **0.60pp** and its labour force participation by
    **1.05pp**; February 2026's ten-year Treasury note **fell 4.5% to 3.9%
    where CBO's own table rises 4.10% to 4.38%**. January 2025's residual is
    at most 0.11pp and is the calendar/fiscal basis: PR #118 transcribed it off
    CBO's *calendar* sheet and this file reads the fiscal one, because every
    budget quantity in this module is fiscal-year.
    """
    if vintage not in _HAND_ENTERED_ASSUMPTIONS:
        raise ValueError(f"Unknown vintage: {vintage}")

    start = first_year if first_year is not None else _ASSUMPTION_FIRST_YEAR[vintage]
    try:
        transcribed = cbo_data.assumption_arrays(_vintage_key(vintage), start)
    except KeyError:
        return _HAND_ENTERED_ASSUMPTIONS[vintage]

    fallback = _HAND_ENTERED_ASSUMPTIONS[vintage]
    return {key: transcribed.get(key, fallback[key]) for key in fallback}


#: Backwards-compatible alias. The name is now a misnomer - only the fallback
#: :func:`interpolated_jan_2025_assumptions` interpolates anything - but it is
#: part of this module's existing surface.
_interpolate_assumptions = vintage_assumptions


@dataclass
class EconomicAssumptions:
    """
    Economic assumptions underlying the baseline projection.
    Based on CBO assumptions (defaults to February 2026 vintage).
    """
    # GDP growth (real)
    real_gdp_growth: np.ndarray = field(default_factory=lambda: np.array([
        0.019, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018
    ]))

    # Inflation (PCE, not GDP deflator)
    inflation: np.ndarray = field(default_factory=lambda: np.array([
        0.025, 0.022, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020
    ]))

    # Unemployment rate
    unemployment: np.ndarray = field(default_factory=lambda: np.array([
        0.044, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045
    ]))

    # Interest rates (10-year Treasury)
    interest_rate_10yr: np.ndarray = field(default_factory=lambda: np.array([
        0.045, 0.043, 0.041, 0.040, 0.039, 0.039, 0.039, 0.039, 0.039, 0.039
    ]))

    # Labor force participation rate
    labor_force_participation: np.ndarray = field(default_factory=lambda: np.array([
        0.620, 0.619, 0.618, 0.616, 0.614, 0.612, 0.610, 0.608, 0.606, 0.602
    ]))


@dataclass
class BaselineProjection:
    """
    10-year baseline budget projection.

    All values in billions of dollars unless otherwise noted.
    """
    start_year: int = 2025
    years: np.ndarray = field(default_factory=lambda: np.arange(2025, 2035))

    # Economic variables
    nominal_gdp: np.ndarray = field(default_factory=lambda: np.zeros(10))
    real_gdp: np.ndarray = field(default_factory=lambda: np.zeros(10))
    #: Nominal GDP for ``start_year - 1`` - the level this vintage's own
    #: Table B-1 publishes for the year before the window opens, and the level
    #: :meth:`CBOBaseline._project_gdp` compounds ``nominal_gdp`` from. Carried
    #: so :meth:`nominal_income_index` can reach a year *before* the window
    #: without extrapolating one it already knows. ``0.0`` on a projection
    #: built by hand rather than by :meth:`CBOBaseline.generate`, which is what
    #: makes the index degrade to 1.0 rather than guess.
    base_nominal_gdp: float = 0.0
    #: This vintage's own published fiscal-year nominal GDP levels, keyed by
    #: fiscal year, where CBO publishes them. Read by
    #: :meth:`nominal_income_index` for a year outside the scoring window - the
    #: SOI anchor is a tax year several years back - so a level CBO prints is
    #: read rather than back-extrapolated from the window's first growth rate.
    #: Empty on a hand-built projection and on a vintage with no transcribed
    #: economic table, in which case the extrapolation rule below applies
    #: unchanged.
    published_nominal_gdp: dict[int, float] = field(default_factory=dict)

    # Revenue categories
    individual_income_tax: np.ndarray = field(default_factory=lambda: np.zeros(10))
    corporate_income_tax: np.ndarray = field(default_factory=lambda: np.zeros(10))
    payroll_taxes: np.ndarray = field(default_factory=lambda: np.zeros(10))
    other_revenues: np.ndarray = field(default_factory=lambda: np.zeros(10))

    # Spending categories
    social_security: np.ndarray = field(default_factory=lambda: np.zeros(10))
    medicare: np.ndarray = field(default_factory=lambda: np.zeros(10))
    medicaid: np.ndarray = field(default_factory=lambda: np.zeros(10))
    other_mandatory: np.ndarray = field(default_factory=lambda: np.zeros(10))
    defense_discretionary: np.ndarray = field(default_factory=lambda: np.zeros(10))
    nondefense_discretionary: np.ndarray = field(default_factory=lambda: np.zeros(10))
    net_interest: np.ndarray = field(default_factory=lambda: np.zeros(10))

    # Debt
    debt_held_by_public: np.ndarray = field(default_factory=lambda: np.zeros(10))

    @property
    def total_revenues(self) -> np.ndarray:
        """Total federal revenues."""
        return (self.individual_income_tax + self.corporate_income_tax +
                self.payroll_taxes + self.other_revenues)

    @property
    def total_outlays(self) -> np.ndarray:
        """Total federal outlays."""
        return (self.social_security + self.medicare + self.medicaid +
                self.other_mandatory + self.defense_discretionary +
                self.nondefense_discretionary + self.net_interest)

    @property
    def deficit(self) -> np.ndarray:
        """Budget deficit (positive = deficit, negative = surplus)."""
        return self.total_outlays - self.total_revenues

    @property
    def primary_deficit(self) -> np.ndarray:
        """Primary deficit (excluding interest payments)."""
        return self.deficit - self.net_interest

    @property
    def deficit_to_gdp(self) -> np.ndarray:
        """Deficit as percentage of GDP."""
        return self.deficit / self.nominal_gdp * 100

    @property
    def debt_to_gdp(self) -> np.ndarray:
        """Debt as percentage of GDP."""
        return self.debt_held_by_public / self.nominal_gdp * 100

    def nominal_income_index(self, year: int) -> float:
        """Nominal-income level for ``year``, in this vintage's own units.

        Read-only. Built entirely from figures this projection already carries,
        so it introduces no constant and nothing fitted:

        * ``start_year + i`` is ``nominal_gdp[i]``, that vintage's own path -
          CBO's published fiscal-year nominal GDP where it exists, and its
          transcribed ``real_gdp_growth + inflation`` compounded off
          :attr:`base_nominal_gdp` where it does not;
        * any other year CBO publishes is read from
          :attr:`published_nominal_gdp` - this extends the rule below to every
          published pre-window year rather than only to ``start_year - 1``, and
          it matters because the SOI anchor is a tax year several years before
          the window;
        * ``start_year - 1`` is :attr:`base_nominal_gdp`, the level the
          vintage's own table publishes for the year before the window;
        * outside all of those, the nearest observed growth rate is continued -
          the rule :func:`fiscal_model.payroll.covered_earnings` and
          :meth:`CBOBaseline._published_corporate_receipts` already apply at the
          ends of their own tables.

        Callers use it as a **ratio** between two years, so the level's own
        anchor cancels and the result is a pure function of the vintage's growth
        assumptions. Returns ``0.0`` when this projection carries no GDP path at
        all (a hand-built :class:`BaselineProjection`), which is the signal for
        a caller to leave its quantity unprojected rather than guess a path.
        """
        gdp = np.asarray(self.nominal_gdp, dtype=float)
        if gdp.size == 0 or not np.any(gdp > 0):
            return 0.0

        first_year = int(self.start_year)
        last_year = first_year + int(gdp.size) - 1
        year = int(year)

        if first_year <= year <= last_year:
            return float(gdp[year - first_year])

        published = self.published_nominal_gdp
        if published and year in published:
            return float(published[year])

        if year > last_year:
            if gdp.size < 2 or gdp[-2] <= 0:
                return float(gdp[-1])
            growth = float(gdp[-1] / gdp[-2]) - 1.0
            return float(gdp[-1]) * (1.0 + growth) ** (year - last_year)

        # Before the window. The year immediately before it is published.
        base = float(self.base_nominal_gdp)
        if base > 0:
            if year == first_year - 1:
                return base
            growth = float(gdp[0] / base) - 1.0
        elif gdp.size >= 2 and gdp[0] > 0:
            growth = float(gdp[1] / gdp[0]) - 1.0
            base = float(gdp[0]) / (1.0 + growth) if growth > -1.0 else float(gdp[0])
            if year == first_year - 1:
                return base
        else:
            return float(gdp[0])

        if growth <= -1.0:
            return base
        return base / (1.0 + growth) ** (first_year - 1 - year)

    def get_year_index(self, year: int) -> int:
        """Get array index for a given year."""
        return year - self.start_year

    def get_value(self, category: str, year: int) -> float:
        """Get a specific value for a category and year."""
        idx = self.get_year_index(year)
        return getattr(self, category)[idx]

    def get_cumulative_deficit(self, start_year: int | None = None,
                               end_year: int | None = None) -> float:
        """Get cumulative deficit over a period."""
        start = start_year or self.start_year
        end = end_year or (self.start_year + len(self.years) - 1)

        start_idx = self.get_year_index(start)
        end_idx = self.get_year_index(end) + 1

        return np.sum(self.deficit[start_idx:end_idx])


class CBOBaseline:
    """
    Generator for CBO-style baseline projections.

    Supports multiple baseline vintages (CBO Feb 2024, Jan 2025, Feb 2026).
    Defaults to CBO February 2026 baseline.
    """

    def __init__(self, start_year: int = 2026, duration: int = 10,
                 use_real_data: bool = True, vintage: BaselineVintage | None = None):
        self.start_year = start_year
        self.duration = duration
        self.years = np.arange(start_year, start_year + duration)
        self.requested_real_data = use_real_data
        self.baseline_data_source = "hardcoded_fallback"
        self.load_error: str | None = None
        self.irs_data_year: int | None = None
        self.gdp_source = "hardcoded"
        self.fred_data_status: dict[str, Any] = {}

        # Set vintage (default to Feb 2026)
        if vintage is None:
            self.baseline_vintage = BaselineVintage.CBO_FEB_2026
        else:
            self.baseline_vintage = vintage

        # Load appropriate assumptions for this vintage
        assumptions_dict = vintage_assumptions(self.baseline_vintage)
        self.assumptions = EconomicAssumptions(
            real_gdp_growth=assumptions_dict['real_gdp_growth'],
            inflation=assumptions_dict['inflation'],
            unemployment=assumptions_dict['unemployment'],
            interest_rate_10yr=assumptions_dict['interest_rate_10yr'],
            labor_force_participation=assumptions_dict['labor_force_participation'],
        )

        # Try to load real data, fall back to hardcoded if unavailable
        if use_real_data:
            try:
                self._load_from_data_sources()
                self.baseline_data_source = "real_data"
                logger.info(f"Successfully loaded {self.baseline_vintage_date} baseline data from IRS SOI and FRED")
            except Exception as e:
                self.load_error = str(e)
                logger.warning(f"Could not load real data: {e}")
                logger.warning(f"Falling back to hardcoded {self.baseline_vintage_date} baseline values")
                self._use_hardcoded_fallback()
        else:
            self._use_hardcoded_fallback()

    @property
    def baseline_vintage_date(self) -> str:
        """Return human-readable vintage date string."""
        vintage_dates = {
            BaselineVintage.CBO_FEB_2024: "February 2024",
            BaselineVintage.CBO_JAN_2025: "January 2025",
            BaselineVintage.CBO_FEB_2026: "February 2026",
        }
        return vintage_dates.get(self.baseline_vintage, "Unknown")

    @property
    def baseline_vintage_sourcing(self) -> str:
        """One word for this vintage's figures, the weaker of its two lines.

        ``"transcribed"`` only when **both** the economic path and the budget
        levels come from CBO's own published table for this edition;
        ``"partial"`` when one does and the other does not — February 2024,
        whose economic forecast CBO's GitHub publishes and whose budget table
        it does not; ``"reconstructed"`` when neither does.

        Deliberately the weaker of the two, so a one-word report cannot read as
        a claim about the half that is not transcribed. Callers that need to
        know which half should read :attr:`vintage_sourcing_detail`.
        """
        detail = self.vintage_sourcing_detail
        grades = {detail.get("economic"), detail.get("budget")}
        if grades == {"transcribed"}:
            return "transcribed"
        if "transcribed" in grades:
            return "partial"
        return "reconstructed"

    @property
    def vintage_sourcing_detail(self) -> dict[str, str]:
        """``{"economic": ..., "budget": ...}`` — see :func:`vintage_sourcing`."""
        return vintage_sourcing(self.baseline_vintage)

    @property
    def vintage_provenance(self) -> dict[str, dict[str, str]]:
        """Repository, file, commit, digest and fetch date, per transcribed line.

        Empty for a line CBO's GitHub publishes nothing for, which is what
        makes the grade above checkable against the data rather than against a
        constant.
        """
        key = _vintage_key(self.baseline_vintage)
        out: dict[str, dict[str, str]] = {}
        for kind in ("economic", "budget"):
            record = cbo_data.provenance().get((key, kind))
            if record is None or not record.transcribed:
                continue
            out[kind] = {
                "repository": record.repository,
                "file_path": record.file_path,
                "commit_sha": record.commit_sha,
                "sha256": record.sha256,
                "fetch_date": record.fetch_date,
                "publication": record.publication,
            }
        return out

    @property
    def corporate_receipts_sourcing(self) -> str:
        """How this vintage's corporate receipts line was obtained.

        ``published_path`` / ``published_base_level`` / ``vintage_estimate`` -
        see :data:`CORPORATE_RECEIPTS_SOURCING`. Narrower than
        :attr:`baseline_vintage_sourcing`, and for two of the three vintages it
        gives a weaker answer, which is the point: a corporate line this module
        reconstructed must not be reportable as CBO's.
        """
        return CORPORATE_RECEIPTS_SOURCING.get(self.baseline_vintage, "unknown")

    @property
    def metadata(self) -> dict[str, Any]:
        """Return machine-readable metadata about the baseline inputs used."""
        return {
            "vintage": self.baseline_vintage.value,
            "vintage_date": self.baseline_vintage_date,
            "vintage_sourcing": self.baseline_vintage_sourcing,
            "vintage_sourcing_detail": self.vintage_sourcing_detail,
            "vintage_provenance": self.vintage_provenance,
            "corporate_receipts_sourcing": self.corporate_receipts_sourcing,
            "vintage_source_document": VINTAGE_SOURCE_DOCUMENT.get(
                self.baseline_vintage, "unknown"
            ),
            "source": self.baseline_data_source,
            "requested_real_data": self.requested_real_data,
            "load_error": self.load_error,
            "irs_data_year": self.irs_data_year,
            "gdp_source": self.gdp_source,
            "fred": dict(self.fred_data_status),
        }

    def _load_from_data_sources(self):
        """Load baseline values from IRS SOI and FRED data."""
        from fiscal_model.data import FREDData, IRSSOIData

        # Initialize data loaders
        irs_data = IRSSOIData()
        fred_data = FREDData()  # Uses FRED_API_KEY env var

        # Get most recent available IRS data year
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError("No IRS SOI data files found. See fiscal_model/data_files/irs_soi/README.md")

        data_year = max(available_years)
        self.irs_data_year = data_year
        logger.info("Loading baseline from %s IRS SOI data", data_year)

        # Load individual income tax revenue from IRS data
        self.base_individual_income_tax = irs_data.get_total_revenue(data_year)

        # Load GDP from FRED live/cache/bundled seed if available, otherwise
        # fall back to IRS ratio proxy.
        gdp_series = fred_data.get_gdp(nominal=True)
        self.fred_data_status = dict(fred_data.data_status)
        fred_source = self.fred_data_status.get("source")

        if fred_source in {"live", "cache", "bundled"}:
            self.base_gdp = float(gdp_series.iloc[-1])
            self.gdp_source = f"fred_{fred_source}"
            logger.info("Loaded GDP from FRED (%s): $%.0fB", fred_source, self.base_gdp)
        else:
            logger.info("FRED unavailable beyond fallback, estimating GDP from IRS income tax ratio")
            self.base_gdp = self.base_individual_income_tax / GDP_RATIOS["income_tax_to_gdp"]
            self.gdp_source = "irs_ratio_proxy"

        # Corporate tax: the vintage's own base-year receipts.
        #
        # This used to be ``base_individual_income_tax x
        # GDP_RATIOS["corporate_tax_to_income_tax"]`` - 18% of the latest IRS
        # SOI tax year on file, a quantity with no vintage in it - which is why
        # all three vintages returned the identical corporate base under the
        # app's own default while the fallback path returned three different
        # ones. The two paths now read one map. Note that the other base levels
        # below still carry the same defect for a vintage with no transcribed
        # budget table - February 2024 - and for the two that have one they are
        # overwritten a few lines down, because ``generate()`` never reads them:
        # where CBO publishes the annual path, that path IS the projection.
        # See ``planning/lanes/R1_baseline_transcription.md`` section 1.3.
        self.base_corporate_tax = _VINTAGE_CORPORATE_BASE_LEVELS[self.baseline_vintage]

        # Payroll tax: Historical average share of GDP
        self.base_payroll_tax = self.base_gdp * GDP_RATIOS["payroll_tax_to_gdp"]

        # Other revenue: Estate, excise, customs share of GDP
        self.base_other_revenue = self.base_gdp * GDP_RATIOS["other_revenue_to_gdp"]

        # Spending categories: Use GDP ratios
        self.base_social_security = self.base_gdp * GDP_RATIOS["social_security_to_gdp"]
        self.base_medicare = self.base_gdp * GDP_RATIOS["medicare_to_gdp"]
        self.base_medicaid = self.base_gdp * GDP_RATIOS["medicaid_to_gdp"]
        self.base_other_mandatory = self.base_gdp * GDP_RATIOS["other_mandatory_to_gdp"]
        self.base_defense = self.base_gdp * GDP_RATIOS["defense_to_gdp"]
        self.base_nondefense = self.base_gdp * GDP_RATIOS["nondefense_to_gdp"]

        # Debt: Current debt-to-GDP ratio
        self.base_debt = self.base_gdp * GDP_RATIOS["debt_to_gdp"]

        # The GDP anchor comes from CBO's own table where one exists. The
        # ratios above are not deleted - they remain the documented rule for a
        # vintage with no published budget table, and February 2024 still uses
        # them - but they now sit on that vintage's own GDP rather than on
        # whatever nominal GDP FRED last reported.
        self._adopt_published_gdp_anchor()

    def _adopt_published_gdp_anchor(self) -> None:
        """Anchor ``base_gdp`` on CBO's own level for this vintage's base year.

        Both loader paths call this, so ``use_real_data=True`` and
        ``use_real_data=False`` cannot disagree about what year a vintage
        starts from - the class of defect PR #130 found in the corporate line,
        where the two paths were 8.6% and 35.5% apart on two vintages.

        What it replaces is worse than a disagreement. Under
        ``use_real_data=True`` - the app's default - ``base_gdp`` was **FRED's
        latest nominal GDP for every vintage alike**, so February 2024's "base
        year" was today's economy, and the nine ``GDP_RATIOS`` spending and
        revenue levels were all built off it. Under ``use_real_data=False`` it
        was a round literal: 30,300 for February 2026 against CBO's own FY2025
        30,330.3, and 28,500 for February 2024 against CBO's FY2024 28,176.6.

        The **budget** base levels are deliberately left alone. For a vintage
        with a transcribed budget table ``generate()`` reads that table and
        never touches them; for one without, they are the documented
        reconstruction. Overwriting them would also have forced a base-year
        decision this lane has no reason to take - ``_CBO_JAN_2025_BASE_LEVELS``
        is FY2025 while ``_project_*`` treats its base as ``start_year - 1`` -
        and that ambiguity is a carry-over, not something to settle in passing.
        """
        gdp = cbo_data.nominal_gdp_table(_vintage_key(self.baseline_vintage))
        if not gdp:
            return
        self.base_gdp = float(cbo_data.series(gdp, self.start_year - 1, 1)[0])
        self.gdp_source = "cbo_published_table"

    def _use_hardcoded_fallback(self):
        """Use hardcoded baseline values (fallback when data unavailable)."""
        self.baseline_data_source = "hardcoded_fallback"
        self.gdp_source = "hardcoded"
        if self.baseline_vintage == BaselineVintage.CBO_JAN_2025:
            # Base year (FY2025) values in billions, transcribed from CBO's
            # January 2025 baseline tables. _CBO_JAN_2025_BASE_LEVELS carries
            # the table reference behind each line.
            for attr, value in _CBO_JAN_2025_BASE_LEVELS.items():
                setattr(self, attr, value)
        elif self.baseline_vintage == BaselineVintage.CBO_FEB_2024:
            # Base year (2024) values in billions
            self.base_gdp = 28500
            self.base_individual_income_tax = 2500
            self.base_corporate_tax = _VINTAGE_CORPORATE_BASE_LEVELS[
                BaselineVintage.CBO_FEB_2024
            ]
            self.base_payroll_tax = 1700
            self.base_other_revenue = 400
            self.base_social_security = 1500
            self.base_medicare = 900
            self.base_medicaid = 600
            self.base_other_mandatory = 900
            self.base_defense = 900
            self.base_nondefense = 750
            self.base_debt = 28000
        else:
            # Base year (2026) values in billions - CBO Feb 2026
            self.base_gdp = 30300  # Nominal GDP estimate for 2026
            self.base_individual_income_tax = 2700  # Individual income tax
            # Corporate tax (slightly lower due to tariff effects). Graded
            # ``vintage_estimate`` in CORPORATE_RECEIPTS_SOURCING: this
            # module's own figure, not a transcribed CBO row.
            self.base_corporate_tax = _VINTAGE_CORPORATE_BASE_LEVELS[
                BaselineVintage.CBO_FEB_2026
            ]
            self.base_payroll_tax = 1850  # Payroll tax
            self.base_other_revenue = 430  # Estate, excise, customs, etc.
            self.base_social_security = 1600  # Higher due to demographics
            self.base_medicare = 950  # Healthcare cost growth
            self.base_medicaid = 630  # Medicaid spending
            self.base_other_mandatory = 960  # Other mandatory programs
            self.base_defense = 950  # Defense discretionary
            self.base_nondefense = 780  # Nondefense discretionary
            self.base_debt = 29700  # Debt held by public (~98% of GDP)

        # Same call the real-data path makes, so the two cannot disagree about
        # a vintage's base year. The literals above survive for a vintage CBO's
        # GitHub publishes no economic table for.
        self._adopt_published_gdp_anchor()

    def generate(self) -> BaselineProjection:
        """Generate a 10-year baseline projection."""
        proj = BaselineProjection(
            start_year=self.start_year,
            years=self.years.copy()
        )

        # Generate GDP path. Where CBO publishes this vintage's own fiscal-year
        # nominal GDP, that path **is** the projection and ``base_gdp`` plays no
        # part in it; ``base_nominal_gdp`` then becomes CBO's own level for
        # ``start_year - 1`` rather than whatever nominal GDP FRED last
        # reported, which is what the reconstruction used for every vintage
        # alike. ``published_gdp`` is also handed to the projection so
        # ``nominal_income_index`` can read a published pre-window year instead
        # of back-extrapolating one.
        published_gdp = cbo_data.nominal_gdp_table(_vintage_key(self.baseline_vintage))
        if published_gdp:
            proj.nominal_gdp = cbo_data.series(published_gdp, self.start_year, 10)
            proj.base_nominal_gdp = float(
                cbo_data.series(published_gdp, self.start_year - 1, 1)[0]
            )
            proj.published_nominal_gdp = dict(published_gdp)
        else:
            # ``base_gdp`` is the level for ``start_year - 1``, which
            # ``_project_gdp`` compounds the first window year off.
            proj.nominal_gdp = self._project_gdp()
            proj.base_nominal_gdp = float(self.base_gdp)
        proj.real_gdp = self._project_real_gdp()

        budget = self._published_budget_path()
        if budget is not None:
            self._apply_published_budget(proj, budget)
            return proj

        # Generate revenues
        proj.individual_income_tax = self._project_individual_tax()
        proj.corporate_income_tax = self._project_corporate_tax()
        proj.payroll_taxes = self._project_payroll_tax()
        proj.other_revenues = self._project_other_revenue()

        # Generate spending
        proj.social_security = self._project_social_security()
        proj.medicare = self._project_medicare()
        proj.medicaid = self._project_medicaid()
        proj.other_mandatory = self._project_other_mandatory()
        proj.defense_discretionary = self._project_defense()
        proj.nondefense_discretionary = self._project_nondefense()

        # Calculate interest and debt
        proj.debt_held_by_public = self._project_debt(proj)
        proj.net_interest = self._project_interest(proj)

        return proj

    def _published_budget_path(self) -> dict[str, dict[int, float]] | None:
        """CBO's own ten-year budget table for this vintage, or ``None``.

        ``None`` for a vintage CBO's GitHub publishes no budget table for -
        February 2024 today - rather than borrowing a neighbouring edition's
        numbers, which is the behaviour that keeps a provenance claim honest.
        The caller falls back to the reconstruction and
        :func:`vintage_sourcing` says it did.
        """
        return cbo_baseline_budget(self.baseline_vintage)

    def _apply_published_budget(
        self, proj: BaselineProjection, budget: dict[str, dict[int, float]]
    ) -> None:
        """Stamp CBO's own budget path onto ``proj``.

        Where CBO publishes the annual path, that path **is** the projection:
        no base level, no growth rule, no premium. That is exactly the shape
        :meth:`_project_corporate_tax` has carried since PR #130, generalised
        from one line to all of them.

        Two mappings are not one-to-one and both are documented at the
        transcription rather than invented here (see
        ``scripts/fetch_cbo_baseline.py``):

        * **Net programme levels.** CBO prints Social Security and Medicare
          gross and puts their offsetting receipts on separate, negative lines;
          this class's categories are net, so the two are added.
        * **``other_mandatory`` is a residual** against CBO's own
          ``proj_outlays_total``. That makes :attr:`~BaselineProjection.deficit`
          reproduce CBO's printed figure to the rounding of the source whatever
          basis a component was published on - the February 2026 vintage's
          FY2026-2035 deficits sum to **$23,143.30B** against CBO's own
          $23,143.3B - and it is the only line whose definition is this
          module's rather than CBO's.
        """
        start, count = self.start_year, 10

        def line(name: str) -> np.ndarray:
            table = budget.get(name)
            if not table:
                return np.zeros(count)
            return cbo_data.series(table, start, count)

        proj.individual_income_tax = line("individual_income_tax")
        proj.corporate_income_tax = line("corporate_income_tax")
        proj.payroll_taxes = line("payroll_taxes")
        # February 2026 splits customs duties out of "other"; earlier editions
        # do not, and the absent line contributes zero.
        proj.other_revenues = line("other_revenues_core") + line("other_revenues_customs")

        social_security = line("social_security_gross") + line("social_security_offset")
        medicare = line("medicare_gross") + line("medicare_offset")
        medicaid = line("medicaid")
        proj.social_security = social_security
        proj.medicare = medicare
        proj.medicaid = medicaid

        proj.defense_discretionary = line("defense_discretionary")
        proj.nondefense_discretionary = line("nondefense_discretionary")
        proj.net_interest = line("net_interest")
        proj.other_mandatory = (
            line("outlays_total")
            - line("discretionary_total")
            - line("net_interest")
            - social_security
            - medicare
            - medicaid
        )
        proj.debt_held_by_public = line("debt_held_by_public")

    def _project_gdp(self) -> np.ndarray:
        """Project nominal GDP."""
        gdp = np.zeros(10)
        gdp[0] = self.base_gdp * (1 + self.assumptions.real_gdp_growth[0] +
                                   self.assumptions.inflation[0])
        for i in range(1, 10):
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i]
            gdp[i] = gdp[i-1] * (1 + growth)
        return gdp

    def _project_real_gdp(self) -> np.ndarray:
        """Project real GDP (2024 dollars)."""
        real_gdp = np.zeros(10)
        real_gdp[0] = self.base_gdp * (1 + self.assumptions.real_gdp_growth[0])
        for i in range(1, 10):
            real_gdp[i] = real_gdp[i-1] * (1 + self.assumptions.real_gdp_growth[i])
        return real_gdp

    def _project_individual_tax(self) -> np.ndarray:
        """Project individual income tax revenues."""
        # Income tax grows faster than GDP due to bracket creep
        revenue = np.zeros(10)
        growth_premium = BASELINE_GROWTH["bracket_creep_premium"]

        revenue[0] = self.base_individual_income_tax * (1 +
                     self.assumptions.real_gdp_growth[0] +
                     self.assumptions.inflation[0] + growth_premium)

        for i in range(1, 10):
            base_growth = (self.assumptions.real_gdp_growth[i] +
                          self.assumptions.inflation[i] + growth_premium)
            revenue[i] = revenue[i-1] * (1 + base_growth)

        return revenue

    def _published_corporate_receipts(self) -> np.ndarray | None:
        """CBO's own projected corporate receipts for this vintage, or ``None``.

        Reads the path PR #121 transcribed into
        ``data_files/corporate/cbo_corporate_receipts.csv`` through
        :mod:`fiscal_model.corporate`'s own loader rather than re-parsing the
        file - one reader, one cache, one place a transcription error could
        hide. The import is deferred because ``corporate`` imports ``policies``,
        and a baseline that imported a policy module at module scope would
        invert this package's dependency direction.

        ``None`` for a vintage with no transcribed block. The loader raises in
        that case rather than borrowing a neighbouring vintage's numbers, which
        is the behaviour that keeps a provenance claim honest; the caller falls
        back to the reconstruction and
        :data:`CORPORATE_RECEIPTS_SOURCING` says it did.
        """
        from fiscal_model.corporate import (
            cbo_corporate_receipts,
            cbo_receipts_by_fiscal_year,
        )

        vintage = self.baseline_vintage.value
        try:
            cbo_receipts_by_fiscal_year(vintage)
        except KeyError:
            return None

        # Ten fiscal years from start_year, matching every other projection
        # method in this class, which returns ``np.zeros(10)`` whatever
        # ``duration`` says. Years past the transcribed window continue the
        # nearest observed growth rate - the loader's own documented rule, the
        # one ``payroll.covered_earnings`` uses on CBO's wage path from the
        # same publication - so the app's FY2026-2035 window is served by a
        # FY2025-2034 table with FY2035 extrapolated.
        return np.array(
            [
                cbo_corporate_receipts(self.start_year + i, vintage)
                for i in range(10)
            ]
        )

    def _project_corporate_tax(self) -> np.ndarray:
        """Project corporate income tax revenues.

        Where the repository carries CBO's own published receipts path for the
        scored vintage, that path **is** the projection: no base level, no
        growth rule, no premium. On February 2024 (publication 59710, Table
        1-1) it grows at 1.21%/yr over FY2025-2034 and *falls* in FY2026 and
        FY2027, against the 4.88%/yr the rule below produces on the same
        vintage's assumptions - and a receipts line four times too steep is a
        defect whether or not anything scored reads it.

        The rule below survives for the two vintages whose annual paths cannot
        be obtained (see :data:`CORPORATE_RECEIPTS_SOURCING`). It starts from
        that vintage's own base-year receipts and adds
        ``BASELINE_GROWTH["corporate_profit_premium"]`` to nominal GDP growth -
        a flat 1pp that is unsourced and that CBO's own February 2024 narrative
        contradicts, and which is left at its value here because retuning a
        constant is a different lane's work.
        """
        published = self._published_corporate_receipts()
        if published is not None:
            return published

        # More volatile, tied to profits
        revenue = np.zeros(10)
        revenue[0] = self.base_corporate_tax * 1.04

        for i in range(1, 10):
            # Corporate profits grow slightly faster than GDP
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i] + BASELINE_GROWTH["corporate_profit_premium"]
            revenue[i] = revenue[i-1] * (1 + growth)

        return revenue

    def _project_payroll_tax(self) -> np.ndarray:
        """Project payroll tax revenues."""
        # Tied to wage growth
        revenue = np.zeros(10)
        revenue[0] = self.base_payroll_tax * 1.04

        for i in range(1, 10):
            # Wage growth typically matches GDP growth
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i]
            revenue[i] = revenue[i-1] * (1 + growth)

        return revenue

    def _project_other_revenue(self) -> np.ndarray:
        """Project other revenues (excise, customs, misc)."""
        revenue = np.zeros(10)
        revenue[0] = self.base_other_revenue * 1.03

        for i in range(1, 10):
            revenue[i] = revenue[i-1] * (1 + BASELINE_GROWTH["other_revenue"])  # Slower growth

        return revenue

    def _project_social_security(self) -> np.ndarray:
        """Project Social Security spending."""
        # Fast growing due to demographics
        spending = np.zeros(10)
        spending[0] = self.base_social_security * 1.06

        for i in range(1, 10):
            # ~5% annual growth
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["social_security"])

        return spending

    def _project_medicare(self) -> np.ndarray:
        """Project Medicare spending."""
        # Fast growing due to demographics and healthcare costs
        spending = np.zeros(10)
        spending[0] = self.base_medicare * 1.07

        for i in range(1, 10):
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["medicare"])

        return spending

    def _project_medicaid(self) -> np.ndarray:
        """Project Medicaid spending."""
        spending = np.zeros(10)
        spending[0] = self.base_medicaid * 1.05

        for i in range(1, 10):
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["medicaid"])

        return spending

    def _project_other_mandatory(self) -> np.ndarray:
        """Project other mandatory spending."""
        spending = np.zeros(10)
        spending[0] = self.base_other_mandatory * 1.03

        for i in range(1, 10):
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["other_mandatory"])

        return spending

    def _project_defense(self) -> np.ndarray:
        """Project defense discretionary spending."""
        # Assume caps or slow growth
        spending = np.zeros(10)
        spending[0] = self.base_defense * 1.02

        for i in range(1, 10):
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["defense"])

        return spending

    def _project_nondefense(self) -> np.ndarray:
        """Project nondefense discretionary spending."""
        spending = np.zeros(10)
        spending[0] = self.base_nondefense * 1.01

        for i in range(1, 10):
            spending[i] = spending[i-1] * (1 + BASELINE_GROWTH["nondefense"])

        return spending

    def _project_debt(self, proj: BaselineProjection) -> np.ndarray:
        """Project debt held by public (iterative with interest)."""
        debt = np.zeros(10)
        debt[0] = self.base_debt + proj.deficit[0]

        for i in range(1, 10):
            debt[i] = debt[i-1] + proj.deficit[i]

        return debt

    def _project_interest(self, proj: BaselineProjection) -> np.ndarray:
        """Project net interest payments."""
        interest = np.zeros(10)

        for i in range(10):
            avg_debt = self.base_debt if i == 0 else (proj.debt_held_by_public[i-1] +
                                                       proj.debt_held_by_public[i]) / 2
            # Effective interest rate is lower than 10-year due to mix of maturities
            effective_rate = self.assumptions.interest_rate_10yr[i] * 0.75
            interest[i] = avg_debt * effective_rate

        return interest

    def adjust_for_policy(self, baseline: BaselineProjection,
                         category: str,
                         changes: np.ndarray) -> BaselineProjection:
        """
        Create a new projection with policy changes applied.

        Args:
            baseline: Original baseline projection
            category: Which category to modify
            changes: Array of changes for each year (in billions)

        Returns:
            New projection with changes applied
        """
        # Create a copy
        new_proj = BaselineProjection(
            start_year=baseline.start_year,
            years=baseline.years.copy(),
            nominal_gdp=baseline.nominal_gdp.copy(),
            real_gdp=baseline.real_gdp.copy(),
            individual_income_tax=baseline.individual_income_tax.copy(),
            corporate_income_tax=baseline.corporate_income_tax.copy(),
            payroll_taxes=baseline.payroll_taxes.copy(),
            other_revenues=baseline.other_revenues.copy(),
            social_security=baseline.social_security.copy(),
            medicare=baseline.medicare.copy(),
            medicaid=baseline.medicaid.copy(),
            other_mandatory=baseline.other_mandatory.copy(),
            defense_discretionary=baseline.defense_discretionary.copy(),
            nondefense_discretionary=baseline.nondefense_discretionary.copy(),
            net_interest=baseline.net_interest.copy(),
            debt_held_by_public=baseline.debt_held_by_public.copy(),
            base_nominal_gdp=baseline.base_nominal_gdp,
            published_nominal_gdp=dict(baseline.published_nominal_gdp),
        )

        # Apply changes
        current = getattr(new_proj, category)
        setattr(new_proj, category, current + changes)

        return new_proj

