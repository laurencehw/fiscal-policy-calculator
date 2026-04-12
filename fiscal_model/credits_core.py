"""
Core tax credit types, constants, and helper functions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np

from .policies import PolicyType, TaxPolicy


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

    def __post_init__(self):
        """Set default policy type for credits."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_CREDIT
        super().__post_init__()

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
        """
        del baseline_revenue, use_real_data

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

        if self.make_fully_refundable and self.credit_type == CreditType.CHILD_TAX_CREDIT:
            return -50.0

        if self.remove_phase_out and self.credit_type == CreditType.CHILD_TAX_CREDIT:
            return -5.0

        return 0.0

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to credit changes.
        """
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
