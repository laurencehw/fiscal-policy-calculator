"""
AutoScorer: routes ProvisionMapper output through the existing scoring pipeline.

Each policy dict from MappingResult is converted to a Policy object and scored
individually; results are summed for the bill-level 10-year estimate.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fiscal_model.time_utils import utc_now

if TYPE_CHECKING:
    from bill_tracker.provision_mapper import MappingResult

logger = logging.getLogger(__name__)


@dataclass
class BillScore:
    """Auto-generated score for a bill."""

    bill_id: str
    scored_at: datetime
    ten_year_cost_billions: float     # Positive = costs money, Negative = raises revenue
    annual_effects: list[float]       # Year-by-year (10 years)
    static_cost: float
    behavioral_offset: float
    confidence: str                   # "high" | "medium" | "low"
    policies_json: list[dict] = field(default_factory=list)
    notes: str = ""


class AutoScorer:
    """
    Routes provision mapper output through the fiscal policy scoring pipeline.

    Accepts a FiscalPolicyScorer instance (injected for testability).
    """

    def __init__(self, scorer=None):
        self._scorer = scorer

    @property
    def scorer(self):
        if self._scorer is None:
            from fiscal_model import FiscalPolicyScorer
            self._scorer = FiscalPolicyScorer(use_real_data=True)
        return self._scorer

    def score(self, mapping_result: MappingResult) -> BillScore | None:
        """
        Score a bill from its MappingResult.

        Returns None if no scoreable policies were found or confidence is too low.
        """
        if not mapping_result.policies:
            return None

        total_static = 0.0
        total_behavioral = 0.0
        total_ten_year = 0.0
        annual_effects = [0.0] * 10
        scored_policies = []
        notes_parts = []

        for policy_dict in mapping_result.policies:
            try:
                policy_obj = self._build_policy(policy_dict)
                if policy_obj is None:
                    notes_parts.append(
                        f"Could not build policy for type={policy_dict.get('policy_type')}"
                    )
                    continue

                result = self.scorer.score_policy(policy_obj, dynamic=False)

                # score_policy may return numpy arrays (year-by-year); extract scalars
                import numpy as np

                def _to_scalar(val) -> float:
                    if val is None:
                        return 0.0
                    if hasattr(val, "__len__"):
                        return float(np.sum(val))
                    return float(val)

                static = _to_scalar(getattr(result, "static_revenue_effect", None))
                behavioral = _to_scalar(getattr(result, "behavioral_offset", None))
                final_raw = getattr(result, "final_deficit_effect", None)

                total_static += static
                total_behavioral += behavioral

                if final_raw is not None and hasattr(final_raw, "__len__") and len(final_raw) >= 10:
                    for i in range(10):
                        annual_effects[i] += float(final_raw[i])
                    total_ten_year += float(np.sum(final_raw))
                else:
                    final = _to_scalar(final_raw)
                    total_ten_year += final
                    for i in range(10):
                        annual_effects[i] += final / 10.0

                scored_policies.append(policy_dict)

            except Exception as e:
                logger.debug("Failed to score policy %s: %s", policy_dict.get("policy_type"), e)
                notes_parts.append(f"Scoring error for {policy_dict.get('policy_type')}: {e}")

        if not scored_policies:
            return None

        return BillScore(
            bill_id=mapping_result.bill_id,
            scored_at=utc_now(),
            ten_year_cost_billions=-total_ten_year / 1e9 if abs(total_ten_year) > 1e6 else total_ten_year,
            annual_effects=annual_effects,
            static_cost=total_static,
            behavioral_offset=total_behavioral,
            confidence=mapping_result.confidence,
            policies_json=scored_policies,
            notes="; ".join(notes_parts),
        )

    # ------------------------------------------------------------------
    # Policy object construction
    # ------------------------------------------------------------------

    def _build_policy(self, policy_dict: dict) -> Any | None:
        """Convert a policy parameter dict to a Policy object."""
        policy_type = policy_dict.get("policy_type", "")
        params = policy_dict.get("parameters", {})
        name = policy_dict.get("provision_text", policy_type)[:80]

        try:
            return self._dispatch(policy_type, name, params)
        except Exception as e:
            logger.debug("Policy construction failed for %s: %s", policy_type, e)
            return None

    def _dispatch(self, policy_type: str, name: str, params: dict) -> Any | None:
        """Dispatch policy_type to the appropriate constructor using factory functions."""
        from fiscal_model.corporate import create_corporate_rate_change
        from fiscal_model.policies import PolicyType, SpendingPolicy, TaxPolicy
        from fiscal_model.tcja import create_tcja_extension

        if policy_type == "income_tax":
            rate = float(params.get("rate_change") or 0.0)
            threshold = float(params.get("affected_income_threshold") or 400_000)
            eti = float(params.get("taxable_income_elasticity") or 0.25)
            return TaxPolicy(
                name=name,
                description=f"Income tax rate change of {rate*100:.2f}pp above ${threshold:,.0f}",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=rate,
                affected_income_threshold=threshold,
                taxable_income_elasticity=eti,
            )

        if policy_type == "capital_gains":
            from fiscal_model import CapitalGainsPolicy
            rate = float(params.get("rate_change") or 0.0)
            threshold = float(params.get("affected_income_threshold") or 400_000)
            return CapitalGainsPolicy(
                name=name,
                description=f"Capital gains rate change of {rate*100:.2f}pp",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                rate_change=rate,
                affected_income_threshold=threshold,
                baseline_realizations_billions=800.0,
                baseline_capital_gains_rate=0.238,
            )

        if policy_type == "corporate":
            rate = float(params.get("rate_change") or 0.0)
            return create_corporate_rate_change(
                rate_change=rate,
                name=name,
                include_behavioral=True,
            )

        if policy_type == "credits":
            from fiscal_model.credits import TaxCreditPolicy
            amount = float(params.get("credit_amount_billions") or 0.0)
            if abs(amount) > 0:
                return TaxCreditPolicy(
                    name=name,
                    description=f"Tax credit: {params.get('credit_type', 'general')}",
                    policy_type=PolicyType.TAX_CREDIT,
                    annual_revenue_change_billions=-amount,  # credit = revenue cost
                    duration_years=int(params.get("expansion_years") or 10),
                )
            return None

        if policy_type == "spending":
            amount = float(params.get("spending_change_billions") or 0.0)
            duration = int(params.get("duration_years") or 10)
            return SpendingPolicy(
                name=name,
                description=f"Spending change of ${amount:.1f}B/year",
                policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
                annual_spending_change_billions=amount,
                duration_years=duration,
            )

        if policy_type == "tcja_extension":
            return create_tcja_extension(
                extend_all=bool(params.get("extend_all", True)),
                keep_salt_cap=bool(params.get("keep_salt_cap", True)),
            )

        if policy_type == "payroll":
            from fiscal_model.payroll import PayrollTaxPolicy
            rate = float(params.get("rate_change") or 0.0)
            cap_change = float(params.get("cap_change") or 0.0)
            return PayrollTaxPolicy(
                name=name,
                description=f"Payroll tax change: ss_rate_change={rate}, ss_cap_change={cap_change}",
                policy_type=PolicyType.PAYROLL_TAX,
                ss_rate_change=rate,
                ss_cap_change=cap_change,
            )

        if policy_type == "estate":
            from fiscal_model.estate import EstateTaxPolicy
            rate = float(params.get("rate_change") or 0.0)
            exemption = float(params.get("exemption_change") or 0.0)
            return EstateTaxPolicy(
                name=name,
                description=f"Estate tax change: rate_change={rate}, exemption_change={exemption}",
                policy_type=PolicyType.ESTATE_TAX,
                rate_change=rate,
                exemption_change=exemption,
            )

        if policy_type in ("transfer", "other"):
            # Model transfers as spending
            amount = float(params.get("transfer_change_billions", 0.0))
            if abs(amount) > 0:
                return SpendingPolicy(
                    name=name,
                    description=f"Transfer/other: ${amount:.1f}B",
                    policy_type=PolicyType.MANDATORY_SPENDING,
                    annual_spending_change_billions=amount,
                    duration_years=10,
                )

        return None
