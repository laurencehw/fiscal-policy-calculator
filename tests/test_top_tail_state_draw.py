"""R6b: synthetic top-tail rows draw their state from the CPS, not a California stamp.

``planning/lanes/R6b_make_calibration_default_preregistration.md`` §1. Opt-in
``by_status`` path only; the default ``augment_top_tail`` call is pinned
elsewhere (``tests/test_soi_cell_calibration.py``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fiscal_model.data.cps_asec import load_tax_microdata
from fiscal_model.microsim.top_tail import (
    SYNTHETIC_SOURCE_LABEL,
    SYNTHETIC_STATE_REFERENCE_AGI,
    augment_top_tail,
)

YEAR = 2023


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    df, _ = load_tax_microdata()
    return df


@pytest.fixture(scope="module")
def augmented(raw: pd.DataFrame) -> pd.DataFrame:
    out, _ = augment_top_tail(raw, YEAR, by_status=True)
    return out


def test_synthetic_states_are_drawn_from_the_cps_top(augmented):
    synth = augmented[augmented["source"] == SYNTHETIC_SOURCE_LABEL]
    cps = augmented[augmented["source"] != SYNTHETIC_SOURCE_LABEL]
    reference_states = set(cps.loc[cps["agi"] >= SYNTHETIC_STATE_REFERENCE_AGI, "state_fips"])

    assert synth["state_fips"].nunique() > 10
    assert set(synth["state_fips"]) <= reference_states
    ca_share = synth.loc[synth["state_fips"] == 6, "weight"].sum() / synth["weight"].sum()
    # California is the largest state at the top of the CPS (about 18% of the
    # weight at $500K+), not all of it.
    assert 0.05 < ca_share < 0.40


def test_state_draw_leaves_the_agi_sample_and_weights_alone(raw, augmented):
    """Only ``state_fips`` depends on the draw: re-stamping California gives the
    frame the CA-stamp code produced, AGI and weights included."""
    no_state = raw.drop(columns="state_fips")
    stamped, _ = augment_top_tail(no_state, YEAR, by_status=True)
    pd.testing.assert_frame_equal(
        stamped.reset_index(drop=True),
        augmented.drop(columns="state_fips").reset_index(drop=True),
    )


def test_frame_without_state_column_still_augments(raw):
    out, report = augment_top_tail(raw.drop(columns="state_fips"), YEAR, by_status=True)
    assert "state_fips" not in out.columns
    assert report.synthetic_records > 0


def test_state_is_inert_for_the_salt_repeal_because_amt_binds(augmented):
    """Why the measured movement of jct_salt_repeal_2024 is exactly 0.00pp: every
    synthetic row pays AMT before and after the repeal, so its state's SALT rate
    never reaches its tax. If this ever fails, re-measure the SALT row."""
    from fiscal_model.distribution_effects import policy_to_microsim_reforms
    from fiscal_model.microsim.engine import MicroTaxCalculator
    from fiscal_model.microsim.salt_imputation import impute_salt_and_itemized
    from fiscal_model.tax_expenditures import SaltCapBaseline, create_repeal_salt_cap

    synth = augmented[augmented["source"] == SYNTHETIC_SOURCE_LABEL]
    policy = create_repeal_salt_cap(salt_baseline=SaltCapBaseline.PERMANENT_10K)
    year = policy.start_year
    pop = impute_salt_and_itemized(synth).copy()
    base = MicroTaxCalculator(year=year).calculate(pop)
    reform = MicroTaxCalculator(year=year).apply_reform(
        pop, policy_to_microsim_reforms(policy, year)
    )
    assert (base["amt_tax"] > 0).all()
    assert np.allclose(reform["final_tax"].to_numpy(), base["final_tax"].to_numpy())
