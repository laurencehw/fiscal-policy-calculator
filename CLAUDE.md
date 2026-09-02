# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fiscal Policy Impact Calculator — a web app that estimates budgetary and economic effects of tax and spending proposals. Live at: https://fiscal-policy-calculator.streamlit.app

See `planning/ROADMAP.md` for the full roadmap and next priorities.

## Model maturity (read before changing or describing features)

The app is a **validated scoring core with experimental interfaces**, not a flat feature set. Hold each tier to the right bar, and describe it to users accordingly (see README "Model maturity"):

- **🟢 Core — validated:** revenue scoring (static + behavioral), distributional analysis (return-level CPS microsim, the default since 2026-06), dynamic scoring (FRB/US-calibrated `EconomicModel`). Benchmarked vs published scores from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation and CRFB where no agency scored the policy — `published_entries` counts all of them, so never describe it as "CBO/JCT/Treasury". Report honest accuracy: fitted calibrated reference models (2.2% revenue over 30 benchmarks, or 4.2% over 31 with the one revised-target row held in place; 7 published distributional tables span 0.0-5.9pp, and two of them are circular) **vs** unfitted module reconstructions (72.1% over 24) **vs** genuine out-of-sample predictions (25 pre-registered cases, 31.3% mean, 18/25 within 25%). Never collapse those tiers into one "validated within X%" claim.
- **🟡 Specialized — calibrated, narrower:** the 14 policy-area modules, state modeling (top-10), OLG. Tuned to reproduce published scores → transparent reconstructions, not independent confirmation.
- **🔵 Exploratory — interfaces/pipelines:** Ask assistant, bill tracker, classroom, multi-model pilots, admin/share. Held to a UX/safety bar, **not an accuracy bar**; bill-tracker LLM extraction is demo-grade.

Guidance: invest in the green core's correctness first; keep the blue tier guard-railed (cost caps, citation discipline) but don't present it as validated estimation.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run app locally
streamlit run app.py

# Run app locally (classroom mode)
streamlit run classroom_app.py

# Run unit tests (1700+ tests)
pytest tests/ -v

# Run specific test file
pytest tests/test_distribution.py -v
pytest tests/test_macro_adapter.py -v

# Run validation against CBO scores
python -c "from fiscal_model.validation import compare_to_cbo; compare_to_cbo()"

# Run distributional validation
python fiscal_model/validation/distributional_validation.py

# Unified validation dashboard (health + calibration + CBO/JCT benchmarks)
python scripts/run_validation_dashboard.py
python scripts/run_validation_dashboard.py --augment-top-tail --filter-to-filers

# Generate API documentation
python scripts/generate_docs.py

# Quick test a policy
python -c "from fiscal_model import FiscalPolicyScorer, TaxPolicy, PolicyType; s = FiscalPolicyScorer(); print(s.score_policy(TaxPolicy(name='test', description='+1pp at 400K', policy_type=PolicyType.INCOME_TAX, rate_change=0.01, affected_income_threshold=400000)))"
```

## Architecture

### Core Scoring Flow

```
Policy Definition → Static Scoring → Behavioral Offset (ETI) → Dynamic Feedback (optional)
                         ↓                    ↓                        ↓
                   ΔRate × Base         -ETI × 0.5 × static      GDP feedback × 0.25
