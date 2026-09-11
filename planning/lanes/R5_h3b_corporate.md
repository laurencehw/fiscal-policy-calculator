# R5 — H3b: the corporate mechanism, with CBO's own haircuts

*Lane of `planning/ROUTE_TO_8_5.md` §1 R5 (Wave F), which is
`HIGH_STAKES_ACCURACY.md` §3 H3b. Branch `model/r5-h3b-corporate`, worktree from
`main` @ `f6a9b28`. Owner decision ⑤ — "hold `reported` until H3b lands, then
re-measure once" — is answered in §6 of this document and nowhere else.*

*Everything in §0 was measured on this tree before a line of §1 was written.
Every figure below is from one of `scripts/cold_holdout.py --json`,
`scripts/run_validation_dashboard.py`,
`fiscal_model.validation.specialized_business.validate_corporate_policy`,
`fiscal_model.ui.estimator_ranges.corporate_estimator_range`, a preset sweep
through `fiscal_model.preset_handler.create_policy_from_preset`, or a `file:line`
in a named repository. Nothing is recalled.*

---

## §0 — BEFORE, measured

### 0.1 The three published corporate targets, both modes

`validate_corporate_policy(..., mode=...)`, the Decision 1 sweep API:

| Benchmark | Target $B | `reported` $B | err | `derived` $B | err | Row winner |
|---|--:|--:|--:|--:|--:|---|
| `biden_corporate_28` (fitted) | −1,347.0 | −1,397.21 | **3.73%** | −1,292.62 | 4.04% | reported, by 0.31pp |
| `biden_corporate_28_fy2022` | −857.8 | −1,397.21 | 62.88% | −1,292.62 | **50.69%** | derived, by 12.19pp |
| `trump_corporate_15` | +673.1 | +1,491.76 | **121.63%** | +1,545.24 | 129.57% | reported, by 7.94pp |
| **mean abs** | | | **62.75%** | | **61.43%** | **derived, by 1.32pp** |

Both means reproduce what `CLAUDE.md` records to the second decimal, so the
population PR #122 measured has not moved. `reported` wins two rows of three and
loses the mean; the row it loses is the only one whose *scope* matches the
factory's shape (the FY2022 Green Book row is the one rate-only corporate row any
Green Book prints, and the word GILTI does not appear in its Proposal section).

### 0.2 Tier 1 and the class ceiling

`cold_holdout.py --json`: **n = 22, mean 11.6%, median 8.9%, 18/22 within 15%,
19/22 within 25%.** (Four rows fewer than the 26 `ROUTE_TO_8_5.md` §1 was written
on; R2 moved them.) Class `corporate`: **n = 1, mean 44.5%, error mass 44.5**,
`cbo_opt64_corporate_rate_1pp` at −196.08 against −135.7.

The plan's three starting points are all **unchanged**: `cbo_opt64` **44.5%**,
`biden_corporate_28_fy2022` **−62.9%**, `trump_corporate_15` **121.6%**.

### 0.3 The H3a estimator span

`corporate_estimator_range`, reproducing `HSB_h3a_corporate_range.md` §6.3
finding 4 to the cent:

| mode | step | total $B | marginal share | position |
|---|--:|--:|--:|---|
| `reported` | +1pp | −199.60 | 82.29% | larger, outside by 6.75 |
| `reported` | +7pp | −1,397.21 | 82.29% | larger, **outside by 47.27** |
| `derived` | +1pp | −196.08 | 80.83% | larger, outside by 3.23 |
| `derived` | +7pp | −1,292.62 | **76.13%** | **inside** |

### 0.4 Calibrated tiers and LOO

fitted n=15 @ 1.6%; held-in-place n=26 @ 12.4%; reconstructions n=38 @ 37.5%
(sub-population `Corporate` **n=2 @ 92.3%**); LOO aggregate 36.5% (n=18), and the
suite still has **no `Corporate` row** — the module is `not cross-validatable`
for the reason `CORPORATE_PER_POINT_YIELD.md` §7(iii) gives.

### 0.5 The applicability test for the haircut, run before §1 was written

The lane's headline mechanism is a *ratio*, so whether it applies to this base is
arithmetic, not judgement, and the arithmetic is part of the BEFORE measurement.
`fiscal_model/data_files/corporate/soi_table11_corporate_tax_items.csv` — the file
the derived path already reads — carries `net_operating_loss_deduction_thousands`
beside `income_subject_to_tax_thousands`:

| TY | income subject to tax $B | NOL deduction $B | NOL ÷ (base + NOL) |
|--:|--:|--:|--:|
| 2019 | 1,733.3 | 212.0 | 10.90% |
| 2020 | 1,780.3 | 169.3 | 8.69% |
| 2021 | 2,422.1 | 263.9 | 9.82% |
| 2022 | 2,879.1 | 377.1 | **11.58%** |

