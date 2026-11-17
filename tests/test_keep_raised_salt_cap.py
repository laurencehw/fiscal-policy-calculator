"""Bet 3: keeping P.L. 119-21's raised SALT cap after 2029.

Pre-registered in ``planning/lanes/BET3_preset_refresh.md``. The reform is the
difference between two cap paths on the same SOI distribution, so these tests
pin the path, the zero years, the band, and that nothing else moved.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.preset_ids import PRESET_ID_BY_LABEL
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tax_expenditures import (
    SaltCapBaseline,
    create_keep_raised_salt_cap,
    create_repeal_salt_cap,
    raised_cap_schedule,
    salt_cap_at,
    salt_cap_schedule,
)

LABEL = "📋 Keep the $40K SALT Cap After 2029"


@pytest.fixture(scope="module")
def scores():
    scorer = FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)
    out = {}
    for label in (LABEL, "📋 Repeal SALT Cap ($1.17T)"):
        policy = create_policy_from_preset(PRESET_POLICIES[label], start_year=APP_DEFAULT_START_YEAR)
        out[label] = scorer.score_policy(policy)
    return out


@pytest.mark.parametrize("year", range(2025, 2030))
def test_the_raised_path_is_current_law_through_2029(year):
    assert raised_cap_schedule(year) == salt_cap_schedule(year)
    for magi in (100_000.0, 550_000.0, 2_000_000.0):
        assert salt_cap_at(SaltCapBaseline.RAISED_CAP_PERMANENT, year, magi) == salt_cap_at(
            SaltCapBaseline.CURRENT_LAW, year, magi
        )


def test_after_2029_the_raised_path_keeps_rising_at_the_statutes_101_percent():
    last = salt_cap_schedule(2029)
    for year in range(2030, 2036):
        row = raised_cap_schedule(year)
        growth = 1.01 ** (year - 2029)
        assert row.limitation_amount == pytest.approx(last.limitation_amount * growth)
        assert row.threshold_amount == pytest.approx(last.threshold_amount * growth)
        # Current law reverts to the flat $10,000; the reform does not.
        assert salt_cap_schedule(year).limitation_amount == 10_000.0
        # The phasedown still never takes the cap below $10,000.
        assert row.cap_at(10_000_000.0) == 10_000.0


def test_it_costs_nothing_until_2030_and_lands_in_its_pre_registered_band(scores):
    result = scores[LABEL]
    years = [int(y) for y in result.years]
    effect = dict(zip(years, (float(x) for x in result.final_deficit_effect), strict=True))
    for year in range(2026, 2030):
        assert effect[year] == 0.0
    for year in range(2030, 2036):
        assert effect[year] > 0.0
    total = sum(effect.values())
    assert 105.0 <= total <= 125.0
    assert total == pytest.approx(119.33, abs=0.01)


def test_a_cap_is_still_a_cap(scores):
    keep = float(scores[LABEL].final_deficit_effect.sum())
    repeal = scores["📋 Repeal SALT Cap ($1.17T)"].final_deficit_effect
    assert keep < float(repeal[4:].sum()) < float(repeal.sum())


def test_cap_repeal_is_untouched(scores):
    assert create_repeal_salt_cap().salt_reform_path is None
    assert float(scores["📋 Repeal SALT Cap ($1.17T)"].final_deficit_effect.sum()) == pytest.approx(740.31, abs=0.01)


def test_the_preset_is_wired_and_carries_no_published_score():
    assert PRESET_ID_BY_LABEL[LABEL] == "salt-cap-40k-permanent"
    assert LABEL not in CBO_SCORE_MAP
    policy = create_keep_raised_salt_cap()
    assert policy.salt_reform_path is SaltCapBaseline.RAISED_CAP_PERMANENT
    assert policy.salt_baseline is SaltCapBaseline.CURRENT_LAW
    assert policy.annual_revenue_change_billions is None
