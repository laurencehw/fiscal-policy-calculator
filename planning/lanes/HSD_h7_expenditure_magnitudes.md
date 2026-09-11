# Lane H7 — the expenditure module's five magnitudes

*Pre-registered 2026-09-11 against `main` @ `20e356d` (Waves A–C merged), in
this lane's first commit, before the module was touched. Sections 1–5 are a
reading of documents and of arithmetic on data already in the tree; §6 (the
outturn) is appended in the lane's last commit.*

Scope: `planning/HIGH_STAKES_ACCURACY.md` §3 **H7**, the half of
`planning/MODELING_IMPROVEMENT.md` §6.2 item 8 that lane W7 left open. W7
settled the **direction** of the tax-expenditure behavioural offset per reform
and said in terms that it would not touch a magnitude: "a direction can be read
off a document, a magnitude cannot be read off the same sentence"
(`W7_expenditure_offset_convention.md` §8, finding 5). This lane asks the five
magnitudes the same question W7 asked the directions — **is there a document?**
— one at a time, and adopts an answer only where there is one.

The lane touches `fiscal_model/tax_expenditures_core.py`,
`fiscal_model/tax_expenditure_distributions.py`, their tests, and — because a
shipped preset moves — one self-contained caption function in
`fiscal_model/ui/tabs/results_summary.py`. It edits **no fitted constant**, no
target, no manifest, `preregistered.py`, `holdout.py`, `loo.py`'s guards,
`target_revisions.py`, `KNOWN_SCORES`/`CBO_SCORE_MAP`, `.github/`, or any shared
doc.

*Amended after the outturn: `scenarios.py` and the expenditure runner **were**
opened, to set `calibrated_to_target=False` on `cap_charitable` under PR #119's
standing rule. That is a reclassification and not a retuning — no constant
moved and no scored number moved — and §6.6a records it in full. §5's ban on
opening `scenarios.py` to **re-fit** stands and was not breached.*

## 0. The plan's baseline is stale, and every figure below is re-measured

`HIGH_STAKES_ACCURACY.md` §3 H7 pre-registers `eliminate_mortgage` LOO
"14.0% → 8 ± 5", `cap_charitable` LOO "13.1% → 20 ± 8" and the Expenditures
module "37.5% → 30 ± 8". Two of those three inputs no longer exist:

* **H9 (PR #145) moved `eliminate_mortgage`'s target to a range.**
  `eliminate_mortgage.v2` carries `[−495.0, −367.9]` with Tax Foundation's
  −$367.9B as the anchor (`target_revisions.py`), and a revised target takes the
  row out of the fitted tier by the ledger's own rule. The row is a
  **reconstruction** now, at **26.5%**, and its leave-one-out reads **29.9%**,
  not 14.0%.
* **The Expenditures LOO module mean is 40.6%**, not 37.5% — the same
  target revision, arriving through `run_loo.py`.

Measured on `20e356d` before a file was opened
(`scripts/cold_holdout.py --json`, `scripts/run_loo.py --donor-matrix`):

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| Tier 1 — out-of-sample | 26 | **14.5%** | 11.5% | 16 | 22 |
| Tier 2 — fitted calibrated | 16 | **1.5%** | 0.1% | 16 | 16 |
| Tier 2 — unfitted reconstructions | 39 | **56.7%** | 36.9% | 10 | 13 |
| Tier 2 — leave-one-out | 18 (4 not x-val) | **35.7%** | 29.1% | 6 | — |

The seven rows this lane can reach, and the eighth and ninth it cannot:

| row | tier | target | model | error |
|---|---|--:|--:|--:|
| `cbo_opt56_employer_health_income_only` | **Tier 1** | −697.0 | −605.8 | 13.10% |
| `cap_employer_health` | fitted | −450.0 | −449.5 | 0.10% |
| `cap_charitable` | fitted | −200.0 | −200.6 | 0.30% |
| `eliminate_step_up` | fitted | −500.0 | −523.5 | 4.70% |
| `repeal_salt_cap` | reconstruction | 1,169.0 | 1,155.6 | 1.10% |
| `eliminate_salt` | reconstruction | −1,621.0 | −1,260.3 | 22.30% |
| `eliminate_mortgage` | **reconstruction** | **[−495.0, −367.9]** | −270.3 | **26.50%** |
| `cap_retirement` | unscored factory | — | — | — |
| `eliminate_like_kind` | unscored factory | — | — | — |

Expenditures leave-one-out: `cap_employer_health` +93.2%, `eliminate_mortgage`
**+29.9%**, `repeal_salt_cap` −33.5%, `eliminate_salt` +33.5%, `cap_charitable`
**+13.1%**; module mean **40.6%** (n=5; `eliminate_step_up` excluded by the
leakage guard).

## 1. The mechanism, magnitude by magnitude

### 1.0 What the parameter is, and what it is not

`estimate_behavioral_offset` computes `abs(static_effect) * elasticity` and
signs it from the reform's `OffsetDirection`. So the number in
`BEHAVIORAL_ELASTICITIES` is **a share of the reform's static revenue effect**
— a pure ratio, dimensionless, and *not* a price elasticity. W7's finding 5
named the confusion and this lane is the one that has to resolve it: a price
elasticity of giving is `%Δgiving ÷ %Δprice`; the module's parameter is
`Δrevenue_behavioural ÷ Δrevenue_static`. They are different quantities, and
a published price elasticity reaches the module only through an identity that
converts one into the other. Where such an identity exists it is written out
below; where it does not, the value is left and the search is recorded.

### 1.1 Mortgage interest, `eliminate` — **0.10 → 0.145028** (erode)

Poterba & Sinai, *Income Tax Provisions Affecting Owner-Occupied Housing:
Revenue Costs and Incentive Effects*, NBER Working Paper 14253 (August 2008),
§6.1 and Table 8, is already the document W7 read for this reform's
**direction**; it prices the magnitude in the same two sentences. Repeal of the
mortgage interest deduction raises **$72.4 billion** "in the absence of any
behavioral response" and **$61.9 billion** once households are allowed to
liquidate taxable financial assets to retire mortgage debt — "about **85
percent** of the tax increase when we do not consider portfolio substitution".

Both figures are *revenue* effects of the *same* repeal, so their ratio is
exactly the quantity `estimate_behavioral_offset` needs, with no conversion:

```
e = 1 − 61.9 / 72.4 = 0.1450276243…
```

The paper's own rounding is "about 85 percent"; the parameter takes the ratio
of the two published figures rather than the rounded sentence, because the
rounding is the paper's presentation and the figures are its estimate.

W7 declined to adopt this — correctly, on its own terms: "reading a paper for a
direction and then taking its coefficient as well would be fitting to a document
this lane chose, and it would move `eliminate_mortgage` a second time in the
same PR". This lane is the second PR, the row has since been re-targeted by H9
to a range neither this model nor Poterba & Sinai was consulted about, and the
adoption is pre-registered below **as a regression**.

*Scope of the entry.* The rule is keyed on `(MORTGAGE_INTEREST, "eliminate")`.
Poterba & Sinai price repeal; nothing in the paper sizes the portfolio response
to a *cap*, so a mortgage cap falls through to the unsourced table value as
before. The module ships no mortgage cap.

### 1.2 Charitable, benefit-rate ceiling — **0.40 → 0.220780 derived** (magnify)

This is the one that needs an identity, and the identity is the module's own
arithmetic rather than a new assumption.

A benefit-rate ceiling at `c` leaves the deduction in place and caps the rate at
which it may be valued. For a filer facing marginal rate `m > c`:

* the **static** revenue gain is `(m − c)` per dollar deducted — which is
  exactly `DeductionDistribution.benefit_share_above_rate`, summed over SOI AGI
  classes as `Σ_b A_b·(m_b − c)⁺`;
* the **price** of a dollar of giving rises from `(1 − m)` to `(1 − c)`, a
  proportional increase of `(m − c)/(1 − m)`;
* a price elasticity `ε` therefore cuts giving in class `b` by
  `ε·A_b·(m_b − c)/(1 − m_b)`;
* every dollar not given is a dollar not deducted **at the capped rate**, so
  revenue rises by a further `c` per dollar. That is CBO's own channel, in
  CBO's own words for this exact design: "This reduction would cause some of
  those taxpayers to spend less than they currently do on deductible items, an
  effect that would **increase tax revenues**" (`cbo.gov/budget-options/58635`,
  Option 49 third alternative) — which is why the reform is `MAGNIFY`.

