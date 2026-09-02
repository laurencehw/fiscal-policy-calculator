# Lane L7 — Pharma incidence

*Wave 1 of [`planning/MODELING_IMPROVEMENT.md`](../MODELING_IMPROVEMENT.md) §3 L7.
Opened 2026-09-01 on `model/l7-pharma`, branched from `main` @ `cff6b88`.*

Pre-registration first (§1.3): this file states the errors before the lane
opens `fiscal_model/pharma.py` and what it expects afterwards. The outturn is
appended in the lane's last commit. Nothing below is a promise of attainment —
§1.5 forbids that — and the numbers here were computed by hand from published
figures *before* a line of module code changed, so a reader can check whether
the mechanism behaved as the lane said it would.

## 1. Starting point (measured on `cff6b88`)

`python scripts/cold_holdout.py`, unfitted-reconstruction tier:

| Row | Target | Model | Error |
|---|---:|---:|---:|
| `universal_insulin_cap` | −$15.0B | −$445.3B | **2,868.6%** |
| `international_reference_pricing` | −$100.0B | −$1,387.9B | **1,287.9%** |
| `expand_drug_negotiation` | −$500.0B | −$371.5B | 25.7% |

Tier aggregates on the same commit:

- **12-row sectoral subset: 394.1% mean / 57.1% median** (mass 4,729).
- 20-row reconstruction tier (sectoral + the 8 P.L. 119-21 line items):
  250.8% mean / 43.1% median.
- The other nine sectoral rows (tariffs 152.3 / 128.0 / 73.2, enforcement 82.3,
  international 41.0 / 23.5 / 17.8 / 15.0, climate 14.2) plus
  `expand_drug_negotiation` 25.7 carry **572.7** of that mass between them.

## 2. What the lane changes

Two localised incidence bugs, neither of which is calibration drift:

- **(a) Insulin.** `_estimate_insulin_savings` books the whole retail-minus-cap
  differential — `($6,000 − $420) × 8.4M` — as a federal outlay reduction, and
  `extend_to_private=True` sets `medicare_share = 1.0`, so extending a cap to
  private insurance *raises* the modelled federal saving 2.5×. A $35/month
  insulin cap is a **cost-sharing** cap: it moves a patient's liability onto the
  plan, and the federal budget picks up only its share of that shift.
- **(b) Reference pricing.** `_estimate_reference_pricing_savings` applies RAND's
  **gross list-price** ratio (2.56) to a **net** Part B + D spending base with no
  rebate adjustment and no brand/generic split — even though US unbranded
  generics are *cheaper* than the OECD comparison and cannot contribute savings.

Both are re-specified on a net-price, brand-only, federal-share basis from
MedPAC, ASPE and RAND figures transcribed into a data file. No parameter is
fitted to any of the three benchmarks.

## 3. Pre-registered expectations

### 3.1 The plan's registered targets (§3 L7)

- `international_reference_pricing` **1,287.9% → <100%**
- sectoral reconstruction mean **394.1% → ~40%** (measured on the 12-row
  sectoral subset, not the 20-row tier)

### 3.2 This lane's own derived expectation — and why it differs

Both plan targets are **arithmetically unreachable from this lane**, and the
lane says so before it starts rather than after it misses:

1. **The sectoral mean has a floor of 47.7%.** Nine of the twelve rows belong to
   other lanes (L8 tariffs, L9 international, enforcement, climate) and one is
   `expand_drug_negotiation`, which this lane does not touch. Their mass is
   572.7, so even driving *both* pharma incidence rows to exactly 0% error
   leaves 572.7 / 12 = **47.7%**. "→ ~40%" needs L8 as well.
