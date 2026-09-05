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

#: The three capital-gains benchmarks. Every behavioural field is gone: the
#: three hand-set elasticity/lock-in tuples these scenarios used to carry
#: (3.2/2.8 with lock-in 1.0; 0.8/0.4 with lock-in 5.3; 0.8/0.4 with a 1.5x
#: residual-avoidance multiplier) were each chosen after seeing that case's own
#: target, and the leave-one-out donor matrix showed the 5.3x tuple was the
#: module's answer key. What is left is structural: what the policy *is* - its
#: base, its baseline rate, whether step-up survives, whether the published
#: figure covers the gains-at-death channel at all. The behaviour comes from
#: one frozen literature set on ``CapitalGainsPolicy`` (Dowd, McClelland &
#: Muthitacharoen 2015; owner Decision 3 of planning/MODELING_IMPROVEMENT.md).
CAPITAL_GAINS_VALIDATION_SCENARIOS = {
    "cbo_2pp_all_brackets": {
        "score_id": "cbo_capgains_2pp_all",
        "description": "CBO +2pp rate increase across all brackets",
        "baseline_realizations_billions": 955.0,
        "baseline_capital_gains_rate": 0.15,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "notes": (
            "2018 baseline. Scored on the one frozen semi-log realizations "
            "response; the elasticity implied by JCT's own path at a 2pp change "
            "is larger than the frozen persistent value, so this row is "
            "expected to over-predict."
        ),
        "limitations": [
            "The realization elasticity JCT's own path implies at a 2pp change "
            "is roughly twice the frozen persistent value (Dowd, McClelland & "
            "Muthitacharoen 2015), and owner Decision 3 forbids reaching for a "
            "larger one.",
            "The scenario supplies a 2018 aggregate base at one blended rate, so "
            "it bypasses the SOI bracket detail the uncalibrated path uses.",
        ],
    },
    "pwbm_39_with_stepup": {
        "score_id": "pwbm_capgains_39_with_stepup",
        "description": "PWBM 39.6% rate (with step-up basis at death)",
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "notes": (
            "With step-up, holding until death escapes tax entirely. The "
            "semi-log form puts the revenue-maximizing rate at 1/b = 30.6%, so "
            "43.4% is past the peak and the rate change loses revenue - which "
            "is PWBM's own result, reached here without a lock-in multiplier."
        ),
        "limitations": [
            "Scored on the one frozen literature elasticity set (Dowd, McClelland "
            "& Muthitacharoen 2015) rather than the 5.3x lock-in multiplier this "
            "scenario carried until Wave 2's L1, which was chosen after seeing "
            "this case's own target and which the leave-one-out donor matrix "
            "identified as the module's answer key. The model now agrees with "
            "PWBM on sign - a 43.4% rate loses revenue while step-up survives - "
            "and under-states the size of the loss by about half.",
            "The realizations flow is held at its observed SOI level across the "
            "window, so a rate change that shifts realizations has no compounding "
            "growth effect beyond the accrued-gains stock ratio.",
        ],
    },
    "pwbm_39_no_stepup": {
        "score_id": "pwbm_capgains_39_no_stepup",
        "description": "PWBM 39.6% rate (without step-up basis)",
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,
        "step_up_at_death": True,
        "eliminate_step_up": True,
        "step_up_exemption": 0.0,
        # PWBM's $113B is the rate change only; they score step-up elimination
        # separately. A scope statement about the published figure, not a
        # behavioural parameter.
        "score_gains_at_death": False,
        "notes": (
            "Without step-up nothing escapes by being held, so the lock-in "
            "wedge between the two worlds shrinks the response. PWBM's $113B "
            "is for the rate change only; the gains-at-death channel is scored "
            "separately and is switched off here."
        ),
        "limitations": [
            "The with/without-step-up price wedge derived from the accrued-gains "
            "stock is 1.44x, smaller than the 1.5x residual-avoidance multiplier "
            "this scenario carried until Wave 2's L1 - which was chosen after "
            "seeing this case's own target. The row is less accurate and no "
            "longer fitted.",
            "PWBM's own estimate embeds threshold timing and business-form "
            "shifting that survive step-up elimination; neither is modelled.",
        ],
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


# Owner Decision 5 (plan §6, accepted 2026-09-01): all three of these
# benchmarks are **tautological in the fitted tier**. Each carries an
# ``annual_revenue_change_billions`` that is the published target divided by
# exactly ten — -160.0 against $1,600B, -60.0 against $600B, -17.8 against
# $178B — so the by-construction scorecard reproduces them because it was told
# the answer, exactly as it does for ``repeal_corporate_amt``.
#
# The decision is to declare that per case rather than delete a case, which is
# what the ``limitations`` block below does: the declaration travels with the
# benchmark into ``ScorecardEntry.known_limitations``, the API payload and the
# validation tab, so a reader who sees the 0.0% also sees why it is not
# evidence. ``calibrated_to_target`` stays True because it is true — the module
# *is* fitted to these targets, and moving them into the unfitted-reconstruction
# tier would say the opposite.
#
# The leave-one-out row is what carries the honesty, and after Wave 3's L3 it
# has something to say: the derivation is per-unit over the CPS microdata and
# reads no annual at all.
TAX_CREDIT_VALIDATION_SCENARIOS = {
    "biden_ctc_2021": {
        "description": "Biden 2021 ARP-style CTC (permanent)",
        "policy_factory": create_biden_ctc_2021,
        "expected_10yr": 1600.0,
        "source": "CBO/JCT 2021",
        "notes": "ARP CTC was 1-year ($110B). Permanent would be ~$1.6T over 10 years.",
        "limitations": [
            "TAUTOLOGICAL FITTED ROW (owner Decision 5). The module's annual for "
            "this benchmark is -$160.0B, the carried $1,600B target divided by "
            "exactly ten, so the by-construction error tests x/10 x 10 == x and "
            "nothing else. Read the leave-one-out row instead: run_loo.py derives "
            "this case per unit from the CPS microdata and never touches the "
            "annual. The row is kept rather than deleted so the tautology stays "
            "visible - deleting a benchmark to improve a tier mean is the failure "
            "mode pre-registration exists to forbid.",
            "The $1,600B is a rounded secondhand figure attributed to 'CBO/JCT "
            "2021' with no transcribed table row behind it, so the residual on "
            "the derived side is measured against a target of unknown precision.",
        ],
    },
    "ctc_extension": {
        "description": "Extend current CTC beyond 2025",
        "policy_factory": create_ctc_permanent_extension,
        "expected_10yr": 600.0,
        "source": "CBO 2024",
        "notes": "Part of TCJA extension cost. Without extension, CTC reverts to $1,000.",
        "limitations": [
            "TAUTOLOGICAL FITTED ROW (owner Decision 5). The module's annual for "
            "this benchmark is -$60.0B, the carried $600B target divided by "
            "exactly ten, so the by-construction error tests x/10 x 10 == x and "
            "nothing else. Read the leave-one-out row instead: run_loo.py derives "
            "this case per unit from the CPS microdata and never touches the "
            "annual. The row is kept rather than deleted so the tautology stays "
            "visible - deleting a benchmark to improve a tier mean is the failure "
            "mode pre-registration exists to forbid.",
            "Examined and deliberately not moved in Wave 4 "
            "(target_revisions.EXAMINED_NOT_REVISED). Two published figures "
            "score a child-credit extension and neither replaces $600B. JCT's "
            "JCX-35-25 scores P.L. 119-21's child credit at +$816.8B over "
            "FY2025-2034, but that is a $2,200 indexed credit against this "
            "benchmark's $2,000 flat one and it is already carried here as the "
            "`pl119_21_child_tax_credit` benchmark, so adopting it would score "
            "one JCT row as two benchmarks. CRS R48286 Table 1, transcribing "
            "CBO, prints $735.3B for 'Increase and Modification of Child and "
            "Dependent Credit', which CRS itself says includes the credit for "
            "other dependents that this module does not score. Both sit *above* "
            "the module's design rather than bracketing it, so a range would "
            "assert a containment neither publisher supports.",
        ],
    },
    "biden_eitc_childless": {
        "description": "Biden childless EITC expansion",
        "policy_factory": create_biden_eitc_childless,
        # Wave 4 target revision (biden_eitc_childless.v2). Treasury FY2025
        # Green Book, "Restore and make permanent the American Rescue Plan
        # expansion of the earned income tax credit for workers without
        # qualifying children", $162,553M over FY2025-2034 (report p. 242).
        "expected_10yr": 162.6,
        "source": "Treasury FY2025 Green Book (report p. 242)",
        "notes": "Triple max credit to ~$1,500, expand age range 19-65+.",
        "limitations": [
            "NO LONGER A TAUTOLOGICAL FITTED ROW. The module's annual for this "
            "benchmark is -$17.8B, which is the *superseded* $178B target "
            "divided by exactly ten; the target is now Treasury's published "
            "$162.6B, so the reported error is a real 9.5% rather than the "
            "by-construction 0.0% it used to be, and no constant was retuned "
            "to close it. The leave-one-out row is still the better read: "
            "run_loo.py derives this case per unit from the CPS microdata and "
            "never touches the annual.",
            "The derived side under-predicts this row for two reasons in the "
            "survey file rather than the rules: CPS ASEC carries no "
            "self-employment earnings, which the EITC counts, and the tax-unit "
            "builder folds 19-to-23-year-olds with a parent pointer into the "
            "parent's unit - which is most of the population an age expansion "
            "from 25 to 19 is about.",
        ],
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
        "description": "Estate reform ($3.5M exemption, 45% rate)",
        "policy_factory": create_biden_estate_proposal,
        "expected_10yr": -450.0,
        # Re-attributed in Phase E. No Biden Green Book (FY2022, FY2024 or
        # FY2025) proposes a $3.5M exemption or a 45% rate; the FY2025 volume's
        # entire estate section is administrative. The design is the "For the
        # 99.5 Percent Act", which JCT did score.
        "source": "JCT letter on the 'For the 99.5 Percent Act' (24 March 2021)",
        "benchmark_date": "2021-03",
        "benchmark_url": (
            "https://www.sanders.senate.gov/wp-content/uploads/"
            "For-the-99.5-Act-JCT-Score.pdf"
        ),
        "notes": (
            "Lower exemption to $3.5M + raise rate to 45%. JCT scores the bill "
            "containing that design at $429.6B over FY2021-2031, but for the "
            "whole ten-section bill, not the exemption and rate alone."
        ),
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
        # Target revised 2026-09-02 through
        # ``validation/target_revisions.py`` (extend_tcja_amt.v1 -> .v2).
        # The carried $450B was never traceable to a document and is 3.5%
        # from CRS R48286 Table 1's *five*-year column ($466.2B); the
        # ten-year column for the same row reads $1,357.1B.
        "expected_10yr": 1_357.1,
        "description": "Extend TCJA AMT relief",
        "policy_factory": create_extend_tcja_amt_relief,
        "source": "CRS R48286 Table 1 (transcribing CBO 60114/60271)",
        "benchmark_date": "2024-11",
        "benchmark_url": (
            "https://www.congress.gov/crs_external_products/R/HTML/"
            "R48286.web.html"
        ),
        # No `calibrated_to_target` key here on purpose: `scorecard.py`
        # derives it from the ledger, because "the module carries a constant
        # fitted to THIS target" stops being true for every revised row at
        # once, and a hand-set flag per scenario would drift.
        "notes": "Keep higher exemptions instead of sunset to pre-TCJA levels",
        "limitations": [
            "Poor against the corrected target by construction, and the gap is "
            "the point of correcting it: the fitted annual scores $450.5B "
            "against a published $1,357.1B (-66.8%). Retuning the constant to "
            "close that is forbidden — it would re-fit the module to the "
            "number it is being tested on.",
            "The module's structural (derived) path scores $855.3B, -37.0% "
            "against the same row, so the unfitted machinery is about 1.8x "
            "closer to the document than the fitted constant. See "
            "planning/lanes/PROVENANCE_amt_insulin.md.",
            "Definitional gap, not split: CRS/CBO score the AMT provision "
            "inside a full TCJA-extension package, where extended rate cuts "
            "push more filers into AMT than a standalone AMT extension would. "
            "TPC's T25-0049 reconstructs the standalone counterfactual and "
            "implies roughly $855B; both are published and they answer "
            "different questions.",
        ],
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
        # Wave 4 target revision (extend_enhanced_ptc.v2). CBO/JCT pub. 60437
        # (June 2024): "making the policy permanent would increase the budget
        # deficit by $335 billion over the 2025-2034 period". The superseded
        # $350B is the September 2025 re-estimate on a FY2026-2035 window, so
        # the figure and the record's stated vintage disagreed by one window.
        "expected_10yr": 335.0,
        "source": "CBO/JCT pub. 60437 (June 2024)",
        "notes": "Extend subsidies beyond 2025 sunset",
        "limitations": [
            "The module's annual is fitted to the superseded $350B, so the "
            "residual against the revised target is a measurement rather than "
            "bookkeeping. Nothing was retuned to close it.",
        ],
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
        "limitations": [
            "Examined and deliberately not moved in Wave 4 "
            "(target_revisions.EXAMINED_NOT_REVISED): no official repeal score "
            "exists. CBO has published no post-TCJA budget option repealing "
            "the deduction, JCT publishes the tax expenditure rather than a "
            "repeal estimate, and the only two ten-year repeal figures — CRS "
            "IF13190's $495B and Yale's 'close to $1.2 trillion' — come from "
            "the same simulator and differ by 2.4x, with CRS labelling its own "
            "'not considered official for revenue scoring purposes'.",
            "The record's annual_cost = 25.0 is a pre-P.L.119-21 level. JCT's "
            "JCX-45-25 puts the capped expenditure at $45.5B in FY2025 rising "
            "to $54.9B in FY2029, because raising the SALT cap to $40,000 took "
            "itemising claimants from 11.8M to 17.8M returns; Treasury's FY2027 "
            "edition gives $23.9B falling to $14.1B on the same statute. "
            "Choosing between them is an owner decision with a visible "
            "consequence for this row, not a provenance lane's.",
        ],
    },
    "repeal_salt_cap": {
        "description": "Repeal SALT $10K cap",
        "policy_factory": create_repeal_salt_cap,
        # Wave 4 target revision (repeal_salt_cap.v2). Penn Wharton Budget
        # Model, "Lifting the SALT Cap", Table 3, "Repeal SALT Cap":
        # -$1,169B over FY2025-2034 against an *extended-TCJA* baseline. The
        # superseded $1,100B was PWBM's FY2024-2033 figure rounded, and the
        # rounding hid the baseline the whole magnitude depends on.
        "expected_10yr": 1169.0,
        "source": "Penn Wharton Budget Model, Table 3 (Feb 2024)",
        "notes": (
            "Bipartisan proposal, benefits high-tax states. Scored against a "
            "permanent-cap (extended TCJA) baseline; against a baseline where "
            "the cap expires after 2025, PWBM's Table 1 scores the same "
            "repeal at $197B."
        ),
        "limitations": [
            "The target and this benchmark's twin `eliminate_salt` state "
            "opposite baselines: repeal is priced against a permanent $10,000 "
            "cap and elimination against CBO's world where the cap has "
            "lapsed. Both are now stated rather than hidden; reconciling them "
            "needs a baseline-vintage concept the expenditure module does not "
            "have.",
            "P.L. 119-21 sec. 70120 replaced the $10,000 cap with $40,000 for "
            "2025-2029 (indexed 1%/yr, phased down above $500,000 of MAGI, "
            "never below $10,000) reverting permanently to $10,000 in 2030, "
            "so 'repeal the $10,000 cap' describes no live reform for most of "
            "the window. JCT's own row for that provision is +$946.2B over "
            "FY2025-2034 and is already carried as `pl119_21_salt_cap_40k`.",
        ],
    },
    "eliminate_salt": {
        "description": "Eliminate SALT deduction entirely",
        "policy_factory": create_eliminate_salt_deduction,
        # Wave 4 target revision (eliminate_salt.v2). CBO, Options for
        # Reducing the Deficit: 2025 to 2034 (pub. 60557), Option 49, row
        # "Eliminate state and local tax deductions", $1,621.0B over
        # FY2025-2034 -- the same option this module's SALT `limitation`
        # block already cites for the cap's lapse date.
        "expected_10yr": -1621.0,
        "source": "CBO pub. 60557, Option 49 (report p. 59)",
        "notes": "Very controversial",
        "limitations": [
            "CBO measures the option on a baseline where the $10,000 cap "
            "lapses after 2025. P.L. 119-21 has since replaced that world "
            "with a $40,000 cap through 2029 reverting to $10,000 in 2030, so "
            "the target's baseline is no longer current law -- a model gap, "
            "not a target one, and one that needs a baseline-vintage concept "
            "the module does not have.",
        ],
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
# 3. **Provenance is not restated here.** A target's pedigree — whether anyone
#    has opened the document it supposedly comes from — lives in
#    ``benchmark_sources.py``, which is the single place the transcription was
#    done. These registries used to carry a ``provenance`` string of their own
#    and it went stale the moment the Phase E sourcing pass ran: 13 of the 17
#    were wrong afterwards. Read it with ``provenance_for(scenario_id)``.

INTERNATIONAL_VALIDATION_SCENARIOS_COMPARE = {
    "biden_gilti_reform": {
        "description": "Biden GILTI reform (country-by-country, 21%)",
        "preset": "\U0001f30d Biden GILTI Reform (-$374B)",
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
        "calibrated_to_target": False,
        "notes": "Country-by-country GILTI at 21% with QBAI eliminated.",
        "limitations": [
            "GILTI is modelled as an aggregate rate change on a single CFC income "
            "pool; the country-by-country mechanics that drive the Treasury proposal "
            "(per-jurisdiction blending, loss ring-fencing, the foreign tax credit "
            "haircut) are not represented. The jurisdictional distribution added for "
            "the base-overlap term is used for the overlap share only, not to set "
            "this level.",
            "Two of the constants behind this row describe themselves as fitted: "
            "gilti_cbc_revenue_multiplier 1.20 ('Treasury calibrated') and "
            "gilti_ftc_offset_rate 0.40 ('Calibration factor'). Treasury OTA prices "
            "the whole CFC active-income preference at $383,830M over FY2025-2034 "
            "against the module's implied $271B, which is the identity that would "
            "replace both.",
            "The target moved in Wave 4 (biden_gilti_reform.v1 -> .v2): it is "
            "now Treasury's own row, 'Revise the global minimum tax regime, "
            "limit inversions, and make related reforms', $373,919M over "
            "FY2025-2034, in place of a rounded -$280B with no table behind "
            "it. The row's proposal text matches this factory's shape "
            "(jurisdiction-by-jurisdiction, rate to 21%, QBAI eliminated) but "
            "its scope also covers the inversion and related-reform "
            "provisions the module does not implement, so the residual is an "
            "upper bound on the module's own miss. The two fitted constants "
            "above were set against the superseded figure and were "
            "deliberately not retuned.",
        ],
    },
    "fdii_repeal": {
        "description": "Repeal the FDII deduction",
        "preset": "\U0001f30d Repeal FDII (-$158B)",
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
        "calibrated_to_target": False,
        "notes": "Full repeal of the 37.5% FDII deduction.",
        "limitations": [
            "Scored by one base x rate identity — FDII income x the deduction rate x "
            "the statutory rate — on an income implied by Treasury OTA's own tax "
            "expenditure for the deduction ($130,230M over FY2025-2034, Tax "
            "Expenditures FY2026 Table 1 line 5). The module therefore reproduces "
            "that published cost by construction and the whole of this row's error "
            "is the distance between it and the carried target.",
            "The IRC 250(a)(3) step-down from a 37.5% to a 21.875% deduction in "
            "TY2026 is inside the published path the income base is inverted from, "
            "so the window average reflects it, but the module's scalar interface "
            "cannot say which years are which.",
            "No behavioural relocation of intangible property, and no interaction "
            "with the GILTI rate change. Treasury's own gross repeal row is "
            "$157,993M, 21% above their tax expenditure, because Green Book "
            "proposals are scored on a baseline already carrying the same volume's "
            "28% corporate rate.",
            "The target moved in Wave 4 (fdii_repeal.v1 -> .v2) from a rounded "
            "-$200B, which matched neither figure Treasury prints, to the "
            "gross row itself: $157,993M. Treasury pairs that row one-for-one "
            "with 'Provide additional support for research and development "
            "expenditures' and prints a subtotal of $0; the module scores "
            "repeal without the R&D offset, which is the gross row. Treasury "
            "scores it on a baseline that already carries the same volume's "
            "28% corporate rate, which is where its ~21% premium over the "
            "$13.023B/yr tax expenditure the module inverts comes from.",
        ],
    },
    "pillar_two_adoption": {
        "description": "Adopt OECD Pillar Two (15% global minimum)",
        "preset": "\U0001f30d Pillar Two Adoption (-$80B)",
        "policy_factory": create_pillar_two_adoption,
        "official_source": "Joint Committee on Taxation",
        "benchmark_date": "2023",
        "benchmark_url": None,
        "calibrated_to_target": False,
        "notes": "Qualified domestic minimum top-up tax at 15%.",
        "limitations": [
            "Poor: the module tops up a $120B undertaxed-profit pool with a 60% "
            "substance carve-out. JCT's estimate additionally embeds foreign adoption "
            "timing, transitional safe harbours, and the US GILTI receipts that get "
            "reassigned abroad once other jurisdictions apply the UTPR.",
            "The -$80B target is the midpoint of a range the module's own source note "
            "gives as $50-120B, so the model's -$61B sits inside the published range "
            "even though it rates Poor against the midpoint. JCT publishes no -$80B; "
            "the scenario this factory models — a US QDMTT and a Pillar-Two-compliant "
            "IIR with no US UTPR — is JCX-22-23 Table 2 Scenario 4 at +$102.6B over "
            "FY2023-2033, against which the model is 40% low.",
            "Every JCT scenario that raises revenue assumes the rest of the world "
            "does not enact. Under Scenario 2, where it does and the US follows, JCT "
            "scores US adoption at -$56.5B of receipts — a revenue loss, the opposite "
            "sign to this benchmark. Re-benchmarking against the range or a named "
            "scenario is provenance work, not a modelling change.",
        ],
    },
    "biden_full_international": {
        "description": "Biden international package (GILTI + FDII + UTPR)",
        "preset": "\U0001f30d Biden International Package (-$632B)",
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
        "calibrated_to_target": False,
        "notes": "Full package target; the module implements three of its provisions.",
        "limitations": [
            "Poor: the package covers GILTI + FDII + UTPR plus anti-inversion "
            "rules and several base-protection provisions the module does not "
            "implement. It scores only the three provisions it has. The target "
            "moved in Wave 4 (biden_full_international.v1 -> .v2) from a "
            "rounded -$700B to Treasury's own 'Subtotal, Reform International "
            "Taxation' of $632,200M, of which those three provisions are "
            "$510,232M — so about a fifth of the target is still provisions "
            "the module does not carry. The 'BEAT replacement' the old record "
            "named is not in the FY2025 volume at all: SHIELD was an FY2022 "
            "row that the UTPR replaced.",
            "The residual is a level, not an interaction. The module now carries a "
            "base-overlap term, but it nets zero here: _estimate_utpr scores "
            "foreign-parented profits and _estimate_gilti_reform scores US-parented "
            "CFC income, so this package's two minimum-tax provisions do not share a "
            "base. The overlap fires only when a policy pulls the GILTI and Pillar "
            "Two levers together, which no shipped preset does.",
            "The UTPR is the package's dominant miss: the module returns $15B over "
            "ten years where Treasury's own row is $136,313M and JCT's Scenario 5 "
            "less Scenario 4 prices one at $133.9B. Closing it means re-basing the "
            "UTPR on JCT's Equation 2 — the group's global low-taxed profit allocated "
            "to the US by an employee-and-tangible-asset key rather than profits "
            "booked in the US — which needs OECD country-by-country aggregates by "
            "ultimate-parent jurisdiction.",
            "FDII repeal is booked at $130B where Treasury's printed subtotal for the "
            "same provision is $0, because they pair it with an equal-and-opposite "
            "R&D support proposal the module does not implement. That overstatement "
            "and the UTPR understatement point in opposite directions.",
        ],
    },
}


TRADE_VALIDATION_SCENARIOS_COMPARE = {
    "trump_universal_10": {
        "description": "Trump universal 10% tariff",
        "preset": "\U0001f3ed Trump Universal 10% Tariff (-$2.17T)",
        "policy_factory": create_trump_universal_10,
        # Re-attributed in Phase E: the figure is Tax Foundation's (Fiscal Fact
        # 861, Table 3). Yale Budget Lab publishes no standalone ten-year
        # estimate for a 10% universal tariff, and the record's link was to
        # Yale's research index rather than to any document.
        "official_source": "Tax Foundation (Fiscal Fact 861)",
        "benchmark_date": "2025-04",
        "benchmark_url": (
            "https://taxfoundation.org/wp-content/uploads/2025/04/FF861.pdf"
        ),
        # Lane L8: no TRADE_BASELINE constant is fitted to this target any
        # more. The coverage rate is 1 minus the Canada-plus-Mexico share of
        # 2024 goods imports, and the score is net of the income-and-payroll
        # offset. The row's error rose from 1.1% to 37.1% as a result, which is
        # what the old figure was hiding.
        "calibrated_to_target": False,
        "notes": "10% outside the USMCA carve-out; scored net of offsets.",
        "limitations": [
            "Poor: the module carves out USMCA-qualifying Canadian and Mexican goods "
            "(1 - 28.03% of 2024 goods imports, Census) because every universal tariff "
            "actually proposed or imposed has done so. FF861 applies no carve-out - its "
            "Table 2 base is the whole $3,353.7B of goods imports - so the two are not "
            "scoring the same policy, and roughly two-fifths of the gap is that.",
            "The target is FF861's *conventional* column. The model's net figure sits "
            "between FF861's dynamic ($1,721B) and dynamic-with-retaliation ($1,443B) "
            "estimates, because it nets retaliation but carries no GDP feedback.",
            "The retaliation channel is a reduced form: an export-value loss converted "
            "at the app's marginal revenue rate, with no multiplier and no supply-chain "
            "effect. It returns about $111B over ten years against FF861 p. 2's $278B.",
        ],
    },
    "trump_china_60": {
        "description": "Trump 60% China tariff",
        "preset": "\U0001f3ed Trump 60% China Tariff (-$500B)",
        "policy_factory": create_trump_china_60,
        "official_source": "Tax Foundation",
        "benchmark_date": "2024",
        "benchmark_url": None,
        # Lane L8: the fitted 50% coverage constant is deleted. The rate is
        # now incremental over the duty Census says China's imports actually
        # pay (10.93% in 2024), applied to the whole base. Error 6.2% -> 44.3%.
        "calibrated_to_target": False,
        "notes": "60% on Chinese imports, incremental over the 10.9% collected in 2024.",
        "limitations": [
            "Poor, and against a target that is itself untraceable: -$500B exceeds "
            "CRFB's upper bound by two-thirds and is only obtainable as a residual from "
            "a Tax Foundation bundle (see benchmark_sources.py). The model now returns "
            "-$278B, inside CRFB's stated range rather than above it.",
            "A 49pp rate change sits well past the 30pp threshold where the elasticity "
            "doubles, so most of the movement is the volume response: imports fall to "
            "32% of base. That is the least well-identified part of the chain.",
            "Trade diversion through third countries — the dominant response in the "
            "2018-2019 episode — is captured only through a single elasticity, and "
            "diverted goods pay no US duty at all in this model.",
        ],
    },
    "auto_tariff_25": {
        "description": "25% tariff on imported autos and parts",
        "preset": "\U0001f3ed 25% Auto Tariff (-$386B)",
        "policy_factory": create_auto_tariff_25,
        "official_source": "Tax Foundation (Trump Tariffs tracker, Table 5)",
        "benchmark_date": "2026-08",
        "benchmark_url": (
            "https://taxfoundation.org/research/all/federal/"
            "trump-tariffs-trade-war/"
        ),
        "calibrated_to_target": False,
        "notes": "USMCA share of HS-87 removed from the base before the rate is applied.",
        "limitations": [
            "The target moved in Wave 4 (auto_tariff_25.v1 -> .v2). The old "
            "-$100B was not a scorekeeper estimate: CRFB, its stated source, "
            "itemises no auto tariff anywhere, and the figure traces to a "
            "White House claim stated *per year* ('about $100 billion with "
            "the auto tariffs alone', 30 March 2025) carried in a ten-year "
            "column. It is now Tax Foundation's tracker row, 'Section 232 "
            "Autos, Heavy Trucks, Buses, and Parts', $386.2B conventional "
            "over 2026-2035.",
            "The transcribed row is not exactly this policy: it bundles heavy "
            "trucks and buses (at 10%, not 25%) and auto parts with passenger "
            "vehicles, and it reflects trade-deal carve-outs. Yale Budget Lab "
            "scores the tariff *as announced* at $600-650B over 2026-35, so "
            "the two published figures differ by 1.7x and the residual should "
            "be read against that spread rather than against a point.",
            "Census 2024 puts HS-87 (vehicles and parts) imports at $384.9B, "
            "of which $186.4B — 48.4% — comes from Canada and Mexico. The "
            "module's carve-out is generous: the March 2025 proclamation "
            "exempts only the US-content share of USMCA-qualifying vehicles, "
            "not the whole import value, so the real base is larger than the "
            "one scored here — and neither publisher applies a USMCA carve-out "
            "at all, modelling US-content exceptions instead.",
            "Not retuned: no TRADE_BASELINE constant was moved to close the "
            "gap the revised target opened.",
        ],
    },
    "steel_tariff_25": {
        "description": "25% tariff on steel and aluminium",
        "preset": "\U0001f3ed 25% Steel/Aluminum Tariff (-$60B)",
        "policy_factory": create_steel_tariff_25,
        "official_source": "Tax Foundation",
        "benchmark_date": "2024",
        "benchmark_url": None,
        "calibrated_to_target": False,
        "notes": "25pp net of the 3.06% Section 232 duty collected, on a $58.9B base.",
        "limitations": [
            "The Section 232 netting is now measured, not assumed: Census puts calculated "
            "duty on HS-72 plus HS-76 at 3.06% of imports for consumption in 2024, far "
            "below the 25%/10% statutory rates because Canada, Mexico and Australia were "
            "exempted and the EU, UK, Japan, Brazil and South Korea traded under quotas "
            "or product exclusions. The proposed 25% is incremental to that 3.06%.",
            "HS-72 plus HS-76 is a proxy for 'steel and aluminium'. Section 232 also "
            "reaches derivative products in HS-73 ($49.6B of imports at 5.63% collected), "
            "which are excluded here; including them would roughly triple the base.",
            "The target is unsourced and, after a second search, stays that "
            "way — recorded in target_revisions.EXAMINED_NOT_REVISED rather "
            "than moved. CBO_SCORE_MAP and PRESET_POLICIES used to spell this "
            "preset differently (-$60B under '25% Steel & Aluminum Tariff' "
            "against -$15B under '25% Steel/Aluminum Tariff'), so the two "
            "dictionaries never joined and the app showed no official score "
            "at all; Phase E reconciled the labels on -$60B. Wave 4 searched "
            "again and found why nothing exists: the 25% Section 232 rate was "
            "in force only from 12 March to 3 June 2025, when it doubled to "
            "50%, and no scorekeeper published a ten-year estimate for the "
            "ten-week regime. Tax Foundation's tracker carries only the 50% "
            "rate with copper folded in ($341.4B conventional, 2026-2035), "
            "CRFB's steel posts score derivative-rule changes rather than a "
            "base tariff, and CRS IN12519 carries no revenue estimate at all.",
        ],
    },
    "reciprocal_tariffs": {
        "description": "Reciprocal tariffs (~20pp average increase)",
        "preset": "\U0001f3ed Reciprocal Tariffs (-$1.5T)",
        "policy_factory": create_reciprocal_tariffs,
        "official_source": (
            "CRFB, 'How Much Will Trump's New Tariffs Raise?' (a published "
            "range across three modellers)"
        ),
        "benchmark_date": "2025-04",
        "benchmark_url": (
            "https://www.crfb.org/blogs/how-much-will-trumps-new-tariffs-raise"
        ),
        "calibrated_to_target": False,
        "notes": "Flat 20pp applied to half of all goods imports, scored net of offsets.",
        "limitations": [
            "'Reciprocal' is implemented as a flat 20pp on 50% of imports — the one "
            "shape assumption left in the trade module that is not a measurement. The "
            "published estimates apply partner-specific rates to partner-specific "
            "bases (a 10% floor rising to 50%, exempting steel, aluminium, autos and "
            "parts, copper, pharmaceuticals, semiconductors and lumber) and assume "
            "substantially larger trade diversion.",
            "The score is now net of avoidance, the income-and-payroll offset and "
            "retaliation, which is most of the distance between a gross customs figure "
            "and a published net score. GDP feedback is still absent, so the model's "
            "-$1,397B sits above where a fully dynamic estimate would land.",
            "The target moved in Wave 4 (reciprocal_tariffs.v1 -> .v2), and it "
            "moved to a *range* rather than to another point. The superseded "
            "-$1.2T was exactly Tax Foundation's *dynamic* score sitting in a "
            "scorecard whose every other target is conventional. CRFB's April "
            "2025 comparison prints three conventional estimates of the same "
            "announced schedule over FY2025-2034 — $1.8T (CRFB), $1.5T (Tax "
            "Foundation), $1.4T (Yale Budget Lab) — so the published target is "
            "[-$1,800B, -$1,400B]. The figure carried here is Tax Foundation's, "
            "the publisher this repository's other tariff benchmarks use, and "
            "it is an anchor inside the range rather than a selection among "
            "the three.",
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
        "preset": "\U0001f48a Universal Insulin Cap ($11B)",
        "policy_factory": create_insulin_cap_all,
        "official_source": "Congressional Budget Office",
        "benchmark_date": "2022",
        "benchmark_url": None,
        "calibrated_to_target": False,
        "notes": "$35/month cap extended from Medicare to private insurance.",
        "limitations": [
            "Read the sign before the percentage. The stored -$15B target points "
            "the wrong way: CBO scores a $35 cap extended to private plans at "
            "+$6.566B of outlays and -$4.793B of revenues over FY2022-2031, about "
            "+$11.4B ADDED to the deficit (publication 57957). The module now also "
            "scores it as a deficit increase, so the percent difference against "
            "this target is large *because* model and benchmark disagree about "
            "direction — it is not an accuracy statement in either direction.",
            "Against CBO's own +$11.4B the module's +$7.0B is the right sign and "
            "the right order of magnitude, about 39% below it. Two omitted "
            "channels explain most of that gap: induced utilisation, and growth in "
            "insulin cost and enrolment across the window, since ASPE's $734M of "
            "Part D out-of-pocket relief is a single 2020 figure held flat.",
            "Repaired in lane L7: _estimate_insulin_cap_deficit_effect now scores "
            "the federal share of a cost-sharing shift (Part D plan liability at "
            "Medicare's 74.5% basic-benefit subsidy share, plus the private "
            "market's premium increase at CBO's 32% marginal income-and-payroll "
            "offset) instead of crediting the whole retail-minus-cap differential "
            "for every insulin user to the federal budget.",
        ],
    },
    "international_reference_pricing": {
        "description": "International reference pricing for Medicare drugs",
        "preset": "\U0001f48a International Reference Pricing (-$100B)",
        "policy_factory": create_reference_pricing,
        "official_source": "RAND price-comparison study, extended by model estimate",
        "benchmark_date": "2021",
        "benchmark_url": None,
        "calibrated_to_target": False,
        "notes": "Cap Medicare drug prices at 120% of the OECD average.",
        "limitations": [
            "The -$100B target is a RAND-derived illustrative figure "
            "('RAND/Estimate' in the record), not a scored legislative proposal, "
            "and it is far below what any published score of a policy like this "
            "carries: CBO scored H.R. 3's cap at 120% of the average "
            "international market price — which reached a limited set of drugs, "
            "not the whole Medicare book — at about $456B over 2020-2029 "
            "(publication 55936). Most of this row's remaining error is the "
            "target, not the module.",
            "Repaired in lane L7: the identity now applies RAND's *net* brand "
            "price ratio (3.08x, RR-A788-3 p. 19) to a brand-only, "
            "rebate-netted Part D base plus ASP-priced Part B drugs, and books "
            "only the federal share of each (Part D 76.3%, Part B 60%). It used "
            "to apply the all-drug *gross list* ratio 2.56x to all $275B of "
            "Medicare drug spending, including the generics where US prices are "
            "already 33% below the OECD comparison.",
            "The implied cut in net brand prices, about 61%, is close to the "
            "roughly 55% average net-price reduction CBO estimated for H.R. 3's "
            "first negotiated group, so the residual is a base question rather "
            "than a price question.",
            "Still missing: RAND's index is computed on presentations sold in "
            "both markets, and the module applies it to all brand spending, so "
            "the reachable base is overstated. No utilisation, launch-delay or "
            "availability response is modelled either.",
        ],
    },
}


ENFORCEMENT_VALIDATION_SCENARIOS_COMPARE = {
    "ira_enforcement": {
        "description": "IRA IRS enforcement funding ($80B/10yr)",
        "preset": "\U0001f50d IRA Enforcement Funding (-$180B)",
        "policy_factory": create_ira_enforcement,
        "official_source": (
            "Congressional Budget Office, publication 58390 (August 2022)"
        ),
        "benchmark_date": "2022-08",
        "benchmark_url": "https://www.cbo.gov/publication/58390",
        "calibrated_to_target": True,
        "notes": "$80B of enforcement funding with a 3-year ramp.",
        "limitations": [
            "The ROI path is a single marginal revenue-per-dollar multiplier (5.0, "
            "chosen to land on the *superseded* target) with a ramp. CBO's estimate "
            "separates enforcement, operations support, taxpayer services and systems "
            "modernisation, only part of which yields revenue.",
            "The target moved in Wave 4 (ira_enforcement.v1 -> .v2) to CBO's "
            "own current figure — 'revenues will increase by $180.4 billion "
            "over the 2022-2031 period' — which explicitly revises the $203.7B "
            "the superseded -$200B sat 2% below.",
            "Both the target and the model score the *revenue* side. CBO's net "
            "deficit effect is roughly $101B once the $79B appropriation is "
            "counted, and CBO says the act provides $79B of total IRS funding "
            "of which $46B is enforcement, where this module assumes $80B of "
            "enforcement funding — so the module prices a larger dose than the "
            "one CBO scored.",
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
            "Examined and deliberately not moved in Wave 4 "
            "(target_revisions.EXAMINED_NOT_REVISED). Treasury's American "
            "Families Plan Tax Compliance Agenda prints '$320 billion', 6% "
            "from the carried -$340B — but that is the yield on an $80B "
            "increase in the IRS budget scored on a *pre-IRA* baseline, where "
            "this preset scores ~$160B stacked on top of the IRA's $80B. "
            "Adopting it would produce a 6% agreement between two figures that "
            "are not estimates of the same reform.",
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
        "preset": "\U0001f331 Repeal EV Credits ($182B)",
        "policy_factory": create_repeal_ev_credits,
        # Re-attributed in Phase E: the published score of terminating the
        # clean-vehicle credits is JCT's (JCX-35-25), not CBO's.
        "official_source": "Joint Committee on Taxation (JCX-35-25)",
        "benchmark_date": "2025-07",
        "benchmark_url": (
            "https://www.jct.gov/getattachment/"
            "eb21dc77-6439-4fc3-8f5d-fc23a8c377e0/x-35-25.pdf"
        ),
        "calibrated_to_target": False,
        "notes": "Repeal of Sections 30D and 45W while other IRA credits stand.",
        "limitations": [
            "Scored as a $7,500 credit on a 1.5M-vehicle base growing 15%/yr; the "
            "income and vehicle-price caps, the separate used (25E) and commercial "
            "(45W) credits, and the demand response to withdrawing the subsidy are "
            "not modelled.",
            "The target moved in Wave 4 (repeal_ev_credits.v1 -> .v2) from a "
            "rounded -$200B to JCT's own two rows summed: sec. 30D ($77,829M) "
            "+ sec. 45W ($104,516M) = $182,345M over FY2025-2034, which is "
            "exactly this module's stated scope. Phase E transcribed that sum "
            "as $182.4B; it is $182.3B. Adding the used-vehicle credit "
            "(sec. 25E, $7.4B) would give $189.8B. For scale on how far this "
            "number has travelled, the repo's own knowledge base still gives a "
            "$30-60B range on the 2022 baseline and JCX-18-22 scored the same "
            "credits at $14.2B over FY2022-2031.",
        ],
    },
}
