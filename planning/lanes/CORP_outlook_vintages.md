# CORP outlook vintages — give each corporate +1pp row the receipts path its own document was priced on

*Pre-registration, written before `fiscal_model/corporate.py` was opened.
Branch `model/corporate-outlook-vintages`, from `main` @ `850832d`. This is
`planning/lanes/CORP_class_accuracy.md` §4.1 — R3's carry-over 6 with the
leftover restated — and nothing else in that note's list.*

The four out-of-sample corporate rows are **one reform priced by four CBO
*Options* editions** (21% → 22%, JCT-estimated, published 2018 / 2020 / 2022 /
2024). `cbo_corporate_receipts.csv` holds **one** block — February 2024,
FY2025–2034 — so the three older rows walk that nearly-flat line *backwards*
into years it does not cover. The Outlook each edition was priced on is already
transcribed as annuals in `scripts/corporate_yield_reconciliation.py`'s
`BASELINES` and has never been wired to scoring.

**What this lane is not.** It is not an accuracy claim about `derived`. Giving
each row its own document's receipts path takes a class of four from 71.6% to
about 40.3%; the 40.3% that remains is the same 80.8%-versus-JCT's-53–57%
marginal-share gap the 2024 row has been reporting since PR #121, and no
edition-specific mechanism is required to explain it (`CORP_class_accuracy.md`
§2.2). What the lane buys is that a 99.7% row stops being reported as a failed
test the module was never given.

---

## 1. Mechanism

### 1.1 Each corporate `CBOScore` names the Outlook edition its target was priced on

`CBOScore` gains one field, `corporate_receipts_vintage: str | None = None`.
It is a **shape input transcribed from the source**, in exactly the sense
`scoring_window_first_year` and `annual_authority_path_billions` already are:
each *Options* volume names the baseline its revenue options are priced
against, and that name is already recorded in
`fiscal_model/data_files/validation/corporate_rate_scores.csv`'s
`baseline_vintage` column and in each row's notes. `None` keeps the module
default, so no other record in `KNOWN_SCORES` changes behaviour.

| row | volume | Outlook the volume names | new field |
|---|---|---|---|
| `cbo2019_opt24_corporate_rate_1pp` | 2018 (pub. 54667) | April 2018, pub. 53651, Table 4-1 | `cbo_apr_2018` |
| `cbo2021_opt19_corporate_rate_1pp` | 2020 (pub. 56783) | September 2020, pub. 56517, Table 1 | `cbo_sep_2020` |
| `cbo2023_opt50_corporate_rate_1pp` | 2022 (pub. 58163) | May 2022, pub. 57950, Table 1-1 | `cbo_may_2022` |
| `cbo_opt64_corporate_rate_1pp` | 2024 (pub. 60557) | February 2024, pub. 59710, Table 1-1 | `cbo_feb_2024` |

The 2024 row names the block it already reads, so **naming it must move
nothing**. That is the lane's cheapest falsification test and §4 states it.

**A window is not a vintage, and a receipts block is not a `BaselineVintage`.**
`scoring_vintage` stays `cbo_feb_2024` on all four: it selects the *budget
baseline* the run is scored on, this repository serves exactly three vintages,
and R3's reasoning for pinning all four there is untouched. No
`BaselineVintage` member is created for 2018, 2020 or 2022 — the three older
Outlooks enter as **corporate-receipts blocks only**, which is what
`CORP_class_accuracy.md` §4.1 says a lane may do without inventing a baseline
nothing else can serve.

### 1.2 `cbo_corporate_receipts` gains a block per edition, graded

Three blocks are appended to
`fiscal_model/data_files/corporate/cbo_corporate_receipts.csv`, transcribed
from `BASELINES`:

| block | window | annual path ($B) | printed 10-yr | sum of annuals |
|---|---|---|--:|--:|
| `cbo_apr_2018` | FY2019–2028 | 276.3, 307.4, 326.7, 352.8, 388.1, 420.6, 446.5, 449.0, 431.4, 447.8 | 3,846.6 | 3,846.6 |
| `cbo_sep_2020` | FY2021–2030 | 122.8, 234.1, 289.3, 318.9, 347.3, 352.3, 355.6, 368.1, 377.6, 386.6 | 3,152.4 | 3,152.6 |
| `cbo_may_2022` | FY2023–2032 | 456.1, 478.0, 483.2, 473.0, 456.9, 461.0, 470.4, 480.1, 491.0, 505.2 | 4,754.9 | 4,754.9 |

