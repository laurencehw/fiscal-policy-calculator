"""
Trade and Tariff Policy Module

Scores a tariff the way a conventional revenue estimate scores an indirect
tax: gross customs duty, net of the import-demand response, duty avoidance and
the income-and-payroll offset — and then reports the two channels a
*conventional* estimate deliberately excludes, GDP feedback and retaliation,
as the separate figures every published tariff estimator prints them as.

The conventional chain, per year::

    Δτ      = stated rate − the duty the base already collects
    p       = border_pass_through × Δτ
    V       = 1 + ε·p                                    for p ≤ 30pp
            = 1 + ε·0.30 + (p − 0.30)·ε·multiplier       above it, floored
    gross   = base · V · Δτ/(1 + Δτ)
    avoid   = avoidance_rate · gross
    offset  = income_payroll_offset · (gross − avoid)
    net     = gross − avoid − offset          → 0.7180 · gross on the
                                                app's window; the offset
                                                is JCT's year path, so
                                                the ratio depends on it

and the two dynamic channels, reported beside it and never inside it::

    impulse = border_pass_through · Δτ · (base · V)      the real income the
                                                        price effect withdraws
    gdp_fb  = FRBUSAdapterLite(impulse).cumulative_revenue_feedback
    retal   = marginal_receipts_rate · [retaliation_rate · Δτ · export_base]

``estimate_static_revenue_effect`` returns ``gross``;
``estimate_behavioral_offset`` returns ``avoid + offset`` **signed to match
``gross``**, so the scorer's ``final_deficit_effect`` is the conventional
figure, both halves stay separately readable — which is what the app's tariff
caption renders — and a tariff *cut* has its cost eroded rather than amplified.

Four things about that chain are worth stating plainly, because the module
used to do none of them:

1. **The income-and-payroll offset.** CBO, JCT and Treasury's Office of Tax
   Analysis all score an indirect tax net of an offset, on the convention
   that a policy change does not alter total nominal income: duty paid is
   income not paid to labour and capital, so the income and payroll tax bases
   shrink. Before this the module returned gross customs revenue and called it
   a score. The offset is a **year path**, not the round 25% it is usually
   quoted at — JCT's own published percentages run 0.244 in 2025 to 0.241 in
   2035, and ship in CBO's Conventional Tariff Analysis Model at
   ``inputs/offset/2025OffsetPostHR1.csv``. See
   :func:`load_income_payroll_offset_path`.
2. **Pass-through belongs in the demand response.** Amiti, Redding & Weinstein
   (2019) and Fajgelbaum et al. (2020) find the duty-inclusive US import price
   rose approximately one-for-one with the 2018-19 tariffs and foreign export
   prices did not fall, so the whole tariff reaches the price importers face:
   ``border_pass_through_rate`` is frozen at 1.00. That is a *different and
   larger* number than the retail pass-through the household-cost display
   needs (Cavallo et al. 2021), which stays at 0.60 under its own key.
3. **The tax-inclusive rate.** A conventional estimate holds nominal income
   fixed, so the same nominal spending buys a duty-inclusive bundle: the duty
   is ``base × τ/(1+τ)``, not ``base × τ`` (Tax Foundation FF861 p. 4 n. 10,
   citing JCT JCX-58-23).
4. **Retaliation and GDP feedback are not conventional-score channels.** Tax
   Foundation FF861 prints three columns for the same policy — conventional
   $2,171.1B, dynamic $1,721.0B, dynamic with retaliation $1,443.0B — and
   every target in this repository's trade block is a *conventional* figure.
   The module used to subtract retaliation inside the score, which made it a
   different object from the thing it was measured against. Both channels are
   still computed, and :meth:`TariffPolicy.get_trade_summary` reports all
   three columns; neither is inside the number the scorer books.

Every level in ``TRADE_BASELINE`` is a 2024 Census measurement, transcribed
with its provenance to ``data_files/trade/tariff_scoring_inputs.csv`` and —
for the Section 232 bases, which are measured at the **article** level rather
than by HS chapter — ``data_files/trade/section232_hts_bases.csv``; the
behavioural parameters are one frozen, cited value per mechanism, and the
income-and-payroll offset is a published year path in
``data_files/trade/income_payroll_offset_path.csv``. No constant here is keyed
to a benchmark. In particular the two coverage constants that
used to be fitted to their own targets are gone: ``universal_coverage_rate`` is
now 1 minus the Canada-plus-Mexico share of goods imports (the USMCA carve-out
every universal-tariff proposal carries), and ``china_effective_coverage`` is
deleted in favour of the incremental-rate identity — a 60% tariff on China
raises the rate by 60pp minus the 10.93% already collected, applied to the
whole base.

References:
- Amiti, Redding & Weinstein (2019), *JEP* 33(4); Fajgelbaum, Goldberg, Kennedy
  & Khandelwal (2020), *QJE* 135(1) — near-complete border pass-through
- Cavallo, Gopinath, Neiman & Tang (2021), *AER: Insights* 3(1) — partial
  retail pass-through
- Ghodsi, Grübler & Stehrer (2016) — US binding weighted-average import-demand
  elasticity of −0.997
- Boehm, Levchenko & Pandalai-Nayar (2023), *AER* 113(4); USITC pub. 5405 —
  elasticities roughly double over the medium run
- JCT, *The Income and Payroll Tax Offset to Changes in Excise Tax Revenues*
  (JCX-59-11) and JCX-9-24, cited through Tax Foundation FF861 pp. 3-4
- Tax Foundation, *How Much Revenue Can Tariffs Really Raise for the Federal
  Government?*, Fiscal Fact 861 (April 2025)
- U.S. Census Bureau international trade series, 2024
- U.S. Congressional Budget Office, *Conventional Tariff Analysis Model*,
  github.com/US-CBO/conventional-tariff-analysis-model @ 59ea68fd (2026-02-17),
  documented at cbo.gov/publication/61388 — the source of the Section 232
  HS-10 article lists, their metal-content shares, the USMCA US-content auto
  carve-out, and JCT's income-and-payroll offset path
"""

