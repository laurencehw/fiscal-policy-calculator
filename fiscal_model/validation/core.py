"""
Core validation types and helpers.

This module contains the shared result model plus the generic validation
helpers used across the specialized policy validators.
"""

from dataclasses import dataclass, field

import numpy as np

from ..baseline import BaselineVintage, CBOBaseline
from ..policies import (
    CapitalGainsPolicy,
    Policy,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
)
from ..scoring import FiscalPolicyScorer
from ..spending_outlays import IMMEDIATE
from .cbo_scores import CBOScore, get_validation_targets, validation_shape

#: Fiscal year the validation window opens on. A record may override it with
#: ``effective_start_year`` when the *source* states a later effective date.
DEFAULT_VALIDATION_START_YEAR = 2025

_SPENDING_CATEGORY_TO_POLICY_TYPE = {
    "defense": PolicyType.DISCRETIONARY_DEFENSE,
    "nondefense": PolicyType.DISCRETIONARY_NONDEFENSE,
    "mandatory": PolicyType.MANDATORY_SPENDING,
}

#: How fast each spending case's budget authority becomes an outlay.
#:
#: This is a **classification, not a fit** - the same discipline the
#: ordinary-vs-AGI-inclusive base split follows. Each case is assigned from the
#: predominant account type of the programs it funds, as the *source* describes
#: them, by this rule and no other:
#:
#: * pay, benefits, allowances, medical-care enrollment
#:       -> ``personnel_and_benefits``
#: * agency operations, force structure, O&M, across-the-board discretionary
#:   caps that fall on the whole discretionary budget
#:       -> ``operations_and_support``
#: * project and formula grants, assistance awards, student aid, foreign
#:   assistance, procurement, R&D
#:       -> ``grants_and_procurement``
#: * construction, infrastructure and other capital grants
#:       -> ``construction_and_capital``
#: * direct benefit payments, outlaid in the year they are owed
#:       -> ``mandatory_benefit``
#:
#: The *rates* behind each class come from CBO options that are not in this
#: battery (see :mod:`fiscal_model.spending_outlays` and
#: ``scripts/fit_outlay_rates.py``). No rate here is keyed to a benchmark, and
#: no assignment was chosen by the error it produced - ``ssfa_wep_gpo_repeal``
#: keeps its ~10% miss under this mapping, which is the point: its residual was
#: never a spend-out miss, and a rule that "fixed" it would be a fitted rule.
_SPENDING_OUTLAY_CLASS: dict[str, str] = {
    # Foreign assistance and State Department programs.
    "cbo_opt37_international_affairs": "grants_and_procurement",
    # AmeriCorps and related national-service grants.
    "cbo_opt38_national_service": "grants_and_procurement",
    # Discretionary Pell Grant student aid.
    "cbo_opt39_pell_eligibility": "grants_and_procurement",
    # CBO's own note names transportation and education grants.
    "cbo_opt42_nondefense_discretionary": "grants_and_procurement",
    # Infrastructure and community-development grants to states and localities.
    "cbo_opt43_state_local_grants": "construction_and_capital",
    # Social Security benefits: paid in the year owed, no authority-to-outlay lag.
    "ssfa_wep_gpo_repeal_outlays": "mandatory_benefit",
    # Caps on the whole discretionary budget, defense and nondefense together.
    "fra_2023_discretionary_caps": "operations_and_support",
    # IIJA's discretionary title is highways, transit, water and broadband
    # construction - the slowest spend-out in the federal budget.
    "iija_2021_discretionary": "construction_and_capital",
}

