# Lane — owner decisions ③ and ④ of the ledger

*Pre-registered 2026-09-11 against `main` @ `994f528`, branch
`provenance/ledger-decisions-3-4`. Two owner decisions, two mechanisms that
already exist, **no module opened and no model output moved**. Everything below
§3 was computed before the implementing commits were written.*

Scope: `planning/HIGH_STAKES_ACCURACY.md` §4 decisions ③ and ④. Owned files:
`fiscal_model/validation/{preregistered,target_revisions,cbo_scores,core}.py`,
`scripts/cold_holdout.py` (reporting only),
`fiscal_model/data_files/validation/headline_counts.json` (regenerated),
`docs/VALIDATION.md`, tests, and the one per-class CI ceiling §3.4 explains.

---

## 1. The two mechanisms

### 1.1 ③ — the IIJA window row

`iija_2021_discretionary.v2` scores CBO's own authorization schedule
(`annual_authority_path_billions`, $446.3B of budget authority) spent out on the
`construction_and_capital` profile. Total outlays across every year the policy
touches are **$433.2B against CBO's $415.4B — 4.3% high**. The row nevertheless
reads **18.2%**, because **$92.6B of those outlays fall in FY2022–2024**, before
the model's FY2025–2034 window opens, so $340.0B is compared against a published
figure covering FY2021–2031. That is an accounting artefact, not a shape or a
spend-out miss, and the row's own `known_limitations` have said so since PR #126.

The mechanism is the one PR #126 built for
`treasury_capgains_39_plus_stepup_elim.v2`: `CBOScore.scoring_window_first_year`,
read by `validation/core.py::_resolve_window_start`, which opens the scorer's
window in the first fiscal year the target's own document covers. It is governed
by one rule, `preregistered.FY2022_TARGET_WINDOW_RULE`, fixed before the model
could read it: *the window is the first year of the window the source's own
published total covers, as already transcribed into the record's
`budget_window`*. IIJA's `budget_window` has read `"FY2022-2031"` and its
`baseline_year` `2021` since the row was entered on 2026-09-01 — four waves
before anything made it matter.

**The target does not move.** It stays at **+$415.448B**, CBO's own estimated
outlays for S.Amdt. 2137 to H.R. 3684 (revised 9 August 2021), Table 1. Only the
shape input moves, which is `iija_2021_discretionary.v2`'s own rule quoted back
at it — *"**The target does not change.** This row replaces v1's shape input"* —
and is why this is a `.v3` under the manifest's supersede rule rather than an
edit: ledger row in one commit, first scoring in the next, `.v2` kept unedited
with `superseded_by`, its +$340.0B / 18.2% left on the record beside `.v1`'s
+$1,894B / 356%.

**What this is not.** It is not a vintage. A discretionary `SpendingPolicy`
scores its own source-stated authority and reads no baseline *level*, which is
why `FY2022_TARGET_WINDOW.md` §4(d) rejected adding a 2021 baseline: it would
cost a `BaselineVintage` member, an assumptions block, `VINTAGE_SOURCING`, the
app's vintage picker and the classroom frozen-link refusal path, and would move
neither FY2022 row. It is also not a claim to a 2021 information set: the model
still prices FY2022–2024 with today's outlay profile. What the change fixes is
that the ten fiscal years priced are the ten the target covers.

`effective_start_year` is already 2022 on this record, so the *policy's* start
year does not move at all — only the scorer's window does. That makes IIJA the
cleaner of the two windowed rows and leaves
`test_effective_start_year_still_beats_a_window` true as written.

### 1.2 ④ — the two pharma model-estimate targets

`expand_drug_negotiation` (−$500B) and `international_reference_pricing`
(−$100B) are `MODEL_ESTIMATE` rows: neither figure is a published score of
anything. H9 (PR #153) searched both in full and wrote the verdicts that
`EXAMINED_NOT_REVISED` now carries, recommending retirement and declining to
apply it because owner decision ④ was open.

- **−$500B** is the repository's extrapolation from $237B, a figure
  `W4_pharma_part_d.md` finding 2 established was never a negotiation score but
  CBO's total for the whole drug-pricing title. CBO's December 2024 *Options*
  volume contains no drug-negotiation option at all; the phrase "at least 50
  drugs" appears nowhere in the FY2025 Budget. The nearest published quantities
  score other things: CBO's −$98,521M for the **existing** program (PL117-169
  Table 1 p. 5, sec. 11001) and the FY2025 Budget's −$200,000M **bundle**
  (Table S-6, report p. 143).
