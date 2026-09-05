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
violated by the implementation lane L7 replaced:

1. **A cost-sharing cap is not a saving.** Capping what a patient pays at the
   pharmacy counter does not reduce what the drug costs; it moves the same
   dollar onto the plan, and Medicare's subsidy of that plan means the federal
   budget picks most of it up. A $35/month insulin cap therefore *widens* the
   deficit. CBO scores exactly this policy at about +$11.4B over FY2022-2031
   (publication 57957: +$6.566B of outlays, -$4.793B of revenues).

2. **A price cap binds on brand molecules, at net prices, and saves the federal
   government only its share.** US unbranded generics are already *cheaper* than
   the OECD comparison, so referencing them abroad raises US prices rather than
   lowering them; US brand prices must be compared net of the rebates Medicare
   already collects; and roughly a quarter of Medicare drug cost is borne by
   beneficiaries, not the Treasury.

Lane W4-pharma (``planning/lanes/W4_pharma_part_d.md``) added the third rule the
first two imply:

3. **"The federal share" is three channels, and the 2025 redesign moved cost
   between them.** Medicare pays for Part D through a capitated *direct
   subsidy*, cost-based *reinsurance* on the catastrophic phase, and the
   *low-income subsidy*. Until 2025 reinsurance covered 80 percent of
   catastrophic-phase cost and was 43 cents of every program dollar; the IRA cut
   it to 20 percent for brands and 40 percent for generics and pushed the
   difference onto plan bids and so onto the direct subsidy. Every score in this
   repository runs over 2025-2034, so the channels are weighted on the
   redesigned benefit, not on the 2023 outturn. See
   :func:`part_d_federal_channels`.

