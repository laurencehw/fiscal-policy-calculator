# H6 — No headline without a row

*Pre-registered 2026-09-09 against `main` @ `f3dc042` (worktree head `8964cb1`,
which adds only nightly bill-tracker data), in this lane's first commit, before
any code was touched. Outturn appended at the end, in the last commit.*

Lane **H6** of `planning/HIGH_STAKES_ACCURACY.md` §3, Wave A. Three rules,
enforced by tests rather than by review:

1. every preset carrying a `CBO_SCORE_MAP` `official_score` gets a badge entry,
   and the badge names the **tier** the row sits in;
2. a preset with **no** scorecard row of any tier may not print a dollar figure
   in its label;
3. `get_confidence_context`'s "High confidence" is keyed to the **tier**, not to
   membership of `CBO_SCORE_MAP`.

This lane **moves no scored quantity**. It touches no module, no target, no
constant, no `preregistered.py` / `holdout.py` / `loo.py` /
`target_revisions.py`, no `KNOWN_SCORES` / `CBO_SCORE_MAP`, and not
`fiscal_model/app_data.py`, which the concurrent **H1** lane owns — including
the four label strikes and the `repeal_corporate_amt` sign, which the plan
assigns to H1's PR (§4 "Conflict notes"). H6 owns the test that enforces the
label rule from then on.

---

## 1. The mechanism

### 1.1 What is on the record, and the arithmetic that does not close

The plan's §1.4 says "**24 presets carry a badge while 28 do not**, including
every tariff, international, pharma, enforcement and climate preset — all of
which *do* have scorecard rows, in the reconstruction tier", and separately that
"**Eight** of the 52 shipped presets have neither a `PRESET_TO_SCORECARD_ID`
badge nor a scorecard row of any tier". The lane brief restated that as "24 with
a badge, 28 with a reconstruction row and no badge, 8 with no row at all".
**Those three numbers sum to 60 against a catalog of 52**, so at most two of them
can be read literally. Measured on this tree — 52 presets excluding
`Custom Policy`, 81 scorecard rows:

| | n |
|---|--:|
| shipped presets (excl. `Custom Policy`) | **52** |
| with a `CBO_SCORE_MAP` `official_score` | **44** |
| with a `PRESET_TO_SCORECARD_ID` badge today | **24** |
| **without** a badge | **28** |
| … of those 28, with a scorecard row of some tier | **20** |
| … of those 28, with **no row at all** | **8** |

So §1.4's "28 do not" is the *unbadged* count and is exact; the "8 with no row"
is exact; and the third figure in the brief — "28 with a reconstruction row" —
is the first two overlapping. The 20 unbadged-with-a-row are **not** uniformly
reconstructions either: **15** are reconstruction rows, **2** are *fitted*
(`repeal_ira_credits` 0.0%, `carbon_tax_50` 0.9%) and **3** are Tier 1
pre-registered out-of-sample rows (`biden_high_income_tax` 9.2%,
`warren_ultramillionaire_surtax_3pp` 19.0%, `medicare_surcharge_2pp` 1.5%).
That matters for rule 1's wording: a badge that said "reconstruction" for all 20
would be wrong about five of them, and calling a Tier 1 row a reconstruction
would understate the only genuine skill claim the repository makes.

### 1.2 The three tiers a badge must distinguish

Read off `ScorecardEntry`, in this order (a Generic row also carries
`calibrated_to_target=True` by default, so the category test has to come first):

| tier | test | wording | n after this lane | mean abs err |
|---|---|---|--:|--:|
| out-of-sample | `category == "Generic"` | "out-of-sample prediction, N% from target" | 3 | **9.9%** |
| fitted | `calibrated_to_target` | "reproduces its published target by construction (calibrated)" | 20 | **1.3%** |
| reconstruction | otherwise | "unfitted reconstruction, N% from its published target" | 21 | **70.4%** |
| no row | no badge | "exploratory — not validated" | 8 | — |

The reconstruction column is the reason the lane exists: today a fitted 0.0% and
a **701.0%** reconstruction reach the same surface with the same green-to-red
rating vocabulary, and 15 of the 21 reconstruction rows have no badge at all, so
the app prints their dollar figure with nothing attached. `_RATING_ICON`'s
"Excellent" for a fitted row is measuring arithmetic (plan §2), so a fitted badge
says **calibrated**, not "Excellent".