- **−$100B** is a derivation from a RAND price index, which is a price statistic
  and not a budget score. CBO *did* score international reference pricing —
  H.R. 3 Title I at −$455,927M over FY2020–2029 (publication 55936) — but on a
  **selected cohort** and a **pre-IRA** baseline in which Medicare had no
  negotiation authority, so adopting it would double-count the −$98.5B the IRA
  since enacted. −$100B is a fifth of CBO's figure for a *narrower* policy and
  an eighth of the module's own answer.

The state is the one H9 built and applied to nothing: `CalibratedTarget.retired`
/ `retired_reason`, with `is_live` excluding a withdrawn row. The edit is §8.7's,
verbatim: two ledger rows appended to `CALIBRATED_TARGETS`, the two keys deleted
from `EXAMINED_NOT_REVISED` (a benchmark may not be both, and
`target_revision_problems` enforces it), and
`test_target_retirement.py::test_nothing_is_retired_yet` updated — which is the
point of that test.

**The trap this must not fall into is arithmetic, not design.** Withdrawing
93.3% and 701.0% from a 39-row tier averaging 56.5% leaves 37 rows at 38.1% —
**18.4 points of "improvement" bought by withdrawing two rows**, which is
`HIGH_STAKES_ACCURACY.md` §5's *"no removing a case to go green"*. So nothing is
deleted: both rows keep their scorecard entries, their model figures and their
withdrawn targets; `calibrated_to_target` is forced `False` exactly as a revision
does; `retired_target_entries` counts them; and
`uncalibrated_reconstruction_retired_held_in_place` prints the tier with both
rows folded back at the error they carried on the day they were withdrawn, on
the line beneath. Quoting 38.1% without 56.5% requires skipping a line.

---

## 2. Files

| File | Change |
|---|---|
| `fiscal_model/validation/preregistered.py` | `IIJA_WINDOW_ENTERED_COMMIT` / `_DATE` / `_FIRST_SCORED_COMMIT`; `.v2` gains `superseded_by`; `.v3` row entered (target unchanged) |
| `fiscal_model/validation/cbo_scores.py` | `scoring_window_first_year=2022` on the IIJA record (scoring commit) |
| `fiscal_model/validation/core.py` | the IIJA row's `known_limitations` rewritten: the window miss is closed, not reported |
| `fiscal_model/validation/target_revisions.py` | two retired `CalibratedTarget` rows; the two keys removed from `EXAMINED_NOT_REVISED` |
| `fiscal_model/data_files/validation/headline_counts.json` | regenerated (expected byte-identical — see §3.3) |
| `.github/workflows/validation-dashboard.yml` | **one** per-class ceiling tightened; see §3.4 |
| `docs/VALIDATION.md` | the IIJA paragraph; a new retirement paragraph |
| `tests/` | the consequential updates §3.5 lists |

No module is opened. `scenarios.py` and `readiness.py` are in the lane's
ownership and are expected to need **no change**; if either does, it is a
finding and is reported rather than absorbed.

---

## 3. Expected outturn

### 3.1 Tier 1 (out-of-sample)

| | before | after |
|---|--:|--:|
| `iija_2021_discretionary` | +$340.0B, **18.2%** | **+$414.3B, 0.3%** |
| mean / median | 14.5% / 11.5% | **13.8% / 10.6%** |
| within 15% / 25% | 16 / 22 | **17** / **22** |
| error mass | 376.0 | **358.1** |
| every other Tier 1 row | — | **unchanged to six decimals** |

**The brief's "within-25 22 → 23" is wrong and this lane corrects it**: IIJA was
already inside 25% at 18.2%, so the count it moves is **within-15**, 16 → 17.
Within-25 is unchanged at 22, which means the pooled floor of 22 is met with no
slack — the same state Wave C left it in, not a new one.

Per class (the eight of `HIGH_STAKES_ACCURACY.md` §2), only one moves:

| class | n | before | after |
|---|--:|--:|--:|
| enacted-law spending | 3 | 13.4% | **7.4%** (12.2 / 0.3 / 9.8) |
| the other seven | 23 | — | **unchanged** |

### 3.2 The calibrated tiers

| | before | after |
|---|---|---|
| fitted | 16 @ 1.5% | **unchanged** |
| fitted, held in place (ledger's own mechanism) | 27 @ 11.9% | **unchanged** |
| reconstructions | 39 @ 56.5%, median 36.9, 10/39 w15, 14/39 w25 | **37 @ 38.1%**, median 29.9, 10/37, 14/37 |
| retired | 0 | **2 @ 397.2%** — 93.3% and 701.0% |
| reconstructions, retired held in place | 39 @ 56.5% | **39 @ 56.5%** (unchanged, by construction) |

The held-in-place line is the falsification test for the retirement: it must be
**identical** to the pre-change reconstruction tier. If it moves, something other
than a withdrawal happened.

### 3.3 Provenance and presets

- `model_estimate` provenance: **4 → 4, unchanged**, and `published_entries`
  **77/81, unchanged**. The brief predicted `model_estimate` 4 → 2; that is not
  what H9 built and not what the design says. A retired row keeps its withdrawn
  figure in `official_10yr_billions` so the entry still prints, and `provenance`
  describes where that figure came from — "the repository's own extrapolation",
  which *is* `model_estimate`. §4.2 of `HSB_h9_provenance.md` says so in as many
  words: *"A retired row is excluded from `published_entries` (it already is:
  both are `model_estimate`)."* Predicted here as **no change**; if either count
  moves, the lane has done something it did not intend.
- `headline_counts.json`: regenerated and expected **byte-identical**
  (`published_entries` 77, `model_estimate_entries` 4, `total_entries` 81,
  `out_of_sample_entries` 26).
- **Presets: all 53 byte-identical, static and dynamic.** The two pharma presets'
  *scores* do not move — only their targets are withdrawn. Their badges keep
  reading `Unfitted reconstruction, 93.3% / 701.0% from −$500B / −$100B`, and
  both already carry `_provenance_clause`'s sentence *"The target itself is this
  model's own estimate, not a published score."* A badge that said "withdrawn"
  would be better; `ui/preset_validation.py` is not this lane's file and
  `_scorecard_index` does not carry `target_retired`, so it is recorded as a
  carry-over rather than taken by implication.

### 3.4 What the gate rule re-derives to

By the workflow's own rule, on the post-change battery:

| gate | live | rule | verdict |
|---|--:|--:|---|
| pooled ceiling | 13.8% | `ceil(13.8 × 1.25) = 18 →` nearest 5 `= 20` | **20, unchanged** |
| pooled floor | 22 within 25% | `22 − 1 = 21` | would **loosen**; left at **22** (downward only) |
| enacted-law spending | 7.4% | `ceil(7.4 × 1.25) = 10` | **17 → 10**, a tightening |
| the other seven classes | — | — | re-derive to themselves |

**One threshold is moved in this PR and it is not a choice.** Two meta-tests in
`tests/test_ci_workflow.py` are one-sided invariants, not advisories:
`test_no_gate_is_looser_than_the_workflow_rule_derives` asserts
`ceilings[slug] <= ceil(mean × 1.25)` and
`test_the_per_class_floor_gates_every_class_the_battery_contains` asserts
`ceilings[slug] <= max(mean × 2, 2.0)`. At a class mean of 7.4% a ceiling of 17
fails both. Tightening needs no reason under the rule; the pooled pair is left
untouched for the docs-sync lane, which has nothing to move.

### 3.5 Tests expected to move

- `test_preregistration.py::test_only_the_fy2022_row_names_its_own_window` — the
  set becomes two. It is renamed rather than relaxed: what it guards is that the
  field is not a general lever, so it asserts the set equals exactly the two rows
  the manifest superseded to get one, and that each names the first year of its
  own `budget_window`.
- `test_target_retirement.py::test_nothing_is_retired_yet` — inverted to pin the
  two retirements and their reasons. This is the test's purpose.
- Anything pinning IIJA's 18.2%, the enacted-law class mean, or the
  `EXAMINED_NOT_REVISED` membership.

