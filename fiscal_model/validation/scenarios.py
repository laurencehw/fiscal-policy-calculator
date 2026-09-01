"""
Scenario registries for specialized validation suites.
"""

from ..amt import (
    create_extend_tcja_amt_relief,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
)
from ..climate import (
    create_carbon_tax_50,
    create_repeal_ev_credits,
    create_repeal_ira_credits,
)
from ..corporate import (
    create_biden_corporate_rate_only,
    create_republican_corporate_cut,
)
from ..credits import (
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_permanent_extension,
)
from ..enforcement import create_double_enforcement, create_ira_enforcement
from ..estate import (
    create_biden_estate_proposal,
    create_eliminate_estate_tax,
    create_tcja_estate_extension,
)
from ..international import (
    create_biden_full_international,
    create_biden_gilti_reform,
    create_fdii_repeal,
    create_pillar_two_adoption,
)
from ..payroll import (
    create_expand_niit,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
)
from ..pharma import (
    create_expand_drug_negotiation,
    create_insulin_cap_all,
    create_reference_pricing,
)
from ..ptc import create_extend_enhanced_ptc, create_repeal_ptc
from ..tax_expenditures import (
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
)
from ..trade import (
    create_auto_tariff_25,
    create_reciprocal_tariffs,
    create_steel_tariff_25,
    create_trump_china_60,
    create_trump_universal_10,
)

CAPITAL_GAINS_VALIDATION_SCENARIOS = {
    "cbo_2pp_all_brackets": {
        "score_id": "cbo_capgains_2pp_all",
        "description": "CBO +2pp rate increase across all brackets",
        "baseline_realizations_billions": 955.0,
        "baseline_capital_gains_rate": 0.15,
        "short_run_elasticity": 3.2,
        "long_run_elasticity": 2.8,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "step_up_lock_in_multiplier": 1.0,
        "notes": (
            "2018 baseline. JCT implied elasticity much higher than academic estimates. "
            "This may reflect additional behavioral channels not in simple model."
        ),
    },
    "pwbm_39_with_stepup": {
        "score_id": "pwbm_capgains_39_with_stepup",
        "description": "PWBM 39.6% rate (with step-up basis at death)",
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,
        "short_run_elasticity": 0.8,
        "long_run_elasticity": 0.4,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "step_up_lock_in_multiplier": 5.3,
        "notes": (
            "With step-up, taxpayers avoid tax by holding until death. "
            "Lock-in multiplier of 5.3x calibrated to match PWBM's revenue loss. "
            "Implies effective elasticity of ~4.2 (short-run) and ~2.1 (long-run)."
        ),
    },
    "pwbm_39_no_stepup": {
        "score_id": "pwbm_capgains_39_no_stepup",
        "description": "PWBM 39.6% rate (without step-up basis)",
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,
        "short_run_elasticity": 0.8,
        "long_run_elasticity": 0.4,
        "step_up_at_death": True,
        "eliminate_step_up": True,
        "step_up_lock_in_multiplier": 1.0,
        "no_step_up_avoidance_multiplier": 1.5,
        "step_up_exemption": 0.0,
        "gains_at_death_billions": 0.0,
        "notes": (
            "Without step-up, behavioral response is more moderate. "
            "A 1.5x residual avoidance multiplier captures PWBM's caveat that "
            "threshold timing and business-form shifting remain even after step-up "
            "basis is eliminated. PWBM $113B is for rate change only; step-up "
            "elimination revenue separate."
        ),
    },
}


TCJA_VALIDATION_SCENARIOS = {
    "tcja_full_extension": {
        "description": "Full TCJA extension (all provisions)",
        "score_id": "tcja_extension_full",
        "extend_all": True,
        "keep_salt_cap": True,
        "expected_10yr": 4600.0,
        "notes": "CBO baseline assumes TCJA expires. Extension is cost relative to that baseline.",
    },
    "tcja_no_salt_cap": {
        "description": "TCJA extension without SALT cap",
        "score_id": None,
        "extend_all": True,
        "keep_salt_cap": False,
        "expected_10yr": 5700.0,
        "notes": "Repealing SALT cap adds ~$1.1T to cost. Popular bipartisan proposal.",
    },
    "tcja_rates_only": {
        "description": "Extend rate cuts only (no other provisions)",
        "score_id": None,
        "extend_all": False,
        "extend_rates": True,
        "extend_standard_deduction": False,
        "keep_exemption_elimination": False,
        "extend_passthrough": False,
        "extend_ctc": False,
        "extend_estate": False,
        "extend_amt": False,
        "keep_salt_cap": False,
        "expected_10yr": 3185.0,
        "notes": "Rate cuts only: ~$3.2T calibrated. This is an illustrative scenario.",
    },
}


