# Provenance lane — corporate and PTC targets

*Opened 2026-09-05 on `provenance/corporate-ptc-targets`, branched from `main` @
`35e20cc`. Work under `planning/memos/CORPORATE_PER_POINT_YIELD.md` §7(ii) —
the memo's three target-side recommendations plus the leave-one-out substitute
its §7(iii) named — and `planning/lanes/SWEEP_offset_sign.md` §7.6 items 3 and
4, the two rows PR #119 left "visibly carrying a target nobody can check".*

**No modelling change at all.** `fiscal_model/corporate.py` and
`fiscal_model/ptc.py` were not opened; no constant was retuned, no elasticity,
base or growth rate touched; every `model_10yr_billions` on the scorecard is
byte-identical to `35e20cc` and `run_loo.py --donor-matrix` is byte-identical
too. What moved is **one target, one provenance label, one estimator field,
three sets of `known_limitations`, and one benchmark that did not exist**.

Three commits, in the order the rules require:

| Commit | What |
|---|---|
| `32d275a` | **the ledger** — one Tier-2 supersession and one examined-and-left verdict, scored against by nothing |
| `fba8380` | **the scoring** — `scenarios.py`, `benchmark_sources.py`, `cbo_scores.py`, `core.py`, the app's preset copy, five test pins |
| *(this one)* | stamps both commits into `CORPORATE_PTC_PROVENANCE_*` and writes this file |

"The target moved before the model was scored against it" is therefore
checkable from `git log`, not asserted in prose.

## 1. `biden_corporate_28` — the figure is right and the reform is not

**Carried target unchanged at −$1,347.0B. Model unchanged at −$1,397.21B.
Error unchanged at −3.73%. What changed is that the row stops claiming the
document agrees with it.**

| | Before | After |
|---|---|---|
| provenance | `line_item` | **`line_item_differs`** |
| published figure recorded | −$1,349.9B | −$1,349.9B (**0.2% — the figures agree**) |
| `scope_differs` | — | **set** |

Treasury's *"Raise the corporate income tax rate to 28 percent"* row (FY2025
Green Book, report p. 239; PDF p. 247) prints $1,349,941M, and −$1,347B is that
figure rounded. The disagreement is not in the number. From the **FY2023**
edition onward the row's own chapter says the GILTI effective rate moves with
the statutory rate — *"The effective global intangible low-taxed income (GILTI)
rate would increase to 14 percent under the proposal"* (FY2024 and FY2025,
chapter report p. 2) — while `create_biden_corporate_rate_only`, the factory
scored against it, sets `gilti_rate_change=0.0` and its own docstring says "No
international changes - just rate". So the target prices a rate increase **and**
a GILTI step against a rate-only shape, and the 3.73% the fitted path reports is
measuring a scope mismatch as well as a fit.

**The two cannot be separated, and the memo established why** (§8): the GILTI
leg's size is never printed and is not recoverable by differencing editions.
FY2022 excludes it (the global minimum tax is a separate $533,503M row); FY2023
is on a Build Back Better baseline with a 20% GILTI rate; FY2024 and FY2025
route 21% → 14% *through* the corporate row while a separate $373,919M
international row takes 14% → 21%. There is nothing to move the target to, so
nothing moved.

### The label had to grow a second meaning, and it is now enforced

`line_item_differs` meant one thing: the transcribed **figure** disagrees. Here
the figure agrees and the **reform** does not, and
`test_line_item_differs_carries_the_published_figure` would have rejected the
row — 0.2% is inside `CONFIRMATION_TOLERANCE_PCT`. Calling it `line_item`
instead would have asserted an agreement the documents do not support.

So `BenchmarkSource` gained **`scope_differs`**, one sentence naming the
mechanism, and the invariant became: a `line_item_differs` row must carry a
figure gap wider than the tolerance **or** a filled `scope_differs` — never
neither, so the label can never mean "something is wrong here, unspecified".
`__post_init__` rejects `scope_differs` on any other provenance (a *confirmed*
line item that also declares a scope difference is confirming something the
module does not build), and the test now asserts both branches are live, so
neither can rot. `docs/VALIDATION.md`'s `line_item_differs` table gains a row
whose gap column is a sentence rather than a number — flagged for the docs sync
in §10.

