# Assessment and route to 9/10

Assessment date: 2026-09-22. Reviewed revision: `2d0ecab`.

## Assessment

**7.5/10 as a public-facing fiscal-analysis tool.** The project has strong
engineering foundations and unusually transparent validation. The main constraint
is uneven modeling accuracy, particularly for complex policies and packages.
This is an assessment of the project, not a statistical accuracy measure.

Strengths:

- Source provenance, preregistered benchmarks, and explicit separation of fitted
  results from independent predictions.
- Shared result objects, stale-result detection, consistent deficit signs, and
  reproducible assignment links.
- Multiple Python versions in CI, a coverage requirement, readiness checks, and
  dependency locking.
- Useful workflows for policy exploration, custom scoring, package building, and
  classroom use.

## Evidence and limitations

The review covered code, CI configuration, documentation, and freshly executed
validation reports. The following results describe the reviewed revision:

- **148 focused tests passed** across scoring, result consistency, API security,
  API bounds, app entrypoints, and UI controller smoke tests.
- Ruff passed. The blocking mypy gate passed for its 18 source files.
- Strict readiness returned `ready_with_warnings`: 6 checks passed, 4 warned,
  and none failed. The assistant key was deliberately unset for local checks.
- The broader test run was stopped at approximately 21%, with no failures
  reported. This review does not establish a full-suite pass or fresh coverage.
- A deployed visual review could not be completed: no browser was available,
  and the web fetch encountered a redirect loop. That is a review limitation,
  not evidence that the deployment is broken.

### Accuracy varies by policy family

The out-of-sample run reported **15.2% mean absolute percentage error across 44
cases**, with **26/44 within 15%** and **36/44 within 25%**. Discretionary spending
averaged **4.6%** error, while corporate policies averaged **40.3%**. A pooled
number must travel with the class results.

The reconstruction tier averaged **42.3% across 38 scored cases**; with the two
retired cases held in place at their withdrawal errors, it averaged **60.0%
across 40 cases**. Neither denominator changes nor fitted agreement should be
presented as improved predictive accuracy.

These figures were reproduced with `scripts/cold_holdout.py --json` and
`scripts/run_validation_dashboard.py`. Existing target revisions, retirements,
and preregistration records remain part of the evidence.

### Microdata and distributional comparisons need improvement

The default validation run contained **119% of benchmark return counts but only
81% of benchmark adjusted gross income** against IRS SOI 2023. Three of seven
distributional benchmarks used tax units where the source ranks households.
These gaps materially limit distributional credibility.

### Package modeling remains simplified

Build explicitly sums published list prices and discloses that interactions are
not modeled. The scoring engine separately aggregates individual policy scores
with one interaction factor. Neither is a full joint liability calculation for
interacting tax provisions. See
[`deficit_target.py`](../fiscal_model/ui/tabs/deficit_target.py) and
[`scoring_engine.py`](../fiscal_model/scoring_engine.py).

### Two concrete defects were reproduced

1. **Package uncertainty depends on policy order.** `score_package` passes the
   first policy to `_calculate_uncertainty`. Reversing a 1 percentage point
   income-tax increase and a $50 billion annual discretionary spending increase
   left the ten-year total unchanged at approximately -$1,038.83 billion but
   changed the uncertainty-range width by 50%, using
   `FiscalPolicyScorer(use_real_data=False)`. The package's composition, rather
   than its list order, must determine its uncertainty.
2. **Unlabelled API keys become log labels.** `_parse_keys` uses the secret as
   the label when a key has no explicit label; request logging emits that label.
   The supported configuration can therefore expose a secret in logs. The
   parsing behavior was reproduced with a dummy key. See
   [`api_security.py`](../fiscal_model/api_security.py).

Documentation also drifts from the runtime: the README describes IRS data as
ending in 2022 although the validation run loads 2023.

## Prioritized implementation plan

The completion criteria below are proposed project goals, not current results
or permission to retune against held-out targets. Existing provenance,
preregistration, and anti-gaming rules continue to apply. Coordinate work with
[`ROUTE_TO_8_5.md`](ROUTE_TO_8_5.md) and its supporting lanes; reconcile dated
status claims rather than silently replacing their historical evidence.

