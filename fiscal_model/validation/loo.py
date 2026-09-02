"""
Leave-one-out cross-validation for the calibrated (Tier 2) modules.

Why this exists
---------------
Tier 2's headline ~5% mean error is **true by construction**. Every calibrated
module carries one hard-coded ``annual_revenue_change_billions`` per benchmark
(``payroll.py``, ``estate.py``, ``amt.py``, ``credits_factory.py``,
``tax_expenditures_factory.py``), so the module reproduces its own targets
because it was told the answer. That number measures bookkeeping, not skill.

Leave-one-out asks the question the by-construction number cannot:

    Holding out one benchmark, can the module's structural machinery —
    calibrated on the *other* benchmarks — reproduce it?

Protocol
--------
For each case in a module with >= 3 benchmarks:

1. Delete the held-out case's own calibrated constant.
2. Re-derive that constant from the module's shared structural machinery plus
   the retained cases' calibration. The derivation functions in this module
   **never read the held-out official target** — every official number is
   funnelled through :func:`official_target`, which no ``derive_*`` function
   calls. ``tests/test_loo.py`` enforces that by monkeypatching
   :func:`official_target` to raise.
3. Score the reconstructed policy through the *same* validation runner the
   by-construction scorecard uses, so sign conventions, growth rules and
   result construction are identical. Only the one constant differs.
4. Report the error against the published target.

Derivation kinds
----------------
``structural`` (kind a)
    A shared mechanism can produce the held-out case from base data plus the
    other cases' calibration: SSA covered-wage bands (payroll), the
    exemption/rate machinery (estate), the AMT taxpayer-count x average-
    liability identity, the CTC/EITC per-unit credit formula.

``bottom_up`` (kind b)
    The annuals are independent free parameters (most of
    ``tax_expenditures_factory.py``), so there is nothing to "hold out" in the
    calibration. LOO instead rebuilds the held-out case from the module's
    published base table (``JCT_TAX_EXPENDITURES``, sourced to JCT's annual
    *Estimates of Federal Tax Expenditures*, JCX-48-24) plus the module's own
    reform-action rules.

``not_cross_validatable``
    Either the base constant the derivation would use **is** the official
    target restated (so "deriving" it would just read the answer key), or the
    target is not a published official score at all. These cases are reported
    with a reason and are **never folded into the aggregate**.

Leakage guard
-------------
:data:`LEAKAGE_TOLERANCE` — if a derived annual matches ``official / 10`` to
within 0.5%, the base constant is the target restated and the case is
downgraded to ``not_cross_validatable`` automatically. That single mechanical
rule catches ``expand_niit`` (payroll), ``repeal_corporate_amt`` (AMT) and
``eliminate_step_up`` (tax expenditures) without any hand-maintained list.

It does **not** catch the three credit benchmarks, and that is worth stating
because their fitted annuals *are* the target over ten. The guard tests the
**derived** annual, not the fitted one, and the credits module derives from the
CPS microdata rather than from its own constant — so the derivation is genuinely
held out even though the constant it replaces is the answer key. The tautology
on the fitted side is declared per case in ``scenarios.py`` under owner
Decision 5 instead of being deleted.

Aggregation
-----------
The suite reports mean / median / share-within-15% over the **derivable cases
only**, and states the count of non-derivable cases alongside. The two are
never combined into one number, exactly as Tier 1 and Tier 2 are never
combined (see ``CLAUDE.md`` "Target Validation").
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from ..amt import AMT_HELD_OUT_MODE, AMT_MODE_REPORTED
from ..credits_core import CREDIT_HELD_OUT_MODE
from ..credits_microdata import CreditMicrodataUnavailable
from ..estate import (
    ESTATE_HELD_OUT_MODE,
    ESTATE_MODE_REPORTED,
    soi_estate_anchor,
    soi_tax_base_pareto_alpha,
)
from ..payroll import SOCIAL_SECURITY_PARAMS, SSA_COVERED_WAGES_ABOVE_BILLIONS
from ..tax_expenditures_core import (
    EXPENDITURE_HELD_OUT_MODE,
    ExpenditureDistributionMissing,
)
from .core import ValidationResult
from .scenarios import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
)
from .specialized_benefits import validate_amt_policy
from .specialized_business import validate_expenditure_policy
from .specialized_capital_gains import validate_capital_gains_policy
from .specialized_household import (
    validate_credit_policy,
    validate_estate_policy,
    validate_payroll_policy,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DERIVATION_STRUCTURAL = "structural"
DERIVATION_BOTTOM_UP = "bottom_up"
DERIVATION_NONE = "not_cross_validatable"

#: A derived annual within this relative distance of ``official / 10`` means
#: the "base data" is the published target restated — not an independent
#: derivation. Such cases are excluded from the aggregate.
LEAKAGE_TOLERANCE = 0.005

#: Errors at or below this are counted in the headline "within 15%" share,
#: matching the tolerance the Tier 1 battery reports.
WITHIN_TOLERANCE_PCT = 15.0

#: Nominal scoring window for the window-average annuals.
HORIZON_YEARS = 10


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class LOOCase:
    """One held-out benchmark and the module's attempt to re-derive it."""

    module: str
    case_id: str
    policy_name: str
    official_10yr: float
    official_source: str
    derivation: str
    calibration_set: tuple[str, ...]
    loo_10yr: float | None = None
    calibrated_10yr: float | None = None
    derived_annual: float | None = None
    calibrated_annual: float | None = None
    percent_error: float | None = None
    included: bool = False
    exclusion_reason: str | None = None
    notes: str = ""

    @property
    def abs_percent_error(self) -> float | None:
        """Absolute LOO error, or ``None`` when nothing was derived."""
        return None if self.percent_error is None else abs(self.percent_error)

    @property
    def within_tolerance(self) -> bool:
        """True when the LOO error is inside :data:`WITHIN_TOLERANCE_PCT`."""
        err = self.abs_percent_error
        return err is not None and err <= WITHIN_TOLERANCE_PCT

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "case_id": self.case_id,
            "policy_name": self.policy_name,
            "official_10yr_billions": self.official_10yr,
            "official_source": self.official_source,
            "derivation": self.derivation,
            "calibration_set": list(self.calibration_set),
            "loo_10yr_billions": self.loo_10yr,
            "calibrated_10yr_billions": self.calibrated_10yr,
            "derived_annual_billions": self.derived_annual,
            "calibrated_annual_billions": self.calibrated_annual,
            "percent_error": self.percent_error,
            "abs_percent_error": self.abs_percent_error,
            "included_in_aggregate": self.included,
            "exclusion_reason": self.exclusion_reason,
            "notes": self.notes,
        }


