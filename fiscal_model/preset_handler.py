"""
Preset policy handler for the Fiscal Policy Calculator.

Creates policy objects from preset configurations.
"""

from typing import Any

# Import policy factory functions
from fiscal_model import (
    create_biden_corporate_rate_only,
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_biden_estate_proposal,
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_ctc_permanent_extension,
    create_eliminate_estate_tax,
    create_eliminate_step_up_basis,
    create_expand_niit,
    create_extend_enhanced_ptc,
    create_extend_tcja_amt_relief,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
    create_repeal_ptc,
    create_repeal_salt_cap,
    create_republican_corporate_cut,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
    create_tcja_estate_extension,
    create_tcja_extension,
    create_tcja_repeal_salt_cap,
)
from fiscal_model.climate import (
    create_carbon_tax_25,
    create_carbon_tax_50,
    create_extend_ira,
    create_repeal_ev_credits,
    create_repeal_ira_credits,
)
from fiscal_model.enforcement import (
    create_double_enforcement,
    create_high_income_enforcement,
    create_ira_enforcement,
)
from fiscal_model.international import (
    create_biden_full_international,
    create_biden_gilti_reform,
    create_fdii_repeal,
    create_pillar_two_adoption,
)
from fiscal_model.pharma import (
    create_comprehensive_pharma_reform,
    create_expand_drug_negotiation,
    create_insulin_cap_all,
    create_reference_pricing,
)
from fiscal_model.trade import (
    create_auto_tariff_25,
    create_reciprocal_tariffs,
    create_steel_tariff_25,
    create_trump_china_60,
    create_trump_universal_10,
)


def create_policy_from_preset(preset_data: dict) -> Any | None:
    """
    Create a policy object from preset configuration data.

    Args:
        preset_data: Dictionary containing preset configuration with keys like
                     is_tcja, is_corporate, is_credit, etc. and type-specific
                     keys like tcja_type, corporate_type, etc.

    Returns:
        Policy object if preset_data matches a known policy type, None otherwise
    """
    if preset_data.get("is_tcja", False):
        return _create_tcja_policy(preset_data)

    elif preset_data.get("is_corporate", False):
        return _create_corporate_policy(preset_data)

    elif preset_data.get("is_credit", False):
        return _create_credit_policy(preset_data)

    elif preset_data.get("is_estate", False):
        return _create_estate_policy(preset_data)

    elif preset_data.get("is_payroll", False):
        return _create_payroll_policy(preset_data)

    elif preset_data.get("is_amt", False):
        return _create_amt_policy(preset_data)

    elif preset_data.get("is_ptc", False):
        return _create_ptc_policy(preset_data)

    elif preset_data.get("is_expenditure", False):
        return _create_expenditure_policy(preset_data)

    elif preset_data.get("is_international", False):
        return _create_international_policy(preset_data)

    elif preset_data.get("is_enforcement", False):
        return _create_enforcement_policy(preset_data)

    elif preset_data.get("is_pharma", False):
        return _create_pharma_policy(preset_data)

    elif preset_data.get("is_trade", False):
        return _create_trade_policy(preset_data)

    elif preset_data.get("is_climate", False):
        return _create_climate_policy(preset_data)

    # Not a complex preset - return None to indicate caller should handle
    return None


def _create_tcja_policy(preset_data: dict):
    """Create TCJA extension policy based on type."""
    tcja_type = preset_data.get("tcja_type", "full")

    if tcja_type == "full":
        return create_tcja_extension(extend_all=True, keep_salt_cap=True)
    elif tcja_type == "no_salt":
        return create_tcja_repeal_salt_cap()
    elif tcja_type == "rates_only":
        return create_tcja_extension(
            extend_all=False,
            extend_rate_cuts=True,
            extend_standard_deduction=False,
            keep_exemption_elimination=False,
            extend_passthrough=False,
            extend_ctc=False,
            extend_estate=False,
            extend_amt=False,
            keep_salt_cap=False,
        )
    else:
        return create_tcja_extension(extend_all=True)


def _create_corporate_policy(preset_data: dict):
    """Create corporate tax policy based on type."""
    corporate_type = preset_data.get("corporate_type", "biden_28")

    if corporate_type == "biden_28":
        return create_biden_corporate_rate_only()
    elif corporate_type == "trump_15":
        return create_republican_corporate_cut()
    else:
        return create_biden_corporate_rate_only()


def _create_credit_policy(preset_data: dict):
    """Create tax credit policy based on type."""
    credit_type = preset_data.get("credit_type", "biden_ctc_2021")

    if credit_type == "biden_ctc_2021":
        return create_biden_ctc_2021()
    elif credit_type == "ctc_extension":
        return create_ctc_permanent_extension()
    elif credit_type == "biden_eitc_childless":
        return create_biden_eitc_childless()
    else:
        return create_biden_ctc_2021()


