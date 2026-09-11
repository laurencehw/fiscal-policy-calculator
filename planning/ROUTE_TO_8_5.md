# The route from 7.5 to 8.5

*Written 2026-09-11 on `planning/route-to-8-5`, branched from `main` @ `20e356d` with
`memo/cbo-github-survey-tax` (PR #154) and `memo/cbo-github-survey-macro` (PR #153) merged in.
Every figure below is from one of four runs on **this** tree — `ANTHROPIC_API_KEY= python
scripts/cold_holdout.py --json`, `scripts/run_validation_dashboard.py`, `scripts/run_loo.py
--donor-matrix`, and a direct `CBOBaseline(start_year=2026, vintage=CBO_FEB_2026).generate()` —
or from a `file:line`, or from a cited section of one of the two survey memos. Nothing is recalled.*

`HIGH_STAKES_ACCURACY.md` re-ranked the work by **who reads the number** and took the app from 6.5
to 7.5 across Waves A, B and C. This plan does not supersede it: Waves D and E are still that
document's, its §1 principles, §4 prohibitions, Decisions 1/3/6, the pre-registration manifest and
the CI gate's own re-derivation rule all continue to bind, and every carry-over item in
`MODELING_IMPROVEMENT.md` §6.2 that neither plan schedules stays open there.

What this plan adds is a **destination with five separate coordinates** and a route to it that is
dominated, for the first time, by a *data channel that did not exist when any prior wave was
planned*. The survey memos' shared headline is the reason: **cbo.gov returns HTTP 403 to this
environment and `github.com/US-CBO` does not**, and CBO's GitHub organisation carries its February
2026 budget baseline, its statutory parameter schedule by filing status by year, its own
budget-authority→outlay vector, its nine marginal revenue rates, its loss-firm haircuts and the
annual revenue effect of 42 enacted acts — most of which this repository has spent seven waves
hand-transcribing, refusing for want of a source, or declaring out of scope because "no published
table exists."

---

## §0 — What 8.5 means, measurably

**Five criteria, never one number.** The repository's own rule — eight classes, three tiers, seven
distributional tables and two provenance states do not collapse — applies to its rating as much as
to its accuracy claim. A tree that meets four of the five is not at 8.5; it is at 7.5 with four
things fixed.

| # | Criterion | Today, measured on this tree | 8.5 |
|--:|---|---|---|
| **1** | **Out-of-sample battery** — size, accuracy, and whether the per-class bands rest on a sample | **n = 26, mean 14.5%, median 11.5%, 16/26 within 15%, 22/26 within 25%.** Eight classes at n = 1, 1, 2, 3, 4, 4, 5, 6 — `corporate` and `tax_expenditure` are **single observations**. Class means: discretionary 4.64, payroll 7.80, tax expenditure 13.10, enacted-law spending 13.40, ordinary rate 14.82, AGI surtax 17.57, capital gains 18.70, corporate 44.50 | **n ≥ 40, mean ≤ 12%, ≥ 30/40 within 25%, and every class n ≥ 3 with no class mean above 25%.** The size condition is not decoration: a band read off one row is not a band |
| **2** | **Reconstruction tier** — measured on a *constant* population, and what a user can reach | **39 rows at 56.7% mean / 36.9% median, 10/39 within 15%, 13/39 within 25%.** Fifteen sub-populations from `Credits` 9.5% (n=1) to `Pharma` **277.8%** (n=3). Worst rows: `international_reference_pricing` **701.0%**, `trump_corporate_15` 121.6%, `expand_drug_negotiation` 93.3%, `ss_donut_250k` 89.2%, `double_enforcement` 82.3%. All five are reachable from Explore and Build today | **≤ 45% mean on the 39 rows held at Wave D's close, ≥ 15/39 within 15%, and no row above 150% reachable from a headline surface** — reached by moving the row, or by H12 demoting the preset, never by retiring the row. A demoted preset keeps its scorecard entry |
| **3** | **Provenance** | Calibrated tiers (n=55): `line_item` 36, `line_item_differs` 8, `secondhand` **7**, `model_estimate` **4**. Both tiers: 77/81 published, 43 transcribed. **And the new measurement this plan turns on:** Tier 1's five `secondhand` rows carry a **23.92% mean against the 21 `line_item` rows' 12.21%**, i.e. **19% of the tier holds 31.8% of its error mass** (119.6 of 376.1) | Calibrated `secondhand` ≤ 5, `model_estimate` ≤ 2, **Tier 1 `secondhand` ≤ 2**, published ≥ 79/81; the `retire` state either applied or declined **in writing, per row** — H9 built it and applied it to nothing, which is correct only while ④ is open |
| **4** | **Consistency and coverage** | 44 of 53 presets badged, the 9 unbadged printing no dollar figure (H6, enforced by test). **Build quotes list prices, not model output** (`fiscal_model/ui/tabs/deficit_target.py:219-232`): 46 options, 44 with a scorecard row, and **13 of those 44 quote a `secondhand` or `model_estimate` target** | Every Build option **either** shows model output beside the list price **or** is labelled a list price on the surface itself; **≤ 6** quoting a `secondhand`/`model_estimate` target. The base-rule contract (H1) holds across all four constructors, and `DistributionalEngine` joins them (§6.2 item 46 — 2.57× apart today) |
| **5** | **The baseline** | `CBO_FEB_2026` — the app's default — is graded **`"sourced"`** at `fiscal_model/baseline.py:163-168` while its corporate line is graded `"vintage_estimate"` at `:220-224`. Measured: FY2026–2035 cumulative deficit **$29,529.1B against CBO's own $23,143.3B (+27.6%)**; end-FY2035 debt $49,362.1B vs $53,103.2B (−7.0%); corporate receipts 436.8 → 667.4, **4.82%/yr against CBO's 3.53%**; FY2026 individual income tax 18.3% low, payroll 11.0% high (macro survey §1 finding 1) | **All three vintages transcribed from CBO's own table**, `VINTAGE_SOURCING` and `CORPORATE_RECEIPTS_SOURCING` graded from what was actually transcribed, and the vintage's ten-year deficit within 1% of the figure its own document prints |

### What is explicitly **not** in 8.5

- **A microsimulation core.** §3 costs it and explains why it is the 9.
- **Any accuracy claim for the 🔵 exploratory tier.** Ask, the bill tracker, classroom and the
  multi-model pilots stay on a UX/safety bar. The one exploratory item this plan carries (R16) is a
  *performance* defect on a 🟢-tier path, not an accuracy one.
- **The fitted tier's 1.5%.** It is bookkeeping and it is not a number to protect. It has already
  lost rows to four mechanisms and fell each time. If a provenance lane takes it to 8% over 12 rows,
  that is the tier becoming honest.
- **A single "validated within X%" headline.** Forbidden by §4 of the existing plan and by this one.

### What 9 would require

A genuine tax-unit microsimulation core producing revenue, distribution and the TCJA decomposition
from one population rather than three reconstructions; the 8 P.L. 119-21 line items below ~15%
instead of 35.8%; and the distributional benchmarks scored on the universe their source ranks with
**zero** `household→tax_unit` fallbacks (3 of 7 fall back today). §3.

---

## §1 — The ranked list

Ranked by **stakes × current error × tractability**, the existing plan's §1.1 ordering. "Moves"
names the §0 criteria. Effort is lane-days on this repository's own scale. **Nothing here is an
instruction to adopt a number**; several lanes are pre-registered regressions and say so.

| Rank | Lane | Stakes | Effort | Moves |
|--:|---|---|--:|---|
| **R1** | Transcribe CBO's own February 2026 baseline (and give the other two vintages a real table) | Every dynamic number, Ask's deficit, Build's target strip, debt/GDP | **3** | ⑤ |
| **R2** | The five Tier 1 rows with no source URL | 31.8% of the tier's error mass | **3** | ①③ |
| **R3** | H10: a Tailor battery, off CBO's 42 enacted acts and four *Options* vintages | The tier is 26 rows; users type shapes it does not contain | **5** | ① |
| **R4** | The statutory parameter schedule → year-indexed thresholds | Unblocks the branch H2 declared impossible | **3** | ① |
| **R5** | H3b: corporate, with CBO's own loss-firm haircut | Largest single Tier 1 row (44.5%); worst headline reconstruction (121.6%) | **4** | ①② |
| **R6** | H12: demote the sectoral presets (Wave D, open) | The 701% row is on Explore today | **1** + owner | ②④ |
| **R7** | The generic base on CBO's own AGI and taxable-income path | 18 of 26 Tier 1 rows; every generic surface | **4** | ① |
| **R8** | Tariffs: JCT's offset *path*, the HS-10 steel base, the elasticity ramp | Five presets, `Trade` at 43.6% | **3** | ② |
| **R9** | The SS donut ramp on CBO's own taxable-payroll path | `ss_donut_250k` at 89.2%, a top-six headline | **2** | ② |
| **R10** | H7: the five expenditure magnitudes (Wave D, open) | `Expenditures` LOO 40.6% | **3** | ② |
| **R11** | H11: the PTC coverage response (Wave D, open) | `repeal_ptc` 29.6%, a shipped preset | **2** | ② |
| **R12** | Decompose `MARGINAL_REVENUE_RATE`; give debt service a rate path | The whole dynamic tab, uncalibrated | **4** | — (⑤-adjacent) |
| **R13** | The death channel's *level* half, checked against CapTax | §6.2 item 55's 7.1× factor | **2** | ① |
| **R14** | CBO's own error-measurement discipline for the app's reporting | How every tier is quoted | **2** | ①②③ |
| **R15** | The spend-out vector: confirm (a), then refit on 1,712 accounts (b) | Provenance of the tier's best class | **1 + 3** | ①③ |
| **R16** | `_scorecard_index`: 6.6s on every scored route | The 🔵 complaint that is really a 🟢 defect | **2** | — |

---

### R1 — Transcribe CBO's February 2026 baseline *(3 lane-days)*

**Stakes.** The highest in this plan and it is not close. The ten-year deficit appears on the
landing page, in every Build package's target strip, and in the Ask assistant's `get_cbo_baseline`
output. By the existing plan's own salience × magnitude × reach test it outranks every row in its
§1.2 table, and it fails only the "is it a score" test — which is why seven waves of score-ranked
work never reached it.

**Current error.** Measured on this tree by running the app's own default:
`sum(p.deficit)` over FY2026–2035 is **$29,529.1B** against CBO's own February 2026 baseline's
**$23,143.3B**, **+27.6%**. End-FY2035 debt held by the public $49,362.1B vs $53,103.2B (−7.0%);
FY2026 individual income tax $2,248.9B vs $2,751.3B (−18.3%); payroll $2,027.1B vs $1,825.6B
(+11.0%); corporate receipts compounding **4.82%/yr against CBO's 3.53%** (macro survey §1 finding 1,
§3 row 1).

