"""Tests for lane L9's two additions to ``fiscal_model/international.py``:
the Pillar Two / GILTI base-overlap term and the FDII base x rate identity.

Two things are pinned here that a unit test would not normally reach for:

* every model input in ``fiscal_model/data_files/international/`` is checked
  against the constant ``INTERNATIONAL_BASELINE`` carries, so the transcription
  and the module cannot drift apart, and
* the CbCR distribution's totals are checked against the published band figures
  it was summarised from, so a row cannot be edited without the totals moving.

See ``planning/lanes/L9_international.md`` for the pre-registration these tests
were written against.
"""

import csv
from pathlib import Path

import pytest

from fiscal_model.international import (
    FOREIGN_PROFIT_BY_ETR_FILE,
    INTERNATIONAL_BASELINE,
    InternationalTaxPolicy,
    create_biden_full_international,
    create_biden_gilti_reform,
    create_fdii_repeal,
    create_pillar_two_adoption,
    create_pillar_two_with_utpr,
    fdii_income_billions,
    load_foreign_profit_by_etr,
    shared_claim_share,
)

PARAMETERS_FILE = (
    Path(FOREIGN_PROFIT_BY_ETR_FILE).parent / "international_parameters.csv"
)


def _read_parameters() -> dict[str, dict[str, str]]:
    with open(PARAMETERS_FILE, encoding="utf-8") as handle:
        reader = csv.DictReader(
            line for line in handle if not line.lstrip().startswith("#")
        )
        return {row["key"]: row for row in reader}


class TestTranscribedParameters:
    """The data file and the module carry the same numbers."""

    def test_every_model_input_matches_the_baseline_constant(self):
        parameters = _read_parameters()
        inputs = {k: v for k, v in parameters.items() if v["role"] == "model_input"}
        assert inputs, "the parameters file has no model_input rows"
        for key, row in inputs.items():
            assert key in INTERNATIONAL_BASELINE, (
                f"{key} is marked model_input but INTERNATIONAL_BASELINE does "
                "not carry it"
            )
            assert INTERNATIONAL_BASELINE[key] == pytest.approx(float(row["value"])), (
                f"{key} drifted: data file {row['value']}, module "
                f"{INTERNATIONAL_BASELINE[key]}"
            )

    def test_fdii_income_is_the_published_tax_expenditure_inverted(self):
        parameters = _read_parameters()
        derived = float(parameters["fdii_base_billions"]["value"])
        assert parameters["fdii_base_billions"]["role"] == "derived"
        assert fdii_income_billions() == pytest.approx(derived, abs=0.01)

    def test_every_external_check_row_is_labelled_as_one(self):
        # An external check must never be read by the module: that is the
        # difference between a transcribed source and a fitted constant.
        parameters = _read_parameters()
        checks = [k for k, v in parameters.items() if v["role"] == "external_check"]
        assert checks
        for key in checks:
            assert key not in INTERNATIONAL_BASELINE


class TestForeignProfitDistribution:
    def test_totals_reconcile_to_the_published_band_figures(self):
        # IRS SOI CbCR Table 4, TY2023: the ETR-under-15% band plus the
        # positive-profit/negative-tax band, less the United States row.
        rows = load_foreign_profit_by_etr()
        assert sum(r.profit_billions for r in rows) == pytest.approx(812.44, abs=0.05)
        assert sum(r.tax_accrued_billions for r in rows) == pytest.approx(25.71, abs=0.05)
        assert sum(r.tangible_assets_billions for r in rows) == pytest.approx(
            1187.67, abs=0.05
        )
        assert sum(r.employees_thousands for r in rows) == pytest.approx(
            5560.7, abs=0.5
        )

    def test_every_row_is_below_the_minimum_rate(self):
        # The file is the shared base by construction; a row at or above 15%
        # would mean the wrong band was transcribed.
        for row in load_foreign_profit_by_etr():
            assert row.effective_rate < 0.15, row.jurisdiction

    def test_comment_lines_and_nonpositive_profit_rows_are_skipped(self):
        raw = FOREIGN_PROFIT_BY_ETR_FILE.read_text(encoding="utf-8").splitlines()
        assert any(line.startswith("#") for line in raw)
        rows = load_foreign_profit_by_etr()
        assert all(r.profit_billions > 0 for r in rows)
        # 24 named jurisdictions plus one residual row.
        assert len(rows) == 25