So the share the module wants is

```
        c · Σ_b A_b · ε · (m_b − c)⁺ / (1 − m_b)
e  =  ─────────────────────────────────────────────
              Σ_b A_b · (m_b − c)⁺
```

— a weighted average of `ε·c/(1 − m_b)` over the classes the ceiling bites,
computed on the **same** SOI Table 2.1 charitable distribution the static path
already reads. No new data, no new constant except `ε`.

**`ε` comes from CRS.** The Congressional Research Service's R40518,
*Charitable Contributions: The Itemized Deduction Cap and Other FY2011 Budget
Options* (Jane G. Gravelle and Donald J. Marples), is a whole report on **this
reform** — a 28% ceiling on the value of itemised deductions — and Appendix A
reviews the panel literature one study at a time before concluding, at report
p. 27: "Ultimately a **center elasticity of 0.5** is used." Table 3 (report
p. 9) carries the band it was chosen from: **low 0.1, central 0.5, high 0.79**.

At `c = 0.28` on the repository's charitable distribution that gives

```
e = 0.220780     (ε = 0.5, CRS central)
```

with the band running `0.044156` (ε = 0.1) to `0.348832` (ε = 0.79).

**Two findings fall straight out of that arithmetic and are registered here,
before the code changes.**

1. **The plan's "nearer 18%" is not reproducible.** `HIGH_STAKES_ACCURACY.md`
   §3 H7 and `W7…md` finding 5 both say the arithmetic of a 28% ceiling at a
   37% marginal rate "implies something nearer 18%". Worked through, at a 37%
   rate the factor is `c/(1 − m) = 0.28/0.63 = 0.4444` per unit of `ε`, so 18%
   would need `ε = 0.405` and CRS's central `ε = 0.5` gives **22.1%**. The
   lane adopts the arithmetic and reports the discrepancy rather than the
   plan's figure.
2. **0.40 is not "a price elasticity misapplied" — it is the right identity at
   the wrong elasticity.** Inverting, the shipped 0.40 corresponds to
   `ε = 0.906`, which is **above the whole of CRS's band** (0.1–0.79) and
   above its central value by 81%. W7 guessed the 0.4 "has the size of a price
   elasticity of giving"; the truth is narrower and more useful — it is the
   size of a price elasticity *after* the conversion, i.e. the module has been
   assuming a giving response CRS's own literature review rules out.

*Scope of the entry.* The rule is keyed on `(CHARITABLE, "cap")` **and scoped
to `CapUnit.BENEFIT_RATE`**, exactly as `OFFSET_DIRECTIONS`'s charitable entry
is, and for the same reason: CBO reverses its verdict for a *floor* design, the
identity above is derived for a rate ceiling, and a rule that did not say which
design it read would assert more than its document does. A charitable floor, or
a dollar cap, falls through to the unsourced table value.

### 1.3 Employer health, `cap` — **0.20 left; search recorded**

