# Lane SALT — a current-law cap path, and two benchmarks that state their baseline

*Pre-registered 2026-09-11 against `main` @ `6287a90` (Wave A–D merged, H7/PR
#157 last), in this lane's first commit, before a module file was opened.
Sections 0–5 are a reading of the statute and of arithmetic on data already in
the tree; §6 (the outturn) is appended in the lane's last commit.*

Scope: owner decision ⑧ of `planning/HIGH_STAKES_ACCURACY.md` — §3 H7's "SALT
is a separate, joint decision" — and `planning/MODELING_IMPROVEMENT.md` §6.2
item 3. The decision, taken: **build a current-law SALT cap path on P.L. 119-21
sec. 70120, score the app's SALT presets on current law, and make each
benchmark state the baseline its own document was scored on.** The targets do
not move. The **shape input** does.

## 0. Why the module needs a baseline at all

The repository's two SALT benchmarks disagree about what world they are in, and
both are right:

* `repeal_salt_cap` carries PWBM's **+$1,169.0B** (Table 3, *Lifting the SALT
  Cap*), priced against a **permanent $10,000 cap** — the extended-TCJA
  baseline. The same paper's Table 1 scores the identical reform at **$197B**
  against the law as it then stood, a factor of 5.9 apart, and the ledger row
  (`target_revisions.repeal_salt_cap.v2`) says so in terms.
* `eliminate_salt` carries CBO's **−$1,621.0B** (pub. 60557, Option 49),
  measured on a baseline where the $10,000 cap **lapses after 2025** — the
  sentence the module's own `limitation` block already quotes: "Beginning in
  2026, deductions for state and local taxes will not be limited."

Neither baseline is current law. P.L. 119-21 sec. 70120, enacted 4 July 2025,
replaced the lapse with a $40,000 cap that rises 1%/yr through 2029, phases
down above $500,000 of modified AGI, and reverts to $10,000 in 2030. Both
ledger rows record that as "a model gap, not a target one, and one that needs a
baseline-vintage concept the expenditure module does not have". This lane
builds that concept.

The consequence today is a shipped preset that is wrong by construction:
**📋 Repeal SALT Cap** scores **+$1,155.6B** over FY2026-2035 from a fitted
$96.0B/yr, and $96.0B/yr is the cost of repealing a $10,000 cap in a year when
the cap is $40,404. For four of the ten years in the app's own window, "repeal
the $10,000 cap" describes no live reform.

### 0.1 Measured before a file was opened

`scripts/cold_holdout.py --json`, `scripts/run_validation_dashboard.py`,
`scripts/run_loo.py --donor-matrix`, and a preset sweep by stable id on the
app's own window (`FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR)`):

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| Tier 1 — out-of-sample | 26 | **14.5%** | 11.5% | 16 | 22 |
| Tier 2 — fitted | 15 | **1.6%** | 0.0% | 15 | — |
| Tier 2 — … held in place | 26 | **12.4%** | 2.4% | 21 | — |
| Tier 2 — reconstructions | 40 | **55.5%** | 33.6% | 11 | — |
| Tier 2 — leave-one-out | 18 (4 not x-val) | **36.5%** | 30.2% | 5 | — |

The rows this lane can reach:

| row | tier | target | model | error |
|---|---|--:|--:|--:|
| `repeal_salt_cap` | reconstruction | 1,169.0 | 1,155.6 | **1.1%** |
| `eliminate_salt` | reconstruction | −1,621.0 | −1,260.3 | **22.3%** |
| `cbo_opt56_employer_health_income_only` | **Tier 1** | −697.0 | −605.8 | 13.10% |

Expenditures leave-one-out (derived mode): `cap_employer_health` +93.2%,
`eliminate_mortgage` +33.4%, `repeal_salt_cap` **−33.5%** (777.0),
`eliminate_salt` **+33.5%** (1,077.9), `cap_charitable` +24.2%; module mean
**43.6%** (n=5; `eliminate_step_up` excluded by the leakage guard).

Presets, on the app's FY2026-2035 window: `salt-cap-repeal` **+$1,155.559035B**
static, **+$996.289732B** dynamic. `salt-deduction-eliminate` has **no
`PRESET_POLICIES` row at all** — it is a `SCORE_ONLY_ID_BY_LABEL` entry, so
Build quotes CBO's −$1,621.0B as a list price and the engine never runs it.
That is the first finding of the lane and it changes what "score the app's two
SALT presets on current law" can mean: one is scored and one is quoted.

