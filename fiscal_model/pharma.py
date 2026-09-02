"""
Pharmaceutical & Drug Pricing Revenue Module

Models revenue effects from pharmaceutical policy changes including:
1. Medicare drug price negotiation (IRA 2022 + expansion)
2. Part D redesign (out-of-pocket caps, manufacturer discounts)
3. Medicaid drug rebate reform
4. Importation and reference pricing

Everything here is an *incidence* model: a drug policy changes a price or a
cost-sharing rule, and only the part of that change the federal government
actually bears belongs in a budget score. Two rules follow, and both were
violated by the implementation this module replaces:

1. **A cost-sharing cap is not a saving.** Capping what a patient pays at the
   pharmacy counter does not reduce what the drug costs; it moves the same
   dollar onto the plan, and Medicare's subsidy of that plan means the federal
   budget picks most of it up. A $35/month insulin cap therefore *widens* the
   deficit. CBO scores exactly this policy at about +$11.4B over FY2022-2031
   (publication 57957: +$6.566B of outlays, -$4.793B of revenues). The previous
   code booked the whole retail-minus-cap differential for every insulin user as
   a federal saving and made that saving 2.5x larger when the cap was extended
   to private insurance, where the federal effect runs the other way.

2. **A price cap binds on brand molecules, at net prices, and saves the federal
   government only its share.** US unbranded generics are already *cheaper* than
   the OECD comparison, so referencing them abroad raises US prices rather than
   lowering them; US brand prices must be compared net of the rebates Medicare
   already collects; and roughly a quarter of Medicare drug cost is borne by
   beneficiaries, not the Treasury.

Key estimates:
- IRA drug negotiation: saves ~$237B/10yr (CBO 2022)
- Expanded negotiation (all drugs, earlier): could save $400-600B/10yr
- Part D $2,000 cap + manufacturer penalties: ~$70B/10yr
- $35/month insulin cost-sharing cap: a *cost*, not a saving (CBO 57957)

References (page-level transcriptions in
``data_files/pharma/drug_pricing_incidence.csv``):
- CBO (2022): IRA drug pricing provisions
- CBO (2022), publication 57957: H.R. 6833, the Affordable Insulin Now Act
- CBO (2019), publication 55936: H.R. 3, Lower Drug Costs Now Act
- RAND RR-A788-3 / HHS ASPE (2024): international drug price comparisons
- MedPAC (June 2023 ch. 2, March 2025 ch. 12): Part D rebates and financing
- HHS ASPE (December 2022): Report on the Affordability of Insulin
"""

from dataclasses import dataclass
from enum import Enum

from .policies import Policy, PolicyType


class DrugPricingReformType(Enum):
    MEDICARE_NEGOTIATION = "medicare_negotiation"
    PART_D_REDESIGN = "part_d_redesign"
    INSULIN_CAP = "insulin_cap"
    IMPORTATION = "importation"
    REFERENCE_PRICING = "reference_pricing"
    COMPREHENSIVE = "comprehensive"