CBO's haircut is **12.8%** of positive net income (§1.1). The two are the same
losses. §1.1 states what follows and §4 states the condition under which it would
have been wrong to act on it.

---

## §1 — The mechanism, per the plan's four items, with its source

### 1.1 Loss-firm haircut — **transcribe, test, and expect to refuse**

**The source, verified at commit.** `github.com/US-CBO/business-investment-model`
@ **`6cb4cea63591d82fa6c6cfe7cf5cb05e3c63732d`** (2026-02-25), cloned read-only.
`source_code/Create_Tax_Data.prg:32-33`:

```
 series dmyrevx=0.80
 series dmyrevnfc=0.85
```

Derivation, `:21-27`, quoted in full because the lane turns on what it says:

> *An adjustment to the statutory corporate tax rate is necessary because it is
> not relevant for loss-making firms or for nonprofits. In 2005, a mid-cycle
> year, the ratio of net income on returns of active corporations
> ($1,948,655,133 thousand from the SOI) was 87.2% of net income on returns with
> positive net income ($2,234,882,109 thousand). Rounding that off, a factor of
> 0.85 is applied to the tax rate for nonfinancial corporations. Nonprofits
> accounted for a bit more than 6% of total investment in private fixed
> nonresidential capital, on average, over the sample (7.1% in 2005). Combining
> that with the adjustment for loss-making firms and rounding, a factor of 0.80
> is applied to the statutory tax rate for investment in private nonresidential
> capital.*

Applied at `:69-70` as `rtcorpx = dmyrevx * (rtcgfs + rtcgsl * (1 - rtcgfs))`.

**Deviation from the plan's own description, recorded.** `ROUTE_TO_8_5.md` §1 R5
and the task brief describe 0.80/0.85 as **"financial vs non-financial"**. CBO's
comment says otherwise and `grep -rn dmyrev source_code/` returns no third
series: **0.85 is loss-making firms alone (nonfinancial corporates) and 0.80 is
0.85 further reduced by the nonprofit share of nonresidential investment**
(0.85 × 0.94 = 0.799). There is no financial-sector haircut in the source, so the
brief's "by sector if the receipts detail supports it" cannot be followed as
written — there is no sector split to apply.

**Why it is expected not to apply, and the test that decides it.** CBO's factor
multiplies a **statutory rate** in a user-cost-of-capital expression, to convert
an economy-wide marginal investment return into the taxed part of it. This
module's derived path multiplies a **base**, and that base is
`projected_statutory_base = CBO receipts ÷ 0.21 × 1.0083` — receipts, which are
what loss-making firms' zero tax already produces. Three independent readings say
the losses are in there already:

1. **CBO itself un-applies the factor where the other input already carries it.**
   `Create_Tax_Data.prg:172-175`: *"Take-up rates for Section 179 and bonus
   depreciation are less than 1 partly because of the same factors that cause
   dmyrevx to multiply the statutory corporate tax rate… **To avoid
   double-counting** when multiplying the effective tax rate by the PDV of
   depreciation allowances, the take-up rates… are divided by dmyrevx."* That is
   a source-level precedent for exactly the question this lane asks.
2. **The repository's own denominator already nets it.**
   `scripts/corporate_yield_reconciliation.py`'s docstring, on `B_average`:
   *"already nets credits, **NOLs**, shifting and every other reason receipts
   fall short of profits times the rate."* Every published marginal share in
   `CORPORATE_PER_POINT_YIELD.md` §4b — 55.1%, 55.9%, 64.4%, 79.5% — is measured
   against that denominator, so a haircut applied to the numerator would be
   compared against a denominator that already carries it.
3. **The measurement in §0.5.** SOI's income subject to tax is net of an NOL
   deduction running 8.69–11.58% of the pre-NOL base (10.25% mean, 11.58% in the
   anchor year TY2022) against CBO's 12.8%.

**The decision rule, fixed here.** The haircut is applied **only if** a reading of
the derived base can be shown *not* to net loss firms. §0.5 shows it does. So the
lane's §1.1 deliverable is a **transcription and a refusal**, not a multiplier:
CBO's two constants and their SOI derivation go into a data file with the commit
SHA and the line numbers, a loader and a computed applicability test go into
`corporate.py`, and a test pins the arithmetic so the refusal is checkable rather
than asserted. **No constant is multiplied into any score.**

