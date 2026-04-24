"""
Tests for the SOI-based top-tail augmentation of CPS microdata.

The bundled CPS-derived microdata tops out near \\$2M AGI because CPS
top-codes incomes. ``augment_top_tail`` injects synthetic records from
IRS SOI aggregate brackets so distributional analyses that depend on
the right tail (capital gains, SALT, step-up basis) don't systematically
under-represent it.
"""

from __future__ import annotations

from fiscal_model.data.cps_asec import load_tax_microdata
from fiscal_model.microsim.soi_calibration import calibrate_to_soi
from fiscal_model.microsim.top_tail import (
    DEFAULT_AUGMENTATION_FLOOR,
    SYNTHETIC_SOURCE_LABEL,
    augment_top_tail,
    filter_source,
)


class TestAugmentationBasics:
    def test_default_floor_is_two_million(self):
        assert DEFAULT_AUGMENTATION_FLOOR == 2_000_000

    def test_augmentation_adds_rows_above_floor(self):
        base, _ = load_tax_microdata()
        augmented, report = augment_top_tail(base, year=2023)
        assert len(augmented) > len(base)
        assert report.synthetic_records > 0
        assert report.brackets_used >= 2

    def test_augmented_rows_are_tagged(self):
        base, _ = load_tax_microdata()
        augmented, _ = augment_top_tail(base, year=2023)
        assert "source" in augmented.columns
        tags = set(augmented["source"].unique())
        assert "cps" in tags
        assert SYNTHETIC_SOURCE_LABEL in tags


class TestCoverageImprovement:
    def test_top_bracket_coverage_reaches_one(self):
        """$10M+ bracket should go from 0% coverage to ~100%."""
        base, _ = load_tax_microdata()
        augmented, _ = augment_top_tail(base, year=2023)

        before = calibrate_to_soi(base, year=2023)
        after = calibrate_to_soi(augmented, year=2023)

        # Find the $10M+ (top) bracket in both reports.
        top_before = before.brackets[-1]
        top_after = after.brackets[-1]

        assert top_before.agi_ratio is None or top_before.agi_ratio < 0.05
        assert top_after.agi_ratio is not None
        # Augmentation should reach at least 90% coverage at the top.
        assert top_after.agi_ratio >= 0.9

    def test_dollar_bracket_1m_to_10m_improves(self):
        r"""\$1M-\$10M coverage goes from ~37% to near 100%."""
        base, _ = load_tax_microdata()
        augmented, _ = augment_top_tail(base, year=2023)

        before = calibrate_to_soi(base, year=2023)
        after = calibrate_to_soi(augmented, year=2023)

        # Find the $1M-$10M bracket.
        def _find(bracket_list, lower):
            for b in bracket_list:
                if b.lower == lower:
                    return b
            return None

        b_before = _find(before.brackets, 1_000_000)
        b_after = _find(after.brackets, 1_000_000)
        assert b_before is not None and b_after is not None

        # Before: ~0.37. After: should be much closer to 1.0.
        assert b_after.agi_ratio > b_before.agi_ratio + 0.3


class TestIdempotence:
    def test_double_augmentation_does_not_stack(self):
        """Calling augment_top_tail twice should replace, not stack."""
        base, _ = load_tax_microdata()
        once, _ = augment_top_tail(base, year=2023)
        twice, _ = augment_top_tail(once, year=2023)

        synth_once = (once["source"] == SYNTHETIC_SOURCE_LABEL).sum()
        synth_twice = (twice["source"] == SYNTHETIC_SOURCE_LABEL).sum()
        assert synth_once == synth_twice


class TestDeterminism:
    def test_same_seed_produces_same_output(self):
        base, _ = load_tax_microdata()
        a, _ = augment_top_tail(base, year=2023, seed=42)
        b, _ = augment_top_tail(base, year=2023, seed=42)

        a_synth = a.loc[a["source"] == SYNTHETIC_SOURCE_LABEL, "agi"].sort_values().values
        b_synth = b.loc[b["source"] == SYNTHETIC_SOURCE_LABEL, "agi"].sort_values().values
        assert (a_synth == b_synth).all()

    def test_different_seeds_produce_different_draws(self):
        base, _ = load_tax_microdata()
        a, _ = augment_top_tail(base, year=2023, seed=1)
        b, _ = augment_top_tail(base, year=2023, seed=2)

        a_synth = sorted(a.loc[a["source"] == SYNTHETIC_SOURCE_LABEL, "agi"].values)
        b_synth = sorted(b.loc[b["source"] == SYNTHETIC_SOURCE_LABEL, "agi"].values)
        # With 600 records, the sorted sequences should differ somewhere.
        assert a_synth != b_synth


class TestFilterSource:
    def test_filter_source_recovers_only_cps(self):
        base, _ = load_tax_microdata()
        augmented, _ = augment_top_tail(base, year=2023)
        cps_only = filter_source(augmented, sources=("cps",))
        assert len(cps_only) == len(base)
        assert (cps_only["source"] == "cps").all()

    def test_filter_source_recovers_only_synthetic(self):
        base, _ = load_tax_microdata()
        augmented, _ = augment_top_tail(base, year=2023)
        synth_only = filter_source(augmented, sources=(SYNTHETIC_SOURCE_LABEL,))
        assert len(synth_only) > 0
        assert (synth_only["source"] == SYNTHETIC_SOURCE_LABEL).all()


class TestReport:
    def test_report_matches_returned_frame(self):
        base, _ = load_tax_microdata()
        augmented, report = augment_top_tail(base, year=2023)
        synth = augmented.loc[augmented["source"] == SYNTHETIC_SOURCE_LABEL]
        assert report.synthetic_records == len(synth)
        assert abs(report.synthetic_weight - synth["weight"].sum()) < 1.0
        # AGI total in report should match the weighted sum to within rounding.
        agi_billions = (synth["weight"] * synth["agi"]).sum() / 1e9
        assert abs(report.synthetic_agi_billions - agi_billions) < 0.1
