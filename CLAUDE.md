# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fiscal Policy Impact Calculator — a web app that estimates budgetary and economic effects of tax and spending proposals. Live at: https://fiscal-policy-calculator.streamlit.app

See `planning/ROADMAP.md` for the full roadmap and next priorities.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run app locally
streamlit run app.py

# Run app locally (classroom mode)
streamlit run classroom_app.py

# Run unit tests (960+ tests)
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

### Module Structure

| Module | Purpose |
|--------|---------|
| `app.py` | Streamlit UI — policy inputs, results charts, dynamic scoring, distribution, comparison |
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
    step_up_lock_in_multiplier=2.0,  # 5.3x matches PWBM revenue loss
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

All core features, all four horizon features, the distributional-validation cycle, and the Ask assistant feature are complete (May 2026). **1200+ tests passing across the model + Ask stack.**

Completed:
1. ✅ 25+ CBO/JCT-validated policies, distributional analysis, dynamic scoring
2. ✅ Tariff scoring, microsimulation engine, FastAPI endpoints
3. ✅ OLG model (30-period Auerbach-Kotlikoff, SS/Medicare reform)
4. ✅ Classroom Mode (7 assignments, PDF export, 80 tests)
5. ✅ State-Level Modeling (top 10 states, SALT interaction)
6. ✅ Real-Time Bill Tracker (congress.gov pipeline, LLM extraction, SQLite)
7. ✅ 6 CBO/JCT distributional benchmarks wired end-to-end (see `docs/VALIDATION_NOTES.md`)
8. ✅ CPS ASEC microsim scaffold with SOI calibration, top-tail Pareto augmentation, and filing-threshold filter
9. ✅ Multi-model pilot platform (CBO-style, TPC-microsim, PWBM-OLG) wired into the Scoring Models tab
10. ✅ API hardening (X-API-Key auth, rate limiting, structured logging)
11. ✅ `GET /summary`, `GET /benchmarks` API endpoints + `scripts/run_validation_dashboard.py` CI gate
12. ✅ **Ask assistant** — citation-grounded Q&A, 19 curated authoritative snapshots, streaming tool-use loop, `/ask` + `/ask/stream` (SSE) endpoints, token-gated admin dashboard, share-link encoding, hard daily cost cap, /health + /readiness integration. 105 tests across the assistant stack.

Next: closing the ARP bundle scope residual (needs Recovery Rebate engine integration) and broadening the multi-model pilots to more policy types. See `planning/NEXT_STEPS.md`.

## Target Validation

25+ policies validated within 15% of CBO/JCT estimates. Key examples:

| Policy | Official Score | Model Score | Error | Status |
|--------|----------------|-------------|-------|--------|
| Biden $400K+ (2.6pp) | -$252B | ~-$250B | ~1% | ✅ |
| **TCJA Extension** | **$4,600B** | **$4,582B** | **0.4%** | ✅ |
| **Corporate 21%→28%** | **-$1,347B** | **-$1,397B** | **3.7%** | ✅ |
| **Biden CTC 2021** | **$1,600B** | **$1,743B** | **8.9%** | ✅ |
| **Estate: Biden Reform** | **-$450B** | **-$496B** | **10.1%** | ✅ |
| **SS Donut $250K** | **-$2,700B** | **-$2,371B** | **12.2%** | ✅ |
| **Repeal Corporate AMT** | **$220B** | **$220B** | **0.0%** | ✅ |
| **Cap Employer Health** | **-$450B** | **-$450B** | **0.1%** | ✅ |

## Future Architecture

Multi-model platform with pluggable scoring engines (next major milestone):
- `models/cbo/` — CBO-style conventional + dynamic
- `models/jct/` — JCT-inspired microsimulation
- `models/tpc/` — Tax Policy Center distributional
- `models/pwbm/` — Penn Wharton OLG (foundation now in `long_run/`)
- `models/yale/` — Yale Budget Lab macro + microsim + behavioral

See `docs/ARCHITECTURE.md` for full design including Yale Budget Lab feature-parity checklist.