**What it would have done, stated in advance so that not doing it is visible.**
×0.85 on `derived`: `cbo_opt64` −196.08 → −166.67, **44.50% → 22.82%**;
`trump_corporate_15` +1,545.24 → +1,313.45, **129.57% → 95.14%**;
`biden_corporate_28_fy2022` −1,292.62 → −1,098.73, **50.69% → 28.09%**;
`biden_corporate_28` −1,292.62 → −1,098.73, **4.04% → 18.43%**. That lands §3's
bands on two rows of three and destroys the one row with a clean document behind
it — which is the hazard `ROUTE_TO_8_5.md` §1 R5 names in advance ("a haircut
moves both corporate rows the same way, so it cannot fix both if they miss in the
same direction"), now measured rather than predicted.

### 1.2 Credit carryforwards (§38(c), §904(c)) and CAMT — a data-acquisition step

`CORPORATE_PER_POINT_YIELD.md` §7(i) names this as the one component of the
JCT–Treasury wedge with a published *mechanism* behind it — CBO's 2018 Option 24
text: *"An increase in the corporate tax rate would increase corporations' ability
to use tax credits, rather than carrying them forward to a future year… That use
of credits would reduce revenues"* — and says the quantity is the **carryforward
stock**, which is in the Form 3800 and Form 1118 statistics rather than in SOI
Table 11, and that CAMT (TY2023, after every SOI year the module reads) is a
second such item.

The lane runs the search against irs.gov, IRS SOI, JCT and Treasury. **If a
published carryforward stock or a CAMT-liable taxable-income base is obtainable,
it is transcribed with page references and priced as a marginal credit-absorption
share; if it is not, the search is recorded per source, with what it would have
moved.** No share is asserted in either case.

**Direction, declared in advance, because it is not the one the lane would
prefer.** The derived path already books a credit haircut: `B_cr = B_stat × r`
with `r = 0.7085`, i.e. **29.15% of every extra pre-credit dollar is assumed
absorbed by extra credits** — the average-equals-marginal substitution the
module's own docstring flags as its weakest point. The §904 leg computed from the
data already in the file (`FTC ÷ 0.21 ÷ B_stat` = 18.55% of the base) is
**smaller** than 29.15%, so a bottom-up marginal credit share may well come in
below the average one and move the row **up**. That is pre-registered as a
possible regression, not a surprise.

### 1.3 Sourced behavioural offsets — a documented null, plus one measured finding

`CORPORATE_PER_POINT_YIELD.md` §5(c) already established the null: JCT publishes
five corporate behavioural margins (JCX-46-11 p. 10) and **no parameter**; PWBM
defers to unstated "estimates of profit shifting elasticities from JCT staff";
Treasury publishes nothing; and the one house that states a parameter, Tax
Foundation (Feb 2021), uses Heckemeyer & Overesch's **0.8** — which is already
`PROFIT_SHIFTING_SEMI_ELASTICITY`. The lane does not re-open a settled search;
it may not assert a share, and §4 makes that a falsification condition.

What the lane adds is a **measurement** of the module's own entity-choice leg.
`_estimate_passthrough_shift` compares the new corporate rate to a hard-coded
29.6% individual effective rate and returns `0.0` whenever the corporate rate is
lower. At +1pp (22%), +7pp (28%) and −6pp (15%) it is lower, so the leg returns
**exactly zero for every corporate benchmark in the repository and for every rate
cut by construction**. The lane reports this; it does not replace it, because
there is no published parameter to replace it with (§1.3 first paragraph).

### 1.4 The direction asymmetry — model only if sourced, else document

Tax Foundation *Options 2.0* is the only edition pricing both directions in one
model: 21%→28% at **$126.6B/pt**, 21%→15% at **$163.2B/pt** — a point of cut
costs **29%** more than a point of increase yields. `derived`'s semi-log offset
`static × β × (τ₀ + Δτ)` produces the asymmetry in the right direction at about
half the published size; `reported`'s flat 12.5% produces none at all (its
marginal share is 82.29% at +1pp, +3pp and +7pp alike, §0.3). **No sourced
mechanism produces the published 29% that is not already `β`, so the lane
documents the comparison and changes nothing.**

---

## §2 — Files

Owned and opened:

- `fiscal_model/corporate.py` — the `derived` branch; `CORPORATE_APP_MODE` **in
  the final commit only** (§6).
- `fiscal_model/data_files/corporate/cbo_loss_firm_haircut.csv` — new; CBO's two
  constants, their SOI 2005 derivation figures, commit SHA and `file:line`.
- `scripts/corporate_marginal_share.py` — new; decomposes the derived path's
  implied marginal share into its factors and prints the §1.1 refusal arithmetic
  and the §1.3/§1.4 measurements, so none of them has to be believed.
- `fiscal_model/validation/core.py` and `fiscal_model/validation/scenarios.py` —
  `known_limitations` on the corporate rows only.
- `fiscal_model/ui/tabs/results_summary.py` — Decision 6 captions, **final commit
  only**, extending the existing corporate caption functions in place.
- `tests/` — `tests/test_corporate_derived.py` and a new
  `tests/test_corporate_loss_firm_haircut.py`.

Not opened: `policies_core.py`, `scoring_engine.py` (R4); `trade.py` (R8);
`preregistered.py`, `benchmark_sources.py`, `cbo_scores.py`, `target_revisions.py`
(no target moves — §5); `CLAUDE.md`, `README`, `NEXT_STEPS`,
`MODELING_IMPROVEMENT`, `CHANGELOG`, `HIGH_STAKES_ACCURACY`, `ROUTE_TO_8_5` and
the workflow gate values (docs-sync lane).

