# Survey of CBO's GitHub organisation — macro, health and spending repositories

*Written 2026-09-11 against `main` @ `20e356d` on branch `memo/cbo-github-survey-macro`.
No app code changed. A sibling memo, `CBO_GITHUB_SURVEY_tax.md`, covers the tax and revenue
repositories; a third pass is expected to write a route-to-8.5 roadmap from both, and this memo
is written for that reader.*

Every repository named below was cloned read-only into a scratch directory and read. Every
figure quoted from a CBO file was read out of the cloned file, not recalled; every figure
quoted about this app carries a `file:line`. Where I computed something from a CBO file — the
aggregate IO price effect, the implied taxable-payroll path, the OCACT cross-check — the script
that computed it is named and the arithmetic is stated so it can be rerun.

---

## §0. Verification: the organisation is legitimate, and here is the evidence

**Verdict: `github.com/US-CBO` is the Congressional Budget Office's own organisation.**
`is_verified: false` on the GitHub API record is a statement about GitHub's *domain-verification*
feature, which CBO has not used; it is not evidence about ownership. Three cbo.gov pages link
*into* the organisation for repositories in this survey — two of them in my assigned set — each by name and by repository URL.

cbo.gov itself returns **HTTP 403 to every programmatic fetch** — the same wall this repository
has already recorded twice (`fiscal_model/data_files/spending/outlay_rates.csv` header,
`planning/MODELING_IMPROVEMENT.md` §6.2 item 16). All three quotations below are therefore taken
from the Internet Archive's capture of the cbo.gov page, with the archived capture timestamp
shown. The evidence is what cbo.gov said, mirrored; it is not a second-hand summary.

**Evidence 1 — a working paper linking its own repository.**
`https://www.cbo.gov/publication/58849`, *The Welfare Effects of Debt: Crowding Out and Risk
Shifting: Working Paper 2022-10* (Wayback capture `20250112075256`). Under the heading **"Data and
Supplemental Information"** the page carries the link **"Code and Data for the Welfare Effects of
Debt Analysis"**, whose href is `github.com/us-cbo/debtwelfare` — the repository in my assigned set.

**Evidence 2 — CBO stating the practice, and naming three repositories.**
`https://www.cbo.gov/publication/61878`, *How CBO Shares Its Models* (Wayback capture
`20260711204031`), states verbatim:

> "When practicable, we post data, computer code, and documentation associated with our models on
> the web-based platform known as GitHub."

and, in the section headed **"Resources Available on GitHub"**:

> "In May 2020, CBO began sharing data, code, and other documentation on that platform."
> … "CBO's GitHub page also features a model that helps the agency's analysts estimate how quickly
> private health insurance premiums will change over time. The premium growth model allows users
> to replicate CBO's projections of premiums and see how those projections are affected under
> alternative scenarios."

The words "premium growth model" on that page are hyperlinked to
`github.com/US-CBO/premium-growth-model`, and the same paragraph links
`github.com/US-CBO/captax` and `github.com/US-CBO/eval-projections`. The May 2020 date matches the
organisation's `created_at` of **2020-05-07** exactly.

**Evidence 3 — a 2026 report linking a 2026 repository.**
`https://www.cbo.gov/publication/62257`, *How Changes in Economic Conditions Might Affect the
Federal Budget: 2026 to 2036* (Wayback capture `20260727100434`), carries under **"Data and
Supplemental Information"** the link **"Excel Model on GitHub"**, href
`github.com/US-CBO/rules-of-thumb-model/blob/main/README.md`.

**Evidence 4 — the site footer.** Every cbo.gov page fetched carries `github.com/US-CBO` in its
own social-links footer, beside CBO's LinkedIn and RSS links.

**Corroboration from inside the repositories.** Every `LICENSE.md` in the organisation carries the
same US-government text — *"created by CBO employees in their official capacity. Therefore, they
are not subject to copyright and are in the public domain in the United States"* — and every
README routes questions to `communications@cbo.gov`, the address on the organisation's own API
record. Several READMEs name CBO analysts by name and division (`premium-growth-model`: Ben
Hopkins, Rajan Topiwala, supervised by Alexandra Minicozzi and Chapin White).

**Licence, for all repositories in this survey.** GitHub reports `NOASSERTION` because the licence
is not one of its recognised SPDX identifiers. The actual text is US-government public domain, with
two conditions that matter for this app: *"Users may not … modify the package and then present it
as official government material"*, and (in the newer repositories, e.g. `premium-growth-model`)
*"CBO requests that those modifying the code clearly identify and accurately attribute authorship
for all modifications."* Both are compatible with vendoring a CBO data file into
`fiscal_model/data_files/` under a header naming its source, which is what this repository already
does for CBO tables. Every repository also carries the standard CBO disclaimer: *"CBO has verified
the accuracy of the results produced when using the package for its own analyses and publications
but not for other purposes."*

---

## §1. Summary

**Three findings dominate, all three are in repositories that were assigned to neither memo, and
the first one is a green-tier defect on a number the landing page prints.**

1. **CBO publishes its February 2026 baseline as two CSV files, and the app's own `CBO_FEB_2026`
   vintage — its default — disagrees with it on every line.** `budgetary-feedback-model/input/
   budget_baseline.csv` is CBO's FY2025–FY2036 budget path; `input/econ_baseline.csv` is the
   matching 38 quarterly economic series, 1995Q1–2036Q4. Run on the app's own default
   (`CBOBaseline(start_year=2026, vintage=CBO_FEB_2026).generate()`, `use_real_data=True`):

   | FY2026–2035 | app | CBO's own February 2026 baseline | gap |
   |---|---:|---:|---:|
   | **cumulative total deficit** | **$29,529.1B** | **$23,143.3B** | app **+27.6%** |
   | debt held by the public, end FY2035 | $49,362.1B | $53,103.2B | app **−7.0%** |
   | individual income tax, FY2026 | $2,248.9B | $2,751.3B | app **−18.3%** |
   | payroll taxes, FY2026 | $2,027.1B | $1,825.6B | app **+11.0%** |
   | corporate receipts, FY2026 → FY2035 | 436.8 → 667.4 (**4.82%/yr**) | 403.98 → 551.91 (**3.53%/yr**) | app **+8.1%** then **+20.9%** |

   `fiscal_model/baseline.py:163-168` grades this vintage `"sourced"`, and `:220-224` grades its corporate
   line `"vintage_estimate"` with the comment *"Neither the level nor the shape is transcribed…
   **not** … 'CBO's February 2026 corporate receipts'"*. The blocker is recorded at `:214-219`:
   *"cbo.gov returns HTTP 403 to this environment and the Wayback Machine holds no snapshot of the
   January 2025 or February 2026 budget projections workbooks (re-checked 2026-09-06). **Adding one
   is a data edit — a block in the CSV — not a code change.**"* The GitHub organisation is not
   403-blocked. The file exists. **The $29.5T figure Ask prints as the ten-year deficit is 27.6%
   above what CBO's own February 2026 baseline projects**, and by
   `HIGH_STAKES_ACCURACY.md` §1.1's own criterion — salience × magnitude × reach — that is the
   highest-stakes number this survey touched.