Three of the 44 rows carry a **published range** rather than a point, and the
badge has to say which side of it the model sits on, because the percentage
against an editorial anchor is not a measurement of accuracy:

| preset | row | range | model | inside? | reported |
|---|---|---|--:|:-:|--:|
| `corporate-15pct` | `trump_corporate_15` | [+595.0, +673.1] | +1,491.8 | **no** ($818.7B out) | 121.6% |
| `pillar-two-adoption` | `pillar_two_adoption` | [−102.6, +56.5] | −61.2 | **yes** ($0.0B) | 23.5% |
| `tariff-reciprocal` | `reciprocal_tariffs` | [−1,800, −1,400] | −1,396.8 | no ($3.2B out) | 6.9% |

### 1.3 The badge's model figure is not always the app's headline

A badge asserts something about *the number on the screen*, so the row behind it
has to score the object the preset builds. Measured — every one of the 44 presets
built through `composer._build_preset_policy` and scored through
`composer._scorer_for` (the Explore/Build path), against its row's
`model_10yr_billions`:

* **40 of 44 agree to 0.0%**, including all 24 badges that exist today.
* **4 diverge**, and they divide into two causes:

| preset | app $B | row $B | gap | cause |
|---|--:|--:|--:|---|
| `ultra-millionaire-surtax-3pp` | −134.6 | −283.5 | **52.5%** | the ordinary/AGI base rule — **H1 closes it** (its pre-registered move is −134.6 → −283.5) |
| `medicare-surcharge-2pp` | −166.5 | −314.6 | **47.1%** | same; H1's move is −166.5 → −314.6 |
| `drug-negotiation-expand` | −41.8 | −33.5 | 24.8% | the app's FY2026 window (PR #115) **plus** the runner's own policy build |
| `top-rate-39-6` | −216.5 | −223.3 | 3.1% | same two |

The last two are decomposed rather than asserted: scored on the validation
window instead of the app's, `top-rate-39-6` reads **−194.81** (so the window is
worth +21.6 in the app's favour and the *runner-built shape* is worth a further
12.7% in the other direction) and `drug-negotiation-expand` reads **−37.63**
(window +4.2, runner shape 12.3%). Neither is a defect this lane may close —
the validation runners build their policies from the `CBOScore` record on
purpose — so both are **declared**, with their measured figures, in a registry
the test reads. The two H1 rows are declared too, with the note that the entry
should be deleted when H1 lands.

### 1.4 Why the map is re-keyed by preset id, and why the legacy name keeps its members

`PRESET_TO_SCORECARD_ID` is keyed by the emoji **display label**, which embeds
the score — exactly the string H1 is rewriting on five presets in parallel. A
label-keyed map loses those entries silently on merge. So the source of truth
becomes id-keyed (`PRESET_ID_TO_SCORECARD_ID`, on `preset_ids.PRESET_ID_BY_LABEL`'s
frozen slugs, which "never change once shipped"), and every label view is derived
through `label_for_preset_id`. `tests/test_policy_catalog.py` already pins
`PRESET_POLICIES` keys to `PRESET_ID_BY_LABEL` keys, so H1's renames must move
both together and this lane's map follows them for free.

**The legacy `PRESET_TO_SCORECARD_ID` keeps exactly the 24 members it has
today**, and that is a deliberate, reported restraint rather than an oversight.
Two modules outside this lane read its *membership* as a claim:

* `composer.py:166` `_tier_for` → `"calibrated" if preset_name in PRESET_TO_SCORECARD_ID else "generic"`;
* `ui/tabs/results_summary.py:99` `_resolve_tier` → `"Calibrated reference"` on
  membership, else `"Benchmarked preset"` when an official score exists.

Adding the 20 to *that* map would relabel every tariff, pharma and enforcement
preset "**Calibrated reference**" on a user-visible surface — a false claim, and
a worse one than the missing badge. Both files belong to other lanes in Wave A
(`composer.py` to H1, `results_summary.py` to H13), so the honest move is to
leave their input alone, put the new coverage in the badge map that
`get_validation_badge` reads, and hand over `badge_tier()` for them to route
through later. That carry-over is written down in §5.

---

## 2. Files

