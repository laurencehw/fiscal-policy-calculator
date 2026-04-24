"""
Methodology tab renderer — in-app documentation of how the calculator works.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.ui.helpers import TEXTBOOK_LINKS


def render_methodology_tab(st_module: Any) -> None:
    """
    Render a comprehensive methodology page explaining the scoring approach,
    data sources, parameters, and validation results.
    """
    st_module.header("How This Calculator Works")
    st_module.markdown(
        "This tool estimates the 10-year budgetary impact of U.S. fiscal policy "
        "proposals using the same three-stage framework employed by the "
        "Congressional Budget Office (CBO)."
    )

    # ── Scoring overview ─────────────────────────────────────────────────
    st_module.subheader("Three-stage scoring")

    col1, col2, col3 = st_module.columns(3)
    with col1:
        st_module.markdown(
            "**1. Static score**\n\n"
            "Direct revenue effect of the rate or policy change, holding "
            "taxpayer behavior constant.\n\n"
            "*Formula:*  \n"
            "`Revenue = Rate change x Marginal income x Taxpayers`\n\n"
            "Only income *above* the threshold is affected — a filer earning "
            "\\$500K with a \\$400K threshold has \\$100K of marginal income."
        )
    with col2:
        st_module.markdown(
            "**2. Behavioral adjustment**\n\n"
            "Taxpayers respond to rate changes — working less, shifting income, "
            "or deferring capital gains. This *dampens* the static estimate.\n\n"
            "*Formula:*  \n"
            "`Offset = Static effect x ETI x 0.5`\n\n"
            "The Elasticity of Taxable Income (ETI) is the key parameter. "
            "Default: **0.25** ([Saez et al. 2012]"
            "(https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))."
        )
    with col3:
        st_module.markdown(
            "**3. Dynamic feedback** *(optional)*\n\n"
            "Tax and spending changes affect GDP, which feeds back into "
            "revenue. Uses FRB/US-calibrated multipliers from the Federal "
            "Reserve.\n\n"
            "*Channels:*  \n"
            "- GDP growth/contraction  \n"
            "- Employment (Okun's Law)  \n"
            "- Crowding out (interest rates)  \n"
            "- Revenue feedback (marginal rate 0.25)"
        )

    # ── Data sources ─────────────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Data sources")

    d1, d2, d3 = st_module.columns(3)
    with d1:
        st_module.markdown(
            "**IRS Statistics of Income**\n\n"
            "Tables 1.1 and 3.3 provide taxpayer counts, income, and tax "
            "liability by AGI bracket. Used to auto-populate affected "
            "filers and average income.\n\n"
            "*Years available:* 2021, 2022  \n"
            "*Source:* [irs.gov/statistics](https://www.irs.gov/statistics/"
            "soi-tax-stats-individual-income-tax-statistics)"
        )
    with d2:
        st_module.markdown(
            "**FRED Economic Data**\n\n"
            "Nominal GDP and macroeconomic indicators from the St. Louis "
            "Federal Reserve. Cached locally with 30-day refresh.\n\n"
            "*Source:* [fred.stlouisfed.org](https://fred.stlouisfed.org)"
        )
    with d3:
        st_module.markdown(
            "**CBO Baseline Projections**\n\n"
            "10-year revenue, spending, and deficit projections under "
            "current law. Forms the baseline against which all policy "
            "changes are measured.\n\n"
            "*Source:* [CBO Budget and Economic Outlook, Feb 2026]"
            "(https://www.cbo.gov/topics/budget)"
        )

    # ── Key parameters ───────────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Key parameters and their sources")

    st_module.markdown(
        "Every parameter in the model is drawn from peer-reviewed research "
        "or official government estimates. All are adjustable."
    )

    st_module.markdown("""
