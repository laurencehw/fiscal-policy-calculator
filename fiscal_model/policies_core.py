"""
Core policy parameter definitions.
"""

import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from .spending_outlays import IMMEDIATE, OutlayProfile, get_outlay_profile

logger = logging.getLogger(__name__)

# Cap on the preferential-income correction. Even at the very top, some income
# is ordinary (wages, interest, non-qualified distributions); this prevents a
# pathological data point from zeroing out the base.
_MAX_PREFERENTIAL_SHARE = 0.55

#: The one default for :attr:`TaxPolicy.ordinary_income_base`, read by every
#: constructor that builds a rate change the user did not classify.
#:
#: ``True`` means the **ordinary** base: an ordinary-bracket rate change is
#: priced on the non-preferential share of marginal income, because it does not
#: reach long-term capital gains or qualified dividends. ``False`` means the
#: **AGI-inclusive** base, which a surtax stated on total income above a
#: threshold does reach.
#:
#: Ordinary is the default because it is the *validation manifest's* default:
#: :func:`fiscal_model.validation.core.create_policy_from_score` sets
#: ``ordinary_income_base = not score.agi_inclusive_base`` and
#: :class:`~fiscal_model.validation.cbo_scores.CBOScore` defaults
#: ``agi_inclusive_base`` to ``False``. Before 2026-09-09 this module's literal
#: said ``False`` while Tailor and the composer both said ordinary, so the same
#: specification returned two answers 1.89x apart depending on which surface
#: the user typed it into. The base is a fact about the policy, read off its
#: source document and never inferred from its shape - a rate change above a
#: threshold can be either, and the out-of-sample battery holds one of each.
#: See ``planning/lanes/HSA_h1_base_rule.md``.
DEFAULT_ORDINARY_INCOME_BASE = True

#: The two IRS SOI income columns a generic rate change can be priced on, and
#: the default, which is every policy's behaviour before 2026-09-10.
#:
#: This is **orthogonal** to :data:`DEFAULT_ORDINARY_INCOME_BASE`. That flag
#: answers "is the preferential (LTCG/QDIV) share removed from the base?"; this
#: one answers "which column *is* the base?". Both facts are read off the
#: source document and neither is inferred from the other: CBO's Option 46
#: states its surtax on **AGI**, and TPC's illustrative top-rate rows state
#: theirs on **taxable income that includes** the preferential portion. Before
#: this constant existed, one boolean carried both questions and the second one
#: always answered "taxable income", so an AGI surtax was priced by subtracting
#: an AGI threshold from an average of taxable income - a unit mismatch worth
#: 40% of the base at $20,000. See ``planning/lanes/HSB_h2b_agi_column.md``.
#:
#: Declared here rather than imported from
#: :mod:`fiscal_model.data.irs_soi`, which declares the same three: importing
#: that module at file scope would pull pandas into the app's import graph and
#: move the cold-start figures ``tests/test_cold_start_ordering.py`` pins, and
#: this module is on the landing page's path. ``tests/test_agi_income_measure.py``
#: fails if the two ever disagree, so the pair cannot drift.
INCOME_MEASURE_TAXABLE_INCOME = "taxable_income"
INCOME_MEASURE_AGI = "agi"
INCOME_MEASURES: tuple[str, ...] = (INCOME_MEASURE_TAXABLE_INCOME, INCOME_MEASURE_AGI)
DEFAULT_INCOME_MEASURE = INCOME_MEASURE_TAXABLE_INCOME

#: What happens to :attr:`TaxPolicy.affected_income_threshold` across the ten
#: years being scored. Three answers, and writing them down is most of the
#: value, because **the default was an unnamed assumption nobody could read off
#: the code**.
#:
#: ``"income"``
#:     The threshold rides the nominal-income index, which is what the engine
#:     has done since ``HSB_h2_base_growth.md`` shipped the base projection.
#:     Scaling the aggregate marginal income above a fixed nominal threshold by
#:     an index ``g`` is arithmetically identical to indexing the threshold by
#:     ``g`` too (that lane's section 1.4), so a user who types "\$400,000" into
#:     Tailor is answered about a threshold reaching **\$617,000** by FY2035.
#:     It is the default because it is today's arithmetic to the cent.
#: ``"statutory"``
#:     The threshold is a boundary the **law** sets, read per year and per
#:     filing status from CBO's own published schedule
#:     (:mod:`fiscal_model.cbo_tax_parameters`). Requires
#:     :attr:`TaxPolicy.threshold_bracket_index`.
#: ``"nominal"``
#:     The amount is fixed in the dollars of each year being scored - the
#:     literal reading of a typed figure, and the closed form of the
#:     "real bracket creep above a fixed nominal threshold" term H2 carried
#:     over. Reachable, measured, and deliberately **not** the default: making
#:     it one would move every generic preset and the whole Tailor surface on a
#:     lane whose gain is expressiveness.
#:
#: See ``planning/lanes/R4_parameter_schedule.md`` section 1.5.
THRESHOLD_INDEXATION_INCOME = "income"
THRESHOLD_INDEXATION_STATUTORY = "statutory"
THRESHOLD_INDEXATION_NOMINAL = "nominal"
THRESHOLD_INDEXATIONS: tuple[str, ...] = (
    THRESHOLD_INDEXATION_INCOME,
    THRESHOLD_INDEXATION_STATUTORY,
    THRESHOLD_INDEXATION_NOMINAL,
)
DEFAULT_THRESHOLD_INDEXATION = THRESHOLD_INDEXATION_INCOME


def ordinary_income_base_for_preset(preset_data: Mapping[str, object] | None) -> bool:
    """The base a catalog preset declares, or the shared default.

    A preset states ``agi_inclusive_base: True`` when its own source scores the
    reform on total income above a threshold — TPC's Warren surtax on AGI,
    Treasury's Medicare surcharge on wage *and* investment income. A preset that
    declares nothing is an ordinary-bracket rate change and takes
    :data:`DEFAULT_ORDINARY_INCOME_BASE`.

    One function rather than six copies of ``not preset.get(...)``: the composer,
    the API's preset route, the Tailor preset seed and the three comparison tabs
    all asked the same question, and nothing kept their answers in step.
    """
    if not preset_data:
        return DEFAULT_ORDINARY_INCOME_BASE
    declared = preset_data.get("agi_inclusive_base")
    if declared is None:
        return DEFAULT_ORDINARY_INCOME_BASE
    return not bool(declared)


def income_measure_for_preset(
    preset_data: Mapping[str, object] | None, *, preset_name: str | None = None
) -> str:
    """The IRS SOI income column a catalog preset's own source states.

    A preset declares ``income_measure: "agi"`` only where its source says AGI
    in as many words - TPC scores the Warren surtax on "AGI above $2 million".
    A preset that declares nothing takes :data:`DEFAULT_INCOME_MEASURE`, which
    is what every preset scored on before 2026-09-10.

    Declaring nothing is the right answer for two of the three surtax presets
    and for different reasons, both recorded in the catalog: Treasury's Medicare
    surcharge is stated on "investment + wage income", which is neither SOI
    column, and the millionaire surtax has no source document at all. A base
    that cannot be transcribed is not guessed at.

    One function rather than a `.get` at each of the six preset-construction
    sites, for the reason :func:`ordinary_income_base_for_preset` exists:
    nothing kept those six answers in step.

    A declared value is validated **here**, where the catalog entry is still in
    hand. Left to ``TaxPolicy.__post_init__`` a typo would surface as
    "income_measure must be ..." from six different call sites with no clue
    which preset carried it, and only on the surfaces that build a policy — the
    catalog itself would import clean.
    """
    if not preset_data:
        return DEFAULT_INCOME_MEASURE
    declared = preset_data.get("income_measure")
    if declared is None:
        return DEFAULT_INCOME_MEASURE
    measure = str(declared)
    if measure not in INCOME_MEASURES:
        raise ValueError(
            f"preset {preset_name or '<unnamed>'!r} declares "
            f"income_measure={declared!r}; expected one of "
            f"{', '.join(INCOME_MEASURES)}"
        )
    return measure


def preferential_income_share(
    threshold: float,
    total_marginal_income_billions: float,
    *,
    year: int | None = None,
) -> float:
    """Share of marginal income above ``threshold`` taxed at *preferential*
    rates (long-term capital gains), and therefore unaffected by an ordinary
    income-tax rate change.

    Sourced from :class:`CapitalGainsBaseline` (Tax Foundation realizations +
    IRS-SOI-derived share-above-threshold schedule). Qualified dividends are not
    separately modeled, so this is a conservative (slightly low) estimate.
    Returns 0.0 on any data error so scoring degrades to the legacy whole-base
    behavior rather than failing.
    """
    if total_marginal_income_billions <= 0 or threshold < 0:
        return 0.0
    try:
        from fiscal_model.data.capital_gains import CapitalGainsBaseline

        cg = CapitalGainsBaseline()
        base = cg.get_baseline_above_threshold_with_rate_method(
            year=year or 2023,
            threshold=max(threshold, 1.0),
        )
        cg_above_billions = float(base["net_capital_gain_billions"])
    except Exception as exc:
        logger.warning("preferential_income_share: cap-gains data unavailable (%s)", exc)
        return 0.0

    share = cg_above_billions / total_marginal_income_billions
    return float(max(0.0, min(_MAX_PREFERENTIAL_SHARE, share)))


class PolicyType(Enum):
    """Categories of fiscal policies."""

    INCOME_TAX = "income_tax"
    CORPORATE_TAX = "corporate_tax"
    PAYROLL_TAX = "payroll_tax"
    CAPITAL_GAINS_TAX = "capital_gains_tax"
    ESTATE_TAX = "estate_tax"
    EXCISE_TAX = "excise_tax"
    TAX_CREDIT = "tax_credit"
    TAX_DEDUCTION = "tax_deduction"
    DISCRETIONARY_DEFENSE = "discretionary_defense"
    DISCRETIONARY_NONDEFENSE = "discretionary_nondefense"
    MANDATORY_SPENDING = "mandatory_spending"
    INFRASTRUCTURE = "infrastructure"
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    MEDICAID = "medicaid"
    UNEMPLOYMENT = "unemployment"
    SNAP = "snap"
    OTHER_TRANSFER = "other_transfer"


