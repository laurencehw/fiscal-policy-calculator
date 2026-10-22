# SS1 — A Social Security trust fund page, benchmarked against CRFB's Reformer

**Status:** pre-registered 2026-10-22, before any file under `fiscal_model/`, `app_pages/` or
`components/` is opened for editing. Requested by Laurence in the project thread on 2026-10-22
("it's another useful benchmark also for us. how we compare to crfb").

**Owns:** a new package `fiscal_model/social_security/`, new data under
`fiscal_model/data_files/social_security/`, a new page `app_pages/social_security.py` and its
registration in `app.py`, the two stale "SS Solvency" package texts in
`fiscal_model/ui/policy_packages.py`, the two pinned OCACT figures in
`fiscal_model/ui/tabs/results_summary.py` (`_PAYROLL_FITTED_TARGETS`), tests touching them, this
file. It touches no scoring module, no validation tier, no yardstick script and no CI gate.

---

## 1. Why

The app scores Social Security only as a federal budget line: `payroll.py` prices four
revenue-side levers (cap to 90%, donut hole, eliminate cap, rate change) in ten-year dollars.
Nothing models the **trust fund** — the year-by-year OASDI reserve, the 75-year actuarial
balance, the depletion year, or the across-the-board cut at depletion. Benefit-side levers
(COLA, PIA formula, retirement age, taxation of benefits) are absent altogether. The only
trust-fund numbers in the app are two typed constants in a results caption (E2.1: 2.55% of
payroll, depletion 2059; E2.5: 2.50%, 2057), and they are a Trustees vintage behind.

CRFB's *Social Security Reformer* (crfb.org/socialsecurityreformer) is the reference product:
a menu of options, additive, showing percent of the 75-year shortfall closed, insolvency year
and the size of the cut at insolvency, with a trust-fund chart. Its own methodology note says
its option effects are "CRFB staff estimates, generally based on Social Security Chief Actuary
figures", that it "generally doesn't account for interactions", and that outputs are "rough
estimates and not formal scores".

## 2. Tier

This page is a **transcription**, not a model. Every option effect is SSA OCACT's own
single-year estimate (`ssa.gov/oact/solvency/provisions/tables/table_runNNN.html`, 2026
Trustees Report intermediate basis); the baseline is the 2026 Trustees Report (Tables IV.B1,
VI.G1, VI.G2). What the repository computes is the ledger (reserves, depletion year, actuarial
balance) from those published rates. It joins **no** validation tier and moves no tier's
figure; the page labels it "transcribed from OCACT — not a model estimate" and never
"validated". Package totals are a **sum of single-provision estimates without interactions**,
which the page states next to the total, exactly as CRFB does.

## 3. The ledger

Per year *t* (2026–2100), as a share of current-law taxable payroll *P_t* (VI.G1):

```
balance_t   = income_rate_t − cost_rate_t + Σ_options Δbalance_{o,t}        (IV.B1 + OCACT)
reserves_t  = reserves_{t−1} × (1 + i_t) + balance_t × P_t × (1 + i_t/2)     (mid-year flows)
i_t         = F_t / F_{t−1} − 1, F = VI.G1 compound effective interest factor
reserves_2025 = 2026 end-of-year reserves − 2026 (total income − cost)        (VI.G2)
```

Depletion year: first year whose reserves at year end are negative (OCACT reports the year in
which reserves run out). Percent payable at depletion: income rate / cost rate in that year.
Actuarial balance: OCACT's summarized-rate formula, present values at the VI.G1 factor —
(reserves at start + PV of income − PV of cost − PV of an ending reserve equal to the 2101
cost) / PV of taxable payroll; the 2101 cost is the 2100 cost rate on 2100 payroll grown at the
2099–2100 payroll growth rate.

## 4. Pre-registered checks (these are what the implementing commits must land on, or say why not)

| # | check | pass bar |
|---|---|---|
| L1 | baseline depletion year | **2034** exactly (TR2026: OASDI reserves depleted in Q3 2034) |
| L2 | baseline 75-year actuarial balance | **−4.42% ± 0.03pp** (TR2026 summary) |
| L3 | baseline end-of-year reserves 2026–2033 | within **2%** of VI.G2 each year |
| L4 | baseline payable at depletion | **83% ± 1pp** (TR2026 summary) |
| L5 | each transcribed option: proposal rate − change = IV.B1 baseline rate | within **0.015pp** in every year (a transcription check: catches mis-read rows) |
| L6 | each option's recomputed change in actuarial balance vs OCACT's own summary row | within **0.03pp** for every option |
| L7 | each option's recomputed depletion year vs OCACT's own summary row | exact for **≥ 90%** of options, within one year for all |

L6/L7 are reconstruction checks of the ledger against OCACT's own arithmetic on the same
inputs, so agreement is expected; a miss means the ledger's mechanics are wrong, not that
OCACT is.

## 5. The CRFB comparison

CRFB's tool is a JavaScript application and its option-level figures are not published in a
fetchable table. The comparison is therefore made on what CRFB *does* publish in prose:

- the headline baseline facts in its 2026 blog post (insolvency year, cut at insolvency), and
- any plan or option for which CRFB publishes "percent of shortfall closed" or a solvency
  verdict, transcribed with its URL and date.

Each comparison row records CRFB's figure, ours, the gap, and the known reason for any gap
(CRFB's baseline is an August 2025 update to the 2025 Trustees Report with option effects
"mostly" from the 2024 Report; OASI-only vs combined OASDI; CRFB's own estimates for
options OCACT does not score, such as the Six Figure Limit). **No constant is tuned to close
a gap.** Where the gap is a baseline-vintage difference it is reported as one, not as error.

Expected (stated before measurement): our baseline will say 2034 and a 17% cut for combined
OASDI; CRFB's 2026 post says 2032 and a 22% cut, which is the **OASI-only** fund. The page
must show both framings or say plainly which one it uses — a reader comparing the two tools
must not see a two-year "disagreement" that is a definitional one.

## 6. Pre-registered side effects

- `_PAYROLL_FITTED_TARGETS` stops typing OCACT figures and reads them from the new provision
  table. Expected movement: E2.1 depletion **2059 → 2058** (TR2026 table_run137 shows 2058;
  the typed 2059 is a TR2025 figure) and E2.1 actuarial balance stays 2.55. E2.5 is
  re-read from table_run214 and its movement is recorded in the outturn whatever it is.
  `tests/test_payroll_target_caption.py` changes with it.
- `policy_packages.py`: "SS Solvency: Raise the Cap" says the fund is depleted "by ~2033" —
  becomes 2034 (combined) / 2032 (OASI). It bundles NIIT expansion, which is general revenue
  and does not reach the OASDI trust funds; the description says so. Package totals untouched.

## 7. Not in scope

Interactions between options; distributional effects by lifetime earnings; the HI (Medicare)
trust fund; CRFB-only options (Six Figure Limit, "tax contributions instead of benefits")
unless OCACT has scored an equivalent; dollar conversion of actuarial balance into the
ten-year budget window (the existing payroll presets keep doing that).

## 8. Outturn

*(appended after implementation)*