2. **Reference pricing cannot reach <100% against a −$100B target**, because
   −$100B is not a score of this policy. Its provenance in
   `benchmark_sources.py` is `model_estimate` ("a RAND price-comparison study is
   a price statistic, not a budget score"), and CBO scored a *narrower*
   international-reference policy — H.R. 3's cap at 120% of the average
   international market price on a limited set of drugs — at several hundred
   billion dollars of Medicare savings over ten years. A correct model of "cap
   **all** Medicare drug prices at 120% of the OECD average" must therefore land
   in that neighbourhood or above, not below $200B. Closing this row to <100%
   would require making the model wrong.

Hand-computed from the published figures below, before any code change:

| Row | Before | Expected after | Basis |
|---|---:|---:|---|
| `universal_insulin_cap` | −$445.3B / 2,868.6% | **≈ +$7B**, a deficit *increase* | ASPE's $734M/yr of Part D out-of-pocket relief × Medicare's 74.5% basic-benefit subsidy share, plus the private-market cost shift × CBO's 32% marginal income-plus-payroll offset |
| `international_reference_pricing` | −$1,387.9B / 1,287.9% | **≈ −$746B / ≈ 646%** | brand-only, rebate-netted Part D + Part B base × the cut implied by RAND's *net* brand ratio (3.08 → 1.20) × the federal share of each program |
| `expand_drug_negotiation` | −$371.5B / 25.7% | unchanged | not touched |
| **12-row sectoral mean** | **394.1%** | **≈ 114%** | (572.7 + 146.6 + 646.1) / 12 |
| 20-row reconstruction mean | 250.8% | ≈ 83% | mass 5,016 → ≈ 1,652 |

**No percentage target is written for the insulin row, deliberately.** Its
carried benchmark has the wrong *sign*: CBO publication 57957 scores a
private-market insulin cap at about **+$11.4B of deficit** (+$6.566B outlays,
−$4.793B revenues, FY2022-2031), against the stored −$15B of savings. Editing
that target is provenance work through the manifest's `superseded_by` rule and
is out of this lane (§4). So the row is judged on two things a percentage cannot
express: (i) does the model now agree with CBO on **sign** — the cap should add
to the deficit, not reduce it; (ii) is it the right **order of magnitude** next
to CBO's +$11.4B. The percent error against the stored −$15B is expected to be
worse than 100% precisely *because* the model is now pointing the right way.

### 3.3 What would falsify the lane

- Any of the nine untouched sectoral rows moving at all (the diff is confined to
  `pharma.py`, one new data file and a dead key in `enforcement.py`).
- The insulin row staying negative — that would mean the incidence bug survived.
- The reference-pricing row collapsing to a small number, which would mean the
  corrections over-shot into a different error rather than fixing incidence.
- Tier 1 (out-of-sample) or the leave-one-out tier moving by any amount. Neither
  contains a pharma case.

## 4. Sources transcribed

All figures land in `fiscal_model/data_files/pharma/` with a provenance header.

| Quantity | Value | Source |
|---|---|---|
| Part D out-of-pocket relief from a $35/month cap | $734M (2020) | HHS ASPE, *Report on the Affordability of Insulin*, Dec 2022, p. 15 |
| Insulin users; share Medicare / private | 7.5M; 52% / 33% | ASPE, same report, pp. 9 and 39 (MEPS 2019) |
| Average out-of-pocket cost per insulin fill | $63, Medicare and private alike | ASPE, same report, p. 12 |
| Medicare's share of Part D basic-benefit cost | 74.5% (statutory) | MedPAC, *Report to the Congress: Medicare Payment Policy*, March 2025, ch. 12, p. 7 |
| Medicare's share of total Part D program spending | 76.3% ($112.1B of $147.0B, 2023) | MedPAC, same chapter, p. 409 |
| Marginal income + payroll rate on employer premiums | 18% + 14% = 32% | CBO, *Reduce Tax Subsidies for Employment-Based Health Insurance*, budget option 58627 |
| Brand share of gross Part D spending | over 80% (2021) | MedPAC, *Report to the Congress*, June 2023, ch. 2, p. 7 |
| Manufacturer rebates as a share of gross Part D spending | 23% (2021) | MedPAC, same chapter, p. 12 |
| US brand prices vs 33 OECD countries, gross | 422% (2022 data) | RAND RR-A788-3 / ASPE, *International Prescription Drug Price Comparisons: Estimates Using 2022 Data*, Feb 2024, p. v |
| …after a 37.2% US gross-to-net adjustment | **308%** | RAND RR-A788-3, p. 19 |
| US unbranded generics vs the same countries | 67% — cheaper | RAND RR-A788-3, p. v |

## 5. Outturn

*(appended in the lane's final commit)*