@dataclass
class Policy:
    """Base class for fiscal policy proposals."""

    name: str
    description: str
    policy_type: PolicyType
    start_year: int = 2025
    duration_years: int = 10
    phase_in_years: int = 1
    sunset: bool = False

    def __post_init__(self):
        if self.duration_years <= 0:
            raise ValueError(f"duration_years must be positive, got {self.duration_years}")
        if self.phase_in_years < 1:
            raise ValueError(f"phase_in_years must be >= 1, got {self.phase_in_years}")
        if self.start_year < 2000 or self.start_year > 2100:
            raise ValueError(f"start_year must be between 2000 and 2100, got {self.start_year}")

    def get_phase_in_factor(self, year: int) -> float:
        """Calculate the phase-in factor for a given year."""
        if year < self.start_year:
            return 0.0

        years_since_start = year - self.start_year

        if self.sunset and years_since_start >= self.duration_years:
            return 0.0

        if self.phase_in_years <= 1:
            return 1.0

        return min(1.0, (years_since_start + 1) / self.phase_in_years)

    def is_active(self, year: int) -> bool:
        """Check if policy is active in a given year."""
        if year < self.start_year:
            return False
        return not (self.sunset and year >= self.start_year + self.duration_years)

    def scores_by_year(self) -> bool:
        """Whether this policy's static annual must be asked for **per year**.

        ``False`` means one annual answers the whole window, and the engine
        applies its growth and phase factors to that single figure. ``True``
        means the quantity genuinely differs by year - a base that is a path
        rather than a level, a cap whose bite moves against what it caps, a
        statutory boundary the law re-indexes - and the engine passes ``year``
        into :meth:`estimate_static_revenue_effect`.

        This exists because the engine had **two** year-indexed policy classes
        and no general concept, each bolted on as six lines of ``isinstance``
        (``planning/MODELING_IMPROVEMENT.md`` section 6.2 item 27, which names
        ``Policy.scores_by_year()`` as the remedy the third case should build
        rather than a third special case). Two classes in this module implement
        it: :class:`CapitalGainsPolicy`, whose realizations base is a flow off a
        projected stock, and :class:`TaxPolicy` with a re-indexed threshold.
        The five ``isinstance`` branches in
        :meth:`fiscal_model.scoring_engine.FiscalPolicyScorer._score_growth_tax_policy_year`
        live in five other modules and are a mechanical follow-up, not a
        different idea - see ``planning/lanes/R4_parameter_schedule.md``
        section 5.
        """
        return False