Searched: CBO 60557 Option 56's own text (report pp. 66–67), CBO
`budget-options/54798` and `budget-options/2013/44903`, CBO/JCT's ACA
employment-based-coverage analyses, and JCT's methodology statements. CBO's
Option 56 names **two** channels and ranks them — plan switching first, then
"to a lesser extent… fewer workers would enroll in employment-based coverage" —
and **quantifies neither**, which is what `W4_option56_excess_share.md`
finding 5 already recorded.

What the search *did* turn up is an elasticity, and it is the wrong one: CBO
and JCT's employer-offer price elasticities by firm size (−0.07 for 1,000+
employees, −0.15 for 100–999, −0.38 for 25–99, −1.14 for smaller firms). Those
price the **coverage-dropping** channel — the one CBO calls the lesser of the
two — and there is no published number for the plan-switching channel that
carries the rest. Building a share of the revenue effect out of the minor
channel's elasticity would produce a magnitude with a citation attached to the
wrong half of the mechanism. **Left at 0.20**, recorded here, and carried over.

### 1.4 Retirement contributions, `cap` — **0.30 left; search recorded**

Searched: CBO `budget-options/2018/54799` and its 2024 successor
`budget-options/60948` (both 403 to this environment directly; the 2018 text
was read for W7 and is quoted in `W7…md` §4.2 row 8), plus JCT's tax-expenditure
methodology. CBO quantifies exactly **one** behavioural leg — "The constraints
on Roth conversions would **reduce revenues by $6 billion** over that period" —
and states that the offsetting gain falls *outside* the scoring window
("**Eventually**, the revenues gained by taxing more investment income would
probably outweigh those lost"). One named leg of several, with the net sign
declared to reverse beyond the window, is not the share this parameter
multiplies. **Left at 0.30**, recorded, carried over. Nothing scored reads it:
`create_cap_retirement_contributions` has no benchmark and no preset, and its
`derived` mode raises `ExpenditureDistributionMissing`.

### 1.5 SALT, `eliminate` and `expand` — **0.05 left; search recorded**

Searched: CBO 58635's extended discussion of Option 49 (the source W7 read for
both SALT directions), CBO 60557 Option 49, JCT's SALT estimates, CRS R46246
(*The SALT Cap: Overview and Analysis*) and RL32781, TPC's *Revisiting the State
and Local Tax Deduction*, and Yale Budget Lab's *Mortgage Interest Deduction:
Options for Reform* (2025). CBO names the channel — affected taxpayers "would
also choose to reduce their spending on other deductible items… that response
would… **increase their tax liability**" — and prices nothing. Yale prices
something adjacent and not this: the mortgage-interest tax expenditure moving
**$323B → $497B** when the SALT limit goes $10,000 → $20,000. That is a
different dose (a doubled cap, not repeal), a different expenditure (mortgage,
not SALT) and a *level*, not a share; converting it into this parameter would
be construction, not sourcing. **Left at 0.05** on both SALT reforms, recorded,
carried over. This is separate from — and does not touch — the SALT **baseline**
question (§6.2 item 3, owner decision ⑧), which is out of scope for this lane.

## 2. Files

* `fiscal_model/tax_expenditure_distributions.py` — one new method on
  `DeductionDistribution` implementing §1.2's identity.
* `fiscal_model/tax_expenditures_core.py` — `OffsetMagnitudeRule` and
  `OFFSET_MAGNITUDES`, keyed on the reform exactly as `OFFSET_DIRECTIONS` is
  and scoped by `cap_unit` the same way; `resolved_offset_magnitude()`;
  `estimate_behavioral_offset` reads it; `BEHAVIORAL_ELASTICITIES`'s comment
  rewritten to say which of its five entries are now superseded by a sourced
  reform rule and which three are still unsourced, each with §1's search.
* `tests/` — the rules, the identity, the resolution order, the scoping
  fallbacks, and the two adopted values against their published figures.
* `fiscal_model/ui/tabs/results_summary.py` — one self-contained caption
  function and one call line (Decision 6; §3.4).

**`BEHAVIORAL_ELASTICITIES` keeps all five values.** Deleting the mortgage and
charitable entries would make any reform outside the two sourced rules — a
charitable floor, a mortgage cap — fall through to the factories'
`behavioral_elasticity=0.0` and score with **no** behavioural response at all.
Absence of a sourced magnitude is not evidence that the magnitude is zero, which
is the same standard W7 applied to directions. The table stays as the documented
unsourced fallback and the comment says so.

## 3. Pre-registered outcomes

Written from §1 and the arithmetic of `final = static × (1 ± e)` before the code
changed. In `reported` mode the static annual is a constant the engine grows, so
changing `e` multiplies the whole ten-year figure by exactly
`(1 ± e_new)/(1 ± e_old)`. A disagreement between this section and §6 is a
finding to write down, not a number to quietly correct.

### 3.1 Rows

| row | tier | e | factor | before | **predicted after** | error before → **after** |
|---|---|---|--:|--:|--:|---|
| `eliminate_mortgage` | reconstruction | 0.10 → 0.145028 | 0.94997 | −270.3 | **−256.8** | 26.50% → **30.2 ± 0.5** |
| `cap_charitable` | **fitted** | 0.40 → 0.220780 | 0.87199 | −200.6 | **−174.9** | 0.30% → **12.6 ± 0.5** |
| `cap_employer_health` | fitted | 0.20 (unchanged) | 1 | −449.5 | −449.5 | 0.10%, **unchanged** |
| `eliminate_step_up` | fitted | 0.00 | 1 | −523.5 | −523.5 | 4.70%, **unchanged** |
| `repeal_salt_cap` | reconstruction | 0.05 (unchanged) | 1 | 1,155.6 | 1,155.6 | 1.10%, **unchanged** |
| `eliminate_salt` | reconstruction | 0.05 (unchanged) | 1 | −1,260.3 | −1,260.3 | 22.30%, **unchanged** |
| `cbo_opt56_employer_health_income_only` | **Tier 1** | 0.20 (unchanged) | 1 | −605.8 | −605.8 | 13.10%, **unchanged** |