| Priority | Work | Completion criterion |
|---|---|---|
| 1. Repair correctness and security | Fix package uncertainty and secret logging. Add tests for policy-order independence, interval ordering, and secret redaction. | Both reproductions pass; full CI passes. |
| 2. Make current evidence authoritative | Generate headline metrics and data-vintage summaries from one versioned report. Consolidate competing roadmap documents. | README, UI, API, and validation reports agree on current facts; historical results remain clearly dated. |
| 3. Improve the shared modeling core | Calibrate filing populations and upper incomes; use a common tax-unit engine for supported revenue and distribution calculations. | Revenue reconciles with distribution totals; household benchmarks use households; residual calibration gaps are quantified. |
| 4. Score policy interactions explicitly | Start with ordinary rates, SALT, AMT, and credits. Calculate combined liability and distinguish supported packages from additive estimates. | Joint-package benchmarks pass; unsupported interactions remain clearly identified. |
| 5. Demonstrate stronger predictive performance | Expand fresh, locked benchmarks across policy families, rate cuts, vintages, and packages. Obtain independent methodological review. | Proposed target: no more than 10% overall mean absolute percentage error, no supported class above 20%, and at least five cases per class, without dropping difficult cases to improve averages. |
| 6. Verify the actual user experience | Add browser journeys for scoring, editing, sharing, exporting, mobile navigation, and keyboard use. Measure production latency. | Core journeys pass in real browsers against explicit accessibility and performance budgets. |

Independent benchmark design should begin before the modeling changes it will
evaluate. Freeze acceptance criteria before implementation; retain fixed-cohort
comparisons and disclose every membership change. Browser verification can
proceed alongside the modeling work.

## First three pull requests

- [x] **Package uncertainty:** remove dependence on the first policy and verify
  order independence and correctly ordered bounds for positive and negative
  deficit effects.
- [x] **API log redaction:** generate a non-secret identifier or require a safe
  label; cover unlabelled keys and empty-label configurations in log tests.
- [x] **Generated validation summaries:** establish one versioned source for
  current metrics and vintages, update consuming surfaces, and distinguish
  current status from historical roadmap prose.

After these repairs, concentrate development on the shared scoring population
and policy interactions. Those changes offer the clearest improvement in what
users can trust.

## Status, 2026-09-29

The three pull requests above landed on branch `ccr-7b92b7f8-aet71q`, with a
documentation sync in front of them. This section records outcomes; the
assessment above is left as written.

- **Package uncertainty** (`606691c`). Reproduced as described: -$1,038.83B in
  either order, band width 1.5x apart. A package's band is now the sum of its
  components' own bands, so it is order-free, reduces to the single-policy band
  for one policy or for same-type, same-sign components, and cannot be narrowed
  by splitting a policy into pieces. The reproduction's width goes 496/331 ->
  919. The same run showed the bounds were **inverted for every
  deficit-reducing estimate** (low above high); the spread now scales the
  magnitude. That reached the `/score/tariff` API, which had returned
  `low > central > high` for every tariff, the comparison table, the CSV export
  and the cumulative chart. No scored number moved.
- **API log redaction** (`0692de5`). Reproduced with dummy keys: both an
  unlabelled entry and an empty label (`:secret`) put the secret into two
  fields of every request log line. Keys without a safe label, including one
  whose label equals its secret, are now logged as `unlabelled-key-<n>`; the
  startup warning names the position, never the secret.
- **Generated validation summaries** (`c155ccc`).
  `fiscal_model/data_files/validation/current_evidence.json`, built by
  `scripts/build_current_evidence.py` from the computations the validation
  reports run, now supplies the figures the About page, the Methodology page and
  the Ask assistant print. `tests/test_current_evidence.py` recomputes it and
  pins the live headline sentences in the README, `CLAUDE.md` and `docs/` to
  it; 13 of those pins fail on the docs as they stood before this work. The
  Ask assistant now quotes a policy's own class error beside the pooled tier,
  and its corporate path names its real benchmark (Treasury's Green Book row,
  4.0%) alongside the class's 40.3%, where it used to say "benchmarked vs CBO
  within ~4%".