| Parameter | Default | Source | Used for |
|-----------|---------|--------|----------|
| Elasticity of Taxable Income (ETI) | 0.25 | Saez, Slemrod & Giertz (2012) | Income tax behavioral response |
| Capital gains elasticity (short-run) | 0.8 | CBO (2012) | Years 1-3 realizations response |
| Capital gains elasticity (long-run) | 0.4 | Dowd, McClelland, Muthitacharoen (2015) | Years 4+ realizations response |
| Spending multiplier (Year 1) | 1.4 | FRB/US model | GDP effect of spending changes |
| Tax multiplier (Year 1) | 0.7 | FRB/US model | GDP effect of tax changes |
| Multiplier decay rate | 0.75/year | FRB/US calibration | How quickly fiscal effects fade |
| Okun's Law coefficient | 0.5 | Ball, Leigh & Loungani (2017) | GDP-to-employment conversion |
| Marginal revenue rate | 0.25 | CBO | Revenue feedback from GDP growth |
| Crowding out rate | 15% | Estimated from literature | Interest rate offset of deficits |
| Labor share of output | 0.65 | BLS | Long-run production function |
| Corporate tax incidence | 75/25 capital/labor | CBO/TPC | Distributional analysis |
| Step-up lock-in multiplier | 2.0 | Calibrated to PWBM | Capital gains deferral incentive |
""")

    # ── Worked examples ──────────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Worked Examples")
    st_module.markdown(
        "The following examples trace the exact arithmetic behind three common "
        "policy types — the same calculations the calculator performs under the "
        "hood. Numbers come from IRS Statistics of Income, the CBO Feb 2026 "
        "baseline, and the calibrated parameters above."
    )

    # ── Example 1: Income tax rate change ────────────────────────────────
    with st_module.expander(
        "Example 1 — Income tax rate increase on high earners ($400K+ threshold, 2.6 pp)"
    ):
        st_module.markdown(
            "This replicates the scoring of a Biden-style top-rate surtax — "
            "a 2.6 percentage-point increase on taxable income above \\$400,000. "
            "The official Treasury estimate for a comparable proposal is **\\$252B** "
            "in 10-year deficit reduction."
        )

        st_module.markdown("#### Step 1 — Static revenue estimate")
        st_module.markdown(
            "The static score holds taxpayer behavior fixed and asks: *how much "
            "revenue does the mechanical rate change generate?*  \n"
            "Only income **above** the threshold is taxed at the new rate:"
        )
        st_module.latex(
            r"\Delta R_{\text{static}} = \Delta\tau \;\times\; (\bar{Y} - T) \;\times\; N"
        )
        st_module.markdown(
            r"where $\Delta\tau$ is the rate change, $T$ is the income threshold, "
            r"$\bar{Y}$ is the average taxable income among affected filers, "
            r"and $N$ is the number of filers above the threshold."
            "\n\n**From IRS SOI (Table 1.1):**"
        )
        st_module.markdown(r"""
