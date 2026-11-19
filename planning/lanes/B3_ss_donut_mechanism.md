# Lane B3: price the Social Security $250K donut from SSA's own wage distribution

*Pre-registered 2026-11-19 against `main` @ `53d7b3a`, in this lane's first
commit, before `fiscal_model/payroll.py` was edited. That commit also adds the
data file the mechanism reads (`data_files/payroll/ssa_net_compensation.csv`),
which no code reads yet and which changes no score. The outturn is appended at
the end, in the last commit.*

Plan: `reviews/cursor-wave1-followups.md` and
`planning/PRIORITY5_AND_CHARTS.md` (the payroll donut item). Under
`planning/MODELING_IMPROVEMENT.md` §1 (pre-register before code, no promise of
attainment) and §4 (no constant retuned to a held-out target).

**Disclosure.** To compute the predictions below I read `payroll.py`,
`scoring_engine.py` and the payroll validation runner (read-only) and ran a
scratch script that evaluates the mechanism in §2 directly from the two SSA
tables and CBO's cap path, outside the engine. That script printed all three
offset columns of §3.2 at once, so the choice in §2.5 was made on concept and
is stated with the alternatives it beat, and their errors, beside it. No module
was changed.

## 1. Starting numbers (`main` @ `53d7b3a`)

| reading | n | mean | median | within 15 | within 25 |
|---|--:|--:|--:|--:|--:|
| Out-of-sample (Tier 1) | 44 | 12.2% | 10.3% | 30 | 39 |
| Calibrated, fitted | 14 | 1.4% | 0.0% | 14 | 14 |
| ... held in place | 25 | 12.8% | 1.1% | 20 | 21 |
| Unfitted reconstructions | 39 | 39.7% | 29.1% | 12 | 16 |
| ... retired held in | 41 | 57.1% | 29.9% | 12 | n/a |

The row this lane exists for: `ss_donut_250k` scores **−$2,700.0B** against
CBO 60557 Option 62 alternative 2's **−$1,426.8B, 89.2%** (target revised
2026-09-11 in PR #145; row in the reconstruction tier since then because its
constant is fitted to the superseded figure). **That 89.2% stays on the record
with its date** — in `scenarios.py`'s limitations, in this file and in the
outturn — and is never described as a fix this lane made: it was the size of
the old target's error, and what replaces it below is a mechanism scored for
the first time.

The shipped preset `ss-donut-250k` prints **−$2,700.0B** on FY2026–2035 today,
the same flat annual ten times.

## 2. The mechanism, fixed here

`create_ss_donut_hole` stops carrying `annual_revenue_change_billions=270.0`.
A policy with a donut threshold and no explicit annual (and no other component)
is scored on a year-indexed base through the engine's existing per-year branch
(`uses_covered_earnings_base`), so the engine passes the fiscal year and grows
nothing itself.

### 2.1 The level: SSA's 2025 distribution

`W(t)`, wages above `t` in a given year, is `A(t) − t·N(t)`, where `N(t)` is
the number of earners at or above `t` and `A(t)` their aggregate net
compensation, both read off SSA's net-compensation table (netcomp.cgi). At a
table boundary that is exact. Between boundaries `N` and `A` are interpolated
log-linearly in `log t` (a locally constant Pareto slope, the rule
`covered_wages_above` already uses). In the open top bracket ($50M and over)
the Pareto index is taken from the bracket's own mean, `α = m / (m − lo)`.

The anchor is **2025**, the latest year SSA publishes. 2024 is not published
("Data for 2024 is not available"). 2023 is used only for the back-test in
§4, never for a score.

At $250,000 in 2025: 5,077,945 earners, $2,693.3B of their net compensation,
**$1,423.9B of wages above $250,000**. The module's fitted band at the same
threshold is $2,177.0B, 53% higher.

### 2.2 The year path

For fiscal year `y`:

```
a_y   = cap(y + 2) / cap(2027)               # AWI growth since 2025
G_y   = covered_earnings(y) / covered_earnings(2025)
E_y   = G_y / a_y                            # growth not explained by AWI
T_y   = max(threshold, cap(y))
base_y = E_y · a_y · W_2025(T_y / a_y)
```

