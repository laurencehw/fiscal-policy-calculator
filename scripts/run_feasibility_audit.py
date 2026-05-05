#!/usr/bin/env python3
"""
Run executable feasibility checks for CPS microsim and pilot multi-model comparison.

Examples:
    python scripts/run_feasibility_audit.py
    python scripts/run_feasibility_audit.py --json
    python scripts/run_feasibility_audit.py --include-model-pilot
    python scripts/run_feasibility_audit.py --include-model-pilot --include-experimental-pwbm
    python scripts/run_feasibility_audit.py --include-model-pilot --use-synthetic-cbo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.feasibility import (  # noqa: E402
    assess_model_pilot_comparison,
    audit_cps_microsim_readiness,
)
from fiscal_model.models.comparison import (  # noqa: E402
    build_default_comparison_models,
    compare_policy_models,
)
from fiscal_model.policies import PolicyType, TaxPolicy  # noqa: E402
from fiscal_model.scoring import FiscalPolicyScorer  # noqa: E402


def _default_policy() -> TaxPolicy:
    return TaxPolicy(
        name="Feasibility Pilot — Top Rate +2pp",
        description="Shared pilot policy used to exercise the current multi-model contract.",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=500_000,
        duration_years=10,
        phase_in_years=1,
        taxable_income_elasticity=0.25,
        data_year=2022,
    )


def _print_text_report(audit, comparison_bundle, model_assessment, model_config) -> None:
    print("CPS Microsim Feasibility Audit")
    print(f"Microdata: {'found' if audit.microdata_exists else 'missing'}")
    print(f"Raw CPS files: {'ready' if audit.raw_person_exists and audit.raw_household_exists else 'incomplete'}")
    print(f"Ready for spike: {'yes' if audit.ready_for_spike else 'no'}")
    print(f"Rows: {audit.row_count:,}")
    print(f"Required columns missing: {', '.join(audit.missing_required_columns) or 'none'}")
    if audit.checks:
        print("")
        print("Weighted sanity checks")
        for check in audit.checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"- {check.name}: {check.actual:,.2f} {check.unit} [{status}]")
    if audit.warnings:
        print("")
        print("Warnings")
        for warning in audit.warnings:
            print(f"- {warning}")

    if comparison_bundle is not None:
        print("")
        print("Pilot model comparison")
        if model_config:
            print(f"IRS-backed CBO path: {'yes' if model_config['use_real_data'] else 'no'}")
            print(
                "Experimental PWBM included: "
                f"{'yes' if model_config['include_experimental_pwbm'] else 'no'}"
            )
        if comparison_bundle.results:
            print(comparison_bundle.to_dataframe().to_string(index=False))
            if comparison_bundle.max_gap is not None:
                print(f"\nMax 10-year gap: {comparison_bundle.max_gap:,.1f}B")
        if comparison_bundle.errors:
            print("")
            print("Model errors")
            for model_name, error in comparison_bundle.errors.items():
                print(f"- {model_name}: {error}")
        if model_assessment is not None:
            print("")
            print(f"Pilot model assessment: {model_assessment.status}")
            if model_assessment.blockers:
                print("Blockers")
                for blocker in model_assessment.blockers:
                    print(f"- {blocker}")
            if model_assessment.warnings:
                print("Warnings")
                for warning in model_assessment.warnings:
                    print(f"- {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--include-model-pilot",
        action="store_true",
        help="Run the current default CBO/TPC pilot comparison for a default test policy.",
    )
    parser.add_argument(
        "--include-experimental-pwbm",
        action="store_true",
        help=(
            "Include the experimental PWBM-OLG adapter in the pilot comparison. "
            "This is expected to fail strict feasibility until the adapter is calibrated."
        ),
    )
    parser.add_argument(
        "--use-synthetic-cbo",
        action="store_true",
        help=(
            "Use the synthetic fallback CBO-style scorer for the model pilot. "
            "By default the audit uses repo IRS data because that is the "
            "decision-relevant comparison path."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 when CPS or included model-pilot feasibility is blocked.",
    )
    args = parser.parse_args()

    audit = audit_cps_microsim_readiness(project_root=PROJECT_ROOT)
    comparison_bundle = None
    model_assessment = None
    model_config = None

    if args.include_model_pilot:
        model_config = {
            "include_experimental_pwbm": args.include_experimental_pwbm,
            "use_real_data": not args.use_synthetic_cbo,
        }
        models = build_default_comparison_models(
            FiscalPolicyScorer,
            use_real_data=model_config["use_real_data"],
            include_experimental_pwbm=args.include_experimental_pwbm,
        )
        comparison_bundle = compare_policy_models(
            _default_policy(),
            models,
            continue_on_error=True,
        )
        model_assessment = assess_model_pilot_comparison(comparison_bundle)

    if args.json:
        payload = {
            "cps_microsim": audit.to_dict(),
            "model_pilot": comparison_bundle.to_dict() if comparison_bundle is not None else None,
            "model_pilot_config": model_config,
            "model_pilot_assessment": (
                model_assessment.to_dict() if model_assessment is not None else None
            ),
        }
        print(json.dumps(payload, indent=2))
    else:
        _print_text_report(audit, comparison_bundle, model_assessment, model_config)

    if args.strict:
        if not audit.ready_for_spike:
            return 2
        if model_assessment is not None and not model_assessment.ready_for_spike:
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

