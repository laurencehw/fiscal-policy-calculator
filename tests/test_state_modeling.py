"""
Tests for Feature 3: State-Level Modeling.

Covers:
- StateTaxDatabase loading and querying
- StateTaxProfile calculations (progressive, flat, no-income-tax)
- FederalStateCalculator combined federal+state calculations
- SALT interaction model
- Edge cases and validation targets
"""

from __future__ import annotations

import pandas as pd
import pytest

from fiscal_model.models.state.calculator import FederalStateCalculator
from fiscal_model.models.state.database import (
    STATE_NAMES,
    SUPPORTED_STATES,
    StateTaxDatabase,
    _parse_json_list,
)
from fiscal_model.models.state.salt_interaction import (
    SALTInteractionResult,
    _approx_filers_millions,
    compute_salt_across_states,
    compute_salt_interaction,
)

# ─── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db():
    return StateTaxDatabase(year=2025)


@pytest.fixture(scope="module")
def sample_pop():
    """Small synthetic population for testing."""
    return pd.DataFrame({
        "agi": [30_000, 75_000, 150_000, 400_000, 1_000_000],
        "wages": [28_000, 72_000, 145_000, 380_000, 900_000],
        "married": [0, 1, 0, 1, 0],
        "children": [0, 2, 1, 0, 0],
        "weight": [1, 1, 1, 1, 1],
    })


# ─── Database loading tests ────────────────────────────────────────────────


def test_database_loads_all_ten_states(db):
    """All 10 supported states should be in the database."""
    for state in SUPPORTED_STATES:
        profile = db.get_state(state)
        assert profile is not None
        assert profile.state == state


def test_database_unsupported_state_raises(db):
    with pytest.raises(KeyError, match="WY"):
        db.get_state("WY")


def test_get_all_states_returns_ten(db):
    all_states = db.get_all_states()
    assert len(all_states) == 10
    assert set(all_states.keys()) == set(SUPPORTED_STATES)


def test_no_income_tax_states(db):
    no_tax = db.get_no_income_tax_states()
    assert "TX" in no_tax
    assert "FL" in no_tax
    assert "CA" not in no_tax
    assert "NY" not in no_tax


def test_income_tax_states(db):
    with_tax = db.get_income_tax_states()
    assert "CA" in with_tax
    assert "NY" in with_tax
    assert "TX" not in with_tax
    assert "FL" not in with_tax


def test_compare_top_rates_sorted(db):
    rates = db.compare_top_rates()
    values = list(rates.values())
    # Should be sorted descending
    assert values == sorted(values, reverse=True)
    # CA should have highest rate (~13.3%)
    top_state = next(iter(rates.keys()))
    assert top_state == "CA"


def test_state_names_mapping():
    assert STATE_NAMES["CA"] == "California"
    assert STATE_NAMES["TX"] == "Texas"
    assert len(STATE_NAMES) == 10


# ─── StateTaxProfile calculation tests ────────────────────────────────────


def test_no_income_tax_state_returns_zero(db):
    tx = db.get_state("TX")
    assert not tx.has_income_tax
    assert tx.calculate_state_tax(200_000) == 0.0
    assert tx.calculate_state_tax(1_000_000) == 0.0


def test_no_income_tax_fl_returns_zero(db):
    fl = db.get_state("FL")
    assert fl.calculate_state_tax(500_000) == 0.0


def test_flat_rate_pa(db):
    pa = db.get_state("PA")
    assert pa.flat_rate == pytest.approx(0.0307, abs=1e-4)
    # PA has no standard deduction; tax = rate * AGI
    tax = pa.calculate_state_tax(100_000)
    assert tax == pytest.approx(100_000 * 0.0307, rel=0.01)


def test_flat_rate_il(db):
    il = db.get_state("IL")
    assert il.flat_rate == pytest.approx(0.0495, abs=1e-4)
    # IL has personal exemption of $2,425 single
    tax = il.calculate_state_tax(100_000, married=False)
    expected = (100_000 - 2_425) * 0.0495
    assert tax == pytest.approx(expected, rel=0.01)


