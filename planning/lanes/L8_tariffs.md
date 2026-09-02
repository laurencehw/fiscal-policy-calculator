# Lane L8 — Tariffs: pass-through, retaliation, and the income/payroll offset

*Wave 3 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §3 L8.
Opened 2026-09-02 on `model/l8-tariffs`, branched from `main` @ `7f25bed`
(after PR #96).*

Pre-registration first (§1.3): this file states the errors before the lane opens
`fiscal_model/trade.py` and what it expects afterwards. The outturn is appended
in the lane's last commit. Nothing below is a promise of attainment — §1.5
forbids that — and every number in §4 was computed by hand from the published
figures and the Census aggregates in §5 **before a line of module code
changed**, so a reader can check whether the mechanism behaved as the lane said
it would.

**Owner Decision 6 binds this lane**: the gross→net change moves shipped tariff
preset numbers by roughly 40–50%, and it ships **with** its user-facing note in
the same PR.

## 1. Starting point (measured on `7f25bed`)

`python scripts/run_validation_dashboard.py` and the Trade runner
(`validate_all_trade`), which reads its targets out of `CBO_SCORE_MAP` so the
app and the scorecard can never disagree:

| Row | Target | Model | Error | Fitted? |
|---|---:|---:|---:|---|
| `trump_universal_10` | −$2,000.0B | −$2,021.6B | **1.1%** | yes (`universal_coverage_rate`) |
| `trump_china_60` | −$500.0B | −$531.1B | **6.2%** | yes (`china_effective_coverage`) |
| `auto_tariff_25` | −$100.0B | −$252.3B | **152.3%** | no |
| `steel_tariff_25` | −$60.0B | −$103.9B | **73.2%** | no |
| `reciprocal_tariffs` | −$1,200.0B | −$2,736.0B | **128.0%** | no |

The app path (`create_policy_from_preset` → `FiscalPolicyScorer`) returns the
same five numbers to the decimal, so these are also the numbers a user sees.

Tier aggregates on the same commit:

- **Out-of-sample (Tier 1): 25 cases, 31.3% mean, 13/25 within 15%, 18/25 within
  25%.** No tariff case is in it, and none should move.
- **Fitted calibrated: 55 rows, 15.4% mean, 43/55 within 15%.** Two of the 55
  are `trump_universal_10` and `trump_china_60`.
- **Unfitted reconstructions: 24 rows, 72.1% mean, 40.0% median** — of which the
  **12 sectoral presets are 104.8% mean / 40.0% median** (mass 1,257.6) and the
  other twelve (8 P.L. 119-21 line items, 3 capital-gains rows, the revised AMT
  row) 39.3%.
- **Leave-one-out: 17 derivable, 32.3% mean, 19.2% median, 8/17 within 15%,
  5 not cross-validatable.** No tariff module is in it.
- The nine sectoral rows this lane does **not** touch carry **904.7** of the
  12-row subset's 1,257.6 of mass (international 17.8 / 15.0 / 23.5 / 41.0,
  pharma 25.7 / 39.0 / 646.2, enforcement 82.3, climate 14.2). That is a
  **75.4% floor** on the 12-row sectoral mean no matter what this lane does.

## 2. What the lane changes

Six things, in `fiscal_model/trade.py` plus one vendored data file. None of them
is a constant keyed to a benchmark.

**(a) There is no income-and-payroll offset at all.** `estimate_static_revenue_effect`
returns gross customs revenue with a flat 5% avoidance haircut and stops. JCT,
CBO and Treasury all score an indirect tax **net of a ~25% income-and-payroll
offset**, on the convention that a policy change does not alter total nominal
income: duty paid is income not paid to labour and capital, so the income and
payroll tax bases shrink. The lane subtracts it.