## 1. The mechanism

### 1.1 The statute, transcribed

IRC §164(b)(6)–(7) as amended by **P.L. 119-21 sec. 70120** (enacted
2026-07-04 — *One Big Beautiful Bill Act*), read 2026-09-11 at
`https://www.law.cornell.edu/uscode/text/26/164`. §164(b)(6) caps the aggregate
of §164(a)(1)–(3) and (b)(5) taxes at the **applicable limitation amount**,
"half the applicable limitation amount in the case of a married individual
filing a separate return". §164(b)(7) states the amount:

| taxable year beginning in | applicable limitation amount | married filing separately | threshold amount | MFS threshold |
|---|--:|--:|--:|--:|
| 2025 | $40,000 | $20,000 | $500,000 | $250,000 |
| 2026 | $40,400 | $20,200 | $505,000 | $252,500 |
| 2027 | $40,804 | $20,402 | $510,050 | $255,025 |
| 2028 | $41,212.04 | $20,606.02 | $515,150.50 | $257,575.25 |
| 2029 | $41,624.16 | $20,812.08 | $520,302.01 | $260,151.00 |
| 2030 and after | $10,000 | $5,000 | — (no phasedown) | — |

2027–2029 are "**101 percent** of the dollar amount in effect under this
subparagraph for taxable years beginning in the preceding calendar year",
applied to both the limitation amount and the threshold; they are computed from
the statute's own rule rather than transcribed from a Revenue Procedure,
because the 2027 adjustment is not yet published (today is 2026-09-11) and the
rule is arithmetic rather than an indexed measurement. The 2025 and 2026
figures are the statute's own.

**Phasedown**, §164(b)(7)(B)–(C): the applicable limitation amount is reduced
by **30 percent of the excess (if any)** of modified AGI over the threshold
amount, "but not below $10,000 ($5,000…)", and the phasedown does not apply to
taxable years beginning after 31 December 2029. Modified AGI is AGI increased
by amounts excluded under §§911, 931, 933. So

```
cap(y, magi) = max(10_000, L(y) − 0.30 × max(0, magi − T(y)))
```

and the phasedown is complete — the cap is exactly $10,000 — at MAGI of
$600,000.00 (2025), $606,333.33 (2026), $612,730.00 (2027), $619,190.63 (2028),
$625,715.87 (2029).

### 1.2 Three baselines, named

`SaltCapBaseline` — the shape input this lane adds. Each is a cap path, and
each is the path some document was scored on:

* `CURRENT_LAW` — the table above. **The app's default.**
* `PERMANENT_10K` — $10,000 every year, no phasedown, never indexed: TCJA made
  permanent, which is the extended-TCJA baseline PWBM's Table 3 prices repeal
  against.
* `LAPSED_CAP` — $10,000 through 2025 and **no cap at all** from 2026: the
  Feb/June 2024 CBO baseline Option 49 is measured on.

A reform is priced **against a stated baseline path**, never against an
implicit one:

* `eliminate` (repeal the deduction) is worth the deduction that is actually
  claimed under the baseline in force — the *capped* expenditure, year by year.
* `expand` (repeal the cap) is worth `uncapped − capped` under the baseline in
  force, year by year.

### 1.3 Using a $10,000-cap SOI base under a $40,000 cap

IRS SOI Table 2.1 (TY2023, already transcribed) publishes, per AGI class,
**both** columns: `salt` — "Total state and local taxes", the amount *before*
the cap — and `salt_limited` — the amount actually deductible with §164(b)(6)
in force. The uncapped column does not depend on the cap, so it is usable under
any cap. The capped column is what identifies the **within-class dispersion**
the class averages discard.

Per AGI class `b`, fit a lognormal to the two published moments:

```
mean_b            = salt_amount_b / salt_returns_b               (published)
E[min(X_b, 10000)] = salt_limited_amount_b / salt_returns_b      (published)
```

