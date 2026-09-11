"""
Core validation types and helpers.

This module contains the shared result model plus the generic validation
helpers used across the specialized policy validators.
"""

from dataclasses import dataclass, field

import numpy as np

from ..baseline import BaselineVintage, CBOBaseline
from ..policies import (
    DEFAULT_THRESHOLD_INDEXATION,
    INCOME_MEASURE_AGI,
    INCOME_MEASURE_TAXABLE_INCOME,
    THRESHOLD_INDEXATION_STATUTORY,
    CapitalGainsPolicy,
    Policy,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
)
from ..scoring import FiscalPolicyScorer
from ..spending_outlays import IMMEDIATE
from .cbo_scores import CBOScore, ScoreSource, get_validation_targets, validation_shape

#: Which realization-at-death design a capital-gains record carries.
#:
#: Both Treasury Green Books state six reliefs in the same paragraph as their
#: per-donor exclusion (FY2022 report p. 63, PDF p. 69; FY2025 report p. 81,
#: PDF p. 89), and one of them - deferral of the tax on a family-owned and
#: -operated business until the interest is sold - changes a score materially.
#: CBO's Option 51, alternative 2 (pub. 60557, report p. 61) states none of
#: them: its whole text is that capital gains "would be taxed as if the
#: decedent had sold the asset at death".
#:
#: So: **a realization-at-death proposal published by the Treasury in a Green
#: Book carries the reliefs that Green Book states alongside its per-donor
#: exclusion; a budget option that states none carries only what its own text
#: describes.** The key is the publisher of the document, not the size of the
#: target, and ``tests/test_capital_gains_death_channel.py`` pins that it
#: selects the same rows as the alternative key (a positive per-donor
#: exclusion), so the rule cannot quietly become a per-row switch.
#:
#: The charitable and section 121 carve-outs and the behavioural response are
#: **not** covered by this rule and apply to every design: a tax-exempt donee,
#: a statutory exclusion the proposals preserve and a price response are
#: properties of any regime that taxes gains at death.
GREEN_BOOK_DEATH_DESIGN_RULE = (
    "A capital-gains record that eliminates step-up and is sourced to a "
    "Treasury Green Book is scored with the Green Book's stated "
    "family-owned-business deferral; one sourced to a CBO or JCT budget option "
    "is not, because those documents state no such election."
)


def uses_green_book_death_design(score: CBOScore) -> bool:
    """Whether ``score``'s document states the Green Book's death-channel reliefs."""
    return bool(score.eliminate_step_up) and score.source is ScoreSource.TREASURY


#: How a per-filing-status threshold is read off a source that does not name
#: every status.
#:
#: Statutory income-tax boundaries vary by filing status, and IRS SOI Table 1.2
#: reports four: joint (with surviving spouses), separate, head of household and
#: single. Some sources print all four - the FY2025 Green Book's top-rate
#: proposal does. Others print two: CBO's Option 46 states "$20,000 for single
#: filers and $40,000 for joint filers" and says nothing about the other two.
#:
#: This rule was fixed **before** any of these records was scored on a split
#: base (``planning/lanes/W7_filing_status_split.md`` section 2.2, committed
#: ahead of the code) so that the reading is a stated convention rather than a
#: per-row choice. Its support is IRC section 1411(b), the one enacted surtax on
#: a broad income measure, which sets the joint amount for a joint return, half
#: of it for married filing separately - the single amount whenever joint is
#: twice single, as it is in both Option 46 alternatives - and the single amount
#: "in any other case", i.e. single and head of household together.
#:
#: The lane doc records what the two alternative readings would have scored:
#: they move the affected rows by under 1.5 points, and the shipped reading is
#: the middle of the three on both. It is not the flattering one.
FILING_STATUS_THRESHOLD_RULE = (
    "A record's income_threshold_by_filing_status carries only the amounts its "
    "own source prints. Every status the source does not name takes "
    "income_threshold - the source's single/unmarried amount - which for a "
    "source naming exactly two amounts means joint returns take the joint "
    "amount and separate, head-of-household and single returns take the single "
    "amount, the structure of IRC section 1411(b)."
)

#: When a record's threshold is read from CBO's own statutory schedule rather
#: than used as the fixed amount it is written as.
#:
#: The schedule exists — CBO publication 53724, three vintages, four filing
#: statuses, CY2021–CY2036 (:mod:`fiscal_model.cbo_tax_parameters`) — which
#: refutes the claim ``cbo_opt45_top4_brackets_2pp``'s own
#: ``known_limitations`` used to carry. What it does not settle is *which*
#: records may read it, and the answer is not "whichever ones have a threshold
#: that looks statutory". This rule was fixed **before** any record was edited
#: (``planning/lanes/R4_parameter_schedule.md`` section 1.3, committed ahead of
#: the code) and it is deliberately narrow: exactly three of the eleven generic
#: records qualify, and the two that are bracket 1 must score to the cent what
#: they scored before.
#:
#: The trap it exists to avoid is in the data. ``$20,000`` **is**
#: ``tp_bracket_2_hoh`` in CY2033 on the February 2024 vintage, so a rule that
#: matched on dollars would sweep CBO's Option 46 surtax onto a schedule its
#: own text never mentions.
STATUTORY_BRACKET_SCHEDULE_RULE = (
    "A record's threshold is read from CBO's tax-parameter schedule if and "
    "only if its own source describes the boundary as a statutory "
    "ordinary-income bracket. The bracket's INDEX (1-7) is what the record "
    "declares; the four dollar amounts per year are the schedule's, read on "
    "the record's own scoring_vintage. An amount the source states in its own "
    "words - an option's '$20,000 for single filers', a Green Book's "
    "'$400,000' - is the source's own number and stays where the source put "
    "it, however closely it happens to sit to a bracket floor. Numeric "
    "coincidence is not evidence."
)

#: Which IRS SOI income column a record's base is read from.
#:
#: ``CBOScore.agi_inclusive_base`` answers a different question - *is the
#: preferential (LTCG/QDIV) share removed?* - and is ``True`` on six records
#: that do **not** agree about the column. SOI Table 1.1 publishes both AGI and
#: taxable income by AGI size class, so a surtax stated on AGI was being priced
#: by subtracting an AGI threshold from an average of taxable income: at Option
#: 46's \$20,000 floor that is 40% of the base.
#:
#: This rule was fixed **before** any record was scored on the AGI column
#: (``planning/lanes/HSB_h2b_agi_column.md`` section 1.2, committed ahead of the
#: code) so the reading is a stated convention rather than a per-row choice. It
#: is not the flattering one: it takes ``warren_ultramillionaire_surtax_3pp``
#: from 5.2% to 24.8%, and the three AGI-inclusive rows it leaves alone would
#: all score *worse* if it moved them (68.4%, 41.6% and 39.2% against 31.8%,
#: 20.2% and 18.3%). Each is left because of what its own source says, and the
#: lane doc publishes those would-be figures so the choice can be overturned by
#: a document rather than by a preference.
AGI_BASE_RULE = (
    "A record's base is read from IRS SOI's AGI column only where its own "
    "source states the reform on AGI in as many words. A source that states "
    "taxable income, or that states a base which is neither SOI column - wages "
    "plus net investment income is neither - keeps the taxable-income column, "
    "and a record with no source document is never reclassified at all."
)

#: The records :data:`AGI_BASE_RULE` moves, each with the sentence that moved it.
#:
#: The honest home for this is a field on ``CBOScore`` beside
#: ``agi_inclusive_base``; ``cbo_scores.py`` belonged to a concurrent lane when
#: this was written, so the mapping lives here and the migration is an owner
#: item. The three ids would be identical either way.
_AGI_BASE_POLICY_IDS: dict[str, str] = {
    # CBO, Options for Reducing the Deficit: 2025-2034 (pub. 60557), option 46,
    # alternative 1, report p. 56.
    "cbo_opt46_agi_surtax_1pp_20k": (
        "a surtax of 1 percentage point would be imposed on AGI above $20,000 "
        "for single filers and $40,000 for joint filers"
    ),
    # The same option, alternative 2, same page.
    "cbo_opt46_agi_surtax_2pp_100k": (
        "a surtax of 2 percentage points would be imposed on AGI above "
        "$100,000 for single filers and $200,000 for joint filers"
    ),
    # The record's own description and note. Its target is secondhand (a
    # TPC-range figure behind a bare taxpolicycenter.org URL) and this rule does
    # not repair that - it is the row this rule makes five times worse.
    "warren_ultramillionaire_surtax_3pp": (
        "3 percentage point surtax on AGI above $2 million ... the surtax "
        "applies to AGI, which contains the preferential LTCG/QDIV portion"
    ),
}


