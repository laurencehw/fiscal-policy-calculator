# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fiscal Policy Impact Calculator — a web app that estimates budgetary and economic effects of tax and spending proposals. Live at: https://fiscal-policy-calculator.streamlit.app

See `planning/ROADMAP.md` for the full roadmap and next priorities.

## Model maturity (read before changing or describing features)

The app is a **validated scoring core with experimental interfaces**, not a flat feature set. Hold each tier to the right bar, and describe it to users accordingly (see README "Model maturity"):

- **🟢 Core — validated:** revenue scoring (static + behavioral), distributional analysis (return-level CPS microsim, the default since 2026-06; CBO's household universe available since Wave 4), dynamic scoring (FRB/US-calibrated `EconomicModel`). Benchmarked vs published scores from CBO, JCT, Treasury and SSA, plus TPC, PWBM, the Tax Foundation, CRFB, Penn Wharton and RAND where no agency scored the policy — `published_entries` counts all of them, so never describe it as "CBO/JCT/Treasury". Report honest accuracy: fitted calibrated reference models (1.6% revenue over 23 benchmarks, or 3.0% over 28 with Wave 4's five revised rows held in place; 7 published distributional tables span 0.00-5.86pp, and two of them are circular) **vs** unfitted module reconstructions (56.6% over 31 — but **65.7% on the 26 rows the tier already held**, which is the like-for-like reading and it got *worse*) **vs** genuine out-of-sample predictions (26 pre-registered cases, 15.9% mean, 22/26 within 25%). Never collapse those tiers into one "validated within X%" claim.
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

# Run unit tests (3415 tests)
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
| **Frozen assignment link** | any `/explore` or `/tailor` URL **+** `baseline=&engine=&spec=&mode=&frozen=1` | the classroom lock (`fiscal_model/ui/frozen_links.py`): applies vintage/engine/dynamic/policy and renders those controls disabled under "🔒 Frozen for this assignment"; **refuses to score** — rather than falling back — when the URL's baseline vintage is not the one this deployment serves. `?classroom=1` on a result surface shows the control that emits one |

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
| `fiscal_model/assistant/knowledge/` | 23 curated Markdown snapshots (CBO baseline, SSA Trustees, TCJA, capital gains, international tax, retirement, fiscal multipliers, ETI literature, state/local, IRA, etc.); frontmatter carries the canonical source URL for citations |
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

All core features, all four horizon features, the distributional-validation cycle, and the Ask assistant feature are complete (May 2026). **3415 tests passing across the model + Ask stack** (1 skipped; `python -m pytest tests/ -q`).

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
12. ✅ **Ask assistant** — citation-grounded Q&A, 23 curated authoritative snapshots, streaming tool-use loop, `/ask` + `/ask/stream` (SSE) endpoints, token-gated admin dashboard, share-link encoding, hard daily cost cap, /health + /readiness integration. 105 tests across the assistant stack.

