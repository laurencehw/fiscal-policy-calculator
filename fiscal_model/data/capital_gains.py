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

That identity is also what projects the flow.  ``R = h * A``, so a realizations
level read off one tax year and used across a ten-year window has to grow with
``A`` or the hazard ``h`` is falling - by 5.8 percent a year, which is a
behavioural assumption nobody stated.  :meth:`realizations_growth_rate` is
therefore the same growth rate the stock already uses, and no new constant
enters.  It applies only where the base's tax year is known, which is the SOI
table below; an aggregate a caller supplies carries its own vintage and this
module has nowhere to record it, so such a base is left exactly as given.

**Gains transferred at death.**  Poterba & Weisbenner (2001) Table 8 report,
from the 1998 Survey of Consumer Finances, expected estates of $118.9 billion a
year and expected unrealized capital gains at death of $42.8 billion - 36
percent of estate value - on the convention that transfers to a surviving
spouse are not realization events.  Both are carried as shares of household net
worth in the same year and grown with it, so the flow is indexed to the asset
stock rather than frozen at one constant.

**What the carve-outs reach.**  A realization-at-death proposal does not tax
all of that flow.  The same Table 8 splits unrealized gain by asset type, which
is what decides how much of a decedent's gain the section 121 principal-
residence exclusion and a family-owned-business deferral remove, and IRS SOI
*Estate Tax Statistics* Table 1 gives the charitable share by size of estate.
Two of the reliefs every such proposal states are already absent from this
base, and the table's own note is what says so: *"Bonds, vehicles, and
collectibles are assumed to have no accrued capital gains"* and *"It is assumed
a decedent transfers his/her full estate to a surviving spouse.  Such
inter-spousal transfers are not included in the estate totals reported above."*
So the tangible-personal-property and spousal carve-outs remove nothing here,
and deducting either would be a double count - which is why the spousal share
is carried in the data file and never read.