**Mechanism.** `CBOBaseline._load_from_data_sources` reconstructs base levels from the eleven
`GDP_RATIOS` at `fiscal_model/constants.py:120-132`, and `baseline.py:214-219` states the blocker in
as many words: *"cbo.gov returns HTTP 403 to this environment and the Wayback Machine holds no
snapshot of the January 2025 or February 2026 budget projections workbooks… Adding one is a data
edit — a block in the CSV — not a code change."* The GitHub organisation is not blocked and the
file exists: `budgetary-feedback-model/input/budget_baseline.csv` is CBO's FY2025–FY2036 budget
path with the matching 38-series quarterly `econ_baseline.csv`, and
`cbo-data/data/budget/ten_year_budget/annual_fy_{2024-06,2025-01,2026-02}.csv` carries 336 variables
on all three vintages plus CBO's own `chg_leg_*/chg_econ_*/chg_tech_*` baseline-change decomposition
(tax survey §2.1, §3 row 1). This is the data edit `baseline.py` specified.

**Files.** `fiscal_model/baseline.py` (`_CBO_FEB_2026_ASSUMPTIONS` `:68-84`,
`_VINTAGE_CORPORATE_BASE_LEVELS` `:195`, `CORPORATE_RECEIPTS_SOURCING` `:220-224`, `VINTAGE_SOURCING`
`:163-168`), `fiscal_model/constants.py:120-132`, a new data block, `tests/test_baseline_vintage.py`.

**Pre-registrable expectation.** **No scored number moves** — PR #130's precedent is exact: a
baseline fix was byte-identical on all 81 scorecard rows while Ask's deficit, Build's target strip
and debt/GDP all moved. The Tier 1 battery is bottom-up and runs on `CBO_FEB_2024`;
`build_scorer_for_vintage()` already demonstrates that changing the vintage moves no Options row.
**Falsified if** any of the 81 `model_10yr_billions` changes. `CORPORATE_RECEIPTS_SOURCING` converts
`vintage_estimate` → `published_path`, which is the one grade `baseline.py` says may not otherwise be
reported as CBO's own. **Decision 6 does not apply** (no headline *score* moves) but the landing
page's deficit does, so the docs sync carries it.

