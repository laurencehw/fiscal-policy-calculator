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

3. **Cell calibration (opt-in)** — ``calibrate_cells_to_soi`` calibrates
   weights within every (AGI class x filing status) cell of IRS SOI
   Table 1.2 so that *both* the cell's return count and its AGI are hit,
   by an entropy-minimising exponential tilt. Nothing calls it by default;
   it exists so the dashboard's ``--calibrate-cells`` flag and a future
   owner decision have a measured, diagnosable alternative to the shipped
   (uncalibrated) weights. See ``planning/lanes/R6_microdata_cell_calibration.md``.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from fiscal_model.data.irs_soi import IRSSOIData, TaxBracketData
from fiscal_model.microsim.top_tail import SYNTHETIC_SOURCE_LABEL

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


# ---------------------------------------------------------------------------
# Cell calibration (AGI class x filing status, returns AND AGI)
# ---------------------------------------------------------------------------

CELL_MODE_HIT = "count+agi"
CELL_MODE_COUNT_ONLY = "count-only"
CELL_MODE_EMPTY = "empty"
CELL_MODE_NO_TARGET = "no-target"

STATUS_MARRIED = "married"
STATUS_HOH = "hoh"
STATUS_SINGLE = "single"

# Newton tolerance (relative to the cell target) and the acceptance check the
# solved weights must pass before a cell is reported as ``count+agi``.
_TILT_TOLERANCE = 1e-9
_TILT_ACCEPT = 1e-6
_TILT_MAX_ITER = 200
_MIN_ROWS_FOR_TILT = 5


@dataclass(frozen=True)
class CellResult:
    """One (AGI class, filing status) cell of the calibration."""

    agi_class: int
    agi_floor: float
    status: str
    rows: int
    target_returns: float
    target_agi_billions: float
    returns_before: float
    returns_after: float
    agi_billions_before: float
    agi_billions_after: float
    mode: str
    max_weight_ratio: float

    @property
    def returns_ratio_before(self) -> float | None:
        return self.returns_before / self.target_returns if self.target_returns > 0 else None

    @property
    def returns_ratio_after(self) -> float | None:
        return self.returns_after / self.target_returns if self.target_returns > 0 else None

    @property
    def agi_ratio_before(self) -> float | None:
        if self.target_agi_billions <= 0:
            return None
        return self.agi_billions_before / self.target_agi_billions

    @property
    def agi_ratio_after(self) -> float | None:
        if self.target_agi_billions <= 0:
            return None
        return self.agi_billions_after / self.target_agi_billions


@dataclass
class CellCalibrationDiagnostics:
    """What a cell calibration did, cell by cell and in aggregate.

    Coverage figures compare weighted microdata to SOI Table 1.1's totals over
    *all* AGI classes, including the "no AGI" class whose negative total
    ($-144.2B in TY2023) no non-negative microdata record can represent; that
    class is why AGI coverage after calibration sits just above 100%, not at it.
    """

    year: int
    cells: list[CellResult] = field(default_factory=list)
    collapse_unmarried_from_class: int | None = None
    returns_coverage_before_pct: float = 0.0
    returns_coverage_after_pct: float = 0.0
    agi_coverage_before_pct: float = 0.0
    agi_coverage_after_pct: float = 0.0
    effective_sample_size_before: float = 0.0
    effective_sample_size_after: float = 0.0
    max_weight_ratio: float = 0.0
    min_weight_ratio: float = 0.0

    @property
    def cells_hit(self) -> int:
        return sum(1 for c in self.cells if c.mode == CELL_MODE_HIT)

    @property
    def cells_count_only(self) -> int:
        return sum(1 for c in self.cells if c.mode == CELL_MODE_COUNT_ONLY)

    @property
    def cells_empty(self) -> int:
        return sum(1 for c in self.cells if c.mode == CELL_MODE_EMPTY)

    @property
    def cells_no_target(self) -> int:
        return sum(1 for c in self.cells if c.mode == CELL_MODE_NO_TARGET)

    @property
    def empty_cells(self) -> list[CellResult]:
        return [c for c in self.cells if c.mode == CELL_MODE_EMPTY]

    @property
    def count_only_cells(self) -> list[CellResult]:
        return [c for c in self.cells if c.mode == CELL_MODE_COUNT_ONLY]

    @property
    def unrepresented_returns(self) -> float:
        """SOI returns sitting in cells with no microdata record at all."""
        return sum(c.target_returns for c in self.empty_cells)

    def summary(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "cells": len(self.cells),
            "cells_hit": self.cells_hit,
            "cells_count_only": self.cells_count_only,
            "cells_empty": self.cells_empty,
            "cells_no_target": self.cells_no_target,
            "returns_coverage_before_pct": self.returns_coverage_before_pct,
            "returns_coverage_after_pct": self.returns_coverage_after_pct,
            "agi_coverage_before_pct": self.agi_coverage_before_pct,
            "agi_coverage_after_pct": self.agi_coverage_after_pct,
            "effective_sample_size_before": self.effective_sample_size_before,
            "effective_sample_size_after": self.effective_sample_size_after,
            "max_weight_ratio": self.max_weight_ratio,
            "min_weight_ratio": self.min_weight_ratio,
            "unrepresented_returns": self.unrepresented_returns,
            "collapse_unmarried_from_class": self.collapse_unmarried_from_class,
        }

    def to_dict(self) -> dict[str, Any]:
        out = self.summary()
        out["cell_detail"] = [
            {**asdict(c), "returns_ratio_after": c.returns_ratio_after, "agi_ratio_after": c.agi_ratio_after}
            for c in self.cells
        ]
        return out