**Both movers are registered regressions.** Neither elasticity was chosen to
move a row toward a target and neither could have: `eliminate_mortgage`'s target
is a published range H9 set at roughly 1.36× the model's own figure, so *any*
increase in an eroding offset moves it away; `cap_charitable`'s fitted annual was
chosen, by W7's finding 3, so that `static × (1 + 0.40)` lands on −200.0, so
*any* change to the magnitude moves it off. That is the lane's whole shape: a
sourced number replacing an unsourced one that was closer to the target.

**`cap_charitable` rates Acceptable (10–20%), not Poor (>20%).** At 12.6% it is
7.4 points inside the bar, so no fitted row goes Poor, strict readiness reports
no `documented_calibrated_policy_ids`, and PR #119's reclassify-don't-retune
precedent is not invoked. If it goes Poor, the lane **reports and stops**
(§5).

### 3.2 The six fitted constants, and which kind each is

W7's finding 3 established that three of the six were fitted so the **static**
path hits the target and three so the **magnified score** does. That split is
what decides whether a row can move at all, so it is restated here with this
lane's verdict against each. **No constant is opened.**

| constant | annual | fitted to | e moves? | row moves? |
|---|--:|---|:-:|---|
| `cap_employer_health` | 31.2 | static × (1+e) | no | no |
| `cap_charitable` | 12.5 | static × (1+e) | **yes** | **yes, registered** |
| `eliminate_mortgage` | 26.2 | **static** | **yes** | **yes, registered** |
| `repeal_salt_cap` | −96.0 | **static** | no | no |
| `eliminate_salt` | 104.7 | **static** | no | no |
| `eliminate_step_up` | 43.6 | neither (e = 0) | no | no |

Re-fitting any of the six is what `HIGH_STAKES_ACCURACY.md` §1.1 forbids and
what this lane's §5 rules out explicitly.

### 3.3 Tiers

* **Tier 1: 26 @ 14.5%, unchanged to the cent on all 26 rows.** The tier's one
  expenditure row is Option 56, whose magnitude §1.3 leaves alone. The pooled
  gate (`--max-mean-error 20 --min-within-25pct 22`) and the per-class ceiling
  (`tax_expenditure=17`) are both untouched.
* **Fitted calibrated: 16 @ 1.5% → 16 @ ≈2.3%**, still 16/16 within 15%. One row
  moves, 0.3% → 12.6%; no row leaves or joins the tier, so the headline reading
  *is* the held-in-place reading.
* **Unfitted reconstructions: 39 @ 56.7% → 39 @ ≈56.8%**, within-15 10/39 and
  within-25 13/39 both unchanged (26.5% was already outside 25%).
* **Leave-one-out — this is where the lane costs the most, and it is
  pre-registered as a regression**:

  | | before | **predicted after** |
  |---|--:|--:|
  | `eliminate_mortgage` LOO | −257.9, **29.9%** | **−245.0, 33.4 ± 1** |
  | `cap_charitable` LOO | −173.8, **13.1%** | **−151.6, 24.2 ± 1** |
  | Expenditures module (n=5) | **40.6%** | **43.6 ± 1** |
  | LOO suite (n=18) | **35.7%** / 29.1% / 6 within 15% | **36.5 ± 1** / ≈29% / **5** |

  The CI ceiling is `--max-mean-error 75` and is nowhere near approached.
  `cap_charitable` crossing 15% is what takes within-15 from 6 to 5.

  The plan's H7 bands (`eliminate_mortgage` 8 ± 5, Expenditures 30 ± 8) are
  **not adopted and are recorded as unreachable**: they were written against the
  pre-H9 −$300.0B point target *and* in the wrong direction even against it —
  the held-out mortgage static is already 4.5% short of −$300.0B (JCT's $25.0B
  base annual against the fitted $26.2B), so a **larger** erosion takes the row
  further from any target below it, never toward one. `cap_charitable`'s
  20 ± 8 is the one plan band this lane's own arithmetic lands inside.

### 3.4 Presets

**Exactly one of the 53 moves: 📋 Cap Charitable Deduction.** On the app's
FY2026–2035 window the scored result goes

| | static | behavioural | **final (deficit)** |
|---|--:|--:|--:|
| before | 126.98882660 | −50.79553064 | **−177.78435723** |
| predicted after | 126.98882660 | **−28.03635** | **−155.02518** |

— a **12.8%** fall in the revenue raised, and a Decision 6 caption is therefore
owed and ships in the same PR, as one self-contained function plus one call line
in `results_summary.py`, computed from the scored result so it cannot drift from
the figure above it.

The other three expenditure presets do not move: Cap Employer Health Exclusion
and Repeal SALT Cap keep unchanged magnitudes, and Eliminate Step-Up Basis has
an elasticity of exactly zero. `eliminate_mortgage` and `eliminate_salt` are
scorecard rows with no preset (`preset_handler._create_expenditure_policy` has
four branches). The remaining 49 presets do not reach this module.

## 4. Falsification

The lane is falsified — and says so in §6 rather than adjusting — if:

1. **any row other than `eliminate_mortgage` and `cap_charitable` moves**;
2. **Tier 1 moves at all**, on any of its 26 rows;
3. either mover moves by other than its `(1 ± e_new)/(1 ± e_old)` factor, which
   would mean the magnitude is not applied where §1.0 says it is;
