"""
Core tax credit types, constants, and helper functions.

Two scoring modes (owner Decision 1)
------------------------------------
``TaxCreditPolicy.mode`` selects between:

``reported``
    Return the calibrated ``annual_revenue_change_billions`` — the window
    average fitted to an official score. This is the app default, and it is
    what every shipped preset uses.

``derived``
    Build the counterfactual and reform credit schedules from the policy's own
    fields and score them per unit over the CPS microdata
    (:mod:`fiscal_model.credits_microdata`). This is the default in the
    held-out validation path, where reading a constant fitted to the target
    would be reading the answer key.

The distinction matters more here than in any other calibrated module: all
three credit benchmarks carry an annual that is exactly the published target
divided by ten, so their by-construction error is arithmetic rather than
evidence (owner Decision 5).

The statutory schedules below are the single source both this module and
:class:`fiscal_model.microsim.engine.MicroTaxCalculator` read. EITC amounts are
tax year 2024, Rev. Proc. 2023-34 sec. 2.06; CTC amounts are IRC sec. 24 as
amended by P.L. 115-97.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np

from .policies import PolicyType, TaxPolicy

#: Score from the fitted window-average annual.
CREDIT_MODE_REPORTED = "reported"

#: Score per unit over the CPS microdata.
CREDIT_MODE_DERIVED = "derived"

CREDIT_MODES = (CREDIT_MODE_REPORTED, CREDIT_MODE_DERIVED)

#: What the app and every shipped preset use. Stays ``reported`` until the
#: derived path beats the fitted one on this module's benchmarks — Decision 1's
#: own rule. Read ``planning/lanes/L3_credits.md`` §4 before flipping it: with
#: Decision 5 the fitted rows are the target restated, so "beats fitted" is not
#: a contest the derived path can win on the carried targets.
CREDIT_APP_MODE = CREDIT_MODE_REPORTED

#: What ``validation/loo.py`` scores the held-out leg in.
CREDIT_HELD_OUT_MODE = CREDIT_MODE_DERIVED

#: What the by-construction scorecard scores in. ``reported``, so the fitted
#: tier keeps reporting the fitted number and Decision 5's exclusion is what
#: carries the honesty rather than a silent mode switch.
CREDIT_SCORECARD_MODE = CREDIT_MODE_REPORTED

#: First year the TCJA child credit reverts to its pre-TCJA level.
#: P.L. 115-97 sec. 11022(b) sunsets the $2,000 credit after 2025.
CTC_SUNSET_YEAR = 2026


class CreditType(Enum):
    """Types of tax credits."""

    CHILD_TAX_CREDIT = "ctc"
    EARNED_INCOME_CREDIT = "eitc"
    PREMIUM_TAX_CREDIT = "ptc"
    EDUCATION_CREDIT = "education"
    OTHER = "other"


CTC_CURRENT_LAW = {
    "credit_per_child": 2000.0,
    "refundable_max": 1700.0,
    "refund_rate": 0.15,
    "refund_threshold": 2500.0,
    "phase_out_start_single": 200000.0,
    "phase_out_start_married": 400000.0,
    "phase_out_rate": 0.05,
    "qualifying_age": 17,
    "pre_tcja_credit": 1000.0,
    "pre_tcja_refundable_max": 1000.0,
    "pre_tcja_phase_out_single": 75000.0,
    "pre_tcja_phase_out_married": 110000.0,
}


EITC_CURRENT_LAW = {
    0: {
        "phase_in_rate": 0.0765,
        "max_credit": 632.0,
        "phase_in_end": 8260.0,
        "phase_out_start_single": 10330.0,
        "phase_out_start_married": 17580.0,
        "phase_out_rate": 0.0765,
        "income_limit_single": 18591.0,
        "income_limit_married": 25511.0,
    },
    1: {
        "phase_in_rate": 0.34,
        "max_credit": 4213.0,
        "phase_in_end": 12390.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.1598,
        "income_limit_single": 49084.0,
        "income_limit_married": 56004.0,
    },
    2: {
        "phase_in_rate": 0.40,
        "max_credit": 6960.0,
        "phase_in_end": 17400.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.2106,
        "income_limit_single": 55768.0,
        "income_limit_married": 62688.0,
    },
    3: {
        "phase_in_rate": 0.45,
        "max_credit": 7830.0,
        "phase_in_end": 17400.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.2106,
        "income_limit_single": 59899.0,
        "income_limit_married": 66819.0,
    },
}


CREDIT_RECIPIENT_COUNTS = {
    "ctc_filers": 36.0,
    "ctc_children": 48.0,
    "eitc_filers": 31.0,
    "eitc_with_children": 22.0,
    "eitc_childless": 9.0,
}


BASELINE_CREDIT_COSTS = {
    "ctc_total": 120.0,
    "ctc_refundable": 32.0,
    "eitc_total": 70.0,
}


@dataclass
class TaxCreditPolicy(TaxPolicy):
    """
    Tax credit policy with phase-in/phase-out modeling.
    """

    credit_type: CreditType = CreditType.OTHER
    is_refundable: bool = False
    is_partially_refundable: bool = False
    max_credit_per_unit: float = 0.0
    credit_change_per_unit: float = 0.0
    units_affected_millions: float = 0.0
    has_phase_in: bool = False
    phase_in_rate: float = 0.0
    phase_in_threshold: float = 0.0
    phase_in_end: float = 0.0
    has_phase_out: bool = True
    phase_out_threshold_single: float = 0.0
    phase_out_threshold_married: float = 0.0
    phase_out_rate: float = 0.0
    refundable_max: float = 0.0
    refund_rate: float = 0.0
    refund_threshold: float = 0.0
    make_fully_refundable: bool = False
    remove_phase_out: bool = False
    expand_qualifying_age: int | None = None
    include_childless_adults: bool = False
    labor_supply_elasticity: float = 0.1
    participation_rate: float = 0.85
    take_up_rate_change: float = 0.0
    #: ARP-style two-tier CTC: the per-child amount that keeps the high
    #: phase-out thresholds while the rest phases down from the low ones.
    #: ``None`` means a single-tier credit, which is current law.
    protected_credit_per_unit: float | None = None
    #: Per-child amount for children under 6, when it differs (ARP: $3,600
    #: against $3,000). ``None`` means one amount for every qualifying child.
    max_credit_under_6: float | None = None
    #: Lower age bound for the childless EITC when ``include_childless_adults``
    #: is set. The ARP moved it from 25 to 19.
    childless_min_age: int = 19
    #: Upper age bound (exclusive). The ARP removed it entirely, which is what
    #: a very large number expresses.
    childless_max_age: int = 200
    #: Per-*person* credit amount for a recovery-rebate-shaped policy (filer,
    #: spouse and every dependent), as against the per-child credits above.
    #: ``None`` for everything that is not one.
    credit_per_person: float | None = None
    #: Income at which a per-person rebate reaches zero. The ARP's third
    #: payment phased out completely $5,000 (single) / $10,000 (joint) above
    #: its start, which is a band rather than a rate.
    phase_out_end_single: float = 0.0
    phase_out_end_married: float = 0.0
    #: ``reported`` or ``derived`` — see the module docstring.
    mode: str = CREDIT_APP_MODE

    def __post_init__(self):
        """Set default policy type for credits."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_CREDIT
        if self.mode not in CREDIT_MODES:
            raise ValueError(f"mode must be one of {CREDIT_MODES}, got {self.mode!r}")
        super().__post_init__()

    # ------------------------------------------------------------------
    # Policy levers, as parameter schedules
    # ------------------------------------------------------------------

    def effective_take_up_rate(self) -> float:
        """Take-up multiplier on the derived per-unit score.

        Only the *change* in take-up, not its level. The identity path applies
        ``participation_rate`` as a level because it counts a statutory
        population and must discount it to claimants; the per-unit path counts
        tax units on a survey file whose own coverage runs the other way — the
        bundled CPS build covers 119% of SOI returns but 81% of SOI AGI, and
        carries no self-employment earnings for the EITC — so applying a level
        haircut on top would discount twice. The two errors are stated rather
        than netted: neither is modelled, and both are in the lane file.

        ``take_up_rate_change`` is an additive shift a reform itself buys — an
        outreach provision, or the simplification an expansion brings with it.
        It was a declared field no code path read. Clipped at 0: take-up cannot
        fall below none of the eligible population.
        """
        return float(max(0.0, 1.0 + self.take_up_rate_change))

    def _ctc_schedules(self):
        """Counterfactual and reform CTC schedules.

        The counterfactual is a **function of the year**, not a constant: IRC
        sec. 24's $2,000 credit reverts to $1,000 after 2025 under P.L. 115-97
        sec. 11022(b), so a ten-year window opening in 2025 is scored against
        current law for one year and the pre-TCJA regime for nine. Scoring a
        permanent credit against $2,000 throughout understates it by most of
        the difference between the two regimes, which is the largest single
        term in a permanent-CTC score.

        Everything else is read off the policy's own fields, including the
        levers that had no reader — ``expand_qualifying_age``,
        ``make_fully_refundable`` and ``remove_phase_out``.
        """
        from .credits_microdata import (
            CreditSchedule,
            current_law_ctc_schedule,
            pre_tcja_ctc_schedule,
        )

        def baseline_for_year(year: int):
            return (
                pre_tcja_ctc_schedule()
                if year >= CTC_SUNSET_YEAR
                else current_law_ctc_schedule()
            )

        credit = self.max_credit_per_unit or CTC_CURRENT_LAW["credit_per_child"]
        params: dict[str, float | bool | int] = {
            "ctc_amount": credit,
            "ctc_amount_under_6": self.max_credit_under_6 or credit,
            "ctc_qualifying_age": int(
                self.expand_qualifying_age or CTC_CURRENT_LAW["qualifying_age"]
            ),
            "ctc_protected_amount": (
                credit if self.protected_credit_per_unit is None
                else self.protected_credit_per_unit
            ),
            "ctc_fully_refundable": bool(
                self.is_refundable or self.make_fully_refundable
            ),
            "actc_max_per_child": self.refundable_max or CTC_CURRENT_LAW["refundable_max"],
            "actc_earned_threshold": (
                self.refund_threshold or CTC_CURRENT_LAW["refund_threshold"]
            ),
            "actc_phasein_rate": self.refund_rate or CTC_CURRENT_LAW["refund_rate"],
        }

        high_single = (
            self.phase_out_threshold_single or CTC_CURRENT_LAW["phase_out_start_single"]
        )
        high_married = (
            self.phase_out_threshold_married
            or CTC_CURRENT_LAW["phase_out_start_married"]
        )
        if self.remove_phase_out or not self.has_phase_out:
            # No phase-out at all: push both tiers above every observed AGI.
            params["ctc_phaseout_start_single"] = 1e12
            params["ctc_phaseout_start_married"] = 1e12
            params["ctc_phaseout_start_low_single"] = 1e12
            params["ctc_phaseout_start_low_married"] = 1e12
        elif self.protected_credit_per_unit is None:
            params["ctc_phaseout_start_single"] = high_single
            params["ctc_phaseout_start_married"] = high_married
            params["ctc_phaseout_start_low_single"] = high_single
            params["ctc_phaseout_start_low_married"] = high_married
        else:
            # Two tiers: the protected amount keeps current law's high
            # thresholds, the increment phases from the policy's own.
            params["ctc_phaseout_start_single"] = CTC_CURRENT_LAW[
                "phase_out_start_single"
            ]
            params["ctc_phaseout_start_married"] = CTC_CURRENT_LAW[
                "phase_out_start_married"
            ]
            params["ctc_phaseout_start_low_single"] = high_single
            params["ctc_phaseout_start_low_married"] = high_married

        return baseline_for_year, CreditSchedule(params=params)

    def _eitc_schedules(self):
        """Counterfactual and reform EITC schedules, or ``None``.

        Only the childless schedule moves. That is not a simplification for
        its own sake: the benchmark this exists for is a *childless* expansion,
        and the bridge's old single multiplier could not express one — it
        scaled all four child counts at once.
        """
        from .credits_microdata import CreditSchedule, current_law_eitc_schedule

        def baseline_for_year(year: int):
            # The EITC has no sunset: its schedule is permanent and indexed.
            del year
            return current_law_eitc_schedule()

        childless = EITC_CURRENT_LAW[0]
        params: dict[str, float | bool | int] = {
            "eitc_childless_max_credit": (
                self.max_credit_per_unit or childless["max_credit"]
            ),
            "eitc_childless_phasein_rate": (
                self.phase_in_rate or childless["phase_in_rate"]
            ),
            "eitc_childless_phaseout_rate": (
                self.phase_out_rate or childless["phase_out_rate"]
            ),
            "eitc_childless_phaseout_start_single": (
                self.phase_out_threshold_single or childless["phase_out_start_single"]
            ),
            "eitc_childless_phaseout_start_married": (
                self.phase_out_threshold_married or childless["phase_out_start_married"]
            ),
        }
        if self.include_childless_adults:
            params["eitc_childless_min_age"] = self.childless_min_age
            params["eitc_childless_max_age"] = self.childless_max_age
        else:
            params["eitc_childless_min_age"] = 25
            params["eitc_childless_max_age"] = 65
        return baseline_for_year, CreditSchedule(params=params)

    def _rebate_schedules(self):
        """Counterfactual and reform schedules for a per-person rebate.

        The counterfactual is no rebate, which is not a legal fiction: a
        recovery rebate is a new credit rather than a change to a standing
        one, so its whole amount is the reform.
        """
        from .credits_microdata import CreditSchedule, no_rebate_schedule

        def baseline_for_year(year: int):
            del year
            return no_rebate_schedule()

        params: dict[str, float | bool | int] = {
            "rebate_per_person": float(self.credit_per_person or 0.0),
            "rebate_phaseout_start_single": (
                self.phase_out_threshold_single or 75_000.0
            ),
            "rebate_phaseout_start_married": (
                self.phase_out_threshold_married or 150_000.0
            ),
        }
        params["rebate_phaseout_end_single"] = (
            self.phase_out_end_single
            or float(params["rebate_phaseout_start_single"]) + 5_000.0
        )
        params["rebate_phaseout_end_married"] = (
            self.phase_out_end_married
            or float(params["rebate_phaseout_start_married"]) + 10_000.0
        )
        return baseline_for_year, CreditSchedule(params=params)

    def credit_schedules(self):
        """``(counterfactual_for_year, reform)``, or ``None`` if inexpressible.

        ``None`` for a credit with no statutory schedule for the per-unit path
        to move — an ``OTHER``-type policy that is neither a CTC or EITC reform
        nor a per-person rebate.
        """
        if self.credit_type == CreditType.CHILD_TAX_CREDIT:
            return self._ctc_schedules()
        if self.credit_type == CreditType.EARNED_INCOME_CREDIT:
            return self._eitc_schedules()
        if self.credit_per_person:
            return self._rebate_schedules()
        return None

    def derived_window_average(self) -> float | None:
        """Window-average annual revenue effect from the CPS microdata.

        ``None`` when the policy has no expressible schedule. Never reads
        ``annual_revenue_change_billions``, which is what makes it usable as a
        held-out derivation.
        """
        from .credits_microdata import derived_annual_for_policy

        return derived_annual_for_policy(self)

    def calculate_credit_for_income(
        self,
        earned_income: float,
        agi: float,
        filing_status: Literal["single", "married"] = "single",
        num_children: int = 0,
    ) -> dict:
        """
        Calculate credit amount for a given income level.
        """
        gross_credit = self.max_credit_per_unit * max(1, num_children)

        if self.has_phase_in:
            if earned_income < self.phase_in_threshold:
                gross_credit = 0.0
            elif earned_income < self.phase_in_end:
                phase_in_income = earned_income - self.phase_in_threshold
                gross_credit = min(gross_credit, phase_in_income * self.phase_in_rate)

        net_credit = gross_credit
        if self.has_phase_out and not self.remove_phase_out:
            threshold = (
                self.phase_out_threshold_married
                if filing_status == "married"
                else self.phase_out_threshold_single
            )
            if agi > threshold:
                phase_out_amount = (agi - threshold) * self.phase_out_rate
                net_credit = max(0, gross_credit - phase_out_amount)

        if self.is_refundable or self.make_fully_refundable:
            refundable = net_credit
            non_refundable = 0.0
        elif self.is_partially_refundable:
            refundable_earnings = max(0, earned_income - self.refund_threshold)
            potential_refund = refundable_earnings * self.refund_rate
            refundable = min(
                self.refundable_max * max(1, num_children),
                potential_refund,
                net_credit,
            )
            non_refundable = net_credit - refundable
        else:
            refundable = 0.0
            non_refundable = net_credit

        return {
            "gross_credit": gross_credit,
            "net_credit": net_credit,
            "refundable_portion": refundable,
            "non_refundable_portion": non_refundable,
        }

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of a credit policy change.

        In ``derived`` mode the answer is the per-unit CPS computation and the
        fitted annual is not read at all. In ``reported`` mode the fitted
        annual wins where it exists, then the per-unit cost identity, and the
        CPS path is the fallback for the policies the identity cannot express
        — a pure refundability or phase-out change, which used to return the
        flat -50.0 / -5.0 constants no code path could reach with a real
        number behind them.
        """
        del baseline_revenue, use_real_data

        if self.mode == CREDIT_MODE_DERIVED:
            derived = self.derived_window_average()
            if derived is not None:
                return derived

        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if self.credit_change_per_unit != 0 and self.units_affected_millions > 0:
            static_cost = (
                self.credit_change_per_unit
                * self.units_affected_millions
                * self.participation_rate
                * 1e6
                / 1e9
            )
            return -static_cost

        if self.make_fully_refundable or self.remove_phase_out:
            derived = self.derived_window_average()
            if derived is not None:
                return derived

        return 0.0

    def uses_window_average_annual(self) -> bool:
        """Whether this policy's annual is already a window average.

        True for a fitted ``annual_revenue_change_billions`` and true in
        ``derived`` mode, where the CPS path averages over the window itself.
        Growing either again would double-count the window's own growth — the
        residual ``docs/VALIDATION_NOTES.md`` §2 records for the Biden CTC.
        """
        return (
            self.annual_revenue_change_billions is not None
            or self.mode == CREDIT_MODE_DERIVED
        )

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to credit changes.

        When ``annual_revenue_change_billions`` is an explicit window-average
        calibration to an official score, skip additional behavioral haircuts
        so we do not erode a figure that already embeds official assumptions.
        """
        if self.annual_revenue_change_billions is not None:
            return 0.0

        if self.credit_type == CreditType.EARNED_INCOME_CREDIT:
            return static_effect * 0.12

        if self.credit_type == CreditType.CHILD_TAX_CREDIT:
            return static_effect * 0.05

        return abs(static_effect) * self.labor_supply_elasticity * 0.3


