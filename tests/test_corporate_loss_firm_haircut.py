"""
Lane R5's gate: CBO's loss-firm haircut is read, measured, and **not applied**.

``planning/lanes/R5_h3b_corporate.md`` §1.1 transcribes CBO's ``dmyrevnfc = 0.85``
and ``dmyrevx = 0.80`` and refuses to multiply the derived base by either,
because that base is CBO's projected corporate receipts divided by the statutory
rate and therefore already nets loss-making firms. Applying it anyway would have
landed two of the lane's three pre-registered bands, which is exactly why the
refusal needs a test rather than a paragraph.

The falsification condition these tests encode is §4.2: *"multiplying
``projected_statutory_base`` — or anything downstream of it — by 0.80 or 0.85
without first showing that the base does not net loss firms."*
"""

from __future__ import annotations

import ast
import inspect

import pytest

from fiscal_model import corporate as corporate_module
from fiscal_model.corporate import (
    CBO_BUSINESS_INVESTMENT_MODEL_COMMIT,
    CORPORATE_MODE_DERIVED,
    CURRENT_CORPORATE_RATE,
    SECTION_38C_ALLOWED_SHARE_OF_REGULAR_TAX,
    CorporateTaxPolicy,
    cbo_loss_firm_haircut,
    credit_absorption_bounds,
    credit_carryforward_item,
    credit_realization_ratio,
    load_cbo_loss_firm_haircut,
    load_credit_carryforward_stocks,
    loss_firm_haircut_is_redundant,
    projected_statutory_base,
    statutory_base_billions,
)
from fiscal_model.policies import PolicyType


# ---------------------------------------------------------------------------
# The transcription is what CBO published
# ---------------------------------------------------------------------------


def test_the_two_constants_are_cbos_own():
    assert cbo_loss_firm_haircut("dmyrevnfc") == 0.85
    assert cbo_loss_firm_haircut("dmyrevx") == 0.80


def test_the_commit_is_pinned():
    """A transcription without a commit is a quotation, not a source."""
    assert len(CBO_BUSINESS_INVESTMENT_MODEL_COMMIT) == 40
    assert CBO_BUSINESS_INVESTMENT_MODEL_COMMIT.isalnum()


def test_the_soi_2005_derivation_reproduces_cbos_872_percent():
    """CBO rounds 87.2% to 0.85; the transcribed inputs must give the 87.2%."""
    row = next(r for r in load_cbo_loss_firm_haircut() if r["variable"] == "dmyrevnfc")
    ratio = float(row["soi_2005_net_income_all_active_returns_thousands"]) / float(
        row["soi_2005_net_income_positive_returns_thousands"]
    )
    assert ratio == pytest.approx(0.872, abs=0.0005)
    assert float(row["implied_ratio"]) == pytest.approx(ratio, abs=5e-5)


def test_the_pair_is_not_financial_versus_nonfinancial():
    """The plan and the brief say it is; CBO's own comment says it is not.

    0.80 is 0.85 further reduced by the nonprofit share of private
    nonresidential investment, so the two differ in *coverage*, not in sector.
    Pinned because a lane that believed the sector story would have gone looking
    for a receipts split that does not exist.
    """
    rows = {r["variable"]: r for r in load_cbo_loss_firm_haircut()}
    assert rows["dmyrevnfc"]["covers_nonprofits"] == "no"
    assert rows["dmyrevx"]["covers_nonprofits"] == "yes"
    assert rows["dmyrevnfc"]["covers_loss_firms"] == "yes"
    assert rows["dmyrevx"]["covers_loss_firms"] == "yes"
    assert "financial" not in rows["dmyrevnfc"]["scope"].replace("nonfinancial", "")


# ---------------------------------------------------------------------------
# The measurement that decides applicability
# ---------------------------------------------------------------------------