4. **`cap_charitable` rates Poor**, or strict readiness reports a
   `documented_calibrated_policy_ids`;
5. **any preset other than 📋 Cap Charitable Deduction moves**;
6. the derived charitable share is not **0.220780** at `c = 0.28`, or the
   mortgage share not **0.145028**, when recomputed after the change.

## 5. What this lane will not do

* **Not re-fit any of the six fitted annuals.** `scenarios.py` and
  `tax_expenditures_factory.py`'s constants are not opened. §3.1 predicts no row
  goes Poor; if one does, the lane **reports it and stops**, the way PR #119
  did, rather than retuning or exempting. *(Outturn: no row went Poor.
  `scenarios.py` was opened after all — for the opposite of a re-fit, to mark
  `cap_charitable` `calibrated_to_target=False` under PR #119's standing rule.
  Not one annual moved; §6.6a and the leakage guard in `tests/test_loo.py` are
  the evidence.)*
* **Not touch the SALT baselines.** `repeal_salt_cap` is priced against a
  permanent $10,000 cap and `eliminate_salt` against CBO Option 49's lapsed-cap
  world; reconciling them is §6.2 item 3 and owner decision ⑧, explicitly out of
  scope for this lane.
* **Not adopt an unsourced magnitude for employer health, retirement or SALT.**
  Three of the five stay exactly as they are, each with its search recorded in
  §1 so the next lane does not repeat it.
* **Not move a target.** `target_revisions.py`, `preregistered.py`,
  `holdout.py`, `loo.py`'s guards, `KNOWN_SCORES` and `CBO_SCORE_MAP` are not
  opened. `eliminate_mortgage` is scored against the range H9 set, unchanged.
* Not build W4's still-open findings 2, 4 and 5 (the health-spending-account
  base, Option 56's payroll leg, the plan-switching channel).
* Not touch `CLAUDE.md`, `README.md`, `planning/NEXT_STEPS.md`,
  `planning/MODELING_IMPROVEMENT.md`, `CHANGELOG.md` or `.github/`.

Anything that moves outside this list is a finding and gets written into §6.

## 6. Outturn

*Appended in the lane's last commit. Every figure below is from a command named
beside it, run on this branch.*

**Every prediction in §3 landed, and all but one of them to the digit.** Two
scored rows moved, both registered regressions, both by exactly the
`(1 ± e_new)/(1 ± e_old)` factor §3.1 computed; Tier 1 is identical to the cent
on all 26 rows; one preset moved and it is the one §3.4 named; no fitted row
went Poor. None of §4's six falsifications fired. The single figure outside its
band is the leave-one-out **median**, hedged at "≈29%" and landing at 30.2%,
which is a reordering of an 18-row list rather than a movement in any
derivation.

### 6.1 What the module reads now

`python scripts/…` (the lane's own decomposition over all eight factories, both
modes):

| reform | mode | e before | **e after** | direction |
|---|---|--:|--:|---|
| `eliminate_mortgage` | reported / derived | 0.100000 | **0.14502762** | erode |
| `cap_charitable` (28% ceiling) | reported / derived | 0.400000 | **0.22077987** | magnify |
| `cap_employer_health` | reported / derived | 0.20 | 0.20 | magnify |
| `repeal_salt_cap` | reported / derived | 0.05 | 0.05 | magnify |
| `eliminate_salt` | reported / derived | 0.05 | 0.05 | magnify |
| `cap_retirement` | reported | 0.30 | 0.30 | erode |
| `eliminate_step_up` | reported / derived | 0.00 | 0.00 | erode |
| `eliminate_like_kind` | reported / derived | 0.00 | 0.00 | erode |

Both adopted values are exactly §1's: `1 − 61.9/72.4 = 0.14502762…` and the
identity's `0.220780` at `ε = 0.5`. No direction changed and no fitted annual
was opened — `tax_expenditures_factory.py`'s six constants and
`validation/scenarios.py` are untouched.

### 6.2 What moved

`python scripts/cold_holdout.py --json`, compared row by row rather than on the
tier means:

| | before | after |
|---|--:|--:|
| **Tier 1 — out-of-sample** | 26 @ 14.5% / 11.5% / 16 / 22 | **unchanged, to the cent on all 26 rows** |
| **Tier 2 — fitted** | 16 @ **1.5%**, median 0.1%, 16/16 within 15% | **16 @ 2.3%**, median 0.1%, **16/16** within 15% |
| ... held in place | 27 @ 11.9%, median 1.1%, 22/27 | **27 @ 12.4%**, median **3.7%**, 22/27 |
| **Tier 2 — reconstructions** | 39 @ **56.7%** / 36.9%, 10/39, 13/39 | **39 @ 56.8%** / 36.9%, 10/39, 13/39 |
| Shipped presets (53) | — | **1 moved**; the other 52 byte-identical in both engine modes |

**Exactly two scorecard rows moved, and they are the two §3.1 named:**

| row | tier | target | before | after | error before → after | **predicted** |
|---|---|--:|--:|--:|---|---|
| `cap_charitable` | fitted | −200.0 | −200.6 | **−174.9** | 0.3% → **12.5%** | −174.9, 12.6 ± 0.5 |
| `eliminate_mortgage` | reconstruction | [−495.0, −367.9] | −270.3 | **−256.8** | 26.5% → **30.2%** | −256.8, 30.2 ± 0.5 |

No row left or joined either calibrated tier, so the headline reading *is* the
held-in-place reading for this lane's mechanism: 16 @ 2.3% on the same 16 rows,
39 @ 56.8% on the same 39. The reconstruction tier's `Expenditures`
sub-population (`repeal_salt_cap`, `eliminate_salt`, `eliminate_mortgage`) goes
**16.6% → 17.9%**, median unchanged at 22.3%.

