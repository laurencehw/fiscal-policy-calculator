#!/usr/bin/env python3
"""
Regenerate the one versioned report of current validation evidence.

The About page, the Methodology page, the Ask assistant and the live headline
sentences in the README, ``CLAUDE.md`` and ``docs/`` all quote the same
validation figures. They used to type them, and PR #173 showed what that costs:
the out-of-sample tier moved 18.0% -> 15.2% and three surfaces kept printing
18.0%. This script writes those figures to
``fiscal_model/data_files/validation/current_evidence.json`` from the same
computations the validation reports run, the surfaces read the file, and
``tests/test_current_evidence.py`` recomputes it and fails if it has drifted.

Run it whenever a change moves a validation tier -- the test says so by name
when you forget -- and then update the live headline sentences the test lists.

Usage::

    python scripts/build_current_evidence.py
    python scripts/build_current_evidence.py --check   # CI-style, no write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.current_evidence import (  # noqa: E402
    EVIDENCE_PATH,
    build_payload,
    load_evidence,
    reset_cache,
    write_payload,
)


def compute_payload() -> dict[str, Any]:
    """Run the four computations and assemble the report (about 15s, mostly scoring)."""
    from fiscal_model.health import check_health
    from fiscal_model.validation.loo import run_leave_one_out
    from scripts.cold_holdout import build_report
    from scripts.run_validation_dashboard import collect_calibrated_tiers

    holdout_report = build_report()
    calibrated_tiers = collect_calibrated_tiers(holdout_report)
    if "error" in calibrated_tiers:
        raise RuntimeError(calibrated_tiers["error"])
    return build_payload(
        holdout_report=holdout_report,
        calibrated_tiers=calibrated_tiers,
        loo_suite=run_leave_one_out().to_dict(),
        health=check_health(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed report differs from this tree's "
        "computation, without writing.",
    )
    args = parser.parse_args(argv)

    payload = compute_payload()
    reset_cache()
    committed = load_evidence()

    if args.check:
        if committed == payload:
            oos = payload["out_of_sample"]
            print(
                f"OK: {EVIDENCE_PATH.name} matches this tree "
                f"(out-of-sample {oos['n']} @ {oos['mean_abs_error']}%)"
            )
            return 0
        print("STALE: committed report does not match this tree's computation")
        print("  committed:", json.dumps(committed, sort_keys=True)[:2000])
        print("  live:     ", json.dumps(payload, sort_keys=True)[:2000])
        print("  fix: python scripts/build_current_evidence.py")
        return 1

    write_payload(payload)
    changed = committed != payload
    oos = payload["out_of_sample"]
    fitted = payload["calibrated"]["fitted"]
    recon = payload["calibrated"]["reconstruction"]
    print(f"{'wrote' if changed else 'unchanged'}: {EVIDENCE_PATH}")
    print(
        f"  out-of-sample {oos['n']} @ {oos['mean_abs_error']}% "
        f"(median {oos['median_abs_error']}%, {oos['within_25pct']} within 25%) | "
        f"fitted {fitted['n']} @ {fitted['mean_abs_error']}% | "
        f"reconstructions {recon['n']} @ {recon['mean_abs_error']}%"
    )
    if changed:
        print(
            "  Now update the live headline sentences tests/test_current_evidence.py "
            "pins (README, CLAUDE.md, docs/VALIDATION.md, docs/METHODOLOGY.md)."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