* `cap(y)` is CBO's own taxable-maximum projection, `tp_ss_max_earnings` in
  `cbo_tax_parameters` (publication 53724). The statute indexes the year-`y`
  maximum to the average wage index of year `y − 2`, so `cap(y+2)/cap(2027)`
  is CBO's projected AWI growth from 2025 to `y`. Beyond the schedule's last
  year the last published growth rate is continued.
* `G_y` is the module's existing covered-earnings path (CBO's February 2024
  wage path times the Trustees' covered-earnings ratio). Splitting it into
  `a_y` (wage level, which shifts the whole distribution) and `E_y` (the rest,
  treated as more earners at the same distribution) is the standard uniform
  scaling: the distribution of `wage / AWI` is held at its 2025 shape.
* `T_y` is where the new tax starts. When the taxable maximum passes the
  threshold the donut closes and the policy taxes wages above the cap. On
  February 2026's schedule that happens in CY2035 ($250,500), inside the app's
  window; on February 2024's it does not happen by FY2034.
* The threshold is **not indexed**, which is what Option 62 alternative 2
  states.

Revenue is `0.124 × base_y`, times `first_fiscal_year_share(1) = 0.75` in the
policy's first year (CBO: effective January), the module's existing calendar
identity.

### 2.3 Which cap path

A new field, `PayrollTaxPolicy.cap_schedule_vintage`, in the pattern of
`threshold_schedule_vintage`: `None` reads
`cbo_tax_parameters.DEFAULT_BASELINE_VINTAGE` (February 2026, the app's
vintage). The battery row sets `cbo_feb_2024`, the baseline CBO's December
2024 Options volume was priced on, on FY2025–2034. `covered_earnings` exists
for the February 2024 wage path only, so the app preset reads a February 2026
cap path with a February 2024 wage path. That is stated as a limitation, and
giving the payroll path a vintage is lane B2b, not this one.

### 2.4 Tier

Nothing in the new path is fitted to any target, so the payroll runner reports
the donut with `calibrated_to_target=False` (the precedent is lane L1's three
capital-gains scenarios). It stays in the reconstruction tier, where it already
is; it **leaves the "fitted, held in place" reading**, because there is no
longer a fitted constant to hold in place. That move is composition, it lowers
that reading by about three points, and §3.3 prints it so it cannot be read as
accuracy.

### 2.5 The behavioural offset: the module's own payroll rule, chosen on concept

CBO's Option 62 table carries the note *"An offset to reflect reduced income
and payroll taxes has been applied to the estimates in this table."* The module
already has a rule for exactly that, written for Option 61's new payroll tax:
`new_earnings_tax_offset_share`, a compensation-shifting term
`(rate + τ) · ETI / (1 − τ)` plus a statutory-incidence term `τ · employer_share`.
This lane applies that same rule to the donut, with nothing new:

* `rate = 0.124`, the OASDI rate the donut applies;
* `τ = LABOR_INCOME_MARGINAL_TAX_RATE = 0.31` (CBO pub. 54911), already in the
  module;
* `ETI = 0.25`, the `TaxPolicy` default;
* `employer_share = 0.5`, the statutory split of the 12.4% (6.2% each side).
  Option 62's tax is the existing OASDI tax, half levied on employers, so the
  incidence term is CBO's own "employers would reduce their employees'
  earnings" paragraph from the option the rule was written for.

Offset share **0.3122** of gross. Two alternatives were computed and are
**not** shipped, with the reason:

| column | why not | battery ten-year | error |
|---|---|--:|--:|
| gross (no offset) | contradicts the table note CBO prints | −$2,428.9B | +70.2% |
| incidence term only | drops a channel the module's own rule has | −$2,052.4B | +43.8% |
| **full rule (ships)** | | **−$1,670.5B** | **+17.1%** |

## 3. Predictions

### 3.1 The battery row (`cbo_feb_2024`, FY2025–2034)

| FY | cap | base $B | gross | net |
|---|--:|--:|--:|--:|
| 2025 | 176,100 | 1,424 | 132.4 | 91.1 |
| 2026 | 185,100 | 1,531 | 189.9 | 130.6 |
| 2027 | 191,400 | 1,642 | 203.7 | 140.1 |
| 2028 | 197,700 | 1,763 | 218.6 | 150.3 |
| 2029 | 204,300 | 1,893 | 234.7 | 161.4 |
| 2030 | 211,500 | 2,029 | 251.6 | 173.1 |
| 2031 | 219,000 | 2,172 | 269.4 | 185.3 |
| 2032 | 226,500 | 2,328 | 288.6 | 198.5 |
| 2033 | 234,000 | 2,493 | 309.1 | 212.6 |
| 2034 | 242,100 | 2,669 | 330.9 | 227.6 |