# Baseline data.
#
# Every value below whose comment names a document is transcribed, with its
# page, in ``data_files/pharma/drug_pricing_incidence.csv``;
# ``tests/test_pharma_incidence.py`` pins this dict against that file so the
# two cannot drift. Nothing here is fitted to a validation benchmark.
PHARMA_BASELINE = {
    # --- Medicare drug spending levels -------------------------------------
    "medicare_part_d_spending_billions": 220.0,  # Annual *gross* Part D drug cost
    # Part B drugs are paid at ASP + 6%, and ASP is already net of most
    # manufacturer price concessions, so this base needs no rebate haircut.
    "medicare_part_b_drugs_billions": 55.0,
    "total_rx_spending_billions": 400.0,  # Total prescription drug spending
    "ira_negotiated_drugs_count": 20,  # IRA: 20 drugs by 2029
    "ira_10yr_savings_billions": 237.0,  # CBO estimate of IRA savings
    "additional_drug_productivity": 0.6,  # Additional drugs 60% as productive as first 20
    "exclusivity_delay_savings_pct": 0.3,  # Earlier negotiation captures ~30% more per drug

    # --- Gross-to-net and brand/generic split (MedPAC, June 2023, ch. 2) ----
    # Brands are over 80% of gross Part D spending (p. 7) and manufacturer
    # rebates average 23% of gross spending *including* generics, which
    # typically carry none (p. 12) — so brand spending net of rebates is
    # (0.80 - 0.23) of gross.
    "part_d_brand_share_of_gross": 0.80,
    "part_d_manufacturer_rebate_share_of_gross": 0.23,

    # --- International price comparison (RAND RR-A788-3 / ASPE, Feb 2024) ---
    # US brand-name originator prices as a multiple of prices in 33 OECD
    # comparison countries, 2022 data: 4.22 at gross manufacturer prices
    # (p. v), 3.08 after the report's own 37.2% US gross-to-net adjustment
    # (p. 19). Unbranded generics are 0.67 — the US is *cheaper* — which is why
    # only the brand base can produce reference-pricing savings. The gross and
    # generic ratios are recorded in the CSV rather than here: nothing reads
    # them, and this module has no room for another unread constant.
    "brand_price_ratio_to_intl_net": 3.08,

    # --- Federal share of Medicare drug cost --------------------------------
    # A price cut reduces total Part D program spending; Medicare bore
    # $112.1B of $147.0B of it in 2023 (MedPAC, March 2025, ch. 12, p. 409).
    "part_d_program_federal_share": 0.763,
    # A cost-sharing shift lands on plan bids instead; the direct subsidy and
    # reinsurance are designed to cover 74.5% of the basic benefit and enrollee
    # premiums the other 25.5% (MedPAC, March 2025, ch. 12, p. 7).
    "part_d_basic_benefit_federal_share": 0.745,
    # Part B: Medicare pays 80% of allowed charges and is 75% general-revenue
    # funded, enrollee premiums covering the rest.
    "part_b_drug_federal_share": 0.60,

    # --- Insulin (HHS ASPE, Report on the Affordability of Insulin, 2022) ---
    # Of 7.5M insulin users (MEPS 2019, p. 39):
    "insulin_medicare_user_share": 0.52,  # p. 39
    "insulin_private_user_share": 0.33,  # p. 39
    # Medicare enrollees and privately insured patients both paid an average of
    # $63 per insulin fill in 2019 (p. 12).
    "insulin_oop_per_fill_dollars": 63.0,
    # Part D beneficiaries would have saved $734M in 2020 under the IRA's
    # $35/month cap (p. 15). That is the amount shifted onto plans.
    "insulin_cap_reference_monthly_dollars": 35.0,
    "insulin_cap_reference_part_d_oop_relief_billions": 0.734,

    # --- Employer-premium tax offset (CBO budget option 58627) --------------
    # Average marginal income tax rate ~18% plus average marginal payroll rate
    # ~14% (both employer and employee shares) on compensation that employer
    # premiums displace.
    "esi_premium_revenue_offset": 0.32,
}

# Published scores this module is *compared against*. None of them is read by a
# scoring path, and none is a parameter: they exist so a reader can see what the
# module is trying to reconstruct.
#
# The former ``"insulin_cap": {"10yr_score": -6.4, "source": "CBO (2022)"}``
# entry was deleted rather than kept as an anchor. It was read by no code path,
# its attribution named no publication, and its sign contradicts the CBO
# estimate that *can* be sourced: publication 57957 scores a $35 cap extended to
# private plans at about +$11.4B of deficit, not -$6.4B of saving. The sourced
# figure now lives in ``data_files/pharma/drug_pricing_incidence.csv`` with its
# page reference, and is quoted in ``_estimate_insulin_cap_deficit_effect``.
CBO_PHARMA_ESTIMATES = {
    "ira_drug_negotiation": {
        "10yr_score": -237.0,
        "source": "CBO (2022)",
        "description": "IRA Medicare drug price negotiation (10 Part D + 10 Part B drugs)",
    },
    "expanded_negotiation": {
        "10yr_score": -500.0,
        "source": "CBO/Estimate",
        "description": "Expand negotiation to all Medicare drugs, remove exclusivity delays",
    },
}