```

### Pages and the URL contract

The app is a **verb-first multipage app** (`st.navigation(position="top")`), not
the old five-tab layout. `app.py` is the router and the Streamlit Cloud entry
point; each surface renders itself from `app_pages/`. There is no global
sidebar — Model settings and Data Status live in the shared chrome's ⚙ and pill
popovers. Below 640px Streamlit moves the top nav into a collapsed sidebar on
its own; that is the intended mobile fallback.

| Page | URL | Notes |
|------|-----|-------|
| **Ask** (default) | `/` , `/?q=<question>` | landing page; `/ask` is shimmed to `/` |
| **Build** | `/build?values=<archetype>` · `?vector=<b64>` · `?policies=<ids>` | opens on "Start from your values"; `?policies=` opens the checklist |
| **Tailor** | `/tailor?type=&rate=&who=&phase=&duration=&dynamic=&run=1` | `who` is an enum (`top400k`) or a bare amount |
| **Explore** | `/explore?preset=<stable id>&dynamic=&run=1` | |
| **More ▾** | `/tracker`, `/methodology`, `/classroom` | |

Emitted share links also carry `baseline=<vintage>&spec=<policy hash>&mode=`.
Every legacy URL (`?analysis=preset&preset=<emoji label>&run=1`, `/ask`,
`/studio`) is rewritten by `app._apply_legacy_url_shim` **before**
`st.navigation`, so no "page not found" flashes. `?mode=classroom` is unchanged.

### Module Structure

| Module | Purpose |
|--------|---------|
| `app.py` | Router — `st.set_page_config`, legacy-URL shim, `st.Page`/`st.navigation(position="top")`. Streamlit Cloud entry point |
| `app_pages/` | One module per page: `ask.py`, `build.py`, `tailor.py`, `explore.py`, `tracker.py`, `methodology.py`, `classroom.py`, `about.py`, `admin.py` |
| `components/chrome.py` | Shared page chrome — brand line, data-status pill popover, ⚙ settings popover, degraded-data banner, dark-mode CSS overlay, one footer per page |
| `components/cards.py` | Ask home's doorway cards and worked-example prefill cards |
| `components/results.py` | `ScoredResult` (the single result object) + `render_score_surface` / `render_results`, spec-hash invalidation, anchor scroll |
| `fiscal_model/preset_ids.py` | Stable preset ids, `exclusive_groups`, `subsumes`, values tags — the identity layer share links and Build rely on |
| `fiscal_model/composer/` | `values_schema.py` (`ValuesVector`, protected rules), `archetypes.yaml` (5 archetypes), `composer.py` (deterministic selector), `translate.py` (free text → vector, temperature=0) |
| `fiscal_model/ui/tabs/deficit_target.py` | The live Build page body (checklist, scoreboard, waterfall, exports). Package Studio was folded into Build's values panel; `ui/tabs/package_builder.py` is dead code |
| `fiscal_model/ui/share_links.py` | URL contract both ways — encode/decode for Explore presets, Tailor params, Build values, plus the legacy rewrite |
| `fiscal_model/scoring.py` | `FiscalPolicyScorer` — main scoring orchestrator |
| `fiscal_model/policies.py` | Policy classes: `TaxPolicy`, `CapitalGainsPolicy`, `SpendingPolicy`, `TransferPolicy` |
| `fiscal_model/baseline.py` | `CBOBaseline` — 10-year budget projections |
| `fiscal_model/economics.py` | `EconomicModel` — dynamic effects, multipliers, GDP feedback |
| `fiscal_model/data/irs_soi.py` | `IRSSOIData` — loads IRS Statistics of Income CSVs |
| `fiscal_model/data/capital_gains.py` | Capital gains baseline + realizations elasticity model |
| `fiscal_model/data/fred_data.py` | FRED API wrapper with caching |
| `fiscal_model/tcja.py` | `TCJAExtensionPolicy` — TCJA extension scoring with component breakdown |
| `fiscal_model/corporate.py` | `CorporateTaxPolicy` — Corporate rate changes, GILTI/FDII, pass-through |
| `fiscal_model/credits.py` | `TaxCreditPolicy` — CTC, EITC with phase-in/out |
| `fiscal_model/estate.py` | `EstateTaxPolicy` — Estate tax with exemption modeling |
| `fiscal_model/payroll.py` | `PayrollTaxPolicy` — SS cap, donut hole, NIIT expansion |
| `fiscal_model/amt.py` | `AMTPolicy` — Individual AMT, Corporate AMT (CAMT) |
| `fiscal_model/ptc.py` | `PremiumTaxCreditPolicy` — ACA premium credits |
| `fiscal_model/tax_expenditures.py` | `TaxExpenditurePolicy` — SALT, mortgage, employer health |
| `fiscal_model/distribution.py` | `DistributionalEngine` — TPC/JCT-style tables by income group |
| `fiscal_model/models/macro_adapter.py` | `MacroModelAdapter` — FRB/US and simple multiplier for dynamic scoring |
| `fiscal_model/validation/cbo_scores.py` | Database of known CBO/JCT scores for validation |
| `fiscal_model/validation/compare.py` | Comparison framework (model vs official) |
| `fiscal_model/validation/distributional_validation.py` | TPC distributional benchmark validation |
| `fiscal_model/assistant/` | Ask assistant — `FiscalAssistant` orchestrator, `AssistantTools` dispatcher, BM25 knowledge search, citation post-processor, cost meter, sqlite rate limiter, admin queries, share-link encoding |
| `fiscal_model/assistant/knowledge/` | 19 curated Markdown snapshots (CBO baseline, SSA Trustees, TCJA, capital gains, international tax, retirement, fiscal multipliers, ETI literature, state/local, IRA, etc.); frontmatter carries the canonical source URL for citations |
| `fiscal_model/ui/tabs/ask_assistant.py` | Streamlit chat UI — streaming, dollar-sign safety, follow-up chips, share button, rate-limit and unavailable-key UX |
| `fiscal_model/ui/tabs/assistant_admin.py` | Token-gated admin dashboard (visible only when URL `?admin=<token>` matches `ASSISTANT_ADMIN_TOKEN`) |

### Data Files

- `fiscal_model/data_files/irs_soi/` — IRS SOI tables (Table 1.1 2021-2022)
- `fiscal_model/data_files/capital_gains/` — IRS SOI preliminary XLS + documented rate proxies

### Key Classes

```python
# Policy definition (model-agnostic) — `description` and `policy_type` are required
TaxPolicy(
    name, description, policy_type,  # PolicyType.INCOME_TAX, etc.
    rate_change, affected_income_threshold,
    taxable_income_elasticity=0.25, duration_years=10
)