@dataclass
class LOOReport:
    """Leave-one-out result for a single calibrated module."""

    module: str
    mechanism: str
    cases: list[LOOCase] = field(default_factory=list)

    @property
    def included_cases(self) -> list[LOOCase]:
        return [c for c in self.cases if c.included]

    @property
    def excluded_cases(self) -> list[LOOCase]:
        return [c for c in self.cases if not c.included]

    @property
    def derivation_kind(self) -> str:
        """``structural``/``bottom_up``/``mixed`` over the included cases."""
        kinds = {c.derivation for c in self.included_cases}
        if not kinds:
            return DERIVATION_NONE
        if len(kinds) == 1:
            return kinds.pop()
        return "mixed"

    @property
    def mean_abs_percent_error(self) -> float | None:
        return _mean([c.abs_percent_error for c in self.included_cases])

    @property
    def median_abs_percent_error(self) -> float | None:
        return _median([c.abs_percent_error for c in self.included_cases])

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "mechanism": self.mechanism,
            "derivation_kind": self.derivation_kind,
            "n_cases": len(self.cases),
            "n_included": len(self.included_cases),
            "n_not_cross_validatable": len(self.excluded_cases),
            "mean_abs_percent_error": self.mean_abs_percent_error,
            "median_abs_percent_error": self.median_abs_percent_error,
            "cases": [c.to_dict() for c in self.cases],
        }


@dataclass
class LOOSuite:
    """Aggregate ``Tier 2 (LOO)`` result across every calibrated module."""

    reports: list[LOOReport] = field(default_factory=list)

    @property
    def cases(self) -> list[LOOCase]:
        return [c for r in self.reports for c in r.cases]

    @property
    def included_cases(self) -> list[LOOCase]:
        return [c for c in self.cases if c.included]

    @property
    def excluded_cases(self) -> list[LOOCase]:
        return [c for c in self.cases if not c.included]

    @property
    def mean_abs_percent_error(self) -> float | None:
        return _mean([c.abs_percent_error for c in self.included_cases])

    @property
    def median_abs_percent_error(self) -> float | None:
        return _median([c.abs_percent_error for c in self.included_cases])

    @property
    def within_15pct(self) -> int:
        return sum(1 for c in self.included_cases if c.within_tolerance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": "Tier 2 (leave-one-out)",
            "n_included": len(self.included_cases),
            "n_not_cross_validatable": len(self.excluded_cases),
            "mean_abs_percent_error": self.mean_abs_percent_error,
            "median_abs_percent_error": self.median_abs_percent_error,
            "within_15pct": self.within_15pct,
            "within_15pct_share": (
                self.within_15pct / len(self.included_cases)
                if self.included_cases
                else None
            ),
            "modules": [r.to_dict() for r in self.reports],
        }


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _median(values: list[float | None]) -> float | None:
    present = sorted(v for v in values if v is not None)
    if not present:
        return None
    mid = len(present) // 2
    if len(present) % 2:
        return present[mid]
    return (present[mid - 1] + present[mid]) / 2


# ---------------------------------------------------------------------------
# Official-target access — the single choke point
# ---------------------------------------------------------------------------

_REGISTRIES: dict[str, dict[str, dict]] = {
    "Payroll": PAYROLL_TAX_VALIDATION_SCENARIOS,
    "Estate": ESTATE_TAX_VALIDATION_SCENARIOS,
    "AMT": AMT_VALIDATION_SCENARIOS_COMPARE,
    "Credits": TAX_CREDIT_VALIDATION_SCENARIOS,
    "Expenditures": TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
    "CapitalGains": CAPITAL_GAINS_VALIDATION_SCENARIOS,
}


