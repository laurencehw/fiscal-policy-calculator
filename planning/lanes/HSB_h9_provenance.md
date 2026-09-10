# Lane H9 — Provenance: the calibrated targets without a document

*Pre-registered 2026-09-09 on `provenance/hs-b-h9-targets`, branched from
`origin/model/hs-a-h1-base-rule` @ `fdb9f8b` (H1's branch, PR #142, awaiting the
owner's merge — H1 rewrote parts of `app_data.py`, which this lane also edits).
Every figure in §1 was measured on that branch point **before any file in §2 was
opened**. Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/HIGH_STAKES_ACCURACY.md` §3 **H9**, Wave B. **No modelling
change of any kind.** This lane moves *targets* and *verdicts*. It may not open
a module — not `payroll.py`, not `climate.py`, not `corporate.py`, not
`ptc.py` — and it retunes nothing. The falsification test is arithmetic: every
`model_10yr_billions` in the 81-row scorecard is byte-identical before and
after, and so is every leave-one-out **derivation**.

---

## 1. Starting numbers, measured on `fdb9f8b`

### 1.1 The three artifacts

| Artifact | Reading |
|---|---|
| `scripts/cold_holdout.py --json` | Tier 1: **26 cases, 15.0% mean, 10.6% median, 17/26 within 15%, 22/26 within 25%** |
| `scripts/run_validation_dashboard.py` | fitted **21 @ 1.7%** (21/21 within 15); held in place **27 @ 5.6%** (25/27); reconstructions **34 @ 57.9%** (median 34.2, 9/34); revised targets **16** |
| `scripts/run_loo.py --donor-matrix` | **18 derivable, 30.1% mean / 19.1% median, 8/18 within 15%**, 4 not cross-validatable |

Provenance, both tiers: `line_item` **51** | `line_item_differs` **7** |
`model_estimate` **6** | `secondhand` **17** | `unclassified` **0**.
Published targets **75/81**, transcribed 36.

Calibrated tier alone (55 rows): `line_item` **30** | `secondhand` **12** |
`line_item_differs` **7** | `model_estimate` **6**.

### 1.2 The eighteen this lane judges

The 30 calibrated `line_item` rows are settled. The 7 `line_item_differs` rows
already carry recorded verdicts (PR #107, PR #122) and are **re-read, not
re-opened**, unless a document contradicts one. What is left is the 12
`secondhand` and the 6 `model_estimate` rows below — the rows a Build package
inherits the provenance of, because `deficit_target.build_catalog` quotes
`CBO_SCORE_MAP`'s `official_score` as a list price rather than model output
(§1.1 of the plan).

| # | Benchmark | Provenance | Target $B | Model $B | Err | Tier |
|--:|---|---|--:|--:|--:|---|
| 1 | `ss_donut_250k` | secondhand | −2,700.0 | −2,700.0 | 0.0% | fitted |
| 2 | `ss_eliminate_cap` | secondhand | −3,200.0 | −3,200.0 | 0.0% | fitted |
| 3 | `biden_ctc_2021` | secondhand | +1,600.0 | +1,600.0 | 0.0% | fitted |
| 4 | `cap_charitable` | secondhand | −200.0 | −200.6 | 0.3% | fitted |
| 5 | `cap_employer_health` | secondhand | −450.0 | −449.5 | 0.1% | fitted |
| 6 | `eliminate_mortgage` | secondhand | −300.0 | −270.3 | 9.9% | fitted |
| 7 | `eliminate_step_up` | secondhand | −500.0 | −523.5 | 4.7% | fitted |
| 8 | `repeal_individual_amt` | secondhand | +450.0 | +450.5 | 0.1% | fitted |
| 9 | `repeal_ira_credits` | secondhand | −783.0 | −783.0 | 0.0% | fitted |
| 10 | `repeal_ptc` | secondhand | −1,100.0 | −774.1 | 29.6% | reconstruction |
| 11 | `steel_tariff_25` | secondhand | −60.0 | −52.9 | 11.9% | reconstruction |
| 12 | `trump_china_60` | secondhand | −500.0 | −278.4 | 44.3% | reconstruction |
| 13 | `carbon_tax_50` | model_estimate | −1,700.0 | −1,714.8 | 0.9% | fitted |
| 14 | `eliminate_estate_tax` | model_estimate | +350.0 | +350.0 | 0.0% | fitted |
| 15 | `tcja_no_salt_cap` | model_estimate | +5,700.0 | +6,494.5 | 13.9% | fitted |
| 16 | `tcja_rates_only` | model_estimate | +3,185.0 | +3,114.7 | 2.2% | fitted |
| 17 | `expand_drug_negotiation` | model_estimate | −500.0 | −33.5 | 93.3% | reconstruction |
| 18 | `international_reference_pricing` | model_estimate | −100.0 | −801.0 | 701.0% | reconstruction |

**Twelve of the eighteen sit in the fitted tier and eleven of those read under
5%.** That is the shape the plan's §5 warns about: a 0.0% row against a target
nobody can find is arithmetic, not agreement. Any revision among rows 1–9 and
13–16 moves that row *out* of the fitted tier by the ledger's own mechanism and
its error goes from bookkeeping to a real miss. **That is the mechanism working
and it must not be undone by retuning.**

### 1.3 The three already recorded as examined-and-left

`eliminate_mortgage` (PR #107), `steel_tariff_25` (PR #107) and `repeal_ptc`
(PR #122) already have verdicts in `EXAMINED_NOT_REVISED`. Each is re-searched
for anything published **since** its verdict date; if nothing new exists, the
verdict is restated with the new search date appended rather than rewritten.

---

## 2. Files this lane may touch

`fiscal_model/validation/{target_revisions,benchmark_sources,scenarios,cbo_scores,scorecard,readiness}.py`
and their siblings in `fiscal_model/validation/` as needed ·
`fiscal_model/data_files/validation/*.csv` transcriptions ·
`fiscal_model/app_data.py` — **only** preset descriptions and `CBO_SCORE_MAP`
`official_score`/`source`/`notes`, and only where a target this lane moves
requires it · `docs/VALIDATION.md` · `scripts/cold_holdout.py` and
`scripts/run_validation_dashboard.py` only where the `retire` state needs a
report field · `tests/` · this file.

**Not** any module outside `fiscal_model/validation/`. Not preset **labels**:
they are `CBO_SCORE_MAP` keys and H1/H6 own the label rule, so a label quoting a
figure this lane revises is *reported*, not renamed.

Sibling Wave B lanes own `policies_core.py` / `scoring_engine.py` (H2) and
`components/results.py` / `results_summary.py` (H3a). `docs/VALIDATION.md` is
edited **last**, after merging `origin/main` or H13's branch, so PR #141's
payroll paragraph and this lane's paragraphs coexist.

---

## 3. The four end states, and the search each target gets

Every one of the eighteen ends in **exactly one** state:

1. **Revised** — a published figure for the same policy design was found and the
   target moves through `target_revisions.py`: ledger row in one commit, the
   registry change that first scores against it in the next, old figure kept as
   a `superseded_by` row with its reason. `target_was_revised()` then turns
   `calibrated_to_target` off and the row reports as a reconstruction.
2. **Range-revised** — two or more standing estimators score the same reform on
   the same window and disagree, so no point is publishable. `is_range`,
   `contains()`, `distance_to_range()`; the anchor is chosen on the documents
   (§5).
3. **Examined-and-left** — the document was opened and the verdict is against
   moving. Written into `EXAMINED_NOT_REVISED`, which
   `target_revision_problems()` already forbids combining with a ledger row.
4. **Retired** — *this target should not exist and nothing replaces it.* The
   state §4 builds.

The searches, per target, and what each would take to move:

| # | Benchmark | The search | What would move it |
|--:|---|---|---|
| 1 | `ss_donut_250k` | CBO Options 2018/2020/2022/**2024** Option 62 alt 2 (already transcribed here at **$1,426.8B** FY2025-2034); OCACT E2.5; PGPF; TPC; PWBM | a published dollar score of the **same** design — same threshold, same benefit-credit treatment, a ten-year window |
| 2 | `ss_eliminate_cap` | CBO Options (no cap-elimination alternative exists in Option 62); OCACT E2.1; Tax Foundation Durante (June 2026) "$3.2T 2027-2036"; PWBM; TPC | same — **and** the Tax Foundation figure is judged on standing, not on distance: it agrees with a constant chosen to produce −$3.2T and post-dates the target |
| 3 | `biden_ctc_2021` | CBO pub. **57673** (Dec 2021) read through an archive mirror; CRFB's transcription; the requesting committee's release | the row transcribed verbatim, with its label, so a $1,597B is not carried as $1,600B |
| 4 | `cap_charitable` | JCT JCX; CBO Options 2011-2024 Option 50; TPC charitable-limit tables; CRS R45922 | a **charitable-only** rate cap. The Green Book 28% row caps all itemised deductions plus five exclusions and is three times larger |
| 5 | `cap_employer_health` | JCT 2009 exclusion-cap estimates; CBO Health Care volume; §4980I repeal scores; CRS R43168 | a **dollar-denominated** cap. Every published option caps at a premium percentile |
| 6 | `eliminate_mortgage` | anything published since 2026-03 | a scored repeal. CRS IF13190's $495B and Yale's ~$1.2T are the same simulator 2.4× apart |
| 7 | `eliminate_step_up` | JCT on the STEP Act; PWBM's 2021 Biden capital-gains decomposition; CBO Option 51 alt 1/2 | step-up elimination **with an exclusion**, scored alone. Option 51 alt 2 has no exemption and is already `cbo_opt51_gains_at_death` |
| 8 | `repeal_individual_amt` | JCX 2025-2026; CBO 2025 menus; TPC t25-/t26- | a published post-2025 **repeal** score. TPC T25-0049 is a baseline projection **and** `amt.py`'s own input — leakage, refused |
| 9 | `repeal_ira_credits` | JCT/CBO on H.R. 2811 (Limit, Save, Grow Act) energy-credit repeal; JCX-18-22; JCX-35-25; TF; CRFB | a scored **repeal**, not a projection of what the credits cost |
| 10 | `repeal_ptc` | anything scoring repeal since 2025-09 | a scored repeal. CBO/JCT 51298 Table 2's $1,142B is a baseline projection — refused, and PR #131 demonstrated the refusal rather than arguing it |
| 11 | `steel_tariff_25` | anything scoring the **25%** Section 232 regime | a ten-year estimate of the ten-week rate. Every published figure is 50%-plus-copper |
| 12 | `trump_china_60` | TF tracker China row; Yale Budget Lab; PIIE; PWBM; CRFB | a **standalone** ten-year conventional estimate of a 60% China tariff |
| 13 | `carbon_tax_50` | Treasury OTA WP-115; JCT carbon-fee bill scores; CRS R45472; TPC; RFF | a published ten-year estimate near **$50/ton**. CBO Option 73's four alternatives are $25 and $15; doubling one is constructing a target |
| 14 | `eliminate_estate_tax` | JCX-67-17 / JCX-63-17; Death Tax Repeal Act scores; TPC/PWBM/TF | a **post-TCJA-baseline** ten-year repeal score. CBO's baseline estate receipts are a projection, not a repeal score |
| 15 | `tcja_no_salt_cap` | CBO 60114/60271 alternatives; CRFB; PWBM; TF; CRS R48286 | a **single published row** for "extend TCJA, cap lapses". Two rows that would have to be added is not a target (PR #122's rule) |
| 16 | `tcja_rates_only` | CRS R48286 Table 1; JCX-35-25; CBO 60114 | a single published row for the rate structure alone |
| 17 | `expand_drug_negotiation` | CBO on the FY2025 Budget's "at least 50 drugs"; CBO on the IRA negotiation program alone; CRFB; KFF | a scored expansion. `W4_pharma_part_d.md` §5.7 finding 3 already measured the model against CBO's ~$98.5B for the existing program |
| 18 | `international_reference_pricing` | CBO on H.R. 3 Title I (the AIM-price cap); the MFN model actuarial estimates | a scored reference-pricing regime whose **scope** matches the module's |

**The failure mode is selection.** A document is adopted on its standing — is it
the same reform, the same window, the same baseline, published by a body whose
other rows this repository already scores against — never on how close it sits
to the model. Six of Wave 4's thirteen revisions made their rows *worse*; if
every revision here improves its row, the suspicion should be that the documents
were chosen to fit.

---

## 4. The `retire` state

`planning/MODELING_IMPROVEMENT.md` §6.2 item 34 records PR #122 declining to
build one because nothing needed it. Rows 17 and 18 are what needs it: "this
target should not exist and nothing replaces it" is a third thing, distinct from
a supersession (which has a replacement) and from examined-and-left (which keeps
the carried figure as a target).

### 4.1 Shape

`preregistered.py` already has the pattern and the ledger mirrors it:

```python
retired: bool = False
retired_reason: str = ""

@property
def is_live(self) -> bool:
    return self.superseded_by is None and not self.retired
```

plus `retired_targets()`, `target_was_retired(policy_id)` and
`RETIRED_POLICY_IDS`. `target_revision_problems()` gains four checks: a retired
row states a reason; a row is never both retired and superseded; a retired
policy has no live row *after* the retirement; and a retired policy is not also
in `EXAMINED_NOT_REVISED`. The live-figure consistency check is skipped for a
retired policy — there is no live row to agree with — and replaced by the
requirement that the scorecard entry is *marked* retired.

### 4.2 What it does to the scorecard, and the trap it must not fall into

Retiring rows 17 and 18 would take **93.3%** and **701.0%** out of a
34-row reconstruction tier averaging 57.9%. On the remaining 32 that reads about
**36.7%** — a 21-point "improvement" bought by deleting two rows. That is
precisely `planning/HIGH_STAKES_ACCURACY.md` §5's *"no removing a case to go
green"*, and a `retire` state that permits it silently is worse than no state at
all.

So the state is built on `declared_calibrated_to_target`'s own pattern — a
second flag and a **second reading**, never a quiet deletion:

* `ScorecardEntry.target_retired` / `target_retirement_reason`. The row **stays
  in the scorecard**, keeps its model figure, and keeps the withdrawn figure in
  `official_10yr_billions` so the entry still prints.
* `calibrated_to_target` is forced `False`, exactly as a revision does.
* The row leaves the reconstruction tier's mean — a withdrawn figure is not a
  benchmark — **and** `ScorecardSummary.retired_target_entries` counts it, and
  the dashboard prints a *retired held in place* reading: the reconstruction
  tier with the retired rows folded back at the error they carried on the day
  they were withdrawn. The two are printed on adjacent lines. Quoting the
  smaller number alone is then a visible omission rather than an invisible one.
* A retired row is excluded from `published_entries` (it already is: both are
  `model_estimate`), and readiness may not treat it as strict-blocking on
  *rating*, because it has no target — but it **is** listed by id in the
  readiness output, so a retirement can never be silent.

### 4.3 It is built, tested, and not applied

Owner decision ④ (`planning/HIGH_STAKES_ACCURACY.md` §4, Wave B) is open. This
lane therefore **builds and tests the state and applies it to nothing**: the
tests exercise it on synthetic ledger rows. The full verdict on both pharma
targets, the recommendation, and the exact one-commit edit that would apply it
go in the outturn, so the owner can say yes without this lane guessing.

---

## 5. The range-target rule, written down

Three rows now carry ranges — `pillar_two_adoption` (Wave 3),
`reciprocal_tariffs` (Wave 4), `trump_corporate_15` (PR #122) — and each was
decided ad hoc. `CalibratedTarget.distance_to_range()` already implements the
arithmetic; what is missing is the rule, so the fourth range row does not
re-open the question. It goes into `docs/VALIDATION.md`:

1. **When a range.** The publishing bodies scored the *same* reform on the
   *same* window and disagree, or one body published several scenarios and no
   single figure. Then any point the repository carries is an **editorial
   midpoint**, and a point target would assert something no document contains.
2. **The error is the distance to the nearest bound**, in dollars, and it is
   `0.0` when the model's score is inside. `contains()` is the pass condition.
3. **The percentage against the anchor is not a measurement of accuracy.** It is
   a distance from one modeller's point. `pillar_two_adoption` reports 23.5%
   while sitting **inside** its bounds; `reciprocal_tariffs` reports 6.9% while
   sitting **$3.2B outside**. Neither percentage means what a percentage means
   on a point row, and both surfaces must say so.
4. **The anchor is chosen on the documents, never on the model.** A standalone
   analysis of the one reform beats a stacked row inside a package that carries
   interaction with the rest of it (`trump_corporate_15`); a publisher this
   repository already scores its neighbours against beats one it does not
   (`reciprocal_tariffs`). Choosing the bound nearer the model is selection and
   is forbidden — PR #122 anchored `trump_corporate_15` on the **farther** bound
   for exactly this reason.
5. **A range row stays `line_item_differs`** whenever the carried anchor is not
   the transcribed figure, so the gap stays visible rather than an editorial
   choice looking sourced.
6. **A range is not a way to pass.** `trump_corporate_15` is $818.7B outside its
   bounds and reports 121.6%; the range did not soften it, the document did.

---

## 6. Prediction

**Every `model_10yr_billions` is byte-identical. Every LOO derivation is
byte-identical.** Only error columns, tier membership, provenance counts and
`CBO_SCORE_MAP` list prices move.

- `cold_holdout.py --json` — the `out_of_sample` block **byte-identical**
  (no Tier 1 target is in scope). The two calibrated blocks change only in
  which rows sit in which and in their error columns.
- `run_loo.py --donor-matrix` — every **derived** figure identical; the error
  column moves on any module whose target this lane revises, exactly as
  Wave 4's PR #107 moved five lines with five identical derivations.
- `run_validation_dashboard.py` — the fitted tier **shrinks** by the number of
  rows revised out of it, and its mean will move without anything improving or
  regressing, which is composition. The held-in-place reading is the one to
  quote beside it.
- Shipped presets score to the cent what they scored before. **No Decision 6
  caption is owed, because no scored number moves** — but a revised target does
  move the **Build package total**, since `build_catalog` sums
  `CBO_SCORE_MAP.official_score`. Every such move is listed in the PR body and
  said out loud rather than left to be noticed.

Expected direction, stated before the searches finish: **most of the eighteen
will not move**, because the plan already records that several have nothing to
move to. The plan's §5 target is `secondhand` 12 → ≤ 6 and `model_estimate`
6 → ≤ 4; this lane will report what the documents support and will not
manufacture a revision to hit a count.

---

## 7. Falsification

The lane is falsified if:

1. Any `model_10yr_billions` differs before and after.
2. Any model constant moves, or any file outside §2 is modified.
3. Any leave-one-out **derivation** differs (`run_loo.py --donor-matrix`).
4. A fitted row whose target moved is retuned, or given a readiness exemption,
   rather than leaving the fitted tier by the ledger's own mechanism.
5. A target is adopted because it is close to the model rather than because the
   document is the right one.
6. `target_revision_problems()` returns anything.
7. The `retire` state is applied to any row while owner decision ④ is open.

---

## 8. Outturn

*Appended in the lane's last commit.*
