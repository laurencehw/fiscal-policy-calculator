"""
Tests for the opt-in SOI cell calibration (AGI class x filing status).

``calibrate_cells_to_soi`` and the ``by_status`` top-tail path are additive:
nothing in the default data path calls them. These tests pin both halves of
that sentence: the calibration hits the Table 1.2 cell targets it claims to
hit, and the default path (``augment_top_tail`` without ``by_status``,
``collect_microdata`` without ``--calibrate-cells``) is untouched.

Targets are IRS SOI Table 1.2 only; no test here reads a benchmark target.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fiscal_model.data.cps_asec import load_tax_microdata
from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.microsim.soi_calibration import (
    CELL_MODE_COUNT_ONLY,
    CELL_MODE_EMPTY,
    CELL_MODE_HIT,
    calibrate_cells_to_soi,
    calibrate_to_soi,
    filing_status_cells,
)
from fiscal_model.microsim.top_tail import (
    DEFAULT_AUGMENTATION_FLOOR,
    SYNTHETIC_HOUSEHOLD_ID_BASE,
    SYNTHETIC_SOURCE_LABEL,
    augment_top_tail,
    derive_top_tail_floor,
)

YEAR = 2023
REL = 1e-6


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    df, _ = load_tax_microdata()
    return df


@pytest.fixture(scope="module")
def augmented(raw: pd.DataFrame) -> pd.DataFrame:
    out, _ = augment_top_tail(raw, YEAR, by_status=True)
    return out


@pytest.fixture(scope="module")
def calibrated(augmented: pd.DataFrame):
    return calibrate_cells_to_soi(augmented, YEAR)


# ---------------------------------------------------------------------------
# The calibration itself
# ---------------------------------------------------------------------------


class TestCellTargets:
    def test_every_hit_cell_lands_on_both_targets(self, calibrated):
        _, diag = calibrated
        hit = [c for c in diag.cells if c.mode == CELL_MODE_HIT]
        assert len(hit) >= 40  # the vast majority of the 53 cells
        for c in hit:
            assert c.returns_after == pytest.approx(c.target_returns, rel=REL), c
            assert c.agi_billions_after == pytest.approx(c.target_agi_billions, rel=REL), c

    def test_count_only_cells_still_hit_their_return_count(self, calibrated):
        _, diag = calibrated
        fallback = diag.count_only_cells
        assert fallback, "the no-AGI class cannot be hit on AGI, so some cell must fall back"
        for c in fallback:
            assert c.returns_after == pytest.approx(c.target_returns, rel=REL), c

    def test_aggregate_returns_equal_soi_exactly(self, calibrated):
        _, diag = calibrated
        assert diag.returns_coverage_after_pct == pytest.approx(100.0, abs=1e-4)

    def test_agi_gap_is_the_unrepresentable_negative_class(self, calibrated):
        """Just above 100%: SOI's no-AGI class totals negative and no record can be negative."""
        out, diag = calibrated
        soi = IRSSOIData().get_bracket_distribution(YEAR)
        assert soi[0].total_agi < 0
        gap_b = (diag.agi_coverage_after_pct / 100.0 - 1.0) * sum(b.total_agi for b in soi)
        # Within 1% of the negative class's size: the count-only fallback cells
        # (class 0 and one thin head-of-household cell) carry the small remainder.
        assert gap_b == pytest.approx(-soi[0].total_agi, rel=1e-2)
        assert 100.0 < diag.agi_coverage_after_pct < 102.0

    def test_diagnostics_are_internally_consistent(self, calibrated):
        out, diag = calibrated
        assert len(diag.cells) == 53
        assert diag.cells_hit + diag.cells_count_only + diag.cells_empty + diag.cells_no_target == 53
        assert diag.cells_empty == 0
        assert diag.effective_sample_size_after < diag.effective_sample_size_before
        assert diag.max_weight_ratio > 1.0 > diag.min_weight_ratio > 0.0
        assert diag.collapse_unmarried_from_class == 15  # $1.5M, data-derived
        assert diag.to_dict()["cells_hit"] == diag.cells_hit
        # Returns coverage before/after is the report's own number on the same frame.
        assert diag.returns_coverage_after_pct == pytest.approx(
            calibrate_to_soi(out, YEAR).summary()["returns_coverage_pct"], rel=1e-9
        )

    def test_only_the_weight_column_changes(self, augmented, calibrated):
        out, _ = calibrated
        assert list(out.columns) == list(augmented.columns)
        assert len(out) == len(augmented)
        same = [c for c in augmented.columns if c != "weight"]
        pd.testing.assert_frame_equal(out[same], augmented[same])
        assert not np.allclose(out["weight"], augmented["weight"])
        assert (out["weight"] >= 0).all()

    def test_input_is_not_mutated(self, augmented):
        before = augmented["weight"].copy()
        calibrate_cells_to_soi(augmented, YEAR)
        pd.testing.assert_series_equal(augmented["weight"], before)

    def test_deterministic(self, augmented, calibrated):
        again, _ = calibrate_cells_to_soi(augmented, YEAR)
        pd.testing.assert_series_equal(again["weight"], calibrated[0]["weight"])


