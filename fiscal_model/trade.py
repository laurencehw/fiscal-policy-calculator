"""
Trade and Tariff Policy Module

Models tariff revenue, consumer price effects, retaliation costs,
and trade flow impacts.

Key estimates calibrated to Tax Foundation / Yale Budget Lab:
- Trump universal 10% tariff: ~$2T revenue/10yr, ~$1,700/household
- Trump 60% China tariff: ~$500B revenue/10yr
- 25% auto tariff: ~$100B revenue/10yr
- Reciprocal tariffs (~20pp avg): ~$1.2T revenue/10yr

References:
- Amiti, Redding & Weinstein (2019): Tariff pass-through ~100%
- Tax Foundation (2024): Trump tariff revenue estimates
- Yale Budget Lab (2024): Trade policy analysis
- USITC (2023): Import and export statistics
"""

from dataclasses import dataclass

from .policies import PolicyType, TaxPolicy

TRADE_BASELINE = {
    # US trade flows (2024)
    "total_imports_billions": 3200.0,
    "total_exports_billions": 2100.0,
    "current_avg_tariff_rate": 0.03,
    "current_tariff_revenue_billions": 80.0,
    "us_households": 130_000_000,

    # Country-specific import bases
    "china_imports_billions": 430.0,
    "eu_imports_billions": 550.0,
    "auto_imports_billions": 380.0,
    "steel_aluminum_imports_billions": 50.0,

    # Behavioral parameters
    "consumer_pass_through_rate": 0.60,
    "import_price_elasticity": -0.50,
    "retaliation_rate": 0.30,
    "tariff_avoidance_rate": 0.05,
    # Effective coverage: not all imports subject (exemptions, existing tariffs, de minimis)
    "universal_coverage_rate": 0.70,  # ~70% of imports effectively covered
}


CBO_TRADE_ESTIMATES = {
    "trump_universal_10": {
        "10yr_score": -2000.0,
        "source": "Tax Foundation / Yale Budget Lab",
    },
    "trump_china_60": {
        "10yr_score": -500.0,
        "source": "Tax Foundation",
    },
    "auto_tariff_25": {
        "10yr_score": -100.0,
        "source": "CRFB",
    },
}


@dataclass
class TariffPolicy(TaxPolicy):
    """
    Tariff / trade policy.

    Models revenue from tariff changes along with consumer costs,
    import volume effects, and trade retaliation.
    """
    policy_type: PolicyType = PolicyType.EXCISE_TAX
    tariff_rate_change: float = 0.0
    target_country: str | None = None
    target_sector: str | None = None
    import_base_billions: float = 0.0
    pass_through_rate: float = TRADE_BASELINE["consumer_pass_through_rate"]
    import_elasticity: float = TRADE_BASELINE["import_price_elasticity"]
    retaliation_rate: float = TRADE_BASELINE["retaliation_rate"]
    include_consumer_cost: bool = True
    include_retaliation: bool = True

    def __post_init__(self):
        self.policy_type = PolicyType.EXCISE_TAX
        super().__post_init__()
        if self.import_base_billions <= 0 and self.tariff_rate_change != 0:
            self.import_base_billions = TRADE_BASELINE["total_imports_billions"]

    def estimate_static_revenue_effect(
        self, baseline_revenue: float, use_real_data: bool = True
    ) -> float:
        if self.tariff_rate_change == 0:
            return 0.0
        base = self.import_base_billions
        rate = self.tariff_rate_change
        # Import volume declines with tariff rate (non-linear at high rates)
        # At low rates (<15%): mostly linear elasticity
        # At high rates (>30%): substitution accelerates, some imports cease entirely
        if rate > 0.30:
            volume_effect = 1 + self.import_elasticity * 0.30 + (rate - 0.30) * self.import_elasticity * 2.0
        else:
            volume_effect = 1 + self.import_elasticity * rate
        return rate * base * max(0.2, volume_effect)

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        return abs(static_effect) * TRADE_BASELINE["tariff_avoidance_rate"]

    def estimate_consumer_cost(self) -> float:
        """Annual cost to consumers from higher import prices."""
        if self.tariff_rate_change <= 0:
            return 0.0
        return self.pass_through_rate * self.tariff_rate_change * self.import_base_billions

    def estimate_retaliation_cost(self) -> float:
        """Annual export loss from trading partner retaliation."""
        if self.tariff_rate_change <= 0:
            return 0.0
        export_base = TRADE_BASELINE["total_exports_billions"]
        return self.retaliation_rate * self.tariff_rate_change * export_base

    def get_household_impact(self) -> float:
        """Annual cost per household."""
        return self.estimate_consumer_cost() * 1e9 / TRADE_BASELINE["us_households"]

    def get_trade_summary(self) -> dict:
        static = self.estimate_static_revenue_effect(0)
        behavioral = self.estimate_behavioral_offset(static)
        consumer = self.estimate_consumer_cost()
        retaliation = self.estimate_retaliation_cost()
        return {
            "tariff_revenue": static,
            "behavioral_offset": behavioral,
            "net_revenue": static - behavioral,
            "consumer_cost": consumer,
            "retaliation_cost": retaliation,
            "household_cost": self.get_household_impact(),
        }


