#!/usr/bin/env python3
"""
Generate a manuscript-facing validation appendix in markdown.

Usage:
    python scripts/generate_validation_appendix.py
    python scripts/generate_validation_appendix.py --output docs/validation_appendix_generated.md
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.compare import (  # noqa: E402
    generate_validation_report,
    validate_all,
    validate_all_amt,
    validate_all_capital_gains,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_expenditures,
    validate_all_payroll,
    validate_all_ptc,
    validate_all_tcja,
)
from fiscal_model.validation.core import ValidationResult  # noqa: E402


def collect_validation_results() -> list[ValidationResult]:
    """Collect the current cross-category validation results and de-duplicate them."""
    suites = [
        validate_all_tcja(verbose=False),
        validate_all_corporate(verbose=False),
        validate_all_credits(verbose=False),
        validate_all_estate(verbose=False),
        validate_all_payroll(verbose=False),
        validate_all_amt(verbose=False),
        validate_all_ptc(verbose=False),
        validate_all_expenditures(verbose=False),
        validate_all_capital_gains(verbose=False),
    ]

    deduped: dict[str, ValidationResult] = {}
    for suite in suites:
        for result in suite:
            deduped[result.policy_id] = result

    return sorted(deduped.values(), key=lambda result: result.policy_name.lower())


def main() -> int:
    """Generate the appendix and print it or write it to disk."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the generated markdown appendix.",
    )
    parser.add_argument(
        "--include-core-database",
        action="store_true",
        help="Include the broader validate_all() score database in addition to the curated category suites.",
    )
    args = parser.parse_args()

    results = collect_validation_results()
    if args.include_core_database:
        results.extend(validate_all(dynamic=False, verbose=False))
        deduped = {result.policy_id: result for result in results}
        results = sorted(deduped.values(), key=lambda result: result.policy_name.lower())

    report = generate_validation_report(results)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"Wrote validation appendix to {args.output}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