@dataclass
class DrugPricingPolicy(Policy):
    """
    Pharmaceutical pricing policy.

    Models savings from drug pricing reforms, which primarily affect
    the spending side (reducing Medicare/Medicaid outlays) rather than
    the revenue side.

    Not modelled: **the Part D annual out-of-pocket cap** (the IRA's $2,000
    limit and any change to it). It has the same incidence as the insulin cap —
    liability moves from the beneficiary to plans, and Medicare's basic-benefit
    subsidy picks up most of it — but no published per-beneficiary shift
    comparable to ASPE's $734M insulin figure has been transcribed for it. An
    ``oop_cap`` field used to sit here, declared and read by nothing, so a
    caller could set it and get a silent no-op; it is gone rather than left as
    a lever that does nothing. Adding the mechanism means adding a sourced
    shift, not restoring the field.
    """
    reform_type: DrugPricingReformType = DrugPricingReformType.COMPREHENSIVE

    # Medicare negotiation
    expand_negotiation: bool = False  # Expand beyond IRA 2022
    negotiation_drug_count: int = 20  # Number of drugs subject to negotiation
    negotiation_discount_pct: float = 0.25  # Average discount from negotiation
    include_part_b: bool = True  # Include Part B drugs
    remove_exclusivity_delay: bool = False  # Remove 9/13 year delay for small molecule/biologic

    # Part D redesign
    manufacturer_discount_pct: float = 0.0  # Mandatory manufacturer discount

    # Insulin
    insulin_cap_monthly: float | None = None  # Monthly insulin price cap
    extend_to_private: bool = False  # Extend insulin cap to private insurance

    # International reference pricing
    reference_pricing: bool = False
    reference_price_target_pct: float = 1.20  # Target: 120% of international average

    # Innovation offset (higher prices → less R&D → fewer drugs)
    innovation_offset_pct: float = 0.05  # 5% of savings lost to reduced innovation

    def __post_init__(self):
        self.policy_type = PolicyType.MANDATORY_SPENDING
        super().__post_init__()

    def estimate_cost_effect(self, baseline_cost: float = 0.0) -> float:
        """
        Estimate the annual federal deficit effect of a drug pricing reform.

        Returns a deficit effect: negative reduces the deficit (a saving),
        positive widens it.

        The innovation offset applies only to the channels that reduce what a
        manufacturer is paid — negotiation, mandatory manufacturer discounts and
        reference pricing. A cost-sharing cap moves a dollar from the patient to
        the plan without touching manufacturer revenue, so it cannot deter R&D
        and carries no offset.
        """
        price_reducing_savings = (
            self._estimate_negotiation_savings()
            + self._estimate_part_d_savings()
            + self._estimate_reference_pricing_savings()
        )
        price_reducing_savings *= (1 - self.innovation_offset_pct)

        return -price_reducing_savings + self._estimate_insulin_cap_deficit_effect()

    def _estimate_negotiation_savings(self) -> float:
        """Savings from Medicare drug price negotiation."""
        if not self.expand_negotiation and self.negotiation_drug_count <= 20:
            return 0.0  # IRA baseline already in law

        base = PHARMA_BASELINE

        # IRA covers 20 drugs saving ~$24B/year at steady state
        ira_per_drug = base["ira_10yr_savings_billions"] / 10 / 20  # ~$1.2B per drug

        # Additional drugs beyond IRA 20
        additional_drugs = max(0, self.negotiation_drug_count - 20)

        # Diminishing returns: highest-spend drugs negotiated first
        if additional_drugs > 0:
            # First 20 drugs cover ~50% of Part D spending
            # Next 30 cover ~25%, etc.
            additional_savings = additional_drugs * ira_per_drug * base["additional_drug_productivity"]
        else:
            additional_savings = 0.0

        # Removing exclusivity delay
        delay_savings = 0.0
        if self.remove_exclusivity_delay:
            # Earlier negotiation captures 2-3 more years of savings per drug
            delay_savings = self.negotiation_drug_count * ira_per_drug * base["exclusivity_delay_savings_pct"]

        return additional_savings + delay_savings

    def _estimate_part_d_savings(self) -> float:
        """Savings from Part D redesign."""
        savings = 0.0

        if self.manufacturer_discount_pct > 0:
            part_d = PHARMA_BASELINE["medicare_part_d_spending_billions"]
            savings += part_d * self.manufacturer_discount_pct

        return savings

    def _estimate_insulin_cap_deficit_effect(self) -> float:
        """Federal deficit effect of an insulin cost-sharing cap, $B per year.

        Positive widens the deficit, which is the direction a cap runs. A
        $35/month cap is a *cost-sharing* cap, not a price cap: it changes
        nothing about what a plan or a manufacturer is paid for insulin, only
        how much of that the patient hands over at the counter. Every dollar the
        patient stops paying is picked up by someone else, and the federal
        budget takes a share of it through two channels.

        **Medicare Part D.** Cost sharing that comes off the beneficiary lands
        on the plan and raises plan bids. Medicare's direct subsidy and
        reinsurance are designed to cover 74.5% of the basic benefit, enrollee
        premiums the remaining 25.5% (MedPAC, *Report to the Congress: Medicare
        Payment Policy*, March 2025, ch. 12, p. 7), so the federal government
        picks up 74.5 cents of every dollar shifted. HHS ASPE estimates that
        Part D beneficiaries would have saved **$734 million** in 2020 had the
        IRA's $35-per-month cap been in force (*Report on the Affordability of
        Insulin*, December 2022, p. 15) — that is the amount shifted. Enrollees
        receiving the low-income subsidy already pay nominal copays far below
        $35 and are inside ASPE's estimate, so no separate exclusion is needed.

        **Private insurance.** Extending the cap to private plans shifts cost
        onto premiums rather than onto the Treasury directly. It reaches the
        federal budget through the exclusion of employer premiums from taxable
        compensation: CBO puts the average marginal income tax rate on that
        compensation at about 18% and the average marginal payroll rate at about
        14% (*Reduce Tax Subsidies for Employment-Based Health Insurance*,
        budget option 58627), so about 32 cents of each shifted dollar returns
        as forgone revenue. That is a revenue loss, booked here on the module's
        one available line; the deficit effect is identical either way.

        Cross-check: CBO scores a $35 cap extended to private plans at +$6.566B
        of outlays and -$4.793B of revenues over FY2022-2031 — about **+$11.4B
        of deficit** (publication 57957). This identity reproduces the sign and
        the order of magnitude. It does not reproduce the level, and two omitted
        channels explain most of the gap: induced utilisation (cheaper insulin
        at the counter is used more, raising plan and federal cost), and growth
        in insulin cost and enrolment across a ten-year window, since ASPE's
        $734M is a single 2020 figure held flat here.

        What this replaces: the previous implementation credited the entire
        retail-minus-cap differential, ($6,000 - $420) for each of 8.4M insulin
        users, to the federal budget — and *raised* that saving 2.5x when the
        cap was extended to private insurance, the one place where the federal
        effect is smallest and runs the other way.
        """
        if self.insulin_cap_monthly is None:
            return 0.0

        base = PHARMA_BASELINE
        oop_per_fill = base["insulin_oop_per_fill_dollars"]
        reference_cap = base["insulin_cap_reference_monthly_dollars"]

        # A cap at or above the average out-of-pocket cost per fill binds on
        # nobody at the average and shifts nothing.
        if self.insulin_cap_monthly >= oop_per_fill:
            return 0.0

        # Scale ASPE's $35-cap estimate to the cap actually being modelled. The
        # amount shifted is the cost sharing sitting above the cap, so it rises
        # linearly as the cap falls from the average cost per fill toward zero.
        scale = (oop_per_fill - self.insulin_cap_monthly) / (oop_per_fill - reference_cap)
        medicare_oop_shift = (
            base["insulin_cap_reference_part_d_oop_relief_billions"] * scale
        )
        federal_effect = medicare_oop_shift * base["part_d_basic_benefit_federal_share"]

        if self.extend_to_private:
            # ASPE finds Medicare and privately insured patients paid the same
            # average $63 per insulin fill in 2019 (p. 12), so the privately
            # insured shift scales with their share of insulin users — 33%
            # against Medicare's 52% (p. 39).
            private_shift = medicare_oop_shift * (
                base["insulin_private_user_share"] / base["insulin_medicare_user_share"]
            )
            federal_effect += private_shift * base["esi_premium_revenue_offset"]

        return federal_effect

    def _estimate_reference_pricing_savings(self) -> float:
        """Federal savings from international reference pricing, $B per year.

        Three things have to line up for this identity to mean anything, and the
        implementation this replaces got each of them wrong — it applied a
        gross, all-drug price ratio to a net, all-drug spending base and booked
        the whole result as a federal outlay reduction.

        **Brand molecules only.** RAND's headline ratio is an all-drug figure
        that hides two opposite findings: US brand-name originator prices were
        422% of prices in 33 OECD comparison countries in 2022, while US
        unbranded generics — 90% of US prescription volume — were 67%, i.e.
        *cheaper* (RAND RR-A788-3 / ASPE, *International Prescription Drug Price
        Comparisons: Estimates Using 2022 Data*, February 2024, p. v).
        Referencing generics abroad would raise US prices. Only brand spending
        can yield savings, so only brand spending is in the base.

        **A net-price ratio against a net-price base.** RAND's own gross-to-net
        adjustment (a 37.2% reduction to retail-dispensed US brand prices)
        leaves brand prices at 308% of comparison-country prices (p. 19), and
        that is the ratio a cap on *net* prices has to close. The base is
        matched to it: manufacturer rebates average 23% of gross Part D spending
        against a brand share of over 80% (MedPAC, June 2023, ch. 2, pp. 7 and
        12), so brand spending net of rebates is (0.80 - 0.23) of gross. Part B
        drugs are paid at ASP, already a net price, and are predominantly
        single-source brands and biologics, so they enter unadjusted.

        **The federal share.** Medicare drug spending is not a federal outlay in
        full. Medicare bore $112.1B of $147.0B of Part D program cost in 2023
        (MedPAC, March 2025, ch. 12, p. 409); the rest is enrollee premiums and
        cost sharing, which a price cut also reduces but which never touched the
        Treasury. Part B pays 80% of allowed charges and is 75% general-revenue
        funded.

        Cross-check: the implied cut in US net brand prices, 3.08 -> 1.20 or
        about 61%, sits close to the roughly 55% average net-price reduction CBO
        estimated for the first group of drugs negotiated under H.R. 3's cap at
        120% of the average international market price; CBO scored that title,
        which reached a limited set of drugs rather than the whole Medicare
        book, at about $456B over 2020-2029 (publication 55936).

        Known limitation, deliberately not parameterised: RAND's index is
        computed on presentations sold in *both* markets, and the overlap is
        well under 100% of US sales bilaterally. This applies the index to all
        brand spending, so it overstates the base a real reference-pricing rule
        could reach.
        """
        if not self.reference_pricing:
            return 0.0

        base = PHARMA_BASELINE
        current_ratio = base["brand_price_ratio_to_intl_net"]
        target_ratio = self.reference_price_target_pct

        if target_ratio >= current_ratio:
            return 0.0

        # Reduction as a fraction of current net brand spending.
        price_reduction = 1 - (target_ratio / current_ratio)

        part_d_brand_net = base["medicare_part_d_spending_billions"] * (
            base["part_d_brand_share_of_gross"]
            - base["part_d_manufacturer_rebate_share_of_gross"]
        )
        part_b_net = base["medicare_part_b_drugs_billions"]

        return (
            part_d_brand_net * price_reduction * base["part_d_program_federal_share"]
            + part_b_net * price_reduction * base["part_b_drug_federal_share"]
        )


