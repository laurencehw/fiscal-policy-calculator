# Lane HS-C — the label figures, and the two labels whose sign was backwards

*Pre-registered 2026-09-11 against `main` @ `2d13e60` (Waves A and B complete;
PRs #140–#147 merged). Branch `ui/hs-c-label-figures`. Every figure below is
read from `fiscal_model/validation/target_revisions.py`, from
`fiscal_model/validation/benchmark_sources.py`, or from a run of
`scripts/cold_holdout.py --json`, `scripts/run_validation_dashboard.py` and a
53-preset sweep keyed by stable preset id, all on that commit. Nothing is
recalled.*

This lane takes two hand-offs and nothing else:

* **H9's carry-over 1** — five preset labels quote a figure H9's provenance pass
  superseded. H9 moved the figures and deliberately renamed nothing, because
  labels are `CBO_SCORE_MAP` keys and Wave A's file-disjointness gave
  `app_data.py` to H1 and H6 (`HSB_h9_provenance.md` §8.5).
* **H1's invariant** — `test_a_label_figure_never_contradicts_its_own_official_score`
  found two labels printing a bare positive figure beside a negative
  `official_score`, and carried them in a `handover` set because one of the two
  was also having its figure revised by H9 and "sign and figure move together in
  the label-rename lane that follows it, not twice".

Plus **H9's carry-over 2** — `payroll.py`'s stale factory docstrings and
duplicate scenario dict, and `ui/tabs/methodology.py`'s SS-donut table row.

---

## 1. The rule

> **A preset label that quotes a figure quotes the figure its scorecard row's
> current published target carries, in this app's own sign convention: a
> negative number reduces the deficit and a positive number increases it.**

Three things follow, and each is a separate failure the tree has actually had:

1. **The figure is the target, not the model.** `🌱 Repeal IRA Clean Energy
   Credits ($783B)` quotes **the model's own output** — `model_10yr_billions` is
   −783.0 and the live target is −851.0. A label that quotes the model is the
   app marking its own homework in the one place a user cannot see it is doing so.
2. **The sign is the app's convention.** `(-$220B)` on Repeal Corporate AMT said
   a \$220B *saving* where the score was a \$220B *cost*; H1 corrected the score
   and H6 the label. Two more labels are in that state today.
3. **A revised target moves the label with it.** Otherwise the Build page totals
   one number (`official_score`) beside a label spelling another, which is
   exactly what H9 left, declared, in
   `tests/test_target_revisions.py::_LABELS_QUOTING_A_SUPERSEDED_FIGURE`.

**What the rule does *not* say.** It does not require a label to carry a figure.
`🏛️ TCJA Rates Only`, `🏢 Trump Corporate 15%`, `🌱 Carbon Tax \$25/ton` and
`🔍 High-Income Enforcement` carry none, three of them because H1 struck one.
Adding a figure to a label that has none is a new claim on screen and is out of
scope here; correcting a **description** that quotes a superseded figure is not,
because the description is prose the same revision already falsified.

### 1.1 The range question, settled on precedent rather than on preference

`eliminate_mortgage`'s live target is a **range**, `[−$495.0B, −$367.9B]`, whose
carried anchor is Tax Foundation's −\$367.9B. The brief asks whether the label
convention has a way to say "range", and it does not need to invent one: the
convention already exists and is **quote the anchor, unmarked**.
`🏭 Reciprocal Tariffs (-$1.5T)` is a range row — `[−$1,800B, −$1,400B]`, anchor
−\$1,500B — and its label quotes the anchor plainly, with the range stated in the
preset's *description* ("Published conventional estimates of the announced
schedule span \$1.4-1.8T; the official score shown anchors on Tax Foundation's
\$1.5T"). So the mortgage label quotes **−\$368B** and the range goes in prose,
in the same shape. The figure is not dropped.

---

## 2. Every label this lane moves, with the source of each figure

`official_score` **already equals the live target for all seven rows** — verified
below, not moved. Only the label string moves.

| # | id | Old label | New label | `official_score` | Where the figure comes from |
|--:|---|---|---|--:|---|
| 1 | `ss-donut-250k` | `💰 SS Donut Hole $250K (-$2.7T)` | `💰 SS Donut Hole $250K (-$1.43T)` | **−1,426.8** | `ss_donut_250k.v2` — CBO, *Options for Reducing the Deficit: 2025 to 2034* (pub. 60557), Option 62 alternative 2, report p. 73, stub "Decrease (−) in the deficit", FY2025–2034 |
| 2 | `estate-repeal` | `🏠 Eliminate Estate Tax ($350B)` | `🏠 Eliminate Estate Tax ($407B)` | **+407.2** | `eliminate_estate_tax.v2` — Tax Foundation, *Options for Reforming America's Tax Code 3.0* (July 2026), Option 83, "10-Year Change in the Deficit, 2027-2036" |
| 3 | `mortgage-deduction-eliminate` | `📋 Eliminate Mortgage Deduction (-$300B)` | `📋 Eliminate Mortgage Deduction (-$368B)` | **−367.9** | `eliminate_mortgage.v2` — **range** `[−495.0, −367.9]`; anchor is Tax Foundation *Options 3.0* Option 25. Other bound CRS IF13190 Table 2. §1.1 |
| 4 | `tariff-china-60pct` | `🏭 Trump 60% China Tariff (-$500B)` | `🏭 Trump 60% China Tariff (-$650B)` | **−650.0** | `trump_china_60.v2` — CRFB, *Options to Raise Tariff Revenue* (17 Dec 2024), row "60% Import Tariff on Chinese Goods", conventional column |
| 5 | `ira-clean-energy-repeal` | `🌱 Repeal IRA Clean Energy Credits ($783B)` | `🌱 Repeal IRA Clean Energy Credits (-$851B)` | **−851.0** | `repeal_ira_credits.v2` — William McBride, *Testimony: The Inflation Reduction Act's Green Energy Tax Credits*, Tax Foundation, 20 May 2025. **Sign *and* figure**: the old label quoted the model, positive |
| 6 | `ev-credit-repeal` | `🌱 Repeal EV Credits ($182B)` | `🌱 Repeal EV Credits (-$182B)` | **−182.3** | `repeal_ev_credits.v2` — JCT JCX-35-25. **Sign only**: the magnitude was already the target's |
| 7 | `tcja-rates-only` | `🏛️ TCJA Rates Only` | **unchanged** | +2,158.7 | Label embeds no figure. Its **description** says "(~\$3.2T)" — the superseded `tcja_rates_only.v1`. Description corrected to CRS R48286 Table 1's \$2,158.7B; label untouched, per §1 |

**Rounding.** Follows the catalog's own convention, which is three significant
figures: `(-$374B)` for −373.9, `($163B)` for 162.6, `(-$180B)` for −180.4 below
a trillion; `($1.36T)` for 1,357.1, `(-$1.62T)` for −1,621.0, `($1.17T)` for
1,169.0 above it. Hence −1,426.8 → `-$1.43T` and −367.9 → `-$368B`.

### 2.1 Descriptions, which the same revisions falsified

Seven `PRESET_POLICIES` descriptions and one knowledge file quote a superseded
figure in prose. They are corrected in the same commits, from the same ledger
rows, because "Raises ~\$2.7T over 10 years" beside a label reading −\$1.43T is
the defect this lane exists to remove, one layer down.

| File | What it says | What it will say |
|---|---|---|
| `app_data.py` SS donut | "Raises ~\$2.7T over 10 years" | CBO Option 62 alt 2's −\$1,426.8B, with the note that the module's own annual is unchanged |
| `app_data.py` estate repeal | "Costs ~\$350B over 10 years" | Tax Foundation's \$407.2B, and that the published row repeals estate **and gift** |
| `app_data.py` China 60% | "Raises ~\$500B over 10 years" | CRFB's \$650B |
| `app_data.py` IRA repeal | "Saves ~\$783B over 10 years (CBO March 2024)" | Tax Foundation's \$851B — **the attribution is wrong too** |
| `app_data.py` TCJA rates only | "(~\$3.2T)" | CRS R48286's \$2,159B |
| `app_data.py` EV repeal | "Saves ~\$182B over FY2025-2034 (JCT JCX-35-25)" | unchanged — already correct |
| `assistant/knowledge/ssa_trustees_2025.md` | "scored by CBO at **−\$2.7T** (model: **−\$2.4T**, error 12%)" | CBO's −\$1.43T, the model's −\$2.7T and the **89.2%** the scorecard actually reports |

That knowledge line is the worst single string this lane touches, and it is worth
stating why: it attributes −\$2.7T **to CBO**, which is the attribution H9 spent
a search refuting (OCACT scores E2.5 in percent of taxable payroll and publishes
no dollars at any horizon); it then quotes a model figure of −\$2.4T that the
module does not produce (it produces −\$2,700.0B, the old target restated); and
it reports 12% where the live row reports **89.2%**. It is BM25-indexed and the
Ask assistant cites it.

### 2.2 H9's carry-over 2 — `payroll.py` and `methodology.py`

* `create_ss_donut_hole`'s docstring says "SS Trustees estimate: ~\$2.7T over 10
  years for \$250K threshold". Both halves are wrong: the estimate is CBO's
  −\$1,426.8B, and the Trustees publish no dollars. The **constant stays at
  270.0** — `scenarios.py` says retuning the covered-wage band "would convert a
  finding back into bookkeeping" — so the docstring will say what the constant
  is (the superseded target ÷ 10) and what the target now is.
* `create_ss_eliminate_cap`'s "SS Trustees estimate: ~\$3.2T" keeps its
  **figure** (`ss_eliminate_cap` was *not* revised; −3,200.0 is live) and loses
  its **attribution**: `benchmark_sources` records it `secondhand`, publisher
  OCACT, `published_10yr_billions=None`, with the search noting E2.1 is scored
  only in percent of payroll.
* `PAYROLL_VALIDATION_SCENARIOS` is a **dead duplicate** — the runner reads
  `validation/scenarios.py`, and nothing in `fiscal_model/`, `scripts/` or
  `tests/` reads this dict's rows (grep: only the `__init__` re-export). Its
  `ss_donut_250k.expected_10yr` is −2,700.0. It is corrected and marked as the
  duplicate it is, so the next reader does not take it for a target.
  `CBO_PAYROLL_ESTIMATES["donut_250k_10yr"]`/`["eliminate_cap_10yr"]` are
  likewise read by nothing (only `rate_1pp_annual` and `expand_niit_annual` are
  read, at lines 466/477/683).
* `ui/tabs/methodology.py` line 669 prints
  `SS Donut Hole \$250K | -\$2,700B | -\$2,700B | 0.0% | PGPF†` under the heading
  **"Calibrated reference models"**. H6/H13 already corrected the source cell and
  its footnote. Four things are still wrong: the Official cell (−\$1,426.8B), the
  Error cell (**89.2%**), the row's **tier** (the revision forced
  `calibrated_to_target=False`, so it is an unfitted reconstruction, not a
  calibrated reference), and the footnote's claim that "\$2,700B is a Peter G.
  Peterson Foundation explainer's sentence" — true of the *superseded* figure,
  and the table no longer carries it as the official one.

