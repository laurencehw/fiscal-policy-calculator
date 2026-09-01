"""
P.L. 119-21 line items: the first sourced line-item block in the calibrated tier.

The targets here are individual rows of JCT's JCX-35-25 table, transcribed with
page references into ``fiscal_model/data_files/validation/pl119_21_jct_line_items.csv``.
These tests guard the two things that make that worth more than a rounded
headline figure: the transcription stays internally consistent with the totals
JCT printed, and every transcribed row is either scored or recorded out of scope
with a reason - never silently dropped.

They also pin the epistemics. No module constant is fitted to any individual JCT
row, so every entry must report ``calibrated_to_target=False``; if that ever
flips, a 41.8% mean error would start being read as a calibration regression
instead of the finding it is.
"""

import pytest

from fiscal_model.validation.cbo_distributions import CBO_PL119_21_2026
from fiscal_model.validation.provenance import LINE_ITEM
from fiscal_model.validation.specialized_pl119_21 import (
    PL119_21_LINE_ITEMS,
    PL119_21_VINTAGE,
    build_provision_policy,
    describe_line_item_coverage,
    mapped_line_items,
    out_of_scope_line_items,
    reference_line_items,
    validate_all_pl119_21,
    validate_pl119_21_provision,
)


def _by_id():
    return {item.provision_id: item for item in PL119_21_LINE_ITEMS}


# ── The transcription ──────────────────────────────────────────────────────


def test_csv_loaded():
    assert PL119_21_LINE_ITEMS, "pl119_21_jct_line_items.csv failed to load"


def test_every_row_is_accounted_for():
    coverage = describe_line_item_coverage()
    assert coverage["unaccounted"] == []
    assert coverage["total"] == (
        len(coverage["mapped"])
        + len(coverage["out_of_scope"])
        + len(coverage["reference"])
    )


def test_every_row_carries_a_page_reference():
    for item in PL119_21_LINE_ITEMS:
        assert 1 <= item.pdf_page <= 10, item.provision_id


def test_out_of_scope_rows_state_a_reason():
    for item in out_of_scope_line_items():
        assert item.note.strip(), f"{item.provision_id} is out of scope with no reason"


def test_mapped_rows_name_a_module_path():
    for item in mapped_line_items():
        assert item.module_path.startswith("fiscal_model."), item.provision_id


def test_deficit_effect_is_the_negated_revenue_effect():
    """The two sign conventions must never drift apart."""
    for item in PL119_21_LINE_ITEMS:
        expected = -item.revenue_effect_2025_34_millions / 1000.0
        assert item.deficit_effect_10yr_billions == pytest.approx(expected, abs=1e-3)


def test_net_total_matches_cbos_companion_estimate():
    """JCT's net total should be CBO's '$4.5 trillion decrease in revenues'.

    CBO publication 61570 puts P.L. 119-21's revenue effect at -$4.5T over
    2025-2034. JCX-35-25's own NET TOTAL is -$4,474,972M. If the transcription
    of the net total drifts, this catches it.
    """
    net = _by_id()["pl119_21_net_total"]
    assert net.revenue_effect_2025_34_millions == -4_474_972
    assert net.deficit_effect_10yr_billions == pytest.approx(4474.972, abs=0.01)


def test_chapter_5_subtotals_reconcile():
    """Subchapter A terminations plus subchapter B must equal the chapter total.

    The subchapter A figure is the only transcribed number JCT does not print
    (it is the sum of the subchapter's 15 rows), so it is the one most worth
    cross-checking.
    """
    items = _by_id()
    subchapter_a = items[
        "pl119_21_energy_credit_terminations"
    ].revenue_effect_2025_34_millions
    chapter_5 = items["pl119_21_chapter_5_total"].revenue_effect_2025_34_millions
    subchapter_b = chapter_5 - subchapter_a
    # Subchapter B (clean fuel production, carbon sequestration, IDCs, PTP
    # qualifying income, dyed fuel) sums to -43,573M in the printed table.
    assert subchapter_b == pytest.approx(-43_573, abs=5)


def test_reference_rows_are_never_scored():
    scored = {r.policy_id for r in validate_all_pl119_21(verbose=False)}
    for item in reference_line_items():
        assert item.provision_id not in scored
    for item in out_of_scope_line_items():
        assert item.provision_id not in scored


# ── The runner ─────────────────────────────────────────────────────────────


def test_all_mapped_provisions_score():
    results = validate_all_pl119_21(verbose=False)
    assert len(results) == len(mapped_line_items())
    assert all(r.accuracy_rating != "Error" for r in results)


def test_entries_declare_line_item_provenance():
    for result in validate_all_pl119_21(verbose=False):
        assert result.model_parameters["provenance"] == LINE_ITEM


