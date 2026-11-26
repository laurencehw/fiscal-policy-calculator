# Sealed Battery Diagnostics: Ordinary-Income Linearity (Finding 1) and Large Capital-Gains Hike Understatement (Finding 3)

**Date:** 2026-11-26
**Context:** First scoring of `fiscal_model/validation/sealed.py` (`planning/lanes/REVIEW_sealed_battery.md`) against four Tax Foundation *Options 3.0* (July 2026) rate options.
**Action taken on code:** **None** for either finding. Finding 2 (the capital-gains top-rate cut crash) is fixed separately in `planning/lanes/REVIEW_cg_top_bracket_scope.md`.

---

## Finding 1: Ordinary-income rate path is linear in the point change

### Observation

On the top ordinary-income bracket (bracket 7, FY2027–2036, post-P.L. 119-21 `cbo_feb_2026` baseline):

| Sealed row | Rate change | Tax Foundation (CY2027–2036) | Model (FY2027–2036) | Model yield / pt | Error |
|---|---:|---:|---:|---:|---:|
| `tf3_opt1_top_rate_35` | `-2pp` (`37% → 35%`) | `+$625.3B` (`$312.7B/pt`) | `+$230.1B` | `$115.05B/pt` | `63.2%` |
| `tf3_opt4_top_rate_50` | `+13pp` (`37% → 50%`) | `-$1,603.8B` (`$123.4B/pt`) | `-$1,495.8B` | `$115.06B/pt` | `6.7%` |

### Code audit of Lane SSG (`fiscal_model/behavioral_weight.py`, `TaxPolicy.estimate_behavioral_offset`)

1. **Textbook implementation, no coding bug.** `fiscal_model/behavioral_weight.py` implements Saez, Slemrod, and Giertz (2012, *Journal of Economic Literature* 50(1), eq. 3) literally:
   $$w = \frac{\tau_0}{1 - \tau_0} \cdot a, \qquad a = \frac{z_m}{z_m - z^*},$$
   where $\tau_0$ is the **old (pre-reform) statutory marginal rate** read from CBO pub. 53724 (`cbo_tax_parameters.ordinary_rate`), and $a$ is the Pareto parameter read from IRS SOI Table 1.1/1.2 (`mean_income / (mean_income - threshold)`).
2. `TaxPolicy.estimate_behavioral_offset(static_effect)` returns `static_effect * eti * w`, so the net revenue ratio $1 - e \cdot w$ is constant across rate changes on the same bracket and net revenue is strictly linear and symmetric in `rate_change` (which `tests/test_scoring.py` also pins explicitly).
3. Evaluating $\tau_0 / (1 - \tau_0)$ at the pre-reform rate is the exact local first-order approximation in Saez, Slemrod, and Giertz (2012, eq. 3) for small $d\tau$:
   $$dR = N (z_m - z^*) \left(1 - e \cdot a \cdot \frac{\tau_0}{1 - \tau_0}\right) d\tau.$$

### Does switching to exact finite-change log net-of-tax asymmetry explain the gap?

No — in fact, it moves the battery **in the wrong direction overall** and explains less than 2% of the `-2pp` gap.

Under an iso-elastic taxable income response $z_1 = z_0 \left(\frac{1-\tau_1}{1-\tau_0}\right)^e$ (equivalently $\Delta \ln z = e \cdot [\ln(1-\tau_1) - \ln(1-\tau_0)]$), the behavioral revenue change is $\tau_1 (z_1 - z_0)$ per dollar of total income $z_0$ (with Pareto scaling $a = z_m / (z_m - z^*)$). Expressing behavioral erosion as a share of the static revenue change $(\tau_1 - \tau_0)(z_m - z^*)$ gives the exact finite-change erosion fraction:
$$\text{erosion}_{\text{exact}}(\tau_0 \to \tau_1) = a \cdot \frac{\tau_1}{\tau_1 - \tau_0} \left[1 - \left(\frac{1-\tau_1}{1-\tau_0}\right)^e\right].$$

Evaluating at the top bracket ($\tau_0 = 0.37$, $e = 0.25$, $a \approx 1.53$, so linear SSG erosion is $0.25 \times \frac{0.37}{0.63} \times a = 0.1468\,a \approx 22.5\%$):