No threshold in a test is relaxed. Every update is an assertion that was pinning
a number this lane deliberately moved.

---

## 4. Falsification

The lane is wrong, and should not merge, if any of these is true:

1. **Any model output moves.** All 81 `model_10yr_billions` must be identical to
   six decimals except `iija_2021_discretionary` (+$340.0B → +$414.3B, which is
   a *window* change, not a model one — the policy and its outlay path are
   untouched). All 53 presets identical, static and dynamic.
2. **Any row is deleted.** 81 scorecard rows before, 81 after. Both retired rows
   must still print, with their model figures and their withdrawn targets.
3. **The held-in-place reconstruction reading moves.** 39 @ 56.5% before and
   after, or the withdrawal removed something it should not have.
4. **A second Tier 1 row moves**, or IIJA lands outside 0.2–0.5%.
5. **Either calibrated tier's fitted block moves** (16 @ 1.5%; 27 @ 11.9% held in
   place), or `run_loo.py --donor-matrix` differs.
6. **A retired row trips readiness.** If it does, the fix is the *reporting* —
   `readiness.py` already lists `retired_target_policy_ids` and exempts a row
   with no target from the strict rating gate — and never the row.
7. **`published_entries` or `model_estimate_entries` moves.**

---

## 5. Outturn

*Measured on the branch at `6f1c769` plus the stamping commit. Every figure in §3
landed; the two the brief predicted differently are reported below with the
arithmetic that decides them.*

### 5.1 Per-row

| row | before | after | |
|---|--:|--:|---|
| `iija_2021_discretionary` | +$339.978895B, **18.17%** | **+$414.286825B, 0.28%** | Acceptable → Excellent |
| `expand_drug_negotiation` | −$33.497352B vs −$500.0B, 93.30% | **same figures, target retired** | leaves the reconstruction mean; counted and reported |
| `international_reference_pricing` | −$801.047289B vs −$100.0B, 701.05% | **same figures, target retired** | as above |
| the other 78 scorecard rows | — | **identical to six decimals** | |

### 5.2 Tiers

| | before | after |
|---|---|---|
| Tier 1 | 26 @ **14.5%**, median 11.5, 16/26 w15, 22/26 w25, mass 376.1 | 26 @ **13.8%**, median **10.6**, **17**/26 w15, 22/26 w25, mass **358.2** |
| fitted | 16 @ 1.5%, median 0.1, 16/16 | **unchanged** |
| fitted, held in place | 27 @ 11.9%, median 1.1, 22/27 | **unchanged** |
| reconstructions | 39 @ 56.5%, median 36.9, 10/39, 14/39 | **37 @ 38.1%**, median **29.9**, 10/37, 14/37 |
| retired | — | **2 @ 397.2%** (93.3%, 701.0%) |
| reconstructions, retired held in place | 39 @ 56.5% | **39 @ 56.5%** — unchanged, which is the falsification test for the withdrawal |
| leave-one-out (`--donor-matrix`) | 18 @ 35.7% | **byte-identical, zero lines differ** |

Per class, one of eight moves: **enacted-law spending 13.4% → 7.4%** (12.2 / 0.3
/ 9.8), mass 40.2 → 22.3. The other seven are identical to the decimal.

**The calibrated rows above are this branch's before/after and are not the merged
reading.** PR #157 (H7, expenditure offset magnitudes) landed while this lane was
open and moved the same tier's *composition* from the other side, reclassifying
`cap_charitable` out of the fitted tier. Merged, the tiers read **fitted 15 @
1.6%** (median 0.0, 15/15 within 15%), **reconstructions 38 @ 37.5%** (median
30.1, 11/38), **retired 2 @ 397.2%**, **retired held in place 40 @ 55.5%** (median
33.6, 11/40). **Tier 1 is identical on both trees** — 26 @ 13.8%, median 10.6,
17/26 and 22/26, and all eight class means to the decimal — so nothing this lane
claims about the out-of-sample tier depends on which tree it is read on. Quote the
merged figures; neither branch's is the live one.

### 5.3 The two things the brief predicted and the measurement contradicts

