# Lane W7 — What a repeal of §36B removes

*Pre-registered 2026-09-06 against `main` @ `a251b32`, before any code change.
Outturn appended at the end of the lane, in the last commit.*

Scope: `planning/MODELING_IMPROVEMENT.md` §6.2 item **31**, which the
corporate/PTC provenance lane opened and was not allowed to close —
*"`repeal_ptc`'s **shape** is as much of the mismatch as its target."*
`PROVENANCE_corporate_ptc.md` §4 traced the carried −$1,100B to CBO and JCT's
own June 2024 baseline projections (publication 51298, Table 2: **$966B of
premium-tax-credit outlays + $176B of revenue reductions = $1,142B over
FY2025-2034**, 3.8% from the target), declined to adopt it — *a projection of
what a credit costs is not a score of repealing it* — and handed the modelling
half over with one sentence: *"`create_repeal_ptc` sets
`coverage_elasticity=0.0`, so what the module computes **is** a baseline cost,
and the mismatch is in the shape as much as in the target."*

That sentence is half right, and §1.2 below says which half. The module does not
compute a baseline cost. It computes **$83.0B a year growing at 4%**, a constant
chosen so that `83.0 × Σ(1.04ᵗ) × 1.10` lands on $1,100B — the `× 1.10` being
the inverted behavioural offset PR #119 corrected. It is a fitted number wearing
a baseline's clothes, and the two are not the same thing: on the vintage the app
actually serves, the credit does not grow at 4% a year at all. It **falls by a
quarter between FY2026 and FY2028**, because the enhanced credits lapsed at the
end of calendar 2025.

The lane touches `fiscal_model/ptc.py`, one new data file under
`fiscal_model/data_files/ptc/`, the PTC tests, a guarded branch of
`fiscal_model/scoring_engine.py`, one caption in
`fiscal_model/ui/tabs/results_summary.py`, and the row's `known_limitations` in
`fiscal_model/validation/scenarios.py` / `benchmark_sources.py`. It adds **no
Tier-1 row**, edits **no target**, no manifest, no threshold, and does not
re-open `EXAMINED_NOT_REVISED`: −$1,100B stays exactly where PR #122 left it.

## 1. Starting numbers