| Reform | Linear SSG erosion | Exact iso-elastic erosion | Implied model 10-yr score | Tax Foundation | Effect on gap |
|---|---:|---:|---:|---:|---|
| `-2pp` (`37% → 35%`) | `0.1468 a` (`22.5%`) | `0.1373 a` (`21.0%`) | `~+$235B` (vs `+$230.1B`) | `+$625.3B` | Closes `<$5B` (`<1.3%`) of the `$395B` gap |
| `+13pp` (`37% → 50%`) | `0.1468 a` (`22.5%`) | `0.2159 a` (`33.0%`) | `~-$1,293B` (vs `-$1,495.8B`) | `-$1,603.8B` | Worsens error from `6.7%` to `~19.4%` |

### Decisive base check: why `-2pp` misses by `$395B`

Even with **zero behavioral offset** ($e = 0$), the model's entire static ordinary taxable income base above the top bracket floor (single `$657,025`, joint `$788,400` in 2027) yields only `~$148–150B` per percentage point over FY2027–2036, or **`~$297B` static for `-2pp`** — less than half of Tax Foundation's `+$625.3B` (`$312.7B/pt`).

That proves the `-2pp` gap is **not** an SSG behavioral-offset bug. Instead, Tax Foundation's Option 1 (`37% → 35%`, `+$625.3B`) yields **`2.54×` as much per point** as Tax Foundation's own Option 4 (`37% → 50%`, `-$1,603.8B`, `$123.4B/pt`):

- Part of Tax Foundation's asymmetry reflects a **base/design difference**: Option 1 eliminates the `37%` bracket entirely (collapsing it into `35%`) and interacts with pass-through/Section 199A, AMT, and Tax Foundation's microsimulation filing-unit income distribution, whereas a `+13pp` hike to `50%` faces much steeper behavioral/shifting responses (including C-corp/pass-through recharacterization that a single-parameter `e = 0.25` ETI does not capture) plus the 2027–2036 baseline details.
- For our model, `behavioral_weight.py` correctly implements textbook Saez, Slemrod, and Giertz (2012) eq. 3 with no defect. Replacing the local formula with finite-change log net-of-tax rates would leave `tf3_opt1_top_rate_35` 62% off while tripling the error on `tf3_opt4_top_rate_50`.

**Verdict for Finding 1:** Change nothing in `fiscal_model/behavioral_weight.py` or `TaxPolicy`. Keep both ordinary-income rows live in `sealed.py`.

---

## Finding 3: Large capital-gains rate hike is understated (`tf3_opt8_cg_top_rate_30`)

### Observation and static/behavioral decomposition

`tf3_opt8_cg_top_rate_30` scores a `+10pp` increase in the top preferential capital-gains and qualified-dividends rate (`20% → 30%`, or `23.8% → 33.8%` with the 3.8% NIIT, step-up in basis retained) above `$613,700` over FY2027–2036. Tax Foundation scores **`-$362.5B`**; the model scores **`-$59.0B`** before the bracket-scope fix (and **`~-$24B`** once the out-of-scope `0%` and `15%` brackets are excluded in `REVIEW_cg_top_bracket_scope`).

Decomposing the 10-year conventional score (TY2023 SOI base grown at `5.8%/yr`, cumulative 10-year projection multiplier `16.36×` across FY2027–2036):

| Decomposition (deficit sign: `-` raises revenue) | Pre-fix (all brackets, `$762.8B` base) | Post-bracket-scope fix (`20%` bracket only, `$672.1B` base) |
|---|---:|---:|
| Static 10-year effect | `-$1,248.1B` | `-$1,099.6B` |
| Behavioral realization offset | `+$1,189.1B` (**95.3%** of static) | `+$1,075.8B` (**97.8%** of static) |
| **Net conventional 10-year score** | **`-$59.0B`** | **`~-$24B`** |
| Year-0 transitory retiming effect (`t=0`) | `~+$70B` (loses revenue in yr 0) | `~+$77B` (loses revenue in yr 0) |
| Years 1–9 persistent + stock-drift effect | `~-$129B` | `~-$101B` |
| Tax Foundation published score | `-$362.5B` | `-$362.5B` |

**Share of the gap due to the realization response: essentially 100% (more than 100% of the gap relative to static).**
Static revenue (`-$1,100B` to `-$1,248B`) is **3× larger** than Tax Foundation's `-$362.5B`. Tax Foundation's net score implies an overall behavioral offset of roughly **67%** of our post-fix static revenue (`~$737B` offset on `$1,100B` static), whereas the model's frozen elasticities offset **95–98%** of static revenue.

### Why the model offsets 95–98% of static revenue

Under the semi-log realization function $R(\tau) = B e^{-b\tau}$ with frozen Dowd, McClelland, and Muthitacharoen (2015, *NTJ* 68(3)) elasticities ($\varepsilon_p = -0.72$ persistent and $\varepsilon_t = -1.20$ transitory at reference rate $\tau_{\text{ref}} = 0.22$, locked under Owner Decision 3 in `planning/lanes/L1_capital_gains.md`):