_KNOWN_LIMITATIONS_BY_POLICY_ID: dict[str, list[str]] = {
    "biden_ctc_2021": [
        "Credit eligibility and refundability are modeled with synthetic tax units rather than CPS ASEC microdata.",
        "Interactions with SALT, AMT, and filing-status heterogeneity remain approximated in the current household tax module.",
    ],
    "ctc_extension": [
        "The current credit module extrapolates from bracket-level aggregates rather than return-level household data.",
    ],
    "ss_cap_90_pct": [
        "Covered-wage bands are SSA-aligned aggregates, not worker-level SSA earnings records.",
    ],
    "ss_donut_250k": [
        "Covered-wage bands are SSA-aligned aggregates, not worker-level SSA earnings records.",
        "Benefit-offset and taxable-benefit interactions are simplified relative to Trustees methodology.",
    ],
    "ss_eliminate_cap": [
        "Covered-wage bands are SSA-aligned aggregates, not worker-level SSA earnings records.",
        "Benefit-offset and taxable-benefit interactions are simplified relative to Trustees methodology.",
    ],
    "expand_niit": [
        "Pass-through income exposure is modeled with simplified aggregate distributions rather than return-level business-owner data.",
    ],
    "biden_corporate_28": [
        "Corporate base-shifting, pass-through spillovers, and international interactions are simplified relative to Treasury and JCT models.",
    ],
    "trump_corporate_15": [
        "This scenario is calibrated from model assumptions rather than a public official score.",
    ],
    "tcja_full_extension": [
        "Aggregate calibration is strong, but the extension decomposition is not backed by CPS ASEC return-level microsimulation.",
    ],
    "tcja_extension_full": [
        "Aggregate calibration is strong, but the extension decomposition is not backed by CPS ASEC return-level microsimulation.",
    ],
    "tcja_no_salt_cap": [
        "This scenario is illustrative rather than matched to a single official score.",
    ],
    "tcja_rates_only": [
        "This scenario is illustrative rather than matched to a single official score.",
    ],
    "pwbm_39_with_stepup": [
        "Capital-gains timing responses are highly sensitive to step-up basis and lock-in assumptions.",
    ],
    "pwbm_39_no_stepup": [
        "Capital-gains timing responses remain sensitive to realization elasticities and gains-at-death assumptions.",
    ],
    # -- Phase A out-of-sample promotions (uncalibrated Generic path) --------
    # These are large, documented misses. They are kept in the honest tier
    # rather than tuned away; each note states the structural reason.
    "top_rate_45": [
        "The uncalibrated path applies a single ETI (0.25) with the standard 0.5 factor, "
        "so an 8pp top-rate increase erodes by only ~12.5%; published top-rate estimates "
        "assume a much larger response at that rate level.",
        "The -$420B target is secondhand (a 'TPC-range' figure with a bare taxpolicycenter.org "
        "URL) and is internally inconsistent with illustrative_top_rate_5pp from the same "
        "source (+5pp above $1M = -$700B), so part of this error is target error.",
    ],
    "biden_capital_gains_39": [
        "Scored with the frozen module-default realization elasticities (0.8 short-run / 0.4 "
        "long-run) and no residual avoidance after step-up elimination; Treasury, JCT and PWBM "
        "all assume far stronger lock-in at a 43.4% top rate, which is why the calibrated "
        "CapitalGains runner needs case-specific multipliers up to 5.3x.",
        "The gains-at-death channel uses the module's $54B CBO aggregate and a linear "
        "exemption share, not an estate-level distribution of unrealized gains.",
    ],
    "treasury_capgains_39_plus_stepup_elim": [
        "Same shape as biden_capital_gains_39 (39.6% above $1M plus step-up elimination), so "
        "the uncalibrated path necessarily produces the same prediction; the two published "
        "targets nevertheless differ by 42% (-$322B vs -$456B), which bounds how well any "
        "single model can match both.",
        "Scored with the frozen module-default realization elasticities (0.8 / 0.4); the "
        "published estimates embed much stronger lock-in and avoidance responses.",
    ],
    # -- Phase D: enacted-law component replications -------------------------
    # Each row states whether its miss is attributable to the missing
    # budget-authority-to-outlay spend-out model (Phase B's finding), because
    # that is the single question these three cases were added to answer.
    "ssfa_wep_gpo_repeal_outlays": [
        "SpendingPolicy carries one annual level grown at 2%/yr; CBO's own path for "
        "the WEP/GPO repeal grows at about 1.1%/yr after the first full year, so the "
        "model drifts above the published path across the window.",
        "NOT a spend-out miss, and the spend-out model confirms that rather than "
        "closing it: classified 'mandatory_benefit', 99.8% of the authority outlays "
        "inside the window and the residual is unchanged. Benefit payments are "
        "outlaid in the year they are owed, so the whole miss is the growth rate.",
        "The FY2025 retroactive catch-up CBO describes ($25.0B, against a $19.7B "
        "steady state) is outside the level shape entirely; the model neither "
        "reproduces the spike nor is credited with it.",
    ],
    "fra_2023_discretionary_caps": [
        "What remains is the level shape, not the spend-out. CBO's caps compound "
        "against a falling funding base and reach -$159.7B by 2033, while a level "
        "grown at 2%/yr reaches only about -$134B, so the model under-predicts for "
        "that reason alone.",
        "This case got WORSE when spend-out was added, and that is the correct "
        "outcome. Its old ~6% total was a cancellation: the model over-predicted the "
        "early years (CBO's 2024 outlay saving is -$64.1B against -$112.3B of budget "
        "authority) and under-predicted the late ones. Spend-out removes the first "
        "error and leaves the second, so a truer path shows a larger total error. "
        "The old number measured the cancellation, not the fit.",
        "Only the caps component is scored. The bill's -$1.5T headline also bundles "
        "the $45B Toxic Exposures Fund appropriation, student-loan payment "
        "resumption, an IRS rescission and debt service.",
    ],
    "iija_2021_discretionary": [
        "Now a WINDOW miss, and no longer either a spend-out or a level-shape miss. "
        "The shape is the source's own authorization schedule "
        "(iija_2021_discretionary.v2: $163.0B of budget authority in FY2022, then "
        "$70.1B, $68.5B, $68.1B, $66.2B and $2.08B/yr, summing to CBO's stated "
        "$446.3B), spent out on the construction_and_capital profile. Total "
        "outlays across every year the policy touches are $433.2B against CBO's "
        "$415.4B - 4.3% high, which is just the profile's 0.973 spend-out sum "
        "applied to the full authority.",
        "The residual is arithmetic, not behaviour: $92.6B of those outlays fall in "
        "FY2022-2024, before the model's FY2025-2034 window opens, so $340.0B is "
        "in-window against a published figure that covers FY2021-2031. The "
        "repository has no 2021 vintage to score this bill on its own window, which "
        "is the vintage mismatch the manifest row already records. Nothing here is "
        "corrected for that: the case is scored on the model's window and reports "
        "the gap.",
        "The superseded v1 row (a level carried forward at 2%/yr) is kept in "
        "preregistered.py at its +$1,894B / 356% and post-spend-out +$1,621B / "
        "290%. Between them the two rows separate the two defects this case "
        "surfaced: the missing spend-out model (L2) and the missing authorization "
        "path (this row).",
    ],
    # -- Phase B: CBO Options for Reducing the Deficit, 2025-2034 -----------
    # Out-of-sample battery. Every miss below is kept and explained; none of
    # these cases had a parameter moved to close its gap.
    "cbo_opt45_all_rates_1pp": [
        "Scored on the SOI ordinary-income base with a single ETI (0.25); JCT's "
        "estimate rises through the window partly because bracket creep pushes "
        "income into higher rates, which the flat-base auto-population does not "
        "reproduce.",
    ],
    "cbo_opt45_top4_brackets_2pp": [
        "'The four highest brackets' is a filing-status-specific boundary that also "
        "moves in 2026 when the pre-2018 rate schedule returns; the generic path "
        "carries one fixed threshold (the 2025 single-filer 24% floor), which counts "
        "joint filers below their own bracket boundary and over-states the base.",
    ],
    "cbo_opt46_agi_surtax_1pp_20k": [
        "A $20,000 single / $40,000 joint threshold sits near the bottom of the "
        "filing population, where the single-threshold approximation is worst: the "
        "model applies the $20,000 floor to every return, so joint filers between "
        "$20,000 and $40,000 of AGI are taxed in the model and exempt in JCT's "
        "estimate - yet the model still under-predicts, because SOI aggregate AGI "
        "above the floor understates the surtax base JCT uses.",
        "No behavioural distinction between a broad low-threshold surtax and a "
        "narrow high-income one: both erode by ETI x 0.5.",
    ],
    "cbo_opt46_agi_surtax_2pp_100k": [
        "Single-filer threshold applied to all returns; the model has no "
        "filing-status dimension.",
    ],
    "cbo_opt47_ltcg_qdiv_2pp": [
        "A uniform +2pp applies to the 0%, 15% and 20% brackets alike, but the "
        "model scores it against the SOI statutory-rate baseline for the *whole* "
        "realizations base, so gains that face the 0% rate (and gains inside "
        "retirement accounts and other non-taxable holders reflected in the SOI "
        "aggregate) are taxed at the margin in the model and not in JCT's estimate.",
        "The frozen 0.8/0.4 realization elasticities are calibrated for large rate "
        "changes; at 2pp the timing response JCT assumes is proportionally larger.",
    ],
    "cbo_opt51_gains_at_death": [
        "The entire score runs through one module constant - $54B of unrealized "
        "gains transferred at death - taxed at the SOI baseline rate. CBO/JCT's "
        "estimate is roughly six times larger because it accrues gains on the full "
        "stock of appreciated assets held by decedents, not an annual realizations "
        "aggregate.",
        "No lock-in unwind: constructive realization at death removes the incentive "
        "to hold appreciated assets, which raises lifetime realizations. The module "
        "models that channel only through an elasticity multiplier that a zero rate "
        "change leaves inert.",
    ],
    "cbo_opt61_new_payroll_tax_1pct": [
        "Scored off the module's Medicare revenue identity ($400B at 2.9%, so ~$140B "
        "per percentage point) grown at 4%/yr. That identity covers all Medicare "
        "wages including the employer share, while CBO's option is employee-side "
        "only and is reduced by the income-tax offset a new payroll tax generates - "
        "neither adjustment exists in the module.",
    ],
    "cbo_opt61_new_payroll_tax_2pct": [
        "Same Medicare-base identity as the 1% alternative, so the error is the same "
        "proportional over-statement; the module is linear in the rate while CBO's "
        "estimate is very nearly so, which is why the two errors barely differ.",
    ],
    "cbo_opt64_corporate_rate_1pp": [
        "The corporate module scores a rate change against its own baseline "
        "corporate revenue and profit aggregates. Those aggregates reproduce the "
        "calibrated 21%->28% benchmark, but at a 1pp step the model over-predicts: "
        "it applies the full statutory-rate delta to the whole base, whereas JCT's "
        "estimate reflects credits, loss carryforwards and the timing of estimated "
        "payments that blunt the first few years.",
    ],
    "cbo_opt37_international_affairs": [
        "Foreign assistance is classified 'grants_and_procurement', a profile fitted "
        "on defence procurement options this battery does not score. What is left is "
        "the gap between that generic profile and this account's own speed.",
    ],
    "cbo_opt38_national_service": [
        "Same generic grants profile as Option 37. National-service grants spend out "
        "a little slower than the profile implies, so the model still books slightly "
        "more inside the window than CBO does.",
    ],
    "cbo_opt39_pell_eligibility": [
        "Pell spends out faster than the generic grants profile - CBO's own path is "
        "essentially complete in two years - so the model now defers past the window "
        "savings CBO books inside it. Closing this needs an account-level rate "
        "rather than an account-class one.",
        "The target is the discretionary outlay total only; CBO reports a separate "
        "-$9.2B mandatory effect that this shape cannot represent.",
    ],
    "cbo_opt42_nondefense_discretionary": [
        "A broad nondefense reduction scored on one grants profile; the option's "
        "real composition spans several account types with different speeds.",
    ],
    "cbo_opt43_state_local_grants": [
        "What remains is the level, not the lag. The 2026 budget authority "
        "(-$12.0B) is inflated by IIJA advance funding and by the option's "
        "25%-then-50% schedule, so anchoring a constant level on it over-states "
        "every later year; CBO's own path drops to -$9.3B in 2027.",
        "Infrastructure and block grants have the slowest spend-out in the battery "
        "(CBO's 2026 outlay saving is -$0.4B against -$12.0B of authority), which is "
        "why this case gained most from the spend-out model.",
    ],
}


