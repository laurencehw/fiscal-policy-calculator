"""
Core tax expenditure types, data tables, and helper functions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np

from .policies import PolicyType, TaxPolicy


class TaxExpenditureType(Enum):
    """Categories of tax expenditures."""

    EMPLOYER_HEALTH = "employer_health"
    RETIREMENT_CONTRIBUTIONS = "retirement_contrib"
    RETIREMENT_EARNINGS = "retirement_earnings"
    MORTGAGE_INTEREST = "mortgage_interest"
    SALT = "salt"
    CHARITABLE = "charitable"
    MEDICAL_EXPENSES = "medical"
    CAPITAL_GAINS = "capital_gains"
    DIVIDENDS = "dividends"
    CHILD_TAX_CREDIT = "ctc"
    EITC = "eitc"
    STEP_UP_BASIS = "step_up"
    LIKE_KIND_EXCHANGE = "like_kind"
    PASS_THROUGH_DEDUCTION = "pass_through"


JCT_TAX_EXPENDITURES = {
    "employer_health": {
        "annual_cost": 250.0,
        "affected_millions": 155.0,
        "avg_benefit": 1_600,
        "growth_rate": 0.04,
    },
    "retirement_401k": {
        "annual_cost": 251.0,
        "affected_millions": 70.0,
        "avg_benefit": 3_600,
        "growth_rate": 0.03,
    },
    "retirement_db": {
        "annual_cost": 122.0,
        "affected_millions": 35.0,
        "avg_benefit": 3_500,
        "growth_rate": 0.02,
    },
    "retirement_ira": {
        "annual_cost": 27.0,
        "affected_millions": 50.0,
        "avg_benefit": 540,
        "growth_rate": 0.03,
    },
    "mortgage_interest": {
        "annual_cost": 25.0,
        "annual_cost_no_limit": 100.0,
        "affected_millions": 20.0,
        "avg_benefit": 1_250,
        "growth_rate": 0.03,
    },
    "salt": {
        "annual_cost": 25.0,
        "annual_cost_no_cap": 120.0,
        "affected_millions": 15.0,
        "avg_benefit": 1_700,
        "growth_rate": 0.03,
    },
    "charitable": {
        "annual_cost": 70.0,
        "affected_millions": 25.0,
        "avg_benefit": 2_800,
        "growth_rate": 0.03,
    },
    "capital_gains_dividends": {
        "annual_cost": 225.0,
        "affected_millions": 25.0,
        "avg_benefit": 9_000,
        "growth_rate": 0.04,
    },
    "step_up_basis": {
        "annual_cost": 50.0,
        "affected_millions": 2.5,
        "avg_benefit": 20_000,
        "growth_rate": 0.04,
    },
    "like_kind_exchange": {
        "annual_cost": 7.0,
        "affected_millions": 0.5,
        "avg_benefit": 14_000,
        "growth_rate": 0.03,
    },
}


REFORM_ESTIMATES = {
    "cap_employer_exclusion_50k": {
        "revenue_10yr": 450.0,
        "source": "CBO",
        "notes": "Cap on excludable employer health contributions",
    },
    "eliminate_employer_exclusion": {
        "revenue_10yr": 2500.0,
        "source": "CBO estimate",
        "notes": "Would be largest base broadener but disruptive",
    },
    "cap_retirement_contrib_20k": {
        "revenue_10yr": 150.0,
        "source": "CBO",
        "notes": "Equalizes treatment across plan types",
    },
    "require_roth_high_income": {
        "revenue_10yr": 100.0,
        "source": "Biden proposal",
        "notes": "Shifts timing of revenue",
    },
    "eliminate_mortgage_deduction": {
        "revenue_10yr": 300.0,
        "source": "CBO",
        "notes": "Controversial - affects homeownership",
    },
    "cap_mortgage_500k": {
        "revenue_10yr": 30.0,
        "source": "CBO estimate",
        "notes": "Moderate reform",
    },
    "repeal_salt_cap": {
        "revenue_10yr": -1100.0,
        "source": "JCT",
        "notes": "Popular bipartisan proposal - costs money",
    },
    "eliminate_salt": {
        "revenue_10yr": 1200.0,
        "source": "JCT estimate",
        "notes": "Very controversial - affects high-tax states",
    },
    "cap_charitable_deduction": {
        "revenue_10yr": 200.0,
        "source": "Obama proposal",
        "notes": "Pease-style limit on high-income itemizers",
    },
    "eliminate_charitable_deduction": {
        "revenue_10yr": 700.0,
        "source": "Estimate",
        "notes": "Would significantly affect nonprofit sector",
    },
    "eliminate_step_up": {
        "revenue_10yr": 500.0,
        "source": "Biden proposal",
        "notes": "Tax gains at death (with $1M+ exemption)",
    },
    "eliminate_like_kind": {
        "revenue_10yr": 80.0,
        "source": "Biden proposal",
        "notes": "End 1031 exchange deferral",
    },
}


TAX_EXPENDITURE_DATA_KEYS = {
    TaxExpenditureType.EMPLOYER_HEALTH: "employer_health",
    TaxExpenditureType.RETIREMENT_CONTRIBUTIONS: "retirement_401k",
    TaxExpenditureType.MORTGAGE_INTEREST: "mortgage_interest",
    TaxExpenditureType.SALT: "salt",
    TaxExpenditureType.CHARITABLE: "charitable",
    TaxExpenditureType.CAPITAL_GAINS: "capital_gains_dividends",
    TaxExpenditureType.STEP_UP_BASIS: "step_up_basis",
    TaxExpenditureType.LIKE_KIND_EXCHANGE: "like_kind_exchange",
}


BEHAVIORAL_ELASTICITIES = {
    TaxExpenditureType.CHARITABLE: 0.4,
    TaxExpenditureType.MORTGAGE_INTEREST: 0.1,
    TaxExpenditureType.RETIREMENT_CONTRIBUTIONS: 0.3,
    TaxExpenditureType.EMPLOYER_HEALTH: 0.2,
    TaxExpenditureType.SALT: 0.05,
}


@dataclass
class TaxExpenditurePolicy(TaxPolicy):
    """
    Tax expenditure policy modeling changes to deductions, exclusions, and credits.
    """

    expenditure_type: TaxExpenditureType = field(default=TaxExpenditureType.CHARITABLE)
    action: Literal["eliminate", "cap", "phase_out", "convert", "expand"] = "cap"
    cap_amount: float | None = None
    cap_rate: float | None = None
    phase_out_start: float | None = None
    phase_out_end: float | None = None
    phase_out_rate: float = 0.03
    convert_to_credit: bool = False
    credit_rate: float = 0.15
    expand_limit: float | None = None
    behavioral_elasticity: float = 0.2
    participation_change: float = 0.0
    annual_revenue_change_billions: float | None = None

    def __post_init__(self):
        """Set policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_DEDUCTION
        super().__post_init__()

    def get_expenditure_data(self) -> dict:
        """Get baseline data for this expenditure type."""
        key = TAX_EXPENDITURE_DATA_KEYS.get(self.expenditure_type, "charitable")
        return JCT_TAX_EXPENDITURES.get(key, {})

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of tax expenditure reform.

        Returns revenue change in billions where positive values raise revenue.
        """
        del baseline_revenue, use_real_data

        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        data = self.get_expenditure_data()
        baseline_cost = data.get("annual_cost", 50.0)

        if self.action == "eliminate":
            return baseline_cost

        if self.action == "cap":
            if self.cap_amount is not None:
                avg_benefit = data.get("avg_benefit", 2000)
                if self.cap_amount >= avg_benefit:
                    share_affected = 0.1 * (avg_benefit / self.cap_amount)
                else:
                    share_affected = 0.3 + 0.4 * (1 - self.cap_amount / avg_benefit)
                return baseline_cost * share_affected

            if self.cap_rate is not None:
                return baseline_cost * 0.15

        if self.action == "phase_out":
            return baseline_cost * 0.20

        if self.action == "convert":
            return baseline_cost * 0.10

        if self.action == "expand":
            if self.expenditure_type == TaxExpenditureType.SALT:
                no_cap_cost = data.get("annual_cost_no_cap", 120.0)
                current_cost = data.get("annual_cost", 25.0)
                return -(no_cap_cost - current_cost)
            return -baseline_cost * 0.20

        return 0.0

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to tax expenditure changes.
        """
        elasticity = BEHAVIORAL_ELASTICITIES.get(
            self.expenditure_type,
            self.behavioral_elasticity,
        )

        offset = abs(static_effect) * elasticity
        if static_effect > 0:
            return -offset
        return offset


