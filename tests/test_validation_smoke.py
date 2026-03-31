"""
Smoke tests for fiscal_model/validation — CBO scores database and helpers.

Covers:
- KNOWN_SCORES is a non-empty dict
- Each score has required fields (ten_year_cost, source)
- get_validation_targets returns a list
- All known score values are numeric
- compare_to_cbo-related imports work (validate_all is importable)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.validation.cbo_scores import (
    KNOWN_SCORES,
    CBOScore,
    ScoreSource,
    get_score,
    get_scores_by_type,
    get_validation_targets,
    list_available_policies,
)

# =============================================================================
# KNOWN_SCORES DATABASE
# =============================================================================

class TestKnownScores:

    def test_is_non_empty_dict(self):
        assert isinstance(KNOWN_SCORES, dict)
        assert len(KNOWN_SCORES) > 0

    def test_all_values_are_cbo_score(self):
        for key, score in KNOWN_SCORES.items():
            assert isinstance(score, CBOScore), f"{key} is not a CBOScore"

    def test_each_score_has_ten_year_cost(self):
        for key, score in KNOWN_SCORES.items():
            assert isinstance(score.ten_year_cost, (int, float)), (
                f"{key} ten_year_cost is not numeric"
            )

    def test_each_score_has_source(self):
        for key, score in KNOWN_SCORES.items():
            assert isinstance(score.source, ScoreSource), (
                f"{key} source is not a ScoreSource"
            )

    def test_each_score_has_name(self):
        for _key, score in KNOWN_SCORES.items():
            assert isinstance(score.name, str) and len(score.name) > 0

    def test_each_score_has_policy_id(self):
        for key, score in KNOWN_SCORES.items():
            assert score.policy_id == key, (
                f"policy_id '{score.policy_id}' != dict key '{key}'"
            )

    def test_ten_year_cost_values_are_finite(self):
        import math
        for key, score in KNOWN_SCORES.items():
            assert math.isfinite(score.ten_year_cost), (
                f"{key} has non-finite ten_year_cost: {score.ten_year_cost}"
            )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

class TestHelperFunctions:

    def test_get_score_existing(self):
        score = get_score("tcja_2017_full")
        assert score is not None
        assert score.policy_id == "tcja_2017_full"

    def test_get_score_nonexistent(self):
        score = get_score("does_not_exist_xyz")
        assert score is None

    def test_get_scores_by_type_income_tax(self):
        scores = get_scores_by_type("income_tax")
        assert isinstance(scores, list)
        assert len(scores) > 0
        for s in scores:
            assert s.policy_type == "income_tax"

    def test_get_scores_by_type_spending(self):
        scores = get_scores_by_type("spending")
        assert isinstance(scores, list)
        assert len(scores) > 0

    def test_list_available_policies(self):
        policies = list_available_policies()
        assert isinstance(policies, list)
        assert len(policies) == len(KNOWN_SCORES)
        assert "tcja_2017_full" in policies

    def test_get_validation_targets_returns_list(self):
        targets = get_validation_targets()
        assert isinstance(targets, list)

    def test_validation_targets_have_rate_change(self):
        targets = get_validation_targets()
        for t in targets:
            assert t.rate_change is not None
            assert t.baseline_year >= 2020


# =============================================================================
# IMPORT SMOKE TESTS
# =============================================================================

class TestImports:

    def test_validation_init_importable(self):
        from fiscal_model.validation import KNOWN_SCORES as ks
        assert len(ks) > 0

    def test_validate_all_importable(self):
        from fiscal_model.validation import validate_all
        assert callable(validate_all)

    def test_validation_result_importable(self):
        from fiscal_model.validation import ValidationResult
        assert ValidationResult is not None

    def test_generate_validation_report_importable(self):
        from fiscal_model.validation import generate_validation_report
        assert callable(generate_validation_report)

    def test_run_validation_suite_importable(self):
        from fiscal_model.validation import run_validation_suite
        assert callable(run_validation_suite)