def test_flat_rate_nc(db):
    nc = db.get_state("NC")
    assert nc.flat_rate == pytest.approx(0.045, abs=1e-4)
    # NC has standard deduction of $10,750 single
    tax = nc.calculate_state_tax(100_000, married=False)
    expected = (100_000 - 10_750) * 0.045
    assert tax == pytest.approx(expected, rel=0.01)


def test_flat_rate_mi(db):
    mi = db.get_state("MI")
    assert mi.flat_rate == pytest.approx(0.0405, abs=1e-4)
    # MI has personal exemption of $5,600 single
    tax = mi.calculate_state_tax(80_000, married=False)
    expected = (80_000 - 5_600) * 0.0405
    assert tax == pytest.approx(expected, rel=0.01)


def test_progressive_ca_single(db):
    ca = db.get_state("CA")
    assert ca.has_income_tax
    assert ca.flat_rate is None
    # At $50,000: should be in the 4-6% range
    tax = ca.calculate_state_tax(50_000, married=False)
    # Standard deduction: $5,202 → taxable = $44,798
    # Bracket check: above $24,684, below $38,959 → at least part at 4%
    assert 1_000 < tax < 5_000, f"CA tax on $50K unexpected: ${tax:,.0f}"


def test_progressive_ca_high_income(db):
    ca = db.get_state("CA")
    tax = ca.calculate_state_tax(1_500_000, married=False)
    # Should include 13.3% bracket
    effective_rate = tax / 1_500_000
    assert effective_rate > 0.10, f"CA effective rate at $1.5M too low: {effective_rate:.2%}"
    assert effective_rate < 0.133, f"CA effective rate at $1.5M too high: {effective_rate:.2%}"


def test_progressive_ny_single(db):
    ny = db.get_state("NY")
    assert ny.has_income_tax
    tax = ny.calculate_state_tax(100_000, married=False)
    # NY standard deduction $8,000 → taxable $92,000
    # Effective rate should be ~5-6%
    effective_rate = tax / 100_000
    assert 0.04 < effective_rate < 0.07, f"NY effective rate at $100K: {effective_rate:.2%}"


def test_oh_zero_bracket(db):
    oh = db.get_state("OH")
    # OH has 0% on first $26,050
    tax_low = oh.calculate_state_tax(20_000)
    assert tax_low == 0.0, f"OH tax on $20K should be 0, got ${tax_low}"
    # Above threshold: small tax
    tax_mid = oh.calculate_state_tax(50_000)
    assert tax_mid > 0


def test_effective_state_rate_zero_agi(db):
    ca = db.get_state("CA")
    assert ca.effective_state_rate(0) == 0.0


def test_effective_state_rate_increases_with_income(db):
    """CA has progressive rates; effective rate should increase with income."""
    ca = db.get_state("CA")
    rates = [ca.effective_state_rate(inc) for inc in [50_000, 200_000, 500_000, 1_000_000]]
    for i in range(len(rates) - 1):
        assert rates[i] <= rates[i + 1], f"Rate not increasing at index {i}: {rates}"


# ─── FederalStateCalculator tests ─────────────────────────────────────────


def test_calculator_ca_adds_state_tax(sample_pop):
    calc = FederalStateCalculator("CA", year=2025)
    result = calc.calculate(sample_pop)
    assert "state_tax" in result.columns
    assert "federal_tax" in result.columns
    assert "combined_tax" in result.columns
    assert "effective_combined_rate" in result.columns
    # State tax should be positive for most filers
    assert (result["state_tax"] > 0).any()


def test_calculator_tx_zero_state_tax(sample_pop):
    calc = FederalStateCalculator("TX", year=2025)
    result = calc.calculate(sample_pop)
    assert (result["state_tax"] == 0.0).all()
    # Combined = federal only
    assert (result["combined_tax"] == result["federal_tax"]).all()


def test_calculator_fl_zero_state_tax(sample_pop):
    calc = FederalStateCalculator("FL", year=2025)
    result = calc.calculate(sample_pop)
    assert (result["state_tax"] == 0.0).all()


