"""
Core policy parameter definitions.
"""

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from .spending_outlays import IMMEDIATE, OutlayProfile, get_outlay_profile

logger = logging.getLogger(__name__)

# Cap on the preferential-income correction. Even at the very top, some income
# is ordinary (wages, interest, non-qualified distributions); this prevents a
# pathological data point from zeroing out the base.
_MAX_PREFERENTIAL_SHARE = 0.55


def preferential_income_share(
    threshold: float,
    total_marginal_income_billions: float,
    *,
    year: int | None = None,
) -> float:
    """Share of marginal income above ``threshold`` taxed at *preferential*
    rates (long-term capital gains), and therefore unaffected by an ordinary
    income-tax rate change.

    Sourced from :class:`CapitalGainsBaseline` (Tax Foundation realizations +
    IRS-SOI-derived share-above-threshold schedule). Qualified dividends are not
    separately modeled, so this is a conservative (slightly low) estimate.
    Returns 0.0 on any data error so scoring degrades to the legacy whole-base
    behavior rather than failing.
    """
    if total_marginal_income_billions <= 0 or threshold < 0:
        return 0.0
    try:
        from fiscal_model.data.capital_gains import CapitalGainsBaseline

        cg = CapitalGainsBaseline()
        base = cg.get_baseline_above_threshold_with_rate_method(
            year=year or 2023,
            threshold=max(threshold, 1.0),
        )
        cg_above_billions = float(base["net_capital_gain_billions"])
    except Exception as exc:
        logger.warning("preferential_income_share: cap-gains data unavailable (%s)", exc)
        return 0.0

    share = cg_above_billions / total_marginal_income_billions
    return float(max(0.0, min(_MAX_PREFERENTIAL_SHARE, share)))


class PolicyType(Enum):
    """Categories of fiscal policies."""

    INCOME_TAX = "income_tax"
    CORPORATE_TAX = "corporate_tax"
    PAYROLL_TAX = "payroll_tax"
    CAPITAL_GAINS_TAX = "capital_gains_tax"
    ESTATE_TAX = "estate_tax"
    EXCISE_TAX = "excise_tax"
    TAX_CREDIT = "tax_credit"
    TAX_DEDUCTION = "tax_deduction"
    DISCRETIONARY_DEFENSE = "discretionary_defense"
    DISCRETIONARY_NONDEFENSE = "discretionary_nondefense"
    MANDATORY_SPENDING = "mandatory_spending"
    INFRASTRUCTURE = "infrastructure"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    UNEMPLOYMENT = "unemployment"
    SNAP = "snap"
    OTHER_TRANSFER = "other_transfer"


@dataclass
class Policy:
    """Base class for fiscal policy proposals."""

    name: str
    description: str
    policy_type: PolicyType
    start_year: int = 2025
    duration_years: int = 10
    phase_in_years: int = 1
    sunset: bool = False

    def __post_init__(self):
        if self.duration_years <= 0:
            raise ValueError(f"duration_years must be positive, got {self.duration_years}")
        if self.phase_in_years < 1:
            raise ValueError(f"phase_in_years must be >= 1, got {self.phase_in_years}")
        if self.start_year < 2000 or self.start_year > 2100:
            raise ValueError(f"start_year must be between 2000 and 2100, got {self.start_year}")

    def get_phase_in_factor(self, year: int) -> float:
        """Calculate the phase-in factor for a given year."""
        if year < self.start_year:
            return 0.0

        years_since_start = year - self.start_year

        if self.sunset and years_since_start >= self.duration_years:
            return 0.0

        if self.phase_in_years <= 1:
            return 1.0

        return min(1.0, (years_since_start + 1) / self.phase_in_years)

    def is_active(self, year: int) -> bool:
        """Check if policy is active in a given year."""
        if year < self.start_year:
            return False
        return not (self.sunset and year >= self.start_year + self.duration_years)