def official_target(module: str, case_id: str) -> float:
    """
    Return the published 10-year target for ``case_id``.

    **Every** read of an official number goes through here. No ``derive_*``
    function in this module may call it — that invariant is what makes the
    leave-one-out predictions genuinely held out, and ``tests/test_loo.py``
    enforces it by monkeypatching this function to raise.
    """
    scenario = _REGISTRIES[module][case_id]
    if "expected_10yr" in scenario:
        return float(scenario["expected_10yr"])
    from .cbo_scores import KNOWN_SCORES  # local import: avoid cycle at import time

    return float(KNOWN_SCORES[scenario["score_id"]].ten_year_cost)


# ---------------------------------------------------------------------------
# Scoring harness — reuse the production runners so nothing can drift
# ---------------------------------------------------------------------------


@contextmanager
def _patched_scenario(registry: dict[str, dict], case_id: str, overrides: dict) -> Iterator[None]:
    """Temporarily replace one scenario entry, restoring it afterwards."""
    original = registry[case_id]
    registry[case_id] = {**original, **overrides}
    try:
        yield
    finally:
        registry[case_id] = original


def _score_with_annual(
    registry: dict[str, dict],
    runner: Callable[..., ValidationResult],
    case_id: str,
    annual: float,
) -> ValidationResult:
    """
    Score ``case_id`` with its calibrated annual replaced by ``annual``.

    The production validation runner does the scoring, so the LOO number and
    the by-construction number differ in exactly one input.
    """
    original_factory = registry[case_id]["policy_factory"]

    def factory(**kwargs: Any):
        policy = original_factory(**kwargs)
        policy.annual_revenue_change_billions = annual
        return policy

    with _patched_scenario(registry, case_id, {"policy_factory": factory}):
        return runner(case_id, verbose=False)


def _calibrated_result(
    runner: Callable[..., ValidationResult],
    case_id: str,
) -> ValidationResult:
    """Score ``case_id`` exactly as the by-construction scorecard does."""
    return runner(case_id, verbose=False)


def _calibrated_annual(registry: dict[str, dict], case_id: str) -> float | None:
    scenario = registry[case_id]
    policy = scenario["policy_factory"](**scenario.get("kwargs", {}))
    return getattr(policy, "annual_revenue_change_billions", None)


def _build_case(
    *,
    module: str,
    case_id: str,
    registry: dict[str, dict],
    runner: Callable[..., ValidationResult],
    derived_annual: float | None,
    derivation: str,
    calibration_set: tuple[str, ...],
    notes: str,
    exclusion_reason: str | None = None,
    calibrated_runner: Callable[..., ValidationResult] | None = None,
) -> LOOCase:
    """
    Assemble one :class:`LOOCase`, applying the leakage guard.

    ``calibrated_runner`` scores the by-construction leg when it must differ
    from the held-out leg by more than the one annual — AMT is the only such
    module: its held-out leg runs the module in ``derived`` mode, so the
    ``By-constr`` column has to be scored explicitly in ``reported`` mode or it
    would silently become a copy of the LOO column.
    """
    scenario = registry[case_id]
    official = official_target(module, case_id)
    calibrated = _calibrated_result(calibrated_runner or runner, case_id)

    case = LOOCase(
        module=module,
        case_id=case_id,
        policy_name=scenario.get("description", case_id),
        official_10yr=official,
        official_source=str(scenario.get("source", calibrated.official_source)),
        derivation=derivation,
        calibration_set=calibration_set,
        calibrated_10yr=calibrated.model_10yr,
        calibrated_annual=_calibrated_annual(registry, case_id),
        derived_annual=derived_annual,
        notes=notes,
        exclusion_reason=exclusion_reason,
    )

    if derivation == DERIVATION_NONE or derived_annual is None:
        case.derivation = DERIVATION_NONE
        case.included = False
        case.exclusion_reason = exclusion_reason or "no structural derivation available"
        return case

    if _restates_target(derived_annual, official):
        case.derivation = DERIVATION_NONE
        case.included = False
        case.exclusion_reason = (
            f"leakage guard: derived annual ${abs(derived_annual):,.1f}B equals the "
            f"published target / {HORIZON_YEARS} "
            f"(${abs(official) / HORIZON_YEARS:,.1f}B), so the base constant is the "
            "answer key restated"
        )
        return case

    loo = _score_with_annual(registry, runner, case_id, derived_annual)
    case.loo_10yr = loo.model_10yr
    case.percent_error = loo.percent_difference
    case.included = True
    return case


def _restates_target(derived_annual: float, official_10yr: float) -> bool:
    """True when the derived annual is just ``official / 10`` in disguise."""
    if official_10yr == 0:
        return False
    implied = abs(official_10yr) / HORIZON_YEARS
    if implied == 0:
        return False
    return abs(abs(derived_annual) - implied) / implied < LEAKAGE_TOLERANCE


# ---------------------------------------------------------------------------
# Payroll — kind (a): SSA covered-wage bands
# ---------------------------------------------------------------------------

#: The three payroll benchmarks that anchor ``SSA_COVERED_WAGES_ABOVE_BILLIONS``.
#: The 400K/500K/1M rows of that table are documented as interpolated from
#: these anchors, so they are *excluded* from every LOO calibration set — using
#: them would smuggle the held-out anchor back in.
PAYROLL_BAND_ANCHORS: dict[str, float] = {
    "ss_eliminate_cap": 176_100.0,
    "ss_donut_250k": 250_000.0,
    "ss_cap_90_pct": 305_000.0,
}