---

## §3 — Pre-registered

Bands are `ROUTE_TO_8_5.md` §1 R5's, re-derived on §0's current values, which are
unchanged from the ones the plan quotes.

| # | Quantity | Now | Pre-registered |
|--:|---|--:|---|
| 1 | `cbo_opt64_corporate_rate_1pp` | 44.50% | **30 ± 8** |
| 2 | `biden_corporate_28_fy2022` | −62.88% (`reported`) | **−45 ± 10** |
| 3 | `trump_corporate_15` | 121.63% (`reported`) | **90 ± 20** |
| 4 | `biden_corporate_28` | 3.73% / 4.04% | moves in `derived` **only**; `reported` byte-identical |
| 5 | derived implied marginal share, +1pp | 80.83% | **falls toward the published 55–80% band, and is not set to a number inside it** |
| 6 | Tier 1 mean | 11.6% (n=22) | moves by `cbo_opt64` alone, and by nothing else |
| 7 | every Tier 1 row except `cbo_opt64` | — | **byte-identical** |
| 8 | LOO `--donor-matrix` | — | **byte-identical** (no corporate row exists to move) |
| 9 | fitted tier | n=15 @ 1.6% | unchanged unless a target moves, and no target moves |

**§3.1 — The outcome this lane actually expects, stated as a prediction.** §0.5
has already run §1.1's decision test and it returns "already netted". So rows 1,
2 and 3 are predicted to **miss their bands by not moving**, and the lane's
result is a refutation plus §6's re-measurement. This is written here, before
§1 is implemented, precisely so that a later reader can tell the difference
between a lane that found this and a lane that decided it afterwards. If §1.2's
search yields a transcribable stock, rows 1–3 move by that and by nothing else.

**§3.2 — The Decision 1 comparison rule, fixed before (A) is implemented.**
Owner decision ⑤ is "hold `reported` until H3b lands, then re-measure once." The
flip ships **if and only if both** of the two metrics `CLAUDE.md` records favour
`derived` **on the finished tree**:

- **Metric 1 — published corporate targets.** Mean absolute error over the three
  published targets (`biden_corporate_28`, `biden_corporate_28_fy2022`,
  `trump_corporate_15`) via `validate_corporate_policy(..., mode=...)`.
  `derived` must be **strictly lower** than `reported`. No tie-break, no
  re-weighting, and the three rows are the population PR #122 left — this lane
  registers no new benchmark.
- **Metric 2 — H3a's four-house estimator span.** At the **+7pp** step every
  shipped corporate preset uses, `corporate_estimator_range(...).model_position`
  must be `"inside"` for `derived` and not `"inside"` for `reported`.

If either fails, `CORPORATE_APP_MODE` stays `reported` and the lane says so.
If `check_readiness.py --strict` blocks the flip, the lane does **not** flip,
reports, and exempts nothing. A fitted row rated Poor after a flip is a finding
to be reported, never exempted.

**§3.3 — Expected preset moves under each outcome, measured in advance.** Swept
through `create_policy_from_preset` on the app's own FY2026–2035 window, 45
scoreable presets × {static, dynamic}. **Exactly two presets differ between the
modes; the other 43 are identical to three decimals in both.**

*If the flip ships:*

| Preset | `reported` | `derived` | Δ |
|---|--:|--:|--:|
| 🏢 Biden Corporate 28%, static | −$1,397.21B | **−$1,310.92B** | +6.2% |
| 🏢 Biden Corporate 28%, dynamic | −$736.71B | **−$662.55B** | +10.1% |
| 🏢 Trump Corporate 15%, static | +$1,491.76B | **+$1,562.75B** | +4.8% |
| 🏢 Trump Corporate 15%, dynamic | +$885.79B | **+$949.20B** | +7.2% |

Both owe a Decision 6 caption computed from the scored result. Badges are
predicted **not** to move: `biden_corporate_28` 3.73% → 4.04% stays Excellent and
`trump_corporate_15` 121.63% → 129.57% stays Poor.

*If the flip does not ship:* **zero presets move**, and §1 has moved nothing
either, because §1.1 refuses and §1.2–1.4 are a transcription, a search record
and two measurements.

---

## §4 — Falsification

The lane has failed, and must say so in its outturn, if any of these is true.

1. **A share is asserted.** `scripts/corporate_yield_reconciliation.py` prints
   **0.5785**, the total factor that reproduces CBO Option 64, and JCT's own
   steady-state **0.590**. If the finished tree's total derived factor lands
   within **±0.02** of either, or if any new constant in `corporate.py` is
   chosen, rounded or bounded with reference to a row's error, the lane has
   failed even if every band in §3 is met.
