# High-stakes accuracy plan — the numbers people actually quote

*Written 2026-09-06 against `main` @ `931037c` (Waves 1–7 complete; PRs #126–#137 merged).*
*Every figure below is from one of four runs on that commit — `python scripts/cold_holdout.py --json`,
`python scripts/run_loo.py --donor-matrix`, `python scripts/run_validation_dashboard.py`, and a
53-preset sweep through `composer._build_preset_policy` → `_scorer_for` → `score_policy` — or from a
`file:line` in the tree. Nothing here is recalled.*

`MODELING_IMPROVEMENT.md` ranked work by **error mass**. That was the right yardstick for seven waves
and it is the wrong one now. The tier means are respectable — Tier 1 at **15.0% over 26**, LOO at
**30.1% over 18** — and the largest remaining errors sit on rows nobody quotes. Meanwhile the number a
Hill staffer copies out of the app for a 2pp surtax above \$400,000 is **−\$166.5B on Tailor and
−\$314.6B on Ask**, for the same policy, on the same commit, and the scorecard validates only the
second one.

This plan re-ranks by **who reads the number**. It supersedes §6.2's *sequencing*, not its rules: §1's
six principles, §4's prohibitions, Decisions 1 and 6, the pre-registration manifest and the CI gate's
own re-derivation rule all continue to bind, and every carry-over item this plan does not schedule
stays open in §6.2.

---

## 1. The high-stakes list

### 1.1 The criterion

A number is high-stakes when all three hold:

1. **Salience** — a journalist, Hill staffer, instructor or researcher would quote it *as a score*,
   not as an illustration. TCJA extension, a corporate rate, the SALT cap. Not "Carbon Tax \$25/ton".
2. **Magnitude** — |10-year| is large enough that being wrong by 30% is a policy-relevant error.
   Everything below is ≥ \$150B; most are ≥ \$500B.
3. **Reach** — how many surfaces produce it. Four exist and they do not agree:
   **P** preset headline (Explore, Build checklist), **T** Tailor custom, **A** Ask hypothetical,
   **B** Build package total. **B is different in kind**: `deficit_target.build_catalog` is driven by
   `CBO_SCORE_MAP`'s `official_score` — the Build page quotes *list prices*, not model output
   (`fiscal_model/ui/tabs/deficit_target.py:218-232`). A Build package inherits the **target's**
   provenance, not the model's error. Twelve `secondhand` and six `model_estimate` targets go straight
   into it.

Ranking for the plan (§3) is then **stakes × current error × tractability**, which is a different
order — the top lane below is worth 47 percentage points on a shipped preset and costs about a day.

### 1.2 The ranked list

Tier key: **F** = calibrated-fitted (bookkeeping; the model reproduces its own constant), **R** =
unfitted reconstruction, **1** = Tier 1 pre-registered out-of-sample, **—** = no scorecard row.
"App" is the 10-year figure the app prints today; "Error" is the scorecard's, against the target named.

| # | Policy | Surfaces | App \$B | Tier | Error | Provenance | Residual cause → pointer |
|--:|---|---|--:|:-:|--:|---|---|
| 1 | **TCJA full extension** | P B | +4,581.9 | F | 0.4% | `line_item` (CBO) | Aggregate fits; the *decomposition* has no microsim path. The 8 JCT line items of P.L. 119-21 reconstruct at **35.8%** — the sharpest evidence the calibrated tier is reconstruction. §6.2 item 17 |
| 2 | **Corporate 21%→28%** | P T A B | −1,397.2 | F | 3.7% | `line_item_differs` (scope) | Fitted to Treasury's rate+GILTI row while the factory sets `gilti_rate_change=0`. Model's marginal base **80.8%** of the vintage average vs JCT **55.9%**. `CORPORATE_PER_POINT_YIELD.md` §4b, §6.2 item 32 |
| 2b | **Corporate 21%→15%** | P B | +1,491.8 | R | **121.6%** | `line_item_differs` (range) | Same base defect, opposite direction, and no fitted constant absorbing it. Published range [+595.0, +673.1]; model sits **\$818.7B outside** |
| 3 | **SS donut \$250K** / **eliminate cap** | P B | −2,700.0 / −3,200.0 | F | 0.0% / 0.0% | `secondhand` ×2 | **The app prints the target.** OCACT publishes percent-of-payroll and no dollars for E2.1/E2.5, so there is nothing to check against. Held out, the mechanism returns −2,664.0 (1.3%) and −3,319.5 (3.7%) — `run_loo.py`. §6.2 item 5 |
| 4 | **Capital gains 39.6% (Biden)** | P T A | −383.2 | 1 | **32.8%** | `line_item` (Green Book FY2025) | Rate channel alone (\$359.0B) exceeds Treasury's whole combined −\$288.6B; semi-log response evaluated at +19.6pp, near its own revenue-maximising rate. Decision 3 freezes the elasticity. `core.py` `biden_capital_gains_39` |
| 4b | **39.6% + step-up elimination** | P T | −381.1 | 1 | 18.4% | `line_item` (Green Book FY2022) | Was 43.3% until PR #126 scored it on its own FY2022–2031 decade. `memos/FY2022_TARGET_WINDOW.md` |
| 4c | **Eliminate step-up basis** | P B | −523.5 | F | 4.7% | `secondhand` | Fitted. `loo.py` **excludes** it for leakage: the derived annual \$50.0B is the target ÷ 10 |
| 5 | **SALT cap repeal** | P B | +1,155.6 | R | 1.1% | `line_item` (PWBM) | Reads well; its sibling `eliminate_salt` reads **22.3%** against CBO Option 49, and the two are priced on **contradictory baselines** (permanent \$10k cap vs lapsed cap). §6.2 item 3 |
| 6 | **Tariffs: universal 10%** | P B | −1,369.8 | R | **36.9%** | `line_item` (Tax Foundation) | ~~No GDP-feedback channel: net/gross sits at 0.60–0.66 against a published 40–50%~~ — **both halves of that diagnosis are wrong; corrected below.** Closed by PR #150 |
| 6b | **China 60% / auto 25% / steel 25% / reciprocal** | P B | −331.1 / −203.9 / −105.2 / −1,642.0 | R | 49.1 / 47.2 / 75.3 / 9.5% | mixed | `reciprocal_coverage_rate = 0.50` is **deleted** for EO 14257's own formula (reproduces all 16 published Annex I rates within 0.80pp); the steel base now reaches HS-73, **1.84× and not "triple"**, and the row is a registered regression against an untraceable target (§6.2 item 65) |

> **Corrected 2026-09-11 (`HSC_h8_tariff_feedback.md` §0, written before any file was opened and
> confirmed by the outturn).** Row 6's residual cause was **backwards in two independent ways**,
> and §3 H8's improvement bands followed from it. First, all five targets are **conventional**
> estimates and the model sat **below** every one of them in magnitude, so adding a GDP-feedback
> drag to the *scored* number moves every trade row **further** from its target. Second, the
> 0.60–0.66 vs 40–50% comparison is a **denominator mismatch**: `net_to_gross_ratio` divides by
> gross duty *after* the import-demand response and the knowledge snapshot's band divides by gross
> *before* it, and on the snapshot's own denominator the universal preset already read **0.589**.
> What actually moved the rows is a convention error neither this table nor §3 named — the score
> netted **retaliation**, which is not in any of these targets, and the repository's own knowledge
> file already said so. The channel is real, is now built, and is **reported beside** the score.
| 7 | **PTC repeal** | P B | −774.1 | R | 29.6% | `secondhand` | PR #131 replaced a fitted annual with CBO 51298 Table 2 and the row got **worse, by design**. What is left is the coverage response: 19.28% transferred, dominated by employment-based coverage (\$101B). `W7_ptc_repeal_shape.md` §5 |
| 7b | **Extend enhanced PTCs** | P B | +366.2 | R | 9.3% | `line_item` | — |
| 8 | **CTC 2021 expansion** / **CTC extension** | P B | +1,600.0 / +600.0 | F | 0.0% / 0.0% | `secondhand` / `line_item_differs` | Fitted to the round target. Held out the module reads **−4.5% / +19.0%** — the honest figures. `ctc_extension`'s own document says +\$735.3B (examined-and-left) |
| 8b | **EITC childless** | P B | +178.0 | R | 9.5% | `line_item` | LOO **−38.0%** |
| 9 | **Estate: Biden reform** | P B | −450.0 | F | 0.0% | `line_item_differs` | JCT's −\$429.6B totals a ten-section bill; examined and left. Growth lever unresolved: 6.81% vs 3.82% moves both LOO rows across −32% to +67%. §6.2 item 14 |
| 10 | **AMT: extend TCJA relief** | P B | +450.5 | R | **66.8%** | `line_item` (CRS R48286) | The app shows **\$450.5B beside a label reading "\$1.36T"**. `reported` mode keeps a constant fitted to the superseded \$450B; the derived path reads −37.0%. Decision 1 |
| 10b | **Repeal individual AMT** | P B | +450.5 | F | 0.1% | `secondhand` | Target is unsourced and internally incoherent with #10 (a repeal cannot cost less than an extension on the same baseline). §6.2 item 2 |
| 11 | **Drug negotiation / reference pricing** | P B | −41.8 / −801.0 | R | 91.6% / **701.0%** | `model_estimate` ×2 | Both targets are the model's own extrapolation. No utilisation response, no launch delay, one Part B base beside a three-channel Part D. §6.2 items 6, 12 |
| 12 | **IRA credit repeal** | P B | −783.0 | F | 0.0% | `secondhand` | Fitted to a round CBO figure |
| 12b | **Repeal EV credits** | P B | −228.4 | R | 25.3% | `line_item` (JCT) | — |
| 13 | **IRS enforcement (IRA / double)** | P B | −188.9 / −60.3 | R | 4.7% / **82.3%** | `line_item` / `line_item_differs` | The doubling row scores a **dose** Treasury did not score (\$160B on top of the IRA's \$80B vs Treasury's \$80B on a pre-IRA baseline) |
| 14 | **Generic ordinary-rate point** (1pp all brackets) | T A B | **T −920.3 / A −1,017.2** | 1 | 22.4% (opt45), 4.1% (JCT 1pp) | `line_item` ×2 | Two surfaces, two answers, 10.5% apart — see §1.3 |
| 15 | **Generic surtax above a threshold** (2pp >\$400K) | P T A | **P/T −166.5 / A −314.6** | 1 | 1.5% on the AGI shape | `secondhand` (Treasury) | 1.89× apart. The validated row is the one Tailor does *not* produce |
| 16 | **Generic payroll point** | T | −1,017.2 | — | — | — | The Tailor chip labelled "Social Security / Medicare taxes" builds a plain `TaxPolicy` on the **individual income base** (`policy_execution.py:238-249`). It never reaches `PayrollTaxPolicy`, has no wage cap, and is validated by nothing |

### 1.3 Four cross-surface defects, measured

**(a) `ordinary_income_base` has three different defaults.** The dataclass says `False`
(`policies_core.py:146`); Tailor's checkbox seeds `True` (`policy_input_tax.py:513`); the composer
sets `not preset_data.get("agi_inclusive_base", False)` = `True` (`composer.py:148`); Ask's
`tool_score_hypothetical_policy` passes nothing and gets the dataclass default (`assistant/tools.py:536-544`).
Measured, on 931037c:

| Shape | Tailor / preset | Ask | Validated row | Official |
|---|--:|--:|--:|--:|
| 1pp, all brackets | −920.3 | −1,017.2 | −920.3 (`cbo_opt45`, 22.4%) | −1,185.3 |
| 2pp above \$400K | −166.5 | −314.6 | −314.6 (`medicare_surcharge_2pp`, 1.5%) | −310.0 |
| 3pp above \$2M | −134.6 | −283.5 | −283.5 (`warren…_3pp`, 19.0%) | −350.0 |

**(b) No preset carries `agi_inclusive_base`.** `grep agi_inclusive_base fiscal_model/app_data.py`
returns nothing; the flag exists only on `CBOScore` records. So the three shipped surtax presets are
scored on the ordinary base while their own validation rows are scored AGI-inclusive. The app shows
**−\$134.6B beside a label quoting TPC's −\$350B** (61.5%) where the scorecard reports **19.0%**, and
**−\$166.5B beside Treasury's −\$310B** (46.3%) where the scorecard reports **1.5%**.

**(c) The generic base is flat for ten years.** Every generic run returns the same annual ten times —
`yr1 == yr10` to the cent on all five shapes tested. CBO's own February 2024 baseline grows nominal
GDP **3.878%/yr**, averaging **28.8%** above TY2023 across FY2025–2034.

> **Corrected 2026-09-10 (`HSB_h2_base_growth.md` §3.1, written before any file was opened, and
> confirmed by the outturn).** This paragraph used to attribute W7's **49.8% → 9.1%** and
> **37.4% → 1.0%** to "the joint effect of (b) and (c)". **That does not survive reading W7's own
> finding 1**, whose decomposition is *three* steps: the filing-status split, then an **AGI base**
> where the option says AGI, then growth. The middle step is **not** (b). (b) is a **preset** flag,
> and a preset flag cannot move a validation row — H1's own falsification test was that zero
> scorecard rows moved, and `cold_holdout.py --json` was byte-identical across PR #142. W7's middle
> step is SOI's **AGI column** in place of its **taxable-income column**, which W7 explicitly scoped
> as "a lane of its own". So the endpoints stated here **embedded a step nobody had built**, and
> H2 was measured against a target it could not reach alone: growth alone gives **34.1%** and
> **17.9%**. The column was then built as **H2b** (PR #146) and the rows landed at **7.4%** and
> **−2.9%**. Both measured chains are in §5's table.

**(d) `controller_utils.get_confidence_context` labels any policy whose *name* is in `CBO_SCORE_MAP`
"High confidence"** (`controller_utils.py:146-166`), with no reference to which tier the row sits in.
That is how a fitted 0.0% and a 701% reconstruction get the same badge.

### 1.4 Presets with no scorecard row at all

Eight of the 52 shipped presets have neither a `PRESET_TO_SCORECARD_ID` badge nor a scorecard row of
any tier — the app prints a model number and nothing checks it:

| Preset | Model \$B | Label claims | Note |
|---|--:|---|---|
| Flat Tax Reform (−5pp all rates) | **+4,601.5** | — | The largest unvalidated number in the app |
| Middle Class Tax Cut (−2pp) | +1,029.4 | — | |
| Carbon Tax \$25/ton | −1,066.8 | "(−\$1.0T)" | Its \$50 sibling is fitted to a `model_estimate` |
| Top Rate to 45% | −724.4 | *(none — withdrawn)* | Target retired in Phase E; correctly shows model only |
| Extend IRA Credits Beyond 2032 | +400.0 | "(\$400B)" | Label figure has no record anywhere |
| High-Income Enforcement | −236.1 | "(−\$250B)" | Label figure has no record anywhere |
| Comprehensive Drug Reform | −158.9 | "(−\$600B)" | **73.5% below its own label** |
| Progressive Millionaire Tax (5pp >\$1M) | −354.6 | — | |

And **24 presets carry a badge while 28 do not**, including every tariff, international, pharma,
enforcement and climate preset — all of which *do* have scorecard rows, in the reconstruction tier.
`PRESET_TO_SCORECARD_ID` simply never learned them. One further label defect:
**"⚖️ Repeal Corporate AMT (−\$220B)"** and its `CBO_SCORE_MAP` entry both carry −220.0 where the
scorecard target and the model carry **+220.0** — the sign is inverted on the label a user reads.

---

## 2. What the evidence supports today, per audience

The three tiers mean different things and the app currently blurs them into one badge.

**Fitted ≈ bookkeeping.** 21 rows at **1.7% mean, 21/21 within 15%**. All 21 are flagged `calibrated_to_target=True`:
the constant was set to reproduce that row. `Estate` and `Payroll` both print **0.0%** in the shipped
`ConfidenceBand` and both are rated **"Excellent"** — that rating is measuring arithmetic. Held out,
the same modules read 10.4% and 3.8%.

**Reconstructions are rough and heterogeneous.** 34 rows at **57.9% / 34.2%**, and the dashboard's own
sub-populations run from `Credits` at 9.5% (n=1) to `Pharma` at **277.8%** (n=3). Never one number.

**Tier 1 is the only skill claim.** 26 rows, **15.0% mean / 10.6% median, 17 within 15%, 22 within
25%** — and it is itself eight populations:

| Class | n | mean | median | max | mass | share of tier |
|---|--:|--:|--:|--:|--:|--:|
| AGI-inclusive surtax | 6 | 20.7% | 13.9% | 49.8% | 124.0 | **31.7%** |
| capital gains | 4 | 20.5% | 19.4% | 32.8% | 82.0 | 21.0% |
| ordinary rate change | 4 | 12.0% | 10.8% | 22.4% | 48.1 | 12.3% |
| corporate | 1 | 44.5% | — | 44.5% | 44.5 | 11.4% |
| enacted-law spending | 3 | 13.4% | 12.2% | 18.2% | 40.2 | 10.3% |
| discretionary spending | 5 | 4.6% | 2.6% | 10.8% | 23.2 | 5.9% |
| payroll | 2 | 7.8% | 7.8% | 8.1% | 15.6 | 4.0% |
| tax expenditure | 1 | 13.1% | — | 13.1% | 13.1 | 3.4% |

Then, per audience:

- **Teaching.** Everything is fit for purpose *if the tier label travels with the number*. The five
  ratings a student sees today ("Excellent" for a fitted 0.0%, "Approximate" for a 277.8%) are
  arithmetically correct and pedagogically backwards. Fix the label before the model.
- **Research.** Tier 1's ordinary-rate, discretionary-spending and payroll classes (11 rows, 4.6–13.4%
  mean) are quotable with the caveat that each has a documented residual. The AGI-surtax class is not
  quotable until §3 H1/H2 land, because its error is a known base definition rather than an unknown.
  Nothing in the fitted tier is evidence of anything except that the constant was set correctly.
- **Hill.** Two things must be said out loud. First, a **Build package total is a sum of published
  targets**, so its accuracy is the *provenance* question (§3 H9), not the modelling one. Second, five
  headline presets rest their accuracy claim entirely on a fitted constant with a `secondhand` target:
  `ss_donut_250k`, `ss_eliminate_cap`, `biden_ctc_2021`, `repeal_ira_credits`, `cap_employer_health`.
  For those, "the model matches CBO" means "the model was told CBO's number".

---

## 3. The plan

> **Status, 2026-09-11 — Waves A, B and C are done (PRs #140-#151).** Nine of the
> thirteen lanes below are closed: **H1**, **H6**, **H13** (Wave A), **H2**,
> **H2b**, **H3a**, **H9** (Wave B) and **H4**, **H5**, **H8** (Wave C), where
> H2b was split out of H2 mid-wave for the reason §1.3(c) records below and the
> preset-label pass shipped beside Wave C as PR #148. Each carries a one-line
> outturn under its own heading and a full record in `planning/lanes/`. Tier 1
> went **15.0% → 14.7% → 14.5%**; the CI gate is **20 / 22** with a per-class
> floor whose capital-gains ceiling Wave C tightened **26 → 24**; badges are 44.
> **Waves A/B moved three tiers on *targets* and Wave C moved one on *accuracy***
> — the reconstruction tier **55.5% → 56.7% on the same 39 rows**, all of it the
> five tariff rows, registered as worse in advance. **Two of Wave C's lanes found
> the plan's own diagnosis wrong** (§1.2 row 6 and §3 H5's "applied by size
> class", both corrected in place with attribution). Waves D and E are open, and
> the owner decisions §4 lists for them are unanswered — **④ (the pharma targets)
> has its machinery built and its one-commit edit written out**, **⑤ (the
> corporate default) has a second independent reading from H3a**, and Wave C
> opened a new one: **the *level* half of the capital-gains death channel**, a
> 7.1× unmeasured factor that points the opposite way from H5 (§6.2 item 55).

Ranked by **stakes × current error × tractability**. Each lane follows the established format and
inherits §1's rules: mechanism not tuning, frozen yardstick, pre-register before opening a file,
regressions count, report movement not attainment.

### H1 — One base rule, four surfaces *(2 lane-days)* — ✅ **DONE, PR #142**

> **Outturn.** Every pre-registered figure landed to six decimal places and **zero validation rows
> moved**. Three surtax presets moved onto their sources' base (Warren 61.5% → **19.0%**, Medicare
> surcharge 46.3% → **1.5%**); Ask's three generic shapes came onto Tailor's answers. Findings the
> plan did not name: **36 of the 52 presets carry `ordinary_income_base` and none reads it**;
> `DistributionalEngine` **ignores it**, so one policy yields a revenue score and a who-pays table
> **2.57× apart** (§6.2 item 46); and the Decision 6 caption was **silent on all three presets it
> exists for** until someone rendered it. The `repeal_corporate_amt` rename could not be made here —
> the label is a *key* of H6's map — so H1 shipped the `CBO_SCORE_MAP` sign plus a test asserting
> the remaining inconsistency, and H6 took the rename. `planning/lanes/HSA_h1_base_rule.md`.

**Mechanism — an attribute, not a heuristic.** The shape alone cannot decide the base, and the battery
says so. `biden_high_income_tax` is a 39.6% rate *above a \$400,000/\$450,000 threshold* and is
classified on the **ordinary** base, where it scores **9.2%**; Option 46's surtax above \$20,000 is
AGI-inclusive. A rule reading "a threshold means AGI-inclusive" would misclassify the first.
`cold_holdout.py --ordinary-base` is the tell: forcing one treatment on every row worsens the other
treatment's cases, in both directions — which is what it looks like when a classification is **read
off the source document** rather than inferred from the form. So:

**(a) The base is an explicit attribute of the policy, never a per-surface default.** One constant,
one default — `ordinary`, matching the validation manifest's default for bracket changes — read by all
four constructors. The dataclass, Tailor, the composer and Ask stop each carrying their own answer.
**(b) The three shipped surtax presets get `agi_inclusive_base=True` from their own sources** — TPC's
Warren table, Treasury's FY2025 Medicare-surcharge row, and the millionaire surtax's own document.
That is the fix for §1.3(b), and it is a per-preset transcription, not a rule.
**(c) Tailor keeps its checkbox, seeded from the shared default**, and Ask's
`score_hypothetical_policy` gains the same optional flag with the same default — so Tailor and Ask
agree by construction rather than by coincidence, with a caption on both saying which base was used.

**Files.** `fiscal_model/policies_core.py` (the shared default), `fiscal_model/app_data.py` (three
preset dicts, plus H6's label fixes folded in — see §4), `fiscal_model/assistant/tools.py`,
`fiscal_model/ui/policy_input_tax.py`, `fiscal_model/composer/composer.py`.
**Pre-register.** Three preset moves, each following from **(b)**: Warren −134.6 → −283.5
(61.5% → 19.0% vs TPC); Medicare surcharge −166.5 → −314.6 (46.3% → 1.5% vs Treasury); Progressive
Millionaire −354.6 → −648.1. One Ask move, following from **(a)**: 1pp all brackets
−1,017.2 → **−920.3**, which is both Tailor's figure and the validated shape.
**The Tailor "2pp above \$400K" run does not move.** It stays on the ordinary base at −\$166.5B unless
the user ticks the box, and the caption now says which base produced it. The defect §1.3(a) records is
that **Ask silently disagreed with Tailor**, not that −\$166.5B is the wrong answer to the question
Tailor was asked — a custom entry has no source document to read a base off, so the shared default is
the only honest answer and the caption is what makes it legible.
**Zero Tier 1 rows move** — the validation path reads `score.agi_inclusive_base` and builds its own
policies (`core.py:905`), so a byte-identical `cold_holdout.py --json` is the falsification test.
**Falsified if** any scorecard row moves, or the four moves above miss their computed values.
**Decision 6** applies: three shipped numbers move by 1.8–2.1×, so the caption lands in the same PR.

### H2 — Grow the generic base on the scored vintage *(3 lane-days)* — ✅ **DONE, PRs #144 + #146**

> **Outturn.** Ten Tier 1 rows moved and every pre-registered figure landed, worst miss **$0.08B**.
> **This lane's own falsification condition fired**: the tier mean **rose 15.0% → 15.6%**, because six
> rows had been under-predicting by *less* than a decade of the baseline's growth is worth. The lane
> reported it and tuned nothing. **H2b** (PR #146) then gave the AGI-stated rows SOI's AGI column —
> the step §1.3(c) had misattributed — and the tier read **14.7%**, below where H2 found it, with
> 15/26 within 15% and 23/26 within 25%, both better than either branch point. **So the condition is
> satisfied by the pair and not by H2 alone.** The two Option 46 rows ran 49.8% → 34.1% → **7.4%**
> and 37.4% → 17.9% → **−2.9%**; the endpoints below (~9.1%, ~1.0%) were never reachable, see
> §1.3(c). All three registered regressions landed, plus two the plan did not name
> (`biden_high_income_tax` and `cbo_opt45_top4_brackets_2pp`). H2b's own registered regression is
> `warren_ultramillionaire_surtax_3pp` **5.2% → 24.8%**, the class's best-scoring row made five times
> worse by a rule read off its own source. Seven shipped presets moved. Findings: **four Tier 1
> targets are rules of thumb with no source URL** and two of them score the same reform against
> targets 23.5% apart (§6.2 item 45); **`medicare_surcharge_2pp`'s 1.5% was measuring a
> cancellation**; the wage-path-vs-nominal-GDP fork is worth **0.35%** and decides nothing; and a
> review caught the Decision 6 caption reading `final_deficit_effect` on dynamic runs, disagreeing
> with the headline above it by 69.1% on Warren. `planning/lanes/HSB_h2_base_growth.md`,
> `planning/lanes/HSB_h2b_agi_column.md`.

**Mechanism.** The generic path holds the SOI aggregate at its tax year for ten years. Project it on
the *scored vintage's own* nominal path — the precedent is W5-A's payroll base ("CBO's own February
2024 wage path times one covered-earnings ratio measured on completed history") and W5-C's
realizations base. The ratio is measured; the path is the vintage's. No constant is fitted.
**Files.** `fiscal_model/policies_core.py` (`TaxPolicy` scoring branch), `fiscal_model/scoring_engine.py`.
**Pre-register.** With H1 landed, `cbo_opt46_agi_surtax_1pp_20k` **49.8% → ~9.1%** and
`cbo_opt46_agi_surtax_2pp_100k` **37.4% → ~1.0%** (both hand-computed in `W7_filing_status_split.md`
finding 1). `cbo_opt45_all_rates_1pp` under-predicts by 22.4% and should close. **Three registered
regressions**: `medicare_surcharge_2pp` (1.5%), `illustrative_top_rate_5pp` (7.4%) and
`illustrative_500k_2pp` (8.9%) all currently under-predict by less than the growth term is worth, so
they will cross their targets. That is the price and it is stated in advance — W7's precedent is that
a lane which reaches a better tier mean by making four rows worse reports both.
**Falsified if** the two Option 46 rows land outside ±3pp of 9.1% and 1.0%, or if the tier mean rises.
**Not in scope: the year-indexed threshold.** Option 45's own text reverts the bracket schedule in
2026 and the model cannot express it. Closing it needs a published post-2025 rate table, which does
not exist (`core.py`, `cbo_opt45_top4_brackets_2pp` limitation 2), and the direction is known: it takes
that row *further* under. **Rejected for this plan**, carried as §6.2 item 27's third `isinstance`
branch — which is the trigger for building `Policy.scores_by_year()` rather than a special case.

### H3 — Corporate: show the range, then narrow the base *(4 lane-days, two commits)*

**H3a, presentation (1 day) — ✅ DONE, PR #143.**

> **Outturn.** Every prediction held and **every artifact is byte-identical** — `corporate.py` was
> not opened. A headline corporate run now prints the four published scores converted to its own
> rate step (**−$1,349.9B to −$935.8B** at +7.0pp) and says where it sits among them. **"Above every
> published estimator" could not be hard-coded, and the measurement is the finding**: `reported` is
> above all four at every step, but **`derived` lands *inside* the published span at the +7pp step
> every shipped preset uses** (76.1% marginal share against a published 55.1–79.5%) and outside it
> at +1pp — a second, independent reading for owner question ⑤, pointing the same way as PR #122's
> Decision 1 reversal (§6.2 item 53). Two further findings: the two corporate bands **do not
> overlap** and the direction asymmetry runs *opposite* to the one `trump_corporate_15`'s ledger note
> cites; and a bundled run's naive per-point share of **102.5%** of the average base is not a base
> defect but `extend_bonus_depreciation`, measured at +$294.15B of +$1,491.8B. The review lesson is
> general: **a test that records a finding must assert the finding, not its neighbourhood.**
> `planning/lanes/HSB_h3a_corporate_range.md`. **H3b remains open (Wave E).**

Wherever the app quotes a corporate number, quote the **estimator
range**. The record is transcribed in `CORPORATE_PER_POINT_YIELD.md` §4b: on FY2025–2034, a point of
statutory rate is worth **55.1%** (Tax Foundation), **55.9%** (JCT), **64.4%** (PWBM) and **79.5%**
(Treasury, rate+GILTI) of the vintage's average base. The model is at **80.8%**. A user told "−\$1.4T"
with no range is being told the model agrees with everyone, and it agrees with the highest.
**H3b, mechanism (3 days).** The remaining 44 of `cbo_opt64`'s 62 points are **credit carryforwards**
(§38(c), §904(c)) and **CAMT**, both of which CBO's 2018 Option 24 narrative places *inside* JCT's
estimate. Each needs a quantity from Form 3800 / Form 1118 statistics — a data-acquisition step.
**Sourced behavioural offsets, not a marginal-realization ratio.** The lane may add pass-through/C-corp
income shifting and profit shifting from JCT's own published methodology and the literature JCT cites;
it may **not** assert a share. The number that would land the row is printed by
`scripts/corporate_yield_reconciliation.py` (total factor **0.5785** against JCT's steady-state
**0.590**) and approaching it is the failure mode.
**Files.** `fiscal_model/corporate.py` (derived branch); H3a touches `components/results.py` and
`fiscal_model/ui/tabs/results_summary.py` only.
**Pre-register.** H3b: `cbo_opt64` 44.5% → 30 ± 8; `biden_corporate_28_fy2022` −62.9% → −45 ± 10;
`trump_corporate_15` 121.6% → 90 ± 20. `biden_corporate_28` is fitted and will move in `derived` only.
**Owner decision required up front:** does H3a's range display change Decision 33's answer?
`CORPORATE_APP_MODE` stays `reported` today because the mean cannot discriminate on three targets 57%
apart — a shipped range is arguably the honest resolution of exactly that.

### H4 — Empirically calibrated bands, by policy class *(2 lane-days)* — ✅ **DONE, PR #149**

> **Outturn.** **Zero scored numbers move and every headline caption changes**,
> which is the deliverable; the band is now the policy's own Tier 1 class's error
> spread, keyed by the same routing the CI per-class gate uses
> (`validation/policy_classes.py`, imported by `cold_holdout.py`, byte-identical).
> **26/26 rows fall inside their class's outer band**, and inner coverage is
> *computed and printed* rather than asserted — it is **not a majority
> everywhere**, `ordinary rate change` covering 1 of 4. **The description below is
> wrong in the direction that understates the defect**: the ETI branch does not
> "return nothing", it falls through, and `get_band_for_result` fell through to
> `Generic`, which **is** the Tier 1 tier — so **31 of 56 surfaces printed
> "±14.7% across 26 calibrated runs"** for policies with no Tier 1 row, including
> *International Reference Pricing*, whose own row is 701.0% from its target. Both
> replaced branches were **fixed proportions of the point estimate** (13 rows drew
> exactly `0.1/0.875` = 11.43% of the headline; 27 drew one of four per-module
> fractions). **18 of 53 presets get a band; 35 print no band and say why**, with
> their own row's error and tier beside the absence. Findings: a `policy_type`
> lookup would have been wrong for four modules (`AMTPolicy` and
> `IRSEnforcementPolicy` declare `income_tax`, `InternationalTaxPolicy` declares
> `corporate_tax`); `type(policy) is TaxPolicy` is load-bearing, since all 17
> subclasses subclass it directly; **a FastAPI response model is a second schema
> that fails as a 400**, and the first full suite produced 12 failures reading
> `assert 400 == 200`, none mentioning credibility; and two shipped surfaces
> forbade collapsing the tiers four lines after doing it twice, at "(~5%)" and
> "~8%". `planning/lanes/HSC_h4_empirical_bands.md`.

**Mechanism.** Replace the ETI-sweep band (`results_summary.py:169-217`) and the category
`ConfidenceBand` (`validation/credibility.py:158-180`) with a band derived from the **Tier 1 error
distribution for that policy class** — §2's eight-row table, keyed off the same routing
`POLICY_TYPE_TO_SCORECARD_CATEGORY` already does. Ordinary-rate changes ±12%; AGI surtaxes ±21%;
capital gains ±21%; discretionary spending ±5%. Where two official bodies disagree, add a second
**estimator-disagreement** band from the published range (corporate 55.1–79.5% per point; Pillar Two
[−102.6, +56.5]; reciprocal tariffs [−1,800, −1,400]; Trump 15% [+595, +673]).
**Why it is worth doing now.** Today's band has three defects, all measurable: the ETI branch returns
nothing for every calibrated preset (the module factories zero the *offset*, so flexing the elasticity
moves zero); the category band uses the **mean as the median** by its own admission
(`credibility.py:174-176`); and it is computed over `summary.by_category`, which mixes fitted
bookkeeping with reconstructions — producing "Estate: n=3, 0.0%, Excellent".
**Files.** `fiscal_model/validation/credibility.py`, `fiscal_model/ui/tabs/results_summary.py`.
**Falsified if** a class's shipped band fails to contain that class's own Tier 1 rows at the stated
coverage. **Decision 6:** every headline caption changes; lands in the same PR.

### H5 — Capital gains: the decedent headcount, and the window rule *(3 lane-days)* — ✅ **DONE, PR #151**

> **Outturn.** Owner decision ⑥ taken; every figure landed on its band. The module
> carried **two death rates 8.3× apart** — `estate_flow_rate` as a headcount rate
> giving 408,532 decedents, against `death_exit_rate()`'s 2.647%/yr, which has
> priced the lock-in wedge since Wave 2 — and the count is now **3,384,194** with
> the $196.2097B level untouched. `cbo_opt51_gains_at_death` **20.3% → 35.5%**
> (registered regression), `biden_capital_gains_39` **32.8% → 27.0%**,
> `treasury_capgains…v2` **18.4% → 1.8%**, `cbo_opt47` unmoved to the cent; the
> class **20.5% → 18.7%** and the tier **14.7% → 14.5%**, with within-25 falling
> 23 → **22**, exactly the CI floor. **"Applied by size class" below is refuted in
> sign** — see the correction under §3's own paragraph — and **two of the three
> bands below were unattainable**, which the lane established before running:
> `biden_capital_gains_39` cannot reach 15 ± 8 (its rate channel alone is 24.4%
> over with the death channel at zero) and `treasury_capgains…v2` cannot regress
> to 22 ± 6 (since PR #126 it is scored on its own FY2022–2031 decade, where the
> model is *under*). **This is half of a two-sided correction**: the count and the
> level come from the same PW ratio, and that flow implies **0.372% of the
> accrued-gains stock** where the stock's death exit is priced at **2.647%**, a
> 7.1× unmeasured factor pointing the other way (§6.2 item 55). No preset moved;
> three Tailor shapes did, by 19–31%.
> `planning/lanes/HSC_h5_decedent_headcount.md`.

**Mechanism.** `estate_flow_rate = 0.3195%/yr` is Poterba & Weisbenner's **dollar** flow of estates
over net worth, used as a **headcount** rate: 408,532 decedents against roughly **3.09 million** NCHS
deaths. The replacement is already in the tree and unused in this channel —
`mortality_weighted_net_worth_share` at **2.65%** in `accrued_gains_parameters.csv`, derived from NCHS
mortality against DFA net worth by age.
**Two cautions from `W7_decedent_ladder.md` §8.4, both binding.** It is a **level** change to the whole
death channel and moves `cbo_opt51_gains_at_death` (20.3%) in the **wrong** direction. And it is not
uniform: the implied count above \$12.92M is **4,378** against SOI's **7,194**, short by 1.6× where
the total is short by 7.6× — a uniform scale-up overshoots the top while correcting the middle.

> **Corrected 2026-09-11 (`HSC_h5_decedent_headcount.md` §1.3, measured before any file was
> opened, and shipped as two regenerable CHECK-ONLY parameters plus an ordering test).** The
> second caution — **"apply the rate by size class, because the grading falls at the top"** —
> is **refuted in sign**, off the two tables this paragraph itself names. DFA net worth by age
> of head against NCHS Table 1's `Lx` says the wealthy are **older**, so they die at a
> **higher** rate: head-weighted **1.6456%**, net-worth-weighted **2.6468%** (the shipped
> parameter), size-graded at the top **2.8400%**. Grading therefore takes the implied count
> above \$12.92M to **38,908** where the uniform swap takes it to **36,262** — both *further*
> from 7,194, not nearer. Two things travel with that. The SOI figure **needs a unit before it
> is a check**: SOI counts *individual* decedents over a *gross-estate* threshold and the model
> counts *households* over net worth, so a model count above SOI's is the expected sign and
> W7's 1.6×-vs-7.6× asymmetry is at least partly that gap. And the pre-registration's own
> arithmetic below was **wrong by more than 4×**: 8.3× the count — not ×2 — is what the
> authorised constant gives, and it takes the \$1M → \$5M step to **\$9.40B**, through
> Treasury's \$33.4B and out the other side.

**Pre-register.** Holding gains at death at PW's flow and varying only the count, ×2 takes the
\$1M → \$5M exclusion step 85.02 → 35.46 and ≈NCHS takes it to 9.94; about **twice** the shipped count
reproduces Treasury's own step to within two billion. Expect `biden_capital_gains_39` 32.8% → 15 ± 8,
`treasury_capgains…` 18.4% → 22 ± 6 (a registered regression), `cbo_opt51` 20.3% → 30 ± 8 (registered).
**(Outturn: the first two bands were unattainable and the lane said so in advance — see the outturn
box above. `cbo_opt51` landed at 35.5% on the lane's own recomputed band of 35.5 ± 2.)**
**Owner decision required up front:** `estate_flow_rate` is a level nobody may change by implication.
**The realizations response at large steps is explicitly out of scope.** At +19.6pp the semi-log
response sits near its own revenue-maximising rate (b = 2.27, τ\* = 44.1% against a reform 43.4%), and
Treasury's estimate implies a stronger response than the frozen literature value gives. **Decision 3
freezes that value.** Re-opening it is an owner decision, not a lane's, and it is the single largest
remaining capital-gains term.
**The window rule (§6.2 item 35) is an owner decision, not a lane.** `iija_2021_discretionary` reads
18.2% because \$92.6B of its authority path outlays before the model's window opens; on its own
FY2022–2031 decade it scores **+\$414.3B against +\$415.4B, 0.3%**. `CBOScore.scoring_window_first_year`
exists and PR #126 set the supersede precedent, so this is a `.v3` row and nothing else. **Decide
before Wave B**: a rule applied to one row and not the other is worse than a rule applied to neither.

### H6 — No headline without a row *(2 lane-days)* — ✅ **DONE, PR #140**

> **Outturn.** Badges **24 → 44**, unbadged 28 → 8, and the badged set is now exactly the set of
> presets carrying a `CBO_SCORE_MAP` `official_score`. Each badge names its **tier**: after Wave B's
> revisions the 44 are **16 fitted / 25 unfitted reconstructions / 3 out-of-sample**, pinned by test.
> **Six presets now carry a badge saying they are more than 50% from their published target and five
> said nothing at all before** (reference pricing 701.0%, Trump corporate 121.6%, drug negotiation
> 93.3%, double enforcement 82.3%, TCJA AMT relief 66.8%, auto tariff 52.8%). The map is keyed by
> **stable preset id**, which is what let H1's four renames and H9's five superseded figures land
> without silently losing entries. Findings: **`get_confidence_context` has no caller in the tree**,
> so §1.3(d) describes a live defect on a dead function (§6.2 item 48); the badge caption sink **was
> already lying for six rows**; the plan's own three counts in §1.4 **do not sum** (corrected and now
> pinned by test); and **four of the 44 rows do not score the number the app prints**, two of them
> because the runners score their own policy on the validation window while the app scores
> FY2026–2035 — declared and decomposed rather than smoothed. It also took H1's
> `repeal_corporate_amt` rename and H13's methodology-table source cell.
> `planning/lanes/HSA_h6_no_headline_without_row.md`.

**Mechanism.** Three rules, enforced by a test, not by review.
1. Every preset with a `CBO_SCORE_MAP` `official_score` gets a `PRESET_TO_SCORECARD_ID` entry — the 28
   presets that have a reconstruction row and no badge get one, showing the **reconstruction** rating.
2. A preset with no scorecard row of any tier may not display a dollar figure in its **label**. Four
   do today (Comprehensive Drug Reform, High-Income Enforcement, Extend IRA Credits, Carbon Tax \$25).
   Either register a row or strike the figure; "Top Rate to 45%" is the model for how to do it right.
   **The label edits themselves ship in H1's PR**, because both lanes touch `app_data.py` and Wave A
   must be file-disjoint; H6 owns the **test** that enforces the rule from then on.
3. `get_confidence_context`'s "High confidence" is keyed to the **tier**, not to membership of
   `CBO_SCORE_MAP`.
**Files.** `fiscal_model/ui/preset_validation.py`, `fiscal_model/ui/controller_utils.py`, `tests/`.
**Also fix, in H1's PR and for the same reason:** the `repeal_corporate_amt` label and its
`CBO_SCORE_MAP` sign, −220.0 against a +220.0 target and model.
**Falsified if** any scored quantity moves — neither lane may move a number.

### H7 — Tax expenditures: the five magnitudes, and the SALT baselines *(3 lane-days)*

**Mechanism.** All five `BEHAVIORAL_ELASTICITIES` are unsourced — charitable **0.40**, employer health
**0.20**, mortgage **0.10**, SALT **0.05**, retirement **0.30** — and PR #128 deliberately settled only
their *direction*. Two now have a published figure beside them: Poterba & Sinai's own erosion is
**15%** against mortgage's 0.10 (NBER WP 14253: \$72.4B without behaviour, \$61.9B with, "about 85
percent"), and charitable's 0.40 carries the size of a *price elasticity of giving* applied to a share
of a revenue effect — a different quantity; the arithmetic of a 28% ceiling at a 37% marginal rate
implies nearer **18%**.
**The hazard, named in advance.** Three of the module's six fitted constants were fitted so the
*static* path hits the target and three so the *magnified* score does; on the three static-fitted rows
the convention is carried as pure error (10.1%, 5.0%, 5.1%). Re-fitting them is what §1.1 forbids.
**Pre-register.** `eliminate_mortgage` LOO 14.0% → 8 ± 5; `cap_charitable` LOO 13.1% → 20 ± 8 (a
registered regression if 0.18 replaces 0.40). Expenditures LOO 37.5% → 30 ± 8.
**SALT is a separate, joint decision, not a lane.** `repeal_salt_cap` is priced against a permanent
\$10,000 cap and `eliminate_salt` against CBO Option 49's lapsed-cap world; reconciling them needs a
baseline-vintage concept the module does not have, and `eliminate_salt`'s CBO baseline is not current
law after P.L. 119-21 sec. 70120. **Owner decision** (§6.2 item 3), with a visible consequence for two
headline presets.

### H8 — Tariffs: the GDP-feedback channel *(4 lane-days)* — ✅ **DONE, PR #150**

> **Outturn — and the mechanism below is the wrong diagnosis, which `HSC_h8_tariff_feedback.md` §0
> established before a file was opened.** All five targets are **conventional** estimates and the
> model already sat below every one of them in magnitude, so **adding a GDP drag to the scored
> number moves every trade row further from its target**, not closer; the 0.60–0.66 vs 40–50%
> comparison is also a **denominator mismatch** (the module divides by gross duty *after* the
> import-demand response, the snapshot's band *before* it — on the snapshot's own denominator the
> universal preset already read **0.589**). So the channel is built and **reported beside** the
> score, the column structure FF861 itself publishes, and what moved the rows is a convention
> correction this plan never named: **retaliation left the conventional score**, where it was a
> category error against every target the scorecard carries — and the repository already knew, since
> `tariff_scoring_methodology.md` tells the Ask assistant that `include_retaliation=False` "gives a
> strictly conventional score" while all five scenarios and all five presets ran with it `True`.
> `estimate_behavioral_offset` is now **0.7125 of gross** in either direction, against FF861's
> implied 0.738. Rows, each landing on its own registered figure: `trump_universal_10`
> **42.03% → 36.91%**, `trump_china_60` **57.17% → 49.06%**, `auto_tariff_25` **52.81% → 47.20%**,
> `reciprocal_tariffs` **6.88% → 9.47%** (and `within_published_range` **False → True**, distance
> $3.2B → **$0.0B** — the row carries both readings), `steel_tariff_25` **11.89% → 75.28%**, a
> registered regression. **Trade 34.2% → 43.6%, registered as worse; on the four rows that have a
> document it improves 39.72% → 35.66%.** The two cheap fixes landed too:
> `reciprocal_coverage_rate = 0.50` is **deleted**, for EO 14257's own bilateral-deficit formula on
> Census 2024 across 230 partners, which reproduces **all sixteen published Annex I rates within
> 0.80pp**; and the steel base reaches the Section 232 derivative chapter, $58.9B → $108.4B —
> **1.84×, not the "roughly triple" this repository said in three places** — declared an upper
> bound, because the annexes list articles at HS-10 and the loader has a two-digit chapter (§6.2
> item 64). Five presets moved with a Decision 6 caption; the other 44 score to the cent in both
> modes. Two findings outside the lane's files became items 62 and 63.

**Mechanism *(as written; superseded by the outturn above — the score nets retaliation it should not,
and the missing channel belongs beside the score rather than inside it)*.** The score nets duty
avoidance, the 25% income-and-payroll offset and retaliation, but
not receipts lost to lower output — which is why net/gross sits at **0.60–0.66** where the published
band is 40–50%. Route the tariff's own price and volume effect through `MacroModelAdapter`, the
channel that already exists for dynamic scoring, rather than adding a reduced form.
**Also in scope, both cheap:** `reciprocal_coverage_rate = 0.50` (the one shape assumption in
`TRADE_BASELINE` that is not a measurement — a partner-specific implementation off each partner's
bilateral-deficit-to-imports ratio is the honest fix and the published estimates all use it), and the
steel base, which is HS-72 + HS-76 only where Section 232 also reaches HS-73 derivatives (\$49.6B at
5.63% collected, **roughly tripling** the base).
**Pre-register.** `trump_universal_10` 42.0% → 20 ± 10, `trump_china_60` 44.3% → 25 ± 10,
`auto_tariff_25` 52.8% → 35 ± 12. `steel_tariff_25` 11.9% → **a registered regression** on the HS-73
base, and `reciprocal_tariffs` 6.9% → worse on a partner-specific coverage rate: both currently read
low *because* the base is too small, which is two errors cancelling.
**Decision 6** applies — five shipped presets move — and the caption pattern is L8's own.
**(Outturn: the first three bands were unreachable by the mechanism this paragraph names — a drag
moves conventional rows *away* — and the lane registered four replacement figures off the
retaliation correction, all of which landed to two decimals. The two registered regressions were
right in direction: the steel row went to 75.28% and the reciprocal row to 9.47%, and the steel
floor base would have scored **1.7%** on a base missing most of what Section 232 reaches, which the
lane declared and refused.)**

### H9 — Provenance: 18 targets without a document *(4 lane-days)* — ✅ **DONE, PR #145**

> **Outturn.** Eighteen judged one at a time: **six revised, twelve examined-and-left, one
> transcribed-and-confirmed, and no modelling change at all** — all 81 `model_10yr_billions`
> byte-identical, every leave-one-out *derivation* unchanged, Tier 1 untouched to the byte.
> **Five of the six revisions make their row worse and one makes it far worse**, which is the shape a
> correct provenance pass has: `ss_donut_250k` → CBO's **−$1,426.8B** (0.0% → **89.2%**),
> `tcja_rates_only` → CRS's **+$2,158.7B** (2.2% → **44.3%**), plus `trump_china_60`,
> `eliminate_estate_tax`, `eliminate_mortgage` (a range) and `repeal_ira_credits`. Against §5:
> `model_estimate` **6 → 4** (target ≤ 4, **met**), `secondhand` **12 → 7** (target ≤ 6, one short,
> and the seventh is a locked-holdout id with nothing to move to), `line_item_differs` 7 → 8 with a
> recorded **range** verdict, every survivor carrying a written verdict, and the `retire` state
> **exists**. **The sharpest result is a refusal the mechanism made rather than the author**: H13's
> Tax Foundation cap-elimination figure is −$3,200.0B *to the digit the carried target states*, so
> `target_revision_problems` rejected it as noise. **The `retire` state is built, tested on synthetic
> rows, and applied to nothing** — retiring the two pharma rows would buy **18.5 points of
> "improvement" by deletion**, which §5 forbids, so a retired row keeps its entry and reports only
> beside a held-in-place second reading. **Owner decision ④ is open with its exact one-commit edit
> written out.** `planning/lanes/HSB_h9_provenance.md`.

**Mechanism.** The calibrated tiers hold **55** rows: 30 `line_item`, 12 `secondhand`, 7
`line_item_differs`, 6 `model_estimate`. Apply `PROVENANCE_wave4.md`'s per-target judgement to the 18
that are not `line_item`. Each ends in exactly one of four states: **revised** (through
`target_revisions.py`, ledger commit before scoring commit), **examined-and-left** (with the verdict
written), **range-revised**, or **retired**.
**What is already known, so nobody re-derives it.** Several have nothing to move to: both Social
Security targets (OCACT publishes percent-of-payroll only), `repeal_ira_credits`, `trump_china_60`,
`cap_charitable`, `eliminate_step_up`, `biden_ctc_2021`, `repeal_ptc`, `cap_employer_health`,
`repeal_individual_amt`. The two pharma `model_estimate` targets (−\$500B, −\$100B) are the tier's two
worst rows and neither is in the ledger; **whether either should be retired is an owner decision on the
ledger's own terms** (`W4_pharma_part_d.md` §5).
**Build the `retire` state.** §6.2 item 34 records that PR #122 declined to build one because nothing
needed it. The pharma pair is what needs it: "this target should not exist and nothing replaces it" is
distinct from both a supersession and an examined-and-left.
**A rule for estimator-range targets.** Three rows now carry ranges and each was decided ad hoc. Write
the rule: a range target's error is **distance to the nearest bound**, containment is the pass
condition, and the reported percentage against an editorial midpoint is not a measurement of accuracy.
`CalibratedTarget.distance_to_range()` already implements it; the rule needs stating in
`docs/VALIDATION.md` so the fourth range row does not re-open the question.
**Falsified if** any model constant moves. This lane may not open a module.

### H10 — A Tailor battery: measure the path users type on *(4 lane-days)*

**Mechanism.** Tier 1's 26 rows measure the generic path on **CBO Options shapes**. Users type
different shapes. Register a pre-registered battery of published *rate-change* scores organised by
**threshold** and **filing status**: JCT bluebook rate tables, Green Book rows across FY2022–FY2025
editions, and CBO Options 45/46/47 across the 2018, 2020, 2022 and 2024 volumes (the same reform, four
vintages — four independent observations of one mechanism, which is exactly what the corporate memo
showed is available and nobody has used for the individual base).
**Why it ranks here rather than higher.** It measures without improving. But after H1 and H2 move
every generic number, a battery of 26 rows built from one volume is a thin basis for the claim, and
the four-vintage design is the cheapest way to distinguish a base error from a vintage error.
**Pre-register.** Target: ≥ 40 Tier 1 rows, ≥ 15 of them at thresholds other than \$0/\$400K/\$1M.
No target may be selected after seeing the model's answer — `preregistered.py`'s entry-commit rule.

### H11 — PTC: the coverage response *(2 lane-days)*

**Mechanism.** PR #131 put the static path on CBO 51298 Table 2 and transferred a single **19.28%**
offsetting share from publication 60437. CBO's own itemisation is dominated by **employment-based
coverage** (\$101B) — people who lose marketplace coverage return to employer plans, and the exclusion
costs revenue. Model the composition rather than the aggregate share.
**Also here:** `MARKETPLACE_DATA`'s uncited "19 million lose coverage" is rendered on a surface users
see, and pub. 51298 **Table 1** is identified but untranscribed.
**Pre-register.** `repeal_ptc` 29.6% → 20 ± 8. `extend_enhanced_ptc` 9.3% is a registered regression
risk. **Falsified if** the module reproduces −\$1,100B — that target was examined and left, and the
lane demonstrated why (the same mechanism on the June 2024 vintage returns \$1,143.0B against CBO's own
\$1,142B, **0.09%**).

### H12 — Sectoral presets: caption or demote *(1 lane-day + an owner decision)*

**Recommendation: demote, do not model.** The four pharma presets carry a 277.8% category mean, two
`model_estimate` targets, and the reconstruction tier's worst row at **701.0%**. The named residuals —
no utilisation response, no launch delay, one Part B base beside a three-channel Part D, a
superseded cost-sharing split — are a multi-wave modelling programme, and the presets are not
high-stakes by §1.1's first test: nobody quotes "International Reference Pricing" as a score.
**The lane is therefore presentational**: move the four pharma presets (and, on the same reasoning,
`irs-enforcement-double` at 82.3%) off the headline surfaces into an explicitly-labelled *illustrative*
group, with the reconstruction error printed. **Owner decision required up front** — this removes
figures from Explore and Build. The alternative, modelling them, is §6.2 item 12 and costs ~8 lane-days
for rows nobody cites.

### H13 — Payroll: say what the two OCACT targets are *(1 lane-day)* — ✅ **DONE, PR #141**

> **Outturn.** No model change and **zero numbers moved** — all three artifacts byte-identical, which
> is the lane's own falsification test. OCACT scores E2.1 and E2.5 at **+2.55%** and **+2.50% of
> taxable payroll** and publishes **no ten-year dollar amount at any horizon**, verified three ways
> (including that "billion" and "trillion" do not appear once across the whole six-page category
> summary). **−$2.7T traces to a Peter G. Peterson Foundation sentence** with no report year, run
> number or window, describing a *benefit-crediting* variant where E2.5 says "do not provide benefit
> credit"; **−$3.2T matches nothing PGPF or OCACT prints and its origin is still unlocated**. Two
> published ten-year scores were handed to H9 rather than banked, and **one is a trap dressed as a
> confirmation** — H9's ledger then refused it by its own arithmetic. Unpredicted: **both published
> paths ramp and the module's does not** ($122.0B → $192.0B against a flat $270B, 17.0% high in
> FY2026 and 25.7% low in FY2034), which is `create_repeal_ptc`'s defect in a second module and is
> now §6.2 item 47. `planning/lanes/HSA_h13_payroll_targets.md`.

**Mechanism.** No model change. `ss_donut_250k` and `ss_eliminate_cap` are two of the app's six largest
headline figures, both print the target exactly, and both targets are `secondhand`: OCACT
publishes E2.1 and E2.5 as **percent of payroll**, never dollars. The honest presentation is the
held-out number beside the shipped one — **−\$2,664.0B (1.3%)** and **−\$3,319.5B (3.7%)** from
`run_loo.py` — with the note that the ×10 figure is a conversion nobody published.
**Falsified if** any number moves. This is a caption and a `docs/VALIDATION.md` paragraph.

### Label figures — §6.2 item 43, not an H-lane *(1 lane-day)* — ✅ **DONE, PR #148**

> **Outturn.** Shipped beside Wave C because the two waves that opened it could not take it:
> a preset label is a **key** of H6's badge map, so renaming one crosses a file boundary
> Waves A and B were structured to keep. **Zero numbers move** — `cold_holdout.py --json`,
> `run_validation_dashboard.py` and a 53-preset sweep by stable id all byte-identical. Six
> labels now quote the figure their row's **current** published target carries in the app's own
> sign convention; `_LABELS_QUOTING_A_SUPERSEDED_FIGURE` went **5 → 0** and
> `test_a_label_figure_never_contradicts_its_own_official_score` runs against **all 40**
> figure-carrying labels with no exemptions for the first time. **The sharpest finding is a
> third mechanism for a defect this repository has now found three times**: `🌱 Repeal IRA
> Clean Energy Credits ($783B)` was not quoting a superseded target — −783.0 is
> `model_10yr_billions`, so the app printed **its own output, positively signed, in the slot a
> published score occupies**. Three more: the mortage rename needed
> `SCORE_ONLY_ALIAS_ID_BY_LABEL` rather than `LEGACY_LABEL_ALIASES`, because a score-only Build
> option has no `PRESET_POLICIES` row and the alias index would have raised `KeyError` at
> runtime; **the worst stale string was not a label** but `assistant/knowledge/ssa_trustees_2025.md`,
> which told the Ask assistant the $250K donut was "scored by CBO at −$2.7T (model: −$2.4T,
> error 12%)" — three errors in one BM25-indexed clause; and `methodology.py` had that row under
> the wrong **tier**, inside "calibrated reference models" at 0.0%. Two spillovers carried rather
> than fixed: §6.2 items 56 and 57. `planning/lanes/HSC_label_figures.md`.

### Rejected, with the reason

| Candidate | Verdict |
|---|---|
| Year-indexed threshold (Option 45's 2026 revert) | **Blocked**: needs a published post-2025 rate table that does not exist; direction known to worsen the row. Becomes item 27's `Policy.scores_by_year()` when a third case arrives |
| Corporate marginal-realization ratio | **Forbidden** by §1.1 — the landing factor (0.5785 vs JCT's 0.590) is printed and must not be approached |
| Capital-gains elasticity at large steps | **Owner decision**, Decision 3 freezes it. Largest remaining capital-gains term |
| UTPR re-base on JCT Equation 2 | **Blocked** on `oecd.org` 403s; deriving from Treasury's own row is circular |
| Estate growth lever (6.81% vs 3.82%) | **Owner decision**, §6.2 item 14; moves both LOO rows −32% to +67% |
| `TCJAExtensionPolicy` microsim path | Distributional, not a headline dollar. Real (§6.2 item 17) and out of scope here |
| AMT §55(b)(1) 26/28% bracket | Small; the AMT high-stakes problem is a *target* (item 2) and a *mode* (Decision 1), not the rate schedule |
| `_scorecard_index` 6.5s on scored routes | Performance (§6.2 item 39). Real, not accuracy |
| `.gitignore` masking ruff on `fiscal_model/data/` | Repo-wide gate change, needs its own PR (§6.2 item 41) |

### Process rules this plan adds

1. **Pre-registration, unchanged.** Every lane names its expected movement before opening a file; a
   lane that moves rows it did not name writes down what it learned rather than claiming it.
2. **Decision 1 and Decision 6, unchanged.** `reported` stays the app default per module until that
   module's derived error beats its fitted error; a shipped number that moves ships its caption in the
   same PR.
3. **CI gate re-derived by the workflow's own rule only** (`validation-dashboard.yml`), downward
   only. On 931037c the rule re-derived the then-current gate to itself: ceiling
   `ceil(15.0 × 1.25) = 19 → 20`, floor `22 − 1 = 21`. **✅ Applied after Waves A/B**: on 26 cases at
   **14.7%** with **23** within 25%, the ceiling re-derives to itself again (`ceil(14.7 × 1.25) = 19 →`
   nearest 5 `= 20`) and the floor tightens `23 − 1 = 22`. The gate is now **20 / 22**.
   **✅ Re-derived again after Wave C, and "downward only" did work for the first time**: on 26 cases
   at **14.5%** with **22** within 25%, the ceiling still derives to 20, and the floor derives to
   `22 − 1 = 21` — which would **loosen** the gate. It stays at **22**, and the workflow comment says
   so, because a rule that tightens on improvement and loosens on regression is not a gate.
4. **New: a per-class floor.** The pooled gate cannot see a class regressing while the mean improves —
   which is exactly what happened to `medicare_surcharge_2pp` in W7, and again to
   `warren_ultramillionaire_surtax_3pp` in Wave B. Add `--max-class-mean-error`, applied to §2's eight
   classes, set at each class's post-wave value × 1.25. **✅ Built and wired.** Ceilings use the pooled
   rule's `ceil(value × 1.25)` **without** its round-up-to-5, which exists to give a 26-row mean
   headroom for one new hard case and is not what a class of one or two rows needs: AGI-inclusive
   surtax **22**, ordinary rate change **19**, capital gains **26**, corporate **56**, enacted-law
   spending **17**, discretionary spending **6**, payroll **10**, tax expenditure **17**. The tree had
   no class routing, so one is **derived from each case's own `CBOScore` record** — `policy_type`,
   plus `agi_inclusive_base` for the income-tax split and `cbo_options.runnable_score_ids()` for the
   spending split — which reproduces §2's table exactly (6 / 4 / 4 / 1 / 3 / 5 / 2 / 1) and classifies
   a row the moment it is registered. **After Wave C exactly one ceiling moved**, by the same rule:
   capital gains **26 → 24** (`ceil(18.7 × 1.25) = 24`); the other seven re-derive to themselves.
   **The gate fails three ways**: a class over its ceiling, a class
   the battery contains that was given *no* ceiling, and a ceiling naming a class that does not exist.
   The second matters as much as the first — a gate that ignored an unlisted class would let a row in
   a ninth class sail past it, which is the failure mode PR #119's coverage-grep test exists to
   prevent.
5. **New: no headline without a row** (H6), enforced by a test.
6. **`ANTHROPIC_API_KEY` hygiene — the suite first, then the smoke test.** Two rules, and the lanes
   hit both.
   **The suite runs with the key unset.** With `ANTHROPIC_API_KEY` exported in the shell, parts of
   `tests/` make **live Anthropic calls**. CI never sets it, so a green local run with the key present
   is not the run CI performs — and it bills. Every lane runs
   `ANTHROPIC_API_KEY= python -m pytest tests/ -q`.
   **Only the deliberate smoke test uses the key.** `scripts/smoke_ask_assistant.py` costs ~\$0.04 per
   run, and a lane that moves a scored number **must** re-run it, because the assistant quotes
   `get_app_scoring_context` and `score_hypothetical_policy` off the same engine. The key comes from
   the environment at invocation; it is never written into a lane doc, a test fixture, a commit
   message or a PR body, and the run's *output* — not the key — is what gets pasted.
   **Added after Wave C, where two lanes hit it independently: a piped pytest reports the pipe's
   exit code, not pytest's.** PR #151 recorded a run that reported exit 0 from `| tail -25` while
   pytest had failed, and PR #149 lost a full suite run the same way. **Write the output to a file
   and read the file**, and take the exit code from the unpiped command. It is PR #119 §7.5's lesson
   in a second costume — *"identical to main" is only evidence when the check being compared can
   distinguish them* — and the same class of trap: a green signal produced by something other than
   the thing being checked.

---

## 4. Sequencing

Files are disjoint within a wave, so lanes run as parallel Opus agents in worktrees.

| Wave | Lanes (parallel) | Files | Days | Owner decisions needed **before** the wave opens |
|---|---|---|--:|---|
| **A** | **H1** base rule + labels · **H6** badges and tiers · **H13** payroll caption | `policies_core.py` + `app_data.py` + `tools.py` + `policy_input_tax.py` + `composer.py` / `preset_validation.py` + `controller_utils.py` + `tests/` / docs | 5 | ① Three surtax presets move by ~2×: confirm the Decision 6 caption. ② Four label figures with no record — confirm strike-vs-register per preset **before H1 opens**, since H1 now carries the edit |
| **B** | **H2** base growth · **H3a** corporate range · **H9** provenance | `policies_core.py` + `scoring_engine.py` / `results_summary.py` + `components/results.py` / `validation/*` | 8 | ③ IIJA `.v3` — apply the window rule to the second row, or to neither (§6.2 item 35). ④ Pharma targets: retire, or carry unsourced (H9 needs the answer to build the `retire` state). ⑤ Does a shipped corporate **range** change Decision 33's `reported` default? |
| **C** ✅ | **H4** empirical bands · **H5** capital gains · **H8** tariffs *(+ the label lane, PR #148)* | `credibility.py` + `results_summary.py` / `data/capital_gains.py` / `trade.py` | 9 | ⑥ and ⑦ **both taken.** `policies_core.py` needed **no change at all** for the second wave running, which says the seam between "how many estates, and how big" and "what a proposal does to one" is in the right place |
| **D** | **H7** expenditures · **H11** PTC · **H12** sectoral demotion | `tax_expenditures_core.py` / `ptc.py` / `app_data.py` + `explore.py` | 6 | ⑧ SALT's two baselines (§6.2 item 3) — a joint call on both rows. ⑨ Do the four pharma presets and Double IRS Enforcement stay on headline surfaces? |
| **E** | **H3b** corporate mechanism · **H10** Tailor battery | `corporate.py` / `validation/preregistered.py` + `cbo_scores.py` | 8 | ⑩ H10 registers ~15 new Tier 1 rows: confirm the CI gate is re-derived **after** they land, by the workflow's rule, not before |

**Conflict notes.** H1 and H2 both reach the generic path and must be serial — H1 in Wave A, H2 in
Wave B — because H2's predicted endpoints (9.1%, 1.0%) are computed *with* H1's base rule in place.
H4 must follow H2, since the bands are read off the post-H2 Tier 1 distribution. H3a and H3b are split
across waves deliberately: the presentation is worth shipping before the mechanism, and H3b is the one
lane whose data acquisition (Form 3800 / Form 1118) may not land at all. H9 and H6 both edit
`app_data.py` and must not share a wave — and neither may H1 and H6, which is why the four label
strikes and the `repeal_corporate_amt` sign are folded into **H1's** PR, leaving H6 the badge map, the
confidence tier and the test that enforces the rule afterwards. Wave A is then disjoint: H1 owns
`app_data.py` and the generic constructors, H6 owns `preset_validation.py` and `controller_utils.py`,
H13 owns docs. **Total: 36 lane-days across five waves.**

---

## 5. What success looks like

**Measurable, per class.** Tier 1 targets after Wave C, stated as movement not attainment:

| Class | n | At writing | After Waves A/B | **After Wave C** | Target | Which lane |
|---|--:|--:|--:|--:|--:|---|
| AGI-inclusive surtax | 6 | 20.7% | 17.6% ⚠ | **17.6%** ⚠ | **≤ 10%** | H1 + H2 + H2b |
| ordinary rate change | 4 | 12.0% | 14.8% ⚠ | **14.8%** ⚠ | ≤ 12% (hold) | H2 |
| capital gains | 4 | 20.5% | 20.5% | **18.7%** ✅ | ≤ 18% | H5 |
| corporate | 1 | 44.5% | 44.5% | **44.5%** | ≤ 32% | H3b (Wave E) |
| discretionary + enacted spending | 8 | 7.9% | 7.9% | **7.9%** | hold | — |
| **tier** | 26 → ~40 | 15.0% / 10.6% / 22 within 25 | 14.7% / 12.6% / 23 within 25 | **14.5% / 11.5% / 22 within 25** | **≤ 12% mean, ≥ 30 of 40 within 25%** | all |

**Capital gains is the first class to reach its target, it did so by 0.7 points, and the reading is
not clean.** H5 moved three of the four rows in two directions — `cbo_opt51` **20.3% → 35.5%** as a
registered regression, `biden_capital_gains_39` 32.8% → 27.0%, `treasury_capgains…v2` 18.4% → **1.8%**
— so the class mean fell while its *worst* row got 15 points worse and its median barely moved
(19.4% → 18.8%). The 1.8% is not accuracy: the count and the level come from the same
Poterba–Weisbenner ratio, only the count was authorised to move, and the level that flow implies is
**7.1× below** the module's own death-exit rate (§6.2 item 55), which points the other way. **Read
the class as met on the stated metric and open on the mechanism**, and note that the tier's within-25
count fell 23 → 22 to get there, landing exactly on the CI floor.

⚠ **Two classes missed their mark and both misses are informative.**

**AGI-inclusive surtax is 7.6 points short of ≤ 10%, and none of the distance is a missing
mechanism.** Of its remaining 105.4 points of mass, **70.3 sit on three rows H2b holds on their own
sources' words**: `medicare_surcharge_2pp` (31.8%), whose statutory base — wages plus net investment
income — is **neither SOI column**; and `illustrative_top_rate_5pp` (20.2%) and `illustrative_500k_2pp`
(18.3%), whose targets carry **no source URL**. The two rows with a published option and a transcribed
base read **7.4%** and **2.9%**. So the class figure is now dominated by **target provenance and one
base definition**, and whether the target is met by finding documents or by re-scoping it is an owner
call. Moving the three anyway would put the *tier* at 17.8% against the measured 14.7% — which is
stated here because holding them is also the lower number, and the reason should be overturnable by a
document rather than by a preference.

**Ordinary rate change was asked to hold at ≤ 12% and reads 14.8%**, with **all four of its rows
crossing from under- to over-prediction** when the base stopped being frozen at tax year 2023. Two of
the four are rule-of-thumb targets, and one of those — `illustrative_1pp_all` — **scores the same
reform as `cbo_opt45_all_rates_1pp`** against a target 23.5% away, so the model cannot agree with both
and this change swapped which one it agrees with (+4.1% → −24.5% on the rule of thumb, +22.4% →
**−1.9%** on CBO's printed option). The class cannot be read without that, and §6.2 item 45 is the
target decision it needs.

**The per-class floor of process rule 4 is built** (`cold_holdout.py --max-class-mean-error`, wired
into `validation-dashboard.yml`), at `ceil(class mean × 1.25)` per class, with classes derived from
each case's own benchmark record and a failure mode for any class left un-gated.

**Provenance.** `secondhand` 12 → **≤ 6**, `model_estimate` 6 → **≤ 4** with a written verdict on every
survivor and a `retire` state that exists. `line_item_differs` stays at 7 or falls; it may not rise
without a recorded range or scope verdict.

> **After Wave B (PR #145): one met, one one row short, the rest satisfied.** `model_estimate` **6 → 4**
> (met). `secondhand` **12 → 7** — one short, and the seventh is `repeal_individual_amt`, a
> locked-holdout id with **nothing to move to**. Every survivor carries a written verdict, and the
> `retire` state **exists, is tested, and is applied to nothing**, which is the correct state while
> owner decision ④ is open. `line_item_differs` rose 7 → **8**, which this criterion permits only with
> a recorded range or scope verdict, and it is a recorded **range**: `eliminate_mortgage.v2`. Published
> targets across both tiers went **75 → 77 of 81**, and **the five rows that left `secondhand` did so
> by finding a document, never by deciding a model estimate was good enough.**

**Coverage.** Every one of the 52 shipped presets has a scorecard row **or** carries no dollar figure
in its label. Zero presets display an accuracy claim keyed to `CBO_SCORE_MAP` membership.

> **After Wave A (PRs #140 and #142): met, and enforced by a test.** Badges **24 → 44**, unbadged
> 28 → 8, the badged set is exactly the set carrying an official figure, and the eight remaining
> no-row presets print no dollar figure — `test_a_preset_with_no_row_may_not_print_a_dollar_figure` was
> pre-registered to fail until H1 struck the four label figures and now passes. Each badge names its
> tier (**16 fitted / 25 reconstruction / 3 out-of-sample**), so a fitted 0.0% and a 701%
> reconstruction no longer share a rating vocabulary. **Two coverage gaps remain and both are
> recorded**: `composer._tier_for` and `results_summary._resolve_tier` still key on legacy map
> membership (one line each, through `badge_tier()`), and **five preset labels quote a figure the
> ledger has since superseded** plus two more that are mis-signed — §6.2 item 43, a single-commit
> rename lane nobody in Waves A/B could take without crossing a file boundary.

**Consistency.** One base default: Tailor, Ask, Explore and Build return the same number for the same
policy *specification*, base attribute included, and a test asserts it across all four constructors.
Where a surface lets the user choose the base, the caption says which one produced the number.

> **After Wave A (PR #142): met.** `DEFAULT_ORDINARY_INCOME_BASE` is read by the dataclass, Tailor,
> the composer, the API and Ask, and `tests/test_base_rule_contract.py` asserts one number across all
> four constructors for three specifications — plus a **grep gate over the whole tree** that fails if
> any constructor re-acquires a literal default of its own. The gate has already earned its keep: it
> fired on H2b's *error message* and the message was reworded rather than the gate exempted. **One
> consistency gap is measured and open**: `DistributionalEngine` does not read the base, so a revenue
> score and a who-pays table off one policy object sit **2.57× apart** (§6.2 item 46), asserted by a
> test that fails with instructions when someone closes it.

**Uncertainty.** Every headline carries an empirically calibrated band from its own class's Tier 1
distribution, plus an estimator-disagreement band wherever two official bodies differ.

### Non-goals, stated so no lane drifts into them

- **No tuning to targets.** A lane that adds a constant reproducing a benchmark has failed regardless
  of the error it closes. The corporate landing factor (0.5785) and the AMT repeal target (\$948.9B,
  which is `amt.py`'s own input) are both named here so nobody arrives at them by accident.
- **The fitted tier's 1.7% is not a target to protect.** It has already lost thirteen rows to three
  different mechanisms and the mean *fell* each time, because every row that left was one it had been
  carrying. If H9 moves six more targets and the fitted tier reads 8% over 15 rows, that is the tier
  becoming honest, not the model regressing. **Read the two tiers together or neither.**
- **No new "validated within X%" claim.** Eight classes, three tiers, seven distributional tables and
  two provenance states do not collapse into one number, and this plan's success criteria are
  deliberately written as five separate figures.
- **No removing a case to go green.** Not from Tier 1, not from LOO, not from the preset catalog.
  H12's demotion moves presets off a *surface*; their scorecard rows stay exactly where they are.