@dataclass
class ValidationResult:
    """
    Result of validating model output against an official score.
    """

    policy_id: str
    policy_name: str

    official_10yr: float
    official_source: str
    model_10yr: float
    model_first_year: float
    difference: float
    percent_difference: float
    direction_match: bool
    accuracy_rating: str
    model_parameters: dict = field(default_factory=dict)
    notes: str = ""
    benchmark_kind: str = "Published benchmark"
    benchmark_date: str | None = None
    benchmark_url: str | None = None
    known_limitations: list[str] = field(default_factory=list)

    @property
    def is_accurate(self) -> bool:
        """Check if estimate is within acceptable tolerance (20%)."""
        return abs(self.percent_difference) <= 20.0

    @property
    def abs_percent_difference(self) -> float:
        """Return the absolute percent error."""
        return abs(self.percent_difference)

    @property
    def needs_follow_up(self) -> bool:
        """Flag scenarios that need explicit manuscript discussion."""
        return self.abs_percent_difference >= 8.0 or bool(self.known_limitations)

    def get_summary(self) -> str:
        """Get a one-line summary."""
        direction = "✓" if self.direction_match else "✗"
        return (
            f"{self.policy_name}: "
            f"Official ${self.official_10yr:,.0f}B vs "
            f"Model ${self.model_10yr:,.0f}B "
            f"({self.percent_difference:+.1f}%) "
            f"[{self.accuracy_rating}] {direction}"
        )


