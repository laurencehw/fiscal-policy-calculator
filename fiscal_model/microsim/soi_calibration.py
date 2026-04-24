"""
SOI calibration: compare microsim aggregates to IRS Statistics of Income.

A microsim is only as credible as its calibration. This module computes
bracket-level aggregates from a tax-unit microdata file, compares them
against IRS SOI Table 1.1 for the same year, and reports the deltas
that will surface in downstream scoring.

Two flows are supported:

1. **Read-only comparison** — ``calibrate_to_soi`` returns a structured
   report showing, for each AGI bracket, how many returns and how much
   total AGI the microsim has vs. SOI. The report is what the validation
   tab and CI should cite.

2. **Ratio reweighting** — ``reweight_to_soi`` scales tax-unit weights
   within each bracket so the weighted sum matches SOI. This is a first-
   pass reweighter (no raking, no entropy objective); a full implementation
   would use iterative proportional fitting. Use this as scaffolding —
   the rough correction is better than nothing, but it does not match
   the precision of a full calibration suite like taxdata's.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from fiscal_model.data.irs_soi import IRSSOIData, TaxBracketData

logger = logging.getLogger(__name__)


# Bracket edges (lower bound) used when collapsing microdata AGI into
# buckets that approximately line up with SOI Table 1.1. Using a small,
# fixed set of buckets makes calibration comparable across years even
# when SOI re-cuts its internal reporting.
DEFAULT_CALIBRATION_BRACKETS = (
    0,
    15_000,
    30_000,
    50_000,
    75_000,
    100_000,
    200_000,
    500_000,
    1_000_000,
    10_000_000,  # informal cap; everything above lands in the top bucket
)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BracketComparison:
    """Single-bracket comparison row."""

    lower: float
    upper: float | None
    microsim_returns: float
    soi_returns: float
    microsim_agi_billions: float
    soi_agi_billions: float

    @property
    def returns_ratio(self) -> float | None:
        if self.soi_returns <= 0:
            return None
        return self.microsim_returns / self.soi_returns

    @property
    def agi_ratio(self) -> float | None:
        if self.soi_agi_billions <= 0:
            return None
        return self.microsim_agi_billions / self.soi_agi_billions


@dataclass
class CalibrationReport:
    """Full SOI calibration report for one year."""

    year: int
    brackets: list[BracketComparison] = field(default_factory=list)

    @property
    def total_microsim_returns(self) -> float:
        return sum(b.microsim_returns for b in self.brackets)

    @property
    def total_soi_returns(self) -> float:
        return sum(b.soi_returns for b in self.brackets)

    @property
    def total_microsim_agi_billions(self) -> float:
        return sum(b.microsim_agi_billions for b in self.brackets)

    @property
    def total_soi_agi_billions(self) -> float:
        return sum(b.soi_agi_billions for b in self.brackets)

    def summary(self) -> dict[str, float]:
        return {
            "year": float(self.year),
            "total_microsim_returns_millions": self.total_microsim_returns / 1e6,
            "total_soi_returns_millions": self.total_soi_returns / 1e6,
            "total_microsim_agi_trillions": self.total_microsim_agi_billions / 1000.0,
            "total_soi_agi_trillions": self.total_soi_agi_billions / 1000.0,
            "returns_coverage_pct": (
                100.0 * self.total_microsim_returns / self.total_soi_returns
                if self.total_soi_returns > 0
                else 0.0
            ),
            "agi_coverage_pct": (
                100.0 * self.total_microsim_agi_billions / self.total_soi_agi_billions
                if self.total_soi_agi_billions > 0
                else 0.0
            ),
        }

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "AGI lower": b.lower,
                    "AGI upper": b.upper,
                    "Microsim returns (M)": b.microsim_returns / 1e6,
                    "SOI returns (M)": b.soi_returns / 1e6,
                    "Returns ratio (sim/SOI)": b.returns_ratio,
                    "Microsim AGI ($B)": b.microsim_agi_billions,
                    "SOI AGI ($B)": b.soi_agi_billions,
                    "AGI ratio (sim/SOI)": b.agi_ratio,
                }
                for b in self.brackets
            ]
        )


# ---------------------------------------------------------------------------
# Core calibration / reweighting
# ---------------------------------------------------------------------------


def _aggregate_microdata_by_bracket(
    microdata: pd.DataFrame,
    brackets: tuple[float, ...],
) -> list[tuple[float, float | None, float, float]]:
    """Return ``[(lower, upper_or_None, returns, agi_billions), ...]``."""
    if "agi" not in microdata.columns or "weight" not in microdata.columns:
        raise ValueError(
            "Microdata must include 'agi' and 'weight' columns. See "
            "fiscal_model/data/cps_asec.py for the required schema."
        )

    rows: list[tuple[float, float | None, float, float]] = []
    for idx, lower in enumerate(brackets):
        upper = brackets[idx + 1] if idx + 1 < len(brackets) else None
        if upper is None:
            mask = microdata["agi"] >= lower
        else:
            mask = (microdata["agi"] >= lower) & (microdata["agi"] < upper)
        slice_ = microdata.loc[mask]
        returns = float(slice_["weight"].sum())
        agi_b = float((slice_["agi"] * slice_["weight"]).sum() / 1e9)
        rows.append((float(lower), float(upper) if upper is not None else None, returns, agi_b))
    return rows


def _aggregate_soi_by_bracket(
    soi_brackets: list[TaxBracketData],
    brackets: tuple[float, ...],
) -> list[tuple[float, float | None, float, float]]:
    """Collapse native SOI brackets into our calibration buckets."""
    # Treat each SOI bracket as its own interval; assign it to the
    # calibration bucket that contains its floor. SOI bucket edges are
    # finer than ours in most years, so this collapses correctly as long
    # as SOI buckets don't straddle calibration edges (they rarely do).
    rows: list[tuple[float, float | None, float, float]] = []
    for idx, lower in enumerate(brackets):
        upper = brackets[idx + 1] if idx + 1 < len(brackets) else None
        returns = 0.0
        agi_b = 0.0
        for bucket in soi_brackets:
            if upper is None:
                in_bucket = bucket.agi_floor >= lower
            else:
                in_bucket = lower <= bucket.agi_floor < upper
            if in_bucket:
                returns += float(bucket.num_returns)
                agi_b += float(bucket.total_agi)
        rows.append((float(lower), float(upper) if upper is not None else None, returns, agi_b))
    return rows


def calibrate_to_soi(
    microdata: pd.DataFrame,
    year: int,
    *,
    brackets: tuple[float, ...] = DEFAULT_CALIBRATION_BRACKETS,
    soi_loader: IRSSOIData | None = None,
) -> CalibrationReport:
    """
    Compare microdata to IRS SOI Table 1.1 and return a structured report.

    Args:
        microdata: Tax-unit DataFrame with ``agi`` and ``weight`` columns.
        year: SOI year to compare against.
        brackets: AGI lower bounds; the last entry becomes an implicit
            open-ended top bucket.
        soi_loader: Optional injected ``IRSSOIData`` (for tests).

    Returns:
        ``CalibrationReport`` with one row per calibration bracket.
    """
    soi_loader = soi_loader or IRSSOIData()
    try:
        soi_brackets = soi_loader.get_bracket_distribution(year)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load SOI Table 1.1 for {year}: {exc}. "
            "Verify fiscal_model/data_files/irs_soi/table_1_1_<year>.csv exists."
        ) from exc

    microsim_rows = _aggregate_microdata_by_bracket(microdata, brackets)
    soi_rows = _aggregate_soi_by_bracket(soi_brackets, brackets)

    comparisons: list[BracketComparison] = []
    for (m_lower, m_upper, m_returns, m_agi), (_s_lower, _s_upper, s_returns, s_agi) in zip(
        microsim_rows, soi_rows, strict=True
    ):
        comparisons.append(
            BracketComparison(
                lower=m_lower,
                upper=m_upper,
                microsim_returns=m_returns,
                soi_returns=s_returns,
                microsim_agi_billions=m_agi,
                soi_agi_billions=s_agi,
            )
        )

    return CalibrationReport(year=year, brackets=comparisons)


def reweight_to_soi(
    microdata: pd.DataFrame,
    year: int,
    *,
    brackets: tuple[float, ...] = DEFAULT_CALIBRATION_BRACKETS,
    soi_loader: IRSSOIData | None = None,
    inplace: bool = False,
) -> pd.DataFrame:
    """
    Scale tax-unit weights within each AGI bracket so the weighted returns
    count matches SOI.

    This is a single-dimension proportional reweight: it fixes the returns
    margin but does not jointly calibrate AGI, wages, or dependents. For a
    production-grade calibrator, use iterative proportional fitting or
    taxdata's entropy-based approach.

    The function is included here so the microsim test harness can fail
    loudly when a microdata file diverges from SOI beyond a tolerance,
    and so the demo microdata can be quickly aligned to SOI aggregates
    for illustration.

    Args:
        inplace: If True, mutate ``microdata`` in place. Otherwise, return
            a shallow copy.

    Returns:
        The (possibly copied) DataFrame with adjusted ``weight`` column.
    """
    if not inplace:
        microdata = microdata.copy()

    report = calibrate_to_soi(
        microdata, year, brackets=brackets, soi_loader=soi_loader
    )

    for bracket in report.brackets:
        if bracket.microsim_returns <= 0 or bracket.soi_returns <= 0:
            continue
        ratio = bracket.soi_returns / bracket.microsim_returns
        # Avoid extreme corrections that would blow up variance.
        ratio = float(np.clip(ratio, 0.1, 10.0))
        if bracket.upper is None:
            mask = microdata["agi"] >= bracket.lower
        else:
            mask = (microdata["agi"] >= bracket.lower) & (
                microdata["agi"] < bracket.upper
            )
        microdata.loc[mask, "weight"] = microdata.loc[mask, "weight"] * ratio

    return microdata


__all__ = [
    "DEFAULT_CALIBRATION_BRACKETS",
    "BracketComparison",
    "CalibrationReport",
    "calibrate_to_soi",
    "reweight_to_soi",
]
