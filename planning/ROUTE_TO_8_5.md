# The route from 7.5 to 8.5

*Written 2026-09-11 on `planning/route-to-8-5`, branched from `main` @ `20e356d` with
`memo/cbo-github-survey-tax` (PR #154) and `memo/cbo-github-survey-macro` (PR #153) merged in.
Every figure below is from one of four runs on **this** tree — `ANTHROPIC_API_KEY= python
scripts/cold_holdout.py --json`, `scripts/run_validation_dashboard.py`, `scripts/run_loo.py
--donor-matrix`, and a direct `CBOBaseline(start_year=2026, vintage=CBO_FEB_2026).generate()` —
or from a `file:line`, or from a cited section of one of the two survey memos. Nothing is recalled.*

*Re-measured **2026-09-11** after PRs #155, #157, #158, #159, #160, #161 and #162. **§0's table, §2's
wave rows, §4's rule 5 and every ✅ outturn box below carry the merged-`main` reading**; the dated
prose inside each lane's body is left as it was written, because the ranking in §1 was computed from
it. Where a body figure and an outturn box disagree, the box is live and the body is the motivation
that produced the lane.*

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

> **Re-measured 2026-09-11 on merged `main`, after Wave F — PRs #164, #165, #166 and #167 — on top
> of #155, #157, #158, #159, #160, #161 and #162.** Wave F moved three of the five criteria and
> **not one of them favourably**, which is what a wave of two registered regressions and one refusal
> looks like: ① reads **11.8%** with 17 of 22 within 15% where it read 11.6% and 18, ② reads
> **42.3%** on the *same* 38 rows where it read 37.5%, and ⑤ is unchanged. What did improve is
> outside every criterion: the **corporate app default** now sits on the mode that lands inside the
> published estimator span, and two published bases — the Section 232 annex and the statutory
> bracket schedule — are read at the granularity their own statutes are written at. **The column
> below is still not a scoreboard anybody may congratulate**, and the roadmap owns the reason:
> **criterion ①'s n fell 26 → 22 by *retirement*.** Four Tier 1 targets turned out to be in
> no publication and were withdrawn with their searches recorded — three of them from inside 25% —
> so the tier's mean fell 14.5% → 11.6% while the test it constitutes got **weaker**. **The battery
> has to GROW through R3 before the class means are quotable again.** Three consequences, stated
> plainly rather than buried in a cell. The **AGI-inclusive-surtax class is down to n = 2 and reads
> 5.2%**, which nominally meets this plan's own ≤ 10% target on a battery too small to mean much.
> **Tier 1 now contains no rate cut and no positive target at all** — `illustrative_500k_2pp` was
> both — so it does not test the model in the direction a Tailor user most often asks about. And
> **the share within 25% rose 84.6% → 86.4% while the count fell 22 → 19**: quote the share beside
> the count, because only one of the two is comparable across a battery that changes size. The rule
> cuts both ways, which is the cleanest evidence it is about documents and not about means —
> `medicare_surcharge_2pp` scored **1.2% from the figure Treasury actually prints** and was retired
> anyway, because Treasury prints it for a **1.2pp** reform where the row applies 2pp; restated on
> the document's own rate it reads **39.3% under**, worse than the 31.8% it had been reporting.

| # | Criterion | Today, measured on this tree | 8.5 |
|--:|---|---|---|
| **1** | **Out-of-sample battery** — size, accuracy, and whether the per-class bands rest on a sample | **n = 22, mean 11.8%, median 8.9%, 17/22 within 15%, 19/22 within 25% (86.4%), error mass 258.9** — and **all 22 are `line_item`**, with `secondhand` **0** and `model_estimate` **0** (R2). Eight classes at n = **1, 1, 2, 2, 3, 4, 4, 5** — `corporate` and `tax_expenditure` are still **single observations** and `AGI surtax` has fallen to **two**. Class means: discretionary 4.60, **AGI surtax 5.15**, enacted-law spending 7.40, payroll 7.80, tax expenditure 12.80, **ordinary rate 13.85**, capital gains 18.70, corporate 44.50. **Wave F moved one row and one class**, both as a registered regression: R4's year-indexed statutory brackets took `cbo_opt45_top4_brackets_2pp` 14.3% → **17.9%**, which is the whole of 11.6% → 11.8% and of 12.90 → 13.85, and cost the tier a within-15 row. **R5 did not move the corporate row and says the plan's remedy for it is spent** — the loss-firm haircut is refuted on the merits, the credit channels are bounded and unpriceable, and what the class needs is a *second row* (§6.2 item 81), not a mechanism. **The mean fell 14.5% → 11.6% and most of it is the denominator**: of 120.8 units of mass that left, **94.1 went out with four retirements** and 17.9 with owner ③'s IIJA row, leaving about 8 for rows that moved while staying in | **n ≥ 40, mean ≤ 12%, ≥ 30/40 within 25%, and every class n ≥ 3 with no class mean above 25%.** The size condition is not decoration: a band read off one row is not a band — and **R3 now owes this tier four rows before it is back where it started**, never mind the eighteen that would meet the criterion |
| **2** | **Reconstruction tier** — measured on a *constant* population, and what a user can reach | **38 scored rows at 42.3% mean / 30.1% median, 11/38 within 15% — never quotable on its own line.** **Wave F moved this 37.5% → 42.3% on a constant 38 rows, so it is accuracy and not composition — and three quarters of it is one row against a target nobody published**, `steel_tariff_25` 75.3% → **258.1%** when R8 replaced two whole HS chapters with CBO's own HS-10 Section 232 annex; on the four trade rows that *have* a document the block moves **35.66% → 36.16%**, which is the figure to quote. PR #160 withdrew a **93.3%** and a **701.0%** target, so the tier **with both folded back at the error they carried on the day they were withdrawn reads 40 at 60.0% / 33.3%, 11/40**, printed on the adjacent line; PR #157's reclassification moved `cap_charitable` *in*, 39 → 40. Fifteen sub-populations from `Credits` 9.5% (n=1) to **`Trade` 80.5%** (n=5, from 43.6%), **`Corporate` 90.1%** (n=2, from 92.3%) and `Payroll` **89.2%** (n=1); `Pharma` went **3 rows at 277.8% → 1 at 39.0%**. Worst surviving rows: **`steel_tariff_25` 258.1%**, `trump_corporate_15` **129.6%**, `ss_donut_250k` 89.2%, `double_enforcement` 82.3%. **The ceiling clause is met on the surface half**: PR #158 moved all five sectoral presets into an explicitly-labelled illustrative group with their live error printed | **≤ 45% mean on the 40 rows held at Wave E's close, ≥ 15/40 within 15%, and no row above 150% reachable from a headline surface** — reached by moving the row, or by H12 demoting the preset, never by retiring the row. Both instruments have now been used and **neither deleted a scorecard entry**: a demoted preset keeps its row, and a retired target keeps its row, its model figure and its withdrawn target, and leaves the mean only beside a held-in-place second reading |
| **3** | **Provenance** | Calibrated tiers (n=55): `line_item` 36, `line_item_differs` 8, `secondhand` **7**, `model_estimate` **4** — unmoved by Wave E, which worked on the other tier, and unmoved by Wave F, whose three lanes moved *model* figures and no targets at all. Both tiers: **73 published of 77**, **44 transcribed**; *both halves fell by the same four retired rows*, so 77/81 → 73/77 is a battery shedding unsourced rows and not documents going missing. **The measurement this plan turned on has been spent**: Tier 1's five `secondhand` rows are gone — one superseded onto CBO pub. 58164 and four retired — so Tier 1 carries **0** `secondhand` and **0** `model_estimate`, and the 31.8%-of-mass concentration no longer exists to be closed. The `retire` state is **applied**, to two pharma targets (PR #160) | Calibrated `secondhand` ≤ 5, `model_estimate` ≤ 2, **Tier 1 `secondhand` ≤ 2 — met, at 0**; published ≥ 79/81, **which needs restating on a denominator of 77 before it can be scored again**; the `retire` state either applied or declined **in writing, per row** — applied twice, with the anti-gaming arithmetic printed rather than argued |
| **4** | **Consistency and coverage** | 44 of 53 presets badged, the 9 unbadged printing no dollar figure (H6, enforced by test). **Build quotes list prices, not model output** (`fiscal_model/ui/tabs/deficit_target.py:219-232`): 46 options, 44 with a scorecard row, and **13 of those 44 quote a `secondhand` or `model_estimate` target**. **Not re-measured since PR #156, and two things moved under it**: PR #158 demoted four Build options into the illustrative section, and PR #162's retirements took the `official_score` off **Warren Ultra-Millionaire Surtax** and **High-Earner Medicare Surcharge 2pp**, so both lost their badge while still scoring and still printing no dollar figure — the rule held rather than being waived, and Build's card copy moved "45+ scored policies" → **"40+"** | Every Build option **either** shows model output beside the list price **or** is labelled a list price on the surface itself; **≤ 6** quoting a `secondhand`/`model_estimate` target. The base-rule contract (H1) holds across all four constructors, and `DistributionalEngine` joins them (§6.2 item 46 — 2.57× apart today) |
| **5** | **The baseline** | **Largely met by R1 (PR #159), and the remainder is named.** All three vintages' **economic** paths and **two of three budget** paths are transcribed from `US-CBO/cbo-data` @ `284a9566`, pinned by commit and verified by SHA-256 per file. February 2026's FY2026–2035 cumulative deficit is **$23,143.30B against CBO's own printed $23,143.3B**, end-of-window debt/GDP **103.8% → 118.0%**, January 2025 **$27,710.6B → $21,758.3B**; corporate receipts now compound at **3.53%**, CBO's own figure, where the reconstruction gave 4.82%; the FY2026 individual-income-tax and payroll gaps close exactly. `VINTAGE_SOURCING` is **computed per line rather than asserted** — and it was **false for two of three vintages** while it was asserted. **February 2024 keeps a reconstructed budget path** (`cbo-data` publishes no `ten_year_budget` for that edition, and June 2024 is publication 60039, a different document), so **its debt/GDP is a mixture and must not be quoted** | **All three vintages transcribed from CBO's own table**, `VINTAGE_SOURCING` and `CORPORATE_RECEIPTS_SOURCING` graded from what was actually transcribed, and the vintage's ten-year deficit within 1% of the figure its own document prints. **Two of the three conditions are met and the third is one vintage short**: February 2024's budget path needs either a fourth `BaselineVintage` for June 2024 or a surface that refuses to render a ratio whose numerator and denominator carry different grades |

### What is explicitly **not** in 8.5

- **A microsimulation core.** §3 costs it and explains why it is the 9.
- **Any accuracy claim for the 🔵 exploratory tier.** Ask, the bill tracker, classroom and the
  multi-model pilots stay on a UX/safety bar. The one exploratory item this plan carries (R16) is a
  *performance* defect on a 🟢-tier path, not an accuracy one.
- **The fitted tier's 1.6% over 15 rows.** It is bookkeeping and it is not a number to protect. It
  has now lost rows to a target revision, an unfitted-constant deletion, the offset-sign rule and a
  **reclassification** — PR #157 took it 16 → 15 when `cap_charitable`'s constant turned out to be
  fitted to a quantity the module no longer computes — and the mean moved with membership every
  time, never because anything improved. **Held in place it reads 26 at 12.4%.** If a provenance lane
  takes it to 8% over 12 rows, that is the tier becoming honest.
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
| **R1** ✅ | Transcribe CBO's own February 2026 baseline (and give the other two vintages a real table) | Every dynamic number, Ask's deficit, Build's target strip, debt/GDP | **3** | ⑤ |
| **R2** ✅ | The five Tier 1 rows with no source URL | 31.8% of the tier's error mass | **3** | ①③ |
| **R3** | H10: a Tailor battery, off CBO's 42 enacted acts and four *Options* vintages | The tier is **22** rows, four fewer than when this was written; users type shapes it does not contain, and it now contains no rate cut at all | **5** | ① |
| **R4** ✅ | The statutory parameter schedule → year-indexed thresholds | Unblocked the branch H2 declared impossible; one row **14.3% → 17.9%**, registered | **3** | ① |
| **R5** ✅ | H3b: corporate — the haircut **refused on the merits**, owner ⑤ executed | Row unmoved at 44.5%; `CORPORATE_APP_MODE` → **`derived`**; two presets moved | **4** | ①② |
| **R6** ✅ | H12: demote the sectoral presets (Wave D) | The 701% row was on Explore; it is now in a named illustrative group, and its target is retired | **1** + owner | ②④ |
| **R7** | The generic base on CBO's own AGI and taxable-income path | 18 of 26 Tier 1 rows when this was written; the battery is now **22** and all four retirements were generic income-tax rows, so re-count before quoting. Every generic surface, regardless | **4** | ① |
| **R8** ✅ | Tariffs: JCT's offset *path* and the HS-10 Section 232 base *(the elasticity ramp **refused on the merits**)* | Five presets moved; `Trade` 43.6% → **80.5%**, registered — and **36.16%** on the four documented rows | **3** | ② |
| **R9** | The SS donut ramp on CBO's own taxable-payroll path | `ss_donut_250k` at 89.2%, a top-six headline | **2** | ② |
| **R10** ✅ | H7: the five expenditure magnitudes (Wave D) | `Expenditures` LOO 40.6% → **43.6%**, a registered regression | **3** | ② |
| **R11** ✅ | H11: the PTC coverage response (Wave D) | `repeal_ptc` 29.6% → **23.6%**, a shipped preset | **2** | ② |
| **R12** | Decompose `MARGINAL_REVENUE_RATE`; give debt service a rate path | The whole dynamic tab, uncalibrated | **4** | — (⑤-adjacent) |
| **R13** | The death channel's *level* half, checked against CapTax | §6.2 item 55's 7.1× factor | **2** | ① |
| **R14** | CBO's own error-measurement discipline for the app's reporting | How every tier is quoted | **2** | ①②③ |
| **R15** | The spend-out vector: confirm (a), then refit on 1,712 accounts (b) | Provenance of the tier's best class | **1 + 3** | ①③ |
| **R16** | `_scorecard_index`: 6.6s on every scored route | The 🔵 complaint that is really a 🟢 defect | **2** | — |

---

### R1 — Transcribe CBO's February 2026 baseline *(3 lane-days)* — ✅ **DONE, PR #159**

> **Outturn.** All three vintages' **economic** paths and **two of three budget** paths are now
> transcribed from `US-CBO/cbo-data` @ `284a9566`, pinned by commit and verified by **SHA-256 per
> file**, with `US-CBO/budgetary-feedback-model` as an independent second reading; owner **⑩** settled
> that both CBO repositories count as "CBO's own table", `cbo-data` preferred. February 2026's
> FY2026–2035 cumulative deficit is **$29,529.1B → $23,143.30B** against CBO's own printed
> $23,143.3B, end-of-window debt/GDP **103.8% → 118.0%**, January 2025 $27,710.6B → **$21,758.3B**.
> `VINTAGE_SOURCING` is now **computed from what the transcription actually contains rather than
> asserted**, which is not a tidy-up: it was **false for two of three vintages**, and February 2026's
> ten-year Treasury note **fell 4.5% → 3.9% where CBO's table rises 4.10% → 4.38%** — a baseline whose
> interest-rate path points the wrong way prices debt service the wrong way. **`real_gdp_growth +
> inflation` is not nominal GDP growth and never was**: the reconstruction added a real rate to a
> *PCE* index, where CBO publishes the nominal path itself.
>
> **Eleven Tier 1 rows moved, ten through the nominal-index channel** — CBO's own FY2023 → FY2025
> nominal growth is **10.70%** where the app assumed **8.99%** — **and an eleventh through a channel
> nobody had listed**: `cbo_opt56_employer_health_income_only` reads a baseline *assumption* rather
> than a level, because the cap's chained-CPI proxy calls `vintage_assumptions(...)["inflation"]`,
> and it improved 13.1% → **12.8%**. *A baseline has two surfaces a score can read, and a lane that
> enumerates one of them will miss rows.* **Eight generic presets moved +2.97% static and two
> corporate presets in dynamic mode only, against a registered prediction of zero** — the first sweep
> scored `PRESET_POLICIES[label]`, a dict rather than a policy, so all 106 rows raised and were
> recorded as errors *identically before and after*. That is PR #119 §7.5 in a second costume, with a
> narrower lesson: **a sweep must fail loudly on a row it could not score.** A Decision 6 caption
> ships, computing its counterfactual from the module's own retained literals so it cannot drift.
> **February 2024 keeps a reconstructed budget path** — `cbo-data` publishes no `ten_year_budget` for
> that edition and June 2024 is publication 60039, a different document whose FY2025 deficit is
> $1,937.9B against January 2025's $1,865.3B — so **its debt/GDP is a mixture and must not be
> quoted**. Nothing in the calibrated tiers moved and the leave-one-out donor matrix is
> byte-identical. `planning/lanes/R1_baseline_transcription.md`.
>
> **Six carry-overs, and the first of them is already closed.** (1) **The CI floor** failed at 20
> against a floor of 22 on this branch, and the lane refused to move it because the workflow's rule is
> downward-only — **R2 resolved it**: the two rows R1 pushed across 25% were the one R2 retired for
> want of a document and the one R2 moved onto CBO's own option, and the merged gate is **15 / 19**.
> (2) **February 2024's debt/GDP is a mixture**; the honest remedies are a fourth `BaselineVintage`
> for June 2024 or a surface that refuses to render a ratio whose halves carry different grades, and
> the first ripples into the URL contract, frozen links and the API. (3) **`base_*` budget levels are
> unread for a transcribed vintage** — `generate()` reads the table, but `base_individual_income_tax`
> and its nine siblings are still the reconstruction, and adopting them forces a base-year convention
> this lane had no reason to take. (4) **The calendar/fiscal anchor**: `_income_base_projection_factor`
> anchors on a *tax* year while this reads CBO's *fiscal* table at both ends, and CBO publishes
> `calendar_<edition>.csv` beside it — about **1.4% on a level**, and R7's question rather than R1's.
> (5) **`scoring_engine.py:345-385`'s docstring quotes stale factors** — 1.3118 and 1.3560 where the
> live figures are **1.3053** and **1.3963**. (6) **Four more CBO datasets are one `--source-dir`
> away** in the pinned clone: `tax_parameters` (R4), `revenue_detail/annual_cy_iit_*` (R7),
> `spending_detail` at 21,769 account-rows (R15b) and
> `budgetary-feedback-model/input/rules_of_thumb.csv` (R12) — and
> `scripts/fetch_cbo_baseline.py`'s pinning, digest-checking and identity-check structure is reusable
> for each.

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

### R2 — The five Tier 1 rows with no source URL *(3 lane-days)* — ✅ **DONE, PR #162**

> **Outturn — one supersession, four retirements, and no module opened.** `illustrative_1pp_all`
> moved to **`.v2`** on CBO publication **58164**, *Options for Reducing the Deficit: 2023 to 2032,
> Vol. I*, Option 13 alternative 1 — **−$1,081.3B** over FY2023–2032, report p. 72, *"Data source:
> Staff of the Joint Committee on Taxation"*, which matches the old target's claimed attribution —
> and the row went **24.5% → 10.5%** on its own tree and **14.3%** merged with R1. The other four were
> **retired with the search recorded**: `warren_ultramillionaire_surtax_3pp` (TPC's *AGI Surtax
> Options* is thirteen tables and **every one is a 10 percent surtax**; and the row's *name* is wrong
> too, since Warren's Ultra-Millionaire Tax Act is a **wealth tax on net worth**, so the reform this
> row scores has never been proposed by anyone), `medicare_surcharge_2pp`,
> `illustrative_top_rate_5pp` and `illustrative_500k_2pp` — the battery's **only rate cut and only
> positive target**, and CBO's *Options* volumes are deficit-**reduction** menus carrying no cut at
> all, in any of four editions.
>
> **Tier 1 went 26 rows → 22, `secondhand` 5 → 0, and the gates re-derived 20/22 → 15/19**, with
> `agi_inclusive_surtax` **22 → 7** and `ordinary_rate_change` **19 → 15**. None of the gate movement
> was discretionary: `test_no_gate_is_looser_than_the_workflow_rule_derives` forces the ceiling at
> `ceil(11.3 × 1.25) = 15` and the floor at the live within-25 count. Every surviving row's
> `model_10yr_billions` is byte-identical, `run_loo.py --donor-matrix` is byte-identical, and all four
> calibrated summaries compare `SAME`. **`medicare_surcharge_2pp` proves the rule rather than bending
> to it**: Treasury's FY2025 Green Book prints the proposal at **1.2 percentage points** and
> **$403,790M**, and the model's −$408.6B sits **1.2%** from it — so adopting the figure would have
> turned the tier's third-worst row into one of its best in a line of diff. It was not adopted,
> because the model applies 2pp where the document applies 1.2pp; restated on Treasury's own rate the
> model reads **−$245.2B against −$403.8B, 39.3% under**, *worse* than the 31.8% the row had been
> reporting. **A retirement that raises the honest error is the cleanest demonstration that the rule
> is about documents and not about means.** Unpredicted: **CBO prices the same 1pp reform three times
> and gets three numbers** — −$884.0B (2020), −$1,081.3B (2022), −$1,185.3B (2024) — where the model
> gives two of them **1.0% apart** against CBO's own **9.6%**, so the pair `illustrative_1pp_all` /
> `cbo_opt45_all_rates_1pp` measures the model's **insensitivity to the decade** rather than two
> independent predictions. Two shipped presets lost their `official_score` and badge and neither
> prints a dollar figure in its label; no app number moved.
> `planning/lanes/R2_tier1_secondhand_targets.md`.
>
> **Five carry-overs, and four of them are R3's.** (1) A **`medicare_surcharge_2pp.v2`** at
> **−$403.8B** on a `rate_change=0.012` shape — and its base question comes with it, because wages
> plus net investment income is **neither SOI column**. (2) A **new TPC case** scoring a **10pp**
> surtax on AGI above $2M against **T19-0037's $585.325B**: the withdrawn row's own base and threshold
> at a rate somebody actually priced. (3) An **`illustrative_1pp_all.v3`** with
> `scoring_window_first_year=2023`, worth most of that row's remaining error. (4) **Tier 1 contains no
> rate cut and no positive target**, and R3's `leg_rev_*` series is where a scored cut with a document
> comes from. (5) **Tier 1 is 22 rows against criterion ①'s 40, and `agi_inclusive_surtax` is down to
> n = 2** — R3 owes this tier **four rows before the per-class bands mean anything again**.

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
it. **The headroom this paragraph assumed is gone, and Wave F spent a little more of it.** R2 took the
pooled gate from `--max-mean-error 20` to **15**, and the live mean is **11.8%** since PR #165's
registered regression, so there are about **3.2 points** of ceiling headroom rather than 5.5 — and
the floor is **19**, met with no slack. Two class ceilings are worth knowing before R3 registers into
them: `ordinary_rate_change` is held at **15** against a live 13.85% (its own re-derivation would now
allow 18, and downward-only forbids taking it), and `agi_inclusive_surtax` is at **7** on a class of
**two**, which is the tightest thing in the gate and the class R3 most needs to refill. The gate is re-derived **after** the rows land, by the
workflow's rule, downward only (owner ⑪ — which is this plan's renumbering of
`HIGH_STAKES_ACCURACY.md`'s ⑩; see §2).

**What R2 hands this lane, and it is now four rows in debt rather than fourteen.** The battery is
**22 rows, not 26**, and `agi_inclusive_surtax` is **n = 2**, so R3 owes Tier 1 **four rows before
the per-class bands mean anything again** and eighteen before criterion ① is met. Four specific rows
come with verdicts already written and none of them may be registered without the manifest's
entry-commit rule:

1. **`medicare_surcharge_2pp.v2`** at **−$403.8B**, Treasury's FY2025 Green Book figure, on a
   `rate_change=0.012` shape — the document's own rate, not the 2pp the retired row applied. **Its
   base question travels with it**: the statutory base is wages plus net investment income, which is
   **neither SOI column**, so the honest outcome may still be a scope verdict rather than a row.
2. **A new TPC case** scoring a **10pp** surtax on AGI above $2M against **T19-0037's $585.325B** —
   the withdrawn Warren row's base and threshold at a rate somebody actually priced. The withdrawn
   row's *name* was wrong as well as its number, so this is a new case and not a `.v2`.
3. **`illustrative_1pp_all.v3`** with `scoring_window_first_year=2023`, worth most of that row's
   remaining 14.3% — and read beside R2's own finding that the pair `illustrative_1pp_all` /
   `cbo_opt45_all_rates_1pp` measures **insensitivity to the decade** rather than two independent
   predictions, which is the reason to read CBO's other two vintages of the same option before
   registering them.
4. **A rate cut.** Tier 1 contains **no rate cut and no positive target** since
   `illustrative_500k_2pp` was retired, so the tier does not test the model in the direction a Tailor
   user most often asks about. The `leg_rev_*` series above is where a scored cut with a document
   comes from — `leg_rev_tcja`, `leg_rev_egtrra_01`, `leg_rev_econ_recovery_81` — and that is a
   stronger reason to run this lane than the size condition is.

---

### R4 — The statutory parameter schedule *(3 lane-days)* — ✅ **DONE, PR #165**

> **Outturn.** The impossibility is refuted and the table is transcribed — **5,531 rows**, three
> vintages, SHA-256 pinned, from CBO publication 53724 — with the June 2024 vintage carrying the
> 2026 revert in full. **The revert is not a uniform shift**: joint floors fall 3.5% while single
> floors rise 15.9% and head-of-household floors rise **65.5%**, which is why this lane needed PR
> #127's filing-status split to exist first. `Policy.scores_by_year()` ships with two implementers,
> closing §6.2 item 27 on its own terms, and `TaxPolicy.threshold_indexation` names an assumption
> nobody could read off the code (`"income"` default / `"statutory"` / `"nominal"`).
> `cbo_opt45_top4_brackets_2pp` **14.3% → 17.9%**, landing on its band to the cent, and **the
> direction stated below is backwards — corrected in place, with attribution**: H2 shipped the base
> projection after that sentence was written and the row crossed its target on that step, so the
> schedule takes it further **over**, by the difference of two terms (deflating the boundary
> −$68.4B, the CY2026 reversion +$48.1B). **The arithmetically wrong variant scores four times
> better (3.61% against 17.86%) and is written into the row's `known_limitations` rather than
> taken.** Zero presets, zero Tailor rows, both calibrated tiers and the donor matrix all
> byte-identical; the two bracket-1 rows returned today's figure to the cent, which is what takes
> the new code path end to end. Owner items: the **Tailor `&index=` control** (§6.2 item 78, worth
> 33.3% on an ordinary shape) and **`Top Rate to 45%`'s $609,350**, which is `tp_bracket_7_single`
> for CY2024 exactly (item 79). **148 of the 150 transcribed variables are wired to nothing** and
> deliberately so (item 77). And a process finding worth more than the lane: it **failed CI's
> blocking mypy gate on all four jobs having never run it**, because one keyword-only parameter on a
> base method broke six overrides in five modules it does not own — that command is now in
> `CLAUDE.md`'s Commands section.


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

**Pre-registrable expectation — and the direction below is wrong; corrected 2026-09-11 after PR
#165 measured it.** The registered regression happened, at **14.3% → 17.9%**, but it went further
**over**, not further under: H2 shipped the base projection after this sentence was written and the
row crossed its target on that step, so *the direction was true of the tree it was written about and
false of the tree it was executed on*. The lane's own prediction, measured by a hand prototype that
reproduced the engine to the cent before anything was written, is the one that held. **The argument
this leaves behind is to pre-register a measured band rather than inherit a stated direction.**
*(As written:)* **A registered regression on at least one row**, direction already
known: H2 states the year-indexed threshold takes `cbo_opt45_top4_brackets_2pp` (14.9%) *further
under*. The lane predicts a band for that row and reports the movement, not the attainment. PR
#127's precedent stands — three of four rows got worse and the split was still necessary.

---

### R5 — H3b: corporate, with CBO's own loss-firm haircut *(4 lane-days)* — ✅ **DONE, PR #166**

> **Outturn — the haircut was the wrong mechanism, and the lane says so with the arithmetic rather
> than with a judgement.** It is real, and it is now transcribed with its commit SHA and line
> numbers; it is also a **rate** adjustment inside a user-cost-of-capital expression, while the
> derived path multiplies a **base** that is CBO receipts ÷ the statutory rate — and receipts are
> what loss-making firms' zero tax already produces. Three independent readings agree, one of them
> CBO's own: `Create_Tax_Data.prg:172-175` **divides `dmyrevx` back out** where the other input
> already carries it, *"to avoid double-counting"*; `corporate_yield_reconciliation.py`'s own
> docstring says the denominator every published marginal share is measured against "already nets
> credits, **NOLs**, shifting"; and the module's own SOI file measures those losses at
> **8.69–11.58%** of the pre-NOL base (10.25% mean) against CBO's 12.81%. So §1.1 shipped a
> **transcription and a refusal**, with the decision test run *before* §1 was written and §3.1
> predicting in advance that bands 1, 3 and 5 would miss **by not moving** — which they did.
> **§1's own description of the constants is wrong and is corrected above**: 0.85 is loss-making
> firms alone and 0.80 is that factor times the nonprofit share of nonresidential investment
> (0.85 × 0.94 = 0.799); `grep -rn dmyrev source_code/` returns no third series, so "by sector if
> the receipts detail supports it" cannot be followed — **there is no sector split to apply**, and a
> lane taking the brief literally would have spent its days looking for data that does not exist.
> The credit channels were **bounded, not priced**: §38(c)'s carryforward stock is **$124.47B** (IRS
> Publication 5108, TY2022, pp. 164 and 166) and §904's a labelled **$78.02B residual**, but the
> share that would price either needs SOI's excess-credit tables, which exist for **TY2010 only**;
> CAMT is blocked on a TY2023 Complete Report that does not exist. **Owner ⑤ was then executed on a
> rule fixed before §1 was implemented**, requiring **both** metrics to favour `derived` with no
> tie-break: mean error over the three published corporate targets, **61.43% against 62.75%**; and
> the +7pp estimator-span position, **inside** against **$47.27B outside and larger than all four
> houses**. `CORPORATE_APP_MODE` is now **`derived`**, with three qualifications in the module
> docstring — it wins the mean while **losing two rows of three**, **neither mean is small**, and
> **nothing was retuned** (1900.0 either side, asserted by a test). Presets: **Biden Corporate 28%
> −$1,397.21B → −$1,310.92B**, **Trump Corporate 15% +$1,491.76B → +$1,562.75B**. Scorecard:
> `biden_corporate_28_fy2022` **62.9% → 50.7%**, `trump_corporate_15` **121.6% → 129.6%**,
> `biden_corporate_28` 3.7% → 4.0%. Two findings past the lane: **`_estimate_passthrough_shift` is
> inert in every scored case**, and **`reported` mode's answer does not depend on which decade you
> ask about** — which only the flip could reveal, and which is worth $18.30B. **§6.2 items 80 and
> 81 carry what is left, and item 81 is the honest hand-off: this row's remedy is spent and what it
> needs is a second out-of-sample case, not another mechanism.**


**Stakes and error.** `cbo_opt64_corporate_rate_1pp` at **44.5%** is Tier 1's largest single row and
**11.8% of its mass** — **17.4% since Wave E**, not because it moved but because the battery around it
shrank from 26 rows to 22 — and it is a class of one, so the CI ceiling for `corporate` is **56**.
`trump_corporate_15` at **121.6%** is the worst headline reconstruction outside pharma and sits on
Explore and Build.

**Mechanism — and this paragraph is wrong about what the constants are; corrected 2026-09-11 after
PR #166 read the source.** They are published and they are derived from SOI, but **0.85 is
loss-making firms alone (nonfinancial corporates) and 0.80 is that same factor further reduced by
the nonprofit share of nonresidential investment** (0.85 × 0.94 = 0.799) — not a financial /
non-financial pair, and `grep -rn dmyrev source_code/` returns no third series. **There is therefore
no sector split to apply**, and a lane following the brief's "by sector if the receipts detail
supports it" literally would have spent its days looking for data that does not exist. More
fundamentally, the ratio adjusts a **statutory rate** inside a user-cost-of-capital expression while
this module multiplies a **base** that is CBO receipts ÷ the statutory rate — receipts already carry
loss firms' zero tax — so it was **transcribed and refused**, with CBO's own
`Create_Tax_Data.prg:172-175` dividing the same factor back out *"to avoid double-counting"* as the
precedent. *(As written:)* `CORPORATE_PER_POINT_YIELD.md` §4b established that this model's implied marginal
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
**Unchanged by Wave F too, and it is still the largest thing in the tier.** `CORPORATE_APP_MODE` is
now **`derived`** (PR #166) — describe the corporate app default that way — but the *row* did not
move: `cbo_opt64_corporate_rate_1pp` is unmoved at **44.5%** and carries **17.2% of Tier 1's whole
error mass** in a class of **one**, up from 11.8% before the battery shrank. `HIGH_STAKES_ACCURACY.md`
now has no open lane. **Its remedy is spent** — haircut refuted, credit channels bounded and
unpriceable, behavioural parameter already the only published one — so what this class needs is a
**second out-of-sample row** (§6.2 item 81), which belongs to R3.

**Pre-registrable expectation — outturn: bands 1, 3 and 5 missed by not moving, and §3.1 of the lane
said in advance that they would.** `cbo_opt64` **44.5%** against 30 ± 8; `trump_corporate_15`
**129.6%** against 90 ± 20; the marginal share **80.83%** against "falls toward 55–80%". Only band 2
landed, at **−50.7%** against −45 ± 10, **and it is not credited to the mechanism** — the row moved
because owner ⑤ changed which mode the scorecard scores, and had the flip not shipped it would read
−62.9% and miss like the others. That ordering is the reason the misses are reportable rather than
embarrassing: the applicability test ran, then the prediction was written, then §1 was implemented.
*(As written:)* H3b's existing bands, unchanged: `cbo_opt64` 44.5% → **30 ± 8**;
`biden_corporate_28_fy2022` −62.9% → **−45 ± 10**; `trump_corporate_15` 121.6% → **90 ± 20**.
`biden_corporate_28` is fitted and moves in `derived` only. **Owner ⑤ must be answered first**:
H3a's measurement — `derived` lands *inside* the published span at the +7pp step every shipped
preset uses and outside it at +1pp — is a second independent reading pointing the same way as PR
#122's Decision 1 reversal, and it goes stale (§6.2 item 53).

---

### R6 — H12: demote the sectoral presets *(1 lane-day + owner ⑨)* — ✅ **DONE, PR #158**, *with owner ④ in PR #160*

> **Outturn — both instruments were used and neither deleted a row.** Owner ⑨ was taken: all five
> sectoral presets sit in a last-ordered group named **`Illustrative - unfitted reconstructions`**,
> with a group note and each preset's live, render-time error, and **every scored artifact is
> byte-identical** — the holdout JSON, the dashboard, 52 presets × two engine modes, 44 badges and
> `build_catalog`'s insertion order. Nothing left a registry, so `?preset=`, `/build?policies=` and
> frozen links still score. Owner ④ was then taken separately in PR #160, retiring the two pharma
> `model_estimate` targets — so `Pharma` went **3 rows at 277.8% → 1 at 39.0%** and the reconstruction
> tier's `model_estimate` count **2 → 0**, while the anti-gaming arithmetic prints on the adjacent
> line: **40 at 55.5%** with both withdrawn rows folded back at the error they carried on the day they
> were withdrawn, above which the smaller **38 at 37.5%** cannot be quoted without skipping a line.
> Two findings: **demoting a group can delete an area** (Explore's `Drug Pricing` vanishes rather than
> empties, so the selectbox stays at 14), and **the real default package is the values composer,
> which selects `irs-enforcement-double` into all five archetypes** — measured and left alone, because
> excluding it would move five package totals. That last one is a live carry-over.
> `planning/lanes/HSD_h12_illustrative_group.md`, `planning/lanes/LEDGER_decisions_3_4.md`.

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

**Stakes.** 18 of 26 Tier 1 rows and every generic surface. **Re-read after Wave E**: the battery is
22 rows, and the AGI-inclusive class reads **5.15% on n = 2** rather than 17.57% on n = 6 — R2 did not
remove the target disputes so much as remove the rows carrying them, and R1's transcribed nominal path
then took the two survivors to 7.9% and 2.4%. **That is not this lane's stakes falling.** A class of
two cannot discriminate between a base defect and a lucky pair, the generic base is read by every
surface a user touches whether or not a benchmark scores it, and the rows R3 registers will be scored
on whatever base this lane leaves in place. Run it for the surfaces and for the rows that do not exist
yet, not for the class mean.

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

### R8 — Tariffs: the offset path, the HS-10 base, the elasticity ramp *(3 lane-days)* — ✅ **DONE, PR #164**

> **Outturn — two of the three moves landed, the third is refused on the merits, and the headline
> finding is that the base this repository declared a ceiling was 2.04× too small.** Move 1: the
> offset is now **JCT's own published year path**, 0.244 (2025) → 0.241 (2035), read as the window
> mean over the policy's own years — and it reaches a year-blind engine call **exactly**, because
> `TariffPolicy` is in no growth handler and has no `soi_base_tax_year`, so the gross is flat and
> `Σ_t g(1−o_t) = n·g·(1−ō)` is an identity a test asserts rather than a docstring claims. Move 2:
> the Section 232 bases are aggregated at **HS-10** over CBO's own Census file at CBO's own article
> lists at CBO's own content shares — steel **$108.4B → $219.4B**, autos **$198.5B → $555.0B**.
> **The declared bracket was wrong at both ends**: 558 of `alum_steel.csv`'s 1,180 *primary* lines
> are in HS-73, which the "floor" of HS-72+76 excluded, while the derivative annex lives in chapters
> **82–95** — machinery, furniture, appliances — which HS-73 does not contain at all. *A bracket
> built from the wrong dimension is not conservative in either direction*, and the tell is that the
> ordering of collected duties **flips** (HS-73 5.63% vs HS-72+76's 3.06%; CBO's derivative annex
> **3.87%** vs its primary list's **4.64%**). The auto carve-out was **4.5× too large** and
> `tariff_scoring_inputs.csv` had described the defect correctly in its own source note for a wave.
> **Move 3 is refused rather than deferred**: CTAM's `boehm_elasticities.csv` is normalised to 1.0
> at t+10 and *multiplies* 110 NAICS-4 substitution elasticities, so it is a **time shape on a CES
> nest**, not a scalar import-demand elasticity — the tax memo's §3 row 11 described it wrongly and
> is corrected. Every one of the five scores landed on its §3 prediction **to the cent**, which is
> what the non-importing reimplementation was for. `Trade` **43.6% → 80.5%**, a pre-registered
> regression, and **three quarters of it is `steel_tariff_25`** against a target that is untraceable
> and examined-and-left twice — **the number to quote is the four documented rows, 35.66% →
> 36.16%**. The one external control was declared in advance and predicted to fail: Tax Foundation's
> 50% steel regime at −$341.4B against the module's −$190.95B on the new base and −$94.32B on the
> old — the gap halves and does not close, and the residual is **item 73's unsourced trio**, which
> at a 46pp increment asserts imports fall **62% in year one**. Five presets moved with a caption
> that now prints the offset to one decimal and, for the two Section 232 presets, names the base.


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
3. ~~**The elasticity as a path.**~~ — **REFUSED on the merits by PR #164, not deferred for time.**
   `boehm_elasticities.csv`'s `final_path` is **not an import-demand elasticity**: `code/model/
   CES_time_path.py:14` normalises it to 1.0 at t+10 and `:48-50` *multiplies* 110 NAICS-4
   foreign-to-foreign substitution elasticities by it, with nesting divisors 1.0 / 1.5 / 2.0 at
   `:53-55`. It is a **time shape on a CES nest**, and dropping it into `-0.997`'s slot would be a
   category error; taking it properly means building the nest. *(As written:)* `trade.py:148`'s
   single `-0.997` against CTAM's `boehm_elasticities.csv` (0.5517 → 2.0408 over 2025–2035) and 110
   NAICS-4 substitution elasticities. Note in the lane doc that −0.997 is Tax Foundation's own
   choice (FF861 p. 4), so this swaps one published estimator for another rather than moving toward
   truth. **The tax survey memo's §3 row 11 describes the same file as a "time-varying import-demand
   elasticity" and is corrected there.** What the module's residual actually is has been measured
   instead: §6.2 item 73's unsourced trio, worth a **62% year-one import collapse** at a 46pp
   increment and the whole of the gap in R8's one external control.

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

### R10 / R11 — H7 and H11, expected residuals *(Wave D)* — ✅ **DONE, PRs #157 and #155**

> **Outturn — R10 was a regression and R11 was not, and both were registered in advance.**
> **H7 (PR #157)** sourced two of the five magnitudes through a new per-reform `OFFSET_MAGNITUDES`
> table and left three unsourced with their searches recorded: mortgage **0.10 → 0.14502762**, which
> is `1 − 61.9/72.4` from Poterba & Sinai's own "about 85 percent" (NBER WP 14253), and the
> charitable benefit-rate ceiling **0.40 → 0.22077987**, the module's own identity at `c = 0.28` with
> **ε = 0.5 from CRS R40518** as its only new constant. The parameter is **a share of the reform's
> static revenue effect, not a price elasticity** — the plan's own "nearer 18%" is not reproducible
> and the identity gives 22.1%, while the shipped 0.40 inverts to a price elasticity of **0.906**,
> above CRS's published high of 0.79. `cap_charitable` **0.3% → 12.5%**, `eliminate_mortgage`
> **26.5% → 30.2%**, `Expenditures` LOO **40.6% → 43.6%** and the suite **36.5%**; the hazard this
> entry named held, because **no fitted constant was retuned**. Instead a fifth exit from the fitted
> tier appeared: `create_cap_charitable_deduction`'s annual had been fitted so `static × (1 + 0.40)`
> lands on the target, so once 0.40 is sourced it is fitted to a quantity the module no longer
> computes — reclassified under PR #119's rule, **fitted 16 → 15**. Shipped preset **📋 Cap
> Charitable Deduction −$200.6B → −$174.9B** (−12.80%), badge Excellent → Acceptable.
> **H11 (PR #155)** replaced the transferred **19.28%** with four channels priced per coverage
> person-year from CBO/JCT 60437 — ESI plus mandate penalties **$2,971.43**, Medicaid/CHIP
> **$4,200.00**, BHP/§1332 and other **$57.97**, uninsured **$0.00** — against a coverage change from
> the scored vintage's own 51298 Table 1. The window share is **12.3211%**, `repeal_ptc`
> **29.6% → 23.6%**, inside the registered band, and the shipped preset **🏥 Repeal ACA Premium
> Credits −$774.1B → −$840.8B**. **The aggregate had been booking a Medicaid *saving* as a cost** —
> CBO's $80B contains **+$21B of Medicaid and CHIP** — and the denominator was 61% wrong with both
> halves printed by CBO, an extension's marginal enrollee at **$5,370/yr** against the average
> subsidized enrollee a repeal removes at **$8,671/yr**. **Both flattering corrections were declared
> and declined**, and the falsification held: the June 2024 gross demonstration still returns
> **−$1,143.0B, 0.09%** from CBO's own $1,142B, now pinned by a test.
> `planning/lanes/HSD_h7_expenditure_magnitudes.md`, `planning/lanes/HSD_h11_ptc_coverage.md`.

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

**Depended on R1, and R1 has landed (PR #159)**: the debt-service path was being applied to a deficit
path **27.6% too large**, and it now reads CBO's own transcribed table at **$23,143.30B**. Two of this
lane's own inputs came with it — `budgetary-feedback-model/input/rules_of_thumb.csv` is in the pinned
clone, one `--source-dir` away — and one caveat travels too: February 2024's budget lines are still a
reconstruction, so a debt-service path priced on that vintage is priced on a mixture.

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
| **CTAM's `boehm_elasticities.csv` as `import_price_elasticity`** | **Rejected on the merits by PR #164 — category error.** `CES_time_path.py:14` normalises the column to 1.0 at t+10 and `:48-50` *multiplies* 110 NAICS-4 foreign-to-foreign substitution elasticities by it. It is a **time shape on a CES nest**, not a scalar import-demand elasticity, and taking it means building the nest. The tax survey memo's §3 row 11 said otherwise and is corrected |
| **CBO's loss-firm haircut (0.80 / 0.85) applied to the corporate base** | **Rejected on the merits by PR #166 — wrong object, and the repository's own files said so three times.** It adjusts a *statutory rate* in a user-cost expression; the derived path multiplies a base that is CBO receipts ÷ the rate, which already nets loss firms. CBO itself divides the factor back out where the other input carries it. Also **not** a financial / non-financial pair — §1 R5 is corrected |
| **The steel "floor" base, which would have scored `steel_tariff_25` at 1.7%** | **Refused, twice, and now doubly so.** PR #150 declared and refused it; PR #164's own test asserts the score stays **above $200B** — nowhere near the untraceable −$60B — with a message saying that drift toward that target is a reason to revert the lane |
| **Any constant chosen because it lands a row** | **Forbidden, unchanged.** A lane that adds a constant reproducing a benchmark has failed regardless of the error it closes |

---

## §2 — Waves

Files are disjoint within a wave, so lanes run as parallel agents in worktrees. **Waves A–D and F
are done and Wave E is two lanes of three.** D closed as PRs #155, #157 and #158, with its two owner
decisions taken separately (#160, #161); E's re-scoping around **R1** and **R2** was the right call
and both landed (#159, #162), leaving **R15a** — the spend-out confirmation — as the wave's one open
lane; **F closed as PRs #164, #165 and #166**, with a provenance-pin fix on R1 (#167) beside it.
**Eight lanes of sixteen are therefore closed**: **R1**, **R2**, **R4**, **R5**, **R6**, **R8**,
**R10**, **R11**. Owner decisions ③, ④, **⑤**, ⑧, ⑨ and this plan's ⑩ are taken — ⑤ in
PR #166, which also closes `HIGH_STAKES_ACCURACY.md`'s last open lane, so **that plan now has none**.
**Wave G is next**, and its two decisions (⑪ and ⑭) are still open.

**Wave F's own lesson about wave structure is worth carrying to G.** Its three lanes were disjoint in
files as designed, and **two of the three moved nothing the third touched** — R4 moved one Tier 1 row
and no preset, R5 moved two presets and no Tier 1 row, R8 moved five presets and no Tier 1 row — so
every before/after in §5.11 of `MODELING_IMPROVEMENT.md` is attributable to a single PR. That is the
property Wave B lost when H2 and H2b landed together, and it is worth designing for rather than
hoping for.

| Wave | Lanes (parallel) | Files | Days | Owner decisions needed **before** the wave opens |
|---|---|---|--:|---|
| **D** ✅ | **H7** expenditures · **H11** PTC · **H12** sectoral demotion | `tax_expenditures_core.py` / `ptc.py` / `app_data.py` + `explore.py` | 6 | **⑧ taken (PR #161)** — a `SaltCapBaseline` with three named cap paths from IRC §164(b)(6)–(7) as amended by P.L. 119-21 sec. 70120, so the app scores current law while each benchmark scores its own document's baseline; **both rows unchanged**, the shipped preset **+$1,155.6B → +$740.3B**. It became its own lane rather than a joint call inside H7. **⑨ taken (PR #158)** — no; all five move to a named illustrative group with their live error printed, and nothing leaves a registry |
| **E** ◑ | **R1** baseline transcription ✅ · **R2** Tier 1 provenance ✅ · **R15a** spend-out confirmation *(open)* | `baseline.py` + `constants.py` + data block / `validation/preregistered.py` + `cbo_scores.py` / `data_files/spending/` + docs | **7** | **③ taken (PR #160)** — the window rule is applied to the second row: `iija_2021_discretionary.v3` on FY2022–2031, target unchanged, **18.2% → 0.28%** and its class 13.4% → **7.4%**; read that residual as two terms nearly cancelling rather than as a measurement. **⑩ taken (PR #159)** — **both** `US-CBO` repositories count as "CBO's own table", with `cbo-data` preferred, and `VINTAGE_SOURCING` is computed per line rather than asserted. **R15a is the wave's one open lane.** *Note: this ⑩ is not `HIGH_STAKES_ACCURACY.md`'s ⑩, which is H10's gate re-derivation and is still open — this plan renumbers that one **⑪** (Wave G below), and the collision is recorded in both documents rather than quietly resolved* |
| **F** ✅ | **R4** parameter schedule ✅ · **R5** corporate mechanism ✅ · **R8** tariffs ✅ | `policies_core.py` + `cbo_tax_parameters.py` / `corporate.py` / `trade.py` | **10** | **⑤ taken (PR #166)** — yes: on a rule fixed before the lane implemented anything, requiring **both** metrics to favour `derived` (61.43% vs 62.75% on the three published corporate targets; **inside** the four-house span at +7pp vs $47.27B outside). `CORPORATE_APP_MODE` is now `derived`, two presets moved, nothing was retuned and no readiness exemption was added. R4 and R8 needed no decision and took none. *Note R4 did **not** open `amt.py` or `credits.py`: it transcribed all 150 CBO tax parameters and wired **two**, because each of the rest belongs to a module with calibrated benchmarks (§6.2 item 77)* |
| **G** | **R3** Tailor battery · **R9** SS donut ramp · **R13** death-channel level | `validation/preregistered.py` + `cbo_scores.py` + `policy_classes.py` / `payroll.py` / `data/capital_gains.py` | **9** | ⑪ **New:** R3 registers ~15 rows; confirm the CI gate is re-derived **after** they land, by the workflow's rule, not before. ⑭ **New:** the death-channel *level* (§6.2 item 55) — a level nobody may change by implication, the same class as ⑥ |
| **H** | **R7** generic base · **R12** dynamic constants · **R14** reporting shape | `policies_core.py` + `scoring_engine.py` / `constants.py` + `macro_adapter_frbus.py` / `cold_holdout.py` + `credibility.py` | **10** | ⑫ **New:** Decision 3 — is the capital-gains elasticity at large steps re-openable now that a second agency publishes a reference rate? (R13's measurement is the input; it is the single largest remaining capital-gains term.) ⑬ **New:** does a Build option show model output **beside** the list price, or carry a label saying it is one? Criterion ④ is met either way and the choice is the owner's |
| **I** *(deferred)* | **R15b** spend-out refit · **R16** scorecard performance | `scripts/fit_outlay_rates.py` / `preset_validation.py` + `data/capital_gains.py` | **5** | — |

**Total: 41 lane-days beyond Wave D's 6 — of which R1's 3, R2's 3 and Wave F's 10 are spent**,
leaving **25**, one of which is R15a and the remainder of Wave E. Wave D's own 6 are spent in full.

### Serial constraints, stated

1. **R1 before anything that reads a level. ✅ Satisfied (PR #159).** R12's debt-service path was
   being applied to a deficit path **+27.6% too large**; it now reads CBO's own transcribed table,
   **$23,143.30B against CBO's printed $23,143.3B**. R9's window and Build's target strip both read
   the baseline and both moved. **Two residues travel to the lanes downstream**: February 2024 keeps
   a *reconstructed* budget path, so that vintage's debt/GDP is a mixture and must not be quoted; and
   `base_*` budget levels are still the reconstruction even for a transcribed vintage, which is a
   base-year convention nobody has settled.
2. **R4 before R3 registers any year-indexed row. ✅ Satisfied (PR #165).** The engine now expresses a
   statutory bracket boundary per year per filing status, through `Policy.scores_by_year()` and
   `TaxPolicy.threshold_indexation`, so R3 may register such a row — **under R4's own
   `STATUTORY_BRACKET_SCHEDULE_RULE`**, which is the part that travels: a threshold is read from the
   schedule *if and only if* the row's own source describes the boundary as a statutory ordinary-
   income bracket, and **numeric coincidence is not evidence** ($20,000 *is* `tp_bracket_2_hoh` in
   CY2033 and CBO's Option 46 still means $20,000). R3 should also read the carried-over question
   with it: the `"nominal"` indexation is built and measured and is **not** the default, so a row
   whose source states a plain dollar amount registers against today's `"income"` behaviour unless
   somebody decides otherwise (§6.2 item 78).
3. **R4, R7 and R3 may not share a wave.** All three reach the generic income-tax path, and H2/H2b
   are the precedent for what happens when two base changes land together: the endpoints stopped
   being attributable and the plan's own §1.3(c) had to be corrected in place. One base change per
   wave. **Wave F honoured this and it paid**: R4 was the only base change in it, so its 3.55 points
   on `cbo_opt45_top4_brackets_2pp` decompose exactly (−$68.4B of deflation against +$48.1B of the
   CY2026 reversion) and nothing else in the tier moved by a cent. **R7 is now the next base change
   and belongs alone in its wave**, as Wave H has it.
4. **R2 before R3. ✅ Satisfied (PR #162), and it cost more than the ordering implied.** All five
   untraceable targets are resolved — one superseded, four retired — so `secondhand` is **0** in
   Tier 1 and every surviving row is a `line_item`. But the battery is **22 rows, not 26**, so R3 now
   starts four rows further back than this plan assumed, and R2's verdicts are the standard its rows
   are held to in both directions: a target that cannot be opened does not get registered, and a
   figure that lands the row is not a reason to adopt it.
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
five untraceable targets, would inherit both. **Wave E closed both of those particular objections and
opened a third**: the baseline is now CBO's own table and the battery's five untraceable targets are
gone, but the battery itself is **22 rows**, and calibrating a microsimulation against a validation
tier that lost 15% of its cases — including its only rate cut — would inherit *that*. R3 is the
prerequisite this paragraph should now name.

---

## §4 — Process

Unchanged from `HIGH_STAKES_ACCURACY.md` §3's six rules, plus five the surveys and this tree add.

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
5. **The per-class gate is a floor, not a summary — Wave E moved six of the ten thresholds, none of
   them by choice, and Wave F moved none.** `cold_holdout.py --max-class-mean-error` is wired at
   `validation-dashboard.yml` with eight ceilings, which now read
   `agi_inclusive_surtax=7 ordinary_rate_change=15 capital_gains=24 corporate=56
   enacted_law_spending=10 discretionary_spending=6 payroll=10 tax_expenditure=16` — beside the
   pooled **`--max-mean-error 15 --min-within-25pct 19`** and the LOO `--max-mean-error 75`. It fails
   three ways: a class over its ceiling, a class the battery contains with **no** ceiling, and a
   ceiling naming a class that does not exist. **Ownership, because a threshold with no owner drifts**:
   `agi_inclusive_surtax=7` and `ordinary_rate_change=15` are R2's (PR #162), `tax_expenditure=16` is
   R1's, `enacted_law_spending=10` is owner ③'s (PR #160), `capital_gains=24` is Wave C's, and the
   other three are unchanged. `ordinary_rate_change=15` is **tighter than its own re-derivation, now 18**
   (its class mean is 13.85% since PR #165's registered regression), and stays, because the rule is
   downward only — the second wave running in which it has been held below what the rule would allow. **The pooled floor fell 22 → 19 because the battery
   shrank, not because anything regressed** — the repository's own meta-test
   (`min_within <= within_25pct`) failed on it before CI did — and it is met with **no slack**, so R3
   adds rows against a gate with about 3.4 points of ceiling headroom rather than 5.5. R3 adds rows to
   existing classes and may add a class; **either way the gate is re-derived after the rows land,
   downward only.** The LOO ceiling is still **75 against a live 36.5%**, roughly 2× — §6.2 item 54,
   and it should be re-derived in the same pass.
6. **What the docs sync after each wave must carry.** PR #152's shape is the template — ten files:
   `CLAUDE.md`, `README.md` ("Model maturity" and the validation tables), `docs/CHANGELOG.md`,
   `docs/METHODOLOGY.md`, `docs/VALIDATION.md`, `planning/HIGH_STAKES_ACCURACY.md` (outturn boxes in
   place, corrections attributed), `planning/MODELING_IMPROVEMENT.md` (§5.x outturn + §6.2 items
   struck and opened), `planning/NEXT_STEPS.md`, `.github/workflows/validation-dashboard.yml` (the
   gate, re-derived by rule), `tests/test_ci_workflow.py`. **Add this document to that list** — its
   §0 table is a live scoreboard and a wave that does not update it has not reported. **Wave F adds a
   twelfth: any survey memo a lane contradicted.** R8 refuted `memos/CBO_GITHUB_SURVEY_tax.md`'s
   description of `boehm_elasticities.csv` and R5 refuted its description of CBO's loss-firm
   constants; both are corrected in place with attribution, because a survey memo is what the *next*
   lane reads before it opens a file. **And the sync measures rather than transcribes**: R8's own
   outturn quotes its five app presets at **0.9×** the figures the app prints, because its scratch
   sweep did not move the policy onto the app window before scoring it — so a sync that copied the
   lane doc would have published a nine-year total under a ten-year heading. Re-run the preset sweep
   through `composer._build_preset_policy` → `_scorer_for`, which is the path
   `tests/test_no_headline_without_row.py` uses and therefore the path the app is pinned to.
7. **Report movement, not attainment.** Four of Wave 7's seven lanes, two of Wave C's and two of
   Wave F's were pre-registered regressions that landed as regressions, and lanes in Waves C and F
   found the plan's own diagnosis wrong — **four times now**: §1.2 row 6 and §3 H5's "applied by size
   class" (Wave C), §1 R4's stated *direction* and §1 R5's description of CBO's own constants (Wave F).
   Each is corrected in place with attribution rather than quietly. A lane that reaches a better tier
   mean by making rows worse reports both; a lane whose own falsification condition fires says so and
   tunes nothing. **And a lane may report a mechanism it sourced and then refused**, which is what R5
   did — a refusal with the arithmetic attached is a result, not a shortfall, provided the applicability
   test was run and written down *before* the mechanism was implemented.
8. **Run the blocking type-check gate locally, because it is the one gate no other local command can
   stand in for.** `.github/workflows/tests.yml` (~lines 112–115) runs
   `mypy $(grep -v '^#' mypy.gate.txt | grep -v '^[[:space:]]*$')` as a **blocking** step over a
   green-core allowlist, and PR #165 passed pytest, ruff, `check_readiness.py` and every accuracy gate
   locally while failing that step on **all four CI jobs** — one keyword-only parameter added to a base
   method broke six `[override]`s in five modules the lane did not own, five of them inside the
   blocking allowlist. The cheap fix (widen the five overrides) was also the one reaching furthest
   into other people's files; the right one was to freeze the base signature and add a separate
   inherited method beside it. **A lane's local gate list must name `mypy.gate.txt` beside `ruff` and
   `pytest`**, and the command is now in `CLAUDE.md`'s Commands section. The general form is the one
   this repository keeps relearning: *a repository whose CI has a blocking step no lane brief mentions
   will keep discovering it the same way.*

---

*Measurement provenance for §0 and §1: `ANTHROPIC_API_KEY= python scripts/cold_holdout.py --json`,
`python scripts/run_validation_dashboard.py`, `python scripts/run_loo.py --donor-matrix` and a direct
`CBOBaseline(start_year=2026, vintage=BaselineVintage.CBO_FEB_2026).generate()`, all run on this
branch — and re-run on merged `main` on 2026-09-11 for §0's table, §2's wave rows, §4's rule 5 and the
outturn boxes. The 2026-09-11 baseline figures are CBO's own transcribed table rather than the
module's reconstruction, so `CBOBaseline(...).generate()` is now reading a document rather than
rebuilding one. Health reports `degraded` on `runtime` only — Python 3.14.0 against a supported
`>=3.10,<3.14` — which is a local-environment state, not a tree state.*