| file | change |
|---|---|
| `fiscal_model/ui/preset_validation.py` | id-keyed `PRESET_ID_TO_SCORECARD_ID` (44 entries), tier resolution off `ScorecardEntry`, range awareness, a short per-tier `caption`, `badge_tier()` / `is_calibrated_reference()`, `get_validation_badge` accepting a label **or** an id; `PRESET_TO_SCORECARD_ID` kept as a derived label view of the legacy 24 |
| `fiscal_model/ui/controller_utils.py` | `get_confidence_context` keyed to the tier |
| `tests/test_preset_validation.py` | updated for the new fields |
| `tests/test_no_headline_without_row.py` | new — the three rules |
| `fiscal_model/ui/policy_input_tax.py` | **one hunk, outside this lane's owned list** (H1's file): the preset badge caption is hard-coded "calibrated to reproduce this benchmark, not an independent test" for *any* badge, which is already false for the 6 reconstruction rows in the map today and would become false for 15 more. It renders `badge["caption"]` instead. The hunk is ~340 lines from H1's own edit (the `ordinary_income_base` checkbox at line 513) |

No other file is touched. `fiscal_model/app_data.py` is not opened.

---

## 3. Expected outcome

**Pre-registered, before writing any of it:**

1. **Zero scored quantities move.** `python scripts/cold_holdout.py --json`,
   `python scripts/run_validation_dashboard.py` and the 53-line preset sweep
   (`composer._build_preset_policy` → `_scorer_for` → `score_policy`) are
   **byte-identical** before and after. This lane reads the scorecard; it never
   feeds it.
2. **Badges 24 → 44**, and the badged set becomes **exactly** the set of presets
   carrying a `CBO_SCORE_MAP` `official_score` — 44 = 44, with no preset on
   either side alone. Composition after: **20 fitted** (mean 1.3%, max 13.9%),
   **21 reconstruction** (mean 70.4%, max 701.0%), **3 out-of-sample** (mean
   9.9%, max 19.0%).
3. **Unbadged 28 → 8**, and those 8 are exactly the presets with no scorecard
   row: `millionaire-surtax-5pp`, `middle-class-rate-cut-2pp`,
   `across-the-board-rate-cut-5pp`, `top-rate-45`, `irs-enforcement-high-income`,
   `drug-reform-comprehensive`, `carbon-tax-25`, `ira-clean-energy-extend`.
4. **The label rule fails on this branch by exactly four presets**, and passes
   once H1 merges: `irs-enforcement-high-income` "(-$250B)",
   `drug-reform-comprehensive` "(-$600B)", `carbon-tax-25` "(-$1.0T)",
   `ira-clean-energy-extend` "($400B)". The other four no-row presets already
   carry no figure — `top-rate-45` is the plan's model for how to do it right.
5. **`get_confidence_context` stops reading `CBO_SCORE_MAP`.** It has **no
   caller in the tree today** (grep: one definition, zero call sites), so the
   change is invisible to every surface until something wires it — which is
   itself worth recording, because the plan's §1.3(d) describes it as a live
   defect.
6. No new scorecard computation: everything routes through the one
   `_scorecard_index()` `lru_cache` that `get_validation_badge` already pays for
   (`COLD_START.md` / §6.2 item 39, ~6.5 s on a scored route). The count of full
   scorecard computations per process stays at **one**.

**Predicted to be wrong about:** nothing quantitative — this lane computes no
new quantity. If the badge counts land anywhere other than 44/8, the enumeration
in §1.1 was wrong and the doc is corrected rather than the test relaxed.

---

## 4. Falsification

The lane is falsified if any of these fails:

1. **Any scored quantity moves.** `cmp` on `cold_holdout.py --json`, on
   `run_validation_dashboard.py`, and on the 53-preset sweep. Any byte of
   difference in any of the three falsifies the lane outright.
2. **Coverage is not exact both ways.** A test asserts
   `{presets with an official_score} == {presets with a badge}` — a badge for a
   preset with no official score is as much a failure as a missing one.
3. **A badge points at a row that does not exist.** Every id in the map must
   appear in the live scorecard registry.
4. **A no-row preset prints a dollar figure.** Expected to fail on four presets
   until H1 merges; expected to pass afterwards, with no change to this test.
5. **The badge row does not score the headline.** Every badged preset is built
   and scored the way the app builds and scores it, and compared with its row's
   model figure at 1% tolerance; only the four divergences of §1.3 are declared,
   the two structural ones must *still* diverge (so the registry cannot rot), and
   an undeclared divergence fails.
6. **A tier is collapsed.** A test asserts the three tier wordings are distinct,
   that a fitted badge does not use the word "Excellent", and that no badge
   caption contains a single "validated within X%" claim.

---