@dataclass
class TaxPolicy(Policy):
    """Tax policy proposal with detailed parameters."""

    rate_change: float = 0.0
    new_rate: float | None = None
    affected_income_threshold: float = 0.0
    affected_income_cap: float | None = None
    credit_amount: float = 0.0
    credit_refundable: bool = False
    deduction_amount: float = 0.0
    affected_taxpayers_millions: float = 0.0
    taxable_income_elasticity: float = 0.25
    labor_supply_elasticity: float = 0.1
    annual_revenue_change_billions: float | None = None
    avg_taxable_income_in_bracket: float = 0.0
    marginal_rate_before: float = 0.0
    data_year: int | None = None
    # When True, an *ordinary*-rate change is applied only to the non-preferential
    # share of marginal income — long-term capital gains and qualified dividends
    # (taxed at preferential rates) are excluded, since an ordinary-bracket rate
    # change does not touch them. Set False for AGI-inclusive surtaxes, which do
    # reach that income. The default is the module constant every constructor
    # reads, so the dataclass, Tailor, the composer, Ask and the API cannot each
    # carry their own answer. See ``DEFAULT_ORDINARY_INCOME_BASE``,
    # ``preferential_income_share`` and docs/METHODOLOGY.md (Static Scoring).
    ordinary_income_base: bool = DEFAULT_ORDINARY_INCOME_BASE
    # Which IRS SOI column supplies the base: ``"taxable_income"`` (the default,
    # and every policy's behaviour before 2026-09-10) or ``"agi"``. SOI Table
    # 1.1 rows are AGI size classes and publish BOTH columns, so a surtax whose
    # source states it on AGI - CBO Option 46's "a surtax of 1 percentage point
    # would be imposed on AGI above $20,000" - was being priced by subtracting
    # an AGI threshold from an average of taxable income. Read off the source
    # document, never inferred from the policy's shape, and orthogonal to
    # ``ordinary_income_base``: a rate change stated on taxable income can still
    # reach the preferential portion, which is what TPC's illustrative rows are.
    # See ``DEFAULT_INCOME_MEASURE`` and planning/lanes/HSB_h2b_agi_column.md.
    income_measure: str = DEFAULT_INCOME_MEASURE
    # Optional per-filing-status thresholds, keyed by
    # ``fiscal_model.data.irs_soi.FILING_STATUSES``. Statutory income-tax
    # boundaries are stated per status - CBO's Option 46 surtax at "$20,000 for
    # single filers and $40,000 for joint filers", the 2025 rate tables' 24%
    # bracket at $206,700 joint against $103,350 otherwise - and applying one
    # status's floor to all four is the largest single error in the
    # out-of-sample battery. A **partial** mapping is the natural shape: any
    # status not named falls back to ``affected_income_threshold``, so
    # ``{"joint": 40_000}`` against a $20,000 threshold *is* the option text.
    # ``None`` (the default) keeps the pooled single-threshold path, byte for
    # byte. See ``planning/lanes/W7_filing_status_split.md``.
    threshold_by_filing_status: dict[str, float] | None = None
    # What happens to the threshold across the ten years being scored. See
    # ``THRESHOLD_INDEXATIONS`` for the three answers and why the default is the
    # one it is. ``"income"`` is today's arithmetic to the cent, so every policy
    # that does not ask for something else is unaffected.
    threshold_indexation: str = DEFAULT_THRESHOLD_INDEXATION
    # Which statutory ordinary-income bracket (1-7) this policy's threshold is
    # the floor of. Required by, and only meaningful with,
    # ``threshold_indexation="statutory"``. It is the *index* that is declared
    # and the four dollar amounts per year that are read, because a bracket
    # boundary is one thing stated in four places and re-indexed annually: at
    # the CY2026 reversion on the February 2024 vintage, bracket 4's joint floor
    # falls 3.5% while its head-of-household floor rises 65.5%. Read off the
    # source's own words - "in the four highest brackets" is bracket 4 of seven
    # - and never from numeric proximity, which is a trap the data contains:
    # $20,000 IS ``tp_bracket_2_hoh`` in CY2033 on that vintage, and CBO's
    # Option 46 still means $20,000. See
    # ``fiscal_model.validation.core.STATUTORY_BRACKET_SCHEDULE_RULE``.
    threshold_bracket_index: int | None = None
    # Which baseline vintage's schedule to read - ``"cbo_feb_2024"``,
    # ``"cbo_jan_2025"``, ``"cbo_feb_2026"``. ``None`` takes
    # ``cbo_tax_parameters.DEFAULT_BASELINE_VINTAGE``, which is the vintage
    # ``CBOBaseline`` itself defaults to, so a policy built by Tailor, Ask,
    # Build or the API reads the law of the baseline it is scored against.
    # A vintage is not an option: current law differs between them, and it is
    # the whole point. February 2024 and January 2025 are pre-OBBBA and revert
    # to the 10/15/25/28/33/35/39.6 schedule in CY2026; February 2026 is
    # post-P.L. 119-21 and does not.
    threshold_schedule_vintage: str | None = None
    # Cache for the per-status path only. The pooled path re-derives its
    # marginal income on years 2-10 from ``avg_taxable_income_in_bracket``
    # minus one threshold, a quantity that does not exist once the four
    # statuses face different floors, so the first year's answer is carried
    # instead of silently recomputed the pooled way.
    _split_annual_revenue_billions: float | None = field(
        default=None, init=False, repr=False, compare=False
    )
    # Same cache, same reason, for the *pooled* AGI path. Years 2-10 of any SOI
    # policy fall out of ``_should_use_irs_data`` (year one populates
    # ``affected_taxpayers_millions``) and into the fallback branch, which
    # re-derives marginal income from ``avg_taxable_income_in_bracket`` - a
    # taxable-income quantity. Overwriting that field with an AGI average would
    # make the fallback right and every other reader of it wrong, including the
    # shipped caption that reconstructs what a preset used to print, so the
    # field keeps meaning taxable income and the AGI annual is carried instead.
    _agi_annual_revenue_billions: float | None = field(
        default=None, init=False, repr=False, compare=False
    )
    # Average AGI above the threshold, from the same SOI read, set only on the
    # pooled AGI path. It is the base actually priced there, and nothing else
    # records it: ``avg_taxable_income_in_bracket`` deliberately does not.
    _soi_avg_agi_in_bracket: float | None = field(
        default=None, init=False, repr=False, compare=False
    )
    # Total marginal income the last scoring run priced, in dollars. Recorded
    # by the per-status path only, whose total is a sum over four populations
    # facing four floors and therefore *cannot* be re-derived from a single
    # ``avg_taxable_income_in_bracket`` minus a single threshold. See
    # :meth:`marginal_income_dollars`.
    _split_marginal_income_dollars: float | None = field(
        default=None, init=False, repr=False, compare=False
    )
    # The base ``_ordinary_income_share`` was last measured on, in dollars.
    # The per-status path measures the preferential share on the **pooled**
    # base rather than the split one, so this is not always the quantity above.
    # See :meth:`preferential_share_of_base`.
    _preferential_base_dollars: float | None = field(
        default=None, init=False, repr=False, compare=False
    )
    # The IRS SOI **tax year** the base was actually read from, set only where
    # it was read. It is the anchor a ten-year score projects the base off:
    # SOI reports a dated year and the window prices ten later ones, so the
    # engine grows the annual by the ratio of the scored baseline's own nominal
    # income index between this year and the year being scored
    # (:meth:`fiscal_model.baseline.BaselineProjection.nominal_income_index`).
    # ``None`` for a caller-supplied base - an explicit
    # ``annual_revenue_change_billions``, or a hand-set
    # ``affected_taxpayers_millions`` / ``avg_taxable_income_in_bracket`` -
    # because such an aggregate carries a vintage this class has no field for
    # and is therefore used exactly as given. Same rule, and the same reason, as
    # ``CapitalGainsPolicy``'s ``baseline_realizations_billions``.
    _soi_base_tax_year: int | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self):
        super().__post_init__()
        if not (-1.0 <= self.rate_change <= 1.0):
            raise ValueError(f"rate_change must be between -1.0 and 1.0, got {self.rate_change}")
        if self.new_rate is not None and not (0.0 <= self.new_rate <= 1.0):
            raise ValueError(f"new_rate must be between 0.0 and 1.0, got {self.new_rate}")
        if self.affected_income_threshold < 0:
            raise ValueError(
                f"affected_income_threshold must be >= 0, got {self.affected_income_threshold}"
            )
        if self.taxable_income_elasticity < 0:
            raise ValueError(
                f"taxable_income_elasticity must be >= 0, got {self.taxable_income_elasticity}"
            )
        if self.labor_supply_elasticity < 0:
            raise ValueError(
                f"labor_supply_elasticity must be >= 0, got {self.labor_supply_elasticity}"
            )
        if self.affected_taxpayers_millions < 0:
            raise ValueError(
                f"affected_taxpayers_millions must be >= 0, got {self.affected_taxpayers_millions}"
            )

        if self.income_measure not in (INCOME_MEASURE_TAXABLE_INCOME, INCOME_MEASURE_AGI):
            raise ValueError(
                f"income_measure must be {INCOME_MEASURE_TAXABLE_INCOME!r} or "
                f"{INCOME_MEASURE_AGI!r}, got {self.income_measure!r}"
            )
        if self.income_measure == INCOME_MEASURE_AGI and self.ordinary_income_base:
            # AGI contains realized capital gains and qualified dividends by
            # construction, so removing the preferential share from an AGI base
            # subtracts income the surtax demonstrably reaches. The reverse is
            # NOT an invariant: ordinary_income_base=False on a taxable-income
            # base is a real classification (TPC's illustrative surtaxes), which
            # is exactly why these are two attributes and not one.
            # The message names the flag without writing a literal value beside
            # it: tests/test_base_rule_contract.py greps this tree for a
            # hard-coded base default and an error string is not an exemption
            # worth carving into that gate.
            raise ValueError(
                "income_measure='agi' requires the AGI-inclusive base, so "
                "ordinary_income_base must be off: AGI already contains the "
                "preferential (LTCG/QDIV) income the correction removes"
            )

        if self.threshold_indexation not in THRESHOLD_INDEXATIONS:
            raise ValueError(
                f"threshold_indexation must be one of "
                f"{', '.join(THRESHOLD_INDEXATIONS)}, got {self.threshold_indexation!r}"
            )
        if self.threshold_indexation == THRESHOLD_INDEXATION_STATUTORY:
            if self.threshold_bracket_index is None:
                raise ValueError(
                    "threshold_indexation='statutory' requires "
                    "threshold_bracket_index: the schedule is read by bracket "
                    "index, not by matching a dollar amount"
                )
        elif self.threshold_bracket_index is not None:
            # The reverse is not a harmless extra: a declared bracket that is
            # not read means somebody believes the schedule is in play and it
            # is not, which is the state a silent wrong answer lives in.
            raise ValueError(
                "threshold_bracket_index is only meaningful with "
                f"threshold_indexation='{THRESHOLD_INDEXATION_STATUTORY}', got "
                f"{self.threshold_indexation!r}"
            )
        if self.threshold_bracket_index is not None and not (
            1 <= int(self.threshold_bracket_index) <= 7
        ):
            raise ValueError(
                "threshold_bracket_index must be 1-7 (the statute defines seven "
                f"ordinary-income brackets), got {self.threshold_bracket_index!r}"
            )
        if (
            self.threshold_indexation != THRESHOLD_INDEXATION_INCOME
            and self.affected_taxpayers_millions > 0
        ):
            # A re-indexed threshold re-reads the SOI base every year, because
            # the floor it is measured above moves. A caller-supplied filer
            # count was measured above a threshold this class did not choose,
            # so there is nothing to re-read and the two cannot be combined.
            raise ValueError(
                f"threshold_indexation={self.threshold_indexation!r} re-reads the "
                "IRS SOI base once per scored year, so it cannot be combined "
                "with a caller-supplied affected_taxpayers_millions"
            )

        if self.threshold_by_filing_status is not None:
            if not self.threshold_by_filing_status:
                # An empty mapping declares nothing, so it takes the pooled path
                # rather than becoming a second way of saying the same thing.
                self.threshold_by_filing_status = None
            else:
                from fiscal_model.data.irs_soi import FILING_STATUSES

                unknown = sorted(set(self.threshold_by_filing_status) - set(FILING_STATUSES))
                if unknown:
                    raise ValueError(
                        f"unknown filing status(es) in threshold_by_filing_status: "
                        f"{', '.join(unknown)}; expected some of {', '.join(FILING_STATUSES)}"
                    )
                for status, value in self.threshold_by_filing_status.items():
                    if value < 0:
                        raise ValueError(
                            f"threshold_by_filing_status['{status}'] must be >= 0, got {value}"
                        )

        if self.affected_income_threshold > 10_000_000:
            logger.warning(
                f"Very high income threshold ${self.affected_income_threshold:,.0f} - few taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            logger.warning(
                f"ETI of {self.taxable_income_elasticity} exceeds typical range (0.1-0.4)"
            )

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
        *,
        year: int | None = None,
        threshold_deflator: float = 1.0,
    ) -> float:
        """Estimate static revenue effect before behavioral responses.

        ``year`` and ``threshold_deflator`` are passed by the engine only for a
        policy whose :meth:`scores_by_year` says the answer differs by year -
        which for this class means a re-indexed threshold. Omitted, the
        threshold is the one the policy carries and the answer is the same
        figure for every year, which is every policy's behaviour by default.

        ``threshold_deflator`` converts a threshold stated in the dollars of
        ``year`` into the dollars of the SOI tax year the base is measured in.
        It is **not** a second growth factor and must not be read as one: the
        engine multiplies the returned annual by the same ratio afterwards, so
        a threshold divided by ``g`` here and a base multiplied by ``g`` there
        are the two halves of one unit conversion. See
        ``planning/lanes/R4_parameter_schedule.md`` section 1.2, which records
        that omitting the deflation scores the one moving benchmark at 3.61%
        against the correct 17.86% - a number that looks right because two
        things are wrong.
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if use_real_data and self._should_use_irs_data():
            try:
                return self._estimate_from_irs_data(
                    baseline_revenue,
                    scored_year=year,
                    threshold_deflator=threshold_deflator,
                )
            except Exception as exc:
                logger.warning(f"Could not use IRS data for auto-population: {exc}")
                logger.warning("Falling back to manual parameters or heuristics")

        if (
            self.threshold_by_filing_status is not None
            and self._split_annual_revenue_billions is not None
        ):
            # Years 2-10 of a per-status policy: carry year one's answer. The
            # branch below cannot reproduce it, because it re-derives the base
            # from a single threshold.
            return self._split_annual_revenue_billions

        if (
            self.income_measure == INCOME_MEASURE_AGI
            and self._agi_annual_revenue_billions is not None
        ):
            # Years 2-10 of a pooled AGI policy, for the same reason: the branch
            # below re-derives marginal income from
            # ``avg_taxable_income_in_bracket``, which is the other column.
            return self._agi_annual_revenue_billions

        if (
            self.rate_change != 0
            and self.affected_taxpayers_millions > 0
            and self.avg_taxable_income_in_bracket > 0
        ):
            marginal_income = max(
                0,
                self.avg_taxable_income_in_bracket - self.affected_income_threshold,
            )

            if self.affected_income_threshold == 0:
                marginal_income = self.avg_taxable_income_in_bracket

            ordinary_share = self._ordinary_income_share(
                marginal_income * self.affected_taxpayers_millions * 1e6
            )

            revenue_change = (
                self.rate_change
                * marginal_income
                * ordinary_share
                * self.affected_taxpayers_millions
                * 1e6
            ) / 1e9
            return revenue_change

        if self.rate_change != 0:
            if self.affected_income_threshold > 0:
                if self.affected_income_threshold >= 500000:
                    affected_share = 0.20
                elif self.affected_income_threshold >= 200000:
                    affected_share = 0.40
                elif self.affected_income_threshold >= 100000:
                    affected_share = 0.55
                elif self.affected_income_threshold >= 50000:
                    affected_share = 0.75
                else:
                    affected_share = 0.90
            else:
                affected_share = 1.0

            avg_effective_rate = 0.18
            return baseline_revenue * affected_share * (self.rate_change / avg_effective_rate)

        if self.credit_amount != 0 and self.affected_taxpayers_millions > 0:
            return -self.credit_amount * self.affected_taxpayers_millions / 1e3

        if self.deduction_amount != 0 and self.affected_taxpayers_millions > 0:
            marginal_rate = self.marginal_rate_before if self.marginal_rate_before > 0 else 0.25
            return -self.deduction_amount * marginal_rate * self.affected_taxpayers_millions / 1e3

        return 0.0

    @property
    def soi_base_tax_year(self) -> int | None:
        """IRS SOI tax year this policy's base was read from, if it was read.

        ``None`` until :meth:`_estimate_from_irs_data` has run, and ``None``
        forever for a policy whose base the caller supplied. A caller reading
        this before the policy has been scored gets ``None``, which is correct:
        the base has no vintage yet because it has not been read yet.
        """
        return self._soi_base_tax_year

    def reindexes_threshold(self) -> bool:
        """Whether the threshold moves across the window on something other than income."""
        return self.threshold_indexation != THRESHOLD_INDEXATION_INCOME

    def scores_by_year(self) -> bool:
        """A re-indexed threshold is a per-year quantity; an income-indexed one is not.

        Under ``"income"`` the threshold rides the same index the base does, so
        one annual times that index answers every year and the engine takes the
        cheaper path. Under ``"statutory"`` or ``"nominal"`` the floor moves
        against the base, so the SOI read has to be repeated at a new threshold
        in each year being scored.
        """
        return self.reindexes_threshold()

    def resolve_soi_base_tax_year(self) -> int | None:
        """The SOI tax year this policy's base will be, or was, read from.

        :attr:`soi_base_tax_year` answers the same question only **after** a
        scoring run; the engine needs the answer *before* one, because the
        threshold deflator it passes into the first scored year is a ratio
        anchored on that year. Returns ``None`` where no SOI read will happen -
        a caller-supplied base, an explicit annual, or no SOI data on disk - so
        the caller's projection factor stays 1.0 exactly as it does today.
        """
        if self._soi_base_tax_year is not None:
            return int(self._soi_base_tax_year)
        if self.annual_revenue_change_billions is not None:
            return None
        if not self._should_use_irs_data():
            return None
        if self.data_year:
            return int(self.data_year)
        from fiscal_model.data import IRSSOIData

        available = IRSSOIData().get_data_years_available()
        return max(available) if available else None

    def _should_use_irs_data(self) -> bool:
        """Check if we should attempt to auto-populate from IRS SOI data.

        Threshold of 0 (all brackets) is allowed — that path scores a uniform
        rate change against total SOI taxable income rather than the legacy
        ``baseline × Δrate / 0.18`` heuristic.

        A **re-indexed** threshold keeps returning ``True`` after the first
        scored year, because the floor the base is measured above moves and the
        read has to be repeated. ``__post_init__`` refuses that combination with
        a caller-supplied filer count, so the only way to reach it is a base
        this class populated itself.
        """
        if self.rate_change == 0 or self.affected_income_threshold < 0:
            return False
        if self.affected_taxpayers_millions == 0:
            return True
        return self.reindexes_threshold() and self._soi_base_tax_year is not None

    def statutory_thresholds_for_year(self, year: int) -> dict[str, float]:
        """The four per-status floors this policy applies in ``year``, nominal.

        In the dollars of ``year`` itself, before any deflation onto the SOI
        base year. ``"statutory"`` reads CBO's published schedule at this
        policy's own :attr:`threshold_bracket_index`; ``"nominal"`` returns the
        policy's own amounts, which by definition do not move; ``"income"``
        never reaches here, because its threshold is not a per-year quantity.

        A year outside the edition's published range is **clamped to the
        nearest published year and logged**, rather than extrapolated: a
        schedule is law for the years the law is written for, and compounding a
        price index past the end of the table would be a projection wearing a
        statute's clothes. No window this repository scores reaches a clamp.
        """
        resolved = self.resolved_filing_status_thresholds()
        if self.threshold_indexation == THRESHOLD_INDEXATION_NOMINAL:
            return resolved

        from fiscal_model import cbo_tax_parameters

        vintage = self.threshold_schedule_vintage or cbo_tax_parameters.DEFAULT_BASELINE_VINTAGE
        published = cbo_tax_parameters.years_available(vintage)
        if not published:
            raise cbo_tax_parameters.TaxParameterError(
                f"no tax-parameter schedule transcribed for vintage {vintage!r}"
            )
        read_year = min(max(int(year), published[0]), published[-1])
        if read_year != int(year):
            logger.warning(
                "Tax-parameter schedule for %s covers CY%d-CY%d; CY%d clamped to CY%d",
                vintage, published[0], published[-1], int(year), read_year,
            )
        return cbo_tax_parameters.bracket_floors_by_status(
            vintage, int(self.threshold_bracket_index), read_year
        )

    def _deflated_thresholds(
        self, year: int | None, threshold_deflator: float
    ) -> dict[str, float] | None:
        """Per-status floors in SOI-base-year dollars, or ``None`` to keep today's path."""
        if not self.reindexes_threshold() or year is None:
            return None
        if threshold_deflator <= 0:
            # A degraded baseline carries no index. Fall back to the nominal
            # amounts rather than dividing by zero or silently scoring nothing.
            threshold_deflator = 1.0
        nominal = self.statutory_thresholds_for_year(int(year))
        return {status: value / threshold_deflator for status, value in nominal.items()}

    def _estimate_from_irs_data(
        self,
        baseline_revenue: float,
        *,
        scored_year: int | None = None,
        threshold_deflator: float = 1.0,
    ) -> float:
        """Auto-populate parameters from IRS SOI data and estimate revenue effect.

        ``year`` below is the IRS SOI **tax year** the base is read from;
        ``scored_year`` is the fiscal year being scored. The two are years of
        different things and the distinction is load-bearing, which is why they
        do not share a name.
        """
        _ = baseline_revenue
        from fiscal_model.data import IRSSOIData

        irs_data = IRSSOIData()
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError(
                "No IRS SOI data files found. "
                "See fiscal_model/data_files/irs_soi/README.md for download instructions."
            )

        year = self.data_year if self.data_year else max(available_years)
        logger.info(f"Auto-populating tax policy parameters from {year} IRS SOI data")

        # Whether this is the first scored year, captured before the line below
        # makes it look otherwise. A re-indexed policy runs this method once per
        # scored year, and the fields it records describe the policy's base
        # rather than one year of it, so they are written once.
        first_read = self._soi_base_tax_year is None

        # Record the vintage of the base before it is used, so the engine can
        # project it onto the years actually being scored. Set on both branches
        # below, which is why it is set once here.
        self._soi_base_tax_year = int(year)

        deflated = self._deflated_thresholds(scored_year, threshold_deflator)
        if deflated is not None:
            # A re-indexed threshold always takes the per-status path, even
            # where the four floors are equal: the schedule states four amounts
            # and PR #127's split is byte-identical to the pooled path when they
            # agree, so this costs nothing and keeps one code path.
            return self._estimate_from_irs_data_by_status(
                irs_data, year, thresholds=deflated, record=first_read
            )

        if self.threshold_by_filing_status is not None:
            return self._estimate_from_irs_data_by_status(irs_data, year)

        bracket_info = irs_data.get_filers_by_bracket(
            year=year,
            threshold=self.affected_income_threshold,
        )

        logger.info(
            f"  Affected filers: {bracket_info['num_filers']/1e6:.2f}M "
            f"(threshold: ${self.affected_income_threshold:,.0f})"
        )
        logger.info(f"  Avg taxable income: ${bracket_info['avg_taxable_income']:,.0f}")

        self.affected_taxpayers_millions = bracket_info["num_filers"] / 1e6
        self.avg_taxable_income_in_bracket = bracket_info["avg_taxable_income"]

        # SOI Table 1.1's rows are AGI size classes and it publishes both
        # columns, so a return is selected by its AGI on either path; what the
        # source decides is which quantity is measured *above* the floor. An
        # AGI-stated surtax subtracts an AGI threshold from an AGI average
        # rather than from an average of taxable income, which is the unit
        # mismatch this branch used to carry.
        if self.income_measure == INCOME_MEASURE_AGI:
            self._soi_avg_agi_in_bracket = bracket_info["avg_agi"]
            avg_income = bracket_info["avg_agi"]
        else:
            avg_income = bracket_info["avg_taxable_income"]

        marginal_income = max(0, avg_income - self.affected_income_threshold)

        if self.affected_income_threshold == 0:
            marginal_income = avg_income

        logger.info(f"  Avg total income ({self.income_measure}): ${avg_income:,.0f}")
        logger.info(
            f"  Marginal income above ${self.affected_income_threshold:,.0f}: ${marginal_income:,.0f}"
        )

        ordinary_share = self._ordinary_income_share(
            marginal_income * bracket_info["num_filers"], year=year
        )
        if ordinary_share < 1.0:
            logger.info(
                f"  Ordinary-income share (excl. preferential cap gains): {ordinary_share:.2f}"
            )

        revenue_change = (
            self.rate_change * marginal_income * ordinary_share * bracket_info["num_filers"]
        ) / 1e9

        if self.income_measure == INCOME_MEASURE_AGI:
            self._agi_annual_revenue_billions = revenue_change

        logger.info(
            f"  Estimated revenue change: ${revenue_change:,.1f}B "
            f"({self.rate_change*100:+.1f}pp rate change)"
        )

        return revenue_change

    def resolved_filing_status_thresholds(self) -> dict[str, float]:
        """The four per-status floors this policy applies.

        Any status ``threshold_by_filing_status`` does not name falls back to
        ``affected_income_threshold``, which is what makes a source that states
        two amounts expressible as the two amounts it states.
        """
        from fiscal_model.data.irs_soi import FILING_STATUSES

        declared = self.threshold_by_filing_status or {}
        return {
            status: float(declared.get(status, self.affected_income_threshold))
            for status in FILING_STATUSES
        }

    def _estimate_from_irs_data_by_status(
        self,
        irs_data,
        year: int,
        *,
        thresholds: dict[str, float] | None = None,
        record: bool = True,
    ) -> float:
        """Static revenue effect with the SOI base split by filing status.

        ``thresholds`` overrides the policy's own floors, and is how a
        re-indexed threshold enters: the caller has already read the schedule
        for the year being scored and deflated it into this SOI tax year's
        dollars. ``record=False`` suppresses the fields that describe *the
        policy's* base rather than one year of it, so a policy scored ten times
        reports its first year's filer count instead of its tenth.
        """
        if thresholds is None:
            thresholds = self.resolved_filing_status_thresholds()
        # The income measure is applied INSIDE the split - each status's own
        # marginal AGI above its own floor - not to the pooled aggregate
        # afterwards. The two are not the same number and they do not even move
        # the same way: at Option 46's floors the split AGI ratio is 1.4052
        # where the pooled one is 1.3820, and at the 2pp alternative's it is
        # 1.2535 where the pooled one is 1.3094.
        split = irs_data.get_filers_by_status_thresholds(
            year=year, thresholds=thresholds, income_measure=self.income_measure
        )
        marginal_income = split["marginal_income_dollars"]

        # The preferential-income correction is measured on the POOLED base at
        # this policy's own ``affected_income_threshold`` and then applied to
        # the split base. The capital-gains series behind
        # ``preferential_income_share`` has no filing-status dimension, so
        # re-deriving the ratio against a split denominator would remove the
        # same joint returns twice - once from the base, and again as their
        # gains. See planning/lanes/W7_filing_status_split.md section 2.3.
        pooled = irs_data.get_filers_by_bracket(
            year=year,
            threshold=self.affected_income_threshold,
        )
        pooled_avg = pooled["avg_taxable_income"]
        pooled_marginal_per_return = (
            pooled_avg
            if self.affected_income_threshold == 0
            else max(0.0, pooled_avg - self.affected_income_threshold)
        )
        ordinary_share = self._ordinary_income_share(
            pooled_marginal_per_return * pooled["num_filers"], year=year
        )

        revenue_change = self.rate_change * marginal_income * ordinary_share / 1e9

        if record:
            self.affected_taxpayers_millions = split["num_filers"] / 1e6
            self.avg_taxable_income_in_bracket = split["avg_taxable_income"]
            # A sum over four populations facing four floors, so it is not
            # ``(avg - threshold) x filers`` and must be carried rather than
            # re-derived. See :meth:`marginal_income_dollars`.
            self._split_marginal_income_dollars = float(marginal_income)
            self._split_annual_revenue_billions = revenue_change

        logger.info(
            "  Filing-status split: %s",
            ", ".join(
                f"{status} >${thresholds[status]:,.0f}: "
                f"{split['by_status'][status]['num_filers'] / 1e6:.2f}M filers, "
                f"${split['by_status'][status]['marginal_income_dollars'] / 1e9:,.1f}B"
                for status in thresholds
            ),
        )
        logger.info(
            f"  Estimated revenue change: ${revenue_change:,.1f}B "
            f"({self.rate_change*100:+.1f}pp rate change, filing-status split)"
        )
        return revenue_change

    def marginal_income_dollars(self) -> float:
        """Total marginal income this rate change is priced on, in dollars.

        The pooled identity is ``(avg_taxable_income_in_bracket − threshold) ×
        filers``, with the threshold dropping out at zero — the same arithmetic
        the three scoring branches perform. The **per-status** path cannot be
        written that way: four populations face four floors, so its total is a
        sum rather than a difference of averages, and it records that total
        during scoring for this method to return (see
        ``planning/lanes/W7_filing_status_split.md``).

        Zero before the policy has been scored, when neither the filer count
        nor the average income has been auto-populated yet.
        """
        if self._split_marginal_income_dollars is not None:
            return float(self._split_marginal_income_dollars)
        avg = float(self.avg_taxable_income_in_bracket)
        threshold = float(self.affected_income_threshold)
        if avg <= 0:
            return 0.0
        per_return = avg if threshold == 0 else max(0.0, avg - threshold)
        return per_return * float(self.affected_taxpayers_millions) * 1e6

    def preferential_share_of_base(
        self, *, year: int | None = None, base_dollars: float | None = None
    ) -> float:
        """Preferentially taxed share of this policy's marginal income.

        The question :meth:`_ordinary_income_share` answers *for scoring*, asked
        without the ``ordinary_income_base`` flag in the way. That distinction
        matters to any caller that wants to **compare** the two bases rather
        than apply one: the scoring helper short-circuits to 1.0 on an
        AGI-inclusive policy, which is the right answer there and reports "no
        difference" here.

        Measured on the base the scoring run actually used, which for the
        per-status path is the **pooled** base at this policy's own threshold —
        the capital-gains series has no filing-status dimension, so re-deriving
        the ratio against a split denominator would remove the same joint
        returns twice. Falls back to :meth:`marginal_income_dollars` for a
        policy that has not been scored.

        ``base_dollars`` overrides the recorded base. A policy scored on SOI's
        **AGI** column records that base, but a caption reporting the
        base-flag move *on the taxable column it was made on* needs the share
        of the taxable-column base — :meth:`marginal_income_dollars`, which
        keeps meaning taxable income on every path — and passes it here.

        Returns 0.0 when there is no preferential income to remove: a
        non-income-tax policy, or a base of zero.
        """
        if self.policy_type != PolicyType.INCOME_TAX:
            return 0.0
        base = base_dollars if base_dollars is not None else self._preferential_base_dollars
        if base is None:
            base = self.marginal_income_dollars()
        if base <= 0:
            return 0.0
        return preferential_income_share(
            self.affected_income_threshold,
            base / 1e9,
            year=year if year is not None else self.data_year,
        )

    def _ordinary_income_share(
        self, total_marginal_income_dollars: float, *, year: int | None = None
    ) -> float:
        """Fraction of marginal income subject to an *ordinary* rate change.

        Returns 1.0 (legacy whole-base behavior) unless ``ordinary_income_base``
        is set and this is an income-tax policy, in which case the preferentially
        taxed (long-term capital gains) share is removed.

        Records the base it was asked about so :meth:`preferential_share_of_base`
        can answer the same question afterwards without re-deriving it — which
        is what a fourth hand-written copy of the identity would have to do, and
        the per-status path cannot be re-derived that way at all.
        """
        self._preferential_base_dollars = float(total_marginal_income_dollars)
        if not self.ordinary_income_base:
            return 1.0
        if self.policy_type != PolicyType.INCOME_TAX:
            return 1.0
        pref = preferential_income_share(
            self.affected_income_threshold,
            total_marginal_income_dollars / 1e9,
            year=year if year is not None else self.data_year,
        )
        return 1.0 - pref

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """Behavioral revenue offset under standard ETI methodology.

        Returns a SIGNED value with the same sign as ``static_effect`` so the
        engine's ``deficit_after = static_deficit + behavioral`` (where
        ``static_deficit = -static_revenue``) shrinks the magnitude of the
        revenue change in both directions: erodes the gain on a tax increase
        and recovers some revenue on a tax cut. Magnitude follows the
        Saez-style 0.5·ETI·|static| convention.
        """
        return static_effect * self.taxable_income_elasticity * 0.5

    def validate_inputs(self) -> list[str]:
        """Validate inputs and return warning strings for unusual parameters."""
        warnings = []

        if self.affected_income_threshold > 10_000_000:
            warnings.append(
                f"Very high income threshold (${self.affected_income_threshold:,.0f}): "
                "only a small fraction of taxpayers affected"
            )

        if self.taxable_income_elasticity > 0.5:
            warnings.append(
                f"High ETI ({self.taxable_income_elasticity:.2f}): "
                "typical range is 0.1-0.4; consider if this is intentional"
            )

        if self.rate_change > 0.2:
            warnings.append(
                f"Large rate increase ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly restrictive"
            )

        if self.rate_change < -0.2:
            warnings.append(
                f"Large rate decrease ({self.rate_change*100:+.1f}pp): "
                "verify this policy is intended to be highly stimulative"
            )

        if (
            self.rate_change != 0
            and self.affected_income_threshold == 0
            and self.affected_taxpayers_millions == 0
            and self.avg_taxable_income_in_bracket == 0
        ):
            warnings.append(
                "Rate change specified but no population data provided: "
                "cannot estimate revenue impact accurately. "
                "Consider providing affected_taxpayers_millions or avg_taxable_income_in_bracket"
            )

        return warnings