def create_trump_universal_10() -> TariffPolicy:
    effective_base = (
        TRADE_BASELINE["total_imports_billions"]
        * TRADE_BASELINE["universal_coverage_rate"]
    )
    return TariffPolicy(
        name="Trump Universal 10% Tariff",
        description="10% tariff on all imports. Raises ~\\$2T but costs ~\\$1,700/household.",
        tariff_rate_change=0.10,
        import_base_billions=effective_base,
    )


def create_trump_china_60() -> TariffPolicy:
    # Existing tariffs already cover ~$300B at 25%; incremental is ~40pp on $430B
    # But Tax Foundation scores incremental revenue only at ~$50B/yr
    # Many imports have already shifted or will be substituted at 60%
    return TariffPolicy(
        name="Trump 60% China Tariff",
        description="60% tariff on all Chinese imports (~\\$430B base). Raises ~\\$500B/10yr.",
        tariff_rate_change=0.40,  # Incremental above existing ~20% average
        target_country="china",
        import_base_billions=TRADE_BASELINE["china_imports_billions"] * 0.5,  # Reduced base after substitution
    )


def create_auto_tariff_25() -> TariffPolicy:
    # Incremental above existing ~2.5% auto tariff; effective base smaller
    # due to exemptions (USMCA, parts vs finished vehicles)
    return TariffPolicy(
        name="25% Auto Tariff",
        description="25% tariff on imported vehicles and parts (~\\$380B base).",
        tariff_rate_change=0.225,  # Incremental above existing ~2.5%
        target_sector="autos",
        import_base_billions=TRADE_BASELINE["auto_imports_billions"] * 0.35,  # Effective base after USMCA
    )


def create_steel_tariff_25() -> TariffPolicy:
    return TariffPolicy(
        name="25% Steel/Aluminum Tariff",
        description="25% tariff on steel and aluminum imports (~\\$50B base).",
        tariff_rate_change=0.25,
        target_sector="steel",
        import_base_billions=TRADE_BASELINE["steel_aluminum_imports_billions"],
    )


def create_reciprocal_tariffs() -> TariffPolicy:
    return TariffPolicy(
        name="Reciprocal Tariffs",
        description="Match trading partners' tariff rates (~20pp average increase). Raises ~\\$1.2T.",
        tariff_rate_change=0.20,
        import_base_billions=TRADE_BASELINE["total_imports_billions"] * 0.5,
    )


TRADE_VALIDATION_SCENARIOS = {
    "trump_universal_10": {
        "factory": "create_trump_universal_10",
        "expected_10yr": -2000.0,
        "source": "Tax Foundation",
    },
    "trump_china_60": {
        "factory": "create_trump_china_60",
        "expected_10yr": -500.0,
        "source": "Tax Foundation",
    },
}
