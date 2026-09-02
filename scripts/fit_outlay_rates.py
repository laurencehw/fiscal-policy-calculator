#!/usr/bin/env python3
"""
Rebuild the budget-authority -> outlay spend-out profiles.

Output
------
``fiscal_model/data_files/spending/outlay_rates.csv`` — one row per account
class, carrying ``year_0`` .. ``year_7``: the share of a dollar of budget
authority that becomes an outlay in the year the authority is provided and in
each of the seven following years.

Source of the rates — and why it is not OMB Circular A-11
---------------------------------------------------------
`planning/MODELING_IMPROVEMENT.md` §6 decision 2 named **OMB Circular A-11 §32
outlay rates** as the primary source. That source does not exist as described,
which was verified rather than assumed:

* **A-11 §32 is "Personnel Compensation, Benefits, and Related Costs"** (2016
  edition, ``obamawhitehouse.archives.gov/sites/default/files/omb/assets/
  a11_current_year/s32.pdf``, and the current single-chapter table of
  contents). It contains no outlay rates.
* **A-11 publishes no numeric outlay-rate table in any section.** §80
  ("Development of Baseline Estimates") requires only that new budgetary
  resources outlay "at a rate that is consistent with Presidential policy
  spendout rates"; §81 ("Policy and Baseline Estimates of Budget Authority,
  Outlays, and Receipts") requires *agencies* to enter their own account-level
  "outlay rates that apply to BA or limitations provided in the CY and beyond"
  into MAX. The rates are agency-supplied and unpublished.
* **CBO does publish account-level spendout rates** — publications 61913 (*An
  Interactive Tool for Projecting Discretionary Spending, 2026 to 2036*) and
  62256 (*How Changes in Discretionary Funding for the Budget Year Affect
  Outlays, 2027 to 2036*) — but cbo.gov returns HTTP 403 to the environment
  this was built in, for both the landing pages and ``system/files``. Those
  tools are the obvious external cross-check for whoever can reach them.

Decision 2's own fallback clause therefore governs, and this is what shipped:

    Congressional Budget Office, *Options for Reducing the Deficit: 2025 to
    2034* (December 2024; reposted October 2025), publication 60557.
    https://www.cbo.gov/publication/60557
    Transcribed to ``fiscal_model/data_files/validation/
    cbo_options_2025_2034_alternatives.csv`` by ``scripts/extract_cbo_options.py``.

Nineteen of the 76 options report **both** a budget-authority (or
spending-authority) row and an ``outlays`` row, which is a directly observed
spend-out. Five of the nineteen — options **37, 38, 39, 42 and 43** — are the
scored out-of-sample battery, and none of them, nor any alternative of them,
contributes a single number to any profile here. Option 44 is also excluded:
its outlays exceed its budget authority in every year (10-year ratio 1.52),
because repealing Davis-Bacon also cheapens work paid from prior-year balances,
so its implied profile violates ``s_k >= 0, sum s_k <= 1`` and is not a
spend-out observation. That leaves the donor pool below.

Method
------
For each class, stack every donor's convolution rows

    O_t = sum_k s_k * BA_{t-k}

and solve for ``s`` by non-negative least squares, then rescale if the fitted
shares sum above one. Donor paths are trimmed to start at each option's first
non-zero budget-authority year, since CBO reports no authority before it.

Usage
-----
    python scripts/fit_outlay_rates.py [--check]

``--check`` re-fits and compares against the committed CSV without writing.
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import nnls

REPO_ROOT = Path(__file__).resolve().parent.parent
DONOR_CSV = (
    REPO_ROOT
    / "fiscal_model"
    / "data_files"
    / "validation"
    / "cbo_options_2025_2034_alternatives.csv"
)
OUT_CSV = REPO_ROOT / "fiscal_model" / "data_files" / "spending" / "outlay_rates.csv"

YEAR_COLUMNS = [f"savings_{year}_billions" for year in range(2025, 2035)]

#: Horizon of the fitted profile. Eight years covers every donor's observable
#: tail inside CBO's 10-year table; anything beyond it is unidentified.
PROFILE_YEARS = 8

#: Options in the scored out-of-sample battery. Never donors — fitting a
#: profile on the case it will score is the failure mode
#: `planning/MODELING_IMPROVEMENT.md` §4 forbids.
SCORED_OPTIONS = frozenset({37, 38, 39, 42, 43})

#: Options with both authority and outlay rows that are nonetheless unusable.
EXCLUDED_DONORS = {
    44: (
        "Outlays exceed budget authority in every year (10-year ratio 1.52) "
        "because repealing Davis-Bacon also cheapens work paid from prior-year "
        "balances; the implied profile violates s_k >= 0, sum s_k <= 1."
    ),
}

#: Account class -> donor option numbers. Each class is a spend-out speed, and
#: each donor is assigned to it from the account type CBO's own option title
#: describes — never from how well it fits anything.
DONORS: dict[str, tuple[tuple[int, ...], str]] = {
    "personnel_and_benefits": (
        (29, 36, 40, 41),
        "Military basic pay; basic allowance for housing; VA medical care "
        "enrollment; federal civilian pay adjustment. Compensation and benefit "
        "accounts disburse in the year the authority is provided.",
    ),
    "operations_and_support": (
        (28, 34),
        "The Department of Defense's annual budget as a whole; retiring the "
        "B-1B bomber force. Operations, maintenance and force structure: a "
        "mix of pay that disburses at once and equipment that does not.",
    ),
    "grants_and_procurement": (
        (32, 33, 35),
        "Cancelling the Long-Range Standoff Weapon; cancelling the Future "
        "Long-Range Assault Aircraft; retiring the F-22 fighter force. "
        "Procurement and R&D obligate quickly and disburse over several years, "
        "the same shape as project and formula grants and assistance awards.",
    ),
    "construction_and_capital": (
        (31,),
        "Stopping Ford-class aircraft carrier construction. Shipbuilding is "
        "the slowest spend-out CBO reports, and is the closest observed analogue "
        "to infrastructure and other capital grants.",
    ),
    "mandatory_benefit": (
        (3, 9),
        "The mandatory Pell Grant add-on; the federal employee health voucher "
        "plan. Direct benefit payments are outlaid in the year they are owed, "
        "so there is no authority-to-outlay lag to model.",
    ),
}


def _load_donor_rows() -> dict[int, dict[str, list[dict[str, str]]]]:
    by_option: dict[int, dict[str, list[dict[str, str]]]] = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    with DONOR_CSV.open(encoding="utf-8") as handle:
        reader = csv.DictReader(line for line in handle if not line.startswith("#"))
        for row in reader:
            by_option[int(row["option_number"])][row["measure"]].append(row)
    return by_option


def _authority_and_outlays(
    measures: dict[str, list[dict[str, str]]],
) -> tuple[np.ndarray, np.ndarray]:
    """Budget-authority and outlay paths, trimmed to the first funded year."""
    key = "budget_authority" if "budget_authority" in measures else "spending_authority"
    authority = np.array([float(measures[key][0][col]) for col in YEAR_COLUMNS])
    outlays = np.array([float(measures["outlays"][0][col]) for col in YEAR_COLUMNS])
    first_funded = int(np.argmax(np.abs(authority) > 1e-9))
    return authority[first_funded:], outlays[first_funded:]


def fit_profiles() -> dict[str, np.ndarray]:
    """Fit one spend-out profile per account class from the donor options."""
    by_option = _load_donor_rows()

    leaked = {
        option for options, _ in DONORS.values() for option in options
    } & SCORED_OPTIONS
    if leaked:  # pragma: no cover - guarded by tests too
        raise AssertionError(f"Scored options used as donors: {sorted(leaked)}")

    profiles: dict[str, np.ndarray] = {}
    for account_class, (options, _reason) in DONORS.items():
        design: list[list[float]] = []
        observed: list[float] = []
        for option in options:
            authority, outlays = _authority_and_outlays(by_option[option])
            n_years = len(authority)
            for t in range(n_years):
                design.append(
                    [
                        authority[t - k] if 0 <= t - k < n_years else 0.0
                        for k in range(PROFILE_YEARS)
                    ]
                )
                observed.append(outlays[t])
        shares, _residual = nnls(np.array(design), np.array(observed))
        total = shares.sum()
        if total > 1.0:
            shares = shares / total
        profiles[account_class] = shares
    return profiles


def _rows(profiles: dict[str, np.ndarray]) -> list[list[str]]:
    rows = []
    for account_class, shares in profiles.items():
        options, reason = DONORS[account_class]
        rows.append(
            [account_class]
            + [f"{share:.4f}" for share in shares]
            + [" ".join(str(option) for option in options), reason]
        )
    return rows


def write_csv(profiles: dict[str, np.ndarray]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    header_lines = [
        "# Budget-authority -> outlay spend-out profiles, by account class.",
        "# Each year_N is the share of a dollar of budget authority that becomes an",
        "# outlay N years after the authority is provided.",
        "#",
        "# PRIMARY SOURCE (the fallback in planning/MODELING_IMPROVEMENT.md Sec. 6",
        "# decision 2, and what shipped): CBO, Options for Reducing the Deficit:",
        "# 2025 to 2034 (December 2024; reposted October 2025), publication 60557.",
        "#   https://www.cbo.gov/publication/60557",
        "# Fitted by non-negative least squares on the 14 options that report both a",
        "# budget-authority row and an outlays row and are NOT in the scored battery",
        "# (options 37, 38, 39, 42, 43 are scored and are never donors; option 44 is",
        "# excluded because its outlays exceed its authority in every year).",
        "#",
        "# NOT sourced from OMB Circular A-11 Sec. 32, which decision 2 named: that",
        "# section is 'Personnel Compensation, Benefits, and Related Costs' and",
        "# carries no outlay rates. A-11 publishes no numeric outlay-rate table",
        "# anywhere - Sec. 80 requires only consistency with 'Presidential policy",
        "# spendout rates' and Sec. 81 has agencies enter their own rates into MAX.",
        "# CBO's published account-level rates (publications 61913 and 62256) are the",
        "# external cross-check and were unreachable when this was built (cbo.gov 403).",
        "#",
        "# Rebuilt by scripts/fit_outlay_rates.py.",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        for line in header_lines:
            handle.write(line + "\n")
        writer = csv.writer(handle)
        writer.writerow(
            ["account_class"]
            + [f"year_{n}" for n in range(PROFILE_YEARS)]
            + ["donor_options", "donor_rationale"]
        )
        writer.writerows(_rows(profiles))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Re-fit and compare against the committed CSV without writing.",
    )
    args = parser.parse_args()

    profiles = fit_profiles()

    if args.check:
        from fiscal_model.spending_outlays import load_outlay_profiles

        committed = load_outlay_profiles()
        problems = []
        for account_class, shares in profiles.items():
            stored = committed[account_class].shares
            if not np.allclose(shares[: len(stored)], stored, atol=5e-5):
                problems.append(f"{account_class}: refit {shares} != committed {stored}")
        for problem in problems:
            print(problem)
        if problems:
            return 1
        print(f"OK - {len(profiles)} profiles match {OUT_CSV.name}")
        return 0

    write_csv(profiles)
    for account_class, shares in profiles.items():
        joined = " ".join(f"{share:.3f}" for share in shares)
        print(f"{account_class:<26} sum={shares.sum():.3f}  {joined}")
    print(f"\nWrote {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