def _rate_accuracy(percent_diff: float) -> str:
    """Rate the accuracy of an estimate."""
    abs_diff = abs(percent_diff)
    if abs_diff <= 5:
        return "Excellent"
    if abs_diff <= 10:
        return "Good"
    if abs_diff <= 20:
        return "Acceptable"
    return "Poor"


def _infer_benchmark_kind(official_source: str) -> str:
    """Infer the benchmark type from the source label."""
    source = official_source.lower()

    if "user-provided" in source:
        return "User-supplied target"
    if "congressional budget office" in source or source.startswith("cbo"):
        return "Official budget score"
    if "joint committee on taxation" in source or source.startswith("jct"):
        return "Official budget score"
    if "treasury" in source or "office of management and budget" in source:
        return "Published administration estimate"
    if "trustees" in source or "social security" in source:
        return "Published actuarial estimate"
    if "tax policy center" in source or "penn wharton" in source or "pwbm" in source:
        return "Published external estimate"
    if "model" in source or "estimated" in source:
        return "Illustrative target"
    return "Published benchmark"


def _merge_unique_strings(*groups: list[str] | tuple[str, ...]) -> list[str]:
    """Merge string lists while preserving order and removing duplicates."""
    merged: list[str] = []
    for group in groups:
        for value in group:
            cleaned = value.strip()
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
    return merged