**What it does not move: Tier 1, by construction.** State that in the lane doc, because a lane that
moves the app's most-read number and reports "no accuracy improvement" will otherwise read as a
failure.

---

### R2 — The five Tier 1 rows with no source URL *(3 lane-days)*

**Stakes and error, measured together.** Split Tier 1 by provenance on this tree:

| provenance | n | mean | error mass | within 25% |
|---|--:|--:|--:|--:|
| `line_item` | 21 | **12.21%** | 256.5 | 18/21 |
| `secondhand` | 5 | **23.92%** | 119.6 | 3/5 |

**Nineteen percent of the battery carries 31.8% of its error mass**, and it is exactly the 19% whose
targets nobody can open. The five are `medicare_surcharge_2pp` (31.8%, Treasury),
`warren_ultramillionaire_surtax_3pp` (24.8%, TPC), `illustrative_1pp_all` (24.5%, JCT),
`illustrative_top_rate_5pp` (20.2%, TPC), `illustrative_500k_2pp` (18.3%, TPC). §6.2 item 45 records
that two of them — `illustrative_1pp_all` and `cbo_opt45_all_rates_1pp` — **score the same reform
against targets 23.5% apart**, so the model cannot agree with both, and Wave B's H2 changed which
one it agrees with. The existing plan's §5 already concedes that the AGI-surtax class's 7.6-point
miss is "dominated by target provenance and one base definition."

**Mechanism.** H9's per-target judgement, applied to Tier 1 for the first time — the manifest's
supersede rule (`preregistered.py`, new `.v2` row with `superseded_by`, ledger commit before
scoring commit), not `target_revisions.py`, which is the calibrated tier's ledger. Four states as
before: revised, examined-and-left with the verdict written, range-revised, retired with the search
recorded. `medicare_surcharge_2pp` also needs a **base decision** the class cannot make: its
statutory base is wages plus net investment income, which is **neither SOI column**, so the honest
outcome may be a scope verdict rather than a revision.

**Files.** `fiscal_model/validation/preregistered.py`, `fiscal_model/validation/cbo_scores.py`,
`docs/VALIDATION.md`. **No module may be opened.**

**Pre-registrable expectation.** Direction genuinely unknown, which is the point — H9's own outturn
was that five of six revisions made their row **worse**, and that is the shape a correct provenance
pass has. Register the count, not the mean: Tier 1 `secondhand` **5 → ≤ 2**, with every survivor
carrying a written verdict. **Falsified if** any model constant moves or any row is retired to
improve a mean.

---

### R3 — H10's Tailor battery, with a source *(5 lane-days)*

**Stakes.** Criterion ① is a size condition and only this lane satisfies it. Two classes are single
observations and H4's bands are read off those observations; Wave C's own "what it did not do"
says registering a row there would have been "selecting a target after seeing what the band needed."

**Mechanism.** Two sources, both new.
`cbo-data/data/budget/revenue_detail/annual_fy_2026-02.csv` carries **42 `leg_rev_*` series — CBO's
own annual revenue effect of every major act since 1981**, in dollars and as a share of GDP:
`leg_rev_tcja` FY2018–2027, `leg_rev_obbba_25` FY2025–2035 (−130.905 → −500.987), `leg_rev_ira_22`,
`leg_rev_arpa_21`, `leg_rev_atra_12`, `leg_rev_egtrra_01`, `leg_rev_tax_reform_86`,
`leg_rev_econ_recovery_81` (tax survey §2.1, §3 row 10). Each supplies the five things
`preregistered.py` requires: a line-item dollar figure, an annual path, the document, the vintage
and the window. Second, the *Options* volumes across **2018, 2020, 2022 and 2024** give Options
45/46/47 four times — the same reform, four vintages, four independent observations of one
mechanism, which is what `CORPORATE_PER_POINT_YIELD.md` showed is available and nobody has used for
the individual base.

**Two leakage rules, stated before the lane opens.** `leg_rev_obbba_25` overlaps the eight P.L.
119-21 JCX-35-25 line items already in the reconstruction tier; **one act, one row**, and the lane
states which. `leg_rev_tcja` is TCJA's *enactment*, not the *extension* the module is fitted to, so
it is not leakage — say so explicitly, because it looks like it.

**Files.** `fiscal_model/validation/preregistered.py`, `fiscal_model/validation/cbo_scores.py`,
`fiscal_model/validation/policy_classes.py` (a new class routes, or the gate fails three ways by
design), `.github/workflows/validation-dashboard.yml`.

**Pre-registrable expectation.** ≥ 40 rows, ≥ 15 at thresholds other than $0/$400K/$1M, enacted-law
spending **3 → 8+**, every class n ≥ 3. **The tier mean will rise**, and the lane registers that in
advance: a battery selected for expressibility rather than for fit is the *only* honest way to grow
it, and the existing gate at `--max-mean-error 20` has 5.5 points of headroom. The gate is
re-derived **after** the rows land, by the workflow's rule, downward only (owner ⑪).

---

### R4 — The statutory parameter schedule *(3 lane-days)*

**Stakes.** It refutes a written impossibility. H2 declared the year-indexed threshold out of scope
because "a published post-2025 rate table … does not exist"
(`cbo_scores.py`, `cbo_opt45_top4_brackets_2pp` limitation 2), and the existing plan's rejection
table carries the same verdict. **It exists.**
`cbo-data/data/budget/tax_parameters/annual_cy_2026-02.csv` is 150 variables × CY2025–CY2036:
seven rates (`tp_rate_1..7`), seven bracket boundaries in **four filing statuses**
(`tp_bracket_7_mfj` 751,600 → 768,700 → 944,800; `tp_bracket_7_single` 626,350 → 640,600 → 787,325),
AMT exemptions and phase-outs by status, sixteen EITC parameters, five CTC parameters
(`tp_ctc_per_child` 2,200 → 2,400 → 2,700), **SALT limits by filing status**, standard deductions,
`tp_ss_max_earnings`, and both price indices (tax survey §2.1, §3 row 2).

**Mechanism.** This is §6.2 item 27's third `isinstance` branch, which is the trigger the item names
for building `Policy.scores_by_year()` rather than a fourth special case. The gain is
**expressiveness, not error**, and the rate table is *law*, not an estimate, so there is no leakage
on the statutory side. The hard rule: it may not be used to re-fit anything.

**Files.** `fiscal_model/policies_core.py`, `fiscal_model/amt.py`, `fiscal_model/credits.py`,
`fiscal_model/tax_expenditures_core.py`, `scripts/build_filing_status_data.py`.

