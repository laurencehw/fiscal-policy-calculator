#!/usr/bin/env python
"""Audit every policy class's behavioural offset against the engine's sign contract.

``fiscal_model/scoring_engine.py`` books a score as
``deficit_after = (static_spending - static_revenue) + behavioral``, and hands
``estimate_behavioral_offset`` the year's **static revenue** effect. So an
offset carrying the *same* sign as static **erodes** the revenue change in both
directions — a tax increase raises less than its static figure, a tax cut loses
less than its static figure — and an offset carrying the *opposite* sign
**magnifies** it.  ``TaxPolicy.estimate_behavioral_offset`` states that contract
in its docstring; four modules were found not following it, each by a lane
looking at something else and none by a test.

This script is the test.  For every class that implements or inherits the
offset it builds a synthetic revenue **increase** and a synthetic revenue
**cut**, and runs two probes:

* **Probe A — the function.**  ``estimate_behavioral_offset(+100)`` *and*
  ``(-100)`` on each instance.  This is the sign rule the class implements,
  independent of whether its own factories ever produce a negative static —
  which matters, because ``IRSEnforcementPolicy`` cannot express a revenue
  loss at all and its ``abs()`` would otherwise read as compliance.
* **Probe B — the score.**  ``FiscalPolicyScorer.score_policy(dynamic=False)``
  on both, comparing ``|final_deficit|`` with ``|static_deficit|`` over the
  window.

The classification is assigned from what the probes return, not from what the
docstring says:

``correct``      erodes both directions (same sign as static)
``inverted``     magnifies both directions (opposite sign)
``abs``          always one sign — erodes whichever direction matches
``asymmetric``   erodes one direction, magnifies the other, by some other rule
``zero``         returns 0.0
``convention``   opposite-signed on purpose, with a source (see CONVENTIONS)

Usage::

    python scripts/audit_offset_signs.py            # markdown table
    python scripts/audit_offset_signs.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from fiscal_model.amt import AMT_MODE_REPORTED, AMTPolicy, AMTType
from fiscal_model.corporate import (
    CORPORATE_MODE_DERIVED,
    CORPORATE_MODE_REPORTED,
    create_corporate_rate_change,
)
from fiscal_model.credits_core import CreditType, TaxCreditPolicy
from fiscal_model.enforcement import IRSEnforcementPolicy
from fiscal_model.estate import EstateTaxPolicy
from fiscal_model.international import (
    InternationalReformType,
    InternationalTaxPolicy,
)
from fiscal_model.payroll import PayrollTaxPolicy
from fiscal_model.policies_core import (
    CapitalGainsPolicy,
    PolicyType,
    TaxPolicy,
)
from fiscal_model.ptc import PremiumTaxCreditPolicy, PTCScenario
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.tax_expenditures_core import (
    TaxExpenditurePolicy,
    TaxExpenditureType,
)
from fiscal_model.tcja import create_tcja_extension
from fiscal_model.trade import TariffPolicy

PROBE = 100.0

#: Cases whose offset is opposite-signed **on purpose**, with the source that
#: says the behavioural response raises revenue for that reform.  Keyed on the
#: case label rather than the class, because lane W7 settled item 8 by making
#: the direction a property of the **reform**: ``TaxExpenditurePolicy`` now
#: magnifies where a document says so and erodes everywhere else, so the class
#: is no longer a blanket exception and two of its cases appear below carrying
#: opposite tags.
CONVENTIONS: dict[str, str] = {
    "TaxExpenditurePolicy [SALT]": (
        "CBO, extended discussion of Option 49 (budget-options/58635), second "
        "alternative - this same reform: reduced spending on other deductible "
        "items 'would further decrease their itemized deductions and increase "
        "their tax liability'. The expand direction is its mirror, priced by "
        "Yale Budget Lab: raising the SALT limit brings in new itemizers who "
        "then deduct mortgage interest too, so the loss exceeds the SALT "
        "figure alone."
    ),
}


@dataclass
class Case:
    """One class, in a revenue-raising and a revenue-losing configuration."""

    label: str
    module: str
    build_increase: Callable[[], Any]
    build_cut: Callable[[], Any] | None
    static_kwargs: dict[str, Any] = field(default_factory=dict)
    note: str = ""
    #: ``"function"`` classifies from Probe A's two calls; ``"score"`` from
    #: Probe B's window totals, for a class that does not read
    #: ``static_effect`` at all and so has no function-level sign rule.
    classify_from: str = "function"


def _static(policy: Any, **kwargs: Any) -> float:
    """The module's own annual static revenue effect, whatever its signature."""
    try:
        return float(policy.estimate_static_revenue_effect(0.0, **kwargs))
    except TypeError:
        return float(policy.estimate_static_revenue_effect(0.0))