def agi_base_source_sentence(score: CBOScore) -> str | None:
    """The sentence that puts this record on the AGI column, or ``None``."""
    return _AGI_BASE_POLICY_IDS.get(score.policy_id)


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
        "The target prices a broader reform than the model builds. Treasury's "
        "FY2025 Green Book chapter (report p. 2) states 'The effective global "
        "intangible low-taxed income (GILTI) rate would increase to 14 percent "
        "under the proposal', and every edition since FY2023 carries that step "
        "inside the corporate-rate row, while the factory scored against it "
        "sets gilti_rate_change=0.0. The GILTI leg is never printed separately "
        "and cannot be differenced across editions, so the reported error "
        "measures a scope mismatch as well as a fit.",
    ],
    "biden_corporate_28_fy2022": [
        "Scored across a window offset: the target is Treasury's FY2022-2031 "
        "row on a 2021 baseline and this repository carries no 2021 vintage, "
        "so the corporate runner's own FY2025-2034 window is used. In reported "
        "mode the rate channel is a flat annual, so the model returns the same "
        "figure for either decade - which is the residual this benchmark "
        "exists to show, not an artefact of the offset.",
    ],
    "trump_corporate_15": [
        "The target is a published range rather than a point: PWBM's +$595B "
        "and Tax Foundation's +$673.1B for 21% to 15% across all "
        "corporations, both FY2025-2034 conventional, with Tax Foundation's "
        "carried as the anchor. Until 2026-09-05 the target was this model's "
        "own +$1,920B.",
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
    "biden_high_income_tax": [
        "Scored on all four of the thresholds the Green Book prints (report p. 78): "
        "$450,000 joint and surviving spouses, $425,000 head of household, $400,000 "
        "unmarried, $225,000 married filing separately. This is the one row in the "
        "battery whose base GREW under the filing-status split - the separate-return "
        "floor is $175,000 BELOW the unmarried one, so those returns had been "
        "under-counted, not over-counted - and the row moved 12.0% to 9.2%.",
        "The thresholds are on taxable income and SOI's classes are on AGI. The "
        "thresholds are C-CPI-U indexed after 2024 by the proposal's own text and "
        "the model's do not move; the base now does, so the two no longer push the "
        "same way. This is a registered regression of the base-growth lane: the row "
        "was 9.2% UNDER and is now 18.0% OVER, because it had been under-predicting "
        "by less than a decade of nominal growth is worth "
        "(planning/lanes/HSB_h2_base_growth.md section 3.2).",
    ],
    # -- The base-growth lane's four registered regressions on rule-of-thumb
    # targets. Each of these rows under-predicted by LESS than a decade of the
    # baseline's own nominal growth is worth, so projecting the base onto the
    # years being scored carried it across its target. None was tuned back and
    # no target was touched; see planning/lanes/HSB_h2_base_growth.md section
    # 3.2, and section 3.3 for what these four targets actually are.
    "illustrative_1pp_all": [
        "Lane R2 moved this target onto the document its own record already "
        "described. -$960.0B was a rule of thumb ('1pp ~ $85-100B/year') in no "
        "JCT publication; the figure is now CBO publication 58164, Options for "
        "Reducing the Deficit: 2023 to 2032, Volume I, Option 13 alternative 1, "
        "'Raise all tax rates on ordinary income by 1 percentage point', "
        "-$1,081.3B over FY2023-2032 (report p. 72), 'Data source: Staff of the "
        "Joint Committee on Taxation'. The prediction did not move - the model "
        "scores the same -$1,195.3B it did - so 24.5% to 10.5% is the target "
        "finding its document and nothing else.",
        "MOST OF WHAT IS LEFT IS THE WINDOW, and the size is published rather "
        "than argued. The target covers FY2023-2032 and the runner opens its "
        "window in FY2025; CBO's own 2022 and 2024 editions price the identical "
        "reform at -$1,081.3B and -$1,185.3B, $104.0B apart (9.6%) for nothing "
        "but two years of base. FY2022_TARGET_WINDOW_RULE would close it with "
        "scoring_window_first_year=2023, which moves a model output and is "
        "therefore a .v3 the owner registers, not a provenance lane's to take.",
        "Read this row beside cbo_opt45_all_rates_1pp rather than as an "
        "independent observation. They are the same reform in two Options "
        "volumes, scored on one window with one shape, so the pair measures the "
        "model's insensitivity to the decade (-$1,195.3B here against "
        "-$1,207.3B there, 1.0% apart, where CBO's two figures are 9.6% apart) "
        "rather than two separate predictions. A third edition exists and gives "
        "a third figure: CBO 2020 (pub. 56783) Option 1 alternative 1 prices it "
        "at -$884.0B over FY2021-2030.",
        "Real bracket creep is still not modelled and pushes the other way, so "
        "part of the over-prediction against this target is a term the model is "
        "missing rather than one it added.",
    ],
    "illustrative_top_rate_5pp": [
        "RETIRED in lane R2 (no publication prices a +5pp top rate above "
        "$1,000,000 - not TPC, and not the individual-rate option of any of "
        "the four CBO Options volumes). The row is no longer scored; the "
        "reason is the absence of a document, never the size of the error, "
        "and the searches are in preregistered.py and benchmark_sources.py. "
        "The notes below are kept so the withdrawal does not erase what the "
        "row had recorded.",
        "Illustrative TPC-range target with no source URL, and internally "
        "inconsistent with top_rate_45 from the same source (retired in Phase E "
        "for exactly that reason). Part of this row's error is target error.",
        "A registered regression of the base-growth lane: 7.4% under to 20.2% "
        "over, because the row was under-predicting by less than a decade of "
        "nominal growth is worth.",
        "The record contradicts itself about its own base, and the row is left "
        "where it is because of that. cbo_scores.py says 'TPC scores this on "
        "taxable income that includes the preferential (LTCG/QDIV) portion'; an "
        "earlier version of this note said the surtax is stated on AGI. Neither "
        "can be checked, because the target carries no source URL. AGI_BASE_RULE "
        "moves a row only where its own source says AGI in as many words, so this "
        "one keeps the taxable-income column - and the figure is published rather "
        "than buried: on the AGI column it would score -$991.2B, or 41.6%. A page "
        "reference either way moves it.",
        "A single ETI (0.25) with the standard 0.5 factor erodes a 5pp top-rate "
        "increase by only ~12.5%; published top-rate estimates assume a larger "
        "response at that rate level, which would take this row back down.",
    ],
    "illustrative_500k_2pp": [
        "RETIRED in lane R2 (no publication prices a 2pp rate cut above "
        "$500,000, and CBO's Options volumes are deficit-reduction menus that "
        "contain no rate cut at all). The row is no longer scored; the reason "
        "is the absence of a document, never the size of the error, and the "
        "searches are in preregistered.py and benchmark_sources.py. The notes "
        "below are kept so the withdrawal does not erase what the row had "
        "recorded.",
        "Illustrative TPC-range target with no source URL. A registered "
        "regression of the base-growth lane: 8.9% under to 18.3% over.",
        "The base stays TAXABLE INCOME on the record's own words - 'TPC scores "
        "this on taxable income that includes the preferential (LTCG/QDIV) "
        "portion' - which is a different statement from agi_inclusive_base=True, "
        "and is why AGI_BASE_RULE leaves it. On the AGI column it would score "
        "+$556.6B, or 39.2%. It is also a rate CUT, so the remaining terms point "
        "opposite ways here relative to the raisers in this family.",
    ],
    "medicare_surcharge_2pp": [
        "RETIRED in lane R2 (Treasury's proposal is 1.2pp and prints "
        "$403,790M; -$310.0B is in no Green Book row for it). The row is no "
        "longer scored; the reason is the absence of a document, never the "
        "size of the error, and the searches are in preregistered.py and "
        "benchmark_sources.py. The notes below are kept so the withdrawal "
        "does not erase what the row had recorded.",
        "The largest registered regression of the base-growth lane: 1.5% to 31.8%. "
        "The row was within 1.5% of Treasury's figure with a base held at its 2023 "
        "tax year for a FY2025-2034 window, which means it was carrying an "
        "offsetting over-statement of about the same size - the model prices 2pp on "
        "ALL income above $400,000 where the Green Book's surcharge reaches "
        "investment and wage income through the NIIT/Medicare base, and the "
        "published row is a net of interactions the model does not build. The 1.5% "
        "measured the cancellation, not the fit.",
        "The target is a Green Book row promoted from CBO_SCORE_MAP rather than a "
        "line item transcribed with a page reference, so part of the gap is "
        "provenance. Sizing the base difference needs the surcharge's own statutory "
        "base and is not this lane's.",
        "AGI_BASE_RULE deliberately does NOT move this row to SOI's AGI column, "
        "because its source states a base that is neither SOI column: wages plus "
        "net investment income is not AGI (which also carries proprietors' "
        "income, pensions and IRA distributions, less above-the-line deductions) "
        "and is not taxable income (which is net of the standard or itemised "
        "deduction and of QBI). On the AGI column it would score -$522.2B, or "
        "68.4%, so leaving it is ALSO the lower number, which is why the decision "
        "is recorded here rather than left implicit. What this row needs is the "
        "surcharge's own base, not a choice between two columns that are both "
        "wrong for it.",
    ],
    "warren_ultramillionaire_surtax_3pp": [
        "RETIRED in lane R2 (TPC's AGI-surtax simulation is thirteen tables "
        "and all of them are 10 percent; Warren's own proposal is a wealth "
        "tax). The row is no longer scored; the reason is the absence of a "
        "document, never the size of the error, and the searches are in "
        "preregistered.py and benchmark_sources.py. The notes below are kept "
        "so the withdrawal does not erase what the row had recorded.",
        "The base is now AGI, on the record's own description ('3 percentage "
        "point surtax on AGI above $2 million') and its own note ('the surtax "
        "applies to AGI, which contains the preferential LTCG/QDIV portion'). "
        "SOI publishes both columns and above $2,000,000 the AGI average exceeds "
        "the taxable-income average by 18.6%, so this is a REGISTERED REGRESSION "
        "and the largest single deterioration AGI_BASE_RULE produces: 5.2% to "
        "24.8% over. It is kept at the honest number, because a rule that moved "
        "a row only when the move improved it would not be a reading of the "
        "sources.",
        "Most of what is left is target error. The figure is secondhand - a "
        "TPC-range estimate behind a bare taxpolicycenter.org URL, promoted from "
        "CBO_SCORE_MAP, with no table and no page reference - on a FY2021-2030 "
        "window scored here on FY2025-2034. It is one of the four rule-of-thumb "
        "targets in this tier (planning/lanes/HSB_h2_base_growth.md finding 3), "
        "and whether it is revised, examined-and-left or retired is a target "
        "decision that belongs to the provenance ledger, not to a modelling "
        "lane.",
        "A single ETI (0.25) with the standard 0.5 factor erodes a 3pp surtax at "
        "the very top by 12.5%, and published estimates of a broad-base surtax on "
        "AGI above $2M assume a larger response at that income level, which would "
        "take this row back down. Nothing here was tuned to it.",
    ],
    "top_rate_45": [
        "The uncalibrated path applies a single ETI (0.25) with the standard 0.5 factor, "
        "so an 8pp top-rate increase erodes by only ~12.5%; published top-rate estimates "
        "assume a much larger response at that rate level.",
        "The -$420B target is secondhand (a 'TPC-range' figure with a bare taxpolicycenter.org "
        "URL) and is internally inconsistent with illustrative_top_rate_5pp from the same "
        "source (+5pp above $1M = -$700B), so part of this error is target error.",
    ],
    "biden_capital_gains_39": [
        "The target is Treasury's single combined row - the rate change and the "
        "realization-at-death change together - and the model's two channels "
        "split it $359.0B of rate against $7.4B of death. The rate channel "
        "alone therefore exceeds the whole published figure by 24.4%, which is "
        "where this row's residual now lives and is a floor no change to the "
        "death channel can get under. It over-predicts by 27%; before Wave 5 "
        "projected the realizations base it under-predicted by 17%, on a base "
        "two years stale and never grown.",
        "The death channel is integrated over a fitted size distribution of "
        "estates at death rather than five class means (Wave 7), which moved it "
        "$20.2B to $24.2B: with dispersion the top of the 99th-99.9th percentile "
        "band clears the $5,000,000 per-donor exclusion that its class average "
        "of $1.9M after reliefs never did. Wave C then took it $24.2B -> $7.4B "
        "by counting decedents at an NCHS life-table rate instead of at a flow "
        "of estate dollars, 3.38 million a year against 408,532: the same flow "
        "over 8.3 times as many decedents leaves far less of each gain above a "
        "$5,000,000 exclusion. That improved this row 32.8% -> 27.0% and "
        "worsened cbo_opt51_gains_at_death, which is the trade a level change "
        "to this channel makes. Neither move is where the residual lives.",
        "At +19.6pp the semi-log response is evaluated well up its own curve: "
        "eliminating step-up divides the coefficient by the lock-in wedge, so "
        "b = 2.27 and the revenue-maximizing rate is 44.1% against a reform rate "
        "of 43.4%. Treasury's own estimate implies a much stronger response than "
        "the frozen literature value gives at that rate, and owner Decision 3 "
        "freezes the value.",
        "The $1,000,000 threshold is not indexed, so the projected base is the "
        "above-$1M slice measured in tax-year-2023 AGI. Real bracket creep would "
        "push more gains across a fixed nominal threshold, which understates the "
        "base growth on a row that already over-predicts.",
    ],
    "treasury_capgains_39_plus_stepup_elim": [
        "The same shape as biden_capital_gains_39 - +19.6pp above $1M plus "
        "realization at death - against a COMBINED FY2022 Green Book row, and "
        "since PR #126 scored on the ten fiscal years that document covers "
        "(scoring_window_first_year=2022, the "
        "treasury_capgains_39_plus_stepup_elim.v2 manifest row; the target is "
        "unchanged at -$322.0B and only the shape input moved). On FY2022-2031 "
        "the rate channel is $303.1B and the death channel $13.0B under this "
        "design's $1M per-donor exclusion. The row read 0.2% before Wave 5 "
        "projected the realizations base, and that agreement was already "
        "documented as two errors cancelling "
        "(planning/lanes/W4_gains_at_death.md section 8.4); one of the two was a "
        "tax-year-2023 base priced unchanged in every year of the window.",
        "The window is worth 14.9 points, not the 'about 17' an early version of "
        "this note claimed and not the 27.0 the version before Wave C did - the "
        "offset shrank with the death channel, because the channel it discounts "
        "is smaller once the decedent count is a life-table rate. Re-scoring the "
        "same shape on the default FY2025-2034 decade returns -$375.8B and "
        "16.7%, against -$316.1B and 1.8% on FY2022-2031; "
        "scripts/window_offset_capgains.py prints both. "
        "The old figure discounted the RATE channel only "
        "(359.02 x 0.844354 + 102.45 = 405.6) and missed that the death channel "
        "grows with the same 5.80% net-worth CAGR and that it does not grow "
        "proportionally, because a fixed nominal per-donor exclusion is a step "
        "function whose bite moves faster than the stock it is subtracted from. "
        "PR #126 measured the offset at 28.7 of 43.3 points and PR #132's "
        "decedent ladder took the merged figure to 27.0 of 45.4; Wave C's "
        "headcount took it to 14.9 of 16.7. The control is "
        "biden_capital_gains_39 - same module, same frozen elasticities, an "
        "FY2025 target on the FY2025 window - whose offset is exactly zero to "
        "the cent. See planning/memos/FY2022_TARGET_WINDOW.md.",
        "1.8% is not accuracy, and the cancellation is larger than it was. On "
        "its own decade the row is a net: the model books $0.0B of revenue "
        "across FY2022-2024 where Treasury books $66.0B - the model's enactment "
        "year is a $61.4B transitory revenue LOSS against Treasury's $7.7B "
        "gain, because the module has no receipts lag - against $316.2B across "
        "FY2025-2031 where Treasury books $256.5B. A 23% over-prediction on the "
        "later seven years and a $66B hole in the first three net to 1.8%; read "
        "the annual path, not the total. Treasury's own answer for this row is "
        "not "
        "stable either: $322,485M, $174,488M, $213,855M and $288,583M across "
        "four consecutive Green Books, spanning 85%.",
        "The gap between this row and biden_capital_gains_39 is the per-donor "
        "exclusion alone - $1M against $5M - and the model's price for that step "
        "on the common FY2025-2034 decade has now crossed the published one. "
        "Wave 4 blamed the five-class ladder for an $82.3B step against the two "
        "published rows' $33.4B; Wave 7 replaced the ladder with a fitted size "
        "distribution and the step went to $85.0B, the wrong way, so dispersion "
        "was not the cause (planning/lanes/W7_decedent_ladder.md section 8). "
        "Wave C corrected the headcount, which W7 named as the real lever, and "
        "the step is now $9.4B - through $33.4B and out the other side, a third "
        "of it rather than two and a half times it. The two published rows are "
        "also on different windows, which makes $33.4B an understatement of the "
        "step Treasury itself paid, so the overshoot is larger than $9.4B "
        "against $33.4B makes it look. See "
        "planning/lanes/HSC_h5_decedent_headcount.md section 8.",
        "The earlier note here cited a -$456B companion target that Phase E "
        "retired; it appears in no Treasury volume, so there is no "
        "published-disagreement floor under this row.",
    ],
    "cbo_opt56_employer_health_income_only": [
        "The excess share is now year-indexed (Wave 4 lane 3a), which is what CBO's "
        "own text specifies: the limit grows with a price index while premiums grow "
        "with health costs, so a widening slice of every premium sits above it. That "
        "took the row from 24.0% to 13.1% and the model's revenue growth from 4.0%/yr "
        "to 8.3%/yr against CBO's 14.4%/yr. The remaining shape gap is the two items "
        "below; neither is a parameter.",
        "The base is premiums only. CBO caps 'the total amount of contributions for a "
        "worker's premiums and health spending accounts' (pub. 60557, report p. 66), "
        "and the repository's premium distribution has no flexible-spending, health "
        "reimbursement or health-savings-account dimension, so the dollars above the "
        "limit are understated by whatever those contributions add.",
        "No plan-switching channel. CBO's own text names enrolment in lower-premium "
        "plans as the dominant behavioural response, which converts excluded premium "
        "into taxable wages; the module carries only a flat 0.2 elasticity. The "
        "option states the direction and publishes no magnitude, so a value for it "
        "would have to be fitted to this row.",
        "The limit's indexation uses the baseline's own price path in place of the "
        "chained CPI-U the option names, because the repository carries no "
        "chained-CPI-U series. CBO projects both near 2.0% over 2028-2034.",
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
        "Neither a spend-out, a level-shape nor a window miss since "
        "iija_2021_discretionary.v3. The shape is the source's own authorization "
        "schedule ($163.0B of budget authority in FY2022, then $70.1B, $68.5B, "
        "$68.1B, $66.2B and $2.08B/yr, summing to CBO's stated $446.3B), spent "
        "out on the construction_and_capital profile, and scored on FY2022-2031 "
        "- the decade CBO's own estimate covers and the record's budget_window "
        "has stated since it was entered. It returns +$414.3B against +$415.4B, "
        "0.3%.",
        "What is left is a 4.5% over-statement of the TOTAL netting against the "
        "tail the window still clips, and neither term is behavioural. Outlays "
        "across every year the policy touches are $434.1B, which is the "
        "profile's 0.9727 spend-out sum applied to the full $446.3B of "
        "authority; $19.8B of them fall in FY2032 or later, outside even this "
        "window. The two nearly cancel, so 0.3% is smaller than either term and "
        "should not be read as evidence about the spend-out profile. The honest "
        "statement is that the authority path is CBO's own and the profile "
        "reproduces its total to 4.5%. (Earlier revisions of this note said "
        "$433.2B and 4.3%; the measured total is $434.1B.)",
        "CBO's own table is headed FY2021-2031, eleven fiscal years, and a "
        "ten-year window cannot cover eleven. FY2021 is not a gap: the bill was "
        "signed on 15 November 2021, inside FY2022, and the record's own "
        "budget_window has read FY2022-2031 since it was entered - which is "
        "what FY2022_TARGET_WINDOW_RULE reads, so the window is not a per-case "
        "judgement about which eleventh year to drop.",
        "It needed a WINDOW, not a VINTAGE, and an earlier version of this note "
        "named the wrong blocker. A discretionary SpendingPolicy scores its own "
        "source-stated authority and reads no baseline LEVEL, so the "
        "CBOScore.scoring_window_first_year mechanism PR #126 built for "
        "treasury_capgains_39_plus_stepup_elim scores this bill on FY2022-2031 "
        "with no 2021 vintage in the repository. On the runner's FY2025-2034 "
        "decade v2 read 18.2%, because $92.6B of the path's outlays fall in "
        "FY2022-2024 before that window opens. The number was published in "
        "planning/memos/FY2022_TARGET_WINDOW.md section 6 before the decision "
        "was taken, so that taking it would be a visible choice.",
        "This row does NOT claim a 2021 information set. The outlay profile is "
        "the one fitted on CBO's own donor options (lane L2), and the years "
        "FY2022-2024 are priced with it today rather than forecast in 2021. "
        "What the window fixes is that the ten fiscal years scored are the ten "
        "the target covers.",
        "The superseded rows are kept in preregistered.py: v1 (a level carried "
        "forward at 2%/yr) at +$1,894B / 356% and post-spend-out +$1,621B / "
        "290%, and v2 (the authorization path on the runner's window) at "
        "+$340.0B / 18.2%. Between them the three rows separate the three "
        "defects this case surfaced - the missing spend-out model (L2), the "
        "missing authorization path (v2) and the window (v3).",
    ],
    # -- Phase B: CBO Options for Reducing the Deficit, 2025-2034 -----------
    # Out-of-sample battery. Every miss below is kept and explained; none of
    # these cases had a parameter moved to close its gap.
    "cbo_opt45_all_rates_1pp": [
        "Scored on the SOI ordinary-income base with a single ETI (0.25). The base "
        "is now projected from its SOI tax year onto each year being scored, on the "
        "February 2024 vintage's own nominal path (1.0962x in FY2025 to 1.5438x in "
        "FY2034, 1.3118x on the window average), which took this row from 22.4% "
        "under to 1.9% over. This is the control for the base-growth lane: it is "
        "the row whose target is CBO's own published option on the very window "
        "being scored, and the growth term alone closes it.",
        "What is left is real bracket creep, which pushes the other way and is not "
        "modelled: JCT's estimate rises through the window partly because rising "
        "income moves into higher rates, and a uniform index cannot reproduce that. "
        "Note also that illustrative_1pp_all scores the SAME reform against a "
        "different published figure, -$960.0B against -$1,185.3B, 23.5% apart; the "
        "model cannot agree with both.",
        "This row declares bracket 1 of the statutory schedule and scores to the "
        "cent what it scored before, because bracket 1's floor is $0 in every year "
        "of every vintage. That is not filler: the declaration takes the whole "
        "schedule path end to end - four per-status floors read per year, deflated "
        "onto the SOI base year, scored through the filing-status split - and a $0 "
        "floor must come back out the other side unchanged. If this row ever moves "
        "by a cent, the schedule is perturbing something nobody asked it to touch.",
    ],
    "cbo_opt45_top4_brackets_2pp": [
        "The filing-status boundary is now the option's own: joint returns and "
        "surviving spouses face the 2025 24%-bracket floor of $206,700 and every "
        "other status $103,350 (IRS Rev. Proc. 2024-40 section 2.01, tables 1-4). "
        "That took the row from a 17.9% OVER-prediction to a 12.4% under-prediction "
        "- it removed 25.7% of the base, which was more than the gap.",
        "The threshold now moves in 2026, which the option says it should. CBO's "
        "own text: 'Under both alternatives, the scheduled changes to the underlying "
        "tax brackets and rates would still take effect in 2026', after which the "
        "four highest brackets are 28/33/35/39.6 percent and the boundary is the 28% "
        "floor. The boundary is read per year and per filing status from CBO's own "
        "published schedule (publication 53724, June 2024 edition on this record's "
        "February 2024 vintage) - the table this note used to say does not exist. "
        "The reversion is not a uniform shift: bracket 4's joint floor falls 3.5% "
        "in CY2026 while its head-of-household floor rises 65.5% and its single "
        "floor 15.9%, so a scalar threshold could not have expressed it and neither "
        "could a scalar plus one joint amount.",
        "The floors are statutory boundaries on TAXABLE income and SOI's size "
        "classes are by AGI, so the base is 'returns whose AGI clears the bracket "
        "floor' rather than 'taxable income above it'. That predates the "
        "filing-status lane and is unchanged by it.",
        "The base is now projected onto the years being scored rather than held at "
        "its SOI tax year, which took the row from 12.4% under to 14.9% over - a "
        "registered regression, because it was under-predicting by less than a "
        "decade of nominal growth is worth.",
        "Reading the schedule was a second registered regression and the plan's "
        "stated direction for it was backwards: the row over-predicts, so it went "
        "FURTHER OVER rather than further under. It decomposes into two terms "
        "pointing opposite ways, both of which the base projection created and "
        "neither of which it could resolve. Deflating the boundary into the SOI "
        "base year's dollars - the unit conversion that projection implies, since "
        "scaling the base by g is the same as indexing the threshold by g - is "
        "worth -$68.4B, because the statute indexes on chained CPI and the base "
        "grows on nominal GDP. The 2026 reversion is worth +$48.1B. The net is "
        "-$20.2B, 3.6 points of error. Applying the year's nominal boundary to a "
        "TY2023 income instead - comparing a 2031 threshold to a 2023 return - "
        "would score this row at 3.6%, and that figure is recorded here because "
        "it is what two errors cancelling looks like, not because it is available.",
    ],
    "cbo_opt46_agi_surtax_1pp_20k": [
        "The $20,000 single / $40,000 joint threshold is now the option's own, "
        "applied per filing status against an SOI base split the same four ways "
        "(Table 1.2, TY2023). It removed the 46.1M joint returns' $20,000 of "
        "wrongly-taxed income - $839.8B, 9.2% of the base - and the row got WORSE, "
        "44.7% to 49.8%, because that error was cancelling two larger ones. It is "
        "kept at the honest number rather than reverted.",
        "The base is now projected from its SOI tax year onto each year being "
        "scored, on the February 2024 vintage's own nominal path (1.3118x on the "
        "window average), which took the row 49.8% to 34.1%. It is the largest "
        "single move this row has had and it is not enough on its own.",
        "The base is now AGI, which is what the option says: 'a surtax of 1 "
        "percentage point would be imposed on AGI above $20,000 for single "
        "filers and $40,000 for joint filers'. SOI Table 1.1's rows are AGI size "
        "classes and it publishes both columns, so this branch had been "
        "subtracting an AGI threshold from an average of TAXABLE income - "
        "$92,658 minus $20,000, where the single-filer AGI average above that "
        "floor is $120,414. Reading the column the option states took the row "
        "34.1% to 7.4% (AGI_BASE_RULE). It is applied INSIDE the filing-status "
        "split rather than to the pooled aggregate: the split ratio here is "
        "1.4052 where the pooled one is 1.3820, and on the 2pp alternative the "
        "two move opposite ways.",
        "That was the third of the three terms W7 finding 1 measured, and the "
        "three together land at 7.4% rather than the '9.1%' "
        "planning/HIGH_STAKES_ACCURACY.md section 1.3(c) quotes. W7 computed its "
        "endpoints by hand on a pre-projection tree; both the growth term and "
        "the AGI term were rebuilt as mechanisms afterwards, and a mechanism "
        "does not have to reproduce a hand calculation to be right.",
        "The projection indexes the threshold with the base. Scaling the aggregate "
        "above a fixed nominal floor by a factor f is arithmetically the same as "
        "indexing that floor by f, so the term is a lower bound on the growth of an "
        "unindexed-threshold base and this row stays under for that reason too.",
        "No behavioural distinction between a broad low-threshold surtax and a "
        "narrow high-income one: both erode by ETI x 0.5.",
    ],
    "cbo_opt46_agi_surtax_2pp_100k": [
        "Same three residuals as the 1pp alternative, and this row is where they are "
        "visible: its 16.1% before the filing-status split was TWO ERRORS CANCELLING "
        "A THIRD. Starting 11.1M joint returns $100,000 below their own floor added "
        "34% of base; a taxable-income base rather than AGI and a decade of no "
        "growth each removed about 22%. Splitting the floors alone therefore takes "
        "the row 16.1% to 37.4%, and the old number measured the cancellation rather "
        "than the fit - the same finding fra_2023_discretionary_caps produced when "
        "spend-out landed.",
        "Both remaining terms are now in. The base is projected from its SOI tax "
        "year onto each scored year at 1.3118x on the window average (37.4% to "
        "17.9%), and it is then read from SOI's AGI column, which is what the "
        "option says (17.9% to 2.9% OVER, crossing the target). All three terms "
        "were measured before any of them was built and each landed where it was "
        "pre-registered, so the 16.1% this row showed before the filing-status "
        "split is now decomposed rather than argued about.",
        "At 2.9% this row is the closest non-spending case in the out-of-sample "
        "tier, and that is not evidence the AGI-inclusive family is solved: three "
        "of the six rows carrying agi_inclusive_base keep the taxable-income "
        "column because their own sources state it, or state a base that is "
        "neither SOI column, and they sit at 31.8%, 20.2% and 18.3%.",
        "The thresholds are indexed after 2025 by the option's own text and the "
        "model's are not. The projection indexes them implicitly, at its own rate "
        "rather than the option's, which is a lower bound on the base of an "
        "unindexed floor and not a match for an indexed one.",
    ],
    "cbo_opt47_ltcg_qdiv_2pp": [
        "The realizations base is projected across the window from its IRS SOI "
        "tax year at the accrued-gains stock's own growth rate (5.80%/yr, Federal "
        "Reserve DFA 1998-2024), on the identity that realizations are a flow off "
        "that stock at the observed hazard. Until Wave 5 it was held flat, which "
        "was most of a 44.8% under-prediction. The rate is a net-worth CAGR "
        "carried forward, not a realizations projection - CBO's own baseline has "
        "realizations returning toward a historical share of GDP - and tax year "
        "2023 is a trough: the vendored aggregate reads $1,283.6B (2022), $943.4B "
        "(2023), $1,368.1B (2024). So the level anchor is probably low and the "
        "growth possibly high, in opposite directions, and neither is corrected.",
        "The enactment year is scored at full strength against a fiscal year CBO "
        "scores at a fraction of one. The module's FY2025 rate channel is "
        "negative, because the enactment-year coefficient (8.06, the persistent "
        "3.27 plus the transitory term on the timing-margin share) takes "
        "realizations down 14.9% in a single year; CBO's FY2025 is +$2.4B against "
        "its own +$8.3B for FY2026, which is what a calendar-year tax paid at "
        "filing looks like in fiscal-year receipts. This module has no receipts "
        "lag, and building one is a scoring-engine change that would move every "
        "row in the battery.",
        "Inverting CBO's own published annual path is the check on the frozen "
        "elasticity rather than a limitation of it: on a projected base its "
        "out-years imply a semi-log coefficient of 3.0-3.2, against the frozen "
        "3.2727 (Dowd, McClelland & Muthitacharoen 2015 at CRS R48562's 22% "
        "reference rate) and JCT's own working 3.1. On a flat base the same "
        "inversion gives a coefficient falling from 4.17 to 1.81 across the "
        "window, which no scorekeeper's method produces.",
        "The +2pp does apply to the 0% bracket ($80.7B, 7.29% of the base), and "
        "that is the option's own design - it raises all three preferential "
        "rates. An earlier note here claimed the opposite and used it to explain "
        "an over-prediction; dropping the bracket moves the row further under, "
        "not closer.",
    ],
    "cbo_opt51_gains_at_death": [
        "The whole score is the death channel: the option changes no rate and "
        "states no per-donor exclusion, so it is the one row that tests the "
        "level of gains transferred at death rather than a design. The $54B "
        "constant an earlier note here described was deleted in Wave 2; the base "
        "is now Poterba & Weisbenner's flow carried as a share of household net "
        "worth and grown with the Financial Accounts stock, $196.2B in 2025.",
        "It under-predicts by 35%, and every point of that was bought back "
        "deliberately. Wave 4 registered a regression from 8.4% when it stopped "
        "taxing charitable bequests and small decedents' housing gains, which no "
        "realization-at-death regime reaches; Wave 7 added a further point by "
        "integrating over a fitted size distribution, which shifts gains toward "
        "estates whose charitable share is 36% rather than 4%; and Wave C added "
        "fifteen more, pre-registered, by correcting the decedent count (below).",
        "The decedent headcount was the coarsest thing left in the channel and "
        "is now a life-table rate: 3.38 million a year against roughly 3.09 "
        "million NCHS deaths, where it was 408,532 from Poterba & Weisbenner's "
        "*dollar* flow of estates over net worth used as a headcount rate. That "
        "took this row 20.3% -> 35.5% and is a registered regression, because "
        "the count and the LEVEL come from the same PW ratio and only the count "
        "was authorised to move: spreading an unchanged $196.2B flow over 8.3 "
        "times as many decedents shrinks the gain each one carries, so the "
        "carve-outs and the statutory rate ladder reach less of it. The level is "
        "the other half of the correction and would move this row back: held "
        "against the module's own death_exit_rate, the flow implies 0.372% of "
        "the accrued-gains stock where the stock's death exit is priced at "
        "2.647%. How much of that factor of 7.1 is PW's inter-spousal exclusion "
        "and how much is the 1998 vintage is unmeasured - "
        "planning/lanes/HSC_h5_decedent_headcount.md SS7.",
        "Grading the death rate by estate size was measured and refused rather "
        "than left unexamined. The wealthy are older, so they die at a HIGHER "
        "rate: the size-graded rate at the top of the wealth distribution is "
        "2.84% against the 2.65% now used, so grading would raise the top count "
        "rather than lower it toward SOI's own return count. Both figures are "
        "emitted as CHECK-ONLY rows by scripts/build_capital_gains_data.py.",
        "No lock-in unwind: constructive realization at death removes the incentive "
        "to hold appreciated assets, which raises lifetime realizations. The module "
        "models that channel only through an elasticity multiplier that a zero rate "
        "change leaves inert.",
    ],
    "cbo_opt61_new_payroll_tax_1pct": [
        "A third of the residual is the first fiscal year alone: the option takes "
        "effect in January 2025, so nine of FY2025's twelve months are inside it and "
        "the model books 0.75 of a year, where CBO's own FY2025 row is 0.48 of its "
        "FY2026 row. The volume's income-tax options run 0.77-0.85 and its other "
        "payroll options 0.29-0.31, so there is no stated convention to read off and "
        "0.75 is the calendar rather than a fitted lag.",
        "The rest is base growth. The model prices covered earnings off CBO's own "
        "February 2024 wage path, which grows 3.9%/yr; the base implied by CBO's "
        "published revenue row grows 3.45%/yr, so the model drifts from +3.2% in "
        "FY2026 to +7.2% in FY2034. Nothing in the option text says why CBO's base "
        "grows more slowly than CBO's wages.",
        "The compensation-shifting response uses the repository's frozen ETI of 0.25 "
        "against CBO's own 31% economywide marginal rate on labor income. Neither "
        "was chosen against this target; an ETI of 0.40 would land the row at 0.9%.",
    ],
    "cbo_opt61_new_payroll_tax_2pct": [
        "Same base, incidence and shifting response as the 1% alternative, so the "
        "same three residuals apply. The model is very slightly convex in the rate "
        "(the shift grows with it) where CBO's row is very slightly concave, which "
        "is why the two errors differ by half a point rather than not at all.",
    ],
    "cbo_opt64_corporate_rate_1pp": [
        "Scored in the corporate module's derived mode, so the base is not the "
        "fitted profits aggregate. Since PR #121 it is CBO's own projected "
        "corporate receipts path (publication 59710 Table 1-1) converted to a "
        "statutory base at one ratio measured on completed history - IRS SOI "
        "Table 11's credit-realized TY2022 base over Treasury's actual FY2022 "
        "receipts, 4.80133, which is 1.0083 / 0.21 - and settled on IRC "
        "section 6655's estimated-payment calendar. That base is about a "
        "quarter larger than the fitted one in the window's first year, so "
        "the derived path over-predicts this row by MORE than the fitted path "
        "did, while reproducing the 21%->28% benchmark to 4.04%.",
        "The residual is an ESTIMATOR difference and a SCOPE difference, not "
        "the 42% document gap an earlier version of this note claimed. Both "
        "halves are corrected by "
        "`planning/memos/CORPORATE_PER_POINT_YIELD.md`. (1) This option is a "
        "JCT estimate that CBO publishes - every corporate-rate option in "
        "every Options volume carries 'Data source: Staff of the Joint "
        "Committee on Taxation' - so the comparison with Treasury's Green "
        "Book row is JCT against Treasury OTA, not CBO against Treasury. "
        "(2) Treasury's row is not rate-only: since the FY2023 edition it "
        "carries the GILTI effective rate up with the statutory rate, and its "
        "own chapter says so. (3) Per-point dollars are not comparable across "
        "rate levels or scopes anyway; on the implied marginal base "
        "(|total| / step / 10, as a share of the vintage's own average base) "
        "the record is four estimators clustered and one high - Tax "
        "Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury (rate + GILTI) "
        "79.5% - and this model reads 80.8% at +1pp and 76.1% at +7pp since "
        "PR #121 projected the base off the vintage's own receipts path, above "
        "all four at the small step and above three of the four at the large "
        "one. "
        "There is also NOTHING in the record supporting a per-point yield "
        "that rises with the step: where one estimator prices a big step and "
        "a small one, JCT's 14-point cut from 35% and its 1-point increase "
        "from 21% imply marginal bases of $963.2B and $963.0B.",
        "Option 64 carries NO income-and-payroll-tax offset footnote, though "
        "the facing Option 63 does. An earlier version of this note called "
        "the individual-side interaction 'the largest single unmodelled "
        "channel'; JCT does not apply one here either, so that channel is "
        "refuted as an explanation of this row rather than merely "
        "unmeasured. Two channels that would push the derived score down are "
        "still named and not built, because each needs a number nobody "
        "publishes. Credit CARRYFORWARDS: section 38(c) and section 904(c) "
        "limits rise with the rate, so marginal absorption exceeds the "
        "average ratio the module applies - and CBO's 2018 Option 24, the "
        "only volume with a narrative, names exactly this channel as "
        "included in JCT's estimate ('An increase in the corporate tax rate "
        "would increase corporations' ability to use tax credits ... That use "
        "of credits would reduce revenues'). Lane R5 DID the acquisition the "
        "previous note called for and the stocks exist: IRS Publication 5108 "
        "(TY2022, PDF pp. 164 and 166) prints Form 3800's carryforward into "
        "2022 at $91.16B (Part I line 4) plus $33.31B (Part II line 34), "
        "$124.47B against $72.17B of claims, and SOI's Corporate Foreign Tax "
        "Credit Table 1 prints a $174.44B section 904 limitation - 20.7% of "
        "its own $842.41B of foreign taxable income, so the mechanism is "
        "confirmed on published columns. What is STILL missing is the share "
        "of the base held by taxpayers in the constrained position: SOI's "
        "excess-credit and excess-limitation tables were published for TY2010 "
        "only and the series was discontinued, and the aggregate columns "
        "cannot identify the split (column 19 is limitation less credit by "
        "construction). So the channel is bounded rather than priced - see "
        "`corporate.credit_absorption_bounds` and "
        "`fiscal_model/data_files/corporate/credit_carryforward_stocks.csv`. "
        "The bound is informative: the section 904 channel at its own upper "
        "bound absorbs 28.85% of a marginal pre-credit dollar against the "
        "29.15% the derived path already books by substituting the average "
        "credit ratio for the marginal one, so the section 38(c) channel is "
        "ENTIRELY unbooked and points this row DOWN. CAMT: for a "
        "book-minimum payer a point of regular rate raises nothing until the "
        "regular tax clears the minimum; it began in TY2023, after the last "
        "SOI year on file, and no source publishes the taxable income of "
        "CAMT-liable corporations (Treasury's JY2574 gives ~100 payers and a "
        "2.6% counterfactual effective rate; JCT's 2022 letter to Chairman "
        "Wyden gives 175-200 corporations averaging $8.2B of book income in "
        "2019 - neither is a base).",
        "CBO's own loss-firm haircut was examined by lane R5 and REFUSED. "
        "`business-investment-model/source_code/Create_Tax_Data.prg:32-33` "
        "publishes `dmyrevnfc = 0.85` and `dmyrevx = 0.80`, derived from SOI "
        "2005, and applying 0.85 would take this row to 22.8% - inside that "
        "lane's own pre-registered band. It is not applied because it "
        "multiplies a statutory RATE in a user-cost expression while this "
        "path multiplies a BASE that already nets loss firms: SOI's income "
        "subject to tax is net of a net-operating-loss deduction running "
        "8.7-11.6% of the pre-NOL base against CBO's 12.8%, and CBO itself "
        "DIVIDES by the factor at `:172-175` wherever the other input already "
        "carries it, 'to avoid double-counting'. The pair is also not "
        "financial versus nonfinancial, as this repository's own plan said: "
        "0.80 is 0.85 further reduced by the nonprofit share of "
        "nonresidential investment, and there is no sector split in the "
        "source. `tests/test_corporate_loss_firm_haircut.py` is the gate.",
        "SOI's TY2022 base is inflated by two timing items that reverse - "
        "section 174 R&D capitalisation, which began that year, and the "
        "bonus-depreciation phase-down - and the memo sizes it: SOI's income "
        "subject to tax averaged 71.8% of NIPA pre-tax corporate profits over "
        "TY2019-2021 and 79.8% in TY2022, so TY2022's base is 11.1% above "
        "what the prior ratio implies. That is an upper bound, since it "
        "charges the whole ratio move to the timing items; deflating by it "
        "takes this row to about 46%, not to CBO's figure. The module anchors "
        "on the latest published complete report and does not adjust, and an "
        "earlier anchor year would score this row better - which is exactly "
        "why the year is fixed as 'latest published' rather than chosen.",
        "A fourth, smaller item: the module's section 6655 first-year factor "
        "is 0.757, where JCT's options run 0.591-0.732 first-to-second-year "
        "and Treasury's FY2022/FY2023 rows run 0.593/0.601. Treasury's is a "
        "statutory blend the module has no concept of; JCT's is unexplained, "
        "because no volume mentions payment timing anywhere.",
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


def _resolve_window_start(score: CBOScore) -> int:
    """The fiscal year the validation window opens on for this record.

    A record that names ``scoring_window_first_year`` - the first year of the
    window *its own source* published its total over - is scored on that
    decade, so the ten fiscal years scored are the ten the target covers.
    Everything else keeps :data:`DEFAULT_VALIDATION_START_YEAR`.

    A **window** is not a **vintage**. No shape that carries a window today
    reads a baseline level (``CapitalGainsPolicy.estimate_static_revenue_effect``
    opens with ``_ = baseline_revenue``), so this needs no historical baseline
    and does not pretend to supply one: the model still prices those years with
    today's SOI and Financial Accounts anchors. Which window a case carries is a
    pre-registered shape input under
    ``preregistered.FY2022_TARGET_WINDOW_RULE``, never a per-case knob.
    """
    return int(score.scoring_window_first_year or DEFAULT_VALIDATION_START_YEAR)


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
        ``score.agi_inclusive_base=True``, for AGI-inclusive surtaxes. Where the
        record's source states its boundary **per filing status**, those amounts
        are carried through as ``threshold_by_filing_status`` and the SOI base
        is split the same four ways, so each return faces its own floor rather
        than the single filer's; statuses the source does not name fall back to
        ``income_threshold`` under :data:`FILING_STATUS_THRESHOLD_RULE`.
    ``capital_gains``
        :class:`CapitalGainsPolicy` with the **module-default** elasticity set
        (Dowd, McClelland & Muthitacharoen 2015, persistent 0.72 / transitory
        1.2 at a 22% reference rate) and SOI auto-populated baseline
        realizations and rate. Deliberately *not* the per-case hand-set
        elasticity tuples in ``scenarios.py`` — this path is the uncalibrated
        prediction, so its behavioural parameters are frozen across cases. The
        death channel's *design* — whether the family-owned-business deferral
        applies — comes from the record's own document under
        :data:`GREEN_BOOK_DEATH_DESIGN_RULE`.
    ``corporate_rate``
        :class:`CorporateTaxPolicy` in the module's **derived** mode: the rate
        change applied to IRS SOI Table 11's published *income subject to tax*,
        realized at SOI's own after-credits/before-credits ratio, offset by one
        frozen profit-shifting semi-elasticity and settled on IRC section
        6655's estimated-payment calendar. Deliberately *not* the fitted
        ``BASELINE_TAXABLE_PROFITS_BILLIONS`` profits aggregate, which the
        module's own comment describes as calibrated to reproduce
        ``biden_corporate_28`` - routing an out-of-sample prediction through it
        would be leakage, which is why the mode is pinned here rather than left
        to the module's ``reported`` app default.
    ``payroll_rate``
        :class:`PayrollTaxPolicy` levying the rate as a **new flat tax on
        covered earnings** - all earnings with no taxable maximum, which CBO
        states is this option's base ("the income subject to the tax would
        match that of the Medicare payroll tax"). The base is CBO's own
        baseline wage path times one covered-earnings ratio measured on
        completed history, not a receipts aggregate divided by a statutory
        rate. Statutory incidence is taken from the source: CBO's own
        alternatives are paid entirely by employees, so the employer-share
        term - the one that would shrink the income and payroll bases - is
        zero. Deliberately *not* the Social Security cap machinery: those
        covered-wage bands are calibrated to reproduce the Trustees' own reform
        annuals, so routing a target through them would leak the answer.
    ``spending``
        :class:`SpendingPolicy` from the source-stated annual level, growth,
        phase-in and one-time flag.
    ``tax_expenditure``
        :class:`TaxExpenditurePolicy` in the module's **derived** mode, so the
        score is the published expenditure level times the share of it the
        reform denies — never the per-benchmark annual a factory fits to a
        target. The cap is read in dollars of the excluded or deducted
        quantity, exactly as the source states it. Routing this shape through
        ``reported`` mode would be leakage, which is why the mode is pinned
        here rather than left to the module's app default.

    Every shape honours ``score.effective_start_year`` - the year the *source*
    says the policy takes effect - so an option that starts in FY2026 is not
    credited with a year of effect the official estimate never scored. Failing
    that it takes :func:`_resolve_window_start`, so a case scored on its own
    published decade starts in that decade's first year rather than being
    truncated at its head.

    Returns ``None`` when the record has no constructible shape.
    """
    shape = validation_shape(score)
    if shape is None:
        return None

    start_year = score.effective_start_year or _resolve_window_start(score)

    if shape == "ordinary_rate":
        if ordinary_income_base is None:
            ordinary_income_base = not score.agi_inclusive_base
        # The AGI column only where the record's own source states AGI, and only
        # on the AGI-inclusive base it implies. A caller that FORCES
        # ``ordinary_income_base=True`` - which is what ``cold_holdout.py
        # --ordinary-base`` does to every generic row, in both directions - is
        # asking what the ordinary treatment gives, so it gets the ordinary
        # column too; the alternative is a contradiction TaxPolicy refuses.
        income_measure = (
            INCOME_MEASURE_AGI
            if (agi_base_source_sentence(score) is not None and not ordinary_income_base)
            else INCOME_MEASURE_TAXABLE_INCOME
        )
        # A record whose source calls the boundary a statutory bracket reads
        # the four per-status floors from CBO's own schedule for each scored
        # year, on that record's own vintage. Everything else keeps the
        # threshold it is written with, which is today's behaviour to the cent.
        # See :data:`STATUTORY_BRACKET_SCHEDULE_RULE`.
        statutory_bracket = score.statutory_bracket_index
        return TaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.INCOME_TAX,
            rate_change=score.rate_change,
            affected_income_threshold=score.income_threshold or 0,
            # Only the amounts the record's own source prints; every other
            # status falls back to the line above. See
            # :data:`FILING_STATUS_THRESHOLD_RULE`. Kept even where the schedule
            # supplies the floors: it remains the fallback if the transcription
            # is missing, and ``income_threshold`` stays the anchor the
            # preferential-income share is measured at.
            threshold_by_filing_status=(
                dict(score.income_threshold_by_filing_status)
                if score.income_threshold_by_filing_status
                else None
            ),
            threshold_indexation=(
                THRESHOLD_INDEXATION_STATUTORY
                if statutory_bracket is not None
                else DEFAULT_THRESHOLD_INDEXATION
            ),
            threshold_bracket_index=statutory_bracket,
            # The vintage the run is scored on, so the law read is the law of
            # that baseline. ``None`` where the record names none, which takes
            # the module's own default - the vintage ``CBOBaseline`` defaults to
            # and therefore the one this run is scored against.
            threshold_schedule_vintage=score.scoring_vintage,
            start_year=start_year,
            duration_years=10,
            ordinary_income_base=ordinary_income_base,
            income_measure=income_measure,
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
            defer_family_business_gains=uses_green_book_death_design(score),
            start_year=start_year,
        )

    if shape == "corporate_rate":
        from ..corporate import CORPORATE_VALIDATION_MODE, CorporateTaxPolicy

        return CorporateTaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=score.rate_change,
            start_year=start_year,
            duration_years=10,
            # The uncalibrated path must not read a base fitted to another
            # benchmark, and ``BASELINE_TAXABLE_PROFITS_BILLIONS`` is fitted to
            # ``biden_corporate_28`` by its own comment. Derived mode reads IRS
            # SOI's published statutory base instead. Same reasoning, and the
            # same pinning, as the ``tax_expenditure`` shape below.
            mode=CORPORATE_VALIDATION_MODE,
        )

    if shape == "payroll_rate":
        from ..payroll import PayrollTaxPolicy, PayrollTaxType

        return PayrollTaxPolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.PAYROLL_TAX,
            payroll_tax_type=PayrollTaxType.NEW_EARNINGS_TAX,
            new_payroll_tax_rate=score.rate_change,
            # CBO: "The new tax would be paid entirely by employees."
            employer_share=0.0,
            # CBO: "This option would take effect in January 2025."
            effective_month=1,
            start_year=start_year,
            duration_years=10,
        )

    if shape == "tax_expenditure":
        from ..tax_expenditures_core import (
            EXPENDITURE_MODE_DERIVED,
            TAX_EXPENDITURE_DATA_KEYS,
            CapUnit,
            TaxExpenditurePolicy,
        )

        expenditure_type = next(
            (
                kind
                for kind, key in TAX_EXPENDITURE_DATA_KEYS.items()
                if key == score.expenditure_key
            ),
            None,
        )
        if expenditure_type is None:
            return None
        return TaxExpenditurePolicy(
            name=f"Validation: {score.name}",
            description=score.description,
            policy_type=PolicyType.TAX_DEDUCTION,
            expenditure_type=expenditure_type,
            action=score.expenditure_action,
            cap_amount=score.expenditure_cap_amount,
            cap_unit=CapUnit.BASE_DOLLARS,
            caps_by_coverage_tier=(
                dict(score.expenditure_caps_by_tier)
                if score.expenditure_caps_by_tier
                else None
            ),
            # The uncalibrated path must not see a fitted annual, so the
            # constant is left unset and the mode pinned to ``derived``.
            annual_revenue_change_billions=None,
            mode=EXPENDITURE_MODE_DERIVED,
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
    persistent_elasticity: float = 0.72,
    transitory_elasticity: float = 1.20,
    use_time_varying: bool = True,
    eliminate_step_up: bool = False,
    step_up_exemption: float | None = None,
    score_gains_at_death: bool = True,
    defer_family_business_gains: bool = False,
    start_year: int = DEFAULT_VALIDATION_START_YEAR,
) -> CapitalGainsPolicy:
    """
    Create a CapitalGainsPolicy from a score entry plus required extra inputs.

    The elasticity defaults here are the module defaults: Dowd, McClelland &
    Muthitacharoen (2015)'s persistent -0.72 and transitory -1.2 at a 22%
    reference rate, stored as the magnitudes 0.72 and 1.20 because the sign
    lives in the ``exp(-b * delta_tau)`` response itself. There is one frozen
    set: no case supplies its own.
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
        persistent_elasticity=float(persistent_elasticity),
        transitory_elasticity=float(transitory_elasticity),
        use_time_varying_elasticity=use_time_varying,
        score_gains_at_death=bool(score_gains_at_death),
        defer_family_business_gains=bool(defer_family_business_gains),
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
    resolve_status_thresholds = getattr(policy, "resolved_filing_status_thresholds", None)
    if getattr(policy, "threshold_by_filing_status", None) and resolve_status_thresholds:
        # Reported because the single "threshold" above no longer describes the
        # base once the four statuses face different floors.
        params["threshold_by_filing_status"] = resolve_status_thresholds()
    if isinstance(policy, CapitalGainsPolicy):
        params.update(
            {
                "baseline_rate": policy.baseline_capital_gains_rate,
                "baseline_realizations": policy.baseline_realizations_billions,
                "persistent_elasticity": policy.persistent_elasticity,
                "transitory_elasticity": policy.transitory_elasticity,
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
        scorer = build_scorer_for_vintage(
            _resolve_vintage(score), start_year=_resolve_window_start(score)
        )

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

    # One scorer per (baseline vintage, window). Records that name no vintage
    # keep the model's current default baseline (the historical behaviour);
    # records that name one - the CBO Options battery names the Feb 2024
    # baseline its targets were published against - are scored on it, so
    # baseline drift is not folded into their error. The window is keyed
    # alongside it because a record may name the decade its own source
    # published (:func:`_resolve_window_start`), and a scorer carries its window
    # in the baseline it was built on.
    scorers: dict[tuple[BaselineVintage | None, int], FiscalPolicyScorer] = {}

    results = []
    for score in targets:
        if verbose:
            print(f"\nValidating: {score.name}...")

        key = (_resolve_vintage(score), _resolve_window_start(score))
        if key not in scorers:
            scorers[key] = build_scorer_for_vintage(key[0], start_year=key[1])

        result = validate_policy(score, scorer=scorers[key], dynamic=dynamic)
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