2. **The haircut is applied to a base that already nets it.** Multiplying
   `projected_statutory_base` — or anything downstream of it — by 0.80 or 0.85
   without first showing that the base does *not* net loss firms, when §0.5 shows
   it does.
3. **Any Tier 1 row other than `cbo_opt64_corporate_rate_1pp` moves.** The
   `derived` branch is read by exactly one Tier 1 shape; any other row moving
   means something outside this lane's declared surface changed.
4. **A calibrated tier moves without a target moving.** No target moves in this
   lane, so the fitted tier's n and mean must be unchanged unless the flip moves
   `biden_corporate_28`'s *scored* figure — which it does, and which §3.2 already
   accounts for.
5. **The flip ships on one metric.** §3.2 requires both. A flip that ships on
   Metric 1 alone, or on a re-weighted Metric 1, is a failure of this lane
   whatever the mean says.
6. **A readiness exemption is added.** Strict readiness blocking the flip is an
   outcome to report, not an obstacle to route around.

---

## §5 — Out of scope

- **Any target movement.** `preregistered.py`, `benchmark_sources.py`,
  `cbo_scores.py` and `target_revisions.py` are not opened. `trump_corporate_15`
  keeps the published range **[+595.0, +673.1]** PR #122 gave it, including its
  bonus-depreciation scope gap (the registry's own `scope_differs` measures that
  leg at **+$294.15B** of +$1,491.8B); `biden_corporate_28` keeps its
  `scope_differs` GILTI verdict; `biden_corporate_28_fy2022` is **never to be
  fitted**, and this lane fits nothing to it.
- **`BASELINE_TAXABLE_PROFITS_BILLIONS`.** The fitted constant is not retuned,
  in either direction, under any outcome. Decision 1's whole point is that a
  module wins the default by being right, not by being re-fitted.
- **`reported`'s arithmetic.** Untouched by §1 by construction; the final commit
  changes only which mode the app *selects*.
- **The `_estimate_passthrough_shift` constants** (7% marginal share, 0.15
  elasticity, 29.6% individual effective rate). Measured in §1.3, not replaced:
  there is no published parameter to replace them with, and inventing one is §4.1.
- **The §6655 first-year factor.** `CORPORATE_PER_POINT_YIELD.md` §6 names the
  model's 0.757 against JCT's unexplained 0.591–0.732; JCT publishes no timing
  narrative in any volume, so matching it would be reading JCT's answer backwards.
- **R12's `MARGINAL_REVENUE_RATE`,** which moves the dynamic column of §3.3's
  preset table and is its own lane.
- **`CBOBaseline`'s corporate receipts line.** R1 owns it; the derived path reads
  a transcribed CBO table, not the baseline object.

---

## §6 — Owner decision ⑤: the re-measurement, and the flip

Measured on the finished tree, against §3.2's rule, which was fixed before §1
was implemented.

**Metric 1 — the three published corporate targets.** Unchanged from §0.1,
because §1 shipped no mechanism: **`reported` 62.75%, `derived` 61.43%**.
`derived` is strictly lower. ✅

**Metric 2 — H3a's four-house estimator span at +7pp**, the step every shipped
corporate preset uses: `derived` −$1,292.62B, **inside** the −$1,349.9B to
−$935.8B span; `reported` −$1,397.21B, **larger than all four and $47.27B
outside**. ✅

Both metrics favour `derived`, so **`CORPORATE_APP_MODE` is now
`CORPORATE_MODE_DERIVED`** (`fiscal_model/corporate.py`), in its own commit,
with a Decision 6 caption
(`ui/tabs/results_summary.corporate_mode_flip_caption`) on every corporate rate
figure that moved.

**Three qualifications belong next to that, and the module docstring carries
all three.**

1. **`derived` wins the mean while losing two rows of three.** It takes
   `biden_corporate_28_fy2022` by 12.19 points and gives up `biden_corporate_28`
   by 0.31 and `trump_corporate_15` by 7.94. The row it wins is the only one
   whose *scope* matches what the factory builds — the FY2022 Green Book's
   rate-only row, the one corporate row in any Green Book whose Proposal
   section does not mention GILTI. The row it loses by a whisker is one
   `reported`'s constant is **fitted** to, so 3.73% there is partly arithmetic.
2. **Neither mean is small.** 61.43% against 62.75% is a choice between two
   wrong answers, taken on a rule the repository set in advance. PR #122's
   summary stands unaltered: a module whose implied marginal base is at or above
   every published estimator's misses two published corporate targets in the
   same direction and misses the third by more.
3. **Nothing was retuned to produce it.** `BASELINE_TAXABLE_PROFITS_BILLIONS` is
   1900.0 before and after, asserted by
   `tests/test_corporate_mode_flip.py::test_neither_mode_was_retuned_to_win`.