def _create_estate_policy(preset_data: dict):
    """Create estate tax policy based on type."""
    estate_type = preset_data.get("estate_type", "extend_tcja")

    if estate_type == "extend_tcja":
        return create_tcja_estate_extension()
    elif estate_type == "biden_reform":
        return create_biden_estate_proposal()
    elif estate_type == "eliminate":
        return create_eliminate_estate_tax()
    else:
        return create_tcja_estate_extension()


def _create_payroll_policy(preset_data: dict):
    """Create payroll tax policy based on type."""
    payroll_type = preset_data.get("payroll_type", "cap_90")

    if payroll_type == "cap_90":
        return create_ss_cap_90_percent()
    elif payroll_type == "donut_250k":
        return create_ss_donut_hole()
    elif payroll_type == "eliminate_cap":
        return create_ss_eliminate_cap()
    elif payroll_type == "expand_niit":
        return create_expand_niit()
    else:
        return create_ss_cap_90_percent()


def _create_amt_policy(preset_data: dict):
    """Create AMT policy based on type."""
    amt_type = preset_data.get("amt_type", "extend_tcja")

    if amt_type == "extend_tcja":
        return create_extend_tcja_amt_relief()
    elif amt_type == "repeal_individual":
        # Use start_year=2026 to match CBO $450B estimate (post-TCJA sunset)
        return create_repeal_individual_amt(start_year=2026)
    elif amt_type == "repeal_corporate":
        return create_repeal_corporate_amt()
    else:
        return create_extend_tcja_amt_relief()


def _create_ptc_policy(preset_data: dict):
    """Create Premium Tax Credit policy based on type."""
    ptc_type = preset_data.get("ptc_type", "extend_enhanced")

    if ptc_type == "extend_enhanced":
        return create_extend_enhanced_ptc()
    elif ptc_type == "repeal":
        return create_repeal_ptc()
    else:
        return create_extend_enhanced_ptc()


def _create_expenditure_policy(preset_data: dict):
    """Create tax expenditure policy based on type."""
    expenditure_type = preset_data.get("expenditure_type", "cap_employer_health")

    if expenditure_type == "cap_employer_health":
        return create_cap_employer_health_exclusion()
    elif expenditure_type == "repeal_salt_cap":
        return create_repeal_salt_cap()
    elif expenditure_type == "eliminate_step_up":
        return create_eliminate_step_up_basis()
    elif expenditure_type == "cap_charitable":
        return create_cap_charitable_deduction()
    else:
        return create_cap_employer_health_exclusion()


def _create_international_policy(preset_data: dict):
    """Create international tax policy based on type."""
    intl_type = preset_data.get("international_type", "biden_gilti")

    if intl_type == "biden_gilti":
        return create_biden_gilti_reform()
    elif intl_type == "fdii_repeal":
        return create_fdii_repeal()
    elif intl_type == "pillar_two":
        return create_pillar_two_adoption()
    elif intl_type == "biden_full":
        return create_biden_full_international()
    else:
        return create_biden_gilti_reform()


def _create_enforcement_policy(preset_data: dict):
    """Create IRS enforcement policy based on type."""
    enforcement_type = preset_data.get("enforcement_type", "ira")

    if enforcement_type == "ira":
        return create_ira_enforcement()
    elif enforcement_type == "double":
        return create_double_enforcement()
    elif enforcement_type == "high_income":
        return create_high_income_enforcement()
    else:
        return create_ira_enforcement()


def _create_pharma_policy(preset_data: dict):
    """Create pharmaceutical pricing policy based on type."""
    pharma_type = preset_data.get("pharma_type", "expand_negotiation")

    if pharma_type == "expand_negotiation":
        return create_expand_drug_negotiation()
    elif pharma_type == "insulin_cap":
        return create_insulin_cap_all()
    elif pharma_type == "reference_pricing":
        return create_reference_pricing()
    elif pharma_type == "comprehensive":
        return create_comprehensive_pharma_reform()
    else:
        return create_expand_drug_negotiation()


def _create_trade_policy(preset_data: dict):
    """Create trade/tariff policy based on type."""
    trade_type = preset_data.get("trade_type", "universal_10")

    if trade_type == "universal_10":
        return create_trump_universal_10()
    elif trade_type == "china_60":
        return create_trump_china_60()
    elif trade_type == "auto_25":
        return create_auto_tariff_25()
    elif trade_type == "steel_25":
        return create_steel_tariff_25()
    elif trade_type == "reciprocal":
        return create_reciprocal_tariffs()
    else:
        raise ValueError(f"Unknown trade_type: {trade_type}")


def _create_climate_policy(preset_data: dict):
    """Create climate/energy policy based on type."""
    climate_type = preset_data.get("climate_type", "carbon_50")

    if climate_type == "repeal_ira":
        return create_repeal_ira_credits()
    elif climate_type == "carbon_50":
        return create_carbon_tax_50()
    elif climate_type == "carbon_25":
        return create_carbon_tax_25()
    elif climate_type == "repeal_ev":
        return create_repeal_ev_credits()
    elif climate_type == "extend_ira":
        return create_extend_ira()
    else:
        raise ValueError(f"Unknown climate_type: {climate_type}")