@dataclass
class CapitalGainsPolicy(TaxPolicy):
    """Capital gains policy: a semi-log realizations response on a stock of
    accrued gains, with step-up at death as an escape from that stock.

    **The response is to the tax rate, not to the net-of-tax rate.** The
    capital-gains realization literature reports an elasticity defined as the
    percentage change in realizations over the percentage change in the *tax
    rate* (CRS R48562, *Boundaries on the Long-Run Realization Response to
    Changes in Capital Gains Taxes*, 2025, pp. 1 and 13), behind which sits a
    semi-log realizations function ``R = B exp(-b t)``.  So::

        R1 = R0 * exp(-b * (tau1 - tau0))       b = elasticity / reference rate

    Two properties come free with that form and neither is a second parameter.
    The implied elasticity ``e(t) = b*t`` **rises with the rate**, so the top
    bracket responds more than the 15 percent bracket to the same
    percentage-point change; and there is a revenue-maximizing rate at
    ``tau* = 1/b``.

    **Frozen elasticities.** Dowd, McClelland & Muthitacharoen (2015),
    *New Evidence on the Tax Elasticity of Capital Gains*, National Tax Journal
    68(3): persistent -0.72, transitory -1.2, both at the 22 percent reference
    rate CRS states its Table 4 estimates are adjusted to.  They are stored
    here as **magnitudes** - 0.72 and 1.20 - because the sign already lives in
    ``exp(-b * delta_tau)``; a rate rise cuts realizations either way.  That
    gives
    ``b = 3.273`` and ``tau* = 30.6%``; JCT's own working coefficient is 3.1
    (CRS R48562 p. 8) and Treasury's is 0.72 at 22 percent, the same as DMM's.
    Agersnap & Zidar (2021) estimate a much lower -0.3 to -0.5 and imply a
    higher revenue-maximizing rate; they are named here as the alternative and
    are deliberately **not** used - one frozen set, per owner Decision 3 of
    ``planning/MODELING_IMPROVEMENT.md``.

    The transitory elasticity is a *retiming* response, so it applies in the
    enactment year only, and only to the share of the base that has a timing
    margin: realized long-term gains, not qualified dividends or capital gain
    distributions, which a taxpayer cannot choose when to receive.

    **The base is a dated flow and is projected across the window.**  SOI
    reports realizations for a tax year; a ten-year score prices ten later
    years.  Realizations are a flow off the accrued-gains stock at the observed
    hazard - ``R = h * A`` - so the flow grows at the same rate the stock
    already grows at (:meth:`realizations_projection_factor`), and holding it
    flat instead would assert a hazard falling 5.8 percent a year.  No new
    constant enters: both ``h`` and the growth rate are already read from
    ``accrued_gains_parameters.csv``.  The projection applies only to the
    SOI-populated base, whose tax year is known; a caller who supplies
    ``baseline_realizations_billions`` supplies an aggregate whose vintage this
    class has no field for, so that base is used exactly as given.

    **Lock-in** is not a multiplier.  A share ``omega = m/(h+m)`` of the accrued
    gains stock leaves it at death rather than by sale, where ``h`` is the
    observed realization hazard and ``m`` the mortality-weighted exit rate.
    While step-up is available those gains are never taxed, so the price of
    realizing now is ``tau*(1 - (1-omega)*d)`` against ``tau*(1 - d)`` once
    death is a realization event, with ``d`` discounting the deferral over the
    expected holding horizon ``1/(h+m)``.  DMM estimated under current law, so
    the literature ``b`` is the with-step-up value and the without-step-up
    value is the smaller one that ratio implies.  Lower realizations also let
    the stock accumulate, which feeds back into later realizations and into the
    flow of gains transferred at death; that is tracked as a ratio to the
    baseline stock so no growth rate is introduced into the realizations flow.

    **The death channel is not the whole flow of gains at death.**  Every
    published realization-at-death proposal states reliefs, and
    :meth:`reachable_gains_per_decedent` prices the ones that bite on a base
    measured as unrealized gains: the charitable exclusion, section 121 on the
    principal residence, and - where the design offers it - deferral of tax on
    a family-owned and -operated business until the interest is sold.  Two more
    reliefs those proposals state, the spousal carry-over and the exclusion for
    tangible personal property, remove nothing from this base because Poterba &
    Weisbenner's flow already excludes inter-spousal transfers and assigns no
    accrued gain to vehicles, bonds or collectibles; deducting either would be
    a double count.  Gains at death then respond to a change in *their* rate
    with the **persistent** coefficient only
    (:meth:`death_response_coefficient`) - death cannot be retimed, so the
    transitory term has no place - and the tax induces further charitable
    substitution at the Bakija-Gale-Slemrod price elasticity.

    **Every one of those reliefs is a function of how big the estate is**, and
    since Wave 7 they are read at the estate's own size rather than at one of
    five group means: :meth:`CapitalGainsBaseline.decedent_classes` integrates
    over a piecewise-Pareto size distribution of net worth at death, so a
    per-donor exclusion bites on a distribution instead of removing a whole
    class at once.  The level is unchanged - it is still Poterba & Weisbenner's
    flow - and so is the decedent headcount, which remains the coarsest thing
    in the channel (``planning/lanes/W7_decedent_ladder.md`` §7).
    """

    baseline_capital_gains_rate: float = 0.20
    baseline_realizations_billions: float = 0.0
    #: Dowd, McClelland & Muthitacharoen (2015), at ``elasticity_reference_rate``.
    persistent_elasticity: float = 0.72
    transitory_elasticity: float = 1.20
    #: The tax rate the frozen elasticities are evaluated at (CRS R48562 Table 4).
    elasticity_reference_rate: float = 0.22
    #: Constant-elasticity override, used when ``use_time_varying_elasticity``
    #: is off; interpreted the same way, as a tax-rate elasticity at the
    #: reference rate.
    realization_elasticity: float = 0.5
    use_time_varying_elasticity: bool = True
    step_up_at_death: bool = True
    eliminate_step_up: bool = False
    step_up_exemption: float = 1_000_000
    #: Whether the score includes the gains-at-death channel.  A benchmark that
    #: scores only the rate change of a combined proposal sets this False; it
    #: is a statement about the policy's scope, not a behavioural parameter.
    score_gains_at_death: bool = True
    #: Discount rate on deferred realization, used only to price the lock-in
    #: wedge between the with- and without-step-up worlds.
    deferral_discount_rate: float = 0.04
    #: Whether the death channel applies the carve-outs every published
    #: realization-at-death proposal states.  A caller that wants the bare
    #: "every dollar of accrued gain, taxed" identity turns it off; nothing in
    #: the validation battery does.
    apply_death_carveouts: bool = True
    #: 26 U.S.C. 121(b)(1): $250,000 of gain on a principal residence, per
    #: person.  Both Green Books preserve it and make it portable to a
    #: surviving spouse ($500,000 per couple); the per-person figure is what a
    #: single decedent's final return can use.
    section_121_exclusion: float = 250_000.0
    #: Whether tax on the appreciation of family-owned and -operated businesses
    #: is deferred until the interest is sold.  Stated by both Green Books and
    #: by neither CBO budget option, so it is a **design** switch, not a
    #: behavioural parameter: see ``validation/core.py``'s
    #: ``GREEN_BOOK_DEATH_DESIGN_RULE``.  Off by default, so a policy scores the
    #: bare construction unless its source states the election.
    defer_family_business_gains: bool = False
    #: Price elasticity of charitable bequests, as a magnitude.  Bakija, Gale &
    #: Slemrod (2003), *Charitable Bequests and Taxes on Inheritances and
    #: Estates*, NBER WP 9661 / AEA Papers & Proceedings, Table 1,
    #: specification (a).  Their most robust specification (d) reports -2.142
    #: and Joulfaian (2000) reports -0.74; (a) is the smallest magnitude in the
    #: frozen paper's own table and is taken for that reason, since a larger
    #: one moves every step-up-elimination score further down.
    charitable_bequest_price_elasticity: float = 1.617

    def __post_init__(self):
        super().__post_init__()
        if not (0 <= self.baseline_capital_gains_rate <= 1):
            raise ValueError(
                "baseline_capital_gains_rate must be between 0 and 1, "
                f"got {self.baseline_capital_gains_rate}"
            )
        if self.persistent_elasticity < 0:
            raise ValueError(
                f"persistent_elasticity must be >= 0, got {self.persistent_elasticity}"
            )
        if self.transitory_elasticity < 0:
            raise ValueError(
                f"transitory_elasticity must be >= 0, got {self.transitory_elasticity}"
            )
        if not (0 < self.elasticity_reference_rate < 1):
            raise ValueError(
                "elasticity_reference_rate must be in (0, 1), "
                f"got {self.elasticity_reference_rate}"
            )
        if self.realization_elasticity < 0:
            raise ValueError(
                f"realization_elasticity must be >= 0, got {self.realization_elasticity}"
            )
        if self.deferral_discount_rate < 0:
            raise ValueError(
                f"deferral_discount_rate must be >= 0, got {self.deferral_discount_rate}"
            )
        if self.section_121_exclusion < 0:
            raise ValueError(
                f"section_121_exclusion must be >= 0, got {self.section_121_exclusion}"
            )
        if self.charitable_bequest_price_elasticity < 0:
            raise ValueError(
                "charitable_bequest_price_elasticity must be >= 0 (it is a "
                f"magnitude), got {self.charitable_bequest_price_elasticity}"
            )
        # Whether the caller supplied the base themselves.  ``get_brackets``
        # overwrites the field once it auto-populates, so the question cannot
        # be asked afterwards - and it decides whether the base carries a known
        # tax year and can therefore be projected.
        self._supplied_realizations = float(self.baseline_realizations_billions) > 0
        self._bracket_cache = None
        self._baseline_cache = None

    # ------------------------------------------------------------------
    # Baseline data
    # ------------------------------------------------------------------

    def _data_year(self, baseline) -> int:
        if self.data_year:
            return int(self.data_year)
        return max(baseline.available_years())

    def _baseline_source(self):
        if self._baseline_cache is None:
            from fiscal_model.data import CapitalGainsBaseline

            self._baseline_cache = CapitalGainsBaseline()
        return self._baseline_cache

    def get_brackets(self, use_real_data: bool = True) -> list:
        """Realizations facing this policy, grouped by the rate they face.

        A caller that set ``baseline_realizations_billions`` explicitly - every
        calibrated validation scenario does - gets that single aggregate priced
        at ``baseline_capital_gains_rate``, so those cases are unaffected by
        the SOI bracket table.
        """
        from fiscal_model.data.capital_gains import GainsBracket

        if self._bracket_cache is not None:
            return self._bracket_cache

        if float(self.baseline_realizations_billions) > 0 or not use_real_data:
            realized = float(self.baseline_realizations_billions)
            if realized <= 0:
                raise ValueError(
                    "baseline_realizations_billions must be > 0 for CapitalGainsPolicy "
                    "(set it manually or enable real-data auto-population)."
                )
            self._bracket_cache = [
                GainsBracket(
                    statutory_rate=float(self.baseline_capital_gains_rate),
                    niit_rate=0.0,
                    realizations_billions=realized,
                    tax_billions=realized * float(self.baseline_capital_gains_rate),
                    long_term_share=1.0,
                )
            ]
            return self._bracket_cache

        source = self._baseline_source()
        year = self._data_year(source)
        brackets = source.get_brackets_above_threshold(
            year=year, threshold=float(self.affected_income_threshold)
        )
        if not brackets:
            raise ValueError(
                "No capital gains realizations above threshold "
                f"{self.affected_income_threshold:,.0f} in tax year {year}"
            )
        realized = sum(bracket.realizations_billions for bracket in brackets)
        weighted = sum(
            bracket.realizations_billions * bracket.effective_rate for bracket in brackets
        )
        # Keep the aggregate fields in step so callers that read them - the
        # validation reporter, the UI - describe the base that was used.
        self.baseline_realizations_billions = realized
        self.baseline_capital_gains_rate = weighted / realized if realized > 0 else 0.0
        self._bracket_cache = brackets
        return brackets

    def _reform_rate(self, bracket) -> float:
        """Rate facing one bracket after the reform."""
        if self.new_rate is not None:
            return float(self.new_rate) + bracket.niit_rate
        return float(bracket.statutory_rate + self.rate_change + bracket.niit_rate)

    def _reform_capital_gains_rate(self) -> float:
        """Aggregate reform rate, for callers that want a single number."""
        if self.new_rate is not None:
            return float(self.new_rate)
        return float(self.baseline_capital_gains_rate + self.rate_change)

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def realizations_projection_factor(self, year: int | None) -> float:
        """Growth of the realizations base from its SOI tax year to ``year``.

        ``1.0`` when the year is not known, when the caller supplied the base,
        or when the accrued-gains parameters are unavailable, so the module
        degrades to the flat flow it used before rather than failing.
        """
        if year is None or self._supplied_realizations:
            return 1.0
        try:
            source = self._baseline_source()
            tax_year = source._resolve_year(self._data_year(source))
            return source.realizations_projection_factor(tax_year, int(year))
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning(
                "realizations_projection_factor: data unavailable (%s)", exc
            )
            return 1.0

    def lock_in_wedge(self) -> float:
        """Ratio of the realization price with step-up to the price without.

        ``1.0`` when the accrued-gains stock is unavailable, so the module
        degrades to "step-up makes no difference" rather than failing.
        """
        try:
            source = self._baseline_source()
            year = self._data_year(source)
            hazard = source.realization_hazard(year)
            death = source.death_exit_rate()
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("lock_in_wedge: accrued-gains data unavailable (%s)", exc)
            return 1.0

        exit_rate = hazard + death
        if exit_rate <= 0 or death <= 0:
            return 1.0
        escape_share = death / exit_rate
        horizon = 1.0 / exit_rate
        discount = 1.0 / (1.0 + self.deferral_discount_rate) ** horizon
        price_without = 1.0 - discount
        if price_without <= 0:
            return 1.0
        price_with = 1.0 - (1.0 - escape_share) * discount
        return price_with / price_without

    def semi_log_coefficient(
        self, years_since_start: int = 0, long_term_share: float = 1.0
    ) -> float:
        """``b`` in ``R = B exp(-b t)`` for a given year of the window."""
        reference = float(self.elasticity_reference_rate)
        if self.use_time_varying_elasticity:
            persistent = float(self.persistent_elasticity)
            transitory = float(self.transitory_elasticity)
        else:
            persistent = float(self.realization_elasticity)
            transitory = 0.0

        coefficient = persistent / reference
        if years_since_start <= 0 and transitory > 0:
            # The transitory response is retiming around the effective date and
            # is exhausted after it, and only gains a taxpayer chooses when to
            # realize have a timing margin.
            coefficient += (transitory / reference) * max(0.0, min(1.0, long_term_share))

        if self.eliminate_step_up:
            wedge = self.lock_in_wedge()
            if wedge > 0:
                coefficient /= wedge
        return coefficient

    def _realizations_ratio(self, bracket, years_since_start: int) -> float:
        """``R1/R0`` for one bracket in a given year of the window."""
        delta = self._reform_rate(bracket) - bracket.effective_rate
        coefficient = self.semi_log_coefficient(
            years_since_start=years_since_start,
            long_term_share=bracket.long_term_share,
        )
        return math.exp(-coefficient * delta)

    def stock_ratio(self, years_since_start: int, use_real_data: bool = True) -> float:
        """Reform accrued-gains stock over the baseline stock, in ``t`` years.

        Realizations that do not happen stay in the stock, which then supplies
        later realizations and a larger flow of gains transferred at death.
        Expressed as a ratio so the baseline's own growth cancels and no growth
        rate enters the realizations flow.
        """
        if years_since_start <= 0:
            return 1.0
        try:
            source = self._baseline_source()
            year = self._data_year(source)
            hazard = source.realization_hazard(year)
            death = source.death_exit_rate()
            growth = source._parameters["household_net_worth_growth_rate"]
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("stock_ratio: accrued-gains data unavailable (%s)", exc)
            return 1.0

        brackets = self.get_brackets(use_real_data=use_real_data)
        realized = sum(bracket.realizations_billions for bracket in brackets)
        if realized <= 0 or hazard <= 0:
            return 1.0
        # Permanent hazard response only: the transitory term is a retiming,
        # so it does not change the stock's steady drift.
        reform_realized = sum(
            bracket.realizations_billions * self._realizations_ratio(bracket, 1)
            for bracket in brackets
        )
        # ``hazard`` is national - all SOI realizations over the whole accrued-
        # gains stock - while ``brackets`` is only the slice a thresholded
        # policy reaches. Applying the slice's response to the whole hazard
        # would let a $1M+ proposal slow every taxpayer's realizations. The
        # gains outside the slice keep realizing at the baseline rate, and the
        # slice's share of national realizations stands in for its share of the
        # stock, which SOI does not report.
        national = sum(
            bracket.realizations_billions
            for bracket in source.get_brackets_above_threshold(
                year, 0.0, with_timing_share=False
            )
        )
        affected_share = min(1.0, realized / national) if national > 0 else 1.0
        response = reform_realized / realized
        reform_hazard = hazard * (1.0 - affected_share + affected_share * response)

        ratio = 1.0
        for _ in range(years_since_start):
            inflow = hazard + death
            outflow = (reform_hazard + death) * ratio
            ratio += (inflow - outflow) / (1.0 + growth)
        return max(0.0, ratio)

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def scores_by_year(self) -> bool:
        """Always: the realizations base is a flow off a projected stock.

        This class was the engine's first year-indexed case and was expressed
        as ``isinstance(policy, CapitalGainsPolicy)`` in
        :meth:`~fiscal_model.scoring_engine.FiscalPolicyScorer._score_tax_policy`
        until the schedule lane needed a second one in the same method. The
        behaviour is unchanged - the engine asks the same question and gets the
        same answer - but it now asks it of the policy rather than of the type.
        """
        return True

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
        year: int | None = None,
        *,
        threshold_deflator: float = 1.0,
    ) -> float:
        """Static effect holding realizations fixed, summed over brackets.

        ``year`` is the year being scored, which the base is projected to; the
        engine passes it for a capital-gains policy and nothing else.  Omitted,
        the base stays at its SOI level, which is what a caller asking for the
        data-year identity wants.

        ``threshold_deflator`` is accepted and ignored. This class prices a
        rate change over published bracket rows rather than a base measured
        above a threshold, so there is no statutory floor to re-index; the
        parameter is in the signature because the engine now asks every
        :meth:`scores_by_year` policy the same question and a class that
        narrowed the signature would fail on the call rather than on a claim.
        """
        _ = baseline_revenue
        _ = threshold_deflator
        brackets = self.get_brackets(use_real_data=use_real_data)
        factor = self.realizations_projection_factor(year)
        total = 0.0
        for bracket in brackets:
            tau0 = bracket.effective_rate
            tau1 = self._reform_rate(bracket)
            if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
                raise ValueError(
                    "Capital gains rates must be in [0, 1) for CapitalGainsPolicy"
                )
            total += (tau1 - tau0) * bracket.realizations_billions * factor
        return total

    def estimate_behavioral_offset(
        self,
        static_effect: float,
        years_since_start: int = 0,
        use_real_data: bool = True,
        phase: float = 1.0,
    ) -> float:
        """Behavioral offset from the realizations response.

        ``static_effect`` is not read: the offset is rebuilt bracket by bracket
        because each bracket faces its own price. ``phase`` carries the
        engine's phase-in factor, so a policy that phases its rate change in
        over several years phases the response in with it rather than applying
        the full-strength offset against a partial static effect.
        """
        _ = static_effect
        brackets = self.get_brackets(use_real_data=use_real_data)
        stock = self.stock_ratio(years_since_start, use_real_data=use_real_data)
        # The same projection the static leg applies, so the two stay a
        # decomposition of the score rather than one absorbing the other.
        factor = self.realizations_projection_factor(
            int(self.start_year) + int(years_since_start)
        )

        delta_static = 0.0
        delta_total = 0.0
        for bracket in brackets:
            tau0 = bracket.effective_rate
            tau1 = self._reform_rate(bracket)
            if not (0 <= tau0 < 1) or not (0 <= tau1 < 1):
                raise ValueError(
                    "Capital gains rates must be in [0, 1) for CapitalGainsPolicy"
                )
            r0 = bracket.realizations_billions * factor
            r1 = r0 * self._realizations_ratio(bracket, years_since_start) * stock
            delta_static += (tau1 - tau0) * r0
            delta_total += tau1 * r1 - tau0 * r0
        return (delta_static - delta_total) * max(0.0, float(phase))

    def death_response_coefficient(self) -> float:
        """``b`` for the response of gains at death to a change in their rate.

        The **persistent** coefficient only.  The transitory term is a retiming
        response - a taxpayer brings a sale forward or pushes it back around an
        effective date - and death cannot be retimed to the rate, so it has no
        place here.  The lock-in wedge divides it for the same reason it
        divides the realizations coefficient: once death is a realization
        event, holding on no longer escapes the tax.
        """
        reference = float(self.elasticity_reference_rate)
        persistent = (
            float(self.persistent_elasticity)
            if self.use_time_varying_elasticity
            else float(self.realization_elasticity)
        )
        coefficient = persistent / reference
        if self.eliminate_step_up:
            wedge = self.lock_in_wedge()
            if wedge > 0:
                coefficient /= wedge
        return coefficient

    def _charitable_share_at_death(self, decedent_class, rate: float) -> float:
        """Share of a class's gain that goes to charity once gains are taxed.

        Two parts.  The **level** is what already goes to charity: IRS SOI
        *Estate Tax Statistics* Table 1's charitable deduction over the estate
        net of spousal bequests, by size of estate.  The **increment** is the
        substitution the tax induces, and it is the death channel's avoidance
        response: taxing gains at death makes a charitable bequest cheaper
        relative to a bequest to heirs, because the estate saves ``rate`` times
        the unrealized-gain share of the wealth given.  With a constant
        elasticity of charitable bequests with respect to that price, the share
        rises by ``(1 - rate * gain_share) ** -elasticity``.

        The price change ignores that a charitable bequest already avoids
        estate tax for a taxable estate, so the fall in price - and therefore
        the response - is understated.
        """
        baseline = max(0.0, min(1.0, float(decedent_class.charitable_bequest_share)))
        if baseline <= 0:
            return 0.0
        gain_share = max(0.0, min(1.0, float(decedent_class.unrealized_gain_share)))
        price = 1.0 - max(0.0, min(1.0, rate)) * gain_share
        if price <= 0:
            return 1.0
        induced = price ** (-float(self.charitable_bequest_price_elasticity))
        return max(0.0, min(1.0, baseline * induced))

    def reachable_gains_per_decedent(
        self,
        decedent_class,
        rate: float,
        rate_change_faced: float = 0.0,
        years_since_start: int = 0,
    ) -> float:
        """Gain per decedent a realization-at-death proposal actually reaches.

        The carve-outs apply in the order the statute does, and the per-donor
        exclusion is **not** among them: both Green Books grant it against
        *"other* unrealized capital gains", meaning what is left after the
        named reliefs.  The caller subtracts it afterwards.

        Each share below is the published step function evaluated at **this
        slice's own estate size**, which is what changed in Wave 7; before it,
        five class means read eighteen published rows at eleven of them.

        1. **Charity.**  Appreciated property transferred to charity generates
           no taxable gain, and the tax itself induces more of it
           (:meth:`_charitable_share_at_death`).
        2. **The family-owned-business election**, where the design offers it.
           Tax on the appreciation of a family-owned and -operated business is
           not due until the interest is sold, so inside a ten-year window only
           what is sold is collected - at the module's own observed realization
           hazard, which introduces no new constant.
        3. **Section 121**, up to :attr:`section_121_exclusion` of the gain on
           the principal residence.
        4. **The rate response**, where the proposal changes the rate this
           decedent faces by ``rate_change_faced``
           (:meth:`death_response_coefficient`).

        The spousal and tangible-personal-property reliefs are absent because
        the base already excludes both - Poterba & Weisbenner's Table 8 note,
        quoted in :mod:`fiscal_model.data.capital_gains`.
        """
        gain = float(decedent_class.gains_per_decedent_dollars)
        if gain <= 0 or not self.apply_death_carveouts:
            return max(0.0, gain)

        gain *= 1.0 - self._charitable_share_at_death(decedent_class, rate)

        if self.defer_family_business_gains:
            deferred = max(
                0.0, min(1.0, float(decedent_class.active_business_gain_share))
            )
            if deferred > 0:
                hazard = self._realization_hazard()
                recaptured = 1.0 - (1.0 - hazard) ** (max(0, int(years_since_start)) + 1)
                gain *= 1.0 - deferred * (1.0 - recaptured)

        residence = max(0.0, min(1.0, float(decedent_class.residence_gain_share)))
        gain -= min(gain * residence, max(0.0, float(self.section_121_exclusion)))

        if rate_change_faced != 0.0:
            gain *= math.exp(-self.death_response_coefficient() * rate_change_faced)

        return max(0.0, gain)

    def _realization_hazard(self) -> float:
        try:
            source = self._baseline_source()
            return float(source.realization_hazard(self._data_year(source)))
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("family-business deferral: hazard unavailable (%s)", exc)
            return 0.0

    def estimate_step_up_elimination_revenue(self, years_since_start: int = 0) -> float:
        """Revenue from treating transfers at death as realization events.

        Decedent wealth times the unrealized-gain share of an estate that size,
        less the carve-outs the proposal states
        (:meth:`reachable_gains_per_decedent`), less the per-donor exclusion,
        priced at the rate the gain would face on a final return.  Indexed to
        household net worth, so the flow grows with the asset stock instead of
        sitting at one constant.

        The sum runs over quantile slices of a fitted size distribution, not
        over five estate-size classes, so the per-donor exclusion below is
        subtracted from a spread of gains rather than from a class average.
        """
        if not self.eliminate_step_up or not self.score_gains_at_death:
            return 0.0
        try:
            source = self._baseline_source()
        except Exception as exc:  # pragma: no cover - data-availability guard
            logger.warning("gains at death: data unavailable (%s)", exc)
            return 0.0

        year = int(self.start_year) + max(0, int(years_since_start))
        exemption = max(0.0, float(self.step_up_exemption))
        stock = self.stock_ratio(years_since_start)

        from fiscal_model.data.capital_gains import NIIT_RATE, NIIT_THRESHOLD

        revenue = 0.0
        for decedent_class in source.decedent_classes(year):
            gain = decedent_class.gains_per_decedent_dollars
            if gain <= 0 or decedent_class.decedents_per_year <= 0:
                continue
            niit = NIIT_RATE if gain >= NIIT_THRESHOLD else 0.0
            statutory = source.statutory_rate_on_gain(gain) - niit
            # A rate change that applies above an income threshold reaches a
            # decedent only if the gain on the final return clears it.  The
            # bracket is read off the class's gain before carve-outs, so a
            # decedent whose reliefs drop them into a lower preferential
            # bracket is still priced at the higher one.
            in_scope = gain >= float(self.affected_income_threshold)
            if self.new_rate is not None and in_scope:
                rate = float(self.new_rate) + niit
            elif in_scope:
                rate = statutory + float(self.rate_change) + niit
            else:
                rate = statutory + niit
            rate = max(0.0, min(rate, 0.999))
            rate_change_faced = rate - (statutory + niit) if in_scope else 0.0
            reachable = self.reachable_gains_per_decedent(
                decedent_class, rate, rate_change_faced, years_since_start
            )
            taxable_per_decedent = max(0.0, reachable - exemption)
            if taxable_per_decedent <= 0:
                continue
            taxable = (
                decedent_class.decedents_per_year * taxable_per_decedent / 1e9 * stock
            )
            revenue += taxable * rate
        return revenue


