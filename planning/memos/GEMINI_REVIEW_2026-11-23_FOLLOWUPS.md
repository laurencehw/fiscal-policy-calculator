# Gemini review (23 Nov 2026): what was fixed, and the proposals left for the owner

The review (Gemini 4 Neon High, reading the live site and the source at `a953894`)
is kept outside the repository. Every finding was checked against the code
before anything changed. This memo lists what shipped, what was wrong in the
review, and the items that would move a model score or a benchmark number.
Those follow the lane rule (pre-register, then change), so each is written
here as a proposal for the owner to take or leave, not done.

## Shipped

| PR | Findings | What changed |
|---|---|---|
| #274 | 1.2 tracker | Plausibility checks withhold implausible automated bill readings (22 on the night of the review, including the Clergy Act at -$14,184.8B); the calculator's readings sit in a closed experimental section |
| #276 | 1.1, 1.3, 2.1, 2.2, 2.4, 2.5 (LOO wording), 4.4 (privacy), 1.5 (/changes) | Disclosures on /methods and /about, dynamic view relabelled demand-only, /build gap badge only on a matching window, privacy page corrected |
| #277 | 2.5 (API contract), 2.3 (uncertainty seeding) | Share links pin the snapshot id; published_billions gated; source_commit in provenance; seeded draws |
| engine lane | 4.1, 4.3, 4.4 (inputs, CI) | Per-visitor rate limits behind the shared key, cached /benchmarks and /summary, security headers, constant-time comparisons, pinned Actions |
| Ask lane | 1.4, 4.2 | Input caps, bounded scoring context, spend reservation, real streaming, generic 503 |

## Where the review was wrong or overstated

- **`ACAO: *` on `/`.** A cross-origin preflight to `/api/ask` returns no
  `Access-Control-Allow-Origin`; the header on `/` is Vercel's default on static
  responses. Low risk; no change beyond the other headers.
- **H.R. 463 "inverted sign".** +7pt corporate is a deficit reduction, so the
  sign was right. The reading is withheld for size, not sign.
- **"~14-16 distinct policies".** Grouping the same option across editions and
  its 1pt/2pt versions gives 22 designs, which /methods now prints.
- **LOO "mislabels refits".** Five of six modules do not refit on the retained
  anchors; they rebuild from base data, which is a stricter test than a refit.
  The page wording was imprecise, not the test.
- **/social-security -4.42 vs -4.44.** The page already says the ledger gives
  -4.44 against the Trustees' -4.42, and the 75-row table is already in a
  closed `<details>`.
- **"Decompose the dynamic score".** The result pages already show
  conventional + GDP feedback + debt service; the gap was the headline label.

## Proposals (owner's call; each moves a number)

1. **Supply channel in the dynamic view (2.2).** `build_macro_scenario` feeds
   every tax change to `FRBUSAdapterLite` as one receipts vector, so corporate
   rises read about 12% larger dynamically and cuts 13% costlier, the opposite
   sign to CBO/JCT/PWBM for capital taxes. Proposal: a lane that adds a
   capital-stock channel for corporate and capital-gains instruments (the
   `long_run/solow_growth.py` path, or CBO's rules of thumb in
   `US-CBO/budgetary-feedback-model/input/rules_of_thumb.csv`), pre-registered
   against CBO's and JCT's published dynamic estimates for the corporate rows.
   Until then the label says demand-only.
2. **A sealed prospective test set, with tax cuts (2.1).** Freeze a battery the
   model has never been debugged against: CBO cost estimates for bills
   introduced after a lock date, including revenue-losing ones (H.R. 1
   components scored by JCX-35-25 are the obvious first tax-cut rows). Report
   it beside the 44-row tier, never pooled.
3. **Report by design cluster (2.1).** Print the tier mean over the 22 designs
   (one weight per design) beside the 44-row mean, and add it to the CI gate.
4. **Bracket-specific behavioural offset (2.3).** Replace `ETI x 0.5 x static`
   with `ETI x tau/(1-tau) x a` per bracket from SOI Pareto ratios. This moves
   every ordinary-rate row; pre-register the direction (larger erosion at the
   top, smaller below).
5. **Specialised modules on the baseline's growth (2.3).** The 3% and 4% flat
   growth in `_score_growth_tax_policy_year` for credits, estate, AMT and the
   payroll/corporate fallbacks should read the vintage's nominal path.
6. **Leave-one-out estate case (2.5).** `ESTATE_UNPUBLISHED_TARGET_CASES` still
   excludes `eliminate_estate_tax`, whose target is now Tax Foundation's
   published +$407.2B. Re-admitting it moves the LOO suite mean.
7. **Credibility bands (2.1, 1.2).** `band_for_policy_type` gives a large
   corporate reform (Trump 15%, 129.6% from its target) the tight band of four
   +1pt rows, and maps bill-tracker types onto Tier 1 bands. Proposal: no band
   for a reform outside the class's tested range, and none on tracker readings.
8. **API scorecard (2.5).** `ScorecardResponse` exposes one pooled
   `mean_abs_percent_difference` across tiers. Replace it with per-tier means
   (a contract change for `/validation/scorecard`).
9. **`score_package` dynamic aggregation (2.2).** Package dynamic feedback is
   summed without the interaction factor and drops interest-rate, capital,
   investment and labour-force paths.
10. **`EconomicModel` (2.2).** No surface reports it; either delete it or
    route its `capital` array into `gdp_level` (R9 is the existing lane).
11. **/states SALT (2.4).** Texas and Florida show larger average SALT gains
    than California and New York because the national SALT shape is scaled to
    state averages. Build state tails from SOI state tables; add NJ, CT, MA.
12. **/build totals (1.3).** Default the package total to the calculator's own
    FY2026-2035 scores with interactions, and keep the published list prices
    as a second column.
13. **/tailor levers (Features 2).** Expose capital gains, payroll and
    spending, which the engine already supports.

## Deferred to avoid the open ACA branch (#275)

These touch `fiscal_model/app_data.py` or the preset JSON, which #275 edits:

- Rename "Flat Tax Reform": the preset is a 5-point across-the-board cut that
  keeps the brackets. Suggested label "Across-the-Board Rate Cut (5pp)".
- `cap_employer_health` is labelled "CBO, 2024" but the -$450B traces to CBO's
  2008 Option 9 for a $17,280 cap (H9 finding). Relabel or retire.
- "Cap Charitable Deduction" cites "Treasury, 2024" on /build and
  "Obama/Biden proposal, 2016-02" on /methods; one source line for both.

## Outside the repository (owner actions)

- **Legacy Streamlit app.** Still live at fiscal-policy-calculator.streamlit.app
  with the old `?admin=<token>` path. Take it down or replace it with a
  redirect in the Streamlit Cloud dashboard, then drop the uptime check in
  `.github/workflows/public-app-health.yml`.
- **Vercel environment variables** named by the engine and Ask lanes (set on
  the web project, then redeploy): see those PRs.
- **`bills.db` in git history** (11 MB, rewritten nightly). Moving it to a
  release asset or Vercel Blob needs a decision on where the nightly job
  writes; history rewriting is the owner's call.
- **README.** At 85 KB it contradicts itself in places. A rewrite into a
  200-line front door is worth a lane of its own; `tests/test_current_evidence.py`
  pins several of its sentences, so it moves with the evidence file.
