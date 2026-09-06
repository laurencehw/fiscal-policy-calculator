# Lane W7 — the expenditure module's offset convention, settled on sources

*Pre-registered 2026-09-06 against `main` @ `a251b32`, in this lane's first
commit, before the module was touched. The inventory in §4 is a reading of
documents, not a run of the code, which is why it belongs in the
pre-registration rather than after it. The outturn (§9) is appended in the
lane's last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 **item 8** — the tax-expenditure
module's reverse sign convention, *"now the only one, and its size is measured:
+5% on SALT elimination, +20% on Option 56"*. The lane touches
`fiscal_model/tax_expenditures_core.py`, the two test files that pin its
behaviour, and `tests/test_offset_sign_contract.py`'s exception set. It edits no
target, no threshold, no manifest, `preregistered.py`, `holdout.py`, `loo.py`'s
guards, `target_revisions.py`, `KNOWN_SCORES`/`CBO_SCORE_MAP`, `.github/`, or
`planning/MODELING_IMPROVEMENT.md`. **It changes no elasticity value.**

## 1. The contract, and the one module still outside it

`fiscal_model/scoring_engine.py` books a score as
`static_deficit = static_spending − static_revenue`, then
`deficit_after_behavioral = static_deficit + behavioral`, and hands
`estimate_behavioral_offset` the year's **static revenue** effect. An offset
carrying the **same** sign as static therefore **erodes** it; one carrying the
**opposite** sign **magnifies** it.

PR #119's sweep (`planning/lanes/SWEEP_offset_sign.md`) signed six modules and
left `TaxExpenditurePolicy` alone as the single entry in
`tests/test_offset_sign_contract.py`'s `CONVENTION_EXCEPTIONS`, cited to CBO's
Option 56. Its reason was explicit and is this lane's brief: the convention is
right *there*, unsourced in magnitude everywhere else, and **module-wide**, so
choosing it would move every fitted expenditure row and the whole leave-one-out
column together. Today the module reads:

```python
offset = abs(static_effect) * elasticity
if static_effect > 0:
    return -offset
return offset
```

— one direction for every expenditure, every reform, and both signs of static.

**This lane's claim is that "one direction" is the defect, not "which
direction".** The direction of a behavioural revenue effect is a property of
*the reform*, and the sharpest evidence for that is a single CBO option whose
four alternatives, on the same deductions in the same table, point three
different ways (§4.1).

## 2. What is in scope

Every benchmark and preset that reaches `TaxExpenditurePolicy`, plus the two
public factories nothing scores:

| # | Policy id / preset | Factory | Tier | `BEHAVIORAL_ELASTICITIES` |
|---|---|---|---|--:|
| 1 | `cap_employer_health` + **📋 Cap Employer Health Exclusion** | `create_cap_employer_health_exclusion` | fitted | 0.20 |
| 2 | `eliminate_mortgage` | `create_eliminate_mortgage_deduction` | fitted | 0.10 |
| 3 | `cap_charitable` + **📋 Cap Charitable Deduction** | `create_cap_charitable_deduction` | fitted | 0.40 |
| 4 | `eliminate_step_up` + **📋 Eliminate Step-Up Basis** | `create_eliminate_step_up_basis` | fitted | 0.00 |
| 5 | `repeal_salt_cap` + **📋 Repeal SALT Cap** | `create_repeal_salt_cap` | reconstruction | 0.05 |
| 6 | `eliminate_salt` | `create_eliminate_salt_deduction` | reconstruction | 0.05 |
| 7 | `cbo_opt56_employer_health_income_only` | `validation/core.py`'s `tax_expenditure` shape, `mode="derived"` | **Tier 1** | 0.20 |
| — | (unscored) `create_cap_retirement_contributions` | — | — | 0.30 |
| — | (unscored) `create_eliminate_like_kind_exchange` | — | — | 0.00 |

Two facts about that table matter and are not obvious from the factories.

**Every calibrated factory sets `behavioral_elasticity=0.0`, and on five of the
eight it is dead code.** `estimate_behavioral_offset` reads
`BEHAVIORAL_ELASTICITIES.get(self.expenditure_type, self.behavioral_elasticity)`
— the module-level table wins whenever the expenditure type is listed in it, and
five of these types are. So unlike AMT, estate and PTC in PR #119, this module's
offset is **live on its benchmarks**, which is why the numbers below move at all.
Rows 4 and 8 are the exceptions: `STEP_UP_BASIS` and `LIKE_KIND_EXCHANGE` are
absent from the table, so their zeroed instance value is what is used and their
offset is exactly `0.0`.

**Only four expenditure presets ship.** `PRESET_POLICIES` carries Cap Employer
Health, Repeal SALT Cap, Eliminate Step-Up Basis and Cap Charitable Deduction;
`eliminate_mortgage` and `eliminate_salt` are scorecard rows with no preset
(`preset_handler._create_expenditure_policy` has four branches).