1. **Crossing the revenue-maximizing rate.** The persistent semi-log slope is $b = 0.72 / 0.22 = 3.273$, which puts the semi-log revenue-maximizing combined rate at $\tau^* = 1/b = 30.56\%$. Moving the top bracket from `23.8%` to `33.8%` pushes the rate **above the peak** (`30.56%`): in years 1–9 without stock accumulation, $0.338 \cdot e^{-3.273 \times 0.10} = 0.2437$ vs baseline $0.2380$, leaving only `+$0.57` cents of persistent revenue per dollar of baseline realizations (roughly `-$58B` over 9 years, rising to `~-$101B` once deferred gains accumulate in the accrued-gains stock).
2. **Enactment-year transitory retiming loss.** In year 0, adding the transitory term on the `93.2%` long-term-gain timing margin gives $b_0 = (0.72 + 1.20 \times 0.9317)/0.22 = 8.355$, collapsing year-0 realizations by `56.6%` (`e^{-0.8355} = 0.434`) and producing a **`+$77B` year-0 revenue loss** (taxpayers realizing early ahead of the hike or deferring sharply in year 1) that wipes out three-quarters of the `-$101B` raised in years 1–9.

### Comparison across published elasticity ranges

Every major published elasticity estimate cited in `planning/lanes/L1_capital_gains.md` and CRS R48562 yields a sharply different score on a `+10pp` hike with step-up retained (`23.8% → 33.8%`, `$672.1B` 20%-bracket base, FY2027–2036):

| Literature source | Persistent elasticity (at 22%) | Semi-log $b$ | Revenue-max rate $\tau^* = 1/b$ | Approx. 10-yr score on post-fix base (incl. yr0 transitory) |
|---|---:|---:|---:|---:|
| **DMM (2015) / Treasury OTA** *(model default)* | `-0.72` | `3.27` | `30.6%` | `~-$24B` |
| **JCT** (CRS R48562, p. 8) | `-0.68` | `3.10` | `32.3%` | `~-$68B` |
| **Agersnap & Zidar (2021, *AER: Insights*) — upper** | `-0.50` | `2.27` | `44.0%` | `~-$285B` (`~-$360B` if no yr0 dip) |
| **Implied by Tax Foundation (`-$362.5B`) on our base** | `~-0.42 to -0.46` | `~1.9–2.1` | `~48–52%` | `-$362.5B` |
| **Agersnap & Zidar (2021, *AER: Insights*) — lower** | `-0.30` | `1.36` | `73.3%` | `~-$546B` |

*(Tax Foundation's own *Taxes and Growth* model uses a lower long-run realization elasticity around `-0.5` to `-0.6` and models dividends separately without a sharp full-year `-1.20` enactment-year plunge, placing its `-$362.5B` squarely inside the Agersnap & Zidar range and far from the DMM/JCT/Treasury peak.)*

### Why the 44-row Tier 1 battery never exposed this

None of the six capital-gains rows in `preregistered.py` tests a large rate hike **while step-up in basis is retained**:

- All four CBO Option 47 / R3 rows test **`+2pp`** (`23.8% → 25.8%`), which stays well below DMM's `30.6%` peak.
- Both Biden / Treasury Green Book **`+19.6pp`** rows (`biden_capital_gains_39`, `treasury_capgains_39_plus_stepup_elim`) **eliminate step-up at death**, which divides $b$ by the `1.44×` lock-in wedge (`b = 2.27`, raising $\tau^*$ to `44.1%`) and adds the gains-at-death channel.
- `cbo_opt51_gains_at_death` has `rate_change = 0`.

Only the LOO/reconstruction row `pwbm_39_with_stepup` tests a large rate rise with step-up retained — and there PWBM's own score (`+$33B` deficit, i.e., losing revenue at `43.4%`) agrees in sign with DMM's `30.6%` peak, precisely because PWBM and Treasury sit at the high-elasticity end of the literature while Tax Foundation and Agersnap & Zidar sit at the lower-elasticity end.

**Verdict for Finding 3:** Pure literature-parameter disagreement (`-0.72` DMM/Treasury vs `~-0.45` to `-0.50` Agersnap-Zidar/TF), not a code defect. Leave `persistent_elasticity = 0.72` and `transitory_elasticity = 1.20` frozen per Owner Decision 3. Keep `tf3_opt8_cg_top_rate_30` live in `sealed.py` (recording its post-fix move in `REVIEW_cg_top_bracket_scope.md`).