CapitalGainsPolicy(
    name, description, policy_type,  # PolicyType.CAPITAL_GAINS_TAX
    rate_change, affected_income_threshold,
    baseline_realizations_billions, baseline_capital_gains_rate,
    # Time-varying elasticity (CBO/JCT methodology)
    short_run_elasticity=0.8,  # Years 1-3: timing effects
    long_run_elasticity=0.4,   # Years 4+: permanent response
    transition_years=3,
    # Step-up basis at death (Biden proposal)
    step_up_at_death=True,           # Current law
    eliminate_step_up=False,         # Set True to model step-up elimination
    step_up_exemption=1_000_000,     # Biden: $1M per person
    gains_at_death_billions=54.0,    # CBO estimate
    step_up_lock_in_multiplier=2.0,  # module default; 5.3 is a per-scenario calibration (scenarios.py pwbm_39_with_stepup) that reproduces PWBM's revenue loss
)

# TCJA Extension (calibrated to CBO $4.6T)
from fiscal_model import create_tcja_extension
policy = create_tcja_extension(extend_all=True, keep_salt_cap=True)  # Full extension
policy = create_tcja_extension(extend_all=True, keep_salt_cap=False)  # No SALT cap (+$1.9T)
policy = create_tcja_extension(extend_all=False, extend_rate_cuts=True)  # Rates only (~$3.2T)

# Corporate Tax (calibrated to CBO -$1.35T for 21%→28%)
from fiscal_model import create_biden_corporate_rate_only, CorporateTaxPolicy
policy = create_biden_corporate_rate_only()  # Biden 21%→28% (-$1.35T)
policy = CorporateTaxPolicy(
    name="Custom Corporate",
    rate_change=0.07,  # +7pp
    corporate_elasticity=0.25,
    include_passthrough_effects=True,
    gilti_rate_change=0.105,  # Increase GILTI
    eliminate_fdii=True,  # Repeal FDII
)

# Scoring
scorer = FiscalPolicyScorer(baseline=None, use_real_data=True)
result = scorer.score_policy(policy, dynamic=False)
# result.static_revenue_effect, result.behavioral_offset, result.final_deficit_effect

# Auto-population from IRS
irs = IRSSOIData()
bracket_info = irs.get_filers_by_bracket(year=2022, threshold=400000)
# Returns: {'num_filers': 1.8M, 'avg_taxable_income': 1.2M, ...}

# Distributional analysis (Phase 3)
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
engine = DistributionalEngine()
result = engine.analyze_policy(policy, group_type=IncomeGroupType.QUINTILE)
# result.results: list of DistributionalResult with avg tax change, share of total
print(result.to_dataframe())

# Macro adapter for dynamic scoring
from fiscal_model.models import FRBUSAdapterLite, MacroScenario
import numpy as np

# FRB/US-calibrated adapter (recommended - no pyfrbus needed)
adapter = FRBUSAdapterLite()  # Multipliers: spending=1.4, tax=-0.7
scenario = MacroScenario(
    name="TCJA Extension",
    description="$460B/yr tax cut",
    receipts_change=np.array([-460.0] * 10),  # Revenue loss
)
result = adapter.run(scenario)
print(f"GDP effect: {result.cumulative_gdp_effect:.2f}%-years")
print(f"Revenue feedback: ${result.cumulative_revenue_feedback:.1f}B")