class TestSharedClaimShare:
    def test_a_21_percent_per_country_gilti_subsumes_a_15_percent_top_up(self):
        # Algebra, not data: (0.21Y - 0.8T) - (0.15Y - T) = 0.06Y + 0.2T > 0.
        assert shared_claim_share(0.21, 0.15) == pytest.approx(1.0)

    def test_the_dominance_holds_row_by_row(self):
        ftc = INTERNATIONAL_BASELINE["gilti_ftc_limit"]
        sbie = INTERNATIONAL_BASELINE["pillar_two_sbie_tangible_rate"]
        for row in load_foreign_profit_by_etr():
            tax = max(0.0, row.tax_accrued_billions)
            gilti = max(0.0, 0.21 * row.profit_billions - ftc * tax)
            excess = max(
                0.0, row.profit_billions - sbie * row.tangible_assets_billions
            )
            top_up = max(0.0, 0.15 - tax / row.profit_billions) * excess
            assert gilti >= top_up, row.jurisdiction

    def test_negative_accrued_tax_is_floored_at_zero(self):
        # Table 4's negative-tax band is real, and without the floor a
        # jurisdiction there would be topped up by more than the minimum rate
        # and GILTI credited with more than its own rate on the profit. Both
        # zero-rate cases below are non-zero if the floor is removed.
        assert any(r.tax_accrued_billions < 0 for r in load_foreign_profit_by_etr())
        assert shared_claim_share(0.21, 0.0) == 0.0
        assert shared_claim_share(0.0, 0.15) == 0.0

    def test_the_share_falls_below_one_when_the_claims_interleave(self):
        # At the 2026 statutory GILTI rate the two provisions cross: some
        # jurisdictions are reached further by the top-up than by GILTI.
        share = shared_claim_share(0.13125, 0.15)
        assert 0.0 < share < 1.0

    def test_the_share_is_scale_free_in_the_minimum_rate_direction(self):
        # Raising the GILTI rate can only absorb more of the top-up, never less.
        low = shared_claim_share(0.13125, 0.15)
        high = shared_claim_share(0.21, 0.15)
        assert high >= low

    def test_no_claim_means_no_overlap(self):
        assert shared_claim_share(0.21, 0.0) == 0.0
        assert shared_claim_share(0.0, 0.15) == 0.0


class TestBaseOverlapTerm:
    def test_no_shipped_factory_books_an_overlap(self):
        # The four benchmark factories and the UTPR variant all leave one of
        # the two levers unpulled, so the ordering rule has nothing to net.
        for factory in (
            create_biden_gilti_reform,
            create_fdii_repeal,
            create_pillar_two_adoption,
            create_biden_full_international,
            create_pillar_two_with_utpr,
        ):
            policy = factory()
            assert policy._estimate_base_overlap() == 0.0, factory.__name__
            assert policy.get_component_breakdown()["base_overlap"] == 0.0

    def test_combining_gilti_and_pillar_two_nets_to_the_larger_claim(self):
        combined = InternationalTaxPolicy(
            name="GILTI 21% per country plus Pillar Two",
            description="both levers on the same low-taxed foreign profits",
            gilti_country_by_country=True,
            gilti_new_rate=0.21,
            gilti_eliminate_qbai=True,
            pillar_two_adopt=True,
        )
        gilti = combined._estimate_gilti_reform()
        top_up = combined._estimate_pillar_two()
        assert gilti > 0 and top_up > 0

        overlap = combined._estimate_base_overlap()
        assert overlap == pytest.approx(top_up)  # share is 1 at 21% vs 15%

        static = combined.estimate_static_revenue_effect(0.0)
        assert static == pytest.approx(max(gilti, top_up))
        assert static < gilti + top_up

    def test_the_breakdown_still_reconciles_with_an_overlap_present(self):
        combined = InternationalTaxPolicy(
            name="combined", description="combined",
            gilti_country_by_country=True, gilti_new_rate=0.21,
            pillar_two_adopt=True, adopt_utpr=True,
        )
        breakdown = combined.get_component_breakdown()
        assert breakdown["base_overlap"] > 0
        assert breakdown["static_total"] == pytest.approx(
            breakdown["gilti_reform"]
            + breakdown["fdii_reform"]
            + breakdown["pillar_two"]
            + breakdown["utpr"]
            - breakdown["base_overlap"]
        )
        assert breakdown["static_total"] == pytest.approx(
            combined.estimate_static_revenue_effect(0.0)
        )

    def test_a_gilti_rate_cut_books_no_overlap(self):
        # A negative GILTI delta is a revenue loss; there is nothing for the
        # top-up to be inside of.
        cut = InternationalTaxPolicy(
            name="cut", description="cut",
            gilti_new_rate=0.05, pillar_two_adopt=True,
        )
        assert cut._estimate_gilti_reform() < 0
        assert cut._estimate_base_overlap() == 0.0


class TestFDIIIdentity:
    def test_repeal_returns_the_published_tax_expenditure(self):
        repeal = create_fdii_repeal()._estimate_fdii_reform()
        assert repeal == pytest.approx(
            INTERNATIONAL_BASELINE["fdii_deduction_tax_expenditure_billions"]
        )

    def test_repeal_is_the_limiting_case_of_a_rate_change(self):
        # Repealing the deduction and setting the FDII rate to the statutory
        # rate are the same policy, so the two branches must agree.
        repeal = create_fdii_repeal()._estimate_fdii_reform()
        to_statutory = InternationalTaxPolicy(
            name="rate", description="rate",
            fdii_new_rate=INTERNATIONAL_BASELINE["current_corporate_rate"],
        )._estimate_fdii_reform()
        assert repeal == pytest.approx(to_statutory)

    def test_the_identity_is_base_times_the_rate_wedge(self):
        base = INTERNATIONAL_BASELINE
        wedge = base["current_corporate_rate"] * base["fdii_deduction_rate"]
        assert create_fdii_repeal()._estimate_fdii_reform() == pytest.approx(
            fdii_income_billions() * wedge
        )

    def test_a_partial_rate_rise_raises_less_than_full_repeal(self):
        partial = InternationalTaxPolicy(
            name="partial", description="partial", fdii_new_rate=0.18,
        )._estimate_fdii_reform()
        assert 0 < partial < create_fdii_repeal()._estimate_fdii_reform()
