"""
Tests for the filing-threshold filter.

The bundled CPS-derived microdata weights to ~191M tax units, while
IRS SOI reports ~161M filers. ``filter_to_filers`` drops the ~30M
non-filers so aggregate calibration against SOI lines up.
"""

from __future__ import annotations

import pandas as pd
import pytest

from fiscal_model.data.cps_asec import load_tax_microdata
from fiscal_model.microsim.filing_threshold import (
    FILING_THRESHOLDS_2023,
    filter_to_filers,
)
from fiscal_model.microsim.soi_calibration import calibrate_to_soi


class TestThresholds:
    def test_2023_thresholds_match_irs(self):
        assert FILING_THRESHOLDS_2023["single"] == 13_850
        assert FILING_THRESHOLDS_2023["married_joint"] == 27_700


class TestFilterOutput:
    def test_filter_drops_some_but_not_most(self):
        df, _ = load_tax_microdata()
        _filtered, report = filter_to_filers(df, year=2023)
        assert report.rows_before > report.rows_after > 0
        # Under the permissive filter we drop ~30-40M weighted units,
        # not 100M+. Lock in a sane range.
        assert 20_000_000 <= report.weighted_removed <= 60_000_000

    def test_filter_brings_coverage_near_soi(self):
        df, _ = load_tax_microdata()
        filtered, _ = filter_to_filers(df, year=2023)
        after = calibrate_to_soi(filtered, year=2023)
        s = after.summary()
        # Target: within 10% of SOI returns total after filtering.
        assert 90 <= s["returns_coverage_pct"] <= 110

    def test_filter_preserves_high_income_records(self):
        """Every record above $100K should survive — clearly filers."""
        df, _ = load_tax_microdata()
        filtered, _ = filter_to_filers(df, year=2023)
        high_before = (df["agi"] >= 100_000).sum()
        high_after = (filtered["agi"] >= 100_000).sum()
        assert high_after == high_before

    def test_filter_keeps_families_with_children(self):
        """Low-AGI families with children are refund-only filers."""
        row = {
            "id": 1,
            "weight": 1_000_000.0,
            "wages": 0.0,
            "interest_income": 0.0,
            "dividend_income": 0.0,
            "capital_gains": 0.0,
            "social_security": 0.0,
            "unemployment": 0.0,
            "children": 2,
            "married": 1,
            "age_head": 35,
            "agi": 5_000.0,  # below statutory threshold
        }
        df = pd.DataFrame([row])
        filtered, _ = filter_to_filers(df, year=2023)
        assert len(filtered) == 1

    def test_filter_drops_zero_income_no_children(self):
        """A tax unit with no income and no children is not filing."""
        row = {
            "id": 1,
            "weight": 1_000_000.0,
            "wages": 0.0,
            "interest_income": 0.0,
            "dividend_income": 0.0,
            "capital_gains": 0.0,
            "social_security": 0.0,
            "unemployment": 0.0,
            "children": 0,
            "married": 0,
            "age_head": 45,
            "agi": 0.0,
        }
        df = pd.DataFrame([row])
        filtered, _ = filter_to_filers(df, year=2023)
        assert len(filtered) == 0


class TestFilterRespectsMarriedThreshold:
    def test_married_couple_below_joint_threshold_dropped_without_signals(self):
        """Married couple at \\$20K AGI is below joint \\$27.7K threshold."""
        row = {
            "id": 1,
            "weight": 1_000_000.0,
            "wages": 0.0,
            "interest_income": 0.0,
            "dividend_income": 0.0,
            "capital_gains": 0.0,
            "social_security": 0.0,
            "unemployment": 0.0,
            "children": 0,
            "married": 1,
            "age_head": 45,
            "agi": 20_000.0,  # below married joint threshold
        }
        df = pd.DataFrame([row])
        filtered, _ = filter_to_filers(df, year=2023)
        assert len(filtered) == 0

    def test_married_couple_above_joint_threshold_kept(self):
        row = {
            "id": 1,
            "weight": 1_000_000.0,
            "wages": 0.0,
            "interest_income": 0.0,
            "dividend_income": 0.0,
            "capital_gains": 0.0,
            "social_security": 0.0,
            "unemployment": 0.0,
            "children": 0,
            "married": 1,
            "age_head": 45,
            "agi": 30_000.0,  # above married joint threshold
        }
        df = pd.DataFrame([row])
        filtered, _ = filter_to_filers(df, year=2023)
        assert len(filtered) == 1


class TestErrors:
    def test_missing_required_column_raises(self):
        # Build a frame missing the `wages` column.
        df = pd.DataFrame({"agi": [10_000], "married": [0], "weight": [1.0]})
        with pytest.raises(ValueError, match="filter_to_filers requires"):
            filter_to_filers(df, year=2023)