Two moments, two parameters, one bisection on σ. The deductible amount under a
cap `C` is then `E[min(X_b, C)] × returns_b`, priced at the class's statutory
marginal rate exactly as `DeductionDistribution` already prices the uncapped
one. At `C = $10,000` the fit returns the published limited column **by
construction**, which is the check that the extrapolation is anchored and not
invented: the summed benefit is **$25.020B** against the record's own
`annual_cost = 25.0` — the 0.1% agreement `uncapped_salt_expenditure_billions`
already documents from the other direction.

Nothing here is fitted to a validation target. The fit's data are two published
SOI columns; its check is a third published number.

**The phasedown needs AGI within the class, not just SALT.** The phase-out
range ($500,000 → $600,000-odd) lies entirely inside SOI's $500,000–$1,000,000
class, whose published mean AGI is $680,978 — above the range. Evaluating the
phasedown at the class mean therefore puts the *whole* class at $10,000, which
is a step function at a published class boundary rather than a measurement. So
AGI within each class is given a bounded-Pareto distribution fitted to that
class's own published mean and bounds (`agi_less_deficit ÷ returns`), the same
technique lane W7's decedent ladder uses, and the cap is read at each slice.
The refinement is worth **$6.4B over ten years** on the eliminate leg (317.2 →
323.6) and **−$6.4B** on the repeal leg; it is taken because the class-mean
path is a step at a boundary, not because it is large.

**Cap dollars are nominal and the base is not.** A $40,000 cap indexed at
**1%/yr** by statute sits against SALT payments growing at the expenditure
record's own **3%/yr**, so the cap's bite widens every year of the window
without any new constant. This is the same mechanism Wave 4's Option 56 lane
found for employer premiums, and here the source is the statute rather than an
agency's design note.

**What it cannot see**, recorded now rather than after the result:

1. **New itemisers.** SOI TY2023 observes the population that itemised under a
   $10,000 cap and TCJA's larger standard deduction. Raising the cap to $40,000
   pulls filers who took the standard deduction into itemising, and their SALT
   is not in the table at any AGI. JCT's JCX-45-25 sizes that channel for the
   mortgage deduction — SALT claimants 11.8M → 17.8M returns — so the omission
   is large and one-directional: the model **under-counts** the cap's value.
2. **Filing status.** The statute states every amount by filing status; SOI
   Table 2.1's "All returns" panel has none. The cap path is transcribed by
   status (table above) and the **non-MFS column is the one applied**, because
   the base has no status dimension. MFS is a small and unmeasured share of
   itemisers here.
3. **SALT paid is assumed independent of AGI within a class.** It is not — SALT
   rises with income — so within the $500,000–$1,000,000 class the model gives
   the higher-SALT returns too generous a cap, again under-counting.
4. **The SOI base is not aged from TY2023 to the window's first year.** That is
   the module's existing convention (`SOI_BASE_YEAR = 2023` is declared and
   read by nothing), kept deliberately so this lane moves one thing; aging it
   would raise the uncapped level 9.3% and move rows this lane has no mandate
   over. Carry-over.
5. **No behavioural change of its own.** The SALT offset magnitude stays the
   unsourced 0.05 lane H7 left and searched for. Out of scope (§5).

### 1.4 Which benchmark scores which baseline

`repeal_salt_cap` scores `PERMANENT_10K` and `eliminate_salt` scores
`LAPSED_CAP`, declared in `scenarios.py` in the commit **before** the commit
that first scores them, with the document sentence attached. The app's preset
and every other caller default to `CURRENT_LAW`.

Each factory's fitted annual is kept **only for the baseline it was fitted
to**: `create_repeal_salt_cap`'s −96.0 is the cost of repealing a permanent
$10,000 cap and `create_eliminate_salt_deduction`'s 104.7 is the value of an
uncapped deduction, and neither is the current-law answer to its own question.
On any other baseline the factory passes `annual_revenue_change_billions=None`
and the existing `reported` branch falls through to the structural path — no
new mode, no retuned constant.

### 1.5 A ledger note: `target_revisions.py` cannot carry this

The decision as written says "re-register both targets as new rows … a new row,
old row kept with `superseded_by`". `target_revision_problems()` **refuses**
that: its fifth invariant is that "a supersession actually moves the target — a
'revision' that restates the old figure is bookkeeping noise and hides the rows
that matter." Both targets are unchanged, so a `.v3` in that ledger would fail
the repository's own check.