### 2.3 Ids, links and the mechanism each rename uses

Stable ids **do not move** — they ship in share URLs, and `PRESET_ID_TO_SCORECARD_ID`
is keyed on them (H6), so the badge map costs nothing.

* Five of the six renames are **catalog** presets: the old spelling goes into
  `preset_ids.LEGACY_LABEL_ALIASES`, which `_build_index` folds into
  `_ALIAS_INDEX`, so `?preset=<old emoji label>` resolves.
* The sixth, `eliminate_mortgage`, is a **score-only** Build option: it has a
  `CBO_SCORE_MAP` entry and a Build id but no `PRESET_POLICIES` row.
  `LEGACY_LABEL_ALIASES` is the **wrong** mechanism for it — `_ALIAS_INDEX`
  returns a *catalog label* and `preset_id_for_token` then does
  `PRESET_ID_BY_LABEL[label]`, which would raise `KeyError` for a label that is
  not a catalog preset. `SCORE_ONLY_ALIAS_ID_BY_LABEL` is the right one, kept as
  an empty dict since the Phase E pass against exactly this need and consulted by
  `_SCORE_ONLY_INDEX`. This lane is its first user.

---

## 3. Prediction

**Zero numbers move.** Specifically:

1. `scripts/cold_holdout.py --json` is **byte-identical**. No target, no
   constant, no shape input is touched.
