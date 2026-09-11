# R1 — Transcribe CBO's baselines from CBO's own GitHub

*Lane of `planning/ROUTE_TO_8_5.md` Wave E, §1 R1. Branch
`model/r1-baseline-transcription`, worktree from `main` @ `994f528`.*

**Pre-registered before any file under `fiscal_model/` was edited.** Every figure
in §3 was produced on this tree by a monkeypatched dry run that applies exactly
the mechanism §1 describes — `scratchpad/r1/patch_full.py` — against
`scripts/cold_holdout.py --json` and a 106-row preset sweep, so these are
predictions with a known arithmetic, not guesses. The implementation is
falsified by any §3 figure it misses.

---

## §0 — What is being fixed, measured on this tree

`CBOBaseline` reconstructs every vintage's budget levels from eleven
`GDP_RATIOS` (`fiscal_model/constants.py:120-132`) applied to whatever nominal
GDP FRED last reported, and grows them with hand-entered rates.
`fiscal_model/baseline.py:214-219` states the blocker in as many words —
*"cbo.gov returns HTTP 403 to this environment and the Wayback Machine holds no
snapshot of the January 2025 or February 2026 budget projections workbooks…
Adding one is a data edit — a block in the CSV — not a code change."*

That is true of `cbo.gov` and false of `github.com/US-CBO`, which is not blocked.
Reproduced here before anything was changed, on `CBOBaseline(start_year=2026,
vintage=CBO_FEB_2026, use_real_data=True)` — the app's own default:

| quantity, FY2026–2035 | app | CBO's own February 2026 table | gap |
|---|--:|--:|--:|
| cumulative deficit | **$29,529.1B** | **$23,143.3B** | **+27.6%** |
| end-FY2035 debt held by the public | $49,362.1B | $53,103.2B | −7.0% |
| end-FY2035 debt/GDP | 103.8% | 118.0% | −14.1pp |
| FY2026 individual income tax | $2,248.9B | $2,751.3B | −18.3% |
| FY2026 payroll taxes | $2,027.1B | $1,825.6B | +11.0% |
| corporate receipts CAGR | 4.82%/yr | 3.53%/yr | +1.29pp |

The first row is the number on the landing page, in every Build package's
target strip and in Ask's `get_cbo_baseline`.

**A second defect this lane found while measuring, which §1 R1 does not name.**
`VINTAGE_SOURCING` grades all three vintages `"sourced"`, defined at
`baseline.py:160-163` as *"every economic assumption and base level was
transcribed from that vintage's own published tables"*. Against CBO's own
fiscal-year economic tables that claim is **false for two of the three**:

| vintage | real GDP growth | inflation | unemployment | 10-yr note | LFPR |
|---|--:|--:|--:|--:|--:|
| `CBO_FEB_2024` | **0.602pp** | 0.118pp | 0.190pp | **0.454pp** | **1.048pp** |
| `CBO_JAN_2025` | 0.114pp | 0.065pp | 0.038pp | 0.057pp | 0.074pp |
| `CBO_FEB_2026` | **0.386pp** | **0.311pp** | 0.302pp | **0.480pp** | **1.700pp** |

(max absolute difference over the ten-year window, app against
`cbo-data/data/economic/economic_projections/fiscal_<edition>.csv`.) January 2025
is genuinely transcribed and its residual is the calendar/fiscal basis — PR #118's
note says it was read off the *calendar* sheet. The other two are smoothed round
numbers, and February 2026's ten-year note **falls 4.5% → 3.9% where CBO's
rises 4.10% → 4.38%**, which is the macro survey's §1 finding 1 confirmed on this
tree. A grade that says `sourced` for all three cannot distinguish them.

---

## §1 — Mechanism

### 1.1 Sources, and what each vintage actually gets

Owner decision ⑩: both CBO GitHub repositories count as "CBO's own table",
`cbo-data` preferred. Pinned by commit, verified by SHA-256 of the file read.

