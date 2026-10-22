"""Social Security — trust fund reform menu (``/social-security``).

A menu of SSA Office of the Chief Actuary (OCACT) options on the 2026 Trustees
Report baseline, in the spirit of CRFB's Social Security Reformer: pick
options, see the share of the 75-year shortfall closed, the depletion year,
the benefit cut at depletion and the trust fund ratio path.

Every option effect is OCACT's own estimate, transcribed; the repository only
runs the ledger (``fiscal_model/social_security/trust_fund.py``). Options add
without interactions, and the page says so next to the total. A comparison
with CRFB's published figures sits at the bottom. Lane:
``planning/lanes/SS1_trust_fund_page.md``.

Widget keys are ``ss_group_<exclusive_group>`` (a radio per lever that has
alternative settings) and ``ss_opt_<provision_id>`` (a checkbox per stand-alone
option).
"""

from __future__ import annotations

from typing import Any

from components.chrome import render_chrome, render_page_footer
from fiscal_model.social_security import (
    CATEGORY_LABELS,
    Projection,
    Provision,
    load_catalog,
    project,
)
from fiscal_model.social_security.crfb_benchmark import METRIC_LABELS, crfb_comparison
from fiscal_model.social_security.trust_fund import (
    TRUSTEES_ACTUARIAL_BALANCE,
    TRUSTEES_OASDI_PAYABLE_PCT,
    TRUSTEES_OASI_DEPLETION,
    TRUSTEES_OASI_PAYABLE_PCT,
)
from fiscal_model.ui.helpers import escape_markdown_dollars

PAGE_TITLE = "Social Security"
URL_PATH = "social-security"

NO_CHANGE = "No change"

#: Heading over each set of alternative settings of one lever.
GROUP_LABELS: dict[str, str] = {
    "cola": "How the COLA is computed",
    "initial_benefits": "Initial benefit formula",
    "across_the_board": "Benefit level",
    "retirement_age": "Normal retirement age",
    "payroll_rate": "Payroll tax rate increase",
    "taxable_maximum": "Earnings subject to the payroll tax",
    "benefit_taxation": "Income tax on benefits",
}

CRFB_REFORMER_URL = "https://www.crfb.org/socialsecurityreformer/"
OCACT_INDEX_URL = "https://www.ssa.gov/oact/solvency/provisions/index.html"
TRUSTEES_URL = "https://www.ssa.gov/oact/tr/2026/"

TIER_NOTE = (
    "**Transcribed from SSA's Office of the Chief Actuary — not a model "
    "estimate.** Each option's effect is OCACT's own score on the 2026 "
    "Trustees Report baseline. The calculator only runs the trust fund "
    "ledger from those published rates. Options are **added without "
    "interactions**, as in CRFB's Reformer, so a package total is a rough "
    "guide, not a formal score."
)

FRAMING_NOTE = (
    "**Which trust fund?** This page models the combined OASDI funds "
    "(retirement plus disability), which the Trustees project to run out in "
    f"2034 with {TRUSTEES_OASDI_PAYABLE_PCT}% of scheduled benefits payable. "
    f"The retirement fund alone (OASI) runs out sooner, in {TRUSTEES_OASI_DEPLETION}, "
    f"with {TRUSTEES_OASI_PAYABLE_PCT}% payable: a "
    f"{100 - TRUSTEES_OASI_PAYABLE_PCT}% cut. That is the headline CRFB uses, "
    "so the two tools' current-law dates differ by definition, not by disagreement."
)


def _label(provision: Provision) -> str:
    return escape_markdown_dollars(provision.label)


def _render_menu(st_module: Any) -> list[str]:
    """Draw the option menu and return the selected provision ids."""
    catalog = load_catalog()
    selected: list[str] = []
    for category, heading in CATEGORY_LABELS.items():
        members = [p for p in catalog if p.category == category]
        if not members:
            continue
        with st_module.expander(heading, expanded=False):
            groups: dict[str, list[Provision]] = {}
            for p in members:
                if p.exclusive_group:
                    groups.setdefault(p.exclusive_group, []).append(p)
            for group, options in groups.items():
                by_label = {_label(p): p.provision_id for p in options}
                choice = st_module.radio(
                    f"{GROUP_LABELS.get(group, heading)} (choose one)",
                    [NO_CHANGE, *by_label],
                    key=f"ss_group_{group}",
                )
                if choice in by_label:
                    selected.append(by_label[choice])
            for p in members:
                if p.exclusive_group:
                    continue
                if st_module.checkbox(_label(p), key=f"ss_opt_{p.provision_id}"):
                    selected.append(p.provision_id)
    return selected


def _depletion_text(result: Projection) -> str:
    return str(result.depletion_year) if result.depletion_year else "Not before 2100"


def _render_metrics(st_module: Any, plan: Projection, baseline: Projection) -> None:
    c1, c2, c3, c4 = st_module.columns(4)
    c1.metric(
        "75-year shortfall closed",
        f"{plan.share_of_shortfall_closed * 100:.0f}%",
        help=(
            "The plan's change in the 75-year actuarial balance as a share of the "
            f"Trustees' {-TRUSTEES_ACTUARIAL_BALANCE:.2f}% of taxable payroll deficit."
        ),
    )
    delta = None
    if plan.provision_ids and plan.depletion_year and baseline.depletion_year:
        years = plan.depletion_year - baseline.depletion_year
        delta = f"{years:+d} years" if years else "no change"
    c2.metric("Trust funds depleted", _depletion_text(plan), delta=delta)
    cut = plan.benefit_cut_at_depletion
    c3.metric(
        "Benefit cut at depletion",
        "None" if cut is None else f"{cut * 100:.0f}%",
        help="The across-the-board cut needed when reserves run out: 1 − income ÷ cost that year.",
    )
    c4.metric(
        "75-year actuarial balance",
        f"{plan.actuarial_balance:+.2f}%",
        help="Percent of taxable payroll. The Trustees' published balance plus the plan's change.",
    )
    if plan.provision_ids:
        st_module.caption(
            f"Sum of {len(plan.provision_ids)} separately scored OCACT options, "
            "without interactions."
        )