SS_COVER_90_CAP = 305_000.0


def _anchor_bands() -> dict[str, tuple[float, float]]:
    """Map each anchoring case to its ``(threshold, covered wages $B)`` row."""
    table = dict(SSA_COVERED_WAGES_ABOVE_BILLIONS)
    return {
        case_id: (threshold, table[threshold])
        for case_id, threshold in PAYROLL_BAND_ANCHORS.items()
        if threshold in table
    }


def _pareto_wages_above(bands: list[tuple[float, float]], threshold: float) -> float:
    """
    Covered wages above ``threshold`` from ``bands``, same rule as the module.

    Piecewise log-linear in (threshold, wages) space — a locally constant
    Pareto alpha — extrapolating with the nearest segment's slope, mirroring
    ``payroll.covered_wages_above``.
    """
    ordered = sorted(bands)
    if len(ordered) < 2:
        raise ValueError("need at least two anchors to fit a Pareto segment")

    if threshold <= ordered[0][0]:
        (t0, w0), (t1, w1) = ordered[0], ordered[1]
    elif threshold >= ordered[-1][0]:
        (t0, w0), (t1, w1) = ordered[-2], ordered[-1]
    else:
        segment = next(
            (a, b) for a, b in itertools.pairwise(ordered) if threshold <= b[0]
        )
        (t0, w0), (t1, w1) = segment

    alpha = math.log(w0 / w1) / math.log(t1 / t0)
    return float(w0 * (t0 / threshold) ** alpha)


def derive_payroll_annual(case_id: str) -> float | None:
    """
    Re-derive a payroll benchmark's annual from the *other* anchors' bands.

    Never reads the held-out target: the only held-out quantity is the covered
    wage level at the case's own threshold, which is refitted from the two
    retained anchors' Pareto slope. Returns ``None`` for NIIT expansion, which
    is a different mechanism (3.8% on pass-through income) with no second
    benchmark to calibrate against.
    """
    anchors = _anchor_bands()
    if case_id not in anchors:
        return None

    retained = [band for cid, band in anchors.items() if cid != case_id]
    rate = SOCIAL_SECURITY_PARAMS["rate_combined"]
    current_cap = SOCIAL_SECURITY_PARAMS["cap_2025"]

    if case_id == "ss_eliminate_cap":
        base = _pareto_wages_above(retained, current_cap)
    elif case_id == "ss_donut_250k":
        base = _pareto_wages_above(retained, PAYROLL_BAND_ANCHORS["ss_donut_250k"])
    else:  # ss_cap_90_pct — tax the band between the current cap and the 90% cap
        base = _pareto_wages_above(retained, current_cap) - _pareto_wages_above(
            retained, SS_COVER_90_CAP
        )
    return rate * base


def run_payroll_loo() -> LOOReport:
    """Leave-one-out over the four payroll benchmarks."""
    anchors = _anchor_bands()
    report = LOOReport(
        module="Payroll",
        mechanism=(
            "SSA covered-wage bands (SSA_COVERED_WAGES_ABOVE_BILLIONS) x the 12.4% "
            "OASDI rate. Each held-out anchor's wage level is refitted from the two "
            "retained anchors' Pareto slope; the interpolated 400K/500K/1M rows are "
            "excluded from every calibration set."
        ),
    )
    for case_id in PAYROLL_TAX_VALIDATION_SCENARIOS:
        derived = derive_payroll_annual(case_id)
        if derived is None:
            report.cases.append(
                _build_case(
                    module="Payroll",
                    case_id=case_id,
                    registry=PAYROLL_TAX_VALIDATION_SCENARIOS,
                    runner=validate_payroll_policy,
                    derived_annual=None,
                    derivation=DERIVATION_NONE,
                    calibration_set=(),
                    notes=(
                        "NIIT expansion is a separate mechanism (3.8% on pass-through "
                        "income), not the OASDI wage bands; it is the module's only "
                        "NIIT benchmark, so there is nothing to hold out against."
                    ),
                    exclusion_reason="mechanism has no second benchmark to calibrate on",
                )
            )
            continue
        retained = tuple(cid for cid in anchors if cid != case_id)
        report.cases.append(
            _build_case(
                module="Payroll",
                case_id=case_id,
                registry=PAYROLL_TAX_VALIDATION_SCENARIOS,
                runner=validate_payroll_policy,
                derived_annual=derived,
                derivation=DERIVATION_STRUCTURAL,
                calibration_set=retained,
                notes=(
                    "Covered wages above the case threshold refitted from the retained "
                    "anchors' Pareto slope, then multiplied by the 12.4% OASDI rate."
                ),
            )
        )
    return report


# ---------------------------------------------------------------------------
# Estate — kind (a): exemption / rate machinery
# ---------------------------------------------------------------------------

#: The one estate benchmark whose target is a model estimate rather than a
#: published score, and which the module therefore never folds into the
#: aggregate however well it derives.
ESTATE_UNPUBLISHED_TARGET_CASES = ("eliminate_estate_tax",)


def _estate_derived_runner(case_id: str, verbose: bool = False) -> ValidationResult:
    """Score an estate case through the SOI-fitted size distribution."""
    return validate_estate_policy(case_id, verbose=verbose, mode=ESTATE_HELD_OUT_MODE)