2. **CBO publishes its own budget-authority→outlay spend-out vector, and it is reachable.**
   `budgetary-feedback-model/input/rules_of_thumb.csv`, column `spout`: **0.53, 0.26, 0.09, 0.05,
   0.04**, zero thereafter, applied in `bfm/outlays.py:589-593` as `Σ_k s_k · ΔBA_{t−k}` — the exact
   identity Wave 1's lane L2 built. `fiscal_model/data_files/spending/outlay_rates.csv`'s own header
   says the external cross-check it wanted "**were unreachable when this was built (cbo.gov 403)**".
   That check is now available, it did not have to come from the 403-blocked publications, and on a
   first comparison the NNLS fit **passes**: the app's `operations_and_support` row
   (0.5387, 0.2571, 0.0666, 0.0726, 0.0416) differs from CBO's vector by a mean absolute 0.0118 and
   a maximum 0.0234. This closes §6.2 item 16 — as a confirmation, which is the outcome to want.

3. **The behavioural constants behind dynamic scoring have published CBO counterparts, and the
   app's are rounder than CBO's by a wide margin.** `MARGINAL_REVENUE_RATE = 0.25`
   (`fiscal_model/constants.py:71`, commented "Combined federal revenue/GDP ratio — CBO") stands in
   for what CBO decomposes into nine income-type marginal rates in the same CSV: wages and salaries
   **0.18→0.21**, FICA **0.10**, proprietors **0.11→0.12**, SECA **0.04**, domestic corporate
   profits **0.07→0.08**, dividends **0.02→0.03**, personal monetary interest **0.07→0.08**,
   excise-on-GDP **0.01**, customs **0.15→0.13**. `bfm/revenues.py:35-38` shows the application:
   `Δliability = rate × (alt − base)` on each NIPA series separately, then a fiscal-year weight
   (`ind_fy_wt = 0.75`, `corp_fy_wt = 0.64`, `cg_fy_wt = 0.45` — `input/parameters.csv:2-6`).
   The same file settles a second constant: `trade.py:153`'s `income_payroll_offset_rate = 0.25`,
   documented as the "CBO/JCT/OTA convention", has a published CBO counterpart in the column CBO
   labels *"Effective marginal tax rate on Customs Duties"* — **0.15 in 2026 falling to 0.13 by
   2036**, roughly half the app's figure. The two are not the same quantity (CBO's is a *feedback*
   rate on a macro path; JCT's 25% is a *scoring* convention on an indirect tax), and the memo does
   not propose swapping one for the other — but a shipped trade score whose offset is twice CBO's
   own marginal rate on the same revenue line is worth a sentence somewhere.