def _offset(policy: Any, static_effect: float) -> float:
    return float(policy.estimate_behavioral_offset(static_effect))


def _relation(static_effect: float, offset: float) -> str:
    if offset == 0.0:
        return "zero"
    if static_effect == 0.0:
        return "n/a"
    return "erode" if (offset > 0.0) == (static_effect > 0.0) else "magnify"


def classify_pair(off_at_plus: float, off_at_minus: float) -> str:
    """Assign a tag from one instance's response to ``+PROBE`` and ``-PROBE``.

    This is the class's *sign rule*, which is what the contract is about. It is
    deliberately independent of whether the class's own factories ever hand it
    a negative static: an ``abs()`` that is only ever fed positives is still an
    ``abs()``, and the next caller — Tailor, the composer, the bill tracker —
    is not bound by the factories.
    """
    rel_plus = _relation(PROBE, off_at_plus)
    rel_minus = _relation(-PROBE, off_at_minus)
    if rel_plus == "zero" and rel_minus == "zero":
        return "zero"
    if rel_plus == "erode" and rel_minus == "erode":
        return "correct"
    if rel_plus == "magnify" and rel_minus == "magnify":
        return "inverted"
    # An ``abs()`` shows up as two offsets of the *same* sign against two
    # statics of opposite sign.
    if (
        off_at_plus != 0.0
        and off_at_minus != 0.0
        and (off_at_plus > 0.0) == (off_at_minus > 0.0)
    ):
        return "abs"
    return "asymmetric"


def classify_from_score(rows: dict[str, Any]) -> str:
    """Tag a class that ignores ``static_effect``, from Probe B's window totals."""
    sides = [rows[side] for side in ("increase", "cut") if rows[side] is not None]
    relations = {
        _relation(-side["window_static_deficit"], side["window_behavioural"])
        for side in sides
    }
    if relations == {"zero"}:
        return "zero"
    if relations == {"erode"}:
        return "correct"
    if relations == {"magnify"}:
        return "inverted"
    return "asymmetric"


