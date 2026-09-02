# Changelog

Material changes to the Fiscal Policy Calculator. Trivial fixes are captured
in git history, not here.

## 2026 — ongoing

### Tier-2 target revisions, and a supersede rule for the calibrated tier (2026-09-02)

PR **#90**. Two modelling lanes had referred *target* problems out of Wave 1:
L5 (`amt.py`) found its structural path landing about 1.8× closer to the document
than its fitted constant but could only say so, because the carried target
disagreed with the document; L7 (`pharma.py`) fixed an incidence bug and was
rewarded with a *worse* percentage, because its benchmark pointed the opposite
way. **No modelling change**: no constant retuned, no mechanism altered, no CI
threshold touched.

The calibrated tier had no supersede rule, so this adds the smallest mirror of
`preregistered.py`'s — `fiscal_model/validation/target_revisions.py`. The old
figure stays as a row marked `superseded_by`; the new row carries document,
table, row, page, date and a reason; `target_revision_problems()` fails if the
ledger and the registries the app reads ever disagree. Ledger entry and first
scoring are separate commits, so "the target moved before the model was allowed
to see it" is checkable from `git log`.

| Benchmark | Was | Is | Document |
|---|--:|--:|---|
| `extend_tcja_amt` | $450.0B | **$1,357.1B** | CRS **R48286** Table 1 (transcribing CBO 60114/60271) — "Increased Alternative Minimum Tax Exemption", FY2025–FY2034. The adjacent five-year column prints $466.2B, so $450B was 3.5% from the five-year cost and 66.8% from the ten-year one: a five-year figure in a ten-year column. Corroborated by JCT **JCX-35-25** at $1,362.810B (0.4% away) for P.L. 119-21's AMT provision. |
| `universal_insulin_cap` | −$15.0B (a saving) | **+$11.4B (a cost)** | CBO pub. **57957** (H.R. 6833), table p. 1 — outlays 6,566, revenues −4,793, FY2022–2031. A $35 monthly cap is a *cost-sharing* cap: it moves liability onto the plan and onto the federal subsidy for it. |
| `repeal_individual_amt` | $450.0B | **not moved** | Nothing to move it to — see below. |

**The tiers moved; report them separately, as always.**

| Tier | Before this PR | After |
|---|---|---|
| Out-of-sample, pre-registered (n=25) | 34.4% / 16.1% median / 12 within 15 / 16 within 25 | **unchanged** |
| Calibrated, fitted | 34 @ 2.7%, 33/34 within 15 | **33 @ 2.8%, 32/33** — or **34 @ 4.7%, 32/34** held in place |
| Unfitted module reconstructions | 20 @ 82.6% / 43.1% median | **21 @ 76.7% / 41.0%** |
| — 12 sectoral presets | 113.8% / 57.1% median | **104.8% / 40.0%** |
| Calibrated, leave-one-out | 18 @ 61.7% / 35.6% median | **18 @ 58.7% / 32.5%** |
| Calibrated provenance | 17 `line_item` / 15 `differs` / 15 `secondhand` / 7 `model_estimate` | **19 / 13 / 15 / 7** |
| Sectoral rows disagreeing with their target on **sign** | 1 | **0** |

- **A revised row leaves the fitted tier, and the summary says so.** A constant
  fitted to a superseded figure is not fitted to its replacement, so
  `scorecard.py` derives `calibrated_to_target` from the ledger and
  `extend_tcja_amt` reports among the unfitted reconstructions, where a miss is a
  finding rather than a regression. `ScorecardSummary.revised_target_entries`
  (= **2**) is on the scorecard and on `/validation/scorecard`, so the move can
  never be silent. **Quote "33 at 2.8%" only next to the statement that a 34th
  row moved out**, and never retune the constant to close the 66.8% — that is the
  move a provenance pass is forbidden to make.
- **The LOO fall is a target moving, not a model.** `extend_tcja_amt`'s held-out
  derivation is **unchanged at $855.3B**; its error against the corrected row is
  −37.0% instead of +90.1%, taking the AMT module 100.5% → 73.9% and the suite
  61.7% → 58.7%. No donor-matrix entry moved.
- **`KNOWN_TARGET_SIGN_INVERSIONS` is now an empty set**, and the emptiness is
  the assertion: no scorecard row disagrees with its own target about what a
  policy does.