**How big each decedent's estate is.**  Those three step functions are
published on eighteen size classes between them, and until Wave 7 the module
evaluated them at five group means, so seven of the eighteen were never read by
any scored case - including the whole $1M-$5M band both Green Book per-donor
exclusions sit in.  Worse, a per-decedent exclusion applied to a group mean is a
step function: raising it from $1M to $5M removed a whole class at once.
:meth:`CapitalGainsBaseline.decedent_classes` therefore integrates over a
**piecewise-Pareto size distribution of net worth at death**, fitted in
``decedent_size_distribution.csv`` so that each Distributional Financial
Accounts percentile group's own aggregate is reproduced exactly, and evaluates
each ladder at the estate's own size.  The fit is used only above the 90th
percentile: below it the index comes back below one and the median it implies is
twice the Survey of Consumer Finances' published figure, so those two groups
keep the group mean they always had.  The **level** is untouched - it is still
Poterba & Weisbenner's flow - and only the shape changes.
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
    """One estate-size class in the gains-at-death schedule.

    The three ``*_share`` fields are shares of this class's **unrealized capital
    gain**, not of its estate value, and each corresponds to a relief a
    realization-at-death proposal states:

    ``residence_gain_share``
        The share held in the primary residence, which the section 121
        exclusion reaches up to its statutory per-person cap.
    ``active_business_gain_share``
        The share held in businesses the decedent actively participated in and
        in farms, which the Green Books' family-owned-business election defers
        until the interest is sold.
    ``charitable_bequest_share``
        The share transferred to charity, which no such proposal taxes.

    The spousal and tangible-personal-property reliefs have no field, because
    the base already excludes both (see the module docstring).

    ``unrealized_gain_share`` is a different object: unrealized gain per dollar
    of *wealth* at this estate size (Avery, Grodzicki & Moore), which prices
    how much tax a bequest of appreciated property avoids.

    A class is one **quantile slice** of the fitted size distribution, not one of
    the five Distributional Financial Accounts percentile groups; ``group`` names
    the DFA group the slice belongs to and ``net_worth_millions_usd`` is the
    slice's own conditional mean estate, which is what every share above is read
    at.  The two groups below the 90th percentile are a single slice each.
    """

    group: str
    decedents_per_year: float
    gains_per_decedent_dollars: float
    gains_billions: float
    residence_gain_share: float = 0.0
    active_business_gain_share: float = 0.0
    charitable_bequest_share: float = 0.0
    unrealized_gain_share: float = 0.0
    net_worth_millions_usd: float = 0.0

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
    CARVEOUT_FILE = "decedent_carveout_ladders.csv"
    SIZE_DISTRIBUTION_FILE = "decedent_size_distribution.csv"
    AGM_FILE = "agm_unrealized_gain_share_by_estate_size.csv"
    AGGREGATE_FILE = "taxfoundation_capital_gains_2022_2024.csv"

    #: Quantile slices per dispersed region.  This is quadrature resolution, not
    #: a modelling parameter: the published wealth breakpoints of all three
    #: ladders are forced in as slice edges and the open top slice is closed
    #: analytically, so population and aggregate wealth are exact at any count
    #: and the ten-year death channel is stable to well under a percent when it
    #: is doubled.  ``tests/test_capital_gains_death_channel.py`` pins that.
    DECEDENT_SLICES_PER_REGION = 200

    #: A capital-gains rate change is a change to the 0/15/20 percent ladder.
    #: The 25 percent (unrecaptured section 1250 gain) and 28 percent
    #: (collectibles) rates are separate statutory provisions that options such
    #: as CBO's Option 47 explicitly leave alone, so they are excluded from the
    #: rate-change base while remaining in the file.
    RATE_CHANGE_BRACKETS = (0.00, 0.15, 0.20)

    def __init__(self, data_dir: Optional[Path] = None):
        default_dir = Path(__file__).resolve().parent.parent / "data_files" / "capital_gains"
        self.data_dir = Path(data_dir) if data_dir else default_dir
        # The size distribution does not depend on the year being scored, and
        # the death channel asks for it once per year of a ten-year window.
        self._slice_cache: dict[int, list[tuple[float, float, str]]] = {}
        self._decedent_template_cache: dict[int, list[tuple]] = {}
        # The family-business recapture asks for the realization hazard once per
        # slice per year, and the hazard is a pure function of the year.
        self._hazard_cache: dict[int, float] = {}

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
    def _carveout_ladders(self) -> dict[str, tuple[tuple[float, float], ...]]:
        """Carve-out step functions, keyed by quantity, on their own boundaries.

        Each value is ``((lower bound in $M, share), ...)`` ascending.  Rows
        marked ``applied=False`` are deliberately **not** returned: the spousal
        and tangible-personal-property shares are in the file as the record of a
        double count that would be wrong to make, not as inputs.
        """
        frame = self._read(self.CARVEOUT_FILE)
        frame = frame[frame["applied"].astype(str).str.lower() == "true"]
        ladders: dict[str, list[tuple[float, float]]] = {}
        for _, row in frame.sort_values("size_class_lower_millions_usd").iterrows():
            ladders.setdefault(str(row["quantity"]), []).append(
                (
                    float(row["size_class_lower_millions_usd"]),
                    float(min(1.0, max(0.0, row["share"]))),
                )
            )
        return {name: tuple(rows) for name, rows in ladders.items()}

    @cached_property
    def _agm_ladder(self) -> tuple[tuple[float, float], ...]:
        """Unrealized-gain share of the estate by estate size (AGM Figure 1)."""
        frame = self._read(self.AGM_FILE).sort_values(
            "wealth_at_death_lower_millions_usd"
        )
        return tuple(
            (
                float(row["wealth_at_death_lower_millions_usd"]),
                float(row["unrealized_gain_share"]),
            )
            for _, row in frame.iterrows()
        )

    @cached_property
    def _size_distribution(self) -> pd.DataFrame:
        return self._read(self.SIZE_DISTRIBUTION_FILE)

    @staticmethod
    def _step(ladder: tuple[tuple[float, float], ...], estate_millions: float) -> float:
        """Value of a published step function at this estate size."""
        if not ladder:
            return 0.0
        value = ladder[0][1]
        for lower, share in ladder:
            if estate_millions >= lower:
                value = share
            else:
                break
        return value

    def unrealized_gain_share_at(self, estate_millions: float) -> float:
        """AGM Figure 1's gain share of the gross estate at this estate size."""
        return self._step(self._agm_ladder, estate_millions)

    def carveout_shares_at(self, estate_millions: float) -> dict[str, float]:
        """Every applied carve-out share at this estate size.

        The charitable share is zero below
        ``soi_estate_charitable_floor_millions_usd``: SOI's Estate Tax Table 1 is
        estate-tax filers only, so lending their charitable propensity to a
        sub-million-dollar estate would over-state a relief.  Zero over-states
        the model's revenue instead, which is the conservative direction.
        """
        floor = self._parameters.get("soi_estate_charitable_floor_millions_usd", 0.0)
        shares = {
            name: self._step(ladder, estate_millions)
            for name, ladder in self._carveout_ladders.items()
        }
        if estate_millions < floor:
            shares["charitable_bequest_share"] = 0.0
        return shares

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
        cached = self._hazard_cache.get(int(year))
        if cached is not None:
            return cached
        realized = sum(
            bracket.realizations_billions
            for bracket in self.get_brackets_above_threshold(year, 0.0)
        )
        stock = self.accrued_gains_stock_billions(year)
        hazard = realized / stock if stock > 0 else 0.0
        self._hazard_cache[int(year)] = hazard
        return hazard

    def realizations_growth_rate(self) -> float:
        """Annual growth of the realizations flow.

        Realizations are a flow off the accrued-gains stock at the observed
        hazard, ``R = h * A``, so holding ``R`` fixed while ``A`` grows is not
        a neutral choice: it asserts that ``h`` falls by this rate every year.
        The flow therefore grows at the stock's own rate, which is already in
        the parameter file and already prices the death channel.
        """
        return float(self._parameters["household_net_worth_growth_rate"])

    def realizations_projection_factor(self, from_tax_year: int, to_year: int) -> float:
        """Growth of the realizations flow from an SOI tax year to ``to_year``."""
        rate = self.realizations_growth_rate()
        return float((1.0 + rate) ** (int(to_year) - int(from_tax_year)))

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

    def decedent_size_slices(
        self, slices_per_region: Optional[int] = None
    ) -> list[tuple[float, float, str]]:
        """The decedent population as ``(population share, mean estate $M, group)``.

        Above the 90th percentile this integrates the piecewise-Pareto fitted in
        ``decedent_size_distribution.csv``.  Within a segment of index ``alpha``
        anchored at wealth ``x_lo`` at cumulative population share ``s_lo``,
        wealth at share ``s`` is ``x_lo * (s / s_lo) ** (-1 / alpha)``, so a
        slice ``[a, b]`` of the population has conditional mean

            ``x_lo * s_lo ** (1/alpha) * (b**e - a**e) / (e * (b - a))``,
            ``e = 1 - 1/alpha``,

        which is exact, not a midpoint.  The open-ended top slice is closed with
        the Pareto mean ``x * alpha / (alpha - 1)``, so the population and the
        aggregate wealth of every group are reproduced exactly at any slice
        count.  Slice edges are geometric in the survival probability with every
        published wealth breakpoint - AGM's eight, Poterba & Weisbenner's six,
        SOI's four and the charitable floor - forced in, so no slice straddles a
        boundary of a step function it is about to read.

        The two groups the fit refuses keep their group mean, which is exactly
        what the five-class ladder gave them.
        """
        count = int(slices_per_region or self.DECEDENT_SLICES_PER_REGION)
        if count < 1:
            raise ValueError(f"slices_per_region must be >= 1, got {count}")
        cached = self._slice_cache.get(count)
        if cached is not None:
            return cached

        ladder = self._ladder.set_index("group")
        breakpoints = sorted(
            {
                bound
                for rows in self._carveout_ladders.values()
                for bound, _ in rows
                if bound > 0
            }
            | {bound for bound, _ in self._agm_ladder if bound > 0}
            | {
                value
                for key, value in self._parameters.items()
                if key == "soi_estate_charitable_floor_millions_usd" and value > 0
            }
        )

        slices: list[tuple[float, float, str]] = []
        for _, row in self._size_distribution.iterrows():
            group = str(row["group"])
            lower = float(row["percentile_share_lower"])
            upper = float(row["percentile_share_upper"])
            if not bool(row["dispersed"]):
                slices.append(
                    (
                        upper - lower,
                        float(ladder.loc[group, "mean_net_worth_millions_usd"]),
                        group,
                    )
                )
                continue

            alpha = float(row["pareto_alpha"])
            anchor = float(row["threshold_millions_usd"])
            exponent = 1.0 - 1.0 / alpha
            scale = anchor * upper ** (1.0 / alpha)

            def mean_between(a: float, b: float) -> float:
                return scale * (b**exponent - a**exponent) / (exponent * (b - a))

            if lower <= 0.0:
                # Open-ended top: cut it at **one household**, which is a bound
                # with a meaning rather than an arbitrarily small number, and
                # close that last slice with the Pareto mean above it.  On the
                # shipped DFA vintage the richest household comes out at a few
                # hundred billion dollars, which is the order of magnitude the
                # published wealth lists put it at.
                lower = 1.0 / (self._parameters["households_millions"] * 1e6)
                top_wealth = anchor * (lower / upper) ** (-1.0 / alpha)
                slices.append((lower, top_wealth * alpha / (alpha - 1.0), group))

            edges = {lower * (upper / lower) ** (i / count) for i in range(count + 1)}
            for wealth in breakpoints:
                share = upper * (wealth / anchor) ** (-alpha)
                if lower < share < upper:
                    edges.add(share)
            ordered = sorted(edges)
            for a, b in zip(ordered[:-1], ordered[1:]):
                slices.append((b - a, mean_between(a, b), group))
        self._slice_cache[count] = slices
        return slices

    def decedent_classes(
        self, year: int, slices_per_region: Optional[int] = None
    ) -> list[DecedentClass]:
        """Gains at death split across the fitted estate-size distribution.

        The **level** is Poterba & Weisbenner's flow and is not this schedule's
        to change: gains are distributed across slices in proportion to
        ``wealth * unrealized_gain_share(wealth)`` and renormalised to that flow,
        so ``sum(decedents * gain per decedent)`` is
        :meth:`gains_at_death_billions` whatever the slice count is.  What
        changed in Wave 7 is that the *shape* is a distribution rather than five
        point masses, and that Avery, Grodzicki & Moore's, Poterba &
        Weisbenner's and SOI's step functions are read at each slice's own estate
        size instead of at five group means.

        Decedent counts still apply one uniform death rate across the wealth
        distribution - Poterba & Weisbenner's *dollar* flow of estates over net
        worth, used as a headcount rate.  That is the coarsest thing left in the
        channel and it is not this method's to fix: see
        ``planning/lanes/W7_decedent_ladder.md`` §7.
        """
        total_gains = self.gains_at_death_billions(year)
        count = int(slices_per_region or self.DECEDENT_SLICES_PER_REGION)
        return [
            DecedentClass(
                group=group,
                decedents_per_year=decedents,
                gains_per_decedent_dollars=total_gains * gain_share * 1e9 / decedents
                if decedents > 0
                else 0.0,
                gains_billions=total_gains * gain_share,
                residence_gain_share=residence,
                active_business_gain_share=business,
                charitable_bequest_share=charitable,
                unrealized_gain_share=agm,
                net_worth_millions_usd=mean,
            )
            for (
                group,
                decedents,
                gain_share,
                residence,
                business,
                charitable,
                agm,
                mean,
            ) in self._decedent_template(count)
        ]

    def _decedent_template(self, count: int) -> list[tuple]:
        """Everything about the schedule that does not depend on the year.

        The year enters only as the level of gains at death, so the decedent
        counts, the share of the flow each slice carries and the four published
        shares each slice reads are computed once.
        """
        cached = self._decedent_template_cache.get(count)
        if cached is not None:
            return cached

        households = self._parameters["households_millions"] * 1e6
        flow_rate = self._parameters["estate_flow_rate"]
        schedule = self.decedent_size_slices(count)
        weights = [
            share * households * mean * self.unrealized_gain_share_at(mean)
            for share, mean, _ in schedule
        ]
        total_weight = sum(weights)

        template = []
        for (share, mean, group), weight in zip(schedule, weights):
            shares = self.carveout_shares_at(mean)
            template.append(
                (
                    group,
                    households * share * flow_rate,
                    weight / total_weight if total_weight > 0 else 0.0,
                    shares.get("residence_gain_share", 0.0),
                    shares.get("active_business_gain_share", 0.0),
                    shares.get("charitable_bequest_share", 0.0),
                    self.unrealized_gain_share_at(mean),
                    mean,
                )
            )
        self._decedent_template_cache[count] = template
        return template

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