CORPORATE_VALIDATION_SCENARIOS = {
    "biden_corporate_28": {
        "description": "Biden Corporate Rate to 28%",
        "score_id": "biden_corporate_28",
        "policy_factory": create_biden_corporate_rate_only,
        "expected_10yr": -1347.0,
        "notes": "Core rate increase from 21% to 28% only, without international provisions.",
    },
    "trump_corporate_15": {
        "description": "Trump Corporate Rate to 15%",
        "score_id": None,
        "policy_factory": create_republican_corporate_cut,
        "expected_10yr": 1920.0,
        "notes": (
            "Trump 2024 proposal to lower corporate rate to 15%. No official score; "
            "expected estimate derived from model. Includes bonus depreciation extension."
        ),
    },
}


TAX_CREDIT_VALIDATION_SCENARIOS = {
    "biden_ctc_2021": {
        "description": "Biden 2021 ARP-style CTC (permanent)",
        "policy_factory": create_biden_ctc_2021,
        "expected_10yr": 1600.0,
        "source": "CBO/JCT 2021",
        "notes": "ARP CTC was 1-year ($110B). Permanent would be ~$1.6T over 10 years.",
    },
    "ctc_extension": {
        "description": "Extend current CTC beyond 2025",
        "policy_factory": create_ctc_permanent_extension,
        "expected_10yr": 600.0,
        "source": "CBO 2024",
        "notes": "Part of TCJA extension cost. Without extension, CTC reverts to $1,000.",
    },
    "biden_eitc_childless": {
        "description": "Biden childless EITC expansion",
        "policy_factory": create_biden_eitc_childless,
        "expected_10yr": 178.0,
        "source": "Treasury Green Book 2024",
        "notes": "Triple max credit to ~$1,500, expand age range 19-65+.",
    },
}


ESTATE_TAX_VALIDATION_SCENARIOS = {
    "extend_tcja_exemption": {
        "description": "Extend TCJA estate exemption (~$14M)",
        "policy_factory": create_tcja_estate_extension,
        "expected_10yr": 167.0,
        "source": "CBO",
        "notes": "Keep $14M+ exemption instead of reversion to $6.4M in 2026",
    },
    "biden_estate_reform": {
        "description": "Biden estate reform ($3.5M, 45%)",
        "policy_factory": create_biden_estate_proposal,
        "expected_10yr": -450.0,
        "source": "Treasury estimate",
        "notes": "Lower exemption to $3.5M + raise rate to 45%",
    },
    "eliminate_estate_tax": {
        "description": "Eliminate estate tax",
        "policy_factory": create_eliminate_estate_tax,
        "expected_10yr": 350.0,
        "source": "Model estimate",
        "notes": "Repeal federal estate tax entirely",
    },
}


PAYROLL_TAX_VALIDATION_SCENARIOS = {
    "ss_cap_90_pct": {
        "description": "SS cap to cover 90% of wages",
        "policy_factory": create_ss_cap_90_percent,
        "expected_10yr": -800.0,
        "source": "CBO",
        "notes": "Raise cap from ~$176K to ~$305K",
    },
    "ss_donut_250k": {
        "description": "SS tax on wages above $250K",
        "policy_factory": create_ss_donut_hole,
        "expected_10yr": -2700.0,
        "source": "Social Security Trustees",
        "notes": "Donut hole: tax current cap + above $250K",
    },
    "ss_eliminate_cap": {
        "description": "Eliminate SS wage cap",
        "policy_factory": create_ss_eliminate_cap,
        "expected_10yr": -3200.0,
        "source": "Social Security Trustees",
        "notes": "Tax all wages at 12.4%",
    },
    "expand_niit": {
        "description": "Expand NIIT to pass-through income",
        "policy_factory": create_expand_niit,
        "expected_10yr": -250.0,
        "source": "JCT (Build Back Better)",
        "notes": "Close S-corp/partnership loophole",
    },
}