def _estate_reported_runner(case_id: str, verbose: bool = False) -> ValidationResult:
    """Score an estate case through the fitted annual constant."""
    return validate_estate_policy(case_id, verbose=verbose, mode=ESTATE_MODE_REPORTED)


def derive_estate_annual(case_id: str) -> float | None:
    """
    Re-derive an estate benchmark's annual from the size distribution.

    Builds the scenario's own policy in ``derived`` mode and returns the
    window average of its structural path, which reads no fitted constant:
    ``annual_revenue_change_billions`` is ignored in that mode. The
    ``extend_tcja_exemption`` short-circuit that used to return
    ``CBO_ESTATE_ESTIMATES["extend_tcja_annual"]`` — the published $167B target
    divided by ten, i.e. the answer key — is gone from
    ``estimate_static_revenue_effect`` outright, so there is nothing left to
    bypass. Nothing here touches :func:`official_target`.
    """
    scenario = ESTATE_TAX_VALIDATION_SCENARIOS.get(case_id)
    if scenario is None:
        return None
    if case_id in ESTATE_UNPUBLISHED_TARGET_CASES:
        return None
    policy = scenario["policy_factory"]()
    policy.mode = ESTATE_HELD_OUT_MODE
    return policy.derived_window_average()


def run_estate_loo() -> LOOReport:
    """Leave-one-out over the three estate benchmarks."""
    alpha = soi_tax_base_pareto_alpha()
    anchor = soi_estate_anchor()
    report = LOOReport(
        module="Estate",
        mechanism=(
            "Pareto size distribution of the estate tax base (taxable estate + adjusted "
            f"taxable gifts), shape alpha={alpha:.3f} pooled from IRS SOI Estate Tax "
            "Statistics Table 1 across filing years 2010, 2013 and 2024, level anchored "
            f"on SOI's own {anchor.filing_year} taxable-return panel "
            f"({anchor.taxable_returns:,} returns, "
            f"${anchor.net_estate_tax_billions:.1f}B of net estate tax at a "
            f"${anchor.exemption/1e6:.2f}M exemption). Evaluated on the baseline and "
            "reform exemption paths year by year, one year behind the fiscal year "
            "because Form 706 is filed the year after death. Shared base data, not "
            "per-benchmark constants."
        ),
    )
    all_ids = tuple(ESTATE_TAX_VALIDATION_SCENARIOS)
    for case_id in all_ids:
        derived = derive_estate_annual(case_id)
        retained = tuple(cid for cid in all_ids if cid != case_id)
        if derived is None:
            report.cases.append(
                _build_case(
                    module="Estate",
                    case_id=case_id,
                    registry=ESTATE_TAX_VALIDATION_SCENARIOS,
                    runner=_estate_derived_runner,
                    calibrated_runner=_estate_reported_runner,
                    derived_annual=None,
                    derivation=DERIVATION_NONE,
                    calibration_set=(),
                    notes=(
                        "The machinery now reproduces revenue levels as well as "
                        "differences — its 2026 baseline is ~$47.6B against CBO's ~$50B "
                        "projection, where the old two-point blend implied ~$196B — so "
                        "full repeal is derivable. It stays out of the aggregate for the "
                        "other reason: the $350B target is sourced 'Model estimate', not "
                        "a published score."
                    ),
                    exclusion_reason="target is not a published official score",
                )
            )
            continue
        report.cases.append(
            _build_case(
                module="Estate",
                case_id=case_id,
                registry=ESTATE_TAX_VALIDATION_SCENARIOS,
                runner=_estate_derived_runner,
                calibrated_runner=_estate_reported_runner,
                derived_annual=derived,
                derivation=DERIVATION_STRUCTURAL,
                calibration_set=retained,
                notes=(
                    "Derived from the SOI-fitted tax-base distribution; the fitted annual "
                    "is ignored in derived mode and the extend_tcja_annual short-circuit "
                    "(= target / 10) no longer exists in the module at all."
                ),
            )
        )
    return report


# ---------------------------------------------------------------------------
# AMT — kind (a): taxpayer count x average liability
# ---------------------------------------------------------------------------


def _amt_derived_runner(case_id: str, verbose: bool = False) -> ValidationResult:
    """Score an AMT case through the module's structural (``derived``) path."""
    return validate_amt_policy(case_id, verbose=verbose, mode=AMT_HELD_OUT_MODE)


def _amt_reported_runner(case_id: str, verbose: bool = False) -> ValidationResult:
    """Score an AMT case through the fitted (``reported``) annual constant."""
    return validate_amt_policy(case_id, verbose=verbose, mode=AMT_MODE_REPORTED)


