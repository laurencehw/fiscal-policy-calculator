# L2 — budget-authority → outlay spend-out

*Wave 1 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §3 L2.
Pre-registered 2026-09-01 against `main` @ `cff6b88`, **before** any code in this
lane changed. The outturn is appended at the bottom as the lane's last commit.*

## 1. What is missing

`SpendingPolicy.get_spending_in_year` (`policies_core.py:568-581`) returns
`level x 1.02**t` and `ScoringEngine._score_spending_policy` books that straight
into `static_spending_effect`. Budget authority becomes an outlay in the year it
is provided. `grep -rn 'spend_out\|outlay_rate' fiscal_model/` returns nothing.

Seven Tier-1 rows run through that one defect, carrying **509 of the tier's
1,315 units of error mass (38.7%)** — the largest single mass in the tier.

## 2. Starting point — the 25-case battery on `cff6b88`

`python scripts/cold_holdout.py --json`, run before any edit:

| tier | n | mean | median | within 15% | within 25% |
|---|--:|--:|--:|--:|--:|
| out-of-sample (Tier 1) | 25 | **52.6%** | 21.1% | 8 | 14 |
| calibrated reference (fitted) | 34 | 2.7% | 0.2% | 33 | 34 |
| uncalibrated reconstruction | 20 | 250.8% | 43.1% | 4 | 7 |

`python scripts/run_loo.py --donor-matrix`: 18 derivable, **59.3%** mean,
35.6% median, 6/18 within 15%, 4 not cross-validatable.

The eight rows this lane's mechanism touches, at their current errors:

| policy_id | official ($B) | model ($B) | abs err |
|---|--:|--:|--:|
| `iija_2021_discretionary` | 415.4 | 1894.0 | **355.9%** |
| `cbo_opt43_state_local_grants` | −66.7 | −117.1 | **75.5%** |
| `cbo_opt38_national_service` | −10.3 | −12.7 | 23.1% |
| `cbo_opt37_international_affairs` | −187.0 | −224.4 | 20.0% |
| `cbo_opt42_nondefense_discretionary` | −339.0 | −399.9 | 18.0% |
| `cbo_opt39_pell_eligibility` | −22.1 | −24.4 | 10.3% |
| `ssfa_wep_gpo_repeal_outlays` | 195.7 | 215.4 | 10.1% |
| `fra_2023_discretionary_caps` | −1331.8 | −1254.2 | 5.8% |

## 3. The mechanism this lane adds

`outlays_t = Σ_k s_k · BA_{t−k}`, with `s` a first-year/out-year profile keyed
by **account class** — the thing that actually governs how fast an obligation
becomes a disbursement, and the taxonomy CBO and OMB both describe (pay and
benefits disburse at once; construction and capital take years). Budget
authority and outlays become distinct quantities on the policy and on the
result. Nothing about any case's pre-registered *shape input* changes: every
`annual_amount_billions` stays exactly what `PHASE_D_SPENDING_LEVEL_RULE` and
the Phase B option extraction set.

## 4. Pre-registered expectation

**Derived arithmetically before the fact**, by multiplying each row's current
model total by the 10-year in-window outlay/BA ratio its assigned class implies
for a level path grown at 2%/yr. Predicted errors are therefore *predictions*,
not fitted results; the outturn section records where they were wrong.

Class ratios for a level 10-year path (donor-fitted, §5): personnel 0.991,
mandatory 0.998, operations 0.893, grants/procurement 0.848, construction 0.663.

| policy_id | class assigned | before | **predicted after** | direction |
|---|---|--:|--:|---|
| `iija_2021_discretionary` | construction_and_capital | 355.9% | **~200%** | ↓ ~155pp |
| `cbo_opt43_state_local_grants` | construction_and_capital | 75.5% | **~16%** | ↓ ~59pp |
| `cbo_opt38_national_service` | grants_and_procurement | 23.1% | **~5%** | ↓ ~18pp |
| `cbo_opt37_international_affairs` | grants_and_procurement | 20.0% | **~2%** | ↓ ~18pp |
| `cbo_opt42_nondefense_discretionary` | grants_and_procurement | 18.0% | **~0%** | ↓ ~18pp |
| `cbo_opt39_pell_eligibility` | grants_and_procurement | 10.3% | **~6%** | ↓ ~4pp, sign flips to under |
| `ssfa_wep_gpo_repeal_outlays` | mandatory_benefit | 10.1% | **~10%** | unchanged — *not* a spend-out case |
| `fra_2023_discretionary_caps` | operations_and_support | 5.8% | **~16%** | **↑ ~10pp — a regression, expected** |

**Tier 1 as a whole: 52.6% → ~42%** (mean), within-15 8 → ~10, within-25
14 → ~15. **LOO 59.3% and the 20-case reconstruction mean 250.8% must not move
at all** — no calibrated module and no sectoral preset is a `SpendingPolicy`.

Two entries above are the honest part of the prediction:

- **`fra_2023_discretionary_caps` is pre-registered to get worse.** Its 5.8% is
  not accuracy. `validation/core.py`'s own note already says so: CBO's outlay
  path runs −$64.1B in 2024 against −$112.3B of budget authority and reaches
  −$159.7B by 2033 against the model's ~−$134B, so the model over-predicts the
  early years and under-predicts the late ones and the two errors cancel over
  ten years. Any correct spend-out removes the first error and leaves the
  second, so the total error *rises* while the path gets more right. A lane
  that quietly kept 5.8% by exempting this row would be fitting.
- **IIJA stays the largest row in the tier.** Spend-out is only half of its
  defect; the other half is that a level shape cannot end a five-year
  authorization. Closing that means giving IIJA a humped budget-authority path,
  which is a change to a *pre-registered shape input* — out of this lane's
  remit (`preregistered.py` and `cbo_scores.py` are both off-limits here). The
  machinery to carry such a path ships anyway, tested and unused by validation.

## 5. Data and provenance — the fallback shipped, and why

**Owner Decision 2 named OMB Circular A-11 §32 outlay rates as the primary
source. That source does not exist as described**, and this is a finding, not a
fetch failure:

- **A-11 §32 is "Personnel Compensation, Benefits, and Related Costs."** Checked
  in both the 2016 edition
  (`obamawhitehouse.archives.gov/sites/default/files/omb/assets/a11_current_year/s32.pdf`)
  and the current table of contents. It contains no outlay rates of any kind.
- **A-11 publishes no numeric outlay-rate table in any section.** §80
  ("Development of Baseline Estimates") requires only that new budgetary
  resources "outlay at a rate that is consistent with Presidential policy
  spendout rates"; §81 ("Policy and Baseline Estimates of Budget Authority,
  Outlays, and Receipts") requires *agencies* to enter their own account-level
  "outlay rates that apply to BA or limitations provided in the CY and beyond"
  into MAX. The rates are agency-supplied and unpublished.
- **CBO does publish account-level spendout rates** (publications 61913 and
  62256, the discretionary-outlay interactive tools), but `cbo.gov` returns
  HTTP 403 to this environment on every URL including `system/files`, and
  `web.archive.org` is not reachable either. Transcribing them is the obvious
  follow-up for whoever has network access to cbo.gov.

Decision 2's own fallback clause therefore governs: **the CBO donor options in
the repository's own `cbo_options_2025_2034_alternatives.csv` are the primary
source, and that is what shipped.** The A-11 route stays open as a future
cross-check.

**Donor pool — strictly disjoint from the scored battery.** The CSV carries both
a budget-authority (or spending-authority) row and an `outlays` row for 19 of
the 76 options. Five of those — **37, 38, 39, 42, 43** — are the scored cases.
The remaining 14 are the donor pool, and **no scored option, and no alternative
of a scored option, contributes a single number to any profile.** A test asserts
the disjointness.

Profiles are fitted by non-negative least squares on the pooled donor
convolution `O_t = Σ_k s_k BA_{t−k}`:

| class | donor options (all unscored) | s₀ | Σs |
|---|---|--:|--:|
| `personnel_and_benefits` | 29, 36, 40, 41 | 0.921 | 1.000 |
| `operations_and_support` | 28, 34 | 0.539 | 0.977 |
| `grants_and_procurement` | 32, 33, 35 | 0.405 | 1.000 |
| `construction_and_capital` | 31 | 0.022 | 0.973 |
| `mandatory_benefit` | 3, 9 | 0.977 | 1.000 |

Option 44 (Davis-Bacon repeal) is in the 19 but is **excluded as a donor**: its
outlays exceed its budget authority in every year (10-year ratio 1.52) because
the repeal also cheapens work paid from prior-year balances, so its implied
profile violates `s_k ≥ 0, Σs_k ≤ 1` and is not a spend-out observation.

**Class assignment is a classification, never a fit.** Each case is assigned
from the predominant account type of the programs it funds, as the *source*
describes them — the same discipline `CLAUDE.md` records for the
ordinary-vs-AGI-inclusive base split:

> pay, benefits, allowances, medical-care enrollment → `personnel_and_benefits`
> · agency operations, force structure, O&M, across-the-board discretionary
> caps → `operations_and_support` · project and formula grants, assistance
> awards, student aid, foreign assistance, procurement, R&D →
> `grants_and_procurement` · construction, infrastructure and other capital
> grants → `construction_and_capital` · direct benefit payments outlaid when
> owed → `mandatory_benefit`

No profile rate is keyed to a benchmark id, and no rate was chosen by looking at
the error it produced.

## 6. Rows this lane must not move

Every Tier-1 row that is not a `SpendingPolicy` — the 17 tax, capital-gains,
payroll and corporate cases — must score identically. So must all 34 fitted
calibrated benchmarks, all 20 unfitted reconstructions and all 18 LOO cases.
Any movement there is a bug in the default path, not a result.

## 7. Outturn

*(appended as the lane's last commit)*