import csv
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from .constants import MARGINAL_REVENUE_RATE
from .policies import PolicyType, TaxPolicy

#: One partner of a multi-rate tariff: display name, import base in billions,
#: and the incremental ad valorem rate that partner faces.
ScheduleRow = tuple[str, float, float]

RECIPROCAL_SCHEDULE_PATH = (
    Path(__file__).parent / "data_files" / "trade" / "reciprocal_schedule.csv"
)

INCOME_PAYROLL_OFFSET_PATH = (
    Path(__file__).parent / "data_files" / "trade" / "income_payroll_offset_path.csv"
)

TRADE_BASELINE = {
    # --- Trade levels: U.S. Census Bureau, 2024 (see the CSV) --------------
    "total_imports_billions": 3263.9,
    "total_exports_billions": 2063.0,
    "current_avg_tariff_rate": 0.0236,
    "current_tariff_revenue_billions": 76.6,
    "us_households": 130_000_000,

    # Country- and sector-specific import bases and the duty each already pays
    "china_imports_billions": 440.3,
    "china_existing_avg_tariff": 0.1093,   # calculated duty / imports for consumption
    "us_exports_to_china_billions": 143.3,  # China's retaliation base
    "eu_imports_billions": 550.0,
    # --- Section 232 bases, at the article level --------------------------
    # These five levels are CBO's own HS-10 Section 232 article lists
    # aggregated over CBO's own Census file, both shipped in the Conventional
    # Tariff Analysis Model at commit 59ea68fd. See
    # `data_files/trade/section232_hts_bases.csv`, which carries the path and
    # line count behind every one of them. They replace four HS-chapter
    # proxies, and the chapter proxies were wrong in both directions:
    #
    #   * `alum_steel.csv` puts 558 of its 1,180 lines in **HS 73**, so most of
    #     that chapter is *primary* Section 232 scope, not derivative, and the
    #     old "floor" of HS 72 + HS 76 excluded it;
    #   * the derivative annex lives in chapters 82-86, 87, 94, 95 (high metal
    #     content) and 34, 38, 82, 84, 85, 87, 94, 95 (low) — machinery,
    #     furniture, appliances — which HS 73 does not contain at all, so the
    #     old "ceiling" of HS 73 was 2.5x too *small*;
    #   * HS 87 both over-includes (tractors, trailers, motorcycles, bicycles,
    #     baby carriages) and under-includes (parts in chapters 40, 70, 83, 84,
    #     85, 90) relative to `autos.csv` + `auto_parts.csv`.
    #
    # A derivative is taxed on its metal *content*, which is what Proclamation
    # 10896 says and what the module previously had no way to express: CBO's
    # shares are 0.75 of a high-content article's value and 0.25 of a
    # low-content one (`config/default.yaml:72-73`), so the taxed base is
    # `0.75 x $108.755B + 0.25 x $164.141B`. The derivatives stay their own
    # schedule row because they collect a different duty from the primary base.
    "auto_imports_billions": 214.2811,       # autos.csv, after the US-content carve-out
    "auto_parts_imports_billions": 340.6701,  # auto_parts.csv
    "auto_existing_avg_tariff": 0.018363,
    "steel_aluminum_imports_billions": 96.7516,  # alum_steel.csv, ex auto parts
    "steel_aluminum_existing_avg_tariff": 0.046416,
    "steel_derivative_imports_billions": 122.6015,  # content-weighted
    "steel_derivative_existing_avg_tariff": 0.03872,

    # --- Behavioural parameters: one frozen, cited value per mechanism -----
    # Border pass-through into duty-inclusive import prices. Amiti, Redding &
    # Weinstein (2019); Fajgelbaum et al. (2020): approximately complete.
    "border_pass_through_rate": 1.00,
    # Retail pass-through, for the household-cost display only. Cavallo et al.
    # (2021) find this is materially below the border figure.
    "consumer_pass_through_rate": 0.60,
    # Ghodsi, Grübler & Stehrer (2016) binding weighted-average for the US,
    # adopted by Tax Foundation FF861 p. 4.
    "import_price_elasticity": -0.997,
    "retaliation_rate": 0.30,
    # Still unsourced, and CTAM has nothing to offer: CBO's tariff model
    # carries no avoidance or noncompliance parameter at all. Its
    # `exporter_absorption: 5` is a different object — incomplete border
    # pass-through — and contradicts the 1.00 above, which *is* sourced.
    "tariff_avoidance_rate": 0.05,
    # The income-and-payroll offset is a **year path**, not a scalar: JCT's own
    # published percentages, 0.244 (2025) falling to 0.241 (2035), shipped in
    # CBO's tariff model at `inputs/offset/2025OffsetPostHR1.csv` and applied
    # there one year at a time (`code/model/add_offset.py:18`). The path lives
    # in `data_files/trade/income_payroll_offset_path.csv`; this key is the
    # mean over the *library* default window, kept so that callers reading
    # `TRADE_BASELINE` directly still get a number. The scoring chain does not
    # read it — it reads the path, over each policy's own window.
    "income_payroll_offset_rate": 0.2442,
    # Federal receipts per dollar of income lost to retaliation — the app's own
    # dynamic-scoring convention, not a new constant.
    "marginal_receipts_rate": MARGINAL_REVENUE_RATE,

    # Effective coverage of a universal tariff: 1 minus the Canada + Mexico
    # share of goods imports, i.e. the USMCA carve-out every universal-tariff
    # proposal has carried. Derived, not fitted.
    "universal_coverage_rate": 0.7197,
    # `reciprocal_coverage_rate = 0.50` is gone. It was the last number in this
    # dict that was a shape assumption rather than a measurement — "a flat 20pp
    # on half of goods imports", which is not a policy anyone proposed. The
    # reciprocal preset now reads a partner-by-partner schedule built from
    # Executive Order 14257's own formula applied to 2024 Census bilateral
    # trade: see `reciprocal_schedule.csv` and `load_reciprocal_schedule`.

    # Non-linear tariff response. Elasticities roughly double over the medium
    # run (Boehm, Levchenko & Pandalai-Nayar 2023; USITC pub. 5405), which
    # bites hardest on the large rate changes.
    "high_tariff_threshold": 0.30,
    "high_tariff_elasticity_multiplier": 2.0,
    "min_volume_factor": 0.20,  # Floor: imports never fall below 20% of base
}