@dataclass
class SpendingPolicy(Policy):
    """Spending policy proposal.

    Budget authority and outlays are **distinct quantities**.
    ``annual_spending_change_billions`` (and ``budget_authority_path``) describe
    the *authority* a proposal provides or withdraws;
    :meth:`get_outlays_in_year` spends that authority out over time using the
    profile named by ``outlay_account_class``
    (see :mod:`fiscal_model.spending_outlays`).

    ``outlay_account_class`` defaults to ``"immediate"`` - the identity, one
    dollar of authority becoming one dollar of outlay in the year it is
    provided - so an existing policy scores exactly as it did before spend-out
    existed. Callers that know the account type opt in; the validation shapes
    in ``validation/core.py`` do.
    """

    annual_spending_change_billions: float = 0.0
    annual_growth_rate: float = 0.02
    gdp_multiplier: float = 1.0
    employment_per_billion: float = 10000
    is_one_time: bool = False
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense"
    outlay_account_class: str = IMMEDIATE
    #: Explicit year-by-year budget authority from ``start_year``, for a
    #: proposal whose authority is *not* a level - a multi-year authorization
    #: that ends, say. When set it overrides the level-times-growth path.
    budget_authority_path: tuple[float, ...] | None = None

    def __post_init__(self):
        super().__post_init__()
        category_to_type = {
            "defense": PolicyType.DISCRETIONARY_DEFENSE,
            "nondefense": PolicyType.DISCRETIONARY_NONDEFENSE,
            "mandatory": PolicyType.MANDATORY_SPENDING,
        }
        expected_type = category_to_type.get(self.category)
        if expected_type and self.policy_type != expected_type:
            self.policy_type = expected_type
        if self.budget_authority_path is not None:
            self.budget_authority_path = tuple(float(x) for x in self.budget_authority_path)
        # Fail fast on an unknown class rather than silently outlaying 1:1.
        get_outlay_profile(self.outlay_account_class)

    @property
    def outlay_profile(self) -> "OutlayProfile":
        """The spend-out profile this policy's account class implies."""
        return get_outlay_profile(self.outlay_account_class)

    def get_budget_authority_in_year(
        self, year: int, start_amount: float | None = None
    ) -> float:
        """Budget authority provided in a year, including growth and phase-in.

        This is the quantity a proposal actually sets. It is *not* the outlay
        unless the account spends out immediately.
        """
        if not self.is_active(year):
            return 0.0

        years_since_start = year - self.start_year

        if self.is_one_time and years_since_start > 0:
            return 0.0

        phase_factor = self.get_phase_in_factor(year)

        if self.budget_authority_path is not None and start_amount is None:
            if years_since_start >= len(self.budget_authority_path):
                return 0.0
            return self.budget_authority_path[years_since_start] * phase_factor

        # `is not None`, not truthiness: a caller overriding the level with 0.0
        # means zero authority, and must not silently get the policy's own level
        # back. The branch above already tests `start_amount is None`, so a
        # truthiness test here would disagree with it for exactly that value.
        base = (
            start_amount
            if start_amount is not None
            else self.annual_spending_change_billions
        )
        growth_factor = (1 + self.annual_growth_rate) ** years_since_start
        return base * growth_factor * phase_factor

    def get_outlays_in_year(
        self,
        year: int,
        start_amount: float | None = None,
        *,
        window_start: int | None = None,
    ) -> float:
        """Outlays in a year: budget authority from this and earlier years, spent out.

        ``window_start`` bounds how far back authority is drawn from. It
        defaults to ``start_year``, so authority provided before the policy
        began contributes nothing - which is what a *change* in authority
        means.
        """
        profile = self.outlay_profile
        if profile.shares == (1.0,):
            # The identity. Short-circuited on the *rate*, not on the profile's
            # length: a one-entry profile that outlays less than a full dollar
            # still has to be applied.
            return self.get_budget_authority_in_year(year, start_amount)

        earliest = self.start_year if window_start is None else max(window_start, self.start_year)
        total = 0.0
        for lag, share in enumerate(profile.shares):
            source_year = year - lag
            if source_year < earliest:
                break
            if share == 0.0:
                continue
            total += share * self.get_budget_authority_in_year(source_year, start_amount)
        return total

    def get_spending_in_year(self, year: int, start_amount: float | None = None) -> float:
        """Outlays in a given year.

        Kept under its original name because every caller in the model, the app
        and the tests means *the amount that hits the deficit this year*, which
        is the outlay. Under the default ``immediate`` class this is identical
        to :meth:`get_budget_authority_in_year`.
        """
        return self.get_outlays_in_year(year, start_amount)


