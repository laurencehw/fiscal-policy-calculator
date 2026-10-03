"""
What the opt-in cell calibration moves downstream, recorded as measurements.

This file does **not** assert that calibration improves anything. It records,
as a documented regression where it is one, what happens to the distributional
benchmarks and the three derived credits rows when the microdata is swapped for
the cell-calibrated frame (``planning/lanes/R6_microdata_cell_calibration.md``).

If a number here moves, an upstream module changed; update the record with the
new measurement and say why, never retune the calibration to restore a figure.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

import fiscal_model.credits_microdata as credits_microdata
from fiscal_model.credits_factory import (
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_permanent_extension,
)
from fiscal_model.data.cps_asec import load_tax_microdata
from fiscal_model.distribution_engine import DistributionalEngine
from fiscal_model.microsim.soi_calibration import calibrate_cells_to_soi
from fiscal_model.microsim.top_tail import augment_top_tail
from fiscal_model.validation.benchmark_runners import default_model_runner
from fiscal_model.validation.cbo_distributions import run_full_cbo_jct_validation

YEAR = 2023


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    df, _ = load_tax_microdata()
    return df


@pytest.fixture(scope="module")
def calibrated(raw: pd.DataFrame) -> pd.DataFrame:
    aug, _ = augment_top_tail(raw, YEAR, by_status=True)
    out, _ = calibrate_cells_to_soi(aug, YEAR)
    return out


def _benchmark_errors(
    monkeypatch: pytest.MonkeyPatch, microdata: pd.DataFrame | None
) -> dict[str, float]:
    """Mean absolute share error (pp) per benchmark, on ``microdata`` or the default."""
    if microdata is not None:
        original = DistributionalEngine.analyze_policy_microsim

        def on_supplied_microdata(self, policy, microdata=None, **kwargs):  # type: ignore[no-untyped-def]
            return original(self, policy, microdata=supplied, **kwargs)

        supplied = microdata
        monkeypatch.setattr(DistributionalEngine, "analyze_policy_microsim", on_supplied_microdata)
    logging.disable(logging.CRITICAL)
    try:
        comparisons = run_full_cbo_jct_validation(default_model_runner)
    finally:
        logging.disable(logging.NOTSET)
    return {c.benchmark.policy_id: c.mean_absolute_share_error_pp for c in comparisons}


class TestDistributionalBenchmarks:
    def test_recorded_movement_and_the_salt_regression(self, monkeypatch, calibrated):
        """Six of seven rows do not move; the SALT row gets WORSE, 5.86 -> 11.01pp.

        This is a documented regression, not an expectation of improvement.
        Cause (see the lane doc): the 5.86pp was a cancellation. SALT is imputed
        as a flat state rate on AGI, the AMT binds on every synthetic $2M+ row,
        and JCT ranks by expanded income where the model ranks by AGI. Giving
        the top tail its true weight exposes that; it is not a reason to retune.
        """
        before = _benchmark_errors(monkeypatch, None)
        monkeypatch.undo()
        after = _benchmark_errors(monkeypatch, calibrated)

        unmoved = [
            pid
            for pid in before
            if pid != "jct_salt_repeal_2024" and after[pid] == pytest.approx(before[pid], abs=0.005)
        ]
        assert len(before) == 7
        assert len(unmoved) == 6  # every row but the SALT one: the other six do not move

        assert before["jct_salt_repeal_2024"] == pytest.approx(5.86, abs=0.01)
        assert after["jct_salt_repeal_2024"] == pytest.approx(11.01, abs=0.01)
        assert after["jct_salt_repeal_2024"] > before["jct_salt_repeal_2024"]
        # ARP 2021 is on the household universe and stays at 3.72pp.
        assert after["cbo_arp_2021"] == pytest.approx(3.72, abs=0.01)


class TestCreditsRows:
    @pytest.mark.parametrize(
        ("factory", "default_10yr", "calibrated_10yr"),
        [
            (create_biden_ctc_2021, -1528.5, -1440.5),
            (create_ctc_permanent_extension, -714.2, -799.6),
            (create_biden_eitc_childless, -110.4, -176.8),
        ],
    )
    def test_derived_credits_score_on_the_two_populations(
        self, monkeypatch, calibrated, factory, default_10yr, calibrated_10yr
    ):
        """Recorded movement of the derived (not fitted) credits rows, $B over ten years."""
        original = credits_microdata._base_population
        keep = [c for c in original().columns if c in calibrated.columns]

        def score() -> float:
            policy = factory()
            policy.mode = "derived"
            annual = credits_microdata.derived_annual_for_policy(policy)
            assert annual is not None
            return round(annual * 10, 1)

        assert score() == pytest.approx(default_10yr, abs=0.1)
        monkeypatch.setattr(credits_microdata, "_base_population", lambda: calibrated[keep].copy())
        assert score() == pytest.approx(calibrated_10yr, abs=0.1)