@dataclass
class TaxPolicy(Policy):
    """Tax policy proposal with detailed parameters."""

    rate_change: float = 0.0
    new_rate: float | None = None
    affected_income_threshold: float = 0.0
    affected_income_cap: float | None = None
    credit_amount: float = 0.0
    credit_refundable: bool = False
    deduction_amount: float = 0.0
    affected_taxpayers_millions: float = 0.0
    taxable_income_elasticity: float = 0.25
    labor_supply_elasticity: float = 0.1
    annual_revenue_change_billions: float | None = None
    avg_taxable_income_in_bracket: float = 0.0
    marginal_rate_before: float = 0.0
    data_year: int | None = None
    # When True, an *ordinary*-rate change is applied only to the non-preferential
    # share of marginal income — long-term capital gains and qualified dividends
    # (taxed at preferential rates) are excluded, since an ordinary-bracket rate
    # change does not touch them. Dataclass default False preserves legacy callers;
    # Generic validation, custom UI/API, and preset fallbacks set True. Set False
    # for AGI-inclusive surtaxes. See ``preferential_income_share`` and
    # docs/METHODOLOGY.md (Static Scoring).
    ordinary_income_base: bool = False

    def __post_init__(self):
        super().__post_init__()
        if not (-1.0 <= self.rate_change <= 1.0):
            raise ValueError(f"rate_change must be between -1.0 and 1.0, got {self.rate_change}")
        if self.new_rate is not None and not (0.0 <= self.new_rate <= 1.0):
            raise ValueError(f"new_rate must be between 0.0 and 1.0, got {self.new_rate}")
        if self.affected_income_threshold < 0:
            raise ValueError(
                f"affected_income_threshold must be >= 0, got {self.affected_income_threshold}"
            )
        if self.taxable_income_elasticity < 0:
            raise ValueError(
                f"taxable_income_elasticity must be >= 0, got {self.taxable_income_elasticity}"
            )
        if self.labor_supply_elasticity < 0:
            raise ValueError(
                f"labor_supply_elasticity must be >= 0, got {self.labor_supply_elasticity}"
            )
        if self.affected_taxpayers_millions < 0:
            raise ValueError(
                f"affected_taxpayers_millions must be >= 0, got {self.affected_taxpayers_millions}"
            )

        if self.affected_income_threshold > 10_000_000:
            logger.warning(
                f"Very high income threshold ${self.affected_income_threshold:,.0f} - few taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            logger.warning(
                f"ETI of {self.taxable_income_elasticity} exceeds typical range (0.1-0.4)"
            )

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """Estimate static revenue effect before behavioral responses."""
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if use_real_data and self._should_use_irs_data():
            try:
                return self._estimate_from_irs_data(baseline_revenue)
            except Exception as exc:
                logger.warning(f"Could not use IRS data for auto-population: {exc}")
                logger.warning("Falling back to manual parameters or heuristics")

        if (
            self.rate_change != 0
            and self.affected_taxpayers_millions > 0
            and self.avg_taxable_income_in_bracket > 0
        ):
            marginal_income = max(
                0,
                self.avg_taxable_income_in_bracket - self.affected_income_threshold,
            )

            if self.affected_income_threshold == 0:
                marginal_income = self.avg_taxable_income_in_bracket

            ordinary_share = self._ordinary_income_share(
                marginal_income * self.affected_taxpayers_millions * 1e6
            )

            revenue_change = (
                self.rate_change
                * marginal_income
                * ordinary_share
                * self.affected_taxpayers_millions
                * 1e6
            ) / 1e9
            return revenue_change

        if self.rate_change != 0:
            if self.affected_income_threshold > 0:
                if self.affected_income_threshold >= 500000:
                    affected_share = 0.20
                elif self.affected_income_threshold >= 200000:
                    affected_share = 0.40
                elif self.affected_income_threshold >= 100000:
                    affected_share = 0.55
                elif self.affected_income_threshold >= 50000:
                    affected_share = 0.75
                else:
                    affected_share = 0.90
            else:
                affected_share = 1.0

            avg_effective_rate = 0.18
            return baseline_revenue * affected_share * (self.rate_change / avg_effective_rate)

        if self.credit_amount != 0 and self.affected_taxpayers_millions > 0:
            return -self.credit_amount * self.affected_taxpayers_millions / 1e3

        if self.deduction_amount != 0 and self.affected_taxpayers_millions > 0:
            marginal_rate = self.marginal_rate_before if self.marginal_rate_before > 0 else 0.25
            return -self.deduction_amount * marginal_rate * self.affected_taxpayers_millions / 1e3

        return 0.0

    def _should_use_irs_data(self) -> bool:
        """Check if we should attempt to auto-populate from IRS SOI data.

        Threshold of 0 (all brackets) is allowed — that path scores a uniform
        rate change against total SOI taxable income rather than the legacy
        ``baseline × Δrate / 0.18`` heuristic.
        """
        return (
            self.rate_change != 0
            and self.affected_income_threshold >= 0
            and self.affected_taxpayers_millions == 0
        )

    def _estimate_from_irs_data(self, baseline_revenue: float) -> float:
        """Auto-populate parameters from IRS SOI data and estimate revenue effect."""
        _ = baseline_revenue
        from fiscal_model.data import IRSSOIData

        irs_data = IRSSOIData()
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError(
                "No IRS SOI data files found. "
                "See fiscal_model/data_files/irs_soi/README.md for download instructions."
            )

        year = self.data_year if self.data_year else max(available_years)
        logger.info(f"Auto-populating tax policy parameters from {year} IRS SOI data")
        bracket_info = irs_data.get_filers_by_bracket(
            year=year,
            threshold=self.affected_income_threshold,
        )

        logger.info(
            f"  Affected filers: {bracket_info['num_filers']/1e6:.2f}M "
            f"(threshold: ${self.affected_income_threshold:,.0f})"
        )
        logger.info(f"  Avg taxable income: ${bracket_info['avg_taxable_income']:,.0f}")

        self.affected_taxpayers_millions = bracket_info["num_filers"] / 1e6
        self.avg_taxable_income_in_bracket = bracket_info["avg_taxable_income"]

        marginal_income = max(
            0,
            bracket_info["avg_taxable_income"] - self.affected_income_threshold,
        )

        if self.affected_income_threshold == 0:
            marginal_income = bracket_info["avg_taxable_income"]

        logger.info(f"  Avg total income: ${bracket_info['avg_taxable_income']:,.0f}")
        logger.info(
            f"  Marginal income above ${self.affected_income_threshold:,.0f}: ${marginal_income:,.0f}"
        )

        ordinary_share = self._ordinary_income_share(
            marginal_income * bracket_info["num_filers"], year=year
        )
        if ordinary_share < 1.0:
            logger.info(
                f"  Ordinary-income share (excl. preferential cap gains): {ordinary_share:.2f}"
            )

        revenue_change = (
            self.rate_change * marginal_income * ordinary_share * bracket_info["num_filers"]
        ) / 1e9

        logger.info(
            f"  Estimated revenue change: ${revenue_change:,.1f}B "
            f"({self.rate_change*100:+.1f}pp rate change)"
        )

        return revenue_change

    def _ordinary_income_share(
        self, total_marginal_income_dollars: float, *, year: int | None = None
    ) -> float:
        """Fraction of marginal income subject to an *ordinary* rate change.

        Returns 1.0 (legacy whole-base behavior) unless ``ordinary_income_base``
        is set and this is an income-tax policy, in which case the preferentially
        taxed (long-term capital gains) share is removed.
        """
        if not self.ordinary_income_base:
            return 1.0
        if self.policy_type != PolicyType.INCOME_TAX:
            return 1.0
        pref = preferential_income_share(
            self.affected_income_threshold,
            total_marginal_income_dollars / 1e9,
            year=year if year is not None else self.data_year,
        )
        return 1.0 - pref

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Behavioral revenue offset under standard ETI methodology.

        Returns a SIGNED value with the same sign as ``static_effect`` so the
        engine's ``deficit_after = static_deficit + behavioral`` (where
        ``static_deficit = -static_revenue``) shrinks the magnitude of the
        revenue change in both directions: erodes the gain on a tax increase
        and recovers some revenue on a tax cut. Magnitude follows the
        Saez-style 0.5·ETI·|static| convention.
        """
        return static_effect * self.taxable_income_elasticity * 0.5

    def validate_inputs(self) -> list[str]:
        """Validate inputs and return warning strings for unusual parameters."""
        warnings = []

        if self.affected_income_threshold > 10_000_000:
            warnings.append(
                f"Very high income threshold (${self.affected_income_threshold:,.0f}): "
                "only a small fraction of taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            warnings.append(
                f"High ETI ({self.taxable_income_elasticity:.2f}): "
                "typical range is 0.1-0.4; consider if this is intentional"
            )

        if self.rate_change > 0.2:
            warnings.append(
                f"Large rate increase ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly restrictive"
            )

        if self.rate_change < -0.2:
            warnings.append(
                f"Large rate decrease ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly stimulative"
            )

        if (
            self.rate_change != 0
            and self.affected_income_threshold == 0
            and self.affected_taxpayers_millions == 0
            and self.avg_taxable_income_in_bracket == 0
        ):
            warnings.append(
                "Rate change specified but no population data provided: "
                "cannot estimate revenue impact accurately. "
                "Consider providing affected_taxpayers_millions or avg_taxable_income_in_bracket"
            )

        return warnings


@dataclass
class CapitalGainsPolicy(TaxPolicy):
    """Capital gains policy: a semi-log realizations response on a stock of
    accrued gains, with step-up at death as an escape from that stock.

    **The response is to the tax rate, not to the net-of-tax rate.** The
    capital-gains realization literature reports an elasticity defined as the
    percentage change in realizations over the percentage change in the *tax
    rate* (CRS R48562, *Boundaries on the Long-Run Realization Response to
    Changes in Capital Gains Taxes*, 2025, pp. 1 and 13), behind which sits a
    semi-log realizations function ``R = B exp(-b t)``.  So::

        R1 = R0 * exp(-b * (tau1 - tau0))       b = elasticity / reference rate

    Two properties come free with that form and neither is a second parameter.
    The implied elasticity ``e(t) = b*t`` **rises with the rate**, so the top
    bracket responds more than the 15 percent bracket to the same
    percentage-point change; and there is a revenue-maximizing rate at
    ``tau* = 1/b``.

    **Frozen elasticities.** Dowd, McClelland & Muthitacharoen (2015),
    *New Evidence on the Tax Elasticity of Capital Gains*, National Tax Journal
    68(3): persistent -0.72, transitory -1.2, both at the 22 percent reference
    rate CRS states its Table 4 estimates are adjusted to.  They are stored
    here as **magnitudes** - 0.72 and 1.20 - because the sign already lives in
    ``exp(-b * delta_tau)``; a rate rise cuts realizations either way.  That
    gives
    ``b = 3.273`` and ``tau* = 30.6%``; JCT's own working coefficient is 3.1
    (CRS R48562 p. 8) and Treasury's is 0.72 at 22 percent, the same as DMM's.
    Agersnap & Zidar (2021) estimate a much lower -0.3 to -0.5 and imply a
    higher revenue-maximizing rate; they are named here as the alternative and
    are deliberately **not** used - one frozen set, per owner Decision 3 of
    ``planning/MODELING_IMPROVEMENT.md``.

    The transitory elasticity is a *retiming* response, so it applies in the
    enactment year only, and only to the share of the base that has a timing
    margin: realized long-term gains, not qualified dividends or capital gain
    distributions, which a taxpayer cannot choose when to receive.

    **The base is a dated flow and is projected across the window.**  SOI
    reports realizations for a tax year; a ten-year score prices ten later
    years.  Realizations are a flow off the accrued-gains stock at the observed
    hazard - ``R = h * A`` - so the flow grows at the same rate the stock
    already grows at (:meth:`realizations_projection_factor`), and holding it
    flat instead would assert a hazard falling 5.8 percent a year.  No new
    constant enters: both ``h`` and the growth rate are already read from
    ``accrued_gains_parameters.csv``.  The projection applies only to the
    SOI-populated base, whose tax year is known; a caller who supplies
    ``baseline_realizations_billions`` supplies an aggregate whose vintage this
    class has no field for, so that base is used exactly as given.

    **Lock-in** is not a multiplier.  A share ``omega = m/(h+m)`` of the accrued
    gains stock leaves it at death rather than by sale, where ``h`` is the
    observed realization hazard and ``m`` the mortality-weighted exit rate.
    While step-up is available those gains are never taxed, so the price of
    realizing now is ``tau*(1 - (1-omega)*d)`` against ``tau*(1 - d)`` once
    death is a realization event, with ``d`` discounting the deferral over the
    expected holding horizon ``1/(h+m)``.  DMM estimated under current law, so
    the literature ``b`` is the with-step-up value and the without-step-up
    value is the smaller one that ratio implies.  Lower realizations also let
    the stock accumulate, which feeds back into later realizations and into the
    flow of gains transferred at death; that is tracked as a ratio to the
    baseline stock so no growth rate is introduced into the realizations flow.

    **The death channel is not the whole flow of gains at death.**  Every
    published realization-at-death proposal states reliefs, and
    :meth:`reachable_gains_per_decedent` prices the ones that bite on a base
    measured as unrealized gains: the charitable exclusion, section 121 on the
    principal residence, and - where the design offers it - deferral of tax on
    a family-owned and -operated business until the interest is sold.  Two more
    reliefs those proposals state, the spousal carry-over and the exclusion for
    tangible personal property, remove nothing from this base because Poterba &
    Weisbenner's flow already excludes inter-spousal transfers and assigns no
    accrued gain to vehicles, bonds or collectibles; deducting either would be
    a double count.  Gains at death then respond to a change in *their* rate
    with the **persistent** coefficient only
    (:meth:`death_response_coefficient`) - death cannot be retimed, so the
    transitory term has no place - and the tax induces further charitable
    substitution at the Bakija-Gale-Slemrod price elasticity.
    """

    baseline_capital_gains_rate: float = 0.20
    baseline_realizations_billions: float = 0.0
    #: Dowd, McClelland & Muthitacharoen (2015), at ``elasticity_reference_rate``.
    persistent_elasticity: float = 0.72
    transitory_elasticity: float = 1.20
    #: The tax rate the frozen elasticities are evaluated at (CRS R48562 Table 4).
    elasticity_reference_rate: float = 0.22
    #: Constant-elasticity override, used when ``use_time_varying_elasticity``
    #: is off; interpreted the same way, as a tax-rate elasticity at the
    #: reference rate.
    realization_elasticity: float = 0.5
    use_time_varying_elasticity: bool = True
    step_up_at_death: bool = True
    eliminate_step_up: bool = False
    step_up_exemption: float = 1_000_000
    #: Whether the score includes the gains-at-death channel.  A benchmark that
    #: scores only the rate change of a combined proposal sets this False; it
    #: is a statement about the policy's scope, not a behavioural parameter.
    score_gains_at_death: bool = True
    #: Discount rate on deferred realization, used only to price the lock-in
    #: wedge between the with- and without-step-up worlds.
    deferral_discount_rate: float = 0.04
    #: Whether the death channel applies the carve-outs every published
    #: realization-at-death proposal states.  A caller that wants the bare
    #: "every dollar of accrued gain, taxed" identity turns it off; nothing in
    #: the validation battery does.
    apply_death_carveouts: bool = True
    #: 26 U.S.C. 121(b)(1): $250,000 of gain on a principal residence, per
    #: person.  Both Green Books preserve it and make it portable to a
    #: surviving spouse ($500,000 per couple); the per-person figure is what a
    #: single decedent's final return can use.
    section_121_exclusion: float = 250_000.0
    #: Whether tax on the appreciation of family-owned and -operated businesses
    #: is deferred until the interest is sold.  Stated by both Green Books and
    #: by neither CBO budget option, so it is a **design** switch, not a
    #: behavioural parameter: see ``validation/core.py``'s
    #: ``GREEN_BOOK_DEATH_DESIGN_RULE``.  Off by default, so a policy scores the
    #: bare construction unless its source states the election.
    defer_family_business_gains: bool = False
    #: Price elasticity of charitable bequests, as a magnitude.  Bakija, Gale &
    #: Slemrod (2003), *Charitable Bequests and Taxes on Inheritances and
    #: Estates*, NBER WP 9661 / AEA Papers & Proceedings, Table 1,
    #: specification (a).  Their most robust specification (d) reports -2.142
    #: and Joulfaian (2000) reports -0.74; (a) is the smallest magnitude in the
    #: frozen paper's own table and is taken for that reason, since a larger
    #: one moves every step-up-elimination score further down.
    charitable_bequest_price_elasticity: float = 1.617

    def __post_init__(self):
        super().__post_init__()
        if not (0 <= self.baseline_capital_gains_rate <= 1):
            raise ValueError(
                "baseline_capital_gains_rate must be between 0 and 1, "
                f"got {self.baseline_capital_gains_rate}"
            )
        if self.persistent_elasticity < 0:
            raise ValueError(
                f"persistent_elasticity must be >= 0, got {self.persistent_elasticity}"
            )
        if self.transitory_elasticity < 0:
            raise ValueError(
                f"transitory_elasticity must be >= 0, got {self.transitory_elasticity}"
            )
        if not (0 < self.elasticity_reference_rate < 1):
            raise ValueError(
                "elasticity_reference_rate must be in (0, 1), "
                f"got {self.elasticity_reference_rate}"
            )
        if self.realization_elasticity < 0:
            raise ValueError(
                f"realization_elasticity must be >= 0, got {self.realization_elasticity}"
            )
        if self.deferral_discount_rate < 0:
            raise ValueError(
                f"deferral_discount_rate must be >= 0, got {self.deferral_discount_rate}"
            )
        if self.section_121_exclusion < 0:
            raise ValueError(
                f"section_121_exclusion must be >= 0, got {self.section_121_exclusion}"
            )
        if self.charitable_bequest_price_elasticity < 0:
            raise ValueError(
                "charitable_bequest_price_elasticity must be >= 0 (it is a "
                f"magnitude), got {self.charitable_bequest_price_elasticity}"
            )
        # Whether the caller supplied the base themselves.  ``get_brackets``
        # overwrites the field once it auto-populates, so the question cannot
        # be asked afterwards - and it decides whether the base carries a known
        # tax year and can therefore be projected.
        self._supplied_realizations = float(self.baseline_realizations_billions) > 0
        self._bracket_cache = None
        self._baseline_cache = None

    # ------------------------------------------------------------------
    # Baseline data
    # ------------------------------------------------------------------

    def _data_year(self, baseline) -> int:
        if self.data_year:
            return int(self.data_year)
        return max(baseline.available_years())

    def _baseline_source(self):
        if self._baseline_cache is None:
            from fiscal_model.data import CapitalGainsBaseline

            self._baseline_cache = CapitalGainsBaseline()
        return self._baseline_cache

    def get_brackets(self, use_real_data: bool = True) -> list:
        """Realizations facing this policy, grouped by the rate they face.

        A caller that set ``baseline_realizations_billions`` explicitly - every
        calibrated validation scenario does - gets that single aggregate priced
        at ``baseline_capital_gains_rate``, so those cases are unaffected by
        the SOI bracket table.
        """
        from fiscal_model.data.capital_gains import GainsBracket

        if self._bracket_cache is not None:
            return self._bracket_cache

        if float(self.baseline_realizations_billions) > 0 or not use_real_data:
            realized = float(self.baseline_realizations_billions)
            if realized <= 0:
                raise ValueError(
                    "baseline_realizations_billions must be > 0 for CapitalGainsPolicy "
                    "(set it manually or enable real-data auto-population)."
                )
            self._bracket_cache = [
                GainsBracket(
                    statutory_rate=float(self.baseline_capital_gains_rate),
                    niit_rate=0.0,
                    realizations_billions=realized,
                    tax_billions=realized * float(self.baseline_capital_gains_rate),
                    long_term_share=1.0,
                )
            ]
            return self._bracket_cache

        source = self._baseline_source()
        year = self._data_year(source)
        brackets = source.get_brackets_above_threshold(
            year=year, threshold=float(self.affected_income_threshold)
        )
        if not brackets:
            raise ValueError(
                "No capital gains realizations above threshold "
                f"{self.affected_income_threshold:,.0f} in tax year {year}"
            )
        realized = sum(bracket.realizations_billions for bracket in brackets)
        weighted = sum(
            bracket.realizations_billions * bracket.effective_rate for bracket in brackets
        )
        # Keep the aggregate fields in step so callers that read them - the
        # validation reporter, the UI - describe the base that was used.
        self.baseline_realizations_billions = realized
        self.baseline_capital_gains_rate = weighted / realized if realized > 0 else 0.0
        self._bracket_cache = brackets
        return brackets

    def _reform_rate(self, bracket) -> float:
        """Rate facing one bracket after the reform."""
        if self.new_rate is not None:
            return float(self.new_rate) + bracket.niit_rate
        return float(bracket.statutory_rate + self.rate_change + bracket.niit_rate)

    def _reform_capital_gains_rate(self) -> float:
        """Aggregate reform rate, for callers that want a single number."""
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_capital_gains_rate + self.rate_change)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def realizations_projection_factor(self, year: int | None) -> float:
        """Growth of the realizations base from its SOI tax year to ``year``.

        ``1.0`` when the year is not known, when the caller supplied the base,
        or when the accrued-gains parameters are unavailable, so the module
        degrades to the flat flow it used before rather than failing.
        """
        if year is None or self._supplied_realizations:
            return 1.0
        try:
            source = self._baseline_source()
            tax_year = source._resolve_year(self._data_year(source))
            return source.realizations_projection_factor(tax_year, int(year))
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning(
                "realizations_projection_factor: data unavailable (%s)", exc
            )
            return 1.0

    def lock_in_wedge(self) -> float:
        """Ratio of the realization price with step-up to the price without.

        ``1.0`` when the accrued-gains stock is unavailable, so the module
        degrades to "step-up makes no difference" rather than failing.
        """
        try:
            source = self._baseline_source()
            year = self._data_year(source)
            hazard = source.realization_hazard(year)
            death = source.death_exit_rate()
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("lock_in_wedge: accrued-gains data unavailable (%s)", exc)
            return 1.0

        exit_rate = hazard + death
        if exit_rate <= 0 or death <= 0:
            return 1.0
        escape_share = death / exit_rate
        horizon = 1.0 / exit_rate
        discount = 1.0 / (1.0 + self.deferral_discount_rate) ** horizon
        price_without = 1.0 - discount
        if price_without <= 0:
            return 1.0
        price_with = 1.0 - (1.0 - escape_share) * discount
        return price_with / price_without

    def semi_log_coefficient(
        self, years_since_start: int = 0, long_term_share: float = 1.0
    ) -> float:
        """``b`` in ``R = B exp(-b t)`` for a given year of the window."""
        reference = float(self.elasticity_reference_rate)
        if self.use_time_varying_elasticity:
            persistent = float(self.persistent_elasticity)
            transitory = float(self.transitory_elasticity)
        else:
            persistent = float(self.realization_elasticity)
            transitory = 0.0

        coefficient = persistent / reference
        if years_since_start <= 0 and transitory > 0:
            # The transitory response is retiming around the effective date and
            # is exhausted after it, and only gains a taxpayer chooses when to
            # realize have a timing margin.
            coefficient += (transitory / reference) * max(0.0, min(1.0, long_term_share))

        if self.eliminate_step_up:
            wedge = self.lock_in_wedge()
            if wedge > 0:
                coefficient /= wedge
        return coefficient

    def _realizations_ratio(self, bracket, years_since_start: int) -> float:
        """``R1/R0`` for one bracket in a given year of the window."""
        delta = self._reform_rate(bracket) - bracket.effective_rate
        coefficient = self.semi_log_coefficient(
            years_since_start=years_since_start,
            long_term_share=bracket.long_term_share,
        )
        return math.exp(-coefficient * delta)

    def stock_ratio(self, years_since_start: int, use_real_data: bool = True) -> float:
        """Reform accrued-gains stock over the baseline stock, in ``t`` years.

        Realizations that do not happen stay in the stock, which then supplies
        later realizations and a larger flow of gains transferred at death.
        Expressed as a ratio so the baseline's own growth cancels and no growth
        rate enters the realizations flow.
        """
        if years_since_start <= 0:
            return 1.0
        try:
            source = self._baseline_source()
            year = self._data_year(source)
            hazard = source.realization_hazard(year)
            death = source.death_exit_rate()
            growth = source._parameters["household_net_worth_growth_rate"]
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("stock_ratio: accrued-gains data unavailable (%s)", exc)
            return 1.0

        brackets = self.get_brackets(use_real_data=use_real_data)
        realized = sum(bracket.realizations_billions for bracket in brackets)
        if realized <= 0 or hazard <= 0:
            return 1.0
        # Permanent hazard response only: the transitory term is a retiming,
        # so it does not change the stock's steady drift.
        reform_realized = sum(
            bracket.realizations_billions * self._realizations_ratio(bracket, 1)
            for bracket in brackets
        )
        # ``hazard`` is national - all SOI realizations over the whole accrued-
        # gains stock - while ``brackets`` is only the slice a thresholded
        # policy reaches. Applying the slice's response to the whole hazard
        # would let a $1M+ proposal slow every taxpayer's realizations. The
        # gains outside the slice keep realizing at the baseline rate, and the
        # slice's share of national realizations stands in for its share of the
        # stock, which SOI does not report.
        national = sum(
            bracket.realizations_billions
            for bracket in source.get_brackets_above_threshold(
                year, 0.0, with_timing_share=False
            )
        )
        affected_share = min(1.0, realized / national) if national > 0 else 1.0
        response = reform_realized / realized
        reform_hazard = hazard * (1.0 - affected_share + affected_share * response)

        ratio = 1.0
        for _ in range(years_since_start):
            inflow = hazard + death
            outflow = (reform_hazard + death) * ratio
            ratio += (inflow - outflow) / (1.0 + growth)
        return max(0.0, ratio)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
        year: int | None = None,
    ) -> float:
        """Static effect holding realizations fixed, summed over brackets.

        ``year`` is the year being scored, which the base is projected to; the
        engine passes it for a capital-gains policy and nothing else.  Omitted,
        the base stays at its SOI level, which is what a caller asking for the
        data-year identity wants.
        """
        _ = baseline_revenue
        brackets = self.get_brackets(use_real_data=use_real_data)
        factor = self.realizations_projection_factor(year)
        total = 0.0
        for bracket in brackets:
            tau0 = bracket.effective_rate
            tau1 = self._reform_rate(bracket)
            if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
                raise ValueError(
                    "Capital gains rates must be in [0, 1) for CapitalGainsPolicy"
                )
            total += (tau1 - tau0) * bracket.realizations_billions * factor
        return total

    def estimate_behavioral_offset(
        self,
        static_effect: float,
        years_since_start: int = 0,
        use_real_data: bool = True,
        phase: float = 1.0,
    ) -> float:
        """Behavioral offset from the realizations response.

        ``static_effect`` is not read: the offset is rebuilt bracket by bracket
        because each bracket faces its own price. ``phase`` carries the
        engine's phase-in factor, so a policy that phases its rate change in
        over several years phases the response in with it rather than applying
        the full-strength offset against a partial static effect.
        """
        _ = static_effect
        brackets = self.get_brackets(use_real_data=use_real_data)
        stock = self.stock_ratio(years_since_start, use_real_data=use_real_data)
        # The same projection the static leg applies, so the two stay a
        # decomposition of the score rather than one absorbing the other.
        factor = self.realizations_projection_factor(
            int(self.start_year) + int(years_since_start)
        )

        delta_static = 0.0
        delta_total = 0.0
        for bracket in brackets:
            tau0 = bracket.effective_rate
            tau1 = self._reform_rate(bracket)
            if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
                raise ValueError(
                    "Capital gains rates must be in [0, 1) for CapitalGainsPolicy"
                )
            r0 = bracket.realizations_billions * factor
            r1 = r0 * self._realizations_ratio(bracket, years_since_start) * stock
            delta_static += (tau1 - tau0) * r0
            delta_total += tau1 * r1 - tau0 * r0
        return (delta_static - delta_total) * max(0.0, float(phase))

    def death_response_coefficient(self) -> float:
        """``b`` for the response of gains at death to a change in their rate.

        The **persistent** coefficient only.  The transitory term is a retiming
        response - a taxpayer brings a sale forward or pushes it back around an
        effective date - and death cannot be retimed to the rate, so it has no
        place here.  The lock-in wedge divides it for the same reason it
        divides the realizations coefficient: once death is a realization
        event, holding on no longer escapes the tax.
        """
        reference = float(self.elasticity_reference_rate)
        persistent = (
            float(self.persistent_elasticity)
            if self.use_time_varying_elasticity
            else float(self.realization_elasticity)
        )
        coefficient = persistent / reference
        if self.eliminate_step_up:
            wedge = self.lock_in_wedge()
            if wedge > 0:
                coefficient /= wedge
        return coefficient

    def _charitable_share_at_death(self, decedent_class, rate: float) -> float:
        """Share of a class's gain that goes to charity once gains are taxed.

        Two parts.  The **level** is what already goes to charity: IRS SOI
        *Estate Tax Statistics* Table 1's charitable deduction over the estate
        net of spousal bequests, by size of estate.  The **increment** is the
        substitution the tax induces, and it is the death channel's avoidance
        response: taxing gains at death makes a charitable bequest cheaper
        relative to a bequest to heirs, because the estate saves ``rate`` times
        the unrealized-gain share of the wealth given.  With a constant
        elasticity of charitable bequests with respect to that price, the share
        rises by ``(1 - rate * gain_share) ** -elasticity``.

        The price change ignores that a charitable bequest already avoids
        estate tax for a taxable estate, so the fall in price - and therefore
        the response - is understated.
        """
        baseline = max(0.0, min(1.0, float(decedent_class.charitable_bequest_share)))
        if baseline <= 0:
            return 0.0
        gain_share = max(0.0, min(1.0, float(decedent_class.unrealized_gain_share)))
        price = 1.0 - max(0.0, min(1.0, rate)) * gain_share
        if price <= 0:
            return 1.0
        induced = price ** (-float(self.charitable_bequest_price_elasticity))
        return max(0.0, min(1.0, baseline * induced))

    def reachable_gains_per_decedent(
        self,
        decedent_class,
        rate: float,
        rate_change_faced: float = 0.0,
        years_since_start: int = 0,
    ) -> float:
        """Gain per decedent a realization-at-death proposal actually reaches.

        The carve-outs apply in the order the statute does, and the per-donor
        exclusion is **not** among them: both Green Books grant it against
        *"other* unrealized capital gains", meaning what is left after the
        named reliefs.  The caller subtracts it afterwards.

        1. **Charity.**  Appreciated property transferred to charity generates
           no taxable gain, and the tax itself induces more of it
           (:meth:`_charitable_share_at_death`).
        2. **The family-owned-business election**, where the design offers it.
           Tax on the appreciation of a family-owned and -operated business is
           not due until the interest is sold, so inside a ten-year window only
           what is sold is collected - at the module's own observed realization
           hazard, which introduces no new constant.
        3. **Section 121**, up to :attr:`section_121_exclusion` of the gain on
           the principal residence.
        4. **The rate response**, where the proposal changes the rate this
           decedent faces by ``rate_change_faced``
           (:meth:`death_response_coefficient`).

        The spousal and tangible-personal-property reliefs are absent because
        the base already excludes both - Poterba & Weisbenner's Table 8 note,
        quoted in :mod:`fiscal_model.data.capital_gains`.
        """
        gain = float(decedent_class.gains_per_decedent_dollars)
        if gain <= 0 or not self.apply_death_carveouts:
            return max(0.0, gain)

        gain *= 1.0 - self._charitable_share_at_death(decedent_class, rate)

        if self.defer_family_business_gains:
            deferred = max(
                0.0, min(1.0, float(decedent_class.active_business_gain_share))
            )
            if deferred > 0:
                hazard = self._realization_hazard()
                recaptured = 1.0 - (1.0 - hazard) ** (max(0, int(years_since_start)) + 1)
                gain *= 1.0 - deferred * (1.0 - recaptured)

        residence = max(0.0, min(1.0, float(decedent_class.residence_gain_share)))
        gain -= min(gain * residence, max(0.0, float(self.section_121_exclusion)))

        if rate_change_faced != 0.0:
            gain *= math.exp(-self.death_response_coefficient() * rate_change_faced)

        return max(0.0, gain)

    def _realization_hazard(self) -> float:
        try:
            source = self._baseline_source()
            return float(source.realization_hazard(self._data_year(source)))
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("family-business deferral: hazard unavailable (%s)", exc)
            return 0.0

    def estimate_step_up_elimination_revenue(self, years_since_start: int = 0) -> float:
        """Revenue from treating transfers at death as realization events.

        Decedent wealth times the unrealized-gain share of an estate that size,
        less the carve-outs the proposal states
        (:meth:`reachable_gains_per_decedent`), less the per-donor exclusion,
        priced at the rate the gain would face on a final return.  Indexed to
        household net worth, so the flow grows with the asset stock instead of
        sitting at one constant.
        """
        if not self.eliminate_step_up or not self.score_gains_at_death:
            return 0.0
        try:
            source = self._baseline_source()
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("gains at death: data unavailable (%s)", exc)
            return 0.0

        year = int(self.start_year) + max(0, int(years_since_start))
        exemption = max(0.0, float(self.step_up_exemption))
        stock = self.stock_ratio(years_since_start)

        from fiscal_model.data.capital_gains import NIIT_RATE, NIIT_THRESHOLD

        revenue = 0.0
        for decedent_class in source.decedent_classes(year):
            gain = decedent_class.gains_per_decedent_dollars
            if gain <= 0 or decedent_class.decedents_per_year <= 0:
                continue
            niit = NIIT_RATE if gain >= NIIT_THRESHOLD else 0.0
            statutory = source.statutory_rate_on_gain(gain) - niit
            # A rate change that applies above an income threshold reaches a
            # decedent only if the gain on the final return clears it.  The
            # bracket is read off the class's gain before carve-outs, so a
            # decedent whose reliefs drop them into a lower preferential
            # bracket is still priced at the higher one.
            in_scope = gain >= float(self.affected_income_threshold)
            if self.new_rate is not None and in_scope:
                rate = float(self.new_rate) + niit
            elif in_scope:
                rate = statutory + float(self.rate_change) + niit
            else:
                rate = statutory + niit
            rate = max(0.0, min(rate, 0.999))
            rate_change_faced = rate - (statutory + niit) if in_scope else 0.0
            reachable = self.reachable_gains_per_decedent(
                decedent_class, rate, rate_change_faced, years_since_start
            )
            taxable_per_decedent = max(0.0, reachable - exemption)
            if taxable_per_decedent <= 0:
                continue
            taxable = (
                decedent_class.decedents_per_year * taxable_per_decedent / 1e9 * stock
            )
            revenue += taxable * rate
        return revenue


@dataclass
class SpendingPolicy(Policy):
    """Spending policy proposal.

    Budget authority and outlays are **distinct quantities**.
    ``annual_spending_change_billions`` (and ``budget_authority_path``) describe
    the *authority* a proposal provides or withdraws;
    :meth:`get_outlays_in_year` spends that authority out over time using the
    profile named by ``outlay_account_class``
    (see :mod:`fiscal_model.spending_outlays`).

    ``outlay_account_class`` defaults to ``"immediate"`` - the identity, one
    dollar of authority becoming one dollar of outlay in the year it is
    provided - so an existing policy scores exactly as it did before spend-out
    existed. Callers that know the account type opt in; the validation shapes
    in ``validation/core.py`` do.
    """

    annual_spending_change_billions: float = 0.0
    annual_growth_rate: float = 0.02
    gdp_multiplier: float = 1.0
    employment_per_billion: float = 10000
    is_one_time: bool = False
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense"
    outlay_account_class: str = IMMEDIATE
    #: Explicit year-by-year budget authority from ``start_year``, for a
    #: proposal whose authority is *not* a level - a multi-year authorization
    #: that ends, say. When set it overrides the level-times-growth path.
    budget_authority_path: tuple[float, ...] | None = None

    def __post_init__(self):
        super().__post_init__()
        category_to_type = {
            "defense": PolicyType.DISCRETIONARY_DEFENSE,
            "nondefense": PolicyType.DISCRETIONARY_NONDEFENSE,
            "mandatory": PolicyType.MANDATORY_SPENDING,
        }
        expected_type = category_to_type.get(self.category)
        if expected_type and self.policy_type != expected_type:
            self.policy_type = expected_type
        if self.budget_authority_path is not None:
            self.budget_authority_path = tuple(float(x) for x in self.budget_authority_path)
        # Fail fast on an unknown class rather than silently outlaying 1:1.
        get_outlay_profile(self.outlay_account_class)

    @property
    def outlay_profile(self) -> "OutlayProfile":
        """The spend-out profile this policy's account class implies."""
        return get_outlay_profile(self.outlay_account_class)

    def get_budget_authority_in_year(
        self, year: int, start_amount: float | None = None
    ) -> float:
        """Budget authority provided in a year, including growth and phase-in.

        This is the quantity a proposal actually sets. It is *not* the outlay
        unless the account spends out immediately.
        """
        if not self.is_active(year):
            return 0.0

        years_since_start = year - self.start_year

        if self.is_one_time and years_since_start > 0:
            return 0.0

        phase_factor = self.get_phase_in_factor(year)

        if self.budget_authority_path is not None and start_amount is None:
            if years_since_start >= len(self.budget_authority_path):
                return 0.0
            return self.budget_authority_path[years_since_start] * phase_factor

        # `is not None`, not truthiness: a caller overriding the level with 0.0
        # means zero authority, and must not silently get the policy's own level
        # back. The branch above already tests `start_amount is None`, so a
        # truthiness test here would disagree with it for exactly that value.
        base = (
            start_amount
            if start_amount is not None
            else self.annual_spending_change_billions
        )
        growth_factor = (1 + self.annual_growth_rate) ** years_since_start
        return base * growth_factor * phase_factor

    def get_outlays_in_year(
        self,
        year: int,
        start_amount: float | None = None,
        *,
        window_start: int | None = None,
    ) -> float:
        """Outlays in a year: budget authority from this and earlier years, spent out.

        ``window_start`` bounds how far back authority is drawn from. It
        defaults to ``start_year``, so authority provided before the policy
        began contributes nothing - which is what a *change* in authority
        means.
        """
        profile = self.outlay_profile
        if profile.shares == (1.0,):
            # The identity. Short-circuited on the *rate*, not on the profile's
            # length: a one-entry profile that outlays less than a full dollar
            # still has to be applied.
            return self.get_budget_authority_in_year(year, start_amount)

        earliest = self.start_year if window_start is None else max(window_start, self.start_year)
        total = 0.0
        for lag, share in enumerate(profile.shares):
            source_year = year - lag
            if source_year < earliest:
                break
            if share == 0.0:
                continue
            total += share * self.get_budget_authority_in_year(source_year, start_amount)
        return total

    def get_spending_in_year(self, year: int, start_amount: float | None = None) -> float:
        """Outlays in a given year.

        Kept under its original name because every caller in the model, the app
        and the tests means *the amount that hits the deficit this year*, which
        is the outlay. Under the default ``immediate`` class this is identical
        to :meth:`get_budget_authority_in_year`.
        """
        return self.get_outlays_in_year(year, start_amount)