| Variable | Value | Source |
|----------|-------|--------|
| Rate change (Δτ) | 0.026 (2.6 pp) | Policy |
| Threshold (*T*) | \$400,000 | Policy |
| Avg. taxable income above threshold (*Ȳ*) | ~\$950,000 | IRS SOI |
| Marginal income per filer (*Ȳ* − *T*) | \$550,000 | Derived |
| Filers above threshold (*N*) | ~1.8 million | IRS SOI |
""")
        st_module.markdown("**Year 1 static revenue:**")
        st_module.latex(
            r"\Delta R_1 = 0.026 \times \$550{,}000 \times 1{,}800{,}000 "
            r"= \$25.7\text{ B}"
        )
        st_module.markdown(
            "Taxable income at this bracket grows roughly 3% per year alongside "
            "the CBO income baseline. Summing over 10 years:"
        )
        st_module.latex(
            r"\Delta R_{\text{10yr}}^{\text{static}} "
            r"= \sum_{t=1}^{10} \$25.7\text{B} \times (1.03)^{t-1} "
            r"\approx \$295\text{ B}"
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 2 — Behavioral offset (ETI)")
        st_module.markdown(
            "High-income filers reduce reported taxable income when marginal "
            "rates rise — through reduced hours, income shifting to corporate "
            "form, or increased deductions. The model quantifies this using the "
            "**Elasticity of Taxable Income (ETI)**:"
        )
        st_module.latex(
            r"\varepsilon_{TI} \;=\; \frac{\partial \ln TI}{\partial \ln(1-\tau)}"
        )
        st_module.markdown(
            r"which says: a 1% decrease in the net-of-tax rate $(1-\tau)$ "
            r"causes taxable income to fall by $\varepsilon_{TI}$ percent. "
            "The model's behavioral offset uses a simplified CBO/JCT convention:"
        )
        st_module.latex(
            r"\Delta R_{\text{behavioral}} "
            r"= -\varepsilon_{TI} \times 0.5 \times \Delta R_{\text{static}}"
        )
        st_module.markdown(
            "The factor of 0.5 reflects that the behavioral response phases in "
            "gradually — taxpayers cannot immediately restructure income — so "
            "only half the steady-state response materializes on average across "
            "the 10-year window (a CBO/JCT convention for conventional scoring). "
            "With ETI = 0.25:"
        )
        st_module.latex(
            r"\Delta R_{\text{behavioral}} "
            r"= -0.25 \times 0.5 \times \$295\text{B} "
            r"= -\$36.9\text{B}"
        )
        st_module.markdown(
            "> **Intuition check:** The behavioral offset is about 12.5% of the "
            "static score. This is a *modest* offset — ETI estimates for "
            "high-income filers range 0.15–0.50 across studies, and our default "
            "of 0.25 is the Saez et al. (2012) central estimate."
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 3 — Final 10-year score")
        st_module.latex(
            r"\Delta R_{\text{final}} "
            r"= \Delta R_{\text{static}} + \Delta R_{\text{behavioral}} "
            r"= \$295\text{B} - \$36.9\text{B} "
            r"\approx \$258\text{B}"
        )
        st_module.markdown(
            "**Official Treasury estimate: \\$252B** — model is within ~2%.  \n\n"
            "Uncertainty range (CBO-style, 10-year): roughly **\\$200B to \\$320B**, "
            "reflecting ETI uncertainty (0.15–0.40) and baseline forecast risk."
        )

        st_module.markdown("---")
        st_module.markdown("#### What changes with dynamic scoring?")
        st_module.markdown(
            "A tax increase reduces after-tax income, dampening consumer "
            "spending. Using the FRB/US tax multiplier (−0.7, year 1):"
        )
        st_module.latex(
            r"\Delta\text{GDP}_1 \approx -0.7 \times \frac{\$25.7\text{B}}{\text{GDP}} "
            r"\times \text{GDP} = -\$18\text{B}"
        )
        st_module.markdown(
            "Revenue feedback (25% of GDP change) partially offsets this: "
            "\\$0.25 \\times \\$18\\text{B} = \\$4.5\\text{B} per year flowing "
            "back to the Treasury. The net dynamic effect on deficit reduction is "
            "smaller than the conventional score — a higher-rate policy raises "
            "less revenue than static scoring implies once growth effects are included."
        )

    # ── Example 2: TCJA Extension ─────────────────────────────────────────
    with st_module.expander(
        "Example 2 — TCJA full extension (2026–2035, all provisions)"
    ):
        st_module.markdown(
            "The Tax Cuts and Jobs Act (2017) cut individual and corporate taxes "
            "substantially. Most individual provisions expire after 2025; extending "
            "them is the dominant fiscal policy question of the decade. "
            "**CBO scores the full extension at \\$4,600B** over 2026–2035."
        )
        st_module.markdown(
            "Unlike a simple rate change, TCJA cannot be scored with a single "
            "formula. The model uses **component-based costing** — each provision "
            "is scored independently, then calibrated to CBO."
        )

        st_module.markdown("#### Step 1 — Component-level costs")
        st_module.markdown(
            "Eight major provisions drive the cost. Each is scored using its "
            "own formula, then summed:"
        )
        st_module.markdown(r"""
