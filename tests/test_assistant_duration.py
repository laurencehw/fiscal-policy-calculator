"""``duration_years`` must reach the scoring engine from Ask's tool.

Defect (2026-10 hunt): ``Policy`` honours ``duration_years`` only when
``sunset=True`` and ``score_hypothetical_policy`` never set it, so a "3-year"
policy was scored for ten years and the argument was a silent no-op.
"""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.assistant.tools import AssistantTools
from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture(scope="module")
def tools() -> AssistantTools:
    scorer = FiscalPolicyScorer()
    return AssistantTools(
        scorer=scorer,
        baseline=scorer.baseline,
        cbo_score_map=CBO_SCORE_MAP,
        presets=PRESET_POLICIES,
        policy_types=PolicyType,
        tax_policy_cls=TaxPolicy,
        spending_policy_cls=SpendingPolicy,
    )


def _score(tools: AssistantTools, **kw):
    result = tools.dispatch("score_hypothetical_policy", {"name": "dur", **kw})
    assert "error" not in result, result
    return result


def _active_years(result) -> int:
    by_year = np.asarray(result["final_deficit_by_year"], dtype=float)
    return int(np.count_nonzero(np.abs(by_year) > 1e-9))


@pytest.mark.parametrize(
    "kw",
    [
        {"policy_type": "income_tax", "rate_change": 0.02, "affected_income_threshold": 400_000},
        {"policy_type": "corporate_tax", "rate_change": 0.04},
        {"policy_type": "discretionary_nondefense", "spending_change_billions": 50.0},
    ],
    ids=["income_tax", "corporate_tax", "spending"],
)
def test_three_year_policy_scores_three_years_not_ten(tools, kw) -> None:
    ten = _score(tools, duration_years=10, **kw)
    three = _score(tools, duration_years=3, **kw)
    assert _active_years(ten) == 10
    assert _active_years(three) == 3
    # The three active years are the first three, and match the ten-year run's.
    ten_by = np.asarray(ten["final_deficit_by_year"], dtype=float)
    three_by = np.asarray(three["final_deficit_by_year"], dtype=float)
    assert np.allclose(three_by[:3], ten_by[:3])
    assert np.allclose(three_by[3:], 0.0)
    assert abs(three["raw_engine_estimate_billions"]) < abs(ten["raw_engine_estimate_billions"])


def test_default_duration_is_byte_identical_to_a_full_window(tools) -> None:
    kw = {"policy_type": "income_tax", "rate_change": 0.02, "affected_income_threshold": 400_000}
    default = _score(tools, **kw)
    explicit = _score(tools, duration_years=10, **kw)
    longer = _score(tools, duration_years=25, **kw)
    assert default["raw_engine_estimate_billions"] == explicit["raw_engine_estimate_billions"]
    assert default["raw_engine_estimate_billions"] == longer["raw_engine_estimate_billions"]


def test_non_positive_duration_is_an_error_not_a_silent_ten_years(tools) -> None:
    result = tools.dispatch(
        "score_hypothetical_policy",
        {"name": "x", "policy_type": "corporate_tax", "rate_change": 0.04, "duration_years": 0},
    )
    assert "error" in result