AMT_VALIDATION_SCENARIOS_COMPARE = {
    "extend_tcja_amt": {
        "description": "Extend TCJA AMT relief",
        "policy_factory": create_extend_tcja_amt_relief,
        "expected_10yr": 450.0,
        "source": "JCT/CBO",
        "notes": "Keep higher exemptions instead of sunset to pre-TCJA levels",
    },
    "repeal_individual_amt": {
        "description": "Repeal individual AMT (post-2025)",
        "policy_factory": create_repeal_individual_amt,
        "kwargs": {"start_year": 2026},
        "expected_10yr": 450.0,
        "source": "CBO baseline",
        "notes": "Eliminate all individual AMT after TCJA expires",
    },
    "repeal_corporate_amt": {
        "description": "Repeal corporate AMT (CAMT)",
        "policy_factory": create_repeal_corporate_amt,
        "expected_10yr": 220.0,
        "source": "CBO",
        "notes": "Repeal 15% book minimum tax from IRA 2022",
    },
}


PTC_VALIDATION_SCENARIOS_COMPARE = {
    "extend_enhanced_ptc": {
        "description": "Extend enhanced PTCs (ARPA/IRA)",
        "policy_factory": create_extend_enhanced_ptc,
        "expected_10yr": 350.0,
        "source": "CBO 2024",
        "notes": "Extend subsidies beyond 2025 sunset",
    },
    "repeal_ptc": {
        "description": "Repeal premium tax credits",
        "policy_factory": create_repeal_ptc,
        "expected_10yr": -1100.0,
        "source": "CBO estimate",
        "notes": "Eliminate all ACA subsidies - major coverage loss",
    },
}


TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE = {
    "cap_employer_health": {
        "description": "Cap employer health exclusion at $50K",
        "policy_factory": create_cap_employer_health_exclusion,
        "expected_10yr": -450.0,
        "source": "CBO",
        "notes": "Third-largest tax expenditure",
    },
    "eliminate_mortgage": {
        "description": "Eliminate mortgage interest deduction",
        "policy_factory": create_eliminate_mortgage_deduction,
        "expected_10yr": -300.0,
        "source": "CBO",
        "notes": "From current TCJA levels (~$25B/year)",
    },
    "repeal_salt_cap": {
        "description": "Repeal SALT $10K cap",
        "policy_factory": create_repeal_salt_cap,
        "expected_10yr": 1100.0,
        "source": "JCT",
        "notes": "Bipartisan proposal, benefits high-tax states",
    },
    "eliminate_salt": {
        "description": "Eliminate SALT deduction entirely",
        "policy_factory": create_eliminate_salt_deduction,
        "expected_10yr": -1200.0,
        "source": "JCT estimate",
        "notes": "Very controversial",
    },
    "cap_charitable": {
        "description": "Cap charitable deduction at 28%",
        "policy_factory": create_cap_charitable_deduction,
        "expected_10yr": -200.0,
        "source": "Obama/Biden proposal",
        "notes": "Pease-style limitation",
    },
    "eliminate_step_up": {
        "description": "Eliminate step-up in basis",
        "policy_factory": create_eliminate_step_up_basis,
        "expected_10yr": -500.0,
        "source": "Biden proposal",
        "notes": "Tax gains at death with $1M exemption",
    },
}


# =============================================================================
# Phase E — sectoral module reconstructions (international, trade, pharma,
# IRS enforcement, climate/energy)
# =============================================================================
# Plan §5.3: 21 presets had a live module *and* an official number in
# ``CBO_SCORE_MAP`` but no ``validate_all_*`` runner, so the calibrated tier
# silently understated how much of the app is actually being scored. These
# registries close that gap for the five sectoral modules.
#
# Read this block with three things in mind:
#
# 1. **Targets are read from ``fiscal_model.app_data.CBO_SCORE_MAP``**, keyed by
#    the ``preset`` field below. No target is restated here, so these registries
#    cannot drift away from what the app shows a user.
# 2. **These are reconstructions, not confirmations.** ``calibrated_to_target``
#    records whether the module actually carries a constant fitted to reproduce
#    its benchmark. Where it is ``False`` the module was built from literature
#    and agency aggregates and has simply never been compared to this number —
#    which is why several of them miss badly. Nothing here was retuned to close
#    a gap; a miss is reported with a ``limitations`` note explaining it.
# 3. **``provenance`` is the target's pedigree, not the model's accuracy.** Every
#    one of these targets is a rounded headline figure or an explicit model
#    estimate; none is a transcribed table row. See ``provenance.py``.