def build_cases() -> list[Case]:
    """Every class that implements or inherits ``estimate_behavioral_offset``.

    ``pharma.DrugPricingPolicy``, ``climate.ClimateEnergyPolicy``,
    ``SpendingPolicy`` and ``TransferPolicy`` are deliberately absent: the
    engine books ``np.zeros`` for their behavioural term and never calls the
    method.
    """
    return [
        Case(
            "TaxPolicy",
            "policies_core.py",
            lambda: TaxPolicy(
                name="Rate +2pp above $400K",
                description="synthetic increase",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=0.02,
                affected_income_threshold=400_000,
            ),
            lambda: TaxPolicy(
                name="Rate -2pp above $400K",
                description="synthetic cut",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=-0.02,
                affected_income_threshold=400_000,
            ),
            note="the contract itself",
        ),
        Case(
            "CapitalGainsPolicy",
            "policies_core.py",
            lambda: CapitalGainsPolicy(
                name="LTCG +2pp above $400K",
                description="synthetic increase",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                rate_change=0.02,
                affected_income_threshold=400_000,
            ),
            lambda: CapitalGainsPolicy(
                name="LTCG -2pp above $400K",
                description="synthetic cut",
                policy_type=PolicyType.CAPITAL_GAINS_TAX,
                rate_change=-0.02,
                affected_income_threshold=400_000,
            ),
            static_kwargs={"year": 2026},
            note="offset ignores static_effect; rebuilt bracket by bracket",
            classify_from="score",
        ),
        Case(
            "AMTPolicy",
            "amt.py",
            lambda: AMTPolicy(
                name="AMT +$100B/yr",
                description="synthetic increase",
                policy_type=PolicyType.INCOME_TAX,
                amt_type=AMTType.INDIVIDUAL,
                annual_revenue_change_billions=PROBE,
                mode=AMT_MODE_REPORTED,
            ),
            lambda: AMTPolicy(
                name="AMT -$100B/yr",
                description="synthetic cut",
                policy_type=PolicyType.INCOME_TAX,
                amt_type=AMTType.INDIVIDUAL,
                annual_revenue_change_billions=-PROBE,
                mode=AMT_MODE_REPORTED,
            ),
            note="module-default timing 0.15 / avoidance 0.10",
        ),
        Case(
            "CorporateTaxPolicy [reported]",
            "corporate.py",
            lambda: create_corporate_rate_change(
                rate_change=0.06, mode=CORPORATE_MODE_REPORTED
            ),
            lambda: create_corporate_rate_change(
                rate_change=-0.06, mode=CORPORATE_MODE_REPORTED
            ),
            note="CORPORATE_APP_MODE - what the shipped app scores",
        ),
        Case(
            "CorporateTaxPolicy [derived]",
            "corporate.py",
            lambda: create_corporate_rate_change(
                rate_change=0.06, mode=CORPORATE_MODE_DERIVED
            ),
            lambda: create_corporate_rate_change(
                rate_change=-0.06, mode=CORPORATE_MODE_DERIVED
            ),
            note="signed by Wave 5 B",
        ),
        Case(
            "TaxCreditPolicy [EITC/CTC]",
            "credits_core.py",
            lambda: TaxCreditPolicy(
                name="EITC -$500/unit",
                description="synthetic increase",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.EARNED_INCOME_CREDIT,
                credit_change_per_unit=-500.0,
                units_affected_millions=40.0,
            ),
            lambda: TaxCreditPolicy(
                name="EITC +$500/unit",
                description="synthetic cut",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.EARNED_INCOME_CREDIT,
                credit_change_per_unit=500.0,
                units_affected_millions=40.0,
            ),
            note="the two named credit branches",
        ),
        Case(
            "TaxCreditPolicy [other credits]",
            "credits_core.py",
            lambda: TaxCreditPolicy(
                name="Education credit -$500/unit",
                description="synthetic increase",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.EDUCATION_CREDIT,
                credit_change_per_unit=-500.0,
                units_affected_millions=40.0,
            ),
            lambda: TaxCreditPolicy(
                name="Education credit +$500/unit",
                description="synthetic cut",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.EDUCATION_CREDIT,
                credit_change_per_unit=500.0,
                units_affected_millions=40.0,
            ),
            note="the labour-supply fallback branch",
        ),
        Case(
            "IRSEnforcementPolicy",
            "enforcement.py",
            lambda: IRSEnforcementPolicy(
                name="Enforcement +$16B/yr",
                description="synthetic increase",
                policy_type=PolicyType.INCOME_TAX,
                annual_enforcement_spending_billions=16.0,
            ),
            None,
            note="no cut direction: negative funding clamps the static to 0",
        ),
        Case(
            "EstateTaxPolicy",
            "estate.py",
            lambda: EstateTaxPolicy(
                name="Estate rate +5pp",
                description="synthetic increase",
                policy_type=PolicyType.ESTATE_TAX,
                rate_change=0.05,
            ),
            lambda: EstateTaxPolicy(
                name="Estate rate -5pp",
                description="synthetic cut",
                policy_type=PolicyType.ESTATE_TAX,
                rate_change=-0.05,
            ),
            note="module-default planning 0.16 / gift shifting 0.10",
        ),
        Case(
            "InternationalTaxPolicy",
            "international.py",
            lambda: InternationalTaxPolicy(
                name="GILTI to 21%",
                description="synthetic increase",
                policy_type=PolicyType.CORPORATE_TAX,
                reform_type=InternationalReformType.GILTI_REFORM,
                gilti_country_by_country=True,
                gilti_new_rate=0.21,
            ),
            lambda: InternationalTaxPolicy(
                name="GILTI to 5%",
                description="synthetic cut",
                policy_type=PolicyType.CORPORATE_TAX,
                reform_type=InternationalReformType.GILTI_REFORM,
                gilti_country_by_country=True,
                gilti_new_rate=0.05,
            ),
            note="profit-shifting elasticity is never zeroed by a factory",
        ),
        Case(
            "PayrollTaxPolicy",
            "payroll.py",
            lambda: PayrollTaxPolicy(
                name="OASDI +1pp",
                description="synthetic increase",
                policy_type=PolicyType.PAYROLL_TAX,
                ss_rate_change=0.01,
            ),
            lambda: PayrollTaxPolicy(
                name="OASDI -1pp",
                description="synthetic cut",
                policy_type=PolicyType.PAYROLL_TAX,
                ss_rate_change=-0.01,
            ),
            note="signed by Wave 5 A",
        ),
        Case(
            "PremiumTaxCreditPolicy",
            "ptc.py",
            lambda: PremiumTaxCreditPolicy(
                name="Repeal PTC",
                description="synthetic increase",
                policy_type=PolicyType.TAX_CREDIT,
                scenario=PTCScenario.REPEAL_PTC,
                repeal_ptc=True,
            ),
            lambda: PremiumTaxCreditPolicy(
                name="Extend enhanced PTC",
                description="synthetic cut",
                policy_type=PolicyType.TAX_CREDIT,
                scenario=PTCScenario.EXTEND_ENHANCED,
                extend_enhanced=True,
            ),
            note="module-default coverage 0.3 / adverse selection 0.1",
        ),
        Case(
            "TaxExpenditurePolicy [SALT]",
            "tax_expenditures_core.py",
            lambda: TaxExpenditurePolicy(
                name="Eliminate SALT deduction",
                description="synthetic increase",
                policy_type=PolicyType.INCOME_TAX,
                expenditure_type=TaxExpenditureType.SALT,
                action="eliminate",
            ),
            lambda: TaxExpenditurePolicy(
                name="Expand SALT deduction",
                description="synthetic cut",
                policy_type=PolicyType.INCOME_TAX,
                expenditure_type=TaxExpenditureType.SALT,
                action="expand",
            ),
            static_kwargs={"year": 2026},
            note="CBO 58635 alt 2: the response raises revenue",
        ),
        Case(
            "TaxExpenditurePolicy [mortgage]",
            "tax_expenditures_core.py",
            lambda: TaxExpenditurePolicy(
                name="Eliminate mortgage interest deduction",
                description="synthetic increase",
                policy_type=PolicyType.INCOME_TAX,
                expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
                action="eliminate",
            ),
            lambda: TaxExpenditurePolicy(
                name="Expand mortgage interest deduction",
                description="synthetic cut",
                policy_type=PolicyType.INCOME_TAX,
                expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
                action="expand",
            ),
            static_kwargs={"year": 2026},
            note="Poterba & Sinai: portfolio adjustment erodes the repeal",
        ),
        Case(
            "TCJAExtensionPolicy",
            "tcja.py",
            create_tcja_extension,
            None,
            note="returns 0.0: CBO's $4.6T already embeds behaviour",
        ),
        Case(
            "TariffPolicy",
            "trade.py",
            lambda: TariffPolicy(
                name="Tariff +10pp",
                description="synthetic increase",
                policy_type=PolicyType.EXCISE_TAX,
                tariff_rate_change=0.10,
                import_base_billions=1000.0,
            ),
            lambda: TariffPolicy(
                name="Tariff -10pp",
                description="synthetic cut",
                policy_type=PolicyType.EXCISE_TAX,
                tariff_rate_change=-0.10,
                import_base_billions=1000.0,
            ),
            note="signed by Wave 3 L8",
        ),
    ]