def filing_status_cells(microdata: pd.DataFrame) -> np.ndarray:
    """Assign each tax unit to one of SOI's three calibration statuses.

    ``married`` (joint plus separate) when ``married > 0``; otherwise ``hoh``
    when the unit carries a dependent (``dependent_count``, falling back to
    ``children``); otherwise ``single``. This is the same rule the credits and
    distribution engines use to split a unit's filing status.
    """
    married = microdata["married"].to_numpy() > 0
    if "dependent_count" in microdata.columns:
        has_dep = microdata["dependent_count"].to_numpy() > 0
    elif "children" in microdata.columns:
        has_dep = microdata["children"].to_numpy() > 0
    else:
        has_dep = np.zeros(len(microdata), dtype=bool)
    return np.where(married, STATUS_MARRIED, np.where(has_dep, STATUS_HOH, STATUS_SINGLE))


def _tilt_cell(
    w0: np.ndarray, x: np.ndarray, count: float, agi: float
) -> np.ndarray | None:
    """Solve ``w = w0 * exp(a + b*z)`` so ``sum(w) = count`` and ``sum(w*x) = agi``.

    Entropy-minimising calibration with a linear constraint on AGI (``z`` is
    within-cell standardised AGI). Returns ``None`` when no such tilt exists:
    too few rows, no spread, the target mean outside the cell's observed range,
    or Newton failing to converge to the target.
    """
    if x.size < _MIN_ROWS_FOR_TILT or count <= 0:
        return None
    mean = agi / count
    if not (x.min() < mean < x.max()) or float(np.ptp(x)) == 0.0:
        return None
    scale = max(float(x.std()), 1.0)
    z = (x - mean) / scale
    target = np.array([count, 0.0])
    lam = np.array([np.log(count / w0.sum()), 0.0])
    converged = False
    for _ in range(_TILT_MAX_ITER):
        e = w0 * np.exp(lam[0] + lam[1] * z)
        grad = np.array([e.sum() - count, float((e * z).sum())])
        if abs(grad[0]) < _TILT_TOLERANCE * count and abs(grad[1]) < _TILT_TOLERANCE * count:
            converged = True
            break
        hess = np.array(
            [[e.sum(), float((e * z).sum())], [float((e * z).sum()), float((e * z * z).sum())]]
        )
        step = np.linalg.solve(hess, grad)
        objective0 = e.sum() - lam @ target
        t = 1.0
        while t > 1e-6:
            trial = lam - t * step
            e2 = w0 * np.exp(trial[0] + trial[1] * z)
            if e2.sum() - trial @ target <= objective0 + 1e-12 * abs(objective0):
                break
            t /= 2.0
        lam = lam - t * step
    if not converged:
        return None
    w = np.asarray(w0 * np.exp(lam[0] + lam[1] * z), dtype=float)
    if abs(w.sum() - count) > _TILT_ACCEPT * count or abs(float((w * x).sum()) - agi) > _TILT_ACCEPT * abs(agi):
        return None
    return w