def calculate_percent_difference(model_10yr: float, official_10yr: float) -> float:
    """Return the signed percent difference between model and official scores."""
    difference = model_10yr - official_10yr
    if official_10yr != 0:
        return (difference / abs(official_10yr)) * 100
    return 0.0 if model_10yr == 0 else 100.0


def direction_matches(model_10yr: float, official_10yr: float) -> bool:
    """Check whether the model and official score move in the same direction."""
    return (
        (model_10yr > 0 and official_10yr > 0)
        or (model_10yr < 0 and official_10yr < 0)
        or (model_10yr == 0 and official_10yr == 0)
    )


def build_validation_result(
    *,
    policy_id: str,
    policy_name: str,
    official_10yr: float,
    official_source: str,
    model_10yr: float,
    model_first_year: float,
    model_parameters: dict | None = None,
    notes: str = "",
    direction_match: bool | None = None,
    benchmark_kind: str | None = None,
    benchmark_date: str | None = None,
    benchmark_url: str | None = None,
    known_limitations: list[str] | None = None,
) -> ValidationResult:
    """Construct a ValidationResult from shared metrics."""
    difference = model_10yr - official_10yr
    percent_diff = calculate_percent_difference(model_10yr, official_10yr)
    if direction_match is None:
        direction_match = direction_matches(model_10yr, official_10yr)

    merged_limitations = _merge_unique_strings(
        _KNOWN_LIMITATIONS_BY_POLICY_ID.get(policy_id, []),
        known_limitations or [],
    )

    return ValidationResult(
        policy_id=policy_id,
        policy_name=policy_name,
        official_10yr=official_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=model_first_year,
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters=model_parameters or {},
        notes=notes,
        benchmark_kind=benchmark_kind or _infer_benchmark_kind(official_source),
        benchmark_date=benchmark_date,
        benchmark_url=benchmark_url,
        known_limitations=merged_limitations,
    )


def _resolve_vintage(score: CBOScore) -> BaselineVintage | None:
    """The baseline vintage a score record asks to be scored on, if any."""
    if not score.scoring_vintage:
        return None
    try:
        return BaselineVintage(score.scoring_vintage)
    except ValueError:
        return None


def build_scorer_for_vintage(
    vintage: BaselineVintage | None,
    *,
    start_year: int = DEFAULT_VALIDATION_START_YEAR,
    use_real_data: bool = True,
) -> FiscalPolicyScorer:
    """
    Build a scorer on a specific baseline vintage.

    ``None`` keeps the historical behaviour (the model's current default
    baseline), so records that do not name a vintage are unaffected. A record
    that *does* name one - the CBO Options battery names ``cbo_feb_2024``,
    the vintage its targets were published against - is scored against that
    baseline instead, which removes baseline drift from its error.
    """
    if vintage is None:
        return FiscalPolicyScorer(start_year=start_year, use_real_data=use_real_data)
    baseline = CBOBaseline(
        start_year=start_year, use_real_data=use_real_data, vintage=vintage
    ).generate()
    return FiscalPolicyScorer(
        baseline=baseline, start_year=start_year, use_real_data=use_real_data
    )