**Beyond those three, the yield is narrower than the repository count suggests.** Of my 21
assigned repositories, **five are documentation-only or environment-locked** (the code cannot run
outside CMS's VRDC or a CBO Redshift instance, or the data are proprietary); **six are single-file
Excel models** for budget accounts this app does not score; and **four are careful models of
domains the app has no module for** (hepatitis C, immigration legal status, permitting, financial
regulation). The genuinely load-bearing ones for this app are `social-security-trust-funds-model`,
`premium-growth-model`, `IO-price-model`, `means_tested_transfer_imputations` and
`medicaid-labor-supply-model`, plus the three adjacent repositories in §2.0.

**Two things I checked and am recommending against**, both in §4 and both worth the roadmap
reader's attention before anyone else re-derives them:

- **The OCACT-to-dollars conversion is now constructible and is contradicted by CBO's own
  numbers.** `HSA_h13_payroll_targets.md` §5 refused to convert OCACT's percent-of-taxable-payroll
  into dollars because the denominator was unpublished. It is published — CBO's SS trust funds
  workbook implies OASDI taxable payroll of **$10,890.7B in FY2026 rising to $15,258.2B in FY2035**,
  a 3.82%/yr CAGR. Doing the conversion gives **$201.5B in 2026** against CBO's own **$122.0B** for
  the identical donut design, and **$368.1B in 2034** against CBO's **$192.0B** — a disagreement of
  **1.65× to 1.92×**, widening. H13's refusal was right and is now *demonstrated* rather than
  asserted.
- **Using `premium-growth-model` to close CBO Option 56 is closer to leakage than anything else in
  this survey.** PGM's output feeds HISIM2 (its own README says so in its first sentence), and
  HISIM2 is what produces CBO's health scores. Option 56 is a **Tier 1 pre-registered
  out-of-sample row at 13.1%**. Feeding CBO's own premium projection into the model that predicts
  CBO's own option score would make the row an input to itself.

---

## §2. Per-repository entries

Licence for all: US-government public domain, as quoted in §0. Sizes are the GitHub API's.

### §2.0 Three adjacent repositories assigned to neither memo — and they carry the most value

These are in the organisation, they are squarely macro/budget, and neither my list nor (on its
face) the tax list names them. **The roadmap reader should treat this section as the highest-value
part of the survey.** I have surveyed them to the same standard as my own.

#### `budgetary-feedback-model` — Python, 46 KB, updated 2026-07-13

**What it is.** CBO's Budgetary Feedback Model: "a unified framework for quantifying changes in
projected revenues and outlays relative to CBO's baseline budget projections", an approximation of
CBO's broader budget-model suite intended for *"relatively small deviations from CBO's baseline
projections"*. It builds on CBO's 2020 working paper *A Simplified Model of How Macroeconomic
Changes Affect the Federal Budget* (`https://www.cbo.gov/publication/55884`). Inputs are CBO's
February 2026 baseline (`https://www.cbo.gov/publication/61882`) and the rules of thumb published
April 2026 (`https://www.cbo.gov/publication/62257`).

**What it ships.** `input/econ_baseline.csv` (38 quarterly economic series, 1995Q1–2036Q4);
`input/budget_baseline.csv` (FY2025–FY2036: individual income taxes, payroll taxes, corporate
income taxes, other revenues, mandatory outlays, discretionary outlays, net interest, total and
primary deficit, debt held by the public); `input/rules_of_thumb.csv` (116 columns × 12 years);
`input/parameters.csv` (17 scalars); `glossary.md` defining every column; `bfm/{revenues,outlays,
net_interest_costs}.py`.

**Key parameters, with file and line.**

| Quantity | Where | Value |
|---|---|---|
| Effective marginal tax rate on wages and salaries | `rules_of_thumb.csv` col 99 `rtpwsd` | 0.18 (2025) → 0.21 (2036) |
| … on FICA | col 101 `rtwwsd` | 0.10, flat |
| … on proprietors' income | col 100 `rtpyent` | 0.11 → 0.12 |
| … on domestic NIPA corporate profits | col 93 `rtczb` | 0.07 → 0.08 |
| … on customs duties | col 16 `customs` | 0.15 (2026) → 0.13 (2036) |
| … on excise, per 1% of GDP | col 38 `excisegdp` | 0.01 |
| Discretionary spend-out, by lag | col 115 `spout` | 0.53, 0.26, 0.09, 0.05, 0.04, 0 … |
| Net interest per 1pp rate change, period 1 | col 80 `rate1` | $55.06B (2026) → $10.10B (2036) |
| Fiscal-year weight, individual taxes | `parameters.csv:2` | 0.75 |
| Fiscal-year weight, corporate | `parameters.csv:6` | 0.64 |
| Fiscal-year weight, capital gains | `parameters.csv:3` | 0.45 |
| Off-budget share of FICA liabilities | `parameters.csv:16` | 0.78 |

**Mapping.** `fiscal_model/baseline.py` (`CBOBaseline`, `BaselineVintage`);
`fiscal_model/constants.py:65-79`; `fiscal_model/models/macro_adapter_frbus.py:347-352`;
`fiscal_model/data_files/spending/outlay_rates.csv`; `fiscal_model/economics.py`.

**What the app could use.** (a) `budget_baseline.csv` + `econ_baseline.csv` → a **transcribed**
February 2026 vintage in place of the current `vintage_estimate` (opportunity #1). (b) `spout` →
the external cross-check on L2 the app's own data-file header asks for and could not get (#2).
(c) `MARGINAL_REVENUE_RATE = 0.25` → nine published marginal rates applied to nine NIPA series (#3).
(d) `rate1..rate11` and `debt1..debt11` → the debt-service term `macro_adapter_frbus.py` currently
hardcodes at `cumulative_deficit * 0.04` (#6).

**One caution on `budget_baseline.csv`, to pre-register rather than discover.** Its four revenue
columns minus its three outlay columns do **not** equal its own "Total deficit (-)" column: FY2026
gives $5,177.53B − $7,448.62B = −$2,271.09B against a stated **−$1,852.70B**, a $418.4B gap that is
presumably offsetting receipts booked outside the seven columns shown. The **Total deficit** and
**Debt held by the public** columns are therefore unambiguous and usable as-is; the seven component
lines are indicative, and a lane that rebuilds the vintage from them must reconcile the residual
before claiming the components are CBO's.

**A second observation on the economic block.** `fiscal_model/baseline.py:68-84`'s
`_CBO_FEB_2026_ASSUMPTIONS` carries no source comment, unlike the January 2025 block three
definitions below it which carries a full transcription note — and its values are flat and round
where CBO's are neither. Annual averages computed from `econ_baseline.csv`
(`scratchpad/vintage_check.py`): real GDP growth **2.364%** in 2026 against the app's 1.9%; PCE
inflation **2.959%** against 2.5%; and, most visibly, the 10-year Treasury yield **rises** 4.13% →
4.38% across FY2026–2035 where the app's block **falls** 4.5% → 3.9%. The two paths move in
opposite directions for a decade. `VINTAGE_SOURCING[CBO_FEB_2026]` nevertheless reads `"sourced"`
(`baseline.py:163-168`), which `tests/test_baseline_vintage.py` pins — so the grade, not just the
numbers, is worth re-examining in the same lane.

**What it does not offer.** No policy scoring. CBO says so plainly: the BFM *"is not intended to
capture the effects of policy changes that affect the sensitivity of the tax and spending systems
to changes in the economy"*, and warns that the distribution of an income change matters in a way
the rules of thumb cannot see. It cannot replace any scoring module; it can replace the app's
constants for converting a GDP path into a budget path, and that is where the app currently uses
one number where CBO uses nine.

#### `rules-of-thumb-model` — Excel (no language), 155 KB, updated 2026-05-19

Single workbook, sheets `Contents`, `1. Productivity`, `2. Labor Force`, `3. Interest Rates`,
`4. Inflation and Interest`, plus a `_CBO` duplicate of each. It supplements publication 62257 and
replicates CBO's own interactive tool (publication 61914). It is the front end to the same rules of
thumb the BFM ships as CSV; the BFM is the better source for programmatic use, so this repository's
value is as the **published document** a BFM-derived constant can be cited to. It is also the
provenance for `HSA_h13`'s Tax Foundation trap: nothing here is a policy score.

#### `discount-factors` — Python, 40 KB, updated 2026-02-18

Converts CBO's January 2025 Treasury-yield projections into annual and quarterly discount factors
used for credit-program subsidy costs. `data/treasury_yield_data.csv` carries yields that the
README says are *"provided only in this repository"* and not on cbo.gov. The app discounts nothing
— every score is undiscounted nominal — so there is no current use. It becomes relevant only if the
app ever prices a credit program or reports present values, and I have listed it in §4 rather than
§3 for that reason.

---

### §2.1 Repositories with a direct mapping to an app module

#### `social-security-trust-funds-model` — Excel (no language), 68 KB, updated 2026-02-20

**What it is.** CBO's projection of OASI and DI trust-fund balances *"consistent with CBO's
February 2026 baseline projections"*. One workbook: `README`, `OASI`, `DI`, `Combined`, `License`.

**What it ships, with cell references.** Sheet `Combined` is a full FY2026–FY2036 OASDI budget:
row 7 **Nonfederal Payroll Tax Revenue** (1350.44, 1403.71, 1457.59, 1515.62, 1575.99, 1637.69,
1699.39, 1762.05, 1825.86, 1892.02, 1960.66), row 9 Taxes on Benefits, row 11 Interest, row 18
Benefits, row 24 Surplus/Deficit, row 28 Primary Surplus/Deficit, row 32 End-of-Year Balance.
Sheets `OASI` and `DI` decompose each into FICA, SECA, refunds, taxes on benefits, the federal
employer share and the Railroad Retirement transfer. OASI's combined end-of-year balance crosses
zero in **FY2033** (row 33: −141.658 in 2032 → −710.859 in 2033).

**Derived, by `scratchpad/ss_calc.py`.** Dividing row 7 by the 12.4% combined OASDI rate gives an
implied taxable payroll of **$10,890.7B in FY2026 → $15,258.2B in FY2035**, total $130,003.1B over
the window, **CAGR 3.8179%/yr**.

**Mapping.** `fiscal_model/payroll.py`; presets `ss_donut_250k` and `ss_eliminate_cap`;
§6.2 items 26 and 47; `HIGH_STAKES_ACCURACY.md` §1.2 row 3.

**What the app could use.** The ramp. §6.2 item 47 records that `create_ss_donut_hole` stamps a
flat $270B/yr where CBO's own path runs $122.0B → $192.0B and OCACT's income-rate path runs 1.85%
→ 2.50% of payroll. This workbook supplies the **published denominator** that turns a
percent-of-payroll statement into a shape: a provision expressed as a share of taxable payroll
must grow at 3.82%/yr, and CBO's own donut path grows at 5.8%/yr because the hole closes on top of
that. It also gives the payroll module a vintage-anchored OASDI base where `payroll.py:186-224`
currently carries only the **HI** base (`covered_earnings_base.csv`, CBO February 2024 wages ×
a 1.0313 covered-earnings ratio measured on CY2023 Trustees data).

**What it does not offer, and this is the important half.** No dollar score for any provision, and
no earnings distribution above the taxable maximum — which is the quantity a donut-hole design
actually needs. See §4 for the cross-check that rules out converting OCACT's percentages.

#### `premium-growth-model` — Stata + Quarto, 2.6 MB, updated 2026-02-06

**What it is.** CBO's private health insurance premium growth model, which *"generates inflation
factors that are used in CBO's health insurance simulation model (HISIM2)"* for
employment-based premiums, **employer contributions to HRAs and HSAs**, and nongroup premiums, plus
plan characteristics (employer out-of-pocket maximums, nongroup deductibles). The full technical
report is rendered at `https://us-cbo.github.io/premium-growth-model/report/baseline_2026/report.html`.

**What it ships.** `output/baseline_2026/pgm_2026.csv` — 16 series × calendar years 1987–2036,
with each row's Stata specification printed in a column (`regress lndiff_prem_real_demo
L.lndiff_prem_real_demo lndiff_pdi_real_6yr if year >= 1999 & year <= 2023`). `prepped_data/`
carries the cleaned KFF Employer Health Benefits Survey premium growth series (1999–2024), NHE,
BLS, CPS age-sex indices and a Yamamoto index. `docs/ANNUAL_UPDATES.md` documents each source and
its refresh.

**The headline series.** `pchange_prem_demo_b2026` — CBO's projected annual growth in demographically
adjusted per-capita private health expenditure: **2026 7.149%, 2027 5.252%, 2028 4.837%, 2029
4.531%, 2030 4.444%, 2031 4.571%, 2032 4.587%, 2033 4.622%, 2034 4.655%, 2035 4.722%, 2036 4.792%**.
Levels run `prem_demo_b2026` $8,387.47 (2025) → $13,576.91 (2035) per capita.

**Mapping.** `fiscal_model/tax_expenditures.py` (`cap_employer_health`, CBO Option 56);
§6.2 item 7; Tier 1's one tax-expenditure row at 13.1%.

**What the app could use — with the leakage caveat stated first.** The gap between a cap indexed
to chained CPI (~2.3%/yr) and premiums growing at 4.4–7.1%/yr is the whole mechanism of Option 56's
excess share, and PR #105 already gave that share CBO's chained-CPI indexation. Replacing the
premium side with CBO's own published path would complete the pair. **But Option 56 is a Tier 1
row**, and PGM output feeds HISIM2, which produces CBO's health estimates. I rank this at #7 with
an explicit circularity warning, not higher.

**What it does not offer.** No level for FSA/HRA/HSA *contributions* — only their growth factor —
so the base half of §6.2 item 7 (CBO caps "premiums **and** health spending accounts"; this
repository's premium distribution has no account dimension) is **not** closed by this repository.
No joint distribution of premiums and earnings, so alternatives 56.3 and 56.6 stay out of scope.

#### `IO-price-model` — Jupyter, 7.5 MB, updated 2026-04-27

**What it is.** A Leontief input–output price model over BEA Supply, Use and Import Matrix tables,
solving `p^D = (I − A^{D′})^{-1} A^{M′} p^M + (I − A^{D′})^{-1} v` and mapping the result onto the
PCE and PEQ price indexes through BEA's own PCE and PEQ bridges. Ships the BEA tables
(`inputs/bea_data/`, 9.4 MB, "as of March 25, 2026"), so it runs offline.

**What it ships that matters most.** `outputs/uni10_goods_only_pce_2024.csv` and
`outputs/uni10_goods_only_peq_2024.csv` — CBO's own run of a **uniform 10% goods import price
shock**, at NIPA commodity line level, with `p_D`, `p_M`, `import_share` and the weighted shock per
line. Aggregated by `scratchpad/io_agg.py` over the shipped `initial_purchasers_value` weights:

| | fixed retail margins | proportional retail margins | expenditure-weighted direct import share |
|---|---:|---:|---:|
| PCE price index (76 lines) | **+0.585%** | **+1.035%** | 5.04% |
| PEQ price index (27 lines) | **+3.159%** | **+4.327%** | 32.53% |

**Mapping.** `fiscal_model/trade.py:142` `border_pass_through_rate = 1.00`, `:145`
`consumer_pass_through_rate = 0.60`, `:148` `import_price_elasticity = -0.997`; §6.2 item 11 ("the
single largest remaining piece in `trade.py`"); `HSC_h8_tariff_feedback.md`.

**What the app could use.** A *measured* consumer pass-through in place of an asserted 0.60, and a
price channel that runs through the input–output structure rather than a scalar. The app's 0.60
is a single number applied to the whole import base; CBO's run says the same 10pp shock moves the
PCE index by 5.85–10.35% of the shock and the equipment index by 31.6–43.3%, because the two
baskets have import shares 6.5× apart. That difference is exactly what a scalar cannot express, and
it is also the input a GDP-feedback channel needs — H8 built the channel and reported it beside the
score; this supplies the price side of it.

**What it does not offer.** No revenue score, no import-demand elasticity (`v` and `p^M` are
user-supplied shocks), no tariff schedule, no partner dimension. `reciprocal_coverage_rate` and the
Section 232 base are untouched by it. The shock file is a flat 10 across all commodities with
`v = −0.5`; reproducing a *tariff* rather than an import-price shock requires choosing the shock
oneself.

#### `means_tested_transfer_imputations` — Stata, 542 MB, updated 2023-11-08

**What it is.** CBO's adjustment for survey underreporting of receipt and benefits from Medicaid/
CHIP, SNAP, SSI and federal housing assistance in the CPS ASEC, accompanying Bilal Habib, *How CBO
Adjusts for Survey Underreporting of Transfer Income in Its Distributional Analyses*, Working Paper
2018-07, `https://www.cbo.gov/publication/54234` (July 2018). Version 0.4.0 (2023-11-08) covers CPS
ASEC files 1980–2022, i.e. calendar years 1979–2021.

**Method.** Per-program, per-year probit probabilities of receipt; each unit's probability is
compared with a random draw; the loop re-draws until imputed + reported recipients land within one
weighted household of CBO's administrative target (with a 25% threshold relaxation after 30
non-converging passes). Benefit amounts are then set to CBO's estimated *potential* values from
program rules. Medicaid and SSI impute at person level, SNAP and housing at household level with
benefits assigned to the head. 43 input CSVs of ~14–24 MB each.

**Mapping.** `fiscal_model/distribution.py` (`DistributionalEngine`, CBO household universe since
PR #104); the CPS ASEC microsim; the seven distributional benchmarks spanning 0.00–5.86pp.

**What the app could use, and the hard stop on it.** CBO's published distributional tables are
built on income *including* these imputations; the app's CPS ASEC microdata are not adjusted, so
the app ranks households on an income concept that differs from the one its benchmarks rank on at
the bottom of the distribution. That is a real, named gap. **But the README forbids exactly this
use, in bold:**

> "**These imputations should not be used for state-level analyses, causal analyses, or policy
> simulations.**"

The app's CPS microdata drive `TaxCreditPolicy`'s per-unit engine — a policy simulation. Using the
imputations to re-rank the distributional universe while *not* using them in the credits
simulation is arguably inside the prohibition's letter; doing both is plainly outside it. Add the
542 MB against the repository's own size policy and the two circular distributional benchmarks, and
this ranks low (#9) with the quotation attached, not as a data win.

**What it does not offer.** No CPS ASEC microdata — the user must obtain those separately and merge
on the household/person keys documented in `docs/data_contents.md`.

#### `medicaid-labor-supply-model` — Python, 333 KB, updated 2026-07-27

**What it is.** CBO's estimate of the labor-supply response to Medicaid policy changes, as
`affected individuals × average earnings × percent change in labor supply`. Covers 80-hour/month
community-engagement (work) requirements for childless adults and for parents, and coverage losses
from ending eligibility.

**Key parameters, `parameters/specification_params.yml:187-189`.** `income_elasticity: -0.05`,
`substitution_elasticity: 0.31` ("calibrated to low-income populations"), `mdcd_base_elasticity:
0.02` (2% base earnings response to losing Medicaid, "drawn from the literature"), both structural
elasticities sourced to "TAD" (CBO's Tax Analysis Division). `parameters/dollar_value_medicaid.yml`
values Medicaid at $12,517/yr for disabled, $3,895 for non-expansion adults, $2,208 for expansion
adults, $1,581 for children. `inputs/microdata.csv` is a 1.5 MB IPUMS CPS subsample shipped for
replication only.

**Mapping.** None directly — the app has no Medicaid module, and §6.2 carries no Medicaid item.
The nearest adjacency is `LABOR_SUPPLY_ELASTICITY = 0.15` (`fiscal_model/constants.py:76`,
"Compensated labor supply elasticity — CBO") against CBO's own income −0.05 / substitution 0.31
split, and `fiscal_model/ptc.py`'s coverage response (§1.2 row 7, "19.28% transferred, dominated by
employment-based coverage").

**What the app could use.** `parameters/alternate_coverage_rates.yml` — probability of gaining
alternative coverage after Medicaid loss, by FPL group and by policy type — is the *structure* of
the PTC coverage response the repository is missing, from a CBO source, even though the levels are
for a different program. That is a method borrow, not a parameter borrow, and I rank it #10.

**What it does not offer.** No budgetary effect at all: the output is a change in *earnings*,
which CBO then feeds elsewhere. No PTC, no marketplace premiums.

### §2.2 Macro-uncertainty repositories

#### `markov-switching-macrosimulation-model` — R, 46 KB, updated 2026-02-20

Simulates forecast uncertainty for the unemployment rate, core PCE inflation and the 10-year
Treasury yield for *CBO's 2026 Budget and Economic Outlook* (`https://www.cbo.gov/publication/62105`),
updating the model in `https://www.cbo.gov/publication/58884`. `Inputs/data_251203.csv` carries 17
quarterly series; four further inputs must be downloaded by the user (New York Fed ACM term premia,
Laubach–Williams r*, the FRB/US `LONGBASE.TXT` package, Barnichon's composite help-wanted index),
and the user must supply their own forecast of real disposable income and r*. `R/` is ~95 KB of
estimation and simulation code.

**Mapping.** `fiscal_model/models/macro_adapter_frbus.py`; §6.2 item 58 ("the accuracy band is
symmetric and the errors are not"); H4's empirically calibrated bands.

**What the app could use.** Very little, and the reason is a distinction worth making explicitly
for the roadmap reader: **this model produces forecast uncertainty, and H4 shipped model-error
bands.** A band on "what will unemployment be" is not a band on "how wrong is this app's score of a
2pp surtax". H4 deliberately derived its bands from the Tier 1 error distribution, and that is the
right quantity. The one genuine borrow is that the MSM is the source of the 2,500 national
unemployment simulations `state-unemployment-rate-model` consumes, so it is the upstream of any
future scenario-band work. The repository does note that FRB/US's `LONGBASE.TXT` is a required
input — which is the same FRB/US package `FRBUSAdapter` (the non-Lite path) expects.

**What it does not offer.** No budget linkage, no policy scoring, and it will not run without four
externally downloaded files and a user-supplied forecast.

#### `conditional_forecasting_with_bvar` — R, 82 KB, updated 2025-12-03

Illustrates the methods in CBO working paper `https://www.cbo.gov/publication/59629` (Byoung Hark
Yoo). `data/data_for_bvar.xlsx` (62 KB) and `data/cbo_forecasts.xlsx` (12 KB) are from **CBO's May
2022 baseline**. The README states plainly that the shipped data are restricted to publicly
available variables and *"the code and data here does not generate the exact results in the working
paper"*. Runs over an hour.

**Mapping.** None live. A conditional-forecasting method would matter if the app ever asked "what
does this policy imply for GDP given a path for rates" — it does not; `MacroModelAdapter` runs a
fixed multiplier. Reject for now; noted in §4.

#### `state-unemployment-rate-model` — Stata, 2.8 MB, updated 2026-02-17

Models state-level quarterly total and insured unemployment rates against the national rate,
propagates 2,500 national simulations from the Markov-switching model through them, and computes
the probability that each state triggers UI Extended Benefits. Ships 28 MB of DOL and BLS input
series. **Mapping:** the app's state modelling (top-10 states, SALT interaction) is about *tax*
interaction; this is UI trigger eligibility, a different question on a different set of states. No
use.

### §2.3 Sector models with no app module

- **`hepatitis-c-model`** — R, 6.6 MB, updated 2026-07-24. An individual-level state-transition
  microsimulation over disease stages, insurers (Medicaid, Medicare, commercial, marketplace,
  incarcerated, IHS, uninsured) and ages, with shipped illustrative outputs. Carries the most
  thorough provenance document in the organisation, `docs/hep_c_param_sources.md` (21 KB), citing
  each parameter to a named study. **The app has no hepatitis or disease module.** Its transferable
  asset is the *form* of that document — a parameter-by-parameter source file with an explicit note
  that "in cases in which published estimates were incomplete, inconsistent, or not directly
  applicable … CBO adjusted parameters" — which is a close cousin of this repository's own
  `benchmark_sources.py` discipline. Its own banner is also worth carrying: "**Results from this
  repository are not a cost estimate and should not be interpreted as CBO's expectation of future
  outcomes.**"
- **`legal-status-model`** — Python + Stata, 1.7 MB, updated 2026-06-01. Assigns native-born /
  legal-status / other-foreign-national categories to 2023 ACS or CPS ASEC records using OHSS
  controls; supersedes `https://www.cbo.gov/publication/57022`; definitions in Appendix C of *The
  Demographic Outlook: 2026 to 2056* (`https://www.cbo.gov/publication/61994`). Ships
  `data/cps_asec_adj_weights_2023.csv` (3.9 MB) and OHSS yearbook tables. **No app module.** If the
  app ever scores an immigration provision, this is the first place to come back to; it also ships
  a CPS ASEC weight adjustment that touches the same microdata the credits module reads, which is
  worth knowing before anyone re-weights that file for another reason.
- **`permitting-model`** — MATLAB/Dynare, 435 KB, updated 2026-07-29. A two-state model of private
  investment response to changes in time-to-build, used in CBO's cost estimate for the 2025
  Reconciliation Recommendations of the House Natural Resources Committee
  (`https://www.cbo.gov/publication/61415`); full working paper July 2026
  (`https://www.cbo.gov/publication/62517`). `data/parameter_table.csv` (17 KB) is a structural
  calibration by BEA sector, drawn in part from CBO's own CapTax model. **No app module.** The app's
  supply side is two elasticities on the default `EconomicModel` path
  (`constants.py:74-76`: `LABOR_SUPPLY_ELASTICITY = 0.15`, `CAPITAL_ELASTICITY = 0.25`,
  `INVESTMENT_ELASTICITY = -0.5`, read at `economics.py:166-167`), and *none at all* on the
  `FRBUSAdapterLite` path, whose own docstring says so (`macro_adapter_frbus.py:363-372`: "this
  model has no supply-side channel to sustain long-run effects"). Listed here because it is the
  only CBO repository that models a structural investment response, so it is the natural starting
  point if the roadmap ever builds one — but that is a new module, not a parameter.
- **`financial_regulation_model`** — Python, 21 KB, updated 2025-12-05. Replicates CBO's September
  2019 *Financial Regulation and the Federal Budget* (`https://www.cbo.gov/publication/55586`) —
  lower capital requirements, eliminating orderly liquidation authority, repealing the
  ability-to-repay rule, each under moderate and severe crisis scenarios, on CBO's **May 2019**
  baseline. `input_data/parameter_set.csv` gives low/central/high values for each policy parameter.
  **No app module and a seven-year-old baseline.** Its one transferable idea is the sensitivity
  design: the model ships every combination of low/central/high parameters as output
  (`output_data/baseline_2019_05/change_CR_results.csv`, 34 KB), which is a cleaner form of what
  the app's ETI-sweep band used to attempt before H4 replaced it.

### §2.4 Documentation-only, environment-locked, or single-account Excel models

Brief, as instructed.

- **`annualPartDEventSpendingSummary`** — SAS, 4 KB. One 5 KB program aggregating Medicare Part D
  prescription drug event records into annual spending by plan type (PDP vs MA-PD), aged vs
  disabled, brand vs generic, low-income-subsidy group, and **above vs below the catastrophic
  threshold** (`GDCA`/`GDCC`/`CPP`/`LICS`). Written against the CMS Virtual Research Data Center as
  of 11 October 2025; **no data ship and the code cannot run outside the VRDC**. Relevant to §6.2
  item 12 (the app carries one Part B base beside a three-channel Part D, and a 701.0% row) only as
  a **schema**: it names the exact cut CBO uses for Part D spending. No number in it.
- **`T-MSIS-Person-Summary-File`** — SAS, 288 KB. Builds the person-year Medicaid file behind CBO's
  Medicaid baseline. The README states it "will not function outside" an AWS Redshift instance
  holding T-MSIS Analytic Files, and is "released publicly as part of CBO's transparency efforts
  and may not be run by most readers". Ships two record-layout spreadsheets, no data.
- **`ma_encounter_data_cleaning`** — Python, 14 KB. One script post-processing the Jung et al. (2023)
  Medicare Advantage encounter pipeline in Redshift. Environment-locked; no data.
- **`ma_public_data_cleaning`** — Jupyter, 48 KB. Six notebooks assembling a CMS Medicare Advantage
  benchmark/enrolment panel 2008–2023 from public CMS URLs "as they existed on 1/27/2026". Runnable,
  but the app has no Medicare Advantage module and no MA preset.
- **`maintenance-delays-conventional-navy-ships`** — Stata, 6 KB. A "replication *skeleton*" for
  Appendix C of `https://www.cbo.gov/publication/61507`; the README says it "does not include
  proprietary data" and will not reproduce published estimates. No app relevance.
- **`MPFS-payment-increase-model`** — Excel, 43 KB. Sheets `README`, `Summary`, `1. MPFS FFS Model`,
  `2. Premiums and MA Model`, `License`. Budgetary effects of temporary Medicare physician fee
  schedule payment increases against CBO's February 2026 baseline. The app has no physician-payment
  policy; the workbook's Part B premium feedback structure is adjacent to the pharma module's Part B
  channel but scores a different lever.
- **`sanctions-penalty-model`** — Excel, 86 KB. Sheets include `Fiscal Year Projections`, `Adjusted
  Russia Projections`, `Country-Specific Data`, `Action-Based Data`, `ALLData`. Projects OFAC civil
  settlement revenue from settlements back to 2011. A revenue line the app does not model and would
  not be asked to.
- **`strategic-petroleum-reserve-model`** — Excel, 1.0 MB. Sheets `READ ME`, `SPR Sales Model`,
  `License`. Budget authority and outlays for the "Sale of Strategic Petroleum Reserve Oil" account.
  No app relevance.

---

## §3. Ranked opportunities

Ranked by **(value to a tier the app reports) × (tractability) ÷ (leakage risk)**. "Effect" is
stated as the tier and rows it can move, not as a promised improvement; several of these are
*checks*, whose best outcome is that nothing moves. Effort is lane-days on this repository's own
lane protocol (pre-register, then open a file).

| # | What | App module / constant | Effort | Expected effect | Leakage / circularity | CBO file |
|--:|---|---|--:|---|---|---|
| **1** | **Transcribe CBO's February 2026 baseline** — the FY2025–2036 budget path and the 38-series quarterly economic path — into the vintage the app already ships and defaults to | `fiscal_model/baseline.py` `_CBO_FEB_2026_ASSUMPTIONS` (`:68-84`), `_VINTAGE_CORPORATE_BASE_LEVELS` (`:195`), `CORPORATE_RECEIPTS_SOURCING` (`:220-224`), `VINTAGE_SOURCING` (`:163-168`); §6.2 item 30's residue | **3** | **No validation row moves — every surface a user reads does.** Ask's ten-year deficit is **$29,529.1B against CBO's own $23,143.3B (+27.6%)**; end-FY2035 debt is $49,362.1B against $53,103.2B (−7.0%); the corporate line compounds at 4.82%/yr against CBO's 3.53%; individual income tax is 18.3% low and payroll 11.0% high in FY2026. It also converts `CORPORATE_RECEIPTS_SOURCING` from `vintage_estimate` to `published_path` — the one grade `baseline.py` says may **not** be reported as "CBO's February 2026 corporate receipts" | **None** — a baseline is not a target, and no benchmark is scored on this vintage (the battery runs on `CBO_FEB_2024`). *Risk is breadth, not leakage:* Build's target strip, Ask's deficit and debt/GDP headline all move at once, and `tests/test_baseline_vintage.py` pins the `"sourced"` grade the lane must revisit | `budgetary-feedback-model/input/budget_baseline.csv`, `input/econ_baseline.csv` |
| **2** | **CBO's own discretionary spend-out vector** — 0.53 / 0.26 / 0.09 / 0.05 / 0.04, applied as `Σ_k s_k · ΔBA_{t−k}` | `fiscal_model/data_files/spending/outlay_rates.csv` (the NNLS fit); §6.2 item 16 | **1** | **Closes item 16 as a confirmation.** Tier 1 discretionary spending (n=5, 4.6%) and enacted-law spending (n=3, 13.4%). First comparison: app `operations_and_support` (0.5387, 0.2571, 0.0666, 0.0726, 0.0416) vs CBO (0.53, 0.26, 0.09, 0.05, 0.04) — mean abs 0.0118, max 0.0234, sums 0.9766 vs 0.97. **The likely outturn is that no number moves**, which is the point | **Low.** A different published source from the 14 donor options the profile was fitted on. *Caveat to pre-register:* CBO's vector is **one economy-wide profile** where the app has five account classes, and the BFM applies it only to discretionary BA — so it checks the O&S class and bounds the others; it cannot replace the account-class structure | `budgetary-feedback-model/input/rules_of_thumb.csv` col 115 `spout`; `bfm/outlays.py:587-593` |
| **3** | **Decompose `MARGINAL_REVENUE_RATE`** — one 0.25 → nine published marginal rates on nine NIPA series, plus fiscal-year phasing weights | `fiscal_model/constants.py:71`; `macro_adapter_frbus.py:351` `marginal_tax_rate=0.25`; `economics.py:493` | **3** | Dynamic scoring only — **no Tier 1 or calibrated row moves**, because no benchmark is scored dynamically. Changes the dynamic tab and Ask's dynamic answers. Also gives the app a *composition* channel it lacks entirely: a spending impulse lands on wages (0.19 + 0.10) and a corporate cut on profits (0.075) at very different feedback rates | **None.** No benchmark reads it | `budgetary-feedback-model/input/rules_of_thumb.csv` cols 93, 99, 100, 101, 16, 38; `input/parameters.csv:2-6`; `bfm/revenues.py:16-55` |
| **4** | **A ramp for `create_ss_donut_hole`** — CBO's own OASDI taxable-payroll path, $10,890.7B (FY2026) → $15,258.2B (FY2035), 3.82%/yr | `fiscal_model/payroll.py`; preset `ss_donut_250k`; §6.2 items 26 and 47 | **2** | Reconstruction tier: `ss_donut_250k` at **89.2%**. A flat annual is 17.0% high in FY2026 and 25.7% low in FY2034 against CBO's own path. Moves a shipped headline → **Decision 6 caption owed** | **Medium, and stated up front.** (i) The workbook is February 2026; the target is CBO Option 62 alt 2 from the December 2024 *Options* volume, so the shape input and the target would sit on different vintages — `iija_2021_discretionary.v2`'s precedent covers that but it must be declared. (ii) **Do not use the payroll path to construct a dollar target** — see §4.1 | `social-security-trust-funds-model/Social-security-trust-funds-model.xlsx`, sheet `Combined` row 7 |
| **5** | **A measured tariff price channel** — CBO's own universal-10% goods run at commodity level: PCE +0.585% / +1.035%, PEQ +3.159% / +4.327% | `fiscal_model/trade.py:142` `border_pass_through_rate = 1.00`, `:145` `consumer_pass_through_rate = 0.60`; §6.2 item 11 | **4** | The five trade rows sit at **43.6%** (`Trade`, n=5) and H8's outturn says the channel belongs *beside* the score, not inside it. This supplies the price side of that column with a CBO number rather than an asserted 0.60, and shows the scalar is wrong in a specific way: the same shock moves PCE by 5.85–10.35% of itself and equipment prices by 31.6–43.3% | **None.** The trade benchmarks are Tax Foundation / CRFB / Yale *revenue* scores; this is a *price index* from a different agency model. No constant in `trade.py` is fitted to any price index | `IO-price-model/outputs/uni10_goods_only_pce_2024.csv`, `uni10_goods_only_peq_2024.csv`; `io_price_model.ipynb` |
| **6** | **Published debt-service terms** — `rate1..rate11` ($55.06B per 1pp in period 1, decaying to $10.10B), `debt1..debt11`, `infl1..infl11` | `macro_adapter_frbus.py` `interest_cost = cumulative_deficit * 0.04` and `long_rate_ppts = debt_gdp_pct * 0.03`; `constants.py:79` `CROWDING_OUT_BASE = 0.03` | **3** | Dynamic tab only. Replaces two round numbers with a lag structure CBO publishes as a full lower-triangular matrix, and supplies the **Federal Reserve remittance** channel the app has no concept of (`fed_remit_int0..10`, `fed_remit_cpiu0..10`) | **None** | `budgetary-feedback-model/input/rules_of_thumb.csv` cols 17-27, 62-72, 80-90; `bfm/net_interest_costs.py` |
| **7** | **CBO's premium growth path for Option 56's excess share** — 7.149%, 5.252%, 4.837%, 4.531%, 4.444%, 4.571%, 4.587%, 4.622%, 4.655%, 4.722% | `fiscal_model/tax_expenditures.py` (`cap_employer_health`); §6.2 item 7 | **2** | Tier 1's one tax-expenditure row, **13.1%** | **HIGH — the only entry here where I would want an owner decision before the lane starts.** PGM's own README says its output "is used in CBO's health insurance simulation model (HISIM2)", and HISIM2 produces CBO's health estimates including Option 56's. Feeding CBO's premium projection into a model whose job is to predict CBO's option score is one step from `repeal_individual_amt`'s refused TPC input. Rank it below #1–#6 and register it as a *sensitivity*, not a replacement | `premium-growth-model/output/baseline_2026/pgm_2026.csv`, row `pchange_prem_demo_b2026` |
| **8** | **A five-class sensitivity grid**, as a presentation pattern | `fiscal_model/validation/credibility.py` (H4's bands); §6.2 item 58 ("the band is symmetric and the errors are not") | **2** | No scored number moves. H4's bands are class means and worst rows; CBO's financial-regulation repository ships every low/central/high parameter combination as output, which is how an **asymmetric** band gets built from the model rather than asserted | **None** | `financial_regulation_model/input_data/parameter_set.csv`, `output_data/baseline_2019_05/*.csv` |
| **9** | **Transfer-underreporting imputations for the distributional universe** | `fiscal_model/distribution.py`; the 7 distributional benchmarks (0.00–5.86pp, two circular) | **6** | Would align the app's income concept at the bottom of the distribution with the concept CBO's own tables rank on | **HIGH, and partly a licence question rather than a statistical one.** The README says in bold: *"These imputations should not be used for state-level analyses, causal analyses, or policy simulations."* The same CPS microdata drive `TaxCreditPolicy`. Also 542 MB against the repository's size policy, and two of the seven benchmarks are already circular | `means_tested_transfer_imputations/inputs/*.csv`, `docs/algorithm_description.md` |
| **10** | **Coverage-transition structure for the PTC repeal response** — alternative-coverage probability by FPL band and policy type; Medicaid valued at $12,517 / $3,895 / $2,208 / $1,581 by pathway | `fiscal_model/ptc.py`; `HIGH_STAKES_ACCURACY.md` §3 H11; `repeal_ptc` at 29.6% | **4** | A method, not a parameter: the app's PTC coverage response is a single published 19.28% share. CBO's structure is per-FPL-band transition probabilities with a valued alternative | **Low**, but the *levels* are Medicaid's, not the marketplace's, so nothing here can be lifted as a number | `medicaid-labor-supply-model/parameters/alternate_coverage_rates.yml`, `dollar_value_medicaid.yml`, `specification_params.yml:187-189` |

**If only two lanes are funded: #1 and #2.** #1 is the only entry here that changes what the app
tells a user about *today's budget* rather than about a policy, and it is a data edit the app's own
source comment already specifies (`baseline.py:214-219`). #2 is a one-day check that closes a
carry-over item the repository has recorded as blocked three times and is likely to *confirm* work
already done — which is worth more to the honesty of the scorecard than any single row would be.

**A note on how these rank against the existing plan.** None of them moves a Tier 1 row, because no
CBO repository publishes a policy score (§4.3). Read against `HIGH_STAKES_ACCURACY.md` §1.1's
criterion, that is not a demotion: #1 fails the "is it a score" test and passes salience, magnitude
and reach more comprehensively than any row in §1.2's table, since the ten-year deficit appears on
the landing page, inside every Build package's target strip, and in the Ask assistant's
`get_cbo_baseline` tool output. #2, #3 and #6 are all *inputs to the numbers already ranked*
rather than rows of their own.

---

## §4. Checked and rejected, with reasons

### §4.1 The OCACT-to-dollars conversion: constructible, and contradicted

`HSA_h13_payroll_targets.md` §5 declined to convert OCACT's percent-of-taxable-payroll into
dollars, on the rule that *"a conversion this repository performs is a target this repository
constructed"*, and recorded that the whole finding was that the conversion is unpublished. **The
denominator is now published**, in the repository at §2.1, so the conversion is available. I did it,
and it fails.

Taking OCACT's E2.5 annual income-rate path as H13 transcribed it (1.85% of payroll in 2026 rising
to 2.50% in 2034) against CBO's own implied taxable payroll from the SS trust funds workbook
(`scratchpad/e25_check.py`):

| | 2026 | 2034 |
|---|---:|---:|
| OCACT E2.5 rate × CBO payroll | **$201.5B** | **$368.1B** |
| CBO Option 62 alt 2, same donut design | **$122.0B** | **$192.0B** |
| ratio | **1.65×** | **1.92×** |

Over FY2026–2034 the construction totals **$2,543.9B** against the carried target of **$1,426.8B**.
Two published CBO/SSA sources describing the same reform therefore disagree by a factor that
*widens* across the window. The gap is larger than the income-and-payroll offset (~25%) can
explain, so at least one of three things is true: OCACT's income-rate denominator is not
`revenue ÷ 0.124`; the two agencies' earnings distributions above the cap differ materially; or the
OCACT figure is a trust-fund income concept rather than a unified-budget one.

**Recommendation: do not convert, and record the magnitude.** H13's refusal stands and is now
demonstrated rather than argued — which is the same upgrade PR #131 gave to the refusal of
`repeal_ptc`'s −$1,100B. The payroll path remains usable as a **shape** (opportunity #4) precisely
because a shape does not inherit the level disagreement.

### §4.2 Rejected outright

- **`conditional_forecasting_with_bvar`** — May 2022 data, publicly-available variables only, and
  the README states it does not reproduce the paper. The app conditions nothing on a rate path.
- **`state-unemployment-rate-model`** — UI Extended Benefit triggers by state. The app's state
  module is about SALT interaction, a different question entirely.
- **`markov-switching-macrosimulation-model`** — **forecast** uncertainty, where H4 deliberately
  shipped **model-error** bands. Substituting one for the other would be a category error, and a
  flattering one, since forecast bands are wider than H4's and would make every row look contained.
  Requires four externally downloaded files and a user-supplied forecast besides.
- **`discount-factors`** — the app discounts nothing.
- **`annualPartDEventSpendingSummary`, `T-MSIS-Person-Summary-File`, `ma_encounter_data_cleaning`** —
  no data ship and the code is locked to CMS VRDC or a CBO Redshift instance. The Part D repository
  is worth one sentence in a future pharma lane as a *schema* (above/below catastrophic × LIS ×
  brand/generic × PDP/MA-PD), not as a source.
- **`maintenance-delays-conventional-navy-ships`, `sanctions-penalty-model`,
  `strategic-petroleum-reserve-model`, `MPFS-payment-increase-model`, `ma_public_data_cleaning`,
  `hepatitis-c-model`, `legal-status-model`, `permitting-model`** — well-built models of budget
  accounts and policy domains this app does not score. `permitting-model` is the one to come back
  to if a supply-side investment channel is ever scoped, and `hepatitis-c-model`'s
  `docs/hep_c_param_sources.md` is worth reading once as a model of parameter provenance writing.

### §4.3 Things I looked for and did not find

- **No CBO repository publishes a revenue score for any policy in this app's battery.** Not one of
  the 34 repositories contains a policy-by-policy revenue table of the kind `cbo_scores.py` carries.
  The *Options* volumes remain the only source for those, and they are on cbo.gov behind the 403.
  **No new Tier 1 or Tier 2 validation target comes out of this survey**, and the roadmap should not
  expect one from the macro side.
- **No FRB/US multiplier documentation.** `FRBUSAdapterLite`'s 1.4 / −0.7 / 0.75 / 0.15 / 0.65
  (`macro_adapter_frbus.py:347-352`) remain sourced to "Fed analysis of FRB/US fiscal multipliers"
  with no citation. CBO's organisation does not publish FRB/US multipliers; the `markov-switching`
  repository merely *consumes* an FRB/US data file. That gap is unchanged by this survey.
- **No spend-out rates by account.** CBO's account-level rates (publications 61913, 62256) named in
  §6.2 item 16 are still only on cbo.gov. What the BFM gives is one economy-wide vector — enough for
  a check, not enough to replace the five-class structure.
- **No earnings distribution above the OASDI taxable maximum**, which is what a donut-hole design
  actually needs, and no FSA/HRA/HSA contribution levels, which is the base half of §6.2 item 7.
- **cbo.gov's 403 is unchanged.** Every fetch in this survey went through the Internet Archive.
  Anyone planning a lane that needs a cbo.gov PDF should plan for that, and should note that the
  GitHub organisation is *not* blocked — which is, on its own, an argument for preferring a CBO
  repository to a CBO publication wherever both carry the same number.

---

## Appendix — how to reproduce

Clones (read-only, `--depth 1`) and scratch scripts live under the session scratchpad
`…/scratchpad/cbo_macro/`. The four derivations quoted above:

| Claim | Script | Inputs |
|---|---|---|
| Implied OASDI taxable payroll, 3.8179%/yr CAGR | `scratchpad/ss_calc.py` | `social-security-trust-funds-model/Social-security-trust-funds-model.xlsx` |
| PCE +0.585%/+1.035%, PEQ +3.159%/+4.327% | `scratchpad/io_agg.py` | `IO-price-model/outputs/uni10_goods_only_{pce,peq}_2024.csv` |
| OCACT × CBO payroll vs CBO Option 62 alt 2 | `scratchpad/e25_check.py` | the workbook above + `HSA_h13_payroll_targets.md` §6.4 |
| Rules-of-thumb series by year | `scratchpad/rot.py` | `budgetary-feedback-model/input/rules_of_thumb.csv` |
| CBO Feb 2026 annual economic averages and budget path | `scratchpad/vintage_check.py` | `budgetary-feedback-model/input/{econ,budget}_baseline.csv` |

The app-side figures in §1 finding 1 come from one read-only call, quoted in full so it can be
rerun:

```python
from fiscal_model.baseline import CBOBaseline, BaselineVintage, APP_DEFAULT_START_YEAR
p = CBOBaseline(start_year=APP_DEFAULT_START_YEAR,
                vintage=BaselineVintage.CBO_FEB_2026).generate()
# sum(p.deficit) -> 29529.1 ; p.debt_held_by_public[-1] -> 49362.1
# p.corporate_income_tax[0], [-1] -> 436.8, 667.4
# p.individual_income_tax[0] -> 2248.9 ; p.payroll_taxes[0] -> 2027.1
```

Nothing in this memo was written into the app. No constant was changed, no target was registered,
no scorecard row moved, and the test suite was not run.