## 2. The FY2022 Green Book row, and the estimator on Option 64

### 2.1 A second published corporate benchmark

The memo's §7(iii) answered "can the corporate module have a leave-one-out
row?" with **no** — the module has one fitted constant and, at the time, two
benchmarks, one of which was its own output, so re-deriving the base from it
would reconstruct the constant from itself. The memo named the honest
substitute: **register the FY2022 Green Book row**, the last rate-only one, as
a second published target the module is not fitted to.

| | |
|---|---|
| id | **`biden_corporate_28_fy2022`** |
| target | **−$857.8B** |
| document | Treasury, *General Explanations of the Administration's FY2022 Revenue Proposals*, "Raise the corporate income tax rate to 28 percent", **report p. 104; PDF p. 110**; chapter report p. 3 |
| window | **FY2022-2031** |
| provenance | `line_item` |
| `calibrated_to_target` | **`False`** |
| model | **−$1,397.21B** |
| error | **−62.88%**, Poor |

**Verified from Treasury's own PDF on this branch**, not taken on the memo's
word: $857,817M, five-year subtotal $405,537M, annual path 51,127 / 86,182 /
88,059 / 89,385 / 91,784 / 92,065 / 90,730 / 89,357 / 88,798 / 90,330 ($M) —
digit-for-digit what
`fiscal_model/data_files/validation/corporate_rate_scores.csv` carries.

**Why this row is worth having**, and it is not the error: it is the only
rate-only corporate row any Green Book prints — the word GILTI does not appear
in its two-sentence Proposal section — so it is the one published corporate
target whose scope matches the factory's shape, which is exactly what §1 says
`biden_corporate_28` is not. And its per-point yield is **36% below** the
FY2025 row's ($122.55B against $192.85B). A base anchored on a vintage could
reproduce that; a fixed base cannot, and does not: the module's answer to
"21% → 28%" is the same −$1,397.21B whichever decade is asked about.

**Window offset, stated rather than adjusted.** The target is FY2022-2031 on a
2021 baseline and this repository carries no 2021 vintage, so the row is scored
on the corporate runner's own FY2025-2034 window — the same mismatch
`iija_2021_discretionary` records in the Tier-1 manifest. In `reported` mode the
consequence is nil, because the rate channel is a flat annual: the offset
changes which years the same number is stamped on and nothing else. That is
recorded in the scenario's `limitations` so nobody reads the row as a claim the
model was run on Treasury's window.

**Not fitted, and never to be fitted.**
`BASELINE_TAXABLE_PROFITS_BILLIONS` is fitted to `biden_corporate_28`; a second
constant fitted here would make the pair uninformative. The row reports in the
unfitted-reconstruction tier, where a documented Poor is a warning rather than a
strict-readiness failure — which is why its `limitations` are three entries and
not none.

**It is deliberately NOT in `KNOWN_SCORES`, and that is a finding.**
`fiscal_model/assistant/benchmarks.py:candidate_anchors` turns *every* record in
`KNOWN_SCORES` with `policy_type="corporate_tax"` and a non-zero `rate_change`
into an interpolation anchor for the shipped Ask assistant. Adding a FY2022 row
at `rate_change=0.07` would have put a 2021-vintage figure into the anchor set a
2026 user's "what would +4pp raise?" interpolates across, and quietly lowered
the answer. A provenance lane may not move a shipped surface, so the benchmark
lives in `CORPORATE_VALIDATION_SCENARIOS` with its own `expected_10yr`, exactly
as `trump_corporate_15` does. The runner gained one line for it — scenarios may
now declare `official_source` — because "CBO/Treasury" was the hardcoded label
and two of the three corporate rows are no longer Treasury's.

### 2.2 Option 64's estimator, and its `known_limitations`

