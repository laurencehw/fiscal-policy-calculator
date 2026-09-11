# Changelog

Material changes to the Fiscal Policy Calculator. Trivial fixes are captured
in git history, not here.

## 2026 — ongoing

### Wave D and the first Wave E lanes — a baseline read off CBO's own tables, four targets withdrawn for want of a document, and two magnitudes that finally have one (2026-09-11)

Ten PRs: three Wave D lanes of
[`planning/HIGH_STAKES_ACCURACY.md`](../planning/HIGH_STAKES_ACCURACY.md) —
**#155** PTC coverage composition (H11), **#157** expenditure offset magnitudes
(H7), **#158** the illustrative preset group (H12); the two owner-decision lanes
its §4 had left open — **#160** decisions ③ and ④, **#161** the SALT current-law
baseline (decision ⑧); and the first two lanes of
[`planning/ROUTE_TO_8_5.md`](../planning/ROUTE_TO_8_5.md) — **#162** R2, Tier 1's
secondhand targets, and **#159** R1, the baseline transcription. Plus **#153** and
**#154**, the CBO GitHub survey memos that made R1 possible, and **#156**, the
roadmap itself. Records in [`planning/lanes/`](../planning/lanes/).

**This is the wave that made the out-of-sample battery smaller, and every
document here says so before it quotes the mean.** Four rows were withdrawn
because their targets are in no publication — never because of the size of their
error — so 26 @ 14.5% → 22 @ 11.6% is mostly a change of denominator. The
**share** within 25% rose 84.6% → 86.4% while the **count** fell 22 → 19, and only
one of those two is comparable across a battery that changes size.

| Tier | Before (post-Wave-C) | After (merged) |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 14.5% / 11.5% median / 16 within 15 / 22 within 25 | **22 @ 11.6% / 8.9% / 18 / 19** |
| … error mass | 376.1 | **255.3** |
| … `secondhand` targets | 5 | **0** — every row is now a `line_item` |
| Calibrated, fitted | 16 @ 1.5%, 16/16 | **15 @ 1.6%, 15/15** (`cap_charitable` reclassified) |
| … held in place | 27 @ 11.9%, 22/27 | **26 @ 12.4% / 2.4%, 21/26** |
| Unfitted reconstructions, scored | 39 @ 56.7% / 36.9%, 10 within 15 | **38 @ 37.5% / 30.1%, 11 within 15** |
| … **with the retired rows held in place** | — | **40 @ 55.5% / 33.6%, 11 within 15** |
| … retired targets | 0 | **2 @ 397.2%** at withdrawal |
| Leave-one-out | 18 @ 35.7% / 29.1%, 6 within 15 | **18 @ 36.5% / 30.2%, 5 within 15** |
| Published targets | 77 of 81 | **73 of 77** |
| Tier 1 CI gate | `20 / 22` | **`15 / 19`** |

**Never quote the reconstruction tier's 37.5% on its own line.** Withdrawing a
93.3% row and a 701.0% row from a tier averaging 56.5% over 39 buys **18 points of
"improvement" for nothing**, so `run_validation_dashboard.py` prints the same tier
with both rows folded back at the error they carried on the day they were
withdrawn — **55.5% over 40** — on the line beneath. Quoting the smaller figure
requires skipping a line, which is the point of printing it that way.

**#159 — the baseline is CBO's own table.** `CBOBaseline` stopped reconstructing
each vintage's levels from eleven `GDP_RATIOS` applied to FRED's latest nominal
GDP plus hand-entered growth rates, and now reads CBO's published tables,
transcribed from `US-CBO/cbo-data` @ `284a9566`, pinned by commit and verified by
SHA-256 per file. `cbo.gov` returns HTTP 403 to this environment;
`github.com/US-CBO` does not, and publishes the same tables as CSV under a
public-domain dedication. The February 2026 ten-year deficit went **$29,529.1B →
$23,143.30B** against CBO's printed $23,143.3B, end-of-window debt/GDP **103.8% →
118.0%**, and January 2025 **$27,710.6B → $21,758.3B**. `VINTAGE_SOURCING` is now
computed **per line**, because all three vintages had been graded `sourced` and
the grade was false for two: February 2026's ten-year Treasury note *fell* 4.5% →
3.9% where CBO's own table *rises* 4.10% → 4.38%, and
`real_gdp_growth + inflation` is not nominal GDP growth — the reconstruction added
a real rate to a *PCE* index. Eleven out-of-sample rows moved, in **both**
directions, because the defect was a growth rate rather than a level: CBO's own
FY2023 → FY2025 nominal growth is **10.70%** where the block assumed **8.99%**.
The two CBO Option 46 rows went **49.8% → 7.9%** and **37.4% → 2.4%**, while
`biden_high_income_tax` went **9.2% → 21.9%** — a row that improves when the base
is wrong is a row that was cancelling two errors. An eleventh row moved through a
channel nobody had listed: `cbo_opt56` **13.1% → 12.8%**, through a baseline
*assumption* rather than a level. **February 2024 keeps a reconstructed budget
path** (CBO publishes no `ten_year_budget` file for that edition; June 2024 is
publication 60039, a different document), so **its debt/GDP is a mixture and must
not be quoted**. The default February 2026 vintage is publication **61882**, *The
Budget and Economic Outlook: 2026 to 2036*, through CBO's 51118 data release; it
reproduces that report's own headlines (FY2026 −$1,852.7B, FY2027–2036
−$24,406.0B, FY2036 −$3,115.4B), and the app's $23,143.3B is the same table over
the app's own FY2026–2035 window — **CBO's headline ten-year window is
FY2027–2036**, so the two are different decades of one table. Eight generic
presets moved **+2.97%** static and two corporate presets dynamic-only, against a
registered prediction of zero — the first sweep had scored dicts rather than
policies and recorded 106 identical errors, which is PR #119 §7.5 in a second
costume: **a sweep must fail loudly on a row it could not score.**

**#162 — Tier 1's last five unsourced targets.** Nineteen percent of the battery
carried **33.4% of its error mass**, and it was the 19% whose targets nobody could
open. `illustrative_1pp_all` was **superseded** onto CBO publication 58164's
Option 13 alternative 1, **−$1,081.3B** over FY2023–2032 (report p. 72, "Data
source: Staff of the Joint Committee on Taxation" — which matches the old target's
claimed attribution), taking the row **24.5% → 14.3%** on the merged tree. Four
were **retired with the search recorded**: the Warren ultra-millionaire surtax
(TPC's *AGI Surtax Options* simulation is thirteen tables and every one is a **10
percent** surtax — and the row's *name* is wrong, since Warren's Ultra-Millionaire
Tax Act is a **wealth tax on net worth**), the Medicare surcharge, the 5pp top
rate above $1M, and the 2pp cut above $500K. **The Medicare surcharge proves the
rule rather than bending to it**: Treasury's FY2025 Green Book prints the proposal
at **1.2 percentage points** and **$403,790M**, and the model's −$408.6B sits
**1.2% from it** — but the row applies 2pp, so restated on the document's own rate
it reads **39.3% under**, worse than the 31.8% it had been reporting. **A
retirement that raises the honest error is the cleanest demonstration that the
rule is about documents and not about means.** Two costs are recorded rather than
absorbed: the withdrawn cut was the battery's only rate cut and only positive
target, and the AGI-inclusive class is down to n=2.

**#160 — owner decisions ③ and ④.** `iija_2021_discretionary.v3` scores the bill
on **FY2022–2031**, the ten fiscal years CBO's own estimate covers; the target is
unchanged at +$415.448B and only the shape input moves, taking the row **18.2% →
0.28%**. Read that as **two terms nearly cancelling**: the path outlays $434.1B,
4.5% high, while $19.8B falls outside even this window. And the two pharma
`model_estimate` targets were **retired — the ledger's first retirements**:
`expand_drug_negotiation`'s −$500B was this repository's own extrapolation from a
figure that was never a negotiation score but CBO's total for a whole title, and
`international_reference_pricing`'s −$100B was derived from a **RAND price
index**, which is a price statistic and not a budget score. The reconstruction
tier's `model_estimate` target count went **2 → 0**.

**#161 — a SALT cap path from the statute.** `SaltCapBaseline` carries three named
cap paths transcribed from IRC §164(b)(6)–(7) as amended by **P.L. 119-21
sec. 70120** — $40,000 in 2025 indexed at the statute's own 101 percent, reverting
to **$10,000 in 2030**, with a 30-percent-of-excess phasedown above $500,000 — so
the app scores current law while each benchmark scores the baseline its own
document was measured on. **Both validation rows are unchanged**; the shipped
preset moved **+$1,155.6B → +$740.3B**, because the old figure repealed a cap
current law does not impose until 2030. An independent check the repository
already held: JCX-35-25 line 20 scores sec. 70120 at **+$946,209M**, and the new
mechanism returns **$723.1B, −23.6%** against it.

**#157 — two offset magnitudes that now have a document.** Mortgage repeal
**0.10 → 0.14502762**, which is `1 − 61.9/72.4` from Poterba & Sinai (NBER WP
14253); the charitable benefit-rate ceiling **0.40 → 0.22077987**, from CRS
R40518's central price elasticity of **ε = 0.5** converted through the module's own
identity, because a price elasticity and a share of a revenue effect are different
quantities. The shipped 0.40 **inverts to ε = 0.906, above CRS's own published
high of 0.79**. Both moving rows were **pre-registered regressions**:
`cap_charitable` 0.3% → 12.5% and `eliminate_mortgage` 26.5% → 30.2%, with the
leave-one-out suite 35.7% → 36.5%. A **fifth** mechanism for leaving the fitted
tier turned up with it — `cap_charitable`'s 12.5 annual had been fitted so
`static × (1 + 0.40)` lands on −$200.0B, so sourcing 0.40 leaves the constant
fitted to a quantity the module no longer computes. Three magnitudes remain
unsourced with their searches recorded.

**#155 — the PTC offset is a composition, not a ratio.** A four-channel engine
priced per coverage person-year from CBO/JCT publication 60437 replaces a single
transferred **19.28%**, giving a window share of **12.32%** and taking
`repeal_ptc` **29.6% → 23.6%**. The aggregate had been booking CBO's **+$21B of
Medicaid and CHIP as a cost rather than a saving** — $31.39B in the wrong
direction — and its denominator was an *extension's* marginal enrollee at
**$5,370/yr** where a *repeal* removes the average subsidized enrollee at
**$8,671/yr**. The correction that would have flattered the row was declared and
declined.

