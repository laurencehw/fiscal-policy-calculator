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

*Measured 2026-09-01 on `a186a42`, `python scripts/cold_holdout.py --json`.*

| policy_id | class | before | **predicted** | **after** | vs prediction |
|---|---|--:|--:|--:|---|
| `cbo_opt37_international_affairs` | grants_and_procurement | 20.0% | ~2% | **0.0%** | better |
| `cbo_opt38_national_service` | grants_and_procurement | 23.1% | ~5% | **2.6%** | better |
| `cbo_opt42_nondefense_discretionary` | grants_and_procurement | 18.0% | ~0% | **1.7%** | as named |
| `cbo_opt39_pell_eligibility` | grants_and_procurement | 10.3% | ~6% | **8.1%** | as named |
| `cbo_opt43_state_local_grants` | construction_and_capital | 75.5% | ~16% | **10.8%** | better |
| `ssfa_wep_gpo_repeal_outlays` | mandatory_benefit | 10.1% | ~10% | **9.8%** | as named |
| `fra_2023_discretionary_caps` | operations_and_support | 5.8% | ~16% ↑ | **12.2%** ↑ | regressed, as named |
| `iija_2021_discretionary` | construction_and_capital | 355.9% | ~200% | **290.2%** | **worse than named** |

| tier | n | before | after |
|---|--:|---|---|
| **out-of-sample (Tier 1)** | 25 | 52.6% mean / 21.1% median / 8 within 15 / 14 within 25 | **45.3% / 16.1% / 12 / 15** |
| calibrated reference (fitted) | 34 | 2.7% / 0.2% / 33 / 34 | **unchanged** |
| unfitted reconstruction | 20 | 250.8% / 43.1% / 4 / 7 | **unchanged** |
| leave-one-out | 18 | 59.3% / 35.6% / 6 within 15 | **unchanged** |

**No row moved that this file did not name.** The eight above are the only
rows that changed anywhere in the 79-row scorecard, which is what the
`immediate` default was for.

### Where the prediction was wrong, and why

**IIJA landed at 290.2%, not the ~200% named.** The pre-registered figure
assumed the window would truncate authority at both ends — that the model would
only spend out authority provided inside 2025-2034. It does not, and should not:
the convolution is a property of the policy, so a policy whose `start_year` is
2022 spends its 2022-2024 authority into the window's head. Truncating the head
too would have discarded authority the model's own shape claims to provide, and
would have flattered the result by about 90 points. The choice is documented in
`ScoringEngine._score_spending_policy`; the honest reading is that IIJA's
in-window outlay ratio is 0.856, not the 0.663 a wholly-inside-window
construction path implies, and the level shape is even more of the residual than
the pre-registration assumed.

**`fra_2023_discretionary_caps` regressed less than named** (12.2% against ~16%)
and **`cbo_opt43` improved more** (10.8% against ~16%), both because the
predicted ratios were computed for a full ten active years while these cases
start one year into the window and lose more of their tail.

### What is left

1. **IIJA is still the tier's largest row, and it is no longer a spend-out
   row.** $163.0B carried forward at 2%/yr is ~$1,894B of authority against the
   $446.3B CBO's table provides; spending the wrong authority out correctly
   cannot fix a total built on four times too much of it.
   `SpendingPolicy.budget_authority_path` exists and is tested for exactly this
   shape, but wiring IIJA's authorization schedule to it changes a
   *pre-registered shape input* — `preregistered.py` and `cbo_scores.py` are
   both off-limits to a modelling lane, so it is a manifest decision, not a
   modelling one. Recommend it as the next spending item.
2. **The classes are account *classes*, not accounts.** `cbo_opt39` now
   under-predicts (8.1%) because Pell spends out in two years while the generic
   grants profile takes six. Account-level rates would close that, and CBO
   publishes them (publications 61913 and 62256) — from an environment that can
   reach cbo.gov.
3. **The A-11 cross-check is still open.** Nothing here has been checked against
   an outlay rate published outside CBO's options report, because no such
   published table was reachable. See §5.
