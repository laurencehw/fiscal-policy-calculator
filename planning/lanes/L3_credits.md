# Lane L3 — Credits: children (and dependents) from the CPS microdata

*Pre-registered 2026-09-02 against `main` @ `7f25bed` (the merge of PR #96),
before any code change. Outturn appended at the end of the lane, in the last
commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §3 L3, under §4's rules and owner
Decisions 1 (reported vs derived), 4 (fetch the raw CPS ASEC extract by script,
never vendor it) and 5 (the three credit benchmarks are tautological in the
fitted tier and move to documented-exclusion status).

The plan scoped L3 as two or three lanes. They share `credits_core.py`,
`microsim/engine.py` and `distribution_effects.py`, so this is **one lane
landing the pieces in sequence**, each its own commit with tests.

## 1. Starting numbers

All from the branch point, `7f25bed`, via `python scripts/run_loo.py
--donor-matrix`, `python scripts/cold_holdout.py` and `python
scripts/run_validation_dashboard.py`.

### Leave-one-out (the lane's yardstick)

| Module | Case | Official | By-constr | LOO | Err |
|---|---|--:|--:|--:|--:|
| Credits | `biden_ctc_2021` | 1,600.0 | 1,600.0 | 574.1 | **−64.1%** |
| Credits | `ctc_extension` | 600.0 | 600.0 | 432.0 | **−28.0%** |
| Credits | `biden_eitc_childless` | 178.0 | 178.0 | 101.2 | **−43.1%** |

Credits module mean **45.1%** (n=3 derivable, 0 not cross-validatable), the
worst module in the suite after AMT.

**Suite aggregate: 32.3% mean / 19.2% median over 17 derivable cases, 8/17
within 15%, 5 not cross-validatable.** Per module: Payroll 3.8% (n=3),
Estate 10.4% (n=2), AMT 73.9% (n=2), Credits 45.1% (n=3),
Expenditures 28.8% (n=4), CapitalGains 39.6% (n=3).

### Fitted (by-construction) errors for the same three benchmarks

| Benchmark | Target | Fitted annual | Fitted model | Fitted err |
|---|--:|--:|--:|--:|
| `biden_ctc_2021` | $1,600B | −$160.0B/yr | $1,600.0B | **0.0%** |
| `ctc_extension` | $600B | −$60.0B/yr | $600.0B | **0.0%** |
| `biden_eitc_childless` | $178B | −$17.8B/yr | $178.0B | **0.0%** |

Every annual is the target divided by ten, to the decimal
(`credits_factory.py:74, :145, :227`). This is Decision 5's whole subject.

### Distributional benchmarks (CI-gated)

| Benchmark | Err (pp) | Rating |
|---|--:|---|
| Tax Cuts and Jobs Act, calendar 2018 | 0.00 | excellent |
| TCJA conference agreement, calendar 2019 | 2.10 | good |
| **American Rescue Plan refundable credits, 2021** | **4.76** | good |
| SALT cap repeal, 2024 | 5.86 | acceptable |
| Corporate rate 21% to 28%, 2022 | 2.51 | good |
| TCJA individual-provisions permanent extension, 2026 | 0.74 | excellent |
| P.L. 119-21 tax and cash-transfer provisions, 2026 | 3.96 | good |

The plan and `docs/VALIDATION_NOTES.md` §2 both quote the ARP gap at **~7.5pp**.
It is **4.76pp** on this branch point; the notes are stale, not wrong — they
record the figure at the time of the ARP bundle fix. The lane is measured
against 4.76pp.

### Battery aggregates

- Tier 1 (out-of-sample): **25 cases, 31.3% mean, median 14.1%, 13/25 within 15%, 18/25 within 25%.**
- Calibrated fitted tier: **30 policies, 2.2% mean, 30/30 within 15%.**
- Unfitted module reconstructions: **24 policies, 72.1% mean, 5/24 within 15%, 8/24 within 25%.**

## 2. What the lane changes

### 2.1 The mechanism (§3 L3, implemented, not redesigned)

Compute Δcredit by summing per-unit baseline vs reform credit over the weighted
CPS units, instead of `Δcredit × units × participation`. Concretely, the derived
path builds **two** parameter sets — the counterfactual schedule and the reform
schedule — runs `MicroTaxCalculator` on the CPS tax units under each, and takes
the weighted difference in final tax liability. That is the right quantity
rather than a gross credit total: it carries the non-refundable credit's tax
limit and the refundable leg's earnings phase-in, which is precisely what the
per-unit identity omits and why it understates all three expansions.

Four defects close along the way, all named in §3 L3:

1. **Three declared levers are never read anywhere.** `expand_qualifying_age`
   (`credits_core.py:125`), `include_childless_adults` (`:126`) and
   `take_up_rate_change` (`:129`) are dataclass fields no code path touches.
   They are the fields that express "17-year-olds now qualify", "childless
   workers aged 19-24 and 65+ now qualify" and a take-up response.
2. **`make_fully_refundable` / `remove_phase_out` reach only unreachable flat
   constants** (`credits_core.py:213-218`), while the correct per-unit
   refundability logic in `calculate_credit_for_income` (`:167-181`) is never
   called from the revenue path.
3. **`policy_to_microsim_reforms` collapses an EITC schedule reform to one
   scalar** (`distribution_effects.py:815-817`): `max_credit / 632`, applied as
   a multiplier to *all four* child counts. A childless-only expansion — which
   is exactly what `biden_eitc_childless` is — cannot be expressed at all, and
   the bridge instead multiplies the 3+-child maximum by 2.37.
4. **Two engine bugs.** `engine.py:64` applies a single 21.06% phase-out rate to
   every child count; the statutory childless rate is **7.65%** and the
   one-child rate **15.98%**, both already correct in `credits_core.py:40-81`.
   And the engine's EITC maxima (`:58-61`: 632/3995/6604/7430) contradict
   `credits_core.py`'s (632/4213/6960/7830). The latter are the statutory
   tax-year-2024 amounts of Rev. Proc. 2023-34 §2.06; the engine's 1/2/3+ values
   are a stale vintage. The engine will read the statutory schedule from
   `credits_core` so the two cannot drift again.

A fifth, unnamed in the plan but forced by the same data: the engine's EITC uses
`children` (under 17) as its **qualifying-child** count. A qualifying child for
the EITC is under 19, or under 24 and a full-time student. The under-17 column
undercounts that population by about 12%.

### 2.2 Data build and provenance (Decision 4)

`microsim/tax_microdata_2024.csv` keeps only `children` (under-17 headcount) and
`dependent_count`; **dependent ages do not survive the build**, so neither the
ARP under-6/6-17 split nor an age-17 expansion is expressible. Under Decision 4
the raw extract is fetched by script and never vendored:

- `scripts/fetch_cps_asec.py` downloads
  `https://www2.census.gov/programs-surveys/cps/datasets/2024/march/asecpub24csv.zip`
  (148,664,101 bytes, SHA-256
  `cdb39cdac34bef99dd0940ab28e306f692404c2eea44d85dfd634214872a0a09`,
  Last-Modified 2024-09-10) into a cache **outside the repository**, verifies the
  checksum, and extracts `pppub24.csv` and `hhpub24.csv`.
- `data_builder.py` gains that fetch as its source path and five dependent
  age-band count columns. Person-level weighted counts from the raw file, which
  is what the new columns will aggregate into tax units:

  | band | weighted (M) |
  |---|--:|
  | dependents under 6 | 22.28 |
  | dependents 6-16 | 46.02 |
  | dependents age 17 | 4.47 |
  | dependents age 18 | 4.23 |
  | dependents 19-23, enrolled in school | 6.88 |
  | *all dependents* | *90.75* |
  | *persons under 17 (today's `children`)* | *68.30* |

  Five small integer columns on 78,727 rows; the file must not grow materially
  from its 7.0 MB.
- The derived microdata stays under version control with a provenance header;
  the 148 MB raw extract does not.

census.gov was reachable from this environment (HTTP 200, full download
verified), so nothing in the lane is blocked on it.

### 2.3 Decisions 1 and 5

**Decision 1.** `TaxCreditPolicy` gains a module-local `mode` of `reported` (the
fitted annual) or `derived` (the microdata path), matching what L5 did in
`amt.py` and L6 in `tax_expenditures_core.py`. `derived` becomes the default in
the held-out validation path; the app stays `reported` unless derived beats
fitted on the module's benchmarks. Note what Decision 5 does to that
comparison: **the fitted rows are the target restated**, so "derived beats
fitted" is unwinnable by construction on the carried targets. The comparison
reported is therefore derived against the carried targets *and* against the one
published line item that exists for a comparable provision (§3).

**Decision 5.** The three benchmarks move to documented-exclusion status: a
per-case declaration in the validation registry stating that the annual is the
target divided by ten, so the by-construction error measures bookkeeping. No
case is deleted and no target is touched.

## 3. The prediction

**Headline: the CTC and EITC expansions will close a long way — the per-unit
identity understates them because it prices only the per-child credit increase,
and the microdata path prices refundability, the qualifying-age expansion and
the phase-out relaxation as well. But `ctc_extension` will move the *wrong way
against its carried target* and land near a published JCT line item instead,
and I am pre-registering that miss.**

The reasoning, from the branch point's own data before any code exists. Gross
CTC on the bundled microdata at 2025 parameters is **$125.97B** against an
actual ~$120B, so the base is close to right. Gross CTC at pre-TCJA parameters
($1,000, $75k/$110k thresholds) is **$44.61B**, a gross difference of
**$81.36B/yr**. Refundability limits and the tax-liability cap on the
non-refundable leg take some of that back; nominal growth over the window adds
some. A derived annual in the **$74B-$83B** range is what the arithmetic gives,
i.e. **$740B-$830B over ten years against a carried $600B**.

That is worse than −28.0% against the carried target. It is *better* against the
only published line item for the same provision: **JCT's JCX-35-25 row for
P.L. 119-21's child tax credit is +$816.846B over FY2025-2034**, transcribed with
a page reference in `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`
and already in the repository. The provisions are not identical — JCT scores a
$2,200 indexed credit and this benchmark a $2,000 flat one — so this is an
anchor, not a target, and no target moves in this lane. The shape is the same
one L5 and L6 both found: the structural path is closer to the document than the
fitted constant is, and that is only visible because the carried target and the
document disagree.

### Rows I expect to move, and how far

| Row | Now | Predicted band | Point | Direction |
|---|--:|--:|--:|---|
| LOO `biden_ctc_2021` | −64.1% | **−40% to −15%** | −28% | much better |
| LOO `ctc_extension` | −28.0% | **−10% to +45%** | +30% | **worse against the carried target**; near JCT's own CTC line item |
| LOO `biden_eitc_childless` | −43.1% | **−45% to −10%** | −28% | better |
| Credits module mean | 45.1% | **20% to 32%** | 28.7% | better, but **not** the plan's <20% |
| LOO suite mean (n=17) | 32.3% | **28% to 33%** | 29.4% | better |
| LOO suite median | 19.2% | **17% to 22%** | 19.2% | roughly unchanged |
| LOO within 15% | 8/17 | **8/17 to 10/17** | 8/17 | |
| Distributional ARP 2021 | 4.76pp | **2.0pp to 4.5pp** | 3.3pp | better; the plan's <4pp is reachable |

**On the plan's <20% target for the credits module.** §3 L3 asks for it and I do
not expect to reach it, for a reason that is in the benchmarks rather than the
model: two of the three targets are round hundreds (`biden_ctc_2021` $1,600B,
`ctc_extension` $600B) whose provenance is a one-line "CBO/JCT 2021" and
"CBO 2024" with no transcribed row, and the third is a Green Book figure carried
at $178B. A structural path that reproduces the statutory schedules on real CPS
units has no reason to land on a round hundred. Reaching <20% would mean
choosing parameters that do, which §4 forbids.

### Rows I expect NOT to move

- **No Tier 1 row.** No pre-registered out-of-sample case constructs a
  `TaxCreditPolicy` — `grep` of `validation/preregistered.py` finds none, and
  the credit modules are not on any Generic path. Tier 1 stays at
  **31.3% / 13 / 18**.
- **No fitted-tier row.** Every benchmark in the by-construction scorecard is
  scored in `reported` mode, which returns the same
  `annual_revenue_change_billions` it returns today. **30 policies, 2.2%.**
- **No unfitted-reconstruction row.** The 24 sectoral / line-item
  reconstructions are scored by other modules. **72.1%.**
- **Six of the seven distributional tables.** Only two benchmarks route through
  the microsim at all: `cbo_arp_2021` (two of its three components) and
  `jct_salt_repeal_2024` (`salt_cap: None`). The other five return an empty
  reform dict and take the synthetic bracket path, which this lane does not
  touch. SALT-cap repeal is a tax-side reform whose Δ is additively separable
  from a refundable credit, so **5.86pp should hold to the hundredth**; if it
  moves at all that is a finding about the CTC's non-refundable/ACTC split
  interacting with taxable income, and it goes in §4.
- **No app preset.** `preset_handler.py` builds every credit preset from the
  same factories, which keep their fitted annuals and the `reported` default.
- **No other LOO module.** Payroll, Estate, AMT, Expenditures and CapitalGains
  share no code with `credits_core.py` or `microsim/engine.py`.

Anything that moves outside this list is a finding, and gets written into §4.

### Two things that could move and I am naming in advance

1. **The bundled microdata is rebuilt.** Every consumer of
   `tax_microdata_2024.csv` — SOI calibration coverage, the filing-threshold
   filter, the top-tail augmentation, `/health`'s microdata component — reads
   the rebuilt file. The tax-unit construction rules are unchanged, so the
   existing columns should be byte-identical and the SOI coverage ratios
   (119% returns / 81% AGI) should not move. If they do, the rebuild is not
   reproducible and that is the finding, not the credit numbers.
2. **The engine's EITC baseline changes for every microsim caller.** Correcting
   the phase-out rate, the maxima and the qualifying-child definition raises
   baseline EITC. It is additively separable from most reforms, but the
   multi-model TPC-microsim pilot and the state calculator both call
   `MicroTaxCalculator`, so their outputs move. That is a correction, not a
   regression, and the tests that pin the old numbers are updated with the
   statutory citation rather than the old figure.

## 4. Outturn

*Appended after the code, in the last commit.*
