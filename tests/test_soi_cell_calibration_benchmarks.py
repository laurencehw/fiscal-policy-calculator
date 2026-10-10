"""
What cell calibration moves downstream, recorded as measurements.

Cell calibration is the default population since R6c
(``planning/lanes/R6c_salt_mechanism_and_calibration_default.md``); before that
it was opt-in (``planning/lanes/R6_microdata_cell_calibration.md``). This file
records, raw CPS file against the calibrated default, what the swap does to the
distributional benchmarks and the three derived credits rows. It does **not**
assert that calibration improves anything.

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
from fiscal_model.validation.benchmark_runners import default_model_runner
from fiscal_model.validation.cbo_distributions import run_full_cbo_jct_validation

YEAR = 2023


@pytest.fixture(scope="module")
def raw() -> pd.DataFrame:
    df, _ = load_tax_microdata()
    return df


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
    def test_recorded_movement_and_the_salt_row(self, monkeypatch, raw):
        """Five of seven rows do not move; the SALT row goes 14.91 -> 5.65pp.

        R6 recorded the opposite direction (5.86 -> 11.01pp) under the old
        engine: an AMT that taxed gains at 28% and bound on every $1.5M+ row,
        and a flat SALT rate on AGI. With the statutory AMT and SOI Table 2.1
        SALT ratios (R6c) the raw file is the one that misses, because it has
        almost no top tail. ARP 2021 (household universe) moves in the 4th
        decimal.
        """
        before = _benchmark_errors(monkeypatch, raw)
        monkeypatch.undo()
        after = _benchmark_errors(monkeypatch, None)

        moved = {"jct_salt_repeal_2024", "cbo_arp_2021"}
        unmoved = [
            pid
            for pid in before
            if pid not in moved and after[pid] == pytest.approx(before[pid], abs=0.005)
        ]
        assert len(before) == 7
        assert len(unmoved) == 5

        assert before["jct_salt_repeal_2024"] == pytest.approx(14.9090, abs=5e-4)
        assert after["jct_salt_repeal_2024"] == pytest.approx(5.6541, abs=5e-4)
        assert before["cbo_arp_2021"] == pytest.approx(3.7203, abs=5e-4)
        assert after["cbo_arp_2021"] == pytest.approx(3.7204, abs=5e-4)


class TestCreditsRows:
    @pytest.mark.parametrize(
        ("factory", "raw_10yr", "calibrated_10yr"),
        [
            (create_biden_ctc_2021, -1528.5, -1440.5),
            (create_ctc_permanent_extension, -714.2, -799.6),
            (create_biden_eitc_childless, -110.4, -176.8),
        ],
    )
    def test_derived_credits_score_on_the_two_populations(
        self, monkeypatch, raw, factory, raw_10yr, calibrated_10yr
    ):
        """Recorded movement of the derived (not fitted) credits rows, $B over ten years.

        The default population is the calibrated one (R6c); the raw CPS file is
        swapped in to record what it gave.
        """
        original = credits_microdata._base_population
        keep = [c for c in original().columns if c in raw.columns]

        def score() -> float:
            policy = factory()
            policy.mode = "derived"
            annual = credits_microdata.derived_annual_for_policy(policy)
            assert annual is not None
            return round(annual * 10, 1)

        assert score() == pytest.approx(calibrated_10yr, abs=0.1)
        monkeypatch.setattr(credits_microdata, "_base_population", lambda: raw[keep].copy())
        assert score() == pytest.approx(raw_10yr, abs=0.1)