| app vintage | economic path | budget path |
|---|---|---|
| `CBO_FEB_2024` | `economic_projections/fiscal_2024-02.csv` | **none exists** |
| `CBO_JAN_2025` | `economic_projections/fiscal_2025-01.csv` | `ten_year_budget/annual_fy_2025-01.csv` |
| `CBO_FEB_2026` | `economic_projections/fiscal_2026-02.csv` | `ten_year_budget/annual_fy_2026-02.csv` |

`cbo-data` @ `284a9566`, `budgetary-feedback-model` @ `9b4dd54e`, both fetched
2026-09-11.

**February 2024's budget table is not published and June 2024 is not a
substitute.** `ten_year_budget` ships `2024-06`, `2025-01` and `2026-02`;
`2024-06` is *An Update to the Budget and Economic Outlook* (publication 60039),
a different document with different numbers — its FY2025 deficit is $1,937.9B
against the January 2025 edition's $1,865.3B for the same year. Borrowing it
would be the false provenance claim `VINTAGE_SOURCING` exists to prevent, so
February 2024 keeps its reconstructed budget levels and the grade says so per
line. `economic_projections`, by contrast, **does** carry `2024-02`, so that
vintage's economic path is transcribed like the other two. This is the reason
the grade has to become per-line rather than per-vintage.

### 1.2 Which CBO variable supplies which model line

Long format, `date,variable,value`. Alternatives are tried in order because CBO
publishes some series only in their timing-adjusted form:

```
individual_income_tax    proj_rev_individual_income
corporate_income_tax     proj_rev_corporate_income
payroll_taxes            proj_rev_payroll
other_revenues           proj_rev_other  +  proj_rev_customs   (customs split out from 2026-02)
social_security          proj_mand_social_security  +  proj_offset_social_security
medicare                 proj_mand_medicare         +  proj_offset_medicare
medicaid                 proj_mand_medicaid
defense / nondefense     proj_disc_{defense,nondefense}, as SHARES of proj_outlays_discretionary
net_interest             proj_outlays_net_interest
other_mandatory          proj_outlays_total − proj_outlays_discretionary − net_interest − (the three above)
debt_held_by_public      proj_debt_held_by_public_end
nominal_gdp / real_gdp   gdp / real_gdp                        (economic table, FISCAL year)
```

Two rules, each one the falsification checks in §4 forced:

* **The discretionary split is composition, never a level.** January 2025
  publishes the defence/nondefence split of *outlays* only as
  `*_outlays_timing_adj`, and a timing-adjusted pair does not sum to the
  unadjusted `proj_outlays_discretionary` in a year where 1 October falls on a
  weekend — FY2024, 2028, 2029, 2033 and 2035 miss by $5–7B each. So the ratio
  is taken and the level comes from CBO's own unadjusted total. Where CBO
  publishes both unadjusted (February 2026) the rescaling is the identity to the
  cent. This is PR #127's IRS SOI Table 1.2 rule in a second place.
* **`other_mandatory` is a residual against CBO's own `proj_outlays_total`.**
  That makes `total_outlays` and therefore `deficit` reproduce CBO's printed
  figures whatever basis a component was published on. Where a component is
  timing-adjusted and the total is not, the timing residue lands in
  `other_mandatory`, and `PROVENANCE.csv` says so. February 2026 has no residue:
  `proj_mand_incl_offsets + proj_outlays_discretionary + proj_outlays_net_interest`
  equals `proj_outlays_total` exactly.

Economic series are stored as **fractions** (CBO prints percentages), so they
drop straight into `EconomicAssumptions`. The **fiscal** table is read and the
calendar one deliberately is not: every budget quantity here is fiscal-year, and
mixing the two would make a ratio between two years mean something different at
each end.

### 1.3 What `GDP_RATIOS` and the reconstruction constants become

`GDP_RATIOS`'s nine spending/revenue-to-GDP ratios and `debt_to_gdp` are **not
deleted**. They stay as the documented fallback for a vintage with no
transcribed budget table — February 2024 today — and `_load_from_data_sources`
consults the transcription first. `corporate_tax_to_income_tax` and
`income_tax_to_gdp` keep their existing non-baseline callers. The point of the
lane is that the app's default vintage stops reading them, not that the rule
is destroyed; a grade records which path each vintage took.

