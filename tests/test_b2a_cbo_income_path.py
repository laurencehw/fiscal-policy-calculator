"""Lane B2a: the SOI income base projected on CBO's own income path.

See ``planning/lanes/B2a_cbo_income_path.md``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

from fiscal_model import cbo_income_detail
from fiscal_model.baseline import BaselineProjection, BaselineVintage, CBOBaseline
from fiscal_model.scoring_engine import FiscalPolicyScorer

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _fetch_script():
    path = PROJECT_ROOT / "scripts" / "fetch_cbo_income_detail.py"
    spec = importlib.util.spec_from_file_location("fetch_cbo_income_detail", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def feb_2024() -> BaselineProjection:
    return CBOBaseline(start_year=2025, vintage=BaselineVintage.CBO_FEB_2024).generate()


@pytest.fixture(scope="module")
def feb_2026() -> BaselineProjection:
    return CBOBaseline(start_year=2026, vintage=BaselineVintage.CBO_FEB_2026).generate()


def test_the_vendored_sources_replay_offline():
    """Pins and identities verify against the vendored bytes, no network."""
    assert _fetch_script().main(["--offline-check"]) == 0


def test_check_refuses_a_local_tree():
    module = _fetch_script()
    with pytest.raises(SystemExit):
        module.main(["--check", "--source-dir", str(module.SOURCE_CACHE)])


def test_an_unpinned_file_is_refused():
    module = _fetch_script()
    with pytest.raises(SystemExit):
        module.read_source("data/not/pinned.csv", module.SOURCE_CACHE)


def test_vintages_are_graded_as_in_the_tax_parameter_transcription():
    assert cbo_income_detail.match_grade("cbo_feb_2024") == "nearest_vintage"
    assert cbo_income_detail.match_grade("cbo_jan_2025") == "exact"
    assert cbo_income_detail.match_grade("cbo_feb_2026") == "exact"


def test_series_follows_the_policy_income_measure():
    assert cbo_income_detail.series_for_income_measure("agi") == "rev_iit_agi"
    assert (
        cbo_income_detail.series_for_income_measure("taxable_income")
        == "rev_iit_taxable_income"
    )
    assert cbo_income_detail.series_for_income_measure(None) == "rev_iit_taxable_income"


def test_generated_projection_carries_its_vintage_key(feb_2024, feb_2026):
    assert feb_2024.baseline_vintage_key == "cbo_feb_2024"
    assert feb_2026.baseline_vintage_key == "cbo_feb_2026"


def test_income_base_index_reads_cbo_levels(feb_2024):
    # CBO 2024-06 edition, rev_iit_taxable_income, CY2023 and CY2026 ($B).
    assert feb_2024.income_base_index(2023, "rev_iit_taxable_income") == pytest.approx(12194.937)
    assert feb_2024.income_base_index(2026, "rev_iit_taxable_income") == pytest.approx(13247.113)


def test_years_before_the_edition_are_chain_linked_on_gdp(feb_2024):
    """CY2019 is not in the 2024-06 edition (it starts at CY2021)."""
    series = "rev_iit_taxable_income"
    expected = (
        feb_2024.income_base_index(2021, series)
        * feb_2024.nominal_income_index(2019)
        / feb_2024.nominal_income_index(2021)
    )
    assert feb_2024.income_base_index(2019, series) == pytest.approx(expected)


def test_hand_built_projection_has_no_income_index():
    proj = BaselineProjection(nominal_gdp=np.linspace(28000, 38000, 10))
    assert proj.income_base_index(2027, "rev_iit_taxable_income") == 0.0


def test_scorer_ratio_is_cbo_taxable_income_growth(feb_2026):
    scorer = FiscalPolicyScorer(baseline=feb_2026, start_year=2026)
    expected = 15155.984 / 11960.078  # CY2028 / CY2023, 2026-02 edition
    assert scorer._nominal_income_ratio(2023, 2028) == pytest.approx(expected)
    agi = 20074.8 / 15347.4
    assert scorer._nominal_income_ratio(2023, 2028, "agi") == pytest.approx(agi)


def test_hand_built_baseline_falls_back_to_the_gdp_index():
    """No vintage, no CBO series: the ratio is today's nominal-GDP ratio."""
    gdp = np.linspace(28000.0, 38000.0, 10)
    proj = BaselineProjection(start_year=2026, years=np.arange(2026, 2036), nominal_gdp=gdp)
    scorer = FiscalPolicyScorer(baseline=proj, start_year=2026)
    assert scorer._nominal_income_ratio(2027, 2030) == pytest.approx(gdp[4] / gdp[1])


def test_bracket_income_is_never_the_growth_series():
    """B2a's rule: per-bracket series change meaning in CY2026 (two editions)."""
    assert not any(
        name.startswith("rev_iit_bracket_")
        for name in cbo_income_detail.SERIES_BY_INCOME_MEASURE.values()
    )