**#158 — five presets demoted, zero numbers moved.** The pharma and
double-enforcement presets sit under **`Illustrative - unfitted reconstructions`**
on Explore and Build, last in order, with each preset's live error. Nothing left
any registry, so every link still scores, and every scored artifact is
byte-identical. Two findings: demoting a whole group **deleted** Explore's `Drug
Pricing` area rather than emptying it; and the values composer, which is the real
default package, selects `irs-enforcement-double` into **all five** archetypes.

**Presets that moved:** 13 of 53 — `salt-cap-repeal` **+$1,155.6B → +$740.3B**,
`charitable-deduction-cap` **−$200.6B → −$174.9B**, `aca-ptc-repeal` **−$774.1B →
−$840.8B**, eight generic presets **+2.97%** static, and two corporate presets in
dynamic mode only. The other 40 score to the cent in both engine modes.

### Wave C — a band from the policy's own class, a headcount that matched the module's other death rate, and retaliation out of a conventional score (2026-09-11)

Four PRs, the third wave of
[`planning/HIGH_STAKES_ACCURACY.md`](../planning/HIGH_STAKES_ACCURACY.md):
**#149** empirical accuracy bands (H4), **#151** the decedent headcount (H5),
**#150** tariffs (H8), and **#148** the preset label figures that discharged
§6.2 item 43. Records in [`planning/lanes/`](../planning/lanes/) —
`HSC_h4_empirical_bands.md`, `HSC_h5_decedent_headcount.md`,
`HSC_h8_tariff_feedback.md`, `HSC_label_figures.md` — and §5.9 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md).

**This wave is the mirror image of Waves A/B.** No target moved and no constant
was retuned, so the fitted tier, its held-in-place reading, leave-one-out and all
81 provenance fields are byte-identical. The two tiers that moved both moved on
**mechanism**, and they moved in opposite directions.

| Tier | Before (post-Wave-B) | After (merged) |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 14.7% / 12.6% median / 15 within 15 / 23 within 25 | **26 @ 14.5% / 11.5% / 16 / 22** |
| … error mass | 383.3 | **376.1** |
| Calibrated, fitted | 16 @ 1.5%, 16/16 | **unchanged** |
| … held in place | 27 @ 11.9%, 22/27 | **unchanged** |
| Unfitted reconstructions | 39 @ 55.5% / 29.9%, 11 within 15 | **39 @ 56.7% / 36.9%, 10 within 15** |
| … *the same 39 rows* | 55.5% | **56.7% — accuracy, not composition** |
| … `Trade` sub-population | 5 @ 34.2% | **5 @ 43.6%** (35.66% on the four with a document) |
| Leave-one-out | 18 @ 35.7% / 29.1% | **unchanged, donor matrix byte-identical** |
| Preset badges | 44 | **unchanged** |
| Tier 1 CI gate | `20 / 22` + eight class ceilings | **`20 / 22`**, capital gains **26 → 24** |

**#151 — the decedent headcount.** `CapitalGainsBaseline._decedent_template`
divided households by `estate_flow_rate` — Poterba & Weisbenner's **dollar** flow
of estates over net worth — to get a headcount of **408,532** against roughly
3.09 million NCHS deaths, while the same module has priced the lock-in wedge and
the accrued-gains drift off `death_exit_rate()`'s **2.647%/yr** since Wave 2.
**One module, two death rates 8.3× apart.** The count is now **3,384,194**; the
$196.2097B level is untouched, so gains at death by group are identical to twelve
significant figures and the count enters only as a divisor. A fixed per-donor
exclusion therefore bites 8.3× harder: `cbo_opt51_gains_at_death` **20.3% →
35.5%** (a registered regression), `biden_capital_gains_39` **32.8% → 27.0%**,
`treasury_capgains…v2` **18.4% → 1.8%**, `cbo_opt47` unmoved to the cent; the
capital-gains class **20.5% → 18.7%**. **The 1.8% is not accuracy**: the count and
the level come from the same ratio, only the count was authorised to move, and the
level that flow implies is **7.1×** below the module's own death-exit rate.
**The plan's "apply the rate by size class" was refuted in sign** — the wealthy
are older, so a size-graded rate is *higher* at the top (2.8400% against 2.6468%)
and takes the implied top count to 38,908 where the uniform swap takes it to
36,262, both further from SOI's 7,194. No preset moved; three Tailor shapes did,
by 19–31%.

**#150 — tariffs, where the plan's residual cause was backwards.** All five
targets are *conventional* estimates and the model sat **below** every one, so
adding the GDP-feedback drag the plan prescribed would have moved every row
further out; the 0.60–0.66 vs 40–50% net/gross comparison was a **denominator
mismatch** besides (on the knowledge snapshot's own denominator the universal
preset already read 0.589). The channel is built and **reported beside** the
score, the column structure Tax Foundation FF861 publishes. What moved the rows is
that **retaliation left the conventional score** — a category error against every
target the scorecard carries, and one the repository's own knowledge file had
already described correctly while all five scenarios and presets ran the other
way. `estimate_behavioral_offset` is now **0.7125 of gross** in either direction
against FF861's implied 0.738. `trump_universal_10` **42.03% → 36.91%**,
`trump_china_60` **57.17% → 49.06%**, `auto_tariff_25` **52.81% → 47.20%**,
`reciprocal_tariffs` **6.88% → 9.47%** (and `within_published_range` **False →
True**, distance $3.2B → $0.0B — both readings are correct and the row carries
both), `steel_tariff_25` **11.89% → 75.28%**, registered. Two cheap fixes landed
too: `reciprocal_coverage_rate = 0.50` is **deleted** for EO 14257's own
bilateral-deficit formula on Census 2024 across 230 partners, reproducing **all
sixteen published Annex I rates within 0.80pp**; and the steel base reaches the
Section 232 derivative chapter, $58.9B → $108.4B — **1.84×, not the "roughly
triple" this repository stated in three places** — declared an upper bound. Five
shipped presets moved with a Decision 6 caption: Trump Universal 10%
**−$1,258.5B → −$1,369.8B**, Trump 60% China **−$278.4B → −$331.1B**, 25% Auto
**−$182.2B → −$203.9B**, 25% Steel/Aluminum **−$52.9B → −$105.2B**, Reciprocal
**−$1,396.8B → −$1,642.0B**. The other 44 score to the cent in both modes.

**#149 — accuracy bands from the policy's own class.** Zero scored numbers move
and every headline caption changes. The band is now the observed Tier 1 error
spread of the policy's **own class** — inner half-width the class mean, outer the
class's worst row — keyed by the same routing the CI per-class gate uses
(`fiscal_model/validation/policy_classes.py`, which `cold_holdout.py` now imports
and is byte-identical). **26/26 Tier 1 rows fall inside their class's outer
band**, and inner coverage is *computed and printed*, not asserted: it is not a
majority everywhere — `ordinary rate change` covers 1 of 4. **The largest defect
it removes was not on the plan's list**: `get_band_for_result` fell through to
`Generic`, which **is** the Tier 1 tier, so **31 of 56 surfaces printed "±14.7%
across 26 calibrated runs"** for policies with no Tier 1 row — *International
Reference Pricing* drawing a ±14.7% ribbon beside a scorecard row 701.0% from its
target. The two replaced branches were both fixed proportions of the point
estimate. **18 of 53 presets get a band; 35 print no band and say why**, with
their own row's error and tier beside the absence.

**#148 — six labels onto their row's live target, and one that was quoting the
model.** Zero numbers move. `💰 SS Donut Hole $250K (-$2.7T)` → **`(-$1.43T)`**,
`🏠 Eliminate Estate Tax ($350B)` → **`($407B)`**, `📋 Eliminate Mortgage
Deduction (-$300B)` → **`(-$368B)`**, `🏭 Trump 60% China Tariff (-$500B)` →
**`(-$650B)`**, `🌱 Repeal IRA Clean Energy Credits ($783B)` → **`(-$851B)`**,
`🌱 Repeal EV Credits ($182B)` → **`(-$182B)`**. The fifth of those **was not
quoting a target at all** — −783.0 is `model_10yr_billions`, so the app printed
its own output, positively signed, in the slot a published score occupies: the
third mechanism for a class of defect PRs #119 and #122 each found once.
`_LABELS_QUOTING_A_SUPERSEDED_FIGURE` **5 → 0**, and the label invariant now runs
against **all 40** figure-carrying labels with no exemptions. The worst stale
string was **not a label** but `assistant/knowledge/ssa_trustees_2025.md`, which
told the Ask assistant the donut was "scored by CBO at −$2.7T (model: −$2.4T,
error 12%)" — three errors in one BM25-indexed clause.

**The CI gate, re-derived by the workflow's own rule and downward only.** Pooled
ceiling `ceil(14.5 × 1.25) = 19 →` nearest 5 `= 20`, unchanged. The floor derives
to `22 − 1 = 21`, which would **loosen** the 22 Waves A/B set, so it **stays at
22** — a rule that tightens on improvement and loosens on regression is not a
gate. Per class, exactly one ceiling moved: **capital gains 26 → 24**.

**Carry-overs opened:** §6.2 items **55–65** — the *level* half of the
capital-gains death channel (the 7.1× factor, pointing the other way from #151),
twelve Build-package totals that no longer equal their member sums, two
`official_source` fields contradicting their own ledger row, a symmetric band over
asymmetric errors, 35 presets with no measured out-of-sample accuracy, a stale
"~5% / ~8%" pair in `about.py` and the assistant's system prompt, the decedent
universe, `FRBUSAdapterLite`'s crowding-out sign inverting for revenue-raisers,
`score_policy(dynamic=True)` reading `EconomicModel` rather than the tariff
impulse, the HS-10 Section 232 annex, and `steel_tariff_25`'s untraceable target.

### Waves A and B — one base rule, the base's own decade, and five targets that found their documents (2026-09-10)

Seven PRs, the first two waves of
[`planning/HIGH_STAKES_ACCURACY.md`](../planning/HIGH_STAKES_ACCURACY.md), which
re-ranks the modelling work by **who reads the number** rather than by error
mass. Wave A: **#142** one base rule across four surfaces, **#140** badges and
tiers, **#141** the two OCACT payroll targets. Wave B: **#144** base growth,
**#146** the AGI column, **#143** the corporate estimator range, **#145**
provenance. Records in
[`planning/lanes/`](../planning/lanes/) — `HSA_h1_base_rule.md`,
`HSA_h6_no_headline_without_row.md`, `HSA_h13_payroll_targets.md`,
`HSB_h2_base_growth.md`, `HSB_h2b_agi_column.md`, `HSB_h3a_corporate_range.md`,
`HSB_h9_provenance.md` — and §5.8 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md).

**Three different things moved and they must not be run together.** Tier 1 moved
on **mechanism**; both calibrated tiers and leave-one-out moved on **targets**,
with not one derivation changing; badges and provenance moved on **coverage**.
Only the first is a statement about the model.

| Tier | Before (post-Wave-7) | After (merged) |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 15.0% / 10.6% median / 17 within 15 / 22 within 25 | **26 @ 14.7% / 12.6% / 15 / 23** |
| Calibrated, fitted | 21 @ 1.73%, 21/21 within 15 | **16 @ 1.51%, 16/16** |
| … held in place (ledger rows folded back) | 27 @ 5.6%, 25/27 | **27 @ 11.9%, 22/27** |
| Unfitted reconstructions | 34 @ 57.88% / 34.2% | **39 @ 55.46% / 29.9%** |
| … *the same 34, on the new targets* | 57.88% | **58.26%** |
| Leave-one-out | 18 @ 30.1% / 19.1% | **18 @ 35.7% / 29.1%** |
| Published targets | 75 of 81 | **77 of 81** |
| Preset badges | 24 | **44** (16 fitted / 25 reconstruction / 3 out-of-sample) |
| Tier 1 CI gate | `20 / 21` | **`20 / 22`** + a per-class floor |

**#142 — one base rule.** `ordinary_income_base` had three different defaults, so
a 2pp surtax above \$400,000 scored **−\$166.5B on Tailor and −\$314.6B on Ask**,
on the same commit, with the scorecard validating only the second. One shared
default now serves all four constructors, with a grep gate against re-acquiring a
literal. Three surtax presets declare `agi_inclusive_base` and move onto the base
their sources state. **Zero validation rows moved.** Two findings nobody asked
for: 36 of the 52 presets carry the attribute and **none of them reads it**, and
`DistributionalEngine` ignores it, so one policy object yields a revenue score
and a who-pays table **2.57× apart** (a test now asserts the divergence exists).

**#140 — no headline without a row.** Badges **24 → 44**: the badged set is now
exactly the set of presets carrying an official figure, and each badge names its
**tier** rather than rating a fitted 0.0% and a 701% reconstruction in one
vocabulary. **Six presets now carry a badge saying they are more than 50% from
their published target, and five said nothing at all before.** The map is keyed
by stable preset id, which is what let five renames and five superseded figures
land without losing entries. `get_confidence_context` has **no caller in the
tree** — a live defect on a dead function, fixed so wiring it later is safe and
reported as such.

**#141 — the two OCACT payroll targets.** No model change, zero numbers moved.
OCACT scores E2.1 and E2.5 as **+2.55% and +2.50% of taxable payroll** and
publishes **no ten-year dollar amount at any horizon** — verified three ways,
including that "billion" and "trillion" do not appear once across the whole
category summary. −\$2.7T traces to a Peter G. Peterson Foundation sentence about
a *benefit-crediting* variant; **−\$3.2T matches nothing either body prints**.
Unpredicted: both published paths **ramp** (\$122.0B → \$192.0B) and the module
stamps a flat \$270B.

**#144 — grow the generic base on the scored vintage, and the tier mean rose.**
Every generic run had returned the same tax-year-2023 annual ten times. The base
now carries the scored vintage's own nominal-GDP index; ten Tier 1 rows moved,
every pre-registered figure landed with a worst miss of \$0.08B, and the tier went
**15.0% → 15.6%** — the plan's own falsification condition, reported rather than
tuned away. **The plan's 9.1% / 1.0% endpoints embedded a step nobody had
built**, attributed to a preset flag that cannot move a validation row.

**#146 — the AGI-stated rows read SOI's AGI column.** A **unit mismatch**:
returns were selected by an AGI class boundary and then priced against an average
of *taxable* income. Three of six rows moved and three did not, each on its own
source's sentence. Tier **15.6% → 14.7%**, so the plan's H2 condition is
satisfied **by the pair and not by H2 alone**. The two Option 46 rows went
49.8% → 34.1% → **7.4%** and 37.4% → 17.9% → **−2.9%**. The rule is not the
flattering one and the lane declared it: the class's best row went **5.2% →
24.8%**, and moving the three held rows would read 17.8% for the tier.

**#143 — the corporate estimator range.** Presentation only; every artifact
byte-identical. A headline corporate run now prints all four published scores
converted to its own rate step and says where it sits among them. **In `derived`
mode the model lands inside the published span at the +7pp step every shipped
preset uses and outside it at +1pp**, where `reported` is outside at every step —
a second, independent reading for the open `CORPORATE_APP_MODE` decision.

**#145 — provenance.** Eighteen benchmarks judged one at a time: six revised,
twelve examined-and-left, one transcribed-and-confirmed, **no modelling change at
all**. Five of the six revisions make their row worse, which is the shape a
correct provenance pass has — the \$250,000 donut to CBO's **−\$1,426.8B**
(0.0% → **89.2%**), TCJA rates-only to CRS's **\$2,158.7B** (2.2% → **44.3%**),
and four others. **The sharpest result is a refusal the mechanism made rather
than the author**: a Tax Foundation cap-elimination figure is −\$3,200.0B to the
digit the carried target states, so the ledger rejected it as noise. `secondhand`
**12 → 7**, `model_estimate` **6 → 4**. A `retire` state is built, tested, and
**applied to nothing**, because withdrawing the two pharma rows would buy 18.5
points of "improvement" by deletion.

**Seven shipped presets moved**, each onto its own source's base or decade:
Warren Ultra-Millionaire Surtax −\$134.6B → **−\$456.0B**, High-Earner Medicare
Surcharge −\$166.5B → **−\$426.6B**, Progressive Millionaire Tax −\$354.6B →
**−\$878.8B**, and four generic presets by a uniform **+35.60%** (Flat Tax Reform,
Middle Class Tax Cut, Top Rate to 45%, Biden 2025 Proposal). The other 45 score to
the cent what they scored before. Build package totals moved for seven *more*
presets with no scored number moving at all, because Build quotes list prices.

**The Tier 1 CI gate was re-derived by the workflow's own rule and downward
only**: ceiling `ceil(14.7 × 1.25) = 19` → nearest 5 `= 20`, unchanged; floor
`23 − 1 = 22`, tightened from 21. **A per-class floor now runs beside it**
(`cold_holdout.py --max-class-mean-error`), one ceiling for each of the plan's
eight policy classes, because a pooled mean cannot see one class regressing while
the others carry it — which is what happened to `medicare_surcharge_2pp` in
Wave 7 and to `warren_ultramillionaire_surtax_3pp` in Wave B. Classes are derived
from each benchmark's own record, and the gate **fails if the battery contains a
class nobody gated**.

### Wave 7 — four measured mechanisms, four registered regressions, and a cold start (2026-09-06)

Ten PRs. Seven touch a model or a baseline: a **target-window memo with its own
minimal implementation** (**#126**), a **filing-status dimension** for the generic
income-tax path (**#127**), a **convention lane** settling the expenditure offset
direction on nine sources (**#128**), a **cold-start measurement** (**#129**, 🔵), a
**green-tier fix** to the baseline's corporate receipts line plus the dashboard's
blind spot (**#130**), a **new shape** for `repeal_ptc` (**#131**), and a **fitted
size distribution** in place of the decedent ladder (**#132**). Three are blue-tier:
Plotly dark mode (**#133**), Build frozen links (**#134**), and the footer scorecard
(**#135**). Records:
[`planning/memos/FY2022_TARGET_WINDOW.md`](../planning/memos/FY2022_TARGET_WINDOW.md),
[`planning/lanes/W7_filing_status_split.md`](../planning/lanes/W7_filing_status_split.md),
[`planning/lanes/W7_expenditure_offset_convention.md`](../planning/lanes/W7_expenditure_offset_convention.md),
[`planning/memos/COLD_START.md`](../planning/memos/COLD_START.md),
[`planning/lanes/FIX_baseline_corporate_path.md`](../planning/lanes/FIX_baseline_corporate_path.md),
[`planning/lanes/W7_ptc_repeal_shape.md`](../planning/lanes/W7_ptc_repeal_shape.md),
[`planning/lanes/W7_decedent_ladder.md`](../planning/lanes/W7_decedent_ladder.md);
§5.7 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md)
carries the summary and the five findings.

**Six of the seven Tier 1 rows that moved got worse, all pre-registered, and the
tier mean still fell.** Neither calibrated tier changed population, which makes
this the first round in several where the constant-population reading *is* the
headline reading — and where both calibrated moves are **accuracy** rather than
composition. **No lane's branch figure is the merged one**: #126 and #132 move
the same Treasury row in opposite directions, so the lane docs report Tier 1 at
14.1%, 15.9% and 15.4%, each correct on its own branch and none of them 15.0%.

| Tier | Before (post-#122) | After (merged) |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 15.2% / 11.4% median / 16 within 15 / 22 within 25 | **26 @ 15.0% / 10.6% / 17 / 22** |
| Calibrated, fitted | 21 @ 1.7%, 21/21 within 15 | **21 @ 1.7%, 21/21** — 1.733% → 1.724%, one row; held in place **27 @ 5.6%, 25/27** |
| Unfitted module reconstructions | 34 @ 57.6% / 34.2% median / 9 within 15 / 13 within 25 | **34 @ 57.9% / 34.2% / 9 / 12** — same 34 rows, so **accuracy, not composition** |
| Calibrated, leave-one-out | 18 derivable @ 29.6% / 19.1% median / 8 within 15 | **18 @ 30.1% / 19.1% / 8** — `Expenditures` 35.7% → **37.5%**, registered |
| Distributional (7 tables) | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 81 (75 published); calibrated 55 (49) | **unchanged** |
| Calibrated provenance | 30 / 7 / 12 / 6 / 0 | **unchanged** |
| `revised_target_entries` / `EXAMINED_NOT_REVISED` | 16 / 6 | **unchanged** |
| Tier 1 error mass | 395.1 (capital gains largest at 104.5, 26.4%) | **390.7** — **the two AGI surtaxes largest at 87.2, 22.3%**; capital gains third at 82.0, 21.0% |
| Tier 1 CI gate | `--max-mean-error 20 --min-within-25pct 21` | **unchanged** — re-derives to itself: `ceil(15.0 × 1.25) = 19 → 20`, `22 − 1 = 21` |
| Tests | 3518 passed, 7 skipped | **3722 passed, 8 skipped** (`python -m pytest tests/ -q`) |

**The tail re-ordered again, and capital gains is no longer the tier's largest
error mass — the first time in the plan's history.** The eight largest rows are
`cbo_opt46_agi_surtax_1pp_20k` **49.8%**, `cbo_opt64_corporate_rate_1pp`
**44.5%**, `cbo_opt46_agi_surtax_2pp_100k` **37.4%**, `biden_capital_gains_39`
**32.8%**, `cbo_opt45_all_rates_1pp` 22.4%, `cbo_opt51_gains_at_death` 20.3%,
`warren_ultramillionaire_surtax_3pp` 19.0% and
`treasury_capgains_39_plus_stepup_elim.v2` 18.4%. **Payroll is not in the tail**
— the two Option 61 rows are 8.1% and 7.5%, the 19th and 20th rows by error.

**Per-case, the rows and presets that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt46_agi_surtax_1pp_20k` (Tier 1) | −$1,440.1B | −$796.6B | **−$723.1B** | 44.7% → **49.8%** |
| `cbo_opt46_agi_surtax_2pp_100k` (Tier 1) | −$1,051.0B | −$881.7B | **−$657.5B** | 16.1% → **37.4%** |
| `cbo_opt45_top4_brackets_2pp` (Tier 1) | −$569.5B | −$671.6B | **−$498.7B** | 17.9% → **12.4%** |
| `biden_high_income_tax` (Tier 1) | −$245.9B | −$216.5B | **−$223.3B** | 12.0% → **9.2%** |
| `treasury_capgains_39_plus_stepup_elim` → `.v2` (Tier 1) | −$322.0B, unchanged | −$461.5B on FY2025–2034 | **−$381.1B on FY2022–2031** | 43.3% → **18.4%** |
| `cbo_opt51_gains_at_death` (Tier 1) | −$536.1B | −$432.8B | **−$427.5B** | 19.3% → **20.3%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$379.2B | **−$383.2B** | 31.4% → **32.8%** |
| `repeal_ptc` (calibrated, unfitted) | −$1,100.0B | −$896.9B | **−$774.1B** | 18.5% → **29.6%** |
| `eliminate_mortgage` (calibrated, fitted) | −$300.0B | −$330.4B | **−$270.3B** | 10.1% → **9.9%** |
| 🏥 Repeal ACA Premium Credits (app preset) | — | −$896.9B | **−$774.1B** | +13.7%, Decision 6 caption |