TAX_EXPENDITURE_VALIDATION_SCENARIOS = {
    "cap_employer_health": {
        "description": "Cap employer health exclusion at $50K",
        "policy_factory": "create_cap_employer_health_exclusion",
        "expected_10yr": -450.0,
        "source": "CBO",
        "notes": "Third-largest tax expenditure",
    },
    "eliminate_mortgage": {
        "description": "Eliminate mortgage interest deduction",
        "policy_factory": "create_eliminate_mortgage_deduction",
        "expected_10yr": -300.0,
        "source": "CBO",
        "notes": "Controversial housing policy",
    },
    "repeal_salt_cap": {
        "description": "Repeal SALT $10K cap",
        "policy_factory": "create_repeal_salt_cap",
        "expected_10yr": 1100.0,
        "source": "JCT",
        "notes": "Bipartisan proposal, benefits high-tax states",
    },
    "eliminate_salt": {
        "description": "Eliminate SALT deduction entirely",
        "policy_factory": "create_eliminate_salt_deduction",
        "expected_10yr": -1200.0,
        "source": "JCT estimate",
        "notes": "Very controversial",
    },
    "cap_charitable": {
        "description": "Cap charitable deduction at 28%",
        "policy_factory": "create_cap_charitable_deduction",
        "expected_10yr": -200.0,
        "source": "Obama/Biden proposal",
        "notes": "Pease-style limitation",
    },
    "eliminate_step_up": {
        "description": "Eliminate step-up in basis",
        "policy_factory": "create_eliminate_step_up_basis",
        "expected_10yr": -500.0,
        "source": "Biden proposal",
        "notes": "Tax gains at death with $1M exemption",
    },
}


