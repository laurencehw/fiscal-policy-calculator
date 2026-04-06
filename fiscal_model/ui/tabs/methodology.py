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

    # ── Capital gains ────────────────────────────────────────────────────
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

    st_module.markdown("""
| Policy | Official score | Model score | Error | Source |
|--------|---------------|-------------|-------|--------|
| TCJA Full Extension | \\$4,600B | \\$4,582B | 0.4% | CBO |
| Biden Corporate 28% | -\\$1,347B | -\\$1,397B | 3.7% | Treasury |
| Biden CTC 2021 | \\$1,600B | \\$1,743B | 8.9% | JCT |
| Estate: Biden Reform | -\\$450B | -\\$496B | 10.1% | Treasury |
| SS Donut Hole \\$250K | -\\$2,700B | -\\$2,371B | 12.2% | CBO |
| Repeal Corporate AMT | \\$220B | \\$220B | 0.0% | CBO |
| Cap Employer Health | -\\$450B | -\\$450B | 0.1% | JCT |
| Biden \\$400K+ Surtax | -\\$252B | -\\$250B | ~1% | Treasury |
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
        "6. **2-year data lag** — IRS SOI data is from 2022; taxpayer "
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