INTERNATIONAL_VALIDATION_SCENARIOS_COMPARE = {
    "biden_gilti_reform": {
        "description": "Biden GILTI reform (country-by-country, 21%)",
        "preset": "\U0001f30d Biden GILTI Reform (-$280B)",
        "policy_factory": create_biden_gilti_reform,
        "official_source": (
            "U.S. Treasury, General Explanations of the Administration's "
            "FY2025 Revenue Proposals (Green Book)"
        ),
        "benchmark_date": "2024-03",
        "benchmark_url": (
            "https://home.treasury.gov/system/files/131/"
            "General-Explanations-FY2025.pdf"
        ),
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Country-by-country GILTI at 21% with QBAI eliminated.",
        "limitations": [
            "GILTI is modelled as an aggregate rate change on a single CFC income "
            "pool; the country-by-country mechanics that drive the Treasury proposal "
            "(per-jurisdiction blending, loss ring-fencing, the foreign tax credit "
            "haircut) are not represented.",
            "The -$280B target is the repo's rounded Green Book figure, not a "
            "transcribed row of the FY2025 Green Book revenue table.",
        ],
    },
    "fdii_repeal": {
        "description": "Repeal the FDII deduction",
        "preset": "\U0001f30d Repeal FDII (-$200B)",
        "policy_factory": create_fdii_repeal,
        "official_source": (
            "U.S. Treasury, General Explanations of the Administration's "
            "FY2025 Revenue Proposals (Green Book)"
        ),
        "benchmark_date": "2024-03",
        "benchmark_url": (
            "https://home.treasury.gov/system/files/131/"
            "General-Explanations-FY2025.pdf"
        ),
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Full repeal of the 37.5% FDII deduction.",
        "limitations": [
            "Scored off a single $160B FDII-eligible income aggregate at a fixed "
            "deduction rate; no behavioural relocation of intangible property and no "
            "interaction with the GILTI rate change is modelled.",
            "The -$200B target is a rounded headline figure, not a Green Book table "
            "row.",
        ],
    },
    "pillar_two_adoption": {
        "description": "Adopt OECD Pillar Two (15% global minimum)",
        "preset": "\U0001f30d Pillar Two Adoption (-$80B)",
        "policy_factory": create_pillar_two_adoption,
        "official_source": "Joint Committee on Taxation",
        "benchmark_date": "2023",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Qualified domestic minimum top-up tax at 15%.",
        "limitations": [
            "Poor: the module tops up a $120B undertaxed-profit pool with a 60% "
            "substance carve-out. JCT's estimate additionally embeds foreign adoption "
            "timing, transitional safe harbours, and the US GILTI receipts that get "
            "reassigned abroad once other jurisdictions apply the UTPR.",
            "The -$80B target is the midpoint of a range the module's own source note "
            "gives as $50-120B, so the model's -$61B sits inside the published range "
            "even though it rates Poor against the midpoint.",
        ],
    },
    "biden_full_international": {
        "description": "Biden international package (GILTI + FDII + UTPR)",
        "preset": "\U0001f30d Biden International Package (-$700B)",
        "policy_factory": create_biden_full_international,
        "official_source": (
            "U.S. Treasury, General Explanations of the Administration's "
            "FY2025 Revenue Proposals (Green Book)"
        ),
        "benchmark_date": "2024-03",
        "benchmark_url": (
            "https://home.treasury.gov/system/files/131/"
            "General-Explanations-FY2025.pdf"
        ),
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Full package target; the module implements three of its provisions.",
        "limitations": [
            "Poor: the -$700B package covers GILTI + FDII + UTPR plus the BEAT/SHIELD "
            "replacement, anti-inversion rules and several base-protection provisions "
            "the module does not implement. It scores only the three provisions it has.",
            "Component additivity is assumed: GILTI, FDII and UTPR effects are summed "
            "with no interaction term, while a package estimate nets overlapping bases.",
        ],
    },
}


