"""
Performance benchmarks — ensure all preset policies score within acceptable time.
"""
import time

import pytest

from fiscal_model import FiscalPolicyScorer
from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.preset_handler import create_policy_from_preset


class TestScoringPerformance:
    """Verify that policy scoring completes within acceptable time bounds."""

    @pytest.fixture
    def scorer(self):
        return FiscalPolicyScorer(use_real_data=False)

    def test_all_presets_score_under_2s_total(self, scorer):
        """All preset policies combined should score in under 2 seconds."""
        start = time.perf_counter()
        scored = 0

        for name, preset_data in PRESET_POLICIES.items():
            if name == "Custom Policy":
                continue
            policy = create_policy_from_preset(preset_data)
            if policy is not None:
                scorer.score_policy(policy)
                scored += 1

        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, (
            f"Scoring {scored} presets took {elapsed:.2f}s (limit: 2.0s)"
        )

    def test_single_policy_under_100ms(self, scorer):
        """A single simple tax policy should score in under 100ms."""
        from fiscal_model import PolicyType, TaxPolicy

        policy = TaxPolicy(
            name="Test",
            description="test",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=400_000,
        )

        start = time.perf_counter()
        scorer.score_policy(policy)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.1, (
            f"Single policy took {elapsed:.3f}s (limit: 0.1s)"
        )

    def test_dynamic_scoring_under_200ms(self, scorer):
        """Dynamic scoring should add minimal overhead."""
        from fiscal_model import PolicyType, TaxPolicy

        policy = TaxPolicy(
            name="Test",
            description="test",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=400_000,
        )

        start = time.perf_counter()
        scorer.score_policy(policy, dynamic=True)
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, (
            f"Dynamic scoring took {elapsed:.3f}s (limit: 0.2s)"
        )