def test_entries_are_not_calibrated_to_their_target():
    """The whole point of the block.

    The TCJA module's calibration factor is fitted to CBO's $4.6T aggregate, not
    to any JCT row, so these are uncalibrated reconstructions. If this flips to
    True, ``scripts/cold_holdout.py`` would fold a 40%-error block into the
    fitted-calibrated mean and the anti-leakage comparison would be nonsense.
    """
    for result in validate_all_pl119_21(verbose=False):
        assert result.model_parameters["calibrated_to_target"] is False


def test_entries_are_scored_on_the_january_2025_vintage():
    """CBO measured P.L. 119-21 against its January 2025 baseline."""
    assert PL119_21_VINTAGE.value == "cbo_jan_2025"
    for result in validate_all_pl119_21(verbose=False):
        assert result.model_parameters["scoring_vintage"] == "cbo_jan_2025"


def test_entries_carry_a_jct_page_reference():
    for result in validate_all_pl119_21(verbose=False):
        assert result.model_parameters["jct_document"] == "JCX-35-25"
        assert result.model_parameters["jct_pdf_page"] >= 1


def test_every_scored_provision_has_a_known_limitation():
    """A miss without a stated structural cause is an unexplained miss."""
    for result in validate_all_pl119_21(verbose=False):
        assert result.known_limitations, result.policy_id


def test_directions_match_jct():
    """A provision that JCT scores as a cost must not be modelled as a saving."""
    for result in validate_all_pl119_21(verbose=False):
        assert result.direction_match, (
            f"{result.policy_id}: model {result.model_10yr:+.1f} has the opposite "
            f"sign to JCT's {result.official_10yr:+.1f}"
        )


def test_a_single_component_policy_is_built_per_provision():
    """Each mapped row must switch on exactly one TCJA component."""
    flags = (
        "extend_rate_cuts",
        "extend_standard_deduction",
        "keep_exemption_elimination",
        "extend_passthrough_deduction",
        "extend_ctc_expansion",
        "extend_estate_exemption",
        "extend_amt_relief",
        "keep_salt_cap",
    )
    for item in mapped_line_items():
        policy = build_provision_policy(item.provision_id)
        on = [name for name in flags if getattr(policy, name)]
        assert len(on) == 1, f"{item.provision_id} switched on {on}"


def test_scoring_an_unmapped_provision_is_refused():
    with pytest.raises(ValueError):
        validate_pl119_21_provision("pl119_21_no_tax_on_tips", verbose=False)
    with pytest.raises(ValueError):
        validate_pl119_21_provision("not_a_provision", verbose=False)


def test_energy_terminations_are_excluded_for_leakage_not_for_a_gap():
    """The reason matters: the climate module *could* score it, and must not."""
    note = _by_id()["pl119_21_energy_credit_terminations"].note
    assert "LEAKAGE" in note
    assert "IRA" in note


def test_senior_deduction_has_no_separate_jct_row():
    """Recorded so nobody goes looking for a line item JCT never printed."""
    note = _by_id()["pl119_21_personal_exemption_termination"].note
    assert "senior deduction" in note


# ── The distributional table ───────────────────────────────────────────────


def test_pl119_21_distributional_benchmark_is_registered():
    from fiscal_model.validation.cbo_distributions import CBO_JCT_BENCHMARKS

    assert CBO_PL119_21_2026 in CBO_JCT_BENCHMARKS
    assert len(CBO_JCT_BENCHMARKS) == 7


def test_pl119_21_distributional_shares_sum_to_minus_one():
    total = sum(row.share_of_total for row in CBO_PL119_21_2026.rows)
    assert total == pytest.approx(-1.0, abs=0.01)


def test_pl119_21_distributional_benchmark_states_its_scope():
    """The benchmark must say it is NOT the law's net distributional effect."""
    notes = CBO_PL119_21_2026.notes
    assert "in-kind" in notes
    assert "-$1,214" in notes or "1,214" in notes


def test_pl119_21_distributional_benchmark_is_mapped():
    from fiscal_model.validation.benchmark_runners import default_model_runner

    result = default_model_runner(CBO_PL119_21_2026)
    assert result is not None, "benchmark is registered but produces no model output"


def test_pl119_21_distributional_comparison_runs():
    from fiscal_model.validation.benchmark_runners import default_model_runner
    from fiscal_model.validation.cbo_distributions import compare_distribution

    comparison = compare_distribution(
        default_model_runner(CBO_PL119_21_2026), CBO_PL119_21_2026
    )
    assert len(comparison.per_group) == 10
    assert comparison.mean_absolute_share_error_pp is not None
    # Observed 3.96pp at the time of writing; the ceiling is deliberately loose
    # because this is a held-out table, not one the engine's shares came from.
    assert comparison.mean_absolute_share_error_pp < 8.0