The Tier 1 rule the decision points at (`iija_2021_discretionary.v2`,
`treasury_capgains_39_plus_stepup_elim.v2`) lives in `preregistered.py`, which
**does** have a place for a shape input that moves while a target stands still.
Tier 2 has no such manifest. So the two-commit discipline is transposed rather
than skipped: the baseline declaration is entered into `scenarios.py` as an
inert table in the ledger commit and becomes the scoring input in the next one,
and a test asserts the declaration and the kwarg agree. **That Tier 2 has no
shape-input manifest is a finding and an owner item** (§7).

## 2. Files

Owned: `fiscal_model/tax_expenditures_core.py`,
`fiscal_model/tax_expenditure_distributions.py`,
`fiscal_model/tax_expenditures_factory.py`; the two SALT rows in
`fiscal_model/validation/scenarios.py`; the two SALT entries' `notes` /
`description` in `fiscal_model/app_data.py`; one self-contained caption
function plus its call line in `fiscal_model/ui/tabs/results_summary.py`;
tests. No constant is retuned, no target moves, no `.github/` file and no
shared doc is touched.

## 3. Pre-registered outturns

Computed before a module file was opened, from the arithmetic in §1 on data
already in the tree.

**A. Neither benchmark moves on the scorecard.** Both score `reported` with the
fitted annual on the baseline it was fitted to.

| row | before | predicted after |
|---|--:|--:|
| `repeal_salt_cap` | 1,155.6 (**1.1%**) | 1,155.6 (**1.1%**) |
| `eliminate_salt` | −1,260.3 (**22.3%**) | −1,260.3 (**22.3%**) |

**B. Leave-one-out moves by 0.02 of a billion, and only on one row.** LOO
replaces the annual with the derived start-year one. `eliminate_salt` on
`LAPSED_CAP` derives the uncapped level, which is the same
`uncapped_salt_expenditure_billions()` it derives today: **1,077.9 → 1,077.9,
to the cent**. `repeal_salt_cap` on `PERMANENT_10K` derives
`−(89.5497 − 25.0198) = −64.5299` where it derives `−(89.550 − 25.0) =
−64.550` today, because the capped leg stops reading the record's rounded
`annual_cost = 25.0` and starts reading the same SOI column that constant
agrees with to 0.1%:

| LOO row | before | predicted after |
|---|--:|--:|
| `repeal_salt_cap` | 777.0 (−33.5%) | **776.8 (−33.5%)** |
| `eliminate_salt` | 1,077.9 (+33.5%) | **1,077.9 (+33.5%)** |
| Expenditures module mean | 43.6% (n=5) | **43.6% (n=5)** |
| LOO aggregate | 36.5% (n=18) | **36.5% (n=18)** |

The leakage guard must still pass on both: derived annuals 64.53 and 89.55
against targets-over-ten of 116.9 and 162.1.

**C. One preset moves, by a third.** `salt-cap-repeal` on the app's
FY2026-2035 window, static, is the sum of the current-law repeal path times the
1.05 magnifying offset:

| year | uncapped | capped (current law) | repeal |
|---|--:|--:|--:|
| 2026 | 89.55 | 39.92 | 49.63 |
| 2027 | 92.24 | 41.00 | 51.23 |
| 2028 | 95.00 | 42.11 | 52.89 |
| 2029 | 97.85 | 43.24 | 54.61 |
| 2030 | 100.79 | 25.79 | 74.99 |
| 2031 | 103.81 | 25.97 | 77.84 |
| 2032 | 106.93 | 26.14 | 80.78 |
| 2033 | 110.13 | 26.31 | 83.83 |
| 2034 | 113.44 | 26.46 | 86.97 |
| 2035 | 116.84 | 26.62 | 90.23 |
| **total** | | | **703.02** |

* `salt-cap-repeal` static **+$1,155.56B → +$738.17B**, a fall of **36.1%**.
* `salt-cap-repeal` dynamic **+$996.29B → $636 ± 20B**.
* Every other preset scores to the cent what it scored before.

A Decision 6 caption ships with it, computed from the scored result and stating
the **baseline change** rather than only the number: the old figure repealed a
$10,000 cap that current law does not impose until 2030.

