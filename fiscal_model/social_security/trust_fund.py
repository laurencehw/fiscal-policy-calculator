"""
OASDI trust fund ledger on the 2026 Trustees Report baseline.

What this module computes, and what it does not
-----------------------------------------------
Every *rate* here is transcribed: the baseline income and cost rates come from
Trustees Report Table IV.B1, and each reform option's year-by-year change comes
from SSA OCACT's own single-provision table (``data_files/social_security/``,
provenance in each CSV header). The module computes only the *ledger* from
those rates: year-end reserves, the trust fund ratio, the depletion year, the
share of scheduled benefits payable at depletion, and the 75-year actuarial
balance. Options are added without interactions, which is how CRFB's Social
Security Reformer works too. Lane: ``planning/lanes/SS1_trust_fund_page.md``.

Ledger mechanics
----------------
Table VI.G1's compound interest factor ``F_t`` sits at mid-year *t*
(``F = 1`` on 1 January 2026). The year-end factor is the geometric mean of
neighbouring mid-year factors, ``E_t = sqrt(F_t * F_{t+1})``. Reserves carry
forward at ``E_t / E_{t-1}`` and the year's cash balance enters at mid-year and
earns ``E_t / F_t`` to year end::

    R_t = R_{t-1} * E_t / E_{t-1} + balance_t * P_t * E_t / F_t

with ``balance_t`` in percent of taxable payroll ``P_t``. The actuarial balance
is OCACT's summarized-rate formula: (reserves at the start + PV of balances
- PV of an ending reserve equal to the 2101 cost) / PV of payroll, discounting
mid-year flows by ``F_t`` and the year-end-2100 target by ``E_2100``.

Against the Trustees' own figures (pinned in ``tests/test_social_security.py``):
depletion 2034 (published Q3 2034), actuarial balance -4.44 (published -4.42),
83.5% payable (published 83%). Year-end reserves track Table VI.G2 to 0.1% in
2026 but drift to 7.7% low by 2033, as the remaining balance shrinks toward
zero; the depletion year is unaffected. Each option's recomputed change in
actuarial balance matches OCACT's summary row to 0.01 points.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data_files" / "social_security"
BASELINE_PATH = DATA_DIR / "trustees_2026_oasdi.csv"
CATALOG_PATH = DATA_DIR / "ocact_provisions_2026_catalog.csv"
ANNUAL_PATH = DATA_DIR / "ocact_provisions_2026_annual.csv"

#: Projection window of the 75-year valuation in the 2026 Report.
FIRST_YEAR = 2026
LAST_YEAR = 2100

#: Published 2026 Trustees Report facts (intermediate assumptions). The
#: ledger is checked against these, never calibrated to them.
TRUSTEES_ACTUARIAL_BALANCE = -4.42
TRUSTEES_OASDI_DEPLETION_YEAR = 2034
TRUSTEES_OASDI_PAYABLE_PCT = 83
TRUSTEES_OASI_DEPLETION = "late 2032"
TRUSTEES_OASI_PAYABLE_PCT = 78

#: Reserves at the end of 2025, $billions: Table VI.G2's end-2026 reserves
#: (2,357.7) less 2026 total income (1,493.2) plus 2026 cost (1,696.8).
RESERVES_END_2025 = 2357.7 - (1493.2 - 1696.8)

#: Baseline 2101 cost rate, for the ending-reserve target of the actuarial
#: balance. IV.B1 stops at 2100; OCACT's provision tables print 2101, and
#: proposal minus change gives 20.01 in every one of them (tested).
BASELINE_COST_RATE_2101 = 20.01

OCACT_TABLE_URL = "https://www.ssa.gov/oact/solvency/provisions/tables/table_run{run}.html"

CATEGORY_LABELS: dict[str, str] = {
    "cola": "Cost-of-living adjustment",
    "benefit_formula": "Benefit formula and levels",
    "retirement_age": "Retirement age",
    "payroll_rate": "Payroll tax rate",
    "taxable_maximum": "Taxable maximum",
    "other_revenue": "Broaden the base and other revenue",
    "benefit_taxation": "Income taxation of benefits",
}


@dataclass(frozen=True)
class BaselineYear:
    year: int
    income_rate: float
    cost_rate: float
    taxable_payroll: float
    interest_factor: float


@dataclass(frozen=True)
class Provision:
    """One OCACT-scored option, with OCACT's own summary figures."""

    provision_id: str
    ocact_run: str
    category: str
    exclusive_group: str
    label: str
    description: str
    ocact_change_actuarial_balance: float
    ocact_depletion_year: int | None

    @property
    def source_url(self) -> str:
        return OCACT_TABLE_URL.format(run=self.ocact_run)