- **`AMT_APP_MODE` and `AMT_SCORECARD_MODE` stay `reported`.** Across the three
  AMT benchmarks reported means **22.3%** against derived's **54.2%**, which is
  owner Decision 1's own rule, so **no shipped number changes**. Read past the
  mean: both rows on which derived loses are targets a constant was fitted to, so their
  ~0% is bookkeeping — and the one AMT benchmark no constant was fitted to is the
  one derived wins, 37.0% against 66.8%.
- **`repeal_individual_amt` keeps an unsourced, internally incoherent target.**
  No published post-2025 repeal score exists at JCT, CBO or TPC. TPC T25-0049's
  $948.9B is deliberately not adopted: it is a baseline projection rather than a
  scored repeal, *and* it is `amt.py`'s own input, so adopting it would
  manufacture a 0% row out of the leakage `loo.py` guards against. Closing it
  needs a published score or an owner decision to re-register `holdout.py`'s
  locked `revenue-scorecard-post-lock-2026-05-02` protocol — which has no
  re-registration path. `check_readiness.py --strict` is unchanged from the base
  commit.
- **Two user-facing labels moved with their targets** (slugs unchanged, so no
  share link breaks): `⚖️ AMT: Extend TCJA Relief ($450B)` → `($1.36T)`, and
  `💊 Universal Insulin Cap (-$15B)` → `($11B)`. `/validation/scorecard` and the
  Validation tab now carry `target_revision_id`, `superseded_10yr_billions`,
  `target_revision_reason` per entry and a "Target moved from" column.

### Tier 1 CI gate tightened to 45 / 15 (2026-09-02)

PR **#91**. The out-of-sample gate's own rule — ceiling = `ceil(mean × 1.25)`
rounded up to the nearest 5, floor = the current count within 25% minus one —
derives **45 / 15** from the post-Wave-1 battery (25 cases, 34.4% mean, 16 within
25%), against the **55 / 13** the workflow carried. Both are tightenings, which
the rule says need no reason. The derivation is recorded in the workflow comment
beside the earlier ones, and the places that quote the command now match.

### Modelling Wave 1 — spend-out, AMT, pharma incidence (2026-09-02)

Wave 1 of [`planning/MODELING_IMPROVEMENT.md`](../planning/MODELING_IMPROVEMENT.md),
three lanes on disjoint files plus a follow-up, with the owner's six §6 decisions
recorded first. Every lane pre-registered its expected movement in
`planning/lanes/` **before** touching code; §5.1 of the plan carries the outturn
and the three findings. PRs **#83** (decisions), **#85** (L2 spend-out),
**#86** (L5 AMT), **#87** (L7 pharma), **#88** (IIJA authorization path + app
spend-out).

**Validation tiers moved. Report them separately, as always:**

| Tier | n | Before | After |
|---|--:|---|---|
| Out-of-sample, pre-registered | 25 | 52.6% mean / 21.1% median / 8 within 15 / 14 within 25 | **34.4% / 16.1% / 12 / 16** |
| Calibrated, fitted | 34 | 2.7% / 33 within 15 | **unchanged** |
| Unfitted module reconstructions | 20 | 250.8% / 43.1% median | **82.6% / 43.1%** |
| — 12 sectoral presets | 12 | 394.1% / 57.1% median | **113.8% / 57.1%** |
| — 8 P.L. 119-21 line items | 8 | 35.8% | **unchanged** |
| Calibrated, leave-one-out | 18 | 59.3% / 35.6% median / 6 within 15 | **61.7% / 35.6% / 6** |
| Distributional | 7 | 0.00–5.86pp | **unchanged** |

*Two of these Tier 2 figures moved again the same day, in the target-revision
entry above; the numbers here are Wave 1's outturn, not the current ones.*

- **Budget authority and outlays are now distinct quantities (L2).**
  `SpendingPolicy` no longer books a funding level straight into outlays;
  `outlays_t = Σ_k s_k · BA_{t−k}`, with `s` an account-class profile fitted by
  non-negative least squares on the 14 CBO options that publish both an
  authority row and an outlays row **and are not scored by the battery**. The
  five scored options never donate. Class assignment is a classification from
  the account type each program funds, never a fit. **Finding:** owner Decision
  2 named OMB Circular A-11 §32 as the primary source; A-11 §32 is personnel
  compensation and A-11 publishes **no** outlay-rate table in any section, so
  the decision's own fallback governed and the CBO donor options shipped as
  primary. CBO's account-level rates (publications 61913, 62256) are the open
  cross-check, blocked by cbo.gov 403s.