CREDIT_VALIDATION_SCENARIOS = {
    "biden_ctc_2021": {
        "description": "Biden 2021 ARP-style CTC (permanent)",
        "policy_factory": "create_biden_ctc_2021",
        "expected_10yr": -1600.0,
        "source": "CBO/JCT 2021",
        "notes": "Actual ARP was 1-year, cost ~$110B",
    },
    "ctc_extension": {
        "description": "Extend current CTC beyond 2025",
        "policy_factory": "create_ctc_permanent_extension",
        "expected_10yr": -600.0,
        "source": "CBO 2024",
        "notes": "Part of TCJA extension cost",
    },
    "biden_eitc_childless": {
        "description": "Biden childless EITC expansion",
        "policy_factory": "create_biden_eitc_childless",
        "expected_10yr": -178.0,
        "source": "Treasury Green Book 2024",
        "notes": "Expand age range and nearly triple credit",
    },
}


def estimate_credit_cost(policy: TaxCreditPolicy) -> dict:
    """Estimate total cost of a credit policy over 10 years."""
    annual_static = -policy.estimate_static_revenue_effect(0)
    behavioral = -policy.estimate_behavioral_offset(-annual_static)

    years = np.arange(10)
    # Window-average annuals (a fitted annual, or the derived CPS path) stay
    # flat; bottom-up unit×credit estimates still grow with nominal income.
    if policy.uses_window_average_annual():
        annual_costs = np.full(10, annual_static)
        behavioral_offsets = np.full(10, behavioral)
    else:
        annual_costs = annual_static * (1.03**years)
        behavioral_offsets = behavioral * (1.03**years)

    ten_year_static = np.sum(annual_costs)
    ten_year_behavioral = np.sum(behavioral_offsets)

    return {
        "annual_cost": annual_static,
        "ten_year_cost": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_cost": ten_year_static - ten_year_behavioral,
    }
