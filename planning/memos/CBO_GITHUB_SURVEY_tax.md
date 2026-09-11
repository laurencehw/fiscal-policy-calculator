# Survey of CBO's public GitHub — the tax and revenue repositories

*Written 2026-09-11 against `main` @ `20e356d`, branch `memo/cbo-github-survey-tax`.
No app file was opened for editing and no scored number moved. Twelve repositories were cloned
read-only (`git clone --depth 1`) into scratch; every parameter value below was read out of the
clone, and every `file:line` in the app column was read out of this worktree. A sibling memo,
`CBO_GITHUB_SURVEY_macro.md`, covers the macro/health/spending repositories; a route-to-8.5
roadmap will be written from both.*

---

## §0 — Verification: is `github.com/US-CBO` really CBO?

**Verdict: yes, established from cbo.gov's own pages. Treat the organisation as authentic and the
repositories as CBO work product.** `gh api orgs/us-cbo` reports `is_verified: false`, but that
flag records only whether GitHub has performed *domain verification*; it is not evidence either
way about authorship. The org metadata is consistent — `blog: https://www.cbo.gov`,
`email: communications@cbo.gov`, `created_at: 2020-05-07T18:47:29Z`, 33 public repos — and four
independent pieces of evidence on cbo.gov's own domain settle it.

**An obstacle worth recording, because it is also the memo's thesis.** `www.cbo.gov` returns
**HTTP 403** to this environment for every URL tried — publication pages, `/system/files/*.pdf`,
and through three separate proxies (`r.jina.ai`, `api.allorigins.win`, `api.codetabs.com`), with
Googlebot and browser user-agents alike. This is not new: the repository already records it at
`fiscal_model/baseline.py:215-219` and `fiscal_model/corporate.py:184-186`. The evidence below was
therefore read from **Internet Archive snapshots of cbo.gov**, which serve CBO's own HTML
unmodified; snapshot timestamps are given so the record can be re-checked.

**Evidence 1 — cbo.gov's site-wide footer links to the organisation.** Every cbo.gov page carries a
social-icon row whose GitHub entry is `<a href="https://github.com/US-CBO" rel="noopener"
target="_blank">` with `alt="CBO Github" title="CBO Github"`, served from
`cbo.gov/themes/custom/cbo/images/social-icons/github.svg`. Read from the archived
`https://www.cbo.gov/publication/61388`, snapshot `20260519070132`. A link in a site's own theme
footer is the strongest ownership assertion a site can make short of DNS verification.

**Evidence 2 — a publication page links to a specific repository, in its body text.**
*CBO's Conventional Tariff Analysis Model*, `https://www.cbo.gov/publication/61388`, a
Presentation dated **May 5, 2026** (snapshot `20260519070132`). Verbatim, from the Summary body
field, with the hyperlink target given in brackets:

> "One such framework is the Conventional Tariff Analysis Model
> [`https://github.com/US-CBO/conventional-tariff-analysis-model/blob/main/README.md`], which is
> used to estimate the effects of tariffs on revenues and imports from each U.S. trading partner."

**Evidence 3 — a CBO blog post describes the practice and links to three of these repositories.**
*How CBO Shares Its Models*, `https://www.cbo.gov/publication/61878`, **November 19, 2025**
(snapshot `20260711204031`). Verbatim:

> "When practicable, we post data, computer code, and documentation associated with our models on
> the web-based platform known as GitHub. Users can examine those resources and explore outcomes
> under alternative scenarios."

and

> "GitHub is an online platform that allows people and organizations around the world to share
> their computer code and other data. In May 2020, CBO began sharing data, code, and other
> documentation on that platform."

**"In May 2020" matches the organisation's `created_at` of 2020-05-07 to the month.** The page's
body links to `github.com/US-CBO`, `github.com/US-CBO/captax`, `github.com/US-CBO/eval-projections`
and `github.com/US-CBO/premium-growth-model`.

**Evidence 4 — a cbo.gov publication exists whose title is the practice itself.** *CBO's Use of
GitHub*, `https://www.cbo.gov/publication/59820`, **December 19, 2023** (snapshot `20260520104314`),
whose entire abstract reads: "This presentation describes CBO's use of GitHub and the code and data
the agency has made available on the site." Its body links to `github.com/US-CBO`. Two further
cbo.gov pages surfaced in search with titles of the same kind and were **not** fetched, so they are
cited as titles only and not quoted: *CBO Expands Modeling Resources on GitHub*
(`cbo.gov/publication/62152`) and *Advanced Models and Details* (`cbo.gov/models/details`).

**Licensing.** Every one of the twelve repositories ships a `LICENSE.md` placing the contents in the
public domain. Two wordings are in use. The older one (captax, CPS-tax-filing-units, eval-projections,
conventional-tariff-analysis-model, EmpElastR, business-investment-model, electric_vehicle_model,
discount-factors): "created by CBO employees in their official capacity. Therefore, they are not
subject to copyright and are in the public domain in the United States." The newer one (cbo-data,
budgetary-feedback-model, credit-subsidy-tool, rules-of-thumb-model): "As a work of the United
States Government, these materials are in the public domain within the United States under
17 U.S.C. § 105. The United States Government waives any other intellectual property rights in
these materials worldwide." Both request attribution of modifications; several add "Users may not,
however, modify the package and then present it as official government material." **Nothing here is
copyright-encumbered and nothing needs a licence header beyond attribution.** This matters for the
repository hygiene rule in the global instructions: these are small text/CSV artefacts, publishable.

---

## §1 — Summary

The tax half of CBO's GitHub organisation is worth more to this app than the ratio of "interesting
code" to "usable data" would suggest, and for a reason that has nothing to do with modelling: **it
is a live, machine-readable channel to CBO's own published tables from inside a build that cannot
reach cbo.gov.** Every CBO input in this repository today is a hand transcription of a PDF or XLSX
into a CSV or a Python literal, and `baseline.py:595-600` says in as many words that the remaining
GDP-ratio reconstructions persist because "no vintage-specific published table for them can be
reached from this environment." Three repositories close that: **`cbo-data`** (public domain,
v0.2.0 2026-06-12) is a vintage-aware CSV mirror of *Budget and Economic Data* whose thirteen
datasets include a 336-variable ten-year budget on three vintages, a 166-variable revenue detail
carrying **CBO's own annual revenue effect of every major tax act since 1981**, a 53-variable
individual-income-tax base projection, a 159-variable statutory-parameter file with brackets, AMT,
EITC, CTC and SALT limits **by filing status and year**, and 1,712 budget accounts with budget
authority *and* outlays; **`budgetary-feedback-model`** ships CBO's February 2026 budget and
economic baseline as two small CSVs plus a published rule-of-thumb table of effective marginal tax
rates by income type; and **`conventional-tariff-analysis-model`** ships JCT's income-and-payroll
offset as a *year path* (0.244 → 0.241, not a flat 0.25), the Section 232 HTS lists at article
level, two sourced elasticity files, and CBO's own FY2026–2035 tariff revenue score of
**$2,380.6B**. Beyond the data, three repositories supply *methods* the app has no version of at
all: `captax` is a complete effective-marginal-tax-rate engine with a fully documented parameter
dictionary (and the app has no user-cost-of-capital machinery anywhere — grepped and confirmed);
`business-investment-model` publishes the **0.80/0.85 loss-firm-and-nonprofit haircut** that is the
direct rebuttal to this model's 80.8–90.8% implied marginal corporate base; and `eval-projections`
publishes the error-measurement discipline — legislative adjustment before error, percent-of-GDP
denominators, and a two-thirds spread instead of a mean — that `HIGH_STAKES_ACCURACY.md` §2 has
been reaching for by hand. Four repositories (`EmpElastR`, `electric_vehicle_model`,
`credit-subsidy-tool`, `discount-factors`) are near-zero for this app and are recorded in §4 with
reasons.

---

## §2 — Per-repository entries

Repository sizes and last-push dates are from `gh api orgs/US-CBO/repos`. All `file:line`
references in the *CBO* column are inside the clone; all in the *app* column are inside this
worktree.

---

### 2.1 `cbo-data` — the one that changes the roadmap

**License.** Public domain, 17 U.S.C. § 105 wording, worldwide IP waiver. **Language/size.** Python
ETL, 8,011 KB, last push 2026-06-12. **Version 0.2.0, initial release 2026-05-27** — this is the
newest repository in the organisation and did not exist when any prior wave of this project was
planned.

**What it is.** Its own README: *"Standardized, versioned data from public Congressional Budget
Office (CBO) releases. This repository transforms CBO spreadsheets and tables into CSV outputs with
consistent variable names, schemas, and vintage-aware organization."* `catalog.json` is a DCAT
catalogue whose description states the primary audience explicitly: *"Machine-readable, tidy
versions of CBO's Budget and Economic Data. Primary audience: AI agents and automated systems."*
It accompanies no single publication; each dataset carries its own `publication_id` and
`landingPage`. It does not replace cbo.gov — "The canonical source of data remains Budget and
Economic Data" — but it is a faithful, schema'd, multi-vintage copy.

**Thirteen datasets, each with its own `schema.json` and a `vintages` list.** The ones that matter
here, with the vintages actually shipped:

| dataset | pub | vintages | fields | what it is |
|---|---|---|---|---|
| `ten_year_budget` | 51118 | 2024-06, 2025-01, **2026-02** | 336 | full ten-year budget, FY2025–FY2036, plus CBO's own `chg_leg_* / chg_econ_* / chg_tech_*` baseline-change decomposition and discretionary funding by budget function |
| `revenue_detail` | 51138 | same three | 166 (FY) + 53 (IIT) | receipts by source and excise line; **42 `leg_rev_*` series**, one per enacted act; a separate `annual_cy_iit_*.csv` with the individual income tax base |
| `tax_parameters` | 53724 | same three | 159 | statutory parameters **by filing status by year**, plus CBO's EMTRs on labour and capital |
| `spending_detail` | 51142 | same three | 12 | 21,769 rows = **1,712 budget accounts × 11 fiscal years**, each with `budget_authority` *and* `outlays`, `function_code`, `subfunction_code`, `disc_or_mand` |
| `historical_budget` | 51134 | 2024-02, 2025-01, 2026-02 | 66 | actuals |
| `trust_fund` | 51136 | same three | 51 | ten-year OASDI/HI trust fund projections |
| `automatic_stabilizers` | 51139 | 2023-06, 2024-11 | 20 | cyclical adjustment |

Economic datasets (`historical_economic` 84 fields back to 1949q1, `economic_projections` 148
fields on five vintages, `long_term_economic`, `demographic`, `potential_gdp`) are the sibling
memo's.

**Key parameters, with paths.** `data/budget/tax_parameters/annual_cy_2026-02.csv` is 150 variables
× CY2025–CY2036 in long format. It carries all seven statutory rates (`tp_rate_1..7`) and all seven
bracket boundaries in four filing statuses (`tp_bracket_1..7_{single,mfj,mfs,hoh}`) — e.g.
`tp_bracket_7_mfj` = 751,600 (CY2025) → 768,700 (CY2026) → 944,800 (CY2036), `tp_bracket_7_single`
626,350 → 640,600 → 787,325; AMT exemptions, phase-outs and both AMT rates by status
(`tp_amt_exemption_mfj` 137,000 → 140,200 → 172,300); sixteen EITC parameters by number of children
(`tp_eitc_phasein_rate_*`, `tp_eitc_max_credit_*`, `tp_eitc_phaseout_{single,mfj}_*`); five CTC
parameters (`tp_ctc_per_child` 2,200 in CY2025–26 → 2,400 by CY2030 → 2,700 by CY2035,
`tp_ctc_refund_rate`, `tp_ctc_refund_threshold`, `tp_ctc_max_refundable`,
`tp_ctc_per_other_dependent`); **SALT limits by filing status** (`tp_salt_limit_{single,mfj,mfs,hoh}`);
standard deductions by status; `tp_ss_max_earnings`; and both price indices (`tp_cpi_u`,
`tp_c_cpi_u` 173.016 → 217.680). It also carries **CBO's own effective marginal tax rates**:
`tp_emtr_labor_combined` 27.206 (CY2026) → 28.581 (CY2036), split
`tp_emtr_labor_iit` 18.402 → 19.868 and `tp_emtr_labor_payroll` 8.803 → 8.713; and 38
capital EMTR and tax-wedge series including `tp_emtr_capital_business_c_corp` 12.30 → 15.82 and
`tp_emtr_capital_business_passthrough` 18.96 → 21.21.

`data/budget/revenue_detail/annual_cy_iit_2026-02.csv` is CBO's projection of the individual income
tax base: `rev_iit_agi` 18,810.4 (CY2026) → 25,817.9 (CY2035); `rev_iit_taxable_income` 14,245.168
→ 20,313.807; `rev_iit_taxable_ordinary` and `rev_iit_taxable_capgains_divs` separately;
`rev_iit_capital_gain_loss` 1,703.5 → 1,786.6; `rev_iit_qualified_dividends`; tax by each of the
seven brackets (`rev_iit_tax_bracket_1..7`); `rev_iit_returns_total`, `rev_iit_returns_itemized`,
`rev_iit_returns_amt`; `rev_iit_qbi_deduction`, `rev_iit_niit`, `rev_iit_eitc`,
`rev_iit_child_tax_credit`; and AGI shares for the top 1/5/10/25/50 percent (top 1% = 23.5% in
CY2026).

`data/budget/revenue_detail/annual_fy_2026-02.csv` carries 42 `leg_rev_*` series — the **annual
revenue effect of each major act**, in dollars and as a share of GDP: `leg_rev_tcja` FY2018–FY2027,
`leg_rev_obbba_25` FY2025–FY2035 (−130.905 in FY2025 → −500.987 in FY2035), `leg_rev_ira_22`,
`leg_rev_arpa_21`, `leg_rev_cares_act`, `leg_rev_atra_12`, `leg_rev_egtrra_01`,
`leg_rev_tax_reform_86`, `leg_rev_obra_93`, back to `leg_rev_econ_recovery_81`.

**Maps onto.** `fiscal_model/baseline.py` (all three vintages), `fiscal_model/policies_core.py`'s
generic base, `fiscal_model/amt.py`, `fiscal_model/credits.py`, `fiscal_model/tax_expenditures_core.py`
(SALT), `fiscal_model/data/capital_gains.py`, `scripts/fit_outlay_rates.py`,
`fiscal_model/validation/preregistered.py`.

**What it does not offer.** No policy scoring of any kind — it is data, not a model. No pre-2024
budget vintages (the app's `CBO_FEB_2024` is the oldest shipped, and `eval-projections` is where
older vintages live). No microdata. No distributional tables. The catalogue is regenerated on
release, so a consumer must pin a commit or a `vintage` string; the `generated` field
(`2026-05-14T19:49:19Z`) is the only freshness stamp inside the catalogue itself.

---

### 2.2 `conventional-tariff-analysis-model` (CTAM)

**License.** Public domain, older wording. **Language/size.** Python, 7,052 KB, last push
2026-02-17.

**What it is.** README: *"The Conventional Tariff Analysis Model (CTAM) is a Python-based tool that
pulls U.S. import data, processes tariff policy, and estimates changes in import flows and customs
revenue resulting from those policies. This model is used in the agency's conventional budgetary
analysis of tariff policy changes and its estimates do not account for the economic feedback effects
from those tariff policy changes."* It replicates *CBO's Updated Projections of the Budgetary
Effects of Tariffs as of November 15, 2025*, `https://www.cbo.gov/publication/61877` (blog post
November 20, 2025); the model itself is described at `https://www.cbo.gov/publication/61388`
(Presentation, May 5, 2026).

**Data shipped.** `inputs/base_imports/all_countries_2024_CY_2025-11-12.csv` — Census Bureau import
data, calendar 2024, pulled 2025-11-12 (`config/default.yaml` `data.pull_date`, `data.year`).
`inputs/cmac_imports/CBO_Jan_2025_nominal_goods_projection.csv` — CBO's own nominal goods-import
growth path. `inputs/hts_lists/` — **eighteen HTS article lists** including `alum_steel.csv`,
`alst_deriv_h.csv` / `alst_deriv_l.csv` (high- and low-metal-content derivative products),
`copper.csv`, `autos.csv`, `auto_parts.csv`, `trucks_*.csv`, `wood.csv`, `annex_2_september.csv`
(reciprocal exemptions), `aircraft.csv`, `pharma_inputs.csv`, `reimports_and_mil.csv`.
`inputs/usmca/usmca_utilization_rates.csv` — product-by-product. `inputs/offset/2025OffsetPostHR1.csv`.
`inputs/elasticities/` — two files.