**D. The quoted preset gets a sentence, not a number.**
`salt-deduction-eliminate` has no `PRESET_POLICIES` row, so nothing scores. Its
`notes` will say which baseline CBO's −$1,621.0B is measured on, and that on
current law the same repeal is worth **+$339.7B** over FY2026-2035 — 4.8×
smaller, because from 2026 to 2029 current law already denies most of the
deduction CBO's baseline allows. The **target is not touched**.

**E. Tier 1 is byte-identical.** 26 cases, 14.5% mean, 16/26 within 15%, 22/26
within 25%; `cbo_opt56_employer_health_income_only` stays at **13.10%**. It
runs through this module and must not move: nothing in the employer-health path
reads a SALT cap.

**F. Composition is unchanged.** Fitted 15 @ 1.6%, held-in-place 26 @ 12.4%,
reconstructions 40 @ 55.5%, revised targets 22, 81 scorecard rows. Both SALT
rows are already reconstructions (their targets were revised in Wave 4) and
stay there; no row enters or leaves a tier, so
`build_validation_headline.py --check` should pass unregenerated.

**G. The unpredicted check that is worth more than any of the above.** JCT's
own score of **sec. 70120 itself** is in this repository already:
`pl119_21_salt_cap_40k`, JCX-35-25 line 20, **+$946,209M over FY2025-2034** —
JCT scoring the current-law cap path against a baseline in which the cap
lapses, which is exactly the quantity this lane computes with the sign
reversed. On FY2025-2034 the new mechanism returns **$685.3B** static,
**$719.6B** with the offset, **−24.0%** from JCT. Pre-registered band:
**−24 ± 4%**. That row's own `known_limitations` say "the app's SALT component
represents the flat $10,000 cap only, so this row is scored against a design
the module cannot express" — after this lane the module **can** express it.
Rewiring that benchmark is a different module's runner (`tcja.py`) and a second
decision, so it is reported and **not** taken (§5, §7).

## 4. Falsification

The lane fails, and is reverted rather than argued, if any of these is true
after the change:

1. **Tier 1 is not byte-identical.** 26 rows, every figure, `cbo_opt56` above
   all.
2. **Any constant is fitted.** No number in this lane may be chosen so that a
   benchmark lands closer to its target. The two SALT annuals keep the values
   they have; the lognormal σ is identified by two *published* SOI columns and
   the bounded-Pareto α by a *published* class mean.
3. **Either preset lands on its target by construction.** The current-law
   repeal at $738.2B is **36.9% from PWBM's $1,169.0B** and is meant to be:
   they are answers to different questions. A current-law figure arriving
   within a few percent of a permanent-cap target would mean the baseline is
   not reaching the score.
4. **The cap path does not reproduce the published capped column.** At $10,000
   the fitted distribution must return the SOI `salt_limited` benefit to better
   than 0.5% (predicted: exact by construction, $25.020B).
5. **The leakage guard fires**, or either SALT row leaves the LOO denominator.
6. **A second preset moves.** Only `salt-cap-repeal` may move.

## 5. Out of scope

* **The SALT behavioural magnitude (0.05).** Lane H7 searched and found nothing
  — "CBO 58635 names the channel and prices nothing; Yale Budget Lab prices a
  different dose of a different expenditure" — and this lane does not reopen
  it. It multiplies both the before and the after figures, so it cancels out of
  every comparison here except the levels themselves.
* **Aging the SOI base from TY2023.** §1.3 note 4.
* **`pl119_21_salt_cap_40k`.** §3 G.
* **The `eliminate_salt` target.** CBO's −$1,621.0B stays exactly where it is;
  so does PWBM's +$1,169.0B. This lane moves a shape input, not a target.
* **`eliminate_mortgage`'s interaction with the SALT cap.** Yale's own finding
  that raising the SALT limit pulls filers into itemising and enlarges the
  *mortgage* expenditure ($323B → $497B between a $10,000 and a $20,000 limit)
  is quoted in `OFFSET_DIRECTIONS` already. Wiring it would move a second
  benchmark on a second module's base.
* **`preset_handler.py`, `app_pages/`, `deficit_target.py`, presentation
  flags.** H12's lane.

## 6. Outturn