@dataclass(frozen=True)
class ProvisionPath:
    """An option's change from current law, by year, in percent of payroll."""

    change_cost_rate: dict[int, float]
    change_income_rate: dict[int, float]


@dataclass(frozen=True)
class Projection:
    """The ledger for one plan (an empty plan is current law)."""

    provision_ids: tuple[str, ...]
    years: tuple[int, ...]
    income_rate: tuple[float, ...]
    cost_rate: tuple[float, ...]
    reserves_end: tuple[float, ...]
    trust_fund_ratio: tuple[float, ...]
    depletion_year: int | None
    payable_at_depletion: float | None
    computed_actuarial_balance: float
    change_in_actuarial_balance: float

    @property
    def actuarial_balance(self) -> float:
        """The Trustees' published balance plus this plan's computed change.

        The change is linear in the rates, so adding it to the published
        figure keeps the headline on the Trustees' number while the ledger's
        own 0.02-point baseline residual cancels out of the difference.
        """
        return TRUSTEES_ACTUARIAL_BALANCE + self.change_in_actuarial_balance

    @property
    def share_of_shortfall_closed(self) -> float:
        """Fraction of the 75-year shortfall closed (1.0 = 75-year balance)."""
        return self.change_in_actuarial_balance / -TRUSTEES_ACTUARIAL_BALANCE

    @property
    def solvent_through_window(self) -> bool:
        return self.depletion_year is None

    @property
    def benefit_cut_at_depletion(self) -> float | None:
        if self.payable_at_depletion is None:
            return None
        return 1.0 - self.payable_at_depletion


class ExclusiveGroupError(ValueError):
    """Two alternative settings of the same lever were selected together."""


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(line for line in handle if not line.startswith("#")))


@lru_cache(maxsize=1)
def load_baseline() -> tuple[BaselineYear, ...]:
    return tuple(
        BaselineYear(
            year=int(row["year"]),
            income_rate=float(row["income_rate"]),
            cost_rate=float(row["cost_rate"]),
            taxable_payroll=float(row["taxable_payroll_billions"]),
            interest_factor=float(row["interest_factor"]),
        )
        for row in _rows(BASELINE_PATH)
    )


@lru_cache(maxsize=1)
def load_catalog() -> tuple[Provision, ...]:
    return tuple(
        Provision(
            provision_id=row["provision_id"],
            ocact_run=row["ocact_run"],
            category=row["category"],
            exclusive_group=row["exclusive_group"],
            label=row["label"],
            description=row["description"],
            ocact_change_actuarial_balance=float(row["ocact_change_actuarial_balance"]),
            ocact_depletion_year=(
                int(row["ocact_depletion_year"]) if row["ocact_depletion_year"] else None
            ),
        )
        for row in _rows(CATALOG_PATH)
    )


def provisions_by_id() -> dict[str, Provision]:
    return {p.provision_id: p for p in load_catalog()}


@lru_cache(maxsize=1)
def load_provision_paths() -> dict[str, ProvisionPath]:
    cost: dict[str, dict[int, float]] = {}
    income: dict[str, dict[int, float]] = {}
    for row in _rows(ANNUAL_PATH):
        pid, year = row["provision_id"], int(row["year"])
        cost.setdefault(pid, {})[year] = float(row["change_cost_rate"])
        income.setdefault(pid, {})[year] = float(row["change_income_rate"])
    return {pid: ProvisionPath(cost[pid], income[pid]) for pid in cost}