2. `scripts/run_validation_dashboard.py` is **byte-identical** apart from
   nothing — all 81 scorecard rows, both calibrated tiers, the 12 reconstruction
   sub-populations and the LOO suite are unchanged.
3. The **53-preset sweep keyed by stable preset id** is byte-identical, in all
   three columns (`static | behavioral | final`) and in the `official_score`
   each id carries.
4. `run_loo.py --donor-matrix` is byte-identical.
5. No Decision 6 caption is owed, because Decision 6 is about a *scored* number
   moving and none does.

**What does move, and is visible to a user:** six label strings, seven
descriptions, one knowledge file, one methodology table row and a handful of
docstrings. A Build package's total does **not** move — `build_catalog` reads
`official_score`, which H9 already moved and this lane does not touch.

**Counts that move.** `_LABELS_QUOTING_A_SUPERSEDED_FIGURE` goes **5 → 0** and
`test_base_rule_contract.py`'s `handover` set goes **3 → 0**, so
`test_a_label_figure_never_contradicts_its_own_official_score` runs against
**every** `CBO_SCORE_MAP` label with no exemptions for the first time.
`LEGACY_LABEL_ALIASES` goes **5 → 10** and `SCORE_ONLY_ALIAS_ID_BY_LABEL`
**0 → 1**.