def create_policy_from_score(
    score: CBOScore, *, ordinary_income_base: bool | None = None
) -> Policy | None:
    """
    Build the policy object a known official score describes.

    Dispatch is on the record's *shape* (:func:`validation_shape`), not on a
    single hard-coded ``policy_type``:

    ``ordinary_rate``
        :class:`TaxPolicy` from rate + threshold. ``ordinary_income_base``
        defaults to True (exclude preferential LTCG/QDIV); pass False, or set
        ``score.agi_inclusive_base=True``, for AGI-inclusive surtaxes.
    ``capital_gains``
        :class:`CapitalGainsPolicy` with the **module-default** elasticity set
        (short-run 0.8 / long-run 0.4) and SOI auto-populated baseline
        realizations and rate. Deliberately *not* the per-case hand-set
        elasticity tuples in ``scenarios.py`` — this path is the uncalibrated
        prediction, so its behavioural parameters are frozen across cases.
    ``corporate_rate``
        :class:`CorporateTaxPolicy` from the rate change, module defaults for
        elasticity and base.
    ``payroll_rate``
        :class:`PayrollTaxPolicy` levying the rate on the **Medicare base** -
        all covered earnings with no taxable maximum, which is the base a flat
        new payroll tax applies to. Deliberately *not* the Social Security cap
        machinery: those covered-wage bands are calibrated to reproduce the
        Trustees' own reform annuals, so routing a target through them would
        leak the answer.
    ``spending``
        :class:`SpendingPolicy` from the source-stated annual level, growth,
        phase-in and one-time flag.

    Every shape honours ``score.effective_start_year`` - the year the *source*
    says the policy takes effect - so an option that starts in FY2026 is not
    credited with a year of effect the official estimate never scored.

    Returns ``None`` when the record has no constructible shape.
    """
    shape = validation_shape(score)
    if shape is None:
        return None

    start_year = score.effective_start_year or DEFAULT_VALIDATION_START_YEAR

    if shape == "ordinary_rate":
        if ordinary_income_base is None:
            ordinary_income_base = not score.agi_inclusive_base
        return TaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.INCOME_TAX,
            rate_change=score.rate_change,
            affected_income_threshold=score.income_threshold or 0,
            start_year=start_year,
            duration_years=10,
            ordinary_income_base=ordinary_income_base,
        )

    if shape == "capital_gains":
        return create_capital_gains_policy_from_score(
            score,
            # 0.0 leaves both fields to the SOI auto-population inside
            # CapitalGainsPolicy.estimate_static_revenue_effect().
            baseline_capital_gains_rate=0.0,
            baseline_realizations_billions=0.0,
            eliminate_step_up=score.eliminate_step_up,
            step_up_exemption=score.step_up_exemption,
            start_year=start_year,
        )

    if shape == "corporate_rate":
        from ..corporate import CorporateTaxPolicy

        return CorporateTaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=score.rate_change,
            start_year=start_year,
            duration_years=10,
        )

    if shape == "payroll_rate":
        from ..payroll import PayrollTaxPolicy, PayrollTaxType

        return PayrollTaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.PAYROLL_TAX,
            payroll_tax_type=PayrollTaxType.MEDICARE,
            medicare_rate_change=score.rate_change,
            start_year=start_year,
            duration_years=10,
        )

    # shape == "spending"
    return SpendingPolicy(
        name=f"Validation: {score.name}",
        description=score.description,
        policy_type=_SPENDING_CATEGORY_TO_POLICY_TYPE[score.spending_category],
        annual_spending_change_billions=float(score.annual_amount_billions or 0.0),
        # A source that states a *schedule* rather than a level gets the
        # schedule; the level and its growth rate are then unused. See
        # ``IIJA_AUTHORIZATION_PATH_RULE`` in ``preregistered.py``.
        budget_authority_path=score.annual_authority_path_billions,
        annual_growth_rate=score.annual_growth_rate,
        phase_in_years=score.phase_in_years,
        is_one_time=score.is_one_time,
        category=score.spending_category,
        outlay_account_class=spending_outlay_class(score.policy_id),
        start_year=start_year,
        duration_years=10,
    )


def spending_outlay_class(policy_id: str) -> str:
    """Account class governing how fast a spending case's authority outlays.

    Falls back to ``immediate`` for an unmapped case, so a newly added record
    scores exactly as it would have before spend-out existed until somebody
    classifies it deliberately.
    """
    return _SPENDING_OUTLAY_CLASS.get(policy_id, IMMEDIATE)