**1. Within-25 does not move.** The brief expected 22 → 23. IIJA was already
*inside* 25% at 18.2%, so improving it to 0.3% moves the **within-15** count,
16 → **17**, and leaves within-25 at 22. The consequence for the gate is the
opposite of the brief's: the pooled floor of 22 is met **with no slack**, exactly
as Wave C left it, rather than gaining a case of headroom.

**2. `model_estimate` provenance does not move.** The brief expected 4 → 2. It
stays at **4**, and `published_entries` stays at **77/81**, because a retired row
keeps its withdrawn figure in `official_10yr_billions` and `provenance` describes
where *that figure* came from — "the repository's own extrapolation", which is
`model_estimate`. This is what `HSB_h9_provenance.md` §4.2 built and says in as
many words. The two predictions were also mutually inconsistent: with
`published_entries = total − model_estimate − unclassified`, moving the second to
2 would have moved the first to 79.

What the retirement *does* move in the provenance reporting is the tier split:
`uncalibrated_reconstruction.model_estimate_targets` goes **2 → 0** and
`retired_targets.model_estimate_targets` **0 → 2**, so the reconstruction tier
now contains no target that is this model's own output. That is the honest
version of the brief's "4 → 2".

### 5.4 The gate values the docs-sync lane should apply

| gate | live | rule | verdict |
|---|--:|--:|---|
| `--max-mean-error` | 13.8% | `ceil(13.8 × 1.25) = 18 →` nearest 5 `= 20` | **20, unchanged** |
| `--min-within-25pct` | 22 | `22 − 1 = 21` | would **loosen**; **stays at 22** |
| `enacted_law_spending` | 7.4% | `ceil(7.4 × 1.25) = 10` | **17 → 10** — *applied in this PR* |
| the other seven classes | — | — | re-derive to themselves |

**One threshold moved here and it was not a choice.** Two meta-tests in
`tests/test_ci_workflow.py` are one-sided invariants —
`test_no_gate_is_looser_than_the_workflow_rule_derives` (`ceiling <= ceil(mean ×
1.25)`) and `test_the_per_class_floor_gates_every_class_the_battery_contains`
(`ceiling <= max(mean × 2, 2.0)`) — and a ceiling of 17 fails both at a class
mean of 7.4%. Tightening needs no reason under the plan's own rule. The pooled
pair is untouched and has nothing for the sync lane to move.

### 5.5 Gates

| Gate | Result |
|---|---|
| Every `model_10yr_billions` byte-identical except IIJA | **80/81 identical**; IIJA +$340.0B → +$414.3B, which is a *window* change |
| All 53 presets, static and dynamic | **byte-identical** (`cmp` clean) |
| `run_loo.py --donor-matrix` | **byte-identical**, zero lines differ |
| `target_revision_problems(entries)` / `manifest_problems` | **clean** |
| `ANTHROPIC_API_KEY= pytest tests/ -q` | **passes**, after the five consequential updates §5.6 lists |
| `ruff check` over CI's scope | **All checks passed** |
| `check_readiness.py --strict` | **byte-identical to the pre-change run** — same exit 2, same five warnings, and the two retired rows trip nothing |
| `build_validation_headline.py --check` | **OK** without regenerating: 77 published of 81, unchanged |
| pooled gate, per-class gate, LOO gate as the workflow runs them | **exit 0, 0, 0** |

### 5.6 The five tests this moved, and what each was pinning

None is a threshold relaxed.

1. `test_only_the_fy2022_row_names_its_own_window` → **renamed** to
   `test_only_rows_the_manifest_superseded_name_their_own_window`, and
   **strengthened**: it now also asserts that each windowed record's
   `scoring_window_first_year` equals the first year of its own `budget_window`,
   which is `FY2022_TARGET_WINDOW_RULE` written as a test rather than a
   membership list that has to be edited for every arrival.
2. `test_the_fy2022_window_rule_is_recorded_not_left_per_case` → now requires
   **every live row carrying a window** to quote the rule, so the rule cannot be
   a preamble one row honours and the next does not.
3. `test_iija_shape_change_is_a_new_row_with_the_same_target` → `.v2` is itself
   superseded now, so `not v1.is_live and v2.is_live` became `not v1.is_live and
   not v2.is_live`. What the test pins is the supersession *chain* and the
   target's immobility across it, not which row is in force.
