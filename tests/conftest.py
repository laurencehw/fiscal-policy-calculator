"""
Pytest fixtures for fiscal policy calculator tests.
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.policies import TaxPolicy, PolicyType
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType


# =============================================================================
# POLICY FIXTURES
# =============================================================================

@pytest.fixture
def basic_tax_policy():
    """Basic income tax policy for testing."""
    return TaxPolicy(
        name="Test Tax Increase",
        description="2.6pp increase on income above $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
        affected_income_threshold=400_000,
    )


@pytest.fixture
def tax_cut_policy():
    """Tax cut policy for testing."""
    return TaxPolicy(
        name="Test Tax Cut",
        description="2pp cut for all income",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.02,
        affected_income_threshold=0,
    )


@pytest.fixture
def middle_class_policy():
    """Middle class targeted policy."""
    return TaxPolicy(
        name="Middle Class Cut",
        description="1pp cut for income $50K-$200K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.01,
        affected_income_threshold=50_000,
    )


# =============================================================================
# ENGINE FIXTURES
# =============================================================================

@pytest.fixture
def distribution_engine():
    """Distributional analysis engine."""
    return DistributionalEngine(data_year=2022)


# =============================================================================
# DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_macro_scenario():
    """Sample macro scenario for testing."""
    from fiscal_model.models import MacroScenario

    return MacroScenario(
        name="Test Scenario",
        description="Test tax cut scenario",
        start_year=2025,
        horizon_years=10,
        receipts_change=np.array([-100.0] * 10),  # $100B/yr tax cut
        outlays_change=np.zeros(10),
    )


@pytest.fixture
def spending_scenario():
    """Sample spending scenario for testing."""
    from fiscal_model.models import MacroScenario

    return MacroScenario(
        name="Spending Increase",
        description="Test spending scenario",
        start_year=2025,
        horizon_years=10,
        receipts_change=np.zeros(10),
        outlays_change=np.array([50.0] * 10),  # $50B/yr spending increase
    )