def validate_selection(provision_ids: Iterable[str]) -> tuple[str, ...]:
    """Return the ids in catalog order, rejecting unknown ids and group clashes."""
    catalog = provisions_by_id()
    chosen = set(provision_ids)
    unknown = sorted(chosen - set(catalog))
    if unknown:
        raise KeyError(f"Unknown OCACT provision id(s): {', '.join(unknown)}")
    seen: dict[str, str] = {}
    for pid in sorted(chosen):
        group = catalog[pid].exclusive_group
        if not group:
            continue
        if group in seen:
            raise ExclusiveGroupError(
                f"{seen[group]} and {pid} are alternative settings of the same lever "
                f"({group}); choose one."
            )
        seen[group] = pid
    return tuple(p.provision_id for p in load_catalog() if p.provision_id in chosen)


def _year_end_factors(factors: Sequence[float]) -> list[float]:
    """``E_t`` for t = FIRST_YEAR-1 .. LAST_YEAR from mid-year factors F_{t}.

    ``factors`` runs FIRST_YEAR-1 .. LAST_YEAR; F_{LAST_YEAR+1} is extended
    at the last year's growth.
    """
    extended = [*factors, factors[-1] ** 2 / factors[-2]]
    return [math.sqrt(extended[k] * extended[k + 1]) for k in range(len(factors))]


def project(provision_ids: Iterable[str] = ()) -> Projection:
    """Run the ledger for current law plus the given OCACT provisions."""
    ids = validate_selection(provision_ids)
    paths = load_provision_paths()
    rows = [r for r in load_baseline() if FIRST_YEAR - 1 <= r.year <= LAST_YEAR]
    year_end = _year_end_factors([r.interest_factor for r in rows])
    window = rows[1:]

    years: list[int] = []
    income: list[float] = []
    cost: list[float] = []
    reserves: list[float] = []
    ratios: list[float] = []
    reserve = RESERVES_END_2025
    pv_balance = 0.0
    pv_payroll = 0.0
    for k, row in enumerate(window, start=1):
        y = row.year
        inc = row.income_rate + sum(paths[p].change_income_rate[y] for p in ids)
        cst = row.cost_rate + sum(paths[p].change_cost_rate[y] for p in ids)
        payroll = row.taxable_payroll
        f_mid = row.interest_factor
        ratios.append(max(reserve, 0.0) / (cst / 100 * payroll) * 100)
        reserve = reserve * year_end[k] / year_end[k - 1] + (
            (inc - cst) / 100 * payroll * year_end[k] / f_mid
        )
        pv_balance += (inc - cst) / 100 * payroll / f_mid
        pv_payroll += payroll / f_mid
        years.append(y)
        income.append(inc)
        cost.append(cst)
        reserves.append(reserve)

    depletion = next((y for y, r in zip(years, reserves, strict=True) if r < 0), None)
    payable = None
    if depletion is not None:
        k = years.index(depletion)
        payable = income[k] / cost[k]

    payroll_2101 = window[-1].taxable_payroll ** 2 / window[-2].taxable_payroll
    cost_2101 = BASELINE_COST_RATE_2101 + sum(paths[p].change_cost_rate[LAST_YEAR + 1] for p in ids)
    ending_target = cost_2101 / 100 * payroll_2101 / year_end[-1]
    balance = (RESERVES_END_2025 + pv_balance - ending_target) / pv_payroll * 100

    baseline_balance = balance if not ids else _baseline_actuarial_balance()
    return Projection(
        provision_ids=ids,
        years=tuple(years),
        income_rate=tuple(income),
        cost_rate=tuple(cost),
        reserves_end=tuple(reserves),
        trust_fund_ratio=tuple(ratios),
        depletion_year=depletion,
        payable_at_depletion=payable,
        computed_actuarial_balance=balance,
        change_in_actuarial_balance=balance - baseline_balance,
    )


@lru_cache(maxsize=1)
def _baseline_actuarial_balance() -> float:
    return project(()).computed_actuarial_balance