*Appended 2026-09-11 in the lane's last commit, measured on the branch with
every change in.*

**Every pre-registered figure landed. One preset moved, one leave-one-out row
moved by $0.2B, and nothing else in the repository moved at all.**

### 6.1 The pre-registration, row by row

| pre-registered | predicted | actual | |
|---|--:|--:|---|
| A. `repeal_salt_cap` scorecard | 1,155.6 (1.1%) | **1,155.6 (1.1%)** | ok |
| A. `eliminate_salt` scorecard | −1,260.3 (22.3%) | **−1,260.3 (22.3%)** | ok |
| B. `repeal_salt_cap` LOO | 776.8 (−33.5%) | **776.7 (−33.6%)** | ok |
| B. `eliminate_salt` LOO | 1,077.9, to the cent | **1,077.9** | ok |
| B. Expenditures LOO module mean | 43.6% (n=5) | **43.6% (n=5)** | ok |
| B. LOO aggregate | 36.5% (n=18) | **36.5% (n=18)** | ok |
| C. `salt-cap-repeal` static | +$738.2B | **+$740.3B** | +0.29% |
| C. `salt-cap-repeal` dynamic | +$636 ± 20B | **+$646.6B** | ok |
| C. every other preset | to the cent | **to the cent** | ok |
| D. current-law `eliminate_salt` | +$339.7B | **+$337.6B** | −0.63% |
| E. Tier 1 | byte-identical | **byte-identical** | ok |
| F. composition | unchanged | **unchanged** | ok |
| G. JCT sec. 70120 anchor | −24 ± 4% | **−23.58%** | ok |

`scripts/cold_holdout.py --json` and `scripts/run_validation_dashboard.py` are
**byte-identical** to `main`; `scripts/run_loo.py --donor-matrix` differs in
**one line**; `scripts/check_readiness.py --strict` is byte-identical;
`build_validation_headline.py --check` passes unregenerated (77 published of
81); ruff is clean; both cold-holdout gate commands and the leave-one-out
ceiling pass as the workflow runs them.

**The shipped preset.** 📋 Repeal SALT Cap **+$1,155.56B → +$740.31B** static
(−35.9%) and **+$996.29B → +$646.62B** dynamic (−35.1%), with the Decision 6
caption in `results_summary.salt_current_law_caption`. The other 52 presets
score to the cent in both engine modes.

### 6.2 The one deviation from the pre-registration, and why

§3's figures were computed with within-class **AGI held at its SOI level**
while the SALT amounts were aged; the implementation ages both. Freezing the
incomes a phasedown is read against while growing the taxes it limits is not a
coherent pair — the statute indexes the *threshold* at 1%/yr and indexes
nothing about incomes, which is the whole mechanism — so the coherent choice
was taken and the deviation is reported rather than smoothed. It is worth
**+0.29%** on the repeal leg (738.17 → 740.31) and **−0.63%** on the eliminate
leg (339.75 → 337.61). No pre-registered band is crossed.

### 6.3 Findings

1. **`salt-deduction-eliminate` is quoted, not scored.** It has no
   `PRESET_POLICIES` row at all — it is a `SCORE_ONLY_ID_BY_LABEL` entry — so
   Build prints CBO's −$1,621.0B as a list price and the engine never runs it.
   "Score the app's two SALT presets on current law" therefore has one scored
   half and one quoted half, and the quoted half gets a sentence naming the
   baseline rather than a number. The current-law figure the module *would*
   return is **+$337.6B**, a fifth of the quoted one.
2. **The Tier 2 ledger refuses a no-move re-registration, and it is right to.**
   `target_revision_problems()`'s fifth invariant fails a supersession that
   restates its own figure. Both targets stand, so the `.v3` rows the decision
   asked for cannot exist in `target_revisions.py`. **Tier 2 has no
   shape-input manifest** — Tier 1's `preregistered.py` does, which is how
   `iija_2021_discretionary.v2` and `treasury_capgains…v2` were done — so the
   declaration went into `scenarios.SALT_SCORING_BASELINES`, inert in one
   commit and the scoring input in the next, with a test that fails if the two
   drift. Whether Tier 2 should grow the same manifest is an owner item.