**(b) `pass_through_rate = 0.60` and `retaliation_rate = 0.30` feed only display
paths.** `estimate_consumer_cost` and `estimate_retaliation_cost` are read by
`get_trade_summary` and by nothing that reaches a score. The lane routes the
import-demand response through a **border** pass-through frozen at **1.00**
(near-complete: Amiti, Redding & Weinstein 2019; Fajgelbaum, Goldberg, Kennedy &
Khandelwal 2020 — the duty-inclusive US import price rose one-for-one and
foreign export prices did not fall), and converts the export loss from
retaliation into lost federal receipts at the app's own
`MARGINAL_REVENUE_RATE = 0.25`. The 0.60 stays as the separate **retail**
pass-through the household-cost display needs, which is a different object and a
lower number (Cavallo et al. 2021).

**(c) The retaliation export base was total US exports for every policy.**
`estimate_retaliation_cost` multiplied `retaliation_rate × rate × $2,100B` even
for a $50B steel tariff, which implied retaliation losses larger than the whole
tariff base. The lane gives `TariffPolicy` an explicit
`retaliation_export_base_billions`: US goods exports **to the targeted country**
where the policy names one, and total goods exports scaled by the affected
import share otherwise. One rule, no per-case values.

**(d) The base is the exclusive rate applied to a hand-written import level.**
Two corrections. First, a conventional estimate holds nominal income fixed, so
the duty is the **tax-inclusive** rate on the base: `base × τ/(1+τ)`, not
`base × τ` (Tax Foundation FF861 p. 4 and n. 10, citing JCT JCX-58-23). Second,
every level in `TRADE_BASELINE` is replaced by a 2024 Census measurement (§5).

**(e) Two fitted coverage constants, and a per-case elasticity.**
`universal_coverage_rate = 0.70` and `china_effective_coverage = 0.50` are
fitted to their own benchmarks — the Trade runner says so on the entry. The lane
re-derives the first from Census import values by partner and **deletes** the
second, replacing it with the incremental-rate identity (a 60% tariff on China
raises the rate by 60pp *minus the duty already collected*, applied to the whole
base — not by 40pp applied to half of it). `create_trump_china_60`'s
`import_elasticity=-0.7` override is deleted too: §4 forbids per-case
elasticities. One frozen value, module-wide, cited (§3).

**(f) `create_steel_tariff_25` applies the full 25pp with no netting of the
Section 232 duties already in force**, and `create_reciprocal_tariffs`
hard-codes a `0.5` coverage literal. Both fixed; the literal moves into
`TRADE_BASELINE` as `reciprocal_coverage_rate`.

Also: **`CBO_TRADE_ESTIMATES` is deleted, not cited.** It is unread by any code
path, none of its three figures is a CBO estimate (its own `source` fields say
Tax Foundation, Tax Foundation and CRFB), and all three duplicate targets that
already live in `CBO_SCORE_MAP` — so it is a shadow copy of the targets under a
name that asserts a provenance `benchmark_sources.py` has already established
those figures do not have. `TRADE_VALIDATION_SCENARIOS` at the foot of the same
file goes with it for the same reason: it is a second, staler shadow copy, and
the live registry is `validation/scenarios.py`'s
`TRADE_VALIDATION_SCENARIOS_COMPARE`.

## 3. The frozen parameter set

One value per mechanism, cited, applied to every tariff policy. Nothing here is
keyed to a benchmark id.