Two of the three reproduce CBO's printed total to the cent; September 2020's
annuals sum 0.2 above its printed 3,152.4, which is the same rounding artefact
the February 2024 block already carries (5,093.9 against a printed 5,094.0) and
which `tests/test_corporate_derived.py` already pins at ±0.15. A test asserts
the check for all four blocks at that tolerance.

**Grading.** Each block carries a `sourcing` grade in a new
`CORPORATE_RECEIPTS_BLOCK_SOURCING` map beside the document string, on
`baseline.CORPORATE_RECEIPTS_SOURCING`'s own vocabulary. All four are
`published_path`: every year is CBO's own published figure for that vintage,
read from a CBO table. Nothing here is `published_base_level` or
`vintage_estimate`, and a block that ever were would be refused by the derived
path rather than silently scored.

**Reference precision, stated rather than implied.** The reference recorded per
block is the **table** — Table 4-1, Table 1, Table 1-1 — which is what
`BASELINES` carries and what the yield memo transcribed. It is not a report
*page* number: `cbo.gov` returns HTTP 403 to this environment, so re-opening
each Outlook to add one is not available, and inventing one would be worse than
naming the table. The delivery route was Wayback mirrors of `cbo.gov`, the same
standard `CORPORATE_PER_POINT_YIELD.md` used for all eighteen published scores.

**`US-CBO/cbo-data` does not carry these editions, checked rather than
assumed.** At the pinned commit `284a9566` the repository's
`data/budget/ten_year_budget` holds `annual_fy_{2024-06, 2025-01, 2026-02}.csv`
and nothing older; `data/economic/economic_projections` starts at `2024-02`;
`data/budget/revenue_detail` starts at `2024-06`. So `CORP_class_accuracy.md`
§3 item 5 is answered **no** for all three editions, and the lane takes the
transcription already in the tree, as that item instructs.

**Why `cbo_mar_2016` and `cbo_jun_2017` are left in the script and not
transcribed into the data file.** Both are **pre-TCJA**, at a 35% statutory
rate. `BASE_PER_DOLLAR_OF_RECEIPTS` is `1.0083 / τ` measured at τ = 21%, so
multiplying a 35%-era receipts path by it would price a base that does not
exist. The data file is the set of blocks a *score* may read, and those two may
not; keeping them out of it is the guard rail, not an omission.

### 1.3 The derived path reads the block the row names

`CorporateTaxPolicy` gains `receipts_vintage: str = CORPORATE_RECEIPTS_VINTAGE`
— the module default, so every factory, every preset and every app surface is
untouched. `_derived_rate_effect` and `get_phase_in_factor` pass it to
`projected_statutory_base(year, self.receipts_vintage)`, which already takes a
vintage argument and already raises rather than borrowing another vintage's
numbers. `validation/core.py`'s `corporate_rate` shape passes
`score.corporate_receipts_vintage`.

`reported` mode reads no receipts path at all, so the field is inert there, and
`CORPORATE_VALIDATION_MODE` is `derived` on all four rows regardless.

### 1.4 The 4.80133 anchor stays where it is, and here is why it is not re-anchored per edition

`BASE_PER_DOLLAR_OF_RECEIPTS` = SOI TY2022 credit-realized base ÷ Treasury
FY2022 MTS receipts = 2,039.92 / 424.865 = **4.80133**, against 1/0.21 =
4.76190 — 0.83% apart. It stays **one ratio for all four paths**. Three
reasons, in the order they bind:

1. **It is a wedge between two measurements of one year, not a property of a
   vintage.** What it measures is that SOI's credit-realized base and
   Treasury's receipts ÷ τ agree to within one percent on a completed year.
   That agreement is what makes reading the base off a receipts path a change
   of *vintage* rather than of *concept*, and it is a statement about the two
   series, not about which Outlook is being projected.
