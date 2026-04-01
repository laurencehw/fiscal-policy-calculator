"""
Combined federal + state tax calculator.

Extends MicroTaxCalculator to add state income tax on top of the federal
calculation.  State taxable income generally starts from federal AGI (for
conforming states), so changes to federal deductions/credits can indirectly
affect state taxes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from fiscal_model.microsim.engine import MicroTaxCalculator

from .database import StateTaxDatabase, StateTaxProfile


class FederalStateCalculator:
    """
    Computes combined federal + state income tax liability.

    Key design decisions:
    - State taxable income = AGI - state standard deduction - personal exemptions
      (most states start from federal AGI, ignoring federal itemized deductions
      except where explicitly modeled)
    - SALT cap is applied at the federal level before calling this calculator
    - Local taxes (NYC, Philadelphia, etc.) are *not* modeled; state estimates
      include a note flagging this for affected states

    Usage::

        calc = FederalStateCalculator("CA", year=2025)
        pop = SyntheticPopulation().generate(n=1000)
        result = calc.calculate(pop)
        # result has: federal_tax, state_tax, combined_tax, effective_combined_rate

        # Apply a federal reform (e.g., eliminate SALT cap)
        result_reform = calc.apply_federal_reform(pop, reforms={"salt_cap": None})
    """

    # States where we flag that local taxes are excluded
    _LOCAL_TAX_WARNING_STATES = {"NY", "PA", "OH"}

    def __init__(self, state: str, year: int = 2025):
        self.state = state.upper()
        self.year = year
        self.federal_calc = MicroTaxCalculator(year)
        db = StateTaxDatabase(year)
        self.state_profile: StateTaxProfile = db.get_state(self.state)

    @property
    def has_local_tax_caveat(self) -> bool:
        return self.state in self._LOCAL_TAX_WARNING_STATES

    @property
    def confidence_label(self) -> str:
        return "Model estimate — state approximation"

    def calculate(self, pop: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate combined federal + state tax for the population.

        Args:
            pop: DataFrame with columns from MicroTaxCalculator.calculate()
                 (agi, wages, married, children, weight, ...)

        Returns:
            DataFrame with added columns:
            - federal_tax: federal income tax (same as final_tax from MicroTaxCalculator)
            - state_tax: state income tax
            - combined_tax: federal_tax + state_tax
            - effective_combined_rate: combined_tax / agi
            - effective_state_rate: state_tax / agi
        """
        df = self.federal_calc.calculate(pop)
        df = self._add_state_tax(df)
        return df

    def apply_federal_reform(
        self,
        pop: pd.DataFrame,
        reforms: dict,
    ) -> pd.DataFrame:
        """
        Apply a federal reform and recompute combined federal+state tax.

        Args:
            pop: Population DataFrame
            reforms: Dict of federal reform parameters (same as MicroTaxCalculator.apply_reform)
                     e.g. {"salt_cap": None} to eliminate SALT cap

        Returns:
            Calculated DataFrame with reform applied and state taxes included.
        """
        df = self.federal_calc.apply_reform(pop, reforms)
        df = self._add_state_tax(df)
        return df

    def effective_rate_curve(
        self,
        incomes: list[float] | None = None,
        married: bool = False,
    ) -> pd.DataFrame:
        """
        Compute combined effective rate at a range of income levels.

        Returns a DataFrame with columns: agi, federal_rate, state_rate, combined_rate.
        Useful for plotting rate curves.
        """
        if incomes is None:
            incomes = [
                10_000, 20_000, 30_000, 50_000, 75_000, 100_000,
                150_000, 200_000, 300_000, 500_000, 750_000, 1_000_000,
            ]

        records = []
        for agi in incomes:
            row = pd.DataFrame([{
                "agi": agi,
                "wages": agi,
                "married": int(married),
                "children": 0,
                "weight": 1,
            }])
            result = self.calculate(row).iloc[0]
            federal_rate = result["final_tax"] / agi if agi > 0 else 0.0
            state_rate = result["state_tax"] / agi if agi > 0 else 0.0
            records.append({
                "agi": agi,
                "federal_rate": federal_rate,
                "state_rate": state_rate,
                "combined_rate": federal_rate + state_rate,
            })

        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _add_state_tax(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized state income tax calculation."""
        profile = self.state_profile

        if not profile.has_income_tax:
            state_tax = np.zeros(len(df))
        elif profile.flat_rate is not None:
            # Flat-rate states: apply flat rate to (AGI - exemption/std_ded)
            married_mask = df["married"].values == 1
            exemption = np.where(
                married_mask,
                profile.personal_exemption_married,
                profile.personal_exemption_single,
            )
            std_ded = np.where(
                married_mask,
                profile.std_ded_married,
                profile.std_ded_single,
            )
            total_offset = np.maximum(exemption, std_ded)
            taxable = np.maximum(0.0, df["agi"].values - total_offset)
            state_tax = taxable * profile.flat_rate
        else:
            # Progressive brackets
            state_tax = self._progressive_state_tax(df, profile)

        federal_tax = df["final_tax"].values.copy()
        combined_tax = federal_tax + state_tax
        agi = df["agi"].values

        result = df.copy()
        result.loc[:, "state_tax"] = state_tax
        result.loc[:, "federal_tax"] = federal_tax
        result.loc[:, "combined_tax"] = combined_tax
        result.loc[:, "effective_state_rate"] = np.where(agi > 0, state_tax / agi, 0.0)
        result.loc[:, "effective_combined_rate"] = np.where(agi > 0, combined_tax / agi, 0.0)
        return result

    def _progressive_state_tax(
        self, df: pd.DataFrame, profile: StateTaxProfile
    ) -> np.ndarray:
        """Vectorized progressive state income tax."""
        married_mask = df["married"].values == 1
        agi = df["agi"].values

        # State taxable income = AGI - max(std_ded, personal_exemption)
        std_ded = np.where(
            married_mask, profile.std_ded_married, profile.std_ded_single
        )
        exemption = np.where(
            married_mask,
            profile.personal_exemption_married,
            profile.personal_exemption_single,
        )
        total_offset = np.maximum(std_ded, exemption)
        taxable = np.maximum(0.0, agi - total_offset)

        tax = np.zeros(len(df))

        # Loop over bracket segments for single and MFJ separately
        for i_married in (0, 1):
            mask = married_mask == bool(i_married)
            if not mask.any():
                continue

            brackets = profile.brackets_mfj if i_married else profile.brackets_single
            rates = profile.rates_mfj if i_married else profile.rates_single

            if not brackets or not rates:
                continue

            t = taxable[mask]
            tax_segment = np.zeros(len(t))

            for i in range(len(brackets)):
                lower = brackets[i]
                upper = brackets[i + 1] if i + 1 < len(brackets) else np.inf
                rate = rates[i]
                income_in_bracket = np.clip(t - lower, 0.0, upper - lower)
                tax_segment += income_in_bracket * rate

            tax[mask] = tax_segment

        return tax
