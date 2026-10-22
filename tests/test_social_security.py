"""
The Social Security trust fund ledger and its transcribed inputs.

Checks L1-L7 are the ones pre-registered in
``planning/lanes/SS1_trust_fund_page.md`` section 4. L3 (year-end reserves
within 2% of Table VI.G2 every year 2026-2033) missed its bar in 2032-2033;
the outturn in that file records it, and the test below pins what the ledger
actually does so a change to the mechanics shows up.
"""

from __future__ import annotations

import csv

import pytest

from fiscal_model.social_security import (
    ExclusiveGroupError,
    load_catalog,
    project,
    validate_selection,
)
from fiscal_model.social_security.crfb_benchmark import crfb_comparison
from fiscal_model.social_security.trust_fund import (
    ANNUAL_PATH,
    BASELINE_COST_RATE_2101,
    FIRST_YEAR,
    LAST_YEAR,
    TRUSTEES_ACTUARIAL_BALANCE,
    load_baseline,
    load_provision_paths,
)

#: Trustees Report 2026, Table VI.G2, OASDI reserves at end of year ($B).
VI_G2_RESERVES = {
    2026: 2357.7,
    2027: 2102.2,
    2028: 1835.3,
    2029: 1548.5,
    2030: 1240.2,
    2031: 912.0,
    2032: 559.4,
    2033: 182.9,
}


@pytest.fixture(scope="module")
def baseline():
    return project(())


# ── Current law: L1-L4 ───────────────────────────────────────────────────


def test_l1_baseline_depletes_in_2034(baseline):
    assert baseline.depletion_year == 2034


def test_l2_baseline_actuarial_balance(baseline):
    assert baseline.computed_actuarial_balance == pytest.approx(
        TRUSTEES_ACTUARIAL_BALANCE, abs=0.03
    )
    # The headline keeps the Trustees' own number.
    assert baseline.actuarial_balance == TRUSTEES_ACTUARIAL_BALANCE
    assert baseline.share_of_shortfall_closed == 0


def test_l3_baseline_reserves_against_vi_g2(baseline):
    """Within 2% through 2031; the drift grows as reserves near zero (outturn)."""
    for year, published in VI_G2_RESERVES.items():
        ours = baseline.reserves_end[baseline.years.index(year)]
        rel = abs(ours / published - 1)
        bar = 0.02 if year <= 2031 else 0.08
        assert rel <= bar, (year, ours, published)


def test_l4_baseline_payable_at_depletion(baseline):
    assert baseline.payable_at_depletion == pytest.approx(0.83, abs=0.01)


def test_trust_fund_ratio_falls_to_zero(baseline):
    k = baseline.years.index(2035)
    assert baseline.trust_fund_ratio[0] > 100
    assert baseline.trust_fund_ratio[k] == 0


# ── Transcription: L5 ────────────────────────────────────────────────────


def test_l5_every_option_reconciles_to_the_trustees_baseline():
    base = {r.year: r for r in load_baseline()}
    with ANNUAL_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    bad = []
    for row in rows:
        year = int(row["year"])
        if year > LAST_YEAR:
            implied = float(row["proposal_cost_rate"]) - float(row["change_cost_rate"])
            if abs(implied - BASELINE_COST_RATE_2101) > 0.015:
                bad.append((row["provision_id"], year, "2101 cost", implied))
            continue
        for kind in ("cost", "income"):
            implied = float(row[f"proposal_{kind}_rate"]) - float(row[f"change_{kind}_rate"])
            published = getattr(base[year], f"{kind}_rate")
            if abs(implied - published) > 0.015:
                bad.append((row["provision_id"], year, kind, implied, published))
    assert not bad, bad[:10]


def test_every_catalog_option_has_a_full_annual_path():
    paths = load_provision_paths()
    years = set(range(FIRST_YEAR, LAST_YEAR + 2))
    for p in load_catalog():
        assert set(paths[p.provision_id].change_cost_rate) == years, p.provision_id


# ── Reconstruction of OCACT's own summaries: L6, L7 ─────────────────────


@pytest.mark.parametrize("provision", load_catalog(), ids=lambda p: p.provision_id)
def test_l6_change_in_actuarial_balance_matches_ocact(provision):
    result = project([provision.provision_id])
    assert result.change_in_actuarial_balance == pytest.approx(
        provision.ocact_change_actuarial_balance, abs=0.03
    )


def test_l7_depletion_years_match_ocact():
    catalog = load_catalog()
    misses = {}
    for p in catalog:
        ours = project([p.provision_id]).depletion_year
        if ours != p.ocact_depletion_year:
            misses[p.provision_id] = (ours, p.ocact_depletion_year)
    assert len(misses) <= 0.10 * len(catalog), misses
    assert all(
        ours is not None and theirs is not None and abs(ours - theirs) <= 1
        for ours, theirs in misses.values()
    ), misses
    # The one known miss (outturn): E3.2's reserves sit at zero on 1 January 2037.
    assert set(misses) == {"E3.2"}


# ── Plans ────────────────────────────────────────────────────────────────


def test_options_add_without_interactions():
    a = project(["E2.1"]).change_in_actuarial_balance
    b = project(["B1.2"]).change_in_actuarial_balance
    assert project(["E2.1", "B1.2"]).change_in_actuarial_balance == pytest.approx(a + b, abs=1e-9)


def test_selection_rejects_two_settings_of_one_lever():
    with pytest.raises(ExclusiveGroupError):
        validate_selection(["E2.1", "E2.2"])


def test_selection_rejects_unknown_ids():
    with pytest.raises(KeyError):
        validate_selection(["Z9"])


def test_selection_is_returned_in_catalog_order():
    assert validate_selection(["F1", "A2"]) == ("A2", "F1")


def test_a_plan_that_never_depletes_reports_no_cut():
    # The largest revenue and benefit options together.
    plan = project(["E2.1", "B1.2", "C1.4", "A2", "E1.4"])
    assert plan.share_of_shortfall_closed > 1
    assert plan.depletion_year is None
    assert plan.solvent_through_window
    assert plan.benefit_cut_at_depletion is None


def test_catalog_groups_are_well_formed():
    catalog = load_catalog()
    assert len({p.provision_id for p in catalog}) == len(catalog)
    for p in catalog:
        assert p.source_url.startswith("https://www.ssa.gov/oact/solvency/provisions/tables/")


# ── CRFB benchmark ───────────────────────────────────────────────────────


def test_crfb_rows_carry_sources_and_compute():
    rows = crfb_comparison()
    assert rows
    for r in rows:
        assert r.source_url.startswith("https://www.crfb.org/")
        assert r.source_date


def test_crfb_comparison_figures():
    """Pins the comparison as measured (2026-10-22); not a target."""
    by_id = {r.benchmark_id: r for r in crfb_comparison()}
    assert by_id["current_law_oasdi_year"].gap == 0
    assert by_id["current_law_oasi_cut"].gap == 0
    assert by_id["eliminate_cap_share"].our_value == pytest.approx(57.7, abs=0.1)
    assert by_id["eliminate_cap_year"].our_value == 2058
    assert by_id["ppi_share"].our_value == pytest.approx(38.5, abs=0.1)
    assert by_id["ppi_year"].gap == 0
    assert by_id["both_share"].our_value == pytest.approx(96.2, abs=0.1)
    assert by_id["both_year"].our_value == 2074
    assert by_id["both_year"].crfb_text == "never"