TRADE_VALIDATION_SCENARIOS_COMPARE = {
    "trump_universal_10": {
        "description": "Trump universal 10% tariff",
        "preset": "\U0001f3ed Trump Universal 10% Tariff (-$2T)",
        "policy_factory": create_trump_universal_10,
        "official_source": "Tax Foundation / Yale Budget Lab",
        "benchmark_date": "2024",
        "benchmark_url": "https://budgetlab.yale.edu/research",
        "provenance": "secondhand",
        "calibrated_to_target": True,
        "notes": "10% on all imports; 70% effective coverage.",
        "limitations": [
            "The 70% effective-coverage constant in TRADE_BASELINE is calibrated to "
            "reproduce this ~$2T figure; it stands in for exemptions, existing duties "
            "and de minimis rather than being derived from HTS line data.",
            "The static score nets only the import-demand response. The GDP-feedback "
            "drag on income and payroll receipts that Yale and CBO include reaches the "
            "number through the dynamic path, not this entry.",
        ],
    },
    "trump_china_60": {
        "description": "Trump 60% China tariff",
        "preset": "\U0001f3ed Trump 60% China Tariff (-$500B)",
        "policy_factory": create_trump_china_60,
        "official_source": "Tax Foundation",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": True,
        "notes": "60% on Chinese imports, incremental above the existing ~20% average.",
        "limitations": [
            "The 50% China effective-coverage constant is calibrated to this target; "
            "the split between goods already under Section 301 duties and goods newly "
            "exposed is an assumption, not a tariff-line calculation.",
            "Trade diversion through third countries — the dominant response in the "
            "2018-2019 episode — is captured only through a single elasticity.",
        ],
    },
    "auto_tariff_25": {
        "description": "25% tariff on imported autos and parts",
        "preset": "\U0001f3ed 25% Auto Tariff (-$100B)",
        "policy_factory": create_auto_tariff_25,
        "official_source": "Committee for a Responsible Federal Budget (CRFB)",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "USMCA-exempt share removed from the base before the rate is applied.",
        "limitations": [
            "Poor: the effective base is 35% of $380B of auto imports at a 22.5pp "
            "incremental rate, which mechanically yields ~$25B/yr. The -$100B/10yr "
            "target implies roughly $10B/yr — a materially narrower base, or a much "
            "larger volume response than the module's -0.5 import elasticity gives.",
            "Not retuned: the target is a secondhand round number with no published "
            "table behind it, so the gap is reported rather than closed by moving "
            "TRADE_BASELINE constants.",
        ],
    },
    "steel_tariff_25": {
        "description": "25% tariff on steel and aluminium",
        "preset": "\U0001f3ed 25% Steel & Aluminum Tariff (-$60B)",
        "policy_factory": create_steel_tariff_25,
        "official_source": "Tax Foundation",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Flat 25pp on a $50B steel/aluminium import base.",
        "limitations": [
            "Poor: the full 25pp is applied to the whole $50B base with no allowance "
            "for the Section 232 duties already in force, so the incremental rate is "
            "overstated.",
            "Target bookkeeping defect: CBO_SCORE_MAP carries -$60B under the key "
            "'25% Steel & Aluminum Tariff', while PRESET_POLICIES uses the key "
            "'25% Steel/Aluminum Tariff' and labels it -$15B. The two dictionaries "
            "never join, so the preset shows no official score in the app at all and "
            "the two published figures differ by 4x.",
        ],
    },
    "reciprocal_tariffs": {
        "description": "Reciprocal tariffs (~20pp average increase)",
        "preset": "\U0001f3ed Reciprocal Tariffs (~20pp) (-$1.2T)",
        "policy_factory": create_reciprocal_tariffs,
        "official_source": "Tax Foundation / Yale Budget Lab",
        "benchmark_date": "2024",
        "benchmark_url": "https://budgetlab.yale.edu/research",
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Flat 20pp applied to half of all goods imports.",
        "limitations": [
            "Poor: 'reciprocal' is implemented as a flat 20pp on 50% of imports. The "
            "published estimates apply partner-specific rates to partner-specific "
            "bases and assume substantially larger trade diversion.",
            "Neither retaliation nor GDP feedback is netted from this static score, "
            "which is most of the distance between a gross customs figure and a "
            "published net score (the knowledge base puts net at ~40-50% of gross).",
            "Like the steel case, the CBO_SCORE_MAP key ('Reciprocal Tariffs "
            "(~20pp)') does not match the PRESET_POLICIES key ('Reciprocal "
            "Tariffs'), so the app shows no official score for this preset.",
        ],
    },
}