**`cap_charitable` rates Acceptable and nothing was reclassified.** Strict
readiness, queried directly for the field rather than compared as text —
PR #119's §7.5 lesson — returns `documented_calibrated_policy_ids == []` and
`strict_readiness_issues` returns `[('runtime', None)]`, the Python 3.14 issue
that fails on `main` too. `scenarios.py` was never opened.

**The leave-one-out is the price, and §3.3 named it in advance**
(`python scripts/run_loo.py --donor-matrix`, which differs from `main` in
**six lines** and in no derivation outside this module):

| | before | after | predicted |
|---|--:|--:|---|
| `eliminate_mortgage` LOO | −257.9, **29.9%** | **−245.0, 33.4%** | −245.0, 33.4 ± 1 |
| `cap_charitable` LOO | −173.8, **13.1%** | **−151.6, 24.2%** | −151.6, 24.2 ± 1 |
| Expenditures module (n=5) | **40.6%** | **43.6%** | 43.6 ± 1 |
| LOO suite (n=18) | **35.7%** / 29.1% / 6 within 15% | **36.5%** / **30.2%** / **5** | 36.5 ± 1 / ≈29% / 5 |

The CI ceiling (75%) is not approached, and the capital-gains donor matrix is
byte-identical.

### 6.3 The preset, and the caption it ships with

One of the 53 moved, on the app's FY2026–2035 window:

| 📋 Cap Charitable Deduction | static | behavioural | **headline (conventional)** | dynamic total |
|---|--:|--:|--:|--:|
| before | 126.98882660 | −50.79553064 | **−177.78435723** | −155.98287313 |
| after | 126.98882660 | **−28.03657689** | **−155.02540348** | −136.01482279 |

— **−12.80%** of the revenue raised, against §3.4's predicted −155.025. Its
validation badge drops **Excellent → Acceptable** with it, which is the correct
reading: the green badge was bought by a magnitude no document supports. Its
label keeps `(-$200B)`, because that is the published target and H9 examined and
left it.

The Decision 6 caption is one function and one call line in
`results_summary.py`, computed from `static_deficit_effect + behavioral_offset`
— the conventional headline, in both engine modes — and reconstructing the
previous figure from `BEHAVIORAL_ELASTICITIES` rather than from a literal, so it
cannot drift. A test asserts the static and dynamic renders are the same string,
because PR #144's review found a caption one wave ago that read
`final_deficit_effect` and so disagreed with the headline above it by 69% on a
dynamic run. The caption also reaches `eliminate_mortgage`, which no preset
ships but Tailor and the API can construct.

### 6.4 Eight findings

**1 — The plan's "nearer 18%" is not reproducible, and the correct figure is
22.1%.** Registered in §1.2 before any code and confirmed by the identity: at
CRS's central price elasticity of 0.5 the charitable ceiling's implied share is
**0.220780**. Eighteen percent would need `ε = 0.405`, which is not a figure CRS
prints. The plan and `W7…md` finding 5 both carried the 18%; it should be read
as an estimate made in passing, not a result.

**2 — 0.40 was the right identity at an elasticity above the whole published
band.** W7 guessed the shipped 0.40 "has the size of a price elasticity of
giving" and that it was therefore applied to the wrong quantity. Inverting it
through the identity is sharper and worse: **0.40 corresponds to `ε = 0.906`**,
against CRS R40518's low 0.1 / central 0.5 / **high 0.79**. So the module was
not confusing two quantities by a factor — it was assuming a giving response
above the top of the range CRS's own literature review settles on, by 15%.

**3 — A magnitude is a property of the reform, for a second reason directions
do not have.** W7 established the *grain* on the documents: CBO gives one
deduction opposite verdicts under a rate ceiling and a floor. The magnitude
forces the same grain on arithmetic alone, and the direction is
counter-intuitive: **tightening the ceiling from 28% to 15% roughly halves the
behavioural share, 0.2208 → 0.1140**, because the recapture rate *is* the cap
rate and that dominates the larger price change. A module-wide constant would
have over-magnified CBO 60557 Option 49's 15% alternative by **94%**, and the
shipped 0.40 would have over-magnified it by **251%**. Nothing in the
repository scores that alternative today, which is exactly why a constant would
have survived unnoticed.

**4 — The one published elasticity in employer health's neighbourhood prices
the channel CBO calls the lesser one.** W4 finding 5 recorded that CBO publishes
no elasticity for Option 56; that is true of the option's own text, and the
search turned up something adjacent — CBO and JCT's employer **offer** price
elasticities by firm size, −0.07 for 1,000+ employees, −0.15 for 100–999, −0.38
for 25–99, −1.14 for smaller firms. Those price coverage dropping, which
Option 56's own sentence ranks *below* plan switching ("To a lesser extent…"),
and nothing published sizes the plan-switching channel that carries the rest.
So the finding is not "there is no elasticity" but the sharper "the available
elasticity is attached to the wrong half of the mechanism" — which is why 0.20
is left rather than replaced with something that would have had a citation.

**5 — Both movers regress for W7 finding 4's reason, stated in the other
direction.** The held-out statics are already short of their targets —
mortgage's JCT base annual of $25.0B gives −286.6 against a −367.9 anchor, and
charitable's held-out static is 124.1 against −200.0 — so a **larger** erosion
and a **smaller** magnification both move the score further from the target.
The magnitudes were chosen on documents and not on rows, and that they cost the
leave-one-out suite 0.8pp is the price of choosing them that way. The symmetric
observation is the useful one: if a sourced magnitude had *improved* both rows,
the suspicion would be that the document had been chosen to fit.