def probe(case: Case, scorer: FiscalPolicyScorer) -> dict[str, Any]:
    """Run both probes for one case and classify."""
    row: dict[str, Any] = {
        "class": case.label,
        "module": case.module,
        "note": case.note,
    }

    for side, builder in (("increase", case.build_increase), ("cut", case.build_cut)):
        if builder is None:
            row[side] = None
            continue
        policy = builder()
        static_annual = _static(policy, **case.static_kwargs)
        result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)
        static_window = float(np.sum(result.static_deficit_effect))
        final_window = float(np.sum(result.final_deficit_effect))
        behavioural_window = float(np.sum(result.behavioral_offset))
        row[side] = {
            "static_annual_billions": static_annual,
            "offset_at_plus_probe": _offset(policy, PROBE),
            "offset_at_minus_probe": _offset(policy, -PROBE),
            "window_static_deficit": static_window,
            "window_behavioural": behavioural_window,
            "window_final_deficit": final_window,
            "erodes": abs(final_window) <= abs(static_window) + 1e-9,
        }

    inc = row["increase"]
    cut = row["cut"]
    if case.classify_from == "score":
        tag = classify_from_score(row)
    else:
        tag = classify_pair(inc["offset_at_plus_probe"], inc["offset_at_minus_probe"])
        if cut is not None:
            cross = classify_pair(
                cut["offset_at_plus_probe"], cut["offset_at_minus_probe"]
            )
            if cross != tag:
                row["cross_check"] = (
                    f"increase instance reads {tag}, cut instance reads {cross}"
                )
    # Keyed on the full label, not the class: since lane W7 a class can hold a
    # sourced convention on one reform and the plain contract on another.
    if case.label in CONVENTIONS and tag == "inverted":
        tag = "convention"
        row["source"] = CONVENTIONS[case.label]
    row["classification"] = tag
    return row


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:,.1f}"