`_project_*` growth rules are likewise kept and stop being reached for a
transcribed vintage: where CBO publishes the annual path, **that path is the
projection** — no base level, no growth rule, no premium. That is
`_project_corporate_tax`'s existing shape (PR #130) generalised to every line.

### 1.4 The grade

`VINTAGE_SOURCING`'s one string per vintage cannot say "economic path
transcribed, budget levels reconstructed", which is February 2024's exact state.
It becomes a small record with a field per line, derived **from what the
transcription actually contains** rather than asserted, so a vintage whose CSV
block is missing cannot be graded `sourced` by a stale literal.
`CORPORATE_RECEIPTS_SOURCING` keeps its three existing values and February 2026
and January 2025 move `vintage_estimate` / `published_base_level` →
`published_path`.

### 1.5 The fetch script

`scripts/fetch_cbo_baseline.py`: pinned commit SHAs, SHA-256 per file, `--check`
mode, `--source-dir` for a local clone, and three identity checks plus a
cross-check against a *second* CBO repository (§4). Re-runnable; the two
transcribed CSVs plus `PROVENANCE.csv` total 56KB, so they are vendored.

### 1.6 What `nominal_income_index` does, and what it does not

H2's rule (`baseline.py:379`) is **not changed**. Its inputs become CBO's own
`nominal_gdp` path, and the one extension is that a year *before* the window for
which CBO publishes a level reads that level instead of being back-extrapolated
from the window's first growth rate. That is the rule the docstring already
states for `start_year − 1` ("the level the vintage's own Table B-1 publishes"),
applied to every published pre-window year rather than to one.

**The alternative was measured and is recorded so the choice is visible, and it
was not made on the Tier 1 number.** Leaving the back-extrapolation in place for
all pre-window years gives Tier 1 **15.1%** where reading CBO's published level
gives **15.4%**; the published level is chosen because this is a provenance
lane and an extrapolated level is not a transcription. Both readings are in §7.

---

## §2 — Files

Owned and expected to change:

* `fiscal_model/baseline.py` — transcription loader, `generate()`, the grade.
* `fiscal_model/constants.py` — `GDP_RATIOS` comment only (its values stay).
* `fiscal_model/data_files/cbo_baseline/` — new: `cbo_budget_baseline.csv`,
  `cbo_economic_baseline.csv`, `PROVENANCE.csv`.
* `scripts/fetch_cbo_baseline.py` — new.
* `tests/test_baseline_vintage.py`, `tests/test_baseline.py`, and a new
  `tests/test_cbo_baseline_transcription.py`.
* `planning/lanes/R1_baseline_transcription.md` — this file.

**Not** expected to change: `fiscal_model/corporate.py` (the corporate receipts
path already loads through it and this lane adds no vintage to
`cbo_corporate_receipts.csv`), anything under `fiscal_model/validation/`,
`app_data.py`, `app_pages/`, `deficit_target.py`, `results_summary.py`.

---

## §3 — Pre-registered outcomes

### 3.1 Tier 1 — **ten rows move, and the tier gets worse**

§1 R1's "no scored number moves" is **falsified in advance, by measurement**.
Generic income-tax rows read `_income_base_projection_factor`
(`scoring_engine.py:345-385`), which is a ratio of the scored vintage's
`nominal_income_index` — so a transcribed GDP path moves them. The window-mean
factor against TY2023:

| vintage | app | CBO's own | change |
|---|--:|--:|--:|
| `CBO_FEB_2024` (Options battery) | 1.3118 | **1.3053** | −0.50% |
| `CBO_FEB_2026` (rows with no declared vintage) | 1.2988 | **1.3427** | +3.38% |

The second is the larger and it is a genuine correction: CBO's own FY2023→FY2025
nominal growth is **10.70%** where the app assumed 8.99%.

