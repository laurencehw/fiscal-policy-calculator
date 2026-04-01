"""
State tax parameter database for the top 10 US states by population.

Data sourced from Tax Foundation State Tax Rates (2025) and Census ACS.
Covers: CA, TX, FL, NY, PA, IL, OH, GA, NC, MI (~55% of US population).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

_DATA_DIR = Path(__file__).parent.parent.parent / "data_files" / "state_taxes"

# Canonical display names for supported states
STATE_NAMES: dict[str, str] = {
    "CA": "California",
    "TX": "Texas",
    "FL": "Florida",
    "NY": "New York",
    "PA": "Pennsylvania",
    "IL": "Illinois",
    "OH": "Ohio",
    "GA": "Georgia",
    "NC": "North Carolina",
    "MI": "Michigan",
}

SUPPORTED_STATES: list[str] = list(STATE_NAMES.keys())


@dataclass
class StateTaxProfile:
    """Tax parameters for a single state, single year."""

    state: str
    year: int

    # Income tax presence / structure
    has_income_tax: bool
    flat_rate: float | None          # For flat-tax states (PA, IL, GA, NC, MI, OH top)
    top_rate: float                  # Highest marginal rate (0 for no-income-tax states)

    # Brackets and rates (empty for flat-rate and no-income-tax states)
    brackets_single: list[float] = field(default_factory=list)
    rates_single: list[float] = field(default_factory=list)
    brackets_mfj: list[float] = field(default_factory=list)
    rates_mfj: list[float] = field(default_factory=list)

    # Deductions / exemptions
    std_ded_single: float = 0.0
    std_ded_married: float = 0.0
    personal_exemption_single: float = 0.0
    personal_exemption_married: float = 0.0

    # Conformity flags
    allows_federal_deduction: bool = False  # Some states allow deducting federal taxes
    conforms_to_federal_agi: bool = True    # Most states start from federal AGI

    # SALT context (from state_salt_rates.csv)
    effective_salt_rate: float = 0.0
    avg_salt_deduction_itemizers: float = 0.0
    pct_itemizers: float = 0.0

    # Income distribution context (from ACS / Piketty-Saez)
    median_household_income: float = 0.0
    gini_coefficient: float = 0.0
    top_1pct_income_share: float = 0.0

    # Notes
    notes: str = ""

    def calculate_state_tax(self, agi: float, married: bool = False) -> float:
        """
        Compute state income tax for a single filer given AGI.

        Uses the state's brackets/rates with standard deduction or personal exemption.
        For flat-rate states, applies rate to (AGI - personal_exemption).
        For no-income-tax states, returns 0.
        """
        if not self.has_income_tax:
            return 0.0

        exemption = (
            self.personal_exemption_married if married else self.personal_exemption_single
        )
        std_ded = self.std_ded_married if married else self.std_ded_single

        # Taxable income: AGI minus the larger of standard deduction or personal exemption
        # (states vary; we use the available deduction/exemption)
        total_offset = max(std_ded, exemption)
        taxable = max(0.0, agi - total_offset)

        if self.flat_rate is not None:
            return taxable * self.flat_rate

        # Progressive brackets
        brackets = self.brackets_mfj if married else self.brackets_single
        rates = self.rates_mfj if married else self.rates_single

        if not brackets or not rates:
            return 0.0

        tax = 0.0
        for i in range(len(brackets)):
            lower = brackets[i]
            upper = brackets[i + 1] if i + 1 < len(brackets) else float("inf")
            rate = rates[i]
            if taxable <= lower:
                break
            income_in_bracket = min(taxable, upper) - lower
            tax += income_in_bracket * rate

        return tax

    def effective_state_rate(self, agi: float, married: bool = False) -> float:
        """Return effective state tax rate = state_tax / AGI."""
        if agi <= 0:
            return 0.0
        return self.calculate_state_tax(agi, married) / agi


class StateTaxDatabase:
    """
    Loads and queries state tax parameter data for the top 10 US states.

    Usage::

        db = StateTaxDatabase(year=2025)
        ca = db.get_state("CA")
        print(ca.top_rate)          # 0.133
        print(ca.calculate_state_tax(500_000))  # ~$50k
    """

    def __init__(self, year: int = 2025):
        self.year = year
        self._data: dict[str, StateTaxProfile] = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self, state: str) -> StateTaxProfile:
        """Return profile for the given 2-letter state code."""
        code = state.upper()
        if code not in self._data:
            supported = ", ".join(SUPPORTED_STATES)
            raise KeyError(
                f"State '{code}' not in database. Supported states: {supported}"
            )
        return self._data[code]

    def get_all_states(self) -> dict[str, StateTaxProfile]:
        """Return all loaded state profiles."""
        return dict(self._data)

    def get_no_income_tax_states(self) -> list[str]:
        """Return list of states with no income tax."""
        return [s for s, p in self._data.items() if not p.has_income_tax]

    def get_income_tax_states(self) -> list[str]:
        """Return list of states with an income tax."""
        return [s for s, p in self._data.items() if p.has_income_tax]

    def compare_top_rates(self) -> dict[str, float]:
        """Return top marginal rate for each state (sorted descending)."""
        rates = {s: p.top_rate for s, p in self._data.items()}
        return dict(sorted(rates.items(), key=lambda x: -x[1]))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, StateTaxProfile]:
        rates_path = _DATA_DIR / "state_tax_rates_2025.csv"
        salt_path = _DATA_DIR / "state_salt_rates.csv"

        rates_df = pd.read_csv(rates_path)
        salt_df = pd.read_csv(salt_path)

        # Merge on state
        salt_df_indexed = salt_df.set_index("state")

        result: dict[str, StateTaxProfile] = {}
        for _, row in rates_df.iterrows():
            state = str(row["state"]).strip()

            # Parse JSON bracket arrays
            brackets_s = _parse_json_list(row.get("brackets_single_json", "[]"))
            rates_s = _parse_json_list(row.get("rates_single_json", "[]"))
            brackets_mfj = _parse_json_list(row.get("brackets_mfj_json", "[]"))
            rates_mfj = _parse_json_list(row.get("rates_mfj_json", "[]"))

            flat_raw = row.get("flat_rate")
            flat_rate = (
                float(flat_raw)
                if (flat_raw is not None and str(flat_raw).strip() != "" and float(flat_raw) > 0)
                else None
            )

            # SALT data
            salt_row = salt_df_indexed.loc[state] if state in salt_df_indexed.index else None

            profile = StateTaxProfile(
                state=state,
                year=self.year,
                has_income_tax=bool(row["has_income_tax"]),
                flat_rate=flat_rate,
                top_rate=float(row["top_rate"]),
                brackets_single=brackets_s,
                rates_single=rates_s,
                brackets_mfj=brackets_mfj,
                rates_mfj=rates_mfj,
                std_ded_single=float(row.get("std_ded_single", 0) or 0),
                std_ded_married=float(row.get("std_ded_married", 0) or 0),
                personal_exemption_single=float(row.get("personal_exemption_single", 0) or 0),
                personal_exemption_married=float(row.get("personal_exemption_married", 0) or 0),
                allows_federal_deduction=bool(row.get("allows_federal_deduction", False)),
                conforms_to_federal_agi=bool(row.get("conforms_to_federal_agi", True)),
                effective_salt_rate=float(salt_row["effective_salt_rate"]) if salt_row is not None else 0.0,
                avg_salt_deduction_itemizers=float(salt_row["avg_salt_deduction_itemizers"]) if salt_row is not None else 0.0,
                pct_itemizers=float(salt_row["pct_itemizers"]) if salt_row is not None else 0.0,
                median_household_income=float(salt_row["median_household_income"]) if salt_row is not None else 0.0,
                gini_coefficient=float(salt_row["gini_coefficient"]) if salt_row is not None else 0.0,
                top_1pct_income_share=float(salt_row["top_1pct_income_share"]) if salt_row is not None else 0.0,
                notes=str(row.get("notes", "") or ""),
            )
            result[state] = profile

        return result


def _parse_json_list(value) -> list[float]:
    """Parse a JSON array string into a list of floats. Returns [] on failure."""
    try:
        if not value or str(value).strip() in ("", "[]"):
            return []
        parsed = json.loads(str(value))
        return [float(x) for x in parsed]
    except (json.JSONDecodeError, ValueError, TypeError):
        return []