| Parameter | Value | Source |
|---|---:|---|
| Border pass-through to duty-inclusive import prices | **1.00** | Amiti, Redding & Weinstein (2019) *JEP* 33(4); Fajgelbaum et al. (2020) *QJE* 135(1); Amiti, Redding & Weinstein (2020) *AEA P&P* 110 |
| Import-demand elasticity | **−0.997** | Ghodsi, Grübler & Stehrer (2016), binding weighted-average for the United States, as adopted by Tax Foundation FF861 p. 4; USITC pub. 5405 finds ≈−1 in the first year of the 2018-19 tariffs |
| High-rate elasticity multiplier above 30pp | **2.0** (unchanged) | Boehm, Levchenko & Pandalai-Nayar (2023) *AER* 113(4): −0.76 in year 1 converging to −1.75/−2.25 within 7-10 years; USITC pub. 5405: "more than −2" by the end of year 2 |
| Duty avoidance / evasion | **0.05** (unchanged) | Module default; FF861 uses 8% noncompliance from the IRS tax gap, so this is the conservative end |
| Income-and-payroll offset | **0.25** | The longstanding CBO/JCT/OTA convention. FF861 p. 4 n. 3 cites JCT, *The Income and Payroll Tax Offset to Changes in Excise Tax Revenues* (Dec. 23, 2011, JCX-59-11) and n. 11 cites JCX-9-24 for 2024-2034; Tax Foundation's own calculator gives **26.2%** averaged over this window (FF861 p. 4) |
| Retaliation intensity | **0.30** (unchanged) | Module default |
| Federal receipts per dollar of lost export income | **0.25** | `constants.MARGINAL_REVENUE_RATE`, the app's own convention |

**The offset is cited secondhand and this lane says so.** `jct.gov` and
`cbo.gov` both return HTTP 403 to this environment on every URL, so neither
JCX-59-11 nor JCX-9-24 nor CBO publications 20110/58549 could be read directly.
Tax Foundation FF861 — which *is* reachable, and which is already this
repository's transcribed benchmark source for `trump_universal_10` — states the
convention, cites both JCT documents for it, and reports 26.2% for the
2025-2034 window. The lane uses the round **25%** convention rather than
FF861's 26.2%, because 26.2% is Tax Foundation's own calculator output for the
window and adopting it would move a parameter toward one of the benchmarks. The
difference is 1.6% of gross either way.

## 4. Pre-registered expectations

### 4.1 The plan's registered target (§3 L8)

> `auto_tariff_25` 152.3%, `reciprocal_tariffs` 128.0%, `steel_tariff_25` 73.2%
> → **all <40%**.

### 4.2 This lane's own derived expectation — and where it differs

Hand-computed from §3 and §5 before any code change:

```
Δτ      = stated rate − duty already collected on the base
p       = 1.00 × Δτ                                    (border pass-through)
V       = 1 + (−0.997)·p                               for p ≤ 0.30
        = 1 + (−0.997)(0.30) + (p−0.30)(−0.997)(2.0)   above it, floored at 0.20
gross   = base · V · Δτ/(1+Δτ)                         (tax-inclusive rate)
avoid   = 0.05 · gross
offset  = 0.25 · (gross − avoid)
retal   = 0.25 · [0.30 · Δτ · export base]
net     = gross − avoid − offset − retal
```

| Row | Target | Before | Expected after | Expected error |
|---|---:|---:|---:|---:|
| `trump_universal_10` | −$2,000.0B | −$2,021.6B / 1.1% | **≈ −$1,258.5B** | **≈ 37.1%** |
| `trump_china_60` | −$500.0B | −$531.1B / 6.2% | **≈ −$278.4B** | **≈ 44.3%** |
| `auto_tariff_25` | −$100.0B | −$252.3B / 152.3% | **≈ −$182.3B** | **≈ 82.3%** |
| `steel_tariff_25` | −$60.0B | −$103.9B / 73.2% | **≈ −$52.9B** | **≈ 11.9%** |
| `reciprocal_tariffs` | −$1,200.0B | −$2,736.0B / 128.0% | **≈ −$1,396.8B** | **≈ 16.4%** |

**Two of the plan's three rows are expected to land under 40%; `auto_tariff_25`
is not, and the lane says why before it starts.** The −$100B target implies
about $10B/yr. Census 2024 puts HS-87 (vehicles and parts) imports at $384.9B,
of which $186.4B — 48.4% — comes from Canada and Mexico. Even carving all of
that out leaves a $198.5B base, and $10B/yr of *net* receipts off that base
would need a volume collapse the elasticity literature does not support.
`benchmark_sources.py` already records that the −$100B is untraceable (CRFB, its
stated source, itemises no auto figure in any of four posts) and that the two
located primary estimates are **Tax Foundation's $386.2B conventional** and
**Yale Budget Lab's $600-650B**, 4-6.5× above the carried target. The expected
−$182.3B moves *toward* both of them while its percent error against the carried
figure stays above 40%. That is the row reporting a target problem, not a
modelling one, and §1.6 sends target problems to the provenance lane.