| Provision | 10-yr raw cost | Formula type |
|-----------|---------------|--------------|
| Individual rate cuts (7 brackets lowered) | \$1,800 B | ΔRate × bracket income × filers |
| Standard deduction doubled (\$13K → \$26K) | \$720 B | Deduction × marginal rate × switchers |
| Pass-through deduction (Sec. 199A, 20%) | \$700 B | Deduction × pass-through income × rate |
| Child Tax Credit expanded (\$1K → \$2K) | \$550 B | ΔCredit × eligible children |
| AMT relief (raised exemption + phaseout) | \$450 B | AMT liability × affected filers |
| Estate tax relief (doubled exemption) | \$130 B | Estate flows × exemption change |
| SALT cap (\$10K limit) — revenue *offset* | −\$1,100 B | Lost deductions × marginal rate |
| Eliminate personal exemptions — revenue *offset* | −\$650 B | Exemptions × rate × filers |
| **Raw total** | **\$2,600 B** | |
""")
        st_module.markdown(
            "> **Why does the raw total (\\$2,600B) differ so much from CBO (\\$4,600B)?**  \n"
            "The simplified component model uses bracket-level IRS data without "
            "full microsimulation. It misses interaction effects, the detailed "
            "distributional nuance of actual filer data, and second-order behavioral "
            "responses already embedded in CBO's methodology. The calibration "
            "factor closes this gap."
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 2 — Calibration to CBO")
        st_module.markdown(
            "To ensure the full-extension score matches the official CBO figure, "
            "each component is scaled by a single calibration factor:"
        )
        st_module.latex(
            r"\kappa = \frac{\text{CBO target}}{\text{Raw model total}} "
            r"= \frac{\$4{,}600\text{B}}{\$2{,}600\text{B}} \approx 1.77"
        )
        st_module.markdown(
            "Every component cost is multiplied by \\$\\kappa = 1.77 before "
            "display and before partial-extension calculations."
        )
        st_module.latex(
            r"\text{Component}_{\text{calibrated}} = \kappa \times \text{Component}_{\text{raw}}"
        )
        st_module.markdown("For example, the calibrated cost of rate cuts alone:")
        st_module.latex(
            r"\$1{,}800\text{B} \times 1.77 = \$3{,}186\text{B}"
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 3 — Behavioral offset treatment")
        st_module.markdown(
            "Unlike a standard income tax change, **no separate behavioral offset "
            "is applied to TCJA**. The CBO $4,600B estimate already reflects "
            "CBO's conventional scoring methodology, which includes behavioral "
            "responses consistent with the ETI literature. Applying an additional "
            "ETI offset would double-count."
        )
        st_module.latex(
            r"\Delta R_{\text{TCJA, final}} = \kappa \times \sum_i C_i "
            r"= 1.77 \times \$2{,}600\text{B} \approx \$4{,}582\text{B}"
        )
        st_module.markdown(
            "**Official CBO estimate: \\$4,600B** — model error is **0.4%**.  \n\n"
            "This tight match is by design: the calibration factor is set once "
            "against the CBO full-extension score, then held fixed for all "
            "partial-extension calculations."
        )

        st_module.markdown("---")
        st_module.markdown("#### Partial extensions")
        st_module.markdown(
            "The calibration approach lets users extend individual provisions. "
            "Repealing the SALT cap (adding back \\$1,100B raw × 1.77):"
        )
        st_module.latex(
            r"\text{No SALT cap} = \$4{,}582\text{B} + 1.77 \times \$1{,}100\text{B} "
            r"= \$4{,}582\text{B} + \$1{,}947\text{B} \approx \$6{,}529\text{B}"
        )
        st_module.markdown(
            "*(Consistent with independent estimates that full TCJA extension "
            "without the SALT cap costs roughly \\$6.5T.)*"
        )

    # ── Example 3: Capital gains ──────────────────────────────────────────
    with st_module.expander(
        "Example 3 — Capital gains rate increase with step-up basis (time-varying elasticity)"
    ):
        st_module.markdown(
            "Capital gains are taxed only when *realized* — investors can defer "
            "indefinitely by holding assets. This makes capital gains uniquely "
            "sensitive to rate changes in the short run (timing effects) while "
            "the long-run response is more muted. Step-up basis at death amplifies "
            "the lock-in even further."
        )
        st_module.markdown(
            "**Example:** Raise the top long-term capital gains rate from 23.8% "
            "to 28.0% on gains above \\$1M (a common Biden-era proposal)."
        )

        st_module.markdown("#### Step 1 — Baseline and static estimate")
        st_module.markdown(
            "From IRS SOI, total long-term capital gains realizations "
            "by filers above the $1M AGI threshold:"
        )
        st_module.markdown(r"""