All measured on the branch point, `a251b32`, from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix` and
a sweep of `PRESET_POLICIES`.

### 1.1 The two PTC rows

Both live in the **unfitted-reconstruction** tier — neither is fitted any more,
and they got there by two different mechanisms, which is worth stating because
the brief for this lane calls `extend_enhanced_ptc` a fitted row.

| policy_id | target | provenance | model | error | `calibrated_to_target` |
|---|--:|---|--:|--:|---|
| `extend_enhanced_ptc` | +$335.0B | `line_item` | **+$366.2B** | **9.3%** | `False` — Wave 4 (PR #107) moved its target $350B → $335B, and a constant fitted to a superseded figure is not fitted to its replacement |
| `repeal_ptc` | −$1,100.0B | `secondhand` | **−$896.9B** | **18.5%** | `False` — PR #119 reclassified it, because the fitted annual reproduced −$1,100B only through an inverted offset |

There are **no modes** in this module today: `PremiumTaxCreditPolicy` has no
`mode` field, no `PTC_APP_MODE` constant, and one scoring path.

### 1.2 What `create_repeal_ptc` actually removes

```
annual_revenue_change_billions = 83.0        # "Calibrated: ~$1.1T savings"
coverage_elasticity            = 0.0         # "Not modeling coverage offset"
adverse_selection_factor       = 0.1         # dataclass default, never overridden
```

`ScoringEngine._growth_tax_policy_handlers` carries
`(PremiumTaxCreditPolicy, 0.04, False)`, so the annual is grown at **4%/yr**;
`estimate_behavioral_offset` returns `0.1 × |static|` signed with static, so the
offset erodes the saving by 10%. Scored on the benchmark's own window
(FY2026-2035, because `create_repeal_ptc(start_year=2026)` and the validator
builds `FiscalPolicyScorer(start_year=policy.start_year)`):

| FY | model static | model behavioural | model deficit |
|---|--:|--:|--:|
| 2026 | 83.0 | 8.3 | −74.7 |
| 2027 | 86.3 | 8.6 | −77.7 |
| 2028 | 89.8 | 9.0 | −80.8 |
| 2029 | 93.4 | 9.3 | −84.0 |
| 2030 | 97.1 | 9.7 | −87.4 |
| 2031 | 101.0 | 10.1 | −90.9 |
| 2032 | 105.0 | 10.5 | −94.5 |
| 2033 | 109.2 | 10.9 | −98.3 |
| 2034 | 113.6 | 11.4 | −102.2 |
| 2035 | 118.1 | 11.8 | −106.3 |
| **total** | **996.5** | **99.6** | **−896.9** |

Two constants in the same module are never reached by this path and neither is
sourced: `CBO_PTC_ESTIMATES["baseline_enhanced_annual"] = 95.0` (the fallback
`estimate_static_revenue_effect` would return if the annual were unset) and
`BASELINE_PTC_COSTS = {"enhanced_annual": 95.0, "original_aca_annual": 60.0,
"csr_annual": 15.0}`. The module's own header calls the second of those "Original
ACA baseline: ~$95B/year in credits" with no citation.

So the provenance lane's handoff needs one correction: **what the module computes
is not a baseline cost.** It is `1100 / (1.10 × Σ(1.04ᵗ)) = 83.0`, an answer key
run backwards through the growth factor and the defect. The reason that reads
*like* a baseline cost is arithmetic coincidence, and §1.4 shows exactly where
the coincidence is and where it is not.

### 1.3 What CBO publishes, from the documents

Two documents settle every quantity this lane needs, and both were read from
CBO's own PDFs through Wayback mirrors (cbo.gov returns HTTP 403 to every
non-browser client in this environment, as three previous lanes have recorded).

**(a) The baseline path of the credit.** CBO and JCT, *Federal Subsidies for
Health Insurance* / *Health Insurance and Its Federal Subsidies*, recurring
publication **51298**, Table 2, "Premium tax credits and related spending".
Two vintages are transcribed:

| | **June 2024** (report p. 3) | **February 2026** (page 4 of 5) |
|---|---|---|
| outlays for the premium tax credit | 2025 **107**, 2026 84, 2027 86, 2028 89, 2029 91, 2030 93, 2031 97, 2032 101, 2033 107, 2034 **111** | 2026 **88**, 2027 69, 2028 66, 2029 70, 2030 77, 2031 86, 2032 92, 2033 95, 2034 101, 2035 108, 2036 **116** |
| revenue reductions | 2025 22, 2026 24, 2027 15, 2028 15, 2029 15, 2030 16, 2031 16, 2032 17, 2033 18, 2034 19 | 2026 17, 2027 9, 2028 8, 2029 8, 2030 9, 2031 10, 2032 11, 2033 11, 2034 12, 2035 12, 2036 12 |
| printed window totals | outlays **966**, revenue reductions **176**, FY2025-2034 | outlays **878**, revenue reductions **103**, FY2027-2036 |
| both legs, summed by hand | **1,143** over FY2025-2034 | **959** over FY2026-2035 |

The one-dollar gap on the June 2024 revenue leg (177 summed against 176 printed)
and the two-dollar gap on February 2026's outlays (880 against 878) are CBO's
rounding to the billion, not a transcription error; the model reads the
**annual** cells, and the header of the data file records both.

**The February 2026 path is not a slower-growing version of the June 2024 path.
It is a different shape.** Subsidized marketplace enrollment in the same
document's Table 1 runs **20.9M (2025) → 13.4M (2026) → 10.3M (2027)**, and the
uninsured 26.6M → 30.0M → 34.1M, because the ARPA/IRA enhancement expired at the
end of calendar 2025. The credit's two legs fall from $105B in FY2026 to $74B in
FY2028 and do not regain their FY2026 level until FY2033.

**(b) What CBO nets out of a §36B subsidy change.** CBO and JCT, letter to
Chairmen Arrington and Smith, publication **60437** (24 June 2024), report p. 3
and Table 2 (report p. 9), on permanently extending the expanded credit over
FY2025-2034:

> "…making the policy permanent would increase the budget deficit by
> **$335 billion** over the 2025-2034 period. That deficit amount reflects an
> estimated **$415 billion increase in the cost of the premium tax credit** —
> the result of a $250 billion increase in outlays and a $164 billion decrease
> in revenues. The $335 billion increase in the deficit **is net of an
> offsetting increase in revenues**, primarily attributable to a decline in
> offers of employment-based health insurance."

and, itemised on the same page:

| channel | FY2025-2034 |
|---|--:|
| outlays for the credit | +$250B |
| revenue reductions from the credit | +$164B |
| **gross cost of the credit** | **+$415B** |
| Medicaid and CHIP | +$21B |
| Basic Health Program and §1332 waivers | +$17B |
| other outlay effects | −$13B |
| compensation shifting from tax-favoured insurance to **taxable wages** | −$101B |
| employer-mandate penalties | −$3B |
| **net effect on the deficit** | **+$335B** |

This is the decomposition the lane needs and the only published one on this
window: **CBO's own net-to-gross ratio for a §36B subsidy change is
335/415 = 0.8072**, so **19.28% of the gross change in the credit's cost does
not reach the deficit.** The denominator is exactly the quantity 51298's Table 2
prints — outlays plus revenue reductions — which is why the two documents
compose.

**There is no CBO score of a full repeal.** PR #122 searched for one and
recorded the search: the 2018/2020/2022/2025 Options volumes carry no such
option, publication 61734 (September 2025) prices extension and the repeal of
five sections of the 2025 reconciliation act and contains no elimination
option, and the 2017 AHCA/BCRA estimates bundle subsidy repeal with Medicaid on
a pre-enhancement statute and a 2017-2026 window. So the coverage response for a
*repeal* is not stated anywhere, and this lane will not invent an elasticity for
it. What it does instead is §2.2, and §4 is where that is allowed to fail.

### 1.4 Where the −$896.9B actually comes from

Against the June 2024 baseline's own $1,143B on FY2025-2034 the model is 21.5%
low, and the brief asks which of four things that is. The answer is **all four
and none of them cleanly**, because the fitted constant has no decomposition —
but the year-by-year comparison localises it:

| FY | model static | CBO Feb 2026, both legs | model ÷ CBO |
|---|--:|--:|--:|
| 2026 | 83.0 | 105 | **0.79** |
| 2027 | 86.3 | 78 | **1.11** |
| 2028 | 89.8 | 74 | **1.21** |
| 2029 | 93.4 | 78 | 1.20 |
| 2030 | 97.1 | 86 | 1.13 |
| 2031 | 101.0 | 96 | 1.05 |
| 2032 | 105.0 | 103 | 1.02 |
| 2033 | 109.2 | 106 | 1.03 |
| 2034 | 113.6 | 113 | 1.01 |
| 2035 | 118.1 | 120 | 0.98 |
| **total** | **996.5** | **959** | **1.04** |

- **The base.** Over the whole window the fitted level is only **3.9% above**
  CBO's own path, which is why this row has never looked broken. Year by year it
  is **21% low in FY2026 and 21% high in FY2028** — it misses the sunset cliff
  entirely and then tracks the recovery by accident. A repeal is a
  year-by-year removal of a path; scoring it off a smooth 4% ramp gets the
  ten-year total roughly right for the wrong reason, and would get any shorter
  window, any phase-in, and every year of the distributional and dynamic paths
  wrong.
- **The window.** The benchmark scores FY2026-2035; its target's declared window
  is FY2025-2034. On the June 2024 vintage those two windows differ by
  **$1,143B against $1,014B for FY2026-2034 alone** — FY2025, the last year of
  the enhanced credit, is a $129B year and the largest in the table.
- **The revenue leg.** A single constant cannot be attributed to a leg. The
  derived path prices both, and on the February 2026 vintage the revenue leg is
  **$107B of the $959B — 11%**, against 15% on the June 2024 vintage, because
  the enhancement's expiry falls hardest on the non-refundable portion.
- **The coverage response.** The 10% currently applied is
  `adverse_selection_factor`, a dataclass default with no citation, under a
  docstring that describes a premium spiral. CBO's own published number for the
  mirror policy is **19.28%**, and it is not a premium spiral — it is
  employment-based coverage coming back and taxable wages going away.

### 1.5 The rows this lane must not move

`repeal_ptc` and `extend_enhanced_ptc` are the only two benchmarks the PTC
module scores, and **`extend_enhanced_ptc` must not move**: its +$366.2B comes
from `create_extend_enhanced_ptc`'s own `annual_revenue_change_billions=-30.5`,
which this lane does not touch. It gets **no derived path**, and the reason is
leakage rather than laziness: the only published quantity that would drive one
is CBO's own score of that same policy (60437's $335B, or 61734's $349.8B on
FY2026-2035), which is its target. A module that scored a benchmark off its own
target would manufacture a 0% row, which is what `loo.py`'s guard exists to
catch. Recorded here so a later lane does not re-derive the question.

**No mode is added.** Decision 1's `reported`/`derived` pattern exists to keep a
fitted app default while validation moves ahead; here there is nothing to keep,
because the constant being deleted is the fitted one and the app is meant to
move with it (§3.4). A mechanism with no user is dead code —
`PROVENANCE_corporate_ptc.md` §3 declined to build the ledger's retire state on
exactly that ground.

### 1.6 Battery aggregates

| | `a251b32` |
|---|---|
| **Tier 1 out-of-sample** | **26 @ 15.2%** (median 11.4, 16 within 15%, 22 within 25%) |
| **Fitted calibrated** | **21 @ 1.7%**, 21/21 within 15% |
| **Unfitted reconstructions** | **34 @ 57.6%** (median 34.2), 9/34 within 15% |
| **LOO** | **18 derivable @ 29.6%** (median 19.1), 8/18 within 15%, 4 not cross-validatable |
| CI gate | `cold_holdout.py --max-mean-error 20 --min-within-25pct 21`, exit 0 |
| `strict_readiness_issues` | `[('runtime', None)]` — Python 3.14 only; CI runs 3.12 |
| `run_validation_dashboard.py` | exit 1 (pre-existing: 3.14 runtime + degraded microdata calibration) |
| preset **🏥 Repeal ACA Premium Credits** | **−$790.53B** |
| preset **🏥 Extend ACA Enhanced PTCs** | **+$322.78B** |

**No PTC row is in Tier 1 and no PTC module is in the LOO suite** (which holds
Payroll, Estate, AMT, Credits, Expenditures and CapitalGains), so both must come
back byte-identical. That is falsification test 3.

The preset sweep is run through `create_policy_from_preset` on
`FiscalPolicyScorer()`'s library default window, FY2025-2034, which is what the
comparable sweeps in `SWEEP_offset_sign.md` §7.3 and `L8_tariffs.md` §7.5 used.
Because `create_repeal_ptc` starts in 2026, the preset therefore scores **nine**
policy years, FY2026-2034, and the benchmark scores ten.

## 2. What the lane changes

### 2.1 The base: the vintage's own projection of the credit, year by year

A repeal of §36B removes the credit. The credit's cost is a published annual
path, so the static effect becomes

```
static(FY) = outlays_for_the_credit(FY, vintage) + revenue_reductions(FY, vintage)
```

read from `fiscal_model/data_files/ptc/cbo_premium_tax_credit_baseline.csv`, a
transcription of publication 51298's Table 2 with the document, table and page
in the file's own header. Two vintage blocks are transcribed: `cbo_jun_2024`
(FY2024-2034, the years in which both legs are printed) and `cbo_feb_2026`
(FY2026-2036, likewise — the February 2026 table prints outlays for 2025 and
`n.a.` for that year's revenue reductions, so 2025 is not transcribed).

`PTC_BASELINE_VINTAGE = "cbo_feb_2026"`, matching
`CBOBaseline`'s own default (`BaselineVintage.CBO_FEB_2026`) and therefore the
vintage every app surface and the benchmark runner already score on. The
policy carries a `baseline_vintage` field so a caller can ask a different
vintage, and asking for one with no transcribed block **raises** rather than
falling back to another vintage's numbers — the rule
`corporate.cbo_receipts_by_fiscal_year` set, for the same reason: a score
reported as "on the June 2024 baseline" when it was computed on February 2026's
would be a false provenance claim.

Outside a vintage's tabulated years the path **holds the nearest endpoint's
level below the first year and continues the last observed growth rate above the
last**. The asymmetry is deliberate and is a property of this series rather than
a convention: the early years contain a policy cliff (−26% from FY2026 to
FY2027), so extrapolating that growth backwards would invent a 2025 credit of
$141B where CBO prints $111B of outlays, while the late years grow smoothly at
about 7%/yr and continuing them is the same extension `payroll.covered_earnings`
and `corporate.cbo_corporate_receipts` already make.

`create_repeal_ptc`'s `annual_revenue_change_billions=83.0` is **deleted**, not
overridden. `ScoringEngine` gets one guarded branch — the fourth of its kind,
beside the tax-expenditure, payroll and corporate ones — that asks the policy for
the year being scored and switches the module-default 4%/yr growth off rather
than compounding it on a path that already carries CBO's own growth.

### 2.2 The coverage response: CBO's own net-to-gross, and why it is not zero

The published gross cost of the credit is not the deficit effect of removing it.
People who lose marketplace coverage return to employment-based coverage,
where their premiums are excluded from income and payroll tax; some move to
Medicaid, CHIP or a Basic Health Program; employer-mandate penalties change. CBO
prices all of it, and §1.3(b) is the itemisation.

The lane applies **the ratio CBO published for the mirror policy**:

```
PTC_NET_TO_GROSS            = 335.0 / 415.0 = 0.807229
CBO_OFFSETTING_SHARE        = 1 - 335/415   = 0.192771
```

as the module's behavioural offset for the repeal path, same-signed with the
static effect per `TaxPolicy.estimate_behavioral_offset`'s contract, so it
**erodes** the saving. The unsourced `adverse_selection_factor = 0.1` and
`coverage_elasticity` are bypassed on this path, not deleted — both remain
public API and reach the module's other factories.

**Three things this is not, stated before the result is known.**

1. **It is not fitted.** It moves the row *away* from −$1,100B (§3.1), which is
   the tell. A 10% offset would have left the row nearer its target, and the
   lane is shipping the 19.28% anyway.
2. **It is not a full-repeal estimate**, and no published one exists. It is a
   ratio transferred from an *extension of the enhancement* to a *repeal of the
   whole credit*, in the opposite direction. §4's fourth falsification is about
   exactly this, and §5 records the composition argument that says the transfer
   is optimistic in one direction and pessimistic in the other.
3. **It is not leakage today, and could become leakage tomorrow.** The
   numerator, $335B, is `extend_enhanced_ptc`'s own target. That row does not
   read the ratio — it keeps its fitted annual — and `repeal_ptc` is scored
   against a different figure entirely. But a later lane that gives the
   extension a derived path off this ratio would be scoring a benchmark against
   its own target, and the constant's docstring says so.

The gross (zero-offset) figure will be printed beside the shipped one in §3.1
and in the outturn, so an owner can see what declining the transfer costs
without re-running anything.

### 2.3 Where the code goes

| file | change |
|---|---|
| `fiscal_model/data_files/ptc/cbo_premium_tax_credit_baseline.csv` | **new** — two vintage blocks of publication 51298 Table 2, with document/table/page in the header |
| `fiscal_model/ptc.py` | loader + `PTC_BASELINE_VINTAGE`, `PTC_NET_TO_GROSS`, `CBO_OFFSETTING_SHARE`; `baseline_vintage` and `coverage_offset_share` fields; the year-indexed repeal branch; `create_repeal_ptc` loses its fitted annual |
| `fiscal_model/scoring_engine.py` | one guarded branch: pass `year=`, switch off the 4%/yr growth for the baseline-path branch |
| `tests/test_ptc.py` (+ new cases) | the transcription reproduces CBO's printed totals; the vintage switch; the extrapolation rule; the offset's sign and share; `extend_enhanced_ptc` unmoved |
| `fiscal_model/ui/tabs/results_summary.py` | Decision 6 caption, **own commit**, computed from the scored result |
| `fiscal_model/validation/scenarios.py`, `benchmark_sources.py` | `known_limitations` and the `searched` note updated **only where the shape finding changes what remains**. The target does not move and `EXAMINED_NOT_REVISED` is not touched |

## 3. The prediction

Every figure below is arithmetic on the transcribed tables and is committed
before the module is opened. Bands are ±2% on the model figure, which is the
width CBO's own rounding to the billion allows.

### 3.1 `repeal_ptc`

| | model | vs −$1,100B (the carried target) | vs −$1,142B (51298's own figure) |
|---|--:|--:|--:|
| today | −$896.9B | 18.47% | 21.47% |
| **shipped: derived, Feb 2026 vintage, net** | **−$774.1B** | **29.62%** | **32.21%** |
| *printed, not shipped:* derived gross, no offset | −$959.0B | 12.82% | 16.02% |
| *printed, not shipped:* derived net on the June 2024 vintage, FY2025-2034 | −$922.7B | 16.12% | 19.21% |
| *printed, not shipped:* derived gross on the June 2024 vintage, FY2025-2034 | −$1,143.0B | 3.91% | **0.09%** |

**The lane pre-registers a regression, and the last row is why it is a
regression rather than a failure.** Scored on the vintage and window the target
came from, with no coverage response, the mechanism reproduces the figure PR
#122 traced to **0.09%** — which is not a validation of the model but a
demonstration that CBO's baseline projection *is* what −$1,100B is a rounding
of. Two things then move the shipped number away from it, and both are the
point of the lane: the app serves the **February 2026** baseline, in which the
enhanced credit has already lapsed and the ten-year cost of the credit is
**$959B rather than $1,143B**; and a repeal is **not** its gross cost, because
CBO nets 19.28% of any §36B subsidy change out of the deficit.

So the honest reading of the shipped 29.6% is that it is the distance between a
model scored on the 2026 baseline and a target that is a 2024 baseline
projection of a bigger credit. Neither half of that is a modelling error, and
neither is closed by anything a modelling lane may do.

### 3.2 The other tiers

| | before | predicted after |
|---|---|---|
| Tier 1 out-of-sample | 26 @ 15.2% | **identical, row for row** |
| Fitted calibrated | 21 @ 1.7% | **identical** |
| Unfitted reconstructions | 34 @ 57.6% / 34.2% | **34 @ 57.9%**, one row moving |
| — `extend_enhanced_ptc` | +$366.2B, 9.3% | **unchanged, to the cent** |
| LOO | 18 @ 29.6% | **byte-identical** |
| CI gate | exit 0 | **exit 0** — Tier 1 is untouched, and the gate reads Tier 1 |

### 3.3 The scorecard rating, and readiness

`repeal_ptc` goes **Acceptable (18.5%) → Poor (29.6%)**. It is an unfitted
reconstruction carrying `known_limitations`, so `readiness.py`'s three-way split
puts it in `documented_reconstruction`, which is exempt from strict blocking by
the rule in its own comment — *"blocking on it would make deleting the runner
the cheapest way back to green"*. `strict_readiness_issues` must therefore stay
`[('runtime', None)]` locally and pass on CI's 3.12. If it does not, the lane
has found something and §4's fifth test fires.

### 3.4 The preset, and Decision 6

**🏥 Repeal ACA Premium Credits (−$1.1T)** is a shipped preset and it moves:

| | |
|---|--:|
| before | **−$790.53B** |
| predicted after | **−$677.3B** |
| move | **+14.3%** (a smaller saving) |

That is material, so **Decision 6 binds**: a caption in
`fiscal_model/ui/tabs/results_summary.py`, after the existing ones, in its own
commit, computed from the scored result so it cannot drift from the headline
above it, and firing only on the preset that moved. The preset's validation
badge drops with it, Acceptable → Poor, and that is the correct reading rather
than something for a caption to soften: the app now says how far a repeal scored
on the current baseline sits from a target that is a two-year-old baseline
projection of a larger credit.

Every other preset must score **to the cent** what it scored on `a251b32`.
**🏥 Extend ACA Enhanced PTCs** in particular: it routes through the untouched
factory, so it stays at **+$322.78B**.

## 4. Falsification tests

Each of these fires against the lane, not for it.

1. **Any non-PTC scorecard row moving.** Nothing outside `ptc.py` and one
   guarded engine branch is opened; a row moving anywhere else means the branch
   is not guarded.
2. **`extend_enhanced_ptc` moving by a cent.** Its factory is untouched. If it
   moves, the change reached a path §1.5 promised it would not.
3. **Tier 1 or the LOO donor matrix moving.** No PTC row is in either. Checked
   by diffing `cold_holdout.py --json` and `run_loo.py --donor-matrix` against
   the branch point, not by reading the summary lines.
4. **`repeal_ptc` landing *closer* to −$1,100B than the 18.5% it starts at.**
   The lane predicts 29.6%. A mechanism built from two documents that happened
   to land on an untraceable secondhand figure would be evidence that something
   was chosen to fit, and the lane would have to say which choice.
5. **Strict readiness failing.** Predicted `[('runtime', None)]`. A hard failure
   would mean the reconstruction exemption does not work the way §3.3 reads it.
6. **The transcription not reproducing CBO's printed totals** within the
   one-to-two-dollar rounding §1.3 records. A pinned test, so this one fires in
   CI rather than in prose.

## 5. What this lane will not do

- **Move the target.** −$1,100B stays, `EXAMINED_NOT_REVISED` stays at six
  entries, and the $1,142B PR #122 declined is still declined — it is a baseline
  projection, and §3.1's last row shows precisely how completely the model can
  reproduce a baseline projection when asked to.
- **Give `extend_enhanced_ptc` a derived path** (§1.5).
- **Add a `reported`/`derived` mode** (§1.5).
- **Model the composition of the coverage response.** The transferred 19.28% is
  dominated, in CBO's own itemisation, by **employment-based coverage**: $101B
  of the $104B revenue offset is compensation shifting between taxable wages and
  tax-favoured insurance. A repeal of the *whole* credit reaches a different
  population — enrollees between 100% and 150% of the FPL, most of whom have no
  employer offer at all — so the true composition would carry **less**
  employer-shift revenue and **more** Medicaid pickup than the extension's does.
  Those two point in opposite directions and neither is published. Named in
  `known_limitations`, not modelled.
- **Touch the $325B variant.** 60437's footnote 4 says the $335B "incorporated
  interactions associated with extending certain expiring provisions of the 2017
  tax act", and excluding those the extension would cost $325B — a net-to-gross
  of 0.7831, an offsetting share of 21.7% rather than 19.3%. The headline
  sentence is what defines the ratio and is what ships; the 2.4pp band is
  recorded here as the sensitivity an owner should read the shipped figure with.
- **Rebuild the module's unsourced constants.** `BASELINE_PTC_COSTS`,
  `MARKETPLACE_DATA` and the FPL/premium-cap schedules are untouched. The
  repeal path stops reading `CBO_PTC_ESTIMATES["baseline_enhanced_annual"]`;
  the constant stays for the other branches, which is a carry-over rather than a
  clean-up this lane is scoped for.

## 6. Outturn

*Appended 2026-09-06, after the code. Numbers from `python
scripts/cold_holdout.py --json`, `python scripts/run_loo.py --donor-matrix`,
`python scripts/run_validation_dashboard.py`, `python
scripts/check_readiness.py --strict` and a sweep of `PRESET_POLICIES`, all on
the finished branch. `main` did not move under the lane, so §1's baseline is
what these are measured against.*

**The prediction held to the decimal on the row, on both counterfactual reads,
on the preset and on every aggregate.** §3 said −$774.1B / 29.62% against
−$1,100B and −$677.3B for the preset, computed from the transcribed tables
before `ptc.py` was opened. The runner reports **−$774.13B / 29.62%** and the
sweep **−$677.27B**. The two figures §3 printed but did not ship — the gross
read and the June 2024 read — came back at **−$959.0B** and **−$1,143.0B**, the
second of which is **0.09%** from CBO's own $1,142B.

### 6.0 Three corrections to §1, made here rather than there

§§1-5 are the pre-registration and are left as committed, including where they
are wrong. Three sentences in the diagnosis need correcting, and none of them
touches a prediction or a falsification test:

| §1 says | it should say |
|---|---|
| intro: the credit "falls by a quarter between FY2026 and FY2028" | **by nearly a third** — $105B to $74B, 29.5% |
| §1.4: FY2025 at $129B is "the largest in the table" on the June 2024 vintage | **not quite** — FY2034 is $130B. What is true is that the credit falls to $101B in FY2027 and does not exceed its FY2025 level again until the last year of that window |
| §1.4: the revenue leg is 11% against 15% "because the enhancement's expiry falls hardest on the non-refundable portion" | the two shares are **$107B of $959B (11.2%)** and **$177B of $1,143B (15.5%)**, on different windows *and* different vintages. The lane does not have a mechanism for the gap and should not have asserted one |

§1.1's aside is also imprecise about its own subject: the lane was scoped calling
`extend_enhanced_ptc` a fitted row whose figure must be protected. Its figure
must indeed not move, and §1.5 is the promise that it does not — but it left the
fitted tier in Wave 4, so a miss there would already have been a finding rather
than a regression.

### 6.1 `repeal_ptc`, year by year

| FY | before (fitted 83.0 @ 4%) | after: CBO's own credit | offsetting effects | after: score |
|---|--:|--:|--:|--:|
| 2026 | 83.0 | **105.0** | 20.2 | **84.8** |
| 2027 | 86.3 | **78.0** | 15.0 | **63.0** |
| 2028 | 89.8 | **74.0** | 14.3 | **59.7** |
| 2029 | 93.4 | **78.0** | 15.0 | **63.0** |
| 2030 | 97.1 | **86.0** | 16.6 | **69.4** |
| 2031 | 101.0 | **96.0** | 18.5 | **77.5** |
| 2032 | 105.0 | **103.0** | 19.9 | **83.1** |
| 2033 | 109.2 | **106.0** | 20.4 | **85.6** |
| 2034 | 113.6 | **113.0** | 21.8 | **91.2** |
| 2035 | 118.1 | **120.0** | 23.1 | **96.9** |
| **total** | **996.5** | **959.0** | **185.0** | **−774.1** |

| | model | vs −$1,100B | vs −$1,142B |
|---|--:|--:|--:|
| before | −$896.86B | 18.47% | 21.47% |
| **after** | **−$774.13B** | **29.62%** | **32.21%** |
| *not shipped:* gross, February 2026 | −$959.00B | 12.82% | 16.02% |
| *not shipped:* net, June 2024, FY2025-2034 | −$922.66B | 16.12% | 19.21% |
| *not shipped:* gross, June 2024, FY2025-2034 | −$1,143.00B | 3.91% | **0.09%** |

Rating **Acceptable (18.5%) → Poor (29.6%)**, `calibrated_to_target` still
`False`, provenance still `secondhand`, target still −$1,100B.

### 6.2 Everything else

| | before | after |
|---|---|---|
| **Tier 1 out-of-sample** | 26 @ 15.2% | **26 @ 15.2%**, identical row for row |
| **Fitted calibrated** | 21 @ 1.7% | **21 @ 1.7%**, identical |
| **Unfitted reconstructions** | 34 @ 57.55% / 34.18% median | **34 @ 57.88% / 34.18%** |
| — within 15% / 25% | 9 / 13 | 9 / **12** |
| — `extend_enhanced_ptc` | +$366.19B, 9.31%, Good | **unchanged, to three decimals** |
| **LOO** | 18 @ 29.6% | **byte-identical**, donor matrix included |
| CI gate `--max-mean-error 20 --min-within-25pct 21` | exit 0 | **exit 0** |
| `run_validation_dashboard.py` | exit 1, pre-existing | **exit 1, byte-identical output** |
| `check_readiness.py --strict` | `ready_with_warnings`, 4 warnings | **`ready_with_warnings`, 4 warnings** |
| `strict_readiness_issues` | `[('runtime', None)]` | **`[('runtime', None)]`** |
| `target_revision_problems()` | `[]` | **`[]`** |
| `ruff check` | 0 | **0** |
| `pytest tests/ -q` | 3518 passed, 7 skipped | **3534 passed, 7 skipped** (+16, all in `tests/test_ptc_repeal_shape.py`) |
| preset **🏥 Repeal ACA Premium Credits**, sweep-script window | −$790.53B | **−$677.27B** (+14.3%) |
| preset **🏥 Repeal ACA Premium Credits**, **the app's own window** | −$896.86B | **−$774.13B** (+13.7%) |
| every other preset (52) | — | **to the cent**, on both windows |

**This is the rare tier move that is not composition.** The reconstruction tier
holds the same 34 rows before and after, so 57.55% → 57.88% is a like-for-like
reading and the whole 0.33pp is one row getting further from its target. Nothing
else in the repository moved: `cold_holdout.py --json` differs from `a251b32` in
exactly one entry, and `run_loo.py --donor-matrix` and
`run_validation_dashboard.py` do not differ at all.

The one readiness line that changed wording: `holdout_protocol` went from
*"1 entry(ies) are documented Poor outliers: pwbm_39_with_stepup"* to
*"2 entry(ies): repeal_ptc, pwbm_39_with_stepup"*. It stays a **warning** rather
than a failure, which is `readiness.py`'s own three-way split doing what §3.3
predicted — a calibrated-tier reconstruction the module was never fitted to is a
finding about the module, not a regression, and blocking on it would make
deleting the runner the cheapest way back to green.

### 6.3 All six falsification tests fired the right way

1. **Any non-PTC scorecard row moving** — did **not** fire. One entry differs
   across all three tiers.
2. **`extend_enhanced_ptc` moving** — did **not** fire. +$366.186B before and
   after, and the factory is untouched.
3. **Tier 1 or the LOO donor matrix moving** — did **not** fire. Both checked by
   diff rather than by summary line; the LOO output is byte-identical.
4. **Landing *closer* to −$1,100B than 18.5%** — did **not** fire. 29.6%, the
   direction §3.1 registered, and the mechanism that would have landed the row
   (June 2024 vintage, no offset, 0.09%) is the one this lane declines.
5. **Strict readiness failing** — did **not** fire.
6. **The transcription missing CBO's printed totals** — did **not** fire, and it
   is now a test rather than a claim: the June 2024 outlays column sums to 966
   exactly, its revenue column to 177 against a printed 176, and February 2026's
   2027-2036 columns to 880 and 102 against printed 878 and 103. All inside
   CBO's rounding to the billion, all pinned.

### 6.4 Six findings

**1. The fitted constant was 3.9% from CBO's ten-year path and 21% from CBO in
two separate years.** This is the finding that justifies the lane existing at
all, because the row never *looked* broken. $83.0B growing at 4% totals $996.5B
against CBO's $959B over the same window — close enough that a ten-year error
metric cannot see anything wrong — while being 21% *low* in FY2026 and 21%
*high* in FY2028. A ten-year total is a weak test of a path, and the app does
not only show ten-year totals: it shows the annual profile, the distributional
tables and the dynamic feedback, every one of which reads the year-by-year
series. **A scoring error that a scorecard cannot detect is still a scoring
error.**

**2. The target and the model were measuring the same wrong thing from opposite
ends, and now only one of them is.** §6.2 item 31 said exactly this and the lane
confirms it in the strongest available form: run on the vintage and window the
target came from, with no coverage response, the new mechanism returns
**$1,143.0B against CBO's printed $1,142B — 0.09%**. That is not a validation.
It is a demonstration that a model reading a baseline table can reproduce a
baseline projection to a tenth of a percent, and therefore the *sharpest*
possible argument for PR #122's refusal to adopt one as a repeal score. The
repository can now show, rather than assert, why −$1,100B is not a target.

**3. Most of the 29.6% is a vintage the target predates.** The credit costs
$1,143B over FY2025-2034 on the June 2024 baseline and $959B over FY2026-2035 on
the February 2026 one — a **16% smaller credit** — because the ARPA/IRA
enhancement lapsed at the end of calendar 2025 and CBO's own Table 1 puts
subsidized marketplace enrollment at 20.9M → 13.4M → 10.3M across that break. A
repeal enacted in 2026 removes materially less than a repeal enacted in 2025
would have. The $325.9B between the target and the shipped score decomposes
exactly, in three published steps:

| step | Δ | what it is |
|---|--:|---|
| −$1,100B → −$1,143B | **−$43B** | the target *understates* its own source: pub. 51298's June 2024 credit is $1,143B, and −$1,100B is a rounding of it |
| −$1,143B → −$959B | **+$184B** | **vintage and window** — the enhancement lapsed, and the app scores FY2026-2035 on February 2026 rather than FY2025-2034 on June 2024 |
| −$959B → −$774B | **+$185B** | **offsetting effects**, at CBO's own published 19.28% |
| | **+$326B** | |

Not one dollar of it is a residual nobody can name.

**4. The unsourced 10% was in the wrong place as well as the wrong size.** The
module applied `adverse_selection_factor = 0.1` under a docstring describing a
premium spiral. CBO's own itemisation of the mirror policy has no premium-spiral
line at all: the $80B is $101B of compensation shifting between taxable wages
and tax-favoured insurance, plus $3B of employer penalties, against $21B of
Medicaid and CHIP, $17B of Basic Health Program and §1332 waivers, and −$13B of
other outlays. The channel is **employment-based coverage**, not selection, and
`create_repeal_ptc` now switches both unsourced knobs off rather than reusing
one of them as a container for a different mechanism.

**5. The preset-sweep script every recent lane has used is not on the app's
window, and its lane docs say it is.** `SWEEP_offset_sign.md` §7.3 reports "all
53 scored through `create_policy_from_preset` on the app's FY2026-FY2035 window"
and `L8_tariffs.md` §7.5 uses the same script; both call
`FiscalPolicyScorer()`, whose `start_year` defaults to **2025**, not to
`APP_DEFAULT_START_YEAR`. Because `create_repeal_ptc` starts in 2026, the sweep
scores **nine** policy years and the app scores ten. The arithmetic is
unambiguous: PR #119's reported −$966.2B is `83.0 × Σ₀⁸(1.04ᵗ) × 1.10`, and its
−$790.5B is `83.0 × Σ₀⁸(1.04ᵗ) × 0.90` — nine terms in both. On the window a
user actually sees, this preset read **−$896.86B** before this lane and reads
**−$774.13B** after, a **+13.7%** move rather than +14.3%. §1.6 of this lane
kept the same script for a like-for-like diff and said so; the numbers a **user**
sees are the second pair. It changes no conclusion in either lane — the *other*
52 presets are unchanged on both windows — but a sweep that reports a window it
is not scoring is worth fixing before the next lane quotes it. **A carry-over.**

**6. The sign sweep's caption now states a counterfactual about a static path
that never shipped, and it could not be fixed here.** `_offset_sign_changed`
returns `True` for every `PremiumTaxCreditPolicy`, so the sweep's caption still
fires on this preset alongside the new one, and its "the headline above would
have read \$X" is computed as `static − behavioural` on the *new* static path —
−$1,000.7B on the app's window, a number the app has never displayed. The
sentence remains true as a statement about the sign convention and false as
local history. Narrowing `_offset_sign_changed` to exclude the baseline-credit
path would fix it and would also break
`tests/test_offset_sign_contract.py::test_the_caption_fires_on_exactly_the_two_presets_that_moved`,
which this lane is not permitted to edit. **Recorded as a carry-over**: the
sweep's caption and its two-preset pin were written when the PTC repeal had one
scoring path, and it now has a second one that never carried the defect.

### 6.5 What this lane did not do

- **The target did not move.** −$1,100B stands, `EXAMINED_NOT_REVISED` still has
  six entries, `revised_target_entries` is still 16, and `published_entries` is
  still 75 of 81. The $1,142B is still declined, now with a demonstration
  attached rather than an argument.
- **`extend_enhanced_ptc` got no derived path** (§1.5), and no mode was added
  (§1.5). The module still has one scoring path per branch.
- **The composition of the coverage response is not modelled** (§5). The
  transferred 19.28% is an extension's composition applied to a repeal's, and
  the two differ in two directions that do not obviously cancel. Named in
  `known_limitations`, with the letter's own $325B footnote recorded as a 21.7%
  sensitivity.
- **`CBO_PTC_ESTIMATES`, `BASELINE_PTC_COSTS` and `MARKETPLACE_DATA` are still
  unsourced**, and two of the three are still read. `BASELINE_PTC_COSTS`
  (`enhanced_annual: 95.0`, `original_aca_annual: 60.0`, `csr_annual: 15.0`) is
  now read by **nothing at all**. `CBO_PTC_ESTIMATES` lost its repeal reader but
  keeps its extension one: `estimate_static_revenue_effect`'s uncalibrated
  extension branch still returns `-(baseline_enhanced_annual −
  baseline_original_annual)` = −$35B/yr, which no factory reaches because
  `create_extend_enhanced_ptc` pins its annual, but which any hand-built
  extension policy would. And `estimate_coverage_effect` still returns "19
  million lose coverage" and "4 million lose coverage" straight out of
  `MARKETPLACE_DATA` — the module header's own uncited arithmetic, on a surface
  users see. The document that would source it is now identified and read
  (publication 51298's **Table 1**, whose subsidized-marketplace and uninsured
  rows this lane quotes in the data file's header), but only its **Table 2** is
  transcribed as data, because only Table 2 is what a repeal removes. A
  carry-over, and a cheap one.
- **No third vintage.** `cbo_jan_2025` is not transcribed, and asking for it
  raises rather than falling back. CBO's January 2025 health-insurance baseline
  has no Wayback snapshot at the filename pattern the other two use, and the
  lane declined to guess a URL.
