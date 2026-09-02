"""
Core tax expenditure types, data tables, and helper functions.

Units
-----
Every reform parameter in this module is a number with a unit, and the two
defects `planning/MODELING_IMPROVEMENT.md` section 3 L6 names were both unit
errors rather than calibration errors:

* a $50,000 cap on excludable health **premiums** was compared against
  ``avg_benefit = 1_600``, an average **tax benefit**, concluding that 0.32%
  of the base was affected;
* eliminating the SALT deduction was priced off ``annual_cost = 25.0``, the
  expenditure **with the $10,000 cap in force**, while the uncapped level sat
  unread in the same record.

:class:`CapUnit` now makes a cap say what it measures, and each expenditure
carries a distribution of that quantity (``tax_expenditure_distributions``) so
the module can answer "how much sits above the cap" instead of approximating
it. A statutory limitation is a declared object with its statute and its
expiry, not a spare field, so the ``eliminate`` and ``expand`` rules read the
level in force rather than hard-coding one.

Scoring modes
-------------
Every policy in this module carries a ``mode``. ``reported`` scores the fitted
``annual_revenue_change_billions``; ``derived`` ignores it and scores from the
base table plus the distributions. See the SCORING MODES block below for which
path each caller takes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import numpy as np

from .policies import PolicyType, TaxPolicy
from .tax_expenditure_distributions import (
    load_deduction_distribution,
    load_premium_distribution,
)


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


class CapUnit(Enum):
    """
    What a cap parameter measures.

    ``BASE_DOLLARS``
        Dollars of the deducted or excluded quantity, per return or per
        policy: the premium a $50,000 exclusion cap caps, the deduction a
        $500,000 mortgage cap caps. Every published cap design uses this unit.
    ``BENEFIT_RATE``
        A ceiling on the rate at which the item may be valued -- the
        Obama/Biden 28% limitation, CBO Option 49's 15% alternative.
    ``BENEFIT_DOLLARS``
        Dollars of *tax benefit* per return. Kept because a design could be
        written this way, and because naming it is what makes the old
        premiums-against-benefits comparison impossible to reintroduce by
        accident: it now has to be asked for.
    """

    BASE_DOLLARS = "base_dollars"
    BENEFIT_RATE = "benefit_rate"
    BENEFIT_DOLLARS = "benefit_dollars"


# =============================================================================
# SCORING MODES
# =============================================================================
# Owner Decision 1 (planning/MODELING_IMPROVEMENT.md section 6.1, accepted
# 2026-09-01): a calibrated module keeps its fitted annuals as a `reported`
# mode alongside a `derived` mode that scores from structure instead. L5
# implemented the pattern in `amt.py`; this is the same shape.

#: Score from the fitted ``annual_revenue_change_billions`` constant.
EXPENDITURE_MODE_REPORTED = "reported"

#: Ignore the fitted constant and score from ``JCT_TAX_EXPENDITURES`` plus the
#: distributions in ``tax_expenditure_distributions``.
EXPENDITURE_MODE_DERIVED = "derived"

EXPENDITURE_MODES = (EXPENDITURE_MODE_REPORTED, EXPENDITURE_MODE_DERIVED)

#: What the shipped app scores. Decision 1 keeps a module on ``reported``
#: until its derived error beats its fitted error, and here it does not:
#:
#: ===========================  ===========  ==========  =========  ==========
#: Benchmark                    Target       Reported    Derived    Winner
#: ===========================  ===========  ==========  =========  ==========
#: ``cap_employer_health``      -$450B       +0.1%       +93.2%     reported
#: ``eliminate_mortgage``       -$300B       -10.1%      -5.1%      derived
#: ``repeal_salt_cap``          $1,100B      +5.1%       +4.0%      derived
#: ``eliminate_salt``           -$1,200B     -5.0%       -20.4%     reported
#: ``cap_charitable``           -$200B       -0.3%       +13.1%     reported
#: ``eliminate_step_up``        -$500B       -4.7%       -20.1%     reported
#: ===========================  ===========  ==========  =========  ==========
#:
#: Mean 4.2% reported against 26.0% derived, so every preset stays on
#: ``reported`` and no shipped number changes. Read those rows with the same
#: caution as AMT's: five of the six targets are reproduced by a constant
#: fitted to them, so their near-zero errors measure bookkeeping. On the one
#: benchmark whose published line item the repository actually carries --
#: ``eliminate_salt``, $1,621.0B in CBO pub. 60557 Option 49 against the
#: -$1,200B this scorecard uses -- derived is the closer of the two, 10.9%
#: below the document against reported's 22.3%.
EXPENDITURE_APP_MODE = EXPENDITURE_MODE_REPORTED

#: What the *held-out* validation path scores. ``validation/loo.py``'s
#: ``run_tax_expenditure_loo`` builds every case in this mode, so the
#: leave-one-out number measures the base table plus the reform rules rather
#: than a scalar re-derivation of the fitted constant.
EXPENDITURE_HELD_OUT_MODE = EXPENDITURE_MODE_DERIVED


# ``annual_cost`` is the expenditure in **tax dollars** -- the revenue the
# provision costs, not the amount excluded or deducted. ``avg_benefit`` is the
# same quantity per participant. Neither is a cap-able quantity, which is what
# the employer-health bug turned on; ``base_distribution`` names the
# distribution of the quantity a dollar cap actually caps.
#
# ``limitation``, where present, is a statutory limit that already applies to
# the expenditure, with the statute that created it and the year through which
# it binds. ``annual_cost`` is then the expenditure *with* the limit in force
# and ``unlimited_cost_key`` points at the level without it.
JCT_TAX_EXPENDITURES = {
    "employer_health": {
        "annual_cost": 250.0,
        "affected_millions": 155.0,
        "avg_benefit": 1_600,
        "growth_rate": 0.04,
        "base_distribution": {"kind": "premium"},
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
        # Deliberately *not* wired into any rule. Nothing in the repository
        # says which limitation this is the "no limit" level of. The natural
        # candidate, TCJA's $750,000 acquisition-debt cap (IRC 163(h)(3)(F)),
        # is worth single-digit billions a year, not $75B, so this looks like
        # a pre-TCJA level reflecting the smaller standard deduction rather
        # than a debt-limit counterfactual. A rule that read it would move
        # `eliminate_mortgage` from -5.1% to about +244% on an unsourced
        # constant, so it stays unread and goes to the provenance lane. Give
        # it a `limitation` block with a statute and an expiry and it becomes
        # live automatically, which is the point of declaring limitations.
        "annual_cost_no_limit": 100.0,
        "affected_millions": 20.0,
        "avg_benefit": 1_250,
        "growth_rate": 0.03,
        "base_distribution": {"kind": "deduction", "column": "mortgage_interest"},
    },
    "salt": {
        "annual_cost": 25.0,
        "annual_cost_no_cap": 120.0,
        "affected_millions": 15.0,
        "avg_benefit": 1_700,
        "growth_rate": 0.03,
        "base_distribution": {"kind": "deduction", "column": "salt_limited"},
        "unlimited_base_distribution": {"kind": "deduction", "column": "salt"},
        "limitation": {
            "name": "$10,000 cap on the state-and-local-tax deduction",
            "statute": "IRC 164(b)(6), added by P.L. 115-97 sec. 11042",
            "unit": CapUnit.BASE_DOLLARS,
            "amount": 10_000.0,
            "expires_after": 2025,
            "unlimited_cost_key": "annual_cost_no_cap",
            "source": (
                "CBO, Options for Reducing the Deficit: 2025 to 2034 "
                "(pub. 60557, Dec 2024), Option 49, report p. 59: 'Beginning "
                "in 2026, deductions for state and local taxes will not be "
                "limited.'"
            ),
        },
    },
    "charitable": {
        "annual_cost": 70.0,
        "affected_millions": 25.0,
        "avg_benefit": 2_800,
        "growth_rate": 0.03,
        "base_distribution": {"kind": "deduction", "column": "charitable"},
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


class ExpenditureDistributionMissing(LookupError):
    """
    A cap was asked for on an expenditure with no distribution of its base.

    Raised rather than silently approximated: the approximation this replaced
    is exactly the ``cap_employer_health`` bug, and a rule that cannot see the
    distribution of the quantity it caps has no business returning a number.
    ``validation/loo.py`` catches this and reports the case as not derivable
    with a reason.
    """


@dataclass
class TaxExpenditurePolicy(TaxPolicy):
    """
    Tax expenditure policy modeling changes to deductions, exclusions, and credits.

    Scoring modes
    -------------
    ``mode="reported"`` returns ``annual_revenue_change_billions`` when it is
    set -- the fitted constant, and what every shipped preset scores.
    ``mode="derived"`` ignores it and runs the reform rule against
    ``JCT_TAX_EXPENDITURES`` and the distributions. See the SCORING MODES block
    at the top of this module.

    Cap units
    ---------
    ``cap_amount`` is read in ``cap_unit``, which defaults to
    :attr:`CapUnit.BASE_DOLLARS`: dollars of the deducted or excluded quantity,
    per return or per policy. ``cap_rate`` is always a
    :attr:`CapUnit.BENEFIT_RATE` ceiling.
    """

    expenditure_type: TaxExpenditureType = field(default=TaxExpenditureType.CHARITABLE)
    action: Literal["eliminate", "cap", "phase_out", "convert", "expand"] = "cap"
    cap_amount: float | None = None
    cap_unit: CapUnit = CapUnit.BASE_DOLLARS
    caps_by_coverage_tier: dict[str, float] | None = None
    cap_rate: float | None = None
    mode: str = EXPENDITURE_APP_MODE
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
        if self.mode not in EXPENDITURE_MODES:
            raise ValueError(f"mode must be one of {EXPENDITURE_MODES}, got {self.mode!r}")
        super().__post_init__()

    def get_expenditure_data(self) -> dict:
        """Get baseline data for this expenditure type."""
        key = TAX_EXPENDITURE_DATA_KEYS.get(self.expenditure_type, "charitable")
        return JCT_TAX_EXPENDITURES.get(key, {})

    # -- levels and limitations ------------------------------------------

    def limitation_years_in_window(self, data: dict) -> int:
        """
        How many years of this policy's window a declared limitation binds.

        A limitation is a separate statutory provision with its own expiry
        (SALT's $10,000 cap expires after 2025 under IRC 164(b)(6)). Reading
        it is what lets ``eliminate`` price the deduction that will actually
        be claimed instead of the one claimed under a limitation that has
        lapsed -- the ``eliminate_salt`` half of this lane.
        """
        limitation = data.get("limitation")
        if not limitation:
            return self.duration_years
        expires_after = limitation.get("expires_after")
        if expires_after is None:
            return self.duration_years
        capped = expires_after - self.start_year + 1
        return max(0, min(self.duration_years, capped))

    def benefit_level_billions(self, data: dict) -> float:
        """
        The expenditure's annual value under the baseline in force, in $B.

        With no declared limitation this is ``annual_cost``. With one, it is
        the window-average of the limited and unlimited levels, weighted by
        how many years of the window the limitation binds.
        """
        limited = data.get("annual_cost", 50.0)
        limitation = data.get("limitation")
        if not limitation:
            return limited
        unlimited = data.get(limitation["unlimited_cost_key"], limited)
        capped_years = self.limitation_years_in_window(data)
        share_capped = capped_years / self.duration_years
        return limited * share_capped + unlimited * (1.0 - share_capped)

    # -- distributions ----------------------------------------------------

    def _base_distribution_spec(self, data: dict) -> dict | None:
        """
        Which distribution describes the base a cap would apply to.

        When a limitation has lapsed over the whole window, the base is the
        unlimited one, so SALT's uncapped deduction distribution replaces its
        capped one.
        """
        if data.get("limitation") and self.limitation_years_in_window(data) == 0:
            unlimited = data.get("unlimited_base_distribution")
            if unlimited is not None:
                return unlimited
        return data.get("base_distribution")

    def _share_of_benefit_above_cap(self, data: dict) -> float:
        """Share of the expenditure's value denied by this policy's cap."""
        spec = self._base_distribution_spec(data)
        if spec is None:
            raise ExpenditureDistributionMissing(
                f"no base distribution for {self.expenditure_type.value!r}; a "
                f"cap cannot be applied to a quantity the module cannot see"
            )
        if self.cap_rate is not None:
            if spec["kind"] != "deduction":
                raise ExpenditureDistributionMissing(
                    f"a rate ceiling needs a deduction distribution, but "
                    f"{self.expenditure_type.value!r} carries a "
                    f"{spec['kind']!r} distribution"
                )
            return load_deduction_distribution(spec["column"]).benefit_share_above_rate(
                self.cap_rate
            )
        if self.cap_unit is CapUnit.BENEFIT_DOLLARS:
            # The old rule, now reachable only by asking for it by name.
            avg_benefit = data.get("avg_benefit", 2000)
            if self.cap_amount >= avg_benefit:
                return 0.1 * (avg_benefit / self.cap_amount)
            return 0.3 + 0.4 * (1 - self.cap_amount / avg_benefit)
        if spec["kind"] == "premium":
            return load_premium_distribution().base_share_above(
                self.cap_amount,
                year=self.start_year,
                growth_rate=data.get("growth_rate", 0.03),
                caps_by_tier=self.caps_by_coverage_tier,
            )
        return load_deduction_distribution(spec["column"]).benefit_share_above_amount(
            self.cap_amount
        )

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of tax expenditure reform.

        Returns revenue change in billions where positive values raise revenue.

        In ``reported`` mode this is the fitted annual constant when one is
        set. In ``derived`` mode the constant is ignored and the answer is the
        expenditure's level under the baseline in force, times the share of it
        the reform denies -- where "the share" comes from the distribution of
        the quantity the reform's parameter is denominated in.

        Raises :class:`ExpenditureDistributionMissing` for a cap on an
        expenditure whose base has no transcribed distribution.
        """
        del baseline_revenue, use_real_data

        if (
            self.mode == EXPENDITURE_MODE_REPORTED
            and self.annual_revenue_change_billions is not None
        ):
            return self.annual_revenue_change_billions

        data = self.get_expenditure_data()
        baseline_cost = data.get("annual_cost", 50.0)

        if self.action == "eliminate":
            # Repealing the provision raises what the provision costs under
            # the baseline in force over this policy's window, which is not
            # `annual_cost` when a declared limitation has lapsed.
            return self.benefit_level_billions(data)

        if self.action == "cap" and (self.cap_amount is not None or self.cap_rate is not None):
            return self.benefit_level_billions(data) * self._share_of_benefit_above_cap(data)

        if self.action == "phase_out":
            return baseline_cost * 0.20

        if self.action == "convert":
            return baseline_cost * 0.10

        if self.action == "expand":
            # Repealing a *limitation* is worth the limitation's own cost --
            # the difference between the two levels -- and is defined against
            # the baseline that contains it. That is deliberately not
            # year-indexed the way `eliminate` is, and the asymmetry is real:
            # `eliminate_salt` is scored by CBO on a 2026+ window where the
            # $10,000 cap has lapsed, while the $1,100B repeal figure
            # presupposes it binds. The contradiction is in the two sources,
            # not in this rule; see `planning/lanes/L6_tax_expenditures.md`.
            limitation = data.get("limitation")
            if limitation:
                unlimited = data.get(limitation["unlimited_cost_key"], baseline_cost)
                return -(unlimited - baseline_cost)
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