Key estimates:
- IRA drug negotiation: about $100B/10yr for the negotiation program itself
  (CBO, quoted by HHS in CMS's 15 August 2024 release); the frequently quoted
  $237B is CBO's score of the IRA's *entire* drug-pricing title
- Expanded negotiation: adding molecules runs down a steep concentration curve
- Part D $2,000 out-of-pocket cap: a *cost*, not a saving, on the same incidence
  as the insulin cap
- $35/month insulin cost-sharing cap: a *cost*, not a saving (CBO 57957)

References (page-level transcriptions in
``data_files/pharma/drug_pricing_incidence.csv``):
- CBO (2022), publication 57957: H.R. 6833, the Affordable Insulin Now Act
- CBO (2019), publication 55936: H.R. 3, Lower Drug Costs Now Act
- CMS press releases, 15 August 2024 and 17 January 2025: the Medicare Drug
  Price Negotiation Program's selection schedule, selected-drug spending and
  first-cycle savings
- RAND RR-A788-3 / HHS ASPE (2024): international drug price comparisons
- MedPAC (June 2023 ch. 2, March 2025 ch. 12): Part D rebates and financing
- HHS ASPE (December 2022): Report on the Affordability of Insulin
- HHS ASPE (January 2025, HP-2025-02): the Part D redesign's out-of-pocket cap
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

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
# Every value below is transcribed, with its page, in
# ``data_files/pharma/drug_pricing_incidence.csv``;
# ``tests/test_pharma_incidence.py`` pins this dict against that file so the
# two cannot drift. Nothing here is fitted to a validation benchmark.
PHARMA_BASELINE = {
    # --- Medicare drug spending levels -------------------------------------
    # Total *gross* covered prescription drug costs under Part D. CMS: the ten
    # drugs selected for 2026 "accounted for $56.2 billion in total Medicare
    # spending, or about 20 percent of total Part D gross spending in 2023"
    # (press release, 15 August 2024), i.e. about $281B. This replaces an
    # unsourced 220.0, which the negotiation ladder below contradicts: current
    # law's own cumulative selections reach $257B of gross spending by 2034.
    "medicare_part_d_gross_spending_billions": 281.0,
    # Part B drugs are paid at ASP + 6%, and ASP is already net of most
    # manufacturer price concessions, so this base needs no rebate haircut.
    # MedPAC: fee-for-service Medicare and its beneficiaries spent about $54B on
    # separately paid Part B drugs in 2023 (July 2025 Data Book, section 10,
    # chart 10-1). This replaces an unsourced 55.0.
    "medicare_part_b_drugs_billions": 54.0,

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
    # only the brand base can produce reference-pricing savings.
    "brand_price_ratio_to_intl_net": 3.08,
    # How much of the US brand book the index actually reaches. RAND compares
    # only presentations sold in *both* markets. For the combined 33-country
    # comparison the matched presentations are 90.2% of US sales (Table A.4,
    # p. 36); brand-name originators are 84% of the sales that contribute
    # (Table A.6, p. 38) against 87% of all US sales (Table 2.2, p. 12).
    "rand_us_sales_share_in_comparison": 0.902,
    "rand_brand_share_of_contributing_us_sales": 0.84,
    "rand_brand_share_of_all_us_sales": 0.87,

    # --- Part D federal channels, level (MedPAC, March 2025, ch. 12) --------
    # Table 12-5 (p. 432) and p. 409: Medicare's 2023 Part D payments were
    # $4.9B of capitated direct subsidy, $63.3B of cost-based reinsurance and
    # $43.9B of low-income subsidy, against $128.2B of plan payments plus
    # $18.8B of enrollee cost sharing; enrollees paid $16.1B of basic premiums.
    "part_d_direct_subsidy_billions_2023": 4.9,
    "part_d_reinsurance_billions_2023": 63.3,
    "part_d_low_income_subsidy_billions_2023": 43.9,
    "part_d_enrollee_premiums_billions_2023": 16.1,
    "part_d_enrollee_cost_sharing_billions_2023": 18.8,

    # --- Part D federal channels, 2025 redesign weights (same chapter) ------
    # Per enrollee per month for the 2025 benefit year, after the IRA cut
    # catastrophic-phase reinsurance from 80% to 20% (brand) / 40% (generic)
    # and the 6% cap on the base beneficiary premium pushed the difference onto
    # the capitated direct subsidy (Table 12-2 p. 424, quoted p. 421).
    "part_d_direct_subsidy_pmpm_2025": 142.67,
    "part_d_reinsurance_pmpm_2025": 40.08,
    "part_d_base_beneficiary_premium_2025": 36.78,

    # --- Statutory subsidy shares ------------------------------------------
    # A cost-sharing shift lands on plan bids; the direct subsidy and
    # reinsurance are designed to cover 74.5% of the basic benefit and enrollee
    # premiums the other 25.5% (MedPAC, March 2025, ch. 12, p. 418).
    "part_d_basic_benefit_federal_share": 0.745,
    # Part B: Medicare pays 80% of allowed charges and is 75% general-revenue
    # funded, enrollee premiums covering the rest.
    "part_b_drug_federal_share": 0.60,

    # --- Medicare Drug Price Negotiation Program (CMS) ----------------------
    # Three selection cycles, each published with the drugs' total gross
    # Medicare drug spending over an annual window. They are the only public
    # measurement of how fast the spending ladder falls away as the negotiated
    # set is extended: $5.62B, $2.73B and $1.80B of gross spending per molecule.
    "negotiation_cycle1_drugs": 10,
    "negotiation_cycle1_gross_billions": 56.2,
    "negotiation_cycle2_drugs": 15,
    "negotiation_cycle2_gross_billions": 41.0,
    "negotiation_cycle3_drugs": 15,
    "negotiation_cycle3_gross_billions": 27.0,
    # "If the new prices had been in effect in 2023, they would have saved an
    # estimated $6 billion in net covered prescription drug costs, or
    # approximately 22 percent, across the 10 selected drugs" (CMS, 17 January
    # 2025). $6B against the same drugs' $56.2B of gross spending is the
    # observed saving per gross dollar, and it needs no separate assumption
    # about the gross-to-net ratio or the negotiated discount, because CMS
    # published their product.
    "negotiation_cycle1_saving_billions": 6.0,
    # The IRA's steady-state cap: "up to 20 more Part B or Part D drugs for each
    # year after" 2028 (CMS, 15 August 2024).
    "ira_annual_selection_cap": 20,

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

    # --- Part D annual out-of-pocket cap (HHS ASPE, HP-2025-02, Jan 2025) ---
    # 11.3 million enrollees are projected to reach the IRA's $2,000 cap in
    # 2025 with total out-of-pocket savings of $7.2B (Table 2B, p. 7). That is
    # the amount the cap shifts off beneficiaries and onto plan liability. In
    # the absence of the IRA the same enrollees would have paid about $14.3B
    # (Table 2A, p. 6), which is what a cap of $0 would shift.
    "part_d_oop_cap_reference_dollars": 2000.0,
    "part_d_oop_cap_reference_relief_billions": 7.2,
    "part_d_oop_cap_baseline_out_of_pocket_billions": 14.3,

    # --- Drug availability response (CBO) ----------------------------------
    # Lower expected returns deter development, so a price-reducing policy
    # shrinks the brand book it is applied to. CBO has published a drug-count
    # figure for each of the two policies this module scores, and they differ by
    # more than an order of magnitude, so one blanket constant cannot stand for
    # both.
    #
    # Negotiation: under the enacted IRA, "the number of drugs that would be
    # introduced to the U.S. market would be reduced by about 1 over the
    # 2023-2032 period, about 5 over the subsequent decade, and about 7 over the
    # decade after that" — 13 of about 1,300 over thirty years, 1 percent (CBO,
    # Summary: Estimated Budgetary Effects of Public Law 117-169, 7 September
    # 2022, p. 15). One drug against a decade's share of that 1,300 is the
    # first-decade rate.
    "cbo_ira_fewer_drugs_first_decade": 1.0,
    "cbo_thirty_year_new_drugs": 1300.0,
    # International reference pricing: for H.R. 3's cap at 120% of the average
    # international market price, "a reduction in revenues of $0.5 trillion to
    # $1 trillion would lead to a reduction of approximately 8 to 15 new drugs
    # coming to market over the next 10 years", against CBO's own denominator
    # of about 30 approvals a year, "suggesting that about 300 drugs might be
    # approved over the next 10 years" (CBO, letter to Chairman Pallone,
    # 11 October 2019, publication 55722). The midpoint of CBO's own range.
    "cbo_hr3_fewer_drugs_first_decade": 11.5,
    "cbo_hr3_first_decade_new_drugs": 300.0,

    # --- Employer-premium tax offset (CBO budget option 58627) --------------
    # Average marginal income tax rate ~18% plus average marginal payroll rate
    # ~14% (both employer and employee shares) on compensation that employer
    # premiums displace.
    "esi_premium_revenue_offset": 0.32,
}


#: New selections by initial price applicability year under current law: 10 for
#: 2026, up to 15 more for 2027, up to 15 more for 2028, and up to 20 more for
#: each year after that (CMS press release, 15 August 2024). The negotiated set
#: is cumulative, so current law reaches 160 molecules by 2034 — not the "20
#: drugs" the module used to assume.
IRA_SELECTION_SCHEDULE: dict[int, int] = {2026: 10, 2027: 15, 2028: 15}

#: The first applicability year governed by the statute's standing annual cap
#: rather than by its fixed opening schedule.
IRA_STEADY_STATE_YEAR = max(IRA_SELECTION_SCHEDULE) + 1


def part_d_federal_channels() -> dict[str, float]:
    """Federal share of a $1 reduction in Part D program cost, by channel.

    Medicare pays for Part D through three channels and a drug-price change
    reaches the Treasury through all of them:

    - **Direct subsidy.** A capitated monthly payment set as a share of the
      national average plan bid. Lower drug cost lowers bids, and Medicare
      picks up its share of that.
    - **Reinsurance.** A cost-based payment on spending above the annual
      out-of-pocket threshold. From 2025 it covers 20 percent of
      catastrophic-phase cost for brands and 40 percent for generics, down from
      80 percent (MedPAC, March 2025, ch. 12, Figure 12-1, p. 420).
    - **Low-income subsidy.** Medicare pays most or all of the cost sharing and
      premiums of the quarter of enrollees who qualify.

    The weights are built in two steps, both from MedPAC's March 2025 Part D
    chapter. First the level: of the $147.0B universe the chapter reports for
    2023 ($128.2B of plan payments plus $18.8B of enrollee cost sharing, p.
    409), the basic-benefit block — direct subsidy $4.9B, reinsurance $63.3B,
    enrollee premiums $16.1B (Table 12-5, p. 432) — is 57.3 percent, the
    low-income subsidy 29.9 percent and enrollee cost sharing 12.8 percent.

    Then the redesign: 2023 was the last full year of the old benefit, in which
    reinsurance was 43 cents of every program dollar. MedPAC publishes the
    redesigned split for 2025 in per-enrollee-per-month terms — direct subsidy
    $142.67, reinsurance $40.08, base beneficiary premium $36.78 (Table 12-2,
    p. 424) — and the basic-benefit block is re-split on those shares.

    The result is that the redesign moves cost *between* the two Medicare
    channels without changing the federal total much: reinsurance falls from
    0.431 of the universe to 0.105 and the direct subsidy rises from 0.033 to
    0.373, because the IRA's 6 percent cap on the base beneficiary premium
    forces the direct subsidy up by nearly what reinsurance loses. The federal
    total is 0.776 against the 0.763 the 2023 outturn gives directly.

    Known limitation, deliberately not adjusted: the redesign also moves cost
    sharing onto plans through the $2,000 out-of-pocket cap, which raises the
    basic-benefit block and shrinks the 12.8 percent cost-sharing block. MedPAC
    publishes no post-redesign split of that, so the 2023 blocks are held. The
    omission biases the federal share *down*, since cost sharing is the one
    block with no federal channel in it at all.
    """
    base = PHARMA_BASELINE
    direct_2023 = base["part_d_direct_subsidy_billions_2023"]
    reinsurance_2023 = base["part_d_reinsurance_billions_2023"]
    lis_2023 = base["part_d_low_income_subsidy_billions_2023"]
    premiums_2023 = base["part_d_enrollee_premiums_billions_2023"]
    cost_sharing_2023 = base["part_d_enrollee_cost_sharing_billions_2023"]

    universe = (
        direct_2023 + reinsurance_2023 + lis_2023 + premiums_2023 + cost_sharing_2023
    )
    basic_block = (direct_2023 + reinsurance_2023 + premiums_2023) / universe

    direct_pmpm = base["part_d_direct_subsidy_pmpm_2025"]
    reinsurance_pmpm = base["part_d_reinsurance_pmpm_2025"]
    premium_pmpm = base["part_d_base_beneficiary_premium_2025"]
    basic_pmpm = direct_pmpm + reinsurance_pmpm + premium_pmpm

    return {
        "direct_subsidy": basic_block * direct_pmpm / basic_pmpm,
        "reinsurance": basic_block * reinsurance_pmpm / basic_pmpm,
        "low_income_subsidy": lis_2023 / universe,
    }


def negotiation_availability_response() -> float:
    """Share of negotiation savings lost to drugs that never reach the market.

    CBO's own figure for the enacted IRA: about **1** fewer drug introduced over
    2023-2032, out of about **1,300** expected over thirty years (*Summary:
    Estimated Budgetary Effects of Public Law 117-169*, 7 September 2022, p. 15).
    A decade's share of that denominator is the base a first-decade count is a
    fraction of. The result — a little over two-tenths of one percent — is small,
    and CBO says so in terms: 13 of 1,300 over thirty years is "a reduction of
    1%".
    """
    base = PHARMA_BASELINE
    per_decade = base["cbo_thirty_year_new_drugs"] / 3.0
    return base["cbo_ira_fewer_drugs_first_decade"] / per_decade


def reference_pricing_availability_response() -> float:
    """Share of reference-pricing savings lost to drugs that never launch.

    CBO scored exactly this policy design. For H.R. 3's cap at 120% of the
    average international market price, CBO put the revenue reduction to
    manufacturers at $0.5-1 trillion and concluded it "would lead to a reduction
    of approximately 8 to 15 new drugs coming to market over the next 10 years",
    against about 300 approvals expected in that decade (letter to Chairman
    Pallone, 11 October 2019, publication 55722). The midpoint of CBO's range
    over CBO's denominator is 3.8 percent — an order of magnitude above the
    negotiation figure, which is why the two channels no longer share one
    constant.
    """
    base = PHARMA_BASELINE
    return (
        base["cbo_hr3_fewer_drugs_first_decade"]
        / base["cbo_hr3_first_decade_new_drugs"]
    )


def part_d_federal_share() -> float:
    """Sum of :func:`part_d_federal_channels` — Medicare's share of a Part D
    drug-cost reduction under the 2025 benefit design."""
    return sum(part_d_federal_channels().values())


@lru_cache(maxsize=1)
def negotiation_spending_ladder() -> tuple[float, float]:
    """``(scale, exponent)`` of gross Medicare drug spending by selection rank.

    CMS has now run three selection cycles and published, for each, the total
    gross Medicare drug spending of the molecules it picked:

    ==========  ======  =======================  ==================
    Cycle       Drugs   Gross spending           Per molecule
    ==========  ======  =======================  ==================
    IPAY 2026   10      $56.2B (calendar 2023)   $5.62B
    IPAY 2027   15      $41B (Nov 23 - Oct 24)   $2.73B
    IPAY 2028   15      $27B (Nov 24 - Oct 25)   $1.80B
    ==========  ======  =======================  ==================

    Because CMS selects in descending order of spending among eligible drugs,
    those three points are a measured rank-size curve. A least-squares line
    through them in logs gives spending at rank ``r`` of ``scale * r ** -alpha``
    with alpha near 0.63, reproducing all three cycles to within 2 percent. That
    curve is what replaces the module's former constant per-drug average, which
    said the 200th molecule was worth as much as the 5th.

    Three things it does not capture, all stated rather than parameterised:
    CMS selects from *negotiation-eligible* drugs, so the ranks are spending
    ranks within a statutorily restricted pool; the third cycle's denominator is
    Part B and Part D together while the first two are Part D alone; and a fit
    through three points has no standard error worth quoting.
    """
    base = PHARMA_BASELINE
    cycles = (
        (base["negotiation_cycle1_drugs"], base["negotiation_cycle1_gross_billions"]),
        (base["negotiation_cycle2_drugs"], base["negotiation_cycle2_gross_billions"]),
        (base["negotiation_cycle3_drugs"], base["negotiation_cycle3_gross_billions"]),
    )

    ranks: list[float] = []
    spend: list[float] = []
    start = 0
    for count, gross in cycles:
        # The cycle's mean selection rank stands for the cycle.
        ranks.append(start + (count + 1) / 2)
        spend.append(gross / count)
        start += count

    xs = [math.log(r) for r in ranks]
    ys = [math.log(s) for s in spend]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sum(
        (x - mean_x) ** 2 for x in xs
    )
    scale = math.exp(mean_y - slope * mean_x)
    return scale, -slope


def negotiated_gross_spending(molecules: float) -> float:
    """Annual gross Medicare drug spending on the top ``molecules`` by rank."""
    if molecules <= 0:
        return 0.0
    scale, exponent = negotiation_spending_ladder()
    return sum(scale * rank ** -exponent for rank in range(1, int(molecules) + 1))


def current_law_negotiated_molecules(year: int) -> int:
    """Cumulative molecules with a negotiated price in ``year`` under the IRA."""
    first = min(IRA_SELECTION_SCHEDULE)
    if year < first:
        return 0
    total = 0
    for applicability_year in range(first, year + 1):
        total += IRA_SELECTION_SCHEDULE.get(
            applicability_year, PHARMA_BASELINE["ira_annual_selection_cap"]
        )
    return total


@dataclass
class DrugPricingPolicy(Policy):
    """
    Pharmaceutical pricing policy.

    Models savings from drug pricing reforms, which primarily affect
    the spending side (reducing Medicare/Medicaid outlays) rather than
    the revenue side.

    Not modelled: **the exclusivity delay itself.** The IRA bars a molecule from
    selection until 7 years after approval (11 for biologics), and an
    ``remove_exclusivity_delay`` field used to book an unsourced 30 percent
    bonus for repealing it. Under a statutory cap on *selections per year* the
    delay changes which molecules are negotiated, not how many, and no published
    figure prices that composition shift. What the delay does do is bound how
    fast the negotiated set can grow, and that is the job the flag now has: see
    :meth:`_negotiation_selections_per_year`.

    Also gone: ``include_part_b``. It was declared, defaulted to ``True`` and
    read by nothing, in either the old negotiation identity or the new one, so a
    caller could switch it and get a silent no-op. The negotiated set is now
    priced off CMS's own selection cycles, whose third round covers Part B and
    Part D together, and the module has no published way to split that ladder by
    part. Restoring the field means finding that split, not re-declaring it.
    """
    reform_type: DrugPricingReformType = DrugPricingReformType.COMPREHENSIVE

    # Medicare negotiation
    expand_negotiation: bool = False  # Expand beyond IRA 2022
    negotiation_drug_count: int = 20  # Molecules selected per applicability year
    remove_exclusivity_delay: bool = False  # Lift the 7/11-year eligibility bar

    # Part D redesign
    manufacturer_discount_pct: float = 0.0  # Mandatory manufacturer discount
    oop_cap: float | None = None  # Annual out-of-pocket cap, dollars

    # Insulin
    insulin_cap_monthly: float | None = None  # Monthly insulin price cap
    extend_to_private: bool = False  # Extend insulin cap to private insurance

    # International reference pricing
    reference_pricing: bool = False
    reference_price_target_pct: float = 1.20  # Target: 120% of international average

    # Drug availability response (lower expected returns → fewer launches).
    # ``None`` means each price-reducing channel uses CBO's own published figure
    # for the policy it scored; a number overrides both with one value.
    innovation_offset_pct: float | None = None

    def __post_init__(self):
        self.policy_type = PolicyType.MANDATORY_SPENDING
        super().__post_init__()

    def estimate_cost_effect(self, baseline_cost: float = 0.0) -> float:
        """
        Estimate the annual federal deficit effect of a drug pricing reform.

        Returns a deficit effect: negative reduces the deficit (a saving),
        positive widens it.

        The availability response applies only to the channels that reduce what
        a manufacturer is paid — negotiation, mandatory manufacturer discounts
        and reference pricing. A cost-sharing cap moves a dollar from the
        patient to the plan without touching manufacturer revenue, so it cannot
        deter development and carries none.

        It is applied **per channel**, because CBO published a different figure
        for each of the two policies: about 1 fewer drug in the first decade
        under the IRA's negotiation program against 8 to 15 under H.R. 3's
        international reference cap. The single unsourced 5 percent this
        replaces stood between them and was attached to neither. See
        :func:`negotiation_availability_response` and
        :func:`reference_pricing_availability_response`.
        """
        negotiation_offset = (
            negotiation_availability_response()
            if self.innovation_offset_pct is None
            else self.innovation_offset_pct
        )
        reference_offset = (
            reference_pricing_availability_response()
            if self.innovation_offset_pct is None
            else self.innovation_offset_pct
        )

        price_reducing_savings = (
            self._estimate_negotiation_savings()
            + self._estimate_manufacturer_discount_savings()
        ) * (1 - negotiation_offset)
        price_reducing_savings += self._estimate_reference_pricing_savings() * (
            1 - reference_offset
        )

        cost_sharing_shift = (
            self._estimate_insulin_cap_deficit_effect()
            + self._estimate_oop_cap_deficit_effect()
        )
        return -price_reducing_savings + cost_sharing_shift

    # ------------------------------------------------------------------
    # Medicare drug price negotiation
    # ------------------------------------------------------------------

    def _negotiation_selections_per_year(self) -> int:
        """Molecules the policy adds to the negotiated set each year.

        The IRA caps selections at 20 per applicability year. Raising that cap
        is only meaningful if enough molecules are *eligible* to be selected:
        CMS draws each cycle from "the top 50 negotiation-eligible Part D drugs
        with the highest total Medicare Part D expenditures and the top 50
        negotiation-eligible Part B drugs" (CMS, IPAY 2028 selected-drug fact
        sheet), and a drug is not negotiation-eligible until 7 years after
        approval, 11 for a biologic.

        So a policy that raises the annual count without lifting that bar is
        promising more selections than the statute makes eligible, and the
        module scores it at the cap. The module has no published measure of the
        flow of newly eligible molecules other than the cap Congress set, and
        uses that; the assumption is recorded rather than tuned.
        """
        cap = int(PHARMA_BASELINE["ira_annual_selection_cap"])
        if not self.expand_negotiation:
            return cap
        if not self.remove_exclusivity_delay:
            return cap
        return max(cap, int(self.negotiation_drug_count))

    def _policy_negotiated_molecules(self, year: int, first_expanded_year: int) -> int:
        """Cumulative negotiated molecules in ``year`` under the policy.

        ``first_expanded_year`` is ``max(IRA_STEADY_STATE_YEAR, start_year + 2)``
        and both terms are the statute's, not the module's. A policy cannot
        change selections already in train: CMS published the IPAY 2026 list in
        August 2023 and the IPAY 2027 list in January 2025, so a selection
        precedes its applicability year by at least two years, which is the
        ``+ 2``. And an expansion of the *annual cap* has nothing to raise until
        the year that cap starts governing, which is 2029 — before then the
        statute names the count outright (10, then up to 15, then up to 15).

        For every policy in this repository the 2029 term binds first, because
        the shipped presets start in 2025, so the two-year lead is currently
        inert and is recorded rather than relied on.
        """
        law = current_law_negotiated_molecules(year)
        if year < first_expanded_year:
            return law

        per_year = self._negotiation_selections_per_year()
        total = current_law_negotiated_molecules(first_expanded_year - 1)
        total += per_year * (year - first_expanded_year + 1)
        return max(law, total)

    def _estimate_negotiation_savings(self) -> float:
        """Federal saving from expanding Medicare drug price negotiation, $B/yr.

        Bottom-up, in four published steps.

        **The negotiated set is cumulative and current law is not "20 drugs".**
        The IRA sets prices for 10 molecules in 2026, up to 15 more in 2027, up
        to 15 more in 2028 and up to 20 more every year after that (CMS, 15
        August 2024). By 2034 current law has negotiated 160 molecules. The
        module used to compare a policy against a standing set of 20.

        **Which molecules, and what they cost.** CMS selects in descending order
        of Medicare spending, and has published the spending of all three
        cycles' selections. :func:`negotiation_spending_ladder` turns that into
        gross spending by rank, so the molecules an expansion adds are priced as
        what they are — the tail of the distribution — rather than as replicas
        of Eliquis.

        **What negotiation saves per dollar of that spending.** CMS: the 2026
        negotiated prices, applied to 2023, "would have saved an estimated $6
        billion in net covered prescription drug costs, or approximately 22
        percent, across the 10 selected drugs", and those drugs had $56.2B of
        gross spending. $6B / $56.2B is the saving per gross dollar, and using
        it directly avoids assuming both a gross-to-net ratio and a negotiated
        discount when CMS has published their product. (The 22 percent is off
        *net* covered drug costs; the implied gross-to-net on these molecules is
        far steeper than the 23 percent Part D average, because the selection
        rule picks the largest single-source brands and MedPAC reports rebates
        above 40 percent in exactly those classes — diabetic therapies,
        anticoagulants, asthma/COPD agents (June 2023, ch. 2, Table 2-1).)

        **Whose dollar it was.** The reduction is shared out through the three
        channels of :func:`part_d_federal_channels`.

        The result is a window average, because the negotiated set grows every
        year and the scoring engine asks this module for one annual number.

        Cross-check, on a policy CBO actually scored rather than on this
        preset's benchmark: run against current law's own schedule this identity
        gives about $74B of federal saving over 2026-2031 and about $134B over
        2026-2034, against the roughly **$100 billion over ten years** CBO
        estimated for the negotiation program (quoted by the Secretary of Health
        and Human Services in CMS's 15 August 2024 release, alongside CBO's
        $3.7B for the first year). The $237B often attached to "IRA drug
        negotiation" — and used by the implementation this replaces — is CBO's
        score of the IRA's *entire* drug-pricing title, so dividing it by the
        negotiation program's drug count overstated the per-molecule saving by
        roughly 2.4 times.
        """
        if not self.expand_negotiation:
            return 0.0

        first_expanded_year = max(IRA_STEADY_STATE_YEAR, self.start_year + 2)
        saving_rate = (
            PHARMA_BASELINE["negotiation_cycle1_saving_billions"]
            / PHARMA_BASELINE["negotiation_cycle1_gross_billions"]
        )
        federal_share = part_d_federal_share()

        window = range(self.start_year, self.start_year + self.duration_years)
        total = 0.0
        for year in window:
            incremental_gross = negotiated_gross_spending(
                self._policy_negotiated_molecules(year, first_expanded_year)
            ) - negotiated_gross_spending(current_law_negotiated_molecules(year))
            total += incremental_gross * saving_rate * federal_share

        return total / self.duration_years

    # ------------------------------------------------------------------
    # Part D redesign
    # ------------------------------------------------------------------

    def _estimate_manufacturer_discount_savings(self) -> float:
        """Federal saving from a mandatory manufacturer discount, $B/yr.

        The identity this replaces applied the discount percentage to the whole
        of gross Part D spending and booked every cent as a federal saving —
        the same two errors the reference-pricing path carried before lane L7:
        no brand restriction, no rebate netting, and no federal share. A
        manufacturer discount is negotiated off what the manufacturer is
        actually paid, which is the brand base net of the rebates plans already
        collect, and Medicare keeps only its share of the reduction.
        """
        if self.manufacturer_discount_pct <= 0:
            return 0.0

        base = PHARMA_BASELINE
        brand_net = base["medicare_part_d_gross_spending_billions"] * (
            base["part_d_brand_share_of_gross"]
            - base["part_d_manufacturer_rebate_share_of_gross"]
        )
        return brand_net * self.manufacturer_discount_pct * part_d_federal_share()

    def _estimate_oop_cap_deficit_effect(self) -> float:
        """Federal deficit effect of a Part D annual out-of-pocket cap, $B/yr.

        The same incidence as the insulin cap, one benefit phase up. Capping
        what a beneficiary can pay in a year does not reduce what their drugs
        cost; it moves the liability onto the plan, plan bids rise, and
        Medicare's basic-benefit subsidy covers 74.5 percent of that (MedPAC,
        March 2025, ch. 12, p. 418). So a cap *widens* the deficit.

        The published shift is ASPE's, and it comes with both endpoints a
        tighter cap needs. The 11.3 million Part D enrollees who reach the IRA's
        $2,000 cap in 2025 save **$7.2 billion** of out-of-pocket cost
        (*Projecting the Impact of the Inflation Reduction Act's Part D
        Redesign*, HP-2025-02, January 2025, Table 2B, p. 7), and in the absence
        of the IRA the same enrollees would have paid about **$14.3 billion**
        (Table 2A, p. 6). A cap of $0 shifts all $14.3B and a cap of $2,000
        shifts $7.2B, so the module interpolates linearly between ASPE's two
        published points and **refuses to extrapolate above $2,000**, where it
        has no measurement at all.

        This is the mechanism lane L7 declined to guess at. Its ``oop_cap``
        field was deleted rather than left as a lever that changed nothing, with
        the condition that "adding the mechanism means adding a sourced shift,
        not restoring the field". The shift above is that source.

        Cross-check: at the IRA's own $2,000 the identity gives about $5.4B a
        year, or **$54B over ten years**. CBO scored the whole Part D benefit
        redesign at **+$30B of federal spending over 2022-2031** (KFF, quoting
        CBO's score of the IRA: "$29.9 billion in higher spending associated
        with Part D benefit redesign and $0.1 billion ... to spread out
        out-of-pocket costs"). The identity sits above that, and should: CBO's
        $30B is the *net* of the redesign, in which the cap's cost is offset by
        cutting catastrophic reinsurance from 80 percent to 20 and by the new
        manufacturer discount program, neither of which this lever contains. It
        also sits far below what the redesign has actually cost — CRFB, reading
        CBO's 2026 baseline, now puts it at "$200 to $300 billion through 2031"
        against the original $30B.

        Known limitation: ASPE's $7.2B is a single 2025 projection held flat,
        exactly as the insulin channel holds ASPE's $734M flat, so neither
        channel grows with drug cost or enrolment across the window.
        """
        if self.oop_cap is None:
            return 0.0

        base = PHARMA_BASELINE
        reference_cap = base["part_d_oop_cap_reference_dollars"]
        if self.oop_cap > reference_cap:
            # Above ASPE's cap the module has no published shift, so it claims
            # none rather than extrapolating past its data.
            return 0.0

        at_reference = base["part_d_oop_cap_reference_relief_billions"]
        at_zero = base["part_d_oop_cap_baseline_out_of_pocket_billions"]
        shift = at_zero + (at_reference - at_zero) * (
            max(self.oop_cap, 0.0) / reference_cap
        )
        return shift * base["part_d_basic_benefit_federal_share"]

    # ------------------------------------------------------------------
    # Insulin
    # ------------------------------------------------------------------

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
        Payment Policy*, March 2025, ch. 12, p. 418), so the federal government
        picks up 74.5 cents of every dollar shifted. HHS ASPE estimates that
        Part D beneficiaries would have saved **$734 million** in 2020 had the
        IRA's $35-per-month cap been in force (*Report on the Affordability of
        Insulin*, December 2022, p. 15) — that is the amount shifted. Enrollees
        receiving the low-income subsidy already pay nominal copays far below
        $35 and are inside ASPE's estimate, so no separate exclusion is needed.

        This channel deliberately keeps the statutory 74.5 percent rather than
        the three-channel share in :func:`part_d_federal_channels`. Those
        channels apportion a reduction in *drug cost*; a cost-sharing cap
        reduces no drug cost at all, it converts beneficiary liability into plan
        liability, and plan liability is subsidised at the statutory rate. The
        low-income channel is already inside ASPE's figure and the catastrophic
        phase has carried no cost sharing since 2024, so adding either would
        double-count.

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

    # ------------------------------------------------------------------
    # International reference pricing
    # ------------------------------------------------------------------

    def _estimate_reference_pricing_savings(self) -> float:
        """Federal savings from international reference pricing, $B per year.

        Four things have to line up for this identity to mean anything.

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

        **Only the molecules with a foreign price to reference.** This is what
        lane L7 left open and lane W4 closes. RAND's index is computed on
        presentations sold in *both* markets: a US product with no counterpart
        in any comparison country contributes nothing to the ratio, and a
        reference-pricing rule has nothing to reference it against. RAND
        publishes the coverage. For the combined 33-country comparison the
        matched presentations account for **90.2 percent of US sales** and 88.3
        percent of US volume (Table A.4, p. 36); within those matched
        presentations brand-name originators are **84 percent** of US sales
        (Table A.6, p. 38), against **87 percent** across all US sales
        (Table 2.2, p. 12). Brand-originator sales the index reaches are
        therefore 0.902 x 0.84 / 0.87, about **87 percent** of the brand base —
        RAND's own warning that "the presentations contributing to bilateral
        comparisons accounted for smaller shares of brand-name originator ...
        sales" made arithmetic.

        **The federal share.** Medicare drug spending is not a federal outlay in
        full: a price cut also reduces enrollee premiums and cost sharing, which
        never touched the Treasury. Part D runs through the three channels of
        :func:`part_d_federal_channels`. Part B pays 80% of allowed charges and
        is 75% general-revenue funded.

        Cross-check: the implied cut in US net brand prices, 3.08 -> 1.20 or
        about 61%, sits close to the roughly 55% average net-price reduction CBO
        estimated for the first group of drugs negotiated under H.R. 3's cap at
        120% of the average international market price; CBO scored that title,
        which reached a limited set of drugs rather than the whole Medicare
        book, at about $456B over 2020-2029 (publication 55936).

        Known limitation, deliberately still not parameterised: **no
        utilisation response.** A 61 percent cut in brand prices should raise
        the quantity dispensed, and neither leg models that. Lane W4 went
        looking for CBO's own assumption and did not find a usable one. What it
        found instead is worth recording, because two of the three answers point
        away from adding a term:

        - CBO's negotiation model appears to assume none at all — the working
          paper behind the H.R. 3 estimate says "because utilization of a drug
          does not vary with its price in that model, the negotiation can be
          expressed by accounting only for the per-beneficiary net benefit of
          the drug" (Adams and Herrnstadt, *CBO's Model of Drug Price
          Negotiations Under the Elijah E. Cummings Lower Drug Costs Now Act*,
          working paper 2021-01, publication 56905). That sentence could not be
          confirmed against the document itself, which cbo.gov serves only to
          browsers, so it is a lead and not a citation.
        - The one *published* CBO utilisation parameter runs the other way and
          against a base this module does not have: a 1 percent increase in
          prescriptions filled reduces Medicare's spending on **other medical
          services** by about 0.2 percent (*Offsetting Effects of Prescription
          Drug Use on Medicare's Spending for Medical Services*, publication
          43741, November 2012).
        - No CBO price elasticity of demand for prescription drugs could be
          sourced at all.

        So no utilisation term is added. Adding an invented one would be exactly
        the failure the availability response above was rewritten to avoid.
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

        # Share of US brand-originator sales the RAND index actually reaches.
        coverage = (
            base["rand_us_sales_share_in_comparison"]
            * base["rand_brand_share_of_contributing_us_sales"]
            / base["rand_brand_share_of_all_us_sales"]
        )

        part_d_brand_net = base["medicare_part_d_gross_spending_billions"] * (
            base["part_d_brand_share_of_gross"]
            - base["part_d_manufacturer_rebate_share_of_gross"]
        )
        part_b_net = base["medicare_part_b_drugs_billions"]

        reachable_cut = price_reduction * coverage
        return (
            part_d_brand_net * reachable_cut * part_d_federal_share()
            + part_b_net * reachable_cut * base["part_b_drug_federal_share"]
        )


# Factory functions

def create_expand_drug_negotiation() -> DrugPricingPolicy:
    """Expand Medicare drug negotiation beyond the IRA's 20-per-year cap."""
    return DrugPricingPolicy(
        name="Expand Drug Negotiation",
        description=(
            "Select 50 molecules a year for Medicare price negotiation instead of "
            "the IRA's 20, and lift the 7/11-year eligibility bar so that many are "
            "eligible. Estimated: -\\$500B/10yr."
        ),
        policy_type=PolicyType.MANDATORY_SPENDING,
        reform_type=DrugPricingReformType.MEDICARE_NEGOTIATION,
        expand_negotiation=True,
        negotiation_drug_count=50,
        remove_exclusivity_delay=True,
    )

def create_insulin_cap_all() -> DrugPricingPolicy:
    """$35 insulin cap for all Americans."""
    return DrugPricingPolicy(
        name="Universal Insulin Cap ($35)",
        description=(
            "\\$35/month insulin cap for Medicare and private insurance. A "
            "cost-sharing cap shifts a patient's liability onto the plan and "
            "onto the federal subsidy for it, so CBO scores it as ADDING to "
            "the deficit: +\\$11.4B/10yr (pub. 57957, FY2022-2031). The "
            "-\\$15B this line used to quote was superseded by "
            "universal_insulin_cap.v2 and points the wrong way."
        ),
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