def test_the_derived_base_already_nets_the_losses_cbo_prices():
    """SOI's own NOL deduction is the same quantity CBO's 12.8% measures.

    This is the lane's decision rule (§1.1): the haircut applies only if the
    base can be shown *not* to net loss firms, and this shows it does. The
    tolerance is wide on purpose — the claim is "the same order, from the same
    SOI", not "equal to a basis point", because CBO's is a 2005 flow of
    current-year losses and SOI's is a post-TCJA stock of carryforwards used.
    """
    result = loss_firm_haircut_is_redundant()
    assert result["cbo_loss_share_of_positive_net_income"] == pytest.approx(
        0.1281, abs=0.001
    )
    assert result["soi_nol_share_of_pre_nol_base"] == pytest.approx(0.1158, abs=0.001)
    assert abs(result["gap_pp"]) < 2.0


def test_every_transcribed_soi_year_shows_the_same_thing():
    """One year could be a coincidence; four in a row is the base's construction."""
    for year in (2019, 2020, 2021, 2022):
        share = loss_firm_haircut_is_redundant(year)["soi_nol_share_of_pre_nol_base"]
        assert 0.08 < share < 0.13, year


# ---------------------------------------------------------------------------
# ...and therefore: nothing applies it
# ---------------------------------------------------------------------------


def _scored_total(rate_change: float, mode: str) -> float:
    policy = CorporateTaxPolicy(
        name="probe",
        description="probe",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=rate_change,
        mode=mode,
        start_year=2025,
        duration_years=10,
    )
    total = 0.0
    for year in range(2025, 2035):
        static = policy.estimate_static_revenue_effect(0.0, True, year)
        offset = policy.estimate_behavioral_offset(static)
        total += (static - offset) * policy.get_phase_in_factor(year)
    return total


def test_the_projected_base_carries_no_haircut():
    """``projected_statutory_base`` is receipts / tau x the anchor ratio, full stop."""
    from fiscal_model.corporate import (
        BASE_PER_DOLLAR_OF_RECEIPTS,
        cbo_corporate_receipts,
    )

    for year in (2025, 2030, 2034):
        assert projected_statutory_base(year) == pytest.approx(
            cbo_corporate_receipts(year) * BASE_PER_DOLLAR_OF_RECEIPTS
        )


def test_no_score_is_within_reach_of_the_haircut_applied():
    """§4.2: the score must not look like the haircut was quietly applied.

    ``x0.85`` on the derived +1pp path returns about $166.7B against the
    unhaircut $196.1B, which would read 22.8% against CBO Option 64's $135.7B —
    *inside* this lane's pre-registered band. So "it landed the band" is not
    evidence of anything, and this test is what stops it becoming so.
    """
    total = _scored_total(0.01, CORPORATE_MODE_DERIVED)
    for factor in (0.80, 0.85):
        assert abs(total) > abs(total * factor) + 5.0, factor
    assert abs(total) == pytest.approx(196.08, abs=1.0)


def test_the_module_never_reads_the_haircut_in_a_scoring_path():
    """A grep gate, in PR #119's shape: the constants have exactly one reader.

    ``cbo_loss_firm_haircut`` may be called by the loader's own tests and by
    ``scripts/corporate_marginal_share.py``. If a scoring method ever calls it,
    this fails — which is cheaper than noticing later that a row improved.
    """
    source = inspect.getsource(corporate_module)
    tree = ast.parse(source)
    scoring_functions = {
        "_derived_rate_effect",
        "estimate_static_revenue_effect",
        "estimate_behavioral_offset",
        "get_phase_in_factor",
        "projected_statutory_base",
        "credit_realized_base_billions",
        "base_per_dollar_of_receipts",
    }

    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in scoring_functions:
            continue
        seen.add(node.name)
        names = {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name)
        } | {
            child.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Attribute)
        }
        assert "cbo_loss_firm_haircut" not in names, node.name
        assert not any("dmyrev" in n for n in names), node.name

    # The allowlist is only a gate while it matches the module. If a scoring
    # function is renamed away, this fails rather than silently passing.
    assert seen == scoring_functions, scoring_functions - seen


# ---------------------------------------------------------------------------
# The credit-carryforward acquisition
# ---------------------------------------------------------------------------