## 3. How a direction is read, and the standard applied

The question asked of each source is exactly one question: **does the
behavioural response to *this* reform make the revenue change larger in
magnitude than a no-behaviour calculation of it, or smaller?**

That question is well posed for this module and not for every module, because
the module's static base is a **tax expenditure**, and JCT states in terms what
a tax expenditure excludes (JCX-48-24, *Estimates of Federal Tax Expenditures
for Fiscal Years 2024-2028*, report p. 12):

> "A tax expenditure calculation is not the same as a revenue estimate for the
> repeal of the tax expenditure provision for three reasons. First, unlike
> revenue estimates, tax expenditure calculations do not incorporate the effects
> of the behavioral changes that are anticipated to occur in response to the
> repeal of a tax expenditure provision."

So the offset is not a haircut on a number that already contains behaviour; it
is the *whole* behavioural adjustment, and its sign has to be read reform by
reform. One thing it is **not** carrying, and this matters for the readings
below: the itemisation margin is already inside the base, because JCT counts an
itemised deduction as a tax expenditure "**only to the extent that taxpayer's
total amount of itemized deductions exceeds the standard deduction**" (JCX-48-24
report p. 4). A filer who drops to the standard deduction is netted in the level,
not in the offset.

**The standard.** `erode` is the default — it is the engine's documented
contract and what the other twelve classes do. A policy gets `magnify` only
where a **source states that the behavioural response increases revenue** for
that reform. "A source" means a scorekeeper's own text about the option being
scored, or, where no scorekeeper has scored it, the published estimate the
benchmark's target comes from. Absence of a statement is not evidence of
magnification: it returns `erode`.

**Magnitudes are out of scope and stay exactly as they are.** `0.4` on
charitable, `0.2` on employer health, `0.1` on mortgage, `0.05` on SALT and
`0.3` on retirement are five unsourced numbers, and this lane names them rather
than fixing them (§8). Two of them turn out to sit near a published elasticity
by coincidence, and the coincidence is reported as one.

## 4. The inventory

*Documents read for this lane. CBO's own site returns HTTP 403 to this
environment, as `W4_option56_excess_share.md` finding 5 records; the 2024
compendium was read from a mirror of `60557-budget-options.pdf` and the
extended discussions through a text proxy, and every quotation below was taken
from the document text rather than from a search summary.*

### 4.1 The finding that makes a per-policy field necessary

CBO's Option 49, *Eliminate or Limit Itemized Deductions*, has four
alternatives over the same deductions in the same table, and the 2022 extended
discussion of it (`cbo.gov/budget-options/58635`, "Effects on the Budget")
gives them **three different behavioural directions**:

| alternative | CBO's own sentence | direction |
|---|---|---|
| 1 — eliminate all itemised deductions | "the estimate for that alternative is **not sensitive** to the resulting reductions in spending on deductible items because all taxpayers would be required to take the standard deduction" | none |
| 2 — eliminate the **SALT** deduction | "Other affected taxpayers might continue to itemize but would also choose to reduce their spending on other deductible items; that response would affect tax revenues… That reduction would further decrease their itemized deductions and **increase their tax liability**" | **magnify** |
| 3 — limit the tax benefit to **15% of value** | "This reduction would cause some of those taxpayers to spend less than they currently do on deductible items, **an effect that would increase tax revenues**" | **magnify** |
| 4 — limit the tax benefit to 4% of AGI | "that reduced spending **would not affect revenues** unless the reduction caused the tax benefit of the itemized deductions to drop below 4 percent of AGI" | none |

