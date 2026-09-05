# Provenance lane — Wave 4 targets

*Opened 2026-09-02 on `provenance/wave4-targets`, branched from `main` @
`5deef17`. Work under `planning/MODELING_IMPROVEMENT.md` §6.2 items **3**
(`repeal_salt_cap`'s unsourced $1,100B), **4** (the mortgage record's unsourced
`annual_cost_no_limit`), **5** (`ctc_extension` against JCT's +$816.8B) and
**6** (the twelve remaining `line_item_differs` rows), plus the three tariff
targets `L8_tariffs.md` left flagged. Both supersede mechanisms are used: the
Tier-1 manifest (`fiscal_model/validation/preregistered.py`) and the Tier-2
revision ledger (`fiscal_model/validation/target_revisions.py`).*

**No modelling change at all.** Every `model_10yr_billions` in the scorecard is
byte-identical to `5deef17`, every leave-one-out *derivation* is unchanged, no
constant was retuned, no mechanism altered, no CI threshold touched, no case
deleted or retired. What moved is thirteen targets and the labels that quote
them.

Three commits, in the order the rules require:

| Commit | What |
|---|---|
| `318be6b` | **the ledger** — twelve Tier-2 revisions and one Tier-1 supersession entered, scored against by nothing |
| `22ccdd2` | **the scoring** — `CBO_SCORE_MAP`, `scenarios.py`, `KNOWN_SCORES` and the preset labels moved onto them |
| this one | stamps both commits into `WAVE4_PROVENANCE_*` and writes this file |

"The target moved before the model was scored against it" is therefore
checkable from `git log`, not asserted in prose.

## 1. What each target was, and what it is now

Twelve calibrated targets, one out-of-sample target. The model column is the
same number before and after — that is the point of the table.

| Target | Was | Is | Document row | Model | Err before → after |
|---|---|---|---|---:|---|
| **`eliminate_salt`** | −$1,200.0B, "JCT estimate", no table | **−$1,621.0B** | CBO pub. **60557**, Option 49 *"Eliminate or Limit Itemized Deductions"*, row *"Eliminate state and local tax deductions"*, report **p. 59** (PDF p. 65) | −$1,260.3B | 5.0% → **22.3%** |
| **`repeal_salt_cap`** | +$1,100.0B, "JCT", **no document at all** | **+$1,169.0B** | PWBM, Novak, *"Lifting the SALT Cap"*, **Table 3** *(Against Extended TCJA, FY25-34)*, row *"Repeal SALT Cap"* | +$1,155.6B | 5.1% → **1.2%** |
| **`biden_gilti_reform`** | −$280.0B, a rounded headline | **−$373.9B** | Green Book **FY2025**, Table of Revenue Estimates, *"Revise the global minimum tax regime, limit inversions, and make related reforms"*, report **p. 239** (PDF p. 247) | −$230.3B | 17.8% → **38.4%** |
| **`fdii_repeal`** | −$200.0B, matching neither figure Treasury prints | **−$158.0B** (the gross row) | Green Book **FY2025**, *"Repeal the deduction for foreign-derived intangible income"*, $157,993M, report **p. 239** | −$110.7B | 44.7% → **29.9%** |
| **`biden_full_international`** | −$700.0B, a rounded headline | **−$632.2B** | Green Book **FY2025**, *"Subtotal, Reform International Taxation"*, $632,200M, report **p. 240** (PDF p. 248) | −$353.7B | 49.5% → **44.1%** |
| **`biden_eitc_childless`** | +$178.0B, credited to JCT, no table | **+$162.6B** | Green Book **FY2025**, *"Restore and make permanent the American Rescue Plan expansion of the earned income tax credit for workers without qualifying children"*, $162,553M, report **p. 242** | +$178.0B | **0.0%** → **9.5%** |
| **`ira_enforcement`** | −$200.0B, 2% below CBO's **withdrawn** $203.7B | **−$180.4B** | CBO pub. **58390** (Aug 2022), letter **p. 1**: *"revenues will increase by $180.4 billion over the 2022-2031 period"* | −$188.9B | 5.5% → **4.7%** |
| **`repeal_ev_credits`** | −$200.0B, attributed to CBO | **−$182.3B** | JCT **JCX-35-25**, sec. 30D ($77,829M) + sec. 45W ($104,516M), **p. 3** (PDF p. 5) | −$228.4B | 14.2% → **25.3%** |
| **`extend_enhanced_ptc`** | +$350.0B on a record declaring FY2025-2034 | **+$335.0B** | CBO/JCT pub. **60437** (June 2024), letter **p. 1** | +$366.2B | 4.6% → **9.3%** |
| **`trump_universal_10`** | −$2,000.0B, "Tax Foundation / Yale Budget Lab" | **−$2,171.1B** | Tax Foundation **FF861**, Table 3 *"Conventional Revenue Estimates"*, row *"10 Percent Universal Tariff"*, report **p. 4** | −$1,258.5B | 37.1% → **42.0%** |
| **`auto_tariff_25`** | −$100.0B, credited to CRFB | **−$386.2B** | Tax Foundation tariff tracker, **Table 5**, *"Section 232 Autos, Heavy Trucks, Buses, and Parts"*, conventional column, 2026-2035 | −$182.2B | 82.2% → **52.8%** |
| **`reciprocal_tariffs`** | −$1,200.0B, a point | **a published range, [−$1,800B, −$1,400B]**, anchor −$1,500B | CRFB, *"How Much Will Trump's New Tariffs Raise?"*, table *"Ten-Year Scores of Trump's Tariffs, If Made Permanent"*, FY2025-2034 | −$1,396.8B | 16.4% → **6.9%** vs the anchor; **inside** the range |
| **`biden_high_income_tax`** *(Tier 1)* | −$252.0B | **−$245.9B** | Green Book **FY2025**, *"Increase the top marginal income tax rate for high-income earners"*, $245,924M, report **p. 242** (PDF p. 250) | −$216.5B | 14.1% → **12.0%** |

**Six of the thirteen get worse.** That is the shape a correct provenance pass
has: if every revision improved its row, the suspicion would be that the
documents were chosen to fit rather than the figures read off them.

Four benchmarks were opened and **deliberately left**, recorded in
`EXAMINED_NOT_REVISED` (§4), and one target (`repeal_individual_amt`) stays
where the AMT/insulin lane left it, blocked on an owner decision this lane may
not make.

## 2. The two that were not merely unsourced

Most of the twelve are a rounded headline standing in for a printed row. Two are
a different kind of error, and both are the same kind of error as
`extend_tcja_amt`'s five-year figure in a ten-year column.

### 2.1 `auto_tariff_25` — a per-year claim in a ten-year column

The carried −$100B is credited to CRFB. CRFB itemises no auto tariff in any of
five tariff-revenue posts. The figure traces instead to Peter Navarro,
30 March 2025: *"We're going to raise about $100 billion with the auto tariffs
alone"* — a **per-year** claim, inside the "$6 to $7 trillion over the 10-year
period" that FactCheck.org and the *Washington Post* Fact Checker both ran down
as unsupported. Carried as a decade figure it is wrong by a factor of ten, and
in the direction that flatters the model: it made a module scoring −$182.2B look
82% out when the published conventional estimate is −$386.2B.

Superseded by a **point** rather than a range, because the second published
figure is not a second estimate of the same thing. Yale Budget Lab
(28 March 2025) scores the tariff *as announced* at $600-650B over 2026-35 —
before the trade-deal carve-outs and US-content exceptions the tracker's
as-in-force row reflects. Design gaps that remain, stated rather than adjusted:
the tracker row bundles heavy trucks and buses (at 10%, not 25%) and parts with
passenger vehicles, and neither publisher applies the module's 65% USMCA
carve-out — both model US-content exceptions instead.

### 2.2 `reciprocal_tariffs` — a dynamic score in a conventional column

−$1,200B is **exactly Tax Foundation's dynamic score** of the reciprocal
schedule, sitting in a scorecard whose every other target is conventional and
below all three published conventional estimates. It was a **tier** error, not a
magnitude error, and no amount of scaling would have found that.

CRFB's April 2025 comparison prints three conventional estimates of the same
announced schedule on the same fiscal window:

| Modeller (CRFB's table, FY2025-2034) | Conventional | Dynamic |
|---|---:|---:|
| CRFB | **$1.8T** | $1.6T |
| Tax Foundation | **$1.5T** | $1.2T ← *the superseded target* |
| Yale Budget Lab | **$1.4T** | $1.0T |

Three modellers, one policy, one window, **29% apart**. That is what a range
asserts and a point cannot, so the row is superseded by
**[−$1,800B, −$1,400B]** on the Wave 3 range mechanism. The anchor the
registries carry is Tax Foundation's $1.5T, chosen because Tax Foundation is
the publisher this repository's other two tariff benchmarks are scored against
— an in-range anchor, not a selection among the three.

The row therefore stays `line_item_differs`, exactly as `pillar_two_adoption`
does, because the anchor is not the transcribed figure and hiding the gap would
leave an editorial midpoint looking sourced.

The model's −$1,396.8B is **inside** the range. Its 6.9% against the anchor is a
distance from one modeller's point, not a measurement of accuracy; and one
design caveat the range does not close is that the published estimates apply a
10% floor rising to 50% by halving each partner's bilateral-deficit-to-imports
ratio (exempting steel, aluminium, autos and parts, copper, pharmaceuticals,
semiconductors and lumber), where the module applies a flat ~20pp to half of
goods imports.

## 3. `repeal_salt_cap` — the target was findable, and the rounding hid the baseline

§6.2 item 3 recorded $1,100B as unsourced and left the row reporting −29.4%
against it in leave-one-out. It is Penn Wharton's, **rounded**: PWBM's Table 2
gives −$1,116B over FY2024-2033. Rounding that to $1,100B is harmless. What the
rounding hid is not.

| PWBM, *"Lifting the SALT Cap"*, same reform | Baseline | 10yr |
|---|---|---:|
| Table 1 | **current law** (cap expires after 2025) | **−$197B** |
| Table 2 | extended TCJA, FY2024-2033 | −$1,116B |
| **Table 3** | **extended TCJA, FY2025-2034** | **−$1,169B** |

**5.7× apart on the baseline alone.** A SALT-cap target carried without its
baseline is ambiguous by an order of magnitude, so the revision adopts Table 3 —
the repository's own window — and the baseline now travels with the target in
both `benchmark_sources.py` and the scenario's `notes`. The extended-TCJA figure
is also the counterfactual the expenditure module's derived path computes, since
it prices repeal as (unlimited SALT expenditure − limited SALT expenditure) with
the cap in force throughout.

That leaves the contradiction `L6_tax_expenditures.md` §6 named **stated rather
than resolved**: `repeal_salt_cap` is now explicitly priced against a permanent
$10,000 cap while its twin `eliminate_salt` is priced on CBO Option 49's world
where the cap has lapsed. Reconciling them needs a baseline-vintage concept the
expenditure module does not have. Both rows now say which baseline they are on,
which is the most a provenance lane can do.

Two footnotes that belong with it. `eliminate_salt`'s revision is **not** a new
leak: PR #100 had already replaced `annual_cost_no_cap = 120.0` — the superseded
target over ten — with $89.55B computed from IRS SOI Table 2.1, so this revision
retires the last echo of that constant rather than creating another. And
"repeal the $10,000 cap" describes no live reform for most of the window:
P.L. 119-21 sec. 70120 replaced it with $40,000 for 2025-2029 reverting to
$10,000 in 2030, and JCT's row for *that* provision (+$946.2B) is already
carried separately as `pl119_21_salt_cap_40k`.

## 4. Examined and deliberately not moved

Four verdicts, in `EXAMINED_NOT_REVISED`. The registry exists so that "somebody
opened the document and decided against" stops looking identical to "nobody has
looked", and a benchmark may not be both revised and examined-and-left —
`target_revision_problems()` fails if one ever is.

### `ctc_extension` — §6.2 item 5, answered "no"

Two published figures score a child-credit extension and neither replaces $600B.

| Figure | What it is | Why not |
|---|---|---|
| CRS **R48286** Table 1, **$735.3B** | CBO's May 2024 estimate, *"Increase and Modification of Child and Dependent Credit"* | CRS states it *"include[s] the budgetary impact of the Credit for other dependents"*, which `credits.py` does not score — a **superset** |
| JCT **JCX-35-25**, **+$816.846B** | P.L. 119-21's child credit, same window | a **$2,200 indexed** credit against this benchmark's **$2,000 flat** one, and **already carried here** as `pl119_21_child_tax_credit` — adopting it would score one JCT row as two benchmarks |

Both sit *above* the module's design rather than bracketing it, so a range would
assert a containment neither publisher supports. Reported both ways for the
record: the fitted $600.0B is 0.00% / −18.4% / −26.5% against the three figures;
the held-out structural path's $714.2B is +19.0% / −2.9% / −12.6%. **The
structural path is twice as close to JCT's row as the fitted constant while
scoring worse against the carried target** — a finding that is only visible
because the two disagree, and an argument for the L3 rebuild rather than for
moving this target. What would move it is a published score of a $2,000 flat
extension without the other-dependents credit. None exists.

### `double_enforcement` — a 6% agreement that would measure nothing

Treasury's *American Families Plan Tax Compliance Agenda* (p. 18) prints
"$320 billion", 6% from the carried −$340B, so the *gap* argues for moving it.
The **dose** argues against. That $320B is the yield on an **$80B** increase in
the IRS budget scored in 2021 on a **pre-IRA** baseline; this preset scores
~$160B of additional funding stacked *on top of* the IRA's $80B — twice the
dose, on a baseline that already contains the dose Treasury scored. Treasury's
$700B headline is not a candidate either: $460B of it is bank information
reporting the module does not implement.

### `steel_tariff_25` — the negative result now has a cause

The 25% Section 232 rate on steel and aluminium was in force from
**12 March 2025 to 3 June 2025**, when it doubled to 50%. No scorekeeper
published a ten-year estimate for the ten-week regime, which is why Phase E
found nothing and why this pass found nothing either. The nearest published
figures score different policies: Tax Foundation's tracker carries only the 50%
rate with copper folded in ($341.4B conventional, 2026-2035); CRFB's two
steel/aluminium posts score *derivative-rule* changes (+$70B through FY2036,
revised to −$90B once the proclamation landed), so their proximity to −$60B is
coincidence; CRS **IN12519** carries no revenue estimate at all, confirmed by
extracting its full text. On the question this pass set out to answer — whether
derivative products are in or out — every published figure includes them and
none separates the two, so the distinction cannot be sourced either.

**Left in place and left unsourced, and explicitly not retired.** Retiring a
case to avoid reporting an unsourced target is the failure mode the ledger
exists to prevent.

### `eliminate_mortgage` — §6.2 item 4, half answered

No official repeal score exists. CBO has published no post-TCJA budget option
repealing the deduction; JCT publishes the *tax expenditure*, which is not a
repeal score because it omits the behavioural and itemisation response. The two
ten-year repeal figures that exist come from the **same simulator and differ by
2.4×** — CRS IF13190's $495B (which CRS itself labels *"not considered official
for revenue scoring purposes"*) against Yale's own June 2025 *"close to
$1.2 trillion"*. That disagreement is itself the argument against adopting
either, and −$300B stays.

**But the constant §6.2 item 4 asked about is now sourced**, and the source says
its name is wrong:

> `annual_cost_no_limit = 100.0` → **100.3**. Treasury OTA, *Tax Expenditures*
> (FY2019 edition, 16 October 2017 — law as of 1 July 2017, i.e. **before** the
> $750,000 acquisition-debt limit existed), Table 1 row 59, *"Deductibility of
> mortgage interest on owner-occupied homes"*: $1,003,230M over FY2018-2027 =
> **$100.32B/yr**. JCX-59-23 corroborates from the other direction: $100.6B in
> FY2027, the first full year after the TCJA provisions were then scheduled to
> expire.

Phase E's guess about the *shape* of the number was right — this is a
pre-TCJA-**law** level, not a debt-limit counterfactual — and that is exactly
why it **stays deliberately unwired**. What it is the "no limit" level *of* is
the pre-TCJA regime as a whole (the smaller standard deduction and the uncapped
SALT deduction, which together set how many filers itemise), not
IRC 163(h)(3)(F). The acquisition-debt limit alone is worth about **$4B/yr**:
JCX-35-25 scores *"Extension of limitation on deduction for qualified residence
interest"* at +$39,532M over FY2025-2034. So attaching a `limitation` block
keyed to the $750,000 cap and pointing `unlimited_cost_key` here would still be
wrong by an order of magnitude, and would still move `eliminate_mortgage` from
−5.1% to about +244%. Sourcing the constant changed the *reason* it stays
unread, not the decision.

One further modelling handoff this search produced, not acted on: the record's
`annual_cost = 25.0` is a **pre-P.L.119-21** level. JCT's JCX-45-25 puts the
capped expenditure at $45.5B in FY2025 rising to $54.9B in FY2029 (raising the
SALT cap to $40,000 took itemising claimants from 11.8M to 17.8M returns), while
Treasury's FY2027 edition gives $23.9B falling to $14.1B on the *same* statute —
a 2-4× disagreement driven by Treasury's comprehensive-income baseline against
JCT's normal-tax one. Choosing between them is an owner decision with a visible
consequence for this row.

## 5. What the tiers look like, both halves

**Read the two tiers together or neither.** Five rows moved from one to the
other, so every single-tier reading is a composition artefact.

| | Base `5deef17` | This branch |
|---|---|---|
| **Fitted calibrated** | **28 @ 2.04%**, 28/28 within 15%, worst `tcja_no_salt_cap` 13.9% | **23 @ 1.61%**, 23/23 within 15%, same worst row |
| **Fitted, rows held in place** | 28 @ 2.04%, 28/28 | **28 @ 3.00%**, **27/28** — the one over is `eliminate_salt` at 22.3% |
| **Unfitted reconstructions** | **26 @ 61.80%** (median 38.0), 5/26 within 15% | **31 @ 52.62%** (median 28.4), 9/31 within 15% |
| — *the same 26 rows, on the new targets* | 61.80% | **60.94%** |
| — sectoral presets (14) | 81.04% | **79.45%** |
| — P.L. 119-21 line items (8) | 35.82% | **35.82%**, unmoved |
| — capital-gains scenarios (3) | 39.61% | **39.61%**, unmoved |
| — TCJA AMT relief (1) | 66.80% | **66.80%**, unmoved |
| — *Wave 4 arrivals (5)* | — | **9.38%** |
| `revised_target_entries` | 3 | **15** |
| Scorecard rows / published | 80 / 73 | **unchanged** |
| Calibrated rows / published | 54 / 47 | **unchanged** |

**Both means fall and neither is an improvement.** The fitted mean falls from
2.04% to 1.61% because the five rows that left it were the five it was carrying;
the reconstruction mean falls from 61.8% to 52.6% because those same five
arrive averaging 9.4%. On a constant population the reconstruction tier moves
**61.80% → 60.94%**, which is the only honest single number for "what did the
new targets do to the model's measured error": **0.9pp**, against 8.3pp of
composition. Quote the two side by side or quote neither.

The five that left the fitted tier — `biden_eitc_childless`, `eliminate_salt`,
`extend_enhanced_ptc`, `ira_enforcement`, `repeal_salt_cap` — did so
mechanically. A constant fitted to a superseded figure is not fitted to its
replacement, so `target_was_revised()` turns `calibrated_to_target` off and the
row reports where a miss is a finding. Retuning any of them to close the new gap
would have been the relaxation; none was touched.

### Provenance

| | Base | This branch |
|---|---|---|
| Calibrated `line_item` | 19 | **30** |
| Calibrated `line_item_differs` | 13 | **5** |
| Calibrated `secondhand` | 15 | **12** |
| Calibrated `model_estimate` | 7 | **7** |
| Calibrated `unclassified` | 0 | **0** |
| Generic `line_item` / `differs` / `secondhand` | 20 / 1 / 5 | **21 / 0 / 5** |

The honest published-target count is **unchanged at 47 calibrated / 73 across
both tiers** — no row changed to or from `model_estimate`. What changed is how
many of those published targets the repository *agrees with*: thirteen fewer
rows now disagree with the document they cite.

**All five remaining `line_item_differs` rows are recorded decisions, and none
is an open question:**

| Row | Carried | Published | Verdict |
|---|---:|---:|---|
| `pillar_two_adoption` | −$80.0B | −$102.6B | Wave 3 **range revision**; in-range anchor |
| `reciprocal_tariffs` | −$1,500.0B | −$1,800.0B | Wave 4 **range revision**; in-range anchor (§2.2) |
| `biden_estate_reform` | −$450.0B | −$429.6B | Wave 3 **examined-and-left** |
| `ctc_extension` | +$600.0B | +$735.3B | Wave 4 **examined-and-left** (§4) |
| `double_enforcement` | −$340.0B | −$320.0B | Wave 4 **examined-and-left** (§4) |

§6.2 item 6 — "the 12 remaining `line_item_differs` rows … the rest carry no
per-target judgement" — is **closed**. Nine were revised, three were examined
and left, and the twelfth (`biden_high_income_tax`, the Generic-tier row) went
through the Tier-1 manifest.

## 6. Tier 1

Only one row moves, and only in the error column.

| | Base | This branch |
|---|---|---|
| cases | 26 | **26** |
| mean abs error | 31.0% | **30.9%** |
| median | 15.1% | **14.2%** |
| within 15% | 13/26 | **13/26** |
| within 25% | 19/26 | **19/26** |
| `biden_high_income_tax` | −$216.5B vs −$252.0B, **14.1%** | −$216.5B vs −$245.9B, **12.0%** |

`biden_high_income_tax.v1` is superseded by `.v2`. Phase E had transcribed the
Green Book row this record always cited — $245,924M, report p. 242 — and
deliberately left the manifest alone, because a frozen out-of-sample target may
only move through a new row and that is an owner decision. This is that
decision, taken under the manifest's own entry-before-scoring rule.

Two things worth stating so the improvement is not over-read. **Nothing in the
model reads the target**: the case is scored bottom-up from SOI filer counts
with ETI 0.25 on the ordinary-income base, and the prediction is the same
−$216.5B it was. And the record's old note claimed Treasury describes the
proposal as *"combined with other provisions"* — that is wrong about the table;
Treasury prints the top-rate increase as its own line. The FY2024 Green Book
prints $235,263M for the same row over FY2024-2033, which is the check that the
row is stable across vintages rather than a one-off.

The CI gate is untouched and passes: `cold_holdout.py --max-mean-error 40
--min-within-25pct 18`. By the workflow's own rule the derived values are
ceiling `ceil(30.9 × 1.25) = 39 → 40` and floor `19 − 1 = 18` — **both
unchanged**, so there is nothing for the coordinator to move.

## 7. Leave-one-out — the error column moves, the derivations do not

This is the check that a target move is a target move. `run_loo.py
--donor-matrix` output differs from base in **five lines**, and every derived
figure in them is identical:

| Row | Derived | Target | Err before → after |
|---|---:|---|---|
| `biden_eitc_childless` | 110.4 (unchanged) | 178.0 → 162.6 | −38.0% → **−32.1%** |
| `repeal_salt_cap` | 777.0 (unchanged) | 1,100.0 → 1,169.0 | −29.4% → **−33.5%** |
| `eliminate_salt` | −1,077.9 (unchanged) | −1,200.0 → −1,621.0 | +10.2% → **+33.5%** |

| Module / suite | Base | This branch |
|---|---|---|
| Credits | 20.5% (n=3) | **18.5%** (n=3) |
| Expenditures | 30.2% (n=5, 1 not x-val) | **35.7%** (n=5, 1 not x-val) |
| Aggregate | 28.4% mean / 16.5% median, 9/18 within 15% | **29.6% / 19.1%, 8/18** |
| Not cross-validatable | 4 | **4** |

No donor-matrix entry moved. `loo.py`'s leakage guard was not touched and does
not fire on any revised row: the revisions removed the last constant that was a
target restated (§3), they did not create one.

## 8. Gate outcomes

| Gate | Base `5deef17` | This branch |
|---|---|---|
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py scripts/` | 0 | **0** |
| `pytest tests/ -q` | 0 | **0** (3185 passed, 1 skipped) |
| `target_revision_problems()` | `[]` | **`[]`** |
| `cold_holdout.py --max-mean-error 40 --min-within-25pct 18` | 0 | **0** |
| `run_loo.py --donor-matrix` | 0 | **0** |
| `run_validation_dashboard.py` | 1 (pre-existing: Python 3.14 runtime + degraded microdata calibration) | **1**, identical output |
| `check_readiness.py --strict` | `ready_with_warnings`, 4 warnings | **identical** — same four, no new issue |

Four tests were updated, all of them pins rather than assertions about the
model: `test_capability_gate` (the Ask gate's Treasury anchor, now a named
constant), `test_validation_targets` (the double-registration check, which also
now asserts the *absence* of the superseded figure), `test_policy_catalog` /
`test_policy_status` / `test_validation_runners` (label spellings), and
`test_target_revisions`, which grew three pins: the whole ledger as a
`policy_id → (superseded, live)` table, both range revisions' bounds, and — new
in this lane — **that no stable preset id moved**, checked against a written-out
table rather than read back off the catalog it is meant to police.

## 9. Left undone, deliberately

- **`repeal_individual_amt`'s $450B stays.** §6.2 item 2, unchanged: no
  published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a
  baseline projection *and* `amt.py`'s own input, so adopting it would
  manufacture a 0% row out of leakage. Closing it needs a published score or an
  owner decision to re-register `holdout.py`'s locked protocol — a gate no lane
  may edit.
- **The twelve remaining calibrated `secondhand` rows are untouched.** They were
  not in this lane's brief and several have nothing to move *to*: both Social
  Security payroll targets (OCACT publishes percent-of-payroll, no dollars),
  `repeal_ira_credits`, `trump_china_60`, `cap_charitable`, `eliminate_step_up`,
  `biden_ctc_2021`, `repeal_ptc`, `cap_employer_health`, plus
  `repeal_individual_amt` and the two this lane examined and left
  (`steel_tariff_25`, `eliminate_mortgage`). Each needs the same per-target
  judgement.
- **The two SALT baselines still contradict each other** (§3). Stated in both
  records; reconciling them needs a baseline-vintage concept the expenditure
  module does not have, and `eliminate_salt`'s CBO baseline is in any case no
  longer current law after P.L. 119-21.
- **`annual_cost = 25.0` on the mortgage record is a pre-P.L.119-21 level**
  (§4), and JCT and Treasury disagree about its replacement by 2-4×. A modelling
  decision with a visible consequence for `eliminate_mortgage`.
- **`annual_cost_no_limit` stays unwired** (§4). Sourcing it changed the reason,
  not the decision.
- **Nothing was done about *why* rows miss.** `fdii_repeal` at 29.9%,
  `biden_gilti_reform` at 38.4%, `biden_full_international` at 44.1% and
  `trump_universal_10` at 42.0% are module findings, and §6.2 items 9, 10 and 11
  name the mechanisms that would close them. A provenance lane may not build
  them.

## 10. Handoff to the docs lane

`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`, `docs/METHODOLOGY.md`,
`planning/MODELING_IMPROVEMENT.md`, `planning/NEXT_STEPS.md` and
`docs/CHANGELOG.md` were **not touched** — other Wave 4 lanes are live on them.
The rows this branch invalidates:

| File | Says today | Should say |
|---|---|---|
| `CLAUDE.md` "Model maturity" + "Target Validation", Tier 2 headline | "fitted calibrated reference models (2.0% revenue over 28 benchmarks … 4.3% over 29 with the revised TCJA-AMT row held in place)" | **23 @ 2.0% → 1.6%**; held in place, **28 @ 3.0%, 27/28 within 15%** |
| `CLAUDE.md` Target Validation, reconstruction tier | "26 unfitted module reconstructions … 61.8% mean / 38.0% median, 5/26 within 15%" and its four sub-populations | **31 @ 52.6% / 28.4%, 9/31 within 15%**; sub-populations **14 sectoral @ 79.5%**, 8 P.L. 119-21 @ 35.8%, 3 capital-gains @ 39.6%, AMT @ 66.8%, **plus 5 Wave 4 arrivals @ 9.4%** — and the constant-population read, **60.9% on the 26 rows the tier already held** |
| `CLAUDE.md` Target Validation, revisions | "`ScorecardSummary.revised_target_entries` is **3**" | **15** |
| `CLAUDE.md` Target Validation, provenance line | "19 `line_item` / 13 `line_item_differs` / 15 `secondhand` / 7 `model_estimate` / 0 `unclassified`" | **30 / 5 / 12 / 7 / 0**; published counts unchanged at 47 and 73 |
| `CLAUDE.md` Target Validation, the disagreement sentence | "**13 calibrated targets are still known to disagree** with the document they cite (14 counting the Generic tier's Biden $400K row) … FDII repeal against a Treasury row that nets to $0, the SALT-deduction repeal against CBO Option 49's −$1,621.0B, and eleven more" | **5**, and none of them open: two are range revisions with in-range anchors and three are examined-and-left. FDII and the SALT deduction are both **now on their documents** |
| `CLAUDE.md` Target Validation, Tier 1 | "26 pre-registered cases, 31.0% mean, median 15.1%" | **30.9% mean, median 14.2%**; 13/26 and 19/26 unchanged; and the Biden $400K row is **−$216.5B vs −$245.9B (12.0%)**, no longer "−$217B vs −$252B (~14%)" |
| `CLAUDE.md` Target Validation, LOO | "28.4% mean / 16.5% median over 18 leave-one-out cases, 9/18 within 15%"; "`Credits` 45.1% → 20.5%"; "`Expenditures` 28.8% (n=4) → 30.2% (n=5)" | **29.6% / 19.1%, 8/18**; **Credits 18.5%**; **Expenditures 35.7%** — and all three moved because a *target* moved, not a derivation |
| `CLAUDE.md` Model maturity, "never describe it as CBO/JCT/Treasury" | the publisher list | now also **Penn Wharton** (`repeal_salt_cap`) and **CRFB** (`reciprocal_tariffs`'s range) as *cited* publishers |
| `docs/VALIDATION.md` `line_item_differs` table | 13 rows listed as open owner decisions | **5 rows**, each with a stated verdict; the other 8 moved to `line_item` and their old figures live in `target_revisions.py` |
| `docs/VALIDATION_NOTES.md` §6, LOO aggregate + expenditures bullet | 28.4% / 16.5%, 9/18; "Tax expenditures 5 of 6, mean 30.2%" | **29.6% / 19.1%, 8/18**; **5 of 6, mean 35.7%** |
| `planning/MODELING_IMPROVEMENT.md` §6.2 | items 3, 4, 5, 6 open | **3 closed** (PWBM Table 3, with the baseline contradiction restated as the live half); **4 half-closed** (constant sourced, still unwired; `annual_cost` is the new open half); **5 closed as examined-and-left**; **6 closed** |
| Anywhere quoting a preset's dollar figure | "-$700B", "-$280B", "-$200B", "-$2T", "-$1.2T", "$178B", "$350B", "$1.1T", "-$1.2T", "-$100B", "$200B" | the labels in `app_data.py` — the **ids** are unchanged, so no link or share URL needs editing |
