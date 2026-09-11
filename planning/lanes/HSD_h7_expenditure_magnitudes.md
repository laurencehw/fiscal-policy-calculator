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
`target_revisions.py`, `KNOWN_SCORES`/`CBO_SCORE_MAP`, `scenarios.py`,
`.github/`, or any shared doc.

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
  did, rather than retuning or exempting.
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

*Appended in the lane's last commit.*