**Strict readiness does not block it, and the check was run in the form that can
distinguish.** PR #119's §7.5 lesson is that Python 3.14 fails the runtime
component *first* and masks everything after it, so a bare exit code proves
nothing here. `strict_readiness_issues()` returns **exactly one issue before the
flip and exactly one after it**, and in both cases it is the environmental
runtime warning. No fitted row went Poor: `biden_corporate_28` moves 3.73% →
4.04% and stays **Excellent**, and `repeal_corporate_amt` does not move at all.
No exemption was added.

---

## §7 — Outturn

### 7.1 Against the pre-registration

| # | Quantity | Before | Pre-registered | **Outturn** | |
|--:|---|--:|---|--:|---|
| 1 | `cbo_opt64_corporate_rate_1pp` | 44.50% | 30 ± 8 | **44.50%** | ❌ missed — unmoved |
| 2 | `biden_corporate_28_fy2022` | 62.88% | −45 ± 10 | **50.69%** | ✅ inside — *but see below* |
| 3 | `trump_corporate_15` | 121.63% | 90 ± 20 | **129.57%** | ❌ missed — worse |
| 4 | `biden_corporate_28` | 3.73% | moves in `derived` only | **4.04%** served; `reported` branch byte-identical | ✅ |
| 5 | derived marginal share, +1pp | 80.83% | falls toward 55–80%, not set inside it | **80.83%** | ❌ unmoved |
| 6 | Tier 1 mean | 11.6% | moves by `cbo_opt64` alone | **11.6%**, n=22, median 8.9%, 18/22 within 15 | ✅ |
| 7 | every Tier 1 row but `cbo_opt64` | — | byte-identical | **all 22 byte-identical** | ✅ |
| 8 | LOO `--donor-matrix` | 36.5% (n=18) | byte-identical | **byte-identical**, every module row unmoved | ✅ |
| 9 | fitted tier | 15 @ 1.6% | unchanged | **15 @ 1.6%**, 15/15 within 15 | ✅ |

**§3.1 predicted rows 1, 3 and 5 would miss by not moving, and they did.** That
prediction was written before §1 was implemented and after §0.5 had run the
applicability test, which is the sequence the protocol asks for and the reason
the misses are reportable rather than embarrassing.

**Row 2 landed its band and should not be credited to §1.** The band was a
prediction about the *mechanism*; the mechanism was refused, and the row moved
because part (B) changed which mode the scorecard scores. Had the flip not
shipped, row 2 would read 62.88% and miss like the others. Two of three bands
would have been landed by applying the haircut — which is exactly why §4.2 made
that a falsification condition rather than a goal.

### 7.2 What was sourced, and what was not obtainable

| Item | Outcome |
|---|---|
| **Loss-firm haircut** (§1.1) | **Sourced and refused.** `dmyrevnfc = 0.85`, `dmyrevx = 0.80`, verified at `business-investment-model` @ `6cb4cea…`, `Create_Tax_Data.prg:32-33`, derivation `:21-27`, use `:69-70` |
| **§38(c) general business credit carryforward** (§1.2) | **Obtained.** IRS Publication 5108 (TY2022, Rev. 9-2025), PDF pp. 164 and 166 — $91.16B (Part I line 4) + $33.31B (Part II line 34) = **$124.47B**, against $72.17B of claims. Downloaded and read page-by-page here, not taken on report |
| **§904(c) foreign tax credit carryover** (§1.2) | **Partly.** SOI's Corporate Foreign Tax Credit Table 1 (`22it01fi.xlsx`) publishes the limitation ($174.44B), taxes available ($203.70B) and the claim ($112.16B), but footnote [2] says in as many words that *"carryover of foreign taxes and applicable reductions are not shown separately"*. The carryover is a **$78.02B residual**, labelled as one |
| **The share that would price either channel** | **Not obtainable.** SOI's excess-credit / excess-limitation tables (1.1 and 1.2) exist for **TY2010 only**; `22it11mi.xlsx`, `22it12mi.xlsx` and `21it11mi.xlsx` all 404 and the series was discontinued. TY2010 is pre-TCJA, before the participation exemption, GILTI and the §904 basket rewrite |
| **SOI Complete Report TY2023** | **Not published.** TY2022 is the frontier; `23co11ccr.xlsx` 404s and the landing page lists TY2014–2022 |
| **CAMT base** (§1.2) | **Not published.** No source gives the taxable income of CAMT-liable corporations. Treasury JY2574: ~100 payers, ~$250B over 2025–2034, 2.6% counterfactual effective rate. JCT's 2022 letter to Chairman Wyden: 175–200 corporations averaging $8.2B of book income in 2019. The two populations differ by a factor of two and neither is a base. Recorded as `published_context` |
| **Behavioural offsets** (§1.3) | **Null, already established.** `CORPORATE_PER_POINT_YIELD.md` §5(c): JCT publishes five corporate margins and no parameter, PWBM defers to unstated JCT staff estimates, Treasury publishes nothing, and the one house that states a parameter uses Heckemeyer & Overesch's 0.8 — which is `PROFIT_SHIFTING_SEMI_ELASTICITY` already |
| **Direction asymmetry** (§1.4) | **Documented, not modelled.** Tax Foundation *Options 2.0* prices a cut 28.9% dearer per point; `derived` produces **+13.4%**, `reported` **exactly 0.0%** |