4. `test_nothing_is_retired_yet` → **inverted**, which is its purpose. It is now
   `test_exactly_the_two_targets_the_owner_withdrew_are_retired` and pins the set
   in both directions, plus that each row states a reason, keeps its withdrawn
   figure and keeps a scorecard entry. A companion asserts the retired set is
   disjoint from `EXAMINED_NOT_REVISED`.
5. `test_the_ledger_holds_exactly_the_revisions_these_passes_made` →
   `len(CALIBRATED_TARGETS)` was `2 × len(_LEDGER)`, which assumed every ledger
   row is half of a supersession. A **retirement has no pair**, so the identity
   is now `2 × len(_LEDGER) + len(RETIRED_POLICY_IDS)`. That is a real (if small)
   finding about the ledger's shape, not a count bumped.

New: `test_iija_window_change_is_a_third_row_with_the_same_target`.

### 5.7 Findings

1. **The brief's two predicted movements were both wrong, and each is wrong for a
   reason worth keeping.** Within-25 does not move because *improving a row that
   was already inside the band moves no band count except the tighter one* — a
   general property of count-based gates that makes the pooled floor insensitive
   to exactly the improvements it is supposed to reward. And provenance does not
   move because a **withdrawn target still has a provenance**: retiring a target
   says nothing about where the withdrawn figure came from.

2. **IIJA's 0.3% is two terms nearly cancelling, and the row's own note now says
   so.** The path outlays $433.2B in total against CBO's $415.4B — 4.3% high,
   which is just the `construction_and_capital` profile's 0.973 spend-out sum
   applied to the full authority — while $18.9B falls in FY2032 or later, outside
   even this window. 0.3% is smaller than either term. Reading it as evidence
   about the spend-out profile would repeat the error
   `treasury_capgains_39_plus_stepup_elim`'s 0.2% and FRA's old 6% both made.

3. **CBO's table is headed FY2021–2031, eleven fiscal years, and a ten-year
   window cannot cover eleven.** This is not a gap and not a judgement call: IIJA
   was signed 15 November 2021, inside FY2022, and the record's own
   `budget_window` has read `"FY2022-2031"` since entry — which is the field
   `FY2022_TARGET_WINDOW_RULE` reads, so the rule decides it rather than the lane.

4. **`effective_start_year` already equalled the window, which makes IIJA the
   clean case for the mechanism.** For the Treasury row, PR #126's field had to
   move the scorer's window *and* the policy's start together. Here the policy
   does not move at all — its outlay path is identical year by year — so the
   experiment isolates the window exactly, and
   `test_effective_start_year_still_beats_a_window` stays true as written.

5. **The retirement removes the reconstruction tier's only `model_estimate`
   targets.** `Pharma` as a reconstruction sub-population goes **3 @ 277.8% →
   1 @ 39.0%** (`universal_insulin_cap` alone), and the tier's
   `model_estimate_targets` count goes 2 → 0. So the sentence *"no row this tier
   reports is scored against this model's own output"* is now true of the
   reconstruction tier and was not before.

6. **`docs/VALIDATION.md` was carrying a stale within-25 count for the
   reconstruction tier** — 13/39 where the live figure is 14/39. Corrected in
   passing; it appears to date from before Wave C's tariff lane moved the tier.

### 5.8 Carry-overs

1. **The preset badge for a retired row still reads "Unfitted reconstruction,
   93.3% from −$500B".** `ui/preset_validation.py` is not this lane's file and
   `_scorecard_index` does not carry `target_retired`, so a badge cannot say
   "withdrawn" today. It is not a false claim — `_provenance_clause` already
   appends *"The target itself is this model's own estimate, not a published
   score"* to both — but "withdrawn" is the more accurate word and the field it
   needs is one line.
2. **Two further retirement candidates are named and not acted on**,
   `carbon_tax_50` and `eliminate_step_up` (`HSB_h9_provenance.md` §8.7).
3. **The `line_item_differs` / `EXAMINED_NOT_REVISED` counts in
   `docs/VALIDATION.md`'s provenance section** are a PR #122 snapshot that Wave B
   had already made stale. This lane added a live-count command rather than
   rewriting a historical paragraph; a docs pass should decide whether that
   section is a record or a status.
