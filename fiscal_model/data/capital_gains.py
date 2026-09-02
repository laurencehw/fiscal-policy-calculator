"""Capital gains baseline: realizations by statutory bracket, the accrued-gains
stock, and the flow of gains transferred at death.

Three quantities live here, each read from a vendored file with a provenance
header in ``fiscal_model/data_files/capital_gains/`` and regenerable by
``python scripts/build_capital_gains_data.py``:

**Realizations by statutory bracket.**  IRS SOI Table 3.5 publishes, for every
AGI class, the income actually taxed at each preferential capital-gains rate -
0, 15, 20, 25 and 28 percent - and the tax it generated.  That, plus the
section 1411 NIIT surtax where the AGI class lies above its threshold, is the
base a capital-gains rate change applies to.  It replaces the aggregate
realizations series times a hand-written share ladder that this module used
before, which at threshold 0 returned every realized dollar at one blended
15.5 percent rate, including gains facing the 0 percent bracket.

**The accrued-gains stock.**  Household net worth (Federal Reserve
Distributional Financial Accounts, the Z.1 companion) times the unrealized-gain
share of wealth that Avery, Grodzicki & Moore (FEDS 2013-28) Figure 1 reports
by estate size.  Realizations are a flow off this stock, so the ratio of the
two is an observed hazard rather than an assumption, and the share of accrued
gains that leaves the stock at death rather than by sale is what makes step-up
at death worth avoiding tax for.

**Gains transferred at death.**  Poterba & Weisbenner (2001) Table 8 report,
from the 1998 Survey of Consumer Finances, expected estates of $118.9 billion a
year and expected unrealized capital gains at death of $42.8 billion - 36
percent of estate value - on the convention that transfers to a surviving
spouse are not realization events.  Both are carried as shares of household net
worth in the same year and grown with it, so the flow is indexed to the asset
stock rather than frozen at one constant.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Optional

import pandas as pd

#: Statutory long-term capital gains rate brackets, keyed by the lower bound of
#: taxable income for a single filer in 2025 (Rev. Proc. 2024-40).  Used only to
#: price a gain whose size is known but whose bracket is not - the gain a
#: decedent would report on a final return, say.
LTCG_RATE_BRACKETS: tuple[tuple[float, float], ...] = (
    (0.0, 0.00),
    (48_350.0, 0.15),
    (533_400.0, 0.20),
)

#: Net investment income tax, 26 U.S.C. 1411: 3.8 percent on net investment
#: income once modified AGI exceeds $200,000 for a single filer.
NIIT_RATE = 0.038
NIIT_THRESHOLD = 200_000.0


@dataclass(frozen=True)
class GainsBracket:
    """Realizations facing one statutory preferential rate.

    ``long_term_share`` is the share of this bracket's base made up of realized
    long-term gains rather than qualified dividends and capital gain
    distributions.  It is the share with a *timing* margin: a taxpayer chooses
    when to sell an appreciated asset and cannot choose when a fund distributes.
    """

    statutory_rate: float
    niit_rate: float
    realizations_billions: float
    tax_billions: float
    long_term_share: float

    @property
    def effective_rate(self) -> float:
        """Combined statutory plus NIIT rate actually facing these gains."""
        return self.statutory_rate + self.niit_rate


@dataclass(frozen=True)
class DecedentClass:
    """One estate-size class in the gains-at-death schedule."""

    group: str
    decedents_per_year: float
    gains_per_decedent_dollars: float
    gains_billions: float

    def taxable_gains_billions(self, exemption: float) -> float:
        """Gains above a per-decedent exemption, in billions."""
        taxable_per_decedent = max(0.0, self.gains_per_decedent_dollars - exemption)
        return self.decedents_per_year * taxable_per_decedent / 1e9


class CapitalGainsBaseline:
    """Threshold-specific capital gains baselines from bundled published data."""

    BRACKET_FILE = "soi_capital_gains_by_rate_bracket.csv"
    HOLDING_FILE = "soi_gains_by_holding_period.csv"
    PARAMETER_FILE = "accrued_gains_parameters.csv"
    LADDER_FILE = "decedent_estate_ladder.csv"
    AGGREGATE_FILE = "taxfoundation_capital_gains_2022_2024.csv"

    #: A capital-gains rate change is a change to the 0/15/20 percent ladder.
    #: The 25 percent (unrecaptured section 1250 gain) and 28 percent
    #: (collectibles) rates are separate statutory provisions that options such
    #: as CBO's Option 47 explicitly leave alone, so they are excluded from the
    #: rate-change base while remaining in the file.
    RATE_CHANGE_BRACKETS = (0.00, 0.15, 0.20)

    def __init__(self, data_dir: Optional[Path] = None):
        default_dir = Path(__file__).resolve().parent.parent / "data_files" / "capital_gains"
        self.data_dir = Path(data_dir) if data_dir else default_dir

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _read(self, name: str) -> pd.DataFrame:
        path = self.data_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Capital gains data file not found: {path}")
        return pd.read_csv(path, comment="#")

    @cached_property
    def _brackets(self) -> pd.DataFrame:
        return self._read(self.BRACKET_FILE)

    @cached_property
    def _holding(self) -> pd.DataFrame:
        return self._read(self.HOLDING_FILE)

    @cached_property
    def _parameters(self) -> dict[str, float]:
        frame = self._read(self.PARAMETER_FILE)
        return {str(k): float(v) for k, v in zip(frame["key"], frame["value"])}

    @cached_property
    def _ladder(self) -> pd.DataFrame:
        return self._read(self.LADDER_FILE)

    @cached_property
    def _aggregate(self) -> pd.DataFrame:
        path = self.data_dir / self.AGGREGATE_FILE
        return pd.read_csv(path).sort_values("tax_year").reset_index(drop=True)

    def available_years(self) -> list[int]:
        """Tax years for which SOI bracket detail is vendored."""
        return sorted(int(y) for y in self._brackets["tax_year"].unique())

    def _resolve_year(self, year: int) -> int:
        years = self.available_years()
        if year in years:
            return year
        return min(years, key=lambda candidate: abs(candidate - year))

    # ------------------------------------------------------------------
    # Realizations by bracket
    # ------------------------------------------------------------------

    def pareto_tail_index(self, year: int) -> float:
        """Pareto index of the top AGI class, fitted to the two classes below it.

        SOI's top class is open-ended ("$10,000,000 or more"), so a threshold
        inside it cannot be prorated across a range.  The amount above ``x`` in
        a Pareto tail scales as ``x**(1-alpha)``, and the two topmost classes
        pin ``alpha`` down: the share of their combined realizations that sits
        in the open-ended class is ``(L_top/L_prev)**(1-alpha)``.  Returns 1.0 -
        an infinitely thin tail, so a threshold inside the top class takes all
        of it - if the fit is degenerate, which keeps the old behaviour as the
        fallback rather than as the rule.
        """
        frame = self._brackets[self._brackets["tax_year"] == self._resolve_year(year)]
        frame = frame[frame["statutory_rate"].isin(self.RATE_CHANGE_BRACKETS)]
        if frame.empty:
            return 1.0
        top = frame[frame["agi_upper"] == float("inf")]
        if top.empty:
            return 1.0
        top_lower = float(top["agi_lower"].max())
        previous = frame[frame["agi_upper"] == top_lower]
        if previous.empty or top_lower <= 0:
            return 1.0
        previous_lower = float(previous["agi_lower"].min())
        if previous_lower <= 0 or previous_lower >= top_lower:
            return 1.0
        top_amount = float(top["income_taxed_at_rate_thousands"].sum())
        previous_amount = float(previous["income_taxed_at_rate_thousands"].sum())
        combined = top_amount + previous_amount
        if combined <= 0 or top_amount <= 0 or top_amount >= combined:
            return 1.0
        share = top_amount / combined
        return 1.0 - math.log(share) / math.log(top_lower / previous_lower)

    def _share_of_class_above(
        self, row: pd.Series, threshold: float, tail_index: float = 1.0
    ) -> float:
        """Share of an AGI class that lies above ``threshold``.

        Classes wholly above the threshold count in full and classes wholly
        below not at all.  A class straddling the threshold is prorated
        linearly across its AGI range - an approximation, flagged here because
        it is one: gains are concentrated toward the top of a class, so a
        straddling class contributes slightly more than this allows.  The
        open-ended top class has no range to prorate across, so it uses the
        Pareto tail :meth:`pareto_tail_index` fits to the classes below it.
        Every threshold in the validation battery (0 and $1,000,000) falls on
        an SOI class boundary, so neither rule binds for any scored case.
        """
        lower = float(row["agi_lower"])
        upper = float(row["agi_upper"])
        if lower >= threshold:
            return 1.0
        if upper <= threshold:
            return 0.0
        if upper == float("inf"):
            if tail_index <= 1.0 or lower <= 0:
                return 1.0
            return float(min(1.0, (lower / threshold) ** (tail_index - 1.0)))
        if upper <= lower:
            return 1.0
        return (upper - threshold) / (upper - lower)

    def timing_margin_share(self, year: int, threshold: float) -> float:
        """Share of the preferential base above ``threshold`` that can be retimed.

        A taxpayer chooses when to sell an appreciated asset and cannot choose
        when a fund distributes or a corporation declares a dividend, so the
        transitory response belongs to realized **long-term gains** and not to
        the qualified dividends and capital gain distributions that share the
        preferential rates with them.  Numerator: net long-term capital gain by
        AGI class, SOI Table 1.4A.  Denominator: the preferential base itself,
        SOI Table 3.5 - not long-term plus short-term, because short-term gains
        are taxed at ordinary rates and were never in this base to begin with.
        """
        resolved = self._resolve_year(year)
        tail_index = self.pareto_tail_index(resolved)
        holding = self._holding[self._holding["tax_year"] == resolved]
        long_term = 0.0
        for _, row in holding.iterrows():
            share = self._share_of_class_above(row, threshold, tail_index)
            if share > 0:
                long_term += share * float(row["net_long_term_gain_thousands"]) / 1e6

        base = sum(
            bracket.realizations_billions
            for bracket in self.get_brackets_above_threshold(
                resolved, threshold, with_timing_share=False
            )
        )
        if base <= 0:
            return 1.0
        return float(min(1.0, max(0.0, long_term / base)))

    def get_brackets_above_threshold(
        self,
        year: int,
        threshold: float,
        *,
        rate_change_brackets_only: bool = True,
        with_timing_share: bool = True,
    ) -> list[GainsBracket]:
        """Realizations above ``threshold``, grouped by the rate they face.

        ``with_timing_share=False`` skips the long-term share lookup, which
        :meth:`timing_margin_share` needs to avoid recursing into itself.
        """
        resolved = self._resolve_year(year)
        threshold = max(0.0, float(threshold))
        frame = self._brackets[self._brackets["tax_year"] == resolved]
        tail_index = self.pareto_tail_index(resolved)
        timing_share = (
            self.timing_margin_share(resolved, threshold)
            if with_timing_share
            else 1.0
        )

        buckets: dict[tuple[float, float], list[float]] = {}
        for _, row in frame.iterrows():
            statutory = float(row["statutory_rate"])
            if rate_change_brackets_only and statutory not in self.RATE_CHANGE_BRACKETS:
                continue
            share = self._share_of_class_above(row, threshold, tail_index)
            if share <= 0:
                continue
            key = (statutory, float(row["niit_rate"]))
            realized, tax = buckets.setdefault(key, [0.0, 0.0])
            buckets[key] = [
                realized + share * float(row["income_taxed_at_rate_thousands"]) / 1e6,
                tax + share * float(row["tax_generated_thousands"]) / 1e6,
            ]

        return [
            GainsBracket(
                statutory_rate=statutory,
                niit_rate=niit,
                realizations_billions=realized,
                tax_billions=tax,
                long_term_share=timing_share,
            )
            for (statutory, niit), (realized, tax) in sorted(buckets.items())
            if realized > 0
        ]

    def get_baseline_above_threshold_with_rate_method(
        self,
        year: int,
        threshold: float,
        rate_method: str = "statutory_by_agi",
    ) -> dict:
        """Aggregate realizations and the average rate facing them.

        Kept for callers that want one number rather than the bracket detail.
        ``average_effective_tax_rate`` is now the realizations-weighted average
        of each bracket's statutory-plus-NIIT rate, so it no longer books
        0-percent-bracket gains at a blended positive rate.
        """
        brackets = self.get_brackets_above_threshold(year, threshold)
        realized = sum(bracket.realizations_billions for bracket in brackets)

        if rate_method == "taxfoundation_aggregate":
            row = self._aggregate_row(year)
            rate = float(row["average_effective_tax_rate"])
            rate_source = "taxfoundation_aggregate"
        else:
            weighted = sum(
                bracket.realizations_billions * bracket.effective_rate for bracket in brackets
            )
            rate = weighted / realized if realized > 0 else 0.0
            rate_source = "soi_statutory_bracket"

        total = sum(
            bracket.realizations_billions
            for bracket in self.get_brackets_above_threshold(year, 0.0)
        )
        return {
            "tax_year": self._resolve_year(year),
            "threshold": max(0.0, float(threshold)),
            "net_capital_gain_billions": realized,
            "average_effective_tax_rate": rate,
            "taxes_paid_on_capital_gains_billions": sum(b.tax_billions for b in brackets),
            "share_of_total_realizations": (realized / total) if total > 0 else 0.0,
            "rate_source": rate_source,
        }

    def _aggregate_row(self, year: int) -> pd.Series:
        frame = self._aggregate
        exact = frame[frame["tax_year"] == year]
        if not exact.empty:
            return exact.iloc[0]
        index = (frame["tax_year"] - year).abs().idxmin()
        return frame.loc[index]

    # ------------------------------------------------------------------
    # The accrued-gains stock
    # ------------------------------------------------------------------

    def household_net_worth_billions(self, year: int) -> float:
        """Household net worth in ``year``, grown from the DFA anchor quarter."""
        anchor = self._parameters["household_net_worth_anchor_millions_usd"] / 1e3
        anchor_year = int(self._parameters["household_net_worth_anchor_year"])
        growth = self._parameters["household_net_worth_growth_rate"]
        return anchor * (1.0 + growth) ** (year - anchor_year)

    def accrued_gains_stock_billions(self, year: int) -> float:
        """Household stock of unrealized capital gains in ``year``."""
        share = self._parameters["accrued_gain_share_of_net_worth"]
        return self.household_net_worth_billions(year) * share

    def realization_hazard(self, year: int) -> float:
        """Share of the accrued-gains stock realized in a year.

        A data identity: SOI realizations over the Financial Accounts stock, at
        the baseline rate.  This is the hazard a rate change moves.
        """
        realized = sum(
            bracket.realizations_billions
            for bracket in self.get_brackets_above_threshold(year, 0.0)
        )
        stock = self.accrued_gains_stock_billions(year)
        return realized / stock if stock > 0 else 0.0

    def death_exit_rate(self) -> float:
        """Share of the accrued-gains stock leaving it at death in a year.

        Household net worth is held disproportionately by the old, so this is
        the mortality-weighted share of net worth - NCHS life table against DFA
        net worth by age of reference person - not the crude death rate.  The
        accrued-gain share cancels between numerator and denominator, so the
        same figure prices the stock's death exit and the wealth's.
        """
        return self._parameters["mortality_weighted_net_worth_share"]

    # ------------------------------------------------------------------
    # Gains transferred at death
    # ------------------------------------------------------------------

    def gains_at_death_billions(self, year: int) -> float:
        """Unrealized capital gains transferred at death in ``year``.

        Poterba & Weisbenner (2001) Table 8's flow, carried as a share of
        household net worth in the year they measured it and grown with the
        Financial Accounts stock.  Their convention - assets passing to a
        surviving spouse are not realization events - is the convention every
        realization-at-death proposal uses, so the flow is already the one such
        a policy reaches.
        """
        share = self._parameters["gains_at_death_share_of_net_worth"]
        return self.household_net_worth_billions(year) * share

    def decedent_classes(self, year: int) -> list[DecedentClass]:
        """Gains at death split across estate-size classes.

        The level is Poterba & Weisbenner's; the *shape* is Avery, Grodzicki &
        Moore's unrealized-gain share of the gross estate by estate size,
        evaluated on DFA net worth by percentile group.  Decedent counts come
        from applying Poterba & Weisbenner's estate-flow rate uniformly across
        groups, so the classes carry no within-group dispersion - a coarse
        schedule, but one with a per-decedent exemption in it, which a single
        aggregate flow cannot have.
        """
        total_gains = self.gains_at_death_billions(year)
        households = self._parameters["households_millions"] * 1e6
        flow_rate = self._parameters["estate_flow_rate"]
        ladder = self._ladder
        weights = ladder["net_worth_millions_usd"] * ladder["unrealized_gain_share"]
        total_weight = float(weights.sum())

        classes: list[DecedentClass] = []
        for (_, row), weight in zip(ladder.iterrows(), weights):
            decedents = households * float(row["household_share"]) * flow_rate
            gains = total_gains * float(weight) / total_weight if total_weight > 0 else 0.0
            per_decedent = (gains * 1e9 / decedents) if decedents > 0 else 0.0
            classes.append(
                DecedentClass(
                    group=str(row["group"]),
                    decedents_per_year=decedents,
                    gains_per_decedent_dollars=per_decedent,
                    gains_billions=gains,
                )
            )
        return classes

    @staticmethod
    def statutory_rate_on_gain(gain_dollars: float) -> float:
        """Preferential rate a gain of this size faces on a final return."""
        rate = LTCG_RATE_BRACKETS[0][1]
        for lower, bracket_rate in LTCG_RATE_BRACKETS:
            if gain_dollars >= lower:
                rate = bracket_rate
            else:
                break
        if gain_dollars >= NIIT_THRESHOLD:
            rate += NIIT_RATE
        return rate
