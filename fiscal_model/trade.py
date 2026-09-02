"""
Trade and Tariff Policy Module

Scores a tariff the way a conventional revenue estimate scores an indirect
tax: gross customs duty, net of the import-demand response, duty avoidance,
the income-and-payroll offset, and the federal receipts lost when trading
partners retaliate against US exports.

The chain, per year::

    Δτ      = stated rate − the duty the base already collects
    p       = border_pass_through × Δτ
    V       = 1 + ε·p                                    for p ≤ 30pp
            = 1 + ε·0.30 + (p − 0.30)·ε·multiplier       above it, floored
    gross   = base · V · Δτ/(1 + Δτ)
    avoid   = avoidance_rate · gross
    offset  = income_payroll_offset · (gross − avoid)
    retal   = marginal_receipts_rate · [retaliation_rate · Δτ · export_base]
    net     = gross − avoid − offset − retal

``estimate_static_revenue_effect`` returns ``gross``;
``estimate_behavioral_offset`` returns ``avoid + offset + retal`` **signed to
match ``gross``**, so the scorer's ``final_deficit_effect`` is the net figure,
both halves stay separately readable — which is what the app's tariff caption
renders — and a tariff *cut* has its cost eroded rather than amplified.

Three things about that chain are worth stating plainly, because the module
used to do none of them:

1. **The income-and-payroll offset.** CBO, JCT and Treasury's Office of Tax
   Analysis all score an indirect tax net of an offset of about 25%, on the
   convention that a policy change does not alter total nominal income: duty
   paid is income not paid to labour and capital, so the income and payroll
   tax bases shrink. Before this the module returned gross customs revenue and
   called it a score.
2. **Pass-through belongs in the demand response.** Amiti, Redding & Weinstein
   (2019) and Fajgelbaum et al. (2020) find the duty-inclusive US import price
   rose approximately one-for-one with the 2018-19 tariffs and foreign export
   prices did not fall, so the whole tariff reaches the price importers face:
   ``border_pass_through_rate`` is frozen at 1.00. That is a *different and
   larger* number than the retail pass-through the household-cost display
   needs (Cavallo et al. 2021), which stays at 0.60 under its own key.
3. **The tax-inclusive rate.** A conventional estimate holds nominal income
   fixed, so the same nominal spending buys a duty-inclusive bundle: the duty
   is ``base × τ/(1+τ)``, not ``base × τ`` (Tax Foundation FF861 p. 4 n. 10,
   citing JCT JCX-58-23).

Every level in ``TRADE_BASELINE`` is a 2024 Census measurement, transcribed
with its provenance to ``data_files/trade/tariff_scoring_inputs.csv``; the
behavioural parameters are one frozen, cited value per mechanism. No constant
here is keyed to a benchmark. In particular the two coverage constants that
used to be fitted to their own targets are gone: ``universal_coverage_rate`` is
now 1 minus the Canada-plus-Mexico share of goods imports (the USMCA carve-out
every universal-tariff proposal carries), and ``china_effective_coverage`` is
deleted in favour of the incremental-rate identity — a 60% tariff on China
raises the rate by 60pp minus the 10.93% already collected, applied to the
whole base.

References:
- Amiti, Redding & Weinstein (2019), *JEP* 33(4); Fajgelbaum, Goldberg, Kennedy
  & Khandelwal (2020), *QJE* 135(1) — near-complete border pass-through
- Cavallo, Gopinath, Neiman & Tang (2021), *AER: Insights* 3(1) — partial
  retail pass-through
- Ghodsi, Grübler & Stehrer (2016) — US binding weighted-average import-demand
  elasticity of −0.997
- Boehm, Levchenko & Pandalai-Nayar (2023), *AER* 113(4); USITC pub. 5405 —
  elasticities roughly double over the medium run
- JCT, *The Income and Payroll Tax Offset to Changes in Excise Tax Revenues*
  (JCX-59-11) and JCX-9-24, cited through Tax Foundation FF861 pp. 3-4
- Tax Foundation, *How Much Revenue Can Tariffs Really Raise for the Federal
  Government?*, Fiscal Fact 861 (April 2025)
- U.S. Census Bureau international trade series, 2024
"""

import math
from dataclasses import dataclass

from .constants import MARGINAL_REVENUE_RATE
from .policies import PolicyType, TaxPolicy