**6 — The plan's H7 bands were unreachable and its baseline was two weeks
stale.** §0 recorded this before the lane opened a file: `eliminate_mortgage`'s
LOO baseline of 14.0% predates H9's range revision (it reads 29.9%), the
Expenditures module reads 40.6% and not 37.5%, and the pre-registered *direction*
was wrong even against the old −$300.0B point target, because a bigger erosion on
a static already 4.5% short of it cannot move toward it. `cap_charitable`'s
20 ± 8 is the one plan band this lane landed inside, at 24.2%. A plan band
computed off a number a later wave has moved is worth re-deriving rather than
inheriting.

**7 — There is a fourth way for a fitted constant to stop being a calibration,
and one gate already knew it. `tests/test_loo.py` found it.** The one gate this
lane's §3 did not anticipate is
`test_loo_is_materially_worse_than_by_construction`, which asserts that the
*fitted* subset's by-construction error is bookkeeping — mean below 1.0% over
nine cases. It **failed**, at 1.42%, and the whole of the move is
`cap_charitable` going 0.3% → 12.5%. That is correct and is the finding:
**`create_cap_charitable_deduction`'s 12.5 was fitted so that `static × (1 +
0.40)` lands on −$200.0B, so once the 0.40 is sourced the constant is fitted to
a quantity the module no longer computes.** `CLAUDE.md` counts four live
mechanisms that move a row out of the fitted tier — a ledger target revision,
Wave 2's deleted tuples, Wave 3's unfitted trade constants, and PR #119's
sign-defect reclassification — and this is a fifth. The test's own comment
already says the by-construction number measures bookkeeping "only where a
constant is actually fitted **to the figure the suite scores against**"; it just
enumerated two of the ways that can stop being true and now has to enumerate
three.

**The row is not retuned — that is what §1.1 of the plan forbids — and the
lane's first pass left the reclassification as an owner question.** It was not
one: PR #119's rule is standing, and §6.6a applies it. `cap_charitable` is
`calibrated_to_target=False`, the fitted tier goes 16 → 15 and the reconstruction
tier 39 → 40, and the three places those counts are pinned move with it. The
leakage guard is the part worth keeping either way: `−174.9 × 1.40 / 1.220780 =
−200.6`, asserted within 1% of −$200.0B, so "reclassified" cannot become a
licence to move the constant. A later lane that retunes it fails there.

**8 — A derived magnitude needs a fallback the static path does not have.**
`_share_of_benefit_above_cap` *raises* `ExpenditureDistributionMissing` when a
cap is applied to an expenditure with no transcribed distribution, because there
a missing distribution changes the score. A derived **magnitude** with no
distribution returns `None` and falls back to the unsourced table instead, which
is the right asymmetry: an offset is a haircut on a number that already exists,
and refusing to score a reform because its *offset* cannot be derived would be a
harder failure than the defect. No shipped reform reaches that branch today.

### 6.5 Falsification: none of the six fired

1. **A row other than the two moving** — did not fire. All 26 Tier 1 rows, the
   other 15 fitted rows and the other 38 reconstructions are identical to the
   cent, checked row by row.
2. **Tier 1 moving at all** — did not fire. `cbo_opt56_employer_health_income_only`
   is −605.8 at 13.10%, as it was.
3. **A mover moving by other than its factor** — did not fire.
   `−270.3 × (1 − 0.14502762)/(1 − 0.10) = −256.8`;
   `−200.6 × 1.22077987/1.40 = −174.9`.
4. **`cap_charitable` rating Poor, or strict readiness naming a calibrated row**
   — did not fire; `documented_calibrated_policy_ids` is empty.
5. **A preset other than Cap Charitable Deduction moving** — did not fire. The
   sweep over all 53 stable ids × static/dynamic differs in two lines, both that
   preset's.
6. **The derived shares differing from §1** — did not fire: 0.220780 and
   0.145028, recomputed after the change by a test that rebuilds the identity
   rather than asserting the constant.

### 6.6 Gates

| command | result |
|---|---|
| `ANTHROPIC_API_KEY= python -m pytest tests/ -q` | **4,024 passed, 7 skipped** (`20e356d`: 4,002 passed, 7 skipped — the lane adds 22). The first full run had **one failure**, `test_loo_is_materially_worse_than_by_construction`, which is finding 7 |
| `python scripts/cold_holdout.py --max-mean-error 20 --min-within-25pct 22` | **exit 0** |
| `python scripts/cold_holdout.py --max-class-mean-error …` (all eight) | **exit 0** |
| `python scripts/run_loo.py --donor-matrix --max-mean-error 75` | **exit 0** (36.5%) |
| `python scripts/build_validation_headline.py --check` | **exit 0** (77 published of 81, unchanged) |
| `python scripts/run_validation_dashboard.py` | **exit 1**, as on `20e356d`; the diff is **nine lines**, all of them this module's |
| strict readiness, queried for the field | **`[('runtime', None)]`**, unchanged |
| `python -m ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py` | clean |

The dashboard's exit 1 is the pre-existing `runtime [degraded] Python 3.14.0`
and `microdata [warn]` pair, neither this lane's.

### 6.6a The reclassification — owner item ① answered, and applied

*Appended after the owner's standing answer: PR #119's rule is that a constant
which reproduced its target **only through an unsourced or defective magnitude
is not a calibration to that target** — reclassify, do not retune, do not
exempt. Finding 7 left that open as an owner decision; it was not open.*

`cap_charitable` is now `calibrated_to_target=False`, by the same wiring PR #119
used for `trump_corporate_15` and `repeal_ptc`: `calibrated_to_target` is
threaded through the **expenditure** runner
(`specialized_business.py:validate_expenditure_policy`) with a `True` default,
so only a scenario that says otherwise moves, and `scenarios.py`'s
`cap_charitable` entry says otherwise with the reason and two `limitations`
written in. **No constant was retuned and no scored number moved** — all 81
`model_10yr_billions` are identical to the reading in §6.2, `cap_charitable`
still scores −174.9 and `eliminate_mortgage` −256.8.

**The tiers move by composition, and the fitted tier's mean rises rather than
falls, which is the tell that this is not a tidy-up:**

| | §6.2 (H7 before reclassifying) | **after** |
|---|--:|--:|
| Tier 1 — out-of-sample | 26 @ 14.5% / 11.5% / 16 / 22 | **unchanged, to the cent** |
| Tier 2 — fitted | 16 @ **2.3%**, median 0.1%, 16/16 | **15 @ 1.6%**, median **0.0%**, **15/15** |
| ... held in place | 27 @ 12.4%, median 3.7%, 22/27 | **26 @ 12.4%**, median **2.4%**, **21/26** |
| Tier 2 — reconstructions | 39 @ **56.8%** / 36.9%, 10/39, 13/39 | **40 @ 55.7%** / **33.6%**, **11/40**, **14/40** |
| leave-one-out | 18 @ 36.5% / 30.2% / 5 | **unchanged** |

Read those two means the way `CLAUDE.md` insists: **1.6% is not an improvement
on 2.3% and 55.7% is not an improvement on 56.8%.** The fitted tier fell because
the row it lost was carrying 12.5% against a tier of near-zeros, and the
reconstruction tier fell because a 12.5% row joined a tier averaging 56.8% —
both moves are arithmetic of membership, and the *fitted* reading against its
pre-reclassification self is **1.5% → 1.6%**, up. The held-in-place line loses a
row for the same reason and its within-15 count goes 22/27 → 21/26.

**Badge composition moves with it**, pinned in three places rather than
discovered: `test_the_tier_composition_is_what_the_lane_registered`
**16/25/3 → 15/26/3**, `test_no_other_row_left_the_fitted_tier` **16/39 →
15/40** with `cap_charitable` named in the assertion the way H9's five are, and
`preset_validation.py`'s inline comment for `charitable-deduction-cap` goes
`# fitted, 0.3%` → `# reconstruction, 12.5%`. The shipped badge on 📋 Cap
Charitable Deduction therefore reads **reconstruction**, not "Calibrated" — the
honest label, since the constant no longer reproduces the target.