**Two rows are expected to get worse, and that is the point.**
`trump_universal_10` at 1.1% and `trump_china_60` at 6.2% are bookkeeping: the
Trade runner already flags both `calibrated_to_target=True` and its
`known_limitations` say in as many words that the 70% and 50% coverage constants
are fitted to reproduce those figures. Once the constants are Census
measurements and the score is net, both rows show their real error. Their
`calibrated_to_target` flags must therefore flip to `False` — after this lane no
`TRADE_BASELINE` constant is fitted to any target — which moves two rows out of
the fitted tier and into the reconstruction tier.

### 4.3 Tier arithmetic, stated both ways

Composition changes flatter tiers on their own; §2.3 of the plan is explicit
that a mean which moves because the population moved has not improved. So both
populations are pre-registered:

| Aggregate | Before | Expected after |
|---|---:|---:|
| Three unfitted trade rows, summed error | 353.5 | **≈ 110.6** |
| All five trade rows, summed error | 360.8 | **≈ 192.0** |
| **12-row sectoral mean** (constant population) | **104.8%** | **≈ 84.6%** |
| 14-row sectoral mean (with the two reclassified rows) | — | ≈ 78.3% |
| **24-row reconstruction mean** (constant population) | **72.1%** | **≈ 62.0%** |
| 26-row reconstruction mean (with the two reclassified) | — | ≈ 60.3% |
| Fitted calibrated | 55 @ 15.4% | **53 @ ≈15.8%** |
| Out-of-sample (Tier 1) | 25 @ 31.3% | **unchanged** |
| Leave-one-out | 17 @ 32.3% | **unchanged** |
| Distributional | 7 @ 0.00–3.96pp | **unchanged** |

The fitted tier gets *worse* by construction here: removing two rows that scored
1.1% and 6.2% raises the mean of what is left. Reporting the reconstruction
tier's fall without that is the composition trick §2.3 names.

### 4.4 Two out-of-sample cross-checks the lane will report

Neither is a benchmark and neither is fitted to; both are published quantities
the new channels can be checked against.

1. **Net as a share of gross.** The repository's own knowledge snapshot
   (`assistant/knowledge/tariff_scoring_methodology.md`) puts a fully-netted
   tariff score at **40–50% of gross** customs revenue, that chain including a
   GDP-feedback drag this module does not model. The expected net/gross ratios
   are **0.60–0.66**, which is where a score that stops short of general
   macro feedback should sit — above the snapshot's band, not below it.
2. **Retaliation.** FF861 p. 2 estimates that in-kind retaliation to a 10%
   universal tariff reduces federal revenue by **$278B** over ten years. The
   module's expected figure is **$111.4B** — 2.5× smaller. The gap is the
   channel's known limitation: an export-value loss is not an income loss, and
   nothing here carries a multiplier or a supply-chain effect.

### 4.5 What would falsify the lane

- Any Tier 1, leave-one-out, or distributional number moving at all. The diff
  touches `trade.py`, one data file, the Trade scenarios' metadata, and one UI
  caption; no case in those tiers is a tariff.
- Any of the nine untouched sectoral rows moving.
- A trade row landing far from §4.2's hand arithmetic — that would mean the
  implementation is not the mechanism this file describes.
- The net/gross ratio landing **below** 0.50, which would mean the module is
  now double-counting the offset against the avoidance haircut or the
  retaliation channel.

## 5. Data transcribed

