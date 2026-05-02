#!/usr/bin/env python3
"""
Run the release-readiness gate.

This is the CI-friendly companion to ``scripts/run_validation_dashboard.py``.
It evaluates the same readiness contract exposed by ``GET /readiness`` and
exits non-zero only when the verdict is ``not_ready`` by default. Use
``--strict`` for release gates that require an exact ``ready`` verdict.

Usage:
    python scripts/check_readiness.py
    python scripts/check_readiness.py --json
    python scripts/check_readiness.py --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.readiness import build_readiness_report, readiness_to_dict  # noqa: E402


def _print_human(payload: dict) -> None:
    print(f"Readiness verdict: {payload['verdict']}")
    print(
        f"Checks: {payload['pass_count']} pass, "
        f"{payload['warn_count']} warn, {payload['fail_count']} fail"
    )
    print()
    for check in payload["checks"]:
        required = "required" if check["required"] else "optional"
        print(
            f"[{check['status'].upper():4}] "
            f"{check['name']} ({required}) — {check['summary']}"
        )

    if payload.get("issues"):
        print()
        print("Issues:")
        for issue in payload["issues"]:
            required = "required" if issue["required"] else "optional"
            print(
                f"- [{issue['severity'].upper():4}] "
                f"{issue['name']} ({required}) — {issue['summary']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the readiness report as JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat ready_with_warnings as a failing verdict.",
    )
    args = parser.parse_args()

    report = build_readiness_report()
    payload = readiness_to_dict(report)

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        _print_human(payload)

    if report.verdict == "not_ready":
        return 1
    if args.strict and report.verdict != "ready":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