def estimate_expenditure_revenue(policy: TaxExpenditurePolicy) -> dict:
    """Estimate total revenue effect of a tax expenditure policy."""
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)
    growth_rate = policy.get_expenditure_data().get("growth_rate", 0.03)

    years = np.arange(10)
    annual_effects = annual_static * ((1 + growth_rate) ** years)
    behavioral_effects = behavioral * ((1 + growth_rate) ** years)

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }


def get_all_expenditure_estimates() -> dict:
    """Get summary of all tax expenditure baseline costs."""
    return {
        "Employer Health Insurance": JCT_TAX_EXPENDITURES["employer_health"]["annual_cost"],
        "401(k) and DC Plans": JCT_TAX_EXPENDITURES["retirement_401k"]["annual_cost"],
        "Defined Benefit Plans": JCT_TAX_EXPENDITURES["retirement_db"]["annual_cost"],
        "IRAs": JCT_TAX_EXPENDITURES["retirement_ira"]["annual_cost"],
        "Capital Gains/Dividends": JCT_TAX_EXPENDITURES["capital_gains_dividends"]["annual_cost"],
        "SALT (with $10K cap)": JCT_TAX_EXPENDITURES["salt"]["annual_cost"],
        "SALT (no cap)": JCT_TAX_EXPENDITURES["salt"]["annual_cost_no_cap"],
        "Mortgage Interest": JCT_TAX_EXPENDITURES["mortgage_interest"]["annual_cost"],
        "Charitable Contributions": JCT_TAX_EXPENDITURES["charitable"]["annual_cost"],
        "Step-Up Basis": JCT_TAX_EXPENDITURES["step_up_basis"]["annual_cost"],
        "Like-Kind Exchange": JCT_TAX_EXPENDITURES["like_kind_exchange"]["annual_cost"],
    }