All figures land in `fiscal_model/data_files/trade/census_trade_2024.csv` with a
provenance header. Source: **U.S. Census Bureau, USA Trade Online / Census API,
`timeseries/intltrade/imports/hs` and `.../exports/hs`, 2024 annual
(year-to-date through December 2024), retrieved 2026-09-02.** Imports are
general imports at customs value (`GEN_VAL_YR`); effective duty rates are
calculated duty over imports for consumption (`CAL_DUT_YR / CON_VAL_YR`), which
includes the Section 232 and Section 301 duties actually collected — China's
10.93% against a ~2.4% world average is that showing up. Exports are total
exports (`ALL_VAL_YR`). This is the same source Tax Foundation FF861 p. 3 n. 4
builds its baseline from (it cites USITC DataWeb, which republishes the Census
series).

| Quantity | Derived value | Constant it replaces |
|---|---:|---|
| US goods imports, 2024 | **$3,263.9B** | `total_imports_billions` 3,200.0 |
| US goods exports, 2024 | **$2,063.0B** | `total_exports_billions` 2,100.0 |
| Average duty collected, all imports | **2.36%** | `current_avg_tariff_rate` 0.03 |
| Customs duties collected | **$76.6B** | `current_tariff_revenue_billions` 80.0 |
| Imports from China | **$440.3B** | `china_imports_billions` 430.0 |
| Duty collected on China imports | **10.93%** | `china_existing_avg_tariff` 0.20 |
| US goods exports to China | **$143.3B** | *(new — China's retaliation base)* |
| Imports from Canada + Mexico, share of total | **28.03%** | — |
| ⇒ universal-tariff coverage, 1 − USMCA share | **0.7197** | `universal_coverage_rate` 0.70 (fitted) |
| HS-87 vehicles and parts imports | **$384.9B** | `auto_imports_billions` 380.0 |
| Duty collected on HS-87 | **1.99%** | `auto_existing_avg_tariff` 0.025 |
| HS-87 imports from Canada + Mexico, share | **48.42%** | `auto_usmca_exempt_share` 0.65 |
| HS-72 + HS-76 (steel + aluminium) imports | **$58.9B** | `steel_aluminum_imports_billions` 50.0 |
| Duty collected on HS-72 + HS-76 | **3.06%** | *(new — the Section 232 netting)* |
| — | — | `china_effective_coverage` 0.50 **deleted** |

**Three honest caveats on the derivations**, recorded here rather than
discovered later:

- **The universal coverage rate is the USMCA carve-out, and FF861 does not
  apply one.** Tax Foundation's $2,171.1B scores a 10% tariff on the *whole*
  $3.35T goods base. Every universal tariff actually proposed or imposed has
  exempted USMCA-qualifying Canadian and Mexican goods, which is what 1 − 28.03%
  measures. Keeping the carve-out is the right model of the policy and is one
  named reason the row will not reproduce the benchmark.
- **The auto USMCA share over-states the carve-out.** The March 2025
  proclamation exempts only the *US-content* share of USMCA-qualifying
  vehicles, not the whole import value, so the true base is larger than
  $198.5B and the expected −$182.3B is if anything low.
- **HS-72 + HS-76 is a proxy for "steel and aluminium".** Section 232 also
  reaches derivative products in HS-73 ($49.6B, 5.63% collected), which are
  excluded here; including them would roughly triple the base.

## 6. Scope: what this lane does not touch

`scripts/cold_holdout.py`, `scripts/run_loo.py`, `loo.py`,
`tests/test_preregistration.py`, the CI thresholds, `KNOWN_SCORES`,
`CBO_SCORE_MAP`'s figures, `preregistered.py`, `benchmark_sources.py`,
`target_revisions.py`, and the shared docs. No preset **label** changes: every
tariff label quotes the *official* score (−$2T, −$500B, −$100B, −$60B, −$1.2T),
not the model's, and this lane touches no official figure — so
`preset_ids.py`'s label/id twins are untouched and the test that pins them
still passes on the same strings.

The steel target is carried at −$60B and neither of the repository's two
figures for it is traceable (`benchmark_sources.py`). The error above is
measured against −$60B because that is what is carried; it is not a claim that
−$60B is right.

## 7. Outturn

*Appended by the lane's last commit.*
