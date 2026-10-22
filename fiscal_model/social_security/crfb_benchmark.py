"""
Our trust fund ledger next to the figures CRFB publishes for its Reformer.

Rows live in ``data_files/social_security/crfb_benchmarks.csv`` with their
source URL and date. For each row this module runs the ledger on the mapped
OCACT provisions and reports both numbers and the gap. The gap is a finding,
not an error to be tuned away: CRFB's option figures rest on an earlier
Trustees vintage and CRFB's own estimates, and the CSV's ``note`` column says
what was expected to differ before the comparison was run
(``planning/lanes/SS1_trust_fund_page.md`` section 5).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache

from fiscal_model.social_security.trust_fund import (
    DATA_DIR,
    TRUSTEES_OASI_PAYABLE_PCT,
    project,
)

BENCHMARKS_PATH = DATA_DIR / "crfb_benchmarks.csv"

#: The Trustees' OASI-only depletion year. The ledger models combined OASDI,
#: so OASI rows compare against this transcribed figure.
TRUSTEES_OASI_DEPLETION_YEAR = 2032

METRIC_LABELS = {
    "depletion_year": "Depletion year",
    "cut_at_depletion_pct": "Benefit cut at depletion",
    "shortfall_closed_pct": "Share of 75-year shortfall closed",
}


@dataclass(frozen=True)
class BenchmarkRow:
    benchmark_id: str
    crfb_item: str
    metric: str
    framing: str
    crfb_value: float | None
    crfb_text: str
    our_provisions: tuple[str, ...]
    crfb_baseline: str
    source_url: str
    source_date: str
    note: str
    our_value: float | None
    our_basis: str

    @property
    def gap(self) -> float | None:
        if self.crfb_value is None or self.our_value is None:
            return None
        return self.our_value - self.crfb_value

    def display(self, value: float | None, *, ours: bool) -> str:
        if value is None:
            if ours:
                return "not depleted by 2100"
            return self.crfb_text or "—"
        if self.metric == "depletion_year":
            return f"{value:.0f}"
        return f"{value:.0f}%"


def _our_value(metric: str, framing: str, provisions: tuple[str, ...]) -> tuple[float | None, str]:
    if framing == "oasi":
        if metric == "depletion_year":
            return float(TRUSTEES_OASI_DEPLETION_YEAR), "Trustees (OASI), transcribed"
        if metric == "cut_at_depletion_pct":
            return float(100 - TRUSTEES_OASI_PAYABLE_PCT), "Trustees (OASI), transcribed"
        raise ValueError(f"No OASI figure for metric {metric!r}")
    result = project(provisions)
    basis = f"Ledger on OCACT {', '.join(provisions)}" if provisions else "Ledger, current law"
    if metric == "depletion_year":
        return (float(result.depletion_year) if result.depletion_year else None), basis
    if metric == "cut_at_depletion_pct":
        cut = result.benefit_cut_at_depletion
        return (None if cut is None else cut * 100), basis
    if metric == "shortfall_closed_pct":
        return result.share_of_shortfall_closed * 100, basis
    raise ValueError(f"Unknown benchmark metric {metric!r}")


@lru_cache(maxsize=1)
def crfb_comparison() -> tuple[BenchmarkRow, ...]:
    out: list[BenchmarkRow] = []
    with BENCHMARKS_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(line for line in handle if not line.startswith("#"))
        for row in reader:
            provisions = tuple(p for p in row["our_provisions"].split(";") if p)
            ours, basis = _our_value(row["metric"], row["framing"], provisions)
            out.append(
                BenchmarkRow(
                    benchmark_id=row["benchmark_id"],
                    crfb_item=row["crfb_item"],
                    metric=row["metric"],
                    framing=row["framing"],
                    crfb_value=float(row["crfb_value"]) if row["crfb_value"] else None,
                    crfb_text=row["crfb_text"],
                    our_provisions=provisions,
                    crfb_baseline=row["crfb_baseline"],
                    source_url=row["source_url"],
                    source_date=row["source_date"],
                    note=row["note"],
                    our_value=ours,
                    our_basis=basis,
                )
            )
    return tuple(out)
