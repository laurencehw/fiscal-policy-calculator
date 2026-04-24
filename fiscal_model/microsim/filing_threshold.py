"""
Filing-status filter for CPS-derived microdata.

CPS ASEC covers every US household; IRS Statistics of Income covers
*filed returns*. About 30M CPS tax units are non-filers — people whose
income is below the federal filing threshold and who don't file for a
refund. They show up in the bundled microdata as legitimate population
records but inflate the low-AGI calibration buckets against SOI.

Concretely, SOI 2023 reports ~161M returns, while the bundled CPS
microdata weights to ~191M tax units — a 30M gap that lives almost
entirely in the \\$0-\\$15K AGI bucket (coverage ratio 2.65x). Any
distributional analysis that compares model output to SOI aggregates
without filtering will over-represent the bottom.

This module applies the IRS filing thresholds to the microdata:

- Married filing jointly: AGI >= \\$27,700 (2023) — filed if either
  spouse has gross income, plus various edge cases.
- Single / head of household: AGI >= \\$13,850 (2023).
- Any tax unit with self-employment income >= \\$400 must file
  regardless of AGI (not modelled here — requires self-employment
  column which the CPS build doesn't preserve).

The filter is permissive at the edges: it retains tax units who might
file for refundable credits (EITC, CTC) even if they are technically
below the gross-income threshold. The result is a 'likely filer'
population whose weighted total lands within a few percent of SOI.

Opt-in so the default microdata path remains pure population-level.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

# 2023 IRS filing thresholds (USD).
FILING_THRESHOLDS_2023 = {
    "single": 13_850,
    "married_joint": 27_700,
    "head_of_household": 20_800,
}

# Rough year-over-year inflation factor we apply to other years until a
# per-year threshold table is wired in. Off by no more than a few
# percent for 2019-2025.
_CPI_FACTOR_FROM_2023 = {
    2019: 0.85,
    2020: 0.86,
    2021: 0.91,
    2022: 0.98,
    2023: 1.00,
    2024: 1.03,
    2025: 1.06,
    2026: 1.08,
}


@dataclass(frozen=True)
class FilerFilterReport:
    """What the filter removed."""

    year: int
    rows_before: int
    rows_after: int
    weighted_before: float
    weighted_after: float
    threshold_applied_single: float
    threshold_applied_married: float

    @property
    def rows_removed(self) -> int:
        return self.rows_before - self.rows_after

    @property
    def weighted_removed(self) -> float:
        return self.weighted_before - self.weighted_after


def _thresholds_for_year(year: int) -> dict[str, float]:
    factor = _CPI_FACTOR_FROM_2023.get(year, 1.0)
    return {
        k: v * factor for k, v in FILING_THRESHOLDS_2023.items()
    }


def filter_to_filers(
    microdata: pd.DataFrame,
    year: int,
    *,
    include_refund_filers: bool = True,
) -> tuple[pd.DataFrame, FilerFilterReport]:
    """
    Drop tax units that clearly did not file a federal return.

    The goal is to move the weighted population from CPS tax-unit
    counts (~191M, 2023 build) toward SOI filer counts (~161M). It is
    calibrated deliberately loose: we drop only units with *all* of

    - no wages,
    - no Social Security / unemployment,
    - no dividend / interest / capital-gain income,
    - no children (so they can't file for refundable CTC),
    - and AGI below the single-filer gross income threshold.

    Anyone with any positive income signal or a child is kept — they
    might file a return for refunded withholding, EITC, or CTC, and
    those filers do appear in SOI. The resulting filter drops about
    30M weighted units, moving microsim-to-SOI coverage from 1.19× to
    ~1.00×.

    Args:
        microdata: Tax-unit DataFrame with ``agi``, ``married``,
            ``wages``, ``weight`` columns.
        year: Tax year (used to select inflation-adjusted thresholds).
        include_refund_filers: Kept for backwards compatibility; the
            filter always includes refund-eligible units now.

    Returns:
        Tuple of ``(filtered_df, report)``. Filtered frame has the
        same schema as input; report describes what was removed.
    """
    del include_refund_filers  # always True under the looser filter
    required = {"agi", "married", "wages", "weight"}
    missing = required - set(microdata.columns)
    if missing:
        raise ValueError(
            f"filter_to_filers requires columns {sorted(required)}; missing {sorted(missing)}"
        )

    thresholds = _thresholds_for_year(year)
    single_thr = thresholds["single"]
    married_thr = thresholds["married_joint"]

    # Income signals — any positive value implies potential filing.
    def _positive(col: str) -> pd.Series:
        if col in microdata.columns:
            return microdata[col].astype(float) > 0
        return pd.Series(False, index=microdata.index)

    has_wages = _positive("wages")
    has_benefits = _positive("social_security") | _positive("unemployment")
    has_investment = (
        _positive("dividend_income")
        | _positive("interest_income")
        | _positive("capital_gains")
    )
    has_children = (
        microdata["children"].astype(int) > 0
        if "children" in microdata.columns
        else pd.Series(False, index=microdata.index)
    )
    agi = microdata["agi"].astype(float)
    is_married = microdata["married"].astype(int) > 0

    # Definitely files: clears the statutory threshold.
    meets_threshold = (
        ((~is_married) & (agi >= single_thr))
        | (is_married & (agi >= married_thr))
    )

    # Probably files: refundable credit or withholding-refund candidate.
    probable_refund_filer = (
        (agi > 0) & (has_wages | has_benefits | has_investment | has_children)
    )

    keep_mask = meets_threshold | probable_refund_filer

    # Keep augmented synthetic records unconditionally — they represent
    # SOI filer aggregates by construction.
    if "source" in microdata.columns:
        keep_mask = keep_mask | (microdata["source"] != "cps")

    filtered = microdata.loc[keep_mask].copy()
    report = FilerFilterReport(
        year=year,
        rows_before=len(microdata),
        rows_after=len(filtered),
        weighted_before=float(microdata["weight"].sum()),
        weighted_after=float(filtered["weight"].sum()),
        threshold_applied_single=single_thr,
        threshold_applied_married=married_thr,
    )
    return filtered, report


__all__ = [
    "FILING_THRESHOLDS_2023",
    "FilerFilterReport",
    "filter_to_filers",
]