**Pre-registrable expectation.** **A registered regression on at least one row**, direction already
known: H2 states the year-indexed threshold takes `cbo_opt45_top4_brackets_2pp` (14.9%) *further
under*. The lane predicts a band for that row and reports the movement, not the attainment. PR
#127's precedent stands — three of four rows got worse and the split was still necessary.

---

### R5 — H3b: corporate, with CBO's own loss-firm haircut *(4 lane-days)*

**Stakes and error.** `cbo_opt64_corporate_rate_1pp` at **44.5%** is Tier 1's largest single row and
**11.8% of its mass**, and it is a class of one, so the CI ceiling for `corporate` is **56**.
`trump_corporate_15` at **121.6%** is the worst headline reconstruction outside pharma and sits on
Explore and Build.

**Mechanism.** `CORPORATE_PER_POINT_YIELD.md` §4b established that this model's implied marginal
base is **80.8%** of the vintage average against a published 55.1% (Tax Foundation), 55.9% (JCT),
64.4% (PWBM) and 79.5% (Treasury). CBO's own answer to "how much of the statutory base is live" is
published and derived from SOI: **0.80 and 0.85** — `dmyrevx` and `dmyrevnfc` at
`business-investment-model/source_code/Create_Tax_Data.prg:32-33`, derivation at `:21-27` (tax
survey §3 row 4). That is a published ratio, not a fit to any score.

**The hazard, named in advance and unchanged.** `scripts/corporate_yield_reconciliation.py` prints
the number that would land the row — total factor **0.5785** against JCT's steady-state **0.590** —
and approaching it is the failure mode. And **a haircut moves both corporate rows the same way**, so
it cannot fix both if they miss in the same direction, which §6.2 item 53 says they do.

**Files.** `fiscal_model/corporate.py` (derived branch, `:151-217`; the fitted constant at `:78` is
self-documented as fitted at `:71-77`).

**Pre-registrable expectation.** H3b's existing bands, unchanged: `cbo_opt64` 44.5% → **30 ± 8**;
`biden_corporate_28_fy2022` −62.9% → **−45 ± 10**; `trump_corporate_15` 121.6% → **90 ± 20**.
`biden_corporate_28` is fitted and moves in `derived` only. **Owner ⑤ must be answered first**:
H3a's measurement — `derived` lands *inside* the published span at the +7pp step every shipped
preset uses and outside it at +1pp — is a second independent reading pointing the same way as PR
#122's Decision 1 reversal, and it goes stale (§6.2 item 53).

---

### R6 — H12: demote the sectoral presets *(1 lane-day + owner ⑨)*

Criterion ② has a ceiling clause and this is how it is met without deleting anything.
`international_reference_pricing` reads **701.0%**, `expand_drug_negotiation` 93.3%,
`double_enforcement` 82.3%; `Pharma` is a **277.8%** category mean over three rows and two of its
targets are `model_estimate` — the model's own extrapolation. Nobody quotes "International Reference
Pricing" as a score, so it fails the existing plan's first salience test. **Recommendation unchanged:
demote, do not model** — the alternative is §6.2 item 12 at ~8 lane-days for rows nobody cites. The
scorecard rows stay exactly where they are; this moves presets off a *surface*. Owner ⑨ is required
because it removes figures from Explore and Build, and owner ④ (retire the two pharma targets, or
carry them unsourced) interacts: **retiring them would buy 18.5 points of "improvement" by
deletion**, which §5 forbids, so a retired row keeps its entry and reports only beside a
held-in-place second reading. H9 built that machinery and applied it to nothing.

---

### R7 — The generic base on CBO's own projected path *(4 lane-days)*

**Stakes.** 18 of 26 Tier 1 rows and every generic surface. The AGI-inclusive class is **17.57%
against a plan target of ≤ 10%**, and after R2 removes the target disputes this is the only
remaining *mechanism* named for it.

**Mechanism.** H2 grew a TY2023 SOI aggregate by nominal GDP and **its own falsification condition
fired** — the tier rose 15.0% → 15.6% before H2b's AGI column brought it to 14.7%. CBO publishes the
base itself, annually, on three vintages:
`cbo-data/.../revenue_detail/annual_cy_iit_2026-02.csv` carries `rev_iit_agi` 18,810.4 (CY2026) →
25,817.9 (CY2035), `rev_iit_taxable_income` 14,245.168 → 20,313.807, `rev_iit_taxable_ordinary` and
`rev_iit_taxable_capgains_divs` **separately**, `rev_iit_capital_gain_loss`, `rev_iit_returns_total`,
and AGI shares for the top 1/5/10/25/50 percent (tax survey §2.1, §3 row 7). The
ordinary/preferential split is the quantity H2b reconstructed from SOI by hand.

**The leakage line, and it is fine.** These are CBO's *projections of the base*, not published
scores — a base improvement, not a fit. But the same file carries `rev_iit_tax_bracket_1..7`, CBO's
own projected tax collected in each bracket, and **a lane scoring a bracket reform may not read it
as a check on its own output.** The tax memo's §4 records this rejection on principle; repeat it in
the lane doc.

**Pre-registrable expectation.** High variance, rows moving in both directions, some crossing.
Register per-row bands before opening a file and expect at least two registered regressions — this
is the third base change in three waves and the previous two both produced them.

---

### R8 — Tariffs: the offset path, the HS-10 base, the elasticity ramp *(3 lane-days)*