- **Documentation drift** (`3c38515`). Besides the IRS 2022 -> 2023 correction:
  headline figures and CI gates still quoting the pre-PR-#173 tier, two
  documented commands that did not run (`compare_to_cbo` exists nowhere; the
  ARCHITECTURE example imported `quick_score` from the wrong module and omitted
  a required argument), a README preset table 3 presets and one area out of
  date, a distributional row rated "good" at 5.86pp, and a CONTRIBUTING guide
  missing three of CI's blocking steps. `ROADMAP.md` is now an index naming this
  file as the active plan.

Two further defects surfaced along the way and were fixed:

- **The API reported `"baseline_vintage": "unknown"` for every real score**
  (`6036848`). The projection the serializer reads carried no vintage; the API
  tests only ever used a fake baseline that did.
- **Two order-dependent tests.** The API-security fixture re-read the
  environment before `monkeypatch` restored it, which left auth switched on for
  later tests in the same worker once the module's last test set a key; and
  `dark_template()` returned a different object on its first call than on every
  later one, because Plotly copies on registration.

**One finding is recorded, not fixed, because it moves numbers and needs its
own lane.** `score_policy(dynamic=True)` runs `EconomicModel`, whose supply
channel multiplies *all* of nominal GDP by `-rate_change x
labor_supply_elasticity`, with no weighting by the share of labour income the
change reaches. For +2.6 points on income above $400,000 over FY2026-2035:
conventional **-$302.2B**; the app's dynamic view (FRB/US-Lite) **-$338.9B**;
`EconomicModel` **-$86.1B**, its -$216.1B of feedback erasing 72% of the static
score. The app's pages use FRB/US-Lite, but `POST /score` and `/score/preset`
with `dynamic: true`, the Ask assistant's scored hypotheticals, the comparison
tabs and the CSV export's GDP columns read `EconomicModel`. Two options, which
are an owner decision: weight the channel by a sourced affected share (a
pre-registered modelling lane under priority 3), or route those surfaces
through the adapter the app already uses (a contract change for API clients).
`docs/METHODOLOGY.md` previously described `EconomicModel` as the app's default
dynamic engine; it now says which surface reads which.

**The owner chose routing, the same day** (`4726e68`). The finding above stands
as the record of what was measured; this is what was done about it.
`fiscal_model/dynamic_view.py` is the app's dynamic view with no UI attached:
the conventional path, the macro scenario built from it, the adapter the model
setting names (FRB/US-Lite by default), and the `DynamicView` decomposition. The
app delegates to it, and its own dynamic figures are byte-identical across 45
presets x both macro models. `POST /score` and `/score/preset`, Ask's
`score_hypothetical_policy` and the Ask page's scoring context now call it too.
The engine is asked only for a conventional run, so `EconomicModel` never runs
for the API or Ask, and a test that makes it raise proves so.

- **The API's contract changed for dynamic requests, and only for them.**
  `ten_year_deficit_impact` stays the conventional score. It used to move by
  `EconomicModel`'s feedback and be repeated as `dynamic_adjusted_impact`, which
  is now conventional - feedback + debt service. `debt_service`,
  `dynamic_model` and per-year `debt_service` and `dynamic_effect` are new, and
  a macro-model failure nulls the dynamic fields with an `error_message` rather
  than failing the score. The reference policy's dynamic answer went
  **-$86.1B -> -$338.9B**, the app's figure. Every one of the 53 presets'
  dynamic answers moved. `EconomicModel`'s feedback had been a median 1.53x the
  adapter's in magnitude. TCJA's full extension went +$3,951.4B -> +$5,238.8B:
  its feedback fell from +$630.6B to +$305.3B, and +$962.2B of debt service,
  which the old figure never netted, now counts. No static response moved: all
  53 are identical apart from the new null fields, and `final_static_effect`
  moved in none.
