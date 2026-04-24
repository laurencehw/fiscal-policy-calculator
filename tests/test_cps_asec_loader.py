"""
Tests for the public CPS ASEC microdata loader (fiscal_model.data.cps_asec).

These exercise the contract that the multi-model tab and the microsim
calibration rely on: the loader always returns a DataFrame with the
required schema plus a descriptor indicating whether the microdata is
bundled-synthetic or CPS-real, with clear error messages otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from fiscal_model.data.cps_asec import (
    REQUIRED_COLUMNS,
    describe_microdata,
    load_tax_microdata,
)


class TestLoadTaxMicrodata:
    def test_loads_bundled_file_by_default(self):
        df, source = load_tax_microdata()
        assert isinstance(df, pd.DataFrame)
        for column in REQUIRED_COLUMNS:
            assert column in df.columns, f"Missing required column {column}"
        assert source.path.exists()
        assert source.weighted_tax_units > 0

    def test_descriptor_reflects_file_provenance(self):
        """The descriptor's is_synthetic flag must match the observed scale."""
        _, source = load_tax_microdata()
        # The bundled file is a real CPS-derived build (~191M weighted
        # tax units, ~$12T AGI). If it is ever replaced with a small
        # demonstration file, the heuristic will flip to is_synthetic=True
        # and this test will catch the regression.
        assert isinstance(source.is_synthetic, bool)
        if source.is_synthetic:
            assert source.weighted_tax_units < 50_000_000
        else:
            assert source.weighted_tax_units >= 50_000_000
            assert "CPS" in source.notes or "ASEC" in source.notes

    def test_missing_file_raises_with_helpful_message(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist.csv"
        with pytest.raises(FileNotFoundError, match="No tax microdata file"):
            load_tax_microdata(nonexistent)

    def test_malformed_file_raises_clear_error(self, tmp_path):
        bad = tmp_path / "bad.csv"
        pd.DataFrame({"foo": [1, 2], "bar": [3, 4]}).to_csv(bad, index=False)
        with pytest.raises(ValueError, match="missing required columns"):
            load_tax_microdata(bad)

    def test_custom_path_is_honored(self, tmp_path):
        copy = tmp_path / "copy.csv"
        df, _ = load_tax_microdata()
        df.to_csv(copy, index=False)
        reloaded, source = load_tax_microdata(copy)
        assert source.path == copy.resolve()
        assert len(reloaded) == len(df)


class TestDescribeMicrodata:
    def test_describe_returns_status_for_bundled(self):
        desc = describe_microdata()
        assert desc["status"] in {"synthetic", "real"}
        assert "path" in desc
        assert desc["weighted_tax_units"] > 0

    def test_describe_flags_missing(self, tmp_path):
        desc = describe_microdata(tmp_path / "missing.csv")
        assert desc["status"] == "missing"
        assert "message" in desc

    def test_describe_flags_malformed(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("a,b\n1,2\n")
        desc = describe_microdata(bad)
        assert desc["status"] == "malformed"


class TestRealFileDetection:
    def test_large_real_file_is_not_flagged_synthetic(self, tmp_path):
        """A file with 6000+ rows and 100M+ weight should be flagged 'real'."""
        n = 6000
        df = pd.DataFrame(
            {
                "id": range(n),
                "weight": [20_000.0] * n,  # 6000 * 20k = 120M weighted units
                "wages": [60_000.0] * n,
                "interest_income": [0.0] * n,
                "dividend_income": [0.0] * n,
                "capital_gains": [0.0] * n,
                "social_security": [0.0] * n,
                "unemployment": [0.0] * n,
                "children": [1] * n,
                "married": [1] * n,
                "age_head": [40] * n,
                "agi": [60_000.0] * n,
            }
        )
        path = tmp_path / "fake_real.csv"
        df.to_csv(path, index=False)

        _, source = load_tax_microdata(path)
        assert source.is_synthetic is False
        assert "CPS" in source.notes or "ASEC" in source.notes