- **PR #126: the FY2022 Green Book row is scored on the decade its own document
  covers, and the offset every doc quoted was wrong by twelve points.**
  `CBOScore.scoring_window_first_year` moves **the scorer's window and the
  policy's start together** (moving only the window truncates the head), and
  setting it is a supersede rather than an edit — `.v1` kept with `superseded_by`,
  `.v2` registered at the same −$322.0B, entry commit before scoring commit, which
  is `iija_2021_discretionary.v2`'s rule exactly. **28.7 of the row's 43.3 points
  are the window, not the "~17" the repository had been quoting**: the old figure
  discounted only the rate channel (`359.02 × 0.844354 + 102.45 = 405.6`,
  reproduced to the dollar by the new `scripts/window_offset_capgains.py`), and
  the death channel both grows with the same 5.80% net-worth CAGR and does **not**
  grow proportionally — a uniform discount gives $86.5B where the re-score gives
  $65.8B, because a fixed nominal per-donor exclusion is a step function whose
  bite moves faster than the stock. The control, `biden_capital_gains_39`, has an
  offset of **exactly zero to the cent**. And **18.4% is not accuracy either**: it
  nets Treasury's $66.0B booked across FY2022–24 against the model's $6.1B — the
  model's enactment year is a $59.8B transitory revenue *loss* — against $106.4B
  of over-prediction across FY2025–2031. **The same mechanism would take IIJA
  18.2% → 0.3%**; the memo publishes that number and leaves the `.v3` decision to
  the owner, because a lane may not take a second target decision by implication.

