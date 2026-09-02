"""
Budget-authority -> outlay spend-out.

Why this module exists
----------------------
Until it did, ``SpendingPolicy`` turned a budget-authority level straight into
an outlay in the year the authority was provided. That is wrong for every
account that does not disburse immediately, and it was the single largest
mechanism error in the out-of-sample battery: seven Tier-1 rows, 509 of the
tier's 1,315 units of error mass, all one cause
(``planning/MODELING_IMPROVEMENT.md`` §2.1).

The mechanism
-------------
Outlays are the convolution of budget authority with a spend-out profile::

    outlays_t = sum_k  s_k * BA_{t-k}

``s_k`` is the share of a dollar of budget authority that becomes an outlay
``k`` years after the authority is provided. The profile is keyed by **account
class**, because that is what governs disbursement speed: pay and benefits go
out in the year they are provided; construction and capital take most of a
decade. CBO states the same thing in its discretionary-spending tools ("outlays
for an agency's salaries and administrative expenses generally occur quickly,
while budget authority for construction of infrastructure or weapon systems may
be disbursed over several years").

A ten-year *window* truncates the tail: authority provided in year 9 outlays
mostly outside the window. That truncation is not an approximation, it is the
reason CBO's own 10-year outlay/budget-authority ratios sit below one (option
37 0.824, 38 0.798, 39 0.913, 42 0.835, 43 0.693), and reproducing it is most of
what this module buys.

Where the rates come from
-------------------------
``fiscal_model/data_files/spending/outlay_rates.csv``, fitted by
``scripts/fit_outlay_rates.py`` on the 14 CBO options that publish both a
budget-authority row and an outlays row and are **not** in the scored battery.
The file's header carries the full provenance, including why OMB Circular A-11
§32 - the source ``planning/MODELING_IMPROVEMENT.md`` §6 decision 2 named - is
not it: that section is "Personnel Compensation, Benefits, and Related Costs"
and A-11 publishes no numeric outlay-rate table in any section.

**Anti-leakage.** No scored option, and no alternative of a scored option,
contributes a number to any profile. ``tests/test_spending_outlays.py`` asserts
the donor pool is disjoint from the battery.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

#: Account class for spending that outlays in the year the authority is
#: provided. Not a fitted profile - it is the identity, and the default, so a
#: ``SpendingPolicy`` that does not opt in behaves exactly as it did before
#: this module existed.
IMMEDIATE = "immediate"

DATA_FILE = Path(__file__).parent / "data_files" / "spending" / "outlay_rates.csv"


@dataclass(frozen=True)
class OutlayProfile:
    """A spend-out profile: the share of budget authority outlaid each year."""

    account_class: str
    shares: tuple[float, ...]
    donor_options: tuple[int, ...] = ()
    rationale: str = ""

    def __post_init__(self) -> None:
        if any(share < 0 for share in self.shares):
            raise ValueError(f"{self.account_class}: outlay shares must be >= 0")
        total = sum(self.shares)
        if total > 1.0 + 1e-6:
            raise ValueError(
                f"{self.account_class}: outlay shares sum to {total:.4f}, above 1.0"
            )

    @property
    def first_year_rate(self) -> float:
        """Share outlaid in the year the authority is provided."""
        return self.shares[0] if self.shares else 0.0

    def outlays(self, authority: list[float] | tuple[float, ...]) -> list[float]:
        """Convolve a budget-authority path into an outlay path of equal length.

        Outlays that fall past the end of the path are dropped, which is the
        within-window truncation CBO's own 10-year totals embed.
        """
        n_years = len(authority)
        result = [0.0] * n_years
        for year in range(n_years):
            amount = authority[year]
            if amount == 0.0:
                continue
            for lag, share in enumerate(self.shares):
                target = year + lag
                if target >= n_years:
                    break
                result[target] += share * amount
        return result


#: The identity profile: every dollar outlays the year it is provided.
IMMEDIATE_PROFILE = OutlayProfile(
    account_class=IMMEDIATE,
    shares=(1.0,),
    rationale=(
        "Identity, not an estimate. Preserves the pre-spend-out behaviour for "
        "any policy that does not declare an account class."
    ),
)


@lru_cache(maxsize=1)
def load_outlay_profiles() -> Mapping[str, OutlayProfile]:
    """Load the fitted spend-out profiles, plus the ``immediate`` identity.

    Cached and returned read-only: one caller mutating a shared spend-out rate
    would silently move every spending score in the process.
    """
    profiles: dict[str, OutlayProfile] = {IMMEDIATE: IMMEDIATE_PROFILE}

    with DATA_FILE.open(encoding="utf-8") as handle:
        reader = csv.DictReader(line for line in handle if not line.startswith("#"))
        for row in reader:
            shares = []
            index = 0
            while f"year_{index}" in row:
                shares.append(float(row[f"year_{index}"]))
                index += 1
            while shares and shares[-1] == 0.0:
                shares.pop()
            donors = tuple(
                int(part) for part in (row.get("donor_options") or "").split() if part
            )
            account_class = row["account_class"]
            profiles[account_class] = OutlayProfile(
                account_class=account_class,
                shares=tuple(shares),
                donor_options=donors,
                rationale=row.get("donor_rationale", ""),
            )
    return MappingProxyType(profiles)


def get_outlay_profile(account_class: str | None) -> OutlayProfile:
    """Profile for an account class; ``None`` and ``"immediate"`` are the identity."""
    if not account_class or account_class == IMMEDIATE:
        return IMMEDIATE_PROFILE
    profiles = load_outlay_profiles()
    try:
        return profiles[account_class]
    except KeyError:
        raise ValueError(
            f"Unknown outlay account class {account_class!r}. "
            f"Known classes: {sorted(profiles)}"
        ) from None


#: Plain-English name for each account class, for anything a reader sees. The
#: model layer owns these because two surfaces quote them - the Tailor form's
#: profile picker and the note printed beside a spending score - and a second
#: copy would be a second thing to keep true.
ACCOUNT_CLASS_LABELS: Mapping[str, str] = MappingProxyType(
    {
        IMMEDIATE: "immediate (no spend-out)",
        "mandatory_benefit": "benefit payments",
        "personnel_and_benefits": "pay and benefits",
        "operations_and_support": "operations and support",
        "grants_and_procurement": "grants and procurement",
        "construction_and_capital": "construction and capital",
    }
)


def account_class_label(account_class: str | None) -> str:
    """Plain-English name for an account class; the raw name if it has none."""
    if not account_class:
        return ACCOUNT_CLASS_LABELS[IMMEDIATE]
    return ACCOUNT_CLASS_LABELS.get(account_class, account_class)


def account_classes() -> tuple[str, ...]:
    """Every account class the model can spend out, ``immediate`` included."""
    return tuple(sorted(load_outlay_profiles()))