class TestIdempotence:
    def test_calibrating_a_calibrated_frame_changes_nothing(self, calibrated):
        out, diag = calibrated
        again, diag2 = calibrate_cells_to_soi(out, YEAR)
        np.testing.assert_allclose(again["weight"], out["weight"], rtol=1e-6)
        assert diag2.cells_hit == diag.cells_hit
        assert diag2.cells_count_only == diag.cells_count_only
        assert diag2.max_weight_ratio == pytest.approx(1.0, abs=1e-5)


class TestEmptyAndFallbackCells:
    def test_cells_without_rows_are_flagged_not_papered_over(self):
        """Only married units in one class: the hoh and single cells there are empty."""
        df = pd.DataFrame(
            {
                "agi": [60_000.0, 62_000.0, 66_000.0, 70_000.0, 72_000.0, 58_000.0],
                "weight": [1.0] * 6,
                "married": [1] * 6,
                "dependent_count": [0] * 6,
            }
        )
        out, diag = calibrate_cells_to_soi(df, YEAR)
        empties = {(c.agi_class, c.status) for c in diag.empty_cells}
        # 50-75K is SOI class 9.
        assert (9, "hoh") in empties and (9, "single") in empties
        assert (9, "married") not in empties
        assert diag.unrepresented_returns > 0
        for c in diag.empty_cells:
            assert c.returns_after == 0.0 and c.rows == 0
        # The married cell was calibrated; the empty ones were not invented.
        married = next(c for c in diag.cells if (c.agi_class, c.status) == (9, "married"))
        assert married.mode == CELL_MODE_HIT
        assert out["weight"].sum() == pytest.approx(married.target_returns, rel=REL)

    def test_target_mean_outside_the_cell_range_falls_back_to_count_only(self):
        # Class 9 (50-75K) married mean AGI is well above 51K, so a cell whose
        # rows all sit at ~51K cannot be tilted to the AGI target.
        df = pd.DataFrame(
            {
                "agi": np.linspace(50_100.0, 51_000.0, 8),
                "weight": [10.0] * 8,
                "married": [1] * 8,
                "dependent_count": [0] * 8,
            }
        )
        _, diag = calibrate_cells_to_soi(df, YEAR)
        cell = next(c for c in diag.cells if (c.agi_class, c.status) == (9, "married"))
        assert cell.mode == CELL_MODE_COUNT_ONLY
        assert cell.returns_after == pytest.approx(cell.target_returns, rel=REL)

    def test_count_only_option_skips_the_agi_target(self, augmented):
        _, diag = calibrate_cells_to_soi(augmented, YEAR, use_agi=False)
        assert diag.cells_hit == 0
        assert diag.returns_coverage_after_pct == pytest.approx(100.0, abs=1e-4)

    def test_missing_columns_raise(self):
        with pytest.raises(ValueError, match="married"):
            calibrate_cells_to_soi(pd.DataFrame({"agi": [1.0], "weight": [1.0]}), YEAR)

    def test_status_rule(self):
        df = pd.DataFrame({"married": [1, 0, 0], "dependent_count": [2, 1, 0]})
        assert list(filing_status_cells(df)) == ["married", "hoh", "single"]