@lru_cache(maxsize=1)
def load_reciprocal_schedule() -> tuple[ScheduleRow, ...]:
    """Partner-by-partner covered base and rate for the reciprocal tariff.

    Reads ``data_files/trade/reciprocal_schedule.csv``, which
    ``scripts/build_reciprocal_schedule.py`` writes from 2024 Census bilateral
    trade by applying Executive Order 14257's own formula — bilateral goods
    deficit over goods imports, halved, floored at 10% — and removing the
    Annex II sectors partner by partner.

    ``role=external_check`` rows are the published Annex I rates. They exist so
    a reconstruction that drifts from the document is visible, and this loader
    skips them: nothing the module scores may read them.
    """
    rows: list[ScheduleRow] = []
    with RECIPROCAL_SCHEDULE_PATH.open(encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    for record in csv.DictReader(lines):
        if record.get("role") != "model_input":
            continue
        base = float(record["covered_imports_billions"])
        if base <= 0:
            continue
        rows.append((record["partner"], base, float(record["reciprocal_rate"])))
    if not rows:
        raise ValueError(
            f"{RECIPROCAL_SCHEDULE_PATH} carries no model_input rows; "
            "rebuild it with scripts/build_reciprocal_schedule.py"
        )
    return tuple(rows)


@lru_cache(maxsize=1)
def load_income_payroll_offset_path() -> tuple[tuple[int, float], ...]:
    """JCT's published income-and-payroll offset, year by year.

    Reads ``data_files/trade/income_payroll_offset_path.csv``, a transcription
    of ``inputs/offset/2025OffsetPostHR1.csv`` from CBO's Conventional Tariff
    Analysis Model at commit ``59ea68fd``. CBO applies it multiplicatively, one
    year at a time, at ``code/model/add_offset.py:18``.
    """
    rows: list[tuple[int, float]] = []
    with INCOME_PAYROLL_OFFSET_PATH.open(encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    for record in csv.DictReader(lines):
        rows.append((int(record["year"]), float(record["offset"])))
    if not rows:
        raise ValueError(f"{INCOME_PAYROLL_OFFSET_PATH} carries no rows")
    return tuple(sorted(rows))


def income_payroll_offset_rate(year: int) -> float:
    """The offset JCT publishes for ``year``, clamped to the path's own range.

    Clamped rather than extrapolated: a published path is a statement about
    the years it covers, and inventing a slope beyond them would turn a
    transcription back into an assumption.
    """
    path = load_income_payroll_offset_path()
    if year <= path[0][0]:
        return path[0][1]
    if year >= path[-1][0]:
        return path[-1][1]
    return dict(path)[year]


def window_income_payroll_offset_rate(start_year: int, duration_years: int) -> float:
    """Mean offset over ``[start_year, start_year + duration_years)``.

    **This is an identity, not an approximation, for every tariff the module
    scores today.** ``scoring_engine`` calls ``estimate_behavioral_offset``
    once per year with no year argument, and a tariff's gross is flat across
    the window — :class:`TariffPolicy` is not in the engine's growth handlers
    and has no ``soi_base_tax_year``, so the income-base projection factor is
    1.0. With a flat gross ``g``, ``sum_t g(1 - o_t) = n * g * (1 - mean o)``
    exactly. It would become an approximation for a phased-in tariff, which is
    why ``planning/lanes/R8_tariff_ctam.md`` carries the year-indexed hand-off
    as an open item rather than claiming this is general.
    """
    if duration_years <= 0:
        return income_payroll_offset_rate(start_year)
    years = range(int(start_year), int(start_year) + int(duration_years))
    return sum(income_payroll_offset_rate(y) for y in years) / len(years)


@dataclass
class TariffPolicy(TaxPolicy):
    """
    Tariff / trade policy.

    Scores net customs receipts — gross duty less the import-demand response,
    avoidance, the income-and-payroll offset and the receipts lost to
    retaliation — and reports consumer cost and household impact alongside.
    """
    policy_type: PolicyType = PolicyType.EXCISE_TAX
    tariff_rate_change: float = 0.0
    target_country: str | None = None
    target_sector: str | None = None
    import_base_billions: float = 0.0
    pass_through_rate: float = TRADE_BASELINE["consumer_pass_through_rate"]
    border_pass_through_rate: float = TRADE_BASELINE["border_pass_through_rate"]
    import_elasticity: float = TRADE_BASELINE["import_price_elasticity"]
    retaliation_rate: float = TRADE_BASELINE["retaliation_rate"]
    #: Value of US exports a trading partner can retaliate against. Defaults to
    #: total goods exports scaled by this policy's share of goods imports —
    #: partners retaliate in proportion to the harm done, so a $59B steel
    #: tariff does not invite retaliation against the whole $2.1T of exports.
    #: A country-targeted factory overrides it with exports to that country.
    retaliation_export_base_billions: float = 0.0
    include_consumer_cost: bool = True
    #: Whether the *reported* dynamic-with-retaliation figure carries the
    #: retaliation channel. Since lane H8 this no longer touches the scored
    #: number: retaliation is not in a conventional estimate, and every target
    #: this module is measured against is a conventional estimate.
    include_retaliation: bool = True
    #: Optional partner- or segment-specific rates, ``(name, base, rate)``.
    #: When set, every step of the chain sums over the rows instead of
    #: evaluating once at an average rate. That matters because the volume
    #: response is **convex** in the rate — the elasticity doubles above a 30pp
    #: price change — so an average understates the loss on the rows above the
    #: threshold and overstates it on the rows below.
    rate_schedule: tuple[ScheduleRow, ...] = field(default_factory=tuple)

    def __post_init__(self):
        self.policy_type = PolicyType.EXCISE_TAX
        super().__post_init__()
        if self.rate_schedule:
            self.rate_schedule = tuple(
                (str(name), float(base), float(rate))
                for name, base, rate in self.rate_schedule
            )
            self.import_base_billions = sum(row[1] for row in self.rate_schedule)
            # The scalar rate becomes the base-weighted average, so every
            # caller that reads `tariff_rate_change` — the consumer-cost
            # display, the retaliation channel, the zero guards — keeps
            # working. The *score* never reads it when a schedule is set.
            if self.import_base_billions:
                self.tariff_rate_change = (
                    sum(base * rate for _, base, rate in self.rate_schedule)
                    / self.import_base_billions
                )
        if self.import_base_billions <= 0 and self.tariff_rate_change != 0:
            self.import_base_billions = TRADE_BASELINE["total_imports_billions"]
        if self.retaliation_export_base_billions <= 0:
            total_imports = TRADE_BASELINE["total_imports_billions"]
            exposure = self.import_base_billions / total_imports if total_imports else 0.0
            # Exposure is a *share* of trade, so it is capped at 1. A caller can
            # pass an import base above total US goods imports (the API takes an
            # arbitrary figure, and a hypothetical can exceed the 2024 vintage);
            # without the cap that would invite retaliation against more US
            # exports than exist, which is not what "proportional" means.
            self.retaliation_export_base_billions = (
                TRADE_BASELINE["total_exports_billions"] * min(1.0, exposure)
            )

    # -- the scoring chain -------------------------------------------------

    def import_price_change(self) -> float:
        """Proportional rise in the price importers face.

        The tariff reaches that price approximately one-for-one: foreign
        exporters did not cut their prices in 2018-19 (Amiti, Redding &
        Weinstein 2019; Fajgelbaum et al. 2020). This is the price change the
        import-demand elasticity acts on — not the retail pass-through, which
        is smaller and belongs to the consumer-cost display.
        """
        return self.border_pass_through_rate * self.tariff_rate_change

    def _volume_factor_at(self, rate: float) -> float:
        """Share of a base facing ``rate`` that still arrives."""
        price_change = self.border_pass_through_rate * rate
        threshold = TRADE_BASELINE["high_tariff_threshold"]
        hi_mult = TRADE_BASELINE["high_tariff_elasticity_multiplier"]
        floor = TRADE_BASELINE["min_volume_factor"]
        if price_change > threshold:
            factor = (
                1
                + self.import_elasticity * threshold
                + (price_change - threshold) * self.import_elasticity * hi_mult
            )
        else:
            factor = 1 + self.import_elasticity * price_change
        return max(floor, factor)

    def import_volume_factor(self) -> float:
        """Share of the pre-tariff import base that still arrives.

        With a ``rate_schedule`` this is the base-weighted average of the
        per-row factors, which is a *report* rather than an input: the score
        evaluates the factor row by row, because the response is convex.
        """
        if self.rate_schedule and self.import_base_billions:
            return (
                sum(
                    base * self._volume_factor_at(rate)
                    for _, base, rate in self.rate_schedule
                )
                / self.import_base_billions
            )
        return self._volume_factor_at(self.tariff_rate_change)

    def estimate_static_revenue_effect(
        self, baseline_revenue: float, use_real_data: bool = True
    ) -> float:
        """Gross customs duty, after the import-demand response.

        The rate is applied tax-inclusively. A conventional estimate holds
        nominal income fixed, so the same nominal spending buys a
        duty-inclusive bundle and the duty collected is ``base × τ/(1+τ)``
        (Tax Foundation FF861 p. 4 n. 10, citing JCT JCX-58-23). Everything
        that stands between this and the score is in
        :meth:`estimate_behavioral_offset`.
        """
        if self.rate_schedule:
            return sum(
                base * self._volume_factor_at(rate) * rate / (1 + rate)
                for _, base, rate in self.rate_schedule
            )
        if self.tariff_rate_change == 0:
            return 0.0
        rate = self.tariff_rate_change
        adjusted_base = self.import_base_billions * self.import_volume_factor()
        return adjusted_base * rate / (1 + rate)

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Everything between gross customs duty and the conventional score.

        Two channels, and since lane H8 only two:

        * **Avoidance and evasion** — a flat share of gross duty.
        * **The income-and-payroll offset** — the CBO/JCT/OTA convention that
          an indirect tax shrinks the income and payroll tax bases by about a
          quarter of its net receipts.

        **Retaliation is not here any more.** A conventional revenue estimate
        does not net foreign retaliation: Tax Foundation FF861 prints
        retaliation in a third column beside its conventional and dynamic ones,
        and every target this module is scored against is a conventional
        figure. Subtracting it inside the score made the model a different
        object from the thing it was measured against. It is still computed —
        :meth:`estimate_retaliation_revenue_loss` — and
        :meth:`get_trade_summary` reports it beside the GDP-feedback channel.

        The ratio this leaves is ``(1 − 0.05) × (1 − offset)`` of gross
        duty, for every tariff in every direction — 0.7180 on the app's
        FY2026-2035 window and 0.7178 on the validation window, against
        FF861's implied 0.738. The remaining difference is that FF861 books
        its 8% noncompliance inside the base rather than as a separate line.
        It used to be a flat 0.7125, because the offset used to be a scalar.

        **Signed to match ``static_effect``**, the convention
        :meth:`fiscal_model.policies_core.TaxPolicy.estimate_behavioral_offset`
        sets for every behavioural offset in the repository: the scorer adds
        this to ``-static_revenue``, so an offset carrying the static effect's
        sign erodes the magnitude in *both* directions. A tariff cut loses less
        revenue than its gross figure because the income and payroll bases grow
        back; returning an unsigned positive here would make a cut cost more
        than its own gross, not less.

        Scales with ``static_effect`` so a phased-in tariff nets down by the
        same proportion its gross duty phases in by.
        """
        gross = abs(static_effect)
        if gross == 0.0:
            return 0.0
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = (gross - avoidance) * self.income_payroll_offset_rate()
        return math.copysign(avoidance + offset, static_effect)

    def income_payroll_offset_rate(self) -> float:
        """JCT's offset over this policy's own window.

        The convention used to be the round 0.25 that CBO, JCT and Treasury's
        Office of Tax Analysis are usually *quoted* at, cited secondhand
        through Tax Foundation FF861 because jct.gov 403s this environment.
        The percentages themselves ship in CBO's own tariff model, so this now
        reads them: 0.244 in 2025 falling to 0.241 in 2035
        (:func:`load_income_payroll_offset_path`).

        Deliberately **not** FF861's 26.2%, which
        ``tariff_scoring_inputs.csv`` already records as an external check not
        adopted — it is Tax Foundation's own model output for this window, and
        adopting it would move a parameter toward one of this module's own
        benchmarks. JCT's path is neither.
        """
        return window_income_payroll_offset_rate(
            int(getattr(self, "start_year", 2025) or 2025),
            int(getattr(self, "duration_years", 10) or 10),
        )

    # -- the channels, separately readable ---------------------------------

    def estimate_income_payroll_offset(self) -> float:
        """Annual income and payroll receipts lost to the tariff itself.

        Signed like the duty it offsets, so a tariff cut returns a negative
        figure — the income and payroll bases grow when duty falls.
        """
        gross = self.estimate_static_revenue_effect(0.0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        return (gross - avoidance) * self.income_payroll_offset_rate()

    def macro_demand_impulse(self) -> float:
        """Annual real income the tariff's price effect withdraws, in billions.

        The impulse a macro model should see is **not** the tariff's net
        receipts, which is what the generic dynamic path uses today. A tariff
        withdraws more real income than it collects, for two reasons already in
        this module:

        * the duty-inclusive price rises by the *whole* tariff (border
          pass-through frozen at 1.00 on Amiti–Redding–Weinstein and Fajgelbaum
          et al.), so households pay ``Δτ`` on every dollar that still arrives
          while the Treasury collects ``Δτ/(1+Δτ)``; and
        * the goods that stop arriving — ``1 − V(p)`` of the base — cost
          surplus and raise no duty at all.

        So the impulse is the tariff's own price *and* volume effect,
        ``border_pass_through · Δτ · base · V``, which is the gross duty
        grossed back up by ``(1 + Δτ)``. For the universal preset that is
        $211.5B/yr against net receipts of $125.9B/yr, and that gap is the
        channel.

        Signed like the duty: a tariff cut returns a negative impulse.
        """
        if self.rate_schedule:
            return sum(
                self.border_pass_through_rate * rate * base * self._volume_factor_at(rate)
                for _, base, rate in self.rate_schedule
            )
        return (
            self.border_pass_through_rate
            * self.tariff_rate_change
            * self.import_base_billions
            * self.import_volume_factor()
        )

    def estimate_gdp_feedback_revenue_loss(self, horizon_years: int = 10) -> float:
        """Federal receipts lost over the window because output falls.

        Routed through :class:`~fiscal_model.models.FRBUSAdapterLite`, the
        adapter the repository already uses for dynamic scoring, rather than
        through a reduced form of this module's own. Every parameter in the
        channel — the −0.7 tax multiplier, the 0.75 decay, the 0.15
        crowding-out term, the 0.65 monetary offset and the 0.25 marginal
        revenue rate — is the adapter's. This method supplies the one thing the
        adapter does not have, which is :meth:`macro_demand_impulse`.

        **Not in the score.** Published tariff estimates put GDP feedback in a
        *dynamic* column and the targets in this repository's trade block are
        conventional; folding it into the score would measure one against the
        other. :meth:`get_trade_summary` reports it beside the conventional
        figure, the way FF861 prints its three columns.

        Returned as a **loss signed like the duty**, so a tariff increase gives
        a positive number that is subtracted from a positive conventional
        score, and a tariff cut gives a negative one.
        """
        impulse = self.macro_demand_impulse()
        if impulse == 0.0 or horizon_years <= 0:
            return 0.0
        # Local import: fiscal_model.models pulls in the whole adapter family,
        # and importing it at module scope would put a macro dependency on the
        # import path of every policy module.
        from .models import FRBUSAdapterLite, MacroScenario

        scenario = MacroScenario(
            name=f"{self.name} — tariff price and volume effect",
            description=(
                "Real income withdrawn by the tariff's duty-inclusive price "
                "rise on the imports that still arrive"
            ),
            start_year=int(getattr(self, "start_year", 2025) or 2025),
            horizon_years=horizon_years,
            receipts_change=np.full(horizon_years, impulse, dtype=float),
        )
        return -float(FRBUSAdapterLite().run(scenario).cumulative_revenue_feedback)

    def estimate_consumer_cost(self) -> float:
        """Annual cost to consumers from higher retail prices."""
        if self.tariff_rate_change <= 0:
            return 0.0
        if self.rate_schedule:
            return sum(
                self.pass_through_rate * rate * base
                for _, base, rate in self.rate_schedule
                if rate > 0
            )
        return self.pass_through_rate * self.tariff_rate_change * self.import_base_billions

    def estimate_retaliation_cost(self) -> float:
        """Annual export value lost to trading-partner retaliation."""
        if self.tariff_rate_change <= 0:
            return 0.0
        return (
            self.retaliation_rate
            * self.tariff_rate_change
            * self.retaliation_export_base_billions
        )

    def estimate_retaliation_revenue_loss(self) -> float:
        """Annual federal receipts lost to retaliation.

        Lost exports are lost income, and the federal government takes about
        :data:`~fiscal_model.constants.MARGINAL_REVENUE_RATE` of income at the
        margin. This under-states the drag — an export-value loss is not an
        income loss, and no multiplier or supply-chain effect is modelled — and
        the lane file records the size of the gap against Tax Foundation's own
        estimate of retaliation's revenue cost.
        """
        return self.estimate_retaliation_cost() * TRADE_BASELINE["marginal_receipts_rate"]

    def get_household_impact(self) -> float:
        """Annual cost per household."""
        return self.estimate_consumer_cost() * 1e9 / TRADE_BASELINE["us_households"]

    def get_trade_summary(self, horizon_years: int = 10) -> dict:
        """Annual figures for all three of the columns a tariff has.

        ``net_revenue`` is the **conventional** figure and is always what the
        scorer books, so the summary and the score cannot disagree. The GDP and
        retaliation channels are reported beside it — ``dynamic_revenue`` and
        ``dynamic_with_retaliation_revenue`` — which is the column structure
        Tax Foundation FF861 publishes for the same policy ($2,171.1B /
        $1,721.0B / $1,443.0B for the 10% universal tariff).

        The GDP channel is a path over ``horizon_years`` rather than a flat
        annual, so it appears twice: ``gdp_feedback_revenue_loss`` is the
        annualised figure, for arithmetic with the other annual rows, and
        ``gdp_feedback_revenue_loss_total`` is the window total the adapter
        actually returns.
        """
        gross = self.estimate_static_revenue_effect(0)
        avoidance = gross * TRADE_BASELINE["tariff_avoidance_rate"]
        offset = self.estimate_income_payroll_offset()
        retaliation_exports = self.estimate_retaliation_cost()
        retaliation_revenue = (
            self.estimate_retaliation_revenue_loss() if self.include_retaliation else 0.0
        )
        conventional = gross - avoidance - offset
        gdp_total = self.estimate_gdp_feedback_revenue_loss(horizon_years)
        gdp_annual = gdp_total / horizon_years if horizon_years else 0.0
        dynamic = conventional - gdp_annual
        return {
            "gross_tariff_revenue": gross,
            # Retained key: several callers and tests read "tariff_revenue" as
            # the gross customs figure, which is what it has always been.
            "tariff_revenue": gross,
            "behavioral_offset": avoidance,
            "income_payroll_offset": offset,
            "retaliation_revenue_loss": retaliation_revenue,
            "conventional_revenue": conventional,
            "net_revenue": conventional,
            "net_to_gross_ratio": conventional / gross if gross else 0.0,
            "macro_demand_impulse": self.macro_demand_impulse(),
            "gdp_feedback_revenue_loss": gdp_annual,
            "gdp_feedback_revenue_loss_total": gdp_total,
            "dynamic_revenue": dynamic,
            "dynamic_with_retaliation_revenue": dynamic - retaliation_revenue,
            "consumer_cost": self.estimate_consumer_cost(),
            "retaliation_cost": retaliation_exports,
            "household_cost": self.get_household_impact(),
        }


def create_trump_universal_10() -> TariffPolicy:
    """10% on all imports outside the USMCA carve-out."""
    coverage = TRADE_BASELINE["universal_coverage_rate"]
    effective_base = TRADE_BASELINE["total_imports_billions"] * coverage
    return TariffPolicy(
        name="Trump Universal 10% Tariff",
        description=(
            "10% tariff on all imports outside the USMCA carve-out "
            "(~\\$2,349B base). Costs ~\\$1,700/household."
        ),
        tariff_rate_change=0.10,
        import_base_billions=effective_base,
        retaliation_export_base_billions=(
            TRADE_BASELINE["total_exports_billions"] * coverage
        ),
    )


def create_trump_china_60() -> TariffPolicy:
    """60% on Chinese goods, incremental over the duty already collected.

    Applied to the *whole* China base at the incremental rate rather than to
    half of it at a hand-set increment: a 60% tariff raises the rate on every
    Chinese good, by 60pp minus whatever Section 301 already collects on it,
    and Census puts that collected rate at 10.93% for 2024.
    """
    existing_tariff = TRADE_BASELINE["china_existing_avg_tariff"]
    return TariffPolicy(
        name="Trump 60% China Tariff",
        description=(
            "60% tariff on Chinese imports, incremental over the ~10.9% "
            "already collected (~\\$440B base)."
        ),
        tariff_rate_change=0.60 - existing_tariff,
        target_country="china",
        import_base_billions=TRADE_BASELINE["china_imports_billions"],
        retaliation_export_base_billions=TRADE_BASELINE["us_exports_to_china_billions"],
    )


def create_auto_tariff_25() -> TariffPolicy:
    """25% on the Section 232 vehicle and parts articles, net of US content.

    The base is CBO's own two article lists — ``autos.csv`` (62 HS-10 lines)
    and ``auto_parts.csv`` (316) — aggregated over CBO's own Census file, not
    the whole of HS 87. That matters in both directions: HS 87 carries
    tractors, trailers, motorcycles, bicycles and baby carriages that Section
    232 does not reach, while most of the parts list sits in chapters 40, 70,
    83, 84, 85 and 90, outside HS 87 altogether.

    The USMCA carve-out is CBO's too, and much smaller than the one it
    replaces. The March 2025 proclamation exempts the **US-content share** of a
    **qualifying** vehicle, not the whole import value, so CBO taxes Canadian
    and Mexican vehicles on ``1 - 0.50`` and ``1 - 0.35`` of the qualifying
    share (``code/tariffs.py:186-187``) and parts in full. That is $41.0B of
    carve-out against the roughly $186B a whole-value 48.42% exemption removed
    — and ``tariff_scoring_inputs.csv`` had already recorded, in that key's own
    source note, that the whole-value form over-stated it.
    """
    base = (
        TRADE_BASELINE["auto_imports_billions"]
        + TRADE_BASELINE["auto_parts_imports_billions"]
    )
    return TariffPolicy(
        name="25% Auto Tariff",
        description=(
            "25% tariff on the Section 232 vehicle and parts articles, "
            "incremental over the 1.84% they already collect and net of the "
            f"US content of USMCA-qualifying vehicles (~\\${base:,.0f}B base)."
        ),
        tariff_rate_change=0.25 - TRADE_BASELINE["auto_existing_avg_tariff"],
        target_sector="autos",
        import_base_billions=base,
    )


def create_steel_tariff_25(include_derivatives: bool = True) -> TariffPolicy:
    """25% on the Section 232 steel, aluminium and derivative articles.

    Both legs are now measured at the **article** level, off CBO's own HS-10
    Section 232 lists aggregated over CBO's own Census file, where they used to
    be whole HS chapters. The primary list (1,167 lines after CBO's own
    exclusion of auto parts) is $96.75B paying **4.64%** — far below the
    25%/10% statutory rates, because Canada, Mexico and Australia were exempted
    and the EU, UK, Japan, Brazil and South Korea traded under quotas or
    product exclusions. That collected rate, not the statutory one, is what a
    proposed 25% is incremental to.

    A **derivative** article is taxed on its metal *content*, which is what
    Proclamation 10896 says and what the module could not previously express.
    CBO's content shares are 0.75 of a high-content article and 0.25 of a
    low-content one, giving a taxed base of $122.60B paying 3.87%. The
    derivatives stay a separate schedule row because they collect a different
    duty from the primary base.

    **The chapter bracket this replaces was wrong at both ends.** Most of HS 73
    turns out to be *primary* Section 232 scope — 558 of the primary list's
    1,180 lines — so the old "floor" of HS 72 + HS 76 excluded it; and the
    derivative annex lives in chapters 82 to 95, which HS 73 does not contain,
    so the old "ceiling" was 2.5x too small. The measured base is 2.04x that
    ceiling.

    ``include_derivatives=False`` still returns the primary leg alone. It is
    now a genuine floor — the articles Section 232 reaches directly — rather
    than one end of a bracket built from the wrong chapters.
    """
    rows: list[ScheduleRow] = [
        (
            "Section 232 steel and aluminium articles",
            TRADE_BASELINE["steel_aluminum_imports_billions"],
            0.25 - TRADE_BASELINE["steel_aluminum_existing_avg_tariff"],
        )
    ]
    if include_derivatives:
        rows.append(
            (
                "Section 232 derivative articles (metal content)",
                TRADE_BASELINE["steel_derivative_imports_billions"],
                0.25 - TRADE_BASELINE["steel_derivative_existing_avg_tariff"],
            )
        )
    base = sum(row[1] for row in rows)
    return TariffPolicy(
        name="25% Steel/Aluminum Tariff",
        description=(
            "25% tariff on steel, aluminium and the Section 232 derivative "
            f"articles, incremental over the duty each base already collects "
            f"(~\\${base:,.0f}B base)."
        ),
        tariff_rate_change=0.25 - TRADE_BASELINE["steel_aluminum_existing_avg_tariff"],
        target_sector="steel",
        import_base_billions=base,
        rate_schedule=tuple(rows),
    )


def create_reciprocal_tariffs() -> TariffPolicy:
    """Executive Order 14257's schedule, partner by partner.

    The rate each partner faces is the EO's own formula — 2024 bilateral goods
    deficit over goods imports from that partner, halved, floored at 10% —
    applied to Census 2024 and with the Annex II sectors removed partner by
    partner. The reconstruction reproduces sixteen published Annex I rates to
    within about a point; see ``reciprocal_schedule.csv``.

    What this replaces is ``reciprocal_coverage_rate = 0.50``: a flat 20pp on
    half of goods imports, which no publisher scored and nobody proposed.
    """
    schedule = load_reciprocal_schedule()
    base = sum(row[1] for row in schedule)
    weighted = sum(b * r for _, b, r in schedule) / base if base else 0.0
    return TariffPolicy(
        name="Reciprocal Tariffs",
        description=(
            "Partner-specific reciprocal rates (EO 14257's own formula on "
            f"2024 Census bilateral trade: {weighted:.0%} average on "
            f"~\\${base:,.0f}B of covered imports, Annex II sectors and the "
            "USMCA partners excluded)."
        ),
        target_country="reciprocal_schedule",
        rate_schedule=schedule,
        retaliation_export_base_billions=(
            TRADE_BASELINE["total_exports_billions"] * base
            / TRADE_BASELINE["total_imports_billions"]
        ),
    )
