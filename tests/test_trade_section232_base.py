"""Lane R8: the Section 232 bases are CBO's article lists, not HS chapters.

`fiscal_model/data_files/trade/section232_hts_bases.csv` transcribes CBO's own
HS-10 Section 232 annex lists aggregated over CBO's own Census file, pinned to
`conventional-tariff-analysis-model` commit 59ea68fd. These tests pin the
module against that transcription, and assert the lane's findings rather than
their neighbourhood — the review lesson PR #143 left behind.
"""

import csv
from pathlib import Path

import pytest

from fiscal_model.trade import (
    TRADE_BASELINE,
    create_auto_tariff_25,
    create_steel_tariff_25,
)

CSV_PATH = (
    Path(__file__).parent.parent
    / "fiscal_model"
    / "data_files"
    / "trade"
    / "section232_hts_bases.csv"
)

#: The figures lane H8 shipped, kept here so the comparison is in the test
#: rather than in a comment. HS 72 + HS 76 was the declared floor; adding
#: whole-chapter HS 73 was the declared ceiling.
H8_FLOOR = 58.9
H8_CEILING = 108.4
H8_DERIVATIVE_UPPER_BOUND = 49.5
H8_AUTO_BASE = 384.9 * (1 - 0.4842)


def _rows() -> dict[str, dict[str, str]]:
    with CSV_PATH.open(encoding="utf-8") as fh:
        lines = [line for line in fh if not line.startswith("#")]
    return {row["key"]: row for row in csv.DictReader(lines)}


class TestTranscription:
    def test_the_csv_parses_and_every_row_carries_a_ctam_path(self):
        rows = _rows()
        assert rows
        for key, row in rows.items():
            assert row["source"].strip(), f"{key} has no source"
            assert row["ctam_path"].strip(), f"{key} has no CTAM path"
            assert row["role"] in {"model_input", "context", "external_check"}

    def test_the_pinned_commit_is_named_in_the_header(self):
        """A transcription without a commit is not reproducible."""
        text = CSV_PATH.read_text(encoding="utf-8")
        assert "59ea68fd6a6f006ca240bc45100b634b3787c2a2" in text
        assert "conventional-tariff-analysis-model" in text

    def test_every_model_input_matches_trade_baseline(self):
        rows = {k: v for k, v in _rows().items() if v["role"] == "model_input"}
        mapped = {
            "section232_steel_primary_base_billions": "steel_aluminum_imports_billions",
            "section232_steel_primary_existing_avg_tariff": (
                "steel_aluminum_existing_avg_tariff"
            ),
            "section232_deriv_content_base_billions": (
                "steel_derivative_imports_billions"
            ),
            "section232_deriv_content_existing_avg_tariff": (
                "steel_derivative_existing_avg_tariff"
            ),
            "section232_auto_taxed_base_billions": "auto_imports_billions",
            "section232_auto_parts_imports_billions": "auto_parts_imports_billions",
            "section232_auto_existing_avg_tariff": "auto_existing_avg_tariff",
        }
        for csv_key, baseline_key in mapped.items():
            assert csv_key in rows, f"{csv_key} is not a model_input row"
            assert TRADE_BASELINE[baseline_key] == pytest.approx(
                float(rows[csv_key]["value"]), rel=1e-9
            ), f"{baseline_key} has drifted from the transcription"

    def test_the_derivative_base_is_the_content_weighted_sum_cbo_computes(self):
        """`0.75 x high + 0.25 x low`, CBO's own shares at default.yaml:72-73.

        CBO applies them as a rate blend (tariffs.py:256-274); for incremental
        revenue that is identical to taxing that share of the value, which is
        the `(base, incremental rate)` shape `rate_schedule` takes.
        """
        rows = _rows()
        high = float(rows["section232_deriv_high_imports_billions"]["value"])
        low = float(rows["section232_deriv_low_imports_billions"]["value"])
        share_high = float(rows["alum_steel_deriv_high_share"]["value"])
        share_low = float(rows["alum_steel_deriv_low_share"]["value"])
        assert share_high == 0.75
        assert share_low == 0.25
        assert TRADE_BASELINE["steel_derivative_imports_billions"] == pytest.approx(
            share_high * high + share_low * low, rel=1e-6
        )

    def test_the_census_cross_checks_reproduce_the_earlier_transcription(self):
        """The proof that CBO's file is the same Census series, one vintage on.

        If these ever drift, the article lists are being aggregated over a
        different universe from the one `tariff_scoring_inputs.csv` measured
        independently in February 2025, and none of the rest follows.
        """
        rows = _rows()
        # HS-73: transcribed independently at 0.0563 in Feb 2025.
        assert float(rows["ctam_census_hs73_existing_avg_tariff"]["value"]) == (
            pytest.approx(0.0563, abs=5e-4)
        )
        # All chapters: $76.6B of duty, 2.36%, in the earlier transcription.
        assert float(rows["ctam_census_all_chapters_cal_dut_billions"]["value"]) == (
            pytest.approx(76.6, rel=0.01)
        )