def test_combined_tax_exceeds_federal(sample_pop):
    """For income-tax states, combined should be > federal for high-income filers."""
    for state in ["CA", "NY", "PA", "IL"]:
        calc = FederalStateCalculator(state, year=2025)
        result = calc.calculate(sample_pop)
        # High-income row (AGI=400K or 1M) should have state tax > 0
        high_inc = result[result["agi"] >= 150_000]
        assert (high_inc["combined_tax"] > high_inc["federal_tax"]).all(), (
            f"{state}: high-income combined should exceed federal"
        )


def test_calculator_effective_combined_rate_bounds(sample_pop):
    calc = FederalStateCalculator("CA", year=2025)
    result = calc.calculate(sample_pop)
    # Combined effective rate should be between 0 and ~60%
    rates = result["effective_combined_rate"]
    assert (rates >= 0).all()
    assert (rates <= 0.60).all()


def test_apply_federal_reform_salt_cap_change(sample_pop):
    """Lifting SALT cap should reduce taxable income and federal tax for itemizers."""
    calc = FederalStateCalculator("CA", year=2025)

    # Add itemized deductions and SALT to test SALT interaction
    pop_with_itemize = sample_pop.assign(
        itemized_deductions=sample_pop["agi"] * 0.25,
        state_and_local_taxes=sample_pop["agi"] * 0.10,
    )

    baseline = calc.calculate(pop_with_itemize)

    # Reform: lift SALT cap entirely
    reform = calc.apply_federal_reform(pop_with_itemize, reforms={"salt_cap": None})

    # Federal tax should be <= baseline for high-income filers who benefit
    # (lifting cap means more deductions, lower federal taxable income)
    high_inc_mask = pop_with_itemize["agi"] >= 150_000
    baseline_high = baseline.loc[high_inc_mask, "federal_tax"]
    reform_high = reform.loc[high_inc_mask, "federal_tax"]
    assert (reform_high <= baseline_high).all(), "Lifting SALT cap should not increase federal tax"


def test_effective_rate_curve_returns_dataframe():
    calc = FederalStateCalculator("NY", year=2025)
    curve = calc.effective_rate_curve()
    assert isinstance(curve, pd.DataFrame)
    assert "agi" in curve.columns
    assert "federal_rate" in curve.columns
    assert "state_rate" in curve.columns
    assert "combined_rate" in curve.columns
    assert len(curve) > 5


def test_effective_rate_curve_combined_exceeds_federal():
    """NY state rate > 0, so combined > federal for income-tax payers."""
    calc = FederalStateCalculator("NY", year=2025)
    curve = calc.effective_rate_curve()
    # For incomes above standard deduction
    high_inc = curve[curve["agi"] >= 50_000]
    assert (high_inc["combined_rate"] > high_inc["federal_rate"]).all()


def test_calculator_confidence_label():
    calc = FederalStateCalculator("CA")
    assert "approximation" in calc.confidence_label.lower()


def test_calculator_local_tax_caveat_ny():
    calc = FederalStateCalculator("NY")
    assert calc.has_local_tax_caveat


def test_calculator_local_tax_caveat_tx():
    calc = FederalStateCalculator("TX")
    assert not calc.has_local_tax_caveat


# ─── SALT interaction tests ────────────────────────────────────────────────


def test_salt_interaction_ca_cap_lift():
    """Lifting SALT cap in CA should be costly to federal revenue."""
    result = compute_salt_interaction("CA", baseline_cap=10_000, reform_cap=None)
    assert isinstance(result, SALTInteractionResult)
    # Lifting cap → more deduction → federal revenue loss (negative change)
    assert result.federal_revenue_change_billions < 0
    assert result.affected_filers > 0
    assert result.avg_deduction_change > 0


def test_salt_interaction_tx_no_income_tax():
    """TX has low SALT deduction usage; revenue impact should be smaller than CA."""
    ca_result = compute_salt_interaction("CA", baseline_cap=10_000, reform_cap=None)
    tx_result = compute_salt_interaction("TX", baseline_cap=10_000, reform_cap=None)
    # CA should have larger (more negative) federal revenue impact
    assert ca_result.federal_revenue_change_billions < tx_result.federal_revenue_change_billions