- **The in-app readers went with it.** The Scoring Methods tab's
  "FRB/US-Lite (Dynamic)" column ran `EconomicModel`. So did the side-by-side
  compare's totals, the state tab and the SALT and AGI-column captions, on a
  dynamic run. The cumulative chart's band and the CSV's Low/High columns were
  centred on `EconomicModel`'s path while the line they surround is the
  conventional one, and the CSV's GDP and employment columns were
  `EconomicModel`'s under a header naming FRB/US-Lite. The tariff caption stopped
  claiming a dynamic run's headline applies feedback, which has not been true
  since Phase 4 fixed the headline to the conventional score. The Methodology
  page's dynamic-scoring notes named FRB/US-Lite and then printed
  `EconomicModel`'s state-dependent multiplier table; they now describe the
  model the view runs (`4461459`).
- **Ask's spending hypotheticals had never worked.** The tool passed
  `spending_change_billions`, which `SpendingPolicy` rejects, so every spending
  question came back "could not construct policy". Had it constructed, the
  dataclass would have re-derived `policy_type` from its default `nondefense`
  category. Both are fixed.

`cold_holdout.py --json`, `run_validation_dashboard.py`, `run_loo.py
--donor-matrix` and strict readiness are byte-identical. `EconomicModel` is
unchanged: weighting its supply channel by a sourced affected share is still the
pre-registered modelling lane under priority 3, and until it lands no surface
reports it. *(R9, 2026-10-10, landed it: the labour effect is weighted by the IRS
SOI share of AGI above the policy's threshold, and the reference policy reads
-$206.4B through `EconomicModel`; see
`planning/lanes/R9_economic_model_supply_weighting.md`.)*


## Status, 2026-10-03: re-review and the second round

This section records a fresh review of revision `e663cc0` and what was done
about it. The assessment above and the two status sections before this one are
left as written.

### Re-score: 7.0 before, 8.0 after, not 9

**Before: about 7/10**, half a point *below* the 7.5 on file, because a defect
hunt that went looking for what the first review did not (security, API
contracts, URL handling, the Ask tool loop) found things that had been missed.
**After: about 8/10.** Nine would need the plan's priority 5 — no more than 10%
pooled out-of-sample error with no supported class above 20% — and nothing
changed in this round moves it: the tier is still **15.2% over 44**, corporate
still **40.3%**. Reaching it without retuning or dropping hard cases is a
modelling programme, not a session, and the plan's own anti-gaming rules forbid
the shortcuts. The honest reading of this round is that **everything that could
be verified and repaired without touching a validation number was**, and the
half-point it did not buy is the half-point those rules reserve.

**Verified on the merged tree rather than lane by lane:** the full suite is
**4,653 passed, 7 skipped, 23 deselected** (the browser journeys, opt-in); ruff
at CI's pinned 0.15.8 and the blocking mypy gate are clean; and
`cold_holdout.py --json`, `run_validation_dashboard.py` and
`run_loo.py --donor-matrix` are **byte-identical** to the pre-round tree. No
scored number moved.

### Defects found and fixed (each reproduced first; each test fails on the old code)

1. **SSRF in the Ask `fetch_url` tool.** `http://127.0.0.1:PORT\@cbo.gov/`
   passed the domain allowlist (`urlparse` host `cbo.gov`) while `requests`
   connected to `127.0.0.1`; a local server returned its body through the tool.
   The host is now taken from the URL that will actually be fetched and must
   agree with `urlparse`; userinfo, backslashes, control characters, non-http(s)
   schemes and odd ports are refused; redirects are followed by hand (at most 3
   hops, each re-validated); non-global addresses are refused; the response is
   capped at 5 MB. The DNS check is a pre-flight, so rebinding is narrowed, not
   closed.
2. **Ask headlines were anchored on retired targets.** The four rows PR #162
   withdrew for want of a document were still handed to the model as
   "official" anchors, so a 3pp cut headlined **$600B against an engine run of
   $3,855B**. Retirement is now derived from the pre-registered ledger, so no
   retired id can anchor.