- **PR #127: statutory thresholds are stated per filing status, and now the model
  can express one.** `TaxPolicy.affected_income_threshold` was a scalar and
  `IRSSOIData` read only Table 1.1, which has no filing-status dimension, so one
  status's floor was applied to all four populations — at CBO Option 46
  alternative 1 taxing 46.1M joint returns from $20,000 where JCT starts them at
  $40,000, **$839.8B of base, 9.2% of the whole**.
  `scripts/build_filing_status_data.py` transcribes IRS SOI **Table 1.2** and
  `get_bracket_distribution_by_status` takes only its *composition* onto Table
  1.1's totals, so a uniform threshold reproduces the pooled path to the cent.
  **Three of the four rows got worse and that is the finding**: `opt46_2pp`'s old
  **16.1% was two errors cancelling a third** — the split alone gives 37.4%, an
  AGI base (which is what CBO's text specifies) 21.6%, and a base grown at CBO's
  own nominal GDP rather than frozen at tax year 2023 **1.0%**. Both remaining
  terms move rows with no filing-status boundary, so each is its own lane. Two
  more findings: the single-threshold approximation was **not** uniformly generous
  — the Green Book row's married-filing-separately floor is $175,000 *below* the
  amount the model applied, so that base had been under-counted — and SOI Tables
  1.1 and 1.2 disagree about taxable income by **$319.2B** while agreeing exactly
  on returns and AGI, which neither table mentions.

- **PR #128: the expenditure offset's direction is now read off the sources, one
  reform at a time.** "One direction" was the defect, not "which direction": CBO's
  Option 49 gives four alternatives over the same deductions **three different
  behavioural directions**, and its charitable option reverses its own verdict for
  a *floor* design. `TaxExpenditurePolicy` carries a per-reform `direction` with
  the source sentence attached — **magnify** for Option 56, the 28% charitable
  benefit-rate ceiling, SALT elimination and SALT-cap repeal; **erode** for
  mortgage (Poterba & Sinai's own 85%), step-up, retirement and like-kind. Only
  `eliminate_mortgage` moved and **zero presets** did. The registered price is the
  leave-one-out suite, and the reason is worth keeping: the old −5.1% was **two
  errors cancelling**, since the held-out annual is JCT's $25.0B against the
  fitted $26.2B — a static path 4.5% *low* — and magnifying it by 10% put the
  score 5.1% *high*. Unpredicted finding: **the module's six fitted constants
  disagree about whether the convention exists**, three fitted so the *static*
  path hits the target and three so the *magnified* score does. And a **sixth**
  sign defect turned up in `estimate_expenditure_revenue()`, which aggregates in
  revenue space and was adding a deficit-space offset — a sign contract enforced
  at the two ends of a pipeline says nothing about the middle of it. **Magnitudes
  remain unsourced**; item 8 is closed on direction and open on magnitude.

- **PR #130: every baseline vintage now has its own corporate receipts line, and
  nothing scored moved.** `_load_from_data_sources` set
  `base_corporate_tax = base_individual_income_tax × 0.18` and
  `_project_corporate_tax` grew it at **4.88%/yr** against CBO's own **1.21%**,
  neither term taking a vintage — so under `use_real_data=True`, the app's
  default, all three vintages started from **$386.62B to the cent** while
  `use_real_data=False` returned three different figures, the mode named "real
  data" being the one with no vintage in it. February 2024 now **is** CBO
  publication 59710 Table 1-1; the other two keep the reconstruction from their
  own base year; `CORPORATE_RECEIPTS_SOURCING` grades all three so a
  reconstruction cannot be reported as CBO's. All 26 out-of-sample rows, both
  calibrated tiers, all 81 scorecard entries, the donor matrix, 53 presets and 16
  Tailor combinations are **byte-identical**; what moved is the baseline *behind*
  them — Ask's ten-year deficit **$30,020.7B → $29,529.1B**, end-of-window
  debt/GDP **104.8% → 103.8%**, the deficit moving further than the revenue
  because $58.3B is interest not paid on debt not issued. **Second half:**
  `run_validation_dashboard.py` had printed Tier 1 and leave-one-out and nothing
  about the 55 calibrated rows between them, which is why PR #119 could move both
  calibrated tiers and leave it byte-identical. It now prints a calibrated block
  with twelve reconstruction sub-populations, and `declared_calibrated_to_target`
  makes the honest held-in-place reading computable: **27 at 5.6%**, not the 37 at
  15.5% that folding in all 16 revised rows would give.

- **PR #131: a repeal of §36B now removes the credit CBO projects.**
  `create_repeal_ptc`'s $83.0B/yr was `1100 / (1.10 × Σ 1.04ᵗ)` — the carried
  target run backwards through the engine's growth factor and the inverted offset
  PR #119 corrected. **And it looked fine, which is the finding**: 3.9% from CBO's
  own ten-year total while being 21% low in FY2026 and 21% high in FY2028, because
  a smooth 4% ramp cannot see the cliff the ARPA/IRA expiry puts in the credit —
  and the app shows the annual profile, the distributional tables and the dynamic
  feedback off that same series. The static path is now CBO/JCT publication
  **51298** Table 2's own annual cost (both legs, two vintages transcribed, an
  untranscribed vintage **raising** rather than falling back) times
  (1 − **19.28%**) of offsetting effects from publication **60437**. The whole
  $326B of movement is three published steps and not one dollar of residual. **The
  refusal to adopt −$1,100B is now demonstrated rather than argued**: the same
  mechanism on the June 2024 vintage and window with no offset returns $1,143.0B
  against the $1,142B PR #122 traced — **0.09%**.

- **PR #132: the decedent ladder is replaced, and the hypothesis behind it is
  disproved.** Five point masses reading three published carve-out step functions
  at each class's *mean* estate became a **piecewise-Pareto size distribution of
  net worth at death**, fitted to the Distributional Financial Accounts' own
  percentile-group aggregates (each reproduced to 1e-9), with the published wealth
  breakpoints forced in as quadrature edges. **Seven of eighteen published rows
  had never been evaluated**, including the whole $1M–$5M band both Green Book
  exclusions sit in; six are now alive. **But the $1M → $5M step got bigger,
  82.26 → 85.02**, and the direction is not an accident: `max(0, gain − E)` is
  convex in the gain, so a mean-preserving spread *raises* the taxable excess — a
  sharper schedule makes an exclusion cost **more**. **What moves it is the
  decedent headcount**: `estate_flow_rate` is Poterba & Weisbenner's *dollar* flow
  of estates used as a *headcount* rate, giving 408,532 decedents against roughly
  3.09 million NCHS deaths, and about twice the shipped count reproduces
  Treasury's own step to within two billion. The fit also **refuses below the top
  decile and says so twice**. Two Tailor figures moved by 2.6% and 1.2%, and the
  caption shipped anyway.

- **PRs #129 and #135: the cold start was measured, and it was the footer.**
  Network is ruled out at **0.55s median**, ~3% of the observed ~20s. Import
  ordering was real and is fixed — `app.py` named a `fiscal_model` submodule at
  module scope, so **time to first paint went 1.593s → 0.022s** and
  modules-at-import 1,901 → 586, pinned by five subprocess checks that all fail on
  the pre-change file. **The largest term was one nobody had looked for**: the
  page footer ran every specialized validator over all 81 scorecard rows to print
  one clause — **8.68s of the landing page's 9.38s first script run**. PR #135
  closed it on a third option neither candidate in the memo offered: the count is
  a **generated artifact** (`scripts/build_validation_headline.py` →
  `headline_counts.json`), read with stdlib `json` and pinned by a test that
  recomputes the scorecard, so the landing page's first run went **8.404s →
  0.668s** and the clause still prints on the *first* run. **A cheap registry
  count cannot be made exact**, which is why: `published_entries` counts rows the
  runners actually returned, so it would over-report by exactly the number of
  benchmarks currently failing to score. Still open: the **Cloud-sleep half** —
  Community Cloud apps sleep after 12 hours and do not wake by themselves, so for
  a slept app no app-side work touches the first visitor — and the **scored**
  route at ~10.6s, whose 6.555s goes to `get_validation_badge → _scorecard_index`
  and needs each row's figures rather than a count.

- **PRs #133 and #134: the charts follow the page, and Build packages freeze.**
  20 of 21 chart sites are themed through `theme_figure`, reading the ⚙ toggle's
  own `dark_mode` flag rather than `st.context.theme` (which reports the
  *Streamlit* theme, always light in this deployment, and would have made the
  charts disagree with the page); values are written at **layout** level, because
  `st.plotly_chart(theme="streamlit")` merges Streamlit's own layout over any
  custom template. Light mode is pinned byte-identical two ways and contrast is
  measured rather than asserted. And `frozen=1` now holds a lock on `/build`:
  `?policies=&target=&metric=` plus the shared `baseline=&engine=&spec=&mode=`
  stamps, re-applied on **every** rerun, with every input disabled and **the
  exports still live**, because an export is not an edit. `?values=`/`?vector=`
  links freeze too, since the composer is deterministic, and the emitted link
  resolves to `policies=` so a re-scored catalog cannot recompose an assignment
  already handed out.

### The behavioural-offset sign sweep, and the corporate follow-through (2026-09-05)

Four PRs, and only two of them touch a model: a **cross-cutting sweep** of the
behavioural-offset sign contract (**#119**), a **research memo** on the published
per-point corporate yields that changed no code (**#120**), a **modelling lane**
projecting the corporate base off the scored vintage (**#121**), and a
**provenance pass** on the corporate and PTC targets (**#122**). Records:
[`planning/lanes/SWEEP_offset_sign.md`](../planning/lanes/SWEEP_offset_sign.md),
[`planning/memos/CORPORATE_PER_POINT_YIELD.md`](../planning/memos/CORPORATE_PER_POINT_YIELD.md),
[`planning/lanes/W6_corporate_base_projection.md`](../planning/lanes/W6_corporate_base_projection.md),
[`planning/lanes/PROVENANCE_corporate_ptc.md`](../planning/lanes/PROVENANCE_corporate_ptc.md);
§5.6 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md)
carries the summary and the four findings.

**One Tier 1 row moved and both calibrated tiers changed population.** Read the
constant-population figures beside the headline means, because #119 and #122 both
moved `trump_corporate_15` — in opposite directions, for different reasons.

| Tier | Before (Wave 5) | After (merged) |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 15.9% / 11.4% median / 16 within 15 / 22 within 25 | **26 @ 15.2% / 11.4% / 16 / 22** |
| Calibrated, fitted | 23 @ 1.6%, 23/23 within 15 | **21 @ 1.7%, 21/21** — held in place, **23 @ 7.7%, 21/23** |
| Unfitted module reconstructions | 31 @ 56.6% / 29.9% median / 9 within 15 | **34 @ 57.6% / 34.2% / 9** — **57.4% on the 33 rows held before #122**, **56.6% on the 31 held before #119** |
| Calibrated, leave-one-out | 18 derivable @ 29.6% / 19.1% median / 8 within 15 | **byte-identical output**, on all four branches |
| Distributional (7 tables) | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 80 (73 published) | **81 (75 published)**; calibrated 55 (49 published) |
| Calibrated provenance | 30 / 5 / 12 / 7 / 0 | **30 / 7 / 12 / 6 / 0** |
| `revised_target_entries` | 15 | **16** |
| `EXAMINED_NOT_REVISED` | 5 | **6** |
| Tier 1 error mass | 412.9 over 26 (corporate largest at 62.3, 15.1%) | **395.1** (capital gains largest at **104.5, 26.4%**; corporate **44.5, 11.3%**) |
| Tier 1 CI gate | `--max-mean-error 20 --min-within-25pct 21` | **unchanged** — re-derives to itself on 15.2% / 22 |
| Tests | 3415 passed, 1 skipped | **3518 passed, 7 skipped** (`python -m pytest tests/ -q`) |

**The tail re-ordered and corporate is no longer the largest row.** The four
largest are now `cbo_opt46_agi_surtax_1pp_20k` at **44.7%**,
`cbo_opt64_corporate_rate_1pp` at **44.5%**,
`treasury_capgains_39_plus_stepup_elim` at **43.3%** and `biden_capital_gains_39`
at **31.4%**. The AGI-surtax row has not moved through six waves; it became the
largest because corporate fell past it.

**Per-case, the rows and presets that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt64_corporate_rate_1pp` (Tier 1) | −$135.7B | −$220.3B | **−$196.1B** | 62.3% → **44.5%** |
| `trump_corporate_15` (calibrated) | $1,920B → **[+$595.0B, +$673.1B]** | +$1,918.0B | **+$1,491.8B** | 0.1% → 22.3% → **121.6%** |
| `repeal_ptc` (calibrated) | −$1,100.0B | −$1,096.2B | **−$896.9B** | 0.3% → **18.5%** |
| `biden_corporate_28_fy2022` (**new**) | −$857.8B | — | **−$1,397.2B** | **−62.9%** |
| `biden_corporate_28` (calibrated, fitted) | −$1,347.0B | −$1,397.2B | unchanged | 3.7%, now labelled a **scope** disagreement |
| 🏢 Trump Corporate 15% (app preset) | — | +$1,690.6B | **+$1,314.9B** | −22.2%, Decision 6 caption |
| 🏥 Repeal ACA Premium Credits (app preset) | — | −$966.2B | **−$790.5B** | +18.2%, Decision 6 caption |

- **PR #119: seven of fifteen behavioural offsets were against the engine's
  contract.** `scoring_engine.py` books
  `deficit_after_behavioral = static_deficit + behavioral` on the **static
  revenue** effect, so a same-signed offset erodes and an opposite-signed one
  magnifies. Probed at the function (`f(+100)`, `f(−100)`) *and* at the score,
  three modules were **inverted** — `AMTPolicy`, `EstateTaxPolicy`,
  `PremiumTaxCreditPolicy`, all three carrying the identical comment pair
  `# Reduces revenue gain` / `# Reduces revenue loss` above a
  `return -total_offset`, one copy-paste in three files — and four were
  **`abs()`-ed**: `CorporateTaxPolicy` in `reported` (the app default), the
  `TaxCreditPolicy` fallback branch, `IRSEnforcementPolicy` and
  `InternationalTaxPolicy`. AMT booked **25% more** than its own static in both
  directions. Six were fixed with `math.copysign`; `TaxExpenditurePolicy` is kept
  opposite-signed as a **sourced convention**, cited to CBO 60557 Option 56, whose
  text has both channels raising revenue — and its size is now measured (+5% on a
  SALT elimination, +20% on Option 56). Two shipped presets moved with a caption
  computed from the scored result; the other 51 score to the cent, and both moved
  presets' badges dropped (Excellent → Poor, Excellent → Acceptable), which is the
  correct reading. `tests/test_offset_sign_contract.py` is the new gate: **92 tests
  (86 passing, 6 skipped)** probing ±$100B in both directions, plus a coverage grep
  that fails if any class defining `estimate_behavioral_offset` is missing from the
  case list.
  **Strict readiness then failed on CI where it passes on `main`**, and the owner
  chose **reclassify, don't retune, don't exempt**: `trump_corporate_15` and
  `repeal_ptc` became `calibrated_to_target=False`, because a constant that
  reproduced its target only through a defect is not a calibration to that target.
  **The lesson in §7.5**: the failure was invisible locally because Python 3.14
  fails the runtime check *first* and masks everything after it, so a byte diff of
  the output showed nothing — *"identical to main" is only evidence when the
  check being compared can distinguish them.*
- **PR #120: the corporate memo, no code.** 18 published corporate-rate estimates
  across 10 vintages, transcribed with page references and annual paths to
  `fiscal_model/data_files/validation/corporate_rate_scores.csv` and printed by
  `scripts/corporate_yield_reconciliation.py`. Three claims in `cbo_opt64`'s
  `known_limitations` refuted: the split is **JCT vs Treasury OTA**, not CBO vs
  Treasury (every corporate-rate option in every *Options* volume carries "Data
  source: Staff of the Joint Committee on Taxation"); Treasury's 28% row has
  bundled a **GILTI step** since the FY2023 edition, so it is not rate-only; and
  per-point dollars are not comparable across rate levels or scopes — on the
  implied marginal base the record is Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%,
  Treasury 79.5%, **model 90.8%**. JCT's 14-point cut from 35% and its 1-point
  increase from 21% imply marginal bases of $963.2B and $963.0B, so nothing
  supports a yield rising with the step. And **Option 64 carries no
  income-and-payroll offset footnote though the facing Option 63 does**, which
  refutes the old "largest unmodelled channel" claim outright.
- **PR #121: the corporate base is projected off the vintage, not aged at 4%/yr.**
  Base = CBO's February 2024 corporate receipts path (pub. 59710 Table 1-1) ×
  **4.80133** base-$/receipts-$ anchored on SOI TY2022 ÷ MTS FY2022, with a §6655
  convolution for the fiscal-year phase. `cbo_opt64` **62.3% → 44.5%** against a
  pre-registered band of 42 ± 4; Tier 1 **15.9% → 15.2%** with only that row
  moving; derived `biden_corporate_28` **−7.81% → +4.04%**. The window-average
  marginal share fell **90.8% → 80.8%**, closing an inconsistency independent of
  any target — the old aging grew the base 3.4× faster than the receipts it is a
  share of, so by FY2033 it priced a point against *more* base than the baseline
  implies exists. `derived` only, so no shipped number moved and no caption was
  owed. **Its finding**: `CBOBaseline.generate().corporate_income_tax` grows at
  **4.88%/yr** and, under `use_real_data=True`, returns an **identical** path for
  all three vintages. Nothing scored reads it today; it is a 🟢-tier defect and a
  carry-over.
- **PR #122: the corporate and PTC targets, moved onto documents or left with a
  reason.** No model output changed. `biden_corporate_28` became
  `line_item_differs` through a new **`scope_differs`** kind — the figures agree to
  **0.2%** (Treasury prints $1,349,941M) and the *reforms* do not, because the
  row's own chapter has moved the GILTI effective rate with the statutory rate
  since FY2023 while the factory sets `gilti_rate_change=0.0`; the target did not
  move, because the GILTI leg's size is never printed. A `line_item_differs` row
  must now carry a figure gap wider than tolerance **or** a filled `scope_differs`,
  never neither. `biden_corporate_28_fy2022` was registered as the module's second
  published target and **never to be fitted** — the only *rate-only* corporate row
  any Green Book prints, and deliberately **not** added to `KNOWN_SCORES`, because
  `assistant/benchmarks.py` would have turned a 2021-vintage figure into an
  interpolation anchor for the shipped Ask assistant. `cbo_opt64`'s estimator was
  corrected to **JCT** and its `known_limitations` rewritten, with the §174 anchor
  inflation sized at **11.1%** (an upper bound that takes the row to ~46%, not to
  CBO). `trump_corporate_15` was superseded to the published range
  **[+$595.0B, +$673.1B]** — PWBM Table 1 and Tax Foundation Table 2, printed side
  by side by CRFB — anchored on Tax Foundation's because it is a standalone
  analysis of this one reform rather than a stacked row in a whole-campaign
  package; the model sits **$818.7B outside**, and a third of that is bonus
  depreciation (+$294.2B), which neither published figure includes and which is not
  adjusted away because summing two rows of PWBM's table would be constructing a
  target rather than reading one. The preset's description, which had been quoting
  this model's own output back at users as "~$1.9T", now states the published
  range. And `repeal_ptc` was **examined and left**: its −$1,100B traces to
  CBO/JCT pub. 51298 Table 2's **$1,142B**, 3.8% away — a baseline projection in a
  repeal-score column, whose adoption would take the row from 18.5% to 21.5%. No
  scored repeal of §36B exists in any CBO or JCT publication, including the
  September 2025 marketplace menu (pub. 61734).

**Decision 1's corporate comparison now points the other way, and the owner
kept `reported`.** Measured on the merged tree, where both PR #121's base
projection and PR #122's moved targets apply, the module reads **reported 62.75%
against derived 61.43%** on three published targets — derived leads, narrowly, by
winning the FY2022 rate-only row and losing a little on the other two. The flip
was built and pre-registered as **PR #124** (`planning/lanes/DECISION1_corporate_mode.md`
on that branch; every moved number landed on its prediction) and **closed
unmerged on 2026-09-05 by owner decision**: on this benchmark set the mean cannot
discriminate — derived wins one row of three, rows one and two are the *same
reform on the same window* with published targets 57% apart, so one model number
is scored against both and "winning" means sitting lower rather than tracking a
vintage, and row three is missed by more than 100% in both modes. Flipping would
also have left `biden_corporate_28` a fitted row scored by a path with nothing
fitted in it, which no rule covers. **`CORPORATE_APP_MODE` stays `reported`**;
the override and its revisit trigger — a rate-only published 28% score on a
carried vintage — are recorded in `planning/MODELING_IMPROVEMENT.md` §6.2 item 33.
Neither figure is small, and the comparison has reversed three times in four PRs —
twice because a row whose target was the model's own output moved.

### Modelling Wave 5 — a payroll base that is earnings, a corporate base that is published, a realizations base that grows; plus frozen classroom links and one app scoring window (2026-09-05)

Three modelling lanes on disjoint files, plus two blue-tier PRs and the
coordinator's gate re-derivation. **Wave 5 is not in the plan's sequencing** — it
is three of §6.2's carry-over items taken in parallel. Every lane pre-registered
its expected movement in [`planning/lanes/`](../planning/lanes/) **before**
touching code and appended an outturn afterwards; §5.5 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md) carries
the summary and the four findings. PRs **#111** (frozen assignment links),
**#113** (payroll at the margin), **#114** (corporate at the margin), **#115**
(app default scoring window), **#116** (preferential rate at the margin),
**#117** (CI gate).

**Only Tier 1 moved, and that is the point.** No target moved and no constant was
retuned, so 0 of the 23 fitted rows and 0 of the 31 reconstruction rows changed
and `run_loo.py --donor-matrix` is byte-identical — a falsification test each
lane registered in advance and each passed. It is the first wave in which only
Tier 1 moved, so there is no composition to net out.

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 18.0% / 12.6% median / 14 within 15 / 21 within 25 | **26 @ 15.9% / 11.4% / 16 / 22** |
| Calibrated, fitted | 23 @ 1.6%, 23/23 within 15 | **unchanged — 0 rows moved** |
| Unfitted module reconstructions | 31 @ 56.6% / 29.9% median / 9 within 15 | **unchanged — 0 rows moved** |
| Calibrated, leave-one-out | 18 derivable @ 29.6% / 19.1% median / 8 within 15 | **byte-identical output** |
| Distributional (7 tables) | 0.00–5.86pp (ARP 3.72) | **unchanged** |
| Scorecard rows | 80 (73 published) | **unchanged** |
| `revised_target_entries` | 15 | **15** — no target moved |
| Tier 1 error mass | 468.1 over 26 (payroll largest at 109.6, 23.4%) | **412.9** (capital gains largest at **104.5, 25.3%**; payroll **15.6, 3.8%**) |
| Tier 1 CI gate | `--max-mean-error 25 --min-within-25pct 20` | **`20 / 21`**, both tightening |
| Tests | 3322 passed, 1 skipped | **3415 passed, 1 skipped** (`python -m pytest tests/ -q`) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt61_new_payroll_tax_1pct` (Tier 1) | −$1,281.5B | −$1,975.0B | **−$1,378.2B** | 54.1% → **7.5%** |
| `cbo_opt61_new_payroll_tax_2pct` (Tier 1) | −$2,540.0B | −$3,950.0B | **−$2,745.0B** | 55.5% → **8.1%** |
| `cbo_opt47_ltcg_qdiv_2pp` (Tier 1) | −$103.3B | −$57.1B | **−$92.5B** | 44.8% → **10.5%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$240.5B | **−$379.2B** | 16.7% under → **31.4% over** *(pre-registered regression)* |
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$322.7B | **−$461.5B** | 0.2% → **43.3% over** *(pre-registered regression; the 0.2% was two errors cancelling)* |
| `cbo_opt64_corporate_rate_1pp` (Tier 1) | −$135.7B | −$199.6B | **−$220.3B** | 47.1% → **62.3%** *(pre-registered regression)* |
| 💊 Expand Drug Negotiation (app preset) | — | −$33.5B | **−$41.8B** | one more post-2029 year in the FY2026–2035 window |
| 💊 Comprehensive Drug Reform (app preset) | — | −$150.5B | **−$158.9B** | same |
| Tailor: +2pp all brackets / +5pp all brackets / +5pp above $1M / 39.6% above $1M + step-up repeal | — | −$56.4B / −$110.9B / −$22.3B / −$490.7B | **−$91.4B / −$183.7B / −$46.9B / −$626.9B** | Decision 6 caption ships with them |

- **PR #113: the payroll base is now earnings, not a receipts total divided by
  the wrong rate.** The two CBO Option 61 rows went **54.1% / 55.5% → 7.5% /
  8.1%**, the largest single move of the wave, and reproduced the lane's hand
  arithmetic to the decimal. **The plan's own scoping was wrong on both halves**:
  §2.1 called for "employer-share incidence + income-tax offset", and CBO's
  option text says the tax "would be paid entirely by employees" — adding that
  offset would have moved the model *further* from the target, for a reason the
  source explicitly rules out. The real defect was `$400B / 2.9% = $13,793B`,
  Medicare receipts divided by a rate that does not raise all of them, with the
  0.9% Additional Medicare Tax's own $15B sitting four lines above it in the same
  dict. The base is now CBO's February 2024 wage path × the Trustees'
  covered-earnings ratio. **A second module was found with an inverted
  behavioural-offset sign** — `trade.py` was the first, in Wave 3 — and neither
  was found by a test, because both modules' calibrated factories zero the
  elasticity.
- **PR #114: the corporate rate is priced on a published base, and the row got
  worse on purpose.** `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**,
  pre-registered and landed to the decimal along with all fifteen other
  registered rows. The derived path uses IRS SOI Table 11's income subject to tax
  ($2,879.1B, TY2022), realized at SOI's own after/before-credits ratio and
  settled on IRC §6655's calendar. **The fitted $1,900B it replaced was not a
  wrong concept but a stale vintage**, within 3% of SOI's TY2018 figure — and it
  was two errors, a base 34% too small against an offset well below what the
  published semi-elasticity implies at 7pp, which nearly cancel at 7pp and do not
  at 1pp. What is left is a disagreement between documents: CBO 60557 prices a
  point at **$135.7B** over the window and Treasury's FY2025 Green Book at
  **$192.8B**, with the *larger* rate change carrying the *larger* per-point
  yield. `CORPORATE_APP_MODE` stays `reported` under Decision 1 (1.92% against
  9.67%), so nothing a user sees moved. Two findings recorded and not acted on:
  **`corporate.py`'s offset returns `abs(static_effect)`**, so a shipped rate-cut
  preset books a behavioural response that makes the cut *more* expensive (the
  third module with an offset defect, now pinned by a test in both behaviours),
  and **the corporate module has no leave-one-out row at all**.
- **PR #116: the realizations base grows with the stock it is a flow off.**
  `R(t) = h · A(t)` at the module's own 5.8% net-worth CAGR, introducing no new
  constant, closed **34.3 of CBO Option 47's 44.8 points, to 10.5%**, with no
  elasticity, bracket, threshold or rule touched. The obvious hypothesis was
  **refuted** by arithmetic already in the tree: SOI Table 3.5's preferential
  columns *exceed* the whole year's realized gains in both vendored years (1.046
  and 1.189), so they already contain qualified dividends, and adding a column
  would have double-counted $313–336B by being wrong twice. The same projection
  was registered as a **net Tier 1 regression** on the two Green Book rows and
  landed inside both bands. **The FY2022 row's old 0.2% was never accuracy** —
  Wave 4's own lane doc recorded it as two errors cancelling, and this lane
  removed the first — and about **17 of its 43 points are the window** it is
  scored on (target FY2022–2031, model FY2025–2034). Four Tailor rows moved
  26–110%, so a Decision 6 caption ships with them; the reconstruction scenarios
  and the CapitalGains leave-one-out are byte-identical, because a projection is
  a property of the base's vintage and those rows carry 2018 and 2021 vintages.
- **PR #111: frozen assignment links.** `frozen=1` beside the provenance stamps
  a share link already carried (`baseline=&engine=&spec=&mode=`) pins vintage,
  engine, dynamic and policy on `/explore` and `/tailor`, so a whole class hands
  in one set of numbers; the pinned controls render disabled under a "🔒 Frozen
  for this assignment" banner with a provenance line under the number. A link
  frozen on a vintage this deployment is not serving **refuses to score** and
  names both vintages, rather than falling back quietly — as do a `frozen=1` with
  no `baseline=` and an unknown `engine=` token. `?classroom=1` on a result
  surface reveals the instructor control that emits one. Blue tier: no scoring
  change, every existing URL preserved. Deliberately left out: **Build packages
  are not freezable**, and the **Data & methodology options are not pinned**.
- **PR #115: one app scoring window, FY2026–FY2035.** `APP_DEFAULT_START_YEAR =
  2026` now routes through every app surface and the API's `budget_window`; the
  window was never chosen before, it was whatever `Policy.start_year` happened to
  be, so Explore and Tailor could render different windows off the same baseline.
  Presets move with `max(policy.start_year, APP_DEFAULT_START_YEAR)`, so a
  factory stating a later effective year keeps it. **The library defaults stay at
  2025**, because each benchmark is scored over the window its own document used
  and moving one would be a target revision with its own ledger. Exactly one
  validation path read a default — the five sectoral runners pinned their scorer
  but not their policy — and it was fixed in a separate first commit that leaves
  all five scripts byte-identical. Two pharma presets moved by one calendar year,
  correctly.
- **PR #117: the Tier 1 CI gate, re-derived by the workflow's own rule.**
  `--max-mean-error 25 --min-within-25pct 20` → **`20 / 21`** (ceiling
  `ceil(15.9 × 1.25) = 20`; floor `22 − 1 = 21`). Both tighten. A modelling lane
  never touches the yardstick, so the coordinator re-derives it separately.

**Every Wave 5 module keeps `reported` as its app default under Decision 1.** The
only shipped numbers that moved are the four Tailor capital-gains rows, with
their Decision 6 caption, and the two pharma presets the window change carried
forward a year.

### Modelling Wave 4 — the death channel's carve-outs, CBO's household universe, Option 56's indexation, Part D's three channels, statutory AMT phase-outs, thirteen targets onto their documents (2026-09-05)

Six lanes on disjoint files plus a target-provenance lane and the coordinator's
gate re-derivation. **Wave 4 is not in the plan's sequencing** — it is six of
§6.2's carry-over items taken in parallel. Every lane pre-registered its expected
movement in [`planning/lanes/`](../planning/lanes/) **before** touching code and
appended an outturn afterwards; §5.4 of
[`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md) carries
the summary, the three findings and the five missed pre-registrations. PRs
**#104** (distributional households), **#105** (Option 56 excess share), **#106**
(AMT phase-outs), **#107** (target provenance), **#108** (gains at death),
**#109** (pharma Part D), **#110** (CI gate).

**Validation tiers moved, and two of the four changed population — so the
like-for-like readings are printed beside them, and in this wave both printed
means fell for reasons that are not improvements:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 26 @ 31.0% / 15.1% median / 13 within 15 / 19 within 25 | **26 @ 18.0% / 12.6% / 14 / 21** |
| Calibrated, fitted | 28 @ 2.0%, 28/28 within 15 | **23 @ 1.6%, 23/23** — or **28 @ 3.0%, 27/28** with Wave 4's five revised rows held in place (29 @ 5.2%, 27/29 with the TCJA-AMT row too) |
| Unfitted module reconstructions | 26 @ 61.8% / 38.0% median / 5 within 15 | **31 @ 56.6% / 29.9% / 9** — but **65.7% / 40.5% over the same 26 rows**, i.e. *worse* |
| — sectoral presets | 14 @ 81.0% / 38.0% median | **15 @ 82.6% / 39.0%** (**88.2%** over the 14) |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | 39.6% | **unchanged** |
| — TCJA AMT relief | 66.8% | **unchanged** |
| — Wave 4 provenance arrivals | — | **5 @ 9.4%** |
| Calibrated, leave-one-out | 18 derivable @ 28.4% / 16.5% median / 9 within 15 | **18 derivable @ 29.6% / 19.1% / 8** — every bit of it a *target* movement, no derivation moved |
| — `Credits` | 20.5% | **18.5%** |
| — `Expenditures` | 30.2% | **35.7%** |
| Not cross-validatable | 4 | **unchanged** |
| Distributional (7 tables) | 0.00–7.77pp | **0.00–5.86pp** (ARP 7.77 → **3.72**) |
| Scorecard rows | 80 (73 published) | **unchanged** |
| `revised_target_entries` | 3 | **15** |
| `line_item_differs` (calibrated) | 13 | **5**, each with a written verdict |
| Provenance (calibrated) | 19 / 13 / 15 / 7 / 0 | **30 / 5 / 12 / 7 / 0** |
| Tier 1 CI gate | `--max-mean-error 40 --min-within-25pct 18` | **`25 / 20`** |
| Tests | — | **3322 passed, 1 skipped** (`python -m pytest tests/ -q`) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$1,022.3B | **−$322.7B** | 217.5% → **0.2%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$678.1B | **−$240.5B** | 134.9% → **16.7%** |
| `cbo_opt51_gains_at_death` (Tier 1) | −$536.1B | −$581.2B | **−$432.8B** | 8.4% → **19.3%** *(worse, pre-registered as a regression)* |
| `cbo_opt56_employer_health_income_only` (Tier 1) | −$697.0B | −$529.9B | **−$605.8B** | 24.0% → **13.1%** |
| `biden_high_income_tax` (Tier 1, **target revised**) | −$252.0B → **−$245.9B** | −$216.5B | −$216.5B | 14.1% → **12.0%** |
| `expand_drug_negotiation` (Tier 2b) | −$500.0B | −$371.5B | **−$33.5B** | 25.7% → **93.3%** *(worse, by design)* |
| `international_reference_pricing` (Tier 2b) | −$100.0B | −$746.2B | **−$801.0B** | 646.2% → **701.0%** *(worse, by design)* |
| `universal_insulin_cap` (Tier 2b) | +$11.4B | +$7.0B | +$7.0B | **39.0%**, unchanged to the cent |
| `eliminate_salt` (fitted → Tier 2b, **target revised**) | −$1,200.0B → **−$1,621.0B** | −$1,260.3B | −$1,260.3B | 5.0% → **22.3%** |
| `repeal_salt_cap` (fitted → Tier 2b, **target revised**) | +$1,100.0B → **+$1,169.0B** | +$1,155.6B | +$1,155.6B | 5.1% → **1.2%** |
| `biden_eitc_childless` (fitted → Tier 2b, **target revised**) | +$178.0B → **+$162.6B** | +$178.0B | +$178.0B | 0.0% → **9.5%** |
| `extend_enhanced_ptc` (fitted → Tier 2b, **target revised**) | +$350.0B → **+$335.0B** | +$366.2B | +$366.2B | 4.6% → **9.3%** |
| `ira_enforcement` (fitted → Tier 2b, **target revised**) | −$200.0B → **−$180.4B** | −$188.9B | −$188.9B | 5.5% → **4.7%** |
| `biden_gilti_reform` (Tier 2b, **target revised**) | −$280.0B → **−$373.9B** | −$230.3B | −$230.3B | 17.8% → **38.4%** |
| `fdii_repeal` (Tier 2b, **target revised**) | −$200.0B → **−$158.0B** | −$110.7B | −$110.7B | 44.7% → **29.9%** |
| `biden_full_international` (Tier 2b, **target revised**) | −$700.0B → **−$632.2B** | −$353.7B | −$353.7B | 49.5% → **44.1%** |
| `repeal_ev_credits` (Tier 2b, **target revised**) | −$200.0B → **−$182.3B** | −$228.4B | −$228.4B | 14.2% → **25.3%** |
| `trump_universal_10` (Tier 2b, **target revised**) | −$2,000.0B → **−$2,171.1B** | −$1,258.5B | −$1,258.5B | 37.1% → **42.0%** |
| `auto_tariff_25` (Tier 2b, **target revised**) | −$100.0B → **−$386.2B** | −$182.2B | −$182.2B | 82.2% → **52.8%** |
| `reciprocal_tariffs` (Tier 2b, **target → a range**) | −$1,200.0B → **[−$1,800B, −$1,400B]**, anchor −$1,500B | −$1,396.8B | −$1,396.8B | 16.4% → **6.9%** vs the anchor; $3.2B outside the nearer bound |
| ARP refundable credits (distributional) | — | 7.77pp | **3.72pp** | scored on CBO's own household universe |

- **PR #108: the death channel now knows what a realization-at-death proposal
  does not tax.** Six carve-outs transcribed from the Green Books' own text —
  spousal transfers, charitable bequests, the §121 residence exclusion, tangible
  personal property, a family-owned-business deferral, and the per-donor
  exclusion applied *after* the others — plus a semi-log rate response at death.
  Tier 1 fell **31.0% → 18.5% on this PR alone** and the capital-gains error mass
  **405.6 → 81.0**, from half the tier's mass to a sixth. **The Treasury row's
  0.2% is two errors cancelling and must never be quoted as accuracy**: the
  mechanism removes 87.2% of that row's death channel where the pre-registered
  hand path said 92.8%. Option 51 got **worse by design**, and that was
  registered in advance — its 8.4% had been bought by taxing charitable bequests
  and small decedents' housing gains that no such regime reaches.
- **PR #104: the distributional engine gained CBO's household universe**,
  size-adjusted household income before transfers and taxes with quintiles
  containing equal numbers of *people*, and each benchmark is now registered on
  the universe **its source ranks**, with the surfaces reporting the universe
  **scored**. ARP **7.77pp → 3.72pp**; six of the seven tables unmoved to the
  hundredth. Two findings: **3 of the 7 fall back `household→tax_unit`** because
  `TCJAExtensionPolicy` and the corporate policy have no microsim path — so the
  two *circular* rows are visibly scored on a population CBO does not use — and a
  per-household **dollar column was wrong by a factor of three** and invisible to
  every gate, because the error metric scores shares.
- **PR #105: Option 56's excess share now knows what year it is.** 24.0% →
  **13.1%**, from CBO's own chained-CPI indexation rather than a fitted
  parameter; the pre-registered 5%/yr escape hatch that would have landed the row
  at 0.6% was declared in advance and **not taken**. What is left: a **base
  omission** (CBO caps premiums *and* FSA/HRA/HSA contributions) and an
  **unsourced behavioural offset whose sign convention is the reverse of
  `TaxPolicy`'s**, both named and neither tuned.
- **PR #106: statutory §55(d)(2) transcribed from eleven Revenue Procedures.**
  No benchmark moved, by design. A threshold reform stops scoring exactly zero
  (a −$200,000 MFJ change is now +$300.1B over ten years where every value used
  to return 0.0), and the module can represent P.L. 119-21's design as distinct
  from a naive TCJA extension. Finding worth keeping: two schedule rows were 20%
  wrong and it never showed, because both benchmarks sit on anchors.
- **PR #109: Part D's three federal channels — and the reconstruction rows got
  worse.** Direct subsidy 0.37269, reinsurance 0.10470, low-income subsidy
  0.29864, federal total 0.77603 against the 2023 aggregate's 0.7626; a
  negotiation ladder reproducing all three published CMS cycles to within 2.1%;
  a RAND coverage base. The two pre-registered mechanisms landed within $3B of
  the pre-registered figure, and then the lane's **own** ladder condemned an
  unsourced $220B Part D gross-spending constant the reference-pricing leg also
  reads — CMS's own sentence puts the total at $281B. **The alternative was to
  keep an unsourced number because it flattered the prediction.** Presets moved
  by design, with a Decision 6 caption in the same PR: negotiation −$371.5B →
  **−$33.5B**, reference pricing −$746.2B → **−$801.0B**, comprehensive −$573.5B
  → **−$150.5B**, insulin unchanged.
- **PR #107: thirteen targets onto their documents, and no modelling change at
  all.** Every `model_10yr_billions` byte-identical, every LOO derivation
  unchanged, no constant retuned, no threshold touched. Two of the thirteen were
  not merely unsourced but the wrong *kind* of number: the auto tariff's −$100B
  was a **per-year** claim in a ten-year column, and the reciprocal-tariff target
  was **Tax Foundation's dynamic score in a conventional column** — a tier error
  no rescaling would have found, now the second **range** revision. **Six of the
  thirteen got worse**, which is the shape a correct provenance pass has. Four
  more benchmarks were examined and deliberately left; `line_item_differs` went
  13 → **5**, and all five carry a written verdict.
- **PR #110: the Tier 1 CI gate re-derived by the workflow's own rule** after the
  death channel halved the tier — ceiling `ceil(18.0 × 1.25) = 23` rounded up to
  **25**, floor `21 − 1 = **20**`, a tightening on both.

**Every Wave 4 module keeps `reported` as its app default under Decision 1.** The
shipped numbers that moved are the three drug-pricing presets, by design; the
insulin preset's *description string* was also corrected, having still quoted the
−$15B target PR #90 superseded.

### Modelling Wave 3 — international overlap, net tariffs, credits from CPS microdata, five targets onto their documents (2026-09-02)

Wave 3 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md)
completes the plan: three modelling lanes on disjoint files, a target-provenance
lane alongside them, and the coordinator's gate re-derivation. Every lane
pre-registered its expected movement in `planning/lanes/` **before** touching
code; §5.3 of the plan carries the outturn, the five findings and the three
missed pre-registrations. PRs **#98** (L9 international), **#99** (L8 tariffs),
**#100** (target provenance), **#101** (L3 credits), **#102** (CI gate).