# Factory functions

def create_expand_drug_negotiation() -> DrugPricingPolicy:
    """Expand Medicare drug negotiation beyond IRA."""
    return DrugPricingPolicy(
        name="Expand Drug Negotiation",
        description="Negotiate 50 drugs (vs IRA's 20), remove exclusivity delays. Estimated: -\\$500B/10yr.",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.MEDICARE_NEGOTIATION,
        expand_negotiation=True,
        negotiation_drug_count=50,
        remove_exclusivity_delay=True,
        include_part_b=True,
    )

def create_insulin_cap_all() -> DrugPricingPolicy:
    """$35 insulin cap for all Americans."""
    return DrugPricingPolicy(
        name="Universal Insulin Cap ($35)",
        description="\\$35/month insulin cap for Medicare and private insurance. Estimated: -\\$15B/10yr.",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.INSULIN_CAP,
        insulin_cap_monthly=35.0,
        extend_to_private=True,
    )

def create_reference_pricing() -> DrugPricingPolicy:
    """International reference pricing for Medicare drugs."""
    return DrugPricingPolicy(
        name="International Reference Pricing",
        description="Cap Medicare drug prices at 120% of international average (OECD). Estimated: -\\$100B/10yr.",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.REFERENCE_PRICING,
        reference_pricing=True,
        reference_price_target_pct=1.20,
    )

def create_comprehensive_pharma_reform() -> DrugPricingPolicy:
    """Comprehensive drug pricing reform package."""
    return DrugPricingPolicy(
        name="Comprehensive Drug Pricing Reform",
        description="Expanded negotiation + insulin cap + manufacturer discounts. Estimated: -\\$600B/10yr.",
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.COMPREHENSIVE,
        expand_negotiation=True,
        negotiation_drug_count=50,
        remove_exclusivity_delay=True,
        insulin_cap_monthly=35.0,
        extend_to_private=True,
        manufacturer_discount_pct=0.10,
    )


PHARMA_VALIDATION_SCENARIOS = {
    "ira_drug_negotiation": {
        "description": "IRA drug negotiation baseline",
        "expected_10yr": -237.0,
        "source": "CBO (2022)",
    },
    "expanded_negotiation": {
        "description": "Expand to 50 drugs",
        "expected_10yr": -500.0,
        "source": "Estimate",
    },
}