# Full FRB/US adapter (requires pyfrbus + symengine)
# from fiscal_model.models import FRBUSAdapter
# frbus = FRBUSAdapter()  # Uses Economy_Forecasts model files
# result = frbus.run(scenario)
```

## Methodology Reference

Standard parameters (see `docs/METHODOLOGY.md`):
- **ETI**: 0.25 (Saez et al. 2012)
- **Capital gains elasticity**: time-varying (short-run 0.8, long-run 0.4)
- **Spending multiplier**: 1.0 normal, 1.5-2.0 recession
- **Marginal revenue rate** (dynamic feedback): 0.25
- **Labor/capital shares**: 0.65/0.35

FRB/US-calibrated multipliers (FRBUSAdapterLite):
- **Spending multiplier**: 1.4 (year 1, with 0.75 decay)
- **Tax multiplier**: -0.7 (year 1)
- **Crowding out**: 15% of cumulative deficit
- **Monetary offset / return to potential**: 0.65 annual retention of the
  demand effect — demand-side GDP effects fade over ~5-7 years rather than
  persisting for the full decade; there is **no supply-side channel**, and
  the dynamic tab nets debt-service costs against revenue feedback

Static revenue formula:
```
ΔRevenue = ΔRate × (Avg_Income - Threshold) × Num_Taxpayers
```

Behavioral offset (income tax):
```
Offset = ETI × 0.5 × Static_Effect    # signed; same sign as static
Final  = Static + Offset_signed_against_deficit
       = Static × (1 − ETI × 0.5)     # erodes magnitude in both directions
```

Capital gains behavioral offset (time-varying):
```
R₁ = R₀ × ((1-τ₁)/(1-τ₀))^ε(t)
where ε(t) transitions from short_run to long_run over transition_years
```

## Ask Assistant

The Ask tab and `/ask` + `/ask/stream` endpoints expose a citation-grounded
public-finance assistant. Architecture:

```
User question
    ↓
FiscalAssistant.stream_response()    # claude-sonnet-4-6, streaming, tool loop
    ↓
AssistantTools.dispatch()            # 9 tools, allowlist-enforced
    ├── App-internal: get_app_scoring_context, get_cbo_baseline,
    │   get_validation_scorecard, list_presets, get_preset,
    │   score_hypothetical_policy
    ├── Knowledge: search_knowledge   # BM25 over assistant/knowledge/*.md
    └── Live: query_fred, web_search (domain-restricted),
        fetch_url (allowlisted + pdfplumber fallback)
    ↓
citations.annotate_unsupported()     # strips [^N] markers without provenance
    ↓
RateLimiter.record_turn()            # writes assistant_events sqlite row
```

Hard rules:

- Daily cost cap ($5/day default) is checked **before** each request via
  `RateLimiter.check()`; over-cap requests get a friendly 429-equivalent.
- `MAX_TOOL_ITERATIONS = 4`. On cap, the loop fires one final
  tools-disabled call to force a real answer (no more "model called
  13 tools and never wrote anything" failure mode).
- `DEFAULT_MAX_TOKENS = 800`. Most public-finance answers run 200-400 tokens;
  the cap prevents accidental long-form rambling.
- Citations are enforced *structurally*. The model emits `[^N]` markers;
  the post-processor strips any marker not backed by either a tool call
  (any internal tool counts) or a fetched web URL.
- `st.secrets["ANTHROPIC_API_KEY"]` is promoted to `os.environ` on first
  render — Streamlit Cloud deployments need no extra wiring.
- All env-var configuration lives in `fiscal_model/assistant/rate_limit.py`:
  `ASSISTANT_DAILY_COST_CAP_USD`, `ASSISTANT_SESSION_MESSAGE_CAP`,
  `ASSISTANT_COOLDOWN_SECONDS`, `ASSISTANT_DISABLED`, `ASSISTANT_USAGE_DB`,
  plus `ASSISTANT_ADMIN_TOKEN`, `ASSISTANT_MODEL`, `ASSISTANT_SHOW_TOOLS`.
- Live smoke test: `python scripts/smoke_ask_assistant.py` (~$0.04 per run).

```python
# Programmatic usage (e.g., from a script or notebook)
from fiscal_model.assistant import FiscalAssistant
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.policies import PolicyType, TaxPolicy, SpendingPolicy