PHARMA_VALIDATION_SCENARIOS_COMPARE = {
    "expand_drug_negotiation": {
        "description": "Expand Medicare drug negotiation to 50 drugs",
        "preset": "\U0001f48a Expand Drug Negotiation (-$500B)",
        "policy_factory": create_expand_drug_negotiation,
        "official_source": "CBO (IRA baseline) extended by model estimate",
        "benchmark_date": "2023",
        "benchmark_url": None,
        "provenance": "model_estimate",
        "calibrated_to_target": False,
        "notes": "50 negotiated drugs plus removal of the exclusivity delay.",
        "limitations": [
            "Poor: savings scale linearly in drug count from the IRA per-drug average "
            "with a flat 60% productivity haircut, while CBO's own scoring is highly "
            "non-linear in which molecules enter the negotiation window.",
            "The -$500B target is not a CBO score of this policy — the record's own "
            "source string reads 'CBO/Estimate', and the only published CBO number in "
            "the module is -$237B for the IRA's 20 drugs.",
        ],
    },
    "universal_insulin_cap": {
        "description": "Universal $35/month insulin cap",
        "preset": "\U0001f48a Universal Insulin Cap (-$15B)",
        "policy_factory": create_insulin_cap_all,
        "official_source": "Congressional Budget Office",
        "benchmark_date": "2022",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "$35/month cap extended from Medicare to private insurance.",
        "limitations": [
            "Poor by three orders of magnitude, and the cause is an incidence/unit "
            "error in the module rather than calibration drift: "
            "DrugPricingPolicy._estimate_insulin_savings credits the entire "
            "difference between a $6,000 average annual insulin cost and the $420 "
            "capped cost to the federal budget for all 8.4M insulin users, scoring a "
            "price cap that mostly reallocates cost among patients, insurers and "
            "manufacturers as ~$47B/yr of federal saving.",
            "extend_to_private=True increases the modelled federal saving, whereas "
            "in the published scores the private-market portion has essentially no "
            "federal budget effect.",
            "Reported, not repaired: correcting the incidence changes a shipped "
            "pharma module's output and belongs in a module change, not in a "
            "validation runner.",
        ],
    },
    "international_reference_pricing": {
        "description": "International reference pricing for Medicare drugs",
        "preset": "\U0001f48a International Reference Pricing (-$100B)",
        "policy_factory": create_reference_pricing,
        "official_source": "RAND price-comparison study, extended by model estimate",
        "benchmark_date": "2021",
        "benchmark_url": None,
        "provenance": "model_estimate",
        "calibrated_to_target": False,
        "notes": "Cap Medicare drug prices at 120% of the OECD average.",
        "limitations": [
            "Poor: the module applies the full US/OECD ratio reduction (2.56x -> "
            "1.20x, a 53% cut) to all $275B of Medicare Part B + Part D drug spending, "
            "ignoring the manufacturer rebates already netted out of Part D and any "
            "utilisation or availability response.",
            "The -$100B target is a RAND-derived illustrative figure ('RAND/Estimate' "
            "in the record), not a scored legislative proposal.",
        ],
    },
}