3. **`POST /score` priced `corporate_tax` and `payroll_tax` on the
   individual-income base** — 1pp scored −$1,420.3B for both against the
   corporate module's −$198.9B. Corporate now routes to `CorporateTaxPolicy`;
   payroll returns 400 rather than a wrong number.
4. **`duration_years` was a no-op** for tax policies on the API and in Ask
   (1, 3 and 10 years scored identically). It now takes effect.
5. **Ask accounting.** Usage is booked after each model call, so a client that
   drops the stream is still counted; an upstream failure is a 502 (and an SSE
   `error` event), not a 200 carrying error text; web-search fees are priced;
   an unknown model id is priced at the dearest tier, not Sonnet's.
6. **Cross-request state.** `/ask` shared one `FiscalAssistant`, so two
   concurrent requests overwrote each other's usage (reproduced: Bob's tokens
   counted twice against the cap). Each request now gets its own copy.
7. **Share links.** `?rate=12` crashed Tailor; `?target=nan|inf` crashed Build;
   one non-finite parameter silently discarded a whole Tailor link. Values are
   clamped or dropped individually. A first version also rounded `rate` to the
   slider's step, which would have silently changed what an existing link scores
   (`2.6` → `2.5`, and the −$302.2B reference reproduction with it) and broken
   frozen, spec-hashed links; that was caught in review and reverted, so a link
   scores what it says.
8. **Markdown injection into trusted banners.** URL-supplied `baseline=`,
   `engine=`, `spec=` and `?preset=` values were interpolated into
   `st.error`/`st.info`, producing a clickable attacker link inside the app's
   own "frozen assignment" refusal. They render as inert code spans now.
9. **Forged Ask share tokens.** The token is unsigned and its "assistant" turn
   was replayed to the model as history; the share decoder also inflated before
   checking size (a 39 KB token expanded to 30 MB). Shared turns are display-only
   and the decoder is bounded.
10. **Public `/health`, `/summary`, `/readiness` leaked absolute server paths,
    the interpreter and the usage-db path**, and `/readiness` cost ~8s per
    unauthenticated call. Paths are now repo-relative and `/readiness` is cached
    for 60 seconds.
11. **Smaller:** `/score/tariff` accepted `import_base_billions=1e12` (a −$587T
    answer) and an unused `target_country`; `/score/preset "Custom Policy"`
    scored a UI placeholder; `score_package` ignored `interaction_factor` for the
    behavioural offset and raised on an empty package; nine ruff findings sat in
    `api.py`, which CI never linted (it does now).

### Priorities 3, 4 and 6 of the plan

- **Priority 6, browser verification — landed.** `tests/e2e/` drives the real
  app in Chromium: 22 journeys pass (scoring, edit, share round-trip, CSV
  export, mobile overflow, keyboard), each asserting a latency budget, no
  exception block, no stray console error and no page-level horizontal scroll;
  it is excluded from the default run and has its own CI job that *fails*
  rather than skips if the browser is missing. It found real defects: doorway
  cards had **no keyboard focus indicator** (fixed, contrast-pinned in both
  themes) and the ⚙ control had no usable name (now "⚙ Settings").
  **Not fixable from app code and recorded as such:** Streamlit's own chevron
  text leaks into popover/expander names; the skip link sits eighth in tab order
  (`ui/a11y.py` emits it in the body); and on a narrow *desktop* user agent the
  nav drawer stays open after a tap (it closes on a real mobile UA — the first
  report of this was a test-harness artefact). Production latency was **not**
  measured; the local budgets are ~2.5× observed.
