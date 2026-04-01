"""
TAXSIM validation client for state tax models.

TAXSIM (NBER) is the gold-standard web calculator for federal + state taxes.
This module provides:
1. TAXSIMClient — submits taxpayers to the NBER TAXSIM35 API
2. validate_state_model — compares internal FederalStateCalculator against TAXSIM

Note: TAXSIM API has rate limits; this is for validation/research use only,
not production scoring. Results are cached to avoid redundant calls.

API docs: https://taxsim.nber.org/taxsim35/
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

import numpy as np

TAXSIM_URL = "https://taxsim.nber.org/taxsim35/"

# TAXSIM state codes (numeric FIPS) for our 10 supported states
STATE_FIPS = {
    "CA": 6,
    "TX": 48,
    "FL": 12,
    "NY": 36,
    "PA": 42,
    "IL": 17,
    "OH": 39,
    "GA": 13,
    "NC": 37,
    "MI": 26,
}


@dataclass
class TAXSIMResult:
    """Parsed result from one TAXSIM query."""

    fiitax: float     # Federal income tax
    siitax: float     # State income tax
    fica: float       # FICA (payroll) taxes
    frate: float      # Federal marginal rate (%)
    srate: float      # State marginal rate (%)
    tfica: float      # FICA marginal rate (%)


@dataclass
class ValidationReport:
    """Summary of internal model vs TAXSIM comparison."""

    state: str
    n_sample: int
    federal_mean_abs_error: float     # Mean absolute error on federal tax ($)
    federal_r2: float                 # R² on federal tax
    state_mean_abs_error: float       # Mean absolute error on state tax ($)
    state_r2: float                   # R² on state tax
    combined_mean_abs_error: float    # Mean absolute error on combined tax ($)
    combined_r2: float                # R²

    def passes(
        self,
        r2_threshold: float = 0.95,
        mae_pct_threshold: float = 0.05,
        avg_income: float = 75_000,
    ) -> bool:
        """True if validation targets are met."""
        mae_pct = self.combined_mean_abs_error / avg_income
        return self.combined_r2 >= r2_threshold and mae_pct <= mae_pct_threshold

    def summary(self) -> str:
        return (
            f"{self.state}: federal MAE=${self.federal_mean_abs_error:,.0f} "
            f"(R²={self.federal_r2:.3f}), "
            f"state MAE=${self.state_mean_abs_error:,.0f} "
            f"(R²={self.state_r2:.3f})"
        )


class TAXSIMClient:
    """
    Client for NBER TAXSIM35 web API.

    Rate-limited to one request per second to be polite to the server.
    Results are cached in memory within a session.

    Example::

        client = TAXSIMClient()
        result = client.calculate(
            {"year": 2025, "state": 6, "mstat": 1, "pwages": 100_000},
            state="CA"
        )
        print(f"Federal tax: ${result.fiitax:,.0f}")
        print(f"California tax: ${result.siitax:,.0f}")
    """

    def __init__(self, cache: dict[str, TAXSIMResult] | None = None):
        self._cache: dict[str, TAXSIMResult] = cache if cache is not None else {}
        self._last_request_time: float = 0.0

    def calculate(self, taxpayer: dict[str, Any], state: str) -> TAXSIMResult | None:
        """
        Submit a single taxpayer to TAXSIM35 and return results.

        Args:
            taxpayer: dict with TAXSIM35 input variables:
                - year: tax year (required)
                - state: numeric state FIPS code (use STATE_FIPS dict)
                - mstat: marital status (1=single, 2=married)
                - depx: number of dependents
                - pwages: primary wage income
                - swages: secondary wage income
                - dividends: dividends
                - otherprop: other property income
                - ...see TAXSIM35 docs for full list
            state: 2-letter state code (for cache key)

        Returns:
            TAXSIMResult or None if the API call fails.
        """
        cache_key = _make_cache_key(taxpayer, state)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Rate limit: 1 req/sec
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        try:
            # Build form data
            params = {str(k): str(v) for k, v in taxpayer.items()}
            data = urllib.parse.urlencode(params).encode("ascii")

            req = urllib.request.Request(
                TAXSIM_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")

            self._last_request_time = time.time()
            result = _parse_taxsim_response(text)
            if result is not None:
                self._cache[cache_key] = result
            return result

        except Exception:
            return None

    def validate_state_model(
        self,
        state: str,
        n_sample: int = 50,
        seed: int = 42,
    ) -> ValidationReport | None:
        """
        Validate internal FederalStateCalculator against TAXSIM for a random sample.

        Generates synthetic taxpayers, calculates taxes both internally and via TAXSIM,
        and returns a ValidationReport.

        Args:
            state: 2-letter state code
            n_sample: Number of synthetic taxpayers to test (default 50)
            seed: Random seed for reproducibility

        Returns:
            ValidationReport or None if TAXSIM is unavailable.
        """
        from fiscal_model.microsim.data_generator import SyntheticPopulation

        from .calculator import FederalStateCalculator

        np.random.default_rng(seed)
        pop = SyntheticPopulation(seed=seed).generate(n=n_sample)

        calc = FederalStateCalculator(state, year=2025)
        internal = calc.calculate(pop)

        fips = STATE_FIPS.get(state)
        if fips is None:
            return None

        taxsim_federal = []
        taxsim_state = []

        for _, row in pop.iterrows():
            taxpayer = {
                "year": 2025,
                "state": fips,
                "mstat": 2 if row["married"] == 1 else 1,
                "depx": int(row["children"]),
                "pwages": int(max(0, row.get("wages", row["agi"]))),
                "swages": 0,
            }
            result = self.calculate(taxpayer, state)
            if result is None:
                return None  # API unavailable
            taxsim_federal.append(result.fiitax)
            taxsim_state.append(result.siitax)

        internal_federal = internal["federal_tax"].values
        internal_state = internal["state_tax"].values
        internal_combined = internal["combined_tax"].values

        taxsim_federal_arr = np.array(taxsim_federal)
        taxsim_state_arr = np.array(taxsim_state)
        taxsim_combined = taxsim_federal_arr + taxsim_state_arr

        return ValidationReport(
            state=state,
            n_sample=n_sample,
            federal_mean_abs_error=float(np.mean(np.abs(internal_federal - taxsim_federal_arr))),
            federal_r2=float(_r2(internal_federal, taxsim_federal_arr)),
            state_mean_abs_error=float(np.mean(np.abs(internal_state - taxsim_state_arr))),
            state_r2=float(_r2(internal_state, taxsim_state_arr)),
            combined_mean_abs_error=float(np.mean(np.abs(internal_combined - taxsim_combined))),
            combined_r2=float(_r2(internal_combined, taxsim_combined)),
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_cache_key(taxpayer: dict[str, Any], state: str) -> str:
    payload = json.dumps({"state": state, **taxpayer}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()


def _parse_taxsim_response(text: str) -> TAXSIMResult | None:
    """Parse TAXSIM35 CSV-style response. Returns None if unparseable."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        return None
    try:
        headers = [h.strip().lower() for h in lines[0].split(",")]
        values = [v.strip() for v in lines[1].split(",")]
        row = dict(zip(headers, values, strict=False))
        return TAXSIMResult(
            fiitax=float(row.get("fiitax", 0)),
            siitax=float(row.get("siitax", 0)),
            fica=float(row.get("fica", 0)),
            frate=float(row.get("frate", 0)),
            srate=float(row.get("srate", 0)),
            tfica=float(row.get("tfica", 0)),
        )
    except (ValueError, KeyError):
        return None


def _r2(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Coefficient of determination."""
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0
    return 1.0 - ss_res / ss_tot