def derive_amt_annual(case_id: str) -> float | None:
    """
    Re-derive an individual-AMT benchmark from the module's published base.

    The identity is unchanged — affected-payer count x average liability — but
    it is now evaluated **year by year** against TPC's T25-0049 aggregate AMT
    path, with the baseline leg at the current-law exemption and the policy leg
    at the reform exemption (``AMTPolicy.derived_annual_effect``). The
    calibration constants in ``CBO_AMT_ESTIMATES`` are bypassed, and so is the
    single-point ``BASELINE_AMT_DATA`` summary the earlier derivation used.

    The value returned is the first **non-zero** year of that path, which is
    what ``AMTPolicy.estimate_static_revenue_effect`` returns in derived mode; the
    remaining years reach the scorer through ``AMTPolicy.get_phase_in_factor``,
    so the LOO 10-year figure is the path's own sum rather than this number
    grown at a flat rate. It is reported here because it is the quantity the
    leakage guard has to inspect.

    Corporate AMT returns ``None``: its only base constant,
    ``CORPORATE_AMT["revenue_per_year"] = 22.0``, is the published $220B target
    restated, and no published year path exists for CAMT to replace it.
    """
    if case_id not in ("extend_tcja_amt", "repeal_individual_amt"):
        return None
    scenario = AMT_VALIDATION_SCENARIOS_COMPARE[case_id]
    policy = scenario["policy_factory"](
        **scenario.get("kwargs", {}), mode=AMT_HELD_OUT_MODE
    )
    return float(policy.derived_anchor_effect())


def run_amt_loo() -> LOOReport:
    """Leave-one-out over the three AMT benchmarks."""
    report = LOOReport(
        module="AMT",
        mechanism=(
            "Individual-AMT revenue as affected-payer count x average liability, "
            "evaluated year by year on TPC T25-0049 with the baseline leg at the "
            "current-law exemption and the policy leg at the reform exemption. "
            "Extending TCJA relief costs the difference between the two regimes; "
            "full repeal costs the whole post-sunset path."
        ),
    )
    all_ids = tuple(AMT_VALIDATION_SCENARIOS_COMPARE)
    for case_id in all_ids:
        derived = derive_amt_annual(case_id)
        retained = tuple(cid for cid in all_ids if cid != case_id)
        if derived is None:
            report.cases.append(
                _build_case(
                    module="AMT",
                    case_id=case_id,
                    registry=AMT_VALIDATION_SCENARIOS_COMPARE,
                    runner=_amt_derived_runner,
                    calibrated_runner=_amt_reported_runner,
                    derived_annual=None,
                    derivation=DERIVATION_NONE,
                    calibration_set=(),
                    notes=(
                        "CAMT's only base constant is CORPORATE_AMT['revenue_per_year'] "
                        "= $22B/yr, which is the CBO $220B/10yr target restated. Nothing "
                        "independent remains to derive, and TPC publishes no year path "
                        "for the corporate book minimum tax."
                    ),
                    exclusion_reason="base constant is the published target restated",
                )
            )
            continue
        report.cases.append(
            _build_case(
                module="AMT",
                case_id=case_id,
                registry=AMT_VALIDATION_SCENARIOS_COMPARE,
                runner=_amt_derived_runner,
                calibrated_runner=_amt_reported_runner,
                derived_annual=derived,
                derivation=DERIVATION_STRUCTURAL,
                calibration_set=retained,
                notes=(
                    "Scored through AMTPolicy's derived mode, so the fitted annual is "
                    "not read at all rather than replaced by a scalar. Both cases come "
                    "out further above the carried $450B than the old flat derivation "
                    "did, and that is the finding: TPC shows the 2026 sunset as a cliff "
                    "(0.2M payers to 7.6M) with the path then *growing* to $124.2B by "
                    "2035, so the flat ~$73B/yr was the window's early-year level, not "
                    "its average. The residual is a target problem this lane may not "
                    "touch — benchmark_sources.py records the published line item at "
                    "$1,357.1B and the five-year figure at $466.2B."
                ),
            )
        )
    return report


# ---------------------------------------------------------------------------
# Credits — kind (a): per-unit credit formula
# ---------------------------------------------------------------------------


def derive_credit_annual(case_id: str) -> float | None:
    """
    Re-derive a credit benchmark by summing per-unit credits over the CPS file.

    Builds the scenario's own policy in ``derived`` mode and returns the window
    average of its structural path: the counterfactual and reform statutory
    schedules evaluated tax unit by tax unit over CPS ASEC 2024, differenced on
    final tax liability. Nothing here reads
    ``annual_revenue_change_billions`` — which matters more for this module
    than any other, because all three of its annuals are the published target
    divided by exactly ten.

    This replaced the per-unit *cost identity*
    (``credit_change x units x participation``), which understated all three
    expansions by 28 to 64 percent for a structural reason rather than a noisy
    one: it prices a change in the credit amount and nothing else, so
    refundability, an eligibility expansion and a phase-out threshold are all
    invisible to it.

    Returns ``None`` when the policy has no CTC or EITC schedule to move, or
    when the microdata file carries no dependent ages.
    """
    scenario = TAX_CREDIT_VALIDATION_SCENARIOS.get(case_id)
    if scenario is None:
        return None
    policy = scenario["policy_factory"](**scenario.get("kwargs", {}))
    policy.mode = CREDIT_HELD_OUT_MODE
    try:
        return policy.derived_window_average()
    except CreditMicrodataUnavailable:
        return None