**`test_loo.py`'s exclusion is gone and the guard that mattered stayed.** The
hand-written `{"cap_charitable"}` set is replaced by `_unfitted_case_ids()`,
which reads the scenario registries the LOO suite itself scores against — the
same dicts `scorecard.py` turns into `calibrated_to_target` — so the exclusion
is now a consequence of the reclassification rather than a second, independent
edit, and a row nobody reclassified cannot be waved through by editing the test.
The `CapitalGains` clause stays beside it for the one mechanism the flag cannot
see: those three cases have nothing held out at all. **The leakage guard is kept
and strengthened**: `−174.9 × 1.40 / 1.220780 = −200.6`, asserted within 1% of
−$200.0B, plus an assertion that the case really is in the unfitted set. That is
what stops "reclassified" becoming a licence to move the constant — a later lane
that retunes it to close the 12.5% fails there.

`build_validation_headline.py --check` passes **unchanged at 77 published of
81**: reclassification changes a row's *tier*, never whether its target is
published, so `headline_counts.json` needed no regeneration. Strict readiness
still returns `[('runtime', None)]` with `documented_calibrated_policy_ids`
empty — and it would have stayed empty either way, which is finding 7's point
restated: **the classification follows the finding, not the rating**, exactly as
`repeal_ptc`'s own note in `scenarios.py` says.

### 6.7 Carry-overs

* **Three magnitudes are still unsourced** — employer health 0.20, retirement
  0.30, SALT 0.05 — each with its search in §1 so the next lane does not repeat
  it. Employer health is the one that matters: it is the only one on a Tier 1
  row (Option 56, 13.1%), and finding 4 says what would have to be published
  before it could move.
* **Option 56's other two residuals are untouched**: the base omission (CBO caps
  premiums *and* FSA/HRA/HSA contributions; the premium distribution has no
  account dimension) and the plan-switching channel — W4's findings 2, 4 and 5.
* **The SALT baseline question** (§6.2 item 3, owner decision ⑧) is where this
  lane left it, deliberately.
* **`eliminate_mortgage` is a range row whose model sits outside both bounds**,
  now by $111.1B rather than $97.6B. H9 recorded the 2.4× as a baseline
  difference rather than a simulator one; nothing here addresses the level.
* **Nothing scores a charitable **floor** or CBO Option 49's 15% ceiling**, both
  of which the module can now express with a per-reform magnitude. Finding 3 is
  the argument for registering the 15% alternative as a benchmark.
* **Two shared docs now assert something the code contradicts, and this lane
  deliberately did not edit them** — the same call W7 made and for the same two
  reasons (they are narratives *of prior lanes*, and Wave D requires
  file-disjointness between siblings). `docs/METHODOLOGY.md` line 376 says "**The
  magnitudes are still unsourced**, all five of them" and repeats the
  unreproducible 18%; `docs/VALIDATION.md` line 177 says "**The magnitude is
  still unsourced**, here and on all five entries in `BEHAVIORAL_ELASTICITIES`".
  Both are true of three entries now and false of two. A docs pass owns them,
  together with `docs/VALIDATION.md` line 400's older claim that
  `TaxExpenditurePolicy` "is the single entry in `CONVENTION_EXCEPTIONS`",
  which PR #128 already falsified.