def test_form_3800_part_i_foots_as_published():
    """The footing check is how the line mapping was confirmed at source."""
    line1 = credit_carryforward_item("form_3800_part_i_line_1_current_year_gbc")
    line4 = credit_carryforward_item("form_3800_part_i_line_4_carryforward_to_2022")
    line6 = credit_carryforward_item("form_3800_part_i_line_6_total")
    # Lines 3 and 5 are individually suppressed ('d'); their sum is the residual.
    assert line6 - line1 - line4 == pytest.approx(0.3095, abs=0.001)


def test_the_ftc_claim_matches_the_other_soi_product():
    """Two different SOI publications, the same TY2022 figure, to the dollar.

    ``soi_table11_corporate_tax_items.csv`` is the Complete Report;
    ``credit_carryforward_stocks.csv`` is the Corporate Foreign Tax Credit
    release. If these ever disagree, one of the two transcriptions is wrong.
    """
    from fiscal_model.corporate import soi_row

    complete_report = float(soi_row(2022)["foreign_tax_credit_thousands"]) / 1e6
    ftc_release = credit_carryforward_item("form_1118_col2_ftc_claimed")
    assert complete_report == pytest.approx(ftc_release, abs=1e-6)


def test_the_section_904_limitation_is_tau_times_foreign_taxable_income():
    """The mechanism, confirmed on published columns rather than assumed."""
    limitation = credit_carryforward_item("form_1118_col18_limitation")
    fsti = credit_carryforward_item(
        "form_1118_col16_foreign_taxable_income_after_adjustments"
    )
    assert limitation / fsti == pytest.approx(CURRENT_CORPORATE_RATE, abs=0.005)


def test_the_average_substitution_sits_on_the_section_904_bound():
    """The lane's §1.2 finding, asserted rather than described.

    The derived path books ``1 - credit_realization_ratio()`` of marginal
    absorption. The §904 channel's own upper bound — every claimant in an
    excess-credit position — is within a third of a percentage point of it, so
    the §38(c) channel is unbooked. If a later lane prices §38(c) on top without
    touching the average substitution, this test says where the double count is.
    """
    bounds = credit_absorption_bounds()
    assert bounds["average_substitution_in_use"] == pytest.approx(
        1.0 - credit_realization_ratio()
    )
    gap = abs(
        bounds["average_substitution_in_use"] - bounds["section_904_upper_bound"]
    )
    assert gap < 0.01, gap


def test_the_section_38c_stock_is_live():
    """A channel with no stock behind it would not be worth a carry-over."""
    bounds = credit_absorption_bounds()
    assert bounds["section_38c_carryforward_stock_billions"] > 100.0
    assert bounds["section_38c_stock_in_years_of_claims"] > 1.0
    assert bounds["section_38c_upper_bound"] == SECTION_38C_ALLOWED_SHARE_OF_REGULAR_TAX


def test_no_camt_row_carries_a_money_amount():
    """CAMT is context, never an input: no source publishes the base it shields."""
    for row in load_credit_carryforward_stocks():
        if row["provision"] == "camt":
            assert row["status"] == "published_context"
            assert row["amount_thousands"] == ""


def test_the_residual_is_labelled_a_residual():
    """SOI's footnote [2] says the carryover is not shown separately."""
    row = next(
        r
        for r in load_credit_carryforward_stocks()
        if r["item"].startswith("ftc_carryover_residual")
    )
    assert row["status"] == "derived_residual"
    col17 = credit_carryforward_item("form_1118_col17_taxes_available_for_credit")
    col20 = credit_carryforward_item("form_1118_col20_taxes_paid_or_accrued")
    col27 = credit_carryforward_item("form_1118_col27_taxes_deemed_paid")
    assert float(row["amount_thousands"]) / 1e6 == pytest.approx(
        col17 - col20 - col27, abs=1e-6
    )


def test_the_statutory_base_is_unchanged_by_this_lane():
    """Nothing here may move the quantity every corporate score reads."""
    assert statutory_base_billions(2022) == pytest.approx(2879.100959, abs=1e-4)