`cbo_opt64_corporate_rate_1pp` is a **JCT** estimate that CBO publishes. Every
corporate-rate option in every *Options for Reducing the Deficit* volume carries
"Data source: Staff of the Joint Committee on Taxation" verbatim.
`CBOScore.source` is documented as "Which organization produced the estimate",
so it was wrong: **`ScoreSource.CBO` → `ScoreSource.JCT`**, plus the note now
records that CBO's own Table 1-1 prints 136.0 where the option page and this
target carry 135.7 — CBO's rounding, not a second estimate.

Nothing in the scoring path reads `source`, and nothing moved: Tier 1 is
identical row for row (§6).

`preregistered.py` was **not** touched. Its `source_name` field is documented as
"the source that published it", and CBO did publish it, so the manifest row is
not wrong under its own definition — and the manifest is append-only for a
reason. The estimator distinction lives where the field means estimator.

The row's `known_limitations` were rewritten, because two of the three claims
were refuted by the memo:

| Was | Is |
|---|---|
| "CBO's option is $135.7B per percentage point … and Treasury's FY2025 Green Book row is $192.8B, a **42% gap in which the LARGER rate change carries the LARGER per-point yield**" | An **estimator** difference (JCT vs Treasury OTA) times a **scope** difference (Treasury's row is rate + GILTI). Per-point dollars are not comparable across rate levels or scopes; on the implied marginal base the record is Tax Foundation 55.1%, JCT 55.9%, PWBM 64.4%, Treasury 79.5% — **and this model reads 90.8%, above every published estimator**. Nothing in the record supports a yield rising with the step: JCT's 14-point cut from 35% and its 1-point increase from 21% imply marginal bases of $963.2B and $963.0B |
| the individual-side interaction is "the largest single unmodelled channel" | **Refuted, not unmeasured.** Option 64 carries no income-and-payroll-tax offset footnote though the facing Option 63 does, so JCT applies no such offset either. What is left named-and-not-built is credit **carryforwards** — which CBO's 2018 Option 24, the only volume with a narrative, states *is* inside JCT's estimate — and **CAMT**, which begins in TY2023, after the last SOI year on file |
| §174 and bonus depreciation inflate the TY2022 anchor | **Now sized.** SOI's income subject to tax averaged 71.8% of NIPA pre-tax corporate profits over TY2019-2021 and 79.8% in TY2022, so the TY2022 base is **11.1% above** what the prior ratio implies — an upper bound, since it charges the whole ratio move to the timing items. Deflating by it takes the row to about **46%**, not to CBO's figure |

A fourth entry was added on the §6655 first-year factor (the module's 0.757
against JCT's 0.591-0.732 and Treasury's 0.593/0.601).

## 3. `trump_corporate_15` — superseded, not retired

**+$1,920.0B was never a target.** The scenario's own note reads "No official
score; expected estimate derived from model", Phase E labelled it
`model_estimate` on that admission, and PR #119 showed how thin even that was:
the module's annual reproduced it only because
`estimate_behavioral_offset` returned `abs(static)`, adding 12.5% of a rate
*cut*'s static effect to the deficit instead of taking it off.

The brief said to build a `retired` state in `target_revisions.py` **if** no
published 15% score existed, and to prefer a supersession if one did. Two do,
both primary, both on this repository's own window:

| Publisher | Document | Row | Window | Conventional |
|---|---|---|---|---:|
| **PWBM** | *The 2024 Trump Campaign Policy Proposals* (26 Aug 2024), Table 1 | "Lower the corporate income tax rate to 15%" | FY2025-2034 | **−$595B** |
| **Tax Foundation** | Watson & York, *A Lower Corporate Tax Rate Can Be Part of Broader Tax Reform* (17 Jul 2024, upd. 23 Oct 2024), Table 2 | conventional revenue | 2025-2034 | **−$673.1B** |

CRFB's 6 September 2024 post prints both side by side. That is structurally the
`reciprocal_tariffs` case — several houses, one policy, one window, a spread —
so the row takes a **published range**:

| | Was | Is |
|---|---|---|
| target | +$1,920.0B (`model_estimate`) | **range [+$595.0B, +$673.1B]**, anchor **+$673.1B** |
| provenance | `model_estimate` | **`line_item_differs`** (published figure recorded: PWBM's +$595.0B) |
| model | +$1,491.76B | **+$1,491.76B**, unchanged |
| error | 22.30% | **+121.63%** |
| `within_published_range` | — | **False**, distance **$818.66B** |
| `calibrated_to_target` | False | **False**, unchanged |

Unlike the two earlier range rows, this model is nowhere near its range:
`pillar_two_adoption` sits inside its bounds and `reciprocal_tariffs` $3.2B
outside them, where this one is **$818.66B outside**. The range is not doing the
work here; the document is.

**The anchor rule is about the documents, not the model.** Tax Foundation's is a
standalone analysis of this one reform with its own revenue table; PWBM's is a
stacked row inside a whole-campaign package and therefore carries interaction
with the rest of the package. Anchoring on the bound nearer the model would have
been selection; a midpoint would have been the editorial invention ranges exist
to prevent.

**A third of the residual is scope, and it is measured rather than argued.**
`create_republican_corporate_cut` sets `extend_bonus_depreciation=True` and
neither published figure includes bonus depreciation — PWBM prints the business
provisions separately at −$623B. On this branch the module's
bonus-depreciation leg is **+$294.15B** of its +$1,491.76B in `reported` mode
(+$287.06B of +$1,698.57B in `derived`), so the **rate leg alone reads
+$1,197.6B, or +77.9%** against the anchor. It is not adjusted away: summing two
rows of PWBM's table would be constructing a target rather than reading one.

Most of the rest is the direction asymmetry the memo found. Tax Foundation's
*Options 2.0* is the only document pricing both directions in one edition and
one model — 21%→28% at $126.6B per point, 21%→15% at $163.2B per point — so a
point of cut costs 29% more than a point of increase yields, and `corporate.py`
prices both at the same per-point rate.

**The retire state was therefore not built.** A mechanism with no user is dead
code, and the row that would have used it has a document. `EXAMINED_NOT_REVISED`
already covers "opened and left"; what the ledger still lacks is a way to record
"this target should not exist and nothing replaces it", and nothing in the
repository needs that today. Recorded here so the next lane does not re-derive
the question.

### Three consequences worth naming

1. **`NON_PUBLISHED_BENCHMARK_IDS` shrank, 4 → 3.** It shrinks only by finding a
   document, never by deciding a model estimate is good enough; the comment in
   `provenance.py` now says so.
2. **The app was already quoting a published figure while the scorecard was
   not.** `CBO_SCORE_MAP["🏢 Trump Corporate 15%"]["official_score"]` has been
   **673.0** — credited to CRFB, which is where Tax Foundation's $673B is
   printed. It is inside the new range and did not move; only its attribution
   did ("CRFB" → "Tax Foundation / PWBM (via CRFB)"). Meanwhile
   `PRESET_POLICIES`' description told users "Estimated cost: ~$1.9T over 10
   years" — this model's own output, quoted back at them, contradicting the
   app's own score map. That copy now states the published range and says the
   preset also extends bonus depreciation.
3. **The preset's accuracy badge changes**, Poor (22.3%) → Poor (121.6%). The
   preset itself scores exactly what it scored before; the badge is now a
   distance from a document instead of from the model's own answer.

## 4. `repeal_ptc` — examined, and the search found the target's origin

**Not moved. −$1,100B stays, provenance stays `secondhand`, the row stays at
18.47%.** What this pass added is that the figure is no longer untraceable — and
the trace is the reason not to adopt it.

CBO and JCT's **June 2024 baseline projections** (*Health Insurance and Its
Federal Subsidies*, publication 51298, Table 2, read from CBO's own PDF through
a Wayback mirror; cbo.gov returns HTTP 403 to this environment) print, under
"Premium tax credits and related spending":

| Row | FY2025-2034 |
|---|---:|
| Outlays for premium tax credits | **$966B** |
| Revenue reductions from premium tax credits | **$176B** |
| **The credit itself, both legs** | **$1,142B** |
| *(subtotal incl. §1332 waivers, the Basic Health Program and risk adjustment)* | *$1,316B* |

**$1,142B is 3.8% from the −$1,100B the repository carries.** So the target is a
**baseline projection sitting in a repeal-score column** — the same class of
quantity `benchmark_sources.py` already refuses for this benchmark (JCX-48-24's
exchange-subsidy tax expenditure) and the same one `repeal_individual_amt`
refuses TPC's T25-0049 for. A projection of what a credit costs is not a score
of repealing it: it carries no coverage response and no interaction with
Medicaid, employer coverage or taxable wages, all of which every published
repeal estimate prices.

Three further things the pass established:

- **Adopting it would make the row worse**, 18.5% → 21.5%. This is not a lane
  declining an improvement.
- **No scored repeal exists to move to.** CBO/JCT publication **61734**
  (18 September 2025), the most recent menu of marketplace policies, scores
  permanently extending the expanded credit (~$350B) and repealing five sections
  of the 2025 reconciliation act ($271.9B together) and contains **no option
  eliminating the credit at all** — its full text was extracted to confirm that.
  The 2018/2020/2022/2025 CBO options volumes carry none either, and the 2017
  AHCA/BCRA estimates bundle subsidy repeal with Medicaid on a pre-enhancement
  statute and a 2017-2026 window.
- **A modelling handoff, not acted on.** `create_repeal_ptc` sets
  `coverage_elasticity=0.0` — "Not modeling coverage offset" — so what the
  module computes *is* a baseline cost. The mismatch is in the shape as much as
  in the target, and closing it is an owner decision about `ptc.py`, which a
  provenance lane may not open.

Left in place, left unsourced, and **explicitly not retired**: retiring a case
to avoid reporting an unsourced target is the failure mode the ledger exists to
prevent, and `repeal_ptc` is a locked `holdout.py` id besides.
`EXAMINED_NOT_REVISED` goes **5 → 6**.

## 5. What the tiers look like, both halves

**Read the two tiers together or neither.** One row joined the reconstruction
tier and one row's target left the model's own answer; nothing left the fitted
tier, and no model output moved.

| | Base `35e20cc` | This branch |
|---|---|---|
| **Fitted calibrated** | **21 @ 1.74%**, 21/21 within 15%, worst `tcja_no_salt_cap` 13.94% | **unchanged, all of it** |
| **Unfitted reconstructions** | **33 @ 54.38%** (median 28.40), 9/33 within 15% | **34 @ 57.55%** (median 34.18), 9/34 |
| — *the same 33 rows* | 54.38% / 28.40% | **57.39% / 29.94%** |
| — sectoral presets (15) | 82.63% | **82.63%**, unmoved |
| — P.L. 119-21 line items (8) | 35.82% | **35.82%**, unmoved |
| — capital-gains scenarios (3) | 39.61% | **39.61%**, unmoved |
| — TCJA AMT relief (1) | 66.80% | **66.80%**, unmoved |
| — *this lane's arrival (1)* | — | **62.88%** |
| `revised_target_entries` | 15 | **16** |
| Scorecard rows / published | 80 / 73 | **81 / 75** |
| Calibrated rows / published | 54 / 47 | **55 / 49** |

**The reconstruction mean rose and that is the honest direction.** On a constant
population it moves **54.38% → 57.39%**, 3.0pp, every bit of it
`trump_corporate_15` going 22.3% → 121.6% because it stopped being scored
against this model's own output. The extra 0.2pp to 57.55% is composition — the
new benchmark arriving at 62.88%. Quote the two side by side or quote neither.

Two counts moved in opposite directions and both are gains: **published targets
73 → 75** (the FY2022 row arrives published; `trump_corporate_15` becomes
published), and **model-estimate rows 7 → 6**. The repository now scores itself
against its own output in six places rather than seven.

### Provenance

| | Base | This branch |
|---|---|---|
| Calibrated `line_item` | 30 | **30** |
| Calibrated `line_item_differs` | 5 | **7** |
| Calibrated `secondhand` | 12 | **12** |
| Calibrated `model_estimate` | 7 | **6** |
| Calibrated `unclassified` | 0 | **0** |
| Generic `line_item` / `differs` / `secondhand` | 21 / 0 / 5 | **unchanged** |

`line_item` is flat because two moves cancelled: `biden_corporate_28` left it
for `line_item_differs` and `biden_corporate_28_fy2022` arrived in it.

**All seven `line_item_differs` rows are recorded decisions and none is an open
question:**

| Row | Carried | Published | Verdict |
|---|---:|---:|---|
| `pillar_two_adoption` | −$80.0B | −$102.6B | Wave 3 **range revision**; in-range anchor |
| `reciprocal_tariffs` | −$1,500.0B | −$1,800.0B | Wave 4 **range revision**; in-range anchor |
| `biden_estate_reform` | −$450.0B | −$429.6B | Wave 3 **examined-and-left** |
| `ctc_extension` | +$600.0B | +$735.3B | Wave 4 **examined-and-left** |
| `double_enforcement` | −$340.0B | −$320.0B | Wave 4 **examined-and-left** |
| **`trump_corporate_15`** | **+$673.1B** | **+$595.0B** | this lane's **range revision**; in-range anchor (§3) |
| **`biden_corporate_28`** | **−$1,347.0B** | **−$1,349.9B** | this lane's **scope** verdict — the figures agree, the reforms do not (§1) |

## 6. Tier 1 — nothing moved, which was the requirement

| | Base | This branch |
|---|---|---|
| cases | 26 | **26** |
| mean abs error | 15.9% | **15.9%** |
| median | 11.4% | **11.4%** |
| within 15% / 25% | 16 / 22 | **16 / 22** |
| every `(model, official)` pair | — | **identical, row for row** |

Checked by diffing `cold_holdout.py --json` against the base, not by reading the
summary line. The CI gate passes unchanged: `cold_holdout.py --max-mean-error 20
--min-within-25pct 21`, exit 0, and by the workflow's own rule the derived
values are still ceiling `ceil(15.9 × 1.25) = 20` and floor `22 − 1 = 21`, so
there is nothing for the coordinator to move.

`run_loo.py --donor-matrix` is **byte-identical** to base. Neither corporate row
is in the leave-one-out suite — that is the gap PR #114 named and §7 below
returns to.

## 7. Decision 1's corporate comparison reverses back, and should not be read yet

PR #119 left a live finding: signing the reported offset took the corporate
module's reported mean to **13.02%** against derived's unmoved **9.67%**, so by
Decision 1's own rule the module was due to flip to `derived`. The sweep
declined to flip it and said why — the row producing the reversal,
`trump_corporate_15`, carried provenance `model_estimate`, so neither ranking
was evidence about the world.

On published targets the ranking reverses again:

| Corporate benchmarks | `reported` | `derived` |
|---|---:|---:|
| PR #119, 2 rows (one of them the model's own output) | 13.02% | **9.67%** |
| **This branch, 3 published rows** | **62.75%** | 76.48% |
| — `biden_corporate_28` | −3.73% | −7.81% |
| — `biden_corporate_28_fy2022` | −62.88% | −69.29% |
| — `trump_corporate_15` | +121.63% | +152.35% |

**`CORPORATE_APP_MODE` is unchanged and this lane did not flip anything.** Two
readings of the table, and they should be held together. Decision 1's rule now
keeps the module on `reported`, as it did before PR #119 — but neither figure is
small, and the honest summary is that a module whose implied marginal base is
above every published estimator's misses both published corporate targets in the
same direction and misses the third by more. `derived` is worse on all three,
which is consistent with the memo's §6 finding that the derived base outgrows
its vintage.

**The comparison should not be re-decided from this branch alone.** A corporate
modelling lane (`planning/lanes/W6_corporate_base_projection.md`) is live on
`corporate.py` and is expected to move every one of these six cells; this PR
should merge first so that lane measures against published targets rather than
against +$1,920B.

`tests/test_corporate_derived.py::test_decision_1_now_ranks_derived_ahead_of_reported`
is renamed **`test_decision_1_ranks_the_two_modes_on_the_registered_targets`**
and now reads its targets off `CORPORATE_VALIDATION_SCENARIOS` instead of
carrying its own copy — which is how it came to be pinning a superseded figure
in the first place.

## 8. Gate outcomes

| Gate | Base `35e20cc` | This branch |
|---|---|---|
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py scripts/` | 0 | **0** |
| `pytest tests/ -q` | 0 (3506 passed, 7 skipped) | **0** (3509 passed, 7 skipped — the three extra are parametrized cases over the new benchmark row) |
| `target_revision_problems()` | `[]` | **`[]`** |
| `target_revision_problems(scorecard.entries)` | `[]` | **`[]`** |
| `cold_holdout.py --max-mean-error 20 --min-within-25pct 21` | 0 | **0** |
| `run_loo.py --donor-matrix` | 0 | **0**, byte-identical |
| `run_validation_dashboard.py` | 1 (pre-existing: Python 3.14 runtime + degraded microdata calibration) | **1**, byte-identical output |
| `check_readiness.py --strict` | `ready_with_warnings`, 4 warnings | **identical** — same four |
| `strict_readiness_issues` | `[('runtime', None)]` | **`[('runtime', None)]`** |

Five test pins were updated, all of them counts or figures rather than
assertions about the model:

| Test | Change |
|---|---|
| `test_line_item_differs_carries_the_published_figure` | now accepts a **scope** gap as well as a figure gap, and asserts both branches are live |
| `test_the_ledger_holds_exactly_the_revisions_these_passes_made` | 15 → 16 revisions, 30 → 32 ledger rows |
| `test_the_two_range_revisions_state_the_bounds…` | renamed to `…three_range_revisions…`; pins [595.0, 673.1] and that +$1,920B is outside it |
| `test_no_other_row_left_the_fitted_tier` | reconstructions 33 → 34; the fitted 21 is unchanged, which is the assertion that matters |
| `test_the_corporate_runner_prints_both_modes` / `test_decision_1_…` | 2 → 3 corporate rows and the means in §7 |

Two of those live in `tests/test_corporate_derived.py`, which the concurrent
corporate lane also owns. Both changes were forced by the target move and are
kept as small as the finding allows.

## 9. Left undone, deliberately

- **`repeal_ptc`'s target stays unsourced** (§4). What would move it is a CBO or
  JCT score of eliminating §36B; none exists.
- **`repeal_individual_amt`'s $450B stays**, unchanged from Wave 4 and not this
  lane's brief.
- **The ledger has no retire state** (§3). Nothing needs one today.
- **`preregistered.py` was not touched** (§2.2). Its `source_name` records the
  publisher, which is CBO, and the manifest is append-only.
- **`fiscal_model/corporate.py` was not opened**, so its Decision 1 docstring
  table (lines ~97-110) still says `trump_corporate_15` is `model_estimate` at
  −0.1% / −11.5%. That is now false in all three columns, and it is listed for
  the docs sync below rather than fixed here, because the concurrent corporate
  lane owns that file.
- **Nothing was done about *why* the corporate rows miss.** `biden_corporate_28`
  at 3.73% is a fitted row measuring a scope mismatch, `biden_corporate_28_fy2022`
  at 62.88% is a fixed base failing to track a vintage, and
  `trump_corporate_15` at 121.63% is that plus a bundled provision plus a
  direction asymmetry. The memo's §7(i) names the mechanism that would close the
  second; a provenance lane may not build it.

## 10. Handoff to the docs lane

`README.md`, `CLAUDE.md`, `docs/VALIDATION*.md`, `docs/METHODOLOGY.md`,
`planning/MODELING_IMPROVEMENT.md`, `planning/NEXT_STEPS.md` and
`docs/CHANGELOG.md` were **not touched**. The rows this branch invalidates:

| File | Says today | Should say |
|---|---|---|
| `CLAUDE.md` "Model maturity" + "Target Validation", reconstruction tier | "56.6% over 31 — but **65.7% on the 26 rows the tier already held**" | the tier is **34 @ 57.6% / 34.2% median, 9/34 within 15%** (it was already 33 @ 54.4% after PR #119, which the file has not caught up with); the constant-population read is **57.4% on the 33 rows the tier held**, up 3.0pp, all of it `trump_corporate_15` |
| `CLAUDE.md` Target Validation, sub-populations | "15 sectoral … 8 P.L. 119-21 … 3 capital-gains … TCJA AMT … 5 Wave 4 arrivals" | unchanged figures, **plus this lane's one arrival at 62.9%** |
| `CLAUDE.md` Target Validation, revisions | "`revised_target_entries` is **15**" | **16** |
| `CLAUDE.md` Target Validation, provenance line | "30 `line_item` / 5 `line_item_differs` / 12 `secondhand` / 7 `model_estimate` / 0 `unclassified`"; "51 / 5 / 17 / 7 / 0 across both tiers"; published 47 and 73 | **30 / 7 / 12 / 6 / 0**; **51 / 7 / 17 / 6 / 0** across both tiers; published **49** and **75**, out of **81** rows |
| `CLAUDE.md` Target Validation, the `line_item_differs` sentence | "**none of the 5 is an open question** — two are range revisions … three are examined-and-left" | **7**, still none open: **three** range revisions, three examined-and-left, and one **scope** verdict (`biden_corporate_28`, the first row where the figures agree and the reforms do not) |
| `CLAUDE.md` Target Validation, the twelve untraceable `secondhand` rows | lists `repeal_ptc` among them | still twelve, but `repeal_ptc` is now **examined-and-left with its origin identified** — CBO/JCT pub. 51298 Table 2, $1,142B, 3.8% away, and a baseline projection rather than a repeal score |
| `CLAUDE.md` Target Validation, `EXAMINED_NOT_REVISED` | "It now has **five** entries" | **six** — `repeal_ptc` joins `biden_estate_reform`, `ctc_extension`, `double_enforcement`, `steel_tariff_25` and `eliminate_mortgage` |
| `CLAUDE.md`, Wave 5 §, corporate | "`CORPORATE_APP_MODE` stays `reported` under Decision 1 (1.92% against derived's 9.67%)" | on three **published** targets it is **62.75% against 76.48%** — reported still leads, and neither number is small |
| `docs/VALIDATION.md` line ~298 | the five reconstruction populations | six; add this lane's arrival |
| `docs/VALIDATION.md` line ~307 | `line_item_differs` 5 | **7**, and the table's "gap" column needs a row whose gap is a **scope** sentence, not a number |
| `docs/VALIDATION.md` line ~309 | `model_estimate` 7 | **6** |
| `docs/VALIDATION.md` §332 `line_item_differs` table | five verdicts | **seven** — add `trump_corporate_15` (range) and `biden_corporate_28` (scope) |
| `docs/VALIDATION.md` line ~491 | "Trump corporate 15% \| $1,920B \| $1,918B \| -0.1% \| 'No official score…'" | **[$595B, $673.1B] \| $1,491.8B \| +121.6%**, and the note is now the published range plus the bonus-depreciation scope gap |
| `docs/VALIDATION.md` line ~867 | "Trump 21% to 15% \| $1,920B \| $1,920B \| 0.0% \| Model" | same correction |
| `docs/VALIDATION.md` corporate rows | `biden_corporate_28` as a clean `line_item` | `line_item_differs` with the GILTI scope note; and a new row for `biden_corporate_28_fy2022` |
| `fiscal_model/corporate.py` lines ~97-110 | the Decision 1 docstring table: `trump_corporate_15` +$1,920.0B, −0.1% / −11.5%, provenance `model_estimate` | all three false; **owned by the concurrent corporate lane**, to be corrected there |
| `planning/lanes/SWEEP_offset_sign.md` §7.6 items 3 and 4 | "two rows are now visibly carrying a target nobody can check"; "`biden_corporate_28`'s target is a bundled rate-plus-GILTI row … Noted, not changed" | **both closed**: item 3 by §3 and §4 here, item 4 by §1 |
| `planning/memos/CORPORATE_PER_POINT_YIELD.md` §7(ii) and §7(iii) | three target-side records to correct; "the corporate module cannot be given an honest leave-one-out row today" | §7(ii) **done**, all three; §7(iii)'s named substitute **done** — the module now has two published targets and one of them is not fitted |
