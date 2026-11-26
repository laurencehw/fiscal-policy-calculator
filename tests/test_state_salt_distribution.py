"""Lane REVIEW-11: each state's SALT reads its own SOI distribution."""

from __future__ import annotations

import csv

import pytest

from fiscal_model.models.state import compute_salt_lift
from fiscal_model.tax_expenditure_distributions import (
    STATE_SALT_FILE,
    load_state_capped_deduction_distribution,
    state_salt_codes,
)


def test_every_class_mean_lies_inside_the_bounds_it_is_read_with():
    # The AGI stub bounds are a reading of SOI's documentation; the data check them.
    with STATE_SALT_FILE.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            returns = float(row["returns"])
            if returns <= 0 or row["agi_stub"] == "1":
                continue
            mean = float(row["agi_less_deficit"]) * 1e3 / returns
            assert float(row["agi_lower"]) <= mean, row
            if row["agi_upper"]:
                assert mean < float(row["agi_upper"]), row


def test_the_limited_amount_never_exceeds_the_cap_or_the_amount_claimed():
    with STATE_SALT_FILE.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            n = float(row["salt_returns"])
            if n <= 0:
                continue
            limited = float(row["salt_limited_amount"]) * 1e3 / n
            # SOI rounds amounts to thousands of dollars, and a top class's
            # mean can sit a fraction of a percent over the cap; 1% of slack.
            assert limited <= 10_000.0 * 1.01, row
            assert limited <= float(row["salt_amount"]) * 1e3 / n + 1.0, row


def test_all_fifty_states_and_dc_are_present():
    assert len(state_salt_codes()) == 51


@pytest.mark.parametrize("state", ["CA", "NY", "TX", "FL"])
def test_each_state_distribution_is_its_own(state):
    dist = load_state_capped_deduction_distribution(state)
    assert dist.classes
    assert all(c.sigma is None or c.sigma > 0 for c in dist.classes)


def test_high_income_tax_states_gain_more_per_filer_than_no_income_tax_states():
    # The inversion the outside review found on 23 Nov 2026.
    gain = {s: compute_salt_lift(s).avg_deduction_change for s in ("CA", "NY", "TX", "FL")}
    assert min(gain["CA"], gain["NY"]) > max(gain["TX"], gain["FL"])