**Wave 1 of `planning/MODELING_IMPROVEMENT.md` is done** (2026-09-01/02, PRs #83, #85, #86, #87, #88): L2 budget-authority→outlay spend-out, L5 AMT live exemption branch + published year-indexed path, L7 pharma federal incidence, plus IIJA's superseding authorization-path row and spend-out for the app's spending presets.

**The AMT/insulin target provenance lane is done for two of its three targets** (PR #90, 2026-09-02): `extend_tcja_amt` moved $450B → **$1,357.1B** and `universal_insulin_cap` −$15B → **+$11.4B**, both through the new Tier-2 supersede ledger `fiscal_model/validation/target_revisions.py`, with no constant retuned. `repeal_individual_amt` **stays at $450B**: no published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a baseline projection *and* the derived path's own input, so adopting it would manufacture a 0% row out of leakage. Closing it needs either a published score or an owner decision to re-register `holdout.py`'s locked protocol — a gate no lane may edit. `AMT_APP_MODE` and `AMT_SCORECARD_MODE` both stay `reported`: across the three AMT benchmarks reported means **22.3%** against derived's **54.2%**, which is Decision 1's own rule, so nothing a user sees changed.

**Wave 2 of `planning/MODELING_IMPROVEMENT.md` is done** (2026-09-02, PRs #93, #94, #95): L4 estate (a SOI-fitted Pareto size distribution of the estate tax base in place of a two-point blend that was *exactly invariant* in the exemption), L6 tax expenditures (declared cap units plus SOI-transcribed benefit distributions, so a cap is applied to the quantity it caps), L1 capital gains (SOI Table 3.5 bracket base, the semi-log tax-rate elasticity CRS R48562 defines, a derived lock-in wedge, and a decedent-wealth gains-at-death stock — the 5.3× lock-in multiplier and all three per-case elasticity tuples deleted). Tier 1 fell **34.4% → 31.3%**, LOO **58.7% → 32.3%**, and the three capital-gains scenarios left the fitted tier because nothing is fitted to them any more. Every module keeps `reported` as the app default under Decision 1 (derived did not beat fitted on the carried targets), so no shipped preset moved.

**Wave 3 is done, and with it Waves 1-3 of the modeling plan** (2026-09-02, PRs #98, #99, #100, #101, #102). **L9** international added a jurisdiction-level base-overlap term and gave FDII repeal the same base × rate identity the rate branch already used; both moves were pre-registered as *regressions* against the carried targets and both landed to the decimal (`fdii_repeal` 15.0% → **44.65%**, the package 41.0% → **49.47%**), because the identity moves toward Treasury's own published $130.2B cost and away from a −$200B target 54% above it. **L3** credits replaced `Δcredit × units × participation` with a per-unit engine over CPS ASEC tax units, rebuilt the microdata by script (Decision 4: `scripts/fetch_cps_asec.py`, SHA-256 verified, five dependent age bands, every pre-existing column byte-identical) and took the credits LOO module 45.1% → **20.5%**. **L8** tariffs took the score gross → net and shipped its user-facing caption in the same PR (Decision 6). **PR #100** moved five targets onto their documents. Every Wave 3 module keeps `reported` as the app default under Decision 1; only the tariff presets moved, by design. Carry-overs are the single list in `planning/MODELING_IMPROVEMENT.md` §6, to be sequenced by the owner. See `planning/NEXT_STEPS.md`.

**Wave 4 is done** (2026-09-05, PRs #104, #105, #106, #107, #108, #109, #110). Six lanes plus the gate PR, each pre-registered and each with an outturn appended in `planning/lanes/`. **#108 gains at death** gave the death channel the six carve-outs a realization-at-death proposal does not tax (spousal, charitable, §121 residence, tangible personal property, a family-business deferral and the per-donor exclusion, applied *after* the others) plus a semi-log rate response at death; on that PR alone Tier 1 went **31.0% → 18.5%** and the capital-gains error mass 405.6 → 81.0 — from half the tier's mass to a sixth, and the two payroll rows are now the largest single mass. `treasury_capgains_39_plus_stepup_elim` reads **0.2%**, and the lane says plainly that this is **two errors cancelling and not a measurement of accuracy** (the mechanism removes 87.2% of that row's death channel where the pre-registered hand path said 92.8%); `biden_capital_gains_39` 134.9% → **16.7%**; `cbo_opt51_gains_at_death` **8.4% → 19.3%, worse by design and pre-registered as a regression**, because its 8.4% had been bought by taxing charitable bequests and small decedents' housing gains that no such regime reaches. **#105 Option 56** asked the excess share what year it is: **24.0% → 13.1%**, from CBO's own chained-CPI indexation rather than a fitted parameter. **#104 distributional households** gave `DistributionalEngine` CBO's household universe, registered each benchmark on the universe *its source ranks*, and made the surfaces report the universe **scored** rather than the one registered — ARP 2021 **7.77pp → 3.72pp**, the tables now span **0.00-5.86pp**, and 3 of the 7 fall back `household→tax_unit` because `TCJAExtensionPolicy` and the corporate policy have no microsim path. It also fixed a per-household dollar column that was a factor of three low and invisible to every gate, because the error metric scores shares. **#106 AMT phase-outs** transcribed statutory §55(d)(2) from eleven Revenue Procedures: no benchmark moved by design, and a threshold reform stops scoring exactly zero. **#109 pharma Part D** built three federal channels, a negotiation ladder fitted to all three published CMS cycles, and a RAND-sourced coverage base — **and the reconstruction rows got worse, which the lane reports rather than smooths** (negotiation 25.7% → 93.3%, reference pricing 646.2% → 701.0%, insulin unchanged at 39.0%), because the lane's own ladder condemned an unsourced $220B Part D gross-spending constant the reference-pricing leg also reads. Presets moved by design: negotiation −$371.5B → **−$33.5B**, reference pricing −$746.2B → **−$801.0B**, comprehensive −$573.5B → **−$150.5B**, insulin unchanged. **#107 provenance** moved 13 targets onto their documents (12 Tier 2 plus `biden_high_income_tax.v2` at −$245.9B), recorded 4 more as examined-and-left, and made the reciprocal-tariff target a range; six of the thirteen got *worse*, which is the shape a correct provenance pass has. **#110** re-derived the Tier 1 CI gate by the workflow's own rule: **40/18 → 25/20**.

**Wave 5 is done** (2026-09-05, PRs #111, #113, #114, #115, #116, #117). Three modelling lanes at the margin, each pre-registered with an outturn appended in `planning/lanes/`, plus two blue-tier PRs and the gate. **#113 payroll (`W5_payroll_margin.md`)** took the two CBO Option 61 rows **54.1% / 55.5% → 7.5% / 8.1%**, the largest single move of the wave. The plan's own scoping was wrong on both halves: CBO's option text says *"the new tax would be paid entirely by employees"*, so the "income-tax offset" §2.1 scoped does not exist, and the real defect was `$400B / 2.9% = $13,793B` — Medicare receipts divided by a rate that does not raise all of them, because the 0.9% Additional Medicare Tax sits on a far smaller base four lines above it in the same dict. The base is now CBO's own February 2024 wage path times the Trustees' covered-earnings ratio. **#114 corporate (`W5_corporate_margin.md`)** was a **pre-registered regression**, landed to the decimal: `cbo_opt64_corporate_rate_1pp` **47.1% → 62.3%**, because the derived path prices a point of rate on IRS SOI Table 11's published statutory base ($2,879.1B, TY2022) instead of a fitted $1,900B that turns out to be within 3% of the **TY2018** vintage. The residual is a disagreement between two documents the model cannot close — CBO 60557 prices a point at $135.7B over the window, Treasury's FY2025 Green Book at $192.8B, a 42% gap in which the *larger* rate change carries the *larger* per-point yield. `CORPORATE_APP_MODE` stays `reported` under Decision 1 (1.92% against derived's 9.67%), so no shipped number moved. **#116 preferential rate (`W5_preferential_margin.md`)** projected the realizations base with the accrued-gains stock it is a flow off (`R(t) = h · A(t)`, no new constant), taking CBO Option 47 **44.8% → 10.5%**; the qualified-dividends hypothesis was **refuted** by arithmetic already in the tree (SOI Table 3.5's preferential columns exceed the whole year's realized gains, so they already contain qualified dividends), and the same projection was pre-registered as a **net Tier 1 regression** on the two Green Book rows — `biden_capital_gains_39` **16.7% under → 31.4% over** and `treasury_capgains_39_plus_stepup_elim` **0.2% → 43.3% over**, the second because the 0.2% was two errors cancelling and this lane removed one of them. Four Tailor capital-gains rows moved by 26–110%, so a Decision 6 caption ships with them. **#117** re-derived the Tier 1 CI gate by the workflow's own rule: **25/20 → 20/21**, both tightening.

**Two blue-tier PRs shipped alongside Wave 5.** **#111 frozen assignment links** adds `frozen=1` beside the existing `baseline=&engine=&spec=&mode=` stamps on `/explore` and `/tailor`, pinning vintage, engine, dynamic and policy so a whole class hands in one set of numbers; a link frozen on a vintage this deployment is not serving **refuses to score** and says so rather than falling back quietly, and the instructor control that emits the link is revealed by `?classroom=1`. **#115 app default window** introduced `fiscal_model.baseline.APP_DEFAULT_START_YEAR = 2026`, so every app surface and the API's `budget_window` now read **FY2026–FY2035** while the library defaults stay at 2025 — validation targets are quoted on their own documents' windows, and moving one would be a target revision rather than a tidy-up. No scorecard number moved; two pharma presets did, by one calendar year (negotiation −$33.5B → **−$41.8B**, comprehensive −$150.5B → **−$158.9B**).

## Target Validation

**Report two tiers separately — do NOT collapse them into a single "validated within 15%" claim.** Run `python scripts/cold_holdout.py` for live numbers.

**Tier 1 — out-of-sample predictions** (uncalibrated, bottom-up from SOI filer counts, module revenue identities and source-stated spending levels; the genuine test). **26 pre-registered cases, mean abs error 15.9% (median 11.4%), 16/26 within 15%, 22/26 within 25%.** Never state this as a single "validated within X%" number — the distribution has a tight core and a long tail, and each tail case has a documented structural cause: rate changes at conventional thresholds land at 2–22%; discretionary funding changes, now spent out on a fitted account-class profile, land at 0–11% for the five CBO Options rows and 10–18% for the three enacted-law components; the tier's one **tax-expenditure cap**, CBO Option 56, lands at **13.1%** since Wave 4 (PR #105) gave the excess share CBO's own chained-CPI indexation instead of evaluating it once at `start_year` — the remaining residual is half a **base omission** (CBO caps premiums *and* FSA/HRA/HSA contributions; the repository's premium distribution has no account dimension) and about a fifth an **unsourced behavioural offset whose sign convention is the reverse of `TaxPolicy`'s**, both named rather than tuned; two rate cases whose source states a filing-status-specific boundary the generic path cannot express land at 18% and 45%. **Payroll left the tail in Wave 5** (PR #113): the two CBO Option 61 rows went 54.1% / 55.5% → **7.5% / 8.1%** once the base stopped being Medicare receipts divided by a rate that does not raise all of them, and they are now the **7th and 9th** most accurate of the 26 — the lane doc says 8th and 10th, which was true on its own branch before the other two Wave 5 lanes moved rows past them.

**The tail's composition changed in Wave 5 and its four largest rows are now:** `cbo_opt64_corporate_rate_1pp` at **62.3%** (PR #114, a pre-registered regression — the derived path prices a point of corporate rate on SOI Table 11's published statutory base, and CBO's option and Treasury's Green Book price that point 42% apart, with the *larger* rate change carrying the *larger* per-point yield); `cbo_opt46_agi_surtax_1pp_20k` at **44.7%**, unchanged and still the tier's clearest filing-status miss (a $20,000 single / $40,000 joint threshold applied as one floor to every return, at the bottom of the filing population where a single-threshold approximation is worst); and the two FY2022/FY2025 Green Book capital-gains rows, `treasury_capgains_39_plus_stepup_elim` at **43.3%** and `biden_capital_gains_39` at **31.4%**, both moved by PR #116 and both **pre-registered as regressions**. Read the Treasury row's history carefully: it was 217.5% before Wave 4's death-channel carve-outs, then **0.2%**, and the 0.2% was never accuracy — Wave 4's own lane doc recorded it as two errors cancelling, one of which was a tax-year-2023 realizations base priced unchanged in every year of the window. Wave 5 removed that error, so the row now over-predicts honestly at 43.3%; **about 17 of those 43 points are the window it is scored on** (its target is FY2022–2031 on a 2021 baseline and the record states no `effective_start_year`, so the model scores FY2025–2034), which is a manifest question rather than a modelling one. `cbo_opt51_gains_at_death` is unchanged at **19.3%**, and its own 8.4% → 19.3% move in Wave 4 was likewise registered in advance as a regression, because the 8.4% had been bought by taxing charitable bequests and small decedents' housing gains that no realization-at-death regime reaches. **Capital gains is again the tier's largest error mass**, though a much smaller one than before Wave 4: 4 cases carrying 104.5 of 412.9 units (25.3%), against 405.6 of 805.8 (50.3%) before Wave 4 and 80.9 of 468.1 (17.3%) after it. Corporate is next at 62.3 (15.1%), the two AGI-surtax rows at 60.8 (14.7%), the two ordinary-rate Option 45 rows at 40.3 (9.8%), the three enacted-law components at 40.2 (9.7%), and payroll — the largest mass after Wave 4 — is now 15.6 (3.8%). The two Green Book rows still land on the *same* side of their targets in Wave 5, but Wave 4's falsification finding stands and is unclosed: the **five-class decedent ladder** has no within-group dispersion, so moving the per-donor exclusion $1M → $5M costs the model $82.2B of death channel where it costs Treasury $33.4B.

**Fifteen of the 26 are the CBO *Options for Reducing the Deficit: 2025–2034* battery** (publication 60557, Dec 2024) — **15 runnable alternatives across 12 of its 76 options**; the other **64 options** carry a one-line exclusion reason in `fiscal_model/validation/cbo_options.py`. Two exclusions are **leakage**, not missing machinery: Options 53 and 62 would be scored by module constants calibrated to reproduce those same reforms. **Option 56 was the third until Wave 3, and a leakage exclusion is not permanent**: it was excluded because the only expressible path ran through `cap_employer_health`'s fitted annual, lane L6 (PR #94) removed that dependency, and PR #100 promoted it — a percentile cap is now the published expenditure level (`JCT_TAX_EXPENDITURES["employer_health"]`) times a share read off a premium distribution, with the validation shape pinning `mode="derived"` so the module's `reported` app default cannot reintroduce the leak. Only CBO's **third** alternative is scored (56.3 and 56.6 limit the income *and payroll* exclusion and the module has no payroll base, so they are out of scope per alternative), and the shape inputs were fixed beforehand by `OPTION_56_SHAPE_RULE`. Spending options qualify only if CBO's *own* budget-authority path is a level `SpendingPolicy` can express (`is_level_budget_authority_path`, 25% tolerance). The battery is scored on `BaselineVintage.CBO_FEB_2024` via `fiscal_model/validation/core.py`'s `build_scorer_for_vintage()` — which changes none of the 15 scores, because every uncalibrated shape is bottom-up and none reads a level off the baseline.

**Three of the 26 are Phase D enacted-law component replications**: the Social Security Fairness Act's WEP/GPO repeal (+$196B official vs +$215B, 10%), the Fiscal Responsibility Act's discretionary caps (−$1,332B vs −$1,170B, 12%) and IIJA's discretionary component (+$415B vs +$340B, 18%). They are *components*, never bill totals — the headline score of an enacted law is a net of provisions no single shape can construct — and one pre-registered rule sets every annual level (`PHASE_D_SPENDING_LEVEL_RULE`). **The spend-out model now exists** (Wave 1 lane L2, PR #85): outlays are `Σ_k s_k · BA_{t−k}` on an account-class profile fitted by NNLS on the 14 CBO donor options the battery does not score, so the five CBO Options spending rows now land at 0–11%. IIJA is no longer a spend-out case: its shape input was superseded under the manifest's own rule (a **new row**, never an edit) to CBO's own authorization schedule — `iija_2021_discretionary.v1` stays on the record at 356% before spend-out and 290.2% after, `.v2` scores +$340.0B against the *unchanged* +$415.4B target, 18.2%. What is left is a **window** miss, not a shape or spend-out miss: the path outlays $433.2B in total (4.3% high) but $92.6B of that falls in FY2022-2024, before the model's FY2025-2034 window opens, and the repository has no 2021 vintage to score the bill on its own window. FRA's 12% is *worse* than the 6% it showed before spend-out, and that was pre-registered: the old 6% was two errors cancelling, and a correct spend-out removes one of them. IRA 2022, Tax Relief for Families 2024 and NDAA FY2025 are recorded out of scope with CBO's component figures (leakage; a $0.4B net of $100B-scale components; a $178M scored quantity below model resolution).

Ordinary-bracket rate changes (JCT 1pp, Biden $400K, CBO Option 45) score on the ordinary-income base; AGI-inclusive surtaxes (TPC $1M+/$500K+, Warren AGI>$2M, Medicare surcharge, CBO Option 46) score on the full taxable-income base — classified from how each source describes its base, never fitted (`cold_holdout.py --ordinary-base` shows the correction *worsens* the AGI-inclusive cases, the tell). The Biden $400K+ Generic path scores **−$216.5B vs −$245.9B official (12.0%)** — earlier docs that cited "~−$250B / ~1%" were showing a hand-tuned figure, not the prediction, and the sign of the residual flipped in Wave 2 (it over-predicted at −$284B / 12.9% until `preferential_income_share` started reading the SOI Table 3.5 bracket base). Wave 4 (PR #107) closed the target-error half of that residual through the manifest's own supersede rule: `biden_high_income_tax.v1`'s rounded −$252B became `.v2`'s **−$245.9B**, the FY2025 Green Book's own printed row ($245,924M, report p. 242), which the FY2024 edition corroborates at $235,263M on its own window. **Nothing in the model reads the target** — the prediction is the same −$216.5B it was, and only the error column moved. Capital-gains cases use ONE frozen elasticity set — since Wave 2 the `CapitalGainsPolicy` dataclass defaults, which are Dowd–McClelland–Muthitacharoen (2015) persistent 0.72 / transitory 1.20 at a 22% reference rate, applied semi-logarithmically as `R₁ = R₀·exp(−b·Δτ)` with `b = ε/τ_ref` because CRS R48562 defines the realization elasticity on the **tax** rate, not the net-of-tax rate. The old 0.8/0.4 net-of-tax pair is gone, and so are `scenarios.py`'s three per-case tuples and the 5.3× lock-in multiplier. Two Tier 1 rows changed in the Phase E provenance pass: `top_rate_45` is **retired** (its −$420B is in no TPC, CBO or JCT publication and the figure is gone from `CBO_SCORE_MAP` too), and `biden_capital_gains_39` is **re-sourced** to the FY2025 Green Book's actual combined row (−$288.6B) with its shape corrected to that document's definition — $5M per-donor exclusion, taxable-income threshold — which moved its error 79% → 142%; Wave 4's death-channel carve-outs then took it to 16.7% under, and Wave 5's realizations projection to **31.4% over**. Every case has a row in `fiscal_model/validation/preregistered.py`, entered in a commit *before* the commit that first scores it; a target that changes gets a **new row** with `superseded_by`, and one that cannot be sourced gets `retired=True` with the search recorded; the tier is CI-gated (`cold_holdout.py --max-mean-error 20 --min-within-25pct 21`, re-derived by the workflow's own rule after Wave 5 — ceiling `ceil(15.9 × 1.25) = 20 → 20`; floor `22 − 1 = 21`, both tightening, PR #117) and Generic entries are no longer exempt from strict readiness. See [[fpc-review-roadmap]] and `planning/VALIDATION_EXPANSION.md`.

**Tier 2 — calibrated reference models** (parameters tuned to reproduce the official decomposition; low error expected by construction). The calibrated tier is **54 benchmarks** and splits in two: **23 fitted** references at **1.6% mean** (23/23 within 15%, worst row `tcja_no_salt_cap` at 13.9%), and **31 unfitted module reconstructions** — the Phase E international/trade/pharma/enforcement/climate presets, the Phase D P.L. 119-21 JCT line items, the rows whose targets the revision ledger moved out of the fitted tier, and the three capital-gains scenarios Wave 2 unfitted, all scored against published figures no module constant is fit to — at **56.6% mean / 29.9% median**, 9/31 within 15% (itself five populations: **15 sectoral presets at 82.6%**, **8 P.L. 119-21 line items at 35.8%**, **3 capital-gains scenarios at 39.6%**, **TCJA AMT relief at 66.8%** and **the 5 rows Wave 4's provenance pass moved in, at 9.4%**, never to be quoted as one number). **Both tier means moved for composition reasons again in Wave 4, and both fell for reasons that are not improvements, so quote the constant-population figures beside them**: on the **26 rows the reconstruction tier already held** the mean is **65.7% / 40.5% median**, *worse* than the 61.8% / 38.0% it read before Wave 4, because PR #109's pharma rebuild took two rows further from their targets; on the **14 sectoral rows the subset already held** it is **88.2%**, not 82.6%. Never quote one tier for the other — and never quote the fitted count without saying which rows left it, because **three different mechanisms move rows out and all are live**. `ScorecardSummary.revised_target_entries` is **15**: a constant fitted to a superseded figure is not fitted to its replacement, so a revised row reports in the unfitted-reconstruction tier, where a miss is a finding rather than a regression. **Wave 4's provenance pass took the fitted tier 28 → 23** on exactly that rule — `biden_eitc_childless`, `eliminate_salt`, `extend_enhanced_ptc`, `ira_enforcement` and `repeal_salt_cap` left mechanically when their targets moved, and retuning any of them to close the new gap would have been the relaxation; none was touched. Held in place instead, the fitted tier reads **28 at 3.0%, 27/28 within 15%**, the one row over being `eliminate_salt` at 22.3% (or **29 at 5.2%** if the revised TCJA-AMT row is also held in, which is the n=29 reading earlier versions of this file quoted at 4.3%). **The fitted mean fell 2.0% → 1.6% while nothing improved**: every row that left was one the tier had been carrying. Separately, **Wave 2's L1 lane took the fitted tier 33 → 30**: deleting `fiscal_model/validation/scenarios.py`'s per-case behavioural tuples removed the only constants ever fitted to `cbo_2pp_all_brackets`, `pwbm_39_with_stepup` and `pwbm_39_no_stepup`, so `calibrated_to_target` is now `False` for all three and the runner says so. Then **Wave 3's L8 lane took it 30 → 28**: `universal_coverage_rate` (fitted to `trump_universal_10`) became a Census measurement and `china_effective_coverage` (fitted to `trump_china_60`) was deleted for an incremental-rate identity, so no `TRADE_BASELINE` constant is fitted to any target and both rows report as reconstructions — at **37.1%** and **44.3%**, where the fitted constants had them reading 1.1% and 6.2%. The fitted mean *fell* 2.8% → 2.2% → 2.0% → **1.6%** across those moves and Wave 4's while nothing regressed, because every row that left was one this tier had been carrying. That is **composition, not accuracy** — read the two tiers together or neither. **Wave 5 moved neither calibrated tier at all**: all three lanes worked at the Tier 1 margin, no target moved and no constant was retuned, so the fitted 23 stay at 1.6% and the 31 reconstructions at 56.6% / 29.9% — 0 of 23 and 0 of 31 scorecard rows changed, which was pre-registered as a falsification test in each lane and is worth quoting as evidence that a Tier 1 lane can be run without disturbing the reconstruction tier. By provenance the 54 are **30 `line_item` / 5 `line_item_differs` / 12 `secondhand` / 7 `model_estimate` / 0 `unclassified`** after the transcription and revision passes (51 / 5 / 17 / 7 / 0 across both tiers), so the honest published-target count is **47** (and **73** across both tiers, out of 80 scorecard rows) — unchanged by Wave 4, because no row changed to or from `model_estimate`. What Wave 4 changed is how many published targets the repository *agrees with*: **thirteen targets moved onto their documents**, taking calibrated `line_item_differs` from 13 to **5** (nine rows left it and one — the reciprocal tariff, whose point target became a range with an out-of-range anchor — joined it), and **none of the 5 is an open question** — two are range revisions carrying an in-range anchor (`pillar_two_adoption`, `reciprocal_tariffs`) and three are examined-and-left decisions (`biden_estate_reform`, `ctc_extension`, `double_enforcement`), each listed with its verdict in `docs/VALIDATION.md`. The Generic tier now has **zero** `line_item_differs` rows. Where a target is carried unmoved the published figure rides on `ScorecardEntry.official_10yr_billions_line_item`. **Fifteen targets were moved** instead, through `fiscal_model/validation/target_revisions.py` — the calibrated tier's mirror of `preregistered.py`'s supersede rule: ledger entry in one commit, first scoring in the next, old figure kept as a `superseded_by` row, and `target_revision_problems()` failing if ledger and registries ever drift apart. `universal_insulin_cap` −$15B → CBO 57957's **+$11.4B**, which was the repository's only *sign* disagreement and is now zero (model +$7.0B, −39.0%); `extend_tcja_amt` $450B → CRS R48286 Table 1's **$1,357.1B**, a five-year cost that had been sitting in a ten-year column; and, in Wave 3, `pillar_two_adoption` −$80B → JCT JCX-22-23 Table 2's **published range [−$102.6B, +$56.5B]**. **A range revision asserts something a point revision does not.** −$80B is the midpoint of the "$50-120B" range `international.py` documents in its own header and appears in no JCT scenario; choosing one scenario instead would mean choosing the *rest of the world's* behaviour, which is not part of the US policy being scored, and the scenario whose conditioning matches the module's own QDMTT mechanism is also the one it scores best against — exactly the selection the ledger exists to prevent. So `CalibratedTarget` gained `published_low_10yr_billions` / `published_high_10yr_billions`, `is_range`, `contains()` and `distance_to_range()`, and for a range row the consistency check asks **containment**, not equality; `ScorecardEntry` and `/validation/scorecard` expose `published_range_low_billions`, `published_range_high_billions`, `within_published_range` and `distance_to_published_range_billions`. The model's **−$61.2B is inside the range, distance to the nearest bound $0.0B**, so the 23.5% the row reports against −$80B is a distance from an editorial midpoint and not a measurement of accuracy. Nothing moved in the registries or the app, because −$80B is inside the range. **Wave 4 (PR #107) moved twelve more, and used the range mechanism a second time.** Ten were a rounded headline standing in for a printed row (`eliminate_salt` −$1,200B → CBO Option 49's **−$1,621.0B**; `repeal_salt_cap` +$1,100B → PWBM Table 3's **+$1,169.0B**; `biden_gilti_reform` −$280B → **−$373.9B**; `fdii_repeal` −$200B → the Green Book's gross **−$158.0B**; `biden_full_international` −$700B → **−$632.2B**; `biden_eitc_childless` +$178B → **+$162.6B**; `ira_enforcement` −$200B → CBO 58390's **−$180.4B**, replacing a figure CBO had *withdrawn*; `repeal_ev_credits` −$200B → JCX-35-25's **−$182.3B**; `extend_enhanced_ptc` +$350B → **+$335.0B**; `trump_universal_10` −$2,000B → Tax Foundation FF861's **−$2,171.1B**); two were a different kind of error — `auto_tariff_25`'s −$100B was a **per-year** Navarro claim sitting in a ten-year column, superseded by Tax Foundation's **−$386.2B**, and `reciprocal_tariffs`' −$1,200B was **exactly Tax Foundation's dynamic score in a conventional column**, a *tier* error no rescaling would have found. That last one became the second range: CRFB, Tax Foundation and Yale score the same announced schedule on the same window **29% apart** ($1.8T / $1.5T / $1.4T conventional), so the row carries **[−$1,800B, −$1,400B]** with Tax Foundation's $1.5T as the in-range anchor. The model's −$1,396.8B sits **$3.2B outside** the nearer bound, so its 6.9% against the anchor is a distance from one modeller's point rather than a measurement of accuracy. Six of the thirteen Wave 4 revisions got *worse*, which is the shape a correct provenance pass has — if every revision improved its row, the suspicion would be that the documents were chosen to fit. Separately, `EXAMINED_NOT_REVISED` records the opposite verdict — "somebody opened the document and decided against" — so a benchmark nobody has examined stops looking identical to one that was, and a benchmark may not be both revised and examined-and-left. It now has **five** entries: `biden_estate_reform` (JCT's −$429.6B totals a ten-section bill against the module's exemption-and-single-rate construction), `ctc_extension` (CRS R48286's $735.3B is a *superset* including the other-dependents credit, and JCT's +$816.8B scores a $2,200 indexed credit already carried here as `pl119_21_child_tax_credit`), `double_enforcement` (Treasury's $320B is 6% away but scores an **$80B** funding increase on a pre-IRA baseline where the preset stacks ~$160B on top of the IRA's $80B — the gap argues for moving it, the dose against), `steel_tariff_25` (the 25% Section 232 rate was in force for ten weeks and no scorekeeper published a ten-year estimate of it; left unsourced and explicitly **not retired**, because retiring a case to avoid reporting an unsourced target is the failure mode the ledger exists to prevent) and `eliminate_mortgage` (no official repeal score exists, and the two that do come from the **same simulator and differ by 2.4×** — CRS IF13190's $495B against Yale's "close to $1.2 trillion"). No AMT constant was retuned to chase `extend_tcja_amt`'s new figure — which is why the fitted path scores −66.8% and the unfitted structural path −37.0% against the same corrected row. `repeal_individual_amt` keeps its unsourced $450B: no published post-2025 repeal score exists, and TPC T25-0049's $948.9B is a baseline projection *and* `amt.py`'s own input, so adopting it would manufacture a 0% row out of the leakage `loo.py` guards against. **Twelve calibrated `secondhand` rows still could not be traced to any document** (down from 15), including both Social Security payroll targets (OCACT publishes only percent-of-payroll, no dollars, for E2.1 and E2.5), `repeal_ira_credits`, `trump_china_60`, `cap_charitable`, `eliminate_step_up`, `biden_ctc_2021`, `repeal_ptc`, `cap_employer_health` and `repeal_individual_amt`, plus the two Wave 4 examined and left. Each needs the same per-target judgement, and several have nothing to move *to*. The eight P.L. 119-21 rows (JCX-35-25, transcribed with page refs to `fiscal_model/data_files/validation/pl119_21_jct_line_items.csv`) are the first block sourced line-by-line from a single JCT table: the TCJA module reproduces CBO's $4.6T aggregate to 0.4% and JCT's own component rows to **35.8%** (scored over JCT's own FY2025-2034 window), which is the sharpest evidence that the calibrated tier is reconstruction rather than structure. Held out, the fitted modules score **29.6% mean / 19.1% median over 18 leave-one-out cases**, 8/18 within 15% (**4** more declared not cross-validatable, never folded in) — run `python scripts/run_loo.py`; report that separately from the by-construction figure, never as a replacement for it. **Wave 5 left `run_loo.py --donor-matrix` byte-identical** and surfaced a gap in what it covers: the suite holds Payroll, Estate, AMT, Credits, Expenditures and CapitalGains and **has no `Corporate` row at all**, so the one module whose base constant was self-documented as calibrated has never been cross-validated (PR #114 finding 5). Adding it is a `loo.py` edit, which no modelling lane may make; it is on the carry-over list. **Wave 4 moved that suite 28.4% → 29.6% and every bit of the move is a *target* movement, not a derivation one**: `run_loo.py --donor-matrix` differs from pre-Wave-4 main in exactly five lines and every derived figure in them is identical, because PR #107 moved three of the targets the suite scores against — `biden_eitc_childless` −38.0% → **−32.1%** (derivation unchanged at 110.4), `repeal_salt_cap` −29.4% → **−33.5%** (777.0), `eliminate_salt` +10.2% → **+33.5%** (−1,077.9). Per module that reads `Credits` 20.5% → **18.5%** and `Expenditures` 30.2% → **35.7%**; Payroll (3.8%), Estate (10.4%), AMT (73.9%) and CapitalGains (39.6%) are untouched, and no donor-matrix entry moved. Wave 2 moved three modules: `CapitalGains` **171.2% → 39.6%** (one frozen literature set replacing three hand-set tuples; `--donor-matrix` now prints three identical rows, because there is no donor left), `Estate` **25.8% → 10.4%** and `Expenditures` **39.4% → 28.8%**. Wave 3 moved two more, and in opposite directions. `Credits` **45.1% → 20.5%** (n=3, none excluded): L3 replaced a `Δcredit × units × participation` identity with two parameter sets run through `MicroTaxCalculator` over CPS ASEC tax units and differenced on final liability, which prices refundability, the tax limit on the non-refundable leg and the qualifying-age expansions the old path had no place to put — `biden_ctc_2021` **−64.1% → −4.5%**, `ctc_extension` **−28.0% → +19.0%**, `biden_eitc_childless` **−43.1% → −38.0%**. `Expenditures` **28.8% (n=4) → 30.2% (n=5)**, and that *rise* is the honest reading: PR #100 replaced `annual_cost_no_cap = 120.0` — exactly the `eliminate_salt` target over ten — with **$89.55B** computed from IRS SOI Table 2.1 priced at the IRC §1 married-joint schedule, so `loo.py`'s untouched leakage guard stopped firing and `eliminate_salt` **re-entered** the derivable set at **+10.2%**, while `repeal_salt_cap` moved **+4.0% → −29.4%** because its old +4.0% was `−(120.0 − 25.0)`, the same leaked constant under a different benchmark. The check that the derivation is not made up: the identical computation on SOI's *limited* column returns **$25.0B** against the record's own `annual_cost = 25.0`. Read the suite figure with that composition attached — the suite now cross-validates **18 of 22** calibrated benchmarks where Wave 2 left it cross-validating 17 and excluding one for leakage. The LOO mean *fell* from 61.7% when the AMT extension's target moved, and that is a **target** movement rather than a model one: `extend_tcja_amt`'s held-out derivation is unchanged at **$855.3B** and its error against the corrected row is −37.0% instead of +90.1%, taking the AMT module from 100.5% to **73.9%**. No donor-matrix entry moved. Examples:

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