- **IIJA is scored on the schedule its source states (#88).** The shape input
  was superseded under the manifest's own rule — a **new row**, never an edit —
  in two commits, entry before scoring. `iija_2021_discretionary.v1` stays on
  the record (+$1,894B, 356%; +$1,621B, 290.2% after spend-out); `.v2` carries
  CBO's own authorization path and scores **+$340.0B against an unchanged
  +$415.4B target, 18.2%**. What remains is a window mismatch: $92.6B of the
  path's outlays fall in FY2022-2024, before the model's FY2025-2034 window
  opens. Earlier docs saying IIJA "is kept at 356% deliberately, as the sharpest
  evidence for the missing spend-out model" are now history on both halves.
- **The Fiscal Responsibility Act row got worse, as pre-registered** (5.8% →
  12.2%). The old figure was two errors cancelling; a correct spend-out removes
  one and leaves the other, so the total error rises while the path gets more
  right.
- **AMT gained a live exemption branch and a published year-indexed path (L5).**
  The exemption-change branch had been dead code, so no exemption change had
  ever been scored. The path is TPC Table T25-0049, transcribed to
  `fiscal_model/data_files/amt/`. **Finding:** the plan's "missing 2026 ramp"
  hypothesis was **wrong** — T25-0049 shows a *cliff* (0.2M → 7.6M AMT payers,
  2025 → 2026) and then *growth* ($71.6B → $124.2B by 2035), so the flat
  ~$73B/yr was the window's early-year level and indexing it **raises** the
  score. Both AMT LOO rows moved away from their carried $450B targets (+73.2%
  → +90.1%, +86.0% → +110.9%) while the extension moved *toward* the published
  line item ($1,357.1B: −66.8% fitted → **−37.0%** derived). **App default stays
  `reported`**; nothing a user sees changed. `docs/VALIDATION_NOTES.md` §6 was
  corrected rather than deleted.
- **Drug pricing now scores federal incidence (L7).** A $35 insulin cap is a
  cost-sharing cap, so the federal budget picks up only its share of the
  liability shift; and international reference pricing is scored on a net-price,
  brand-only, federal-share basis (US unbranded generics are *cheaper* than the
  OECD comparison and cannot contribute savings). Every input is transcribed
  with document, page and URL to
  `fiscal_model/data_files/pharma/drug_pricing_incidence.csv`. No parameter was
  fitted to any of the three pharma benchmarks. **Still unrepaired:** RAND's
  index is computed on presentations sold in both markets and the module applies
  it to all brand spending; no utilisation, launch-delay or availability
  response is modelled on either row.

**Shipped preset numbers moved.** No preset label and no `CBO_SCORE_MAP` entry
changed — labels carry the official score or an annual funding level, not the
model's ten-year total.

| Preset | Before | After |
|---|--:|--:|
| 💊 Universal Insulin Cap | −$445.3B | **+$7.0B** |
| 💊 International Reference Pricing | −$1,387.9B | **−$746.2B** |
| 💊 Comprehensive Drug Reform | −$1,025.8B | **−$573.5B** |
| 💊 Expand Drug Negotiation | −$371.5B | unchanged |

The insulin cap now reads as a deficit *increase*, which is what CBO scores for
the same policy (publication 57957, +$11.4B); the carried −$15B benchmark is the
thing still pointing the wrong way.

**Every spending program's 10-year outlays now follow a spend-out profile.** The
label still quotes the annual funding level, which is budget authority and is
unchanged; only the ten-year outlay total moved. Each score renders one line
naming its profile and its outlay/authority ratio, computed from the scored
result. `immediate` stays reachable under Economic parameters and is the default
for nothing.

| Program (Tailor) | Account class | 10-yr before | 10-yr after | outlay/authority |
|---|---|--:|--:|--:|
| Custom program | construction and capital | +$1,095.0B | **+$725.4B** | 0.663 |
| Infrastructure Investment ($100B/yr) | construction and capital | +$1,146.4B | **+$749.8B** | 0.654 |
| Defense Spending Increase (+10%) | operations and support | +$985.5B | **+$880.2B** | 0.893 |
| Universal Pre-K ($40B/yr) | grants and procurement | +$458.6B | **+$386.9B** | 0.844 |
| R&D Investment ($50B/yr) | grants and procurement | +$600.3B | **+$503.8B** | 0.839 |
| Discretionary Spending Cut (−$50B/yr) | operations and support | −$547.5B | **−$489.0B** | 0.893 |
| Disaster Relief ($30B one-time) | grants and procurement | +$30.0B | +$30.0B | 1.000 |
| Student Debt Forgiveness ($400B one-time) | benefit payments | +$400.0B | +$400.0B | 1.000 |
| Universal Childcare ($100B/yr) | grants and procurement | +$1,146.4B | **+$967.4B** | 0.844 |
| Medicare Buy-in Age 55+ ($50B/yr) | benefit payments | +$573.2B | **+$571.7B** | 0.997 |
| High-Speed Rail Program ($30B/yr) | construction and capital | +$328.5B | **+$217.6B** | 0.663 |

The two one-time programs are unchanged because their whole spend-out tail lands
inside the window — the timing moves, the total does not. Explore ships no
spending preset.

**Owner decisions recorded (#83).** All six of the plan's §6 questions were
answered on 2026-09-01: keep `reported` and `derived` modes; A-11 as the primary
spend-out source (superseded by finding 1 above, via the decision's own fallback
clause); freeze Dowd–McClelland–Muthitacharoen (2015) capital-gains elasticities;
fetch raw CPS ASEC by script rather than vendoring it; move the three
tautological credit benchmarks to documented exclusion; ship the tariff
gross→net change with its UI note.

**No yardstick was touched.** `preregistered.py`'s targets, `cold_holdout.py`,
`run_loo.py`, `loo.py`'s leakage guard, `tests/test_preregistration.py` and the
CI thresholds are all unchanged. The CI derivation rule now implies a ceiling of
45 and a floor of 15 against the workflow's current 55 and 13; both pass with
room and tightening them is left to whoever lands next. *(Done in PR #91, above.)*

### Documentation honesty sync (2026-09-01)

*Superseded on 2026-09-02 by the Wave 1 entry above: the tier figures below were
correct when written and are kept as the record of that change, not as current
numbers.*

- `docs/METHODOLOGY.md` now reports **four validation tiers separately** and
  states outright that there is no single "validated within X%" figure:
  out-of-sample pre-registered (25 cases, 52.6% mean / 21.1% median, 8/25 within
  15%, 14/25 within 25%), calibrated-and-fitted (34 at 2.7%), unfitted module
  reconstructions (20 at 250.8% mean / 43.1% median — 12 sectoral presets at
  394.1% plus 8 P.L. 119-21 line items at 35.8%), and calibrated leave-one-out
  (18 derivable at 59.3% mean / 35.6% median, 4 not cross-validatable). It
  previously carried a stale 23-case/43.4% Tier 1 and a "29 benchmarks ≈ 5%"
  Tier 2.
- **Step-up lock-in multiplier corrected.** METHODOLOGY printed `5.3×` as the
  current-law setting. The module default is **2.0**
  (`CapitalGainsPolicy.step_up_lock_in_multiplier`), and `5.3` is set only by
  the `pwbm_39_with_stepup` validation scenario, where it is fitted to reproduce
  PWBM's revenue loss. (Tests assert that scenario's value and the docs discuss
  it; those reference the same constant rather than adding uses of it.) The document now says which multiplier each
  published result was produced with, and records that the 5.3× is a known
  answer key (`run_loo.py --donor-matrix`), not a parameter.
- **Distributional claim replaced.** The two-line "vs. TPC TCJA analysis"
  summary is now the seven published CBO/JCT tables at 0.00-5.86pp, with the two
  circular ones (CBO 54796, CBO 60007) named as circular.
- **IRS SOI vintage.** METHODOLOGY contradicted itself on the tax-year basis; it
  now states that tax years 2021-2023 ship and production scoring runs on **tax
  year 2023**, and that tax-year (calendar) aggregates are carried into a
  fiscal-year window without conversion.
- `planning/MODELING_IMPROVEMENT.md` §2 error budget and §5 sequencing
  re-derived against the post-Phase-D/E battery; `planning/NEXT_STEPS.md` lost
  its "25+ policies validated within 15%" line.


### Ask assistant (May 2026)

- New **💬 Ask** tab (now the second top-level tab) and matching
  `POST /ask` + `POST /ask/stream` (Server-Sent Events) endpoints expose
  a citation-grounded Q&A assistant. Streams answers from Claude
  Sonnet 4.6 with tool access to the app's scoring engine, CBO baseline,
  validation scorecard, 49 preset policies, and 19 hand-curated
  authoritative snapshots covering CBO baseline, SSA Trustees, TCJA,
  capital gains, international tax, retirement-account taxation, IRA
  clean-energy credits, tariff scoring, JCT distributional methodology,
  fiscal multipliers, ETI literature, state/local fiscal interaction,
  debt sustainability, dynamic-scoring concepts, JCT tax expenditures,
  TPC TCJA distribution, PWBM TCJA dynamic, Yale Budget Lab tariffs,
  CBO long-term outlook, and a common-confusion FAQ.
- **Citation discipline is structural, not aspirational.** The model is
  required to emit `[^N]` footnote markers on every substantive claim.
  A post-processor cross-references each marker against the per-turn
  tool-call provenance log; unsupported markers are stripped and
  replaced with `[citation needed]`, surfacing as a defect to the
  reader.
- **Hard usage caps protect the deployer's API spend.** A sqlite-backed
  `assistant_events` ledger (also serves as the telemetry log)
  enforces a daily cost cap (`$5/day` default), per-session message
  cap (20), cool-down between messages (3s), and an
  `ASSISTANT_DISABLED` env-var kill switch. The same ledger is shared
  by the Streamlit tab and the FastAPI endpoints so a busy API caller
  cannot drain the UI budget.
- **Token-gated admin dashboard** (`💼 Admin` tab) shows today's spend
  vs. cap, KPIs (cache-hit ratio, error rate, avg cost/turn), the
  30-day daily-cost series, tool-usage frequency, and the recent-turn
  table — visible only when the URL has `?admin=<token>` matching
  `ASSISTANT_ADMIN_TOKEN`. Non-admins do not see the tab label.
- **Share-this-answer button.** Each assistant turn includes a 🔗 Share
  affordance that builds a URL containing the full Q+A+provenance as
  a gzip+base64 payload (no backend state). Recipients land on the Ask
  tab with the exact pair pre-rendered. SHARE_SCHEMA_VERSION makes
  future evolution graceful; MAX_DECODED_BYTES guards against
  decompression bombs.
- **Health/readiness wiring.** `/health` now carries an `assistant`
  component with three sub-signals (API key, knowledge corpus size,
  usage db reachability). The assistant is marked `required=False` in
  `/readiness` so a missing key on a CI runner or dev box reports as
  "degraded / warn" without blocking deploy. Older synthetic health
  payloads stay backward-compatible — the new check is skipped when
  the `assistant` key is absent.
- **Streamlit-Cloud secrets are auto-promoted to env vars** on first
  render. A Levenshtein-based typo detector surfaces near-miss key
  names (e.g., `ANTHROPHIC_API_KEY`) inline in the unavailable-key
  diagnostic. End users are never asked to enter an API key.
- **Latency tuning.** `DEFAULT_MAX_TOKENS` reduced from 1600 to 800.
  Follow-up question generation moved to a separate Streamlit rerun so
  it doesn't block answer finalization. Prompt cache pre-warms on a
  daemon thread at app boot so the first real turn skips the
  cache-creation tax. Typical turn: 5-7s, $0.01-$0.02.
- **Anti-spiral safeguards.** The agentic loop is capped at 4 tool
  iterations; on cap, a final tools-disabled call forces the model to
  write a real answer using whatever it has gathered. The system
  prompt explicitly budgets 2-3 tool calls per answer.
- **Dollar-sign KaTeX safety.** A post-processor escapes any unescaped
  `$` before a digit in rendered markdown so currency amounts never
  render as LaTeX math. The system prompt also instructs the model to
  emit `\$` directly.
- **Knowledge refresh script.** `scripts/refresh_knowledge.py` fetches
  any allowlisted authoritative URL through the same pipeline the
  runtime `fetch_url` tool uses (with `pdfplumber` for PDFs) and dumps
  a frontmatter'd stub for hand-summarization. Fails gracefully on
  bot-blocked domains (CBO, SSA) with a clear pointer to manual paste
  or live `web_search`.
- **Live smoke test.** `scripts/smoke_ask_assistant.py` runs three
  short questions through the real Anthropic API to verify the
  streaming tool-use loop, knowledge search, and citation discipline.
  ≈$0.04 per full run; supports `--only N` for single-scenario runs.
- 105 new tests across `tests/test_fiscal_assistant.py`,
  `tests/test_ask_api.py`, `tests/test_assistant_rate_limit.py`,
  `tests/test_assistant_admin.py`, `tests/test_assistant_share.py`,
  `tests/test_assistant_health.py`. All use mocked Anthropic clients;
  no API credit spent in CI.

### Operational readiness and CI telemetry

- `/health`, `/benchmarks`, `/summary`, and validation artifacts now expose
  flattened `issues` arrays with a shared status-issue shape for monitoring
  clients: `surface`, `severity`, `name`, `message`, and `details`.
- The Results Summary tab now renders a validation-evidence card beside each
  headline score, including calibrated category, benchmark count, observed
  error range, holdout status, and known caveats.
- CI smoke coverage now includes `scripts/check_streamlit_boot.py`, which
  starts the Streamlit app locally and verifies the calculator and
  classroom-mode routes serve the app shell.
- The FRED data layer now has a tracked bundled seed path between runtime cache
  and hardcoded fallback, so offline CI/deployments can build the baseline from
  a deterministic GDP seed instead of the IRS-ratio proxy.
- Bundled FRED seed data now carries a 120-day freshness contract, surfaces its
  age/max-age in health payloads, and degrades readiness when the seed ages out.
- Added `scripts/refresh_fred_seed.py` and a monthly `fred-seed-refresh`
  workflow so the tracked FRED seed is refreshed from live FRED with provenance
  and reviewed through a pull request before the 120-day window expires.
- The feasibility audit now emits a structured `model_pilot_assessment` with
  blockers/warnings and supports `--strict`, so implausible multi-model gaps
  stop the feasibility phase before UI expansion. The multi-model tab reuses
  the same assessment to flag pilot-quality blockers in the UI.
- PWBM-OLG is now excluded from the default multi-model pilot and kept behind
  `--include-experimental-pwbm` until its adapter clears the feasibility sanity
  bounds; the user-facing pilot defaults to the comparable CBO/TPC paths.
- The TPC microsim pilot now maps income-tax rate changes with thresholds to a
  taxable-income-above-threshold adjustment instead of collapsing every rate
  policy into a generic top-rate change.
- The model-pilot feasibility audit now uses the IRS-backed CBO-style scorer by
  default, with `--use-synthetic-cbo` retained for isolated diagnostics.
- The default TPC microsim pilot now applies SOI top-tail augmentation with
  metadata, reducing high-income threshold undercoverage while keeping
  `--no-top-tail-augmentation` available for CPS-only diagnostics.
- The experimental PWBM-OLG pilot now nets reform transitions against a
  no-reform OLG reference path and returns zero macro feedback when a policy
  does not map to an OLG parameter override, avoiding baseline transition drift
  being counted as a policy effect.
- The CPS microsim builder now emits explicit `investment_income` as interest,
  dividends, and capital gains, and the tracked `tax_microdata_2024.csv`
  artifact has been regenerated with that column.
- The release-readiness CLI now distinguishes real release blockers from
  expected offline data-environment warnings. `scripts/check_readiness.py
  --strict` still fails `not_ready` and non-environmental warnings, but it no
  longer blocks isolated CI runners solely because live FRED data or a warm
  FRED cache is unavailable.
- Validation and public-health scripts avoid `datetime.UTC` so the supported
  Python `3.10`-`3.13` matrix imports them consistently.

### API hardening

- Added opt-in API key auth via `X-API-Key` header, configured through the
  `FISCAL_API_KEYS` env var. Auth stays off by default so local launches and
  existing callers continue to work unchanged.
- Added a sliding-window rate limiter
  (`FISCAL_API_RATE_LIMIT_PER_MINUTE`, default 60; burst 20) keyed on API
  key label when auth is on and client IP otherwise. Returns `429` with
  `Retry-After: 60`.
- Every request now emits one structured JSON log line via the
  `fiscal_model.api_security` logger (path, method, status, duration,
  caller, key label).
- Wiring is in `fiscal_model/api_security.py`; tests in
  `tests/test_api_security.py`.

### Validation transparency

- New `docs/VALIDATION_NOTES.md` provides root-cause analysis for the three
  biggest validation outliers (SS donut hole 12.2%, Biden CTC 8.9%, Biden
  estate reform 10.1%). Each case documents the mechanical, data, and
  methodological causes with quantified fix paths.

### Test coverage

- New `tests/test_input_validation.py` (38 cases) covering invalid and
  malformed inputs distinct from the existing edge-case suite: structural
  invariants, parameter bounds, non-finite inputs, extreme-but-valid
  numerical robustness, and phase-in/sunset exact-boundary behavior.

### Dollar-escape + scoring unit fixes (April 2026)

- Converted remaining non-raw `"""..."""` tables in `methodology.py` to
  raw strings so bare `\$` no longer triggers `SyntaxWarning` under
  Python 3.12+.
- Removed the `/1e9` and sign-flip heuristic in the bill tracker's
  auto-scorer. `final_deficit_effect` is already in billions with the
  positive=deficit-increase convention used by `cbo_manual_scores.json`,
  so the heuristic was producing inconsistent signs and magnitudes.
- Added `_escape_dollars` helper in `classroom_app.py` to prevent
  Streamlit from rendering dollar amounts as LaTeX in assignment and
  exercise text.

## April 2026 — UI reorganization

### Progressive tab disclosure

The UI now separates primary analysis from advanced features. Previously a
single `st.tabs()` row of five tabs (one of which was a container with a
radio sub-selector) carried everything.

**Primary tabs** (always visible):

- 📊 Results Summary
- 👥 Distribution
- 🌍 Dynamic Scoring
- 📋 Detailed Results

**Advanced** (collapsible `st.expander("🔬 Advanced Analysis")`):

- 📈 Long-Run Growth
- ⚖️ Policy Comparison
- 📦 Package Builder
- 📖 Methodology

All eight tabs are mapped to a unified dictionary for
`render_result_tabs()`; there was no API change for callers.

### Export enhancements

The bottom of Results Summary now offers three export paths:

| Option          | Format           | Use case                                |
|-----------------|------------------|-----------------------------------------|
| CSV download    | Spreadsheet      | Excel, further processing               |
| Text download   | Plain text file  | Email, sharing as attachment            |
| Copy-paste block| Code block       | Direct paste into Word, Google Docs     |

The text summary includes the policy name, deficit impact, year-by-year
breakdown, assumptions, and data sources.

### Uncertainty bands + CBO comparison

Sensitivity bands (default: ETI ± 0.1) are rendered alongside the central
estimate on the Results Summary tab, with an in-line comparison against
the nearest published CBO/JCT score from the validation database.
`fiscal_model/ui/tabs/results_summary.py` is the entry point for this
rendering. The validation comparator is in
`fiscal_model/validation/cbo_scores.py`.

### Backwards compatibility

100% backwards compatible — no public-API change. Tests in
`tests/test_ui_controller_smoke.py` exercise both the old and new tab
paths.

## Earlier milestones

- **State-level modeling**: top 10 states with SALT cap interaction,
  combined federal + state effective rates.
- **OLG model**: 30-period Auerbach-Kotlikoff-style generational
  accounting for Social Security and Medicare reform
  (`fiscal_model/models/olg/`).
- **Classroom mode**: 7 interactive assignments, Laffer curve explorer,
  PDF export; launched with `streamlit run classroom_app.py`.
- **Real-time bill tracker**: pulls from congress.gov, extracts
  provisions via LLM, stores in SQLite (`bill_tracker/`).
- **Tariff scoring**: 5 presets (universal 10%, China 60%, autos 25%,
  reciprocal), consumer price impact by income quintile.
- **25+ validated policies** against CBO/JCT/Treasury scores; see
  `docs/VALIDATION.md` for the full matrix and
  `docs/VALIDATION_NOTES.md` for diagnostics on outliers.