### 7.3 Findings

**1. CBO's haircut is a rate adjustment, and this repository's own files say so
three times.** It multiplies a statutory rate inside a user-cost expression, and
the derived path multiplies a base that is CBO receipts ÷ the statutory rate.
CBO itself *divides by* the same factor at `Create_Tax_Data.prg:172-175` where
the other input already carries it, **"to avoid double-counting"**.
`scripts/corporate_yield_reconciliation.py`'s docstring already said the
denominator every published marginal share is measured against "already nets
credits, **NOLs**, shifting". And the module's own SOI file measures it: income
subject to tax is net of an NOL deduction running **8.69–11.58%** of the pre-NOL
base (10.25% mean, 11.58% at the TY2022 anchor) against CBO's **12.81%** — a gap
of **1.23pp**, and not a smaller haircut waiting to be applied, because CBO's is
a 2005 *flow* of current-year losses and SOI's a post-TCJA *stock* of
carryforwards used under §172(a)'s 80% limitation.

**2. The plan's own description of the source is wrong, and it would have sent a
lane looking for data that does not exist.** `ROUTE_TO_8_5.md` §1 R5 and this
lane's brief both call 0.80/0.85 "financial / non-financial" and the brief asks
for the haircut "by sector if the receipts detail supports it". CBO's comment
says **0.85 is loss-making firms alone (nonfinancial corporates)** and **0.80 is
that same factor further reduced by the nonprofit share of nonresidential
investment** (0.85 × 0.94 = 0.799); `grep -rn dmyrev source_code/` returns no
third series. There is no sector split to apply.

**3. The module's average-credit substitution sits almost exactly on the §904
channel's own upper bound, which is why §38(c) is the live carry-over.** The
derived path books `1 − 0.7085 = 29.147%` of marginal credit absorption by
substituting the average ratio for the marginal one. The §904 channel at *its*
upper bound — every claimant in an excess-credit position, which
`section_904_realization_ratio` already assumes — is **28.851%**, 0.30pp away. So
the §38(c) channel is **entirely unbooked**: $124.47B of stock, 1.72 years of
claims, under a statutory cap of 75% of regular tax that **rises with the
rate**. It is the one named channel that points the score *down*, toward the
published estimators, and it is the only one with a mechanism CBO has ever put
in writing (2018 Option 24).

**4. The direction this lane would have preferred is not the direction the data
points.** Building a *bottom-up* marginal credit share risks coming in **below**
29.147% — most general business credits are fixed dollar amounts whose
*usability*, not size, responds to the rate — which would move the score **up**
and the row **worse**. §1.2 pre-registered that in advance so it could not later
be presented as a surprise.

**5. The entity-choice leg is dead code in every scored case.**
`_estimate_passthrough_shift` fires only when the corporate rate exceeds a
hard-coded 29.6% individual effective rate. At +1pp (22%), +7pp (28%) and −6pp
(15%) it does not, so the leg returns **exactly 0.0 for every corporate
benchmark in the repository and for every rate cut by construction**. JCT names
entity choice as one of its five corporate behavioural margins (JCX-46-11 p. 10)
and publishes no parameter for it, so this lane measured the leg rather than
replacing it.

**6. `reported` mode's answer does not depend on which decade you ask about, and
the flip is what revealed it.** `tests/test_no_headline_without_row.py` went red
on the two corporate presets at 1.42% and 1.13%, and the decomposition is clean:
the runner's own policy re-scored on the app's FY2026–2035 window returns
**−1,310.92** and **+1,562.75**, the app's headlines *to the cent*, so **100% of
the divergence is the window and 0% is the policy build**. Under `reported` the
gap was zero — not because the two agreed, but because that mode prices a rate
change against a fitted aggregate the engine grows from the *policy's own* start
year, so shifting the window shifts the policy with it and the totals cancel
exactly. `derived` reads a path indexed by *fiscal year*, so FY2026–2035 is
genuinely a different decade and is worth $18.30B / $17.51B. Declared as two
`runner_shape` entries in `HEADLINE_ROW_DIVERGENCE` with that measurement.

**7. A shipped caption changed hands rather than disappearing, and the test that
caught it was right to.** `behavioural_sign_caption` fires for a
`CorporateTaxPolicy` only in `reported` mode, because PR #119's `abs()` defect
lived in that branch alone — Wave 5 B had already signed `derived`. So Trump
Corporate 15% stops carrying the sign caption at the same moment its number
moves again. `corporate_mode_flip_caption` covers it, and
`test_the_caption_fires_on_exactly_the_two_presets_that_moved` now asserts both
halves: one preset keeps the old caption, the other has acquired the new one.
The failure mode this avoids is a shipped figure moving twice and being
explained once.