TRADE_BASELINE = {
    # --- Trade levels: U.S. Census Bureau, 2024 (see the CSV) --------------
    "total_imports_billions": 3263.9,
    "total_exports_billions": 2063.0,
    "current_avg_tariff_rate": 0.0236,
    "current_tariff_revenue_billions": 76.6,
    "us_households": 130_000_000,

    # Country- and sector-specific import bases and the duty each already pays
    "china_imports_billions": 440.3,
    "china_existing_avg_tariff": 0.1093,   # calculated duty / imports for consumption
    "us_exports_to_china_billions": 143.3,  # China's retaliation base
    "eu_imports_billions": 550.0,
    "auto_imports_billions": 384.9,         # HS 87
    "auto_existing_avg_tariff": 0.0199,
    "auto_usmca_exempt_share": 0.4842,      # Canada + Mexico share of HS 87
    "steel_aluminum_imports_billions": 58.9,  # HS 72 + HS 76
    "steel_aluminum_existing_avg_tariff": 0.0306,

    # --- Behavioural parameters: one frozen, cited value per mechanism -----
    # Border pass-through into duty-inclusive import prices. Amiti, Redding &
    # Weinstein (2019); Fajgelbaum et al. (2020): approximately complete.
    "border_pass_through_rate": 1.00,
    # Retail pass-through, for the household-cost display only. Cavallo et al.
    # (2021) find this is materially below the border figure.
    "consumer_pass_through_rate": 0.60,
    # Ghodsi, Grübler & Stehrer (2016) binding weighted-average for the US,
    # adopted by Tax Foundation FF861 p. 4.
    "import_price_elasticity": -0.997,
    "retaliation_rate": 0.30,
    "tariff_avoidance_rate": 0.05,
    # CBO/JCT/OTA convention: an indirect tax shrinks the income and payroll
    # tax bases by about a quarter of its net receipts.
    "income_payroll_offset_rate": 0.25,
    # Federal receipts per dollar of income lost to retaliation — the app's own
    # dynamic-scoring convention, not a new constant.
    "marginal_receipts_rate": MARGINAL_REVENUE_RATE,

    # Effective coverage of a universal tariff: 1 minus the Canada + Mexico
    # share of goods imports, i.e. the USMCA carve-out every universal-tariff
    # proposal has carried. Derived, not fitted.
    "universal_coverage_rate": 0.7197,
    # Half of goods imports, the share the reciprocal-tariff preset applies a
    # flat 20pp to. Moved out of the factory so it is visible and testable; it
    # is a shape assumption about that preset, not a measurement.
    "reciprocal_coverage_rate": 0.50,

    # Non-linear tariff response. Elasticities roughly double over the medium
    # run (Boehm, Levchenko & Pandalai-Nayar 2023; USITC pub. 5405), which
    # bites hardest on the large rate changes.
    "high_tariff_threshold": 0.30,
    "high_tariff_elasticity_multiplier": 2.0,
    "min_volume_factor": 0.20,  # Floor: imports never fall below 20% of base
}