4. **The app is untouched by design.** Every user-facing `SpendingPolicy` — the
   composer's per-goal builds included — is still `immediate`. Turning spend-out
   on for those changes shipped preset numbers and belongs with a UI lane, not
   this one.

## 8. Follow-ups

*Appended by the L2 follow-up lane (branch `model/l2-followups`), 2026-09-01/02.
It closed items 1 and 4 of §7 "What is left"; items 2 and 3 (account-level
rates, the A-11 cross-check) are still open and still need an environment that
can reach cbo.gov.*

### 8.1 IIJA: the authorization path (§7 item 1)

The shape input was superseded under the manifest's own rule — a **new row**,
never an edit — because CBO's estimate states a schedule and
`SpendingPolicy.budget_authority_path` can now carry one:

| row | shape input | model | official | err |
|---|---|--:|--:|--:|
| `iija_2021_discretionary.v1` | $163.0B level at 2%/yr | +$1,894.0B → +$1,621.1B after L2 | +$415.4B | 356% → **290%** |
| `iija_2021_discretionary.v2` | the source's own $163.0B → $70.1B → $68.5B → $68.1B → $66.2B → $2.08B/yr | **+$340.0B** | +$415.4B | **18.2%** |

The **target never moved** — same $415.448B, same document, same window — and
`.v1` stays in `preregistered.py` unedited. `IIJA_AUTHORIZATION_PATH_RULE` sets
every year of the path: the five figures CBO states, plus the remainder of
CBO's own $446,306M authority total spread evenly over the years the estimate
describes only as "about $2B/yr". Entered in `1a68118`, scored in `327a69b` —
the two-commit protocol, checkable from the history.

| tier | n | before | after |
|---|--:|---|---|
| **out-of-sample (Tier 1)** | 25 | 45.3% mean / 16.1% median / 12 within 15 / 15 within 25 | **34.4% / 16.1% / 12 / 16** |
| calibrated reference (fitted) | 34 | 2.7% | **unchanged** |
| unfitted reconstruction | 20 | 250.8% | **unchanged** |
| leave-one-out | 18 | 59.3% | **unchanged** |

Exactly one row moved anywhere in the 79-row scorecard.

**What the remaining 18% is.** Not the shape and not the spend-out: the path
outlays **$433.2B in total** against CBO's $415.4B — 4.3% high, which is the
construction profile's 0.973 spend-out sum applied to the full authority — but
**$92.6B of that falls in FY2022-2024**, before the model's FY2025-2034 window
opens, against a published figure covering FY2021-2031. It is a window
mismatch, recorded rather than corrected; the repository has no 2021 vintage to
score the bill on its own window. Between them the two rows now separate the
two defects this case surfaced: the missing spend-out model (`.v1`) and the
missing authorization path (`.v2`).

### 8.2 The app spends out too (§7 item 4)

§7 recorded "the app is untouched by design… belongs with a UI lane". It is
done. Every Tailor spending program declares an `outlay_account_class` in its
own definition and Build's spending goals derive one from the goal category —
classification by account type, on the same taxonomy §5 records, never keyed to
a benchmark id. Explore ships no spending preset.

10-year figures, `immediate` → classified: infrastructure +1,146.4 → +749.8,
custom +1,095.0 → +725.4, defence +985.5 → +880.2, childcare +1,146.4 →
+967.4, R&D +600.3 → +503.8, pre-K +458.6 → +386.9, high-speed rail +328.5 →
+217.6, the discretionary cut −547.5 → −489.0, Medicare buy-in +573.2 →
+571.7; the two one-time programs are unchanged (+30.0, +400.0) because their
whole tail lands inside the window. No preset label moved — every label quotes
an *annual* funding level, which is authority and is what it always was.

Each spending score now renders one line naming its profile and its
outlay/authority ratio, computed from the scored result so it cannot drift from
the number above it. `immediate` stays reachable under Economic parameters as
an explicit choice, and is the default for nothing.
