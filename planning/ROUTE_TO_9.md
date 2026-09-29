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
reports it.