**Central: −$1,670.5B, +17.1% against −$1,426.8B. Band: −$1,590B to
−$1,750B** (±5%, for rounding and for the engine's own path through the
same arithmetic). A score outside the band is reported as a miss, not tuned.

The sign of the residual is predicted to be **over** (the model raises more
than CBO), with the path growing faster than CBO's (about 7% a year against
CBO's $122.0B → $192.0B over 2026–2034, about 5.8%) and a first year well above
CBO's $35.7B.

### 3.2 The shipped preset (`cbo_feb_2026`, FY2026–2035)

Net path 98.2 → 242.6; FY2035 has the donut closed (cap $250,500).
**Central −$1,794.7B** (gross −$2,609.5B, incidence only −$2,205.0B), band
−$1,705B to −$1,885B. The preset moves **−$2,700.0B → about −$1,794.7B**,
−33.5%, and ships with a Decision 6 caption computed from the scored result.
It prints no error against −$1,426.8B on its own window, because that figure
is FY2025–2034 on February 2024's baseline; the badge keeps reading the
battery row.

### 3.3 Tiers

| reading | before | predicted after |
|---|---|---|
| Unfitted reconstructions | 39 @ 39.7%, median 29.1%, 12 ≤15, 16 ≤25 | **39 @ 37.8%**, median 28.4%, 12 ≤15, **17 ≤25** |
| ... retired held in | 41 @ 57.1% | about 41 @ 55.3% |
| Calibrated, fitted | 14 @ 1.4% | unchanged |
| ... held in place | 25 @ 12.8% | **24 @ 9.6%** (composition: the donut leaves, §2.4) |
| Dashboard `Payroll` sub-population | 1 @ 89.2% | 1 @ about 17.1% |
| Out-of-sample (44 rows), per-class gates | 12.2% / 39 ≤25 | **byte-identical** |
| Leave-one-out (`run_loo.py --donor-matrix`) | Payroll 32.3% | identical except the donut's by-construction column |
| OCACT figures on the Social Security page | | **byte-identical**, with a test |

LOO stays identical because its held-out leg sets an explicit annual on the
policy, which keeps the old table path; the 250K point of
`SSA_COVERED_WAGES_ABOVE_BILLIONS` then feeds only LOO and no score. Whether to
replace that table with the SSA tail too is left as an owner question in the
PR, because doing it would move the Payroll LOO module and two other payroll
rows.

**No ten-year target is built from CBO's option.** The target stays
−$1,426.8B; CBO's annual path and first-year figure are used only to describe
the residual, never as an input.

## 4. Back-test and limitations, stated in advance

* **Back-test.** Scaling SSA's 2023 table to 2025 by the same rule (AWI-like
  growth from the raw average wage, 63,932.64 → 69,861.77, and earner growth
  173.7M → 175.6M) predicts $1,309.7B of wages above $250K against SSA's
  actual $1,423.9B, **−8.0%**. The top of the distribution grew faster than
  the average, so uniform scaling from 2025 forward is likely to understate the
  base. Not corrected.
* Self-employment earnings above $250K are taxable under Option 62 (SECA) and
  absent from net compensation, so the base is understated.
* The first-year share of 0.75 overstates FY2025: wages above $250K arrive late
  in the calendar year as earners pass the threshold, and CBO books $35.7B.
* Net compensation includes elective deferrals, which are OASDI wages; it does
  not include all covered-employment adjustments.
* `τ = 0.31` is CBO's economy-wide marginal rate on labour; top earners face a
  higher one, which would raise the offset.
* The model's base grows faster than CBO's annual path implies.

## 5. Falsification

The lane has failed its own test if any of these happen, and the outturn says
so rather than adjusting anything:

1. The battery row lands outside −$1,590B to −$1,750B.
2. Any Tier 1 row, any per-class gate figure or any LOO derived figure moves.
3. The OCACT Social Security figures move.
4. Any payroll row other than `ss_donut_250k` moves, or any preset other than
   `ss-donut-250k`.