And CBO's *charitable* option, in the same family and with a **floor** design
rather than a rate cap (`cbo.gov/budget-options/54790`, "Effects on the
Budget"), points the other way outright:

> "Those responses make the estimated increase in revenues under either
> alternative **smaller than it would be otherwise**."

— because the responses it names are avoidance that *restores* deductibility:
bunching gifts "in a single tax year to qualify for the deduction", and, for the
noncash alternative, taxpayers who "could sell the items they would have donated
and donate the proceeds".

A module-wide constant cannot express that, and neither can a per-*expenditure*
one: the charitable deduction is `magnify` under a rate cap and `erode` under a
floor. **The direction is a property of the reform, so the field is keyed on the
reform.**

### 4.2 The table

| # | Policy | Source | What the source says | Source direction | Module now | Module magnitude, and its source |
|---|---|---|---|---|---|---|
| 1 | `cap_employer_health` — cap the exclusion | CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557), **Option 56**, report pp. 66-67 | "All three alternatives would reduce federal deficits by increasing tax revenues, because some workers would enroll in lower-premium plans (which would increase their taxable income) and others would remain enrolled in higher-premium plans and pay taxes on the portion that remained above the threshold. To a lesser extent, revenues would also increase because fewer workers would enroll in employment-based coverage." | **magnify** | magnify | 0.20 — **unsourced**; CBO publishes no elasticity or share for either channel (W4 finding 5) |
| 2 | `cbo_opt56_employer_health_income_only` — Option 56, third alternative | same | same | **magnify** | magnify | 0.20 — unsourced; worth +20% on this row |
| 3 | `cap_charitable` — 28% ceiling on the deduction's **value** | CBO 58635, **Option 49 third alternative** (the identical benefit-rate design; CBO 60557 Option 49 prices the 15% version, and the 2016 volume, `budget-options/2016/52254`, prices the **28%** version) | "This reduction would cause some of those taxpayers to spend less than they currently do on deductible items, **an effect that would increase tax revenues**." Corroborated by CBO 60557 Option 50 and 54790: giving does fall. | **magnify** | magnify | 0.40 — **unsourced**. It has the size of a giving *price* elasticity, but it is applied to the static **revenue** effect, which is a different quantity |
| 4 | `eliminate_salt` — repeal the SALT deduction | CBO 58635, **Option 49 second alternative** — the same reform | "That reduction would further decrease their itemized deductions and **increase their tax liability**" | **magnify** | magnify | 0.05 — unsourced |
| 5 | `repeal_salt_cap` — repeal the $10,000 cap | the mirror of #4, plus CBO 58635 "Economic Effects" ("the deduction for state and local taxes encourages state and local governments to raise taxes… than they otherwise would") and Yale Budget Lab, *Mortgage Interest Deduction: Options for Reform* (2025) | Yale: "Raising the SALT deduction limit means more taxpayers will itemize… Some of these new itemizers will now be able to deduct mortgage interest", and prices it — the MID tax expenditure goes **$323B at a $10,000 limit to $497B at $20,000**. Restoring the deduction enlarges the revenue **loss** beyond the SALT figure alone. | **magnify** | magnify | 0.05 — unsourced |
| 6 | `eliminate_mortgage` — repeal the mortgage-interest deduction | Poterba & Sinai, *Income Tax Provisions Affecting Owner-Occupied Housing* (NBER WP 14253, Aug 2008), §6.1 and Table 8 | "We estimate that in the absence of any behavioral response, eliminating the mortgage interest deduction would raise **$72.4 billion**"; allowing portfolio adjustment the same repeal raises **$61.9 billion**, "about **85 percent** of the tax increase when we do not consider portfolio substitution", because "when households liquidate their taxable financial assets to retire mortgage debt, they no longer earn taxable income on those assets". No scorekeeper has published a post-TCJA repeal score (`EXAMINED_NOT_REVISED`). | **erode** | magnify ✗ | 0.10 — unsourced. It happens to sit at 10% against Poterba–Sinai's 15%, which is a **coincidence**: nothing in the module was fitted to that paper and this lane does not move it toward it |
| 7 | `eliminate_step_up` — tax gains at death | CBO, *Change the Tax Treatment of Capital Gains From Sales of Inherited Assets* (`budget-options/54792`, "Effects on the Budget"), the same reform CBO 60557 Option 51 carries | "heirs might choose to **delay the sales** of inherited assets… to defer capital gains taxes and **thereby reduce their tax liability**", and the estimate "incorporates the response by some heirs" | **erode** | magnify ✗ | **0.00** — `STEP_UP_BASIS` is absent from `BEHAVIORAL_ELASTICITIES`, so the direction has no numerical consequence today |
| 8 | `cap_retirement` (unscored) — lower the contribution limits | CBO, *Further Limit Annual Contributions to Retirement Plans* (`budget-options/2018/54799`, "Effects on the Budget") | The behavioural legs CBO prices point both ways and net **negative inside the window**: "The constraints on Roth conversions would **reduce revenues by $6 billion** over that period"; the offsetting gain is explicitly *outside* it — "**Eventually**, the revenues gained by taxing more investment income would probably outweigh those lost". No statement that the saving response raises revenue. | **erode** (default; no statement to the contrary) | magnify ✗ | 0.30 — unsourced |
| 9 | `eliminate_like_kind` (unscored) — repeal §1031 | none found | No scorekeeper text located stating a direction for §1031 repeal. | **erode** (default) | magnify ✗ | **0.00** — `LIKE_KIND_EXCHANGE` is absent from the elasticity table |