# ---------------------------------------------------------------------------
# The by_status top-tail path, and the default path it must not touch
# ---------------------------------------------------------------------------


class TestByStatusTopTail:
    def test_floor_is_derived_from_the_data(self, raw):
        brackets = IRSSOIData().get_bracket_distribution(YEAR)
        assert derive_top_tail_floor(raw, brackets) == 1_500_000.0
        # A looser threshold moves the floor up the class ladder.
        assert derive_top_tail_floor(raw, brackets, min_cps_rows=1) > 1_500_000.0

    def test_synthetic_rows_survive_the_household_layer(self, augmented):
        synth = augmented[augmented["source"] == SYNTHETIC_SOURCE_LABEL]
        assert len(synth) == 800  # 4 classes x 2 statuses x 100
        assert synth["household_id"].is_unique
        assert (synth["household_id"] >= SYNTHETIC_HOUSEHOLD_ID_BASE).all()
        assert (synth["household_weight"] > 0).all()
        assert not set(synth["household_id"]) & set(
            augmented.loc[augmented["source"] != SYNTHETIC_SOURCE_LABEL, "household_id"]
        )
        assert set(synth["married"]) == {0, 1}

    def test_cps_rows_in_augmented_classes_are_replaced(self, raw, augmented):
        cps = augmented[augmented["source"] != SYNTHETIC_SOURCE_LABEL]
        assert len(cps) < len(raw)
        assert (cps["agi"] < 1_500_000.0).all()

    def test_idempotent(self, augmented):
        again, _ = augment_top_tail(augmented, YEAR, by_status=True)
        pd.testing.assert_frame_equal(again.reset_index(drop=True), augmented.reset_index(drop=True))

    def test_status_aware_cells_reproduce_table_1_2_returns(self, augmented):
        by = IRSSOIData().get_bracket_distribution_by_status(YEAR)
        synth = augmented[augmented["source"] == SYNTHETIC_SOURCE_LABEL]
        married = synth.loc[synth["married"] == 1, "weight"].sum()
        unmarried = synth.loc[synth["married"] == 0, "weight"].sum()
        top = range(15, 19)
        want_m = sum(by["joint"][i].num_returns + by["separate"][i].num_returns for i in top)
        want_u = sum(by["head_of_household"][i].num_returns + by["single"][i].num_returns for i in top)
        assert married == pytest.approx(want_m, rel=1e-9)
        assert unmarried == pytest.approx(want_u, rel=1e-9)


class TestDefaultPathUntouched:
    def test_default_call_equals_the_explicit_default_floor(self, raw):
        default, rep = augment_top_tail(raw, YEAR)
        explicit, rep2 = augment_top_tail(
            raw, YEAR, floor=DEFAULT_AUGMENTATION_FLOOR, by_status=False
        )
        pd.testing.assert_frame_equal(default, explicit)
        assert rep == rep2

    def test_default_synthetic_rows_are_still_the_old_shape(self, raw):
        """The household-layer defect is fixed in the new path only."""
        default, rep = augment_top_tail(raw, YEAR)
        assert rep.floor == DEFAULT_AUGMENTATION_FLOOR
        assert rep.synthetic_records == 600
        synth = default[default["source"] == SYNTHETIC_SOURCE_LABEL]
        assert (synth["household_id"] == 0).all()
        assert (synth["household_weight"] == 0).all()
        assert (synth["married"] == 1).all()
        assert len(default) == len(raw) + 600

    def test_calibration_never_runs_unless_asked(self, raw):
        """A plain augmented frame keeps its original weights."""
        default, _ = augment_top_tail(raw, YEAR)
        assert default.loc[default["source"] == "cps", "weight"].equals(raw["weight"])