### 7.4 Presets moved

Swept through `create_policy_from_preset` on the app's own FY2026–2035 window,
45 scoreable presets × {static, dynamic}. **Exactly two presets moved, and both
carry the Decision 6 caption; the other 43 score to three decimals what they
scored before, in both engine modes.**

| Preset | Before | After | Δ |
|---|--:|--:|--:|
| 🏢 Biden Corporate 28%, static | −$1,397.21B | **−$1,310.92B** | +6.2% |
| 🏢 Biden Corporate 28%, dynamic | −$736.71B | **−$662.55B** | +10.1% |
| 🏢 Trump Corporate 15%, static | +$1,491.76B | **+$1,562.75B** | +4.8% |
| 🏢 Trump Corporate 15%, dynamic | +$885.79B | **+$949.20B** | +7.2% |

Badges do not move: `biden_corporate_28` 3.73% → 4.04% stays **Excellent** and
`trump_corporate_15` 121.63% → 129.57% stays **Poor**, both as §3.3 predicted.

### 7.5 Tier movements

| Tier | Before | After |
|---|--:|--:|
| Tier 1 (out-of-sample) | 22 @ 11.6%, median 8.9%, 18/22 within 15 | **identical**, zero rows moved |
| fitted | 15 @ 1.6%, 15/15 within 15 | **15 @ 1.6%** |
| held in place | 26 @ 12.4% | 26 @ 12.4% (median 2.4% → 2.6%) |
| unfitted reconstructions | 38 @ 37.5%, median 30.1% | **38 @ 37.4%**, median 30.1% |
| retired held in | 40 @ 55.5% | 40 @ 55.4% |
| leave-one-out | 18 @ 36.5% | **byte-identical** |

**The reconstruction tier's 0.1pp is accuracy on a constant population**, not
composition: the same 38 rows sit in it before and after, and the whole of the
move is `biden_corporate_28_fy2022` −12.19pp against `trump_corporate_15`
+7.94pp, which over 38 rows is −0.11pp. Worth stating plainly because this
repository has three times had to explain that a tier mean moved for reasons
that were not accuracy — here, for once, it is.

### 7.6 Deviations from §2

- **`fiscal_model/ui/preset_validation.py` was opened**, which §2 did not list.
  The flip put two corporate presets over `HEADLINE_ROW_TOLERANCE_PCT`, and the
  registry that exists for exactly that has to carry them or the suite stays
  red. The change is two data entries scoped to the corporate presets, each with
  the measured decomposition in §7.3 finding 6; no mechanism in that module was
  touched.
- **Four test files outside the lane's own were updated** —
  `test_corporate_derived.py`, `test_cbo_regression.py`,
  `test_offset_sign_contract.py`, `test_no_headline_without_row.py` (through the
  registry). Every one of them pinned the old app default; none had its
  *assertion* weakened, and two gained a stronger one (the sign caption now
  asserts where the explanation went, and the mode-flip test asserts the
  decision rule rather than the outcome).

### 7.7 Carry-overs

1. **§38(c) carryforward absorption.** The stock is now transcribed and the
   channel bounded; what is missing is the share of the base held by taxpayers
   both §38(c)-capped and holding carryforward. SOI's excess-position tables
   stopped after TY2010. A lane that wants this needs either a reinstated SOI
   table, a Treasury OTA tabulation, or microdata — **not** a chosen share.
   Finding 3 says why it is the channel worth wanting.
2. **CAMT.** Blocked on TY2023 SOI, which does not exist yet. Worth re-checking
   when the TY2023 Complete Report publishes, because CAMT will be in it.
3. **The §6655 first-year factor**, 0.757 against JCT's unexplained 0.591–0.732
   — untouched, and untouchable without a source, since no *Options* volume
   mentions payment timing.
4. **`_estimate_passthrough_shift` is inert** (finding 5). Either source a
   parameter for JCT's entity-choice margin or delete the leg; leaving an
   unsourced branch that never fires is the worst of the three.
5. **`cbo_opt64` is still Tier 1's largest row at 44.5% and still a class of
   one.** This lane did not move it and says so. The plan's own remedy is spent:
   the haircut is refuted, the credit channels are bounded and unpriceable, and
   the behavioural parameter is already the only published one. What is left is
   a **second corporate out-of-sample row** so the class stops being n=1 —
   `corporate_rate_scores.csv` carries eighteen published estimates across ten
   vintages, and R3's Tailor battery is where that belongs.
6. **The window sensitivity finding 6 exposes is now a property worth keeping.**
   `derived` gives a different answer for FY2026–2035 than for FY2025–2034 and
   `reported` cannot. That is the right behaviour and it is currently visible
   only as a declared badge divergence; a future lane might surface it.