def create_capital_gains_policy_from_score(
    score: CBOScore,
    *,
    baseline_capital_gains_rate: float,
    baseline_realizations_billions: float,
    short_run_elasticity: float = 0.8,
    long_run_elasticity: float = 0.4,
    transition_years: int = 3,
    use_time_varying: bool = True,
    eliminate_step_up: bool = False,
    step_up_exemption: float | None = None,
    start_year: int = DEFAULT_VALIDATION_START_YEAR,
) -> CapitalGainsPolicy:
    """
    Create a CapitalGainsPolicy from a score entry plus required extra inputs.

    The elasticity defaults here are the module defaults (0.8 short-run / 0.4
    long-run, Auten-Clotfelter/CBO range). The calibrated ``CapitalGains``
    runner overrides them per case; the Generic out-of-sample path must not.
    """
    if score.rate_change is None:
        raise ValueError("score.rate_change is required")

    extra: dict = {}
    if step_up_exemption is not None:
        extra["step_up_exemption"] = float(step_up_exemption)

    return CapitalGainsPolicy(
        eliminate_step_up=eliminate_step_up,
        name=f"Validation: {score.name}",
        description=score.description,
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=score.rate_change,
        affected_income_threshold=score.income_threshold or 0,
        start_year=start_year,
        duration_years=10,
        **extra,
        baseline_capital_gains_rate=float(baseline_capital_gains_rate),
        baseline_realizations_billions=float(baseline_realizations_billions),
        short_run_elasticity=float(short_run_elasticity),
        long_run_elasticity=float(long_run_elasticity),
        transition_years=int(transition_years),
        use_time_varying_elasticity=use_time_varying,
    )


create_capital_gains_example_from_score = create_capital_gains_policy_from_score


def _model_parameters_for(policy: Policy) -> dict:
    """Record the parameters that actually drove a shape's score.

    Each shape reports its own drivers. In particular ``CorporateTaxPolicy``
    subclasses ``TaxPolicy`` but ignores the individual bracket fields
    (``affected_income_threshold``, ``affected_taxpayers_millions``,
    ``avg_taxable_income_in_bracket``) — it scores off the corporate revenue
    and profit bases — so reporting those would make the validation output
    look auditable while describing nothing that moved the number.
    """
    from ..corporate import CorporateTaxPolicy

    if isinstance(policy, SpendingPolicy):
        return {
            "annual_spending_change_billions": policy.annual_spending_change_billions,
            "annual_growth_rate": policy.annual_growth_rate,
            "phase_in_years": policy.phase_in_years,
            "is_one_time": policy.is_one_time,
        }

    if isinstance(policy, CorporateTaxPolicy):
        return {
            "rate_change": policy.rate_change,
            "baseline_rate": policy.baseline_rate,
            "corporate_elasticity": policy.corporate_elasticity,
            "baseline_revenue_billions": policy.baseline_revenue_billions,
            "baseline_profits_billions": policy.baseline_profits_billions,
            "include_passthrough_effects": policy.include_passthrough_effects,
        }

    params = {
        "rate_change": policy.rate_change,
        "threshold": policy.affected_income_threshold,
        "taxpayers_millions": policy.affected_taxpayers_millions,
        "avg_income": policy.avg_taxable_income_in_bracket,
    }
    if isinstance(policy, CapitalGainsPolicy):
        params.update(
            {
                "baseline_rate": policy.baseline_capital_gains_rate,
                "baseline_realizations": policy.baseline_realizations_billions,
                "short_run_elasticity": policy.short_run_elasticity,
                "long_run_elasticity": policy.long_run_elasticity,
                "eliminate_step_up": policy.eliminate_step_up,
            }
        )
    return params


def validate_policy(
    score: CBOScore,
    scorer: FiscalPolicyScorer | None = None,
    dynamic: bool = False,
) -> ValidationResult | None:
    """
    Validate model output against a known CBO score.

    Args:
        score: The official score to validate against
        scorer: Pre-initialized scorer (creates new one if None)
        dynamic: Whether to use dynamic scoring

    Returns:
        ValidationResult or None if policy can't be replicated
    """
    policy = create_policy_from_score(score)
    if policy is None:
        return None

    if scorer is None:
        scorer = build_scorer_for_vintage(_resolve_vintage(score))

    try:
        result = scorer.score_policy(policy, dynamic=dynamic)
    except Exception as exc:
        return ValidationResult(
            policy_id=score.policy_id,
            policy_name=score.name,
            official_10yr=score.ten_year_cost,
            official_source=score.source.value,
            model_10yr=0.0,
            model_first_year=0.0,
            difference=score.ten_year_cost,
            percent_difference=100.0,
            direction_match=False,
            accuracy_rating="Error",
            notes=f"Model error: {exc!s}",
            benchmark_kind=_infer_benchmark_kind(score.source.value),
            benchmark_date=score.source_date,
            benchmark_url=score.source_url,
            known_limitations=_merge_unique_strings(
                _KNOWN_LIMITATIONS_BY_POLICY_ID.get(score.policy_id, []),
                ["Model execution failed during this validation run."],
            ),
        )

    return build_validation_result(
        policy_id=score.policy_id,
        policy_name=score.name,
        official_10yr=score.ten_year_cost,
        official_source=score.source.value,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters=_model_parameters_for(policy),
        notes=score.notes or "",
        benchmark_date=score.source_date,
        benchmark_url=score.source_url,
    )