@dataclass
class TransferPolicy(Policy):
    """Transfer program policy."""

    benefit_change_percent: float = 0.0
    benefit_change_dollars: float = 0.0
    eligibility_age_change: float = 0.0
    new_beneficiaries_millions: float = 0.0
    annual_cost_change_billions: float = 0.0
    labor_force_participation_effect: float = 0.0

    def estimate_cost_effect(self, baseline_cost: float) -> float:
        """Estimate change in program costs."""
        if self.annual_cost_change_billions != 0:
            return self.annual_cost_change_billions

        cost_change = baseline_cost * self.benefit_change_percent

        if self.new_beneficiaries_millions != 0:
            avg_benefit = baseline_cost / 60
            cost_change += avg_benefit * self.new_beneficiaries_millions

        return cost_change


@dataclass
class PolicyPackage:
    """A package of multiple policies analyzed together."""

    name: str
    description: str
    policies: list[Policy] = field(default_factory=list)
    interaction_factor: float = 1.0

    def add_policy(self, policy: Policy):
        """Add a policy to the package."""
        self.policies.append(policy)

    def get_all_years(self) -> tuple[int, int]:
        """Get the range of years covered by all policies."""
        if not self.policies:
            return (2025, 2034)

        start = min(policy.start_year for policy in self.policies)
        end = max(policy.start_year + policy.duration_years for policy in self.policies)
        return (start, end)

    def get_active_policies(self, year: int) -> list[Policy]:
        """Get all policies active in a given year."""
        return [policy for policy in self.policies if policy.is_active(year)]