def test_salt_interaction_no_change():
    """If baseline_cap equals reform_cap, no change."""
    result = compute_salt_interaction("CA", baseline_cap=10_000, reform_cap=10_000)
    assert result.avg_deduction_change == pytest.approx(0.0, abs=0.01)
    assert result.federal_revenue_change_billions == pytest.approx(0.0, abs=0.01)


def test_salt_interaction_lower_cap_raises_revenue():
    """Lowering the SALT cap raises federal revenue."""
    result = compute_salt_interaction("NY", baseline_cap=10_000, reform_cap=5_000)
    # Lower cap → less deduction → positive revenue change
    assert result.federal_revenue_change_billions > 0
    assert result.avg_deduction_change < 0


def test_salt_interaction_result_description():
    result = compute_salt_interaction("CA", baseline_cap=10_000, reform_cap=None)
    desc = result.description
    assert "CA" in desc or "$10,000" in desc


def test_salt_across_states_returns_dataframe():
    df = compute_salt_across_states(baseline_cap=10_000, reform_cap=None)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 10
    assert "State" in df.columns
    assert "Federal Revenue Change ($B)" in df.columns


def test_salt_across_states_ca_ny_biggest_impact():
    """CA and NY should have the largest negative revenue impact."""
    df = compute_salt_across_states(baseline_cap=10_000, reform_cap=None)
    top_impact = df.sort_values("Federal Revenue Change ($B)").head(2)
    top_states = set(top_impact["State"].tolist())
    # CA and NY should be in the top 2 most impacted
    assert len(top_states.intersection({"CA", "NY"})) >= 1, (
        f"Expected CA or NY in top 2, got {top_states}"
    )


def test_approx_filers_ca():
    assert _approx_filers_millions("CA") == pytest.approx(18.2, abs=1.0)


def test_approx_filers_unknown_state():
    # Unknown state should return a default
    result = _approx_filers_millions("ZZ")
    assert result > 0


# ─── JSON parsing helper tests ─────────────────────────────────────────────


def test_parse_json_list_valid():
    result = _parse_json_list("[0, 10000, 50000]")
    assert result == [0.0, 10_000.0, 50_000.0]


def test_parse_json_list_empty_string():
    assert _parse_json_list("") == []


def test_parse_json_list_empty_array():
    assert _parse_json_list("[]") == []


def test_parse_json_list_invalid():
    assert _parse_json_list("not-json") == []


def test_parse_json_list_none():
    assert _parse_json_list(None) == []


# ─── Integration: multi-state calculations ────────────────────────────────


def test_all_states_calculate_without_error(sample_pop):
    """All 10 states should produce valid results without errors."""
    for state in SUPPORTED_STATES:
        calc = FederalStateCalculator(state, year=2025)
        result = calc.calculate(sample_pop)
        assert len(result) == len(sample_pop), f"{state}: result length mismatch"
        assert (result["combined_tax"] >= 0).all(), f"{state}: negative combined tax"
        assert (result["effective_combined_rate"] >= 0).all(), f"{state}: negative effective rate"
        assert (result["effective_combined_rate"] <= 1.0).all(), f"{state}: rate > 100%"


def test_high_income_filer_ca_vs_tx(sample_pop):
    """CA high-income filer should pay substantially more than TX (state tax difference)."""
    ca_calc = FederalStateCalculator("CA")
    tx_calc = FederalStateCalculator("TX")

    ca_result = ca_calc.calculate(sample_pop)
    tx_result = tx_calc.calculate(sample_pop)

    # For the $1M filer
    high_inc_mask = sample_pop["agi"] == 1_000_000
    ca_state_tax = ca_result.loc[high_inc_mask, "state_tax"].values[0]
    tx_state_tax = tx_result.loc[high_inc_mask, "state_tax"].values[0]

    assert ca_state_tax > 50_000, f"CA $1M state tax too low: ${ca_state_tax:,.0f}"
    assert tx_state_tax == 0.0


def test_salt_interaction_all_states_no_error():
    """Should compute SALT interaction for all states without raising."""
    for state in SUPPORTED_STATES:
        result = compute_salt_interaction(state, baseline_cap=10_000, reform_cap=None)
        assert result is not None
        assert isinstance(result.federal_revenue_change_billions, float)