**Four of the nine are magnify on a source; five are erode.** Of the five, three
(#7, #8, #9) carry an elasticity of zero or reach no benchmark, so **exactly one
scored row's direction actually flips: `eliminate_mortgage`.**

That is a smaller numeric outcome than the brief anticipated, and it is the
honest one. The convention PR #119 called "unsourced in magnitude everywhere
else" turns out to be **directionally right on four of the six benchmark
policies** — including both SALT rows, where CBO's own text names the channel —
and directionally wrong on one that is scored and two that are not. The
magnitudes remain unsourced on all of them, which is the part item 8 was right
about and this lane does not touch.

## 5. Starting numbers

From `python scripts/cold_holdout.py --json`, `python scripts/run_loo.py
--donor-matrix` and the readiness query, all on `a251b32`.

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| **Tier 1 — out-of-sample** | 26 | **15.20%** | 11.4% | 16 | 22 |
| **Tier 2 — fitted calibrated** | 21 | **1.733%** | 0.0% | 21 | 21 |
| **Tier 2 — unfitted reconstructions** | 34 | **57.556%** | 34.15% | 9 | 13 |
| **Tier 2 — leave-one-out** | 18 derivable (4 not x-val) | **29.6%** | 19.1% | 8 | — |

The seven rows this lane can reach:

| row | tier | official | model | error |
|---|---|--:|--:|--:|
| `cbo_opt56_employer_health_income_only` | Tier 1 | −697.0 | −605.8 | 13.10% |
| `cap_employer_health` | fitted | −450.0 | −449.5 | 0.10% |
| `cap_charitable` | fitted | −200.0 | −200.6 | 0.30% |
| `eliminate_step_up` | fitted | −500.0 | −523.5 | 4.70% |
| `eliminate_mortgage` | fitted | −300.0 | −330.4 | **10.10%** |
| `repeal_salt_cap` | reconstruction | 1,169.0 | 1,155.6 | 1.10% |
| `eliminate_salt` | reconstruction | −1,621.0 | −1,260.3 | 22.30% |

Expenditures leave-one-out, the column that moves with the module rather than
with a target: `cap_employer_health` +93.2%, `eliminate_mortgage` **−5.1%**,
`repeal_salt_cap` −33.5%, `eliminate_salt` +33.5%, `cap_charitable` +13.1%;
module mean **35.7%** (n=5 derivable, `eliminate_step_up` excluded by the
leakage guard). Strict readiness returns `[('runtime', None)]`.

## 6. The change

One mechanism, in one module.

1. **`OffsetDirection`** — an enum with two members, `ERODE` (same sign as
   static, the engine's contract) and `MAGNIFY` (opposite sign, a second
   revenue-raising channel).
2. **`OFFSET_DIRECTIONS`** — a table keyed on the **reform**, `(expenditure
   type, action)`, whose entries carry the direction, the source sentence that
   establishes it, and — where the source's verdict is design-specific — the
   `cap_unit` the entry applies to. §4.1 is why that last field exists: CBO says
   `magnify` for a benefit-rate cap on charitable giving and `erode` for a
   floor, so an entry that did not say which design it read would be asserting
   more than the document does. A reform with no entry, or with an entry whose
   design qualifier does not match, resolves to **`ERODE`**.
3. **`TaxExpenditurePolicy.offset_direction`** — an optional field, default
   `None` meaning "resolve from the table". An explicit value overrides it, so
   Tailor, the composer and any raw construction can state a direction without
   editing the table.
4. `estimate_behavioral_offset` becomes `math.copysign(abs(static) *
   elasticity, static)` for `ERODE` and `copysign(…, −static)` for `MAGNIFY`.
   **No elasticity value changes**; `BEHAVIORAL_ELASTICITIES` is untouched.
5. `tests/test_offset_sign_contract.py` — `CONVENTION_EXCEPTIONS` stops being a
   set of class names and becomes a set of *policies*, so the class is no longer
   a blanket exception: the contract test must **pass** for every erode policy
   and the sourced-magnify ones are enumerated with their citations.

## 7. Predictions

Written from §4 and the arithmetic of `final = static × (1 ± e)`, before any
code. In `reported` mode the static annual is a constant the engine grows, so
flipping a direction multiplies the whole ten-year figure by exactly
`(1 − e)/(1 + e)`. A disagreement between this section and §9 is a finding to
write down, not a number to quietly correct.

### 7.1 Rows

| row | e | factor | before | **predicted after** | error before → after |
|---|--:|--:|--:|--:|---|
| `eliminate_mortgage` (fitted) | 0.10 | 0.8182 | −330.4 | **−270.3** | 10.1% → **9.9%** |
| `cap_employer_health` | 0.20 | 1 | −449.5 | −449.5 | 0.10% (unchanged) |
| `cap_charitable` | 0.40 | 1 | −200.6 | −200.6 | 0.30% (unchanged) |
| `eliminate_step_up` | 0.00 | 1 | −523.5 | −523.5 | 4.70% (unchanged) |
| `repeal_salt_cap` | 0.05 | 1 | 1,155.6 | 1,155.6 | 1.10% (unchanged) |
| `eliminate_salt` | 0.05 | 1 | −1,260.3 | −1,260.3 | 22.30% (unchanged) |
| `cbo_opt56…` (**Tier 1**) | 0.20 | 1 | −605.8 | −605.8 | 13.10% (unchanged) |

**`eliminate_mortgage` does not go Poor and needs no reclassification.** Its
static is −300.4 against a −300.0 target — the fitted annual 26.2 was chosen as
if there were **no offset at all**, and the magnify convention then pushed the
score 10% past the target. Signing it pushes the score 10% short of the target
instead, so the row is about equally wrong either way and stays Acceptable. That
is a finding about how the constant was fitted, not a reason to move it, and
**no constant is retuned**: `scenarios.py` is opened only if a row goes Poor,
under PR #119's reclassify-don't-retune precedent, and this lane predicts it
will not have to be opened at all.

### 7.2 Tiers

- **Tier 1: 26 @ 15.20%, unchanged to the cent on all 26 rows.** The one Tier 1
  expenditure row is Option 56 and its direction is the sourced one. The CI gate
  (`--max-mean-error 20 --min-within-25pct 21`) is not approached.
- **Fitted calibrated: 21 @ 1.733% → 21 @ 1.724%**, still 21/21 within 15%,
  median still 0.0%. The whole of the change is one row moving 0.2pp *toward*
  its target. **No row leaves the tier**, so unlike PR #119 there is no
  composition effect to quote and no held-in-place reading that differs from the
  headline one.
- **Unfitted reconstructions: 34 @ 57.556%, unchanged**, both SALT rows being
  sourced-magnify.
- **Leave-one-out: this is where the lane costs something, and it is
  pre-registered as a regression.** `run_tax_expenditure_loo` scores through the
  production runner in `reported` mode with a re-derived annual, so the offset
  applies: `eliminate_mortgage` goes **−315.3 → −258.0, −5.1% → −14.0%**, the
  Expenditures module mean **35.7% → 37.5%**, and the suite **29.6% → ≈30.1%**.
  Within-15% stays 8/18 (14.0% is still inside). The leakage guard is untouched
  and `eliminate_step_up` stays excluded by it.
- **Presets: none of the 53 moves.** Three of the four expenditure presets are
  sourced-magnify and the fourth (Eliminate Step-Up Basis) has an elasticity of
  zero. So **no Decision 6 caption is owed**, and if one turns out to be owed
  the prediction was wrong and it ships in its own commit.

### 7.3 Falsification

The lane is falsified — and says so in §9 rather than adjusting — if:

1. **any row other than `eliminate_mortgage` moves.** That would mean a
   direction was misread, or that an elasticity thought to be zero is not;
2. **`eliminate_mortgage` does not move**, or moves by other than the
   `(1−e)/(1+e)` factor, which would mean the offset is not applied where §2
   says it is;
3. **a shipped preset moves**, which would mean the four-branch preset handler
   reaches a policy this inventory missed;
4. **Tier 1 moves at all**;
5. **strict readiness reports a `documented_calibrated_policy_ids`**, which
   would mean a fitted row went Poor and §7.1's arithmetic was wrong.

## 8. What this lane will not do

- **Not touch a single elasticity.** `BEHAVIORAL_ELASTICITIES`'s five values are
  unsourced and stay exactly as they are. Two of them now have a published
  number to be compared against — Poterba & Sinai's 15% against mortgage's
  10%, and the giving price elasticity literature against charitable's 0.4,
  which is applied to the wrong quantity in any case (a price elasticity of
  giving is not a share of a revenue effect). Both are carry-overs.
- Not open `preregistered.py`, `holdout.py`, `loo.py`'s guards,
  `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`, any CI threshold,
  `tests/test_cold_holdout.py`'s anti-leakage invariant, or
  `planning/MODELING_IMPROVEMENT.md`.
- Not retune any fitted annual. `scenarios.py` is opened only to set
  `calibrated_to_target: False` on a row the PR #119 precedent covers, and §7.1
  predicts none.
- Not build the payroll leg of Option 56, the health-spending-account base, or
  the plan-switching channel — W4's findings 2, 4 and 5, all still open.
- Not touch the shared docs. `docs/VALIDATION.md`'s Option 56 section,
  `docs/METHODOLOGY.md` and `planning/MODELING_IMPROVEMENT.md` §6.2 item 8 are
  all stale after this lane and a docs pass owns them.

Anything that moves outside this list is a finding and gets written into §9.

## 9. Outturn

*Appended in the lane's last commit. Every figure below is from a command named
beside it, run on this branch.*

**Every prediction in §7 landed, to the digit.** One scored row moved, by the
factor §7.1 computed; no preset moved; Tier 1 is identical to the cent; the
leave-one-out regression arrived at the size it was pre-registered at. None of
§7.3's five falsifications fired.

### 9.1 What the module reads now

`python scripts/audit_offset_signs.py`, the same script and cases PR #119 wrote,
with a second expenditure case added so the class shows both of its kinds:

| class | dir | f(+100) | f(−100) | window static | window behav | window final | erodes | tag |
|---|---|--:|--:|--:|--:|--:|:-:|---|
| TaxExpenditurePolicy [SALT] | increase | −5.0 | 5.0 | −952.6 | −47.6 | −1,000.2 | **NO** | |
| | cut | −5.0 | 5.0 | 740.0 | 37.0 | 777.0 | **NO** | convention |
| TaxExpenditurePolicy [mortgage] | increase | 10.0 | −10.0 | −286.6 | 28.7 | −257.9 | yes | |
| | cut | 10.0 | −10.0 | 57.3 | −5.7 | 51.6 | yes | correct |

The audit now reads **14 correct, 1 convention, 1 zero**, where the branch point
read 13/1/1 and PR #119's own branch point read 6 correct against 7 defects. The
one remaining `convention` row is a **policy**, not a class: `[SALT]` carries
the exemption with CBO's sentence attached and `[mortgage]`, built beside it in
the same class, is held to the contract like everything else.

### 9.2 What moved

| | before | after |
|---|--:|--:|
| **Tier 1 — out-of-sample** | 26 @ 15.196% / 11.4% / 16 / 22 | **unchanged, to the cent on all 26 rows** |
| **Tier 2 — fitted calibrated** | 21 @ **1.733%**, 21/21 within 15% | **21 @ 1.724%**, 21/21 within 15%, median still 0.0% |
| **Tier 2 — unfitted reconstructions** | 34 @ 57.556% / 34.15% | **unchanged, to the cent on all 34 rows** |
| **Tier 2 — leave-one-out** | 18 @ **29.6%** / 19.1%, 8/18 within 15% | **18 @ 30.1%** / 19.1%, 8/18 — *worse, by design* |
| Shipped presets (53) | — | **0 moved**; the sweep diffs byte-identical |

**No row left or joined either calibrated tier**, so unlike PR #119 there is no
composition effect here and the held-in-place reading *is* the headline reading:
21 @ 1.724% on the same 21 rows, 34 @ 57.556% on the same 34. The fitted mean
falling 0.009pp is one row moving 0.2pp closer to its target and nothing else.

**One scorecard row moved, and nothing was retuned:**

| row | tier | target | before | after | error |
|---|---|--:|--:|--:|---|
| `eliminate_mortgage` | fitted | −300.0 | −330.4 | **−270.3** | 10.1% → **9.9%** |

It stays Acceptable, so `scenarios.py` was never opened and PR #119's
reclassify-don't-retune precedent was never invoked. `python -c "from
fiscal_model.readiness import …"` returns **`[('runtime', None)]`**, the Python
3.14 issue that fails on `main` too and is not this lane's.

**The leave-one-out is the price, and §7.2 named it in advance:**

| | before | after |
|---|--:|--:|
| `eliminate_mortgage` LOO | −315.3, **−5.1%** | **−257.9, +14.0%** |
| Expenditures module (n=5) | 35.7% | **37.5%** |
| LOO suite (n=18) | 29.6% | **30.1%** |

Median (19.1%) and within-15% (8/18) are unchanged, because 14.0% is still
inside the band. The leakage guard is untouched and `eliminate_step_up` is still
excluded by it with the same message.

### 9.3 Six findings

**1 — The convention was right more often than item 8 assumed, and the row it
was wrong about is one no scorekeeper has scored.** Item 8 measured the
convention's size on "SALT elimination" and Option 56 and called it unsourced
outside the latter. It is not: CBO's extended discussion of Option 49
(`budget-options/58635`) names the channel for the SALT elimination **by name**,
in the alternative that is that exact reform, and says it "would… increase their
tax liability". Both SALT rows and the charitable rate cap join Option 56 on the
magnify side with documents behind them. The one *scored* reform where the
convention was wrong is the mortgage-interest deduction — and the source that
settles it is not a scorekeeper, because there isn't one: the row is already in
`EXAMINED_NOT_REVISED` precisely because no post-TCJA repeal score exists. It is
Poterba & Sinai (NBER WP 14253, Table 8), who price repeal at $72.4B with no
behavioural response and $61.9B once households sell taxable assets to retire
mortgage debt, "about 85 percent".

**2 — The grain is the whole finding, and the documents force it.** A
module-wide direction could not have been right, and neither could a
per-expenditure one. CBO's Option 49 puts four alternatives over the same
deductions in the same table and gives them **three** different directions
(§4.1); CBO's charitable option reverses its own verdict between a rate ceiling
("an effect that would increase tax revenues") and a floor ("smaller than it
would be otherwise"), because a floor can be bunched over and a rate ceiling
cannot. `OFFSET_DIRECTIONS` is therefore keyed on `(expenditure, action)` and a
rule may carry the cap design it was read for; a different design falls back to
erode rather than inheriting a verdict its document never gave. A test builds
both charitable caps side by side and asserts they resolve differently.

**3 — The module's own six fitted constants disagree about whether the
convention exists.** This is the sharpest thing the lane found and it was not
predicted. Reconstructing each annual against its own growth rate over ten
years:

| constant | annual | e | static path | static × (1+e) | its target | fitted to |
|---|--:|--:|--:|--:|--:|---|
| `cap_employer_health` | 31.2 | 0.20 | 374.6 | **449.5** | −450.0 | static × (1+e), 0.1% off |
| `cap_charitable` | 12.5 | 0.40 | 143.3 | **200.6** | −200.0 | static × (1+e), 0.3% off |
| `eliminate_mortgage` | 26.2 | 0.10 | **300.4** | 330.4 | −300.0 | **static**, 0.1% off |
| `repeal_salt_cap` | −96.0 | 0.05 | **−1,100.5** | −1,155.6 | 1,100.0 (pre-Wave-4) | **static**, 0.0% off |
| `eliminate_salt` | 104.7 | 0.05 | **1,200.3** | 1,260.3 | −1,200.0 (pre-Wave-4) | **static**, 0.0% off |
| `eliminate_step_up` | 43.6 | 0.00 | 523.5 | 523.5 | −500.0 | neither; 4.7% off |

**Three were fitted so that the static path hits the target and three so that
the magnified score does.** That is why this module's fitted rows were never
uniformly near zero the way the rest of the tier's are: on the three
static-fitted rows the convention was carried as **pure error** — 10.1% on
mortgage, 5.0% on the SALT elimination, 5.1% on the cap repeal — while the two
magnified-fitted rows absorbed it. It also means the fitted tier's near-zero
entries are not all near-zero for the same reason, which is worth knowing before
anyone reads a 0.1% as agreement. Nothing was retuned: re-fitting the three
static-fitted annuals to the score is exactly the move §1.1 of the plan forbids,
and it would make the row that moved here move again for a second reason.

**4 — The leave-one-out got worse because two errors stopped cancelling.** The
held-out mortgage annual is the JCT base level, $25.0B, against the fitted
$26.2B — a static path of −286.6 against the −300.0 target, **4.5% low**. The
old magnify convention added 10% to that and produced −315.3, **5.1% high**, so
the row read as one of the module's best. Signing it takes the same 4.5%-low
static to −257.9, **14.0% low**, which is the base error plus the offset rather
than the base error netted against it. That is the same shape as the Fiscal
Responsibility Act's spend-out in Wave 1: a correct mechanism removing one of
two errors that were cancelling, and the honest reading is that the −5.1% was
never evidence.

**5 — The direction is now sourced and the magnitude still is not, and the
distance between those two facts is measurable.** Poterba & Sinai's own figure
is a **15%** erosion against the module's 10%. It was **not adopted**: reading a
paper for a direction and then taking its coefficient as well would be fitting
to a document this lane chose, and it would move `eliminate_mortgage` a second
time in the same PR. Charitable's 0.4 is worse than unsourced — it has the size
of a *price elasticity of giving* and is applied to a share of the static
**revenue** effect, which is a different quantity; the arithmetic of a 28%
ceiling at a 37% marginal rate implies something nearer 18%. Employer health's
0.2 is the one W4 finding 5 already flagged as unpublishable from CBO's text.
All five are named in `BEHAVIORAL_ELASTICITIES`'s own comment now and all five
are carry-overs.

**6 — A sixth defect, found by asking who reads the offset downstream, and it
is not in the module's scoring path at all.**
`estimate_expenditure_revenue()` — a public helper the package exports —
aggregates in **revenue** space and returned `net_effect = ten_year_static +
ten_year_behavioral`, where the offset it is adding is the engine's
**deficit**-space quantity. So it disagreed with the engine *before* this lane
(the module magnified in deficit space while the helper eroded in revenue
space) and would have disagreed in the opposite direction after it. The fix is
a minus, and it changes **no scored number**: `cold_holdout.py --json` is
byte-identical across it on all 81 rows, because nothing shipped reads the
helper — no preset, no scorecard row, no API surface, only the package's
`__all__` and one test. That is exactly why it survived: the contract is
checked at `estimate_behavioral_offset` and again at the engine, and this
function sits between them where neither looks. The test that covered it
asserted `net_effect == static + offset`, a **tautology** that would have
passed under either sign; it now checks the arithmetic *and* the direction, on
one magnifying policy and one eroding one. The generalisable lesson is PR
#119's own, one level out: a sign contract enforced at the two ends of a
pipeline says nothing about the middle of it.

**One slip in the pre-registration, and it is arithmetic.** §2 says the zeroed
`behavioral_elasticity` every calibrated factory passes is dead code "on five of
the eight". It is **six of the eight**: five expenditure *types* are listed in
`BEHAVIORAL_ELASTICITIES`, but SALT has two factories. The module's own comment
now names the two exceptions —
`create_eliminate_step_up_basis` and `create_eliminate_like_kind_exchange` —
rather than counting. Nothing downstream turned on the count.

### 9.4 Falsification: none of the five fired

1. **Any row other than `eliminate_mortgage` moving** — did not fire. All 26
   Tier 1 rows, all 20 other fitted rows and all 34 reconstruction rows are
   identical to the cent, checked row by row rather than on the tier means.
2. **`eliminate_mortgage` not moving, or moving by other than
   `(1−e)/(1+e)`** — did not fire. −330.4 × 0.8182 = −270.3, which is what it
   scores.
3. **A shipped preset moving** — did not fire. All 53 diff byte-identical.
4. **Tier 1 moving at all** — did not fire.
5. **Strict readiness reporting a `documented_calibrated_policy_ids`** — did not
   fire; it returns `[('runtime', None)]`, which is what `main` returns.

### 9.5 Gates

| command | result |
|---|---|
| `python -m pytest tests/ -q` | **3,537 passed, 7 skipped** (`a251b32`: 3,518 passed, 7 skipped — the lane adds 19, counted by `--collect-only` on the two changed test files: 110 → 129). Measured on the outturn commit; the finding-6 commit that follows it adds and removes no test, and its two touched files were re-run green (`tests/test_tax_expenditures.py` + `tests/test_offset_sign_contract.py`, 123 passed / 6 skipped) |
| `python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | **exit 0** (15.2%, 22/26 — the gate is not approached) |
| `python scripts/run_loo.py --donor-matrix --max-mean-error 75` | **exit 0** (30.1%) |
| `python scripts/run_validation_dashboard.py` | **exit 1**, as on `a251b32`; the diff is **two lines**, both the Expenditures LOO figure |
| `python -c "… strict_readiness_issues …"` | **`[('runtime', None)]`**, unchanged from `a251b32` |
| `python -m ruff check fiscal_model/ tests/ scripts/` | clean |

The dashboard's exit 1 is the pre-existing `runtime [degraded] Python 3.14.0`
and `microdata [warn] SOI 2023` pair, neither touched here. PR #119's §7.5
lesson was taken rather than repeated: a byte-diff of an already-failing check
proves nothing, so strict readiness was queried **directly** for
`documented_calibrated_policy_ids` rather than compared as text — the query CI's
Python 3.12 would answer.

### 9.6 What this lane did not do

- **Did not touch a single elasticity.** Finding 5.
- Did not open `preregistered.py`, `holdout.py`, `loo.py`'s guards,
  `target_revisions.py`, `KNOWN_SCORES`, `CBO_SCORE_MAP`, any CI threshold,
  `tests/test_cold_holdout.py`'s anti-leakage invariant, `.github/`, or
  `planning/MODELING_IMPROVEMENT.md`.
- **Did not open `scenarios.py` at all.** No row went Poor, so no
  reclassification was owed and no fitted annual was retuned — including the
  three finding 3 shows were fitted to a static path rather than to a score.
- Did not ship a Decision 6 caption, because no shipped number moved. If a
  future lane re-fits those three constants, it will owe one.
- Went **one step outside** §6's plan, and says so here rather than in a
  footnote: `estimate_expenditure_revenue()`'s aggregation sign (finding 6).
  It is the same contract in the same file, it moves no scored number, and
  leaving it would have meant shipping a helper that contradicts the engine in
  the *opposite* direction from the one it contradicted it in before.
- Did not build W4's findings 2, 4 and 5 (the health-spending-account base, the
  payroll leg of Option 56, the plan-switching channel). All still open.
- Did not touch the shared docs. `docs/VALIDATION.md`'s Option 56 paragraph
  ("an unsourced behavioural offset whose sign convention is the reverse of
  `TaxPolicy`'s"), `docs/METHODOLOGY.md` line 198, `CLAUDE.md`'s Tier 1
  paragraph and `planning/MODELING_IMPROVEMENT.md` §6.2 item 8 are all stale
  after this lane; a docs pass owns them. Item 8 is **closed** as far as the
  direction goes and **open** as far as the magnitudes go, and the two halves
  should be recorded separately.