def render_markdown(rows: list[dict[str, Any]]) -> str:
    """The inventory table, in the shape the lane doc carries it."""
    lines = [
        "| class | module | dir | static/yr | f(+100) | f(-100) | window static | "
        "window behav | window final | erodes | tag |",
        "|---|---|---|--:|--:|--:|--:|--:|--:|:-:|---|",
    ]
    for row in rows:
        for side in ("increase", "cut"):
            data = row[side]
            head = row["class"] if side == "increase" else ""
            mod = row["module"] if side == "increase" else ""
            tag = row["classification"] if side == "cut" else ""
            if data is None:
                lines.append(
                    f"| {head} | {mod} | {side} | - | - | - | - | - | - | - | {tag} |"
                )
                continue
            lines.append(
                f"| {head} | {mod} | {side} "
                f"| {_fmt(data['static_annual_billions'])} "
                f"| {_fmt(data['offset_at_plus_probe'])} "
                f"| {_fmt(data['offset_at_minus_probe'])} "
                f"| {_fmt(data['window_static_deficit'])} "
                f"| {_fmt(data['window_behavioural'])} "
                f"| {_fmt(data['window_final_deficit'])} "
                f"| {'yes' if data['erodes'] else '**NO**'} "
                f"| {tag} |"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    scorer = FiscalPolicyScorer()
    rows = [probe(case, scorer) for case in build_cases()]

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print()
    print("  Behavioural-offset sign contract - deficit = -revenue + behavioural,")
    print("  so an offset with the STATIC's sign erodes and the opposite sign magnifies.")
    print()
    print(render_markdown(rows))
    print()
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    print("  " + "   ".join(f"{tag}: {n}" for tag, n in sorted(counts.items())))
    defects = [r["class"] for r in rows if r["classification"] in ("abs", "inverted", "asymmetric")]
    if defects:
        print("  against the contract: " + ", ".join(defects))
    for row in rows:
        if "source" in row:
            print(f"\n  {row['class']} - convention, source:\n    {row['source']}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