scorer = FiscalPolicyScorer()
assistant = FiscalAssistant(
    scorer=scorer,
    baseline=scorer.baseline,
    cbo_score_map=CBO_SCORE_MAP,
    presets=PRESET_POLICIES,
    knowledge_dir="fiscal_model/assistant/knowledge",
    policy_types=PolicyType,
    tax_policy_cls=TaxPolicy,
    spending_policy_cls=SpendingPolicy,
)
chunks = list(assistant.stream_response(
    "What's the current CBO 10-year deficit projection?",
    history=[],
))
print("".join(chunks))
print("Tools used:", [p["tool"] for p in assistant.last_provenance])
print("Cost:", assistant.last_usage.cost_usd)
```

## Current Development Priorities

All core features, all four horizon features, the distributional-validation cycle, and the Ask assistant feature are complete (May 2026). **1700+ tests passing across the model + Ask stack.**

Completed:
1. ✅ 25+ CBO/JCT-validated policies, distributional analysis, dynamic scoring
2. ✅ Tariff scoring, microsimulation engine, FastAPI endpoints
3. ✅ OLG model (30-period Auerbach-Kotlikoff, SS/Medicare reform)
4. ✅ Classroom Mode (7 assignments, PDF export, 80 tests)
5. ✅ State-Level Modeling (top 10 states, SALT interaction)
6. ✅ Real-Time Bill Tracker (congress.gov pipeline, LLM extraction, SQLite)
7. ✅ 7 CBO/JCT distributional benchmarks wired end-to-end (see `docs/VALIDATION_NOTES.md`)
8. ✅ CPS ASEC microsim scaffold with SOI calibration, top-tail Pareto augmentation, and filing-threshold filter
9. ✅ Multi-model pilot platform (CBO-style, TPC-microsim, PWBM-OLG) wired into the Scoring Models tab
10. ✅ API hardening (X-API-Key auth, rate limiting, structured logging)
11. ✅ `GET /summary`, `GET /benchmarks` API endpoints + `scripts/run_validation_dashboard.py` CI gate
12. ✅ **Ask assistant** — citation-grounded Q&A, 19 curated authoritative snapshots, streaming tool-use loop, `/ask` + `/ask/stream` (SSE) endpoints, token-gated admin dashboard, share-link encoding, hard daily cost cap, /health + /readiness integration. 105 tests across the assistant stack.

**Wave 1 of `planning/MODELING_IMPROVEMENT.md` is done** (2026-09-01/02, PRs #83, #85, #86, #87, #88): L2 budget-authority→outlay spend-out, L5 AMT live exemption branch + published year-indexed path, L7 pharma federal incidence, plus IIJA's superseding authorization-path row and spend-out for the app's spending presets.

**The AMT/insulin target provenance lane is done for two of its three targets** (PR #90, 2026-09-02): `extend_tcja_amt` moved $450B → **$1,357.1B** and `universal_insulin_cap` −$15B → **+$11.4B**, both through the new Tier-2 supersede ledger `fiscal_model/validation/target_revisions.py`, with no constant retuned. `repeal_individual_amt` **stays at $450B**: no published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a baseline projection *and* the derived path's own input, so adopting it would manufacture a 0% row out of leakage. Closing it needs either a published score or an owner decision to re-register `holdout.py`'s locked protocol — a gate no lane may edit. `AMT_APP_MODE` and `AMT_SCORECARD_MODE` both stay `reported`: across the three AMT benchmarks reported means **22.3%** against derived's **54.2%**, which is Decision 1's own rule, so nothing a user sees changed.

**Wave 2 of `planning/MODELING_IMPROVEMENT.md` is done** (2026-09-02, PRs #93, #94, #95): L4 estate (a SOI-fitted Pareto size distribution of the estate tax base in place of a two-point blend that was *exactly invariant* in the exemption), L6 tax expenditures (declared cap units plus SOI-transcribed benefit distributions, so a cap is applied to the quantity it caps), L1 capital gains (SOI Table 3.5 bracket base, the semi-log tax-rate elasticity CRS R48562 defines, a derived lock-in wedge, and a decedent-wealth gains-at-death stock — the 5.3× lock-in multiplier and all three per-case elasticity tuples deleted). Tier 1 fell **34.4% → 31.3%**, LOO **58.7% → 32.3%**, and the three capital-gains scenarios left the fitted tier because nothing is fitted to them any more. Every module keeps `reported` as the app default under Decision 1 (derived did not beat fitted on the carried targets), so no shipped preset moved.

Next: **Wave 3** — **L3** credits/microsim (raw CPS ASEC fetched by script at build time per Decision 4; the three tautological credit benchmarks move to documented-exclusion status per Decision 5), **L8** tariffs (gross → net, landing with its UI note in the same PR per Decision 6), **L9** international. Carry-overs: L7's Part D channels, L5's phase-out thresholds, L1's death-channel behavioural response, promoting CBO Option 56 once the excess share is year-indexed, and CBO's account-level spendout rates (pubs 61913, 62256) as an external cross-check on L2, still blocked by cbo.gov 403s. Open owner decisions are listed in `planning/MODELING_IMPROVEMENT.md` §6. See `planning/NEXT_STEPS.md`.

## Target Validation

**Report two tiers separately — do NOT collapse them into a single "validated within 15%" claim.** Run `python scripts/cold_holdout.py` for live numbers.

**Tier 1 — out-of-sample predictions** (uncalibrated, bottom-up from SOI filer counts, module revenue identities and source-stated spending levels; the genuine test). **25 pre-registered cases, mean abs error 31.3% (median 14.1%), 13/25 within 15%, 18/25 within 25%.** Never state this as a single "validated within X%" number — the distribution has a tight core and a long tail, and each tail case has a documented structural cause: rate changes at conventional thresholds land at 2–22%; discretionary funding changes, now spent out on a fitted account-class profile, land at 0–11% for the five CBO Options rows and 10–18% for the three enacted-law components; two rate cases whose source states a filing-status-specific boundary the generic path cannot express land at 18% and 45%; **gains at death now lands at 8.4%**, having been 84.4% before Wave 2 replaced a flat $54B/yr constant with decedent wealth × an unrealized-gain share by estate size; and what is left of the behavioural tail runs 45% (a 2pp preferential-rate change), 47% (corporate margins), 54–56% (payroll incidence) and **135% / 218%** for the two step-up-elimination rows, whose whole residual is that the model applies *no* behavioural response to the death channel — no spousal or charitable carve-out, no §121 residence exclusion, no tangible-personal-property exclusion, no family-business deferral — all of which Treasury's own score prices. Capital gains remains the tier's dominant error mass (4 cases, 405.6 of 781.8 units, 51.9%) even after Wave 2 took 73.8 units out of it.

**Fourteen of the 25 are the CBO *Options for Reducing the Deficit: 2025–2034* battery** (publication 60557, Dec 2024) — **14 runnable alternatives across 11 of its 76 options**; the other **65 options** carry a one-line exclusion reason in `fiscal_model/validation/cbo_options.py`. Three exclusions are **leakage**, not missing machinery: Options 53, 56 and 62 would be scored by module constants calibrated to reproduce those same reforms. Spending options qualify only if CBO's *own* budget-authority path is a level `SpendingPolicy` can express (`is_level_budget_authority_path`, 25% tolerance). The battery is scored on `BaselineVintage.CBO_FEB_2024` via `validation/core.build_scorer_for_vintage()` — which changes none of the 14 scores, because every uncalibrated shape is bottom-up and none reads a level off the baseline.

**Three of the 25 are Phase D enacted-law component replications**: the Social Security Fairness Act's WEP/GPO repeal (+$196B official vs +$215B, 10%), the Fiscal Responsibility Act's discretionary caps (−$1,332B vs −$1,170B, 12%) and IIJA's discretionary component (+$415B vs +$340B, 18%). They are *components*, never bill totals — the headline score of an enacted law is a net of provisions no single shape can construct — and one pre-registered rule sets every annual level (`PHASE_D_SPENDING_LEVEL_RULE`). **The spend-out model now exists** (Wave 1 lane L2, PR #85): outlays are `Σ_k s_k · BA_{t−k}` on an account-class profile fitted by NNLS on the 14 CBO donor options the battery does not score, so the five CBO Options spending rows now land at 0–11%. IIJA is no longer a spend-out case: its shape input was superseded under the manifest's own rule (a **new row**, never an edit) to CBO's own authorization schedule — `iija_2021_discretionary.v1` stays on the record at 356% before spend-out and 290.2% after, `.v2` scores +$340.0B against the *unchanged* +$415.4B target, 18.2%. What is left is a **window** miss, not a shape or spend-out miss: the path outlays $433.2B in total (4.3% high) but $92.6B of that falls in FY2022-2024, before the model's FY2025-2034 window opens, and the repository has no 2021 vintage to score the bill on its own window. FRA's 12% is *worse* than the 6% it showed before spend-out, and that was pre-registered: the old 6% was two errors cancelling, and a correct spend-out removes one of them. IRA 2022, Tax Relief for Families 2024 and NDAA FY2025 are recorded out of scope with CBO's component figures (leakage; a $0.4B net of $100B-scale components; a $178M scored quantity below model resolution).

Ordinary-bracket rate changes (JCT 1pp, Biden $400K, CBO Option 45) score on the ordinary-income base; AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren AGI>$2M, Medicare surcharge, CBO Option 46) score on the full taxable-income base — classified from how each source describes its base, never fitted (`cold_holdout.py --ordinary-base` shows the correction *worsens* the AGI-inclusive cases, the tell). The Biden $400K+ Generic path scores **−$217B vs −$252B official (~14%)** — earlier docs that cited "~−$250B / ~1%" were showing a hand-tuned figure, not the prediction, and the sign of the residual flipped in Wave 2 (it over-predicted at −$284B / 12.9% until `preferential_income_share` started reading the SOI Table 3.5 bracket base; the FY2025 Green Book's own row is −$245.9B, so part of the residual is target error). Capital-gains cases use ONE frozen elasticity set — since Wave 2 the `CapitalGainsPolicy` dataclass defaults, which are Dowd–McClelland–Muthitacharoen (2015) persistent 0.72 / transitory 1.20 at a 22% reference rate, applied semi-logarithmically as `R₁ = R₀·exp(−b·Δτ)` with `b = ε/τ_ref` because CRS R48562 defines the realization elasticity on the **tax** rate, not the net-of-tax rate. The old 0.8/0.4 net-of-tax pair is gone, and so are `scenarios.py`'s three per-case tuples and the 5.3× lock-in multiplier. Two Tier 1 rows changed in the Phase E provenance pass: `top_rate_45` is **retired** (its −$420B is in no TPC, CBO or JCT publication and the figure is gone from `CBO_SCORE_MAP` too), and `biden_capital_gains_39` is **re-sourced** to the FY2025 Green Book's actual combined row (−$288.6B) with its shape corrected to that document's definition — $5M per-donor exclusion, taxable-income threshold — which moved its error 79% → 142%. Every case has a row in `fiscal_model/validation/preregistered.py`, entered in a commit *before* the commit that first scores it; a target that changes gets a **new row** with `superseded_by`, and one that cannot be sourced gets `retired=True` with the search recorded; the tier is CI-gated (`cold_holdout.py --max-mean-error 40 --min-within-25pct 17`, re-derived from the post-Wave-2 battery by the workflow's own rule) and Generic entries are no longer exempt from strict readiness. See [[fpc-review-roadmap]] and `planning/VALIDATION_EXPANSION.md`.

**Tier 2 — calibrated reference models** (parameters tuned to reproduce the official decomposition; low error expected by construction). The calibrated tier is **54 benchmarks** and splits in two: **30 fitted** references at **2.2% mean** (30/30 within 15%, worst row `tcja_no_salt_cap` at 13.9%), and **24 unfitted module reconstructions** — the Phase E international/trade/pharma/enforcement/climate presets, the Phase D P.L. 119-21 JCT line items, the one row whose target the revision ledger moved, and the three capital-gains scenarios Wave 2 unfitted, all scored against published figures no module constant is fit to — at **72.1% mean / 40.0% median** (itself four populations: **12 sectoral presets at 104.8%**, **8 P.L. 119-21 line items at 35.8%**, **3 capital-gains scenarios at 39.6%** and **TCJA AMT relief at 66.8%**, never to be quoted as one number). Never quote one for the other — and never quote the fitted 30 without saying which rows left it, because **two different mechanisms move rows out and both are live**. `ScorecardSummary.revised_target_entries` is **2**: a constant fitted to a superseded figure is not fitted to its replacement, so a revised row reports in the unfitted-reconstruction tier, where a miss is a finding rather than a regression. Held in place instead, the fitted tier reads **31 at 4.2%, 30/31 within 15%**. Separately, **Wave 2's L1 lane took the fitted tier 33 → 30**: deleting `validation/scenarios.py`'s per-case behavioural tuples removed the only constants ever fitted to `cbo_2pp_all_brackets`, `pwbm_39_with_stepup` and `pwbm_39_no_stepup`, so `calibrated_to_target` is now `False` for all three and the runner says so. The fitted mean *fell* 2.8% → 2.2% while nothing regressed, because those three rows were what the tier had been carrying; left in place they would have raised it to 6.2%. That is **composition, not accuracy** — read the two tiers together or neither. By provenance the 54 are **19 `line_item` / 13 `line_item_differs` / 15 `secondhand` / 7 `model_estimate` / 0 `unclassified`** after the transcription and revision passes, so the honest published-target count is **47** (and **72** across both tiers, out of 79 scorecard rows). Read that before quoting any error as accuracy: **13 targets are still known to disagree with the document they cite** — FDII repeal against a Treasury row that nets to $0, the SALT-deduction repeal against CBO Option 49's −$1,621.0B, and eleven more, each listed in `docs/VALIDATION.md`; where a target is carried unmoved the published figure rides on `ScorecardEntry.official_10yr_billions_line_item`. **Two were moved** instead, through `fiscal_model/validation/target_revisions.py` — the calibrated tier's mirror of `preregistered.py`'s supersede rule: ledger entry in one commit, first scoring in the next, old figure kept as a `superseded_by` row, and `target_revision_problems()` failing if ledger and registries ever drift apart. `universal_insulin_cap` −$15B → CBO 57957's **+$11.4B**, which was the repository's only *sign* disagreement and is now zero (model +$7.0B, −39.0%); `extend_tcja_amt` $450B → CRS R48286 Table 1's **$1,357.1B**, a five-year cost that had been sitting in a ten-year column. No AMT constant was retuned to chase the new figure — which is why the fitted path scores −66.8% and the unfitted structural path −37.0% against the same corrected row. `repeal_individual_amt` keeps its unsourced $450B: no published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a baseline projection *and* `amt.py`'s own input, so adopting it would manufacture a 0% row out of the leakage `loo.py` guards against. Another 15 could not be traced to any document, including both Social Security payroll targets (OCACT publishes only percent-of-payroll, no dollars, for E2.1 and E2.5). The eight P.L. 119-21 rows (JCX-35-25, transcribed with page refs to `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`) are the first block sourced line-by-line from a single JCT table: the TCJA module reproduces CBO's $4.6T aggregate to 0.4% and JCT's own component rows to **35.8%** (scored over JCT's own FY2025-2034 window), which is the sharpest evidence that the calibrated tier is reconstruction rather than structure. Held out, the fitted modules score **32.3% mean / 19.2% median over 17 leave-one-out cases**, 8/17 within 15% (**5** more declared not cross-validatable, never folded in) — run `python scripts/run_loo.py`; report that separately from the by-construction figure, never as a replacement for it. Wave 2 moved three modules: `CapitalGains` **171.2% → 39.6%** (one frozen literature set replacing three hand-set tuples; `--donor-matrix` now prints three identical rows, because there is no donor left), `Estate` **25.8% → 10.4%** and `Expenditures` **39.4% → 28.8%**. Read the suite figure with the composition change attached: `eliminate_salt` left the derivable set when L6 made `annual_cost_no_cap = 120.0` load-bearing and `loo.py`'s untouched leakage guard saw that it is exactly the carried target over ten, so the module now cross-validates on **four** benchmarks where it used to claim five, and part of the suite improvement is a 74.9% case leaving the denominator rather than a model getting better. The LOO mean *fell* from 61.7% when the AMT extension's target moved, and that is a **target** movement rather than a model one: `extend_tcja_amt`'s held-out derivation is unchanged at **$855.3B** and its error against the corrected row is −37.0% instead of +90.1%, taking the AMT module from 100.5% to **73.9%**. No donor-matrix entry moved. Examples:

| Policy (calibrated) | Official Score | Model Score | Error |
|--------|----------------|-------------|-------|
| **TCJA Extension** | **$4,600B** | **$4,582B** | **0.4%** |
| **Corporate 21%→28%** | **-$1,347B** | **-$1,397B** | **3.7%** |
| **Biden CTC 2021** | **$1,600B** | **$1,600B** | **0.0%** |
| **Estate: Biden Reform** | **-$450B** | **-$450B** | **0.0%** |
| **SS Donut $250K** | **-$2,700B** | **-$2,700B** | **0.0%** |
| **Repeal Corporate AMT** | **$220B** | **$220B** | **0.0%** |
| **Cap Employer Health** | **-$450B** | **-$450B** | **0.1%** |

## Future Architecture

Multi-model platform with pluggable scoring engines (next major milestone):
- `models/cbo/` — CBO-style conventional + dynamic
- `models/jct/` — JCT-inspired microsimulation
- `models/tpc/` — Tax Policy Center distributional
- `models/pwbm/` — Penn Wharton OLG (foundation now in `long_run/`)
- `models/yale/` — Yale Budget Lab macro + microsim + behavioral

See `docs/ARCHITECTURE.md` for full design including Yale Budget Lab feature-parity checklist.
