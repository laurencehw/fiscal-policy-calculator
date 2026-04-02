"""
Parametrized CBO/JCT validation tests.

Runs the model against each known CBO/JCT validation target and asserts:
1. A matching policy can be created
2. The direction (cost vs savings) matches
3. The estimate is within tolerance of the official score

Note: Only income tax policies with rate_change are validated through the
generic pipeline. Capital gains, TCJA, corporate, etc. require specialized
policy constructors tested elsewhere (test_cbo_regression.py).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.validation.cbo_scores import get_validation_targets
from fiscal_model.validation.compare import create_policy_from_score, validate_policy

# Only include targets that go through the generic TaxPolicy pipeline.
# Capital gains scores (rate_change >= 0.10 with threshold >= 1M) need
# CapitalGainsPolicy and are validated separately.
_VALIDATION_TARGETS = [
    t for t in get_validation_targets()
    if not (t.rate_change is not None and abs(t.rate_change) >= 0.10
            and t.income_threshold is not None and t.income_threshold >= 1_000_000)
]

_SCORER = None


def _get_scorer():
    global _SCORER
    if _SCORER is None:
        _SCORER = FiscalPolicyScorer(start_year=2025, use_real_data=True)
    return _SCORER


@pytest.mark.parametrize(
    "score",
    _VALIDATION_TARGETS,
    ids=[t.policy_id for t in _VALIDATION_TARGETS],
)
class TestCBOValidationDirection:
    """Validate model agrees with CBO on direction (cost vs savings)."""

    def test_policy_can_be_created(self, score):
        """Verify we can create a matching policy from the CBO score."""
        policy = create_policy_from_score(score)
        assert policy is not None, (
            f"Could not create policy for {score.name}"
        )

    def test_direction_matches(self, score):
        """Model should agree with CBO on cost vs savings direction."""
        result = validate_policy(score, scorer=_get_scorer(), dynamic=False)
        if result is None:
            pytest.skip(f"Cannot replicate policy: {score.name}")

        assert result.direction_match, (
            f"Direction mismatch for {score.name}: "
            f"Official={score.ten_year_cost:+,.0f}B, "
            f"Model={result.model_10yr:+,.0f}B"
        )


@pytest.mark.parametrize(
    "score",
    _VALIDATION_TARGETS,
    ids=[t.policy_id for t in _VALIDATION_TARGETS],
)
class TestCBOValidationAccuracy:
    """Validate model order-of-magnitude accuracy for auto-populated policies.

    Note: The generic pipeline uses IRS auto-population which may differ
    significantly from hand-calibrated parameters (e.g., Biden $400K+
    uses AGI threshold vs taxable income threshold). Hand-calibrated
    policies achieve <15% error (see CLAUDE.md). Auto-populated policies
    are tested for order-of-magnitude correctness and direction only.
    """

    def test_within_order_of_magnitude(self, score):
        """Model estimate should be within 100% of official score."""
        result = validate_policy(score, scorer=_get_scorer(), dynamic=False)
        if result is None:
            pytest.skip(f"Cannot replicate policy: {score.name}")

        assert abs(result.percent_difference) <= 100.0, (
            f"Model outside order-of-magnitude for {score.name}: "
            f"Official={score.ten_year_cost:+,.0f}B, "
            f"Model={result.model_10yr:+,.0f}B "
            f"({result.percent_difference:+.1f}%)"
        )