---

## 4. Falsification

This lane is falsified, and must be reverted rather than explained, if:

1. any `model_10yr_billions` in the scorecard differs from the pre-lane run;
2. any of the 53 preset scores, keyed by **stable preset id**, differs in any of
   its three columns;
3. any `official_score` in `CBO_SCORE_MAP` differs in value (the *key* moves; the
   value may not);
4. any `abs_percent_difference`, tier mean, tier count or LOO figure moves;
5. a stable preset id changes, or a pasted `?preset=<old label>` link stops
   resolving to the id it resolved to before — the parametrised
   `test_every_retired_label_still_resolves` plus a score-only equivalent;
6. the `handover` set in `test_base_rule_contract.py` is left non-empty, or
   `_LABELS_QUOTING_A_SUPERSEDED_FIGURE` is left non-empty, for any reason other
   than a **new** revision arriving during the lane;
7. a label is renamed to a figure that is not its row's live target — i.e. if
   `test_the_app_labels_carry_the_revised_figures`'s equality/containment
   assertion has to be relaxed to make the rename pass.

**The prohibition this lane is most at risk of breaking** is the one that looks
like tidying: *retuning a constant so the model matches the figure the label now
prints*. `ss_donut_250k` reads 89.2% and `repeal_ira_credits` 8.0%; the first is
a finding H9 registered and the second is a row whose 0.0% was leakage. Neither
constant is opened. No file under `fiscal_model/payroll.py` other than
docstrings, comments and the dead duplicate's target field is edited, and
`climate.py`, `trade.py`, `estate.py`, `tax_expenditures.py` and `tcja.py` are
not opened at all.

---

## 5. Files

| File | Edit |
|---|---|
| `fiscal_model/app_data.py` | 6 `CBO_SCORE_MAP` keys, 5 `PRESET_POLICIES` keys, 5 descriptions |
| `fiscal_model/preset_ids.py` | 5 `PRESET_ID_BY_LABEL` keys, 1 `SCORE_ONLY_ID_BY_LABEL` key, +5 `LEGACY_LABEL_ALIASES`, +1 `SCORE_ONLY_ALIAS_ID_BY_LABEL` |
| `fiscal_model/policy_status.py` | 4 keys |
| `fiscal_model/ui/policy_packages.py` | 4 membership strings |
| `fiscal_model/ui/tabs/deficit_target.py` | 1 `_SCORE_ONLY_ENTRIES` key |
| `fiscal_model/validation/scenarios.py` | 3 `"preset"` strings — **and nothing else in the file** |
| `fiscal_model/payroll.py` | 2 factory docstrings, the dead duplicate, 2 constant comments |
| `fiscal_model/ui/tabs/methodology.py` | 1 table row + its footnote |
| `fiscal_model/assistant/knowledge/ssa_trustees_2025.md` | 1 bullet |
| `docs/VALIDATION.md`, `docs/METHODOLOGY.md` | the paragraphs that say the rename is outstanding |
| `tests/` | `test_base_rule_contract.py`, `test_target_revisions.py`, `test_build_page.py`, `test_policy_catalog.py` |

**Not touched:** `ui/tabs/results_summary.py` (H4), `validation/credibility.py` (H4),
`ui/estimator_ranges.py` (H4), `data/capital_gains.py` and `policies_core.py` (H5),
`trade.py` and its data (H8), `CLAUDE.md`, `README.md`, `NEXT_STEPS.md`,
`MODELING_IMPROVEMENT.md`, `CHANGELOG.md`.