class TestTheChapterBracketWasWrongAtBothEnds:
    """Lane R8's headline finding, asserted rather than described."""

    def test_the_declared_upper_bound_was_two_and_a_half_times_too_small(self):
        """H8 declared whole-chapter HS-73 a ceiling. It is not one.

        The Section 232 derivative annex lives in chapters 82, 83, 84, 85, 86,
        87, 94 and 95 (high metal content) and 34, 38, 82, 84, 85, 87, 94, 95
        (low) — machinery, furniture, appliances — none of which HS-73
        contains.
        """
        measured = TRADE_BASELINE["steel_derivative_imports_billions"]
        assert measured > 2.4 * H8_DERIVATIVE_UPPER_BOUND
        assert measured / H8_DERIVATIVE_UPPER_BOUND == pytest.approx(2.48, abs=0.05)

    def test_the_declared_floor_was_below_the_primary_article_list(self):
        """Most of HS-73 is *primary* Section 232 scope, so the floor excluded it.

        `alum_steel.csv` puts 558 of its 1,180 HS-10 lines in HS-73.
        """
        assert TRADE_BASELINE["steel_aluminum_imports_billions"] > H8_FLOOR
        assert TRADE_BASELINE["steel_aluminum_imports_billions"] == pytest.approx(
            96.7516, rel=1e-6
        )

    def test_the_measured_base_is_about_twice_the_declared_ceiling(self):
        policy = create_steel_tariff_25()
        assert policy.import_base_billions / H8_CEILING == pytest.approx(2.02, abs=0.05)

    def test_the_derivative_annex_collects_less_duty_than_the_primary_list(self):
        """The reverse of the chapter proxy, and the tell that they differ.

        HS-73 collects 5.63% against HS-72 + HS-76's 3.06%; CBO's derivative
        annex collects 3.87% against its primary list's 4.64%. If these two
        were the same set of articles the ordering could not flip.
        """
        assert (
            TRADE_BASELINE["steel_derivative_existing_avg_tariff"]
            < TRADE_BASELINE["steel_aluminum_existing_avg_tariff"]
        )
        assert TRADE_BASELINE["steel_aluminum_existing_avg_tariff"] > 0.0306


class TestTheAutoBase:
    def test_the_base_is_both_article_lists(self):
        policy = create_auto_tariff_25()
        assert policy.import_base_billions == pytest.approx(
            TRADE_BASELINE["auto_imports_billions"]
            + TRADE_BASELINE["auto_parts_imports_billions"],
            abs=1e-9,
        )

    def test_the_parts_list_is_the_larger_half_and_sits_outside_hs87(self):
        """Most of what a 25% auto tariff reaches is not in HS-87 at all.

        `auto_parts.csv` spans chapters 40, 70, 73, 83, 84, 85, 87 and 90.
        A whole-chapter HS-87 proxy therefore both over-includes (tractors,
        trailers, motorcycles, bicycles, baby carriages) and under-includes.
        """
        assert (
            TRADE_BASELINE["auto_parts_imports_billions"]
            > TRADE_BASELINE["auto_imports_billions"]
        )
        # HS-87 is $389.0B of imports for consumption; the two article lists
        # together are $555.0B, so the chapter cannot contain them.
        assert create_auto_tariff_25().import_base_billions > 389.0

    def test_the_usmca_carveout_is_us_content_not_whole_value(self):
        """CBO exempts the US content of a *qualifying* vehicle, not the vehicle.

        `tariffs.py:186-187` taxes Canadian and Mexican vehicles at
        `rate x (1 - us_content)` on their USMCA-utilised share. That removes
        $41.0B where the module's old whole-value 48.42% removed about $186B —
        an over-statement `tariff_scoring_inputs.csv` had already recorded in
        that key's own source note.
        """
        rows = _rows()
        carveout = float(rows["autos_usmca_us_content_carveout_billions"]["value"])
        gross_vehicles = float(rows["section232_auto_imports_billions"]["value"])
        assert TRADE_BASELINE["auto_imports_billions"] == pytest.approx(
            gross_vehicles - carveout, rel=1e-6
        )
        assert carveout == pytest.approx(41.02, abs=0.05)
        assert carveout < 0.25 * (389.0 * 0.4842)

    def test_the_base_is_nearly_three_times_the_chapter_proxy(self):
        ratio = create_auto_tariff_25().import_base_billions / H8_AUTO_BASE
        assert 2.7 < ratio < 2.9


class TestNothingWasChosenToLandARow:
    """The falsification test §4.4 of the lane doc registers.

    Every figure is an aggregation of CBO's shipped Census file over CBO's
    shipped article lists at CBO's shipped content shares. The steel row's
    target is −$60B and untraceable; if the base had been chosen to close that
    gap the score would be near it, and it is nowhere near it.
    """

    def test_the_steel_row_is_nowhere_near_its_untraceable_target(self):
        policy = create_steel_tariff_25()
        ten_year = policy.get_trade_summary()["conventional_revenue"] * 10
        assert ten_year > 200.0, (
            "the steel score has moved toward its untraceable -$60B target; "
            "lane R8 registered that as a reason to revert"
        )

    def test_the_fifty_percent_control_is_still_short_of_the_published_figure(self):
        """The one external control that exists, and it does not close.

        Tax Foundation's tracker scores the 50% Section 232 regime (copper
        folded in) at −$341.4B over 2026-2035. On this base the module returns
        about −$191B, where the chapter proxies gave about −$94B: the gap
        halves and does not close. The residual is the unsourced high-rate
        elasticity device, not the base — a carry-over, and this test exists
        so that closing it is visible when someone does.
        """
        from fiscal_model.trade import TariffPolicy

        rows = (
            (
                "primary",
                TRADE_BASELINE["steel_aluminum_imports_billions"],
                0.50 - TRADE_BASELINE["steel_aluminum_existing_avg_tariff"],
            ),
            (
                "derivative",
                TRADE_BASELINE["steel_derivative_imports_billions"],
                0.50 - TRADE_BASELINE["steel_derivative_existing_avg_tariff"],
            ),
        )
        policy = TariffPolicy(
            name="50% Section 232",
            description="Control for lane R8",
            target_sector="steel",
            tariff_rate_change=0.50,
            rate_schedule=rows,
        )
        ten_year = policy.get_trade_summary()["conventional_revenue"] * 10
        assert 180.0 < ten_year < 200.0
        assert ten_year < 341.4, "the control now exceeds Tax Foundation's figure"