| Variable | Value | Source |
|----------|-------|--------|
| Baseline realizations (*R*₀) | ~\$500 B/yr | IRS SOI, calibrated |
| Baseline rate (τ₀) | 23.8% (20% + 3.8% NIIT) | Current law |
| New rate (τ₁) | 28.0% | Policy |
| Rate change (Δτ) | 4.2 pp = 0.042 | Derived |
""")
        st_module.markdown("Year 1 static (ignoring behavioral):")
        st_module.latex(
            r"\Delta R_{\text{static}} = \Delta\tau \times R_0 "
            r"= 0.042 \times \$500\text{B} = \$21\text{B}"
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 2 — Time-varying elasticity")
        st_module.markdown(
            "Investors *time* realizations. When a rate increase is announced, "
            "many sell immediately to lock in the old rate — boosting short-run "
            "realizations but pulling them forward from future years. The model "
            "captures this with a **time-varying elasticity** that transitions "
            "from a high short-run value to a lower long-run value:"
        )
        st_module.latex(
            r"\varepsilon(t) = \begin{cases} "
            r"\varepsilon_{\text{SR}} = 0.8 & t \leq 3 \text{ (timing/anticipation)} \\ "
            r"\varepsilon_{\text{LR}} = 0.4 & t > 3 \text{ (permanent response)} "
            r"\end{cases}"
        )
        st_module.markdown(
            "Realized gains in year *t* are modeled as:"
        )
        st_module.latex(
            r"R_t = R_0 \times \left(\frac{1 - \tau_1}{1 - \tau_0}\right)^{\varepsilon(t) \;\times\; \lambda}"
        )
        st_module.markdown(
            r"where $\lambda$ is the **step-up lock-in multiplier**. Under current "
            r"law, unrealized gains are forgiven at death — so investors can avoid "
            r"the tax entirely by holding until death. This makes the effective "
            r"elasticity much larger: $\lambda = 2.0$ when step-up exists, "
            r"$\lambda = 1.0$ when it is eliminated."
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 3 — Year-by-year calculation")
        st_module.markdown(
            "**With step-up basis (current law), Year 1** ($\\varepsilon(1) = 0.8$, $\\lambda = 2.0$):"
        )
        st_module.latex(
            r"\varepsilon_{\text{eff}} = 0.8 \times 2.0 = 1.6"
        )
        st_module.latex(
            r"\frac{1-\tau_1}{1-\tau_0} = \frac{0.720}{0.762} = 0.9449"
        )
        st_module.latex(
            r"R_1 = \$500\text{B} \times (0.9449)^{1.6} "
            r"= \$500\text{B} \times 0.913 = \$456.7\text{B}"
        )
        st_module.markdown("Net revenue raised in year 1:")
        st_module.latex(
            r"\Delta\text{Rev}_1 = \tau_1 R_1 - \tau_0 R_0 "
            r"= 0.280 \times \$456.7\text{B} - 0.238 \times \$500\text{B} "
            r"= \$127.9\text{B} - \$119.0\text{B} = \$8.9\text{B}"
        )
        st_module.markdown(
            "The *static* estimate was \\$21B, but only \\$8.9B materializes — "
            "the behavioral offset absorbs **57%** of the static score in year 1. "
            "Investors are accelerating realizations *before* the rate takes effect "
            "and deferring them *after*."
        )

        st_module.markdown(
            "**Year 4+ (long-run)** ($\\varepsilon(4) = 0.4$, $\\lambda = 2.0$):"
        )
        st_module.latex(
            r"\varepsilon_{\text{eff}} = 0.4 \times 2.0 = 0.8"
        )
        st_module.latex(
            r"R_4 = \$500\text{B} \times (0.9449)^{0.8} "
            r"= \$500\text{B} \times 0.956 = \$477.8\text{B}"
        )
        st_module.latex(
            r"\Delta\text{Rev}_4 = 0.280 \times \$477.8\text{B} - 0.238 \times \$500\text{B} "
            r"= \$133.8\text{B} - \$119.0\text{B} = \$14.8\text{B}"
        )
        st_module.markdown(
            "The behavioral offset falls to **30%** once timing effects dissipate — "
            "closer to the steady-state elasticity."
        )

        st_module.markdown("---")
        st_module.markdown("#### Step 4 — Effect of eliminating step-up basis")
        st_module.markdown(
            "If step-up basis is eliminated simultaneously (Biden's proposal), "
            "$\\lambda = 1.0$. Year 1 with $\\varepsilon(1) = 0.8$:"
        )
        st_module.latex(
            r"R_1^{\text{no step-up}} = \$500\text{B} \times (0.9449)^{0.8} "
            r"= \$500\text{B} \times 0.956 = \$477.8\text{B}"
        )
        st_module.latex(
            r"\Delta\text{Rev}_1^{\text{no step-up}} = 0.280 \times \$477.8\text{B} - 0.238 \times \$500\text{B} "
            r"= \$14.8\text{B}"
        )
        st_module.markdown(
            "Eliminating step-up raises the year 1 revenue take from **\\$8.9B to "
            "\\$14.8B** — a 66% increase — because investors can no longer avoid "
            "the tax by holding until death, reducing the lock-in incentive."
        )

        st_module.markdown("---")
        st_module.markdown("#### Summary: 10-year scores")
        st_module.markdown(r"""