def _render_chart(st_module: Any, plan: Projection, baseline: Projection) -> None:
    import plotly.graph_objects as go

    from fiscal_model.ui.charts import horizontal_legend, theme_figure

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(baseline.years),
            y=list(baseline.trust_fund_ratio),
            name="Current law",
            line={"dash": "dot"},
        )
    )
    if plan.provision_ids:
        fig.add_trace(
            go.Scatter(x=list(plan.years), y=list(plan.trust_fund_ratio), name="Your plan")
        )
    fig.update_layout(
        title="Trust fund ratio: reserves at the start of the year as % of that year's cost",
        yaxis_title="Percent of annual cost",
        height=380,
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
        legend=horizontal_legend(align="right"),
    )
    st_module.plotly_chart(theme_figure(fig), use_container_width=True)


def _render_selection_table(st_module: Any, plan: Projection) -> None:
    if not plan.provision_ids:
        return
    import pandas as pd

    catalog = {p.provision_id: p for p in load_catalog()}
    rows = []
    for pid in plan.provision_ids:
        p = catalog[pid]
        rows.append(
            {
                "OCACT id": pid,
                "Option": p.label,
                "Change in actuarial balance": p.ocact_change_actuarial_balance,
                "Share of shortfall": p.ocact_change_actuarial_balance
                / -TRUSTEES_ACTUARIAL_BALANCE,
                "Depleted (alone)": str(p.ocact_depletion_year or "after 2100"),
                "OCACT table": p.source_url,
            }
        )
    st_module.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Change in actuarial balance": st_module.column_config.NumberColumn(format="%+.2f"),
            "Share of shortfall": st_module.column_config.NumberColumn(format="percent"),
            "OCACT table": st_module.column_config.LinkColumn(display_text="table"),
        },
    )


def _render_crfb_comparison(st_module: Any) -> None:
    import pandas as pd

    st_module.markdown("### How this compares with CRFB")
    st_module.markdown(
        f"CRFB's [Social Security Reformer]({CRFB_REFORMER_URL}) does not publish "
        "its option figures as a table, so the comparison uses the numbers CRFB "
        "states in its posts. Gaps are reported, not tuned away. CRFB's option "
        "figures rest on the 2025 Trustees Report, whose 75-year deficit was "
        "smaller than 2026's, so the same option closes a larger share there."
    )
    rows = [
        {
            "CRFB item": r.crfb_item,
            "Measure": METRIC_LABELS[r.metric] + (" (OASI)" if r.framing == "oasi" else ""),
            "CRFB": r.display(r.crfb_value, ours=False),
            "This page": r.display(r.our_value, ours=True),
            "Our basis": r.our_basis,
            "Why they may differ": r.note,
            "Source": r.source_url,
        }
        for r in crfb_comparison()
    ]
    st_module.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={"Source": st_module.column_config.LinkColumn(display_text="CRFB")},
    )


def _render_method(st_module: Any) -> None:
    with st_module.expander("How the ledger works", expanded=False):
        st_module.markdown(
            f"- **Baseline:** income and cost rates from the [2026 Trustees Report]({TRUSTEES_URL}) "
            "(Table IV.B1), taxable payroll and the trust fund interest factor from Table VI.G1, "
            "reserves at the end of 2025 from Table VI.G2.\n"
            f"- **Options:** each option's year-by-year change in cost and income rates, "
            f"from [OCACT's provision tables]({OCACT_INDEX_URL}).\n"
            "- **Ledger:** reserves grow at the Trustees' interest factor plus each year's "
            "income minus cost. Depletion is the first year reserves end negative.\n"
            "- **Checks:** current law comes out at 2034 and 83% payable (Trustees: 2034, 83%), "
            "and the 75-year balance at −4.44% (Trustees: −4.42%). Each option's change in the "
            "balance matches OCACT's own figure to 0.01 points, and its depletion year matches "
            "in 32 of 33 cases (one is a year early).\n"
            "- **Not modelled:** interactions between options, effects on the rest of the "
            "budget, distributional effects, and Medicare's trust fund. For the ten-year "
            "budget cost of payroll tax changes, use the payroll presets on Explore."
        )


def render(st_module: Any, deps: Any, app_root: Any = None) -> None:
    """Render the Social Security reform menu."""
    del app_root
    render_chrome(st_module=st_module, deps=deps)

    st_module.markdown("## Social Security trust fund")
    st_module.markdown(
        "Pick reform options and see how far they go toward keeping Social Security "
        "solvent for the next 75 years."
    )
    st_module.info(TIER_NOTE)

    menu_col, result_col = st_module.columns([2, 3])
    with menu_col:
        st_module.markdown("#### Options")
        selected = _render_menu(st_module)

    baseline = project(())
    plan = project(selected)
    with result_col:
        _render_metrics(st_module, plan, baseline)
        _render_chart(st_module, plan, baseline)

    _render_selection_table(st_module, plan)
    st_module.caption(FRAMING_NOTE)
    _render_crfb_comparison(st_module)
    _render_method(st_module)
    render_page_footer(st_module)