3. **The distributional path is now inconsistent with the revenue path, and
   the test that caught it was the synthetic one.** Forcing the synthetic
   bracket reference moved the SALT distributional benchmark **0.0pp →
   24.9pp** until its runner was given JCX-4-24's own January 2024 baseline.
   The **default** microsim path did not move at all — because
   `microsim/engine.py` sets `self.salt_cap = 10000` and
   `distribution_effects.py` reads `getattr(policy, "salt_cap", 10000)`, so
   the who-pays table prices a $10,000-cap world for the same policy object
   whose revenue score is now current law. That is a real inconsistency in a
   green-tier surface and this lane owns neither file. Carry-over.
4. **JCT has scored this mechanism and the repository already carries the
   score.** `pl119_21_salt_cap_40k` is JCX-35-25 line 20, **+$946,209M over
   FY2025-2034** — sec. 70120 measured against a baseline in which the cap
   lapses, which is this module's repeal quantity with the sign reversed. On
   that window the new mechanism returns **$723.1B, −23.6%**. Its row's own
   `known_limitations` say "the app's SALT component represents the flat
   $10,000 cap only, so this row is scored against a design the module cannot
   express"; after this lane the module **can** express it, and that benchmark
   is run by `tcja.py`. Rewiring it changes a benchmark's runner and is an
   owner decision, not this lane's.
5. **The −23.6% has a named direction and it is not the elasticity.** SOI tax
   year 2023 observes the population that itemised under a $10,000 cap and
   TCJA's larger standard deduction. JCT's JCX-45-25 puts SALT claimants at
   **11.8M → 17.8M returns** under the $40,000 cap, so the filers the raised
   cap pulls into itemising are absent from the base at every income — a
   one-directional omission that makes the model **under**-count exactly as
   observed. The two smaller omissions run the same way: SALT is assumed
   independent of AGI within a class when it rises with income, and the base
   is not aged from TY2023 to the window's first year.
6. **Fifteen of the 22 AGI classes cannot carry a bounded-Pareto AGI fit**, and
   the reason is a fact about the published table rather than a defect: a
   bounded Pareto on $5,000–$10,000 cannot produce a mean above $6,931 and SOI
   publishes $7,777, so those classes are flatter than Pareto. Every one of
   the fifteen has an upper bound at or below $200,000, and no published SALT
   phasedown starts below $250,000, so not one of them is reachable.
7. **The AGI refinement is small and was taken for its shape, not its size.**
   Reading the phasedown at the class mean instead of across the class moves
   the eliminate leg by **2.0%** ($317.2B → $323.6B over ten years on the
   pre-registration's own arithmetic). It was taken because the class-mean path
   is a *step function at a published class boundary* — SOI's $500,000–
   $1,000,000 class has a mean AGI of $680,978, above the 2026 phase-out
   completion of $606,333, so the whole class drops to $10,000 at once.
8. **`SOI_BASE_YEAR = 2023` is declared and read by nothing.** The module's own
   comment says amounts "are grown from this year to a policy's first year";
   they are not. Aging them would raise the uncapped level 9.3% and move rows
   in three other reforms, so it is deliberately untouched here.

## 7. Carry-overs and owner items

* **Owner item.** Should Tier 2 grow a shape-input manifest, as
  `preregistered.py` has for Tier 1? `SALT_SCORING_BASELINES` is this lane's
  local answer and does not generalise.
* **Owner item.** `pl119_21_salt_cap_40k` can now be scored by the expenditure
  module against `SaltCapBaseline.LAPSED_CAP` rather than by `tcja.py`'s flat
  $10,000 component. Finding 4 gives the figure it would read.
* **Carry-over.** `microsim/engine.py` and `distribution_effects.py` hard-code
  a $10,000 SALT cap, so a policy object's revenue score and its distributional
  table now disagree about what year it is (finding 3).
* **Carry-over.** Aging the SOI base from TY2023 (finding 8).
* **Carry-over.** New itemisers under a raised cap (finding 5) — the largest
  named term in the −23.6%, and the one that would need a base outside SOI
  Table 2.1's itemiser panel.
* **Carry-over.** The MFS column of the statutory path is transcribed and
  unused: SOI Table 2.1's "All returns" panel has no filing-status dimension.
* **Still open from H7.** The SALT behavioural magnitude of 0.05 is unsourced
  and was not touched (§5).