| Scenario | 10-yr score | Behavioral offset (avg) |
|----------|------------|------------------------|
| Rate ↑ to 28%, step-up retained | ~\$110 B | ~48% of static |
| Rate ↑ to 28%, step-up eliminated | ~\$180 B | ~14% of static |
| Static (no behavioral response) | ~\$210 B | 0% |
""")
        st_module.markdown(
            "> **Key takeaway for public economics:** The revenue effect of a "
            "capital gains rate increase depends *critically* on whether step-up "
            "basis is eliminated simultaneously. A rate hike alone may raise "
            "surprisingly little revenue in the first few years due to lock-in. "
            "This is why Biden's proposal combined both elements."
        )

    # ── Capital gains detail ─────────────────────────────────────────────
    st_module.markdown("---")
    with st_module.expander("Capital gains methodology"):
        st_module.markdown(
            "Capital gains have unique behavioral dynamics. Investors can "
            "**time** when they realize gains, so the short-run response to "
            "rate changes is much larger than the long-run response.\n\n"
            "**Time-varying elasticity:**\n"
            "- Years 1-3: e = 0.8 (timing/anticipation effects dominate)\n"
            "- Years 4+: e = 0.4 (only permanent behavioral response remains)\n"
            "- Transition: linear interpolation over 3 years\n\n"
            "**Step-up basis at death:**\n"
            "Under current law, unrealized gains are forgiven at death. This "
            "creates a *much* stronger lock-in effect (multiplier = 2.0x on "
            "base elasticity) because taxpayers can avoid tax entirely by "
            "holding until death. When step-up is eliminated, the lock-in "
            "multiplier drops to 1.0x.\n\n"
            "**Sources:**\n"
            "- CBO (2012): [How Capital Gains Tax Rates Affect Revenues]"
            "(https://www.cbo.gov/publication/43334)\n"
            "- Dowd et al. (2015): Long-run elasticity estimates\n"
            "- Penn Wharton Budget Model: Step-up basis calibration"
        )

    # ── Dynamic scoring detail ───────────────────────────────────────────
    with st_module.expander("Dynamic scoring methodology"):
        st_module.markdown(
            "Dynamic scoring adds macroeconomic feedback to the conventional "
            "estimate. The model uses an **FRB/US-calibrated adapter** — "
            "multipliers calibrated to match the Federal Reserve's FRB/US "
            "macroeconomic model (the same approach used by the Yale Budget "
            "Lab).\n\n"
            "**How it works:**\n"
            "1. Fiscal shock (tax cut or spending increase) enters the economy\n"
            "2. GDP changes by `shock x multiplier`, with multiplier decaying "
            "annually (0.75 decay rate)\n"
            "3. Employment changes via Okun's Law (1% GDP = ~0.5% employment)\n"
            "4. Revenue feedback: 25% of GDP change flows back as tax revenue\n"
            "5. Crowding out: cumulative deficits raise interest rates, "
            "partially offsetting GDP gains\n\n"
            "**State-dependent multipliers:**\n\n"
            "| Economic condition | Spending multiplier | Tax multiplier |\n"
            "|---|---|---|\n"
            "| Normal | 1.0 | 0.5 |\n"
            "| Recession | 1.5 - 2.0 | 0.8 - 1.0 |\n"
            "| At ZLB | 2.0+ | 1.0+ |\n"
            "| Overheating | 0.5 | 0.3 |\n\n"
            "**Sources:**\n"
            "- Auerbach & Gorodnichenko (2012): Recession multipliers\n"
            "- Christiano, Eichenbaum & Rebelo (2011): ZLB effects\n"
            "- Yale Budget Lab: [Dynamic scoring using FRB/US]"
            "(https://budgetlab.yale.edu/research/"
            "dynamic-scoring-using-frbus-macroeconomic-model)"
        )

    # ── Distributional analysis ──────────────────────────────────────────
    with st_module.expander("Distributional analysis methodology"):
        st_module.markdown(
            "The distributional engine estimates how tax changes affect "
            "different income groups, following TPC/JCT conventions.\n\n"
            "**Income groups:**\n"
            "- Quintiles (5 equal-population groups)\n"
            "- Deciles (10 groups)\n"
            "- JCT dollar brackets ($10K increments)\n"
            "- Top income breakout (top 1%, 0.1%)\n\n"
            "**Metrics per group:**\n"
            "- Average tax change ($)\n"
            "- Tax change as % of income\n"
            "- Share of total revenue change\n"
            "- Winners/losers (%)\n"
            "- Effective tax rate change (ppts)\n\n"
            "**Corporate tax incidence** follows CBO/TPC: 75% borne by capital "
            "owners, 25% by workers.\n\n"
            "**Validation:** Distributional shares match TPC TCJA analysis "
            "within 5 percentage points for all quintiles."
        )

    # ── Uncertainty ──────────────────────────────────────────────────────
    with st_module.expander("Uncertainty methodology"):
        st_module.markdown(
            "All estimates include uncertainty ranges that widen over time, "
            "consistent with CBO practice.\n\n"
            "**Base uncertainty:** 10% in year 1, growing by 2pp per year\n\n"
            "**Adjustments:**\n"
            "- Tax policy: 1.2x (revenue more uncertain than spending)\n"
            "- Dynamic scoring: 1.5x (macro models diverge significantly)\n\n"
            "**Asymmetric ranges:** Costs tend to exceed estimates, so the "
            "high estimate uses a 1.1x factor vs 0.9x for the low estimate.\n\n"
            "**Sources of uncertainty:**\n"
            "1. Baseline projections (economy may differ from CBO forecast)\n"
            "2. Behavioral response (ETI estimates range 0.15 to 0.50)\n"
            "3. Dynamic effects (macro models give very different answers)\n"
            "4. Data lag (IRS data is 2 years behind)"
        )

    # ── Validation ───────────────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Validation against official scores")

    st_module.markdown(
        "The model has been validated against 25+ CBO/JCT/Treasury estimates. "
        "All major policies score within 15% of official estimates."
    )

    st_module.markdown(r"""