2. **A per-edition anchor has no sourced anchor year for two of the three
   editions.** The rule the module follows —
   `payroll.COVERED_EARNINGS_TO_WAGES`'s — is: measure once, on completed
   history, never on a projection year. April 2018's own completed history is
   FY2017 (τ = 35%) and FY2018 (the IRC §15 blended-rate transition year, MTS
   receipts $204.7B against FY2017's $297.0B). Neither is a 21% year, and all
   four rows price a **21% → 22%** change, so the ratio the identity needs is
   the 21%-era one. September 2020's nearest completed years are FY2019 and
   FY2020, both of which the transcribed MTS file's own header marks as
   distorted (FY2020 is a pandemic year). SOI Table 11 is transcribed for
   TY2022 and the neighbouring years only; there is no post-TCJA,
   non-pandemic, non-transition year for an April 2018 anchor to be measured
   on.
3. **A per-edition anchor would be a fitted degree of freedom per row.** Four
   ratios chosen against four targets is exactly what
   `MODELING_IMPROVEMENT.md` §4 forbids and what
   `CORP_class_accuracy.md` §4.4 lists under "do not do these". One ratio,
   four paths, four errors — which is what makes the four residuals four
   readings of one gap rather than four independent scores.

So: **no re-anchoring, no new constant, nothing fitted.** If a later lane finds
a published SOI/MTS pair for a 21%-era year an edition's own vintage would
anchor on, that is its own decision with its own pre-registration.

---

## 2. Files

Owned and expected to change:

- `fiscal_model/data_files/corporate/cbo_corporate_receipts.csv` — three blocks
  appended, header extended to say which blocks exist, why the two pre-TCJA
  Outlooks are not among them, and what each block's ten-year check is.
- `fiscal_model/corporate.py` — `CORPORATE_RECEIPTS_BLOCK_SOURCING` +
  `corporate_receipts_document()`; `CorporateTaxPolicy.receipts_vintage`;
  `_derived_rate_effect` and `get_phase_in_factor` thread it. The receipts-path
  reader only: no constant, no elasticity, no offset, no mode default.
- `fiscal_model/validation/cbo_scores.py` — `CBOScore.corporate_receipts_vintage`;
  the field set on the four corporate rows. (The brief scopes this file to
  `known_limitations`; §1.1's "each corporate `CBOScore` names its Outlook
  edition" requires the field, so the dataclass and those four records are
  opened too. No target, window, vintage or rate moves.)
- `fiscal_model/validation/core.py` — the `corporate_rate` shape passes the
  field; `_CORPORATE_BACK_PROJECTED_RECEIPTS` rewritten (it currently *is* the
  defect this lane removes) and re-scoped to whatever the rows still carry.
- `scripts/corporate_options_vintage_gap.py` — the `contemporaneous_*` columns
  become the **live** column; the February-2024-only reading is kept as
  `pre_install_*` history, with the first-year MTS diagnostic untouched.
- `scripts/corporate_yield_reconciliation.py` — the four post-TCJA `annual`
  lists are populated from the CSV so the transcription has one home; the two
  pre-TCJA ones keep their literals with §1.2's reason.
- `.github/workflows/validation-dashboard.yml` and `tests/test_ci_workflow.py`
  — the gate re-derivations of §3.5.
- `tests/` — `test_corporate_options_vintage_gap.py`,
  `test_corporate_derived.py`, `test_cbo_options_multi_volume.py`, plus new
  coverage.

Not to be touched: `CLAUDE.md`, `README.md`, `docs/`, `planning/NEXT_STEPS.md`,
`planning/MODELING_IMPROVEMENT.md`, `docs/CHANGELOG.md`.

---

## 3. Pre-registered outturn

Every figure below is computed on `main` @ `850832d` by
`python scripts/corporate_options_vintage_gap.py --json`, whose
`contemporaneous_*` reconstruction reproduces the live scores on the shipped
path to **$0.000B**. They are predictions of what the *engine* will return once
the paths are wired, not re-statements of what the script already prints.

### 3.1 The four rows

| row | before | **after (predicted)** | model $B after |
|---|--:|--:|--:|
| `cbo2019_opt24_corporate_rate_1pp` | 99.7% | **53.4%** | −147.75 |
| `cbo2021_opt19_corporate_rate_1pp` | 93.1% | **21.8%** | −120.90 |
| `cbo2023_opt50_corporate_rate_1pp` | 49.2% | **41.6%** | −183.12 |
| `cbo_opt64_corporate_rate_1pp` | 44.5% | **44.5%** | −196.081903, **to the cent** |

Tolerance: ±0.15 percentage points on the three that move (the same $0.15B the
reconstruction check uses), and **exact** on the 2024 row.

Three of the four are *improvements* and none of them is an accuracy gain in
the sense of a better mechanism: the 2018 and 2020 rows were being scored on a
base 1.295× and 1.578× the one their targets were priced against, and the 2022
row on one 1.053× it. **Quote the 21.8% with its clause or not at all**: the
September 2020 Outlook projects FY2021 corporate receipts at $122.8B against a
Treasury actual of $371.8B, so that row's 21.8% is the module's usual level
measured against a COVID-depressed denominator, not a more accurate score.

### 3.2 The class

- `corporate`: **4 @ 71.6% → 4 @ 40.3%**, error mass **286.5 → 161.3**,
  reduction **−125.2**. Within-15 0 → 0; within-25 0 → **1** (the 2020 row).
- Median 71.2% → **43.1%**.

### 3.3 The tier

- n **44 unchanged** — no row is registered, superseded, retired or
  reclassified by this lane.
- mean **18.0% → 15.2%** (±0.1), error mass **793.8 → 668.6** (±0.5).
- median **12.3% unchanged** — all four corporate rows sit above the median
  both before and after, so the rank ordering around it does not move.
- within-15 **26 unchanged**; within-25 **35 → 36**.
- **Every one of the other 40 rows byte-identical**, asserted against the
  pre-lane `cold_holdout.py --json` rather than described.

### 3.4 What must not move

- **Fitted tier**: 15 @ 1.6%, byte-identical.
- **Unfitted reconstruction tier**: 38 @ 42.3% (and the held-in-place 40 @
  60.0% beneath it), byte-identical.
- **The three calibrated corporate rows — do they read a block?** Yes, and it
  is the **same block they read today**. `biden_corporate_28`,
  `biden_corporate_28_fy2022` and `trump_corporate_15` are built by
  `create_biden_corporate_rate_only` / `create_republican_corporate_cut`, which
  set no `receipts_vintage`, and their `CBOScore` records get no
  `corporate_receipts_vintage`, so all three keep `cbo_feb_2024` by the
  dataclass default. `biden_corporate_28_fy2022` is the one that invites a
  change and does not get one: its target is Treasury's FY2022 Green Book row
  and `BASELINES`' nearest vintage, `cbo_jul_2021`, is explicitly **a proxy
  with no annual path transcribed** (`"annual": None`), so there is nothing to
  wire and wiring the proxy would be manufacturing a shape. Its window stays
  stated rather than adjusted, exactly as `CLAUDE.md` records.
- **Leave-one-out**: `run_loo.py --donor-matrix` byte-identical, every line.
  No calibrated constant is touched and no fitted module reads a receipts
  block.
- **Presets**: all **208** rows of the sweep (52 presets × `reported`/`derived`
  × static/dynamic, by stable id, full ten-year path) byte-identical. **No
  Decision 6 caption is owed** unless one moves.

### 3.5 Gates, re-derived by the workflow's own rule

The re-derivations are **forced, not discretionary**: the one-sided invariants
in `tests/test_ci_workflow.py::test_no_gate_is_looser_than_the_workflow_rule_derives`
fail on this tree at the current values.

| gate | now | rule | **after** |
|---|--:|---|--:|
| pooled ceiling | 25 | `ceil(15.2 × 1.25) = 19` → nearest 5 = 20 | **20** |
| pooled floor | 34 | `within_25 − 1 = 36 − 1` | **35** |
| class `corporate` | 90 | `ceil(40.33 × 1.25) = 51` | **51** |

Both pooled moves are tightenings, so the "downward only" clause does not bite.
The other seven class ceilings re-derive to themselves or would **loosen**
(`ordinary_rate_change` for the third wave running) and are therefore held:
`agi_inclusive_surtax` `ceil(7.2 × 1.25) = 9`, `capital_gains`
`ceil(14.4 × 1.25) = 18`, `discretionary_spending` `ceil(4.64 × 1.25) = 6`,
`enacted_law_spending` `ceil(7.43 × 1.25) = 10`, `ordinary_rate_change`
`ceil(15.3 × 1.25) = 20`, `payroll` `ceil(18.6 × 1.25) = 24`,
`tax_expenditure` `ceil(7.1 × 1.25) = 9`.

### 3.6 A consequence that is not a scored number, declared in advance

`fiscal_model/validation/credibility.py`'s `tier1_class_bands()` computes each
class's empirical band from the **live** battery — inner half-width the class
mean, outer half-width the class's worst row. So the corporate presets'
credibility caption moves with the class: inner **±71.6% → ±40.3%**, outer
**±99.7% → ±53.4%**. That is the band reporting a smaller observed error
distribution because the distribution *is* smaller, which is what the band is
for. It is a caption, not a headline score, so **no Decision 6 caption is
owed** — Decision 6 is about a scored number moving, and none does.

---

## 4. Falsification

The lane is **wrong**, and stops rather than adjusts, if any of these fires:

1. **`cbo_opt64_corporate_rate_1pp` moves by a cent.** FY2025–2034 *is* the
   transcribed February 2024 block; a lane that installs three older paths and
   moves the row that already had its own has changed something else.
2. **Any shipped preset moves by a cent**, in either mode, static or dynamic.
   The new field defaults to the module constant precisely so this cannot
   happen; if it does, the default is not where it is claimed to be.
3. **Any non-corporate Tier 1 row moves.** Nothing outside `corporate.py`'s
   receipts reader is opened.
4. **Any constant is fitted or retuned.** Asserted by test, before and after:
   `BASE_PER_DOLLAR_OF_RECEIPTS == 4.80133…`,
   `PROFIT_SHIFTING_SEMI_ELASTICITY == 0.8`,
   `BASELINE_TAXABLE_PROFITS_BILLIONS == 1900.0`,
   `ESTIMATED_PAYMENT_SAME_FY_SHARE == 0.75`, `CORPORATE_BASE_GROWTH == 0.04`.
   A per-edition anchor ratio is a retune by another name and is out (§1.4).
5. **Either calibrated tier or the LOO donor matrix moves.**
6. **A predicted row lands outside ±0.15pp of §3.1.** The reconstruction
   already matches the live identity to $0.000B, so a miss means the engine is
   not applying the identity the script models — a finding about the engine,
   to be reported rather than papered over.

---

## 5. Out of scope

Named so that the ~40% left over is visibly *left over* rather than quietly
absorbed:

- **The marginal share.** After the vintage is right, all four residuals are
  readings of one gap: this module reaches **80.8%** of the credit-realized
  statutory base a receipts path implies, JCT reaches 53–57% on a clean
  post-TCJA baseline and 66% on the COVID one. That is the class's remaining
  problem and it is not this lane's.
- **§38(c) general-business-credit absorption.** The stock is transcribed
  ($124.47B of carryforward against $72.17B of claims) and the share that would
  price it is published for no post-2010 year. `CORP_class_accuracy.md` §4.2.
- **CAMT.** Blocked on a TY2023 SOI Complete Report that does not exist, and
  §2.2 shows it cannot be the separator between these editions anyway.
- **JCT's 0.591–0.732 first-year factor**, the 1.19× JCT-vs-Treasury estimator
  gap, and CBO's 0.85/0.80 loss-firm haircut — all refused or unsourced
  elsewhere and untouched here.
- **MTS actuals as a scoring path.** JCT scored a *projection*; the first-year
  MTS ratio stays a diagnostic and the script keeps printing it as one.
- **A `BaselineVintage` member for 2018, 2020 or 2022.** No scored *budget*
  path needs one; a receipts-file key is enough, and inventing an enum member
  this deployment cannot serve would let a frozen assignment link claim a
  vintage that does not exist.

---

## 6. Outturn

*(Appended after implementation.)*
