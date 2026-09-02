"""
Score a credit reform by summing per-unit credits over the CPS microdata.

Why this module exists
----------------------
``TaxCreditPolicy.estimate_static_revenue_effect`` prices a credit change as
``Δcredit × units × participation``. That identity can express "the credit per
child went up by \\$1,300" and nothing else. It cannot see refundability (a
family with no tax liability gets none of a non-refundable increase, and all of
a refundable one), it cannot see a phase-out threshold moving, and it cannot see
an eligibility expansion at all — which is why the three declared levers
``expand_qualifying_age``, ``include_childless_adults`` and
``take_up_rate_change`` had no code path to reach. Measured against the three
credit benchmarks the identity understated every one of them
(``planning/lanes/L3_credits.md`` §1).

The mechanism here is the one ``planning/MODELING_IMPROVEMENT.md`` §3 L3 asks
for: build the counterfactual and the reform parameter sets, run
:class:`fiscal_model.microsim.engine.MicroTaxCalculator` over the weighted CPS
tax units under each, and take the weighted difference in final tax liability.
Refundability, the tax-liability cap on the non-refundable leg, the ACTC
earnings phase-in, both CTC phase-out tiers and the EITC's own qualifying-child
and age tests all fall out of the calculator rather than being asserted.

The counterfactual moves with the law
-------------------------------------
A ten-year window that starts in 2025 straddles the TCJA sunset, so the
counterfactual a permanent credit is scored against is **not one schedule**:
it is current law in 2025 and the pre-TCJA regime from 2026, when IRC sec. 24's
\\$2,000 reverts to \\$1,000 under P.L. 115-97 sec. 11022(b). The baseline is
therefore a function of the year, not a constant. This is most of what
separates a \\$1.6T score for a permanent ARP child credit from the roughly
\\$0.9T the same reform costs against a \\$2,000 baseline throughout.

What it does not do
-------------------
No labour-supply response, and no take-up *level*: only the change a reform
itself buys (``take_up_rate_change``). The CPS file records who could claim a
credit, not who does, so a full-take-up computation overstates; but the file's
own coverage runs the other way — 119% of SOI returns against 81% of SOI AGI,
and no self-employment earnings at all, which the EITC counts. Both errors are
stated rather than netted against each other.

Income growth over the scoring window is applied as a uniform nominal factor on
the CPS incomes, with the statutory parameters held at their nominal levels —
which is what the statute does: the CTC's \\$2,000, its \\$200k/\\$400k
thresholds and the ACTC's \\$2,500 floor are not indexed, while the EITC's are.
The EITC parameters are therefore grown at the same rate and the CTC's are not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from .credits_core import CTC_CURRENT_LAW, EITC_CURRENT_LAW

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .credits_core import TaxCreditPolicy

#: Nominal growth applied to CPS incomes across the scoring window. Matches the
#: 3% ``estimate_credit_cost`` already uses for bottom-up unit×credit paths, so
#: the derived window average and the bottom-up one grow on the same assumption.
NOMINAL_GROWTH = 0.03

#: Scoring window length, matching ``HORIZON_YEARS`` in the validation harness.
WINDOW_YEARS = 10

#: Columns the derived path needs beyond the engine's own requirements.
REQUIRED_DEPENDENT_COLUMNS = (
    "dependents_under_6",
    "dependents_6_to_16",
    "dependents_age_17",
    "dependents_age_18",
    "dependents_19_to_23_student",
)

#: Incomes that grow with the nominal path.
_INCOME_COLUMNS = (
    "wages",
    "interest_income",
    "dividend_income",
    "capital_gains",
    "investment_income",
    "social_security",
    "unemployment",
    "agi",
)


class CreditMicrodataUnavailable(RuntimeError):
    """The CPS file cannot support a per-unit credit derivation.

    Raised rather than silently falling back so a caller never mistakes a
    degraded answer for the real one; ``loo.py`` turns it into a documented
    exclusion.
    """


@dataclass(frozen=True)
class CreditSchedule:
    """One leg of a credit comparison, as ``MicroTaxCalculator`` reform keys.

    A schedule is a complete statement of the CTC and EITC parameters for a
    single legal regime. Two of them — counterfactual and reform — are what a
    credit score is a difference of.
    """

    #: Reform-dict entries handed straight to ``MicroTaxCalculator``.
    params: dict[str, float | bool | int] = field(default_factory=dict)

    def grown(self, factor: float, *, grow_eitc: bool = True) -> CreditSchedule:
        """Return the schedule with its indexed dollar amounts scaled.

        The CTC's amounts and thresholds are *not* indexed under current law,
        so they are left alone; the EITC's are, so they move with incomes.
        Applying growth to incomes but not to an indexed parameter would
        manufacture real bracket creep the statute does not have.
        """
        if not grow_eitc:
            return self
        grown = dict(self.params)
        for key in (
            "eitc_childless_max_credit",
            "eitc_childless_phaseout_start_single",
            "eitc_childless_phaseout_start_married",
        ):
            if key in grown:
                grown[key] = float(grown[key]) * factor
        if "eitc_expansion" in grown:
            # A multiplier, not a dollar amount — indexation is already in the
            # level it multiplies.
            pass
        return replace(self, params=grown)


def current_law_ctc_schedule() -> CreditSchedule:
    """Current-law (2025, post-TCJA) CTC parameters."""
    return CreditSchedule(
        params={
            "ctc_amount": CTC_CURRENT_LAW["credit_per_child"],
            "ctc_qualifying_age": int(CTC_CURRENT_LAW["qualifying_age"]),
            "ctc_phaseout_start_single": CTC_CURRENT_LAW["phase_out_start_single"],
            "ctc_phaseout_start_married": CTC_CURRENT_LAW["phase_out_start_married"],
            "ctc_fully_refundable": False,
            "actc_max_per_child": CTC_CURRENT_LAW["refundable_max"],
            "actc_earned_threshold": CTC_CURRENT_LAW["refund_threshold"],
            "actc_phasein_rate": CTC_CURRENT_LAW["refund_rate"],
        }
    )


def pre_tcja_ctc_schedule() -> CreditSchedule:
    """Post-2025-sunset CTC parameters — the pre-TCJA regime.

    \\$1,000 per child, refundable up to \\$1,000 at 15% of earnings above
    \\$3,000, phasing out from \\$75,000 / \\$110,000. These are the pre-TCJA
    statutory levels already carried in ``CTC_CURRENT_LAW``.
    """
    return CreditSchedule(
        params={
            "ctc_amount": CTC_CURRENT_LAW["pre_tcja_credit"],
            "ctc_qualifying_age": int(CTC_CURRENT_LAW["qualifying_age"]),
            "ctc_phaseout_start_single": CTC_CURRENT_LAW["pre_tcja_phase_out_single"],
            "ctc_phaseout_start_married": CTC_CURRENT_LAW["pre_tcja_phase_out_married"],
            "ctc_fully_refundable": False,
            "actc_max_per_child": CTC_CURRENT_LAW["pre_tcja_refundable_max"],
            # The pre-TCJA ACTC earnings floor was $3,000; TCJA cut it to
            # $2,500. IRC sec. 24(d)(1)(B)(i) as in effect before P.L. 115-97.
            "actc_earned_threshold": 3_000.0,
            "actc_phasein_rate": CTC_CURRENT_LAW["refund_rate"],
        }
    )


def current_law_eitc_schedule() -> CreditSchedule:
    """Current-law childless EITC parameters (the engine's own defaults)."""
    childless = EITC_CURRENT_LAW[0]
    return CreditSchedule(
        params={
            "eitc_childless_max_credit": childless["max_credit"],
            "eitc_childless_phasein_rate": childless["phase_in_rate"],
            "eitc_childless_phaseout_rate": childless["phase_out_rate"],
            "eitc_childless_phaseout_start_single": childless["phase_out_start_single"],
            "eitc_childless_phaseout_start_married": childless[
                "phase_out_start_married"
            ],
            "eitc_childless_min_age": 25,
            "eitc_childless_max_age": 65,
        }
    )


def no_rebate_schedule() -> CreditSchedule:
    """The counterfactual for a recovery rebate: no rebate at all."""
    return CreditSchedule(params={"rebate_per_person": 0.0})


@lru_cache(maxsize=1)
def _base_population() -> pd.DataFrame:
    """Load the CPS tax-unit file once per process."""
    from .data.cps_asec import load_tax_microdata

    df, source = load_tax_microdata()
    if not source.has_dependent_ages:
        raise CreditMicrodataUnavailable(
            f"{source.path} carries no dependent age bands. Rebuild it with "
            "`python -m fiscal_model.microsim.data_builder --fetch`."
        )
    keep = [
        "weight",
        "married",
        "children",
        "dependent_count",
        "age_head",
        *REQUIRED_DEPENDENT_COLUMNS,
        *(column for column in _INCOME_COLUMNS),
    ]
    return df[[column for column in keep if column in df.columns]].copy()


def _grown_population(factor: float) -> pd.DataFrame:
    """The CPS population with every income column scaled by ``factor``."""
    pop = _base_population()
    if factor == 1.0:
        return pop
    grown = pop.copy()
    for column in _INCOME_COLUMNS:
        if column in grown.columns:
            grown.loc[:, column] = grown[column] * factor
    return grown


def weighted_liability_change(
    baseline: CreditSchedule,
    reform: CreditSchedule,
    *,
    growth_factor: float = 1.0,
    year: int = 2025,
) -> float:
    """Weighted change in final tax liability, in billions.

    Positive means revenue rises (the reform is a tax increase); a credit
    expansion therefore returns a negative number, matching the sign convention
    ``estimate_static_revenue_effect`` uses.
    """
    from .microsim.engine import MicroTaxCalculator

    pop = _grown_population(growth_factor)
    calc = MicroTaxCalculator(year=year)
    baseline_result = calc.apply_reform(pop, dict(baseline.params))
    reform_result = calc.apply_reform(pop, dict(reform.params))
    delta = reform_result["final_tax"].values - baseline_result["final_tax"].values
    return float((delta * pop["weight"].values).sum() / 1e9)


def window_average_change(
    baseline_for_year: Callable[[int], CreditSchedule],
    reform: CreditSchedule,
    *,
    start_year: int = 2025,
    years: int = WINDOW_YEARS,
    growth: float = NOMINAL_GROWTH,
) -> float:
    """Window average of the annual liability change, in billions per year.

    The validation harness treats ``annual_revenue_change_billions`` as a
    window average and holds it flat, so a single-year level would misstate a
    path that moves. Each year's incomes are grown at ``growth`` and the EITC's
    indexed parameters with them; the CTC's unindexed amounts and thresholds
    stay nominal, which is what makes its real value erode across the window
    exactly as the statute has it. ``baseline_for_year`` supplies the
    counterfactual in force that year, which is how the 2025 sunset enters.
    """
    annuals = []
    for offset in range(years):
        factor = (1.0 + growth) ** offset
        year = start_year + offset
        annuals.append(
            weighted_liability_change(
                baseline_for_year(year).grown(factor),
                reform.grown(factor),
                growth_factor=factor,
                year=start_year,
            )
        )
    return float(np.mean(annuals))


def derived_annual_for_policy(policy: TaxCreditPolicy) -> float | None:
    """Window-average annual revenue effect of ``policy``, or ``None``.

    ``None`` means the policy is not one the per-unit path can express — an
    ``OTHER``-type credit with no CTC or EITC schedule behind it, for instance.
    Callers treat that as "no derivation", never as zero.
    """
    schedules = policy.credit_schedules()
    if schedules is None:
        return None
    baseline_for_year, reform = schedules
    delta = window_average_change(
        baseline_for_year, reform, start_year=policy.start_year
    )
    return delta * policy.effective_take_up_rate()


__all__ = [
    "NOMINAL_GROWTH",
    "REQUIRED_DEPENDENT_COLUMNS",
    "WINDOW_YEARS",
    "CreditMicrodataUnavailable",
    "CreditSchedule",
    "current_law_ctc_schedule",
    "current_law_eitc_schedule",
    "derived_annual_for_policy",
    "no_rebate_schedule",
    "pre_tcja_ctc_schedule",
    "weighted_liability_change",
    "window_average_change",
]
