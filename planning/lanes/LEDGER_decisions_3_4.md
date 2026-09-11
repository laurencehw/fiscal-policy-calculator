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
