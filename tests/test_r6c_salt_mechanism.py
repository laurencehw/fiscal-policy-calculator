"""R6c: the statutory AMT, the SOI SALT imputation, and the calibrated default.

See planning/lanes/R6c_salt_mechanism_and_calibration_default.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fiscal_model.microsim.engine import MicroTaxCalculator
from fiscal_model.microsim.salt_imputation import (
    _FALLBACK_SALT_RATE,
    impute_salt_and_itemized,
    soi_itemized_ratios,
)


def _unit(**kw) -> pd.DataFrame:
    row = {
        "id": 1, "weight": 1.0, "wages": 0.0, "interest_income": 0.0,
        "dividend_income": 0.0, "capital_gains": 0.0, "social_security": 0.0,
        "unemployment": 0.0, "children": 0, "married": 1, "age_head": 55,
        "agi": 0.0,
    }
    row.update(kw)
    return pd.DataFrame([row])


# ── AMT parameters are the transcribed statute ──────────────────────────────
def test_amt_parameters_match_the_transcribed_tables():
    from fiscal_model.amt import load_statutory_amt_parameters
    from fiscal_model.cbo_tax_parameters import parameter

    calc = MicroTaxCalculator()
    row = load_statutory_amt_parameters()["tcja"][2025]
    assert (calc.amt_exemption_single, calc.amt_exemption_married) == row.exemption[:2]
    assert (
        calc.amt_phaseout_threshold_single,
        calc.amt_phaseout_threshold_married,
    ) == row.phase_out_threshold[:2]
    assert calc.amt_phaseout_rate == row.phase_out_rate
    for status in ("mfj", "single"):
        assert calc.amt_threshold == parameter("cbo_jan_2025", f"tp_amt_bracket_2_{status}", 2025)


# ── AMT mechanics ───────────────────────────────────────────────────────────
def test_exemption_is_fully_phased_out_at_high_amti():
    calc = MicroTaxCalculator()
    # 1,252,700 + 137,000 / 0.25 = 1,800,700: exemption is gone above it.
    df = calc.calculate(_unit(agi=3_000_000.0, wages=3_000_000.0))
    base = 3_000_000.0
    expected = 239_100 * 0.26 + (base - 239_100) * 0.28
    assert df["amt_tax"].iloc[0] == pytest.approx(expected)


def test_gains_are_taxed_at_capital_gains_rates_inside_the_amt():
    """§55(b)(3): $4.5M of gains on a $5M return is taxed at 20% inside the
    AMT, not 28%. Before R6c the whole base took 26/28%: $1,395,220."""
    calc = MicroTaxCalculator()
    df = calc.calculate(
        _unit(agi=5_000_000.0, wages=500_000.0, capital_gains=4_500_000.0)
    )
    ordinary = 239_100 * 0.26 + (500_000 - 239_100) * 0.28
    # Gains stack on the $500,000 ordinary base: 15% up to $600,050, 20% above.
    gains = 100_050 * 0.15 + (4_500_000 - 100_050) * 0.20
    assert df["amt_tax"].iloc[0] == pytest.approx(ordinary + gains)


def test_amti_adds_back_salt_but_allows_other_itemized_deductions():
    calc = MicroTaxCalculator()
    pop = _unit(
        agi=400_000.0, wages=400_000.0,
        state_and_local_taxes=40_000.0, itemized_deductions=100_000.0,
    )
    df = calc.calculate(pop, salt_cap=None)
    # AMTI = 400,000 - (100,000 - 40,000) = 340,000; exemption 137,000 unphased.
    base = 340_000.0 - 137_000.0
    assert df["amt_tax"].iloc[0] == pytest.approx(base * 0.26)


def test_breakpoint_does_not_depend_on_who_else_is_in_the_frame():
    """The old engine halved the 26% band for everyone in a frame with no
    married row."""
    calc = MicroTaxCalculator()
    single = _unit(agi=2_000_000.0, wages=2_000_000.0, married=0)
    both = pd.concat([single, _unit(agi=50_000.0, wages=50_000.0, id=2)], ignore_index=True)
    alone = calc.calculate(single)["amt_tax"].iloc[0]
    mixed = calc.calculate(both)["amt_tax"].iloc[0]
    assert alone == pytest.approx(mixed)


# ── SALT imputation reads SOI Table 2.1 ─────────────────────────────────────
def test_imputation_reproduces_the_soi_class_ratios_at_the_national_rate():
    ratios = soi_itemized_ratios()
    agi = np.array([75_000.0, 300_000.0, 3_000_000.0])
    pop = pd.DataFrame({"agi": agi})  # no state: national rate, scale 1
    out = impute_salt_and_itemized(pop)
    cls = np.searchsorted(ratios["agi_lower"].to_numpy(), agi, side="right") - 1
    np.testing.assert_allclose(
        out["state_and_local_taxes"].to_numpy(), agi * ratios["salt_ratio"].to_numpy()[cls]
    )
    np.testing.assert_allclose(
        (out["itemized_deductions"] - out["state_and_local_taxes"]).to_numpy(),
        agi * ratios["other_ratio"].to_numpy()[cls],
    )


def test_soi_salt_share_is_above_the_old_flat_rate_below_5m():
    """The shipped imputation used 5.76% of AGI at every income. Among SOI
    itemizers the SALT share falls with income but stays above that from
    $100K to $5M, which is where the old imputation under-counted the benefit."""
    r = soi_itemized_ratios().set_index("agi_lower")["salt_ratio"]
    band = r.loc[100_000:2_000_000]
    assert (band > _FALLBACK_SALT_RATE).all()
    assert band.is_monotonic_decreasing


def test_state_scaling_is_relative_to_the_national_rate():
    from fiscal_model.microsim.salt_imputation import _DEFAULT_SALT_PATH, _salt_rate_by_state

    ny = _salt_rate_by_state(_DEFAULT_SALT_PATH)["NY"]
    pop = pd.DataFrame({"agi": [300_000.0, 300_000.0], "state_fips": [36, 99]})
    out = impute_salt_and_itemized(pop)
    salt = out["state_and_local_taxes"].to_numpy()
    assert salt[0] / salt[1] == pytest.approx(ny / _FALLBACK_SALT_RATE)


# ── One default population, read by every microsim surface ─────────────────
@pytest.fixture(scope="module")
def default_population():
    from fiscal_model.microsim.population import load_default_population

    return load_default_population()


def test_default_population_is_the_cell_calibrated_frame(default_population):
    from fiscal_model.data.cps_asec import load_tax_microdata
    from fiscal_model.microsim.population import DEFAULT_CALIBRATION_YEAR
    from fiscal_model.microsim.soi_calibration import calibrate_to_soi

    raw, _ = load_tax_microdata()
    assert len(default_population) != len(raw)
    summary = calibrate_to_soi(default_population, year=DEFAULT_CALIBRATION_YEAR).summary()
    assert summary["returns_coverage_pct"] == pytest.approx(100.0, abs=0.5)


def test_routed_readers_read_the_default_population(default_population):
    from fiscal_model import credits_microdata, package_interactions

    assert len(package_interactions._population()) == len(default_population)
    assert len(credits_microdata._base_population()) == len(default_population)


def test_distribution_engine_reads_the_default_population(monkeypatch, default_population):
    import fiscal_model.microsim.population as population_mod
    from fiscal_model.distribution_engine import DistributionalEngine
    from fiscal_model.policies import PolicyType, TaxPolicy

    calls = []

    def spy(path=None):
        calls.append(path)
        return default_population.copy()

    monkeypatch.setattr(population_mod, "load_default_population", spy)
    policy = TaxPolicy(
        name="t", description="t", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01, affected_income_threshold=400_000,
    )
    DistributionalEngine().analyze_policy_microsim(policy)
    assert calls == [None]


def test_salt_distributional_row_is_at_its_preregistered_value():
    from fiscal_model.validation.benchmark_runners import default_model_runner
    from fiscal_model.validation.cbo_distributions import (
        CBO_JCT_BENCHMARKS,
        compare_distribution,
    )

    bench = next(b for b in CBO_JCT_BENCHMARKS if b.policy_id == "jct_salt_repeal_2024")
    cmp = compare_distribution(default_model_runner(bench), bench)
    assert cmp.mean_absolute_share_error_pp == pytest.approx(5.6541, abs=5e-5)