- **Priority 4, interactions — partly landed.** The Build page used to say only
  "no interaction effects". It now classifies the package, names the overlapping
  pairs, flags list prices that cannot all be true at once (TCJA's full
  extension plus AMT *repeal* — the repeal's $450B is below the $1,357B the
  extension's own AMT relief is worth), and for the pairs the microsim can
  express shows a **measured interaction as a share, not a dollar figure** — a
  +2.6pp top-rate rise alongside SALT-cap repeal yields **13.7% less than the
  two sum to**; a $1M surtax alongside it **20.2% less, and the sign flips**.
  Rate × AMT, rate × credits and CTC × EITC are **structurally additive** in
  `MicroTaxCalculator` and are labelled so, never as a measured zero. **The
  package total is still the sum of list prices**; nothing is jointly scored in a
  headline number, and corporate, estate, payroll, tariffs and the TCJA
  composite remain additive-only.
- **Priority 3, shared population — measured and offered, not made the
  default.** The default CPS run holds **119.0% of SOI returns and 81.0% of
  AGI** because *no calibration is applied on any default path* (`reweight_to_soi`
  has no caller outside its tests) and the AGI definition omits pensions,
  self-employment and rents. `--calibrate-cells` (library:
  `calibrate_cells_to_soi`) post-stratifies on 19 AGI classes × filing status to
  IRS SOI Table 1.2 and takes the run to **100.0% / 100.9%**, with held-out
  taxable income at 106.2% and income tax at 102.7% of SOI. **It is opt-in
  because it moves scored numbers:** the SALT-repeal distributional row goes
  **5.86 → 11.01pp worse** (the 5.86 was a cancellation, now exposed — recorded
  as a registered regression, not retuned) and three credits rows move
  (`biden_ctc_2021` −1,528.5 → −1,440.5, `ctc_extension` −714.2 → −799.6,
  `biden_eitc_childless` −110.4 → −176.8 against −162.6). Making it the default
  needs pre-registration and an owner decision; see
  `planning/lanes/R6_microdata_cell_calibration.md`.

### Carry-overs, in order of what they would buy

1. **Priority 5** — the only thing between 8 and 9, and not available by edit.
2. Decide whether `--calibrate-cells` becomes the default (moves three credits
   rows and the SALT distributional row; the synthetic top tail is stamped
   California, a suspected contributor to the SALT regression, unmeasured).
3. Joint scoring inside the package headline for the supported pairs.
4. Ask's `suggest_followups` and cache pre-warm calls are not in the cost
   ledger, so that spend never reaches the daily cap.
5. Money renders as `$+4,581.9B` / `$-302.2B` (sign after the dollar) at about
   93 sites; one shared formatter and a test sweep is the fix.
6. The skip link, the Ask page's key-help expander name, and a measurement of
   the *production* app's latency (`E2E_BASE_URL=… E2E_LATENCY_SCALE=3`).
7. The Ask page prints a "Pilot quality blocker" alert on routine presets, which
   the browser run flagged and nobody has yet decided is intended.

## Status, 2026-10-04: carry-overs from the re-review

The 2026-10-03 section's carry-overs, worked in four parallel lanes plus
follow-ups. **No scored validation number moved**: `cold_holdout.py --json`,
`run_loo.py --donor-matrix` and the full `run_validation_dashboard.py` text are
byte-identical to the pre-round tree, and so are all seven distributional
benchmarks. The score stays **about 8/10**: this round made the 8 sturdier
(one green-core distributional defect, one wrong price table, one live
uncapped spend path, a misleading pilot alarm) and did not touch priority 5,
which is still what stands between 8 and 9.

### Fixed (each reproduced first; each test fails on the old code)

1. **Distribution tables summed group money unweighted** (`R7_weighted_group_totals.md`).
   `create_groups_from_microdata` weighted the return counts and not the AGI,
   taxable income or baseline tax, so the CPS top quintile showed an average AGI
   of **$132 instead of $309,920**, and the tax-unit branch's `pct_with_*`, ETR
   and %-of-income columns were unweighted too. Pre-registered by a scratch
   sweep of 45 tables before the fix; the outturn was byte-identical to the
   prediction. Shares, totals and every headline progressive/regressive call
   are unchanged (they were already weighted); the seven benchmarks are
   bit-identical because they score only already-weighted fields.
2. **An all-bracket rate change reached only the top bracket in distribution
   tables** (R7 §7). A threshold-0 `TaxPolicy` mapped to
   `new_top_rate = 0.37 + Δ`, so Flat Tax Reform's distribution table summed to
   **−$9.37B against a −$612B revenue score** (0.34% of returns affected). It now
   uses the same post-tax adder as every other threshold: −$461.15B, 59.8%
   affected. Top-bracket-only presets are pinned byte-identical. The adder
   ignores the AMT for every rate change, which is now named as an engine
   follow-up.
3. **The public Build page's "Translate to a package" made uncapped Sonnet
   calls**, as did Ask's follow-up suggestions and cache pre-warm: none
   checked the daily cap or wrote a ledger row. All now check
   `budget_allows` first and record via `record_paid_call`, under their own
   event labels so the admin view can tell spend apart.
4. **The Ask price table was wrong.** Haiku 4.5 at $0.80/$4 (it is $1/$5), Opus
   4.7 at $15/$75 (it is $5/$25), and no Fable 5.1 — so the "price an unknown
   model at the dearest tier" fallback was not the dearest model. Snapshot ids
   now match the *longest* known prefix (`claude-opus-5-5-…` also starts with
   `claude-opus-5-`).
5. **The keyless Ask page showed the public the names of the deployment's
   secrets** (`st.secrets accessible: True`, every top-level key). The public
   now sees one line; setup help needs the admin token or
   `ASSISTANT_SHOW_SETUP=1`.
6. **"Pilot quality blocker: implausible gaps" was a false alarm on every
   preset.** 43 of 52 presets have one engine that can score them; the
   assessment counted "only one result" as a quality failure and the tab
   printed a gap claim with no gap (`max_gap` was `None` on all 43). One-engine
   presets now get a coverage note; a blocker names the two engines and their
   estimates. The real large gaps (Warren surtax 72%, Progressive Millionaire
   64%, EITC childless 46%) still show as disagreement. The SALT pilot had been
   scoring exactly $0 because the CPS file has no SALT columns; it now refuses.
   The pilot tab also opens on the preset the reader scored, not the first one.
7. **Money printed the sign after the dollar** (`$+4,581.9B`) at 99 UI call
   sites. One formatter now prints `+$4,581.9B`; digits are Python's own,
   only the sign moved; a guard test greps the UI tree and a rendered Explore
   check fails on the old pattern.
8. **The skip link was the 8th Tab stop.** It is now the first (`tabindex="1"`
   on that one element; Streamlit's header precedes `stMain` in the DOM, so
   reordering from app code cannot work). The e2e xfail is a hard test.

### Corrected claims

- `distributional_validation.py`'s **105.9% is relative share error** on a
  single TPC 2018 TCJA table, not a failing gate: the same comparison in the
  dashboard's metric is **6.94pp**. It is the only independent check of the
  calibrated TCJA tier table (the dashboard's two TCJA rows are circular); the
  script now prints both metrics.
- The distribution tab claimed "benchmarked against CBO/JCT tables within
  ≤3pp"; the tables span 0.00–5.86pp and only two exercise that path.
- R6's guess that California-stamped synthetic rows drove the SALT regression
  under `--calibrate-cells` was wrong: the row is unchanged to 1e-15 under any
  state draw, because all 800 synthetic rows are AMT-bound.

### Decision now open to the owner

`planning/lanes/R6b_make_calibration_default_preregistration.md` pre-registers
making SOI cell calibration the default. It would **turn the dashboard red**
(the SALT distributional row 5.86 → 11.01pp crosses a gate) until the SALT
mechanism — flat-rate imputation and AMT-bound synthetic rows — is fixed, and
would move leave-one-out credits 18.5% → 17.3% and the health check to `ok`.
It is not flipped.

**Taken 2026-10-10, together with the SALT mechanism fix**
(`planning/lanes/R6c_salt_mechanism_and_calibration_default.md`). The AMT was
the cause: it taxed gains at 28% with no exemption phase-out, so it bound on
every $1.5M+ return. With a statutory AMT and SOI Table 2.1 SALT ratios, the
calibrated default reads 5.65pp and the dashboard exits 0. Every
pre-registered number reproduced exactly; no revenue score moved.

### Still open

Priority 5; joint scoring in the package headline; production latency (the
environment's network policy denies the deployed host); the AMT-blind rate
adder; `bill_tracker/provision_mapper.py`'s offline LLM call is uncapped by
design.