**Key parameters, with file:line.** All of the following are in `config/default.yaml`:
`CTAM.exporter_absorption: 5` (line 96 — "Percentage of tariff rate increase absorbed by
exporters"); `tariffs.misc_params.alum_steel_deriv_high_share: 0.75` and
`alum_steel_deriv_low_share: 0.25` (the metal-content shares of the two derivative lists);
`copper_deriv_share: 0.90`; `civil_aircraft_share: 0.50`; `ca_usmca_cost: 3` /
`mx_usmca_cost: 3` (ad-valorem equivalents of complying with USMCA rules of origin, explicitly
non-revenue-generating); `us_content_{ca,mx}_autos: 0.50 / 0.35`; `auto_parts_rebate: -5`; plus
every statutory rate as of 15 November 2025 (`alum_steel_rate: 50`, `auto_rate: 25`,
`ca_base_rate: 35`, `mx_base_rate: 25`, `eu_capped_rate: 15`, `china_added_rate: 10`,
`ru_alum_rate: 200`, and 15 more). `CTAM.actuals: {'2025': 86.495}` is actual 2025 tariff revenue,
defined in the same line as "difference between Treasury-reported customs revenue and January 2025
base (incl. JCT offset)".

The **JCT income-and-payroll offset** is `inputs/offset/2025OffsetPostHR1.csv`, an eleven-row
year path: **0.244 (2025), 0.247, 0.247, 0.247, 0.245, 0.243, 0.243, 0.242, 0.242, 0.242,
0.241 (2035)**. It is applied multiplicatively at `code/model/add_offset.py:22`
(`df[str(year)] *= (1 - offset_value)`), immediately followed by the calendar-to-fiscal conversion
at `add_offset.py:26` — `df[y] = df[y-1] * 0.2976 + df[y] * 0.7024`.

`inputs/elasticities/boehm_elasticities.csv` carries a `final_path` rising 0.5517 (2025) → 0.8125 →
0.8967 → 0.9825 → 1.1483 → 1.2750 → 1.4750 → 1.7750 → 1.9175 → 2.0408 (2034–35), built from
`elas_partial_yr` and `elas_full_yr` columns with a `months_till_june` weight of 7.
`inputs/elasticities/centered5_f2f_constructed_elas.csv` is 110 NAICS-4 foreign-to-foreign
substitution elasticities (1111 → 4.642, 1112 → 3.626, …).

> **Correction (2026-09-11, from PR #164's lane, `planning/lanes/R8_tariff_ctam.md` finding 3).**
> This paragraph and §3 row 11 below both described `boehm_elasticities.csv` as a **"time-varying
> import-demand elasticity"**. **It is not one.** `code/model/CES_time_path.py:14` normalises
> `final_path` to **1.0 at t+10** and `:48-50` then *multiplies* the 110 NAICS-4 substitution
> elasticities in `centered5_f2f_constructed_elas.csv` by it, with nesting divisors 1.0 / 1.5 / 2.0
> at `:53-55`. The published 0.5517 → 2.0408 is therefore a **time shape on a CES nest**, and the
> two files are one object rather than two. It cannot be dropped into `trade.py`'s
> `import_price_elasticity` slot — that would be a category error — so route-doc move R8.3 was
> **refused on the merits** rather than deferred. Taking it means building the nest, which is its own
> lane. The residual the move was meant to address has been measured instead and is
> `MODELING_IMPROVEMENT.md` §6.2 item 73: the unsourced trio at `trade.py:172-174`, which at a 46pp
> increment asserts imports fall **62% in year one** and accounts for the whole of the gap in R8's
> one external control (Tax Foundation's 50% steel regime at −$341.4B against the module's
> −$190.95B on the new HS-10 base).

**Published outputs, committed.** `outputs/replication/fy_revenue_summary.csv` gives fiscal-year
customs revenue by country for the November 15, 2025 policy: **2026–2035 total $2,380.58B**, of
which China $490.40B, Rest of World $1,216.33B, USMCA Mexico $137.92B, Japan $134.33B, Germany
$133.84B, USMCA Canada $103.23B, Non-USMCA Mexico $104.22B, Non-USMCA Canada $60.31B.
`outputs/replication/cy_implied_import_decline_pct.csv` gives the implied import decline: total
16.49% over the period, 7.46% in 2025 rising to 22.40% by 2035; China 25.57%; Non-USMCA Canada
43.88%.

**Maps onto.** `fiscal_model/trade.py` in its entirety.

**What it does not offer.** It is conventional by design — there is no macro feedback channel, which
is the same position PR #150 arrived at independently. It is a *policy replication*, not a general
scenario engine: the shipped configuration encodes one specific November-2025 tariff schedule, and
a user wanting "a 10% universal tariff" would have to write a tariff specification rather than set a
switch. `code/api.py` pulls from the Census API, which needs network; the shipped `base_imports`
file avoids that. And nothing in it is fitted to the app's presets, which is why it is usable — but
by the same token nothing in it answers "what would a hypothetical 60% China tariff raise", which
is what four of the app's five trade presets ask.

---

### 2.3 `captax` — CBO's Capital Tax model

**License.** Public domain, older wording. **Language/size.** Python 3.8, 8,678 KB, last push
2026-02-17. **Version 0.8.0, 2026-02-17**, and its `CHANGE_LOG.md` states the vintage precisely:
parameters "consistent with CBO's February 2026 economic projections" and the data supplementing
*The Budget and Economic Outlook: 2026 to 2036* (`cbo.gov/publication/61882`), and
**"Incorporated tax provisions in the 2025 reconciliation act (Public Law 119-21)."**

**What it is.** README: CBO uses it *"to estimate federal effective marginal tax rates (EMTRs) on
marginal investments for the U.S. economy and in finer detail by industry, asset type, legal form of
organization (C corporations versus pass-through entities, for example), and source of financing
(debt versus equity)."* Documented in Working Paper 2022-01, *CBO's Model for Estimating the Effect
of Federal Taxes on Capital Income from New Investment*, `https://cbo.gov/publication/57429`.

**Key parameters, with paths.** `captax/data/inputs/environment_parameters/environment_parameters.csv`
is eighteen scalars, each with a sourced entry in `docs/environment_parameters.md`:
`nonfinancial_c_corp_debt_share 0.2697`, `nonfinancial_pass_thru_debt_share 0.3047`,
`financial_sector_debt_share 0.4722`, `ooh_debt_share 0.4013` (all "CBO, based on the Financial
Accounts of the United States (2001-2024)"); `c_corp_equity_retained_earnings_share 0.5`;
`c_corp_equity_repurchases_share 0.6`; `nominal_rate_of_return_equity 0.0877` ("10-year Treasury
bonds plus an equity premium"); `nominal_rate_of_return_debt 0.0682` ("corporate bonds rated Baa");
`inflation_rate 0.0226`; `avg_local_prop_tax_rate 0.0086` ("2023 American Housing Survey"); and —
directly relevant to `fiscal_model/data/capital_gains.py` — **`cap_gains_at_death_share 0.4316`**,
`cap_gains_short_term_share 0.0286`, `cap_gains_long_term_holding_period 9.1096` years,
`cap_gains_at_death_holding_period 30` years, sourced to "SOI Sale of Capital Assets (2007-2015) and
SOI Estate Tax Returns (2007-2016)".

`captax/data/inputs/policy_parameters/policy_parameters_Current-Law_comprehensive.csv` is
**69 current-law policy parameters × 2026–2036**. Its first eleven columns are CBO's own weighted
average marginal tax rates by income type: `c_corp_tax_rate` 0.21 flat (source "Internal Revenue
Code … 0.2100 by statute"); `pass_thru_tax_rate` 0.3042 (2026) → 0.3164 (2036), source **"CBO's
Microsimulation Tax Model"**; `dividend_inc_tax_rate` 0.1997 → 0.2063; `cap_gains_long_term_tax_rate`
**0.2116 (2026)** → 0.2052 (2036), source **"CBO individual income tax model"**;
`cap_gains_short_term_tax_rate` 0.3495 → 0.3339; `interest_inc_from_biz_tax_rate` 0.3036 → 0.3089;
`seca_tax_rate` 0.0352. It also carries `c_corp_interest_deductible_share 0.9884` and
`pass_thru_interest_deductible_share 0.9933` (the §163(j) bite, measured), and the §199A inputs
`pass_thru_inc_share_below_thresholds 0.3225` and `pass_thru_eligibility_below_thresholds 0.7734`.

Other shipped matrices: `economic_depreciation.csv` (95 detailed industries × 84 asset types, "CBO,
based on 2023 BEA Detailed Fixed Asset tables"), `debt_shares.csv` (industry × legal form, "SOI
Nonfarm Sole Proprietorship, Partnership, and Corporate Returns (2020-2022)"), recovery periods,
acceleration rates, straight-line flags, inflation adjustments, §179 expensing shares for C corps
and pass-throughs separately, other expensing shares (permanent and temporary), ITC rates and
non-depreciable bases, and PTC rates for each of 2026–2033 plus a permanent file.

**Committed outputs.** `captax/data/outputs/Current-Law/comprehensive/summary_2026_2036_*.csv`
(255 KB) gives `req_before_tax_returns`, `req_after_tax_returns_savers`, `total_tax_wedges`,
`total_EMTRs`, `c_corp_EMTRs` and dollar `weights` by asset aggregate × legal form × financing ×
year 2026–2036, with a parallel `uniformity` run; plus three 2026 cross-tabs and two supplemental
XLSX tables. Model constants are in `captax/constants.py` (`START_YEAR = 2026` at :13,
`NUM_YEARS = 11` at :11, `NUM_DETAILED_INDS = 95` at :24).

**Maps onto.** `fiscal_model/corporate.py` (which has no EMTR or user-cost machinery at all),
`fiscal_model/data/capital_gains.py`, and the H3b lane in `HIGH_STAKES_ACCURACY.md` §3.

**What it does not offer.** **CapTax computes rates, not revenue.** It returns EMTRs and tax wedges;
it never produces a dollar figure, a tax base or a ten-year score, so it cannot on its own supply a
validation target or replace `BASELINE_TAXABLE_PROFITS_BILLIONS`. Its weights are investment flows
in millions, not taxable profits. Running it needs a `conda` environment (Python 3.8), which is a
real obstacle against this machine's Python 3.14; the *inputs and outputs*, however, are plain CSV
and need nothing.

---

### 2.4 `budgetary-feedback-model` (BFM)

**License.** Public domain, 17 U.S.C. § 105 wording. **Language/size.** Python, 46 KB, last push
2026-07-13 — the most recently updated repository in this set.

**What it is.** README: *"The Budgetary Feedback Model (BFM) is one of the tools that CBO uses to
estimate how changes in the macroeconomy affect the federal budget… The model uses CBO's baseline
economic and budget projections, together with a set of rules of thumb, to estimate the budgetary
effects of specified economic scenarios."* It builds on CBO's 2020 working paper *A Simplified Model
of How Macroeconomic Changes Affect the Federal Budget*, `https://www.cbo.gov/publication/55884`.
The README states both vintages exactly: baselines from *The Budget and Economic Outlook: 2026 to
2036* (`cbo.gov/publication/61882`, February 2026), rules of thumb from *How Changes in Economic
Conditions Might Affect the Federal Budget: 2026 to 2036* (`cbo.gov/publication/62257`, April 2026).

**Data shipped.** Six CSVs in `input/`. `budget_baseline.csv` is 38 rows × 11 columns —
`Individual income taxes`, `Payroll taxes`, `Corporate income taxes`, `Other revenues`,
`Mandatory outlays`, `Discretionary outlays`, `Net interest outlays`, `Total deficit (-)`,
`Primary deficit (-)`, `Debt held by the public`, by year. FY2026 reads: individual 2,751.29,
payroll 1,825.57, **corporate 403.98**, other 196.69, mandatory 4,529.34, discretionary 1,880.30,
net interest 1,038.98, deficit −1,852.70, debt 32,095.17. `econ_baseline.csv` and
`alternative_economics.csv` are the economic side (38 variables including `gdp`, `gdpfe`, `pgdp`,
`r10yr`, `rbaa`, `ruc`, `wsd`, `zb`, quarterly from 1995q1). `parameters.csv` is sixteen scalars.
`rules_of_thumb.csv` is 12 rows (2025–2036) × 120 columns, each documented in `glossary.md`.

**Key parameters, with file:line.** `input/parameters.csv` holds **calendar-to-fiscal-year weights
by revenue source**: `ind_fy_wt 0.75`, `cg_fy_wt 0.45`, `fica_fy_wt 0.75`, `seca_fy_wt 0.36`,
`corp_fy_wt 0.64`, `duties_fy_wt 0.74`, `pension_fy_wt 0.70`, plus `delta_eitc_fy_wt 0.03`,
`medicare_inf_lswp_wt 0.75`, `pgdp_wt 0.80`, `socfica_off 0.78`, `socsec_off 0.75`, `cboawba 470.6`.

`input/rules_of_thumb.csv` holds **CBO's effective marginal tax rates by income type, year by
year**, defined in `glossary.md:95-108`: `rtpwsd` (wages and salaries, excluding pension/IRA) 0.19
(2026) → 0.21 (2036); `rtwwsd` (FICA) 0.10 flat; `rtpyent` (proprietors) 0.11 → 0.12;
`rtcs` (S corp individual income) 0.30 flat; `rtczb` (domestic NIPA corporate profits) 0.07 → 0.08;
`rtgdpzb` (GDP corporate profits) 0.02 → 0.01; `rtpdiv` (dividends, no pension/IRA) 0.02 → 0.03;
`customs` 0.15 → 0.13; `excisegdp` 0.01; `scorpifccorp` 0.12; `scorppropratio` 0.13. Mechanics live
in `bfm/revenues.py`, `bfm/outlays.py`, `bfm/net_interest_costs.py`. `config/config.yaml` sets
`start_year: 2026`, `n_project: 10`, `n_lags: 31`, and three toggles including
`toggle_net_int_opt` ("=1 disables rate effects on existing debt and indexed securities").

**Maps onto.** `fiscal_model/baseline.py` (directly), `fiscal_model/models/macro_adapter_frbus.py`
and `fiscal_model/constants.py:71` (`MARGINAL_REVENUE_RATE = 0.25`),
`fiscal_model/corporate.py`'s §6655 fiscal-year convolution, PR #126's window work.

**What it does not offer.** The BFM runs the arrow in the opposite direction from this app: it
perturbs *the economy* and reads the *baseline's* response. It has no policy lever, no multiplier
and no fiscal-impulse channel, so it cannot validate the app's dynamic scoring — only its **revenue
recapture rate**, which is exactly the piece the app currently has as a single 0.25.

---

### 2.5 `eval-projections`

**License.** Public domain, older wording. **Language/size.** Python 3.8, 5,153 KB, last push
2026-02-17.

**What it is.** README: *"The code and data in this repository allow users to replicate the
evaluations CBO regularly conducts of its projections of various budget components: outlays,
revenues, deficits, and debt."* Four accompanying reports are named: *An Evaluation of CBO's
Projections of Deficits and Debt From 1984 to 2023* (`cbo.gov/publication/60664`), *…of Outlays from
1984 to 2021* (`58613`), *An Evaluation of CBO's Past Revenue Projections* (`56499`), and *The
Accuracy of CBO's Budget Projections for Fiscal Year 2025* (`61916`).

**Data shipped.** `input_data/baselines.csv` — **20,343 rows**, every CBO baseline from 1984 to 2025
by `component / category / subcategory / baseline_date / projected_fiscal_year /
projected_year_number / value`, with `Spring_flag` and `Winter_flag`. Plus `actuals.csv`,
`actual_GDP.csv`, and `baseline_changes.csv` (subsequent legislative changes).
`output_data/` holds twelve committed CSVs, three per component.

**The method is the asset, and it is three specific choices.** (i) `src/errors.py:35-41` adjusts
the projection for later legislation **before** measuring error:
`adjusted_projection = value + legislative_[component]_change`, then
`projection_error = adjusted_projection − actual_value`. (ii) `src/errors.py:47-56` reports the
error two ways — `projection_error_pct_actual` and `projection_error_pct_GDP` — so a level error and
a scale-free error are always both on the page. (iii) `src/summary.py:67-68` reports four statistics
and the fourth is not a mean: `RMSE = ((error ** 2).mean()) ** 0.5` and
`two_thirds_spread = error.quantile(5/6) - error.quantile(1/6)`.

**The published numbers are a yardstick this app has never had.** From
`output_data/revenue_projection_errors_summary_stats.csv`, by projection-year number
(average error / average absolute error / RMSE / two-thirds spread, all percent of actual):
total revenue year 1 −0.5 / **2.8** / 4.1 / 6.5; year 6 3.1 / **10.1** / 11.7 / 25.3; year 11
4.6 / **13.2** / 15.2 / 30.8. Individual income taxes year 6 2.4 / **12.8** / 15.4 / 33.6.
Payroll taxes year 6 4.5 / **7.7** / 9.3 / 15.8. **Corporate income taxes year 6
11.2 / 28.2 / 34.4 / 66.2**, year 10 2.4 / 16.9 / 20.3 / 41.4.

**Maps onto.** `scripts/cold_holdout.py`, `scripts/run_validation_dashboard.py`,
`fiscal_model/validation/credibility.py`, `fiscal_model/validation/policy_classes.py`, and
`HIGH_STAKES_ACCURACY.md` §2 and §3 H4.

**What it does not offer.** It evaluates *baseline projections*, not *policy scores* — the two are
different quantities and the memo must not let the roadmap conflate them. CBO's revenue baseline is
a forecast of the economy; a policy score is a difference between two runs on the same baseline, and
its error has different sources. The figures above are therefore a **comparator and a method**, not
a target the app should try to beat or claim to have matched.

---

### 2.6 `CPS-tax-filing-units`

**License.** Public domain, older wording. **Language/size.** Stata/IC 14.2, 49 KB, last push
2026-03-11. The smallest useful repository here.

**What it is.** README: *"This repository contains the code CBO uses to combine individuals into tax
filing units in the Annual Social and Economic Supplement (ASEC) of the U.S. Census Bureau's Current
Population Survey (CPS). This model was developed specifically to statistically match data from the
CPS ASEC household survey with the data from the Internal Revenue Service's Statistics of Income
data."* It cites `cbo.gov/publication/52914` for the overall matching process and states it is
tested on survey years **2023, 2024 and 2025**.

**The method, documented at `docs/algorithm.md`.** Every individual is a primary filer, a spouse, or
a dependent (qualifying child or qualifying relative). Dependency is built from two CPS variables,
`HHDFMX` (primary family / subfamily / unrelated, with child/married/adult/reference detail) and
`PERRP` (relationship to householder). The primary tax unit starts from the householder; children,
grandchildren and foster children in the primary family attach if they qualify; other relatives
attach on the qualifying-relative test. Related subfamilies, unrelated subfamilies, group quarters
and secondary individuals each get named rules; roommates and boarders are always their own units;
unmarried partners are their own unit if they have relatives, otherwise attach on a support test.
The **support test is proxied by restricting a potential relative's income to the standard deduction
for married filing separately**, and an unmarried partner additionally requires the filer's income
to be at least twice the partner's. Three **reassignment routines** then run, explicitly "to reflect
the incentives of taxpayers to reduce tax liability": collapse related subfamilies into the primary
family where the subfamily head qualifies as a dependent; reallocate up to two youngest qualifying
children between head and related subfamilies; and the same between head and unmarried partner.
Finally, qualifying dependents with positive gross income are **appended as additional (dependent)
tax units**. Code: `scripts/4a_flag_dependents.do`, `4b_identify_tax_unit_relationships.do`,
`4c_reassign_relationships.do`, `4e_collapse_to_tax_units.do`.

**Data shipped.** Six CSVs in `outputs/`, for calendar years 2022, 2023 and 2024.
`Kinships_in_Tax_Units_CPS_CY_2024.csv` tabulates survey observations and population in millions by
`pass × married × status_on_tax_return × kinship_to_head`, at each of the four passes
(`base_assignment`, `collapse_SFs`, `swap_bw_families`, `final_pass`) — so the effect of each
reassignment routine is visible. `CPS_CBO_Incomes_Crosswalk_CY_2024.csv` maps 22 CPS income
variables (`wsal_val`, `semp_val`, `div_val`, `pnsn_val`, …) onto 18 CBO income concepts with
dollar totals, including a `retrmnt_intrst_buildup` row the app has no analogue for.

**Maps onto.** `fiscal_model/microsim/data_builder.py:398-408` (the app's five-line construction
rule), `fiscal_model/microsim/engine.py:532` (binary married/not filing status),
`fiscal_model/microsim/filing_threshold.py`.

**What it does not offer.** It is Stata, and running it needs the CPS ASEC raw files plus a Stata
licence — so this is a **specification to port, not a pipeline to adopt**. It builds units; it does
not compute tax. It has no SOI-matching step in the repository (only the unit construction that
feeds one), so it cannot fix the app's documented 191M-CPS-units-vs-161M-SOI-returns gap by itself.

---

### 2.7 `business-investment-model`

**License.** Public domain, older wording. **Language/size.** EViews `.prg`, 667 KB, last push
2026-02-25; release date stated at `main.prg:50` as February 25, 2026, data current to
February 11, 2026.

**What it is.** README: *"The Congressional Budget Office models most business investment by using a
modified neoclassical specification. The methodology embedded in the code here is consistent with
that presented in CBO Working Paper 2018-09: CBO's Model for Forecasting Business Investment"*
(`cbo.gov/publication/54871`). Twelve investment categories, eight in a state-space system, four by
OLS. Author Mark Lasky.

**Key parameters, with file:line.** The one that matters most to this app is
`source_code/Create_Tax_Data.prg:32-33`: **`dmyrevx = 0.80`** (all private nonresidential capital)
and **`dmyrevnfc = 0.85`** (nonfinancial corporates) — **and these are *nested*, not a financial / non-financial pair**: CBO's comment at `:21-27` derives 0.85 from loss-making firms alone (SOI 2005, net income on all active returns ÷ net income on returns with positive net income = 87.2%, rounded) and 0.80 from that same factor further reduced by the nonprofit share of nonresidential investment, 0.85 × 0.94 = 0.799. `grep -rn dmyrev source_code/` returns no third series, so **there is no sector split to apply** — recorded here because `ROUTE_TO_8_5.md` §1 R5 described it the other way and would have sent a lane looking for data that does not exist (PR #166 finding 2). — the share of the statutory rate that is
actually live after loss-making firms and nonprofits. The derivation is in the comment at
`Create_Tax_Data.prg:21-27`: SOI 2005 net income on returns of active corporations
$1,948,655,133k is **87.2%** of net income on returns *with positive* net income $2,234,882,109k
→ 0.85; nonprofits are 6–7.1% of nonresidential investment → 0.80 combined. The combined effective
rate is then `rtcorpx = dmyrevx * (rtcgfs + rtcgsl * (1 - rtcgfs))` at `:69-70`, with the statutory
federal rate `rtcgfs = 0.21` from 2018 at `:15`.

Also transplantable: the **§179 ladder hard-coded by year** at `Create_Tax_Data.prg:124-307`,
running $10,000 (1958–81) through $1,000,000 (2018), chained-CPI indexed 2019 to 2025q2, and
**$2,500,000 from 2025q3 under P.L. 119-21** (`:303`); the **§179 take-up elasticity 0.252**
(`:309`, from Kitchen & Knittel 2016 p. 24, comment at `:142-149`); the **bonus-depreciation
take-up factor `Xfactor = 0.772`** (`:317`, "For bonusrate=50%, Xfactor=0.772"), with the statutory
path 100% 2018–22, 0.8 / 0.6 / 0.4 for 2023/24/25 (`:337-343`) and P.L. 119-21's restoration at
0.64 (2025q1), 0.70 (2025q2), 1.0 from 2025q3 (`:353-357`); the **§174 R&E amortization switch**
(`:413-428`), expensed through 2021, zero from 2022, restored 0.4 / 0.5 / 1 across 2025; a
retroactivity convention of 50/50 perfect-foresight/myopic weights (`:215-218`); and the
Hall–Jorgenson user cost at `Create_Iterative_Model.prg:12`,
`qualx = (1-τ̄)(1-vbus)·P·y / (1 - ITC - τ̄·z) / (1/slife + rxyav)`, with the closed-form PDV of
depreciation allowances `z` at `Create_Iterative_Model.prg:33`. Structural constants:
`c1 = 0.7` (tax-wedge exponent), `c2 = 0.18`, `c3 = 0.23`, `alphaadj = 0.28`, `rxyav = 0.040` real
required return (`First_Solve_of_Iterative_Model.prg:10-21`), re-estimated in
`outputs/State_space_coefficients.csv` at c(1)=0.590167389, c(2)=0.170124727, c(3)=0.222333375.

**Data shipped.** `inputs/…Quarterly.csv` (795 KB, **407 variables, 1929Q1–2025Q3**),
`…Annual.csv` (139 variables, 1929–2025), `…Monthly.csv`, plus a 35-page
`docs/CBO_Business_Investment_Data_Documentation.pdf` sourcing every series (BEA NIPA and Fixed
Assets, BLS, Fed Financial Accounts, Moody's AAA/BAA, Philadelphia Fed SPF, Baker Hughes, Brent,
Henry Hub). Tax-law series (`LIFE*`, `DB*`, `ITC*`) are transcribed from Jane G. Gravelle, *The
Economic Effects of Taxing Capital Income* (1994), patched for later acts.

**Maps onto.** `fiscal_model/corporate.py:78` (the fitted base), `corporate.py:672-679` (the flat
−$28.0B bonus-depreciation constant), `cbo_opt64`'s `known_limitations` §174 note, and
`HIGH_STAKES_ACCURACY.md` §3 H3b.

**What it does not offer.** EViews is commercial, so this is readable and not runnable. More
important: **it is a model of investment demand, not of revenue.** It never computes a tax
liability, an EMTR or a corporate tax base; `rtcgsl` is backed out of NIPA profits and corporate
receipts are an *input*. And its tax-law series are transcriptions of a 1994 book, so adopting them
means inheriting that transcription rather than reading a primary source.

---

### 2.8 `rules-of-thumb-model`

**License.** Public domain, 17 U.S.C. § 105 wording. **Language/size.** A single 171 KB `.xlsx`, no
macros, last push 2026-05-19.

**What it is.** README: *"The rules of thumb model allows users to define and analyze alternative
economic scenarios by specifying differences in the values of four economic variables—productivity
growth, labor force growth, interest rates, and inflation—relative to the values underlying CBO's
most recent projections."* It supplements *How Changes in Economic Conditions Might Affect the
Federal Budget: 2026 to 2036* (`cbo.gov/publication/62257`) and replicates the interactive tool at
`cbo.gov/publication/61914`. Baseline: publication 61882, February 2026.

**Key parameters, by sheet and cell.** Ten sheets: four interactive (`1. Productivity`,
`2. Labor Force`, `3. Interest Rates`, `4. Inflation and Interest`), four locked `_CBO`
illustrative companions, `Contents`, `License`. User inputs sit at `C13:M13` on each sheet with
hard caps (productivity ±0.5 pp, labor force ±0.75 pp, rates ±1.0 pp, inflation ±1.0 pp); an
out-of-range entry trips a guard at `1!A19` that blanks the table. The headline sensitivities, for
a 0.1 pp/year shock, effect on the deficit over FY2027–2036 ($B): **productivity −0.1 → −316.600**
(`5. Productivity_CBO!O24`), **labor force −0.1 → −165.980** (`6!O24`), **interest rates +0.1 →
−378.882** (`7!O24`), **inflation and rates +0.1 → −311.467** (`8!O25`), against a baseline
FY2027–2036 deficit of −$24,405.987B (`!O27`). The mechanism is `SUMPRODUCT(shock_vector,
matrix_row)` and is **linear in the shock**, so a 1 pp read is ×10.

Two matrices are directly usable. **Net interest per 1 pp rate rise from 2026**
(`3. Interest Rates!C122:M122`): 55.064, 75.159, 42.737, 33.893, 28.180, 25.387, 18.537, 16.602,
12.596, 12.394, 10.099 — a rollover profile summing to about $331B, front-loaded. **Debt-service
rate applied to cumulative deficit** (`3!C138:M148`, first row): **0.99%** in the enactment year,
then 3.54, 3.66, 3.81, 3.96, 4.12, 4.29, 4.46, 4.63, 4.81, **5.01%**. Receipts per 1 pp rate rise
(`3!C106:M116`) run 4.461 → 1.108, *offset* by a Fed-remittance row (`3!C118:M118`) of
36.038 → 52.304 $B/yr, so CBO's net is **+$4.5B of revenue over ten years from a 1 pp higher rate
path** — a channel the app does not have. Fiscal-year weighting is explicit throughout
(`1!C70`: `FY = CY × 0.75 + prior CY × 0.25`).

**Maps onto.** `fiscal_model/models/macro_adapter_frbus.py:443` (`interest_cost =
cumulative_deficit * 0.04`), `:350` (`crowding_out = 0.15`), `:351` (`marginal_tax_rate = 0.25`).

**What it does not offer.** No unemployment lever, no wage-share, no oil price, **and no policy
lever at all** — it perturbs the economy and reads the baseline's response, the mirror image of what
the app does. Discretionary outlays are hard-zero in three of four scenarios (`1!A98`). Interactions
are not modelled. It is strictly linear, so the ±0.5/±0.75/±1.0 caps are load-bearing. And the
effects carry hand-applied `Net Interest Residual` / `Debt Service Residual` rows
(e.g. `1!C132:M132` 2.794 → −0.931) that are unexplained fudge terms an adopter would inherit blind.

---

### 2.9 `electric_vehicle_model`

**License.** Public domain, older wording. **Language/size.** Stata, 262 KB, last push
2024-04-30 — the **stalest** repository in this set.

**What it is.** README: *"CBO's electric vehicle model projects U.S. market equilibrium demand for
electric vehicles (EVs) and supply of public EV chargers."* It accompanies David H. Austin,
*Modeling the Demand for Electric Vehicles and the Supply of Charging Stations in the United States:
Working Paper 2023-06*, `https://www.cbo.gov/publication/58964`. CBO's own caveat, verbatim:
**"The model has not been used for any CBO baseline or cost estimate analyses."**

**Key parameters (all `model/set_parameters.do` unless noted).** The §30D construction is the
reusable part: `AMPCBaseCar 3150` (:132, $45/kWh × 70 kWh) and `AMPCBaseTruck 5400` (:133);
`AMPCShare` (:135-154), the share of the §45X credit passed through to consumers, ICCT-sourced, at
0.25 (2023), 0.5 (2024–29), 0.375 (2030), 0.25 (2031), 0.125 (2032); `EVBuyerQual` (:102-111),
CBO's own share of EV buyers qualifying jointly on AGI and MSRP, **0.6700 (2023) → 0.7600
(2030–32)**, derived at :112-126 from an ICCT MSRP share of 87% and an AGI share rising 68% → 77%;
`CritMin{Low,Med,Hi}` (:60-90), the share of sales meeting the Critical Minerals test, Med 0.790
(2025) → 0.720 (2030) → 0.780 (2032). The credit identity is `calc_RA_tax_credits.do:38-40`,
capped at 7500 with 5% noise, and it prices the **leasing loophole explicitly** at `:57`
(`lease 0.5`). Elasticities: `EtaPrElasEVMean −2`, sd 0.5 (:205-206, Cole et al. 2023);
`EtaChargerElasEVMean 0.4` (:211-212, Springel 2020); `GammaElasEVMean 0.67` (:221-222, Springel
2020, with Li et al. 2017 at 0.61). Discount rate 0.03 (:315); cost of capital 0.08 (:319,
Damodaran 2023); battery $125/kWh with a $50 floor (:374-384); dealer markup 0.15 (:407).
IIJA: `IIJASubsidyRate 0.8` (:595) and annual charger increments from $7B of IIJA's $7.5B
(:617-639). Data: `inputs/EV_model_data.csv`, 43 rows, EIA **AEO2023 Table 38, "No Inflation
Reduction Act" case**, plus AEO2023 Tables 8 and 12.

**Maps onto.** `fiscal_model/climate.py:68-70` (`ev_credit_per_vehicle 7500.0`,
`ev_sales_millions_per_year 1.5`, `ev_sales_growth_rate 0.15`) and `climate.py:245-271`.

**What it does not offer.** **No revenue or outlay estimate anywhere** — outputs are fleet, share,
relative prices and charger counts at P17/P50/P83, with no federal-cost column, and CBO disclaims
cost-estimate use. Four load-bearing parameters are admitted free calibration knobs (`MeanDrift
0.037` at :167, `InitDeltaL2 4.46` at :192, `ShareCorrect2023 1.1` at :295, `muEPAFactor 0.0108`
at :251, the last two labelled "numeric value meaningless by itself"). It needs Stata. And it is
stale in three ways that matter: AEO2023 on the "No IRA" case, FEOC unimplemented, and
`RAEndYear 2032` (:27) counterfactual after P.L. 119-21 terminated §30D in 2025.

---

### 2.10 `EmpElastR`

**License.** Public domain, older wording; `DESCRIPTION` adds "Users may not use or modify the data
or computer code and then present it as official government material." **Language/size.** R package,
316 KB, last push 2025-12-15; package v1.0.0 built 2019-11-07.

**What it is.** README: *"an R package (EmpElastR) that provides the data, functions, and
documentation for the calculation of employment elasticities used by the Congressional Budget Office
in its 2019 analyses of the effects of options to raise the federal minimum wage."* Accompanies
*The Effects on Employment and Family Income of Increasing the Federal Minimum Wage*, July 2019,
`https://www.cbo.gov/publication/55410`, and the November 2019 interactive tool (`55681`).

**Key parameters (`R/elasticities.R`).** `short_run_elasticity_lit_teen = -0.4550` (:38) and
`short_run_elasticity_lit_adult = -0.1475` (:39), derived in
`vignettes/employment_elasticities.Rmd:196-259` from a literature teen elasticity of −0.070 scaled
by 1/0.25 × 1/0.60, and an all-affected-worker median of −0.25 decomposed against the teen share.
`ratio_of_long_run_to_short_run_elasticities = 1.5` (:112); `cost_of_labor_growth_h = 0.8` (:186);
`ratio_15_to_h = 1.2` (:237). Data is three `.rda` files covering 164 policy options for 2017–2029,
with **no stated source** for `size_stats`.

**Maps onto.** Nothing in this app.

**What it does not offer.** These are **minimum-wage employment elasticities** — the probability of
job loss per mandated change in log wage — not labour-supply or taxable-income elasticities. They do
not inform the ETI of 0.25 or the 0.65/0.35 factor shares. The window is hard-coded to 2020–2029 and
is stale. The 164 options' size statistics come from a microsimulation that is not in the
repository, so the policy content is absent. Data needs R or `pyreadr`.

---

### 2.11 `discount-factors`

**License.** Public domain, older wording. **Language/size.** Python, 40 KB, last push 2026-02-18.

**What it is.** README: *"The code in this repository calculates discount factors, which are used to
estimate budgetary costs of federal programs such as federal mortgage guarantee programs."* **It
names no accompanying publication** — no title, number or date. The only citation is the data
source, "CBO's January 2025 baseline",
`https://www.cbo.gov/system/files/2025-04/55022-2025-01-Historical-Economic-Data.zip`.

**Key parameters (`src/functions.py`).** `maturity_pillars = [1,2,3,5,7,10,20,30]` (:5),
`max_maturity = 41` (:6); semiannual-coupon to effective-annual at :61
(`grp = (1.0 + grp/2.0)**2 - 1.0`); linear interpolation across pillars (:80), flat beyond 30 (:83);
a par-to-zero bootstrap at :123-129; geometric extrapolation 31–41 at :133; and — worth flagging as
an approximation rather than a convention — **quarterly factors by linear interpolation of the
factors themselves rather than of log-factors** at :169. Input `data/treasury_yield_data.csv`, 45
quarterly rows 2024Q4–2035Q4, eight maturities. Committed outputs give 41 maturities × FY2025–FY2035
(FY2025 1-yr 0.960257 = 4.139%, 10-yr 0.661665, 30-yr 0.259665).

**Maps onto.** Nothing the app does today. The app has no discounting machinery at all.

**What it does not offer.** No publication, no methodology document, no tests, and **`environment.yml`
is missing** although the README's own install step instructs `conda env create -f environment.yml` —
the documented install cannot be run. One vintage only (January 2025), already stale against the
February 2026 vintage two sibling repositories use. No FCRA-specific conventions, no real factors, no
uncertainty. It is roughly 250 lines of bootstrap arithmetic.

---

### 2.12 `credit-subsidy-tool`

**License.** Public domain, 17 U.S.C. § 105 wording. **Language/size.** VBA + one 194 KB `.xlsm`,
172 KB, last push 2026-07-28.

**What it is.** README: *"The credit subsidy tool produces credit subsidy estimates for direct loan
and loan guarantee programs using two approaches: the accounting procedures used in the federal
budget and prescribed by the Federal Credit Reform Act of 1990 (FCRA), and an alternative approach
in which costs are estimated on the basis of the market value of the federal government's
obligations--termed a fair-value approach."* Accompanies *Estimates of the Cost of Federal Credit
Programs in 2027*, July 2026, `https://www.cbo.gov/publication/61645`. The VBA ships as readable
plain-text `.bas`/`.cls` alongside the binary — 849 lines.

**Key parameters.** `Discount_Factors!B2` states the vintage: **"Last updated: February 2026
baseline (www.cbo.gov/publication/61882)"**, with 100 annual / 200 semiannual / 400 quarterly
periods at rows 7–406; implied annual zero rates 3.535% (1y), 4.195% (10y), 4.836% (30y), 5.080%
(100y). `Risk_Premium!A7:F36` is the published risk-adjusted spread table in basis points with loss
multiples, split under and over five years: commercial AAA 29 / 57 bp (multiples 10.2 / 13.6),
A 47 / 94, BBB 66 / 132, BB 148, B− 155, below B− 161; consumer 222 / 326 / 480 / 630 bp banded by
loss rate; student 144 / 182 / 220 / 292.5 / 365; housing 40 / 60 / 90 bp with loss multiples
"n.a.". `SubsidyCalculation.bas:159` holds an undocumented backstop —
`ceiling = disbursement_sum - (disbursement_sum - TotalSubsidy_FCRA)/2`.

**Maps onto.** Nothing. The app scores no credit programs.

**What it does not offer.** Nothing for revenue or deficit scoring; this is program-level credit
valuation. A single term structure, not per-cohort, so it cannot answer cross-vintage questions.
Excel plus VBA, so reuse means reimplementation. README states outright: "The subsidy estimates
generated by the model do not constitute a CBO estimate."

---

## §3 — Ranked opportunities

Ranked by **(stakes × current error × tractability)**, the ordering `HIGH_STAKES_ACCURACY.md` §1.1
uses. "Effort" is lane-days on that plan's own scale. Every row names the CBO file that supplies it
and states the leakage position honestly. **Nothing in §3 is a recommendation to adopt without a
pre-registered lane; several rows would make a row worse, and those say so.**

| # | Opportunity | App module / constant (`file:line`) | CBO file | Effort | Expected effect | Leakage / circularity risk |
|--:|---|---|---|--:|---|---|
| **1** | **Ship CBO's Feb 2026 budget baseline, and make the vintage library real.** `CBOBaseline` reconstructs base levels from GDP ratios under the app's default `use_real_data=True`, and its own comment says why: no vintage-specific published table "can be reached from this environment". Three of the nine ratios are mandatory-spending levels CBO publishes directly. | `fiscal_model/constants.py:120-132` (`GDP_RATIOS`); `fiscal_model/baseline.py:553-618`, `:595-600`, `:647-664` (Feb 2026 hardcoded literals), `:220-224` (`CORPORATE_RECEIPTS_SOURCING`) | `budgetary-feedback-model/input/budget_baseline.csv` (11 columns × FY2025–2036) and `cbo-data/data/budget/ten_year_budget/annual_fy_{2024-06,2025-01,2026-02}.csv` (336 vars × 3 vintages) | 3 | No *scored* number need move — PR #130's precedent is that a baseline fix can be byte-identical on all 81 rows while the numbers behind Ask, Build and debt/GDP move. Closes §6.2's baseline carry-over and the `vintage_estimate` grade on `CBO_FEB_2026`. | **None.** No target is fitted to a baseline level; the app's Tier 1 shapes are bottom-up and `build_scorer_for_vintage()` already demonstrates that changing the vintage moves no Options row. |
| **2** | **The statutory parameter schedule the app has been transcribing by hand — brackets, AMT, EITC, CTC, SALT, standard deduction, by filing status, by year, on three vintages.** H2 declared the year-indexed threshold out of scope because "a published post-2025 rate table … does not exist". It exists. | `fiscal_model/validation/cbo_scores.py` (`cbo_opt45_top4_brackets_2pp` limitation 2); `fiscal_model/amt.py` (PR #106's eleven Revenue Procedures); `fiscal_model/credits.py`; `fiscal_model/tax_expenditures_core.py` (SALT); `scripts/build_filing_status_data.py` | `cbo-data/data/budget/tax_parameters/annual_cy_2026-02.csv` — `tp_bracket_1..7_{single,mfj,mfs,hoh}`, `tp_amt_*`, `tp_eitc_*` (16), `tp_ctc_*` (5), `tp_salt_limit_*`, `tp_std_deduction_*`, `tp_ss_max_earnings`, `tp_rate_1..7` | 3 | Makes §6.2 item 27's third `isinstance` branch buildable, i.e. `Policy.scores_by_year()`. Direction on `cbo_opt45_top4_brackets_2pp` (14.9%) is **known to be adverse** — H2 says the year-indexed threshold takes that row further under — so this is a **pre-registered regression** on at least one row. | **None** on the statutory side: a rate table is law, not an estimate. But it must not be used to *re-fit* anything; the gain is expressiveness, not error. |
| **3** | **Replace the flat tariff offset with JCT's published year path, and close the steel base's declared upper bound.** `trade.py:127-135` already says the HS-73 whole-chapter base is an upper bound "because the Section 232 annexes list articles at HS-10"; CTAM ships those article lists with metal-content shares. | `fiscal_model/trade.py:153` (`income_payroll_offset_rate = 0.25`), `:136` (`steel_derivative_imports_billions = 49.5`), `:150` (`tariff_avoidance_rate = 0.05`, whose CSV row concedes it is "Retained module default") | `conventional-tariff-analysis-model/inputs/offset/2025OffsetPostHR1.csv` (0.244 → 0.241); `inputs/hts_lists/alst_deriv_h.csv`, `alst_deriv_l.csv`, `alum_steel.csv`; `config/default.yaml` shares 0.75 / 0.25 | 3 | Closes §6.2 item 64. The offset is worth ~1pp on every trade row, with sign depending on the year. The steel base narrows from an upper bound to an article-level measure; `steel_tariff_25` (75.28%) is scored against an **untraceable, examined-and-left-twice** target, so its movement is not evidence either way and the lane must say so. | **None.** No `TRADE_BASELINE` constant has been fitted to any target since Wave 3's L8. The offset file is JCT's, not the app's. |
| **4** | ~~**Give the corporate module CBO's own loss-firm-and-nonprofit haircut.**~~ **REFUSED on the merits by PR #164's sibling lane, PR #166** (`planning/lanes/R5_h3b_corporate.md` §1.1). The ratio is real and is now transcribed with its commit SHA and line numbers — but it adjusts a **statutory rate** inside a user-cost-of-capital expression, while this module multiplies a **base** that is CBO receipts ÷ the statutory rate, and receipts already carry loss firms' zero tax. CBO itself *divides the factor back out* at `Create_Tax_Data.prg:172-175` where the other input carries it, **"to avoid double-counting"**; the module's own SOI file measures those losses at **8.69–11.58%** of the pre-NOL base against CBO's 12.81%. Applying it would have landed two of three pre-registered bands and destroyed the one row with a clean document behind it. **§6.2 items 80 and 81 are what is left.** *(As surveyed:)*  `CORPORATE_PER_POINT_YIELD.md` §4b established that this model's implied marginal base is 80.8–90.8% of the vintage average against a published 55.1–79.5%; CBO's own answer to "how much of the statutory base is live" is 0.80/0.85, derived from SOI. | `fiscal_model/corporate.py:78` (`BASELINE_TAXABLE_PROFITS_BILLIONS = 1900.0`, self-documented as fitted at `:71-77`); the derived branch at `:151-217` | `business-investment-model/source_code/Create_Tax_Data.prg:32-33` (`dmyrevx 0.80`, `dmyrevnfc 0.85`), derivation at `:21-27`; combined rate at `:69-70` | 3 | Directly targets H3b's pre-registered band `cbo_opt64` 44.5% → 30 ± 8 (the tier's single largest row, 11.8% of Tier 1 mass) and `biden_corporate_28_fy2022` −62.9% → −45 ± 10. **A haircut moves both rows the same way, so it cannot fix both if they miss in the same direction — which §6.2 item 53 says they do.** | **Low but real.** The haircut is a *published ratio from SOI*, not a fit to any score. The hazard H3b names remains: `scripts/corporate_yield_reconciliation.py` prints the number that would land the row (0.5785 vs JCT's 0.590), and approaching it is the failure mode. |
| **5** | **Adopt CBO's own error-measurement discipline for the app's validation reporting.** Three specific choices, none of which the app makes: adjust for later legislation before measuring; report percent-of-GDP beside percent-of-actual; report a **two-thirds spread** rather than a mean. | `scripts/cold_holdout.py`, `scripts/run_validation_dashboard.py`, `fiscal_model/validation/credibility.py` (PR #149's class bands use mean and worst row) | `eval-projections/src/errors.py:35-41, :47-56`; `src/summary.py:67-68`; the published stats in `output_data/revenue_projection_errors_summary_stats.csv` | 2 | Zero scored numbers move. It gives H4's bands a *published* shape (CBO's own year-6 total-revenue two-thirds spread is 25.3 pp against an average absolute error of 10.1%) and gives the roadmap a defensible external comparator for the first time. | **None** — but the memo's caveat must travel: CBO evaluates *baseline projections*, this app scores *policy differences*. The numbers are a method and a comparator, never a target to claim parity with. |
| **6** | **Decompose the dynamic feedback's marginal revenue rate by income type, and give debt service a rate path.** The app applies 0.25 to GDP and 4% flat to cumulative deficit, in five places. | `fiscal_model/constants.py:71`; `macro_adapter_frbus.py:351` (`marginal_tax_rate = 0.25`), `:443` (`interest_cost = cumulative_deficit * 0.04`), `:350` (`crowding_out = 0.15`); `macro_adapter_simple.py:111`; `olg/pwbm_model.py:236` | `budgetary-feedback-model/input/rules_of_thumb.csv` (`rtpwsd` 0.19–0.21, `rtwwsd` 0.10, `rtczb` 0.07–0.08, `rtgdpzb` 0.01–0.02, `customs` 0.13–0.15); `rules-of-thumb-model-2026.xlsx` `3!C138:M148` (debt-service rate 0.99% → 5.01%) and `3!C122:M122` (rollover profile) | 3 | The dynamic tab is 🟢-tier by CLAUDE.md's own taxonomy and has **no** published calibration for these two constants. A wage dollar recaptures ~0.29–0.31 under BFM, not 0.25; a corporate-profit dollar recaptures ~0.01–0.02. Expect shipped dynamic figures to move materially — Decision 6 applies. | **None.** No dynamic constant is fitted to a scorecard target; `cold_holdout.py` scores statically. |
| **7** | **Replace the generic base's hand-grown SOI aggregate with CBO's own projected AGI and taxable-income path — and its realizations path.** H2 grew a TY2023 aggregate by nominal GDP and its own falsification condition fired; W5-C projected realizations from an accrued-gains stock. CBO publishes both, annually, on three vintages. | `fiscal_model/policies_core.py` (the `TaxPolicy` scoring branch), `fiscal_model/scoring_engine.py`, `fiscal_model/data/capital_gains.py` | `cbo-data/.../revenue_detail/annual_cy_iit_2026-02.csv` — `rev_iit_agi`, `rev_iit_taxable_income`, `rev_iit_taxable_ordinary`, `rev_iit_taxable_capgains_divs`, `rev_iit_capital_gain_loss`, `rev_iit_returns_total`, `rev_iit_tax_bracket_1..7` | 4 | Touches every Tier 1 income-tax row (18 of 26) and every generic surface. **The AGI-inclusive class is 28.0% of Tier 1 mass and its plan target of ≤10% is missed by 7.6 points**; this is the only remaining lever named for it that is not a target dispute. High variance: it will move rows in both directions and some will cross. | **Moderate, and it must be handled.** These are *CBO's projections of the base*, not published scores — using them is a base improvement, not a fit. But `rev_iit_tax_bracket_1..7` is close enough to "the answer" for bracket reforms that a lane must **not** read it as a check on its own output. |
| **8** | **Port CBO's tax-unit construction algorithm and check the app's build against CBO's own kinship tabulations.** The app's rule is five documented lines with **no citation to any published tax-unit algorithm**, and its filing status is binary married/not by its own admission. | `fiscal_model/microsim/data_builder.py:398-408`, `:249-260`, `:355-390`; `fiscal_model/microsim/engine.py:532`; `fiscal_model/microsim/filing_threshold.py` | `CPS-tax-filing-units/docs/algorithm.md` (the full rule); `scripts/4a`–`4e*.do`; `outputs/Kinships_in_Tax_Units_CPS_CY_2024.csv` (population by status × kinship at each of four passes) | 4 | Head-of-household and MFS become expressible, which is what PR #127's filing-status split needs to be more than a composition weight. The kinship table is a **direct check** on the app's unit counts, against the 191M-vs-161M gap `filing_threshold.py:10-14` records. Credits LOO is 18.5%; this is the module's main structural gap. | **None.** A unit-construction rule is a method, not a target; the kinship table is a population count, not a score. |
| **9** | **Refit the spend-out profile on 1,712 real budget accounts instead of 14 donor options.** | `scripts/fit_outlay_rates.py`; `fiscal_model/data_files/spending/outlay_rates.csv` (NNLS on 14 CBO donor options) | `cbo-data/data/budget/spending_detail/annual_fy_{2024-06,2025-01,2026-02}.csv` — 21,769 rows, `budget_authority` **and** `outlays` per account per year, with `function_code`, `subfunction_code`, `disc_or_mand` | 3 | The five CBO Options spending rows already land at 0–11% and discretionary spending is the tier's best class (4.6%), so the *accuracy* gain is small. The gain is **provenance and coverage**: an account-class profile fitted on the accounts themselves, across three vintages, rather than on 14 hand-picked donors. | **Improves** the current position: the 14 donors are CBO options, i.e. estimates; account-level BA and outlays are the baseline's own accounting. |
| **10** | **Register CBO's own enacted-law revenue paths as Tier 1 component targets.** The tier has exactly three enacted-law replications and they carry 10.7% of its mass at 13.4% mean. CBO publishes 42 acts. | `fiscal_model/validation/preregistered.py:242-293` (`PreregisteredCase`), `fiscal_model/validation/cbo_scores.py:57-137` (`CBOScore`) | `cbo-data/.../revenue_detail/annual_fy_2026-02.csv` — `leg_rev_obbba_25` (FY2025–2035), `leg_rev_tcja` (FY2018–2027), `leg_rev_ira_22`, `leg_rev_arpa_21`, `leg_rev_atra_12`, `leg_rev_egtrra_01`, `leg_rev_tax_reform_86`, 35 more | 4 | This is H10's battery with a source. Each row supplies a line-item dollar figure, an annual path, the document, the vintage and the window — the five things `preregistered.py` requires. Target: the tier's enacted-law class grows from 3 to 8+. | **Must be read carefully, per act.** `leg_rev_tcja` is TCJA's *enactment*, not the *extension* the module is fitted to, so it is not leakage — but `leg_rev_obbba_25` overlaps the eight P.L. 119-21 JCX-35-25 line items already in the reconstruction tier, and registering both would double-count. One act, one row, stated. |
| **11** | ~~**Source the tariff elasticity as a time path and the exporter absorption as a number.**~~ **PARTLY DONE (PR #164) and partly REFUSED on the merits.** The offset path and the HS-10 Section 232 base landed; the *elasticity* did not, because `boehm_elasticities.csv` is **not an import-demand elasticity** — see the correction box above §2. `exporter_absorption: 5` was also not taken: it is incomplete border pass-through, a different object, and it **contradicts** the app's sourced `border_pass_through_rate = 1.00`. The live item is the unsourced trio, now sized at a **62% year-one import collapse** (§6.2 item 73). | `fiscal_model/trade.py:148` (`import_price_elasticity = -0.997`, single scalar), `:142` (`border_pass_through_rate = 1.00`), `:172-174` (`high_tariff_threshold 0.30`, multiplier 2.0, floor 0.20 — **no CSV row and no citation**) | `conventional-tariff-analysis-model/inputs/elasticities/boehm_elasticities.csv` (0.5517 → 2.0408 over 2025–2035); `centered5_f2f_constructed_elas.csv` (110 NAICS-4 substitution elasticities); `config/default.yaml` `exporter_absorption: 5` | 2 | A short-run/long-run ramp where the app has one number. `Trade` is 43.6% (n=5) after PR #150 and **registered as worse on purpose**; four of the five rows improve to 35.66% on their own documents. Direction here is genuinely unknown in advance. | **None** — but note the app's −0.997 is Tax Foundation's own choice (FF861 p. 4), so moving to CBO's path swaps one published estimator for another rather than moving toward truth. State that. |
| **12** | **Check the capital-gains module's death channel and holding periods against CBO's own published shares.** The app derives a 1.44× lock-in wedge from a 2.35%/yr realization hazard and a 2.647% death exit; Wave C left a **7.1× unmeasured factor** between the count and the level (§6.2 item 55). | `fiscal_model/data/capital_gains.py`; `CapitalGainsPolicy` defaults in `fiscal_model/policies.py`; `elasticity_reference_rate = 0.22` (CRS R48562) | `captax/.../environment_parameters.csv` — `cap_gains_at_death_share 0.4316`, `cap_gains_long_term_holding_period 9.1096`, `cap_gains_at_death_holding_period 30`, `cap_gains_short_term_share 0.0286`; and `cap_gains_long_term_tax_rate 0.2116` (2026) from `policy_parameters_Current-Law_comprehensive.csv` | 2 | **A measurement, not a change.** CBO's 43.16% at-death share and 9.11-year long-term holding period are an independent read on the same quantities the app derives, sourced to SOI Sale of Capital Assets 2007-2015 and SOI Estate Tax Returns 2007-2016. If they disagree with the app's hazard, that is the finding item 55 asked for. | **None** if kept as a check. **Decision 3 freezes the elasticity**, so `elasticity_reference_rate` may not move to CapTax's 0.2116 without an owner decision — the comparison is reportable, the change is not a lane's to take. |
| **13** | **The five unsourced expenditure magnitudes.** H7's own framing: PR #128 settled direction and explicitly left magnitude. | `fiscal_model/tax_expenditures_core.py:467-473` — charitable 0.4, mortgage 0.1, retirement 0.3, employer health 0.2, SALT 0.05, with the block comment at `:449-466` stating "These five numbers are unsourced" | **Nothing in these twelve repositories supplies them.** Recorded here so the roadmap does not go looking. | — | — | — |

**Sequencing note for the roadmap.** Rows 1, 5 and 9 move no scored number and can run in any order.
Rows 2, 7 and 10 all touch the generic income-tax path and **must not run in the same wave** — H2 and
H2b are the precedent for what happens when two base changes land together and their endpoints stop
being attributable. Rows 3 and 11 are one lane's worth of work in `trade.py` and should be one lane.
Rows 4 and 12 are each half of a question the plan already has open (H3b and §6.2 item 55).

---

## §4 — Checked and rejected

**`EmpElastR` — rejected, wrong elasticity.** Minimum-wage employment elasticities are the
probability of job loss per mandated change in log wage. They are not labour-supply elasticities and
not taxable-income elasticities, so they say nothing about the app's ETI of 0.25 or the 0.65/0.35
factor shares. The window is hard-coded to 2020–2029 (`R/elasticities.R:37`) and the 164 options'
size statistics come from a microsimulation that is not in the repository, so even the minimum-wage
content is incomplete. No source is stated for `size_stats`.

**`electric_vehicle_model` — rejected as a target, retained as a construction.** It produces **no
dollars**: the summary outputs are fleet, share, prices and charger counts, and CBO states the model
"has not been used for any CBO baseline or cost estimate analyses". Building a credit cost from
`EVTC × EVShare × LDVSales` would be the app's construction, not CBO's, so it could not be a valid
out-of-sample target — it would be the `trump_corporate_15` `model_estimate` defect in a new costume.
Four load-bearing parameters are admitted free calibration knobs. And it is counterfactual in three
ways after P.L. 119-21 (AEO2023 "No IRA" case, FEOC unimplemented, `RAEndYear 2032`). The per-vehicle
credit identity with ICCT-sourced qualification shares and the explicit leasing term is worth reading
if anyone ever rebuilds `climate.py:245-271`, but it is not a §3 row.

**`credit-subsidy-tool` — rejected, out of scope.** The app scores no credit programs. The
February 2026 discount factors are duplicated in `discount-factors` and, more usefully, the same
baseline is in `budgetary-feedback-model`. The risk-premium table is genuinely interesting and has
no use here.

**`discount-factors` — rejected, thin and stale.** ~250 lines of bootstrap arithmetic, one vintage
(January 2025), no accompanying publication, no tests, and a missing `environment.yml` that makes its
own documented install fail. The app has no discounting anywhere, so there is nothing to replace. One
detail is worth knowing if discounting is ever built: its quarterly interpolation is on the factors
rather than the log-factors (`src/functions.py:169`), which is an approximation and not a convention
any agency states.

**CBO's Nov-2025 tariff score as a Tier 1 target — checked and rejected for now.**
`fy_revenue_summary.csv`'s $2,380.58B over FY2026–2035 is a genuine published CBO conventional
estimate and is not leakage, but the **shape is not expressible**: it is a stack of overlapping
Section 232 actions, reciprocal rates, USMCA carve-outs, country caps and article-level exemptions
that `TariffPolicy` cannot construct. Registering it would produce a row whose error measures the
app's inability to express the policy rather than its accuracy. The tractable fragment is the
**implied import decline** (16.49% total, 25.57% for China) as a check on the elasticity, which
belongs inside §3 row 11 rather than in the battery.

**CapTax's EMTRs as validation targets — checked and rejected.** CapTax returns rates and wedges,
never dollars. There is no ten-year score in the repository to score against.

**Re-fitting anything on `cbo-data` — rejected on principle, recorded because the temptation is
real.** `rev_iit_tax_bracket_1..7` is CBO's own projected tax collected in each bracket. Any lane
that reads it while scoring a bracket reform is reading something adjacent to the answer. It is
usable as a *base*, and the §3 row says so; it is not usable as a check on a bracket score.

**`social-security-trust-funds-model` — not surveyed here.** It is in the organisation (68 KB, last
push 2026-02-20) and is plainly relevant to the two OCACT payroll benchmarks H13 found publish no
dollar amounts, but it falls to the sibling macro/spending memo. Flagged so the roadmap does not
lose it.

**Six further repositories sit outside this memo's twelve and outside the obvious macro/health/
spending set**, so the roadmap should confirm the sibling memo covered them rather than assume it:
`IO-price-model` (7,574 KB, 2026-04-27), `debtwelfare` (816 KB, **2022-12-16** — the only stale
repository in the organisation), `financial_regulation_model`, `conditional_forecasting_with_bvar`,
`markov-switching-macrosimulation-model` and `sanctions-penalty-model`. None has a name suggesting
tax or revenue scoring. The full organisation listing, with language, size and last-push date for
all 33 repositories, is reproducible with
`gh api "orgs/US-CBO/repos?per_page=100" --jq '.[] | [.name, .language, (.size|tostring), .pushed_at] | @tsv'`.
