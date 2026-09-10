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
5. **A range row stays `line_item_differs`, always.** The pre-registration said
   "whenever the carried anchor is not the transcribed figure"; the existing
   test contract is stricter and better, and this lane adopted it —
   `test_a_range_revision_publishes_its_bounds_and_keeps_the_gap_visible`
   asserts `provenance != LINE_ITEM` and a non-null
   `official_10yr_billions_line_item` for **every** range row. So the record's
   `published_10yr_billions` carries the bound the anchor is *not*, and the
   spread is on the row rather than only in the ledger.
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

Three commits, in the order the rules require, plus this one:

| Commit | What |
|---|---|
| `f6d203e` | **the `retire` state** — built, tested on synthetic rows, applied to nothing |
| `cf9eb53` | **the ledger** — six revisions and nine examined-and-left verdicts entered, scored against by nothing |
| `63e76b8` | **the scoring** — `scenarios.py`, `CBO_SCORE_MAP` and `benchmark_sources.py` moved onto them |
| this one | stamps both hashes into `H9_PROVENANCE_*` and writes this section |

**No modelling change at all.** All **81** `model_10yr_billions` are
byte-identical, every leave-one-out **derivation** is unchanged, no constant was
retuned, no case deleted or retired, and Tier 1 is untouched to the byte
(`cold_holdout.py --json`'s `out_of_sample` block does not differ).

### 8.1 The eighteen, one line each

| # | Benchmark | Was | Verdict | Is | Document | Err before → after | Tier |
|--:|---|--:|---|--:|---|---|---|
| 1 | `ss_donut_250k` | −2,700.0 | **revised** | **−1,426.8** | CBO 60557, Option 62 alt 2, report p. 73 (PDF p. 79) | 0.0% → **89.2%** | fitted → recon |
| 2 | `ss_eliminate_cap` | −3,200.0 | examined-and-left | −3,200.0 | — (TF June 2026 equals it to the digit) | 0.0% → 0.0% | fitted |
| 3 | `biden_ctc_2021` | +1,600.0 | **transcribed** (no move) | +1,600.0 | CBO 57673 Table 1 row "XIII. 137102", p. 3 — **$1,597B** | 0.0% → 0.0% | fitted |
| 4 | `cap_charitable` | −200.0 | examined-and-left | −200.0 | — (CRFB 2013's $75B is self-labelled rough) | 0.3% → 0.3% | fitted |
| 5 | `cap_employer_health` | −450.0 | examined-and-left, **origin found** | −450.0 | CBO 2008 Vol. 1 Option 9 p. 24 is $452.1B — for a $17,280/yr cap | 0.1% → 0.1% | fitted |
| 6 | `eliminate_mortgage` | −300.0 | **range-revised** | **[−495.0, −367.9]**, anchor −367.9 | TF *Options 3.0* Option 25 (anchor); CRS IF13190 Table 2 | 9.9% → **26.5%** | fitted → recon |
| 7 | `eliminate_step_up` | −500.0 | examined-and-left | −500.0 | — (every standalone figure is 2.4× smaller, and broader) | 4.7% → 4.7% | fitted |
| 8 | `repeal_individual_amt` | +450.0 | examined-and-left | +450.0 | — (TF Option 38's baseline is the opposite one) | 0.1% → 0.1% | fitted |
| 9 | `repeal_ira_credits` | −783.0 | **revised** | **−851.0** | TF, McBride, House Oversight testimony, 20 May 2025 | 0.0% → **8.0%** | fitted → recon |
| 10 | `repeal_ptc` | −1,100.0 | examined-and-left (restated) | −1,100.0 | — (pub. 61734 read in full; no repeal option) | 29.6% → 29.6% | recon |
| 11 | `steel_tariff_25` | −60.0 | examined-and-left (restated) | −60.0 | — | 11.9% → 11.9% | recon |
| 12 | `trump_china_60` | −500.0 | **revised** | **−650.0** | CRFB, *Options to Raise Tariff Revenue*, 17 Dec 2024 | 44.3% → **57.2%** | recon |
| 13 | `carbon_tax_50` | −1,700.0 | examined-and-left | −1,700.0 | — (nothing at $50/ton with a 5% escalator) | 0.9% → 0.9% | fitted |
| 14 | `eliminate_estate_tax` | +350.0 | **revised** | **+407.2** | TF *Options 3.0* Option 83, printed p. 105 | 0.0% → **14.0%** | fitted → recon |
| 15 | `tcja_no_salt_cap` | +5,700.0 | examined-and-left | +5,700.0 | — (CRFB's $5.1T pairs with a $3.9T base) | 13.9% → 13.9% | fitted |
| 16 | `tcja_rates_only` | +3,185.0 | **revised** | **+2,158.7** | CRS R48286 Table 1 (transcribing CBO 60114, JCT) | 2.2% → **44.3%** | fitted → recon |
| 17 | `expand_drug_negotiation` | −500.0 | examined-and-left, **retirement recommended** | −500.0 | — (owner decision ④) | 93.3% → 93.3% | recon |
| 18 | `international_reference_pricing` | −100.0 | examined-and-left, **retirement recommended** | −100.0 | — (owner decision ④) | 701.0% → 701.0% | recon |

**Five of the six revisions make their row worse and one makes it far worse.**
That is the shape a correct provenance pass has; if every revision improved its
row the suspicion would be that the documents were chosen to fit. The one that
improves — `repeal_ira_credits`, 0.0% → 8.0% — improves only in the sense that
0.0% was arithmetic: the module's annual **was** the target.

The seven `line_item_differs` rows were re-read and none was re-opened, except
`eliminate_mortgage`, whose Wave 4 verdict a document **contradicted** (§8.4).

### 8.2 Counts

| | Before | After |
|---|---|---|
| Provenance, both tiers | `line_item` 51 · `line_item_differs` 7 · `secondhand` 17 · `model_estimate` 6 | **57 · 8 · 12 · 4** |
| Provenance, calibrated (55) | 30 · 7 · 12 · 6 | **36 · 8 · 7 · 4** |
| Published targets | 75 / 81 | **77 / 81** |
| Transcribed | 36 | **43** |
| `revised_target_entries` | 16 | **22** |
| `retired_target_entries` | 0 | **0** (the state exists; ④ is open) |

Against the plan's §5 criteria: `secondhand` **12 → 7** (target ≤ 6, one short,
and the seventh is `repeal_individual_amt`, a locked-holdout id with nothing to
move to); `model_estimate` **6 → 4** (target ≤ 4, **met**); every survivor
carries a written verdict; the `retire` state **exists**. `line_item_differs`
rose 7 → 8, which §5 permits only "with a recorded range or scope verdict" — it
is a recorded **range** verdict, `eliminate_mortgage.v2`.

### 8.3 Both tiers, and neither move is accuracy

| | Before | After |
|---|---|---|
| **Fitted** | 21 @ **1.73%**, 21/21 within 15 | **16 @ 1.51%**, 16/16 |
| **Fitted, ledger rows held in place** | 27 @ 5.6%, 25/27 | **27 @ 11.9%**, 22/27 |
| **The 21 rows the fitted tier held, on the new targets** | 1.73% | **9.82%**, 18/21 |
| **Reconstructions** | 34 @ **57.88%** (median 34.18), 9/34 | **39 @ 55.46%** (median 29.94), 11/39 |
| — *the same 34 rows, on the new targets* | 57.88% | **58.26%** |
| — *the five that arrived* | — | **36.42%** |
| Leave-one-out suite | 30.1% / 19.1%, 8/18 | **35.7% / 29.1%**, 6/18 |

**Read the two tiers together or neither, and read every one of these five lines
before quoting any of them.** The fitted mean *falls* 1.73% → 1.51% while
nothing improved, because the five rows that left it averaged **2.42%** — above
the tier's own mean. The reconstruction mean *falls* 57.88% → 55.46% while
nothing improved, because the five arrivals average **36.42%**; on a constant
population the tier gets **worse**, 57.88% → **58.26%**, and the whole 0.38pp is
`trump_china_60`. The single honest number for "what did the new targets do to
the model's measured error" is that 0.38pp, against 2.42pp of composition.

The one reading that is not composition at all is the third row: **the 21 rows
the fitted tier held before this lane, scored on the targets it leaves behind,
read 9.82% rather than 1.73%.** That is what five untraceable targets had been
worth to the tier's headline.

Leave-one-out moved for the same reason and no other: `run_loo.py
--donor-matrix` differs in **six lines** and every *derived* figure in them is
identical — `ss_donut_250k` −2,664.0 and `eliminate_mortgage` −257.9 are what
they were. Payroll **3.8% → 32.3%**, Expenditures **37.5% → 40.6%**, and
`eliminate_estate_tax` is `not x-val` before and after. Wave 4's PR #107 moved
five lines the same way.

### 8.4 The findings

**1 — CBO scores the $250,000 donut, on this repository's own window, 47% below
the figure the app has been printing.** Option 62 alternative 2, report p. 73:
−$1,426.8B over FY2025-2034. It is the same design in CBO's own words — "*The
second alternative would apply the 12.4 percent payroll tax to earnings over
$250,000 in addition to earnings below the maximum taxable amount under current
law... the gap between the two would shrink*", and "*The current-law taxable
maximum would still be used for calculating benefits, so scheduled benefits
would not change under this alternative*", which is OCACT E2.5's "do not provide
benefit credit". The 0.0% it replaces was `payroll.py`'s own arithmetic in its
own comment: `2_177.0  # 270 / 0.124`. **The row is now 89.2% and no constant
was retuned**, which is the mechanism working. Two wedges are stated rather than
adjusted: CBO's table note says an income-and-payroll-tax offset has been
applied and the module has no such channel, and footnote *a* about added benefit
outlays is attached to **alternative 1 only**, so the wedge that separates
`ss_cap_90_pct`'s revenue and deficit lines does not exist here.

**2 — The ledger refused the cap-elimination figure by its own arithmetic, and
that is the sharpest result of the pass.** H13 handed over Tax Foundation's
June 2026 "$3.2 trillion from 2027 through 2036 on a conventional basis",
scoring a proposal that applies the payroll tax to all earnings above the cap
"with no corresponding changes to benefits" — this design exactly. It is
**−$3,200.0B to the digit the document states**, and the carried target is
−$3,200.0B, so `target_revision_problems` rejects it: *"superseded without
changing the figure; a revision that restates the old target is noise."* The
lane did not have to argue the judgement — the mechanism made it. And the
judgement is right for a second reason: `payroll.py`'s constant is documented as
"*window-average of Trustees $3.2T over 10yr*", so recording the coincidence as
a confirmation would assert that a constant chosen to produce −$3.2T had been
validated by a document published eighteen months later, on a window this
repository does not use, at one significant figure.

**3 — "OCACT publishes no ten-year dollar amount for any payroll provision" was
too strong, and this repository has been saying it.** True of the *provisions*
tables; false of the office. OCACT's letter on the Medicare and Social Security
Fair Share Act (11 July 2023, to Sen. Whitehouse and Rep. Boyle), Table 1b.n,
prints "Total 2023-2032" = **$3,035.1B in nominal dollars** — for a **$400,000**
donut with no benefit credit and, unlike CBO, no income-tax offset. Different
threshold, so not a line item for either payroll row, but the claim needed
narrowing and now has it in `benchmark_sources.py` and `docs/VALIDATION.md`.

**4 — `eliminate_mortgage`'s 2.4× was the standard deduction, not the
simulator.** Wave 4 left the row on the premise that its two known figures "come
from the same simulator and differ by 2.4×, which is itself the argument against
adopting either". Tax Foundation's July 2026 guide supplies a third from an
independent general-equilibrium model, and the 2.4× resolves as a **baseline**
gap: Yale's "close to $1.2 trillion" is scored against **pre-P.L. 119-21**
current law, where TCJA's larger standard deduction lapses and the itemising
population roughly doubles, while CRS's $495B and Tax Foundation's $367.9B are
both post-OBBBA. Two independent models, one baseline, **35% apart** — which is
what a range is for. Anchor Tax Foundation's, on the rule PR #122 used: a
standalone modelled option with its own printed table beats a CRS transcription
of somebody else's simulator that CRS itself labels "not considered official for
revenue scoring purposes". **Here that rule lands on the bound nearer the
model** (26.5% against 45.4%), where on `trump_corporate_15` the same rule landed
on the farther one. The rule is the constant; which bound it picks is not.

**5 — `cap_employer_health`'s −$450B is most likely a real published figure for
a cap a third the size, a decade early.** CBO's *Budget Options, Volume 1:
Health Care* (December 2008) Option 9, p. 24, is the only published option that
states the cap in dollars — "*$1,440 a month for family coverage or $565 a month
for individual coverage*" — and JCT scores it at **$452.1B over FY2009-2018**,
0.5% from the carried target. $1,440 a month is $17,280 a year against the
$50,000 this benchmark's own description states. So the shape is
`extend_tcja_amt`'s exactly — the right number for the wrong quantity — with the
difference that there is nothing to move it *to*: no agency has ever scored a
cap set at a chosen dollar level, only at premium percentiles.

**6 — `eliminate_step_up`'s target is above an upper bound.** An exclusion makes
a repeal **narrower**, so the published no-exclusion figures bound the
with-exclusion design from above: PWBM's $204B (FY2021-2030), CBO/JCT Option 6's
$110.3B (carryover), Tax Foundation Option 15's $206.4B (2027-2036). The carried
−$500B is about 2.4× the largest of them. Every estimate that *does* carry an
exclusion is bundled — JCX-15-16's $248,739M is Obama's 28% rate **and** gains at
death with a $100,000 exclusion in one line; PWBM's $376B is three provisions in
one line — and JCT never scored the STEP Act, whose own one-pager describes this
benchmark's $1M exclusion and cites only a tax expenditure.

**7 — `tcja_rates_only`'s published row had been in the repository's own
document since May 2024.** CRS R48286 Table 1, "Reduced Individual Tax Rates",
**$2,158.7B over FY2025-2034** — the same table, the same column and the same
window this repository already reads `extend_tcja_amt`'s $1,357.1B out of. No
new document was needed and no summing was involved, so PR #122's rule against
constructing a target by adding rows never came into play. The row goes 2.2% →
**44.3%**, and the 2.2% was a decomposition of a fitted aggregate reproducing
itself.

**8 — Build was quoting a list price its own benchmark disagreed with.**
`CBO_SCORE_MAP["🏛️ TCJA Extension (No SALT Cap)"]` carried **$6,500B** with the
note "~\$4.6T + \$1.9T SALT" while `tcja_no_salt_cap` scored against **$5,700B**
and the scenario assumed ~$1.1T. Both published figures for the increment say
about **$1.2T** — CRFB's "Extend except SALT cap" row is +$1.2T beyond full
extension, and CRS R48286's itemized-deduction row is $1,244.3B. The list price
is aligned to the benchmark so one number is one number; the target itself stays
unsourced, because CRFB's $5.1T pairs with CRFB's own $3.9T base and this
repository scores the base extension against CBO's $4.6T.

**9 — `carbon_tax_50` has no published counterpart and its apparent one is a
coincidence.** Nothing anywhere scores $50/ton with a 5% escalator. The two
totals near the design both use a **2% real** escalator: Treasury OTA WP-115's
$2,221B (CY2019-2028, starting at $49/ton) and Rhodium/Columbia SIPA's
**$1,682–1,781B of 2016 dollars** (CY2020-2029, starting at $50/ton). The
carried −$1,700B falls **inside** that second range — and that is not evidence:
the window is six years earlier, the units are 2016 dollars and the escalator is
not the module's, so the coincidence is two offsetting differences. CBO's own
Option 73 alternative 1 is the one figure on this repository's window with the
module's exact escalator, $919.3B for $25/ton rising 5%, and doubling it would
be constructing a target.

**10 — `biden_ctc_2021` was blocked by a filename as much as by the bot wall.**
The letter is `57673-BBBA-GrahamSmith-Letter.pdf`; the spelling the record
carried returns CBO's own "Page not Found", so no amount of retrying would have
worked. Table 1's row "XIII. 137102 | Child tax credit" reads **1,597** in the
"With Modifications" column, and the earned income tax credit ($135B) and child
care and preschool ($752B) are separate rows — the figure is the child credit
alone. $1,600B is that rounded, **0.19%**, which is the verdict
`biden_corporate_28` gets at 0.2%: a confirmation, not a revision. One thing is
left to read and is recorded rather than papered over — footnote (a) on the
column header was not captured.

### 8.5 Build totals moved, and no caption is owed — but say it out loud

`deficit_target.build_catalog` quotes `CBO_SCORE_MAP.official_score` as a **list
price**, so a moved target moves a Build package total even though no scored
number moved anywhere:

| Preset | Was | Is | Δ |
|---|--:|--:|--:|
| 💰 SS Donut Hole \$250K | −2,700.0 | **−1,426.8** | +1,273.2 |
| 🏠 Eliminate Estate Tax | 350.0 | **407.2** | +57.2 |
| 📋 Eliminate Mortgage Deduction | −300.0 | **−367.9** | −67.9 |
| 🏭 Trump 60% China Tariff | −500.0 | **−650.0** | −150.0 |
| 🌱 Repeal IRA Clean Energy Credits | −783.0 | **−851.0** | −68.0 |
| 🏛️ TCJA Rates Only | 3,200.0 | **2,158.7** | −1,041.3 |
| 🏛️ TCJA Extension (No SALT Cap) | 6,500.0 | **5,700.0** | −800.0 (alignment, not a revision) |

**No Decision 6 caption is owed**, because Decision 6 is about a *scored* number
moving and none did. A Build package containing any of these seven now shows a
different total; that is the target's provenance changing, which is exactly what
plan §1.1 says a Build package inherits.

**Five preset labels now quote a superseded figure and were not renamed.**
Labels are `CBO_SCORE_MAP` keys, and plan §4 gives the label rule to H1 and H6,
which own `app_data.py` in Wave A; renaming a map key under them is the
collision the sequencing exists to prevent. They are **declared** in
`tests/test_target_revisions.py::_LABELS_QUOTING_A_SUPERSEDED_FIGURE`, with a
test that fails if a sixth joins:

- `💰 SS Donut Hole $250K (-$2.7T)` → −$1,426.8B
- `🏠 Eliminate Estate Tax ($350B)` → +$407.2B
- `📋 Eliminate Mortgage Deduction (-$300B)` → −$367.9B
- `🏭 Trump 60% China Tariff (-$500B)` → −$650.0B
- `🌱 Repeal IRA Clean Energy Credits ($783B)` → −$851.0B

The `test_the_app_labels_carry_the_revised_figures` assertion that mattered is
unchanged and still passing: `CBO_SCORE_MAP`'s **figure** equals (or is contained
by) the live target for every revised row.

### 8.6 The `retire` state — built, tested, applied to nothing

`CalibratedTarget` gains `retired` / `retired_reason` and `is_live` excludes a
withdrawn row, mirroring `preregistered.py`. `superseded_targets_for` is re-keyed
on `superseded_by` rather than on `not is_live`, so a withdrawal can never be
reported as a revision's history. Four new ledger checks: a retirement states its
reason; is never also superseded; is **final** (nothing live after it); and is
matched by a scorecard entry that says so — the check that replaces the
equality check a point row gets.

**The design problem was not the state, it was the arithmetic.** Retiring the two
pharma rows would take 93.3% and 701.0% out of a 34-row tier averaging 57.9% and
leave 32 rows at about **36.7%** — a 21-point improvement bought by deletion,
which is what plan §5's *"no removing a case to go green"* forbids. So:

* the row **keeps its scorecard entry and its model figure**, and
  `ScorecardSummary.retired_target_entries` counts it;
* `calibrated_to_target` is forced `False`, exactly as a revision does;
* it leaves the reconstruction mean **only alongside a second reading** —
  `uncalibrated_reconstruction_retired_held_in_place`, the same tier with the
  withdrawn rows folded back at the error they carried on the day they were
  withdrawn. `cold_holdout.py` and `run_validation_dashboard.py` print both on
  adjacent lines with the sentence that says why;
* `check_readiness.py` **lists** it (`retired_target_policy_ids`) and does not
  block on its rating, because blocking on a row with no target would make
  deleting it the cheapest way back to green.

`tests/test_target_retirement.py` is 15 tests on synthetic ledger rows, the
first of which — `test_nothing_is_retired_yet` — fails if a retirement is ever
applied without the owner's answer.

### 8.7 Owner decision ④ — the pharma pair, with the edit that would apply it

**Recommendation: retire both.** Neither figure is a score of anything, and each
is contradicted by every published quantity in its neighbourhood.

- **`expand_drug_negotiation` (−$500B).** No published score of an expansion
  exists — CBO's Options volume has no drug-negotiation option at all, and the
  phrase "at least 50 drugs" appears nowhere in the FY2025 Budget. −$500B is the
  repository's extrapolation from $237B, which `W4_pharma_part_d.md` finding 2
  established was never a negotiation score but CBO's total for the whole
  drug-pricing title. The nearest real figures score other things: CBO's
  −$98,521M for the **existing** program (PL117-169 Table 1 p. 5, sec. 11001) and
  the FY2025 Budget's −$200,000M **bundle** (Table S-6, report p. 143).
- **`international_reference_pricing` (−$100B).** A RAND price index is a price
  statistic. CBO *did* score international reference pricing — H.R. 3 Title I at
  "about $456 billion over the 2020-2029 period" (publication 55936, 10 December
  2019, Table 1: −455,927 million) — but on a **selected cohort** and a
  **pre-IRA** baseline in which Medicare had no negotiation authority at all, so
  adopting it would double-count the −$98.5B the IRA since enacted. −$100B is a
  fifth of CBO's figure for a **narrower** policy and an eighth of the module's
  own answer.

**A third and a fourth candidate turned up and are named rather than acted on**:
`carbon_tax_50` (finding 9 — the target restates `climate.py`'s own calibration)
and `eliminate_step_up` (finding 6 — the target is above an upper bound). Each
would need the same signature.

**The exact one-commit edit, if the answer is yes.** In
`fiscal_model/validation/target_revisions.py`, append to `CALIBRATED_TARGETS`:

```python
CalibratedTarget(
    revision_id="expand_drug_negotiation.v1",
    policy_id="expand_drug_negotiation",
    official_10yr_billions=-500.0,
    source_name="none (this repository's own extrapolation)",
    source_date="2024",
    window="stated as 10-year; not traceable to any published window",
    entered_commit="<this commit>",
    entered_date="<today>",
    first_scoring_run_commit="<this commit>",
    retired=True,
    retired_reason=(
        "<the verdict already written in EXAMINED_NOT_REVISED, verbatim>"
    ),
),
CalibratedTarget(
    revision_id="international_reference_pricing.v1",
    policy_id="international_reference_pricing",
    official_10yr_billions=-100.0,
    ...  # same shape
    retired=True,
    retired_reason=("<the verdict already written, verbatim>"),
),
```

and delete those two keys from `EXAMINED_NOT_REVISED` (a benchmark may not be
both, and `target_revision_problems` enforces it). Nothing else changes:
`from_result` already reads `retired_target_for`, the tiers already split, both
reports already print, and `tests/test_target_retirement.py::
test_nothing_is_retired_yet` is the one test that must then be updated — which
is the point of it.

**What the reports will say the moment it lands** (measured on this branch's
figures): reconstructions **39 @ 55.46% → 37 @ 36.99%** (median 29.62, 11/37
within 15), retired **2 @ 397.17%** — 93.30% and 701.05% — and the held-in-place
line **39 @ 55.46%** on the row beneath. **18.5 points of "improvement" bought by
withdrawing two rows**, and anyone quoting the 36.99% without the 55.46% will
have had to skip a line to do it. That is the whole reason the second reading
exists.

### 8.8 Gates

| Gate | Result |
|---|---|
| Every `model_10yr_billions` byte-identical | **81/81 identical** |
| `run_loo.py --donor-matrix` derivations | **identical**; six lines differ and every derived figure in them is unchanged |
| `cold_holdout.py --json` `out_of_sample` block | **byte-identical** |
| `target_revision_problems(entries)` | **clean** |
| `ANTHROPIC_API_KEY= pytest tests/ -q` | see §8.9 |
| `ruff check` over CI's scope | **All checks passed** |
| `check_readiness.py --strict` | only strict issue is **`runtime`** (Python 3.14), as on `main`; `documented_poor_calibrated_policy_ids` is **empty** — no fitted row is Poor |
| `build_validation_headline.py --check` | regenerated for 75 → **77** published, then **OK** |

Two rows go Poor by revision (`ss_donut_250k` 89.2%, `tcja_rates_only` 44.3%) and
each carries a `limitations` entry saying what moved and why the constant was not
retuned. That is documentation, not exemption: the readiness check's own design
is that a Poor entry with a `known_limitations` note is a recorded miss rather
than a hidden one, and both rows are in the *reconstruction* population, where
plan §5 says a miss is a finding.

### 8.9 What the lane did not do

- **Did not retire anything.** ④ is open; §8.6's first test is the guard.
- **Did not rename a preset label.** §8.5.
- **Did not open a module.** Not `payroll.py`, not `climate.py`, not `trade.py`,
  not `tcja.py`, not `estate.py`, not `tax_expenditures.py`. `payroll.py`'s
  duplicate `PAYROLL_VALIDATION_SCENARIOS` still carries −$2,700.0 and its
  factory docstrings still say "SS Trustees estimate: ~$2.7T"; the runner reads
  `validation/scenarios.py`, so nothing scored is affected, but the duplicate is
  now stale and is a carry-over.
- **Did not add a benchmark.** CBO Option 73 alternative 1 ($919.3B for $25/ton
  rising 5%, FY2025-2034) is on this repository's window with the module's exact
  escalator, and `climate.py` carries a `carbon_tax_25` scenario at an unsourced
  −$1,000B that is **not a scorecard row**. Registering it would change the
  scorecard population, which is a bigger move than targets and verdicts.
- **Did not touch `api.py`.** `ScorecardEntryModel` ignores extra fields, so
  `target_retired` is invisible over `/validation/scorecard`. Nothing is retired,
  so nothing is currently hidden; it must be wired before ④ is answered yes.
- **Did not perform arithmetic on a published figure.** CRFB's own note that its
  tariff figures "would likely be 15 percent less over the FY 2025-2034 budget
  window" is carried, not applied.

### 8.10 Carry-overs

1. **Five labels to rename** (§8.5) — H1/H6's file, H9's finding.
2. **`api.py` must expose `target_retired`** before a retirement lands (§8.9).
3. **`payroll.py`'s stale duplicate and docstrings** (§8.9), and
   `fiscal_model/ui/tabs/methodology.py` line 669, which prints
   `SS Donut Hole $250K | -$2,700B | -$2,700B | 0.0% | Trustees` — every cell of
   which is now wrong. H13 flagged it and could not reach it either.
4. **`carbon_tax_25` and CBO Option 73** — a published anchor the climate module
   has and nothing scores against (§8.9).
5. **Two more retirement candidates**, `carbon_tax_50` and `eliminate_step_up`
   (§8.7).
6. **`ss_donut_250k`'s shape**: CBO's annual path for the identical donut ramps
   $122.0B (2026) → $192.0B (2034) as the taxable maximum grows toward $250,000,
   and `create_ss_donut_hole` stamps a flat annual. That is `create_repeal_ptc`'s
   defect in a second module (H13 §6.4), and it now has a published path to be
   fixed against.
7. **The `tcja_no_salt_cap` increment**: the repository assumes ~$1.1T where CRFB
   and CRS both say ~$1.2T (§8.4 finding 8).