def run_credits_loo() -> LOOReport:
    """Leave-one-out over the three tax-credit benchmarks."""
    report = LOOReport(
        module="Credits",
        mechanism=(
            "Per-unit credit schedules evaluated over CPS ASEC 2024 tax units: the "
            "counterfactual and reform CTC/EITC parameter sets are each run through "
            "MicroTaxCalculator and differenced on final tax liability, weighted and "
            "averaged over the window. The counterfactual moves with the law - "
            "current law in 2025, the pre-TCJA regime from 2026 - and the statutory "
            "schedules come from CTC_CURRENT_LAW and EITC_CURRENT_LAW, not from any "
            "per-benchmark constant."
        ),
    )
    all_ids = tuple(TAX_CREDIT_VALIDATION_SCENARIOS)
    for case_id in all_ids:
        derived = derive_credit_annual(case_id)
        retained = tuple(cid for cid in all_ids if cid != case_id)
        report.cases.append(
            _build_case(
                module="Credits",
                case_id=case_id,
                registry=TAX_CREDIT_VALIDATION_SCENARIOS,
                runner=validate_credit_policy,
                derived_annual=derived,
                derivation=(
                    DERIVATION_STRUCTURAL if derived is not None else DERIVATION_NONE
                ),
                calibration_set=retained if derived is not None else (),
                notes=(
                    "Read the By-constr column here as arithmetic, not evidence: each "
                    "of these three annuals is the published target divided by exactly "
                    "ten, so a 0.0% fitted error tests x/10 x 10 == x (owner "
                    "Decision 5; scenarios.py carries the per-case declaration). The "
                    "LOO column is the only one that measures anything, and the "
                    "residual it leaves is a coverage gap in the survey file rather "
                    "than a missing rule: CPS ASEC records no self-employment "
                    "earnings, which the EITC counts, and its dependency rule folds "
                    "19-to-23-year-olds with a parent pointer into the parent's tax "
                    "unit - the population a childless-EITC age expansion is mostly "
                    "about."
                ),
                exclusion_reason=(
                    None
                    if derived is not None
                    else (
                        "no CTC or EITC schedule to move, or the microdata file "
                        "carries no dependent ages"
                    )
                ),
            )
        )
    return report


# ---------------------------------------------------------------------------
# Tax expenditures — kind (b): bottom-up from the JCT base table
# ---------------------------------------------------------------------------


def derive_expenditure_annual(case_id: str) -> float | None:
    """
    Rebuild a tax-expenditure benchmark from its published base.

    These annuals are independent free parameters — there is no shared
    mechanism linking, say, the SALT cap repeal to the charitable cap — so LOO
    can only mean: drop the calibrated constant and let the module's own
    reform-action rules run against ``JCT_TAX_EXPENDITURES``, the base table
    sourced to JCT's *Estimates of Federal Tax Expenditures* (JCX-48-24; the
    curated snapshot lives in ``assistant/knowledge/jct_tax_expenditures.md``).

    Returns ``None`` when the expenditure type has **no base-table entry** at
    all — there is then nothing to rebuild from — or when a cap is asked for
    on an expenditure whose base has no transcribed distribution, since the
    rule then cannot see the quantity it is capping. A rule that runs and
    returns ``0.0`` is a real (and very wrong) derivation, and is reported as
    a ~100% error rather than quietly dropped: silently excluding it would hide
    exactly the misconfiguration this suite exists to surface.
    """
    scenario = TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE.get(case_id)
    if scenario is None:
        return None
    policy = scenario["policy_factory"](**scenario.get("kwargs", {}))
    if not policy.get_expenditure_data():
        return None
    policy.mode = EXPENDITURE_HELD_OUT_MODE
    policy.annual_revenue_change_billions = None
    try:
        return float(policy.estimate_static_revenue_effect(0.0))
    except ExpenditureDistributionMissing:
        return None


def run_tax_expenditure_loo() -> LOOReport:
    """Leave-one-out over the six tax-expenditure benchmarks."""
    report = LOOReport(
        module="Expenditures",
        mechanism=(
            "Bottom-up from JCT_TAX_EXPENDITURES (JCX-48-24 base table) through the "
            "module's own eliminate/cap/expand action rules. The calibrated annuals are "
            "independent constants, so nothing is 'held out' from a shared fit — the "
            "test is whether the published base plus the reform rule reaches the score."
        ),
    )
    all_ids = tuple(TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE)
    for case_id in all_ids:
        derived = derive_expenditure_annual(case_id)
        retained = tuple(cid for cid in all_ids if cid != case_id)
        report.cases.append(
            _build_case(
                module="Expenditures",
                case_id=case_id,
                registry=TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
                runner=validate_expenditure_policy,
                derived_annual=derived,
                derivation=(
                    DERIVATION_BOTTOM_UP if derived is not None else DERIVATION_NONE
                ),
                calibration_set=retained if derived is not None else (),
                notes=(
                    "Base table entry plus the module's action rule; no per-benchmark "
                    "calibration is retained because none exists to retain."
                ),
                exclusion_reason=(
                    None
                    if derived is not None
                    else (
                        "no JCT base-table entry for this expenditure type, or "
                        "no transcribed distribution of the quantity this "
                        "reform caps"
                    )
                ),
            )
        )
    return report


# ---------------------------------------------------------------------------
# Capital gains — the sharpest test: frozen elasticities
# ---------------------------------------------------------------------------