| row | before | **predicted after** |
|---|--:|--:|
| `medicare_surcharge_2pp` | −$408.6B / 31.8% | **−$422.5B / 36.3%** |
| `warren_ultramillionaire_surtax_3pp` | −$436.8B / 24.8% | **−$451.5B / 29.0%** |
| `illustrative_1pp_all` | −$1,195.3B / 24.5% | **−$1,235.7B / 28.7%** |
| `illustrative_top_rate_5pp` | −$841.7B / 20.2% | **−$870.2B / 24.3%** |
| `illustrative_500k_2pp` | +$473.2B / 18.3% | **+$489.2B / 22.3%** |
| `biden_high_income_tax` | −$290.0B / 18.0% | **−$299.8B / 21.9%** |
| `cbo_opt45_top4_brackets_2pp` | −$654.2B / 14.9% | **−$651.0B / 14.3%** |
| `cbo_opt46_agi_surtax_1pp_20k` | −$1,333.0B / 7.4% | **−$1,326.3B / 7.9%** |
| `cbo_opt46_agi_surtax_2pp_100k` | −$1,081.2B / 2.9% | **−$1,075.8B / 2.4%** |
| `cbo_opt45_all_rates_1pp` | −$1,207.3B / 1.9% | **−$1,201.2B / 1.3%** |

The other **16 rows are byte-identical**.

Tier: **14.5% → 15.4%**, median **11.5% → 11.5%**, within-15 **16 → 16**,
within-25 **22 → 20**, mass 376.1 → **400.7**. Classes:
`agi_inclusive_surtax` 17.6% → **20.4%**, `ordinary_rate_change` 14.8% → **16.6%**,
the other six unchanged.

**The two rows that cross 25% are `warren_ultramillionaire_surtax_3pp` and
`illustrative_1pp_all`, and both are `secondhand`** — two of the five Tier 1
targets R2 exists to find documents for. Every row that gets worse is a row that
was already over-predicting; the correction adds a decade of the baseline's own
growth to rows that had too little of it, and nothing in this lane touches the
targets those rows are measured against.

**CI consequence, stated in advance and not to be worked around.** The pooled
gate is `cold_holdout.py --max-mean-error 20 --min-within-25pct 22`. Mean 15.4
passes; **within-25 of 20 fails**. The per-class gate **passes** (`agi_inclusive_surtax`
20.4 ≤ 22, `ordinary_rate_change` 16.6 ≤ 19, the rest unmoved). The workflow's own
re-derivation rule is *downward only* and explicitly refuses to let a floor
follow a count down, so **this lane does not touch the threshold**; it reports
the failure and leaves the decision to the owner. §8 carries the item.

### 3.2 The calibrated tiers and leave-one-out — **nothing moves**

Fitted **16 @ 1.5%** and unfitted reconstructions **39 @ 56.5% / 36.9% median,
10/39 within 15%** are predicted byte-identical, in every row.
`run_loo.py --donor-matrix` is predicted byte-identical. **Falsified if any of
the 55 calibrated `model_10yr_billions` changes.**

That is not an accident of scope: the corporate module's derived path reads
publication 59710's transcribed receipts CSV, not the baseline, and
`payroll.covered_earnings` reads CBO's own wage path from the same publication.
Neither is touched.

### 3.3 Presets — **none moves, in either mode**

All **53 presets × 2 module modes × static** and **× dynamic** — 106 scored rows —
are predicted identical to the cent. `HSB_h2_base_growth.md` warns that the
vintage's nominal index moves "every generic preset in static mode"; measured,
**no shipped preset takes that path**, because the specialized modules override
the static path and the generic presets in `PRESET_POLICIES` carry no
`soi_base_tax_year`. **Falsified if any preset moves.**

**No Decision 6 caption is owed**, on Decision 6's own terms: it fires when a
shipped *score* moves, and none does. §3.4's figures are baseline quantities.

### 3.4 Ask, Build and the vintage tables — **these are what the lane moves**

`CBO_FEB_2026`, FY2026–2035, `use_real_data=True`:

| figure | before | **predicted after** |
|---|--:|--:|
| ten-year cumulative deficit | $29,529.09B | **$23,143.30B** |
| mean annual deficit (Build strip) | $2,952.91B | **$2,314.33B** |
| end-FY2035 debt held by the public | $49,362.06B | **$53,103.22B** |
| end-FY2035 nominal GDP | $47,534.59B | **$45,011.50B** |
| end-FY2035 debt/GDP | 103.84% | **117.98%** |
| FY2026 nominal GDP | $33,915.45B | **$31,902.00B** |
| FY2026 total revenues | $5,181.24B | **$5,595.92B** |
| FY2026 total outlays | $7,712.35B | **$7,448.62B** |
| FY2026 deficit | $2,531.11B | **$1,852.70B** |
| corporate receipts FY2026 → FY2035 | 436.80 → 667.36 (4.82%/yr) | **403.98 → 551.91 (3.53%/yr)** |