`Trade` is **43.6%** over 5 rows after PR #150 registered it as worse on purpose; on the four rows
that have a document it reads 35.66%. Three sourced moves, one lane (tax survey §3 rows 3 and 11
are one lane's work in one file):

1. **The offset is a year path, not a scalar.** `trade.py:153`'s `income_payroll_offset_rate = 0.25`
   against CTAM's `inputs/offset/2025OffsetPostHR1.csv` — JCT's own **0.244 → 0.241**. Worth ~1pp on
   every trade row, sign depending on the year.
2. **The steel base at article level.** `trade.py:127-135` already declares the HS-73
   whole-chapter base an **upper bound** "because the Section 232 annexes list articles at HS-10";
   CTAM ships those lists (`inputs/hts_lists/alst_deriv_h.csv`, `alst_deriv_l.csv`, `alum_steel.csv`)
   with metal-content shares 0.75/0.25. Closes §6.2 item 64.
3. **The elasticity as a path.** `trade.py:148`'s single `-0.997` against CTAM's
   `boehm_elasticities.csv` (0.5517 → 2.0408 over 2025–2035) and 110 NAICS-4 substitution
   elasticities. Note in the lane doc that −0.997 is Tax Foundation's own choice (FF861 p. 4), so
   this swaps one published estimator for another rather than moving toward truth.

**`steel_tariff_25`'s movement is not evidence either way**: its target is untraceable and
examined-and-left twice (§6.2 item 65), and the lane must say so rather than quote the row.
Decision 6 applies — five presets move.

---

### R9 — The SS donut ramp *(2 lane-days)*

`ss_donut_250k` is **89.2%** — the reconstruction tier's fourth-worst row and one of the app's six
largest headline figures. H13 found the defect and could not take it: **both published paths ramp
and the module's does not**, $122.0B (FY2026) → $192.0B (FY2034) against a flat $270B, 17.0% high at
the start and 25.7% low at the end (§6.2 item 47). CBO's own OASDI taxable-payroll path is now
reachable — **$10,890.7B (FY2026) → $15,258.2B (FY2035), 3.82%/yr**, from
`social-security-trust-funds-model` sheet `Combined` row 7 (macro survey §3 row 4).

**Two constraints, both from the memo, both binding.** The workbook is February 2026 and the target
is CBO Option 62 alt 2 from the December 2024 *Options* volume, so shape input and target sit on
different vintages — `iija_2021_discretionary.v2`'s precedent covers it but the lane must declare it.
And **the payroll path may not be used to construct a dollar target**: see the rejection in §1's
closing table. Decision 6 caption owed.

---

### R10 / R11 — H7 and H11, expected residuals *(Wave D, running)*

**H7 (expenditures, 3 days).** All five `BEHAVIORAL_ELASTICITIES` are unsourced
(`tax_expenditures_core.py:467-473`, the block comment at `:449-466` saying so). Two now have a
published figure beside them — Poterba & Sinai's 15% against mortgage's 0.10, and charitable's 0.40
carrying the size of a *price elasticity of giving* where the 28%-ceiling arithmetic implies nearer
0.18. **The surveys supply nothing here** and the tax memo says so explicitly (§3 row 13), which is
worth recording so nobody goes looking. Expected residual: `Expenditures` LOO is **40.6%** on this
tree (up from 37.5% after H9 moved `eliminate_mortgage`'s target), and the hazard is unchanged —
three of the module's six fitted constants were fitted so the *static* path hits the target and
three so the magnified score does, so re-fitting them is what §1.1 forbids.

**H11 (PTC, 2 days).** `repeal_ptc` at **29.6%**; the residual is the coverage response, a single
19.28% share dominated by employment-based coverage ($101B). The macro memo adds a *method*: CBO's
`medicaid-labor-supply-model` publishes alternative-coverage probability **by FPL band** with valued
alternatives (macro survey §3 row 10). **The levels are Medicaid's, not the marketplace's, so
nothing there can be lifted as a number** — it is a structure. Falsified if the module reproduces
−$1,100B, which PR #131 demonstrated is a baseline projection.

---

### R12 — The dynamic tab's two round numbers *(4 lane-days)*

The dynamic tab is 🟢 by CLAUDE.md's own taxonomy and **no benchmark is scored dynamically**, so no
tier moves and the whole lane is a provenance upgrade on numbers users read.
`MARGINAL_REVENUE_RATE = 0.25` (`constants.py:71`, commented "Combined federal revenue/GDP ratio —
CBO") stands in for what CBO decomposes into **nine** published marginal rates on nine NIPA series:
wages 0.18→0.21, FICA 0.10, proprietors 0.11→0.12, SECA 0.04, domestic corporate profits 0.07→0.08,
dividends 0.02→0.03, personal interest 0.07→0.08, excise 0.01, customs 0.15→0.13, applied as
`Δliability = rate × (alt − base)` per series with fiscal-year weights 0.75/0.64/0.45
(`budgetary-feedback-model/input/rules_of_thumb.csv`; `bfm/revenues.py:35-38`;
`input/parameters.csv:2-6` — macro survey §1 finding 3, §3 row 3). Alongside it,
`macro_adapter_frbus.py:443`'s `interest_cost = cumulative_deficit * 0.04` against CBO's published
lower-triangular debt-service matrix (`rate1..rate11`, $55.06B per 1pp decaying to $10.10B) plus the
Federal Reserve remittance channel the app has no concept of (macro §3 row 6).

**It also gives the app a composition channel it entirely lacks**: a spending impulse lands on wages
(0.19 + 0.10) and a corporate cut on profits (0.075) at very different feedback rates, where today
both recapture 0.25. Shipped dynamic figures will move materially — **Decision 6 applies**. One
sentence the memo earned and this lane should carry: CBO's own marginal rate on customs duties is
**0.15 falling to 0.13**, roughly half `trade.py:153`'s 0.25. They are not the same quantity (a
feedback rate vs a scoring convention) and the lane must not swap one for the other — but a shipped
trade score whose offset is twice CBO's marginal rate on the same revenue line deserves the sentence.

**Depends on R1**: the debt-service path is applied to a deficit path that is 27.6% too large today.

---

### R13 — The death channel's level half *(2 lane-days)*

§6.2 item 55, opened by Wave C and pointing the **opposite way** from the half Wave C took.
`gains_at_death_share_of_net_worth` is `estate_flow_rate × gain_share_of_estates` — the same
Poterba & Weisbenner *dollar* flow PR #151 removed from the headcount — and held against the
module's own `death_exit_rate` it implies **0.372% of the accrued-gains stock where the stock's
death exit is priced at 2.647%, a factor of 7.1**, none of which has been measured.
`cbo_opt51_gains_at_death` now **under**-predicts at 35.5%, so a larger level closes what the
headcount opened. The survey supplies the independent read: CapTax's
`environment_parameters.csv` carries `cap_gains_at_death_share` **0.4316**,
`cap_gains_long_term_holding_period` **9.1096** and `cap_gains_at_death_holding_period` **30**,
sourced to SOI *Sale of Capital Assets* 2007–2015 and SOI *Estate Tax Returns* 2007–2016 (tax survey
§3 row 12). **Run it as a measurement first.** The level is a thing nobody may change by
implication — owner ⑭, the same class of decision as ⑥ — and CapTax's
`cap_gains_long_term_tax_rate 0.2116` may **not** replace `elasticity_reference_rate = 0.22`, because
Decision 3 freezes it.

---

### R14 — CBO's own error-measurement discipline *(2 lane-days)*

Zero scored numbers move; it changes how every tier is quoted. `eval-projections` publishes three
choices this app makes none of (`src/errors.py:35-41, :47-56`; `src/summary.py:67-68`): **adjust for
later legislation before measuring**; report **percent-of-GDP beside percent-of-actual**; and report
a **two-thirds spread** rather than a mean. CBO's own year-6 total-revenue two-thirds spread is
**25.3 pp against an average absolute error of 10.1%** — which is both a published *shape* for H4's
bands and the first external comparator this roadmap has had. The macro memo adds the asymmetry:
H4's bands are symmetric and the errors are not (§6.2 item 58), and
`financial_regulation_model` ships every low/central/high combination as output, which is how an
asymmetric band gets built from a model rather than asserted (macro §3 row 8).

**The caveat must travel with the numbers**: CBO evaluates *baseline projections*, this app scores
*policy differences*. The discipline is a method and a comparator, **never a target to claim parity
with**.

---

### R15 — The spend-out vector: confirm, then refit *(1 + 3 lane-days)*

**(a), 1 day.** `fiscal_model/data_files/spending/outlay_rates.csv`'s own header records that the
external cross-check it wanted "were unreachable when this was built (cbo.gov 403)" — §6.2 item 16,
recorded as blocked three times. `budgetary-feedback-model/input/rules_of_thumb.csv` column `spout`
is **0.53, 0.26, 0.09, 0.05, 0.04**, zero thereafter, applied at `bfm/outlays.py:589-593` as
`Σ_k s_k · ΔBA_{t−k}` — the exact identity lane L2 built. On a first comparison the NNLS fit
**passes**: the app's `operations_and_support` row (0.5387, 0.2571, 0.0666, 0.0726, 0.0416) differs
by a mean absolute **0.0118** and a maximum **0.0234** (macro §1 finding 2, §3 row 2).
**The likely outturn is that no number moves, which is the point.** Caveat to pre-register: CBO's is
**one economy-wide vector** against the app's five account classes, and BFM applies it to
discretionary BA only — it checks the O&S class and bounds the others; it cannot replace the
structure.

**(b), 3 days, optional.** `cbo-data/.../spending_detail/annual_fy_{2024-06,2025-01,2026-02}.csv` is
**21,769 rows = 1,712 budget accounts × 11 fiscal years**, each with `budget_authority` *and*
`outlays`, `function_code`, `subfunction_code`, `disc_or_mand` (tax §3 row 9). Refitting there
improves *provenance*, not accuracy — the five CBO Options spending rows already land at 0–11% and
discretionary is the tier's best class at **4.64%**. The 14 donors are CBO *options*, i.e. estimates;
account BA and outlays are the baseline's own accounting.

---

### R16 — `_scorecard_index` on scored routes *(2 lane-days)*

The exploratory-tier performance item, and it is really a 🟢 defect. PR #135 took the landing page's
first script run 8.404s → 0.668s; the **scored** route is unchanged at ~**10.6s**, with exactly one
call over half a second — **6.555s** arriving at `preset_validation.get_validation_badge →
_scorecard_index` from `policy_input_tax.render_tax_policy_inputs` (§6.2 item 39). An artifact of
counts cannot serve it: the per-preset badge needs each row's model figure, official figure, rating
and source URL, and pinning model *outputs* would be a far larger claim than pinning a count. What
closes it is making the scorecard fast — ~**93,000** pandas `iterrows` calls under the Wave 2 L1
capital-gains path (`data/capital_gains.py:267, :287, :427`). Ranked last because it moves no §0
criterion, but it is the one "the app is slow" complaint that is not a UX question.

---

### Rejected explicitly, with reasons

The surveys tempt several things the rules forbid. Recording them so nobody re-derives them.

| Candidate | Verdict |
|---|---|
| **`premium-growth-model` to close Option 56** | **Rejected — leakage.** PGM's own README says its output feeds HISIM2, and HISIM2 produces CBO's health scores including Option 56's. Option 56 is a **Tier 1 out-of-sample row at 13.1%**; feeding CBO's premium projection into the model that predicts CBO's option score makes the row an input to itself. Exactly the class `repeal_individual_amt` refuses TPC's T25-0049 for. If ever taken, it is a **sensitivity**, never a replacement, and it needs an owner decision first (macro §3 row 7, §1) |
| **The OCACT percent-of-payroll → dollars conversion** | **Rejected, and now demonstrated rather than argued.** The denominator is published, the conversion is available, and it **fails**: OCACT E2.5 × CBO's payroll gives $201.5B in 2026 against CBO's own $122.0B for the identical donut design, and $368.1B vs $192.0B in 2034 — **1.65× to 1.92×, widening**, totalling $2,543.9B against the carried $1,426.8B. H13's refusal stands (macro §4.1) |
| **CBO's Nov-2025 tariff score ($2,380.58B, FY2026–2035) as a Tier 1 row** | **Rejected — shape not expressible.** A genuine published CBO conventional estimate and not leakage, but it is a stack of overlapping Section 232 actions, reciprocal rates, USMCA carve-outs, country caps and article-level exemptions `TariffPolicy` cannot construct. The row's error would measure inexpressibility, not accuracy. The tractable fragment is the implied import decline (16.49%; 25.57% for China) as a check on the elasticity, inside R8 (tax §4) |
| **`rev_iit_tax_bracket_1..7` as a check on a bracket score** | **Rejected on principle.** CBO's own projected tax collected per bracket is adjacent to the answer. Usable as a *base* (R7 says so); not usable as a check on the thing it is a base for |
| **The corporate landing factor (0.5785 vs JCT's 0.590)** | **Forbidden.** `scripts/corporate_yield_reconciliation.py` prints it; R5 approaching it is the failure mode, not the goal |
| **CapTax's `cap_gains_long_term_tax_rate 0.2116` for `elasticity_reference_rate`** | **Blocked by Decision 3.** Reportable as a comparison; not a lane's to change |
| **`markov-switching-macrosimulation-model` bands for H4** | **Rejected — category error, and a flattering one.** Forecast uncertainty where H4 deliberately ships model-error bands. Forecast bands are wider and would make every row look contained (macro §4.2) |
| **`means_tested_transfer_imputations` for the distributional universe** | **Rejected for now — licence, size, circularity.** Its README says in bold that the imputations "should not be used for … policy simulations"; 542 MB against the repository's size policy; and two of the seven distributional benchmarks are already circular (macro §3 row 9) |
| **`electric_vehicle_model` as a target source** | **Rejected.** It produces no dollars and CBO states it "has not been used for any CBO baseline or cost estimate analyses." Constructing a credit cost from it would be the app's own construction in a target column — the `trump_corporate_15` `model_estimate` defect in a new costume (tax §4) |
| **Retiring the two pharma rows to improve the tier mean** | **Forbidden.** 18.5 points of "improvement" by deletion. A retired row keeps its entry and reports beside a held-in-place reading (H9) |
| **Any constant chosen because it lands a row** | **Forbidden, unchanged.** A lane that adds a constant reproducing a benchmark has failed regardless of the error it closes |

---

## §2 — Waves

Files are disjoint within a wave, so lanes run as parallel agents in worktrees. Waves A–C are done;
**D is open and running** (H7, H11, H12) and is carried here unchanged; E was scoped by the existing
plan and is re-scoped below because R1 outranks both of its lanes.

| Wave | Lanes (parallel) | Files | Days | Owner decisions needed **before** the wave opens |
|---|---|---|--:|---|
| **D** *(running)* | **H7** expenditures · **H11** PTC · **H12** sectoral demotion | `tax_expenditures_core.py` / `ptc.py` / `app_data.py` + `explore.py` | 6 | ⑧ SALT's two baselines — a joint call on both rows (§6.2 item 3). ⑨ Do the four pharma presets and Double IRS Enforcement stay on headline surfaces? |
| **E** | **R1** baseline transcription · **R2** Tier 1 provenance · **R15a** spend-out confirmation | `baseline.py` + `constants.py` + data block / `validation/preregistered.py` + `cbo_scores.py` / `data_files/spending/` + docs | **7** | ③ IIJA `.v3` — apply the window rule to the second row or to neither (§6.2 item 35); **R2 cannot open with this unsettled**, because it is a Tier 1 target decision. ⑩ **New:** does a CBO *model input* file (`budgetary-feedback-model`) count as "CBO's own table" for `VINTAGE_SOURCING`'s `"sourced"` grade, or only `cbo-data`'s published mirror? |
| **F** | **R4** parameter schedule · **R5** corporate mechanism · **R8** tariffs | `policies_core.py` + `amt.py` + `credits.py` / `corporate.py` / `trade.py` | **10** | ⑤ Does H3a's shipped range change Decision 33's `reported` default? **Answer before R5 opens**; §6.2 item 53 says the measurement goes stale |
| **G** | **R3** Tailor battery · **R9** SS donut ramp · **R13** death-channel level | `validation/preregistered.py` + `cbo_scores.py` + `policy_classes.py` / `payroll.py` / `data/capital_gains.py` | **9** | ⑪ **New:** R3 registers ~15 rows; confirm the CI gate is re-derived **after** they land, by the workflow's rule, not before. ⑭ **New:** the death-channel *level* (§6.2 item 55) — a level nobody may change by implication, the same class as ⑥ |
| **H** | **R7** generic base · **R12** dynamic constants · **R14** reporting shape | `policies_core.py` + `scoring_engine.py` / `constants.py` + `macro_adapter_frbus.py` / `cold_holdout.py` + `credibility.py` | **10** | ⑫ **New:** Decision 3 — is the capital-gains elasticity at large steps re-openable now that a second agency publishes a reference rate? (R13's measurement is the input; it is the single largest remaining capital-gains term.) ⑬ **New:** does a Build option show model output **beside** the list price, or carry a label saying it is one? Criterion ④ is met either way and the choice is the owner's |
| **I** *(deferred)* | **R15b** spend-out refit · **R16** scorecard performance | `scripts/fit_outlay_rates.py` / `preset_validation.py` + `data/capital_gains.py` | **5** | — |

**Total: 41 lane-days beyond Wave D's 6.**

### Serial constraints, stated

1. **R1 before anything that reads a level.** R12's debt-service path is applied to a deficit path
   that is +27.6% today; R9's window and Build's target strip both read the baseline. R1 is in Wave E
   for that reason and not because it is cheap.
2. **R4 before R3 registers any year-indexed row.** A battery that registers a row the engine cannot
   express produces an error measuring inexpressibility. R3 may register only shapes expressible at
   the time it registers them, and the year-indexed subset waits.
3. **R4, R7 and R3 may not share a wave.** All three reach the generic income-tax path, and H2/H2b
   are the precedent for what happens when two base changes land together: the endpoints stopped
   being attributable and the plan's own §1.3(c) had to be corrected in place. One base change per
   wave.
4. **R2 before R3.** Growing the battery while five of its existing rows have untraceable targets
   dilutes the provenance criterion instead of meeting it — and R2's verdicts set the standard R3's
   40 rows are held to.
5. **R13 is a measurement in Wave G and a change only if ⑭ is answered.** Half of a two-sided
   correction was already registered in Wave C and 35.5% is the price of the half.
6. **R5 and R13 both want H3a-style presentation shipped first.** It is (PR #143); do not re-open it.

---

## §3 — A longer horizon: the microsimulation core

**What exists already.** `fiscal_model/microsim/` is **2,634 lines**: `engine.py` (826, with
`MicroTaxCalculator` at `:22` and `calculate` at `:194`), `data_builder.py` (809),
`soi_calibration.py` (309), `top_tail.py` (244), `filing_threshold.py` (193),
`salt_imputation.py` (91). It is real — Wave 3's L3 credits lane runs two CTC/EITC parameter sets
through it over CPS ASEC tax units and differences on final liability, taking the credits LOO module
45.1% → 18.5%. It is also **measured, on this tree, as insufficient**: the dashboard's SOI
calibration block reads **191.1M microsim returns against SOI's 160.6M (119.0% coverage)** and
**$12.38T of AGI against $15.29T (81.0%)**, with the $0–15K bucket at **2.65×** and the **$10M+
bucket at 0.00** — the top of the distribution is empty.

**What the surveys add.** Three pieces, and together they are most of a core:

1. **A published tax-unit construction algorithm.** `CPS-tax-filing-units/docs/algorithm.md` states
   CBO's full rule; `scripts/4a`–`4e*.do` implement it; and
   `outputs/Kinships_in_Tax_Units_CPS_CY_2024.csv` gives population by filing status × kinship at
   each of four passes. The app's own rule is **five documented lines with no citation to any
   published tax-unit algorithm** (`microsim/data_builder.py:398-408`) and its filing status is
   binary married/not by its own admission (tax survey §3 row 8). The kinship table is a **direct
   check** on the 191M-vs-161M gap `filing_threshold.py:10-14` records.
2. **The statutory parameter schedule** (R4) — brackets, AMT, EITC, CTC, SALT limits and standard
   deductions **by filing status by year, CY2025–CY2036, on three vintages**. A microsimulation
   without a year-indexed parameter schedule is a one-year calculator run ten times, which is what
   the app has.
3. **CBO's own projected base** (R7) as the aggregate the simulated population is calibrated to,
   with `rev_iit_returns_total`, `rev_iit_returns_itemized` and `rev_iit_returns_amt` as counts to
   calibrate against rather than the SOI aggregate held at its tax year.

**What the app cannot obtain.** The IRS Public Use File is restricted and nothing in CBO's
organisation substitutes for it; CPS top-coding is why the $10M+ bucket reads 0.00 and why
`top_tail.py`'s Pareto augmentation exists; and the transfer-underreporting imputations that would
fix the bottom of the distribution carry a README that forbids policy simulation and 542 MB against
the repository's size policy. So the honest scope is a **CPS-based tax-unit microsimulation with a
Pareto-augmented top tail and a published construction algorithm** — better than three
reconstructions, not equal to JCT's.

**Cost.** 20–30 lane-days across at least four lanes: unit construction against the kinship table
(5); the parameter schedule wired through the calculator, which is R4 done properly rather than
bolted on (5); calibration to CBO's own return counts and AGI path (5); and a `TCJAExtensionPolicy`
microsim path (§6.2 item 17) with its distributional half (5–10). None of it is parallel with the
others in the way §2's waves are, because each reads the previous one's population.

**What it would unlock.** The eight P.L. 119-21 JCX-35-25 line items reconstruct at **35.8%** today
and are the sharpest evidence the calibrated tier is reconstruction rather than structure; a
microsim path is the only mechanism anyone has named for them. Three of the seven distributional
benchmarks fall back `household→tax_unit` because `TCJAExtensionPolicy` and the corporate policy have
no microsim path, so the surfaces report a universe the source does not rank. And criterion ④'s Build
question would dissolve: a package total computed from one population is model output, not a sum of
list prices.

**Why it is the 9 and not the 8.5.** Every §0 criterion is reachable without it — the battery grows
from published paths, the reconstruction tier improves through sourced mechanisms and a demotion, the
provenance counts fall by reading documents, consistency is a contract already half-built, and the
baseline is a data edit. A microsim core changes what the model *is*: it stops reconstructing agency
scores and starts producing them. That is a different claim, it costs roughly as much as this whole
plan, and it should not be started until the five coordinates above are met — because a
microsimulation calibrated against a baseline that is 27.6% off, and validated against a battery with
five untraceable targets, would inherit both.

---

## §4 — Process

Unchanged from `HIGH_STAKES_ACCURACY.md` §3's six rules, plus four the surveys and this tree add.

1. **`cbo-data` is the canonical machine-readable source, and cbo.gov is still 403.** Every fetch in
   both surveys went through the Internet Archive; `github.com/US-CBO` is **not** blocked. Where both
   carry the same number, prefer the repository — it is versioned, schema'd, vintage-aware, and its
   own `catalog.json` names "AI agents and automated systems" as the primary audience. Two
   consequences for lanes: **pin a commit or a `vintage` string**, because the catalogue is
   regenerated on release and its only freshness stamp is a `generated` field; and a lane needing a
   cbo.gov PDF must plan for the 403 rather than discover it.
2. **A piped pytest reports the pipe's exit code, not pytest's.** Two Wave C lanes hit this
   independently — PR #151 recorded exit 0 from `| tail -25` while pytest had failed, and PR #149
   lost a full suite run the same way. **Write the output to a file, read the file, take the exit
   code from the unpiped command.** It is PR #119 §7.5's lesson in a second costume: a green signal
   produced by something other than the thing being checked.
3. **`ANTHROPIC_API_KEY` unset for the suite; the key only for the deliberate smoke test.** With it
   exported, parts of `tests/` make live Anthropic calls and bill. CI never sets it, so a green local
   run with the key present is not the run CI performs. A lane that moves a scored number must
   re-run `scripts/smoke_ask_assistant.py` (~$0.04), because the assistant quotes
   `get_app_scoring_context` and `score_hypothetical_policy` off the same engine.
4. **`ruff format` — never.** CI runs `ruff check` only
   (`.github/workflows/tests.yml:101-110`, pinned at 0.15.8); `ruff format --check .` fails on ~317
   files repo-wide on `main` and is not a gate. Running the formatter produces a diff that buries the
   lane. Note also that `.gitignore`'s bare `data/` line makes ruff skip `fiscal_model/data/`
   entirely (§6.2 item 41) — a repo-wide gate change needing its own PR, not a lane's.
5. **The per-class gate is a floor, not a summary.** `cold_holdout.py --max-class-mean-error` is
   wired at `validation-dashboard.yml:186-191` with eight ceilings —
   `agi_inclusive_surtax=22 ordinary_rate_change=19 capital_gains=24 corporate=56
   enacted_law_spending=17 discretionary_spending=6 payroll=10 tax_expenditure=17` — beside the
   pooled `--max-mean-error 20 --min-within-25pct 22` and the LOO `--max-mean-error 75`. It fails
   three ways: a class over its ceiling, a class the battery contains with **no** ceiling, and a
   ceiling naming a class that does not exist. R3 adds rows to existing classes and may add a class;
   **either way the gate is re-derived after the rows land, downward only.** Note the LOO ceiling is
   now **2.1× its live mean** (75 against 35.7%) — §6.2 item 54, and it should be re-derived in the
   same pass.
6. **What the docs sync after each wave must carry.** PR #152's shape is the template — ten files:
   `CLAUDE.md`, `README.md` ("Model maturity" and the validation tables), `docs/CHANGELOG.md`,
   `docs/METHODOLOGY.md`, `docs/VALIDATION.md`, `planning/HIGH_STAKES_ACCURACY.md` (outturn boxes in
   place, corrections attributed), `planning/MODELING_IMPROVEMENT.md` (§5.x outturn + §6.2 items
   struck and opened), `planning/NEXT_STEPS.md`, `.github/workflows/validation-dashboard.yml` (the
   gate, re-derived by rule), `tests/test_ci_workflow.py`. **Add this document to that list** — its
   §0 table is a live scoreboard and a wave that does not update it has not reported.
7. **Report movement, not attainment.** Four of Wave 7's seven lanes and two of Wave C's were
   pre-registered regressions that landed as regressions, and two Wave C lanes found the plan's own
   diagnosis wrong. A lane that reaches a better tier mean by making rows worse reports both; a lane
   whose own falsification condition fires says so and tunes nothing.

---

*Measurement provenance for §0 and §1: `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`,
`python scripts/run_validation_dashboard.py`, `python scripts/run_loo.py --donor-matrix` and a direct
`CBOBaseline(start_year=2026, vintage=BaselineVintage.CBO_FEB_2026).generate()`, all run on this
branch. Health reports `degraded` on `runtime` only — Python 3.14.0 against a supported
`>=3.10,<3.14` — which is a local-environment state, not a tree state.*