#: The behavioural parameter set used by ``frozen`` mode: the
#: ``CapitalGainsPolicy`` dataclass defaults, which come from the realizations
#: literature (Dowd, McClelland & Muthitacharoen 2015 — persistent 0.72,
#: transitory 1.2, both at the 22% reference rate CRS R48562 states its
#: estimates are adjusted to) rather than from any of the three benchmarks.
#: Structural fields (baseline rate, realizations, whether step-up applies, the
#: gains-at-death scope) stay at their scenario values — those define *what*
#: the policy is. Since Wave 2's L1 the scenarios carry no behavioural fields
#: at all, so every donor row of the matrix is this same set.
FROZEN_CAPITAL_GAINS_PARAMS: dict[str, float] = {
    "persistent_elasticity": 0.72,
    "transitory_elasticity": 1.20,
    "elasticity_reference_rate": 0.22,
}


def run_capital_gains_loo() -> LOOReport:
    """
    Score all three capital-gains benchmarks with one frozen elasticity set.

    The three scenarios used to carry three *different* hand-set
    elasticity/lock-in tuples (3.2/2.8 with lock-in 1.0; 0.8/0.4 with lock-in
    5.3; 0.8/0.4 with a 1.5x residual-avoidance multiplier). Each was the
    module's most-tuned parameter, and each was chosen after seeing its own
    target. Wave 2's L1 deleted them, so the scenarios now carry only
    structural fields and this runner scores all three on the one frozen
    literature set — which is what converted that parameter into a prediction.
    """
    report = LOOReport(
        module="CapitalGains",
        mechanism=(
            "Semi-log realizations response R1 = R0 x exp(-b (t1 - t0)) with "
            "b = elasticity / reference rate, frozen at the CapitalGainsPolicy "
            "dataclass defaults (Dowd, McClelland & Muthitacharoen 2015: persistent "
            "0.72, transitory 1.2, at a 22% reference rate) instead of each "
            "scenario's hand-set tuple. Lock-in is the with/without-step-up price "
            "wedge implied by the accrued-gains stock, not a multiplier."
        ),
    )
    # Built directly rather than through _build_case: this module's held-out
    # quantity is a *parameter set*, not a single annual constant, so there is
    # no derived annual to run the leakage guard against. The guard is not
    # needed here either — the frozen values are dataclass defaults from the
    # realizations literature and cannot be any target restated.
    for case_id in CAPITAL_GAINS_VALIDATION_SCENARIOS:
        calibrated = _calibrated_result(validate_capital_gains_policy, case_id)
        retained = tuple(
            cid for cid in CAPITAL_GAINS_VALIDATION_SCENARIOS if cid != case_id
        )
        with _patched_scenario(
            CAPITAL_GAINS_VALIDATION_SCENARIOS, case_id, FROZEN_CAPITAL_GAINS_PARAMS
        ):
            frozen = validate_capital_gains_policy(case_id, verbose=False)
        report.cases.append(
            LOOCase(
                module="CapitalGains",
                case_id=case_id,
                policy_name=CAPITAL_GAINS_VALIDATION_SCENARIOS[case_id]["description"],
                official_10yr=official_target("CapitalGains", case_id),
                official_source=calibrated.official_source,
                derivation=DERIVATION_STRUCTURAL,
                calibration_set=retained,
                loo_10yr=frozen.model_10yr,
                calibrated_10yr=calibrated.model_10yr,
                percent_error=frozen.percent_difference,
                included=True,
                notes=(
                    "Scored with the frozen literature elasticity set rather than this "
                    "scenario's hand-set tuple."
                ),
            )
        )
    return report


def capital_gains_donor_matrix() -> dict[str, dict[str, float]]:
    """
    Score every capital-gains case under every scenario's elasticity tuple.

    Diagnostic for "is one tuple the calibrated answer key?": the outer key is
    the *donor* scenario whose behavioural parameters are borrowed, the inner
    key is the case being scored, and the value is the signed percent error.

    Every behavioural field is written explicitly — a field the donor leaves
    unset falls back to the dataclass default rather than to the scored case's
    own hand-set value, which would leak the answer key back in.
    """
    matrix: dict[str, dict[str, float]] = {}
    for donor_id, donor in CAPITAL_GAINS_VALIDATION_SCENARIOS.items():
        donor_params = {
            name: donor.get(name, default)
            for name, default in FROZEN_CAPITAL_GAINS_PARAMS.items()
        }
        row: dict[str, float] = {}
        for case_id in CAPITAL_GAINS_VALIDATION_SCENARIOS:
            with _patched_scenario(
                CAPITAL_GAINS_VALIDATION_SCENARIOS, case_id, donor_params
            ):
                row[case_id] = validate_capital_gains_policy(
                    case_id, verbose=False
                ).percent_difference
        matrix[donor_id] = row
    return matrix


# ---------------------------------------------------------------------------
# Suite
# ---------------------------------------------------------------------------

MODULE_RUNNERS: dict[str, Callable[[], LOOReport]] = {
    "Payroll": run_payroll_loo,
    "Estate": run_estate_loo,
    "AMT": run_amt_loo,
    "Credits": run_credits_loo,
    "Expenditures": run_tax_expenditure_loo,
    "CapitalGains": run_capital_gains_loo,
}


def run_leave_one_out() -> LOOSuite:
    """Run leave-one-out across every calibrated module with >= 3 benchmarks."""
    return LOOSuite(reports=[runner() for runner in MODULE_RUNNERS.values()])
