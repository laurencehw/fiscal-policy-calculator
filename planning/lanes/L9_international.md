# Lane L9 — International base overlap

*Wave 3 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §3 L9.
Opened 2026-09-02 on `model/l9-international`, branched from `main` @ `7f25bed`
(at the merge of PR #96).*

Pre-registration first (§1.3): this file states the errors before the lane opens
`fiscal_model/international.py` and what it expects afterwards. The outturn is
appended in the lane's last commit. Nothing below is a promise of attainment —
§1.5 forbids that — and every number in §3 was computed by hand from published
figures *before* a line of module code changed, so a reader can check whether
the mechanism behaved as the lane said it would.

**This lane expects two of its four rows to get worse, and says so here rather
than after the fact.** That is the whole of §3.2 and it is the informative part.

## 1. Starting point (measured on `7f25bed`)

`python scripts/cold_holdout.py`, unfitted-reconstruction tier, International:

| Row | Target | Model | Error |
|---|---:|---:|---:|
| `biden_gilti_reform` | −$280.0B | −$230.3B | **17.76%** |
| `fdii_repeal` | −$200.0B | −$170.0B | **15.00%** |
| `pillar_two_adoption` | −$80.0B | −$61.2B | **23.50%** |
| `biden_full_international` | −$700.0B | −$413.0B | **41.00%** |

Tier aggregates on the same commit (post-Wave-2, so these differ from §2.3 of
the plan, which is the pre-Wave-1 record):

- **12-row uncalibrated sectoral subset: 104.84% mean / 39.98% median** (mass 1,258.0).
- 24-row reconstruction tier: **72.1% mean**, 5/24 within 15%.
- Out-of-sample Tier 1: **31.3% mean / 14.1% median, 13/25 within 15%, 18/25 within 25%**.
- Calibrated fitted: **30 rows, 2.2% mean**.
- Leave-one-out: **17 derivable, 32.3% mean / 19.2% median, 8/17 within 15%**
  (5 not cross-validatable).

The four international rows carry **97.3** of the sectoral subset's 1,258.0 of
mass — 7.7% of it. This is Rank 9 in the plan for a reason; the lane is worth
running for the mechanism, not for the tier mean.

## 2. What the lane changes

Both changes are the ones §3 L9 names. Neither is fitted to any benchmark.

**(a) A base-overlap term.** `estimate_static_revenue_effect` is a bare
four-way sum. A reformed per-country GILTI and a Pillar Two top-up reach *the
same* profits — a US multinational's foreign earnings in jurisdictions whose
effective rate is below the minimum — and summing the two claims books that
income twice. JCT states the fix as an ordering rule (JCX-22-23, p. 6: "local
corporate income taxes … QDMTTs, CFC rules (including GILTI …), IIRs, and
finally UTPRs"), and its Equation 1 subtracts the top-up another provision has
already taken. The lane adds `_estimate_base_overlap()`, computed
jurisdiction-by-jurisdiction on an effective-tax-rate distribution transcribed
from IRS SOI's Country-by-Country Report, and subtracts it.

**(b) An FDII base × rate identity.** `_estimate_fdii_reform` returns a flat
`base["fdii_cost_billions"]` (\$20B/yr) for a repeal, while the rate-change
branch two lines below it uses the identity `(new_effective − current_effective)
× fdii_base` on a \$160B base — which at the 37.5% deduction and a 21% statutory
rate is \$12.6B/yr. **The same function's two branches disagree by 59% about what
the FDII deduction costs.** The lane gives repeal the identity and sources the
base to Treasury's own published tax expenditure for the provision.

## 3. Pre-registered expectations

### 3.1 The plan's registered targets (§3 L9)

- `biden_full_international` **41.0% → <25%**
- `fdii_repeal` (15.0%) and `biden_gilti_reform` (17.8%) **must not regress**
- `pillar_two_adoption` (23.5%) is target imprecision — report it against JCT's
  published range as well as the carried midpoint; do not change the target

### 3.2 This lane's own derived expectation — and why it differs

**None of the three is reachable, and two go the other way.** The reasons are
arithmetic and were checkable before the lane started:

1. **The double count §3 L9 names is not in `create_biden_full_international`.**
   The plan says the package "adds a 21% per-country GILTI to Pillar Two's UTPR
   on substantially the same undertaxed foreign profits". As the module is
   coded it does not: `_estimate_utpr` reads
   `foreign_undertaxed_in_us_billions` — profits of **foreign-parented** groups
   — while `_estimate_gilti_reform` reads the CFC income of **US-parented**
   groups. Those bases are disjoint, so an overlap term correctly nets **zero**
   between them. The netting bites between a GILTI reform and a Pillar Two
   top-up, which no shipped factory combines (`create_biden_full_international`
   sets `adopt_utpr=True` and leaves `pillar_two_adopt=False`). **The overlap
   term therefore moves no benchmark row.** It is a correctness fix for
   composite policies, and the lane ships it as one.
2. **The package cannot close, because what is missing from it is a level, not
   an interaction.** Treasury's FY2025 Green Book scores the UTPR it proposes
   at **\$136,313M** over FY2025-2034; the module's UTPR returns \$1.5B/yr, i.e.
   **\$15B**, one ninth of it. Independently, JCT's Scenario 5 minus Scenario 4
   (JCX-22-23 Table 2) prices a US UTPR at **\$133.9B** over FY2023-2033. Two
   published sources agree within 2%, and the module is 9× under both. Closing
   the package means re-basing the UTPR on JCT Equation 2 — the *group's* global
   low-taxed profit allocated to the US by an employee-and-tangible-asset key,
   not profits booked in the US — which needs OECD CbCR aggregates by
   ultimate-parent jurisdiction. `oecd.org` returns HTTP 403 to this
   environment, and the only reachable figure for the quantity is Treasury's own
   row **inside the package benchmark**, so deriving the base from it would be
   circular. **Out of scope, and recorded as the package's dominant residual
   rather than closed.**
3. **The FDII identity makes that row worse against its carried target, because
   the carried target is 54% above Treasury's own published cost for the
   provision.** Treasury OTA's *Tax Expenditures FY2026* prices the FDII
   deduction at **\$130,230M over FY2025-2034** — \$13.0B/yr, against the
   module's \$20B/yr. The repository already records that this row's −\$200B
   "matches neither the gross row (21% away) nor Treasury's net score (zero)"
   (`benchmark_sources.py`, provenance `line_item_differs`). So an identity
   built on the published cost moves the model **toward the document and away
   from the number the row is scored against**. That is the same shape as L5's
   AMT finding and L7's insulin finding, and it is reported the same way.

Hand-computed from the published figures in §4, before any code change. The
module's behavioural offset is `profit_shifting_elasticity (0.5) ×
behavioral_offset_factor (0.3)` = 15%, so net = static × 0.85, and the scorer
repeats the annual figure flat for ten years.

| Row | Before | Expected after | Basis |
|---|---:|---:|---|
| `biden_gilti_reform` | −$230.3B / 17.76% | **unchanged** | not touched |
| `pillar_two_adoption` | −$61.2B / 23.50% | **unchanged** | not touched |
| `fdii_repeal` | −$170.0B / 15.00% | **≈ −$110.7B / ≈ 44.7%** | $165.4B FDII income × 37.5% deduction × 21% = $13.02B/yr; × 0.85 × 10 |
| `biden_full_international` | −$413.0B / 41.00% | **≈ −$353.7B / ≈ 49.5%** | ($27.09 GILTI + $13.02 FDII + $1.50 UTPR)/yr × 0.85 × 10 |
| **12-row sectoral mean** | **104.84%** | **≈ 108.0%** | mass 1,258.0 → ≈ 1,296.1; median 39.98% → ≈ 41.8% |
| 24-row reconstruction mean | 72.1% | **≈ 73.7%** | same mass change over 24 rows |
| Tier 1 out-of-sample (n=25) | 31.3% | **unchanged** | no international case in the tier |
| Calibrated fitted (n=30) | 2.2% | **unchanged** | no international row is fitted |
| Leave-one-out (n=17) | 32.3% | **unchanged** | the international module has no LOO case |

**This is a net regression of about 3.2pp on the sectoral subset, and the lane
registers it before shipping.** The defence is not that the number improves; it
is that \$20B/yr was a round constant inconsistent with the module's own \$160B
base, and \$13.0B/yr is Treasury's own published figure for the same provision,
reached by the identity §3 L9 asked for. A lane that kept \$20B/yr to protect a
15% row would be doing exactly what §1.1 forbids.

### 3.3 What would falsify the lane

- Any of the eight untouched sectoral rows moving at all — the diff is confined
  to `international.py`, one new data file, the runner's `known_limitations`
  strings and tests.
- `biden_gilti_reform` or `pillar_two_adoption` moving by any amount. Both are
  outside the diff, and the overlap term must return zero for both.
- The overlap term returning non-zero for any of the four shipped factories.
- Tier 1, the fitted tier, the distributional tables or the leave-one-out tier
  moving. None contains an international case.
- `fdii_repeal` landing anywhere other than ≈ −$110.7B, or the package anywhere
  other than ≈ −$353.7B. Both are closed-form.

## 4. Sources transcribed

All figures land in `fiscal_model/data_files/international/` with a provenance
header, on the pattern L7 set in `data_files/pharma/`.

| Quantity | Value | Source |
|---|---|---|
| FDII deduction, tax expenditure FY2025-2034 | **\$130,230M** (FY2025 16,420 → FY2034 14,190) | Treasury OTA, *Tax Expenditures FY2026*, 27 Nov 2024, Table 1 line 5; PDF p. 25 |
| §250(a)(3) deduction rate | 37.5% through TY2025, **21.875%** from TY2026 | same, item 5 description, PDF p. 4 |
| Reduced rate on CFC active income, tax expenditure FY2025-2034 | \$383,830M | same, Table 1 line 4 (external check only) |
| Green Book row, "Repeal the deduction for foreign-derived intangible income" | gross **\$157,993M**, paired with −\$157,993M of R&D support, subtotal **\$0** | Treasury, *General Explanations … FY2025* (Green Book), Table of Revenue Estimates, report p. 239 / PDF p. 247 |
| Green Book row, "Adopt the undertaxed profits rule" | **\$136,313M** | same |
| Green Book row, "Revise the global minimum tax regime, limit inversions, and make related reforms" | \$373,919M | same |
| Green Book, "Subtotal, Reform International Taxation" | \$632,200M | same, report p. 240 / PDF p. 248 |
| Pillar Two ordering of priority | local CIT → QDMTT → CFC rules (GILTI) → IIR → UTPR | JCT, JCX-22-23, *Possible Effects of Adopting the OECD's Pillar Two*, June 2023, p. 6 |
| Top-up identity (IIR net of QDMTT already paid) | Eq. 1, `max(0, 15% − ETR_j)(Y_j − SBIE_j) + ACTT_j − QDMTT_j` | same, p. 3 |
| UTPR identity and allocation key | Eq. 2, 50% × [EMP_k/EMP_j + TANG_k/TANG_j] × Σ_M max(0, 15% − ETR_M)(Y_M − SBIE_M) | same, p. 4 |
| Substance-based income exclusion | 5% of payroll **and** 5% of tangible assets | same, p. 3 |
| JCT Table 2, Scenario 4 (US enacts Pillar Two, no US UTPR) | **+\$102.6B** FY2023-2033 | same, p. 10 |
| JCT Table 2, Scenario 5 (US enacts, including a UTPR) | **+\$236.5B** FY2023-2033 → implied UTPR **\$133.9B** | same, p. 10 |
| JCT Table 2, Scenario 2 (rest of world enacts too) | **−\$56.5B** — a revenue *loss* | same, p. 10 |
| US MNE foreign profit, ETR < 15% sub-groups, TY2023 | profit **\$772.1B**, tax accrued \$31.4B, tangible assets \$1,103.6B, employees 4.59M | IRS SOI, *Country-by-Country Report* (Form 8975) Table 4, TY2023, published March 2026 |
| …plus positive-profit sub-groups with negative accrued tax | profit \$40.3B, tax −\$5.7B, tangible \$84.1B | same |
| US MNE foreign profit, ETR ≥ 15% sub-groups, TY2023 | profit \$463.0B, tax accrued \$137.6B | same |

**The CbCR caveat, stated once and carried in the data file.** Form 8975
"profit (loss) before income tax" is a financial-accounting measure that
includes intra-group dividends and equity income, and "income tax accrued —
current year" excludes deferred tax; the US row's implied 5.4% rate on
below-15% sub-groups is the artefact this produces. The lane therefore uses the
distribution's **shape** — which jurisdictions sit below a given minimum rate,
and how the two provisions' claims interleave across them — and takes no level
from it. Every level in the module is unchanged.

## 5. Two findings recorded for the provenance lane, not acted on

Both are §1.6 work and this lane does not touch a target.

1. **`pillar_two_adoption` should be read against JCT's range, not the −\$80B
   midpoint.** JCT publishes no −\$80B. Its Scenario 4 — a US QDMTT and a
   Pillar-Two-compliant IIR, no UTPR, which is what
   `create_pillar_two_adoption` models — is **+\$102.6B** over FY2023-2033, and
   the module's −\$61.2B is 40% under it, not 23.5% under a midpoint. The row's
   own module note gives the range as \$50-120B, inside which −\$61.2B sits.
   The finding that matters is the **conditioning**: every JCT scenario that
   raises revenue assumes the rest of the world does *not* enact. Under
   Scenario 2, the state of the world, US adoption **loses \$56.5B** — the
   opposite sign to the benchmark.
2. **`biden_gilti_reform`'s two module constants are self-declared calibration
   factors** (`gilti_cbc_revenue_multiplier = 1.20`, comment "Treasury
   calibrated"; `gilti_ftc_offset_rate = 0.40`, comment "Calibration factor").
   Treasury OTA prices the whole CFC active-income preference at **\$383,830M**
   over FY2025-2034, against the module's implied \$271B for taking GILTI to the
   full statutory rate with QBAI eliminated — the identity that would replace
   both constants. It is left alone deliberately: the lane was told not to
   regress that row, the tax expenditure also covers §245A exclusions a GILTI
   rate change does not recover, and swapping a fitted constant for a
   published-but-broader one on a row outside the lane's two named mechanisms
   is the kind of unregistered move §1.3 exists to prevent. Recorded so the
   next lane has the number.

## 6. Outturn

Measured on `65b9f9d`, the lane's last code commit. (The figures were first
measured on `676b336`; the readability pass after it changed no number — the
commit message records the check.)

| Row | Target | Before | After | Error before → after |
|---|---:|---:|---:|---:|
| `biden_gilti_reform` | −$280.0B | −$230.27B | −$230.27B | 17.76% → **17.76%** |
| `fdii_repeal` | −$200.0B | −$170.00B | **−$110.70B** | 15.00% → **44.65%** |
| `pillar_two_adoption` | −$80.0B | −$61.20B | −$61.20B | 23.50% → **23.50%** |
| `biden_full_international` | −$700.0B | −$413.00B | **−$353.71B** | 41.00% → **49.47%** |
| **12-row sectoral subset** | | **104.84%** | **108.01%** | median 39.98% → 47.06% |
| 24-row reconstruction tier | | 72.1% | **73.7%** | 5/24 → 4/24 within 15% |
| Tier 1 out-of-sample (n=25) | | 31.3% | **31.3%** | 13/25 and 18/25 unchanged |
| Calibrated fitted (n=30) | | 2.2% | **2.2%** | 30/30 within 15% unchanged |
| Leave-one-out (n=17) | | 32.3% | **32.3%** | median 19.2%, 8/17 unchanged |

**The pre-registration held on everything it argued from, and missed one number
it did not.** §3.2 predicted `fdii_repeal` at ≈ −$110.7B / ≈ 44.7% and the
package at ≈ −$353.7B / ≈ 49.5%; the runners return −$110.70B / 44.65% and
−$353.71B / 49.47%. The sectoral mean was predicted at ≈ 108.0% and returns
108.01%; the 24-row tier at ≈ 73.7% and returns 73.7%. The sectoral **median**
was predicted at ≈ 41.8% and came in at **47.06%** — an indexing slip in the
hand arithmetic, which took the 5th and 6th of twelve sorted errors instead of
the 6th and 7th. Recorded rather than quietly corrected, per §1.3.

**Every falsification test in §3.3 passed.** None of the eight sectoral rows
this lane does not own moved by any amount; `biden_gilti_reform` and
`pillar_two_adoption` are unchanged to the cent; the overlap term returns
exactly zero for all five shipped factories, which
`test_no_shipped_factory_books_an_overlap` now pins; and Tier 1, the fitted
tier and the leave-one-out tier are unchanged, as is the distributional set.

### The overlap term, and the finding that came with it

It ships and it changes nothing on the battery — which was registered in
advance and is the point, not an excuse. What it does establish is a result
worth having in writing:

> With an 80% foreign tax credit, a per-country GILTI at 21% claims
> `0.21·Y − 0.8·T` from a jurisdiction where a 15% Pillar Two top-up claims at
> most `0.15·Y − T`. The difference is `0.06·Y + 0.2·T`, positive for every
> positive profit and non-negative tax. **A 21% per-country GILTI subsumes a
> 15% minimum tax in every jurisdiction, without exception**, so a policy
> carrying both raises the larger of the two, never the sum.

That is algebra; the CbCR distribution is what shows where it stops holding.
`shared_claim_share(0.13125, 0.15)` — the 2026 statutory GILTI rate against the
OECD minimum — returns **0.9916**, not 1: at that rate the two provisions
interleave across jurisdictions and about 0.8% of the smaller claim sits
outside the larger. A constant would have got the 21% case right and this one
wrong.

The plan's premise about *where* the double count sits did not survive contact
with the code, and §3.2 said so before the lane opened a file. The module's
UTPR reads foreign-parented profits and its GILTI reads US-parented CFC income;
`create_biden_full_international` combines exactly those two, so its overlap is
zero. The package's residual is a **level**: a \$15B UTPR against Treasury's own
\$136,313M row and JCT's implied \$133.9B, partly offset by an FDII repeal
booked at \$130B where Treasury's printed subtotal is \$0.

### `pillar_two_adoption` read against the range, not the midpoint

Required by the lane brief; no target was touched.

| Comparator | Figure | Model −$61.2B is |
|---|---:|---:|
| Carried benchmark (midpoint) | −$80.0B | 23.5% low |
| The module's own stated range | $50–120B | **inside it** |
| JCT JCX-22-23 Scenario 4 — the scenario this factory models | +$102.6B | 40.4% low |
| JCT Scenario 2 — rest of the world enacts too | **−$56.5B**, a revenue *loss* | opposite sign |

The row's real problem is not its distance from any of these. It is that
`create_pillar_two_adoption` models US adoption **conditional on nobody else
adopting**, which is the only state of the world in which JCT scores it as a
raiser at all. Provenance work (§1.6), flagged here and left alone.

### Shipped preset output moved

| Preset | Official | Before | After |
|---|---:|---:|---:|
| 🌍 Biden GILTI Reform | −$280B | −$230.27B | unchanged |
| 🌍 Repeal FDII | −$200B | −$170.00B | **−$110.70B** |
| 🌍 Pillar Two Adoption | −$80B | −$61.20B | unchanged |
| 🌍 Biden International Package | −$700B | −$413.00B | **−$353.71B** |

No preset label or `CBO_SCORE_MAP` entry changed: those carry the official
score, not the model's, and this lane touched no target.

### What this lane did not do

- **The UTPR was not re-based.** It needs OECD country-by-country aggregates by
  ultimate-parent jurisdiction to size the global low-taxed pool and the US
  allocation key of JCT's Equation 2; `oecd.org` returns HTTP 403 to this
  environment, and the only reachable figure for the quantity — Treasury's own
  \$136,313M — sits inside the `biden_full_international` benchmark, so
  deriving the base from it would be circular. **This is the single largest
  remaining item in the module** and it is what a Wave 4 lane should open with.
- **`biden_gilti_reform`'s two fitted constants were not replaced**, for the
  reasons in §5.2. The identity and its published figure are recorded there.
- **No target moved**, no per-benchmark constant was added, and
  `cold_holdout.py`, `run_loo.py`, `loo.py`, `preregistered.py`,
  `target_revisions.py`, `benchmark_sources.py`, `KNOWN_SCORES` and
  `CBO_SCORE_MAP` were not opened.
- **`fiscal_model/assistant/knowledge/international_tax.md` is stale and was
  left stale.** Its "What the app reproduces" block claims GILTI \$340B, FDII
  \$145B and a \$960B package; the module returned \$230B / \$170B / \$413B
  *before* this lane and \$230B / \$111B / \$354B after. The file is the Ask
  assistant's citation-grounded knowledge base, not this lane's to edit, and it
  was already wrong by a factor the lane did not create. Flagged for whoever
  owns it.

### Gates

| Gate | Exit |
|---|---|
| `ruff check fiscal_model/ tests/ app.py app_pages/ components/ classroom_app.py scripts/` | 0 |
| `pytest tests/ -q -x` | 0 — 3,026 passed, 1 skipped |
| `cold_holdout.py --max-mean-error 40 --min-within-25pct 17` | 0 |
| `run_loo.py --donor-matrix --max-mean-error 75` | 0 |
| `run_validation_dashboard.py` | 1 — pre-existing (runtime Python 3.14 and microdata calibration degraded) |
| `check_readiness.py --strict` | 2 — pre-existing (same two warnings plus the two documented Poor outliers) |
