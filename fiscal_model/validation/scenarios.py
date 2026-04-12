"""
Scenario registries for specialized validation suites.
"""

from ..amt import (
    create_extend_tcja_amt_relief,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
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
from ..estate import (
    create_biden_estate_proposal,
    create_eliminate_estate_tax,
    create_tcja_estate_extension,
)
from ..payroll import (
    create_expand_niit,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
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
        "step_up_exemption": 0.0,
        "gains_at_death_billions": 0.0,
        "notes": (
            "Without step-up, behavioral response is more moderate. "
            "PWBM $113B is for rate change only; step-up elimination revenue separate."
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