| Policy | Official score | Model score | Error | Source |
|--------|---------------|-------------|-------|--------|
| TCJA Full Extension | \$4,600B | \$4,582B | 0.4% | CBO |
| Biden Corporate 28% | -\$1,347B | -\$1,397B | 3.7% | Treasury |
| Biden CTC 2021 | \$1,600B | \$1,743B | 8.9% | JCT |
| Estate: Biden Reform | -\$450B | -\$496B | 10.1% | Treasury |
| SS Donut Hole \$250K | -\$2,700B | -\$2,371B | 12.2% | CBO |
| Repeal Corporate AMT | \$220B | \$220B | 0.0% | CBO |
| Cap Employer Health | -\$450B | -\$450B | 0.1% | JCT |
| Biden \$400K+ Surtax | -\$252B | -\$250B | ~1% | Treasury |
""")

    # ── Limitations ──────────────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Known limitations")

    st_module.markdown(
        "1. **No microsimulation** — Uses bracket-level IRS data, not "
        "individual tax returns. This means complex interactions between "
        "provisions (e.g., AMT + SALT + CTC phase-outs) are approximated.\n"
        "2. **Simplified corporate model** — Pass-through income (S-corps, "
        "partnerships) not fully modeled.\n"
        "3. **State interactions are partial** — state modeling currently "
        "covers top states with representative-taxpayer assumptions.\n"
        "4. **Trade module is separate** — tariff scoring is available, but "
        "integration with all policy modules is still evolving.\n"
        "5. **Reduced-form dynamic scoring** — Uses calibrated multipliers "
        "rather than structural general-equilibrium equations.\n"
        "6. **Data lag** — IRS SOI data lags ~2 years; taxpayer "
        "distributions may have shifted."
    )

    # ── Textbook reference ─────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Textbook reference")
    st_module.markdown(
        "This calculator accompanies *Modern Public Economics: Theory, "
        "Evidence, and Policy*. Relevant chapters:\n\n"
        f"- [Optimal Taxation (Ch 16)]({TEXTBOOK_LINKS['optimal_taxation']})"
        " — theory of efficient tax design\n"
        f"- [Personal Income Tax (Ch 18)]({TEXTBOOK_LINKS['income_tax']})"
        " — income tax, labor supply, tax expenditures\n"
        f"- [Corporate Tax (Ch 19)]({TEXTBOOK_LINKS['corporate_tax']})"
        " — corporate tax incidence and reform\n"
        f"- [The Federal Budget (Ch 22)]({TEXTBOOK_LINKS['federal_budget']})"
        " — CBO scoring, reconciliation, budget process\n"
        f"- [Fiscal Sustainability (Ch 25)]"
        f"({TEXTBOOK_LINKS['fiscal_sustainability']})"
        " — deficits, multipliers, debt dynamics"
    )

    # ── References ───────────────────────────────────────────────────────
    st_module.markdown("---")
    with st_module.expander("Full references"):
        st_module.markdown(
            "**Academic literature:**\n\n"
            "1. Saez, E., Slemrod, J., & Giertz, S.H. (2012). \"The Elasticity "
            "of Taxable Income with Respect to Marginal Tax Rates.\" "
            "*Journal of Economic Literature*, 50(1), 3-50.\n"
            "2. Auerbach, A.J., & Gorodnichenko, Y. (2012). \"Measuring the "
            "Output Responses to Fiscal Policy.\" *American Economic Journal: "
            "Economic Policy*, 4(2), 1-27.\n"
            "3. Christiano, L., Eichenbaum, M., & Rebelo, S. (2011). \"When Is "
            "the Government Spending Multiplier Large?\" *Journal of Political "
            "Economy*, 119(1), 78-121.\n"
            "4. Gruber, J., & Saez, E. (2002). \"The Elasticity of Taxable "
            "Income.\" *Journal of Public Economics*, 84(1), 1-32.\n"
            "5. Dowd, T., McClelland, R., & Muthitacharoen, A. (2015). \"New "
            "Evidence on the Tax Elasticity of Capital Gains.\" *National Tax "
            "Journal*, 68(3), 511-544.\n"
            "6. Ball, L., Leigh, D., & Loungani, P. (2017). \"Okun's Law: Fit "
            "at 50?\" *Journal of Money, Credit and Banking*, 49(7).\n\n"
            "**Official methodology documents:**\n\n"
            "7. CBO (2014). \"How CBO Analyzes the Effects of Changes in "
            "Federal Fiscal Policies on the Economy.\"\n"
            "8. JCT (2017). \"Overview of Revenue Estimating Procedures and "
            "Methodologies.\" [jct.gov](https://www.jct.gov/publications/2017/jcx-1-17/)\n"
            "9. Yale Budget Lab. \"Methodology and Documentation.\" "
            "[budgetlab.yale.edu](https://budgetlab.yale.edu/research)\n"
            "10. CBO (2026). \"The Budget and Economic Outlook: 2026 to 2036.\"\n\n"
            "**Data sources:**\n\n"
            "11. IRS Statistics of Income: [irs.gov/statistics]"
            "(https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics)\n"
            "12. Federal Reserve Economic Data: [fred.stlouisfed.org]"
            "(https://fred.stlouisfed.org)"
        )