**Validation tiers moved, and three of the four changed population — so the
like-for-like readings are printed beside them:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered | 25 @ 31.3% / 14.1% median / 13 within 15 / 18 within 25 | **26 @ 31.0% / 15.1% / 13 / 19** |
| Calibrated, fitted | 30 @ 2.2%, 30/30 within 15 | **28 @ 2.0%, 28/28** — or **29 @ 4.3%, 28/29** with the revised row held in place |
| Unfitted module reconstructions | 24 @ 72.1% / 40.0% median | **26 @ 61.8% / 38.0%** (**63.6%** over the pre-L8 24 rows) |
| — sectoral presets | 12 @ 104.8% / 40.0% median | **14 @ 81.0% / 38.0%** (**87.8% / 32.3%** over the 12) |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | 39.6% | **unchanged** |
| Calibrated, leave-one-out | 17 derivable @ 32.3% / 19.2% median / 8 within 15 | **18 derivable @ 28.4% / 16.5% / 9** (**29.5%** over the 17) |
| — `Credits` | 45.1% | **20.5%** |
| — `Expenditures` | 4 cases @ 28.8% | **5 cases @ 30.2%** |
| Not cross-validatable | 5 | **4** — `eliminate_salt` left the excluded set and re-entered the derivable one |
| Distributional (7 tables) | 0.00–5.86pp | **0.00–7.77pp** (ARP 4.76 → **7.77**) |
| Scorecard rows | 79 (72 published) | **80 (73 published)** |
| `revised_target_entries` | 2 | **3** |
| CBO Options battery | 14 alternatives / 11 options / 65 excluded / 3 leakage | **15 / 12 / 64 / 2** |
| Tier 1 CI gate | `--max-mean-error 40 --min-within-25pct 17` | **`40 / 18`** |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt56_employer_health_income_only` (Tier 1, **new**) | −$697.0B | — | **−$529.9B** | — → **24.0%** |
| `fdii_repeal` (Tier 2b) | −$200.0B | −$170.0B | **−$110.7B** | 15.0% → **44.65%** |
| `biden_full_international` (Tier 2b) | −$700.0B | −$413.0B | **−$353.7B** | 41.0% → **49.47%** |
| `trump_universal_10` (fitted → Tier 2b) | −$2,000.0B | −$2,021.6B | **−$1,258.5B** | 1.1% → **37.1%** |
| `trump_china_60` (fitted → Tier 2b) | −$500.0B | −$531.1B | **−$278.4B** | 6.2% → **44.3%** |
| `auto_tariff_25` (Tier 2b) | −$100.0B | −$252.3B | **−$182.2B** | 152.3% → **82.2%** |
| `steel_tariff_25` (Tier 2b) | −$60.0B | −$103.9B | **−$52.9B** | 73.2% → **11.9%** |
| `reciprocal_tariffs` (Tier 2b) | −$1,200.0B | −$2,736.0B | **−$1,396.8B** | 128.0% → **16.4%** |
| `biden_ctc_2021` (LOO) | +$1,600.0B | +$574.1B | **+$1,528.5B** | −64.1% → **−4.5%** |
| `ctc_extension` (LOO) | +$600.0B | +$432.0B | **+$714.2B** | −28.0% → **+19.0%** |
| `biden_eitc_childless` (LOO) | +$178.0B | +$101.2B | **+$110.4B** | −43.1% → **−38.0%** |
| `eliminate_salt` (LOO, **readmitted**) | −$1,200.0B | *excluded* | **−$1,077.9B** | — → **+10.2%** |
| `repeal_salt_cap` (LOO) | +$1,100.0B | +$1,144.0B | **+$777.0B** | +4.0% → **−29.4%** |
| ARP refundable credits (distributional) | — | 4.76pp | **7.77pp** | worse, and the more correct configuration |

- **L9 (PR #98): the double count the plan named does not exist.** The module's
  UTPR reads profits of foreign-parented groups and its GILTI reads US-parented
  CFC income, so the new `_estimate_base_overlap()` term nets **exactly zero**
  for every shipped factory. What it establishes instead is algebra: with an 80%
  foreign tax credit, a per-country GILTI at 21% claims more than a 15% top-up in
  every jurisdiction, so a policy carrying both raises the larger, never the sum —
  and at 2026's statutory 13.125% the shared-claim share is 0.9916, not 1, so a
  constant would have got one case right and the other wrong. The **FDII
  identity** replaced a flat $20B/yr with Treasury OTA's published $130,230M
  cost, moving the row toward the document and away from a target 54% above it;
  both regressions were pre-registered and landed to two decimal places. The
  package's real residual is a **level**: a $15B UTPR against Treasury's own
  $136,313M row and JCT's implied $133.9B.
- **L8 (PR #99): tariff scores are net, not gross, and every shipped preset
  moved.** `estimate_static_revenue_effect` had no income-and-payroll offset at
  all. It now subtracts duty avoidance, the ~25% offset CBO/JCT/Treasury apply to
  any indirect tax, and the receipts lost to retaliation, on Census 2024 levels,
  a tax-inclusive rate and a border pass-through frozen at 1.00. **The five
  presets moved 28–49%**, with a caption computed from the scored result shipping
  in the same PR under owner Decision 6. Two fitted coverage constants were
  re-derived or deleted, so no `TRADE_BASELINE` constant is fitted to any target
  and both Trump rows left the fitted tier. The lane also found and fixed a **sign
  defect**: `estimate_behavioral_offset` returned an unsigned positive number, so
  a 5pp tariff *cut* on a $1,000B base scored $711B of deficit against a $553B
  gross revenue loss; signed, the same cut scores $394B. No shipped preset moves
  on that fix — all five are increases.
- **L3 (PR #101): credits are computed per unit over CPS ASEC tax units.** Two
  statutory parameter sets run through `MicroTaxCalculator` and differenced on
  final liability, in place of `Δcredit × units × participation`. The largest
  single correction is a **counterfactual**, not a parameter: IRC §24's $2,000
  reverts to $1,000 after 2025, so a window opening in 2025 is scored against
  current law for one year and the pre-TCJA regime for nine — $883B against a
  fixed baseline, **$1,528B** against the one the statute specifies. Three dead
  levers now have readers, and the engine's EITC qualifying-child count moved
  from the CTC's under-17 column to IRC §32(c)(3)'s definition (**79.7M against
  65.0M**). Per owner **Decision 4** the raw 148 MB March 2024 ASEC archive is
  fetched by `scripts/fetch_cps_asec.py` (SHA-256 verified) into a cache outside
  the repository and never vendored; five dependent age bands were added and
  every pre-existing column comes back byte-identical, with the SOI ratios
  (119% / 81%) unmoved. Per **Decision 5** the three tautological credit
  benchmarks carry a per-case declaration. **The ARP distributional benchmark got
  worse, 4.76pp → 7.77pp**, and that is the finding: the old figure ranked one of
  three components by IRS return counts and the other two by CPS tax units, and
  the two universes were partly cancelling. Scored consistently the quintile
  dollar levels move from about a third of CBO's to close to them and the bundle
  totals $485B, within 10% of the three provisions' actual cost, while the share
  error grows because the model's bottom quintile is 38.2M tax units against
  CBO's ~26M households.
- **PR #100: five targets, five judgements, one modelling change.** **CBO Option
  56 promoted into Tier 1** at −$529.9B against −$697.0B (24.0%) — a leakage
  exclusion is not permanent, and L6 had removed the fitted annual its only path
  ran through; only CBO's third alternative is scored, because 56.3 and 56.6 need
  a payroll base the module does not have. **Pillar Two re-benchmarked as a
  published range**, [−$102.6B, +$56.5B] from JCX-22-23 Table 2, with the model
  **inside** it at distance $0.0B — the ledger gained `is_range`, `contains()`
  and `distance_to_range()`, and the scorecard and API gained
  `published_range_low_billions` / `..._high_billions` / `within_published_range`
  / `distance_to_published_range_billions`. **The leaked SALT constant replaced by
  its computation**: `annual_cost_no_cap = 120.0` was exactly the `eliminate_salt`
  target over ten and is now **$89.55B** from IRS SOI Table 2.1 priced at the
  statutory schedule, checked by the identical computation on the *limited* column
  returning $25.0B against the record's own 25.0. **The estate target examined and
  deliberately not moved**, under a new `EXAMINED_NOT_REVISED` state, because
  JCT's −$429.6B totals a ten-section bill the module does not construct. **The
  Treasury FY2022 combined-row reading confirmed**, not superseded.
- **PR #102: the Tier 1 CI gate re-derived by the workflow's own rule** after the
  battery grew — ceiling `ceil(31.0 × 1.25) = 39 → 40`, unchanged; floor
  `19 − 1 = 18`, a tightening from 17.
- **Nothing else a user sees changed.** Every Wave 3 module keeps `reported` as
  its app default under owner Decision 1 (credits: 0.0% reported against 20.5%
  derived — read with Decision 5 in hand, since the fitted annuals *are* their
  targets over ten). No target moved from a modelling branch, no CI threshold was
  touched by a lane, no per-benchmark constant was added, and two were deleted.

### Modelling Wave 2 — estate distribution, tax-expenditure units, capital gains (2026-09-02)

Wave 2 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md),
three lanes on disjoint files. Every lane pre-registered its expected movement in
`planning/lanes/` **before** touching code; §5.2 of the plan carries the outturn,
the four findings and the three missed bands. PRs **#93** (L4 estate), **#94**
(L6 tax expenditures), **#95** (L1 capital gains).

**Validation tiers moved. Report them separately, as always:**

| Tier | Before | After |
|---|---|---|
| Out-of-sample, pre-registered (n=25) | 34.4% / 16.1% median / 12 within 15 / 16 within 25 | **31.3% / 14.1% / 13 / 18** |
| Calibrated, fitted | 33 @ 2.8%, 32/33 within 15 | **30 @ 2.2%, 30/30** — or **31 @ 4.2%, 30/31** with the revised row held in place |
| Unfitted module reconstructions | 21 @ 76.7% / 41.0% median | **24 @ 72.1% / 40.0%** |
| — 12 sectoral presets | 104.8% / 40.0% median | **unchanged** |
| — 8 P.L. 119-21 line items | 35.8% | **unchanged** |
| — 3 capital-gains scenarios | *(in the fitted tier)* | **39.6%** |
| Calibrated, leave-one-out | 18 derivable @ 58.7% / 32.5% median / 6 within 15 | **17 derivable @ 32.3% / 19.2% / 8** |
| — `CapitalGains` | 171.2% | **39.6%** |
| — `Estate` | 25.8% | **10.4%** |
| — `Expenditures` | 5 cases @ 39.4% | **4 cases @ 28.8%** |
| Not cross-validatable | 4 | **5** (`eliminate_salt` joined) |
| Distributional (7 tables) | 0.00–5.86pp | **unchanged** |
| Tier 1 error mass | 859.5 | **781.8** (capital gains 479.4 → **405.6**) |

**Per-case, the rows that moved:**

| Row | Official | Before | After | Error |
|---|--:|--:|--:|--:|
| `cbo_opt51_gains_at_death` (Tier 1) | −$536.1B | −$83.7B | **−$581.2B** | 84.4% → **8.4%** |
| `cbo_opt47_ltcg_qdiv_2pp` (Tier 1) | −$103.3B | −$205.7B | **−$57.1B** | 99.1% → **44.8%** |
| `biden_capital_gains_39` (Tier 1) | −$288.6B | −$699.4B | −$678.1B | 142.3% → **134.9%** |
| `treasury_capgains_39_plus_stepup_elim` (Tier 1) | −$322.0B | −$816.6B | **−$1,022.3B** | 153.6% → **217.5%** |
| `cbo_opt45_top4_brackets_2pp` (Tier 1) | −$569.5B | −$716.4B | −$671.6B | 25.8% → **17.9%** |
| `illustrative_1pp_all` (Tier 1) | −$960.0B | −$935.4B | −$920.3B | 2.6% → 4.1% |
| `cbo_opt45_all_rates_1pp` (Tier 1) | −$1,185.3B | −$935.4B | −$920.3B | 21.1% → 22.4% |
| `biden_high_income_tax` (Tier 1) | −$252.0B | −$284.5B | −$216.5B | 12.9% → 14.1% |
| `cbo_2pp_all_brackets` (LOO) | −$70.0B | −$154.3B | **−$79.8B** | −120.5% → **−14.0%** |
| `pwbm_39_with_stepup` (LOO) | +$33.0B | −$89.3B | **+$23.6B** | −370.5% → **−28.4%**, sign restored |
| `pwbm_39_no_stepup` (LOO) | −$113.0B | −$138.6B | −$26.6B | −22.6% → **+76.5%** |
| `biden_estate_reform` (LOO) | −$450.0B | −$244.9B | **−$457.2B** | +45.6% → **−1.6%** |
| `extend_tcja_exemption` (LOO) | +$167.0B | +$176.9B | +$199.0B | +6.0% → **+19.2%** |
| `cap_employer_health` (LOO) | −$450.0B | −$11.5B | −$30.5B | +97.4% → **+93.2%** |
| `cap_charitable` (LOO) | −$200.0B | −$168.5B | −$173.8B | +15.7% → **+13.1%** |
| `eliminate_salt` (LOO) | −$1,200.0B | −$300.9B | −$1,444.4B | +74.9% → **excluded** (−10.9% against the published −$1,621.0B) |

- **L1 (PR #95) found a fifth defect under the plan's four, and it was a unit
  error.** Realization elasticities were applied as **net-of-tax-rate**
  elasticities where CRS R48562 defines them on the **tax rate** (semi-log,
  `R = B·exp(−b·t)`, so `ε = b·t`), which made the frozen 0.8 an effective
  **0.25**. Dowd–McClelland–Muthitacharoen's 0.72 at CRS's 22% reference rate
  gives **b = 3.273** against **JCT's own 3.1** and a revenue-maximizing rate of
  30.6% — so 43.4% sits past the peak and the model reproduces PWBM's
  revenue-*loss* finding with no multiplier at all. The 5.3× lock-in multiplier,
  the residual-avoidance multiplier and `fiscal_model/validation/scenarios.py`'s three
  per-case tuples are **deleted**. The base is now IRS SOI Table 3.5's
  bracket-priced income ($1,107.7B in five buckets, not $1,368B at a blended
  15.5%); lock-in is a derived **1.44×** price wedge from an accrued-gains stock;
  gains at death are **$196.2B in 2025 growing 5.8%/yr** across five estate-size
  classes, not a flat $54B/yr. **Tailor's capital-gains form loses its lock-in
  slider**, its short/long-run elasticity pair, its transition slider and its
  gains-at-death input, and gains persistent/transitory elasticity inputs; its
  scored outputs move (a +2pp all-brackets change goes −$219.2B → −$56.4B). No
  preset moved. What is left undone is the **death channel's behavioural
  response** — no spousal or charitable carve-out, no §121 residence exclusion,
  no family-business deferral — which is the entire residual on the two Treasury
  rows, and the realizations base is still not projected across the window.
- **L4 (PR #93) replaced an estate blend that was *exactly invariant* in the
  exemption.** For any `E ≤ $6.4M` the old machinery's count × average product
  was constant, so lowering the exemption derived **zero** revenue — and the app
  scored "cut the estate exemption to $3.5M" as free. A Pareto size distribution
  of the estate tax base (α = **1.73843**, pooled from seven local estimates
  inside IRS SOI Estate Tax Statistics Table 1 for filing years 2010, 2013 and
  2024) replaces eight fitted constants, anchored on SOI's own FY2024 row and
  lagged one year because a Form 706 is filed the year after death (IRC
  §6075(a)). `create_estate_exemption_change(3.5e6)` now returns **+$35.4B/yr**.
  The extension row got *worse* (+6.0% → +19.2%) because its old 6% was a
  four-times-too-high level cancelling against a zero exemption response, and
  because the object that grows is the distribution rather than revenue. The
  **growth rate is unresolved**: SOI-fitted 6.81%/yr reproduces history but
  projects to figures no published estate estimate supports, so the module ships
  nominal GDP growth (3.82%) and over-states historical collections by 109% on
  2009 decedents; the choice is pinned by a test. Portability/DSUE and the
  graduated rate schedule remain unmodelled, and
  `create_warren_estate_proposal`'s fitted −$2,600B derives at **−$663.6B**
  because PWBM's figure scores a package with a separate wealth tax.
- **L6 (PR #94) made every cap declare its unit, and the leakage guard fired.**
  `CapUnit` distinguishes `BASE_DOLLARS`, `BENEFIT_RATE` and `BENEFIT_DOLLARS`,
  and each expenditure gained a benefit distribution by AGI class from IRS SOI
  Table 2.1 (`jct.gov` returns HTTP 403 to this environment on every URL; SOI is
  the administrative source under JCT's own tables and separates *total* from
  *limited* SALT). Making `eliminate` read `annual_cost_no_cap = 120.0` then
  tripped `loo.py`'s **untouched** leakage guard, because $120.0B is exactly the
  carried −$1,200B target over ten: the case is now not cross-validatable, and
  **part of the LOO improvement is that case leaving the denominator** — 31.7%
  like-for-like over 18 against the printed 32.3% over 17. SOI × statute puts the
  uncapped SALT deduction at **$89.6B/yr**, 25% below the record's $120.0B, while
  reproducing the *capped* $25.0B to a tenth of a percent. `cap_employer_health`
  moved only 4pp because **a $50,000 premium cap is above the entire
  distribution** (CBO's own 75th-percentile family premium is $31,300; the
  carried −$450B corresponds to a cap near **$26,400**) — a miss pre-registered
  before the code was written. **CBO Option 56 is now scorable**: +2.5% in its
  own first year, −12.8% with a year-indexed excess share; not yet promoted.
- **The three capital-gains scenarios left the fitted tier**, because deleting
  the per-case tuples removed the only constants ever fitted to them, so
  `calibrated_to_target` is now `False` and the runner says so. The fitted mean
  *fell* 2.8% → 2.2% while nothing regressed — those rows were what the tier had
  been carrying, and left in place they would have raised it to 6.2%. That is
  **composition, not accuracy**; read it next to the reconstruction tier or not
  at all. `run_loo.py --donor-matrix` now prints three identical rows: there is
  no donor left to be an answer key.
- **Every Wave 2 module keeps `reported` as the app default** under owner
  Decision 1 (estate 0.0% reported against 19.2% / −1.6% / +34.7% derived;
  expenditures 4.2% reported against 26.0% derived), so **no shipped preset
  moved**. `check_readiness.py`'s `holdout_protocol` check went PASS → **WARN**
  rather than FAIL: `pwbm_39_with_stepup` is a locked holdout id that now rates
  Poor with the direction right, and the repository's existing rule — a Poor
  entry carrying a documented `known_limitations` note on a benchmark the module
  is *not* fitted to is a warning — now applies to the holdout check on the same
  terms. The entry stays in the battery. Re-locking the protocol instead is an
  open owner decision, listed with five others in §6.1 of the plan.

### Tier 1 CI gate tightened to 40 / 17 (2026-09-02)

PR **#96**. The out-of-sample gate's own rule — ceiling = `ceil(mean × 1.25)`
rounded up to the nearest 5, floor = the current count within 25% minus one —
derives **40 / 17** from the post-Wave-2 battery (25 cases, 31.3% mean, 18 within
25%), against the **45 / 15** the workflow carried after Wave 1. A tightening,
which the rule says needs no reason. The derivation is recorded in the workflow
comment beside the earlier ones, and the places that quote the command now match.

### Tier-2 target revisions, and a supersede rule for the calibrated tier (2026-09-02)

PR **#90**. Two modelling lanes had referred *target* problems out of Wave 1:
L5 (`amt.py`) found its structural path landing about 1.8× closer to the document
than its fitted constant but could only say so, because the carried target
disagreed with the document; L7 (`pharma.py`) fixed an incidence bug and was
rewarded with a *worse* percentage, because its benchmark pointed the opposite
way. **No modelling change**: no constant retuned, no mechanism altered, no CI
threshold touched.

The calibrated tier had no supersede rule, so this adds the smallest mirror of
`preregistered.py`'s — `fiscal_model/validation/target_revisions.py`. The old
figure stays as a row marked `superseded_by`; the new row carries document,
table, row, page, date and a reason; `target_revision_problems()` fails if the
ledger and the registries the app reads ever disagree. Ledger entry and first
scoring are separate commits, so "the target moved before the model was allowed
to see it" is checkable from `git log`.

| Benchmark | Was | Is | Document |
|---|--:|--:|---|
| `extend_tcja_amt` | $450.0B | **$1,357.1B** | CRS **R48286** Table 1 (transcribing CBO 60114/60271) — "Increased Alternative Minimum Tax Exemption", FY2025–FY2034. The adjacent five-year column prints $466.2B, so $450B was 3.5% from the five-year cost and 66.8% from the ten-year one: a five-year figure in a ten-year column. Corroborated by JCT **JCX-35-25** at $1,362.810B (0.4% away) for P.L. 119-21's AMT provision. |
| `universal_insulin_cap` | −$15.0B (a saving) | **+$11.4B (a cost)** | CBO pub. **57957** (H.R. 6833), table p. 1 — outlays 6,566, revenues −4,793, FY2022–2031. A $35 monthly cap is a *cost-sharing* cap: it moves liability onto the plan and onto the federal subsidy for it. |
| `repeal_individual_amt` | $450.0B | **not moved** | Nothing to move it to — see below. |

**The tiers moved; report them separately, as always.**

| Tier | Before this PR | After |
|---|---|---|
| Out-of-sample, pre-registered (n=25) | 34.4% / 16.1% median / 12 within 15 / 16 within 25 | **unchanged** |
| Calibrated, fitted | 34 @ 2.7%, 33/34 within 15 | **33 @ 2.8%, 32/33** — or **34 @ 4.7%, 32/34** held in place |
| Unfitted module reconstructions | 20 @ 82.6% / 43.1% median | **21 @ 76.7% / 41.0%** |
| — 12 sectoral presets | 113.8% / 57.1% median | **104.8% / 40.0%** |
| Calibrated, leave-one-out | 18 @ 61.7% / 35.6% median | **18 @ 58.7% / 32.5%** |
| Calibrated provenance | 17 `line_item` / 15 `differs` / 15 `secondhand` / 7 `model_estimate` | **19 / 13 / 15 / 7** |
| Sectoral rows disagreeing with their target on **sign** | 1 | **0** |

- **A revised row leaves the fitted tier, and the summary says so.** A constant
  fitted to a superseded figure is not fitted to its replacement, so
  `scorecard.py` derives `calibrated_to_target` from the ledger and
  `extend_tcja_amt` reports among the unfitted reconstructions, where a miss is a
  finding rather than a regression. `ScorecardSummary.revised_target_entries`
  (= **2**) is on the scorecard and on `/validation/scorecard`, so the move can
  never be silent. **Quote "33 at 2.8%" only next to the statement that a 34th
  row moved out**, and never retune the constant to close the 66.8% — that is the
  move a provenance pass is forbidden to make.
- **The LOO fall is a target moving, not a model.** `extend_tcja_amt`'s held-out
  derivation is **unchanged at $855.3B**; its error against the corrected row is
  −37.0% instead of +90.1%, taking the AMT module 100.5% → 73.9% and the suite
  61.7% → 58.7%. No donor-matrix entry moved.
- **`KNOWN_TARGET_SIGN_INVERSIONS` is now an empty set**, and the emptiness is
  the assertion: no scorecard row disagrees with its own target about what a
  policy does.
- **`AMT_APP_MODE` and `AMT_SCORECARD_MODE` stay `reported`.** Across the three
  AMT benchmarks reported means **22.3%** against derived's **54.2%**, which is
  owner Decision 1's own rule, so **no shipped number changes**. Read past the
  mean: both rows on which derived loses are targets a constant was fitted to, so their
  ~0% is bookkeeping — and the one AMT benchmark no constant was fitted to is the
  one derived wins, 37.0% against 66.8%.
- **`repeal_individual_amt` keeps an unsourced, internally incoherent target.**
  No published post-2025 repeal score exists at JCT, CBO or TPC. TPC T25-0049's
  $948.9B is deliberately not adopted: it is a baseline projection rather than a
  scored repeal, *and* it is `amt.py`'s own input, so adopting it would
  manufacture a 0% row out of the leakage `loo.py` guards against. Closing it
  needs a published score or an owner decision to re-register `holdout.py`'s
  locked `revenue-scorecard-post-lock-2026-05-02` protocol — which has no
  re-registration path. `check_readiness.py --strict` is unchanged from the base
  commit.
- **Two user-facing labels moved with their targets** (slugs unchanged, so no
  share link breaks): `⚖️ AMT: Extend TCJA Relief ($450B)` → `($1.36T)`, and
  `💊 Universal Insulin Cap (-$15B)` → `($11B)`. `/validation/scorecard` and the
  Validation tab now carry `target_revision_id`, `superseded_10yr_billions`,
  `target_revision_reason` per entry and a "Target moved from" column.

### Tier 1 CI gate tightened to 45 / 15 (2026-09-02)

PR **#91**. The out-of-sample gate's own rule — ceiling = `ceil(mean × 1.25)`
rounded up to the nearest 5, floor = the current count within 25% minus one —
derives **45 / 15** from the post-Wave-1 battery (25 cases, 34.4% mean, 16 within
25%), against the **55 / 13** the workflow carried. Both are tightenings, which
the rule says need no reason. The derivation is recorded in the workflow comment
beside the earlier ones, and the places that quote the command now match.

### Modelling Wave 1 — spend-out, AMT, pharma incidence (2026-09-02)

Wave 1 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md),
three lanes on disjoint files plus a follow-up, with the owner's six §6 decisions
recorded first. Every lane pre-registered its expected movement in
`planning/lanes/` **before** touching code; §5.1 of the plan carries the outturn
and the three findings. PRs **#83** (decisions), **#85** (L2 spend-out),
**#86** (L5 AMT), **#87** (L7 pharma), **#88** (IIJA authorization path + app
spend-out).

**Validation tiers moved. Report them separately, as always:**

| Tier | n | Before | After |
|---|--:|---|---|
| Out-of-sample, pre-registered | 25 | 52.6% mean / 21.1% median / 8 within 15 / 14 within 25 | **34.4% / 16.1% / 12 / 16** |
| Calibrated, fitted | 34 | 2.7% / 33 within 15 | **unchanged** |
| Unfitted module reconstructions | 20 | 250.8% / 43.1% median | **82.6% / 43.1%** |
| — 12 sectoral presets | 12 | 394.1% / 57.1% median | **113.8% / 57.1%** |
| — 8 P.L. 119-21 line items | 8 | 35.8% | **unchanged** |
| Calibrated, leave-one-out | 18 | 59.3% / 35.6% median / 6 within 15 | **61.7% / 35.6% / 6** |
| Distributional | 7 | 0.00–5.86pp | **unchanged** |

*Two of these Tier 2 figures moved again the same day, in the target-revision
entry above; the numbers here are Wave 1's outturn, not the current ones.*

- **Budget authority and outlays are now distinct quantities (L2).**
  `SpendingPolicy` no longer books a funding level straight into outlays;
  `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` an account-class profile fitted by
  non-negative least squares on the 14 CBO options that publish both an
  authority row and an outlays row **and are not scored by the battery**. The
  five scored options never donate. Class assignment is a classification from
  the account type each program funds, never a fit. **Finding:** owner Decision
  2 named OMB Circular A-11 §32 as the primary source; A-11 §32 is personnel
  compensation and A-11 publishes **no** outlay-rate table in any section, so
  the decision's own fallback governed and the CBO donor options shipped as
  primary. CBO's account-level rates (publications 61913, 62256) are the open
  cross-check, blocked by cbo.gov 403s.
- **IIJA is scored on the schedule its source states (#88).** The shape input
  was superseded under the manifest's own rule — a **new row**, never an edit —
  in two commits, entry before scoring. `iija_2021_discretionary.v1` stays on
  the record (+$1,894B, 356%; +$1,621B, 290.2% after spend-out); `.v2` carries
  CBO's own authorization path and scores **+$340.0B against an unchanged
  +$415.4B target, 18.2%**. What remains is a window mismatch: $92.6B of the
  path's outlays fall in FY2022-2024, before the model's FY2025-2034 window
  opens. Earlier docs saying IIJA "is kept at 356% deliberately, as the sharpest
  evidence for the missing spend-out model" are now history on both halves.
- **The Fiscal Responsibility Act row got worse, as pre-registered** (5.8% →
  12.2%). The old figure was two errors cancelling; a correct spend-out removes
  one and leaves the other, so the total error rises while the path gets more
  right.
- **AMT gained a live exemption branch and a published year-indexed path (L5).**
  The exemption-change branch had been dead code, so no exemption change had
  ever been scored. The path is TPC Table T25-0049, transcribed to
  `fiscal_model/data_files/amt/`. **Finding:** the plan's "missing 2026 ramp"
  hypothesis was **wrong** — T25-0049 shows a *cliff* (0.2M → 7.6M AMT payers,
  2025 → 2026) and then *growth* ($71.6B → $124.2B by 2035), so the flat
  ~$73B/yr was the window's early-year level and indexing it **raises** the
  score. Both AMT LOO rows moved away from their carried $450B targets (+73.2%
  → +90.1%, +86.0% → +110.9%) while the extension moved *toward* the published
  line item ($1,357.1B: −66.8% fitted → **−37.0%** derived). **App default stays
  `reported`**; nothing a user sees changed. `docs/VALIDATION_NOTES.md` §6 was
  corrected rather than deleted.
- **Drug pricing now scores federal incidence (L7).** A $35 insulin cap is a
  cost-sharing cap, so the federal budget picks up only its share of the
  liability shift; and international reference pricing is scored on a net-price,
  brand-only, federal-share basis (US unbranded generics are *cheaper* than the
  OECD comparison and cannot contribute savings). Every input is transcribed
  with document, page and URL to
  `fiscal_model/data_files/pharma/drug_pricing_incidence.csv`. No parameter was
  fitted to any of the three pharma benchmarks. **Still unrepaired:** RAND's
  index is computed on presentations sold in both markets and the module applies
  it to all brand spending; no utilisation, launch-delay or availability
  response is modelled on either row.

**Shipped preset numbers moved.** No preset label and no `CBO_SCORE_MAP` entry
changed — labels carry the official score or an annual funding level, not the
model's ten-year total.

| Preset | Before | After |
|---|--:|--:|
| 💊 Universal Insulin Cap | −$445.3B | **+$7.0B** |
| 💊 International Reference Pricing | −$1,387.9B | **−$746.2B** |
| 💊 Comprehensive Drug Reform | −$1,025.8B | **−$573.5B** |
| 💊 Expand Drug Negotiation | −$371.5B | unchanged |

The insulin cap now reads as a deficit *increase*, which is what CBO scores for
the same policy (publication 57957, +$11.4B); the carried −$15B benchmark is the
thing still pointing the wrong way.

**Every spending program's 10-year outlays now follow a spend-out profile.** The
label still quotes the annual funding level, which is budget authority and is
unchanged; only the ten-year outlay total moved. Each score renders one line
naming its profile and its outlay/authority ratio, computed from the scored
result. `immediate` stays reachable under Economic parameters and is the default
for nothing.

| Program (Tailor) | Account class | 10-yr before | 10-yr after | outlay/authority |
|---|---|--:|--:|--:|
| Custom program | construction and capital | +$1,095.0B | **+$725.4B** | 0.663 |
| Infrastructure Investment ($100B/yr) | construction and capital | +$1,146.4B | **+$749.8B** | 0.654 |
| Defense Spending Increase (+10%) | operations and support | +$985.5B | **+$880.2B** | 0.893 |
| Universal Pre-K ($40B/yr) | grants and procurement | +$458.6B | **+$386.9B** | 0.844 |
| R&D Investment ($50B/yr) | grants and procurement | +$600.3B | **+$503.8B** | 0.839 |
| Discretionary Spending Cut (−$50B/yr) | operations and support | −$547.5B | **−$489.0B** | 0.893 |
| Disaster Relief ($30B one-time) | grants and procurement | +$30.0B | +$30.0B | 1.000 |
| Student Debt Forgiveness ($400B one-time) | benefit payments | +$400.0B | +$400.0B | 1.000 |
| Universal Childcare ($100B/yr) | grants and procurement | +$1,146.4B | **+$967.4B** | 0.844 |
| Medicare Buy-in Age 55+ ($50B/yr) | benefit payments | +$573.2B | **+$571.7B** | 0.997 |
| High-Speed Rail Program ($30B/yr) | construction and capital | +$328.5B | **+$217.6B** | 0.663 |

The two one-time programs are unchanged because their whole spend-out tail lands
inside the window — the timing moves, the total does not. Explore ships no
spending preset.

**Owner decisions recorded (#83).** All six of the plan's §6 questions were
answered on 2026-09-01: keep `reported` and `derived` modes; A-11 as the primary
spend-out source (superseded by finding 1 above, via the decision's own fallback
clause); freeze Dowd–McClelland–Muthitacharoen (2015) capital-gains elasticities;
fetch raw CPS ASEC by script rather than vendoring it; move the three
tautological credit benchmarks to documented exclusion; ship the tariff
gross→net change with its UI note.

**No yardstick was touched.** `preregistered.py`'s targets, `cold_holdout.py`,
`run_loo.py`, `loo.py`'s leakage guard, `tests/test_preregistration.py` and the
CI thresholds are all unchanged. The CI derivation rule now implies a ceiling of
45 and a floor of 15 against the workflow's current 55 and 13; both pass with
room and tightening them is left to whoever lands next. *(Done in PR #91, above.)*

### Documentation honesty sync (2026-09-01)

*Superseded on 2026-09-02 by the Wave 1 entry above: the tier figures below were
correct when written and are kept as the record of that change, not as current
numbers.*

- `docs/METHODOLOGY.md` now reports **four validation tiers separately** and
  states outright that there is no single "validated within X%" figure:
  out-of-sample pre-registered (25 cases, 52.6% mean / 21.1% median, 8/25 within
  15%, 14/25 within 25%), calibrated-and-fitted (34 at 2.7%), unfitted module
  reconstructions (20 at 250.8% mean / 43.1% median — 12 sectoral presets at
  394.1% plus 8 P.L. 119-21 line items at 35.8%), and calibrated leave-one-out
  (18 derivable at 59.3% mean / 35.6% median, 4 not cross-validatable). It
  previously carried a stale 23-case/43.4% Tier 1 and a "29 benchmarks ≈ 5%"
  Tier 2.
- **Step-up lock-in multiplier corrected.** METHODOLOGY printed `5.3×` as the
  current-law setting. The module default is **2.0**
  (`CapitalGainsPolicy.step_up_lock_in_multiplier`), and `5.3` is set only by
  the `pwbm_39_with_stepup` validation scenario, where it is fitted to reproduce
  PWBM's revenue loss. (Tests assert that scenario's value and the docs discuss
  it; those reference the same constant rather than adding uses of it.) The document now says which multiplier each
  published result was produced with, and records that the 5.3× is a known
  answer key (`run_loo.py --donor-matrix`), not a parameter.
- **Distributional claim replaced.** The two-line "vs. TPC TCJA analysis"
  summary is now the seven published CBO/JCT tables at 0.00-5.86pp, with the two
  circular ones (CBO 54796, CBO 60007) named as circular.
- **IRS SOI vintage.** METHODOLOGY contradicted itself on the tax-year basis; it
  now states that tax years 2021-2023 ship and production scoring runs on **tax
  year 2023**, and that tax-year (calendar) aggregates are carried into a
  fiscal-year window without conversion.
- `planning/MODELING_IMPROVEMENT.md` §2 error budget and §5 sequencing
  re-derived against the post-Phase-D/E battery; `planning/NEXT_STEPS.md` lost
  its "25+ policies validated within 15%" line.


### Ask assistant (May 2026)

- New **💬 Ask** tab (now the second top-level tab) and matching
  `POST /ask` + `POST /ask/stream` (Server-Sent Events) endpoints expose
  a citation-grounded Q&A assistant. Streams answers from Claude
  Sonnet 4.6 with tool access to the app's scoring engine, CBO baseline,
  validation scorecard, 49 preset policies, and 19 hand-curated
  authoritative snapshots covering CBO baseline, SSA Trustees, TCJA,
  capital gains, international tax, retirement-account taxation, IRA
  clean-energy credits, tariff scoring, JCT distributional methodology,
  fiscal multipliers, ETI literature, state/local fiscal interaction,
  debt sustainability, dynamic-scoring concepts, JCT tax expenditures,
  TPC TCJA distribution, PWBM TCJA dynamic, Yale Budget Lab tariffs,
  CBO long-term outlook, and a common-confusion FAQ.
- **Citation discipline is structural, not aspirational.** The model is
  required to emit `[^N]` footnote markers on every substantive claim.
  A post-processor cross-references each marker against the per-turn
  tool-call provenance log; unsupported markers are stripped and
  replaced with `[citation needed]`, surfacing as a defect to the
  reader.
- **Hard usage caps protect the deployer's API spend.** A sqlite-backed
  `assistant_events` ledger (also serves as the telemetry log)
  enforces a daily cost cap (`$5/day` default), per-session message
  cap (20), cool-down between messages (3s), and an
  `ASSISTANT_DISABLED` env-var kill switch. The same ledger is shared
  by the Streamlit tab and the FastAPI endpoints so a busy API caller
  cannot drain the UI budget.
- **Token-gated admin dashboard** (`💼 Admin` tab) shows today's spend
  vs. cap, KPIs (cache-hit ratio, error rate, avg cost/turn), the
  30-day daily-cost series, tool-usage frequency, and the recent-turn
  table — visible only when the URL has `?admin=<token>` matching
  `ASSISTANT_ADMIN_TOKEN`. Non-admins do not see the tab label.
- **Share-this-answer button.** Each assistant turn includes a 🔗 Share
  affordance that builds a URL containing the full Q+A+provenance as
  a gzip+base64 payload (no backend state). Recipients land on the Ask
  tab with the exact pair pre-rendered. SHARE_SCHEMA_VERSION makes
  future evolution graceful; MAX_DECODED_BYTES guards against
  decompression bombs.
- **Health/readiness wiring.** `/health` now carries an `assistant`
  component with three sub-signals (API key, knowledge corpus size,
  usage db reachability). The assistant is marked `required=False` in
  `/readiness` so a missing key on a CI runner or dev box reports as
  "degraded / warn" without blocking deploy. Older synthetic health
  payloads stay backward-compatible — the new check is skipped when
  the `assistant` key is absent.
- **Streamlit-Cloud secrets are auto-promoted to env vars** on first
  render. A Levenshtein-based typo detector surfaces near-miss key
  names (e.g., `ANTHROPHIC_API_KEY`) inline in the unavailable-key
  diagnostic. End users are never asked to enter an API key.
- **Latency tuning.** `DEFAULT_MAX_TOKENS` reduced from 1600 to 800.
  Follow-up question generation moved to a separate Streamlit rerun so
  it doesn't block answer finalization. Prompt cache pre-warms on a
  daemon thread at app boot so the first real turn skips the
  cache-creation tax. Typical turn: 5-7s, $0.01-$0.02.
- **Anti-spiral safeguards.** The agentic loop is capped at 4 tool
  iterations; on cap, a final tools-disabled call forces the model to
  write a real answer using whatever it has gathered. The system
  prompt explicitly budgets 2-3 tool calls per answer.
- **Dollar-sign KaTeX safety.** A post-processor escapes any unescaped
  `$` before a digit in rendered markdown so currency amounts never
  render as LaTeX math. The system prompt also instructs the model to
  emit `\$` directly.
- **Knowledge refresh script.** `scripts/refresh_knowledge.py` fetches
  any allowlisted authoritative URL through the same pipeline the
  runtime `fetch_url` tool uses (with `pdfplumber` for PDFs) and dumps
  a frontmatter'd stub for hand-summarization. Fails gracefully on
  bot-blocked domains (CBO, SSA) with a clear pointer to manual paste
  or live `web_search`.
- **Live smoke test.** `scripts/smoke_ask_assistant.py` runs three
  short questions through the real Anthropic API to verify the
  streaming tool-use loop, knowledge search, and citation discipline.
  ≈$0.04 per full run; supports `--only N` for single-scenario runs.
- 105 new tests across `tests/test_fiscal_assistant.py`,
  `tests/test_ask_api.py`, `tests/test_assistant_rate_limit.py`,
  `tests/test_assistant_admin.py`, `tests/test_assistant_share.py`,
  `tests/test_assistant_health.py`. All use mocked Anthropic clients;
  no API credit spent in CI.

### Operational readiness and CI telemetry

- `/health`, `/benchmarks`, `/summary`, and validation artifacts now expose
  flattened `issues` arrays with a shared status-issue shape for monitoring
  clients: `surface`, `severity`, `name`, `message`, and `details`.
- The Results Summary tab now renders a validation-evidence card beside each
  headline score, including calibrated category, benchmark count, observed
  error range, holdout status, and known caveats.
- CI smoke coverage now includes `scripts/check_streamlit_boot.py`, which
  starts the Streamlit app locally and verifies the calculator and
  classroom-mode routes serve the app shell.
- The FRED data layer now has a tracked bundled seed path between runtime cache
  and hardcoded fallback, so offline CI/deployments can build the baseline from
  a deterministic GDP seed instead of the IRS-ratio proxy.
- Bundled FRED seed data now carries a 120-day freshness contract, surfaces its
  age/max-age in health payloads, and degrades readiness when the seed ages out.
- Added `scripts/refresh_fred_seed.py` and a monthly `fred-seed-refresh`
  workflow so the tracked FRED seed is refreshed from live FRED with provenance
  and reviewed through a pull request before the 120-day window expires.
- The feasibility audit now emits a structured `model_pilot_assessment` with
  blockers/warnings and supports `--strict`, so implausible multi-model gaps
  stop the feasibility phase before UI expansion. The multi-model tab reuses
  the same assessment to flag pilot-quality blockers in the UI.
- PWBM-OLG is now excluded from the default multi-model pilot and kept behind
  `--include-experimental-pwbm` until its adapter clears the feasibility sanity
  bounds; the user-facing pilot defaults to the comparable CBO/TPC paths.
- The TPC microsim pilot now maps income-tax rate changes with thresholds to a
  taxable-income-above-threshold adjustment instead of collapsing every rate
  policy into a generic top-rate change.
- The model-pilot feasibility audit now uses the IRS-backed CBO-style scorer by
  default, with `--use-synthetic-cbo` retained for isolated diagnostics.
- The default TPC microsim pilot now applies SOI top-tail augmentation with
  metadata, reducing high-income threshold undercoverage while keeping
  `--no-top-tail-augmentation` available for CPS-only diagnostics.
- The experimental PWBM-OLG pilot now nets reform transitions against a
  no-reform OLG reference path and returns zero macro feedback when a policy
  does not map to an OLG parameter override, avoiding baseline transition drift
  being counted as a policy effect.
- The CPS microsim builder now emits explicit `investment_income` as interest,
  dividends, and capital gains, and the tracked `tax_microdata_2024.csv`
  artifact has been regenerated with that column.
- The release-readiness CLI now distinguishes real release blockers from
  expected offline data-environment warnings. `scripts/check_readiness.py
  --strict` still fails `not_ready` and non-environmental warnings, but it no
  longer blocks isolated CI runners solely because live FRED data or a warm
  FRED cache is unavailable.
- Validation and public-health scripts avoid `datetime.UTC` so the supported
  Python `3.10`-`3.13` matrix imports them consistently.

### API hardening

- Added opt-in API key auth via `X-API-Key` header, configured through the
  `FISCAL_API_KEYS` env var. Auth stays off by default so local launches and
  existing callers continue to work unchanged.
- Added a sliding-window rate limiter
  (`FISCAL_API_RATE_LIMIT_PER_MINUTE`, default 60; burst 20) keyed on API
  key label when auth is on and client IP otherwise. Returns `429` with
  `Retry-After: 60`.
- Every request now emits one structured JSON log line via the
  `fiscal_model.api_security` logger (path, method, status, duration,
  caller, key label).
- Wiring is in `fiscal_model/api_security.py`; tests in
  `tests/test_api_security.py`.

### Validation transparency

- New `docs/VALIDATION_NOTES.md` provides root-cause analysis for the three
  biggest validation outliers (SS donut hole 12.2%, Biden CTC 8.9%, Biden
  estate reform 10.1%). Each case documents the mechanical, data, and
  methodological causes with quantified fix paths.

### Test coverage

- New `tests/test_input_validation.py` (38 cases) covering invalid and
  malformed inputs distinct from the existing edge-case suite: structural
  invariants, parameter bounds, non-finite inputs, extreme-but-valid
  numerical robustness, and phase-in/sunset exact-boundary behavior.

### Dollar-escape + scoring unit fixes (April 2026)

- Converted remaining non-raw `"""..."""` tables in `methodology.py` to
  raw strings so bare `\$` no longer triggers `SyntaxWarning` under
  Python 3.12+.
- Removed the `/1e9` and sign-flip heuristic in the bill tracker's
  auto-scorer. `final_deficit_effect` is already in billions with the
  positive=deficit-increase convention used by `cbo_manual_scores.json`,
  so the heuristic was producing inconsistent signs and magnitudes.
- Added `_escape_dollars` helper in `classroom_app.py` to prevent
  Streamlit from rendering dollar amounts as LaTeX in assignment and
  exercise text.

## April 2026 — UI reorganization

### Progressive tab disclosure

The UI now separates primary analysis from advanced features. Previously a
single `st.tabs()` row of five tabs (one of which was a container with a
radio sub-selector) carried everything.

**Primary tabs** (always visible):

- 📊 Results Summary
- 👥 Distribution
- 🌍 Dynamic Scoring
- 📋 Detailed Results

**Advanced** (collapsible `st.expander("🔬 Advanced Analysis")`):

- 📈 Long-Run Growth
- ⚖️ Policy Comparison
- 📦 Package Builder
- 📖 Methodology

All eight tabs are mapped to a unified dictionary for
`render_result_tabs()`; there was no API change for callers.

### Export enhancements

The bottom of Results Summary now offers three export paths:

| Option          | Format           | Use case                                |
|-----------------|------------------|-----------------------------------------|
| CSV download    | Spreadsheet      | Excel, further processing               |
| Text download   | Plain text file  | Email, sharing as attachment            |
| Copy-paste block| Code block       | Direct paste into Word, Google Docs     |

The text summary includes the policy name, deficit impact, year-by-year
breakdown, assumptions, and data sources.

### Uncertainty bands + CBO comparison

Sensitivity bands (default: ETI ± 0.1) are rendered alongside the central
estimate on the Results Summary tab, with an in-line comparison against
the nearest published CBO/JCT score from the validation database.
`fiscal_model/ui/tabs/results_summary.py` is the entry point for this
rendering. The validation comparator is in
`fiscal_model/validation/cbo_scores.py`.

### Backwards compatibility

100% backwards compatible — no public-API change. Tests in
`tests/test_ui_controller_smoke.py` exercise both the old and new tab
paths.

## Earlier milestones

- **State-level modeling**: top 10 states with SALT cap interaction,
  combined federal + state effective rates.
- **OLG model**: 30-period Auerbach-Kotlikoff-style generational
  accounting for Social Security and Medicare reform
  (`fiscal_model/models/olg/`).
- **Classroom mode**: 7 interactive assignments, Laffer curve explorer,
  PDF export; launched with `streamlit run classroom_app.py`.
- **Real-time bill tracker**: pulls from congress.gov, extracts
  provisions via LLM, stores in SQLite (`bill_tracker/`).
- **Tariff scoring**: 5 presets (universal 10%, China 60%, autos 25%,
  reciprocal), consumer price impact by income quintile.
- **25+ validated policies** against CBO/JCT/Treasury scores; see
  `docs/VALIDATION.md` for the full matrix and
  `docs/VALIDATION_NOTES.md` for diagnostics on outliers.