@dataclass
class TransferPolicy(Policy):
    """Transfer program policy."""

    benefit_change_percent: float = 0.0
    benefit_change_dollars: float = 0.0
    eligibility_age_change: float = 0.0
    new_beneficiaries_millions: float = 0.0
    annual_cost_change_billions: float = 0.0
    labor_force_participation_effect: float = 0.0

    def estimate_cost_effect(self, baseline_cost: float) -> float:
        """Estimate change in program costs."""
        if self.annual_cost_change_billions != 0:
            return self.annual_cost_change_billions

        cost_change = baseline_cost * self.benefit_change_percent

        if self.new_beneficiaries_millions != 0:
            avg_benefit = baseline_cost / 60
            cost_change += avg_benefit * self.new_beneficiaries_millions

        return cost_change


@dataclass
class PolicyPackage:
    """A package of multiple policies analyzed together."""

    name: str
    description: str
    policies: list[Policy] = field(default_factory=list)
    interaction_factor: float = 1.0

    def add_policy(self, policy: Policy):
        """Add a policy to the package."""
        self.policies.append(policy)

    def get_all_years(self) -> tuple[int, int]:
        """Get the range of years covered by all policies."""
        if not self.policies:
            return (2025, 2034)

        start = min(policy.start_year for policy in self.policies)
        end = max(policy.start_year + policy.duration_years for policy in self.policies)
        return (start, end)

    def get_active_policies(self, year: int) -> list[Policy]:
        """Get all policies active in a given year."""
        return [policy for policy in self.policies if policy.is_active(year)]