`CBO_JAN_2025`: cumulative deficit $27,710.57B → **$21,758.26B**, end debt
$48,115.23B → **$52,055.87B**, end debt/GDP 101.53% → **118.48%**, corporate CAGR
4.80% → **0.48%**.

`CBO_FEB_2024`: budget lines **unchanged** (no published table) — cumulative
deficit stays $29,707.19B, end debt $49,350.15B, corporate receipts 491.40 →
568.77 at 1.64%/yr. Only GDP moves: FY2025 $34,012.91B → **$30,503.60B**, end
$47,900.82B → **$43,243.97B**, debt/GDP 103.03% → **114.12%**.

Grades: `VINTAGE_SOURCING` gains per-line fields; `CORPORATE_RECEIPTS_SOURCING`
`cbo_feb_2026` **`vintage_estimate` → `published_path`** and `cbo_jan_2025`
**`published_base_level` → `published_path`**.

---

## §4 — Falsification

1. **The headline.** Summing the transcribed February 2026 deficit over
   FY2026–2035 must reproduce CBO's own **$23,143.3B** to the rounding of the
   source. *Measured on the dry run: **$23,143.303B**.* If the implementation
   does not reproduce this, the lane is wrong and nothing ships.
2. **Revenue identity.** Per vintage per year, the transcribed revenue
   components must sum to `proj_rev_total` within $0.35B. Catches a dropped
   customs column.
3. **Outlay identity.** The `other_mandatory` residual must be positive in every
   year. Catches a gross line read where a net one was meant.
4. **Discretionary identity.** The defence/nondefence split must equal
   `proj_outlays_discretionary` after apportioning. Catches a timing-adjusted
   half paired with an unadjusted one — *this check fired on the first run and
   is why §1.2's composition rule exists.*
5. **A second CBO repository.** February 2026's individual, corporate, payroll
   and net-interest lines must agree with
   `budgetary-feedback-model/input/budget_baseline.csv`, a different CBO file in
   a different CBO repository, within the greater of $1B and 0.5%.
6. **Cross-check on January 2025.** The existing hand-transcribed
   `_CBO_JAN_2025_BASE_LEVELS` (PR #118, read off CBO's own Tables B-1/B-4/B-5)
   must agree with the FY2025 column of the new transcription. An independent
   confirmation that the mapping in §1.2 is the right one.
7. **Every §3 figure**, to the cent where stated.

---

## §5 — Out of scope

* **Registering a June 2024 vintage.** `annual_fy_2024-06.csv` is a complete CBO
  budget table this lane does not use, because adding a fourth `BaselineVintage`
  ripples into the URL contract, frozen links, the API and H12's files. Recorded
  as a carry-over with the file named.
* **Any target movement.** No row in `preregistered.py`, `cbo_scores.py` or
  `target_revisions.py` is opened. The ledger lane owns those.
* **The CI floor.** §3.1's failure is reported, not fixed.
* **`MARGINAL_REVENUE_RATE`, the debt-service rate path, the spend-out vector,
  the statutory parameter schedule, CBO's AGI path** — R12, R15, R4 and R7.
* **Calendar-year economics.** The anchor year of `_income_base_projection_factor`
  is a *tax* year and the table read here is fiscal. One series is read for both
  ends exactly as the existing code does; whether the anchor should read the
  calendar table is R7's question, and the lane records the size of it rather
  than taking it.
* **`scoring_engine.py`'s docstring**, which quotes the old 1.3118 factor. Not
  this lane's file; carried to §8.

---

## §6 — Outturn

*(appended after implementation)*

## §7 — Findings

*(appended after implementation)*

## §8 — Carry-overs

*(appended after implementation)*
