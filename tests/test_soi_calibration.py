"""
Tests for the microsim-to-SOI calibration harness.

Calibration is the gate that lets the microsim produce defensible
aggregates. These tests cover the three paths we care about: the
bracket-level comparison produces sensible output against real SOI
Table 1.1 data; the reweighter brings a bracket into agreement; and
the report contract stays stable so CI can parse it.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.microsim.soi_calibration import (
    DEFAULT_CALIBRATION_BRACKETS,
    BracketComparison,
    CalibrationReport,
    calibrate_to_soi,
    reweight_to_soi,
)


@pytest.fixture
def fake_microdata() -> pd.DataFrame:
    """Deliberately thin synthetic sample — just enough to populate brackets."""
    rows = []
    # Populate a few brackets with obviously-undercounted weights.
    for agi, weight in [
        (10_000, 1.0),
        (25_000, 1.0),
        (60_000, 2.0),
        (120_000, 3.0),
        (250_000, 1.0),
        (750_000, 0.5),
        (2_000_000, 0.2),
    ]:
        rows.append(
            {
                "id": len(rows),
                "weight": weight * 1_000_000,  # weights in units of filers
                "agi": agi,
                "wages": agi * 0.9,
                "interest_income": 0.0,
                "dividend_income": 0.0,
                "capital_gains": 0.0,
                "social_security": 0.0,
                "unemployment": 0.0,
                "children": 0,
                "married": 0,
                "age_head": 40,
            }
        )
    return pd.DataFrame(rows)


class TestCalibrateToSOI:
    def test_returns_one_row_per_bracket(self, fake_microdata):
        report = calibrate_to_soi(fake_microdata, year=2022)
        assert isinstance(report, CalibrationReport)
        assert len(report.brackets) == len(DEFAULT_CALIBRATION_BRACKETS)
        assert all(isinstance(b, BracketComparison) for b in report.brackets)

    def test_each_bracket_has_soi_counts(self, fake_microdata):
        report = calibrate_to_soi(fake_microdata, year=2022)
        # At least some bracket should find SOI returns.
        assert any(b.soi_returns > 0 for b in report.brackets)

    def test_total_soi_returns_roughly_matches_known_population(self, fake_microdata):
        """SOI Table 1.1 totals to ~150M filers nationwide in recent years."""
        report = calibrate_to_soi(fake_microdata, year=2022)
        total_soi = report.total_soi_returns
        assert 100_000_000 <= total_soi <= 200_000_000, (
            f"Expected ~150M SOI filers, got {total_soi:,.0f}"
        )

    def test_microsim_undercount_flagged_in_ratio(self, fake_microdata):
        """With our intentionally-small fake weights, microsim/SOI < 1 in most brackets."""
        report = calibrate_to_soi(fake_microdata, year=2022)
        populated = [b for b in report.brackets if b.soi_returns > 0 and b.microsim_returns > 0]
        assert populated, "Expected at least one populated bracket"
        ratios = [b.returns_ratio for b in populated if b.returns_ratio is not None]
        # Our fake weights are at most 3e6 per bracket; real SOI has hundreds of millions.
        assert all(r < 1.0 for r in ratios)

    def test_summary_matches_totals(self, fake_microdata):
        report = calibrate_to_soi(fake_microdata, year=2022)
        summary = report.summary()
        assert summary["year"] == 2022
        assert summary["total_microsim_returns_millions"] == pytest.approx(
            report.total_microsim_returns / 1e6
        )
        assert 0 <= summary["returns_coverage_pct"] <= 1000

    def test_to_dataframe_is_usable(self, fake_microdata):
        df = calibrate_to_soi(fake_microdata, year=2022).to_dataframe()
        assert {"AGI lower", "Microsim returns (M)", "SOI returns (M)"} <= set(df.columns)

    def test_missing_columns_raise_clearly(self):
        df = pd.DataFrame({"agi": [10, 20]})  # no weight column
        with pytest.raises(ValueError, match="agi.*weight|weight"):
            calibrate_to_soi(df, year=2022)

    def test_injects_loader_for_isolation(self, fake_microdata):
        loader = IRSSOIData()
        report = calibrate_to_soi(fake_microdata, year=2022, soi_loader=loader)
        assert report.total_soi_returns > 0


class TestReweightToSOI:
    def test_reweight_brings_bracket_closer_to_soi(self, fake_microdata):
        before = calibrate_to_soi(fake_microdata, year=2022)
        adjusted = reweight_to_soi(fake_microdata, year=2022)
        after = calibrate_to_soi(adjusted, year=2022)

        for bracket_before, bracket_after in zip(before.brackets, after.brackets, strict=True):
            if bracket_before.soi_returns <= 0 or bracket_before.microsim_returns <= 0:
                continue
            # After reweighting with a clipped 10x cap, each populated bracket
            # should move *toward* SOI — either exactly matching, or at least
            # no worse in absolute ratio terms.
            err_before = abs(1.0 - (bracket_before.returns_ratio or 0.0))
            err_after = abs(1.0 - (bracket_after.returns_ratio or 0.0))
            assert err_after <= err_before + 1e-6, (
                f"Bracket {bracket_before.lower}: reweight made returns ratio "
                f"worse ({err_before:.2f} -> {err_after:.2f})"
            )

    def test_reweight_is_copy_by_default(self, fake_microdata):
        original_weights = fake_microdata["weight"].copy()
        reweight_to_soi(fake_microdata, year=2022)
        pd.testing.assert_series_equal(
            fake_microdata["weight"], original_weights, check_names=False
        )

    def test_reweight_inplace_mutates(self, fake_microdata):
        original_weights = fake_microdata["weight"].copy()
        reweight_to_soi(fake_microdata, year=2022, inplace=True)
        assert not fake_microdata["weight"].equals(original_weights)

    def test_reweight_respects_clip_bounds(self, fake_microdata):
        """A 10x cap means no weight should grow by more than 10x."""
        before = fake_microdata["weight"].copy()
        after = reweight_to_soi(fake_microdata, year=2022)
        ratio = after["weight"] / before
        ratio = ratio.replace([float("inf")], 10.0).fillna(1.0)
        assert ratio.min() >= 0.1 - 1e-9
        assert ratio.max() <= 10.0 + 1e-9