@dataclass
class TariffPolicy(TaxPolicy):
    """
    Tariff / trade policy.

    Scores net customs receipts — gross duty less the import-demand response,
    avoidance, the income-and-payroll offset and the receipts lost to
    retaliation — and reports consumer cost and household impact alongside.
    """
    policy_type: PolicyType = PolicyType.EXCISE_TAX
    tariff_rate_change: float = 0.0
    target_country: str | None = None
    target_sector: str | None = None
    import_base_billions: float = 0.0
    pass_through_rate: float = TRADE_BASELINE["consumer_pass_through_rate"]
    border_pass_through_rate: float = TRADE_BASELINE["border_pass_through_rate"]
    import_elasticity: float = TRADE_BASELINE["import_price_elasticity"]
    retaliation_rate: float = TRADE_BASELINE["retaliation_rate"]
    #: Value of US exports a trading partner can retaliate against. Defaults to
    #: total goods exports scaled by this policy's share of goods imports —
    #: partners retaliate in proportion to the harm done, so a $59B steel
    #: tariff does not invite retaliation against the whole $2.1T of exports.
    #: A country-targeted factory overrides it with exports to that country.
    retaliation_export_base_billions: float = 0.0
    include_consumer_cost: bool = True
    include_retaliation: bool = True

    def __post_init__(self):
        self.policy_type = PolicyType.EXCISE_TAX
        super().__post_init__()
        if self.import_base_billions <= 0 and self.tariff_rate_change != 0:
            self.import_base_billions = TRADE_BASELINE["total_imports_billions"]
        if self.retaliation_export_base_billions <= 0:
            total_imports = TRADE_BASELINE["total_imports_billions"]
            exposure = self.import_base_billions / total_imports if total_imports else 0.0
            self.retaliation_export_base_billions = (
                TRADE_BASELINE["total_exports_billions"] * exposure
            )

    # -- the scoring chain -------------------------------------------------

    def import_price_change(self) -> float:
        """Proportional rise in the price importers face.

        The tariff reaches that price approximately one-for-one: foreign
        exporters did not cut their prices in 2018-19 (Amiti, Redding &
        Weinstein 2019; Fajgelbaum et al. 2020). This is the price change the
        import-demand elasticity acts on — not the retail pass-through, which
        is smaller and belongs to the consumer-cost display.
        """
        return self.border_pass_through_rate * self.tariff_rate_change

    def import_volume_factor(self) -> float:
        """Share of the pre-tariff import base that still arrives."""
        price_change = self.import_price_change()
        threshold = TRADE_BASELINE["high_tariff_threshold"]
        hi_mult = TRADE_BASELINE["high_tariff_elasticity_multiplier"]
        floor = TRADE_BASELINE["min_volume_factor"]
        if price_change > threshold:
            factor = (
                1
                + self.import_elasticity * threshold
                + (price_change - threshold) * self.import_elasticity * hi_mult
            )
        else:
            factor = 1 + self.import_elasticity * price_change
        return max(floor, factor)

    def estimate_static_revenue_effect(
        self, baseline_revenue: float, use_real_data: bool = True
    ) -> float:
        """Gross customs duty, after the import-demand response.

        The rate is applied tax-inclusively. A conventional estimate holds
        nominal income fixed, so the same nominal spending buys a
        duty-inclusive bundle and the duty collected is ``base × τ/(1+τ)``
        (Tax Foundation FF861 p. 4 n. 10, citing JCT JCX-58-23). Everything
        that stands between this and the score is in
        :meth:`estimate_behavioral_offset`.
        """
        if self.tariff_rate_change == 0:
            return 0.0
        rate = self.tariff_rate_change
        adjusted_base = self.import_base_billions * self.import_volume_factor()
        return adjusted_base * rate / (1 + rate)

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Everything between gross customs duty and the budget effect.

        Three channels:

        * **Avoidance and evasion** — a flat share of gross duty.
        * **The income-and-payroll offset** — the CBO/JCT/OTA convention that
          an indirect tax shrinks the income and payroll tax bases by about a
          quarter of its net receipts.
        * **Retaliation** — the federal receipts lost when partners tax US
          exports back, converted at the app's own marginal revenue rate. Zero
          for a tariff *cut*, which invites none, and suppressed when
          ``include_retaliation`` is off, which is what a strictly conventional
          (no-retaliation) score wants.

        **Signed to match ``static_effect``**, the convention
        :meth:`fiscal_model.policies_core.TaxPolicy.estimate_behavioral_offset`
        sets for every behavioural offset in the repository: the scorer adds
        this to ``-static_revenue``, so an offset carrying the static effect's
        sign erodes the magnitude in *both* directions. A tariff cut loses less
        revenue than its gross figure because the income and payroll bases grow
        back; returning an unsigned positive here would make a cut cost more
        than its own gross, not less.

        Scales with ``static_effect`` so a phased-in tariff nets down by the
        same proportion its gross duty phases in by.
        """
        gross = abs(static_effect)
        if gross == 0.0:
            return 0.0
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = (gross - avoidance) * TRADE_BASELINE["income_payroll_offset_rate"]
        retaliation = 0.0
        if self.include_retaliation:
            full = abs(self.estimate_static_revenue_effect(0.0))
            phase = gross / full if full else 0.0
            retaliation = abs(self.estimate_retaliation_revenue_loss()) * phase
        return math.copysign(avoidance + offset + retaliation, static_effect)

    # -- the channels, separately readable ---------------------------------

    def estimate_income_payroll_offset(self) -> float:
        """Annual income and payroll receipts lost to the tariff itself.

        Signed like the duty it offsets, so a tariff cut returns a negative
        figure — the income and payroll bases grow when duty falls.
        """
        gross = self.estimate_static_revenue_effect(0.0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        return (gross - avoidance) * TRADE_BASELINE["income_payroll_offset_rate"]

    def estimate_consumer_cost(self) -> float:
        """Annual cost to consumers from higher retail prices."""
        if self.tariff_rate_change <= 0:
            return 0.0
        return self.pass_through_rate * self.tariff_rate_change * self.import_base_billions

    def estimate_retaliation_cost(self) -> float:
        """Annual export value lost to trading-partner retaliation."""
        if self.tariff_rate_change <= 0:
            return 0.0
        return (
            self.retaliation_rate
            * self.tariff_rate_change
            * self.retaliation_export_base_billions
        )

    def estimate_retaliation_revenue_loss(self) -> float:
        """Annual federal receipts lost to retaliation.

        Lost exports are lost income, and the federal government takes about
        :data:`~fiscal_model.constants.MARGINAL_REVENUE_RATE` of income at the
        margin. This under-states the drag — an export-value loss is not an
        income loss, and no multiplier or supply-chain effect is modelled — and
        the lane file records the size of the gap against Tax Foundation's own
        estimate of retaliation's revenue cost.
        """
        return self.estimate_retaliation_cost() * TRADE_BASELINE["marginal_receipts_rate"]

    def get_household_impact(self) -> float:
        """Annual cost per household."""
        return self.estimate_consumer_cost() * 1e9 / TRADE_BASELINE["us_households"]

    def get_trade_summary(self) -> dict:
        gross = self.estimate_static_revenue_effect(0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = self.estimate_income_payroll_offset()
        retaliation_exports = self.estimate_retaliation_cost()
        retaliation_revenue = (
            self.estimate_retaliation_revenue_loss() if self.include_retaliation else 0.0
        )
        net = gross - avoidance - offset - retaliation_revenue
        return {
            "gross_tariff_revenue": gross,
            # Retained key: several callers and tests read "tariff_revenue" as
            # the gross customs figure, which is what it has always been.
            "tariff_revenue": gross,
            "behavioral_offset": avoidance,
            "income_payroll_offset": offset,
            "retaliation_revenue_loss": retaliation_revenue,
            "net_revenue": net,
            "net_to_gross_ratio": net / gross if gross else 0.0,
            "consumer_cost": self.estimate_consumer_cost(),
            "retaliation_cost": retaliation_exports,
            "household_cost": self.get_household_impact(),
        }


def create_trump_universal_10() -> TariffPolicy:
    """10% on all imports outside the USMCA carve-out."""
    coverage = TRADE_BASELINE["universal_coverage_rate"]
    effective_base = TRADE_BASELINE["total_imports_billions"] * coverage
    return TariffPolicy(
        name="Trump Universal 10% Tariff",
        description=(
            "10% tariff on all imports outside the USMCA carve-out "
            "(~\\$2,349B base). Costs ~\\$1,700/household."
        ),
        tariff_rate_change=0.10,
        import_base_billions=effective_base,
        retaliation_export_base_billions=(
            TRADE_BASELINE["total_exports_billions"] * coverage
        ),
    )


def create_trump_china_60() -> TariffPolicy:
    """60% on Chinese goods, incremental over the duty already collected.

    Applied to the *whole* China base at the incremental rate rather than to
    half of it at a hand-set increment: a 60% tariff raises the rate on every
    Chinese good, by 60pp minus whatever Section 301 already collects on it,
    and Census puts that collected rate at 10.93% for 2024.
    """
    existing_tariff = TRADE_BASELINE["china_existing_avg_tariff"]
    return TariffPolicy(
        name="Trump 60% China Tariff",
        description=(
            "60% tariff on Chinese imports, incremental over the ~10.9% "
            "already collected (~\\$440B base)."
        ),
        tariff_rate_change=0.60 - existing_tariff,
        target_country="china",
        import_base_billions=TRADE_BASELINE["china_imports_billions"],
        retaliation_export_base_billions=TRADE_BASELINE["us_exports_to_china_billions"],
    )


def create_auto_tariff_25() -> TariffPolicy:
    """25% on imported vehicles and parts, less the USMCA share of the base."""
    return TariffPolicy(
        name="25% Auto Tariff",
        description=(
            "25% tariff on imported vehicles and parts outside the USMCA "
            "share of the base (~\\$199B of \\$385B)."
        ),
        tariff_rate_change=0.25 - TRADE_BASELINE["auto_existing_avg_tariff"],
        target_sector="autos",
        import_base_billions=(
            TRADE_BASELINE["auto_imports_billions"]
            * (1 - TRADE_BASELINE["auto_usmca_exempt_share"])
        ),
    )


def create_steel_tariff_25() -> TariffPolicy:
    """25% on steel and aluminium, net of the Section 232 duty in force.

    The base pays 3.06% today — far below the 25%/10% statutory Section 232
    rates, because Canada, Mexico and Australia were exempted and the EU, UK,
    Japan, Brazil and South Korea traded under quotas or product exclusions.
    That collected rate, not the statutory one, is what a proposed 25% is
    incremental to.
    """
    return TariffPolicy(
        name="25% Steel/Aluminum Tariff",
        description=(
            "25% tariff on steel and aluminium imports, incremental over the "
            "~3.1% Section 232 duty already collected (~\\$59B base)."
        ),
        tariff_rate_change=0.25 - TRADE_BASELINE["steel_aluminum_existing_avg_tariff"],
        target_sector="steel",
        import_base_billions=TRADE_BASELINE["steel_aluminum_imports_billions"],
    )


def create_reciprocal_tariffs() -> TariffPolicy:
    coverage = TRADE_BASELINE["reciprocal_coverage_rate"]
    return TariffPolicy(
        name="Reciprocal Tariffs",
        description=(
            "Match trading partners' tariff rates (~20pp average increase on "
            "half of goods imports)."
        ),
        tariff_rate_change=0.20,
        import_base_billions=TRADE_BASELINE["total_imports_billions"] * coverage,
        retaliation_export_base_billions=(
            TRADE_BASELINE["total_exports_billions"] * coverage
        ),
    )