def _class_index(agi: np.ndarray, floors: np.ndarray) -> np.ndarray:
    """SOI class index of each AGI. Values below the first floor (negative AGI)
    belong to SOI's first, "no adjusted gross income" class."""
    idx = np.searchsorted(floors, agi, side="right") - 1
    return np.asarray(np.maximum(idx, 0))


def _effective_sample_size(w: np.ndarray) -> float:
    denom = float((w**2).sum())
    return float(w.sum() ** 2 / denom) if denom > 0 else 0.0


def calibrate_cells_to_soi(
    microdata: pd.DataFrame,
    year: int = 2023,
    *,
    soi_loader: IRSSOIData | None = None,
    collapse_unmarried_from: float | None = None,
    use_agi: bool = True,
) -> tuple[pd.DataFrame, CellCalibrationDiagnostics]:
    """Calibrate weights to IRS SOI Table 1.2 by AGI class x filing status.

    For each of SOI's 19 AGI classes and each of ``married`` (joint plus
    separate), ``hoh`` and ``single``, the unit weights in that cell are tilted
    ``w = w0 * exp(a + b*z)`` so the cell's weighted **return count and AGI**
    both equal SOI's. Where the cell's target mean AGI lies outside the cell's
    observed AGI range (or there are fewer than five rows) the cell falls back
    to a count-only rescale and is flagged ``count-only``; a cell with SOI
    returns but no microdata rows is flagged ``empty`` and left unrepresented.
    Targets are Table 1.2 only; nothing is fitted to any benchmark.

    Pure and deterministic: no network, no randomness, input not mutated.

    Args:
        microdata: tax-unit frame with ``agi``, ``weight``, ``married`` and
            (optionally) ``dependent_count`` / ``children``.
        year: SOI year (Tables 1.1 and 1.2 must exist for it).
        soi_loader: injectable ``IRSSOIData``.
        collapse_unmarried_from: AGI floor from which ``hoh`` and ``single``
            are one cell. Synthetic top-tail records carry only married /
            unmarried, so by default this is the floor of the lowest class
            holding any ``soi_pareto_augmented`` row; ``None`` with no
            synthetic rows means no collapse.
        use_agi: ``False`` rescales to counts only (post-stratification).

    Returns:
        ``(calibrated_df, diagnostics)``. ``household_weight`` is untouched.
    """
    for column in ("agi", "weight", "married"):
        if column not in microdata.columns:
            raise ValueError(f"cell calibration needs a {column!r} column")
    loader = soi_loader or IRSSOIData()
    try:
        classes = loader.get_bracket_distribution(year)
        by_status = loader.get_bracket_distribution_by_status(year)
    except Exception as exc:
        raise RuntimeError(
            f"Could not load SOI Tables 1.1/1.2 for {year}: {exc}."
        ) from exc

    floors = np.array([c.agi_floor for c in classes], dtype=float)
    n_classes = len(classes)

    out = microdata.copy()
    agi = out["agi"].to_numpy(dtype=float)
    w_before = out["weight"].to_numpy(dtype=float)
    w_after = w_before.copy()
    cls = _class_index(agi, floors)
    status = filing_status_cells(out)

    collapse_cls: int | None = None
    if collapse_unmarried_from is not None:
        collapse_cls = int(_class_index(np.array([collapse_unmarried_from]), floors)[0])
        if floors[collapse_cls] < collapse_unmarried_from:
            collapse_cls += 1
    elif "source" in out.columns:
        synthetic = (out["source"] == SYNTHETIC_SOURCE_LABEL).to_numpy()
        if synthetic.any():
            collapse_cls = int(cls[synthetic].min())
    if collapse_cls is not None:
        status = np.where((cls >= collapse_cls) & (status == STATUS_HOH), STATUS_SINGLE, status)

    def _cell_targets(i: int) -> list[tuple[str, float, float]]:
        joint, sep = by_status["joint"][i], by_status["separate"][i]
        hoh, single = by_status["head_of_household"][i], by_status["single"][i]
        married = (joint.num_returns + sep.num_returns, (joint.total_agi + sep.total_agi) * 1e9)
        if collapse_cls is not None and i >= collapse_cls:
            return [
                (STATUS_MARRIED, *married),
                (
                    STATUS_SINGLE,
                    hoh.num_returns + single.num_returns,
                    (hoh.total_agi + single.total_agi) * 1e9,
                ),
            ]
        return [
            (STATUS_MARRIED, *married),
            (STATUS_HOH, hoh.num_returns, hoh.total_agi * 1e9),
            (STATUS_SINGLE, single.num_returns, single.total_agi * 1e9),
        ]

    cells: list[CellResult] = []
    for i in range(n_classes):
        for st, n_target, a_target in _cell_targets(i):
            mask = (cls == i) & (status == st)
            rows = int(mask.sum())
            w0 = w_before[mask]
            x = agi[mask]
            r_before = float(w0.sum())
            a_before = float((w0 * x).sum() / 1e9)
            if n_target <= 0:
                cells.append(
                    CellResult(i, float(floors[i]), st, rows, float(n_target), a_target / 1e9,
                               r_before, r_before, a_before, a_before, CELL_MODE_NO_TARGET, 1.0)
                )
                continue
            if rows == 0 or r_before <= 0:
                cells.append(
                    CellResult(i, float(floors[i]), st, rows, float(n_target), a_target / 1e9,
                               r_before, r_before, a_before, a_before, CELL_MODE_EMPTY, 0.0)
                )
                continue
            tilted = _tilt_cell(w0, x, n_target, a_target) if (use_agi and a_target > 0) else None
            mode = CELL_MODE_HIT
            if tilted is None:
                tilted = w0 * (n_target / r_before)
                mode = CELL_MODE_COUNT_ONLY
            w_after[mask] = tilted
            positive = w0 > 0
            ratio = float((tilted[positive] / w0[positive]).max()) if positive.any() else 0.0
            cells.append(
                CellResult(i, float(floors[i]), st, rows, float(n_target), a_target / 1e9,
                           r_before, float(tilted.sum()), a_before,
                           float((tilted * x).sum() / 1e9), mode, ratio)
            )

    out["weight"] = w_after

    soi_returns = float(sum(c.num_returns for c in classes))
    soi_agi_b = float(sum(c.total_agi for c in classes))
    changed = (w_before > 0) & (w_after != w_before)
    ratios = w_after[changed] / w_before[changed] if changed.any() else np.array([1.0])
    diagnostics = CellCalibrationDiagnostics(
        year=year,
        cells=cells,
        collapse_unmarried_from_class=collapse_cls,
        returns_coverage_before_pct=100.0 * float(w_before.sum()) / soi_returns,
        returns_coverage_after_pct=100.0 * float(w_after.sum()) / soi_returns,
        agi_coverage_before_pct=100.0 * float((w_before * agi).sum() / 1e9) / soi_agi_b,
        agi_coverage_after_pct=100.0 * float((w_after * agi).sum() / 1e9) / soi_agi_b,
        effective_sample_size_before=_effective_sample_size(w_before),
        effective_sample_size_after=_effective_sample_size(w_after),
        max_weight_ratio=float(ratios.max()),
        min_weight_ratio=float(ratios.min()),
    )
    return out, diagnostics


__all__ = [
    "CELL_MODE_COUNT_ONLY",
    "CELL_MODE_EMPTY",
    "CELL_MODE_HIT",
    "CELL_MODE_NO_TARGET",
    "DEFAULT_CALIBRATION_BRACKETS",
    "BracketComparison",
    "CalibrationReport",
    "CellCalibrationDiagnostics",
    "CellResult",
    "calibrate_cells_to_soi",
    "calibrate_to_soi",
    "filing_status_cells",
    "reweight_to_soi",
]
