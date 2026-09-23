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

- [ ] **Package uncertainty:** remove dependence on the first policy and verify
  order independence and correctly ordered bounds for positive and negative
  deficit effects.
- [ ] **API log redaction:** generate a non-secret identifier or require a safe
  label; cover unlabelled keys and empty-label configurations in log tests.
- [ ] **Generated validation summaries:** establish one versioned source for
  current metrics and vintages, update consuming surfaces, and distinguish
  current status from historical roadmap prose.

After these repairs, concentrate development on the shared scoring population
and policy interactions. Those changes offer the clearest improvement in what
users can trust.