def validate_all(dynamic: bool = False, verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all suitable policies in the database.
    """
    targets = get_validation_targets()

    if verbose:
        print(f"\nRunning validation against {len(targets)} policies...")
        print("=" * 70)

    # One scorer per baseline vintage. Records that name no vintage keep the
    # model's current default baseline (the historical behaviour); records that
    # name one - the CBO Options battery names the Feb 2024 baseline its targets
    # were published against - are scored on it, so baseline drift is not folded
    # into their error.
    scorers: dict[BaselineVintage | None, FiscalPolicyScorer] = {}

    results = []
    for score in targets:
        if verbose:
            print(f"\nValidating: {score.name}...")

        vintage = _resolve_vintage(score)
        if vintage not in scorers:
            scorers[vintage] = build_scorer_for_vintage(vintage)

        result = validate_policy(score, scorer=scorers[vintage], dynamic=dynamic)
        if result:
            results.append(result)
            if verbose:
                print(f"  {result.get_summary()}")

    return results


def run_validation_suite(verbose: bool = True) -> dict:
    """
    Run complete validation suite and return summary statistics.
    """
    results = validate_all(dynamic=False, verbose=verbose)

    if not results:
        return {"error": "No policies could be validated"}

    accurate_count = sum(1 for result in results if result.is_accurate)
    direction_match_count = sum(1 for result in results if result.direction_match)
    percent_diffs = [abs(result.percent_difference) for result in results]

    summary = {
        "total_policies": len(results),
        "accurate_count": accurate_count,
        "accuracy_rate": accurate_count / len(results) * 100,
        "direction_match_count": direction_match_count,
        "direction_match_rate": direction_match_count / len(results) * 100,
        "mean_percent_error": np.mean(percent_diffs),
        "median_percent_error": np.median(percent_diffs),
        "max_percent_error": np.max(percent_diffs),
        "min_percent_error": np.min(percent_diffs),
        "ratings": {
            "Excellent": sum(1 for result in results if result.accuracy_rating == "Excellent"),
            "Good": sum(1 for result in results if result.accuracy_rating == "Good"),
            "Acceptable": sum(1 for result in results if result.accuracy_rating == "Acceptable"),
            "Poor": sum(1 for result in results if result.accuracy_rating == "Poor"),
        },
        "results": results,
    }

    if verbose:
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Policies tested: {summary['total_policies']}")
        print(
            f"Within 20% accuracy: {summary['accurate_count']} "
            f"({summary['accuracy_rate']:.0f}%)"
        )
        print(
            f"Direction match: {summary['direction_match_count']} "
            f"({summary['direction_match_rate']:.0f}%)"
        )
        print(f"Mean error: {summary['mean_percent_error']:.1f}%")
        print(f"Median error: {summary['median_percent_error']:.1f}%")
        print("\nRatings breakdown:")
        for rating, count in summary["ratings"].items():
            print(f"  {rating}: {count}")

    return summary


def quick_validate(
    rate_change: float,
    income_threshold: float,
    expected_10yr: float,
    policy_name: str = "Test Policy",
) -> ValidationResult:
    """
    Quick validation of a specific policy configuration.
    """
    policy = TaxPolicy(
        name=policy_name,
        description=f"{rate_change*100:+.1f}pp rate change for income ≥${income_threshold:,.0f}",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate_change,
        affected_income_threshold=income_threshold,
    )

    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)
    result = scorer.score_policy(policy, dynamic=False)
    direction_match = True if expected_10yr == 0 else direction_matches(
        result.total_10_year_cost,
        expected_10yr,
    )

    return build_validation_result(
        policy_id="quick_test",
        policy_name=policy_name,
        official_10yr=expected_10yr,
        official_source="User-provided",
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "rate_change": rate_change,
            "threshold": income_threshold,
            "taxpayers_millions": policy.affected_taxpayers_millions,
            "avg_income": policy.avg_taxable_income_in_bracket,
        },
        direction_match=direction_match,
        benchmark_kind="User-supplied target",
    )