ENFORCEMENT_VALIDATION_SCENARIOS_COMPARE = {
    "ira_enforcement": {
        "description": "IRA IRS enforcement funding ($80B/10yr)",
        "preset": "\U0001f50d IRA Enforcement Funding (-$200B)",
        "policy_factory": create_ira_enforcement,
        "official_source": "Congressional Budget Office (H.R. 5376 scoring)",
        "benchmark_date": "2022",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": True,
        "notes": "$80B of enforcement funding with a 3-year ramp.",
        "limitations": [
            "The ROI path is a single marginal revenue-per-dollar multiplier (5.0, "
            "chosen to land on this target) with a ramp. CBO's estimate separates "
            "enforcement, operations support, taxpayer services and systems "
            "modernisation, only part of which yields revenue.",
            "The -$200B target is the rounded revenue side of CBO's 2022 letter, not "
            "the net-of-outlays figure, so the model and the target are not measuring "
            "quite the same quantity.",
        ],
    },
    "double_enforcement": {
        "description": "Double IRS enforcement beyond IRA levels",
        "preset": "\U0001f50d Double IRS Enforcement (-$340B)",
        "policy_factory": create_double_enforcement,
        "official_source": (
            "U.S. Treasury, 'The Case for a Robust Attack on the Tax Gap' (2021); "
            "Sarin & Summers enforcement estimates"
        ),
        "benchmark_date": "2021",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "$16B/year of additional enforcement above the IRA baseline.",
        "limitations": [
            "Poor: the module applies a lower base ROI (4.0) and a faster "
            "diminishing-returns factor (0.80) to a $16B/yr increment, which compounds "
            "to far less yield than the estimate the target comes from. Neither "
            "constant was ever fit to this benchmark.",
            "The target is an administration/academic estimate rather than a CBO or "
            "JCT score, and it assumes sustained funding whose revenue arrives partly "
            "outside the module's 4-year ramp and 10-year window.",
        ],
    },
}


CLIMATE_VALIDATION_SCENARIOS_COMPARE = {
    "repeal_ira_credits": {
        "description": "Repeal IRA clean-energy tax credits",
        "preset": "\U0001f331 Repeal IRA Clean Energy Credits ($783B)",
        "policy_factory": create_repeal_ira_credits,
        "official_source": (
            "CBO, budgetary effects of the energy-related tax provisions of "
            "P.L. 117-169 (upward revision)"
        ),
        "benchmark_date": "2024-03",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": True,
        "notes": "Full repeal of the IRA clean-energy credit suite.",
        "limitations": [
            "The module's annual constant is this target restated over ten years, so "
            "the 0.0% error demonstrates plumbing, not predictive content — the same "
            "leakage pattern loo.py flags for repeal_corporate_amt.",
            "CBO's 2024 figure is a projection of uncapped-credit uptake that has "
            "already moved by roughly a factor of two since 2022; treating it as a "
            "fixed benchmark understates its own uncertainty.",
        ],
    },
    "carbon_tax_50": {
        "description": "Carbon tax at $50/ton with a 5% escalator",
        "preset": "\U0001f331 Carbon Tax \\$50/ton (-$1.7T)",
        "policy_factory": create_carbon_tax_50,
        "official_source": "CBO-style estimate (no published score)",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "provenance": "model_estimate",
        "calibrated_to_target": True,
        "notes": "Economy-wide CO2 tax starting at $50/ton.",
        "limitations": [
            "Not a published benchmark: climate.py documents "
            "carbon_tax_behavioral_factor as calibrated so that $50/ton yields "
            "~$1.7T, and the target restates that. Scoring against it measures "
            "internal consistency only.",
            "No interaction with income or payroll receipts (a carbon tax erodes its "
            "own base and the income-tax base simultaneously) and no rebate or "
            "revenue-recycling design is modelled.",
        ],
    },
    "repeal_ev_credits": {
        "description": "Repeal the EV purchase tax credits",
        "preset": "\U0001f331 Repeal EV Credits ($200B)",
        "policy_factory": create_repeal_ev_credits,
        "official_source": "Congressional Budget Office",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "provenance": "secondhand",
        "calibrated_to_target": False,
        "notes": "Repeal of Sections 30D and 45W while other IRA credits stand.",
        "limitations": [
            "Scored as a $7,500 credit on a 1.5M-vehicle base growing 15%/yr; the "
            "income and vehicle-price caps, the separate used (25E) and commercial "
            "(45W) credits, and the demand response to withdrawing the subsidy are "
            "not modelled.",
            "The -$200B target is a rounded figure; the repo's own knowledge base "
            "gives a $30-60B range for EV-credit elimination on the 2022 baseline, so "
            "the published numbers for this policy span an order of magnitude.",
        ],
    },
}
